
---

## Remaining Checklist (Current)

Use this as the execution checklist from current repo state.

### Must Close for MVP Credibility

- [ ] **Live n8n dispatch reliability pass**
  - **Pass criteria:** `POST /executions/trigger/{workflow_id}` returns `201` with non-null `n8n_execution_id`, status polling transitions using live n8n data, trace is populated from real node execution data.
  - **Current status:** Still blocked by intermittent `N8N_UNAVAILABLE` in smoke evidence.

- [ ] **Telegram channel parity (trigger `telegram` + `both`)**
  - **Pass criteria:** One successful Telegram-originated run appears in history/analytics and routing is validated for `both`.
  - **Current status:** Telegram webhook relay is live on workflow `tYUVnBenBYrGWAnF`; executions 171, 172, 174, 176, 177, and 178 completed with Telegram `ok: true`. Backend trigger/history parity for `both` still needs separate validation.

- [x] **Replace mock KB with real Google Drive retrieval**
  - **Pass criteria:** Researcher consumes Drive content in main path with fallback behavior and source attribution shows `google_drive`.
  - **Current status:** Resolved. Live workflow maps intents to the exact requested KB names, searches Drive by filename, downloads the selected Google Doc, extracts binary text, and logs debug rows to `Sheet1`. Verified `google_drive` retrieval for `sales_inquiry_kb`, `support_ticket_kb`, `complaint_kb`, `general_question_kb`, `order_request_kb`, and `default_fallback_kb`.

- [ ] **Run 10-case reliability matrix with evidence**
  - **Pass criteria:** >=9/10 green with execution IDs and per-case notes.
  - **Current status:** Telegram/KB evidence added to `docs/test-matrix.md`; full 10-case matrix still needs a complete reliability pass, but the Drive credential visibility blocker is resolved.

### High-Value Validation Still Pending

- [ ] **Pause/Resume live behavior validation**
  - **Pass criteria:** Pause transitions visible `running -> paused`, resume creates linked run (`resumed_from`), UI/history reflect transitions.

- [ ] **Analytics metrics validation on real runs**
  - **Pass criteria:** relevance/completeness scores are populated and agent contribution/bottleneck values are reasonable under live traffic.

### Already Implemented (Do Not Rebuild)

- [x] Integrations management endpoints + operational UI (`/system/integrations` connect/verify/disconnect).
- [x] Pause/Resume controls and backend endpoints (`/executions/{id}/pause`, `/executions/{id}/resume`) with trigger/retry/resume wiring.
- [x] Expanded quality metrics and bottleneck/contribution surfacing in analytics/history.

---
