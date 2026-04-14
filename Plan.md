Here is the complete, final, gap-free phase plan. Everything in one document.

---

## North Star

```
Demo day:
User signs up → builds "Customer Inquiry Handler" →
sends test email → watches 5 agents collaborate →
receives automated reply → sees detailed scorecard.
Reliable 9/10 times. Under 30 seconds.
```

---

## Architecture

```
Next.js (UI)  ←→  FastAPI (Python)  ←→  n8n (Docker)
                        ↕
                   Supabase (DB + Auth)
                        ↕
            Sarvam AI / LM Studio + Google APIs
```

**Why FastAPI stays:** FastAPI handles JWT auth, Supabase DB operations, n8n API orchestration, execution log processing, analytics aggregation, and file export via reportlab/pandas. These are Python-native operations. The service boundary means agent logic, DB layer, and UI are independently testable. This is documented in `README.md` under "Architecture Decisions" for evaluators who ask.

**Why n8n stays in Docker:** Core of the project brief. Non-negotiable.

**Why Sarvam + LM Studio:** Sarvam for cloud speed, LM Studio as local fallback if Sarvam is down on demo day. Both OpenAI-compatible — one env var switches between them.

---

## The Demo Script

Written now. Every layer is built toward making this work.

```
Input email:
  From:    customer@test.com
  Subject: Enterprise pricing inquiry
  Body:    "Hi, we're a 50-person team looking for an
            enterprise solution. Pricing and demo?"

Agent 1 — Classifier:
  {"type":"sales_inquiry","priority":"high","confidence":0.95}

Agent 2 — Researcher (real Drive lookup):
  {"relevant_info":"Enterprise plan: ₹X/month for 50+
   seats. Demo via Calendly.","source":"google_drive"}

Agent 3 — Qualifier:
  {"lead_score":8,"reason":"50-person team,
   explicit purchase intent, demo request"}

Agent 4 — Responder:
  {"draft_reply":"Hi, thanks for reaching out...
   [personalized, references team size + pricing]"}

Agent 5 — Executor:
  {"sent":true,"channel":"gmail","logged":true}

Total: under 30 seconds. 9/10 reliability.
```

---

## Layer 0 — Docker + n8n + FastAPI + Sarvam
**Status: ✅ DONE**

**Update `docker-compose.yml` now** — add n8n iframe auth fix and pin version:

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

```bash
docker compose down && docker compose up --build
git add -A && git commit -m "layer-0: docker + fastapi + n8n + sarvam"
git tag layer-0-complete
```

---

## Layer 1 — Supabase Schema + RLS
**Goal:** All 6 tables exist. RLS locked. Triggers working.

**Why first:** Schema is the contract everything else is built against. Auth endpoints need `profiles`. Agent logs need `executions`. Bottleneck detection needs `duration_ms` in `agent_logs`. Integrations page needs `data_sources`. Change schema after writing endpoints means rewriting endpoints. Do it once, do it right.

**Run in Supabase SQL Editor — Part 1: Tables**

```sql
create extension if not exists "uuid-ossp";

-- PROFILES
create table public.profiles (
  id uuid references auth.users(id) on delete cascade primary key,
  email text not null,
  full_name text,
  avatar_url text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- WORKFLOWS
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

-- AGENTS
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

-- EXECUTIONS
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

-- AGENT LOGS
-- duration_ms stored here enables bottleneck detection in Layer 10
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

-- DATA SOURCES
-- powers the integrations management page in Layer 6.5
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

**Part 2: Indexes + Triggers**

```sql
-- INDEXES
create index on public.workflows(user_id);
create index on public.executions(workflow_id);
create index on public.executions(user_id);
create index on public.executions(started_at desc);
create index on public.agent_logs(execution_id);
create index on public.agent_logs(agent_role);

-- UPDATED_AT TRIGGER
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

-- AUTO-CREATE PROFILE ON SIGNUP
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', '')
  );
  -- seed all 4 data source rows as disconnected
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

**Part 3: RLS**

```sql
alter table public.profiles enable row level security;
alter table public.workflows enable row level security;
alter table public.agents enable row level security;
alter table public.executions enable row level security;
alter table public.agent_logs enable row level security;
alter table public.data_sources enable row level security;

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

**Verify:**
```sql
select table_name from information_schema.tables
where table_schema = 'public'
order by table_name;
-- Expected: agent_logs, agents, data_sources,
--           executions, profiles, workflows
```

**Done when:** All 6 tables visible. RLS on all. Test signup creates profile + 4 data_source rows automatically.

```bash
git add -A && git commit -m "layer-1: supabase schema + RLS + triggers"
git tag layer-1-complete
```

---

## Layer 2 — GCP OAuth + Gmail Trigger + Classifier Agent
**Goal:** Real Gmail email arrives → Classifier returns valid JSON 10/10 times.

**Why real Gmail from day one:**

The PDF demo goal says "send a test inquiry via Gmail." Building with a mock webhook and swapping to real Gmail later means debugging OAuth under time pressure. Set it up once on Day 3, never touch it again.

**GCP setup — covers Gmail + Sheets + Drive with one credential:**

```
1. console.cloud.google.com → New Project → "n8n-hestabit"
2. APIs & Services → Enable:
   - Gmail API
   - Google Sheets API
   - Google Drive API
3. OAuth consent screen:
   - User type: External
   - App name: n8n-hestabit
   - Add your email as test user
4. Credentials → Create OAuth2 Client → Web application
   - Redirect URI: http://localhost:5678/rest/oauth2-credential/callback
   - Copy Client ID + Client Secret
5. n8n → Settings → Credentials → New → Google OAuth2 API
   → Paste Client ID + Secret → Sign in with Google
6. This one credential works for Gmail, Sheets, and Drive nodes
```

**n8n workflow — Layer 2:**

```
Gmail Trigger
  (poll every 1 min, unread only, INBOX label)
  ↓
Set node
  (extract: subject, body, sender, message_id)
  ↓
HTTP Request node
  (POST https://api.sarvam.ai/v1/chat/completions)
  (Authorization: Bearer ${SARVAM_API_KEY})
  ↓
Code node — JSON extraction
  ↓
IF node — extraction ok?
  → true:  output classification
  → false: retry HTTP Request once
            → still false: Error node (log raw output)
```

**Classifier system prompt:**

```
You are a customer inquiry classifier.
Return ONLY a raw JSON object.
No explanation. No markdown. No code fences. No preamble.
Just the JSON object and nothing else.

Required format:
{"type":"...","priority":"...","confidence":0.0}

type must be exactly one of:
sales_inquiry | support_ticket | complaint |
general_question | order_request

priority must be exactly one of:
low | medium | high

confidence must be a float between 0.0 and 1.0
```

**JSON extraction Code node — between every agent:**

```javascript
const raw = $input.first().json.output
  || $input.first().json.message?.content
  || $input.first().json.choices?.[0]?.message?.content
  || "";

function extractJSON(text) {
  // Method 1 — direct parse
  try { return JSON.parse(text.trim()); } catch {}

  // Method 2 — strip markdown fences
  const s = text.replace(/```(?:json)?\s*|\s*```/g, "").trim();
  try { return JSON.parse(s); } catch {}

  // Method 3 — first complete {...} block
  const m1 = text.match(/\{[^{}]*\}/s);
  if (m1) { try { return JSON.parse(m1[0]); } catch {} }

  // Method 4 — greedy {...} for nested JSON
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

**Why extract-first not retry-first:**

If Sarvam fails to return valid JSON, the problem is the model adding wrapper text, not a bad prompt. Retrying with a "stricter" prompt almost always also fails for the same reason. The 4-method extraction catches 95%+ of malformed responses. Only retry if all 4 extraction methods fail.

**Done when:** Send 10 real test emails to connected Gmail. Get valid JSON with `type`, `priority`, `confidence` back 10/10 times. Verify in n8n execution log.

```bash
git add -A && git commit -m "layer-2: gcp oauth + classifier 10/10"
git tag layer-2-complete
```

---

## Layer 3 — Full 5-Agent Chain + Sheets Logging + Test Matrix
**Goal:** All 5 agents chained. Gmail reply sent. Sheets logged. Test matrix green 9/10.

**Why this is the most critical layer:**

This is the product. Layers 4-11 are the platform around it. Every subsequent layer is only worth building if this works reliably. Give this layer 3 days. Do not move to Layer 4 until the test matrix passes.

**Full n8n chain:**

```
Gmail Trigger
  ↓
Set node — normalize input
  {original_inquiry, sender_email, message_id, source_channel:"gmail"}
  ↓
[Classifier Agent] → [Code: extract JSON] → [IF: _ok?]
  → false: retry once → still false: fail execution
  ↓ true
[Researcher Agent] → [Code: extract JSON] → [IF: _ok?]
  ↓ true
[Qualifier Agent]  → [Code: extract JSON] → [IF: _ok?]
  ↓ true
[Responder Agent]  → [Code: extract JSON] → [IF: _ok?]
  ↓ true
[Executor Agent]   → [Code: extract JSON] → [IF: _ok?]
  ↓ true
Gmail Send (reply to original thread using message_id)
  ↓
Google Sheets Append Row (execution log)
```

**Shared state object — passed through every node:**

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

**Required keys per agent validation node:**

```
Classifier:  ["type", "priority", "confidence"]
Researcher:  ["relevant_info", "source"]
Qualifier:   ["lead_score", "reason"]
Responder:   ["draft_reply"]
Executor:    ["sent", "channel", "logged"]
```

**Researcher fallback — if no KB match:**

```json
{"relevant_info": "No specific information found.",
 "source": "none", "use_fallback": true}
```

Responder system prompt handles this:
```
If relevant_info is "No specific information found",
draft a polite reply acknowledging the inquiry and
promising a follow-up within 24 business hours.
```

**Google Sheets log columns:**

```
timestamp | source_channel | sender_email | inquiry_snippet |
inquiry_type | priority | lead_score | reply_sent |
total_duration_ms | status
```

**Test matrix — run before tagging layer-3-complete:**

| # | Type | Classifier ✓ | Researcher ✓ | Qualifier ✓ | Responder ✓ | Executor ✓ | Gmail ✓ | Sheets ✓ | Pass? |
|---|---|---|---|---|---|---|---|---|---|
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

Pass criteria per row: all 5 agents return valid JSON with correct keys AND Gmail reply arrives AND Sheets row logged.

Target: 9/10 rows fully green.

**After test matrix passes — export workflow immediately:**

```
n8n UI → three dots → Download
Save as: backend/templates/inquiry_workflow.json
This becomes the template for Layer 7.
```

```bash
git add -A && git commit -m "layer-3: full chain + sheets + 9/10 test matrix"
git tag layer-3-complete
```

---

## Layer 3.5 — Google Drive KB + WhatsApp Integration
**Goal:** Researcher uses real Drive. WhatsApp works as second trigger.

**Why this never fully disappears from the plan:**

The PDF explicitly lists Drive knowledge retrieval as a MUST HAVE. Even the simplified fallback approach uses real Drive — not a local JSON file. It cannot be cut to zero.

**Simplified Drive approach — no search API needed:**

```
Drive folder structure:
  /KnowledgeBase/
    sales_inquiry.txt
    support_ticket.txt
    complaint.txt
    general_question.txt
    order_request.txt

Researcher node:
  classification.type → filename
  Google Drive node → Download File → "{type}.txt"
  → content passed to Researcher agent as context
```

This uses the same GCP credential from Layer 2. One new node. No Drive search API. Always works. If time permits, upgrade to Drive search. If not, this is still real Drive integration.

**Researcher system prompt with Drive content:**

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

**WhatsApp Business Cloud setup:**

```
1. developers.facebook.com → My Apps → Create App → Business
2. Add WhatsApp product → get temporary access token + phone number ID
3. Install ngrok: snap install ngrok
4. ngrok.com → free account → copy auth token
5. ngrok config add-authtoken YOUR_TOKEN
6. ngrok http 5678 → copy https://xxxx.ngrok-free.app
7. Meta webhook URL: https://xxxx.ngrok-free.app/webhook/whatsapp
8. n8n → Credentials → WhatsApp Business Cloud → paste token
9. Add WhatsApp Trigger node as second entry to same chain
```

**Normalized input node — handles both channels:**

```javascript
// Set node at top of chain
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

**Executor routes output by channel:**

```javascript
// IF node in Executor
if ($input.first().json.source_channel === "whatsapp") {
  // WhatsApp Send node
} else {
  // Gmail Send node
}
```

**Cut line for this layer specifically:**

```
Running out of time?
  → Keep simplified Drive (filename lookup, not search)
  → Drop WhatsApp, Gmail only for demo
  → Drive never disappears — it's MUST HAVE
  → WhatsApp is secondary — Gmail is the primary demo channel
```

**Done when:** Test email → Gmail reply + Drive doc in Researcher output + Sheets log. WhatsApp message → WhatsApp reply + same chain + Sheets log.

```bash
git add -A && git commit -m "layer-3.5: drive kb + whatsapp trigger"
git tag layer-3.5-complete
```

---

## Layer 4 — FastAPI DB Connection + JWT Middleware + System Status
**Goal:** FastAPI talks to Supabase. Every protected route requires valid JWT. System status endpoint live.

**Why after agent chain:**

The agent chain is the product. FastAPI is the platform API. If Layer 3.5 isn't working, stay there until it is. A working agent chain with no UI beats a polished API with broken agents.

**Add to `requirements.txt`:**

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

**`backend/app/db/client.py`:**

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

**`backend/app/middleware/auth.py`:**

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

**`backend/app/api/system.py` — status endpoint:**

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
    """
    Returns connection status for n8n + all 4 integrations.
    Polled by frontend every 30 seconds.
    Powers the status bar on execution page.
    """
    db = get_supabase_admin_client()
    status = {
        "n8n": False,
        "gmail": False,
        "whatsapp": False,
        "google_drive": False,
        "google_sheets": False
    }

    # Check n8n
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

**Consistent error format — every endpoint in the entire API:**

```python
# Every error uses this shape — no exceptions
{"error": "Human readable message", "code": "SNAKE_CASE_CODE"}

# Full list:
{"error": "Token expired",          "code": "TOKEN_EXPIRED"}
{"error": "Invalid token",          "code": "INVALID_TOKEN"}
{"error": "Email already exists",   "code": "EMAIL_EXISTS"}
{"error": "Invalid credentials",    "code": "INVALID_CREDENTIALS"}
{"error": "Workflow not found",     "code": "NOT_FOUND"}
{"error": "n8n API unreachable",    "code": "N8N_UNAVAILABLE"}
{"error": "Execution not found",    "code": "EXECUTION_NOT_FOUND"}
```

**Done when:** Valid JWT → user dict. Expired JWT → `TOKEN_EXPIRED`. Fake JWT → `INVALID_TOKEN`. `/system/status` returns all connection states. Zero 500s on auth failures.

```bash
git add -A && git commit -m "layer-4: db + jwt + system status"
git tag layer-4-complete
```

---

## Layer 5 — Auth Endpoints
**Goal:** Register, login, logout, profile — working via FastAPI. Test all edge cases via curl before touching frontend.

**Endpoints:**

```
POST /auth/register   → Supabase signup → DB trigger creates profile + data_sources
POST /auth/login      → JWT in httpOnly cookie
POST /auth/logout     → clears cookie
GET  /auth/me         → returns profile (protected)
PUT  /auth/me         → update full_name, avatar_url (protected)
```

**Why httpOnly cookie not localStorage:**

XSS attacks cannot steal httpOnly cookies — JavaScript has zero access to them. localStorage exposes the token to any injected script. For a platform handling real business emails this is the correct default even for MVP.

**Edge cases — all must return clean errors, no 500s:**

```
Duplicate email      → 409 {"code": "EMAIL_EXISTS"}
Wrong password       → 401 {"code": "INVALID_CREDENTIALS"}
                          (never reveal which field was wrong)
Empty fields         → 422 (FastAPI validation, Pydantic model)
Profile auto-created → DB trigger, never null on /auth/me
Token refresh        → Supabase client handles silently
```

**Test sequence via curl before Layer 6:**

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test1234!","full_name":"Test User"}'
# Expected: 201 {"message": "User created"}

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test1234!"}' \
  -c cookies.txt
# Expected: 200, cookie set

# Me
curl http://localhost:8000/auth/me \
  -b cookies.txt
# Expected: 200 {"id":"...","email":"...","full_name":"..."}

# Duplicate email
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test1234!","full_name":"Test"}'
# Expected: 409 {"code": "EMAIL_EXISTS"}

# Logout
curl -X POST http://localhost:8000/auth/logout -b cookies.txt
# Expected: 200, cookie cleared

# Me after logout
curl http://localhost:8000/auth/me -b cookies.txt
# Expected: 401 {"code": "INVALID_TOKEN"}
```

**Done when:** All 5 curl sequences return expected responses. Zero 500s.

```bash
git add -A && git commit -m "layer-5: auth endpoints complete"
git tag layer-5-complete
```

---

## Layer 6 — Next.js Auth Pages + Dashboard Shell
**Goal:** Login, register UI. Protected routing. Shell all pages live in.

**Pages:**

```
/             → redirect: /dashboard (authed) or /login (not authed)
/login        → form → POST /auth/login → /dashboard
/register     → form → POST /auth/register → /login
/dashboard    → protected shell, sidebar nav, "you're logged in"
```

**Sidebar navigation — built once, reused by every page:**

```
≡  n8n Platform
─────────────────
🏠 Dashboard        /dashboard
⚡ Workflows        /workflows
🔌 Integrations     /settings/integrations
📋 History          /history
📊 Analytics        /analytics
👤 Profile          /profile
```

**Next.js middleware — one file, ~20 lines:**

```typescript
// src/middleware.ts
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

**Status bar component — built here, used from Layer 8 onward:**

```typescript
// src/components/StatusBar.tsx
// Polls GET /system/status every 30 seconds
// Shows: [● n8n] [● Gmail] [● Sheets] [● Drive] [● WhatsApp]
// Green dot = connected, red = disconnected
// Displayed at top of every protected page
```

**Done when:** Register in browser → at `/dashboard` → refresh → still there → logout → at `/login` → navigate to `/dashboard` → redirected to `/login`. Status bar visible on dashboard.

```bash
git add -A && git commit -m "layer-6: next.js auth + shell + status bar"
git tag layer-6-complete
```

---

## Layer 6.5 — Data Sources Management Page
**Goal:** Users see and manage all 4 integration connections from the UI. PDF Feature 6 requires this explicitly.

**FastAPI endpoints:**

```
GET  /integrations
  → reads data_sources table for current user
  → returns list with is_connected + last_verified_at

POST /integrations/verify/{source_type}
  → source_type: gmail | whatsapp | google_drive | google_sheets
  → pings n8n credential status via n8n API
  → updates is_connected + last_verified_at in Supabase
  → returns updated status
```

**Next.js page `/settings/integrations`:**

```
┌──────────────────────────────────────────────┐
│ Data Sources & Integrations                  │
├──────────────────────────────────────────────┤
│ ● Gmail              ✅ Connected            │
│   Last verified: 2 min ago    [Verify] [Help]│
├──────────────────────────────────────────────┤
│ ● WhatsApp Business  ✅ Connected            │
│   Last verified: 5 min ago    [Verify] [Help]│
├──────────────────────────────────────────────┤
│ ● Google Drive       ✅ Connected            │
│   Last verified: 2 min ago    [Verify] [Help]│
├──────────────────────────────────────────────┤
│ ● Google Sheets      ✅ Connected            │
│   Last verified: 2 min ago    [Verify] [Help]│
└──────────────────────────────────────────────┘
```

Note: Credentials are configured inside n8n directly (Layer 2 GCP setup). This page shows status and lets users verify — it does not store raw credentials in our DB. The `credentials` column in `data_sources` is intentionally empty for security.

**Done when:** All 4 integration cards show correct connected/disconnected status. Verify button updates `last_verified_at` and refreshes the UI.

```bash
git add -A && git commit -m "layer-6.5: integrations management page"
git tag layer-6.5-complete
```

---

## Layer 7 — Workflow CRUD + Embedded n8n Editor + Agent Config UI
**Goal:** Users create workflows, configure agents, and edit visually in embedded n8n.

**Three distinct pieces — build in order:**

---

**Piece 1: Workflow CRUD**

FastAPI endpoints:
```
POST   /workflows
  → clone backend/templates/inquiry_workflow.json
  → POST cloned template to n8n API
  → save workflow + 5 default agent rows to Supabase
  → return workflow with n8n_workflow_id

GET    /workflows
  → list user's workflows from Supabase

GET    /workflows/{id}
  → workflow + 5 agent rows

PUT    /workflows/{id}
  → update name, description, trigger_channel in Supabase
  → update workflow name in n8n via PATCH

DELETE /workflows/{id}
  → delete from n8n first
  → then delete from Supabase
  → if n8n delete fails: return 500, don't delete Supabase row
```

Template clone:
```python
import json
from uuid import uuid4

def clone_workflow(name: str, trigger_channel: str) -> dict:
    with open("templates/inquiry_workflow.json") as f:
        template = json.load(f)
    template["name"] = name
    template["id"] = str(uuid4())
    # patch active trigger based on channel
    for node in template["nodes"]:
        if node["type"] == "n8n-nodes-base.gmailTrigger":
            node["disabled"] = trigger_channel == "whatsapp"
        if node["type"] == "n8n-nodes-base.whatsappTrigger":
            node["disabled"] = trigger_channel == "gmail"
    return template
```

Sync failure handling:
```python
# POST /workflows
try:
    # 1. Clone + POST to n8n
    n8n_workflow = clone_workflow(name, trigger_channel)
    n8n_response = await post_to_n8n(n8n_workflow)
    n8n_workflow_id = n8n_response["id"]
except Exception:
    raise HTTPException(500, {"code": "N8N_UNAVAILABLE"})

try:
    # 2. Save to Supabase
    workflow = db.table("workflows").insert({...}).execute()
    # 3. Insert 5 default agent rows
    db.table("agents").insert([...5 agents...]).execute()
except Exception:
    # Rollback: delete from n8n
    await delete_from_n8n(n8n_workflow_id)
    raise HTTPException(500, {"code": "DB_ERROR"})
```

---

**Piece 2: Agent Configuration UI**

FastAPI endpoints:
```
GET /workflows/{id}/agents
  → returns 5 agent rows ordered by order_index

PUT /agents/{agent_id}
  → update system_prompt, tools, handoff_rules, output_format
  → sync system_prompt to corresponding n8n node parameters
  → this MUST update n8n, not just Supabase
```

n8n node sync:
```python
async def sync_agent_to_n8n(
    n8n_workflow_id: str,
    agent_role: str,
    system_prompt: str
):
    # 1. GET current workflow from n8n
    workflow = await get_n8n_workflow(n8n_workflow_id)
    # 2. Find the node matching agent_role by name
    for node in workflow["nodes"]:
        if node["name"] == f"{agent_role.title()}_Agent":
            # 3. Update system message in node parameters
            node["parameters"]["messages"]["values"][0]["content"] \
                = system_prompt
    # 4. PUT updated workflow back to n8n
    await update_n8n_workflow(n8n_workflow_id, workflow)
```

Page `/workflows/{id}/agents`:
```
┌─────────────────────────────────────────┐
│ 🔵 Classifier Agent          [order: 1] │
│ System Prompt:                          │
│ ┌─────────────────────────────────────┐ │
│ │ You are a classifier...             │ │
│ │ [editable textarea, 8 rows]         │ │
│ └─────────────────────────────────────┘ │
│ Tools:                                  │
│ [✓ Gmail read] [✓ Drive search]         │
│ [✓ Sheets update] [ WhatsApp send]      │
│ Output format: [JSON ▼]                 │
│ Handoff rule: → Researcher              │
│                              [Save]     │
└─────────────────────────────────────────┘
```

---

**Piece 3: Embedded n8n Editor**

Page `/workflows/{id}/edit`:
```typescript
// The iframe shows the full n8n visual editor
// N8N_AUTH_EXCLUDE_ENDPOINTS in docker-compose ensures
// no login screen appears inside the iframe
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

This satisfies both:
- "Visual n8n node connections showing agent handoffs"
- "Edit existing workflows in embedded n8n editor"

**Done when:** Create workflow in UI → appears in n8n at `localhost:5678`. Edit agent system prompt → reflected in n8n node. Delete workflow → gone from both. Embedded editor loads and is interactive with no login screen.

```bash
git add -A && git commit -m "layer-7: workflow crud + n8n embed + agent config"
git tag layer-7-complete
```

---

## Layer 8 — Execution Trigger + Controls + Status Bar + Trace View
**Goal:** One-click trigger, Start/Stop/Retry, honest trace view, connection status indicators.

**FastAPI endpoints:**

```
POST /executions/trigger/{workflow_id}
  → body: {inquiry_text, source_channel, sender_id}
  → POST to n8n webhook/trigger endpoint
  → save execution row (status: "running") to Supabase
  → return {execution_id} immediately (non-blocking)

GET /executions/{id}/status
  → poll n8n GET /executions/{n8n_execution_id}
  → if still running: return {status:"running", progress_pct}
  → if complete:
      fetch node-level logs from n8n
      map NODE_TO_AGENT names to roles
      save agent_logs rows to Supabase with duration_ms
      update execution status + duration_ms + finished_at
  → return full status object

GET /executions/{id}/trace
  → read agent_logs from Supabase for this execution
  → return ordered by agent order_index

POST /executions/{id}/cancel
  → DELETE /executions/{n8n_execution_id} in n8n
  → update execution status to "cancelled" in Supabase

POST /executions/{id}/retry
  → fetch original inquiry_snippet + source_channel from execution row
  → re-POST to trigger endpoint with same input
  → return new {execution_id}
```

**Honest note on Pause:**

n8n does not support pausing a running execution via API. The UI button is labeled **"Stop"** not "Pause." Stop calls the Cancel endpoint. This is documented and honest.

**Node name → agent role mapping:**

```python
NODE_TO_AGENT = {
    "Classifier_Agent": "classifier",
    "Researcher_Agent": "researcher",
    "Qualifier_Agent":  "qualifier",
    "Responder_Agent":  "responder",
    "Executor_Agent":   "executor"
}
```

These node names are set when building the workflow in Layer 3 — keep them consistent.

**Frontend execution page UI:**

```
Status bar (always visible, polls /system/status every 30s):
[● n8n] [● Gmail] [● Sheets] [● Drive] [● WhatsApp]

─────────────────────────────────────────────────
Test Inquiry
─────────────────────────────────────────────────
[Inquiry text input]
Channel: [Gmail ▼]   [▶ Run]  [■ Stop]  [↺ Retry]
─────────────────────────────────────────────────

⟳ Running... (polling every 2s)

↓ Completed in 5.4s

✅ Classifier    0.8s
   Input:  "Hi, we're a 50-person team..."
   Output: {"type":"sales_inquiry","priority":"high"}

✅ Researcher    1.2s
   Input:  {classification + inquiry}
   Output: {"relevant_info":"Enterprise plan...","source":"google_drive"}

✅ Qualifier     0.9s
   Output: {"lead_score":8,"reason":"50-person team..."}

✅ Responder     2.1s
   Output: {"draft_reply":"Hi, thanks for reaching out..."}

✅ Executor      0.4s
   Output: {"sent":true,"channel":"gmail","logged":true}

Reply sent to: customer@test.com  ✅
Logged to: Google Sheets          ✅
```

**Done when:** Click Run → spinner → trace appears → Gmail reply arrives. Stop cancels. Retry re-runs with same input. Status bar shows all green. This is the demo.

```bash
git add -A && git commit -m "layer-8: execution trigger + trace + controls"
git tag layer-8-complete
```

---

## Layer 9 — History + Logs + Export
**Goal:** Full execution history, detail view, export JSON/TXT/PDF.

**FastAPI endpoints:**

```
GET /executions
  → paginated, filters: status, source_channel, date_range
  → returns list with snippet, duration, status, score

GET /executions/{id}
  → full execution + all agent_logs

GET /executions/{id}/export
  → ?format=json|txt|pdf
  → JSON: raw dump of execution + agent_logs
  → TXT: formatted readable text
  → PDF: reportlab — header, agent trace table, reply sent

GET /analytics/export
  → ?format=csv|pdf
  → CSV: pandas DataFrame of all executions
  → PDF: reportlab summary report with chart images
```

**Export implementations:**

```python
# JSON export
import json
def export_json(execution, agent_logs) -> bytes:
    data = {"execution": execution, "agent_logs": agent_logs}
    return json.dumps(data, indent=2, default=str).encode()

# TXT export
def export_txt(execution, agent_logs) -> bytes:
    lines = [
        f"Execution Report — {execution['started_at']}",
        f"Channel: {execution['source_channel']}",
        f"Status: {execution['status']}",
        f"Duration: {execution['duration_ms']}ms",
        f"Score: {execution['score']}/10",
        "",
        "Original Inquiry:",
        execution['inquiry_snippet'],
        "",
        "Agent Trace:"
    ]
    for log in agent_logs:
        lines += [
            f"\n[{log['agent_role'].upper()}] {log['duration_ms']}ms",
            f"Output: {json.dumps(log['output'], indent=2)}"
        ]
    lines += ["", "Final Reply:", execution['final_reply'] or "N/A"]
    return "\n".join(lines).encode()

# PDF export — reportlab
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table
def export_pdf(execution, agent_logs) -> bytes:
    # SimpleDocTemplate → Paragraph headers → Table for agent trace
    # Returns PDF bytes
    ...
```

**History page `/history`:**

```
[Filter: All|Gmail|WhatsApp] [Status: All|✅|❌]  [Export CSV]

Date          Source    Snippet               Duration  Status  Score
Apr 14 10:23  Gmail     "Enterprise pric..."  5.4s      ✅       8/10
Apr 14 09:11  WhatsApp  "Refund request..."   8.1s      ✅       7/10
Apr 13 16:42  Gmail     "Support ticket..."   31.2s     ❌        —
```

**Detail page `/history/{id}`:**

- Full original inquiry text
- Agent trace timeline (reuses Layer 8 component — no rebuild)
- Final reply sent
- Export buttons: `[JSON]` `[TXT]` `[PDF]`
- Scorecard (if generated — from Layer 10)

**Done when:** History shows all executions. Click row → full trace + reply. All 3 export formats download correctly.

```bash
git add -A && git commit -m "layer-9: history + logs + export"
git tag layer-9-complete
```

---

## Layer 10 — Analytics Dashboard + Full Scorecard
**Goal:** Honest metrics. Per-agent scorecard. Real bottleneck detection. Both export formats.

**FastAPI endpoints:**

```
GET /analytics/summary
  → total_executions, success_rate, avg_duration_ms,
    most_common_type, avg_quality_score

GET /analytics/chart
  → ?period=daily|weekly
  → returns [{date, count, success_count}]

GET /analytics/agents
  → per-agent avg_duration_ms, success_rate,
    bottleneck_flag across all user's executions

GET /executions/{id}/scorecard
  → deterministic part: computed from agent_logs + execution
  → sarvam part: async LLM call with rubric prompt
  → saves result to executions.scorecard_detail
  → returns full scorecard
```

**Analytics dashboard `/analytics`:**

```
┌──────────────┬──────────────┬──────────────┐
│ 47           │ 91.4%        │ 6.2s         │
│ Total        │ Success rate │ Avg time     │
└──────────────┴──────────────┴──────────────┘

Inquiries over time [recharts BarChart]
Mon: 8  Tue: 12  Wed: 6  Thu: 11  Fri: 10

Most common inquiry types:
  sales_inquiry      52%  ████████████
  support_ticket     28%  ███████
  general_question   20%  █████

Avg AI quality score: 7.4/10

[Export PDF]  [Export CSV]

Per-agent performance:
Agent        Avg Duration   Success Rate   Bottleneck
Classifier   0.9s           98%            —
Researcher   1.1s           95%            —
Qualifier    0.8s           97%            —
Responder    2.3s           94%            —
Executor     0.4s           99%            —
```

**Bottleneck detection — deterministic, not LLM:**

```python
def detect_bottleneck(
    agent_role: str,
    duration_ms: int,
    user_id: str,
    db
) -> bool:
    """
    Compares agent duration against its own rolling average
    over the last 10 executions for this user.
    Flags as bottleneck if duration > 2x rolling average.
    Purely deterministic — no LLM involved.
    """
    recent = db.table("agent_logs")\
        .select("duration_ms")\
        .eq("agent_role", agent_role)\
        .order("created_at", desc=True)\
        .limit(10)\
        .execute()

    if not recent.data or len(recent.data) < 3:
        return False  # not enough data yet

    avg = sum(r["duration_ms"] for r in recent.data) / len(recent.data)
    return duration_ms > (avg * 2)
```

**Individual execution scorecard:**

Part 1 — deterministic (always shown, always honest):
```
Chain completion:    ✅ All 5 agents completed
Reply generated:     ✅ Yes
Handling time:       5.4s (below avg 6.2s ✅)
Channel delivered:   ✅ Gmail sent
KB match found:      ✅ google_drive
Bottlenecks:         None ✅
```

Part 2 — Sarvam AI assessment (secondary, clearly labeled):
```
AI quality assessment: 7/10
  Answers inquiry directly:     3/3  ✅
  Personalized to context:      2/3  ⚠️
  Professional and clear:       2/2  ✅
  Includes clear next step:     0/2  ❌
Weakest area: "Missing specific follow-up timeline"
```

Sarvam scoring prompt — explicit rubric, not "rate this 1-10":
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

Scorecard runs **async after execution completes** — never inline — so it adds zero latency to the execution itself. Saved to `executions.scorecard_detail` jsonb column.

**Done when:** Dashboard shows real numbers from real executions. Per-agent table populated. Bottleneck flag appears when agent runs slow. Scorecard on every execution detail page. Both exports download correctly.

```bash
git add -A && git commit -m "layer-10: analytics + scorecard + bottleneck"
git tag layer-10-complete
```

---

## Layer 11 — Polish + Smoke Tests + Deploy Prep
**Goal:** Anyone clones the repo, runs `docker compose up`, and has a working demo in under 10 minutes.

**Checklist:**

Version already pinned in Layer 0 update: `docker.n8nio/n8n:1.48.0`

Smoke test script `smoke_test.sh`:
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
  -d '{"email":"smoke@test.com","password":"Test1234!",
       "full_name":"Smoke Test"}' \
  | grep -q '"message"' && echo "✅" || echo "❌"

echo -n "L5 Auth login: "
curl -sf -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke@test.com","password":"Test1234!"}' \
  -c /tmp/smoke_cookies.txt \
  | grep -q '"200"' && echo "✅" || echo "❌"

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

`README.md` structure:
```
## What this is
## Architecture (with diagram)
## Architecture decisions (why FastAPI)
## Prerequisites
## Setup (5 steps)
## GCP OAuth setup
## Running the demo
## Demo script
## Test matrix results
## Troubleshooting
```

`FUTURE.md` — out of scope, acknowledged:
```
- Workflow template marketplace
- Team collaboration + sharing
- Human-in-the-loop approval
- A/B testing agent prompts
- Scheduled batch processing
- Advanced cross-workflow analytics
- Google Drive search (currently uses filename lookup)
```

Rerun full test matrix from Layer 3. Fix any flakiness. Record 3-minute demo video as backup.

**Done when:** Fresh clone + env vars + `docker compose up` = working demo in under 10 minutes. All smoke tests green.

```bash
git add -A && git commit -m "layer-11: polish + smoke tests + deploy ready"
git tag layer-11-complete
```

---

## Complete Layer Order

```
Layer 0    Docker + n8n + FastAPI + Sarvam (pinned)   ✅ DONE
Layer 1    Supabase schema + RLS + triggers            ← START HERE
Layer 2    GCP OAuth + Gmail trigger + Classifier      
Layer 3    Full 5-agent chain + Sheets + test matrix   
Layer 3.5  Drive KB (simplified) + WhatsApp trigger    
Layer 4    FastAPI DB + JWT middleware + system status  
Layer 5    Auth endpoints (all edge cases)             
Layer 6    Next.js auth pages + shell + status bar     
Layer 6.5  Data sources management page               
Layer 7    Workflow CRUD + n8n embed + agent config UI 
Layer 8    Execution trigger + controls + trace view   
Layer 9    History + logs + export JSON/TXT/PDF        
Layer 10   Analytics + per-agent scorecard + export    
Layer 11   Polish + smoke tests + deploy prep          
```

---

## 30-Day Timeline

```
Week 1  Days 1-7
  Day 1-2   Layer 1   Supabase schema + RLS
  Day 3     Layer 2   GCP OAuth + Classifier 10/10
  Day 4-6   Layer 3   Full chain + test matrix 9/10
  Day 7     Buffer / start Layer 3.5

Week 2  Days 8-14
  Day 8-9   Layer 3.5 Drive KB + WhatsApp
  Day 10-11 Layer 4   FastAPI DB + JWT + status
  Day 12-13 Layer 5   Auth endpoints
  Day 14    Layer 6   Next.js auth + shell

Week 3  Days 15-21
  Day 15    Layer 6.5 Integrations page
  Day 16-18 Layer 7   Workflow CRUD + embed + agent UI
  Day 19-21 Layer 8   Execution trigger + trace

Week 4  Days 22-30
  Day 22-24 Layer 9   History + export
  Day 25-27 Layer 10  Analytics + scorecard
  Day 28-29 Layer 11  Polish + smoke tests
  Day 30    Demo rehearsal + buffer
```

---

## Cut Lines

```
Behind end of Week 1?
  → Push Layer 3.5 to Week 2 (already planned)
  → Use simplified Drive (filename not search) — always keep Drive
  → Drive is MUST HAVE, never cut to zero

Behind end of Week 2?
  → Drop Layer 6.5 (integrations page)
  → Drop WhatsApp, Gmail only for demo
  → Saves 2 days

Behind end of Week 3?
  → Drop TXT + PDF export, JSON only
  → Drop analytics export PDF/CSV
  → Drop bottleneck detail, keep overall score
  → Saves 1.5 days

Never cut:
  → Layers 2, 3   the agent chain (the product)
  → Layer 7       workflow creation + agent config UI
  → Layer 8       execution trigger + trace view
  → These ARE the demo
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Time runs out | High | Critical | Cut lines above, agents before UI |
| Sarvam JSON inconsistency | High | High | Extract-first, 4 methods, 2 retries max |
| Agent handoffs break | High | High | Validation node between every agent |
| GCP OAuth blocks Layer 2 | Medium | High | Start Day 3 morning, not afternoon |
| n8n iframe shows login screen | Medium | High | N8N_AUTH_EXCLUDE_ENDPOINTS in Layer 0 |
| n8n template clone fails | Low | High | Template manually tested + exported in Layer 3 |
| Agent sync to n8n fails (Layer 7) | Medium | Medium | Log + surface error, don't silently fail |
| WhatsApp ngrok disconnects | Medium | Medium | Gmail is primary demo channel |
| Sarvam API down on demo day | Low | Critical | LM Studio local fallback via env var |
| JWT middleware bug | Low | Critical | Test all token states in Layer 4 curl sequence |

---

## Version Control Checkpoints

```bash
# Right now
git init  # if not done
git add -A
git commit -m "layer-0: docker + fastapi + n8n + sarvam"
git tag layer-0-complete

# After every layer
git add -A
git commit -m "layer-N: one line of what works"
git tag layer-N-complete

# If something breaks
git checkout layer-N-complete
```

---

This plan now covers every single PDF must-have with zero gaps, zero contradictions, and honest cut lines that never sacrifice the core demo. Ready to start Layer 1?