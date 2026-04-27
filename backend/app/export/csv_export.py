from io import StringIO

import pandas as pd


def render_executions_csv(executions: list[dict]) -> str:
    if not executions:
        columns = [
            "id",
            "workflow_id",
            "source_channel",
            "status",
            "started_at",
            "finished_at",
            "duration_ms",
            "score",
        ]
        frame = pd.DataFrame(columns=columns)
    else:
        frame = pd.DataFrame(executions)
        desired = [
            "id",
            "workflow_id",
            "source_channel",
            "status",
            "inquiry_snippet",
            "sender_id",
            "started_at",
            "finished_at",
            "duration_ms",
            "score",
            "n8n_execution_id",
        ]
        columns = [column for column in desired if column in frame.columns]
        frame = frame[columns]

    stream = StringIO()
    frame.to_csv(stream, index=False)
    return stream.getvalue()
