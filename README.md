# 🏰 TechRook Policy Chatbot — Complete Project

A **zero-hallucination, role-based HR Policy Chatbot** for TechRook Technologies Pvt. Ltd., powered by FastAPI + LangChain RAG + React.

---

## 📁 Project Structure

```
techrook-chatbot/
├── backend/
│   ├── main.py              # FastAPI server (auth + chat + checklist endpoints)
│   ├── auth.py              # JWT authentication + mock user database
│   ├── rag_engine.py        # LangChain RAG with self-correction loop
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Environment variables template
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                      # Root component (auth + chat orchestrator)
│   │   ├── main.jsx                     # React entry point
│   │   ├── api.js                       # API service layer (auth/chat/checklist)
│   │   ├── hooks/
│   │   │   └── useAuth.js               # Authentication state hook
│   │   └── components/
│   │       ├── AuthScreen.jsx           # Login + Signup UI
│   │       ├── ChatWindow.jsx           # Main chat interface
│   │       └── ChecklistPanel.jsx       # Onboarding checklist drawer
│   ├── index.html
│   ├── vite.config.js                   # Vite + proxy config
│   ├── package.json
│   └── .env.example
│
├── handbook/
│   └── techrook_handbook.txt            # TechRook Employee Handbook 2026 (RAG source)
│
└── README.md
```

---

## ⚙️ Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.10+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| Anthropic API Key | — | https://console.anthropic.com |

---

## 🚀 Setup — Step by Step

### Step 1 — Clone / Extract the project

If you downloaded the zip, extract it:
```bash
unzip techrook-chatbot.zip
cd techrook-chatbot
```

---

### Step 2 — Backend Setup

```bash
cd backend
```

**Create a virtual environment:**
```bash
python -m venv venv

# Activate it:
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```
> ⏳ This takes 2–5 minutes — it downloads sentence-transformers (embedding model).

**Create your `.env` file:**
```bash
cp .env.example .env
```

Open `.env` and add your Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
SECRET_KEY=any-long-random-string-here
```

**Start the backend:**
```bash
python main.py
```

You should see:
```
🔄 Initializing TechRook RAG engine...
✅ Created 87 document chunks
✅ FAISS vector store created with sentence-transformers embeddings
✅ RAG engine ready!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

> 📍 Backend is now running at **http://localhost:8000**
> 📚 API docs available at **http://localhost:8000/docs**

---

### Step 3 — Frontend Setup

Open a **new terminal window** (keep backend running):

```bash
cd frontend
```

**Install dependencies:**
```bash
npm install
```

**Create your `.env` file:**
```bash
cp .env.example .env
```

The default `.env` works as-is (uses Vite proxy to forward `/api` → `http://localhost:8000`).

**Start the frontend:**
```bash
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in 300ms
  ➜  Local:   http://localhost:5173/
```

---

### Step 4 — Open the App

Go to **http://localhost:5173** in your browser.

---

## 🔑 Demo Accounts

| Email | Role | Grade | Password |
|-------|------|-------|----------|
| alice@techrook.in | L0 Trainee | L0 | pass123 |
| bob@techrook.in | L1-L2 Employee | L2A | pass123 |
| carol@techrook.in | L3+ Manager | L3 | pass123 |

Or click **"New employee? Create account"** to register with any `@techrook.in` email.

---

## 🏗️ Architecture

```
User Browser
    │
    ▼
React Frontend (port 5173)
    │  POST /api/chat
    │  POST /api/auth/login
    │  GET  /api/checklist
    ▼
FastAPI Backend (port 8000)
    │
    ├── auth.py ──► JWT validation + mock user DB
    │
    └── rag_engine.py
            │
            ├── 1. Retrieve relevant chunks from FAISS vector store
            │       (TechRook Handbook embedded with sentence-transformers)
            │
            ├── 2. Build role-filtered system prompt (L0/L1-L2/L3+)
            │
            ├── 3. Call Claude Sonnet via LangChain
            │
            ├── 4. SELF-CORRECTION: verify answer against source chunks
            │
            └── 5. Return verified answer + sources
```

---

## 🔐 Role-Based Access

| Role | Who | Access |
|------|-----|--------|
| **L0** | Trainees/Interns | Onboarding, basic leave, certifications, attendance, security basics, POSH awareness |
| **L1-L2** | Executives/Managers | All employee policies: full leave, salary, travel, appraisal, WFH stipend, referral bonus |
| **L3+** | Directors/Executives | ALL policies including recruitment, disciplinary administration, ICC roles, all recognition awards |

---

## ☑️ Onboarding Checklist Items

| # | Item | Policy Source |
|---|------|---------------|
| 1 | Upload Documents (Aadhaar, PAN, Relieving Letter) | Chapter 8.1 |
| 2 | Open ICICI Power Pay Account | Chapter 11 |
| 3 | Complete CyberVault Basics Certification (Day 15 deadline) | Chapter 9.1 |
| 4 | Complete AI Ethics 101 Certification (Day 15 deadline) | Chapter 9.2 |
| 5 | Acknowledge POSH Policy | Chapter 26 |
| 6 | Enroll 2 MFA Devices (within 3 working days) | Chapter 23.1 |

---

## 🛡️ Anti-Hallucination Design

1. **Retrieval-grounded answers** — Claude only sees the top-5 retrieved handbook chunks, not its training knowledge
2. **Self-correction loop** — a second Claude call verifies the answer against the source before returning it
3. **Role filtering** — lower-grade users are blocked from manager-only policy topics
4. **Mandatory source citations** — every response includes `📋 Source: Chapter X`
5. **Humble refusal** — off-topic or abusive questions get a polite redirect

---

## 🔧 Changelog — v1.1 (Accuracy Fixes)

| # | Fix | File | Impact |
|---|-----|------|--------|
| 1 | **AIMessage for assistant history** — was incorrectly using `SystemMessage` for chat history turns, causing LangChain to misinterpret prior assistant replies in multi-turn conversations | `rag_engine.py` | Multi-turn follow-up accuracy |
| 2 | **Self-correction actually re-verifies** — previously set `verified = True` unconditionally after a retry, even if the retry answer was still wrong; now runs a second verification pass on the corrected answer | `rag_engine.py` | Hallucination detection reliability |
| 3 | **Larger chunks (800 → 1200) + more overlap (100 → 200)** — reduces boundary gaps where a policy answer spans two consecutive chunks | `rag_engine.py` | Completeness of multi-clause answers |
| 4 | **More retrieved chunks (k=5 → k=7)** — broader context window for questions that touch multiple policy areas | `rag_engine.py` | Coverage for complex queries |
| 5 | **Separator fix** — `"."` → `". "` prevents mid-abbreviation splits (e.g. `"INR 25,000"` no longer splits at the decimal point) | `rag_engine.py` | Numeric accuracy in answers |
| 6 | **`self_corrected` flag exposed in API response** — frontend/callers can now see whether a self-correction was triggered | `main.py` | Observability |

---



**Backend fails to start — `ModuleNotFoundError`**
```bash
# Make sure virtual environment is activated, then:
pip install -r requirements.txt
```

**`sentence-transformers` download is slow**
> First run downloads a ~90MB model. Subsequent runs use the cached version.

**Frontend shows "Connection error"**
> Make sure the backend is running (`python main.py`) before starting the frontend.

**CORS error in browser**
> The Vite proxy in `vite.config.js` handles this automatically. Don't call port 8000 directly from the browser.

**`ANTHROPIC_API_KEY` not found**
> Make sure you created `backend/.env` from the `.env.example` and added your actual key.

---

## 🚢 Production Notes

For production deployment:
- Replace `fake_user_db` in `auth.py` with PostgreSQL + SQLAlchemy
- Replace `fake_checklist_db` with a real database
- Use a strong random `SECRET_KEY` (32+ characters)
- Run backend with: `uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4`
- Build frontend with: `npm run build` (serves from `dist/`)
- Consider adding Redis for session management

---

## 📞 TechRook HR Contacts (from Handbook)
- **HR General**: hr@techrook.in | +91-40-6800-1250
- **IT Support**: itsupport@techrook.in | +91-40-6800-1300
- **POSH/ICC**: posh.icc@techrook.in
- **EAP (24/7)**: eap@techrook.in | +91-80-4500-2299
