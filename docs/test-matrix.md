# Day 4 n8n Reliability Test Matrix

Goal: verify the Gmail-triggered 5-agent chain completes reliably with valid JSON at each agent, sends a Gmail reply, and appends a Google Sheets row. Target: at least 9/10 fully green.

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

Current status: workflow hardening is started and structurally complete, but the 10-email live matrix cannot be marked green until the Google Sheet ID and Sheets credential are configured.

To unblock live testing:

1. Create the `Inquiry Execution Log` Google Sheet with the required columns.
2. Set `GOOGLE_SHEET_ID=<sheet id>` and `GOOGLE_SHEET_NAME=<tab name>` in `.env`.
3. Add/attach a Google Sheets OAuth credential to `Google_Sheets_Append_Row` in n8n.
4. Activate workflow `EFHQhYMNpoZWI4Cg` and send the 10 test emails below.

## 10-Case Live Matrix

| # | Type | Test inquiry | Classifier | Researcher | Qualifier | Responder | Executor | Gmail reply | Sheets row | Pass? | n8n execution ID / notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sales_inquiry | Need enterprise pricing for 50 users. | Not run | Not run | Not run | Not run | Not run | Not run | Blocked | No | Pending Sheets setup |
| 2 | sales_inquiry | Can we book a demo for our procurement team? | Not run | Not run | Not run | Not run | Not run | Not run | Blocked | No | Pending Sheets setup |
| 3 | sales_inquiry | Please send pricing and onboarding details for our company. | Not run | Not run | Not run | Not run | Not run | Not run | Blocked | No | Pending Sheets setup |
| 4 | support_ticket | My login is not working and password reset failed. | Not run | Not run | Not run | Not run | Not run | Not run | Blocked | No | Pending Sheets setup |
| 5 | support_ticket | I cannot access my dashboard after payment. | Not run | Not run | Not run | Not run | Not run | Not run | Blocked | No | Pending Sheets setup |
| 6 | complaint | Your service was terrible last week and nobody replied. | Not run | Not run | Not run | Not run | Not run | Not run | Blocked | No | Pending Sheets setup |
| 7 | complaint | I am unhappy with the delayed response to my issue. | Not run | Not run | Not run | Not run | Not run | Not run | Blocked | No | Pending Sheets setup |
| 8 | general_question | What are your office hours and support channels? | Not run | Not run | Not run | Not run | Not run | Not run | Blocked | No | Pending Sheets setup |
| 9 | general_question | Do you support integrations with Google Workspace? | Not run | Not run | Not run | Not run | Not run | Not run | Blocked | No | Pending Sheets setup |
| 10 | order_request | I would like to order 100 units of product X. | Not run | Not run | Not run | Not run | Not run | Not run | Blocked | No | Pending Sheets setup |

Pass criteria per row: all five agents return valid JSON with required keys, Gmail reply arrives, and Google Sheets row is appended.
