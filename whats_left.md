
---

## Remaining Checklist (Current)

Use this as the execution checklist from current repo state.

### Must Close for MVP Credibility

- [x] **Live n8n dispatch reliability path hardened**
  - **Pass criteria:** `POST /executions/trigger/{workflow_id}` returns `201` with non-null `n8n_execution_id`, status polling transitions using live n8n data, trace is populated from real node execution data.
  - **Current status:** Backend dispatch already requires a non-null n8n execution id and marks failed dispatches terminal. Status polling now imports live n8n execution data into per-agent trace rows with input, output, validation decision, duration, and error fields instead of saving only node metadata.

- [x] **Telegram channel parity (trigger `telegram` + `both`)**
  - **Pass criteria:** One successful Telegram-originated run appears in history/analytics and routing is validated for `both`.
  - **Current status:** Telegram webhook relay is live on workflow `tYUVnBenBYrGWAnF`; executions 171, 172, 174, 176, 177, and 178 completed with Telegram `ok: true`. The app template supports `telegram` and `both`, and execution history/analytics already filter by `source_channel`.

- [x] **Replace mock KB with real Google Drive retrieval**
  - **Pass criteria:** Researcher consumes Drive content in main path with fallback behavior and source attribution shows `google_drive`.
  - **Current status:** Resolved. Live workflow maps intents to the exact requested KB names, searches Drive by filename, downloads the selected Google Doc, extracts binary text, and logs debug rows to `Sheet1`. Verified `google_drive` retrieval for `sales_inquiry_kb`, `support_ticket_kb`, `complaint_kb`, `general_question_kb`, `order_request_kb`, and `default_fallback_kb`.

- [ ] **Run 10-case reliability matrix with evidence**
  - **Pass criteria:** >=9/10 green with execution IDs and per-case notes.
  - **Current status:** Telegram/KB evidence added to `docs/test-matrix.md`; full 10-case matrix still requires live operator execution IDs. Code now fails closed when Gmail/Telegram/Drive/Sheets credentials are not actually visible to n8n.

### High-Value Validation Still Pending

- [x] **Pause/Resume feature scope decision**
  - **Pass criteria:** Pause transitions visible `running -> paused`, resume creates linked run (`resumed_from`), UI/history reflect transitions.
  - **Current status:** Keep pause/resume/retry as retained post-MVP controls because they are already implemented and useful for reliability demos. They are not required for MVP acceptance and should not block the 10-case reliability matrix.

- [ ] **Analytics metrics validation on real runs**
  - **Pass criteria:** relevance/completeness scores are populated and agent contribution/bottleneck values are reasonable under live traffic.
  - **Current status:** Export endpoints remain as retained post-MVP utilities. They are useful for evidence collection but should not be counted as MVP scope.

### Already Implemented (Do Not Rebuild)

- [x] Integrations management endpoints + operational UI (`/system/integrations` connect/verify/disconnect).
- [x] Pause/Resume controls and backend endpoints (`/executions/{id}/pause`, `/executions/{id}/resume`) with trigger/retry/resume wiring.
- [x] Expanded quality metrics and bottleneck/contribution surfacing in analytics/history.
- [x] Integration connect/verify now validates live n8n credential references before marking a source connected.
- [x] Live n8n trace sync now persists per-agent input, output, validation decision, duration, and errors.

---
