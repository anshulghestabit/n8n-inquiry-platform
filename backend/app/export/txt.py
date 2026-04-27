from datetime import datetime


ROLE_LABELS = {
    "classifier": "Classifier",
    "researcher": "Researcher",
    "qualifier": "Qualifier",
    "responder": "Responder",
    "executor": "Executor",
}


def _format_time(value: str | None) -> str:
    if not value:
        return "-"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value


def render_execution_report(execution: dict, agent_logs: list[dict]) -> str:
    lines = [
        "n8n Inquiry Platform - Execution Report",
        "=" * 44,
        f"Execution ID: {execution.get('id', '-')}",
        f"Workflow ID: {execution.get('workflow_id', '-')}",
        f"Status: {execution.get('status', '-')}",
        f"Source channel: {execution.get('source_channel', '-')}",
        f"Sender: {execution.get('sender_id') or '-'}",
        f"Started at: {_format_time(execution.get('started_at'))}",
        f"Finished at: {_format_time(execution.get('finished_at'))}",
        f"Duration (ms): {execution.get('duration_ms') if execution.get('duration_ms') is not None else '-'}",
        f"Score: {execution.get('score') if execution.get('score') is not None else '-'}",
        "",
        "Inquiry",
        "-" * 44,
        execution.get("inquiry_snippet") or "-",
        "",
        "Final Reply",
        "-" * 44,
        execution.get("final_reply") or "-",
        "",
        "Agent Trace",
        "-" * 44,
    ]

    if not agent_logs:
        lines.append("No agent logs recorded.")
    else:
        for index, log in enumerate(agent_logs, start=1):
            role = ROLE_LABELS.get(log.get("agent_role"), log.get("agent_role", "agent"))
            lines.extend(
                [
                    f"{index}. {role}",
                    f"   Status: {log.get('status', '-')}",
                    f"   Duration (ms): {log.get('duration_ms') if log.get('duration_ms') is not None else '-'}",
                    f"   Input: {log.get('input')}",
                    f"   Output: {log.get('output')}",
                    f"   Error: {log.get('error_message') or '-'}",
                ]
            )

    return "\n".join(lines) + "\n"
