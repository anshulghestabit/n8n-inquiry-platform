# What's Left: MVP Gap Backlog

This backlog translates current project gaps into actionable items with priority and effort so you can close MVP fastest.

## Coverage Snapshot

- Estimated feature coverage: **65-75%**
- Estimated true end-to-end demo readiness: **45-55%**

## P0 (Must finish for MVP demo credibility)

### 1) Wire true end-to-end execution trigger into n8n
- **Gap:** Browser "Test Inquiry" creates DB execution records but does not reliably start/track full n8n run from API contract.
- **Current refs:** `backend/app/api/executions.py`, `frontend/src/app/(dashboard)/workflows/[id]/page.tsx`
- **Definition of done:**
  - `POST /executions/trigger/{workflow_id}` starts n8n execution and stores `n8n_execution_id`.
  - Polling endpoint reflects live n8n state and final status without manual callback simulation.
  - Trace is populated from real execution path.
- **Priority:** P0
- **Effort:** **L**

### 2) Complete WhatsApp channel path (parity with Gmail)
- **Gap:** Canonical workflow/template used by app is Gmail-first and not fully WhatsApp-complete for production demo path.
- **Current refs:** `backend/templates/inquiry_workflow.json`, `backend/app/api/workflows.py`
- **Definition of done:**
  - Trigger channel `whatsapp` runs from incoming WhatsApp message to final send + log.
  - Trigger channel `both` works with proper routing and validations.
  - One successful WhatsApp run visible in history + analytics.
- **Priority:** P0
- **Effort:** **L**

### 3) Replace mock KB with real Google Drive retrieval in main flow
- **Gap:** Main template uses mock sales KB block instead of real Drive search/read in execution path.
- **Current refs:** `backend/templates/inquiry_workflow.json` (Mock_Sales_KB step)
- **Definition of done:**
  - Researcher receives real Drive content (with fallback if missing).
  - Source attribution in logs reflects `google_drive` when used.
  - At least 3 test cases show correct retrieval behavior.
- **Priority:** P0
- **Effort:** **M-L**

### 4) Run and document 10-case reliability matrix with evidence
- **Gap:** Matrix exists but needs full live pass evidence tied to current finalized flow.
- **Current refs:** `docs/test-matrix.md`
- **Definition of done:**
  - 10 real inquiries executed, >=9/10 fully green.
  - Per-case execution IDs, outcomes, and notes captured.
  - Failures (if any) include fix notes.
- **Priority:** P0
- **Effort:** **M**

## P1 (Needed to match your written MVP feature list)

### 5) Add Pause execution control (UI + backend behavior)
- **Gap:** Start/Cancel/Retry exist; Pause is missing.
- **Current refs:** `frontend/src/app/(dashboard)/workflows/[id]/page.tsx`, `backend/app/api/executions.py`
- **Definition of done:**
  - Pause control exposed and functional (`running` -> `paused`).
  - Resume behavior defined and tested.
  - Status/trace UI reflects paused state.
- **Priority:** P1
- **Effort:** **M**

### 6) Make Integrations page operational (not placeholder)
- **Gap:** Integrations page is static with disabled actions.
- **Current refs:** `frontend/src/app/(dashboard)/settings/integrations/page.tsx`, `backend/app/api/system.py`
- **Definition of done:**
  - Connect/verify/disconnect actions for Gmail, WhatsApp, Drive, Sheets.
  - Credential/source status persists to `data_sources`.
  - Clear failure messages for invalid or missing credentials.
- **Priority:** P1
- **Effort:** **M-L**

### 7) Tighten scorecard quality metrics
- **Gap:** Overall score and bottleneck metrics exist, but response relevance/completeness scoring is basic.
- **Current refs:** `backend/app/api/analytics.py`, `backend/app/api/executions.py`
- **Definition of done:**
  - Per-run scorecard includes explicit relevance/completeness dimensions.
  - Agent contribution metrics are normalized and visible in UI.
  - Bottleneck explanation is deterministic and understandable.
- **Priority:** P1
- **Effort:** **M**

## P2 (Nice-to-have / polish before submission)

### 8) Improve dashboard from sprint placeholder to live ops summary
- **Gap:** Dashboard content still references sprint/day placeholders.
- **Current refs:** `frontend/src/app/(dashboard)/dashboard/page.tsx`
- **Definition of done:**
  - Live cards for processed count, success rate, avg handling time, latest run.
  - Quick actions to create workflow / run test inquiry.
- **Priority:** P2
- **Effort:** **S-M**

### 9) Add stronger error taxonomy + UX hints
- **Gap:** Many failures collapse into generic `DB_ERROR` / `N8N_UNAVAILABLE` style messages.
- **Definition of done:**
  - User-facing guidance for common failures (missing OAuth, bad channel config, missing template nodes).
  - Structured error codes mapped to remediation steps.
- **Priority:** P2
- **Effort:** **S-M**

---

## Suggested Execution Order

1. P0-1 n8n trigger wiring
2. P0-3 real Drive retrieval
3. P0-2 WhatsApp parity
4. P0-4 reliability matrix evidence
5. P1-6 integrations management
6. P1-5 pause/resume
7. P1-7 scorecard depth
8. P2 polish items

## Practical ETA (single developer)

- **Fast-track MVP-complete (P0 + critical P1):** ~6-10 working days
- **Polished submission including P2:** ~10-14 working days

---

## Current Implementation Steps (Completed This Session)

1. Implemented integrations management backend + UI:
   - Added `GET /system/integrations` and connect/verify/disconnect actions.
   - Made Integrations page operational with status, credential hint input, and action controls.

2. Implemented execution control and runtime wiring updates:
   - Added Pause/Resume controls and backend endpoints (`/executions/{id}/pause`, `/executions/{id}/resume`).
   - Wired `trigger`, `retry`, and `resume` to dispatch real n8n runs.
   - Added n8n execution polling/sync logic in execution status endpoint.

3. Implemented scorecard and analytics depth improvements:
   - Added relevance/completeness/overall quality metrics.
   - Added deterministic bottleneck explanation and contribution percentage per agent.
   - Surfaced these metrics in Analytics and History detail UI.

4. Ran verification and graph update:
   - Backend compile checks passed.
   - Frontend lint passed.
   - Graph updated via `graphify update .`.

## What Is Left To Test (High Priority)

### A) n8n live dispatch + full execution lifecycle (currently blocked)
- **Observed in smoke run:** `POST /executions/trigger/{workflow_id}` returns `503` with `N8N_UNAVAILABLE`.
- **Need to verify once n8n connectivity is fixed:**
  - Trigger returns `201` with non-null `n8n_execution_id`.
  - Status polling transitions from `running` to terminal state using live n8n data.
  - Trace entries are populated from real n8n node execution data.
  - Cancel and Pause invoke n8n stop endpoint correctly.

### B) Pause/Resume behavior validation
- **Need to test with real running execution:**
  - Pause changes visible status to `paused`.
  - Resume creates a new run linked to original execution (`resumed_from`).
  - UI and history reflect state transitions accurately.

### C) Analytics metric correctness under real traffic
- **Need to verify after successful runs exist:**
  - Relevance/completeness non-zero for valid runs.
  - Agent `contribution_pct` sums and trends look reasonable.
  - Bottleneck explanation consistently matches observed slowest role.

### D) WhatsApp + Drive production-path parity tests (still open P0 items)
- **WhatsApp path:** validate trigger channel `whatsapp` and `both` with one successful run in history/analytics.
- **Drive retrieval path:** replace mock KB in canonical flow and verify source attribution as `google_drive`.

## Latest Smoke Test Evidence

- Artifact: `/tmp/smoke_e2e_results_round2.json`
- Result summary:
  - Passed: health, auth, workflow create, history, analytics endpoints.
  - Failed: trigger dispatch to n8n (`N8N_UNAVAILABLE`).
  - Graceful failure persistence confirmed in `executions.scorecard_detail.n8n_trigger_error`.
