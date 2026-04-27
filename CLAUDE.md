# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An n8n-based multi-agent customer inquiry automation platform. Incoming Gmail/WhatsApp messages are processed through a 5-agent AI pipeline (Classifier → Researcher → Qualifier → Responder → Executor) orchestrated by n8n, managed via a FastAPI backend and Next.js frontend.

## Services & Ports

| Service | Port | Notes |
|---|---|---|
| n8n | 5678 | Workflow engine (Docker) |
| FastAPI | 8000 | Python backend (Docker or local) |
| Next.js | 3000 | Frontend (run locally) |
| Supabase | — | External (cloud) |

## Commands

### Start all backend services (n8n + FastAPI)
```bash
docker compose up --build
docker compose restart backend   # after changing .env
```

### Run FastAPI locally (outside Docker)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Run frontend
```bash
cd frontend
npm install
npm run dev
```

### Backend API docs (development only)
```
http://localhost:8000/docs
```

## Architecture

```
Next.js (UI :3000)  ←→  FastAPI (:8000)  ←→  n8n (:5678, Docker)
                              ↕
                      Supabase (Postgres + Auth + RLS)
                              ↕
                  Sarvam AI (cloud) / LM Studio (local fallback)
```

### LLM switching
`LLM_PROVIDER` env var controls which LLM is used — `sarvam` (default) or `lmstudio`. Both implement the OpenAI-compatible API, so `backend/app/core/llm.py` uses the OpenAI SDK for both. No code changes needed to switch providers.

### n8n workflow creation
FastAPI never builds n8n workflow JSON programmatically. Instead, `backend/templates/inquiry_workflow.json` is a manually-exported n8n workflow; FastAPI clones it and patches only the `name`, `id`, and active trigger node. This avoids silent failures from mismatched node UUIDs.

### JWT authentication
Supabase issues JWTs on login. FastAPI decodes them using `SUPABASE_JWT_SECRET` (not the anon key). Tokens are stored in httpOnly cookies, not localStorage. The middleware at `backend/middleware/auth.py` handles verification for all protected routes.

### Agent JSON validation (inside n8n)
Each agent in the n8n workflow has a Code node after the HTTP Request node that tries to extract JSON via 4 methods in cascade: direct parse → strip markdown fences → find first `{...}` → greedy `{...}` match. An IF node routes to retry (max once) only if all 4 methods fail.

### Execution polling
After triggering a workflow via `POST /executions/trigger/{workflow_id}`, the frontend polls `GET /executions/{id}/status` every 2 seconds. FastAPI fetches execution state from n8n's API and maps n8n node names back to agent roles before writing to `agent_logs`.

## Database Schema (Supabase)

Key tables: `profiles`, `workflows`, `agents`, `executions`, `agent_logs`, `data_sources`.  
RLS is enabled on all tables. An auto-trigger creates a `profiles` row + 4 `data_sources` rows on `auth.users` insert.  
Schema lives in `supabase/schema.sql` — apply via Supabase SQL Editor.

## Environment Variables

Copy `.env.example` → `.env`. Critical vars:
- `N8N_API_KEY` — obtained after first n8n login (Settings → API → Enable)
- `SUPABASE_JWT_SECRET` — from Supabase project settings (not in `.env.example`, must be added manually)
- `N8N_RUNNERS_AUTH_TOKEN` — required by docker-compose for the `task-runners` service

## Google OAuth (GCP)

One OAuth2 credential in n8n covers Gmail, Google Sheets, and Google Drive. Redirect URI must be `http://localhost:5678/rest/oauth2-credential/callback`. See `Sample-Readme.md` § GCP OAuth Setup for the full step-by-step.

## Google Drive Knowledge Base

The Researcher agent fetches `{inquiry_type}.txt` from a `/KnowledgeBase/` folder in the connected Google Drive. Valid inquiry types: `sales_inquiry`, `support_ticket`, `complaint`, `general_question`, `order_request`.

## graphify Knowledge Graph

This project has a graphify knowledge graph at `graphify-out/`.
- Before answering architecture or codebase questions, read `graphify-out/GRAPH_REPORT.md` for god nodes and community structure.
- If `graphify-out/wiki/index.md` exists, navigate it instead of reading raw files.
- After modifying code files, run `graphify update .` to keep the graph current.