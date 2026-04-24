# n8n Multi-Agent Customer Inquiry Automation Platform
## Complete Step-by-Step Implementation Guide

> **North Star:** User signs up → builds "Customer Inquiry Handler" → sends test email → watches 5 agents collaborate → receives automated reply → sees detailed scorecard. Reliable 9/10 times. Under 30 seconds.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites Checklist](#prerequisites-checklist)
- [Project Folder Structure](#project-folder-structure)
- [Layer 0 — Docker + n8n + FastAPI + Sarvam](#layer-0--docker--n8n--fastapi--sarvam)
- [Layer 1 — Supabase Schema + RLS](#layer-1--supabase-schema--rls)
- [Layer 2 — GCP OAuth + Gmail Trigger + Classifier Agent](#layer-2--gcp-oauth--gmail-trigger--classifier-agent)
- [Layer 3 — Full 5-Agent Chain + Sheets Logging + Test Matrix](#layer-3--full-5-agent-chain--sheets-logging--test-matrix)
- [Layer 3.5 — Google Drive KB + WhatsApp Integration](#layer-35--google-drive-kb--whatsapp-integration)
- [Layer 4 — FastAPI DB Connection + JWT Middleware + System Status](#layer-4--fastapi-db-connection--jwt-middleware--system-status)
- [Layer 5 — Auth Endpoints](#layer-5--auth-endpoints)
- [Layer 6 — Next.js Auth Pages + Dashboard Shell](#layer-6--nextjs-auth-pages--dashboard-shell)
- [Layer 6.5 — Data Sources Management Page](#layer-65--data-sources-management-page)
- [Layer 7 — Workflow CRUD + Embedded n8n Editor + Agent Config UI](#layer-7--workflow-crud--embedded-n8n-editor--agent-config-ui)
- [Layer 8 — Execution Trigger + Controls + Status Bar + Trace View](#layer-8--execution-trigger--controls--status-bar--trace-view)
- [Layer 9 — History + Logs + Export](#layer-9--history--logs--export)
- [Layer 10 — Analytics Dashboard + Full Scorecard](#layer-10--analytics-dashboard--full-scorecard)
- [Layer 11 — Polish + Smoke Tests + Deploy Prep](#layer-11--polish--smoke-tests--deploy-prep)
- [30-Day Timeline](#30-day-timeline)
- [Cut Lines (What to Drop if Behind)](#cut-lines)
- [Risk Register](#risk-register)

---

## Architecture Overview

```
Next.js (UI :3000)  ←→  FastAPI (Python :8000)  ←→  n8n (Docker :5678)
                                ↕
                         Supabase (DB + Auth)
                                ↕
                  Sarvam AI / LM Studio + Google APIs
```

**Four services, one `docker-compose.yml`:**

| Service | Port | Role |
|---------|------|------|
| Next.js frontend | 3000 | User interface — auth, workflows, execution monitor, analytics |
| FastAPI backend | 8000 | JWT auth, DB operations, n8n orchestration, export (PDF/CSV) |
| n8n workflow engine | 5678 | 5-agent pipeline, Gmail/Drive/Sheets/WhatsApp nodes |
| Supabase (cloud) | — | PostgreSQL database, authentication, Row Level Security |

**Why this architecture (for evaluators):**
- **FastAPI stays** because it handles JWT auth, Supabase DB ops, n8n API orchestration, execution log processing, analytics aggregation, and file export via reportlab/pandas — all Python-native operations.
- **n8n stays in Docker** because it's the core of the project brief (non-negotiable) and provides native Gmail/Drive/Sheets/WhatsApp nodes with built-in OAuth2.
- **Sarvam + LM Studio** because Sarvam provides cloud speed (OpenAI-compatible), while LM Studio serves as a local fallback if Sarvam is down on demo day. One env var switches between them.

---

## Prerequisites Checklist

Before writing any code, make sure every one of these is set up:

### Accounts to Create

- [ ] **Docker Desktop** installed and running ([docker.com](https://docker.com))
- [ ] **Node.js 18+** installed (`node --version` to verify)
- [ ] **Python 3.11+** installed (`python3 --version` to verify)
- [ ] **Supabase** free account at [supabase.com](https://supabase.com) — create a new project, note down:
  - Project URL (`https://xxxx.supabase.co`)
  - Anon key (`eyJ...`)
  - Service role key (`eyJ...`)
  - JWT secret (Settings → API → JWT Settings)
- [ ] **Sarvam AI** free account at [dashboard.sarvam.ai](https://dashboard.sarvam.ai) — copy your API key
- [ ] **Google Cloud** project at [console.cloud.google.com](https://console.cloud.google.com) (setup in Layer 2)
- [ ] **Git** initialized (`git init` in your project root)

### Optional (for WhatsApp)

- [ ] **Meta Developer** account at [developers.facebook.com](https://developers.facebook.com)
- [ ] **ngrok** account at [ngrok.com](https://ngrok.com) — free tier is fine

---

## Project Folder Structure

Create this exact structure before starting. Every file mentioned in the plan lives in one of these directories.

```
n8n-inquiry-platform/
├── docker-compose.yml
├── .env
├── .env.example
├── .gitignore
├── README.md
├── FUTURE.md
├── smoke_test.sh
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py          # Settings from env vars
│   │   │   └── llm.py             # Sarvam/LM Studio client
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── client.py          # Supabase anon + admin clients
│   │   │   └── models.py          # Pydantic models
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   └── auth.py            # JWT decode + get_current_user
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py            # register, login, logout, me
│   │   │   ├── workflows.py       # CRUD + agent config
│   │   │   ├── executions.py      # trigger, status, trace, cancel, retry
│   │   │   ├── analytics.py       # summary, chart, agents, scorecard
│   │   │   ├── system.py          # /system/status
│   │   │   └── integrations.py    # data sources management
│   │   ├── export/
│   │   │   ├── __init__.py
│   │   │   ├── pdf.py             # reportlab PDF export
│   │   │   ├── csv_export.py      # pandas CSV export
│   │   │   └── txt.py             # text export
│   │   └── templates/
│   │       └── inquiry_workflow.json  # n8n workflow template (from Layer 3)
│   └── tests/
│
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── src/
│   │   ├── middleware.ts           # Route protection
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            # Redirect → /dashboard or /login
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── register/page.tsx
│   │   │   └── (dashboard)/
│   │   │       ├── layout.tsx      # Sidebar + StatusBar shell
│   │   │       ├── dashboard/page.tsx
│   │   │       ├── workflows/
│   │   │       │   ├── page.tsx               # List workflows
│   │   │       │   └── [id]/
│   │   │       │       ├── page.tsx           # Workflow detail
│   │   │       │       ├── agents/page.tsx    # Agent config
│   │   │       │       └── edit/page.tsx      # Embedded n8n editor
│   │   │       ├── history/
│   │   │       │   ├── page.tsx               # Execution list
│   │   │       │   └── [id]/page.tsx          # Execution detail
│   │   │       ├── analytics/page.tsx
│   │   │       ├── settings/
│   │   │       │   └── integrations/page.tsx
│   │   │       └── profile/page.tsx
│   │   ├── components/
│   │   │   ├── StatusBar.tsx
│   │   │   ├── TraceView.tsx
│   │   │   ├── AgentCard.tsx
│   │   │   ├── Scorecard.tsx
│   │   │   └── Sidebar.tsx
│   │   └── lib/
│   │       ├── api.ts              # Axios/fetch wrapper to FastAPI
│   │       └── auth-context.tsx    # React context for auth state
│   └── public/
│
├── n8n/
│   └── .n8n/                       # Docker volume for n8n data
│
└── supabase/
    └── schema.sql                  # All SQL from Layer 1
```

### Step: Create `.gitignore`

```
node_modules/
.env
__pycache__/
*.pyc
.n8n/
.next/
cookies.txt
```

---

## Layer 0 — Docker + n8n + FastAPI + Sarvam

> **Status:** This should already be DONE before starting the guide. If not, do it now.
> **Goal:** `docker compose up` starts both n8n and FastAPI. Sarvam AI responds to a test prompt.
> **Time estimate:** 2–3 hours

### Step 0.1: Create `.env.example`

Create this file in your project root. It documents every env var the project needs.

```env
# === LLM Configuration ===
LLM_PROVIDER=sarvam                          # "sarvam" or "lmstudio"
SARVAM_API_KEY=your_sarvam_api_key_here
SARVAM_BASE_URL=https://api.sarvam.ai/v1
SARVAM_MODEL=sarvam-m4
LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1
LM_STUDIO_MODEL=local-model

# === n8n ===
N8N_ENCRYPTION_KEY=generate_a_random_32_char_string
N8N_URL=http://n8n:5678
N8N_API_KEY=fill_after_first_n8n_login

# === Supabase ===
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase-settings

# === App ===
SECRET_KEY=generate_another_random_string
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000
```

### Step 0.2: Copy `.env.example` to `.env` and fill in real values

```bash
cp .env.example .env
# Now edit .env with your actual keys
```

### Step 0.3: Create `docker-compose.yml`

```yaml
services:
  n8n:
    image: docker.n8nio/n8n:1.48.0
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - N8N_API_DISABLED=false
      - N8N_AUTH_EXCLUDE_ENDPOINTS=rest/.*
      - WEBHOOK_URL=http://localhost:5678
      - GENERIC_TIMEZONE=Asia/Kolkata
    volumes:
      - ./n8n/.n8n:/home/node/.n8n
    networks:
      - app-network

  backend:
    build: ./backend
    container_name: fastapi
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - LLM_PROVIDER=${LLM_PROVIDER}
      - SARVAM_API_KEY=${SARVAM_API_KEY}
      - SARVAM_BASE_URL=${SARVAM_BASE_URL}
      - SARVAM_MODEL=${SARVAM_MODEL}
      - LM_STUDIO_BASE_URL=${LM_STUDIO_BASE_URL}
      - LM_STUDIO_MODEL=${LM_STUDIO_MODEL}
      - N8N_URL=${N8N_URL}
      - N8N_API_KEY=${N8N_API_KEY}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
      - SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=${ENVIRONMENT}
      - FRONTEND_URL=${FRONTEND_URL}
    volumes:
      - ./backend:/app
    depends_on:
      - n8n
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

**Key config notes:**
- `N8N_AUTH_EXCLUDE_ENDPOINTS=rest/.*` — this prevents the n8n login screen from appearing when you embed n8n in an iframe later (Layer 7). Set it now so you never have to debug it later.
- `n8n:1.48.0` — pinned version. Never use `latest` for a demo project.
- The backend `volumes: - ./backend:/app` means code changes reflect without rebuilding.

### Step 0.4: Create `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### Step 0.5: Create `backend/requirements.txt`

```txt
fastapi==0.115.6
uvicorn[standard]==0.30.6
python-dotenv==1.0.1
pydantic==2.10.6
pydantic-settings==2.6.1
supabase==2.7.4
httpx==0.28.1
openai==1.51.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.20
starlette==0.41.3
reportlab==4.2.2
pandas==2.2.2
```

### Step 0.6: Create `backend/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="n8n Inquiry Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Step 0.7: Create `backend/app/core/config.py`

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # LLM
    llm_provider: str = "sarvam"
    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai/v1"
    sarvam_model: str = "sarvam-m4"
    lm_studio_base_url: str = "http://host.docker.internal:1234/v1"
    lm_studio_model: str = "local-model"

    # n8n
    n8n_url: str = "http://n8n:5678"
    n8n_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # App
    secret_key: str = ""
    environment: str = "development"
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
```

### Step 0.8: Create `backend/app/core/llm.py`

```python
from openai import OpenAI
from app.core.config import get_settings

settings = get_settings()

def get_llm_client() -> OpenAI:
    """Returns OpenAI-compatible client pointing to Sarvam or LM Studio."""
    if settings.llm_provider == "sarvam":
        return OpenAI(
            api_key=settings.sarvam_api_key,
            base_url=settings.sarvam_base_url
        )
    else:
        return OpenAI(
            api_key="not-needed",
            base_url=settings.lm_studio_base_url
        )

def get_model_name() -> str:
    if settings.llm_provider == "sarvam":
        return settings.sarvam_model
    return settings.lm_studio_model
```

### Step 0.9: Start everything and verify

```bash
# Create n8n data directory
mkdir -p n8n/.n8n

# Start services
docker compose up --build

# In a new terminal, verify:
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# Open browser:
# http://localhost:5678 → n8n setup wizard appears
```

### Step 0.10: Set up n8n API key

1. Open `http://localhost:5678`
2. Create an owner account (remember these credentials)
3. Go to **Settings → API → Enable API**
4. Copy the generated API key
5. Paste it into your `.env` file as `N8N_API_KEY=your_key_here`
6. Restart the backend: `docker compose restart backend`
7. Verify:

```bash
curl -H "X-N8N-API-KEY: your_key_here" http://localhost:5678/api/v1/workflows
# Expected: {"data":[]}
```

### Step 0.11: Test Sarvam AI connection

```bash
curl https://api.sarvam.ai/v1/chat/completions \
  -H "Authorization: Bearer YOUR_SARVAM_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sarvam-m4",
    "messages": [{"role": "user", "content": "Say hello in JSON format: {\"greeting\": \"...\"}"}],
    "max_tokens": 100
  }'
# Expected: A JSON response with a greeting
```

### Step 0.12: Commit

```bash
git add -A
git commit -m "layer-0: docker + fastapi + n8n + sarvam"
git tag layer-0-complete
```

**✅ Done when:** `docker compose up` starts both services. `/health` returns ok. n8n UI loads. Sarvam responds.

---

## Layer 1 — Supabase Schema + RLS

> **Goal:** All 6 tables exist in Supabase. RLS is on. Triggers auto-create profiles on signup.
> **Time estimate:** Day 1–2 (2 days)
> **Why first:** Schema is the contract everything else is built against. Auth needs `profiles`, agent logs need `executions`, integrations page needs `data_sources`. Changing schema later means rewriting endpoints.

### Step 1.1: Open Supabase SQL Editor

1. Go to your Supabase project dashboard
2. Click **SQL Editor** in the left sidebar
3. Click **New query**

### Step 1.2: Run Part 1 — Create all 6 tables

Copy and paste this entire block into the SQL editor and click **Run**:

```sql
-- ============================================
-- PART 1: TABLES
-- ============================================

create extension if not exists "uuid-ossp";

-- PROFILES (auto-created on signup via trigger)
create table public.profiles (
  id uuid references auth.users(id) on delete cascade primary key,
  email text not null,
  full_name text,
  avatar_url text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- WORKFLOWS (user's automation workflows)
create table public.workflows (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  name text not null,
  description text,
  trigger_channel text check (
    trigger_channel in ('gmail','whatsapp','both')
  ) default 'gmail',
  status text check (
    status in ('active','inactive','draft')
  ) default 'draft',
  n8n_workflow_id text,
  agent_config jsonb default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- AGENTS (5 agents per workflow)
create table public.agents (
  id uuid default uuid_generate_v4() primary key,
  workflow_id uuid references public.workflows(id) on delete cascade not null,
  name text not null,
  role text check (
    role in ('classifier','researcher','qualifier','responder','executor')
  ) not null,
  system_prompt text not null,
  tools jsonb default '[]',
  handoff_rules text,
  output_format text default 'json',
  order_index integer not null,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- EXECUTIONS (each run of a workflow)
create table public.executions (
  id uuid default uuid_generate_v4() primary key,
  workflow_id uuid references public.workflows(id) on delete cascade not null,
  user_id uuid references public.profiles(id) on delete cascade not null,
  n8n_execution_id text,
  source_channel text check (
    source_channel in ('gmail','whatsapp','test')
  ),
  status text check (
    status in ('running','success','failed','cancelled')
  ) default 'running',
  inquiry_snippet text,
  sender_id text,
  final_reply text,
  started_at timestamptz default now(),
  finished_at timestamptz,
  duration_ms integer,
  score integer check (score >= 1 and score <= 10),
  scorecard_detail jsonb default '{}'
);

-- AGENT LOGS (per-agent output within an execution)
-- duration_ms here enables bottleneck detection in Layer 10
create table public.agent_logs (
  id uuid default uuid_generate_v4() primary key,
  execution_id uuid references public.executions(id) on delete cascade not null,
  agent_role text check (
    agent_role in ('classifier','researcher','qualifier','responder','executor')
  ) not null,
  input jsonb,
  output jsonb,
  duration_ms integer not null default 0,
  status text check (
    status in ('success','failed','skipped')
  ) default 'success',
  error_message text,
  created_at timestamptz default now()
);

-- DATA SOURCES (integration connection status)
create table public.data_sources (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  source_type text check (
    source_type in ('gmail','whatsapp','google_drive','google_sheets')
  ) not null,
  is_connected boolean default false,
  last_verified_at timestamptz,
  created_at timestamptz default now(),
  unique(user_id, source_type)
);
```

### Step 1.3: Run Part 2 — Indexes + Triggers

New query, paste and run:

```sql
-- ============================================
-- PART 2: INDEXES + TRIGGERS
-- ============================================

-- Performance indexes
create index on public.workflows(user_id);
create index on public.executions(workflow_id);
create index on public.executions(user_id);
create index on public.executions(started_at desc);
create index on public.agent_logs(execution_id);
create index on public.agent_logs(agent_role);

-- Auto-update updated_at timestamp
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger workflows_updated_at
  before update on public.workflows
  for each row execute function update_updated_at();

create trigger profiles_updated_at
  before update on public.profiles
  for each row execute function update_updated_at();

create trigger agents_updated_at
  before update on public.agents
  for each row execute function update_updated_at();

-- Auto-create profile + 4 data_source rows on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', '')
  );
  insert into public.data_sources (user_id, source_type, is_connected)
  values
    (new.id, 'gmail', false),
    (new.id, 'whatsapp', false),
    (new.id, 'google_drive', false),
    (new.id, 'google_sheets', false);
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
```

### Step 1.4: Run Part 3 — Row Level Security

New query, paste and run:

```sql
-- ============================================
-- PART 3: ROW LEVEL SECURITY
-- ============================================

alter table public.profiles enable row level security;
alter table public.workflows enable row level security;
alter table public.agents enable row level security;
alter table public.executions enable row level security;
alter table public.agent_logs enable row level security;
alter table public.data_sources enable row level security;

-- Each user can only see/edit their own data
create policy "own profile"
  on public.profiles for all using (auth.uid() = id);

create policy "own workflows"
  on public.workflows for all using (auth.uid() = user_id);

create policy "own agents"
  on public.agents for all using (
    exists (
      select 1 from public.workflows
      where id = agents.workflow_id and user_id = auth.uid()
    )
  );

create policy "own executions"
  on public.executions for all using (auth.uid() = user_id);

create policy "own agent logs"
  on public.agent_logs for all using (
    exists (
      select 1 from public.executions
      where id = agent_logs.execution_id and user_id = auth.uid()
    )
  );

create policy "own data sources"
  on public.data_sources for all using (auth.uid() = user_id);
```

### Step 1.5: Verify tables exist

Run this verification query:

```sql
select table_name from information_schema.tables
where table_schema = 'public'
order by table_name;
```

**Expected result:** `agent_logs`, `agents`, `data_sources`, `executions`, `profiles`, `workflows`

### Step 1.6: Test the signup trigger

1. Go to Supabase **Authentication** → **Users** → **Add user**
2. Create a test user with email `test@test.com` and a password
3. Go to **Table Editor** → `profiles` — you should see a row for this user
4. Go to **Table Editor** → `data_sources` — you should see 4 rows (gmail, whatsapp, google_drive, google_sheets) all with `is_connected = false`

If both checks pass, the trigger is working.

### Step 1.7: Save schema locally

Save all three SQL blocks into `supabase/schema.sql` for version control and future reference.

### Step 1.8: Commit

```bash
git add -A
git commit -m "layer-1: supabase schema + RLS + triggers"
git tag layer-1-complete
```

**✅ Done when:** All 6 tables visible in Supabase. RLS enabled on all. Test signup auto-creates profile + 4 data_source rows.

---

## Layer 2 — GCP OAuth + Gmail Trigger + Classifier Agent

> **Goal:** A real Gmail email arrives → Classifier agent returns valid JSON 10/10 times.
> **Time estimate:** Day 3 (1 day)
> **Why real Gmail from day one:** The PDF demo says "send a test inquiry via Gmail." Building with a mock webhook and swapping to real Gmail later means debugging OAuth under time pressure. Set it up once, never touch it again.

### Step 2.1: Create GCP project and enable APIs

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **New Project** → name it `n8n-hestabit` → Create
3. Go to **APIs & Services → Library**
4. Search for and **Enable** each of these:
   - Gmail API
   - Google Sheets API
   - Google Drive API

### Step 2.2: Configure OAuth consent screen

1. Go to **APIs & Services → OAuth consent screen**
2. Select **External** user type → Create
3. Fill in:
   - App name: `n8n-hestabit`
   - User support email: your email
   - Developer contact: your email
4. Click **Save and Continue** through scopes (no changes needed)
5. On the **Test users** page, click **Add Users** → add your Gmail address
6. Save and Continue → Back to Dashboard

### Step 2.3: Create OAuth2 credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth 2.0 Client ID**
3. Application type: **Web application**
4. Name: `n8n-hestabit`
5. Under **Authorized redirect URIs**, add:
   ```
   http://localhost:5678/rest/oauth2-credential/callback
   ```
6. Click **Create**
7. **Copy the Client ID and Client Secret** — you need them in the next step

### Step 2.4: Connect Google OAuth in n8n

1. Open n8n at `http://localhost:5678`
2. Go to **Settings → Credentials → Add Credential**
3. Search for **Google OAuth2 API**
4. Paste your Client ID and Client Secret
5. Click **Sign in with Google** → authorize with your Gmail account
6. This **single credential** works for Gmail, Sheets, and Drive nodes

### Step 2.5: Build the Classifier workflow in n8n

Create a new workflow in n8n and add these nodes in order:

**Node 1: Gmail Trigger**
- Trigger on: New email
- Poll every: 1 minute
- Label/Mailbox: INBOX
- Simple: false (to get full message data)
- Use your Google OAuth2 credential

**Node 2: Set (Normalize Input)**
- Set these fields:
  - `original_inquiry` = `{{ $json.text }}` (email body)
  - `sender_email` = `{{ $json.from }}`
  - `subject` = `{{ $json.subject }}`
  - `message_id` = `{{ $json.id }}`
  - `source_channel` = `gmail`

**Node 3: HTTP Request (Classifier Agent)**
- Method: POST
- URL: `https://api.sarvam.ai/v1/chat/completions`
- Authentication: Header Auth
  - Header Name: `Authorization`
  - Header Value: `Bearer YOUR_SARVAM_API_KEY`
- Body (JSON):
```json
{
  "model": "sarvam-m4",
  "messages": [
    {
      "role": "system",
      "content": "You are a customer inquiry classifier.\nReturn ONLY a raw JSON object.\nNo explanation. No markdown. No code fences. No preamble.\nJust the JSON object and nothing else.\n\nRequired format:\n{\"type\":\"...\",\"priority\":\"...\",\"confidence\":0.0}\n\ntype must be exactly one of:\nsales_inquiry | support_ticket | complaint | general_question | order_request\n\npriority must be exactly one of:\nlow | medium | high\n\nconfidence must be a float between 0.0 and 1.0"
    },
    {
      "role": "user",
      "content": "Classify this customer inquiry:\n\nSubject: {{ $json.subject }}\nBody: {{ $json.original_inquiry }}"
    }
  ],
  "max_tokens": 200
}
```

**Node 4: Code (JSON Extraction)**

This is the critical 4-method extraction cascade. Add a Code node with this JavaScript:

```javascript
const raw = $input.first().json.choices?.[0]?.message?.content
  || $input.first().json.output
  || $input.first().json.message?.content
  || "";

function extractJSON(text) {
  // Method 1: direct parse
  try { return JSON.parse(text.trim()); } catch {}

  // Method 2: strip markdown fences
  const stripped = text.replace(/```(?:json)?\s*|\s*```/g, "").trim();
  try { return JSON.parse(stripped); } catch {}

  // Method 3: first complete {...} block
  const m1 = text.match(/\{[^{}]*\}/s);
  if (m1) { try { return JSON.parse(m1[0]); } catch {} }

  // Method 4: greedy {...} for nested JSON
  const m2 = text.match(/\{.*\}/s);
  if (m2) { try { return JSON.parse(m2[0]); } catch {} }

  return null;
}

const parsed = extractJSON(raw);
return [{
  json: parsed
    ? { ...parsed, _ok: true }
    : { _ok: false, _raw: raw.substring(0, 500) }
}];
```

**Node 5: IF (Validation)**
- Condition: `{{ $json._ok }}` equals `true`
- True branch → continue to next agent (for now, just a Set node that outputs the result)
- False branch → retry the HTTP Request once, then fail

### Step 2.6: Test 10 times

Send 10 different test emails to your connected Gmail inbox. Verify that each one produces a valid JSON response with `type`, `priority`, and `confidence` fields.

Example test emails to send:
1. "Hi, we need enterprise pricing for 50 users" → should be `sales_inquiry`
2. "My login isn't working, please help" → should be `support_ticket`
3. "Your service was terrible last week" → should be `complaint`
4. "What are your office hours?" → should be `general_question`
5. "I'd like to order 100 units of product X" → should be `order_request`

Check each execution in n8n's execution log. All 10 should show valid JSON output.

### Step 2.7: Commit

```bash
git add -A
git commit -m "layer-2: gcp oauth + classifier 10/10"
git tag layer-2-complete
```

**✅ Done when:** 10 real test emails all produce valid JSON with correct `type`, `priority`, `confidence`. Zero extraction failures.

---

## Layer 3 — Full 5-Agent Chain + Sheets Logging + Test Matrix

> **Goal:** All 5 agents chained. Gmail reply sent automatically. Sheets logged. Test matrix green 9/10.
> **Time estimate:** Day 4–6 (3 days)
> **This is the most critical layer.** This IS the product. Every subsequent layer is only worth building if this works reliably. Do not move to Layer 4 until the test matrix passes.

### Step 3.1: Create Google Sheet for logging

1. Create a new Google Sheet named "Inquiry Execution Log"
2. In Row 1, add these column headers:
   ```
   timestamp | source_channel | sender_email | inquiry_snippet |
   inquiry_type | priority | lead_score | reply_sent |
   total_duration_ms | status
   ```
3. Note the Sheet URL/ID — you'll need it for the Google Sheets node

### Step 3.2: Extend the n8n workflow with all 5 agents

Build on the Layer 2 workflow. The full chain is:

```
Gmail Trigger
  →
Set node (normalize input)
  →
[Classifier Agent] → [Code: extract JSON] → [IF: _ok?]
  → false: retry once → still false: fail execution
  → true:
[Researcher Agent] → [Code: extract JSON] → [IF: _ok?]
  → true:
[Qualifier Agent]  → [Code: extract JSON] → [IF: _ok?]
  → true:
[Responder Agent]  → [Code: extract JSON] → [IF: _ok?]
  → true:
[Executor Agent]   → [Code: extract JSON] → [IF: _ok?]
  → true:
Gmail Send (reply to original thread)
  →
Google Sheets Append Row
```

**Important:** Name your HTTP Request nodes consistently:
- `Classifier_Agent`
- `Researcher_Agent`
- `Qualifier_Agent`
- `Responder_Agent`
- `Executor_Agent`

These exact names are used for node-to-agent mapping in Layer 8.

### Step 3.3: Shared state object

Every node in the chain should accumulate results into a shared state. Use a Code node or Set node after each agent to merge the new output into the running state:

```json
{
  "original_inquiry": "...",
  "sender_email": "...",
  "message_id": "...",
  "source_channel": "gmail",
  "classification": {
    "type": "sales_inquiry",
    "priority": "high",
    "confidence": 0.95
  },
  "research": {
    "relevant_info": "...",
    "source": "google_drive"
  },
  "qualification": {
    "lead_score": 8,
    "reason": "..."
  },
  "draft_reply": "...",
  "execution_meta": {
    "started_at": "...",
    "agent_durations": {
      "classifier": 0,
      "researcher": 0,
      "qualifier": 0,
      "responder": 0,
      "executor": 0
    }
  }
}
```

### Step 3.4: Agent system prompts

**Researcher Agent:**
```
You are a knowledge base researcher.
Based on the customer inquiry and classification:
Inquiry: {original_inquiry}
Classification: {classification}

Extract the most relevant information to help respond.
Return ONLY JSON, no explanation:
{"relevant_info": "...", "source": "internal_kb"}

If you don't have specific information, return:
{"relevant_info": "No specific information found.", "source": "none", "use_fallback": true}
```

**Qualifier Agent:**
```
You are a lead/request qualifier.
Based on the inquiry, classification, and research:
Inquiry: {original_inquiry}
Classification: {classification}
Research: {research}

Score the lead or request from 1-10.
Return ONLY JSON:
{"lead_score": 0, "reason": "one sentence explaining the score"}

Higher score = warmer lead or more urgent request.
```

**Responder Agent:**
```
You are a customer service responder.
Draft a professional, personalized reply.
Use all context provided:
Inquiry: {original_inquiry}
Classification: {classification}
Research: {research}
Qualification: {qualification}

If relevant_info is "No specific information found",
draft a polite reply acknowledging the inquiry and
promising a follow-up within 24 business hours.

Return ONLY JSON:
{"draft_reply": "Your complete reply text here"}
```

**Executor Agent:**
```
You are an execution coordinator.
Confirm the reply is ready to send.
Draft reply: {draft_reply}
Channel: {source_channel}

Return ONLY JSON:
{"sent": true, "channel": "{source_channel}", "logged": true}
```

### Step 3.5: Required key validation per agent

After each agent's Code node (JSON extraction), add validation in the IF node:

| Agent | Required keys to check |
|-------|----------------------|
| Classifier | `type`, `priority`, `confidence` |
| Researcher | `relevant_info`, `source` |
| Qualifier | `lead_score`, `reason` |
| Responder | `draft_reply` |
| Executor | `sent`, `channel`, `logged` |

### Step 3.6: Gmail Send node

After the Executor agent succeeds:
- Add a **Gmail Send** node
- To: `{{ $json.sender_email }}`
- Subject: `Re: {{ $json.subject }}`
- Message: `{{ $json.draft_reply }}`
- In Reply To: `{{ $json.message_id }}` (to thread the reply)
- Use the same Google OAuth2 credential

### Step 3.7: Google Sheets Append Row

After Gmail Send:
- Add a **Google Sheets** node (Append Row operation)
- Select your "Inquiry Execution Log" sheet
- Map columns:
  - timestamp: `{{ $now }}`
  - source_channel: `{{ $json.source_channel }}`
  - sender_email: `{{ $json.sender_email }}`
  - inquiry_snippet: `{{ $json.original_inquiry.substring(0, 100) }}`
  - inquiry_type: `{{ $json.classification.type }}`
  - priority: `{{ $json.classification.priority }}`
  - lead_score: `{{ $json.qualification.lead_score }}`
  - reply_sent: `true`
  - total_duration_ms: computed duration
  - status: `success`

### Step 3.8: Run the test matrix

Send 10 test emails covering all inquiry types. For each, verify every column in this table:

| # | Type | Classifier ✓ | Researcher ✓ | Qualifier ✓ | Responder ✓ | Executor ✓ | Gmail ✓ | Sheets ✓ | Pass? |
|---|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | sales_inquiry | | | | | | | | |
| 2 | sales_inquiry | | | | | | | | |
| 3 | sales_inquiry | | | | | | | | |
| 4 | support_ticket | | | | | | | | |
| 5 | support_ticket | | | | | | | | |
| 6 | complaint | | | | | | | | |
| 7 | complaint | | | | | | | | |
| 8 | general_question | | | | | | | | |
| 9 | general_question | | | | | | | | |
| 10 | order_request | | | | | | | | |

**Pass criteria per row:** all 5 agents return valid JSON with correct keys AND Gmail reply arrives AND Sheets row logged.

**Target: 9/10 rows fully green.**

### Step 3.9: Export workflow template

**Do this immediately after the test matrix passes:**

1. In n8n UI → click the three dots menu on your workflow → **Download**
2. Save the downloaded JSON as `backend/templates/inquiry_workflow.json`
3. This becomes the template that Layer 7 clones for new workflows

### Step 3.10: Commit

```bash
git add -A
git commit -m "layer-3: full chain + sheets + 9/10 test matrix"
git tag layer-3-complete
```

**✅ Done when:** 9/10 test emails complete the full chain — all 5 agents pass, Gmail reply arrives, Sheets row logged.

---

## Layer 3.5 — Google Drive KB + WhatsApp Integration

> **Goal:** Researcher uses real Google Drive. WhatsApp works as a second trigger.
> **Time estimate:** Day 8–9 (2 days)
> **Drive is MUST HAVE** — the PDF explicitly lists Drive knowledge retrieval. WhatsApp is secondary.

### Step 3.5.1: Create Drive Knowledge Base

1. In your Google Drive, create a folder called `KnowledgeBase`
2. Inside it, create 5 text files:
   - `sales_inquiry.txt` — contains your company's pricing, plans, demo booking info
   - `support_ticket.txt` — contains common troubleshooting steps, FAQ answers
   - `complaint.txt` — contains complaint handling procedures, escalation paths
   - `general_question.txt` — contains office hours, contact info, general FAQ
   - `order_request.txt` — contains ordering process, payment methods, delivery info
3. Fill each file with realistic content (at least a paragraph each)

### Step 3.5.2: Add Drive node to Researcher

In the n8n workflow, before the Researcher Agent HTTP Request:

1. Add a **Google Drive** node (Download File operation)
2. File Path: `/KnowledgeBase/{{ $json.classification.type }}.txt`
3. Use the same Google OAuth2 credential
4. This downloads the matching KB file based on the Classifier's output

### Step 3.5.3: Update Researcher system prompt

```
You are a knowledge base researcher.
You have been given the following document from
the company knowledge base:

{drive_file_content}

Based on the customer inquiry:
{original_inquiry}

Extract the most relevant information.
Return ONLY JSON:
{
  "relevant_info": "...",
  "source": "google_drive",
  "document_used": "..."
}
```

### Step 3.5.4: WhatsApp setup (optional — skip if behind schedule)

If you have time:

1. Go to [developers.facebook.com](https://developers.facebook.com) → My Apps → Create App → Business
2. Add WhatsApp product → get temporary access token + phone number ID
3. Install ngrok: `snap install ngrok` (or download from ngrok.com)
4. Run: `ngrok http 5678` → copy the https URL
5. Set Meta webhook URL: `https://xxxx.ngrok-free.app/webhook/whatsapp`
6. In n8n → Credentials → WhatsApp Business Cloud → paste token
7. Add WhatsApp Trigger node as a second entry point to the same chain

### Step 3.5.5: Input normalization for both channels

Add a Code node at the top of the chain that handles both Gmail and WhatsApp:

```javascript
const isWhatsApp = $input.first().json.messages !== undefined;

return [{
  json: {
    original_inquiry: isWhatsApp
      ? $input.first().json.messages[0].text.body
      : $input.first().json.text,
    sender_id: isWhatsApp
      ? $input.first().json.contacts[0].wa_id
      : $input.first().json.from,
    message_id: isWhatsApp
      ? $input.first().json.messages[0].id
      : $input.first().json.id,
    source_channel: isWhatsApp ? "whatsapp" : "gmail"
  }
}];
```

### Step 3.5.6: Executor routes output by channel

Add an IF node in the Executor section:
- If `source_channel === "whatsapp"` → WhatsApp Send node
- Else → Gmail Send node

### Step 3.5.7: Cut line for this layer

```
Running out of time?
  ✓ Keep simplified Drive (filename lookup, not search) — MUST HAVE
  ✗ Drop WhatsApp, Gmail only for demo — WhatsApp is secondary
```

### Step 3.5.8: Commit

```bash
git add -A
git commit -m "layer-3.5: drive kb + whatsapp trigger"
git tag layer-3.5-complete
```

**✅ Done when:** Test email → Gmail reply arrives with Drive document content in Researcher output + Sheets log. (WhatsApp optional.)

---

## Layer 4 — FastAPI DB Connection + JWT Middleware + System Status

> **Goal:** FastAPI talks to Supabase. Every protected route requires valid JWT. System status endpoint live.
> **Time estimate:** Day 10–11 (2 days)
> **Why after agent chain:** The agent chain is the product. FastAPI is the platform API. A working agent chain with no UI beats a polished API with broken agents.

### Step 4.1: Create Supabase client module

Create `backend/app/db/client.py`:

```python
from supabase import create_client, Client
from app.core.config import get_settings

settings = get_settings()

def get_supabase_client() -> Client:
    """Anon client — respects RLS. Use for auth operations."""
    return create_client(settings.supabase_url, settings.supabase_anon_key)

def get_supabase_admin_client() -> Client:
    """Service role — bypasses RLS. JWT middleware is the security gate."""
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key
    )
```

### Step 4.2: Create JWT middleware

Create `backend/app/middleware/auth.py`:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from app.core.config import get_settings

settings = get_settings()
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        user_id = payload.get("sub")
        email = payload.get("email")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Invalid token", "code": "INVALID_TOKEN"}
            )
        return {"id": user_id, "email": email}
    except JWTError as e:
        if "expired" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Token expired", "code": "TOKEN_EXPIRED"}
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid token", "code": "INVALID_TOKEN"}
        )
```

### Step 4.3: Create system status endpoint

Create `backend/app/api/system.py`:

```python
from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user
from app.db.client import get_supabase_admin_client
from app.core.config import get_settings
import httpx

router = APIRouter(prefix="/system", tags=["system"])
settings = get_settings()

@router.get("/status")
async def system_status(current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    status = {
        "n8n": False,
        "gmail": False,
        "whatsapp": False,
        "google_drive": False,
        "google_sheets": False
    }

    # Check n8n connectivity
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{settings.n8n_url}/api/v1/workflows",
                headers={"X-N8N-API-KEY": settings.n8n_api_key},
                timeout=3.0
            )
            status["n8n"] = r.status_code == 200
    except Exception:
        pass

    # Check integrations from data_sources table
    sources = db.table("data_sources")\
        .select("source_type, is_connected")\
        .eq("user_id", current_user["id"])\
        .execute()

    for row in sources.data:
        status[row["source_type"]] = row["is_connected"]

    return status
```

### Step 4.4: Register router in main.py

Update `backend/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import system  # add this
import os

app = FastAPI(title="n8n Inquiry Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)  # add this

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Step 4.5: Error format contract

**Every endpoint in the entire API must use this error shape:**

```python
{"error": "Human readable message", "code": "SNAKE_CASE_CODE"}
```

Standard codes:
- `TOKEN_EXPIRED` — JWT expired
- `INVALID_TOKEN` — JWT invalid or missing
- `EMAIL_EXISTS` — duplicate email on registration
- `INVALID_CREDENTIALS` — wrong email/password (never reveal which)
- `NOT_FOUND` — resource doesn't exist
- `N8N_UNAVAILABLE` — n8n API unreachable
- `EXECUTION_NOT_FOUND` — execution doesn't exist
- `DB_ERROR` — database operation failed

### Step 4.6: Test via curl

```bash
# Should fail — no JWT
curl http://localhost:8000/system/status
# Expected: 401 {"detail":{"error":"Not authenticated"}}

# With a valid Supabase JWT (get one by logging in via Supabase client):
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:8000/system/status
# Expected: 200 {"n8n": true, "gmail": false, ...}
```

### Step 4.7: Commit

```bash
git add -A
git commit -m "layer-4: db + jwt + system status"
git tag layer-4-complete
```

**✅ Done when:** Valid JWT → user dict. Expired JWT → `TOKEN_EXPIRED`. Fake JWT → `INVALID_TOKEN`. `/system/status` returns all connection states. Zero 500s on auth failures.

---

## Layer 5 — Auth Endpoints

> **Goal:** Register, login, logout, profile — working via FastAPI. All edge cases tested via curl.
> **Time estimate:** Day 12–13 (2 days)

### Step 5.1: Create auth router

Create `backend/app/api/auth.py` with these endpoints:

```
POST /auth/register   → Supabase signup → DB trigger creates profile + data_sources
POST /auth/login      → JWT in httpOnly cookie
POST /auth/logout     → clears cookie
GET  /auth/me         → returns profile (protected)
PUT  /auth/me         → update full_name, avatar_url (protected)
```

**Why httpOnly cookie not localStorage:** XSS attacks cannot steal httpOnly cookies. JavaScript has zero access to them. localStorage exposes the token to any injected script.

### Step 5.2: Implement register

```python
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, EmailStr
from app.db.client import get_supabase_client

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""

@router.post("/register", status_code=201)
async def register(data: RegisterRequest):
    sb = get_supabase_client()
    try:
        result = sb.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {"full_name": data.full_name}
            }
        })
        if result.user is None:
            raise HTTPException(409, {"error": "Email already exists", "code": "EMAIL_EXISTS"})
        return {"message": "User created"}
    except Exception as e:
        if "already" in str(e).lower():
            raise HTTPException(409, {"error": "Email already exists", "code": "EMAIL_EXISTS"})
        raise HTTPException(500, {"error": str(e), "code": "REGISTRATION_FAILED"})
```

### Step 5.3: Implement login

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/login")
async def login(data: LoginRequest, response: Response):
    sb = get_supabase_client()
    try:
        result = sb.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })
        token = result.session.access_token
        response.set_cookie(
            key="auth-token",
            value=token,
            httponly=True,
            secure=False,  # True in production
            samesite="lax",
            max_age=3600 * 24 * 7  # 7 days
        )
        return {"message": "Login successful", "user": {"id": str(result.user.id), "email": result.user.email}}
    except Exception:
        raise HTTPException(401, {"error": "Invalid credentials", "code": "INVALID_CREDENTIALS"})
```

### Step 5.4: Implement logout, me, update profile

```python
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("auth-token")
    return {"message": "Logged out"}

@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    profile = db.table("profiles").select("*").eq("id", current_user["id"]).single().execute()
    return profile.data

class UpdateProfileRequest(BaseModel):
    full_name: str = None
    avatar_url: str = None

@router.put("/me")
async def update_me(data: UpdateProfileRequest, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    result = db.table("profiles").update(update_data).eq("id", current_user["id"]).execute()
    return result.data[0]
```

### Step 5.5: Test all edge cases via curl

Run each command and verify the expected response:

```bash
# 1. Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test1234!","full_name":"Test User"}'
# Expected: 201 {"message": "User created"}

# 2. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test1234!"}' \
  -c cookies.txt
# Expected: 200 + cookie set

# 3. Get profile
curl http://localhost:8000/auth/me -b cookies.txt
# Expected: 200 {"id":"...","email":"test@test.com","full_name":"Test User"}

# 4. Duplicate email
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test1234!","full_name":"Test"}'
# Expected: 409 {"error":"Email already exists","code":"EMAIL_EXISTS"}

# 5. Wrong password
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"wrong"}'
# Expected: 401 {"error":"Invalid credentials","code":"INVALID_CREDENTIALS"}

# 6. Logout
curl -X POST http://localhost:8000/auth/logout -b cookies.txt
# Expected: 200 + cookie cleared

# 7. Me after logout
curl http://localhost:8000/auth/me -b cookies.txt
# Expected: 401
```

### Step 5.6: Commit

```bash
git add -A
git commit -m "layer-5: auth endpoints complete"
git tag layer-5-complete
```

**✅ Done when:** All 7 curl tests pass. Zero 500s on any auth failure.

---

## Layer 6 — Next.js Auth Pages + Dashboard Shell

> **Goal:** Login/register UI. Protected routing. Dashboard shell with sidebar navigation.
> **Time estimate:** Day 14 (1 day)

### Step 6.1: Initialize Next.js project

```bash
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir
cd frontend
npm install axios
```

### Step 6.2: Create route protection middleware

Create `frontend/src/middleware.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server'

const protectedRoutes = ['/dashboard', '/workflows',
  '/history', '/analytics', '/settings', '/profile']
const authRoutes = ['/login', '/register']

export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth-token')?.value
  const path = request.nextUrl.pathname

  const isProtected = protectedRoutes.some(r => path.startsWith(r))
  const isAuth = authRoutes.some(r => path.startsWith(r))

  if (isProtected && !token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  if (isAuth && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }
  return NextResponse.next()
}
```

### Step 6.3: Build login and register pages

Build forms that POST to `/auth/login` and `/auth/register` on your FastAPI backend. On success, redirect to `/dashboard`.

### Step 6.4: Build dashboard shell with sidebar

The sidebar appears on every protected page:

```
📊 n8n Platform
─────────────
▶ Dashboard        /dashboard
▶ Workflows        /workflows
▶ Integrations     /settings/integrations
▶ History          /history
▶ Analytics        /analytics
▶ Profile          /profile
```

### Step 6.5: Build StatusBar component

`StatusBar.tsx` polls `GET /system/status` every 30 seconds and shows:

```
[● n8n] [● Gmail] [● Sheets] [● Drive] [● WhatsApp]
```

Green dot = connected, red = disconnected. Displayed at the top of every protected page.

### Step 6.6: Verify the flow

1. Open `http://localhost:3000` → redirected to `/login`
2. Register a new user → redirected to `/login`
3. Login → at `/dashboard` with sidebar visible
4. Refresh → still at `/dashboard` (cookie persists)
5. Logout → at `/login`
6. Navigate to `/dashboard` directly → redirected to `/login`

### Step 6.7: Commit

```bash
git add -A
git commit -m "layer-6: next.js auth + shell + status bar"
git tag layer-6-complete
```

**✅ Done when:** Full auth flow works in browser. StatusBar visible on dashboard.

---

## Layer 6.5 — Data Sources Management Page

> **Goal:** Users see and manage all 4 integration connections from the UI.
> **Time estimate:** Day 15 (1 day)

### Step 6.5.1: Create FastAPI endpoints

```
GET  /integrations         → list all 4 data sources with status
POST /integrations/verify/{source_type}  → ping n8n credential, update status
```

### Step 6.5.2: Build the UI page at `/settings/integrations`

Show 4 cards, one per integration:

```
┌──────────────────────────────────────────┐
│ 📧 Gmail              ● Connected        │
│   Last verified: 2 min ago    [Verify]   │
├──────────────────────────────────────────┤
│ 💬 WhatsApp Business  ○ Disconnected     │
│   Not yet verified            [Verify]   │
├──────────────────────────────────────────┤
│ 📁 Google Drive       ● Connected        │
│   Last verified: 2 min ago    [Verify]   │
├──────────────────────────────────────────┤
│ 📊 Google Sheets      ● Connected        │
│   Last verified: 2 min ago    [Verify]   │
└──────────────────────────────────────────┘
```

**Note:** Actual credentials are configured inside n8n directly (Layer 2). This page only shows status and lets users verify — it does not store raw credentials.

### Step 6.5.3: Commit

```bash
git add -A
git commit -m "layer-6.5: integrations management page"
git tag layer-6.5-complete
```

**✅ Done when:** All 4 integration cards show correct status. Verify button updates `last_verified_at`.

---

## Layer 7 — Workflow CRUD + Embedded n8n Editor + Agent Config UI

> **Goal:** Users create workflows, configure agents, and edit visually in embedded n8n.
> **Time estimate:** Day 16–18 (3 days)
> **Build in order:** Piece 1 (CRUD) → Piece 2 (Agent Config) → Piece 3 (n8n Embed)

### Piece 1: Workflow CRUD (Day 16)

**FastAPI endpoints:**

```
POST   /workflows         → clone template + POST to n8n + save to Supabase
GET    /workflows         → list user's workflows
GET    /workflows/{id}    → workflow + 5 agent rows
PUT    /workflows/{id}    → update name/description/channel + sync to n8n
DELETE /workflows/{id}    → delete from n8n first, then Supabase
```

**Template clone logic:**

```python
import json
from uuid import uuid4

def clone_workflow(name: str, trigger_channel: str) -> dict:
    with open("templates/inquiry_workflow.json") as f:
        template = json.load(f)
    template["name"] = name
    template["id"] = str(uuid4())
    for node in template["nodes"]:
        if node["type"] == "n8n-nodes-base.gmailTrigger":
            node["disabled"] = trigger_channel == "whatsapp"
        if node["type"] == "n8n-nodes-base.whatsappTrigger":
            node["disabled"] = trigger_channel == "gmail"
    return template
```

**Critical: Sync failure handling**

If n8n succeeds but Supabase fails, roll back the n8n workflow:

```python
try:
    n8n_response = await post_to_n8n(cloned_workflow)
    n8n_workflow_id = n8n_response["id"]
except Exception:
    raise HTTPException(500, {"code": "N8N_UNAVAILABLE"})

try:
    db.table("workflows").insert({...}).execute()
    db.table("agents").insert([...5 default agents...]).execute()
except Exception:
    await delete_from_n8n(n8n_workflow_id)  # rollback
    raise HTTPException(500, {"code": "DB_ERROR"})
```

### Piece 2: Agent Configuration UI (Day 17)

**FastAPI endpoints:**

```
GET /workflows/{id}/agents    → returns 5 agents ordered by order_index
PUT /agents/{agent_id}        → update prompt/tools + sync to n8n node
```

**n8n node sync** — when a user edits a system prompt, it MUST update the corresponding n8n node:

```python
async def sync_agent_to_n8n(n8n_workflow_id, agent_role, system_prompt):
    workflow = await get_n8n_workflow(n8n_workflow_id)
    for node in workflow["nodes"]:
        if node["name"] == f"{agent_role.title()}_Agent":
            node["parameters"]["messages"]["values"][0]["content"] = system_prompt
    await update_n8n_workflow(n8n_workflow_id, workflow)
```

**UI at `/workflows/{id}/agents`:** Show 5 cards, one per agent, each with an editable textarea for the system prompt, tool checkboxes, output format dropdown, and a Save button.

### Piece 3: Embedded n8n Editor (Day 18)

**Page at `/workflows/{id}/edit`:**

```typescript
export default function WorkflowEdit({ params }) {
  const [workflow, setWorkflow] = useState(null)

  return (
    <div style={{ height: 'calc(100vh - 64px)' }}>
      <iframe
        src={`http://localhost:5678/workflow/${workflow?.n8n_workflow_id}`}
        width="100%"
        height="100%"
        style={{ border: 'none' }}
        title="n8n Workflow Editor"
      />
    </div>
  )
}
```

This works because `N8N_AUTH_EXCLUDE_ENDPOINTS=rest/.*` was set in Layer 0 — no login screen appears in the iframe.

### Step 7.1: Commit

```bash
git add -A
git commit -m "layer-7: workflow crud + n8n embed + agent config"
git tag layer-7-complete
```

**✅ Done when:** Create workflow in UI → appears in n8n. Edit agent prompt → reflected in n8n node. Delete workflow → gone from both. Embedded editor loads with no login screen.

---

## Layer 8 — Execution Trigger + Controls + Status Bar + Trace View

> **Goal:** One-click trigger from UI, Start/Stop/Retry controls, live agent trace view.
> **Time estimate:** Day 19–21 (3 days)
> **This is the demo.** This is what you show on demo day.

### Step 8.1: FastAPI endpoints

```
POST /executions/trigger/{workflow_id}
  → body: {inquiry_text, source_channel, sender_id}
  → POST to n8n webhook → save execution (status: "running") → return execution_id

GET /executions/{id}/status
  → poll n8n → if complete: save agent_logs to Supabase → return trace

GET /executions/{id}/trace
  → read agent_logs from Supabase → return ordered by order_index

POST /executions/{id}/cancel
  → DELETE execution in n8n → update status to "cancelled"

POST /executions/{id}/retry
  → re-trigger with same input → return new execution_id
```

### Step 8.2: Node name → agent role mapping

```python
NODE_TO_AGENT = {
    "Classifier_Agent": "classifier",
    "Researcher_Agent": "researcher",
    "Qualifier_Agent":  "qualifier",
    "Responder_Agent":  "responder",
    "Executor_Agent":   "executor"
}
```

### Step 8.3: Build the execution page UI

```
Status bar (always visible, polls /system/status every 30s):
[● n8n] [● Gmail] [● Sheets] [● Drive] [● WhatsApp]

┌─────────────────────────────────────────────┐
│ Test Inquiry                                │
├─────────────────────────────────────────────┤
│ [Inquiry text input                       ] │
│ Channel: [Gmail ▼]   [▶ Run]  [■ Stop]  [↻ Retry] │
├─────────────────────────────────────────────┤

⏳ Running... (polling every 2s)

✅ Completed in 5.4s

├── ✅ Classifier    0.8s
│   Input:  "Hi, we're a 50-person team..."
│   Output: {"type":"sales_inquiry","priority":"high"}
│
├── ✅ Researcher    1.2s
│   Output: {"relevant_info":"Enterprise plan..."}
│
├── ✅ Qualifier     0.9s
│   Output: {"lead_score":8,"reason":"50-person team..."}
│
├── ✅ Responder     2.1s
│   Output: {"draft_reply":"Hi, thanks for reaching out..."}
│
└── ✅ Executor      0.4s
    Output: {"sent":true,"channel":"gmail","logged":true}

Reply sent to: customer@test.com  ✅
Logged to: Google Sheets          ✅
```

### Step 8.4: Honest note on Pause

n8n does not support pausing a running execution via API. The button is labeled **"Stop"** not "Pause." Stop calls the Cancel endpoint.

### Step 8.5: Commit

```bash
git add -A
git commit -m "layer-8: execution trigger + trace + controls"
git tag layer-8-complete
```

**✅ Done when:** Click Run → spinner → trace appears → Gmail reply arrives. Stop cancels. Retry re-runs. Status bar all green.

---

## Layer 9 — History + Logs + Export

> **Goal:** Full execution history, detail view, export in JSON/TXT/PDF.
> **Time estimate:** Day 22–24 (3 days)

### Step 9.1: FastAPI endpoints

```
GET /executions          → paginated list with filters (status, channel, date range)
GET /executions/{id}     → full execution + all agent_logs
GET /executions/{id}/export?format=json|txt|pdf
GET /analytics/export?format=csv|pdf
```

### Step 9.2: Export implementations

**JSON:** Raw dump of execution + agent_logs as formatted JSON.

**TXT:** Human-readable text report with execution summary and agent trace.

**PDF:** Use `reportlab` to generate a PDF with header, agent trace table, and reply sent.

**CSV:** Use `pandas` DataFrame of all executions for analytics export.

### Step 9.3: History page at `/history`

```
[Filter: All|Gmail|WhatsApp] [Status: All|✅|❌]  [Export CSV]

Date          Source    Snippet               Duration  Status  Score
Apr 14 10:23  Gmail     "Enterprise pric..."  5.4s      ✅      8/10
Apr 14 09:11  WhatsApp  "Refund request..."   8.1s      ✅      7/10
Apr 13 16:42  Gmail     "Support ticket..."   31.2s     ❌       —
```

### Step 9.4: Detail page at `/history/{id}`

- Full original inquiry text
- Agent trace timeline (reuse the TraceView component from Layer 8)
- Final reply sent
- Export buttons: `[JSON]` `[TXT]` `[PDF]`
- Scorecard (if generated — from Layer 10)

### Step 9.5: Commit

```bash
git add -A
git commit -m "layer-9: history + logs + export"
git tag layer-9-complete
```

**✅ Done when:** History shows all executions. Click row → full trace + reply. All 3 export formats download.

---

## Layer 10 — Analytics Dashboard + Full Scorecard

> **Goal:** Honest metrics. Per-agent scorecard. Real bottleneck detection. Export.
> **Time estimate:** Day 25–27 (3 days)

### Step 10.1: FastAPI analytics endpoints

```
GET /analytics/summary    → total executions, success rate, avg duration, avg score
GET /analytics/chart      → [{date, count, success_count}] for daily/weekly charts
GET /analytics/agents     → per-agent avg_duration_ms, success_rate, bottleneck_flag
GET /executions/{id}/scorecard → deterministic + Sarvam AI assessment
```

### Step 10.2: Bottleneck detection (deterministic, not LLM)

```python
def detect_bottleneck(agent_role, duration_ms, user_id, db) -> bool:
    """
    Flags as bottleneck if duration > 2x the rolling average
    over the last 10 executions. Purely deterministic.
    """
    recent = db.table("agent_logs")\
        .select("duration_ms")\
        .eq("agent_role", agent_role)\
        .order("created_at", desc=True)\
        .limit(10)\
        .execute()

    if not recent.data or len(recent.data) < 3:
        return False

    avg = sum(r["duration_ms"] for r in recent.data) / len(recent.data)
    return duration_ms > (avg * 2)
```

### Step 10.3: Individual execution scorecard

**Part 1 — Deterministic (always shown):**
- Chain completion: ✅ All 5 agents completed
- Reply generated: ✅ Yes
- Handling time: 5.4s (below avg 6.2s ✅)
- Channel delivered: ✅ Gmail sent
- KB match found: ✅ google_drive
- Bottlenecks: None ✅

**Part 2 — Sarvam AI assessment (async, clearly labeled):**

Scoring prompt with explicit rubric:
```
You are evaluating a customer service reply.
Score on exactly these criteria.
Return ONLY JSON, no explanation, no markdown:
{
  "answers_directly": 0-3,
  "personalized": 0-3,
  "professional": 0-2,
  "next_step": 0-2,
  "total": 0-10,
  "weakest_area": "one sentence max"
}
Original inquiry: {inquiry}
Reply sent: {reply}
```

Scorecard runs **async after execution completes** — adds zero latency to the execution itself. Saved to `executions.scorecard_detail`.

### Step 10.4: Analytics dashboard at `/analytics`

Show: total executions, success rate, avg time, inquiries over time chart (use Recharts), most common inquiry types, avg AI quality score, per-agent performance table with bottleneck flags, and export buttons.

### Step 10.5: Commit

```bash
git add -A
git commit -m "layer-10: analytics + scorecard + bottleneck"
git tag layer-10-complete
```

**✅ Done when:** Dashboard shows real numbers. Per-agent table populated. Bottleneck flags appear. Scorecard on every execution detail. Both exports work.

---

## Layer 11 — Polish + Smoke Tests + Deploy Prep

> **Goal:** Anyone clones the repo, runs `docker compose up`, and has a working demo in under 10 minutes.
> **Time estimate:** Day 28–29 (2 days)

### Step 11.1: Create `smoke_test.sh`

```bash
#!/bin/bash
echo "=== Smoke Tests ==="

echo -n "L0 FastAPI health: "
curl -sf http://localhost:8000/health | grep -q '"status":"ok"' \
  && echo "✅" || echo "❌"

echo -n "L0 n8n API: "
curl -sf -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
  http://localhost:5678/api/v1/workflows \
  | grep -q '"data"' && echo "✅" || echo "❌"

echo -n "L5 Auth register: "
curl -sf -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke@test.com","password":"Test1234!","full_name":"Smoke Test"}' \
  | grep -q '"message"' && echo "✅" || echo "❌"

echo -n "L5 Auth login: "
curl -sf -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke@test.com","password":"Test1234!"}' \
  -c /tmp/smoke_cookies.txt \
  | grep -q '"message"' && echo "✅" || echo "❌"

echo -n "L5 Auth me: "
curl -sf http://localhost:8000/auth/me \
  -b /tmp/smoke_cookies.txt \
  | grep -q '"email"' && echo "✅" || echo "❌"

echo -n "L7 Create workflow: "
curl -sf -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -b /tmp/smoke_cookies.txt \
  -d '{"name":"Smoke Test Workflow","trigger_channel":"gmail"}' \
  | grep -q '"id"' && echo "✅" || echo "❌"

echo "=== Done ==="
```

### Step 11.2: Write README.md

Structure:
1. What this is
2. Architecture (with diagram)
3. Architecture decisions (why FastAPI, why n8n, why template clone)
4. Prerequisites
5. Setup (5 steps)
6. GCP OAuth setup
7. Running the demo
8. Demo script
9. Test matrix results
10. Troubleshooting

### Step 11.3: Write FUTURE.md

Acknowledge out-of-scope features:
- Workflow template marketplace
- Team collaboration + sharing
- Human-in-the-loop approval
- A/B testing agent prompts
- Scheduled batch processing
- Advanced cross-workflow analytics
- Google Drive search (currently uses filename lookup)

### Step 11.4: Final test matrix rerun

Rerun the full 10-email test matrix from Layer 3. Fix any flakiness. Target: 9/10 passing.

### Step 11.5: Record backup demo video

Record a 3-minute screen recording of the full demo flow as a backup in case live demo has issues on demo day.

### Step 11.6: Final commit

```bash
chmod +x smoke_test.sh
git add -A
git commit -m "layer-11: polish + smoke tests + deploy ready"
git tag layer-11-complete
```

**✅ Done when:** Fresh clone + `.env` + `docker compose up` = working demo in under 10 minutes. All smoke tests green. README is clear.

---

## 30-Day Timeline

| Week | Days | Layer | What You Build |
|------|------|-------|---------------|
| **Week 1** | Day 1–2 | Layer 1 | Supabase schema + RLS |
| | Day 3 | Layer 2 | GCP OAuth + Classifier 10/10 |
| | Day 4–6 | Layer 3 | Full 5-agent chain + test matrix 9/10 |
| | Day 7 | Buffer | Catch up / start Layer 3.5 |
| **Week 2** | Day 8–9 | Layer 3.5 | Drive KB + WhatsApp |
| | Day 10–11 | Layer 4 | FastAPI DB + JWT + system status |
| | Day 12–13 | Layer 5 | Auth endpoints |
| | Day 14 | Layer 6 | Next.js auth + dashboard shell |
| **Week 3** | Day 15 | Layer 6.5 | Integrations management page |
| | Day 16–18 | Layer 7 | Workflow CRUD + n8n embed + agent config |
| | Day 19–21 | Layer 8 | Execution trigger + trace view |
| **Week 4** | Day 22–24 | Layer 9 | History + logs + export |
| | Day 25–27 | Layer 10 | Analytics + scorecard |
| | Day 28–29 | Layer 11 | Polish + smoke tests |
| | Day 30 | — | Demo rehearsal + buffer |

---

## Cut Lines

What to drop if you're behind schedule:

**Behind end of Week 1?**
- Push Layer 3.5 to Week 2 (already planned)
- Use simplified Drive (filename lookup, not search) — always keep Drive
- Drive is MUST HAVE, never cut to zero

**Behind end of Week 2?**
- Drop Layer 6.5 (integrations page) — saves 1 day
- Drop WhatsApp, Gmail only for demo — saves 1 day

**Behind end of Week 3?**
- Drop TXT + PDF export, JSON only
- Drop analytics export PDF/CSV
- Drop bottleneck detail, keep overall score
- Saves 1.5 days total

**Never cut:**
- Layers 2 + 3 — the agent chain (this IS the product)
- Layer 7 — workflow creation + agent config UI
- Layer 8 — execution trigger + trace view
- These ARE the demo

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Time runs out | High | Critical | Use cut lines above; agents before UI |
| Sarvam JSON inconsistency | High | High | Extract-first with 4 methods, max 2 retries |
| Agent handoffs break | High | High | Validation node between every agent |
| GCP OAuth blocks Layer 2 | Medium | High | Start Day 3 morning, not afternoon |
| n8n iframe shows login screen | Medium | High | `N8N_AUTH_EXCLUDE_ENDPOINTS` set in Layer 0 |
| n8n template clone fails | Low | High | Template manually tested + exported in Layer 3 |
| Agent sync to n8n fails (Layer 7) | Medium | Medium | Log + surface error, don't silently fail |
| WhatsApp ngrok disconnects | Medium | Medium | Gmail is primary demo channel |
| Sarvam API down on demo day | Low | Critical | LM Studio local fallback via env var |
| JWT middleware bug | Low | Critical | Test all token states in Layer 4 curl tests |

---

## Version Control Strategy

```bash
# After every layer:
git add -A
git commit -m "layer-N: one line of what works"
git tag layer-N-complete

# If something breaks:
git checkout layer-N-complete
# This gets you back to the last known-good state
```

Tags give you rollback points. If Layer 7 breaks everything, `git checkout layer-6.5-complete` puts you back on solid ground.

---

## PDF Feature Coverage Map

Every MUST HAVE from the project PDF is covered:

| PDF Feature | Layer |
|-------------|-------|
| 1. User Authentication | Layer 5 (backend) + Layer 6 (frontend) |
| 2. Workflow & Agent Creation | Layer 7 |
| 3. Browser-Based Execution | Layer 8 |
| 4. Automation History & Logs | Layer 9 |
| 5. Agent Configuration | Layer 7 (Piece 2) |
| 6. Data Sources & Integrations | Layer 2 (GCP) + Layer 3.5 (Drive) + Layer 6.5 (UI) |
| 7. Analytics & Scorecard | Layer 10 |

---

*Built for Hestabit internship — April 2026*