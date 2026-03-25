[![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-4285F4?logo=google&logoColor=white)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Jurisdiction](https://img.shields.io/badge/Jurisdiction-Nigeria%20🇳🇬-008751)](#)

# ⚖️ LexiAssist v8.0

**AI-powered legal workspace for Nigerian lawyers.**

LexiAssist combines a jurisdiction-focused legal assistant with practical law-office tools for research, drafting, case tracking, client management, billing, contract review, document handling, AI cost tracking, persistent storage, and export-ready firm branding — in a Streamlit-powered deployment built for the **Nigerian legal system**.

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

- **AI Legal Assistant** — analysis, drafting, research, procedural guidance, statutory interpretation, strategic advisory, and contract review
- **Three response modes** — Brief · Standard · Comprehensive (up to 16K tokens)
- **Contract Review mode** — clause-by-clause risk analysis with red flag matrix and signability grade
- **Save to Case** — attach AI outputs directly to case files for future reference
- **Analysis Comparison** — compare two AI sessions and get an AI verdict on the stronger analysis
- **Case & hearing management** — track suits, courts, deadlines, hearings, and saved analyses per case
- **Client records & billing** — manage clients, log time entries, generate invoices, and view billing reports with charts
- **AI Cost Tracker** — estimated per-call Gemini usage logging with daily/monthly summaries, charts, and CSV export
- **SQLite persistence** — cases, clients, billing, chat history, templates, references, cost logs, and profile survive app restarts
- **Document support** — import PDF, DOCX, DOC, TXT, RTF, XLSX, XLS, CSV, and JSON as AI context
- **Export** — download outputs as TXT, HTML, PDF, or DOCX with firm branding
- **Legal references** — limitation periods, court hierarchy, and legal maxims, with custom additions
- **Document templates** — built-in and custom templates with full add/edit/delete support
- **User profile** — firm name, lawyer details, export branding, and optional password protection
- **Authentication** — optional login screen via `AUTH_ENABLED` with set/change/remove password
- **Full backup/restore** — export and restore all app data as JSON from the sidebar or Profile tab
- **5 themes** — Emerald · Midnight · Royal · Crimson · Sunset

## Navigation

The app is organised into 10 top-level tabs:

| Tab | Purpose |
|---|---|
| 🏠 Home | Dashboard with stats, upcoming hearings, recent sessions, cost summary |
| 🧠 AI Assistant | Main query interface with issue spotting, follow-up, save to case, and comparison |
| 📚 Research | Legal research memoranda with save to case |
| 📁 Cases | Case manager with saved analyses viewer per case |
| 📅 Calendar | Hearing calendar with overdue/today/week breakdown |
| 📋 Templates | Browse built-in templates and manage custom templates (add/edit/delete) |
| 👥 Clients | Client database with case and billing summaries |
| 💰 Billing | Time entries, invoicing, billing reports, and AI cost tracker |
| 🔧 Tools | Limitation periods, court hierarchy, legal maxims — with custom entries |
| 👤 Profile | Firm details, password protection, full backup/restore, data management |

## AI Models

| Model | ID |
|---|---|
| Gemini 2.5 Flash | `gemini-2.5-flash` |
| Gemini 2.5 Flash Lite | `gemini-2.5-flash-lite` |

Models are configurable via Streamlit secrets or environment variables. Use `GEMINI_MODELS` to provide a custom comma-separated list.

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

# Configure API key (option A — Streamlit secrets)
mkdir -p .streamlit
cat > .streamlit/secrets.toml << EOF
GEMINI_API_KEY = "your-api-key-here"
GEMINI_MODEL = "gemini-2.5-flash"
EOF

# Run
streamlit run app.py
```

Alternatively, set environment variables:

```bash
export GEMINI_API_KEY="your-api-key-here"
export GEMINI_MODEL="gemini-2.5-flash"
streamlit run app.py
```

## Configuration

All options go in `.streamlit/secrets.toml`:

| Key | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `GEMINI_MODEL` | No | Default model (e.g. `gemini-2.5-flash`) |
| `GEMINI_MODELS` | No | Comma-separated list of available models |
| `AUTH_ENABLED` | No | Set `"true"` to require login on startup |

### Example

```toml
GEMINI_API_KEY = "your-api-key-here"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_MODELS = "gemini-2.5-flash,gemini-2.5-flash-lite"
AUTH_ENABLED = "true"
```

## Response Modes

| Mode | Description | Token Limit |
|---|---|---|
| ⚡ Brief | Direct answer, 3–5 sentences | 1,200 |
| 📝 Standard | Structured analysis with strategy layer | 6,000 |
| 🔬 Comprehensive | Full CREAC, devil's advocate, deeper strategy, and risk ranking | 16,384 |

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

## Data Persistence

LexiAssist stores all application data in a local SQLite database:

```text
lexiassist_data.db
```

Stored data includes:

- Cases and saved AI analyses
- Clients
- Time entries and invoices
- Full AI/chat history
- AI cost logs (per-call with model, task, token counts, estimated cost)
- Custom templates
- Custom limitation periods and legal maxims
- User profile and export branding

Data survives browser refreshes, app restarts, and redeployments **as long as the SQLite database file is preserved**. Full backup and restore is available through JSON export/import from the sidebar and the Profile → Data Management tab.

## Security

LexiAssist supports optional password protection.

- Set a password inside the **Profile → Security** tab
- Enable login enforcement by adding this to `.streamlit/secrets.toml`:

```toml
AUTH_ENABLED = "true"
```

If `AUTH_ENABLED` is not set, the app remains open without a login screen.

## Export Support

Outputs can be exported in the following formats:

- **TXT**
- **HTML**
- **PDF**
- **DOCX**

All exports include firm branding (firm name, lawyer details) where configured in the **Profile** tab.

## Tech Stack

| Core | Optional |
|---|---|
| Python 3.11 | Plotly *(charts & cost visualisation)* |
| Streamlit | pdfplumber *(PDF import)* |
| Google Gemini API | python-docx *(DOCX import/export)* |
| Pandas | fpdf2 *(PDF export)* |
| SQLite | openpyxl *(Excel import)* |

## Project Structure

```text
.
├── .streamlit/
│   └── secrets.toml            # API key and configuration (not committed)
├── .gitignore                  # Git ignore rules
├── app.py                      # Entire application (single-file)
├── requirements.txt            # Python dependencies
├── runtime.txt                 # Python version for Streamlit Cloud
├── lexiassist_data.db          # SQLite database (auto-created at runtime)
└── README.md                   # This file
```

## Deployment Notes

- The app is designed for **Streamlit Cloud** and local deployment
- On first deployment, startup may take longer due to dependency installation and database initialisation
- Subsequent loads are typically much faster
- If hosted on free Streamlit infrastructure, occasional cold-start delays are normal after inactivity

## Who This Is For

Lawyers, litigation teams, solo practitioners, chambers, and legal operations professionals working within the **Nigerian legal system** who need AI-assisted legal research, drafting, contract review, matter tracking, billing, and document management in one place.

## Disclaimer

LexiAssist provides **AI-generated legal information** for workflow support, drafting, research, and practice management. It does **not** constitute legal advice. Limitation periods in Nigeria are governed largely by **state-specific laws**, not a single universal federal limitation regime — always verify for the relevant jurisdiction. All statutes, procedural rules, case citations, and authorities should be independently verified before reliance.

---

<p align="center">
  <strong>LexiAssist v8.0</strong> · Built for Nigerian lawyers · <a href="https://lexiassist-legal-world.streamlit.app">Try it live</a> · <a href="https://ai.google.dev">Powered by Google Gemini</a>
</p>
