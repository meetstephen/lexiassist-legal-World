[![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini%202.5-4285F4?logo=google&logoColor=white)](https://ai.google.dev)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791?logo=postgresql&logoColor=white)](https://neon.tech)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Jurisdiction](https://img.shields.io/badge/Jurisdiction-Nigeria%20🇳🇬-008751)](#)
[![Security](https://img.shields.io/badge/Security-Fernet%20Encrypted-6366f1)](#)
[![Grounding](https://img.shields.io/badge/Grounding-Live%20Web%20%2B%20Statute%20RAG-059669)](#)
[![Reasoning](https://img.shields.io/badge/Reasoning-Gemini%20Thinking-A29BFE)](#)
[![Beta](https://img.shields.io/badge/Status-Private%20Beta-f59e0b)](#)

# ⚖️ LexiAssist 2.0

**AI-powered legal workspace for Nigerian lawyers — now with native step-by-step reasoning, app-wide live web grounding with real source links, one-click citation verification, and a one-click "work from this document" workflow.**

LexiAssist combines a jurisdiction-focused AI legal assistant with a full law-office management suite — covering research, drafting, case tracking, task management, client management, contract review, document handling, AI usage tracking, persistent cloud storage, and export-ready firm branding — deployed on Streamlit and purpose-built for the **Nigerian legal system**.

> **Brand vs build:** the app presents itself everywhere as **LexiAssist 2.0**. A precise internal build number is still tracked in `lexi/runtime.py` (`__version__`) for data records, database migrations, and debugging — it is intentionally not shown to users.

<p align="center">
  <a href="https://lexiassist-legal-world.streamlit.app">
    <img src="https://img.shields.io/badge/🚀%20Launch%20App-LexiAssist%20Live-059669?style=for-the-badge&logoColor=white" alt="Launch LexiAssist">
  </a>
</p>

<p align="center">
  👉 <strong><a href="https://lexiassist-legal-world.streamlit.app">https://lexiassist-legal-world.streamlit.app</a></strong>
</p>

---

## What's New in 2.0

| Feature | Description |
|---|---|
| 🧠 Native reasoning ("thinking") | The Gemini 2.5 models reason through the Nigerian legal framework **before** writing the answer, using a native per-mode thinking budget. The reasoning trace is shown in a collapsible **"🧠 How LexiAssist reasoned"** panel so you can audit the logic. Pro-level accuracy from a lightweight Flash model, by architecture. |
| 🌐 App-wide live web grounding | A **single sidebar switch — "🌐 Live web grounding (all AI features)"** — puts *every* AI feature online: it searches the live web via Google and grounds the answer in **real, current sources with clickable links**, instead of training-memory. Verified-database grounding and the citation audit still layer on top. |
| 📰 Practice Updates (always live) | The legal news / practice-update feed is **always** sourced live from the web — it fetches real, recent Nigerian developments and shows the **source link for each item**. No fabricated "news". |
| 🔎 Real online research | **Quick Precedent Finder** and the main **Research** page now genuinely search the live web for relevant Nigerian cases (with source links), instead of relying on the model's memory. |
| 🔍 One-click citation verification | Under the citation audit on any answer, **"🔎 Verify cited case(s) on the live web"** runs a live search and reports each case as **REAL / NOT FOUND / UNCERTAIN** with a source link — closing the gap where a genuine case simply isn't in the local database. |
| 📄 One-click document actions | Drop a contract / pleading / judgment and use one-click chips — **📄 Summarise · ⚠️ Spot Risks · 📋 Key Terms & Obligations · 🗣️ Explain to Client** — each runs instantly with the uploaded document attached. Whole documents are analysed (up to ~50 pages), not just the first few. |
| 🤖 AI Usage tab | Per-call Gemini usage and estimated spend (today / month / all-time, charts, call log, CSV export) now lives in **Profile → 🤖 AI Usage**. |
| 🧭 Leaner navigation | Decluttered from 22 to 17 tabs: Source Research folded into **Research**, Calendar folded into **Cases**, and two low-relevance pages removed. The duplicate **Authority Verification** (previously also a Tools tab) was removed in favour of the stronger standalone page. |

---

## How the AI stays accurate (and how to *prove* it)

LexiAssist is built so a lawyer can **verify** what the AI says, not just trust it. Four layers work together:

1. **Native reasoning before answering** — the model spends a budget of private "thinking" tokens working through the issue, applicable statutes, and authorities before it writes a word. The summarised reasoning is shown so you can check the logic.
2. **Live web grounding (real sources)** — when web grounding is on (and always-on for Practice Updates, Precedent Finder, and the citation verifier), answers are grounded in **live Google Search results** and the **actual source URLs are shown as clickable links**. Open them and confirm — they are real.
3. **Verified Nigerian database grounding** — 150+ landmark Supreme Court / Court of Appeal decisions and 18+ core statute provisions are retrieved and injected into the prompt, and every answer is scanned so cited cases are checked against this database.
4. **Citation audit + one-click verifier** — every response is scanned for citations and labelled ✅ Verified / ⚠️ Unverified; one click then runs a **live web check** on the cited cases (REAL / NOT FOUND / UNCERTAIN, with links).

### How online-sourced cases are labelled (authenticity, honestly)

When the **Quick Precedent Finder** returns cases, each one is tagged by **how strongly its authenticity was actually evidenced** — the labels never overstate what was checked:

| Badge | Meaning | What you must do |
|---|---|---|
| ✅ **Verified (in database)** | The case name matches LexiAssist's hand-verified local database of real Nigerian decisions. | Safe to rely on the existence; still confirm it's on-point. |
| 🌐 **Web-sourced — confirm source** | Not in the local DB, but a **live web search actually returned it** with a valid Nigerian-report citation shape, and a **clickable source link** is provided. | **Open the source link and confirm** the report (NWLR/LPELR/LawPavilion) before citing. |
| ⚠️ **Needs Verification** | The live search returned no confirming source (possibly model memory), or the citation shape is invalid. | Treat as unconfirmed — verify independently before any reliance. |

This deliberately replaced an earlier "high confidence" label that was based only on a citation's *format* — a hallucinated citation can have a perfectly valid shape, so format alone is never treated as proof of existence. **Relevance** is handled separately: results are retrieved with a precision-gated matcher (a single incidental shared word can no longer surface an off-topic case), and the model is instructed to silently ignore any candidate that is not genuinely on-point.

> **"I used Practice Updates and it really went online — it gave me a source link I clicked and it was true. Does that mean it's working?"**
> **Yes — that is exactly the design, and it confirms grounding is working end-to-end on your setup.** The Practice Updates feed forces live web search **on by default** (it does not depend on the sidebar switch), so it always fetches real, current developments and shows you the real source link for each. The fact that you clicked through and the source was genuine means: (a) your Gemini API key has Google Search grounding enabled and within quota, and (b) the source links the model returns are the real ones it used. The general AI features are **off by default** for web grounding — flip the sidebar switch **🌐 Live web grounding** to put those online too.

### What needs to be enabled on your side
Live grounding uses **Google Search as a tool through the Gemini API**, which draws on your **API key's Search grounding quota** (free daily allowance on standard Google AI Studio keys, then billable). If a search is ever unavailable, the app **degrades gracefully** — it falls back to verified-database grounding and still answers — so nothing breaks; you simply won't see live source links for that call.

---

## Features

### 🤖 AI Legal Assistant
- **Eight task types** — 💬 General Query · 🔍 Legal Analysis (issue-spotting, CREAC) · 📄 Document Drafting · 📚 Legal Research · 📋 Procedural Guidance · 🎯 Strategic Advisory · ⚖️ Statutory Interpretation · 📑 Contract Review
- **Native reasoning** — Gemini 2.5 "thinking" runs before the answer (per-mode budget); collapsible reasoning-trace panel for auditability
- **Three response modes** — Brief · Standard · Comprehensive (up to 131K output tokens)
- **Streaming output** — responses appear word-by-word via `generate_content_stream()`
- **Live web grounding (optional per query, or app-wide)** — grounds answers in real web sources and shows the links used
- **Quality gate** — silent self-critique; a weak answer triggers one automatic stricter regeneration
- **4-axis confidence scores** — Statutory Grounding · Case Law Support · Procedural Certainty · Position-taking
- **RAG grounding** — verified Nigerian statute provisions retrieved by similarity and injected into every system prompt
- **Citation audit + one-click live-web verifier** — see "How the AI stays accurate" above
- **Contract Review** — clause-by-clause risk matrix and signability grade
- **Contract Version Diffing** — visual line-by-line diff of V1 vs V2 plus AI explanation of legal significance
- **One-click document workflow** — upload PDF/DOCX/TXT/RTF/XLSX/CSV/JSON (sanitised against prompt injection), then run Summarise / Spot Risks / Key Terms / Explain-to-Client in one click; whole-document analysis (~50 pages)
- **Save to Case · Analysis Comparison · Issue Spotting · Follow-up Questions · Case Strength Meter**

### 🔍 Authority Verification (standalone page)
- Paste any AI-generated argument, draft, or memo; every case, statute, rule, and constitutional provision cited is extracted and classified
- Status per citation: **Verified · Unverified · Possible Hallucination · Repealed · Foreign · Needs Section Number · Check Spelling**
- Deterministic checks: verified-case database match, repealed-law scan, foreign-authority scan; confidence score and fix per citation
- Downloadable TXT verification report

### 🛡️ Citation Verification Engine
- 150+ verified landmark Supreme Court and Court of Appeal decisions across Constitutional · Electoral · Contract · Land · Evidence · Criminal · Employment · Oil & Gas · Banking · Tort · Company · Tax · Customary Law · Procedure
- Regex coverage for major Nigerian report series: NWLR · LPELR · SCNLR · SC · All NLR · NMLR · NCLR
- Verified citations badged ✅; unverified flagged inline with ⚠️; one-click live-web confirmation
- Admin-added verified cases persist to the database and load into every session

### 📰 Practice Updates (live)
- Always sourced **live from the web** — fetches real, recent Nigerian legal developments
- Each item shows date, plain-English summary, practice impact, and a **clickable source link**
- Deep-dive on any item is also live-web-grounded
- If the search returns nothing solid, it says so rather than inventing content

### ✅ Task Manager
- Tasks with due date, priority, status, linked case, assigned lawyer, notes; overdue auto-detection; 4-badge summary; inline updates; audit-logged; persisted

### 📋 Court Process Checklist
- AI-generated, rule-cited filing checklist for 15 matter types × 13 courts × 11 state rule sets — pre-action, documents, filing steps, frontloading, service, common defects, timeline; TXT export

### 📜 Audit Log
- 17 event types, colour-coded, **hash-chained** (retroactive tampering is detectable), admin-viewable with filtering and CSV export

### 🔒 Security
- **PBKDF2-HMAC-SHA256** password hashing (260,000 iterations) with **`hmac.compare_digest()`** timing-safe verification
- **Login rate limiting** — 5 failed attempts → 5-minute lockout, with warnings from attempt 3
- **Prompt-injection protection** — `sanitize_doc_context()` strips control characters, detects known injection patterns, and wraps uploaded document text in hard "data-only" delimiters before it reaches the AI
- **Fernet-encrypted SMTP credentials** — decrypted only at send-time, in memory
- **Persistent, revocable session tokens** (30-day) stored server-side; per-user data isolation (`u:{user_id}:` namespacing)
- **Graceful AI fallback chain** — if a model rejects native thinking or the web-search tool, the call automatically steps down (thinking+search → search-only → plain) instead of failing

### ⚙️ Firm Admin Settings (admin only)
- Billing defaults (hourly rate, currency, VAT/WHT) with live preview · default court/jurisdiction · monthly AI budget + allowed-model whitelist · letterhead footer + bank details · user-permission controls — all audit-logged

### 🔎 Global Search
- One field searches across **Cases · Clients · saved Analyses · AI history** simultaneously, grouped by category — a true cross-cutting workspace search

### 🏢 Practice Management
- Case & hearing management (with the hearing **Calendar** as a tab inside Cases) · Task Manager · Home dashboard with Next-7-Days panel · rich empty states · Case Bundle Export (PDF/TXT) · fuzzy Conflict Checker · client records · document templates with `[PLACEHOLDER]` detection · full JSON backup/restore

### 📧 Hearing Reminder Emails
- Automatic alerts for hearings within 1 or 7 days; HTML emails; Gmail App Password stored encrypted; managed from **Profile → 🔔 Notifications**

---

## Navigation

Grouped sidebar navigation with 5 sections:

| Section | Pages |
|---|---|
| ⚖️ **Practice** | 🏠 Home · 🧠 AI Assistant · 📚 Research *(Case Law & Statutes + From My Sources)* · 📝 Notes → Brief |
| 📁 **Matters** | 📁 Cases *(Case Manager + Hearing Calendar)* · ✅ Tasks · 📜 Pleadings · 🔍 Conflict Check |
| 👥 **Clients & Fees** | 👥 Clients · ⚖️ Fee Calculator |
| 🔧 **Tools** | 🔧 Tools · 📰 Practice Updates · 🔍 Authority Verify · 🎯 Witness Prep · 🤝 Settlement · 🔎 Due Diligence · 📋 Templates · 🔎 Search |
| 👤 **Account** | 👤 Profile *(incl. 🤖 AI Usage)* · ❓ Help · 📜 Privacy · 📋 Terms · 🛡️ Admin *(admin only)* |

### 🔧 Tools — Tab Reference

| Tab | What it does |
|---|---|
| ⏳ Limitation Periods | Reference table + AI deadline calculator with jurisdiction-specific verification warnings |
| 🧮 Deadline Calculator | Compute limitation deadlines from date of cause of action with special-notes warnings |
| 🏛️ Court Hierarchy | Visual hierarchy of Nigerian courts with jurisdiction notes |
| 📜 Legal Maxims | Searchable library of maxims with custom additions |
| 🛡️ AML / SCUML | AML/CFT compliance checker for financial transactions |
| 📋 Court Process Checklist | AI-generated filing checklist — 15 matter types × 13 courts × 11 state rule sets |

> Authority Verification is its own dedicated page (🔍 Authority Verify) — it is no longer duplicated as a Tools tab.

---

## Legal Safety

LexiAssist is designed for use by qualified Nigerian lawyers, not as a direct-to-client service:

- **Reasoning + verifiable sources** — the model reasons before answering, and (when grounded) cites real, clickable web sources alongside verified-database citations.
- **AI tone** — firm positions where facts and authorities permit; uncertainty expressed clearly where law is unsettled or facts incomplete.
- **Limitation periods** — every computed deadline carries a verification warning (state-specific laws, public-officer exceptions, continuing injury, fraud/concealment).
- **Filing fees** — amber warning that registry fees change without notice and must be confirmed.
- **Disclaimer footer** — every AI output and export carries a disclaimer that the content is AI-generated and does not constitute legal advice; full terms live in the Terms of Service.

---

## Security Architecture

| Control | Implementation | Status |
|---|---|---|
| Password hashing | PBKDF2-HMAC-SHA256 · 260,000 iterations | ✅ |
| Timing-safe verification | `hmac.compare_digest()` throughout | ✅ |
| Login rate limiting | 5 attempts → 5-minute lockout | ✅ |
| Failed login logging | `LOGIN_FAILED` audit with attempt count | ✅ |
| Prompt-injection protection | `sanitize_doc_context()` — pattern detection + hard delimiters | ✅ |
| Credential encryption | Fernet symmetric encryption for SMTP passwords | ✅ |
| Session management | 30-day tokens · server-side storage · individual revocation | ✅ |
| Per-user data isolation | Namespaced `u:{user_id}:` keys in all DB queries | ✅ |
| Audit trail | 17 event types · hash-chained · admin-viewable · CSV export | ✅ |
| XSS protection | `esc()` wrapper (`html.escape()`) on all user content in HTML | ✅ |
| Graceful AI degradation | Auto fallback if thinking / web-search tool is rejected | ✅ |

---

## Export Support

| Format | Notes |
|---|---|
| **TXT** | Plain text with firm header, footer, and disclaimer |
| **HTML** | Styled web page with firm branding |
| **PDF** | Print-ready with firm name and generation timestamp |
| **DOCX** | Editable Word document with firm branding and optional letterhead footer |
| **Case Bundle** | Single PDF/TXT combining case facts, all saved analyses, and hearings — one click from the Cases tab |
| **Court Process Checklist** | TXT export of the AI-generated filing checklist |
| **Authority Verification Report** | TXT report of all citations found, their status, problems, and fixes |

Firm name, lawyer details, bank details, and letterhead footer are pulled from **Profile** and **Firm Admin Settings** and applied to all exports automatically.

---

## Tech Stack

| Core | Purpose |
|---|---|
| Python 3.12 | Runtime |
| Streamlit | UI framework |
| Google Gemini 2.5 API | AI generation, native thinking, and live Google Search grounding |
| Pandas | Data handling |
| PostgreSQL + psycopg2 | Persistent storage |
| cryptography (Fernet) | SMTP credential encryption |

| Optional | Purpose |
|---|---|
| Plotly | Charts — AI usage visualisation |
| pdfplumber | PDF document import |
| python-docx | DOCX import and export |
| fpdf2 | PDF export |
| openpyxl | Excel import |

---

## Project Structure

```text
.
├── .streamlit/
│   └── secrets.toml               # API key, database URL, encryption key (not committed)
├── app.py                         # Streamlit entry point + navigation routing
├── lexi/                          # Application package
│   ├── runtime.py                 # Guarded imports, BRAND_LABEL / __version__
│   ├── ai.py                      # Core generate(): thinking, web grounding, quality gate
│   ├── helpers.py                 # build_system_prompt, run_* task helpers, session state
│   ├── prompts.py                 # Prompt loader (prompt_data/*.txt)
│   ├── citations.py               # Verified case DB + citation audit + repealed/foreign scans
│   ├── web_search.py              # Live online case search + one-click citation verifier
│   ├── database.py / migrator.py  # PostgreSQL persistence + migrations
│   ├── crypto.py / auth.py        # Encryption + authentication
│   ├── themes.py                  # Theme engine (CSS, scrollbars, contrast)
│   ├── exports.py                 # TXT / HTML / PDF / DOCX export
│   ├── pages/                     # One module per screen (ai, research, cases, news, …)
│   └── prompt_data/               # External prompt templates
├── tests/                         # pytest smoke + unit tests
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

---

## Requirements

```text
streamlit
google-genai>=1.20.0
psycopg2-binary>=2.9.9
cryptography>=42.0.0
pandas>=2.0.0
plotly>=5.18.0
pdfplumber>=0.10.0
python-docx>=1.1.0
fpdf2>=2.7.0
openpyxl>=3.1.0
python-dateutil>=2.8.2
```

> `google-genai>=1.20.0` is required for stable native "thinking" (`ThinkingConfig`) and the Google Search grounding tool.

---

## Deployment Notes

- Designed for **Streamlit Cloud** and local deployment; runs on **Python 3.12**
- A **PostgreSQL database** (e.g. Neon free tier) is required for persistent storage; tables auto-create on first run
- Set in `.streamlit/secrets.toml`: the **Gemini API key**, the **database URL**, and the **`ENCRYPTION_KEY`** (needed before the first user saves notification settings)
- **Live web grounding** requires the Gemini API key to have **Google Search grounding** enabled (standard Google AI Studio keys include a free daily allowance, then billable). The app falls back to verified-database grounding if a search is unavailable.
- On free Streamlit infrastructure, occasional cold-start delays are normal; the database connection auto-reconnects after a sleep cycle
- The app's persistent database is PostgreSQL configured through `DATABASE_URL` (for example, Neon); Supabase is not required by the application.
- The deployed app exposes a lightweight health check at `/?healthcheck=1`. It returns `OK` before loading the AI or database layers and is suitable for uptime monitoring.
- The repository includes `.github/workflows/supabase-keep-alive.yml`, which makes a read-only Supabase Data API database check every six hours (02:17, 08:17, 14:17, and 20:17 UTC). It queries at most one `statute_chunks` ID using HEAD, returns no records, and respects row-level security. Set the GitHub Actions repository secret `SUPABASE_ANON_KEY`; do not use a service-role key or disable RLS. Missing credentials, unavailable tables, denied requests, and unexpected HTTP statuses fail the workflow. It can also be run manually and runs automatically when its workflow file changes on main.
- Successful checks reduce inactivity-pausing risk but cannot guarantee Free Plan availability. Public GitHub repository schedules can be disabled after 60 days without repository activity, and scheduled runs can be delayed. For an independent free scheduler, cron-job.org can make the same HEAD request every six hours to `https://muywyqrcogqprziijugl.supabase.co/rest/v1/statute_chunks?select=id&limit=1`, with the anonymous key in an `apikey` header and failure notifications enabled. Never put keys in the URL. This external scheduler requires separate setup; it is not provisioned by this repository.

---

## Quality & CI

Every change is gated by a CI pipeline (also reproducible locally on Python 3.12):

- **byte-compile** — `python -m compileall app.py lexi/ tests/`
- **ruff** — lint
- **mypy** — strict type-checking on `lexi/ai.py` and `lexi/migrator.py`
- **pytest** — smoke + unit tests (citations, sanitisation, security, calculators, page wiring)

---

## Who This Is For

Lawyers, litigation teams, solo practitioners, chambers, and legal-operations professionals working within the **Nigerian legal system** who need AI-assisted research, drafting, contract review, matter tracking, task management, citation verification, and document handling in one place — with confidence that the AI **reasons before it answers**, can be put **online to cite real, current sources with links**, is grounded in primary Nigerian law, and produces output that is **independently verifiable** before it reaches a courtroom or a client.

---

## Disclaimer

LexiAssist provides **AI-generated legal information** for workflow support, drafting, research, and practice management. It does **not** constitute legal advice. Limitation periods in Nigeria are governed largely by **state-specific laws** — always verify against the applicable statute for the relevant jurisdiction. All statutes, procedural rules, case citations, and authorities generated by this tool must be **independently verified** before reliance in court or in advice to clients. Live web sources should be opened and confirmed; the verification databases cover landmark decisions and key statutes but are not exhaustive — always confirm against **NWLR**, **LPELR**, or **Law Pavilion** before filing.

---

<p align="center">
  <strong>LexiAssist 2.0</strong> · Built for Nigerian lawyers · <a href="https://lexiassist-legal-world.streamlit.app">Try it live</a> · Powered by Google Gemini · Reasoning + live-web grounded · Secured with Fernet encryption · Private Beta
</p>
