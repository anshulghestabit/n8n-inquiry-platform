from datetime import UTC, datetime
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.db.client import get_supabase_admin_client
from app.middleware.auth import get_current_user


router = APIRouter(prefix="/system", tags=["system"])
settings = get_settings()

SourceType = Literal["gmail", "telegram", "google_drive", "google_sheets"]
SOURCE_TYPES: list[SourceType] = ["gmail", "telegram", "google_drive", "google_sheets"]


class IntegrationActionRequest(BaseModel):
    credential_hint: str = Field(min_length=8, max_length=500)


def api_error(status_code: int, message: str, code: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": message, "code": code})


def get_data_source_map(db, user_id: str) -> dict[str, dict]:
    try:
        sources = (
            db.table("data_sources")
            .select("source_type, is_connected, last_verified_at")
            .eq("user_id", user_id)
            .execute()
        )
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    return {
        row.get("source_type"): {
            "is_connected": bool(row.get("is_connected")),
            "last_verified_at": row.get("last_verified_at"),
        }
        for row in (sources.data or [])
        if row.get("source_type") in SOURCE_TYPES
    }


def upsert_data_source(db, user_id: str, source_type: SourceType, is_connected: bool, last_verified_at: str | None) -> dict:
    payload = {
        "user_id": user_id,
        "source_type": source_type,
        "is_connected": is_connected,
        "last_verified_at": last_verified_at,
    }
    try:
        result = db.table("data_sources").upsert(payload, on_conflict="user_id,source_type").execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")
    return result.data[0]


async def n8n_request(method: str, path: str) -> dict | list:
    if not settings.n8n_api_key:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "n8n API key is not configured", "N8N_UNAVAILABLE")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{settings.n8n_url}{path}",
                headers={"X-N8N-API-KEY": settings.n8n_api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"n8n API returned HTTP {exc.response.status_code}",
            "N8N_UNAVAILABLE",
        )
    except httpx.RequestError:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "n8n API unavailable", "N8N_UNAVAILABLE")


def normalize_rows(payload: dict | list) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def credential_refs_from_workflows(workflows: list[dict]) -> dict[str, list[dict]]:
    refs: dict[str, list[dict]] = {source_type: [] for source_type in SOURCE_TYPES}
    credential_map = {
        "gmailOAuth2": "gmail",
        "telegramApi": "telegram",
        "googleDriveOAuth2Api": "google_drive",
        "googleSheetsOAuth2Api": "google_sheets",
    }

    for workflow in workflows:
        for node in workflow.get("nodes") or []:
            credentials = node.get("credentials") or {}
            if not isinstance(credentials, dict):
                continue
            for credential_type, source_type in credential_map.items():
                credential = credentials.get(credential_type)
                if isinstance(credential, dict) and credential.get("id"):
                    refs[source_type].append(
                        {
                            "id": str(credential["id"]),
                            "name": credential.get("name"),
                            "node": node.get("name"),
                            "workflow": workflow.get("name"),
                        }
                    )
    return refs


async def credential_exists(credential_id: str) -> bool:
    try:
        await n8n_request("GET", f"/api/v1/credentials/{credential_id}")
        return True
    except HTTPException as exc:
        if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            return False
        raise


async def verify_telegram_bot() -> dict:
    if not settings.telegram_bot_token:
        raise api_error(status.HTTP_400_BAD_REQUEST, "TELEGRAM_BOT_TOKEN is not configured", "INTEGRATION_VERIFY_FAILED")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe",
                timeout=10.0,
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPStatusError, httpx.RequestError):
        raise api_error(status.HTTP_400_BAD_REQUEST, "Telegram bot token verification failed", "INTEGRATION_VERIFY_FAILED")

    if not payload.get("ok"):
        raise api_error(status.HTTP_400_BAD_REQUEST, "Telegram bot token verification failed", "INTEGRATION_VERIFY_FAILED")

    return {"bot": payload.get("result", {}).get("username")}


async def verify_integration_connection(source_type: SourceType) -> dict:
    workflows = normalize_rows(await n8n_request("GET", "/api/v1/workflows"))
    refs = credential_refs_from_workflows(workflows).get(source_type, [])
    if not refs:
        detailed_workflows = []
        for workflow in workflows:
            workflow_id = workflow.get("id")
            if workflow_id:
                detailed = await n8n_request("GET", f"/api/v1/workflows/{workflow_id}")
                if isinstance(detailed, dict):
                    detailed_workflows.append(detailed)
        refs = credential_refs_from_workflows(detailed_workflows).get(source_type, [])
    if not refs:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            f"No {source_type} credential is attached to any n8n workflow node",
            "INTEGRATION_VERIFY_FAILED",
        )

    verified_refs = []
    for ref in refs:
        if await credential_exists(ref["id"]):
            verified_refs.append(ref)

    if not verified_refs:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            f"{source_type} credentials are referenced by workflows but not readable from n8n",
            "INTEGRATION_VERIFY_FAILED",
        )

    extra: dict = {}
    if source_type == "telegram":
        extra = await verify_telegram_bot()
    if source_type == "google_sheets" and not settings.google_sheet_id:
        raise api_error(status.HTTP_400_BAD_REQUEST, "GOOGLE_SHEET_ID is not configured", "INTEGRATION_VERIFY_FAILED")

    return {"credential_refs": verified_refs, **extra}


@router.get("/status")
async def system_status(current_user: dict = Depends(get_current_user)):
    connection_status = {
        "n8n": False,
        "gmail": False,
        "telegram": False,
        "google_drive": False,
        "google_sheets": False,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.n8n_url}/api/v1/workflows",
                headers={"X-N8N-API-KEY": settings.n8n_api_key},
                timeout=3.0,
            )
            connection_status["n8n"] = response.status_code == 200
    except Exception:
        connection_status["n8n"] = False

    db = get_supabase_admin_client()
    sources = get_data_source_map(db, current_user["id"])

    for source_type in SOURCE_TYPES:
        source = sources.get(source_type)
        if source:
            connection_status[source_type] = bool(source.get("is_connected"))

    return connection_status


@router.get("/integrations")
async def list_integrations(current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    sources = get_data_source_map(db, current_user["id"])

    return [
        {
            "source_type": source_type,
            "is_connected": bool(sources.get(source_type, {}).get("is_connected", False)),
            "last_verified_at": sources.get(source_type, {}).get("last_verified_at"),
        }
        for source_type in SOURCE_TYPES
    ]


@router.post("/integrations/{source_type}/connect")
async def connect_integration(
    source_type: SourceType,
    body: IntegrationActionRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_supabase_admin_client()
    verification = await verify_integration_connection(source_type)
    verified_at = datetime.now(UTC).isoformat()
    row = upsert_data_source(db, current_user["id"], source_type, True, verified_at)
    return {
        "source_type": row["source_type"],
        "is_connected": bool(row["is_connected"]),
        "last_verified_at": row.get("last_verified_at"),
        "verification": verification,
        "message": "Integration connected and verified",
    }


@router.post("/integrations/{source_type}/verify")
async def verify_integration(
    source_type: SourceType,
    body: IntegrationActionRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_supabase_admin_client()
    sources = get_data_source_map(db, current_user["id"])
    source = sources.get(source_type)
    if not source or not source.get("is_connected"):
        raise api_error(status.HTTP_400_BAD_REQUEST, "Integration is not connected", "INTEGRATION_NOT_CONNECTED")

    verification = await verify_integration_connection(source_type)
    verified_at = datetime.now(UTC).isoformat()
    row = upsert_data_source(db, current_user["id"], source_type, True, verified_at)
    return {
        "source_type": row["source_type"],
        "is_connected": bool(row["is_connected"]),
        "last_verified_at": row.get("last_verified_at"),
        "verification": verification,
        "message": "Integration verified",
    }


@router.post("/integrations/{source_type}/disconnect")
async def disconnect_integration(source_type: SourceType, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    row = upsert_data_source(db, current_user["id"], source_type, False, None)
    return {
        "source_type": row["source_type"],
        "is_connected": bool(row["is_connected"]),
        "last_verified_at": row.get("last_verified_at"),
        "message": "Integration disconnected",
    }
