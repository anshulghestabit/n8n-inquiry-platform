import asyncio
from datetime import UTC, datetime
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.db.client import get_supabase_admin_client
from app.export.pdf import render_execution_pdf
from app.export.txt import render_execution_report
from app.middleware.auth import get_current_user


router = APIRouter(tags=["executions"])

settings = get_settings()

AgentRole = Literal["classifier", "researcher", "qualifier", "responder", "executor"]
SourceChannel = Literal["gmail", "telegram", "test"]
ExecutionStatus = Literal["running", "paused", "success", "failed", "cancelled"]
LogStatus = Literal["success", "failed", "skipped"]
ExportFormat = Literal["json", "txt", "pdf"]

ROLE_ORDER = {
    "classifier": 1,
    "researcher": 2,
    "qualifier": 3,
    "responder": 4,
    "executor": 5,
}

N8N_TO_APP_STATUS = {
    "running": "running",
    "new": "running",
    "waiting": "running",
    "success": "success",
    "error": "failed",
    "crashed": "failed",
    "canceled": "cancelled",
}

NODE_TO_AGENT = {
    "Classifier_Agent": "classifier",
    "Researcher_Agent": "researcher",
    "Qualifier_Agent": "qualifier",
    "Responder_Agent": "responder",
    "Executor_Agent": "executor",
}


class TriggerExecutionRequest(BaseModel):
    inquiry_text: str = Field(min_length=1, max_length=6000)
    source_channel: SourceChannel = "test"
    sender_id: str | None = None


class AgentLogPayload(BaseModel):
    agent_role: AgentRole
    input: dict | None = None
    output: dict | None = None
    duration_ms: int = Field(default=0, ge=0)
    status: LogStatus = "success"
    error_message: str | None = None


class CompleteExecutionRequest(BaseModel):
    status: Literal["success", "failed", "cancelled"]
    final_reply: str | None = None
    score: int | None = Field(default=None, ge=1, le=10)
    n8n_execution_id: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    agent_logs: list[AgentLogPayload] = Field(default_factory=list)


class AppendAgentLogsRequest(BaseModel):
    agent_logs: list[AgentLogPayload] = Field(default_factory=list)


def api_error(status_code: int, message: str, code: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": message, "code": code})


def get_owned_workflow(db, workflow_id: str, user_id: str) -> dict:
    try:
        result = db.table("workflows").select("*").eq("id", workflow_id).eq("user_id", user_id).single().execute()
    except Exception:
        raise api_error(status.HTTP_404_NOT_FOUND, "Workflow not found", "NOT_FOUND")
    return result.data


def get_owned_execution(db, execution_id: str, user_id: str) -> dict:
    try:
        result = db.table("executions").select("*").eq("id", execution_id).eq("user_id", user_id).single().execute()
    except Exception:
        raise api_error(status.HTTP_404_NOT_FOUND, "Execution not found", "EXECUTION_NOT_FOUND")
    return result.data


def get_execution_logs(db, execution_id: str) -> list[dict]:
    result = db.table("agent_logs").select("*").eq("execution_id", execution_id).order("created_at").execute()
    logs = result.data or []
    return sorted(logs, key=lambda row: ROLE_ORDER.get(row.get("agent_role", ""), 99))


def n8n_headers() -> dict[str, str]:
    if not settings.n8n_api_key:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "n8n API key is not configured", "N8N_UNAVAILABLE")
    return {"X-N8N-API-KEY": settings.n8n_api_key}


async def n8n_request(method: str, path: str, payload: dict | None = None) -> dict:
    retryable_statuses = {408, 425, 429, 500, 502, 503, 504}
    attempts = 3
    timeout = 20.0
    last_error_message = "n8n API unavailable"

    for attempt in range(attempts):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    f"{settings.n8n_url}{path}",
                    headers=n8n_headers(),
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()

            if response.status_code == status.HTTP_204_NO_CONTENT:
                return {}
            return response.json()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            last_error_message = f"n8n API returned HTTP {status_code}"
            if status_code in retryable_statuses and attempt < attempts - 1:
                await asyncio.sleep(0.3 * (attempt + 1))
                continue
            break
        except httpx.RequestError as exc:
            last_error_message = f"n8n request failed: {exc.__class__.__name__}"
            if attempt < attempts - 1:
                await asyncio.sleep(0.3 * (attempt + 1))
                continue
            break
        except Exception:
            last_error_message = "n8n API unavailable"
            break

    raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, last_error_message, "N8N_UNAVAILABLE")


def _extract_n8n_execution_id(payload: dict) -> str | None:
    candidate = payload.get("id") or payload.get("executionId")
    if candidate:
        return str(candidate)
    data = payload.get("data")
    if isinstance(data, dict):
        nested = data.get("id") or data.get("executionId")
        if nested:
            return str(nested)
    return None


async def trigger_n8n_execution(workflow: dict, execution_id: str, body: TriggerExecutionRequest) -> str | None:
    n8n_workflow_id = workflow.get("n8n_workflow_id")
    if not n8n_workflow_id:
        raise api_error(status.HTTP_400_BAD_REQUEST, "Workflow has no linked n8n workflow", "N8N_WORKFLOW_MISSING")

    run_payload = {
        "workflowData": {
            "id": n8n_workflow_id,
        },
        "runData": {
            "execution_id": execution_id,
            "inquiry_text": body.inquiry_text,
            "source_channel": body.source_channel,
            "sender_id": body.sender_id,
        },
    }
    run_paths = [f"/rest/workflows/{n8n_workflow_id}/run", f"/api/v1/workflows/{n8n_workflow_id}/run"]
    for path in run_paths:
        response = await n8n_request("POST", path, run_payload)
        parsed = _extract_n8n_execution_id(response)
        if parsed:
            return parsed

    raise api_error(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "n8n run request did not return an execution id",
        "N8N_DISPATCH_FAILED",
    )


def _derive_quality_metrics(agent_logs: list[dict], inquiry_text: str | None, final_reply: str | None) -> dict:
    inquiry = (inquiry_text or "").strip()
    reply = (final_reply or "").strip()
    inquiry_tokens = {token for token in inquiry.lower().split() if len(token) > 3}
    reply_tokens = {token for token in reply.lower().split() if len(token) > 3}
    overlap = len(inquiry_tokens.intersection(reply_tokens))
    relevance = min(100.0, round((overlap / max(1, len(inquiry_tokens))) * 100, 2))

    required_fields = 4
    fulfilled = 0
    if any(log.get("agent_role") == "classifier" and log.get("status") == "success" for log in agent_logs):
        fulfilled += 1
    if any(log.get("agent_role") == "researcher" and log.get("status") == "success" for log in agent_logs):
        fulfilled += 1
    if any(log.get("agent_role") == "qualifier" and log.get("status") == "success" for log in agent_logs):
        fulfilled += 1
    if reply:
        fulfilled += 1
    completeness = round((fulfilled / required_fields) * 100, 2)

    durations = [float(log.get("duration_ms") or 0) for log in agent_logs]
    total_duration = sum(durations)
    slowest_role = "none"
    slowest_duration = 0.0
    for log in agent_logs:
        duration = float(log.get("duration_ms") or 0)
        if duration >= slowest_duration:
            slowest_role = str(log.get("agent_role") or "none")
            slowest_duration = duration

    bottleneck_explanation = (
        f"{slowest_role} consumed {round(slowest_duration, 2)}ms of {round(total_duration, 2)}ms total"
        if total_duration > 0
        else "No duration data available"
    )

    return {
        "quality": {
            "relevance_score": relevance,
            "completeness_score": completeness,
            "overall_quality_score": round((relevance * 0.55) + (completeness * 0.45), 2),
        },
        "bottleneck": {
            "role": slowest_role,
            "duration_ms": round(slowest_duration, 2),
            "explanation": bottleneck_explanation,
        },
    }


def _extract_logs_from_n8n(detail: dict) -> list[dict]:
    run_data = (((detail.get("data") or {}).get("resultData") or {}).get("runData") or {})
    output: list[dict] = []

    for node_name, entries in run_data.items():
        role = NODE_TO_AGENT.get(node_name)
        if not role:
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            duration_ms = int(entry.get("executionTime") or 0)
            status_value = "failed" if entry.get("error") else "success"
            output.append(
                {
                    "agent_role": role,
                    "input": None,
                    "output": {
                        "node": node_name,
                        "item_count": len(((entry.get("data") or {}).get("main") or [[]])[0] or []),
                    },
                    "duration_ms": max(0, duration_ms),
                    "status": status_value,
                    "error_message": str(entry.get("error")) if entry.get("error") else None,
                }
            )

    return sorted(output, key=lambda row: ROLE_ORDER.get(row.get("agent_role", ""), 99))


async def sync_execution_from_n8n(db, execution: dict) -> dict:
    n8n_execution_id = execution.get("n8n_execution_id")
    if not n8n_execution_id:
        return execution

    detail = await n8n_request("GET", f"/api/v1/executions/{n8n_execution_id}?includeData=true")
    n8n_status = str(detail.get("status") or "running")
    mapped_status = N8N_TO_APP_STATUS.get(n8n_status, "running")
    if mapped_status == "running":
        return execution

    logs = _extract_logs_from_n8n(detail)
    if logs:
        db.table("agent_logs").delete().eq("execution_id", execution["id"]).execute()
        db.table("agent_logs").insert([{**row, "execution_id": execution["id"]} for row in logs]).execute()

    started_at = execution.get("started_at")
    finished_at = datetime.now(UTC)
    duration_ms = None
    if started_at:
        started_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        duration_ms = int((finished_at - started_dt).total_seconds() * 1000)

    detail_payload = execution.get("scorecard_detail") or {}
    quality = _derive_quality_metrics(logs, detail_payload.get("inquiry_text"), execution.get("final_reply"))
    merged_detail = {**detail_payload, **quality, "n8n_status": n8n_status}

    update_data = {
        "status": mapped_status,
        "finished_at": finished_at.isoformat(),
        "duration_ms": duration_ms,
        "scorecard_detail": merged_detail,
    }
    if not execution.get("score") and quality.get("quality"):
        update_data["score"] = max(1, min(10, round((quality["quality"]["overall_quality_score"] or 0) / 10)))

    result = db.table("executions").update(update_data).eq("id", execution["id"]).execute()
    return result.data[0]


def display_status(execution: dict) -> str:
    status_value = execution.get("status") or "running"
    details = execution.get("scorecard_detail") or {}
    if status_value == "running" and details.get("paused"):
        return "paused"
    return status_value


def _maybe_finished_fields(current_status: str, duration_ms: int | None) -> dict:
    if current_status != "running":
        return {}
    fields = {
        "finished_at": datetime.now(UTC).isoformat(),
    }
    if duration_ms is not None:
        fields["duration_ms"] = duration_ms
    return fields


@router.post("/executions/trigger/{workflow_id}", status_code=status.HTTP_201_CREATED)
async def trigger_execution(
    workflow_id: str,
    body: TriggerExecutionRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_supabase_admin_client()
    workflow = get_owned_workflow(db, workflow_id, current_user["id"])

    payload = {
        "workflow_id": workflow_id,
        "user_id": current_user["id"],
        "source_channel": body.source_channel,
        "status": "running",
        "inquiry_snippet": body.inquiry_text[:500],
        "sender_id": body.sender_id,
        "scorecard_detail": {"inquiry_text": body.inquiry_text, "sender_id": body.sender_id, "paused": False},
    }

    try:
        result = db.table("executions").insert(payload).execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    execution = result.data[0]

    try:
        n8n_execution_id = await trigger_n8n_execution(workflow, execution["id"], body)
    except HTTPException as exc:
        failed_detail = {
            **(execution.get("scorecard_detail") or {}),
            "n8n_trigger_error": exc.detail,
        }
        db.table("executions").update(
            {
                "status": "failed",
                "finished_at": datetime.now(UTC).isoformat(),
                "scorecard_detail": failed_detail,
            }
        ).eq("id", execution["id"]).execute()
        raise
    if n8n_execution_id:
        execution = (
            db.table("executions")
            .update({"n8n_execution_id": n8n_execution_id})
            .eq("id", execution["id"])
            .execute()
            .data[0]
        )

    return {
        "execution_id": execution["id"],
        "status": display_status(execution),
        "n8n_execution_id": execution.get("n8n_execution_id"),
        "message": "Execution created and dispatched to n8n.",
    }


@router.get("/executions")
async def list_executions(
    status_filter: ExecutionStatus | None = Query(default=None, alias="status"),
    source_channel: SourceChannel | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    db = get_supabase_admin_client()
    query = db.table("executions").select("*").eq("user_id", current_user["id"]).order("started_at", desc=True).limit(limit)

    if status_filter and status_filter != "paused":
        query = query.eq("status", status_filter)
    if source_channel:
        query = query.eq("source_channel", source_channel)

    try:
        result = query.execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    rows = result.data or []
    if status_filter == "paused":
        rows = [row for row in rows if (row.get("status") == "running" and (row.get("scorecard_detail") or {}).get("paused"))]
    return [{**row, "status": display_status(row)} for row in rows]


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    execution = get_owned_execution(db, execution_id, current_user["id"])
    logs = get_execution_logs(db, execution_id)
    return {**execution, "status": display_status(execution), "agent_logs": logs}


@router.get("/executions/{execution_id}/status")
async def get_execution_status(execution_id: str, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    execution = get_owned_execution(db, execution_id, current_user["id"])
    details = execution.get("scorecard_detail") or {}
    if execution.get("status") == "running" and not details.get("paused") and execution.get("n8n_execution_id"):
        try:
            execution = await sync_execution_from_n8n(db, execution)
        except HTTPException:
            pass
    logs = get_execution_logs(db, execution_id)
    return {
        "id": execution["id"],
        "status": display_status(execution),
        "started_at": execution.get("started_at"),
        "finished_at": execution.get("finished_at"),
        "duration_ms": execution.get("duration_ms"),
        "n8n_execution_id": execution.get("n8n_execution_id"),
        "scorecard_detail": execution.get("scorecard_detail") or {},
        "trace": logs,
    }


@router.get("/executions/{execution_id}/trace")
async def get_execution_trace(execution_id: str, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    get_owned_execution(db, execution_id, current_user["id"])
    return get_execution_logs(db, execution_id)


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    execution = get_owned_execution(db, execution_id, current_user["id"])

    if execution["status"] != "running":
        return {"id": execution_id, "status": display_status(execution), "message": "Execution is already terminal"}

    n8n_execution_id = execution.get("n8n_execution_id")
    if n8n_execution_id:
        try:
            await n8n_request("POST", f"/api/v1/executions/{n8n_execution_id}/stop")
        except HTTPException:
            pass

    update_data = {
        "status": "cancelled",
        "finished_at": datetime.now(UTC).isoformat(),
    }
    try:
        result = db.table("executions").update(update_data).eq("id", execution_id).execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    return {"id": execution_id, "status": display_status(result.data[0])}


@router.post("/executions/{execution_id}/pause")
async def pause_execution(execution_id: str, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    execution = get_owned_execution(db, execution_id, current_user["id"])
    if execution["status"] != "running":
        return {"id": execution_id, "status": display_status(execution), "message": "Execution is not running"}

    detail = execution.get("scorecard_detail") or {}
    if detail.get("paused"):
        return {"id": execution_id, "status": "paused", "message": "Execution is already paused"}

    n8n_execution_id = execution.get("n8n_execution_id")
    if n8n_execution_id:
        try:
            await n8n_request("POST", f"/api/v1/executions/{n8n_execution_id}/stop")
        except HTTPException:
            pass

    next_detail = {**detail, "paused": True, "paused_at": datetime.now(UTC).isoformat()}
    result = db.table("executions").update({"scorecard_detail": next_detail}).eq("id", execution_id).execute()
    return {"id": execution_id, "status": "paused", "message": "Execution paused", "execution": result.data[0]}


@router.post("/executions/{execution_id}/resume", status_code=status.HTTP_201_CREATED)
async def resume_execution(execution_id: str, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    execution = get_owned_execution(db, execution_id, current_user["id"])
    detail = execution.get("scorecard_detail") or {}
    if not detail.get("paused"):
        raise api_error(status.HTTP_400_BAD_REQUEST, "Execution is not paused", "EXECUTION_NOT_PAUSED")

    workflow = get_owned_workflow(db, execution["workflow_id"], current_user["id"])
    payload = {
        "workflow_id": execution["workflow_id"],
        "user_id": current_user["id"],
        "source_channel": execution.get("source_channel") or "test",
        "status": "running",
        "inquiry_snippet": execution.get("inquiry_snippet"),
        "sender_id": execution.get("sender_id"),
        "scorecard_detail": {
            "inquiry_text": detail.get("inquiry_text", execution.get("inquiry_snippet")),
            "sender_id": execution.get("sender_id"),
            "resumed_from": execution_id,
            "paused": False,
        },
    }
    result = db.table("executions").insert(payload).execute()
    new_execution = result.data[0]

    body = TriggerExecutionRequest(
        inquiry_text=payload["scorecard_detail"]["inquiry_text"] or execution.get("inquiry_snippet") or "",
        source_channel=payload["source_channel"],
        sender_id=payload.get("sender_id"),
    )
    try:
        n8n_execution_id = await trigger_n8n_execution(workflow, new_execution["id"], body)
    except HTTPException as exc:
        failed_detail = {
            **(new_execution.get("scorecard_detail") or {}),
            "n8n_trigger_error": exc.detail,
        }
        db.table("executions").update(
            {
                "status": "failed",
                "finished_at": datetime.now(UTC).isoformat(),
                "scorecard_detail": failed_detail,
            }
        ).eq("id", new_execution["id"]).execute()
        raise
    if n8n_execution_id:
        new_execution = (
            db.table("executions")
            .update({"n8n_execution_id": n8n_execution_id})
            .eq("id", new_execution["id"])
            .execute()
            .data[0]
        )

    return {
        "execution_id": new_execution["id"],
        "status": display_status(new_execution),
        "message": "Paused execution resumed by creating a new run.",
    }


@router.post("/executions/{execution_id}/retry", status_code=status.HTTP_201_CREATED)
async def retry_execution(execution_id: str, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    execution = get_owned_execution(db, execution_id, current_user["id"])

    details = execution.get("scorecard_detail") or {}
    payload = {
        "workflow_id": execution["workflow_id"],
        "user_id": current_user["id"],
        "source_channel": execution.get("source_channel") or "test",
        "status": "running",
        "inquiry_snippet": execution.get("inquiry_snippet"),
        "sender_id": execution.get("sender_id"),
        "scorecard_detail": {
            "inquiry_text": details.get("inquiry_text", execution.get("inquiry_snippet")),
            "sender_id": execution.get("sender_id"),
            "retry_of": execution_id,
        },
    }

    workflow = get_owned_workflow(db, execution["workflow_id"], current_user["id"])
    try:
        result = db.table("executions").insert(payload).execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    new_execution = result.data[0]
    body = TriggerExecutionRequest(
        inquiry_text=payload["scorecard_detail"]["inquiry_text"] or execution.get("inquiry_snippet") or "",
        source_channel=payload["source_channel"],
        sender_id=payload.get("sender_id"),
    )
    try:
        n8n_execution_id = await trigger_n8n_execution(workflow, new_execution["id"], body)
    except HTTPException as exc:
        failed_detail = {
            **(new_execution.get("scorecard_detail") or {}),
            "n8n_trigger_error": exc.detail,
        }
        db.table("executions").update(
            {
                "status": "failed",
                "finished_at": datetime.now(UTC).isoformat(),
                "scorecard_detail": failed_detail,
            }
        ).eq("id", new_execution["id"]).execute()
        raise
    if n8n_execution_id:
        new_execution = (
            db.table("executions")
            .update({"n8n_execution_id": n8n_execution_id})
            .eq("id", new_execution["id"])
            .execute()
            .data[0]
        )

    return {
        "execution_id": new_execution["id"],
        "status": display_status(new_execution),
        "n8n_execution_id": new_execution.get("n8n_execution_id"),
        "message": "Retry execution created.",
    }


@router.post("/executions/{execution_id}/agent-logs")
async def append_agent_logs(
    execution_id: str,
    body: AppendAgentLogsRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_supabase_admin_client()
    get_owned_execution(db, execution_id, current_user["id"])

    rows = [{**log.model_dump(), "execution_id": execution_id} for log in body.agent_logs]
    if not rows:
        return {"saved": 0}

    try:
        db.table("agent_logs").insert(rows).execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    return {"saved": len(rows)}


@router.post("/executions/{execution_id}/complete")
async def complete_execution(
    execution_id: str,
    body: CompleteExecutionRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_supabase_admin_client()
    execution = get_owned_execution(db, execution_id, current_user["id"])

    if body.agent_logs:
        rows = [{**log.model_dump(), "execution_id": execution_id} for log in body.agent_logs]
        try:
            db.table("agent_logs").insert(rows).execute()
        except Exception:
            raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    existing_detail = execution.get("scorecard_detail") or {}
    inquiry_text = existing_detail.get("inquiry_text")
    quality = _derive_quality_metrics(body.agent_logs if body.agent_logs else get_execution_logs(db, execution_id), inquiry_text, body.final_reply)
    merged_detail = {**existing_detail, **quality, "paused": False}

    update_data = {
        "status": body.status,
        "final_reply": body.final_reply,
        "score": body.score,
        "n8n_execution_id": body.n8n_execution_id,
        "scorecard_detail": merged_detail,
    }
    update_data.update(_maybe_finished_fields(execution["status"], body.duration_ms))
    if body.duration_ms is not None:
        update_data["duration_ms"] = body.duration_ms

    try:
        result = db.table("executions").update(update_data).eq("id", execution_id).execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    return result.data[0]


@router.get("/executions/{execution_id}/export")
async def export_execution(
    execution_id: str,
    format: ExportFormat = Query(default="json"),
    current_user: dict = Depends(get_current_user),
):
    db = get_supabase_admin_client()
    execution = get_owned_execution(db, execution_id, current_user["id"])
    logs = get_execution_logs(db, execution_id)

    if format == "json":
        return {"execution": execution, "agent_logs": logs}

    if format == "txt":
        content = render_execution_report(execution, logs)
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=execution-{execution_id}.txt"},
        )

    pdf_bytes = render_execution_pdf(execution, logs)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=execution-{execution_id}.pdf"},
    )
