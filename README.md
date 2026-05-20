[![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-4285F4?logo=google&logoColor=white)](https://ai.google.dev)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791?logo=postgresql&logoColor=white)](https://neon.tech)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Jurisdiction](https://img.shields.io/badge/Jurisdiction-Nigeria%20🇳🇬-008751)](#)
[![Security](https://img.shields.io/badge/Security-Fernet%20Encrypted-6366f1)](#)
[![RAG](https://img.shields.io/badge/Grounding-Statute%20RAG-059669)](#)
[![Beta](https://img.shields.io/badge/Status-Private%20Beta-f59e0b)](#)
[![Fixes](https://img.shields.io/badge/Hotfix-v9.1.1-dc2626)](#)

# ⚖️ LexiAssist v9.1.1

**AI-powered legal workspace for Nigerian lawyers — with citation verification, authority verification mode, task management, court process checklists, prompt-injection protection, structured AI output, firm admin settings, theme-aware UI throughout, and a comprehensive security hardening update.**

LexiAssist combines a jurisdiction-focused AI legal assistant with a full law-office management suite — covering research, drafting, case tracking, task management, client management, billing, contract review, document handling, AI cost tracking, persistent cloud storage, and export-ready firm branding — deployed on Streamlit and purpose-built for the **Nigerian legal system**.

<p align="center">
  <a href="https://lexiassist-legal-world.streamlit.app">
    <img src="https://img.shields.io/badge/🚀%20Launch%20App-LexiAssist%20Live-059669?style=for-the-badge&logoColor=white" alt="Launch LexiAssist">
  </a>
</p>

<p align="center">
  👉 <strong><a href="https://lexiassist-legal-world.streamlit.app">https://lexiassist-legal-world.streamlit.app</a></strong>
</p>

---

## What's New in v9.1

| Feature | Description |
|---|---|
| 🔍 Authority Verification Mode | Paste any AI-generated text — LexiAssist extracts every case, statute, and rule cited and checks each one: Verified · Unverified · Repealed · Foreign · Possible Hallucination · Needs Section Number |
| ✅ Task Manager | Full task tracking with due dates, priority (High/Medium/Low), linked cases, assigned lawyer, overdue auto-detection, and inline status updates |
| 📋 Court Process Checklist | AI-generated step-by-step filing checklist for any matter type × court × state — covers pre-action, documents, filing steps, frontloading, service, common defects, and estimated timeline |
| 🗂️ Structured AI Output | Every AI response can be re-analysed into three colour-coded sections: ✅ Verified Law · 🧠 Analysis · ⚠️ To Confirm — reducing hallucination risk and malpractice exposure |
| 🛡️ Prompt-Injection Protection | `sanitize_doc_context()` wraps all uploaded document text in hard delimiters and detects 9 known injection patterns before passing content to the AI |
| ⚙️ Firm Admin Settings | Admin-only configuration panel: default hourly rate, VAT/WHT rates, billing currency, default court/jurisdiction, monthly AI budget, allowed models, letterhead footer, bank details, and user permission controls |
| 📅 Home Dashboard — Next 7 Days | Live panel on the home page showing upcoming tasks and hearings due within 7 days, with overdue task count in the stats row (turns red when non-zero) |
| 🔒 Login Rate Limiting | Accounts locked for 5 minutes after 5 failed login attempts — with remaining-attempt warnings from attempt 3 |
| 📊 Expanded Audit Log | 15+ event types now recorded: LOGIN · LOGIN_FAILED · LOGOUT · CASE_DELETED · CLIENT_DELETED · USER_CREATED · USER_DELETED · PASSWORD_RESET · ROLE_CHANGED · ANALYSIS_SAVED · TASK_CREATED · TASK_UPDATED · TASK_DELETED · FIRM_SETTINGS_UPDATED |
| 🔬 Legal Safety Updates | AI tone instruction revised — firm positions where facts permit, uncertainty expressed where law is unsettled; FREP limitation period carries nuance disclaimer; verification warning rendered after every computed deadline |
| 📌 Verified Cases Bootstrap | Admin-added verified cases now load from the database at session start — custom cases survive server restarts without redeployment |
| 🎨 Rich Empty States | Cases, Clients, and Tasks pages now show illustrated empty-state cards with Nigerian law examples and a clear call to action |

---

## Features

### 🤖 AI Legal Assistant
- **AI Legal Assistant** — analysis, drafting, research, procedural guidance, statutory interpretation, strategic advisory, and contract review
- **Four response modes** — Brief · Standard · Comprehensive · Ultra (up to 131K tokens)
- **Streaming output** — responses appear word-by-word via `generate_content_stream()` — no spinner waiting
- **Quality gate** — silent self-critique; score < 5/10 triggers automatic one-shot regeneration with a stricter prompt
- **4-axis confidence scores** — Statutory Grounding · Case Law Support · Procedural Certainty · Position-taking, displayed as coloured progress bars after every response
- **RAG grounding** — 18 verified Nigerian statute provisions retrieved by keyword similarity and injected into every system prompt before generation
- **Structured Output panel** — click ⚡ Generate Structured View on any response to categorise it into three columns: ✅ Verified Law · 🧠 Analysis · ⚠️ To Confirm
- **Citation audit** — every AI response scanned for Nigerian citations; verified against 150+ case database; unverified citations flagged inline with ⚠️
- **Contract Review mode** — clause-by-clause risk analysis with red flag matrix and signability grade
- **Contract Version Diffing** — paste V1 and V2; get a visual HTML line-by-line diff plus AI explanation of the legal significance of every change
- **Save to Case** — attach AI outputs directly to case files; every save recorded in the audit log as `ANALYSIS_SAVED`
- **Analysis Comparison** — compare two AI sessions and get an AI verdict on the stronger analysis
- **Issue Spotting** — rapid decomposition of legal issues before full analysis
- **Follow-up Questions** — continue any analysis with full context preserved
- **Case Strength Meter** — AI-assessed win-probability percentage bars per party, complexity rating, and single most critical immediate action
- **Document upload with injection protection** — PDF, DOCX, TXT, RTF, XLSX, XLS, CSV, JSON — all document text sanitised through `sanitize_doc_context()` before reaching the AI

### 🔍 Authority Verification Mode
- Paste any AI-generated legal argument, draft pleading, or research memo
- LexiAssist extracts every case, statute, regulation, rule, and constitutional provision cited
- Each authority checked against the verified Nigerian case database and statute library
- Status per citation: **Verified** · **Unverified** · **Possible Hallucination** · **Repealed** · **Foreign** · **Needs Section Number** · **Check Spelling**
- Confidence score (0–100%) and specific fix suggestion for every authority
- Summary badge row: count per status category at a glance
- Downloadable TXT verification report with full disclaimer

### 🛡️ Citation Verification Engine
- Database of 150+ verified landmark decisions from the Supreme Court and Court of Appeal
- Covers: Constitutional · Electoral · Contract · Land · Evidence · Criminal · Employment · Oil & Gas · Banking · Tort · Company · Tax · Customary Law · Procedure
- Regex patterns covering all major Nigerian report series: NWLR · LPELR · SCNLR · SC · All NLR · NMLR · NCLR · ECSLR · FHCLR · NICN
- Verified citations shown with ✅ badge; unverified citations shown with ⚠️ [UNVERIFIED — CHECK BEFORE FILING] inline
- Citation audit panel with collapsible verified/unverified case lists — court, year, and ratio shown for each
- New cases added via **Admin → 📚 Law Updates → ⚖️ New Cases** are persisted to the database and loaded into every session automatically — no restart needed

### ✅ Task Manager
- Create tasks with title, due date, priority (High/Medium/Low), status, linked case, assigned lawyer, and notes
- Overdue auto-detection — tasks past their due date that are not marked Done are flagged red automatically
- 4-badge summary row per view: Overdue · Due Today · High Priority · Completed
- Filters by status, priority, and linked case — sorted overdue-first then by date
- Inline status and priority updates without leaving the page
- All task actions (create / update / delete) recorded in the audit log
- Persisted to the database via `persist("tasks")` — survives page reloads and server restarts

### 📋 Court Process Checklist
- Select court (13 options), matter type (15 options), acting-for party, state rules, and brief facts
- AI generates a structured, rule-cited checklist covering:
  - Pre-action requirements (mandatory vs recommended, with authority)
  - Documents to file (with copy counts and court rule references)
  - Filing steps (with deadlines)
  - Frontloading requirements
  - Service method, timeframe, and authority
  - Common filing defects and their consequences
  - Estimated timeline to first hearing
- Downloadable TXT export with full disclaimer
- Every step cites the applicable court rule, order, or statute

### 📋 Legal Data Currency
- `LEGAL_DATA_VERSION` constant tracks the current state of the law with update date, last act incorporated, and notes
- Key amendments hardcoded in the AI system prompt: ACA 2023 · Electoral Act 2022 · CAMA 2020 · BOFIA 2020 · PIA 2021 · Copyright Act 2022 · Police Act 2020
- AI instructed to take firm positions where facts and authorities permit; to express uncertainty clearly where law is unsettled, facts are incomplete, or authority requires verification
- **Admin → 📚 Law Updates** dashboard: add repealed laws, recent amendments, and new verified cases through a UI — all entries injected into AI prompts automatically and persisted across restarts

### 📜 Audit Log
- 15+ event types recorded with colour-coded badges:

| Event | Colour | Triggered by |
|---|---|---|
| `AI_QUERY` | Purple | Every AI generation |
| `ANALYSIS_SAVED` | Blue | Saving AI output to a case |
| `LOGIN` | Amber | Successful sign-in |
| `LOGIN_FAILED` | Red | Failed sign-in attempt (includes attempt count) |
| `LOGOUT` | Grey | Sign-out |
| `CASE_ADDED` | Green | New case created |
| `CASE_DELETED` | Red | Case deleted (includes case title) |
| `CLIENT_ADDED` | Teal | New client created |
| `CLIENT_DELETED` | Red | Client deleted |
| `USER_CREATED` | Green | New user registered or admin-created |
| `USER_DELETED` | Red | Admin deletes a user account |
| `PASSWORD_RESET` | Purple | Admin resets a user's password |
| `ROLE_CHANGED` | Purple | Admin promotes or demotes a user (old → new role) |
| `TASK_CREATED` | Green | New task created |
| `TASK_UPDATED` | Blue | Task status or priority changed |
| `TASK_DELETED` | Red | Task deleted |
| `FIRM_SETTINGS_UPDATED` | Purple | Admin saves firm-wide settings |

- Hash-chained entries — each entry's hash covers its own content plus the previous entry's hash, making retroactive tampering detectable
- Admin-viewable at **Admin → 🗂️ Audit Log** with action-type filtering and CSV export

### 🔒 Security
- **Fernet-encrypted SMTP credentials** — Gmail App Passwords encrypted with `cryptography.fernet` before database storage; decrypted only at send-time, only in memory
- **PBKDF2-HMAC-SHA256** password hashing (260,000 iterations)
- **`hmac.compare_digest()`** used throughout password verification — prevents timing-based enumeration attacks
- **Login rate limiting** — 5 failed attempts triggers a 5-minute lockout; attempt 3+ shows remaining-attempts warning; all failures logged to audit
- **Prompt-injection protection** — `sanitize_doc_context()` strips control characters, detects 9 injection patterns, and wraps document text in hard delimiters before it reaches the AI
- **Persistent session tokens** — 30-day remember-me tokens stored server-side; revocable individually or all at once
- **Per-user data isolation** — all data namespaced to `u:{user_id}:` in the key-value store
- **Active Sessions viewer** — see and revoke any active session from Profile → 🔐 Security

### ⚙️ Firm Admin Settings
Admin-only tab under **👤 Profile → ⚙️ Firm Admin Settings**:
- **Billing**: default hourly rate (₦), billing currency (NGN/USD/GBP/EUR), VAT rate (%), WHT rate (%) — with live billing preview showing sample invoice calculation
- **Jurisdictions**: default court and state — pre-filled throughout the app
- **AI & Budget**: monthly AI spend limit (₦0 = no limit), allowed model whitelist
- **Letterhead & Exports**: default footer text, bank name, account number, account name/sort code
- **User Permissions**: toggle self-registration, require admin approval for new accounts, allow users to set their own API key
- All changes persisted and recorded as `FIRM_SETTINGS_UPDATED` in the audit log

### 🔍 Global Search
- Single search field queries all four data stores simultaneously
- Searches: Case titles · Suit numbers · Court · Notes · Client names · Emails · Saved analysis queries and responses · AI session history
- Results grouped by category with keyword highlighting

### 🏢 Practice Management
- **Case & hearing management** — track suits, courts, deadlines, hearings, lifecycle stages, and saved analyses per case
- **Task Manager** — full task lifecycle with overdue detection, priority flags, and case linking (see above)
- **Home dashboard** — stats row including Overdue Tasks (red when non-zero) and Open Tasks; live Next 7 Days panel showing upcoming tasks and hearings
- **Rich empty states** — Cases, Clients, and Tasks pages show illustrated cards with Nigerian law examples and clear calls to action when no data exists
- **Case Bundle Export** — one-click PDF/TXT download of a complete case file: facts, all saved analyses, billing entries, and hearing dates
- **Fuzzy Conflict Checker** — pre-screens names at ≥45% token-set similarity before sending to AI; catches abbreviations, shortened names, and typographical variants
- **Client records & billing** — manage clients, log time entries, generate invoices, billing reports with charts
- **AI Cost Tracker** — per-call Gemini usage logging with daily/monthly summaries, charts, and CSV export
- **Document support** — import PDF, DOCX, TXT, RTF, XLSX, XLS, CSV, and JSON as AI context; all sanitised against prompt injection
- **Export** — download outputs as TXT, HTML, PDF, or DOCX with firm branding and disclaimer footer
- **Document templates** — built-in and custom templates with automatic `[PLACEHOLDER]` detection, fill form, and AI polish
- **Full backup/restore** — export and restore all app data as JSON from the sidebar or Profile tab

### 📧 Hearing Reminder Emails
- Automatic email alerts for hearings within 1 or 7 days
- HTML emails with case title, suit number, court, date, and days remaining
- Configurable via Gmail App Password — stored encrypted, no third-party service needed
- Managed from **Profile → 🔔 Notifications**

### 🚀 Onboarding Wizard
- 4-step interactive wizard shown to new users on the Home tab
- Steps auto-complete based on real data (firm profile saved · client added · case created · AI query run)
- Progress bar with live percentage
- Dismissable manually; disappears permanently once all 4 steps are complete

---

## Navigation

The app uses **grouped sidebar navigation** with 5 sections, each containing its own set of tabs:

| Section | Pages |
|---|---|
| ⚖️ **Practice** | 🏠 Home · 🧠 AI Assistant · 📚 Research · 📝 Notes → Brief |
| 📁 **Matters** | 📁 Cases · ✅ Tasks · ⚡ Lifecycle · 📜 Pleadings · 📅 Calendar · 🔍 Conflict Check |
| 👥 **Clients & Billing** | 👥 Clients · 💰 Billing · ⚖️ Fee Calculator |
| 🔧 **Tools** | 🔧 Tools · 🎯 Witness Prep · 🤝 Settlement · 🔎 Due Diligence · 📋 Templates · 📰 Legal News · 🔎 Search |
| 👤 **Account** | 👤 Profile · 🛡️ Admin *(admin only)* |

### 🔧 Tools — Tab Reference

| Tab | What it does |
|---|---|
| ⏳ Limitation Periods | Reference table + AI deadline calculator with jurisdiction-specific verification warnings |
| 🧮 Deadline Calculator | Compute limitation deadlines from date of cause of action with special-notes warnings |
| 🏛️ Court Hierarchy | Visual hierarchy of Nigerian courts with jurisdiction notes |
| 📜 Legal Maxims | Searchable library of maxims with custom additions |
| 🛡️ AML / SCUML | AML/CFT compliance checker for financial transactions |
| 📋 Court Process Checklist | AI-generated filing checklist — 15 matter types × 13 courts × 11 state rule sets |
| 🔍 Authority Verification | Paste any AI text → every citation verified and classified |

---

## Legal Safety

LexiAssist is designed for use by qualified Nigerian lawyers, not as a direct-to-client service. Several layers of protection are built in:

- **AI tone**: The AI takes firm positions where facts and authorities permit. Where facts are incomplete, law is unsettled, or authority requires verification, uncertainty is expressed and what must be verified is identified.
- **Limitation periods**: Every computed deadline carries a verification warning noting that limitation periods vary by jurisdiction, cause of action, public officer exceptions, continuing injury, fraud/concealment, and applicable State Limitation Law.
- **FREP nuance**: The Fundamental Rights Enforcement limitation period entry includes a disclaimer noting the continuing violation doctrine, court discretion, and state-specific interpretation.
- **Filing fees**: Every court filing fee calculation displays an amber warning that registry fees change without notice and must be confirmed before filing or quoting to any client.
- **Beta banner**: A visible amber "Private Beta" banner on the home page reminds all users to independently verify all authorities, limitation periods, and legal positions before advising any client.
- **Structured output**: The ⚠️ To Confirm column in the Structured Output panel explicitly flags everything requiring independent verification.
- **Disclaimer footer**: Every AI output and export carries a disclaimer that the content is AI-generated and does not constitute legal advice.

---

## Security Architecture

| Control | Implementation | Status |
|---|---|---|
| Password hashing | PBKDF2-HMAC-SHA256 · 260,000 iterations | ✅ |
| Timing-safe verification | `hmac.compare_digest()` throughout | ✅ |
| Login rate limiting | 5 attempts → 5-minute lockout | ✅ |
| Failed login logging | `LOGIN_FAILED` audit with attempt count | ✅ |
| Prompt-injection protection | `sanitize_doc_context()` — 9 pattern detection + hard delimiters | ✅ |
| Credential encryption | Fernet symmetric encryption for SMTP passwords | ✅ |
| Session management | 30-day tokens · server-side storage · individual revocation | ✅ |
| Per-user data isolation | Namespaced `u:{user_id}:` keys in all DB queries | ✅ |
| Audit trail | 17 event types · hash-chained · admin-viewable · CSV export | ✅ |
| XSS protection | `esc()` wrapper (`html.escape()`) on all user content in HTML | ✅ |
| Streamlit version pinned | `streamlit==1.43.2` in `requirements.txt` | ✅ |
| Session token in URL | Token written to query param for auto-login — full cookie migration pending | ⚠️ |

---

## Export Support

All AI outputs can be exported in the following formats:

| Format | Notes |
|---|---|
| **TXT** | Plain text with firm header, footer, and disclaimer |
| **HTML** | Styled web page with firm branding |
| **PDF** | Print-ready with firm name and generation timestamp |
| **DOCX** | Editable Word document with firm branding and optional letterhead footer |
| **Case Bundle** | Single PDF/TXT combining case facts, all saved analyses, hearings, and billing — one click from the Cases tab |
| **Court Process Checklist** | TXT export of AI-generated filing checklist with all steps and authorities |
| **Authority Verification Report** | TXT report of all citations found, their status, problems, and fixes |

Firm name, lawyer details, bank details, and letterhead footer are pulled from **Profile** and **Firm Admin Settings** and applied to all exports automatically.

---

## Tech Stack

| Core | Purpose |
|---|---|
| Python 3.11 | Runtime |
| Streamlit 1.43.2 | UI framework (pinned) |
| Google Gemini API | AI generation and quality gate |
| Pandas | Data handling |
| PostgreSQL + psycopg2 | Persistent storage |
| cryptography (Fernet) | SMTP credential encryption |

| Optional | Purpose |
|---|---|
| Plotly | Charts — cost visualisation and billing reports |
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
├── .gitignore                     # Git ignore rules
├── app.py                         # Entire application (single-file, ~13,000 lines)
├── requirements.txt               # Pinned Python dependencies
├── runtime.txt                    # Python version for Streamlit Cloud
├── LexiAssist_LaunchChecklist.md  # 3-phase launch and security checklist
└── README.md                      # This file
```

---

## Requirements

```text
streamlit==1.43.2
google-genai>=1.0.0
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

---

## Deployment Notes

- Designed for **Streamlit Cloud** and local deployment
- A **PostgreSQL database** (e.g. Neon free tier) is required for persistent storage
- On first deployment, all database tables are created automatically — no manual migration needed
- The `ENCRYPTION_KEY` must be set in secrets before the first user saves notification settings
- **Streamlit version is pinned** to `1.43.2` — do not upgrade without testing UI and `data-testid` selectors
- On free Streamlit infrastructure, occasional cold-start delays are normal after inactivity
- The database connection auto-reconnects if it goes stale after a sleep cycle
- Admin-added verified cases and law updates are bootstrapped into session state on every login — no restart needed after admin updates

---

## Who This Is For

Lawyers, litigation teams, solo practitioners, chambers, and legal operations professionals working within the **Nigerian legal system** who need AI-assisted legal research, drafting, contract review, matter tracking, task management, billing, citation verification, and document management in one place — with confidence that the AI is grounded in primary Nigerian law, its citations are checked before they reach a courtroom, and every generated output is independently verifiable before it goes anywhere near a client.

---

## Changelog

### v9.1.1 — May 2026 (Hotfix)
- **Sidebar restored** — login-screen `display:none` CSS was persisting into the authenticated session; fixed by injecting `display:flex!important` override at the top of `render_sidebar()` on every rerun
- **NameError crash on Tools page** — Firm Admin Settings block was accidentally placed inside `render_due_diligence()` where `_is_admin` and `tab_firm_admin` are not defined; removed from there
- **Firm Admin Settings now functional** — block correctly moved into `render_profile()` where tab variables are defined; uses `SUPPORTED_MODELS` for model list
- **Private Beta banner** — replaced hardcoded `#fffbeb`/`#92400e` with `var(--la-bg2)`/`var(--la-text)`/`var(--la-text2)` — now readable in all 5 themes
- **Navigation speed restored** — removed 5 redundant `st.rerun()` calls from sidebar widgets (mode, theme, font size, high contrast, reduce motion); Streamlit already reruns on widget change — these were each triggering a double render
- **Due Diligence result box** — replaced hardcoded white `#f8fafc` background with `response-box` CSS class
- **Settlement tabs** — replaced 5 hardcoded white/tinted backgrounds with `var(--la-card)` and `var(--la-text)` — now theme-aware
- **Footer colours** — `#64748b` → `var(--la-text2)`, `#e2e8f0` → `var(--la-border)`
- **Additional hardcoded whites** — witness prep result box and login footer text colour also converted to theme CSS variables

### v9.1 — May 2026
- **Authority Verification Mode** — paste any legal text; every citation classified: Verified · Unverified · Repealed · Foreign · Possible Hallucination · Needs Section Number · Check Spelling; confidence score and fix per citation; downloadable TXT report
- **Task Manager** — full task lifecycle under 📁 Matters: priority, due dates, linked cases, assigned lawyer, overdue auto-detection, audit logging
- **Court Process Checklist** — AI-generated filing checklist for 15 matter types × 13 courts × 11 state rule sets; all steps cite applicable rules and orders; downloadable TXT export
- **Structured AI Output** — ⚡ Generate Structured View button on every response; three-column panel: ✅ Verified Law · 🧠 Analysis · ⚠️ To Confirm
- **Prompt-injection protection** — `sanitize_doc_context()` applied to all uploaded document text before AI processing
- **Firm Admin Settings** — admin-only tab: hourly rate, VAT/WHT, currency, AI budget, allowed models, letterhead footer, bank details, user permissions
- **Home dashboard** — stats row now includes Overdue Tasks and Open Tasks; Next 7 Days panel shows upcoming tasks and hearings
- **Login rate limiting** — 5-attempt lockout for 5 minutes; remaining-attempts warning from attempt 3
- **Expanded audit log** — 17 event types including LOGIN_FAILED, LOGOUT, CASE_DELETED, CLIENT_DELETED, USER_CREATED, USER_DELETED, PASSWORD_RESET, ROLE_CHANGED, ANALYSIS_SAVED, TASK_CREATED, TASK_UPDATED, TASK_DELETED, FIRM_SETTINGS_UPDATED; all colour-coded
- **AI tone safeguard** — revised IDENTITY_CORE and Settlement prompts: firm positions where facts permit; uncertainty expressed where law is unsettled or facts are incomplete
- **Limitation period safety** — FREP nuance disclaimer in data; AI prompt instructs model to flag jurisdiction-specific exceptions; verification warning rendered in UI after every computed deadline
- **Verified cases bootstrap** — custom admin-added cases loaded from DB at session start; survive server restarts
- **Rich empty states** — Cases, Clients, Tasks pages; illustrated cards with Nigerian law examples
- **Streamlit pinned** to `1.43.2` in `requirements.txt`
- **hex comparison bug fixed** — `int(t["bg"][1:3], 16) < 0x33` replaces string comparison in theme engine
- **`st.html()` replaced** with `st.components.v1.html()` for cross-version stability
- **Beta verification banner** — visible amber banner on home page

### v9.0 — May 2026
- Citation verification engine with 150+ verified Nigerian landmark cases
- Streaming AI responses via `generate_content_stream()`
- Quality gate: silent self-scoring and auto-regeneration on score < 5/10
- 4-axis confidence scoring panel on every Standard/Comprehensive response
- Fernet-encrypted SMTP credential storage
- Immutable hash-chained audit log with admin viewer and CSV export
- RAG statute grounding — 18 core provisions injected into every AI prompt
- Fuzzy conflict pre-screening at ≥45% token-set similarity
- Global search across all cases, clients, analyses, and history
- Case bundle export (PDF + TXT)
- Contract version diffing (visual HTML diff + AI legal significance)
- Template `[PLACEHOLDER]` auto-detection with fill form and AI polish
- Legal data versioning and currency dashboard
- 4-step onboarding wizard with live progress tracking
- Grouped sidebar navigation (5 sections)
- Legal Currency Dashboard in Admin for runtime law updates
- Active Sessions viewer with individual session revocation

### v8.0 — Previous
- Initial public release
- AI Legal Assistant with Brief / Standard / Comprehensive modes
- Case management, client records, billing, and invoicing
- Case Strength Meter
- Limitation Deadline Calculator
- Quick Precedent Finder
- Notes → Brief Converter
- Hearing reminder emails
- 5 UI themes
- Multi-user authentication with PBKDF2 password hashing and 30-day persistent sessions

---

## Disclaimer

LexiAssist provides **AI-generated legal information** for workflow support, drafting, research, and practice management. It does **not** constitute legal advice. Limitation periods in Nigeria are governed largely by **state-specific laws** — always verify against the applicable statute and applicable State Limitation Law for the relevant jurisdiction before advising any client. All statutes, procedural rules, case citations, and authorities generated by this tool must be **independently verified** before reliance in court or in advice to clients. The citation verification and authority verification databases cover landmark decisions and key statutes but are not exhaustive — always confirm citations against **NWLR**, **LPELR**, or **Law Pavilion** before filing.

---

<p align="center">
  <strong>LexiAssist v9.1.1</strong> · Built for Nigerian lawyers · <a href="https://lexiassist-legal-world.streamlit.app">Try it live</a> · Powered by Google Gemini · Secured with Fernet encryption · Private Beta
</p>
