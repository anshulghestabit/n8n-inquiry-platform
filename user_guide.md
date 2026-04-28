# n8n Inquiry Platform — User Guide

Welcome! This guide walks you through setting up and using the Customer Inquiry Automation Platform — from starting Docker to sending your first automated reply.

---

## What This System Does

When a customer emails you asking about pricing, support, or orders, this platform automatically:

1. **Classifies** the inquiry type (sales, support, complaint, etc.)
2. **Researches** your knowledge base for the right answer
3. **Qualifies** the lead (how hot is this prospect?)
4. **Drafts** a personalized reply
5. **Sends** the reply and logs everything to a spreadsheet

All without you lifting a finger after initial setup.

---

## Quick Overview

```
You → Website ("Create Workflow") → Connect Gmail → Done!
                    ↓
Customer Email arrives → n8n runs 5 agents → Reply sent automatically
```

**The 5 Agents:**
- **Classifier** — "Is this a sales question?"
- **Researcher** — "What does our docs say about this?"
- **Qualifier** — "How interested is this person?"
- **Responder** — "Let's write them a nice reply"
- **Executor** — "Send it and log it"

---

## Step 1: Prepare Your Computer

### Install Prerequisites

You need 3 things on your computer:

1. **Docker Desktop** — [Download here](https://www.docker.com/products/docker-desktop)
   - Click "Download for Windows/Mac"
   - Install and start it (keep it running in background)

2. **Node.js** — [Download here](https://nodejs.org)
   - Click the LTS version (left button)
   - Install using all defaults

3. **Git** — Usually comes with your computer, or [download here](https://git-scm.com)

### Verify Installations

Open Terminal (Mac) or Command Prompt (Windows) and run:

```bash
docker --version
node --version
npm --version
```

You should see version numbers for each. If not, restart your terminal.

---

## Step 2: Get Your API Keys

### 2.1 Supabase (Free Database)

1. Go to [supabase.com](https://supabase.com) and click "Start your project"
2. Create a free account (no credit card)
3. Click "New project"
4. Fill in:
   - **Name:** inquiry-platform
   - **Database password:** Pick a strong password
   - **Region:** Closest to you (e.g., Asia Pacific - Singapore)
5. Wait 1-2 minutes for creation
6. Go to **Project Settings** (gear icon) → **API**
7. Copy these 3 values:
   - `Project URL` → save as `SUPABASE_URL`
   - `service_role` key → save as `SUPABASE_SERVICE_ROLE_KEY`
   - `anon` key → save as `SUPABASE_ANON_KEY`

### 2.2 Sarvam AI (Free AI)

1. Go to [dashboard.sarvam.ai](https://dashboard.sarvam.ai)
2. Sign up with email or Google
3. Go to **API Keys**
4. Copy your API key → save as `SARVAM_API_KEY`

### 2.3 Google Cloud (Gmail + Sheets + Drive)

This is the longest step but only needs to be done once:

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click "New Project" → Name it "inquiry-platform" → Create
3. Click "APIs & Services" → "Library"
4. Enable these 3 APIs (search and enable each):
   - **Gmail API**
   - **Google Sheets API**
   - **Google Drive API**
5. Click "APIs & Services" → "OAuth consent screen"
6. Fill in:
   - **User Type:** External
   - **App Name:** inquiry-platform
   - **Email:** Your Google email
7. Click "Save"
8. Click "APIs & Services" → "Credentials"
9. Click "Create Credentials" → "OAuth client ID"
10. Choose **Web application**
11. Under "Authorized redirect URIs", add:
    ```
    http://localhost:5678/rest/oauth2-credential/callback
    ```
12. Click Create
13. Copy your **Client ID** and **Client Secret**

---

## Step 3: Set Up the Project

### 3.1 Download the Code

```bash
cd Desktop
git clone https://github.com/your-repo/n8n-inquiry-platform
cd n8n-inquiry-platform
```

### 3.2 Create Your Configuration File

```bash
cp .env.example .env
```

Open `.env` in a text editor (Notepad, VS Code, etc.) and fill in:

```env
# LLM — leave as is
LLM_PROVIDER=sarvam

# Sarvam AI
SARVAM_API_KEY=your_sarvam_api_key_here
SARVAM_BASE_URL=https://api.sarvam.ai/v1
SARVAM_MODEL=sarvam-105b

# LM Studio (only change if you have it installed locally)
LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1
LM_STUDIO_MODEL=local-model

# n8n
N8N_ENCRYPTION_KEY=anything_32_characters_long
N8N_URL=http://n8n:5678
N8N_API_KEY=changeme_after_first_login

# Supabase
SUPABASE_URL=your_supabase_url_here
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
SUPABASE_JWT_SECRET=any_random_string_32_chars

# App
SECRET_KEY=any_random_string_32_chars
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000
```

Save the file.

### 3.3 Set Up Google Sheets for Logging

1. Go to [sheets.google.com](https://sheets.google.com)
2. Click "+ New" → "Google Sheets" → "Blank spreadsheet"
3. Rename to "Inquiry Execution Log"
4. Copy the long ID from the URL:
    ```
    docs.google.com/spreadsheets/d/THIS_PART/edit
                                    ↑ copy this long ID
    ```
5. Put this ID in your `.env` as `GOOGLE_SHEET_ID`

### 3.4 Set Up Google Drive for Knowledge Base

1. Go to [drive.google.com](https://drive.google.com)
2. Create a folder named "KnowledgeBase"
3. Inside, create these 5 text files:
   - `sales_inquiry.txt` — "For pricing questions: Our Enterprise plan starts at..."
   - `support_ticket.txt` — "For support: Our support team responds within..."
   - `complaint.txt` — "For complaints: We're sorry to hear that..."
   - `general_question.txt` — "For general questions: You can reach us at..."
   - `order_request.txt` — "For orders: To place an order, visit..."
4. For each file, get its ID from the URL (the long string) and add to `.env` as:
   ```
   GOOGLE_DRIVE_KB_SALES_FILE_ID=the_file_id
   GOOGLE_DRIVE_KB_SUPPORT_FILE_ID=the_file_id
   ```

---

## Step 4: Start Everything

### 4.1 Start Docker Services

In your terminal:

```bash
docker compose up --build
```

This starts:
- **FastAPI** (backend) at http://localhost:8000
- **n8n** (workflow engine) at http://localhost:5678
- **PostgreSQL** (database)

Wait 1-2 minutes for everything to start. You'll see messages like "backend-1 ready".

### 4.2 Set Up n8n

1. Open http://localhost:5678 in your browser
2. Click "Start" to create your n8n account
3. Set up your owner account (email/password)
4. Go to **Settings** (gear icon) → **API**
5. Enable the API
6. Copy the **API Key**
7. Open your `.env` file and replace `changeme_after_first_login` with this key
8. In terminal, restart:
   ```bash
   docker compose restart backend
   ```

### 4.3 Set Up Google in n8n

1. In n8n (http://localhost:5678), go to **Settings** → **Credentials**
2. Click "New" → search "Google OAuth2"
3. Paste your Google **Client ID** and **Client Secret** from Step 2.3
4. Click "Sign in with Google"
5. Accept all permissions

Now your Gmail, Sheets, and Drive are connected in n8n!

---

## Step 5: Set Up the Database

### 5.1 Run the Schema

1. Open [supabase.com](https://supabase.com) → your project → **SQL Editor**
2. Click "New query"
3. Open the file `supabase/schema.sql` from your downloaded code
4. Copy all the contents
5. Paste into the SQL Editor
6. Press **Run**

You should see "Success! No rows returned".

---

## Step 6: Start the Frontend

### 6.1 Install Dependencies

Open a new terminal (keep Docker running):

```bash
cd n8n-inquiry-platform/frontend
npm install
```

### 6.2 Start the Website

```bash
npm run dev
```

Open http://localhost:3000 in your browser.

---

## Step 7: Use the Platform

### 7.1 Create Your Account

1. Go to http://localhost:3000
2. Click "Create an account"
3. Enter your email and password
4. Click "Sign up"

### 7.2 Create a Workflow

1. Go to **Workflows** (left menu)
2. Click "Create New Workflow"
3. Name it "Customer Inquiry Handler"
4. Choose trigger: **Gmail**
5. Click "Create"

That's it! Your workflow is now live.

### 7.3 Run a Test Inquiry

1. Click on your workflow
2. In "Test Inquiry", type:
   ```
   Hi, we're a 50-person team looking for enterprise pricing. Can we schedule a demo?
   ```
3. Select **Gmail** as channel
4. Click **Run Test**

Watch the magic:
- The page shows each agent working (Classifier → Researcher → Qualifier → Responder → Executor)
- In about 5-15 seconds, you'll see "Completed"
- Check your Gmail — you should have a reply!
- Check your Google Sheet — a new row was added!

### 7.4 View Analytics

1. Click **Analytics** (left menu)
2. See:
   - Total inquiries handled
   - Success rate
   - Average response time
   - Per-agent performance (which agent is slowest?)

### 7.5 View History

1. Click **History** (left menu)
2. See every inquiry you've handled
3. Click any row to see the full agent trace

---

## Troubleshooting

### "Docker won't start"

1. Make sure Docker Desktop is running (icon in taskbar)
2. Restart your terminal
3. Try: `docker compose down` then `docker compose up --build`

### "Can't connect to n8n"

- n8n takes 30-60 seconds to start
- Wait and refresh the page
- Check Docker Desktop is running

### "Google not working in n8n"

1. Go to n8n → Settings → Credentials
2. Delete the Google credential
3. Re-create it (Steps 4.3)

### "Test inquiry fails"

1. Check the `.env` file has correct API keys
2. Restart backend: `docker compose restart backend`
3. Check n8n execution log for errors

### "Frontend won't load"

1. Make sure you're in the frontend folder
2. Run `npm install` again
3. Kill the terminal and run `npm run dev` again

---

## What Happens Next?

Once set up, every time a customer emails your Gmail:

```
Customer Email → n8n Trigger → Classifier → Researcher 
    → Qualifier → Responder → Executor → Auto Reply + Sheet Log
```

You can:
- **Edit agent prompts** — Click workflow → Agents tab → edit prompts
- **View history** — Click "History" to see past runs
- **Export data** — Click any execution → Export JSON/TXT/PDF

---

## Need Help?

- **Frontend UI:** http://localhost:3000
- **Backend API:** http://localhost:8000/docs
- **n8n Editor:** http://localhost:5678
- **Supabase:** https://supabase.com/dashboard

---

*Platform built with Next.js, FastAPI, n8n, Supabase, and Sarvam AI*