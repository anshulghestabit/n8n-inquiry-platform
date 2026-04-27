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

SourceType = Literal["gmail", "whatsapp", "google_drive", "google_sheets"]
SOURCE_TYPES: list[SourceType] = ["gmail", "whatsapp", "google_drive", "google_sheets"]


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


@router.get("/status")
async def system_status(current_user: dict = Depends(get_current_user)):
    connection_status = {
        "n8n": False,
        "gmail": False,
        "whatsapp": False,
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
    verified_at = datetime.now(UTC).isoformat()
    row = upsert_data_source(db, current_user["id"], source_type, True, verified_at)
    return {
        "source_type": row["source_type"],
        "is_connected": bool(row["is_connected"]),
        "last_verified_at": row.get("last_verified_at"),
        "message": "Integration connected",
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

    verified_at = datetime.now(UTC).isoformat()
    row = upsert_data_source(db, current_user["id"], source_type, True, verified_at)
    return {
        "source_type": row["source_type"],
        "is_connected": bool(row["is_connected"]),
        "last_verified_at": row.get("last_verified_at"),
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
