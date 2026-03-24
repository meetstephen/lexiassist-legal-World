[![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-4285F4?logo=google&logoColor=white)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Jurisdiction](https://img.shields.io/badge/Jurisdiction-Nigeria%20🇳🇬-008751)](#)

# ⚖️ LexiAssist v8.0

**AI-powered legal workspace for Nigerian lawyers.**

LexiAssist combines a jurisdiction-focused legal assistant with practical law-office tools for research, drafting, case tracking, client management, billing, contract review, and document handling — with SQLite persistence, cost tracking, and user profiles — all in a single-file Streamlit deployment.

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

- **AI Legal Assistant** — analysis, drafting, research, procedural guidance, statutory interpretation, strategic advisory, contract review
- **Three response modes** — Brief · Standard · Comprehensive (up to 16K tokens)
- **Contract Review mode** — clause-by-clause risk analysis with red flag matrix
- **Save to Case** — attach any AI output directly to a case file for reference
- **Analysis Comparison** — select two AI sessions and get a side-by-side AI verdict
- **Case & hearing management** — track suits, courts, deadlines, upcoming hearings, and saved analyses per case
- **Client records & billing** — time entries, invoicing, billing reports with charts
- **AI Cost Tracker** — per-call Gemini usage logging with daily/monthly cost breakdowns
- **SQLite persistence** — cases, clients, billing, history, and references survive restarts
- **Document support** — import PDF, DOCX, TXT, RTF, XLSX, CSV, JSON as AI context
- **Export** — download outputs as TXT, HTML, PDF, or DOCX (with firm branding)
- **Legal references** — limitation periods, court hierarchy, Latin maxims — all user-editable
- **Document templates** — built-in and custom templates with add/edit/delete
- **User profile** — firm name on exports, optional password protection
- **Full backup/restore** — export and import all data as JSON
- **5 themes** — Emerald · Midnight · Royal · Crimson · Sunset

## AI Models

| Model | ID |
|---|---|
| Gemini 2.5 Flash | `gemini-2.5-flash` |
| Gemini 2.5 Flash Lite | `gemini-2.5-flash-lite` |

Models are fully configurable via secrets or environment variables.

## Quick Start

### Try it now

Visit **[lexiassist-legal-world.streamlit.app](https://lexiassist-legal-world.streamlit.app)** — no installation needed.

### Run locally

```bash
# Clone
git clone https://github.com/meetstephen/lexiassist-legal-World.git
cd lexiassist-legal-World

# Install
pip install -r requirements.txt

# Configure API key (option A — secrets)
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

## Response Modes

| Mode | Description | Token Limit |
|---|---|---|
| ⚡ Brief | Direct answer, 3-5 sentences | 1,200 |
| 📝 Standard | Structured analysis + strategy layer | 6,000 |
| 🔬 Comprehensive | Full CREAC + Devil's Advocate + risk matrix | 16,384 |

## Task Types

| Task | Description |
|---|---|
| 💬 General Query | Any legal question |
| 🔍 Legal Analysis | Issue spotting, CREAC reasoning |
| 📄 Document Drafting | Contracts, pleadings, affidavits |
| 📚 Legal Research | Case law, statutes, authorities |
| 📋 Procedural Guidance | Filing rules, court practice |
| 🎯 Strategic Advisory | Risk mapping, options, strategy |
| ⚖️ Statutory Interpretation | Literal, Golden, Mischief rules |
| 📑 Contract Review | Clause-by-clause risk analysis |

## Data Persistence

LexiAssist stores all data in a local SQLite database (`lexiassist_data.db`):

- Cases and attached AI analyses
- Clients
- Time entries and invoices
- Full chat history
- API cost logs
- Custom templates, limitation periods, and maxims
- User profile

Data survives browser refreshes, app restarts, and redeployments as long as the database file is preserved. Full JSON backup and restore is available from the sidebar and Profile tab.

## Tech Stack

| Core | Optional |
|---|---|
| Python 3.9+ | Plotly *(charts)* |
| Streamlit | pdfplumber *(PDF import)* |
| Google Gemini API | python-docx *(DOCX import/export)* |
| Pandas | fpdf2 *(PDF export)* |
| SQLite | openpyxl *(Excel import)* |

## Project Structure

```text
.
├── .streamlit/
│   └── secrets.toml        # API key and configuration
├── .gitignore              # Git ignore rules
├── app.py                  # Entire application (single-file)
├── requirements.txt        # Dependencies
├── runtime.txt             # Python version for deployment
└── README.md               # Documentation
```

## Who This Is For

Lawyers, litigation teams, solo practitioners, and chambers working within the **Nigerian legal system** who need AI-assisted research, drafting, contract review, and matter management in one place.

## Disclaimer

LexiAssist provides **AI-generated legal information** for workflow support, drafting, and research. It does **not** constitute legal advice. Limitation periods in Nigeria are governed by **state-specific laws**, not a single federal statute — always verify for your jurisdiction. All statutes, case citations, and procedural rules should be independently verified before reliance.

---

<p align="center">
  <strong>LexiAssist v8.0</strong> · Built for Nigerian lawyers · <a href="https://lexiassist-legal-world.streamlit.app">Try it live</a> · <a href="https://ai.google.dev">Powered by Google Gemini</a>
</p>
