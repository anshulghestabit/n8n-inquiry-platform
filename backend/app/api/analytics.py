from collections import defaultdict
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.db.client import get_supabase_admin_client
from app.export.csv_export import render_executions_csv
from app.export.pdf import render_execution_pdf
from app.middleware.auth import get_current_user


router = APIRouter(tags=["analytics"])

ExportFormat = Literal["csv", "pdf"]
AGENT_ROLES = ["classifier", "researcher", "qualifier", "responder", "executor"]


def api_error(status_code: int, message: str, code: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": message, "code": code})


def _safe_average(values: list[float]) -> float:
    return (sum(values) / len(values)) if values else 0.0


@router.get("/analytics/summary")
async def analytics_summary(current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    try:
        result = db.table("executions").select("status,duration_ms,score,scorecard_detail").eq("user_id", current_user["id"]).execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    rows = result.data or []
    total = len(rows)
    success_count = sum(1 for row in rows if row.get("status") == "success")
    durations = [float(row["duration_ms"]) for row in rows if row.get("duration_ms") is not None]
    scores = [float(row["score"]) for row in rows if row.get("score") is not None]
    relevance_scores = [
        float((row.get("scorecard_detail") or {}).get("quality", {}).get("relevance_score"))
        for row in rows
        if (row.get("scorecard_detail") or {}).get("quality", {}).get("relevance_score") is not None
    ]
    completeness_scores = [
        float((row.get("scorecard_detail") or {}).get("quality", {}).get("completeness_score"))
        for row in rows
        if (row.get("scorecard_detail") or {}).get("quality", {}).get("completeness_score") is not None
    ]

    return {
        "total_executions": total,
        "success_rate": round((success_count / total) * 100, 2) if total else 0.0,
        "avg_duration_ms": round(_safe_average(durations), 2),
        "avg_score": round(_safe_average(scores), 2),
        "avg_relevance_score": round(_safe_average(relevance_scores), 2),
        "avg_completeness_score": round(_safe_average(completeness_scores), 2),
    }


@router.get("/analytics/chart")
async def analytics_chart(current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    try:
        result = db.table("executions").select("status,started_at").eq("user_id", current_user["id"]).order("started_at").execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    daily: dict[str, dict] = defaultdict(lambda: {"date": "", "count": 0, "success_count": 0})
    for row in result.data or []:
        started_at = row.get("started_at")
        if not started_at:
            continue
        date_key = datetime.fromisoformat(started_at.replace("Z", "+00:00")).date().isoformat()
        daily[date_key]["date"] = date_key
        daily[date_key]["count"] += 1
        if row.get("status") == "success":
            daily[date_key]["success_count"] += 1

    return [daily[key] for key in sorted(daily.keys())]


@router.get("/analytics/agents")
async def analytics_agents(current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    try:
        execution_rows = db.table("executions").select("id,duration_ms,scorecard_detail").eq("user_id", current_user["id"]).execute().data or []
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    execution_ids = [row["id"] for row in execution_rows]
    if not execution_ids:
        return [
            {
                "agent_role": role,
                "avg_duration_ms": 0.0,
                "success_rate": 0.0,
                "contribution_pct": 0.0,
                "bottleneck_flag": False,
                "bottleneck_explanation": "No execution samples yet",
                "sample_size": 0,
            }
            for role in AGENT_ROLES
        ]

    try:
        logs = db.table("agent_logs").select("agent_role,duration_ms,status").in_("execution_id", execution_ids).execute().data or []
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    role_rows: dict[str, list[dict]] = {role: [] for role in AGENT_ROLES}
    total_duration_all_logs = 0.0
    for log in logs:
        role = log.get("agent_role")
        if role in role_rows:
            role_rows[role].append(log)
            total_duration_all_logs += float(log.get("duration_ms") or 0)

    bottleneck_counts = defaultdict(int)
    for row in execution_rows:
        detail = row.get("scorecard_detail") or {}
        bottleneck_role = ((detail.get("bottleneck") or {}).get("role"))
        if bottleneck_role in AGENT_ROLES:
            bottleneck_counts[bottleneck_role] += 1

    output = []
    for role in AGENT_ROLES:
        rows = role_rows[role]
        durations = [float(row.get("duration_ms") or 0) for row in rows]
        avg_duration = _safe_average(durations)
        success_count = sum(1 for row in rows if row.get("status") == "success")
        success_rate = round((success_count / len(rows)) * 100, 2) if rows else 0.0
        bottleneck = bool(rows) and max(durations) > (avg_duration * 2) if avg_duration else False
        role_duration_sum = sum(durations)
        contribution_pct = round((role_duration_sum / total_duration_all_logs) * 100, 2) if total_duration_all_logs else 0.0
        bottleneck_samples = bottleneck_counts.get(role, 0)
        bottleneck_explanation = (
            f"Bottleneck in {bottleneck_samples} runs; avg {round(avg_duration, 2)}ms; contribution {contribution_pct}%"
            if rows
            else "No execution samples yet"
        )

        output.append(
            {
                "agent_role": role,
                "avg_duration_ms": round(avg_duration, 2),
                "success_rate": success_rate,
                "contribution_pct": contribution_pct,
                "bottleneck_flag": bottleneck,
                "bottleneck_explanation": bottleneck_explanation,
                "sample_size": len(rows),
            }
        )

    return output


@router.get("/analytics/export")
async def export_analytics(
    format: ExportFormat = Query(default="csv"),
    current_user: dict = Depends(get_current_user),
):
    db = get_supabase_admin_client()
    try:
        executions = (
            db.table("executions")
            .select("id,workflow_id,source_channel,status,inquiry_snippet,sender_id,started_at,finished_at,duration_ms,score,n8n_execution_id")
            .eq("user_id", current_user["id"])
            .order("started_at", desc=True)
            .execute()
            .data
            or []
        )
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    if format == "csv":
        csv_output = render_executions_csv(executions)
        return Response(
            content=csv_output,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=analytics-executions.csv"},
        )

    synthetic_execution = {
        "id": "analytics-summary",
        "workflow_id": "all-workflows",
        "status": "summary",
        "source_channel": "multi",
        "duration_ms": None,
        "score": None,
        "inquiry_snippet": f"Total rows exported: {len(executions)}",
        "final_reply": "This PDF includes high-level export metadata. Use CSV for full row-level analytics.",
    }
    pdf_bytes = render_execution_pdf(synthetic_execution, [])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=analytics-summary.pdf"},
    )
