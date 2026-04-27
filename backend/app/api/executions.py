from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from app.db.client import get_supabase_admin_client
from app.export.pdf import render_execution_pdf
from app.export.txt import render_execution_report
from app.middleware.auth import get_current_user


router = APIRouter(tags=["executions"])

AgentRole = Literal["classifier", "researcher", "qualifier", "responder", "executor"]
SourceChannel = Literal["gmail", "whatsapp", "test"]
ExecutionStatus = Literal["running", "success", "failed", "cancelled"]
LogStatus = Literal["success", "failed", "skipped"]
ExportFormat = Literal["json", "txt", "pdf"]

ROLE_ORDER = {
    "classifier": 1,
    "researcher": 2,
    "qualifier": 3,
    "responder": 4,
    "executor": 5,
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
    get_owned_workflow(db, workflow_id, current_user["id"])

    payload = {
        "workflow_id": workflow_id,
        "user_id": current_user["id"],
        "source_channel": body.source_channel,
        "status": "running",
        "inquiry_snippet": body.inquiry_text[:500],
        "sender_id": body.sender_id,
        "scorecard_detail": {"inquiry_text": body.inquiry_text, "sender_id": body.sender_id},
    }

    try:
        result = db.table("executions").insert(payload).execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    execution = result.data[0]
    return {
        "execution_id": execution["id"],
        "status": execution["status"],
        "message": "Execution created. n8n can now append logs and complete status.",
    }


@router.get("/executions")
async def list_executions(
    status_filter: ExecutionStatus | None = Query(default=None, alias="status"),
    source_channel: SourceChannel | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    db = get_supabase_admin_client()
    query = (
        db.table("executions")
        .select("*")
        .eq("user_id", current_user["id"])
        .order("started_at", desc=True)
        .limit(limit)
    )

    if status_filter:
        query = query.eq("status", status_filter)
    if source_channel:
        query = query.eq("source_channel", source_channel)

    try:
        result = query.execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    return result.data or []


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    execution = get_owned_execution(db, execution_id, current_user["id"])
    logs = get_execution_logs(db, execution_id)
    return {**execution, "agent_logs": logs}


@router.get("/executions/{execution_id}/status")
async def get_execution_status(execution_id: str, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    execution = get_owned_execution(db, execution_id, current_user["id"])
    logs = get_execution_logs(db, execution_id)
    return {
        "id": execution["id"],
        "status": execution["status"],
        "started_at": execution.get("started_at"),
        "finished_at": execution.get("finished_at"),
        "duration_ms": execution.get("duration_ms"),
        "n8n_execution_id": execution.get("n8n_execution_id"),
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
        return {"id": execution_id, "status": execution["status"], "message": "Execution is already terminal"}

    update_data = {
        "status": "cancelled",
        "finished_at": datetime.now(UTC).isoformat(),
    }
    try:
        result = db.table("executions").update(update_data).eq("id", execution_id).execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    return {"id": execution_id, "status": result.data[0]["status"]}


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

    try:
        result = db.table("executions").insert(payload).execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    new_execution = result.data[0]
    return {
        "execution_id": new_execution["id"],
        "status": new_execution["status"],
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

    update_data = {
        "status": body.status,
        "final_reply": body.final_reply,
        "score": body.score,
        "n8n_execution_id": body.n8n_execution_id,
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
