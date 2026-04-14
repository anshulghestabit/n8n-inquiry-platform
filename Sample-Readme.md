# n8n Multi-Agent Customer Inquiry Automation Platform

> An intelligent automation platform that processes customer inquiries from Gmail and WhatsApp using a 5-agent AI pipeline — classifying, researching, qualifying, responding, and executing — all orchestrated through n8n with a full-stack web interface.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Component Model](#component-model)
4. [Core Design Decisions](#core-design-decisions)
5. [Runtime Flow](#runtime-flow)
6. [Data Flow](#data-flow)
7. [Database Schema](#database-schema)
8. [Agent Pipeline](#agent-pipeline)
9. [API Structure](#api-structure)
10. [Tech Stack](#tech-stack)
11. [Prerequisites](#prerequisites)
12. [Setup](#setup)
13. [GCP OAuth Setup](#gcp-oauth-setup)
14. [Running the Demo](#running-the-demo)
15. [Demo Script](#demo-script)
16. [Architecture Decisions](#architecture-decisions)
17. [Future Work](#future-work)

---

## Project Overview

Small teams waste hours manually checking Gmail and WhatsApp, searching Drive for answers, and updating Sheets — leading to slow replies and lost opportunities. This platform automates that entire workflow.

A user signs up, creates a multi-agent workflow, connects their Gmail and Google Drive, and from that point every incoming customer inquiry is automatically classified, researched, qualified, replied to, and logged — without any manual intervention.

**The 5 agents:**

| Agent | Role |
|---|---|
| Classifier | Identifies inquiry type and priority |
| Researcher | Looks up relevant info from Google Drive KB |
| Qualifier | Scores the lead or request 1–10 |
| Responder | Drafts a personalized reply |
| Executor | Sends the reply and logs to Sheets |

---

## High-Level Architecture

```mermaid
graph TB
    subgraph Input["Input Channels"]
        Gmail["Gmail"]
        WhatsApp["WhatsApp Business"]
    end

    subgraph Platform["Platform — localhost"]
        subgraph UI["Next.js Frontend :3000"]
            Auth["Auth pages"]
            WFBuilder["Workflow builder"]
            ExecMonitor["Execution monitor"]
            History["History & logs"]
            Analytics["Analytics & scorecard"]
        end

        subgraph API["FastAPI Backend :8000"]
            AuthAPI["Auth endpoints"]
            WorkflowAPI["Workflow CRUD"]
            ExecAPI["Execution API"]
            AnalyticsAPI["Analytics API"]
            ExportAPI["Export PDF/CSV"]
        end

        subgraph Automation["n8n Workflow Engine :5678"]
            Trigger["Trigger node"]
            Agents["5-agent chain"]
            Validator["Validation nodes"]
            Sender["Send & log nodes"]
        end

        subgraph DB["Supabase"]
            AuthDB["auth.users"]
            ProfilesDB["profiles"]
            WorkflowsDB["workflows"]
            AgentsDB["agents"]
            ExecutionsDB["executions"]
            LogsDB["agent_logs"]
            SourcesDB["data_sources"]
        end
    end

    subgraph External["External Services"]
        Sarvam["Sarvam AI API"]
        LMStudio["LM Studio (local fallback)"]
        Drive["Google Drive KB"]
        Sheets["Google Sheets log"]
    end

    Gmail -->|new email| Trigger
    WhatsApp -->|new message| Trigger
    UI <-->|HTTP + cookies| API
    API <-->|REST API + JWT| Automation
    API <-->|service role| DB
    Automation <-->|HTTP Request| Sarvam
    Automation <-->|env var switch| LMStudio
    Automation <-->|OAuth2| Drive
    Automation <-->|OAuth2| Sheets
    Automation -->|reply| Gmail
    Automation -->|reply| WhatsApp
```

---

## Component Model

```mermaid
graph LR
    subgraph Frontend["Next.js — src/"]
        MW["middleware.ts\nroute protection"]
        AuthPages["(auth)/\nlogin, register"]
        DashPages["(dashboard)/\nworkflows, history\nanalytics, integrations"]
        Components["components/\nStatusBar\nTraceView\nAgentCard\nScorecard"]
        LibNext["lib/\napi client\nauth context"]
    end

    subgraph Backend["FastAPI — app/"]
        CoreMod["core/\nconfig.py\nllm.py"]
        APIRoutes["api/\nauth.py\nworkflows.py\nexecutions.py\nanalytics.py\nsystem.py"]
        DBMod["db/\nclient.py\nmodels.py"]
        Middleware["middleware/\nauth.py (JWT)"]
        Templates["templates/\ninquiry_workflow.json"]
        ExportMod["export/\npdf.py\ncsv.py\ntxt.py"]
    end

    subgraph N8N["n8n Workflow"]
        TriggerNode["Gmail Trigger\nWhatsApp Trigger"]
        NormalizeNode["Set node\nnormalize input"]
        AgentNodes["5 HTTP Request nodes\none per agent"]
        CodeNodes["5 Code nodes\nJSON extraction"]
        IFNodes["5 IF nodes\nvalidation routing"]
        SendNodes["Gmail Send\nWhatsApp Send"]
        SheetsNode["Google Sheets\nAppend Row"]
    end

    Frontend <--> Backend
    Backend <--> N8N
    Backend <--> DB["Supabase DB"]
    N8N <--> LLM["Sarvam / LM Studio"]
    N8N <--> Google["Google APIs\nDrive, Sheets, Gmail"]
```

---

## Core Design Decisions

```mermaid
mindmap
  root((Design decisions))
    FastAPI as backend
      Python-native PDF/CSV export
      Independent service boundary
      JWT verification separate from UI
      Evaluator signal: Python backend competence
    n8n for agent orchestration
      Visual workflow = part of the UI
      Built-in Google OAuth nodes
      No custom agent framework needed
      iframe embed satisfies PDF requirement
    Supabase for auth and DB
      JWT issued by Supabase verified by FastAPI
      RLS on every table
      Auto-profile trigger on signup
      Free tier sufficient for MVP
    Sarvam AI as primary LLM
      OpenAI-compatible endpoint
      Indian language support
      Free tier available
      LM Studio as local fallback via env var
    Template clone over programmatic generation
      n8n workflow JSON is complex
      One wrong node ID breaks silently
      Build once manually, clone and patch name
      Eliminates entire class of bugs
    Extract-first JSON validation
      Retry with stricter prompt almost always also fails
      4-method extraction catches 95% of issues
      Only retry if all 4 methods fail
      Max 2 retries to cap latency
    httpOnly cookies for JWT storage
      XSS attacks cannot steal httpOnly cookies
      localStorage exposes token to injected scripts
      Correct default for platform handling real emails
    Simplified Drive integration
      Drive search API adds complexity
      Filename lookup covers MVP requirement
      Same GCP credential as Gmail and Sheets
      Upgradeable to search post-MVP
```

---

## Runtime Flow

### Authentication flow

```mermaid
sequenceDiagram
    actor User
    participant UI as Next.js UI
    participant API as FastAPI
    participant Supa as Supabase Auth
    participant DB as Supabase DB

    User->>UI: POST /register {email, password, name}
    UI->>API: POST /auth/register
    API->>Supa: create_user(email, password)
    Supa-->>DB: trigger: INSERT profiles + 4 data_sources rows
    Supa-->>API: user created
    API-->>UI: 201 {message: "User created"}

    User->>UI: POST /login {email, password}
    UI->>API: POST /auth/login
    API->>Supa: sign_in(email, password)
    Supa-->>API: JWT token
    API-->>UI: 200 + Set-Cookie: auth-token (httpOnly)

    User->>UI: GET /dashboard
    UI->>API: GET /auth/me (cookie)
    API->>API: decode JWT (SUPABASE_JWT_SECRET)
    API->>DB: SELECT profiles WHERE id = user_id
    DB-->>API: profile row
    API-->>UI: 200 {id, email, full_name}
    UI-->>User: dashboard rendered
```

### Workflow creation flow

```mermaid
sequenceDiagram
    actor User
    participant UI as Next.js UI
    participant API as FastAPI
    participant N8N as n8n API
    participant DB as Supabase DB

    User->>UI: create workflow {name, trigger_channel}
    UI->>API: POST /workflows
    API->>API: load inquiry_workflow.json template
    API->>API: clone: patch name + id + disable inactive trigger
    API->>N8N: POST /api/v1/workflows {cloned JSON}
    N8N-->>API: {id: n8n_workflow_id}

    alt n8n fails
        API-->>UI: 500 {code: N8N_UNAVAILABLE}
    else n8n succeeds
        API->>DB: INSERT workflows {name, n8n_workflow_id, ...}
        API->>DB: INSERT agents x5 {default prompts, order_index}

        alt DB fails
            API->>N8N: DELETE /api/v1/workflows/{id}
            API-->>UI: 500 {code: DB_ERROR}
        else both succeed
            API-->>UI: 201 {workflow with agents}
            UI-->>User: workflow appears in list
        end
    end
```

### Execution flow (the demo)

```mermaid
sequenceDiagram
    actor User
    participant UI as Next.js UI
    participant API as FastAPI
    participant N8N as n8n
    participant Sarvam as Sarvam AI
    participant Drive as Google Drive
    participant Gmail as Gmail
    participant Sheets as Google Sheets
    participant DB as Supabase DB

    User->>UI: click Run Test Inquiry
    UI->>API: POST /executions/trigger/{workflow_id}
    API->>N8N: POST /api/v1/workflows/{id}/run
    N8N-->>API: {executionId}
    API->>DB: INSERT executions {status: running}
    API-->>UI: {execution_id}
    UI->>UI: start polling /executions/{id}/status every 2s

    N8N->>Sarvam: Classifier prompt + inquiry
    Sarvam-->>N8N: raw LLM response
    N8N->>N8N: Code node: extract JSON (4 methods)
    N8N->>N8N: IF node: extraction ok?

    N8N->>Drive: download {type}.txt from /KnowledgeBase/
    Drive-->>N8N: file content
    N8N->>Sarvam: Researcher prompt + drive content
    Sarvam-->>N8N: research JSON

    N8N->>Sarvam: Qualifier prompt + classification + research
    Sarvam-->>N8N: qualification JSON

    N8N->>Sarvam: Responder prompt + all context
    Sarvam-->>N8N: draft reply JSON

    N8N->>Gmail: Send reply to original thread
    Gmail-->>N8N: sent confirmation
    N8N->>Sheets: Append Row {execution log}
    Sheets-->>N8N: appended

    UI->>API: GET /executions/{id}/status
    API->>N8N: GET /executions/{n8n_id}
    N8N-->>API: {status: success, data: node logs}
    API->>API: map node names to agent roles
    API->>DB: INSERT agent_logs x5 {input, output, duration_ms}
    API->>DB: UPDATE executions {status: success, duration_ms}
    API-->>UI: {status: success, trace: [...]}
    UI-->>User: full agent trace rendered

    Note over API,DB: async after execution
    API->>Sarvam: scorecard rubric prompt
    Sarvam-->>API: {total: 7, criteria: {...}}
    API->>DB: UPDATE executions {score: 7, scorecard_detail: {...}}
```

---

## Data Flow

### Input normalization

```mermaid
flowchart TD
    Gmail["Gmail Trigger\nnew unread email"]
    WhatsApp["WhatsApp Trigger\nnew message"]
    Normalize["Set node\nnormalize input shape"]
    SharedState["Shared state object\noriginal_inquiry\nsender_id\nmessage_id\nsource_channel\nclassification\nresearch\nqualification\ndraft_reply\nexecution_meta"]

    Gmail -->|"from, subject, body,\nmessage_id"| Normalize
    WhatsApp -->|"contacts[0].wa_id,\nmessages[0].text.body"| Normalize
    Normalize --> SharedState
    SharedState --> Chain["5-agent chain"]
```

### JSON validation between agents

```mermaid
flowchart LR
    Agent["Agent\nHTTP Request\nto Sarvam"]
    Code["Code node\nJSON extraction\n4 methods"]
    IF{"IF node\n_ok === true?"}
    Next["Next agent"]
    Retry["Retry agent\nonce"]
    Fail["Error node\nlog raw output\nfail execution"]

    Agent --> Code
    Code --> IF
    IF -->|"true"| Next
    IF -->|"false"| Retry
    Retry -->|"still false"| Fail
    Retry -->|"ok"| Next
```

### JSON extraction cascade

```mermaid
flowchart TD
    Raw["Raw LLM response string"]
    M1{"Method 1\nJSON.parse direct"}
    M2{"Method 2\nStrip code fences\nthen parse"}
    M3{"Method 3\nFind first\n{...} block"}
    M4{"Method 4\nGreedy\n{...} match"}
    Ok["parsed JSON\n_ok: true"]
    Fail["null\n_ok: false"]

    Raw --> M1
    M1 -->|"success"| Ok
    M1 -->|"fail"| M2
    M2 -->|"success"| Ok
    M2 -->|"fail"| M3
    M3 -->|"success"| Ok
    M3 -->|"fail"| M4
    M4 -->|"success"| Ok
    M4 -->|"fail"| Fail
```

### Executor output routing

```mermaid
flowchart TD
    Executor["Executor agent\ndraft_reply ready"]
    Channel{"source_channel?"}
    GmailSend["Gmail Send\nreply to message_id"]
    WASend["WhatsApp Send\nto wa_id"]
    SheetsLog["Google Sheets\nAppend Row"]
    Done["execution complete"]

    Executor --> Channel
    Channel -->|"gmail"| GmailSend
    Channel -->|"whatsapp"| WASend
    GmailSend --> SheetsLog
    WASend --> SheetsLog
    SheetsLog --> Done
```

### Analytics data flow

```mermaid
flowchart LR
    AgentLogs["agent_logs\nduration_ms per agent"]
    Executions["executions\nstatus, score, duration"]
    BottleneckDetect["Bottleneck detection\nif duration > 2x rolling avg"]
    Scorecard["Scorecard\ndeterministic part"]
    SarvamScore["Sarvam AI scoring\nasync after execution"]
    Dashboard["Analytics dashboard\ntotals, charts, per-agent"]

    AgentLogs --> BottleneckDetect
    AgentLogs --> Dashboard
    Executions --> Scorecard
    Executions --> Dashboard
    BottleneckDetect --> Scorecard
    SarvamScore --> Scorecard
    Scorecard --> Dashboard
```

---

## Database Schema

```mermaid
erDiagram
    profiles {
        uuid id PK
        string email
        string full_name
        string avatar_url
        timestamptz created_at
        timestamptz updated_at
    }

    workflows {
        uuid id PK
        uuid user_id FK
        string name
        string trigger_channel
        string status
        string n8n_workflow_id
        jsonb agent_config
        timestamptz created_at
        timestamptz updated_at
    }

    agents {
        uuid id PK
        uuid workflow_id FK
        string name
        string role
        text system_prompt
        jsonb tools
        text handoff_rules
        string output_format
        int order_index
        timestamptz created_at
    }

    executions {
        uuid id PK
        uuid workflow_id FK
        uuid user_id FK
        string n8n_execution_id
        string source_channel
        string status
        text inquiry_snippet
        string sender_id
        text final_reply
        timestamptz started_at
        timestamptz finished_at
        int duration_ms
        int score
        jsonb scorecard_detail
    }

    agent_logs {
        uuid id PK
        uuid execution_id FK
        string agent_role
        jsonb input
        jsonb output
        int duration_ms
        string status
        text error_message
        timestamptz created_at
    }

    data_sources {
        uuid id PK
        uuid user_id FK
        string source_type
        boolean is_connected
        timestamptz last_verified_at
        timestamptz created_at
    }

    profiles ||--o{ workflows : "owns"
    profiles ||--o{ executions : "owns"
    profiles ||--o{ data_sources : "owns"
    workflows ||--o{ agents : "has"
    workflows ||--o{ executions : "runs"
    executions ||--o{ agent_logs : "produces"
```

---

## Agent Pipeline

```mermaid
flowchart TD
    Input["Normalized input\noriginal_inquiry\nsource_channel\nsender_id"]

    subgraph A1["Agent 1 — Classifier"]
        C1["HTTP Request → Sarvam"]
        C2["Extract JSON"]
        C3["Validate: type, priority, confidence"]
    end

    subgraph A2["Agent 2 — Researcher"]
        R1["Google Drive: download {type}.txt"]
        R2["HTTP Request → Sarvam\nwith drive content"]
        R3["Validate: relevant_info, source"]
    end

    subgraph A3["Agent 3 — Qualifier"]
        Q1["HTTP Request → Sarvam\nwith classification + research"]
        Q2["Validate: lead_score, reason"]
    end

    subgraph A4["Agent 4 — Responder"]
        P1["HTTP Request → Sarvam\nwith all previous outputs"]
        P2["Validate: draft_reply"]
    end

    subgraph A5["Agent 5 — Executor"]
        E1["Route by source_channel"]
        E2["Send reply via Gmail or WhatsApp"]
        E3["Append row to Google Sheets"]
        E4["Validate: sent, channel, logged"]
    end

    Output["Execution complete\nreply delivered\nsheets logged"]

    Input --> A1
    A1 --> A2
    A2 --> A3
    A3 --> A4
    A4 --> A5
    A5 --> Output
```

### Agent system prompts

```mermaid
mindmap
  root((Agent prompts))
    Classifier
      Return ONLY raw JSON
      No markdown no fences
      type: 5 valid values
      priority: low medium high
      confidence: 0.0 to 1.0
    Researcher
      Given drive document content
      Extract most relevant info
      Return relevant_info + source
      Fallback if no match found
    Qualifier
      Score the lead 1 to 10
      Use classification + research
      Return lead_score + reason
      Higher score = warmer lead
    Responder
      Use all previous agent outputs
      Personalize to sender context
      Handle fallback gracefully
      Return draft_reply only
    Executor
      Route by source_channel
      Send via correct channel
      Log to sheets
      Return sent + channel + logged
```

---

## API Structure

```mermaid
graph LR
    subgraph Public["Public endpoints"]
        Register["POST /auth/register"]
        Login["POST /auth/login"]
        Health["GET /health"]
    end

    subgraph Protected["Protected endpoints (JWT required)"]
        subgraph AuthGroup["Auth"]
            Me["GET /auth/me"]
            UpdateMe["PUT /auth/me"]
            Logout["POST /auth/logout"]
        end

        subgraph WorkflowGroup["Workflows"]
            ListWF["GET /workflows"]
            CreateWF["POST /workflows"]
            GetWF["GET /workflows/{id}"]
            UpdateWF["PUT /workflows/{id}"]
            DeleteWF["DELETE /workflows/{id}"]
            ListAgents["GET /workflows/{id}/agents"]
            UpdateAgent["PUT /agents/{id}"]
        end

        subgraph ExecGroup["Executions"]
            Trigger["POST /executions/trigger/{wf_id}"]
            Status["GET /executions/{id}/status"]
            Trace["GET /executions/{id}/trace"]
            Cancel["POST /executions/{id}/cancel"]
            Retry["POST /executions/{id}/retry"]
            ExportExec["GET /executions/{id}/export"]
            Scorecard["GET /executions/{id}/scorecard"]
        end

        subgraph AnalyticsGroup["Analytics"]
            Summary["GET /analytics/summary"]
            Chart["GET /analytics/chart"]
            Agents["GET /analytics/agents"]
            ExportAnalytics["GET /analytics/export"]
        end

        subgraph SystemGroup["System"]
            SysStatus["GET /system/status"]
            Integrations["GET /integrations"]
            Verify["POST /integrations/verify/{type}"]
        end
    end
```

### Error response contract

```mermaid
flowchart LR
    Request["Any API request"]
    JWT{"JWT valid?"}
    Handler["Route handler"]
    Success["2xx + data"]
    Error["4xx/5xx\n{error: string\n code: SNAKE_CASE}"]

    Request --> JWT
    JWT -->|"invalid/expired"| Error
    JWT -->|"valid"| Handler
    Handler -->|"success"| Success
    Handler -->|"failure"| Error
```

---

## Tech Stack

```mermaid
graph TB
    subgraph FE["Frontend"]
        Next["Next.js 14\nApp Router"]
        Tailwind["Tailwind CSS"]
        Recharts["Recharts\nanalytics charts"]
        Supabase_JS["Supabase JS\nauth state"]
    end

    subgraph BE["Backend"]
        FastAPI["FastAPI\nPython 3.11"]
        Pydantic["Pydantic v2\nvalidation"]
        Jose["python-jose\nJWT decode"]
        Reportlab["reportlab\nPDF export"]
        Pandas["pandas\nCSV export"]
        HTTPX["httpx\nn8n API calls"]
        OpenAI_SDK["openai SDK\nSarvam + LM Studio"]
    end

    subgraph Automation["Automation"]
        N8N["n8n 1.48.0\nDocker"]
        Gmail_Node["Gmail node\nnative"]
        Sheets_Node["Sheets node\nnative"]
        Drive_Node["Drive node\nnative"]
        WA_Node["WhatsApp Business\nCloud node"]
    end

    subgraph Data["Data"]
        Supabase["Supabase\nPostgres + Auth + RLS"]
    end

    subgraph AI["AI"]
        Sarvam["Sarvam AI\nsarvam-30b\ncloud"]
        LMStudio["LM Studio\nlocal fallback\nenv var switch"]
    end

    subgraph Infra["Infrastructure"]
        Docker["Docker Compose\nlocal"]
        Vercel["Vercel\nfrontend deploy"]
        Railway["Railway\nbackend deploy"]
        Ngrok["ngrok\nWhatsApp webhook"]
    end

    FE <--> BE
    BE <--> Automation
    BE <--> Data
    Automation <--> AI
    Automation <--> Google["Google APIs\nOAuth2"]
```

---

## Prerequisites

- Docker + Docker Compose
- Node.js 18+ (for Next.js frontend)
- Python 3.11+ (only if running FastAPI outside Docker)
- A [Supabase](https://supabase.com) account (free tier)
- A [Sarvam AI](https://dashboard.sarvam.ai) account (free tier)
- A [Google Cloud](https://console.cloud.google.com) project with Gmail, Sheets, and Drive APIs enabled
- A [Meta Developer](https://developers.facebook.com) account (for WhatsApp — optional for basic demo)
- [ngrok](https://ngrok.com) account (for WhatsApp webhook — optional)

---

## Setup

**1. Clone and configure**

```bash
git clone https://github.com/your-org/n8n-inquiry-platform
cd n8n-inquiry-platform
cp .env.example .env
```

**2. Fill in `.env`**

```env
# LLM
LLM_PROVIDER=sarvam
SARVAM_API_KEY=your_sarvam_key
SARVAM_BASE_URL=https://api.sarvam.ai/v1
SARVAM_MODEL=sarvam-30b
LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1
LM_STUDIO_MODEL=local-model

# n8n
N8N_ENCRYPTION_KEY=your_32char_random_string
N8N_URL=http://n8n:5678
N8N_API_KEY=fill_after_first_login

# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=your_jwt_secret

# App
SECRET_KEY=your_random_secret
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000
```

**3. Start services**

```bash
docker compose up --build
```

**4. Set up n8n**

Open `http://localhost:5678`, create an owner account, then:

- Go to Settings → API → Enable API → copy key → paste into `.env` as `N8N_API_KEY`
- Run `docker compose restart backend`

**5. Run Supabase schema**

Copy and run `supabase/schema.sql` in your Supabase SQL Editor.

**6. Start frontend**

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`

---

## GCP OAuth Setup

One setup covers Gmail, Google Sheets, and Google Drive:

```
1. console.cloud.google.com → New Project → "n8n-hestabit"

2. APIs & Services → Library → Enable:
   - Gmail API
   - Google Sheets API
   - Google Drive API

3. APIs & Services → OAuth consent screen:
   - User type: External
   - App name: n8n-hestabit
   - Add your email as test user

4. APIs & Services → Credentials:
   - Create OAuth2 client → Web application
   - Authorized redirect URI:
     http://localhost:5678/rest/oauth2-credential/callback
   - Copy Client ID + Client Secret

5. In n8n (localhost:5678):
   - Settings → Credentials → New → Google OAuth2 API
   - Paste Client ID + Client Secret
   - Click "Sign in with Google"
   - This single credential works for Gmail, Sheets, and Drive nodes
```

---

## Running the Demo

**1. Create a workflow**

- Sign in at `http://localhost:3000`
- Go to Workflows → Create New
- Name: "Customer Inquiry Handler"
- Trigger: Gmail
- Click Create

**2. Configure agents (optional)**

- Click on the workflow → Agents tab
- Edit system prompts, tool selection, handoff rules per agent
- Click Save on each agent

**3. Set up Google Drive KB**

Create a folder `/KnowledgeBase/` in your Google Drive with these files:

```
sales_inquiry.txt
support_ticket.txt
complaint.txt
general_question.txt
order_request.txt
```

Each file should contain relevant answers for that inquiry type.

**4. Run a test inquiry**

- Go to Workflows → select your workflow → click Run Test Inquiry
- Enter: `"Hi, we're a 50-person team looking for enterprise pricing and a demo."`
- Channel: Gmail
- Click Run

**5. Watch the trace**

The UI polls every 2 seconds and shows each agent completing in sequence. When done, check your Gmail for the automated reply.

---

## Demo Script

The happy path this platform is built to handle reliably:

```
Input email:
  From:    customer@test.com
  Subject: Enterprise pricing inquiry
  Body:    "Hi, we're a 50-person team looking for an
            enterprise solution. Pricing and demo?"

Expected agent outputs:

Agent 1 — Classifier:
  {"type":"sales_inquiry","priority":"high","confidence":0.95}

Agent 2 — Researcher:
  {"relevant_info":"Enterprise plan: ₹X/month for 50+
   seats. Demo via Calendly.","source":"google_drive",
   "document_used":"sales_inquiry.txt"}

Agent 3 — Qualifier:
  {"lead_score":8,"reason":"50-person team with
   explicit purchase intent and demo request"}

Agent 4 — Responder:
  {"draft_reply":"Hi [name], thanks for reaching out!
   For a team of 50, our enterprise plan starts at
   ₹X/month... [personalized reply]"}

Agent 5 — Executor:
  {"sent":true,"channel":"gmail","logged":true}

Total time: under 30 seconds
Target reliability: 9/10 runs
```

### Test matrix

Run 10 test emails before demo day:

| # | Type | Classifier | Researcher | Qualifier | Responder | Executor | Gmail | Sheets | Pass |
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

Pass criteria: all 5 agents return valid JSON with correct required keys AND Gmail reply arrives AND Sheets row logged.

Target: 9/10 rows fully green before demo.

---

## Architecture Decisions

### Why FastAPI instead of Next.js API routes

FastAPI handles JWT auth, Supabase DB operations, n8n API orchestration, execution log processing, analytics aggregation, and file export via `reportlab`/`pandas`. These are Python-native operations. Putting this logic in Next.js API routes would mix Python-friendly data processing into a JS runtime. The service boundary also means the agent chain logic, DB layer, and UI are independently testable and deployable — important when debugging a 5-service system.

### Why n8n instead of a custom agent framework

n8n has native Gmail, Google Drive, Google Sheets, and WhatsApp Business Cloud nodes — each with built-in OAuth2 credential management. Building this with LangChain or a custom agent framework would mean implementing all of that from scratch. n8n also provides the embedded visual editor (via iframe) that the PDF explicitly requires, at zero additional cost.

### Why template clone instead of programmatic workflow generation

An n8n workflow JSON contains a nodes array, connections object, credential references, and metadata — all with matching UUIDs. One wrong node ID fails silently. The correct approach: build the 5-agent workflow once manually in n8n's UI, export it, store it as `backend/templates/inquiry_workflow.json`, and have FastAPI clone and patch only three fields: name, id, and active trigger node. This eliminates an entire class of hard-to-debug failures.

### Why extract-first JSON validation

If Sarvam returns malformed JSON, retrying with a "stricter" prompt almost always also fails — the problem is the model adding wrapper text, not a bad prompt. A 4-method extraction cascade (direct parse → strip fences → find first `{...}` → greedy match) catches 95%+ of malformed responses before any retry is needed. Retries are only triggered if all 4 extraction methods fail.

### Why simplified Drive integration (filename lookup not search)

The Drive search API adds a full authorization scope and a more complex n8n node configuration. Filename-based lookup — `download {inquiry_type}.txt from /KnowledgeBase/` — uses the same GCP credential already configured for Gmail and Sheets, takes one node, and covers the "automatic knowledge retrieval from Drive" requirement fully. Upgradeable to search post-MVP.

### Why Sarvam AI + LM Studio

Sarvam AI's `sarvam-30b` model is OpenAI-compatible (same SDK, same API shape), free-tier available, and optimized for Indian language context — directly relevant for customer inquiries from Indian businesses. LM Studio provides a local OpenAI-compatible server as a demo-day fallback if Sarvam is unavailable. Switching between them requires only changing the `LLM_PROVIDER` env var — no code changes.

---

## Future Work

Features explicitly out of scope for MVP, acknowledged for completeness:

- **Workflow template marketplace** — pre-built templates for common use cases
- **Team collaboration** — multi-user workspaces with shared workflows
- **Human-in-the-loop approval** — pause before sending sensitive replies
- **A/B testing agent prompts** — compare different system prompts on live traffic
- **Scheduled batch processing** — process accumulated inquiries on a schedule
- **Advanced cross-workflow analytics** — compare performance across multiple workflows
- **Google Drive search** — semantic search across the KB instead of filename lookup
- **Multi-language support** — Sarvam's Indic language capabilities fully utilized
- **Webhook triggers** — accept inquiries from any source beyond Gmail/WhatsApp

---

*Built for Hestabit internship — April 2026*