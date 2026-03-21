[![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-4285F4?logo=google&logoColor=white)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Jurisdiction](https://img.shields.io/badge/Jurisdiction-Nigeria%20🇳🇬-008751)](#)

# ⚖️ LexiAssist v8.0

**AI-powered legal workspace for Nigerian lawyers.**

LexiAssist combines a jurisdiction-focused legal assistant with practical law-office tools for research, drafting, case tracking, client management, billing, and document handling — all in a single-file Streamlit deployment.

---

## Features

- **AI Legal Assistant** — analysis, drafting, research, procedural guidance, statutory interpretation, strategic advisory
- **Three response modes** — Brief · Standard · Comprehensive
- **Case & hearing management** — track suits, courts, deadlines, and upcoming hearings
- **Client records & billing** — time entries, invoicing, and billing reports
- **Document support** — import PDF, DOCX, TXT, RTF, XLSX, CSV, JSON as AI context
- **Export** — download outputs as TXT, HTML, PDF, or DOCX
- **Legal references** — limitation periods, court hierarchy, Latin maxims
- **Document templates** — contracts, tenancy agreements, powers of attorney, demand letters, written addresses

## AI Models

| Model | ID |
|---|---|
| Gemini 2.5 Flash | `gemini-2.5-flash` |
| Gemini 2.5 Flash Lite | `gemini-2.5-flash-lite` |

## Quick Start

```bash
# Clone
git clone https://github.com/your-username/lexiassist.git
cd lexiassist

# Install
pip install streamlit google-generativeai pandas plotly pdfplumber python-docx fpdf2 openpyxl

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

## Tech Stack

| Core | Optional |
|---|---|
| Python 3.9+ | Plotly *(charts)* |
| Streamlit | pdfplumber *(PDF import)* |
| Google Gemini API | python-docx *(DOCX import/export)* |
| Pandas | fpdf2 *(PDF export)* |
| | openpyxl *(Excel import)* |

## Project Structure

```text
.
├── app.py                  # Entire application (single-file)
├── .streamlit/
│   └── secrets.toml        # API key configuration
├── requirements.txt        # Dependencies
└── README.md
```

## Who This Is For

Lawyers, litigation teams, solo practitioners, and chambers working within the **Nigerian legal system** who need AI-assisted research, drafting, and matter management in one place.

## Disclaimer

LexiAssist provides **AI-generated legal information** for workflow support, drafting, and research. It does **not** constitute legal advice. Always verify statutes, case citations, and procedural rules independently before reliance.

---

<p align="center">
  <strong>LexiAssist v8.0</strong> · Built for Nigerian lawyers · <a href="https://ai.google.dev">Powered by Google Gemini</a>
</p>
