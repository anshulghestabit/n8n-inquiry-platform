# Day 6 Workflow + Execution Verification (Layer 7/8)

Date: 2026-04-27

Environment:
- Backend: `http://localhost:8000`
- n8n API: `https://n8n.anshul-garg.com/api/v1`

Test user:
- `day5_1777291591@example.com`

## Fix applied before verification

`POST /workflows` was failing with `503 N8N_UNAVAILABLE` because n8n v2.16 rejects read-only workflow fields on create/update payloads.

Applied fix in `backend/app/api/workflows.py`:
- Strip read-only fields from n8n create/update payloads.
- Keep only mutable keys: `name`, `nodes`, `connections`, `settings`.

## Day 6 API verification run

1. Create workflow

```bash
POST /workflows
```

- Result: `201`
- Workflow ID: `d4bcae0b-f321-451d-8617-69e0bde87243`
- n8n Workflow ID: `AiGmmj8c2A1oZuSE`

2. Trigger execution

```bash
POST /executions/trigger/d4bcae0b-f321-451d-8617-69e0bde87243
```

- Result: `201`
- Execution ID: `8e6a956b-0544-4fbc-a1cd-2d7bff0e8ec2`
- Status: `running`

3. Append callback logs (simulating n8n callback)

```bash
POST /executions/8e6a956b-0544-4fbc-a1cd-2d7bff0e8ec2/agent-logs
```

- Result: `200`
- Saved logs: `3`

4. Complete execution with remaining logs

```bash
POST /executions/8e6a956b-0544-4fbc-a1cd-2d7bff0e8ec2/complete
```

- Result: `200`
- Final status: `success`
- `n8n_execution_id`: `n8n-day6-verify-001`

5. Verify trace and status polling

```bash
GET /executions/8e6a956b-0544-4fbc-a1cd-2d7bff0e8ec2/status
GET /executions/8e6a956b-0544-4fbc-a1cd-2d7bff0e8ec2/trace
```

- Both endpoints returned `200`.
- Trace contains all 5 ordered agent roles:
  - `classifier`
  - `researcher`
  - `qualifier`
  - `responder`
  - `executor`

6. Verify retry and stop controls

```bash
POST /executions/8e6a956b-0544-4fbc-a1cd-2d7bff0e8ec2/retry
POST /executions/c569f2b6-28c2-4611-ad7a-9f26e5fee53b/cancel
```

- Retry result: `201`, new execution `c569f2b6-28c2-4611-ad7a-9f26e5fee53b` with `running`.
- Cancel result: `200`, status `cancelled`.
- Second cancel result: `200` with message `Execution is already terminal`.

## Evidence artifacts

- `/tmp/day6_create_workflow_success.json`
- `/tmp/day6_trigger.json`
- `/tmp/day6_agent_logs.json`
- `/tmp/day6_complete.json`
- `/tmp/day6_status.json`
- `/tmp/day6_trace.json`
- `/tmp/day6_retry.json`
- `/tmp/day6_cancel.json`

This run validates backend execution lifecycle endpoints and callback persistence behavior end-to-end with live Supabase state.
