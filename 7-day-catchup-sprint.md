# 7-Day Catch-Up Sprint Plan

Goal: move this repo from partial setup to a demo-ready Layer 10 baseline with reproducible workflows and verifiable checkpoints.

## How this will be used

- This file is the single source of truth for day-by-day execution.
- At the end of each day, mark items complete and paste command results/evidence links.
- I will check against this file in future updates.

## Day 1 - Data Contract + Environment Baseline

Deliverables:
- Create `supabase/schema.sql` with tables, indexes, triggers, and RLS from the plan.
- Add `SUPABASE_JWT_SECRET` to `.env.example`.
- Add missing export dependencies (`reportlab`, `pandas`) to `backend/requirements.txt`.

Verification:
- Run Supabase table check query and confirm 6 tables exist.
- Confirm test signup auto-creates one `profiles` row + four `data_sources` rows.

Evidence to save:
- SQL query output screenshot or copied result.
- Final `supabase/schema.sql` committed.

## Day 2 - Layer 4 Backend Core (JWT + System Status)

Deliverables:
- Implement `backend/app/db/client.py`.
- Implement `backend/app/middleware/auth.py`.
- Implement `backend/app/api/system.py`.
- Register router(s) in `backend/main.py`.

Verification:
- `curl http://localhost:8000/system/status` returns 401 without auth.
- Valid JWT returns 200 with system connection state payload.
- Expired/invalid JWT maps to contract error codes.

Evidence to save:
- Curl outputs for no token, invalid token, valid token.

## Day 3 - Layer 5 Auth Endpoints End-to-End

Deliverables:
- Implement `backend/app/api/auth.py` with register/login/logout/me/update.
- Ensure cookie-based auth flow and consistent error shape.

Verification:
- Run 7 curl cases from the plan (register/login/me/duplicate/wrong password/logout/post-logout).
- Confirm no 500 errors in auth failure paths.

Evidence to save:
- Curl output snippets + `Set-Cookie` proof from login.

## Day 4 - n8n Workflow Hardening (Layer 2/3 Reliability)

Deliverables:
- Ensure 5-agent chain exists with exact node names:
  `Classifier_Agent`, `Researcher_Agent`, `Qualifier_Agent`, `Responder_Agent`, `Executor_Agent`.
- Ensure JSON extraction + key validation after each agent.
- Ensure Gmail send and Google Sheets append are wired.

Verification:
- Execute 10-test matrix and target >= 9/10 fully green.

Evidence to save:
- `docs/test-matrix.md` with per-case pass/fail entries.
- n8n execution IDs or screenshots for failed cases and fixes.

## Day 5 - Layer 6 Frontend Auth + Dashboard Shell

Deliverables:
- Initialize frontend app structure under `frontend/`.
- Implement login/register pages and protected dashboard shell.
- Add API client and auth context.

Verification:
- Unauthenticated user is redirected from dashboard routes.
- Authenticated user can login and land in dashboard shell.

Evidence to save:
- Short screen recording or screenshots of login -> dashboard flow.

## Day 6 - Layer 7/8 Platform Flows (Workflow CRUD + Execution)

Deliverables:
- Backend: workflow CRUD and execution endpoints.
- Frontend: workflows list/detail/edit, agent config, trigger/status/trace controls.
- Add and commit `backend/templates/inquiry_workflow.json` exported from n8n.

Verification:
- Create workflow from UI -> clone template -> trigger execution -> view trace.
- Cancel/retry endpoints behave as expected.

Evidence to save:
- API response snippets and one full execution trace view screenshot.

## Day 7 - Layer 9/10 Analytics + Export + Final Smoke

Deliverables:
- Implement export modules (`pdf.py`, `csv_export.py`, `txt.py`).
- Implement analytics backend routes and frontend analytics page.
- Run final smoke test script/checklist.

Verification:
- History list/detail works.
- CSV/PDF/TXT export works for at least one execution.
- Analytics dashboard shows summary, trend, and agent-level view.

Evidence to save:
- Export sample files and analytics screenshot.
- Final smoke test notes (pass/fail + fixes).

## Daily Checkpoint Table

| Day | Focus | Status | Date Completed | Notes |
|---|---|---|---|---|
| 1 | Layer 1 + env/deps baseline | [x] | 2026-04-24 | Supabase tables, RLS, policies, functions, signup trigger, profile row, and 4 data source rows verified |
| 2 | Layer 4 backend core | [x] | 2026-04-24 | `/system/status` verified: no token -> 401 `INVALID_TOKEN`, invalid JWT -> 401 `INVALID_TOKEN`, expired JWT -> 401 `TOKEN_EXPIRED`, valid signed JWT -> 200 connection state payload. |
| 3 | Layer 5 auth endpoints | [x] | 2026-04-24 | Auth endpoints verified: register -> 201, login -> 200 + `Set-Cookie`, `/auth/me` -> 200 with cookie, profile update -> 200, duplicate register -> 409 `EMAIL_EXISTS`, wrong password -> 401 `INVALID_CREDENTIALS`, logout clears cookie, post-logout `/auth/me` -> 401 `INVALID_TOKEN`. Evidence: `docs/day-3-auth-verification.md`. |
| 4 | n8n reliability + test matrix | [ ] |  | Started 2026-04-24. Created n8n workflow `EFHQhYMNpoZWI4Cg` and saved template at `backend/templates/inquiry_workflow.json`; required 5 agent nodes, validation gates, Gmail send, and Sheets append are present. Live 10-case matrix is blocked until `GOOGLE_SHEET_ID` and a Google Sheets credential are configured. Evidence: `docs/test-matrix.md`. |
| 5 | Layer 6 frontend shell | [ ] |  |  |
| 6 | Layer 7/8 workflow + execution | [ ] |  |  |
| 7 | Layer 9/10 analytics + exports | [ ] |  |  |

## Exit Criteria (Sprint Complete)

- All daily rows marked complete with evidence.
- n8n workflow template versioned at `backend/templates/inquiry_workflow.json`.
- Supabase schema versioned at `supabase/schema.sql`.
- End-to-end path works: signup -> create workflow -> trigger -> 5-agent run -> reply/log -> history -> analytics -> export.
