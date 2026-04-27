from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def render_execution_pdf(execution: dict, agent_logs: list[dict]) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    flow = []

    flow.append(Paragraph("n8n Inquiry Platform - Execution Report", styles["Title"]))
    flow.append(Spacer(1, 12))

    summary_data = [
        ["Execution ID", str(execution.get("id", "-"))],
        ["Workflow ID", str(execution.get("workflow_id", "-"))],
        ["Status", str(execution.get("status", "-"))],
        ["Source", str(execution.get("source_channel", "-"))],
        ["Duration (ms)", str(execution.get("duration_ms", "-"))],
        ["Score", str(execution.get("score", "-"))],
    ]

    summary_table = Table(summary_data, colWidths=[150, 370])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e2e8f0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    flow.append(summary_table)
    flow.append(Spacer(1, 14))

    flow.append(Paragraph("Inquiry", styles["Heading2"]))
    flow.append(Paragraph(str(execution.get("inquiry_snippet") or "-"), styles["BodyText"]))
    flow.append(Spacer(1, 10))

    flow.append(Paragraph("Final Reply", styles["Heading2"]))
    flow.append(Paragraph(str(execution.get("final_reply") or "-"), styles["BodyText"]))
    flow.append(Spacer(1, 14))

    flow.append(Paragraph("Agent Trace", styles["Heading2"]))
    if agent_logs:
        trace_data = [["Agent", "Status", "Duration (ms)", "Error"]]
        for log in agent_logs:
            trace_data.append(
                [
                    str(log.get("agent_role", "-")),
                    str(log.get("status", "-")),
                    str(log.get("duration_ms", "-")),
                    str(log.get("error_message") or "-"),
                ]
            )
        trace_table = Table(trace_data, colWidths=[120, 90, 90, 220])
        trace_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        flow.append(trace_table)
    else:
        flow.append(Paragraph("No agent logs recorded.", styles["BodyText"]))

    document.build(flow)
    return buffer.getvalue()
