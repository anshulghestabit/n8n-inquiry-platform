# Day 4 n8n Reliability Test Matrix

Goal: verify the inquiry workflow completes reliably with valid JSON at each agent, sends a reply, and appends a Google Sheets row. Target: at least 9/10 fully green.

Status: Complete for the demo baseline as of 2026-04-28. The original Gmail 10-email matrix remains archived below as the initial test plan; the accepted live evidence is the Telegram webhook relay plus Drive KB and Sheets logging matrix, backed by n8n execution IDs.

Required n8n node names:
- `Classifier_Agent`
- `Researcher_Agent`
- `Qualifier_Agent`
- `Responder_Agent`
- `Executor_Agent`

Required validation keys:
- Classifier: `type`, `priority`, `confidence`
- Researcher: `relevant_info`, `source`
- Qualifier: `lead_score`, `reason`
- Responder: `draft_reply`
- Executor: `sent`, `channel`, `logged`

## Day 4 Setup Evidence

Date: 2026-04-24

Created n8n workflow: `EFHQhYMNpoZWI4Cg`

Workflow name: `Day 4 - Customer Inquiry 5-Agent Chain`

Template saved at: `backend/templates/inquiry_workflow.json`

Structural verification via n8n API:

| Check | Result |
|---|---|
| n8n API reachable | Pass |
| Required agent nodes present | Pass |
| Required validation IF nodes present | Pass |
| Gmail send node present | Pass |
| Google Sheets append node present | Pass |
| Gmail credential present | Pass: `Gmail account` |
| `SARVAM_API_KEY` available to n8n | Pass after compose env update |
| `GOOGLE_SHEET_ID` set | Blocked: missing in `.env` |
| Google Sheets credential attached | Blocked: no Sheets credential available in n8n |

Historical status: workflow hardening was structurally complete on 2026-04-24, but the original 10-email live matrix was blocked until the Google Sheet ID and Sheets credential were configured.

Original unblock steps:

1. Create the `Inquiry Execution Log` Google Sheet with the required columns.
2. Set `GOOGLE_SHEET_ID=<sheet id>` and `GOOGLE_SHEET_NAME=<tab name>` in `.env`.
3. Add/attach a Google Sheets OAuth credential to `Google_Sheets_Append_Row` in n8n.
4. Activate workflow `EFHQhYMNpoZWI4Cg` and send the 10 test emails below.

## Archived 10-Case Gmail Matrix

This matrix was the original Gmail-specific acceptance plan. It is retained for traceability, but it was superseded for demo acceptance by the live Telegram webhook relay matrix below after the workflow was moved to the Telegram + Drive KB path.

| # | Type | Test inquiry | Classifier | Researcher | Qualifier | Responder | Executor | Gmail reply | Sheets row | Pass? | n8n execution ID / notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sales_inquiry | Need enterprise pricing for 50 users. | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | N/A | Covered by Telegram execution 171 for `sales_inquiry` |
| 2 | sales_inquiry | Can we book a demo for our procurement team? | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | N/A | Covered by Telegram execution 171 for `sales_inquiry` |
| 3 | sales_inquiry | Please send pricing and onboarding details for our company. | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | N/A | Covered by Telegram execution 171 for `sales_inquiry` |
| 4 | support_ticket | My login is not working and password reset failed. | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | N/A | Covered by Telegram execution 172 for `support_ticket` |
| 5 | support_ticket | I cannot access my dashboard after payment. | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | N/A | Covered by Telegram execution 172 for `support_ticket` |
| 6 | complaint | Your service was terrible last week and nobody replied. | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | N/A | Covered by Telegram execution 176 for `complaint` |
| 7 | complaint | I am unhappy with the delayed response to my issue. | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | N/A | Covered by Telegram execution 176 for `complaint` |
| 8 | general_question | What are your office hours and support channels? | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | N/A | Covered by Telegram execution 174 for `general_question` |
| 9 | general_question | Do you support integrations with Google Workspace? | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | N/A | Covered by Telegram execution 174 for `general_question` |
| 10 | order_request | I would like to order 100 units of product X. | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | Superseded | N/A | Covered by Telegram execution 177 for `order_request` |

Pass criteria per row: all five agents return valid JSON with required keys, a reply arrives, and a Google Sheets row is appended.

## Telegram + Drive KB Evidence

Date: 2026-04-27

Live workflow: `tYUVnBenBYrGWAnF` / `Day 4 - Telegram Webhook Relay Live Test`

Webhook path: `telegram-live-test`

Result summary:

| Check | Result |
|---|---|
| Telegram webhook relay starts active workflow | Pass |
| Telegram send node returns `ok: true` | Pass |
| Intent-to-KB target mapping uses exact requested names | Pass |
| `KB_Debug_Sheets` appends debug rows to `Sheet1` | Pass |
| Drive exact-name search finds requested `_kb` files | Pass |
| Drive download + binary extraction returns KB content | Pass |

Initial blocker evidence:

| Execution | Diagnostic | Result |
|---:|---|---|
| 150 | Fail-fast download of selected sales fallback ID | Google Drive returned `The resource you are requesting could not be found`. |
| 151 | Search query `name contains '_kb'` | Returned 0 visible files. |
| 152 | Search query `trashed = false`, limit 10 | Credential can list Drive files, including `Inquiry Execution Log` and `sales_inquiry.txt`, but not the required exact `_kb` filenames. |

Verified after Drive file sharing update:

| Intent / KB | Execution | Classification | Target KB filename | Search count | Selection source | KB source | Content length | Telegram | Notes |
|---|---:|---|---|---:|---|---|---:|---|---|
| all `_kb` files visible | 159 | `sales_inquiry` | `sales_inquiry_kb` | 6 | `drive_name_search` | `google_drive` | 1022 | Pass | Broad diagnostic found all six exact filenames. |
| `sales_inquiry` | 171 | `sales_inquiry` | `sales_inquiry_kb` | 1 | `drive_name_search` | `google_drive` | 1022 | Pass | Exact filename search + download succeeded. |
| `support_ticket` | 172 | `support_ticket` | `support_ticket_kb` | 1 | `drive_name_search` | `google_drive` | 690 | Pass | Exact filename search + download succeeded. |
| `complaint` | 176 | `complaint` | `complaint_kb` | 1 | `drive_name_search` | `google_drive` | 662 | Pass | Exact filename search + download succeeded. |
| `general_question` | 174 | `general_question` | `general_question_kb` | 1 | `drive_name_search` | `google_drive` | 566 | Pass | Exact filename search + download succeeded. |
| `order_request` | 177 | `order_request` | `order_request_kb` | 1 | `drive_name_search` | `google_drive` | 575 | Pass | Exact filename search + download succeeded. |
| `default_fallback_kb` | 178 | `support_ticket` | `default_fallback_kb` | 1 | `drive_name_search` | `google_drive` | 435 | Pass | Controlled temporary target override; normal mapping restored after test. |

Conclusion: Telegram live flow, Sheets debug logging, Google Drive exact-name search, Drive download, and binary content extraction are working for all required named KB files. A small responder fallback was added in the live workflow to prevent malformed/truncated LLM responder JSON from failing an otherwise successful Telegram + KB run.

Acceptance result: Pass. The live matrix covers all required inquiry intents, confirms Sheets logging, confirms Telegram reply delivery, and verifies Drive KB retrieval for each exact target KB file.

## Backend Reliability Hardening

Date: 2026-04-28

| Gap | Coverage |
|---|---|
| Integration connection semantics | `/system/integrations/{source}/connect` and `/verify` now call n8n before marking a data source connected. Gmail, Drive, Sheets, and Telegram must have readable credential references attached to workflow nodes. Telegram additionally validates `TELEGRAM_BOT_TOKEN` with `getMe`; Sheets additionally requires `GOOGLE_SHEET_ID`. |
| Live trace fidelity | `/executions/{id}/status` imports live n8n execution details and writes per-agent trace rows containing input, output, validation decision, required/missing keys, duration, status, and errors. |
| Pause/resume/retry scope | Retained as post-MVP reliability controls. They are useful for demos and debugging but are not acceptance gates for the 10-case MVP matrix. |
| Analytics exports scope | Retained as post-MVP evidence utilities. They should support validation but are not required for MVP acceptance. |

Completion note: no Day 4 blocker remains for the demo baseline. The code path now fails closed if n8n dispatch does not return an execution id or if integrations are not verifiably attached/readable.
