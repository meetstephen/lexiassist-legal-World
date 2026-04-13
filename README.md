markdown[![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-4285F4?logo=google&logoColor=white)](https://ai.google.dev)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791?logo=postgresql&logoColor=white)](https://neon.tech)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Jurisdiction](https://img.shields.io/badge/Jurisdiction-Nigeria%20🇳🇬-008751)](#)

# ⚖️ LexiAssist v8.0

**AI-powered legal workspace for Nigerian lawyers.**

LexiAssist combines a jurisdiction-focused legal assistant with practical law-office tools for research, drafting, case tracking, client management, billing, contract review, document handling, AI cost tracking, persistent cloud storage, and export-ready firm branding — in a Streamlit-powered deployment built for the **Nigerian legal system**.

<p align="center">
  <a href="https://lexiassist-legal-world.streamlit.app">
    <img src="https://img.shields.io/badge/🚀%20Launch%20App-LexiAssist%20Live-059669?style=for-the-badge&logoColor=white" alt="Launch LexiAssist">
  </a>
</p>

<p align="center">
  👉 <strong><a href="https://lexiassist-legal-world.streamlit.app">https://lexiassist-legal-world.streamlit.app</a></strong>
</p>

---

## Features

### 🤖 AI Legal Assistant
- **AI Legal Assistant** — analysis, drafting, research, procedural guidance, statutory interpretation, strategic advisory, and contract review
- **Three response modes** — Brief · Standard · Comprehensive (up to 131K tokens)
- **Contract Review mode** — clause-by-clause risk analysis with red flag matrix and signability grade
- **Save to Case** — attach AI outputs directly to case files for future reference
- **Analysis Comparison** — compare two AI sessions and get an AI verdict on the stronger analysis
- **Issue Spotting** — rapid decomposition of legal issues before full analysis
- **Follow-up Questions** — continue any analysis with full context preserved

### 📊 Case Strength Meter *(New)*
- Visual win-probability percentage bars per party
- Colour-coded strength indicators — 🔴 weak · 🟡 moderate · 🟢 strong
- AI-assessed complexity rating and single most important immediate action
- Appears automatically after any Legal Analysis, Advisory, or Contract Review query

### 🧮 Limitation Deadline Calculator *(New)*
- Describe case facts in plain English — AI computes every applicable limitation period
- Exact deadline dates with live countdown in days
- Status flags — 🔴 EXPIRED · 🟡 URGENT · 🟠 WARNING · 🟢 SAFE
- Governing statutory authority cited for every deadline
- Handles special rules including POPA notice requirements

### 🔖 Quick Precedent Finder *(New)*
- Type any legal issue — instantly returns top 5 most authoritative Nigerian cases
- Each result includes full citation, court level, ratio decidendi, and relevance
- Court hierarchy colour coding — 🔴 Supreme Court · 🟡 Court of Appeal · 🟢 Other
- Available directly inside the Research tab

### 📝 Notes → Legal Brief Converter *(New)*
- Paste raw, unstructured client meeting notes
- AI converts them into any of four professional document types:
  - 📋 Legal Brief (Internal Memo)
  - 🤝 Client Retainer Letter
  - 📩 Letter of Demand
  - 📄 Formal Legal Advice Letter
- All outputs downloadable as TXT, HTML, PDF, or DOCX with firm branding
- Save directly to any case file

### 📧 Hearing Reminder Emails *(New)*
- Automatic email alerts for hearings within 7 days
- Formatted HTML emails with case title, suit number, court, date, and days remaining
- Configurable via Gmail App Password — no third-party service needed
- Managed from Profile → 🔔 Notifications tab

### 🏢 Practice Management
- **Case & hearing management** — track suits, courts, deadlines, hearings, and saved analyses per case
- **Client records & billing** — manage clients, log time entries, generate invoices, and view billing reports with charts
- **AI Cost Tracker** — estimated per-call Gemini usage logging with daily/monthly summaries, charts, and CSV export
- **Document support** — import PDF, DOCX, DOC, TXT, RTF, XLSX, XLS, CSV, and JSON as AI context
- **Export** — download outputs as TXT, HTML, PDF, or DOCX with firm branding
- **Legal references** — limitation periods, court hierarchy, and legal maxims, with custom additions
- **Document templates** — built-in and custom templates with full add/edit/delete support
- **User profile** — firm name, lawyer details, export branding, and optional password protection
- **Authentication** — optional login screen via `AUTH_ENABLED` with set/change/remove password
- **Full backup/restore** — export and restore all app data as JSON from the sidebar or Profile tab
- **5 themes** — Emerald · Midnight · Royal · Crimson · Sunset

---

## Navigation

The app is organised into 11 top-level tabs:

| Tab | Purpose |
|---|---|
| 🏠 Home | Dashboard with stats, upcoming hearings, recent sessions, cost summary |
| 🧠 AI Assistant | Main query interface with issue spotting, case strength meter, follow-up, save to case, and comparison |
| 📚 Research | Legal research memoranda with quick precedent finder and save to case |
| 📁 Cases | Case manager with saved analyses viewer per case |
| 📅 Calendar | Hearing calendar with overdue/today/week breakdown |
| 📋 Templates | Browse built-in templates and manage custom templates (add/edit/delete) |
| 👥 Clients | Client database with case and billing summaries |
| 💰 Billing | Time entries, invoicing, billing reports, and AI cost tracker |
| 🔧 Tools | Limitation periods, deadline calculator, court hierarchy, legal maxims — with custom entries |
| 📝 Notes → Brief | Convert raw meeting notes into legal briefs, retainer letters, demand letters, or advice letters |
| 👤 Profile | Firm details, password protection, hearing reminders, full backup/restore, data management |

---

## AI Models

| Model | ID |
|---|---|
| Gemini 2.5 Flash | `gemini-2.5-flash` |
| Gemini 2.5 Flash Lite | `gemini-2.5-flash-lite` |

Models are configurable via Streamlit secrets or environment variables. Use `GEMINI_MODELS` to provide a custom comma-separated list.

---

## Quick Start

### Try it now

Visit **[lexiassist-legal-world.streamlit.app](https://lexiassist-legal-world.streamlit.app)** — no installation needed.

### Run locally

```bash
# Clone
git clone https://github.com/meetstephen/lexiassist-legal-World.git
cd lexiassist-legal-World

# Install dependencies
pip install -r requirements.txt

# Configure secrets
mkdir -p .streamlit
cat > .streamlit/secrets.toml << EOF
GEMINI_API_KEY = "your-api-key-here"
GEMINI_MODEL = "gemini-2.5-flash"
DATABASE_URL = "postgresql://user:password@host/dbname?sslmode=require"
EOF

# Run
streamlit run app.py
```

Alternatively, set environment variables:

```bash
export GEMINI_API_KEY="your-api-key-here"
export GEMINI_MODEL="gemini-2.5-flash"
export DATABASE_URL="postgresql://user:password@host/dbname?sslmode=require"
streamlit run app.py
```

---

## Configuration

All options go in `.streamlit/secrets.toml`:

| Key | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `DATABASE_URL` | Yes | PostgreSQL connection string (see below) |
| `GEMINI_MODEL` | No | Default model (e.g. `gemini-2.5-flash`) |
| `GEMINI_MODELS` | No | Comma-separated list of available models |
| `AUTH_ENABLED` | No | Set `"true"` to require login on startup |

### Example

```toml
GEMINI_API_KEY = "your-api-key-here"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_MODELS = "gemini-2.5-flash,gemini-2.5-flash-lite"
DATABASE_URL = "postgresql://user:password@host/dbname?sslmode=require"
AUTH_ENABLED = "true"
```

---

## Database Setup

LexiAssist uses **PostgreSQL** for persistent cloud storage. All data survives app restarts, sleep cycles, and redeployments.

### Recommended: Neon (free tier)

1. Sign up at **[neon.tech](https://neon.tech)**
2. Create a new project
3. Click **Connect** and copy the connection string
4. Strip `&channel_binding=require` if present — psycopg2 does not support it
5. Add to your Streamlit secrets as `DATABASE_URL`

The connection string format must be:
postgresql://user:password@host/dbname?sslmode=require

> **Note:** Use `postgresql://` not `postgres://` — psycopg2 requires the full prefix.

### What is stored

- Cases and saved AI analyses per case
- Clients
- Time entries and invoices
- Full AI chat history
- AI cost logs (per-call with model, task, token counts, estimated cost)
- Custom templates
- Custom limitation periods and legal maxims
- User profile and export branding

---

## Response Modes

| Mode | Description | Token Limit |
|---|---|---|
| ⚡ Brief | Direct answer, 3–5 sentences | 8,000 |
| 📝 Standard | Structured analysis with strategy layer | 32,000 |
| 🔬 Comprehensive | Full CREAC, devil's advocate, exhaustive strategy and risk ranking | 131,072 |

---

## Task Types

| Task | Description |
|---|---|
| 💬 General Query | Any legal question |
| 🔍 Legal Analysis | Issue spotting and CREAC reasoning |
| 📄 Document Drafting | Contracts, pleadings, affidavits, and legal instruments |
| 📚 Legal Research | Case law, statutes, and authorities |
| 📋 Procedural Guidance | Filing rules, timelines, and court practice |
| 🎯 Strategic Advisory | Risk mapping, exposure ranking, and options |
| ⚖️ Statutory Interpretation | Literal, Golden, and Mischief rule analysis |
| 📑 Contract Review | Clause-by-clause risk analysis with red flag matrix |

---

## Security

LexiAssist supports optional password protection.

1. Go to **Profile → 🔐 Security** tab and set a password
2. Enable login enforcement by adding to `.streamlit/secrets.toml`:

```toml
AUTH_ENABLED = "true"
```

If `AUTH_ENABLED` is not set, the app remains open without a login screen.

> **Tip:** If you forget your password, temporarily set `AUTH_ENABLED = "false"`, reboot the app, reset your password in Profile → Security, then re-enable it.

---

## Export Support

All AI outputs can be exported in the following formats:

| Format | Notes |
|---|---|
| **TXT** | Plain text with firm header and footer |
| **HTML** | Styled web page with firm branding |
| **PDF** | Print-ready with firm name and generation timestamp |
| **DOCX** | Editable Word document with firm branding |

Firm name and lawyer details are pulled from the **Profile** tab and applied to all exports automatically.

---

## Tech Stack

| Core | Optional |
|---|---|
| Python 3.11 | Plotly *(charts & cost visualisation)* |
| Streamlit | pdfplumber *(PDF import)* |
| Google Gemini API | python-docx *(DOCX import/export)* |
| Pandas | fpdf2 *(PDF export)* |
| PostgreSQL + psycopg2 | openpyxl *(Excel import)* |

---

## Project Structure

```text
.
├── .streamlit/
│   └── secrets.toml            # API key, database URL, and config (not committed)
├── .gitignore                  # Git ignore rules
├── app.py                      # Entire application (single-file)
├── requirements.txt            # Python dependencies
├── runtime.txt                 # Python version for Streamlit Cloud
└── README.md                   # This file
```

---

## Deployment Notes

- The app is designed for **Streamlit Cloud** and local deployment
- A **PostgreSQL database** (e.g. Neon free tier) is required for persistent storage
- On first deployment, tables are created automatically — no manual migration needed
- On free Streamlit infrastructure, occasional cold-start delays are normal after inactivity
- The database connection auto-reconnects if the connection goes stale after a sleep cycle

---

## Who This Is For

Lawyers, litigation teams, solo practitioners, chambers, and legal operations professionals working within the **Nigerian legal system** who need AI-assisted legal research, drafting, contract review, matter tracking, billing, and document management in one place.

---

## Disclaimer

LexiAssist provides **AI-generated legal information** for workflow support, drafting, research, and practice management. It does **not** constitute legal advice. Limitation periods in Nigeria are governed largely by **state-specific laws**, not a single universal federal limitation regime — always verify for the relevant jurisdiction. All statutes, procedural rules, case citations, and authorities should be independently verified before reliance.

---

<p align="center">
  <strong>LexiAssist v8.0</strong> · Built for Nigerian lawyers · <a href="https://lexiassist-legal-world.streamlit.app">Try it live</a> · <a href="https://ai.google.dev">Powered by Google Gemini</a>
</p>
