from __future__ import annotations

import html
import io
import json
import logging
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime
from typing import Any

import google.generativeai as genai
import pandas as pd
import plotly.express as px
import streamlit as st

try:
    import pdfplumber
    PDF_SUPPORT = True
except Exception:
    PDF_SUPPORT = False

try:
    from docx import Document
    DOCX_SUPPORT = True
except Exception:
    DOCX_SUPPORT = False

try:
    import openpyxl  # noqa: F401
    XLSX_SUPPORT = True
except Exception:
    XLSX_SUPPORT = False

try:
    import PyPDF2
    PYPDF2_SUPPORT = True
except Exception:
    PYPDF2_SUPPORT = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("LexiAssist")

st.set_page_config(
    page_title="LexiAssist — Elite Legal Practice Management",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "# LexiAssist v6.1\nElite AI Legal Reasoning for Nigerian Lawyers."},
)

# =============================================================================
# CONSTANTS
# =============================================================================
DB_PATH = "lexiassist_history.db"
MAX_DOC_INPUT_CHARS = 12000

CASE_STATUSES = ["Active", "Pending", "Completed", "Archived"]
CLIENT_TYPES = ["Individual", "Corporate", "Government"]

TASK_TYPES: dict[str, dict[str, str]] = {
    "drafting":       {"label": "Document Drafting",       "desc": "Contracts, pleadings, affidavits",                  "icon": "📄"},
    "analysis":       {"label": "Legal Analysis",          "desc": "Issue spotting, CREAC deep reasoning",              "icon": "🔍"},
    "research":       {"label": "Legal Research",          "desc": "Case law, statutes, authorities",                   "icon": "📚"},
    "procedure":      {"label": "Procedural Guidance",     "desc": "Court filing, evidence rules, practice directions", "icon": "📋"},
    "interpretation": {"label": "Statutory Interpretation", "desc": "Analyze and explain legislation",                  "icon": "⚖️"},
    "advisory":       {"label": "Client Advisory",         "desc": "Strategic advice, options memo, risk matrix",       "icon": "🎯"},
    "general":        {"label": "General Query",           "desc": "Ask anything legal-related",                        "icon": "💬"},
}

RESPONSE_MODES = {
    "quick": {
        "label": "⚡ Quick",
        "desc": "Short, direct, strictly on-point",
        "max_tokens": 900,
        "temperature": 0.15,
    },
    "standard": {
        "label": "🧭 Standard",
        "desc": "Balanced explanation with only necessary detail",
        "max_tokens": 2200,
        "temperature": 0.2,
    },
    "deep": {
        "label": "🔬 Deep",
        "desc": "Full senior-lawyer analysis",
        "max_tokens": 7000,
        "temperature": 0.2,
    },
}

ANSWER_LENGTHS = {
    "short": "Short",
    "medium": "Medium",
    "long": "Long",
}

MODEL_MIGRATION_MAP = {
    "gemini-2.0-flash": "gemini-2.5-flash",
    "gemini-2.0-flash-001": "gemini-2.5-flash",
    "gemini-2.0-flash-lite": "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite-001": "gemini-2.5-flash-lite",
}
SUPPORTED_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
DEFAULT_MODEL = "gemini-2.5-flash"

# =============================================================================
# SYSTEM PROMPTS
# =============================================================================
_MASTER_IDENTITY = """
You are LexiAssist — an elite Nigerian legal AI assistant for practicing lawyers.

JURISDICTION: Nigeria.

NON-NEGOTIABLE BEHAVIOUR RULES:
1. Follow the user's exact instruction and scope.
2. Answer only what was asked. Do not add unnecessary sections.
3. If the user asks for a simple explanation, give a simple explanation.
4. If the user asks for depth, then provide depth.
5. Be concise by default unless the user requests detail.
6. Do not go off-topic.
7. Do not fabricate authorities, statutes, cases, or section numbers.
   If uncertain, say: [Citation to be verified].
8. Where relevant, identify uncertainty briefly and specifically.
9. Use Nigerian law unless the user clearly requests otherwise.
10. Prefer practical usefulness over verbosity.

STYLE RULES:
- Direct.
- Precise.
- Professionally clear.
- No unnecessary flourish.
- No repetition.
"""

ISSUE_SPOTTING_INSTRUCTION = _MASTER_IDENTITY + """
YOUR SOLE TASK: ELITE ISSUE SPOTTING.

Do NOT provide full analysis.

1. List obvious issues.
2. List hidden issues a competent senior lawyer would identify.
3. Note threshold issues first (jurisdiction, limitation, standing, condition precedent).
4. State the top missing facts that materially change outcome.
5. Keep it structured and concise.
"""

AMBIGUITY_INSTRUCTION = _MASTER_IDENTITY + """
YOUR SOLE TASK: IDENTIFY THE TOP "IT DEPENDS" FACTORS.

Do NOT provide full analysis.

For each factor:
- State the variable
- State the outcome if favourable
- State the outcome if unfavourable

Also identify:
- deadline risk
- jurisdiction sensitivity
- key evidence vulnerability

Keep it concise.
"""

ANALYSIS_INSTRUCTION = _MASTER_IDENTITY + """
INSTRUCTION ADHERENCE RULE:
- First determine what the user actually asked.
- Match the depth of the answer to the request.
- If the query is narrow, answer narrowly.
- Do not produce full memo structure unless the query requires it.
- Avoid irrelevant sections.

For deeper analysis where appropriate:
- Identify issues separately.
- Distinguish strict law from equity where relevant.
- State rule, explanation, application, and conclusion.
- Mention strongest counter-argument briefly where it matters.
- Give practical next steps only if useful.
"""

DRAFTING_INSTRUCTION = _MASTER_IDENTITY + """
INSTRUCTION ADHERENCE RULE:
- Draft exactly the document or section requested.
- Do not add unrelated clauses unless necessary for validity or protection.
- If instructions are missing, flag them clearly.
- Keep drafts professional and Nigerian-law compliant.
"""

RESEARCH_INSTRUCTION = _MASTER_IDENTITY + """
INSTRUCTION ADHERENCE RULE:
- Answer the precise research question asked.
- Do not pad the answer with irrelevant material.
- Distinguish settled law from uncertain law.
- Mark uncertain citations as [Citation to be verified].
"""

PROCEDURE_INSTRUCTION = _MASTER_IDENTITY + """
INSTRUCTION ADHERENCE RULE:
- Focus on the procedural question asked.
- State the correct process, court, documents, deadlines, and risks.
- Do not wander into unnecessary substantive law.
"""

INTERPRETATION_INSTRUCTION = _MASTER_IDENTITY + """
INSTRUCTION ADHERENCE RULE:
- Interpret the exact provision asked about.
- Use only necessary interpretive tools.
- Do not over-expand unless the question requires it.
"""

ADVISORY_INSTRUCTION = _MASTER_IDENTITY + """
INSTRUCTION ADHERENCE RULE:
- Give strategic advice tied to the client's objective.
- Present options only where useful.
- Avoid unnecessary theoretical discussion.
"""

GENERAL_INSTRUCTION = _MASTER_IDENTITY + """
INSTRUCTION ADHERENCE RULE:
- Determine what the user actually asked.
- If the query is simple, answer simply.
- If the query requests depth, provide depth.
- Avoid irrelevant sections and repetition.
- Stay tightly on scope.
"""

FOLLOWUP_INSTRUCTION = _MASTER_IDENTITY + """
You are continuing an earlier legal discussion.

Rules:
- Do not repeat the full previous answer.
- Only address what is new in the follow-up.
- Maintain consistency unless the new information requires revision.
- Stay on scope.
"""

SELF_CRITIQUE_INSTRUCTION = _MASTER_IDENTITY + """
Your sole task is to critique the legal analysis for:
- instruction adherence
- issue completeness
- legal accuracy
- analytical depth
- strategic usefulness

Format:
QUALITY ASSESSMENT:
Instruction Adherence: ...
Issue Completeness: ...
Legal Accuracy: ...
Analytical Depth: ...
Strategic Value: ...
OVERALL GRADE: [A/B/C/D]
GAPS:
- ...
"""

TASK_INSTRUCTIONS: dict[str, str] = {
    "analysis": ANALYSIS_INSTRUCTION,
    "drafting": DRAFTING_INSTRUCTION,
    "research": RESEARCH_INSTRUCTION,
    "procedure": PROCEDURE_INSTRUCTION,
    "interpretation": INTERPRETATION_INSTRUCTION,
    "advisory": ADVISORY_INSTRUCTION,
    "general": GENERAL_INSTRUCTION,
}

GEN_CONFIG_DEEP = {"temperature": 0.2, "top_p": 0.88, "top_k": 35, "max_output_tokens": 12000}
GEN_CONFIG_FAST = {"temperature": 0.15, "top_p": 0.85, "top_k": 25, "max_output_tokens": 1000}
GEN_CONFIG_CRITIQUE = {"temperature": 0.15, "top_p": 0.85, "top_k": 25, "max_output_tokens": 800}

LIMITATION_PERIODS = [
    {"cause": "Simple Contract", "period": "6 years", "authority": "Limitation Act, s. 8(1)(a)"},
    {"cause": "Tort / Negligence", "period": "6 years", "authority": "Limitation Act, s. 8(1)(a)"},
    {"cause": "Personal Injury", "period": "3 years", "authority": "Limitation Act, s. 8(1)(b)"},
    {"cause": "Defamation", "period": "3 years", "authority": "Limitation Act, s. 8(1)(b)"},
    {"cause": "Recovery of Land", "period": "12 years", "authority": "Limitation Act, s. 16"},
    {"cause": "Mortgage", "period": "12 years", "authority": "Limitation Act, s. 18"},
    {"cause": "Recovery of Rent", "period": "6 years", "authority": "Limitation Act, s. 19"},
    {"cause": "Enforcement of Judgment", "period": "12 years", "authority": "Limitation Act, s. 8(1)(d)"},
    {"cause": "Maritime Claims", "period": "2 years", "authority": "Admiralty Jurisdiction Act, s. 10"},
    {"cause": "Labour Disputes", "period": "12 months", "authority": "NIC Act, s. 7(1)(e)"},
    {"cause": "Fundamental Rights", "period": "12 months", "authority": "FREP Rules, Order II r. 1"},
]

COURT_HIERARCHY = [
    {"level": 1, "name": "Supreme Court of Nigeria", "desc": "Final appellate court", "icon": "🏛️"},
    {"level": 2, "name": "Court of Appeal", "desc": "Intermediate appellate court", "icon": "⚖️"},
    {"level": 3, "name": "Federal High Court", "desc": "Federal causes", "icon": "🏢"},
    {"level": 3, "name": "State High Courts", "desc": "General civil & criminal jurisdiction", "icon": "🏢"},
    {"level": 3, "name": "National Industrial Court", "desc": "Labour & employment disputes", "icon": "🏢"},
]

LEGAL_MAXIMS = [
    {"maxim": "Audi alteram partem", "meaning": "Hear the other side"},
    {"maxim": "Nemo judex in causa sua", "meaning": "No one should judge their own cause"},
    {"maxim": "Res judicata", "meaning": "A matter already decided cannot be re-litigated"},
    {"maxim": "Stare decisis", "meaning": "Stand by decided cases"},
    {"maxim": "Ubi jus ibi remedium", "meaning": "Where there is a right, there is a remedy"},
    {"maxim": "Pacta sunt servanda", "meaning": "Agreements must be honoured"},
    {"maxim": "Nemo dat quod non habet", "meaning": "No one gives what they do not have"},
    {"maxim": "Locus standi", "meaning": "Right or capacity to bring an action"},
]

# =============================================================================
# CSS
# =============================================================================
_BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*{font-family:'Inter',sans-serif}
.main .block-container{padding-top:1rem;padding-bottom:2rem;max-width:1200px}
.hero{padding:3rem;border-radius:1.5rem;color:white;position:relative;overflow:hidden;
  background:linear-gradient(-45deg,#059669,#0d9488,#065f46,#047857,#0f766e);
  background-size:300% 300%;box-shadow:0 20px 60px rgba(5,150,105,.3)}
.hero h1{font-size:2.7rem;font-weight:800;margin:0;line-height:1.15}
.hero p{font-size:1rem;margin:.75rem 0 0;opacity:.9;max-width:650px;line-height:1.6}
.hero-badge{display:inline-block;padding:.35rem .85rem;background:rgba(255,255,255,.15);border-radius:9999px;font-size:.75rem;font-weight:600;margin-top:1rem;border:1px solid rgba(255,255,255,.2)}
.page-header{padding:1.5rem 2rem;border-radius:1.25rem;margin-bottom:1.5rem;color:white;background:linear-gradient(135deg,#059669,#0d9488);box-shadow:0 12px 40px rgba(5,150,105,.25)}
.page-header h1{margin:0;font-size:2rem;font-weight:700}.page-header p{margin:.25rem 0 0;opacity:.85;font-size:.9rem}
.custom-card,.tmpl-card,.tool-card,.feat-card{background:#fff;border:1px solid #e2e8f0;border-radius:1rem;padding:1.25rem;margin-bottom:1rem;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.stat-card{border-radius:1rem;padding:1.25rem;text-align:center;border:1px solid;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.stat-value{font-size:1.75rem;font-weight:700}.stat-label{font-size:.78rem;margin-top:.3rem;font-weight:600;color:#64748b}
.badge{display:inline-block;padding:.2rem .65rem;border-radius:9999px;font-size:.7rem;font-weight:600}
.badge-success{background:#dcfce7;color:#166534}.badge-warning{background:#fef3c7;color:#92400e}
.badge-info{background:#dbeafe;color:#1e40af}.badge-danger{background:#fee2e2;color:#991b1b}
.response-box{background:#f8fafc;border:1px solid #e2e8f0;border-radius:.75rem;padding:1.5rem;margin:1rem 0;white-space:pre-wrap;font-family:'Georgia','Times New Roman',serif;line-height:1.8;font-size:.95rem}
.issue-spot-box{background:#eff6ff;border:1px solid #bfdbfe;border-left:5px solid #2563eb;border-radius:.75rem;padding:1rem;margin:1rem 0}
.ambiguity-box{background:#fefce8;border:1px solid #fde047;border-left:5px solid #eab308;border-radius:.75rem;padding:1rem;margin:1rem 0}
.critique-box{background:#faf5ff;border:1px solid #d8b4fe;border-left:5px solid #8b5cf6;border-radius:.75rem;padding:1rem;margin:1rem 0}
.disclaimer{background:#fef3c7;border-left:4px solid #f59e0b;padding:1rem 1.25rem;border-radius:0 .5rem .5rem 0;margin-top:1rem;font-size:.85rem}
.cal-event{padding:1rem 1.25rem;border-radius:.75rem;margin-bottom:.75rem;border-left:4px solid;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.cal-event.urgent{border-color:#ef4444;background:#fee2e2}
.cal-event.warn{border-color:#f59e0b;background:#fef3c7}
.cal-event.ok{border-color:#10b981;background:#f0fdf4}
.reasoning-stage{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:.5rem;padding:.5rem 1rem;margin:.25rem 0;font-size:.78rem;color:#065f46;font-weight:600}
.quality-grade{display:inline-block;padding:.3rem .8rem;border-radius:.5rem;font-size:1rem;font-weight:800;margin-left:.5rem}
.grade-a{background:#dcfce7;color:#166534;border:2px solid #22c55e}
.grade-b{background:#dbeafe;color:#1e40af;border:2px solid #3b82f6}
.grade-c{background:#fef3c7;color:#92400e;border:2px solid #f59e0b}
.grade-d{background:#fee2e2;color:#991b1b;border:2px solid #ef4444}
.app-footer{text-align:center;padding:2rem 1rem;color:#64748b;font-size:.85rem;border-top:1px solid #e2e8f0;margin-top:2rem}
#MainMenu{visibility:hidden}footer{visibility:hidden}
</style>
"""

_THEME_EMERALD = """<style>
.stat-card{background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:#bbf7d0}.stat-card .stat-value{color:#059669}
.stat-card.t-blue{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#bfdbfe}.stat-card.t-blue .stat-value{color:#2563eb}
.stat-card.t-purple{background:linear-gradient(135deg,#faf5ff,#f3e8ff);border-color:#e9d5ff}.stat-card.t-purple .stat-value{color:#7c3aed}
.stat-card.t-amber{background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fde68a}.stat-card.t-amber .stat-value{color:#d97706}
</style>"""

THEMES = {"🌿 Emerald": _THEME_EMERALD}

# =============================================================================
# TEMPLATES
# =============================================================================
@st.cache_data
def get_templates() -> list[dict[str, str]]:
    return [
        {"id":"1","name":"Employment Contract","cat":"Corporate","content":"EMPLOYMENT CONTRACT\n\nThis Employment Contract is made on [DATE] between:\n\n1. [EMPLOYER NAME]\n2. [EMPLOYEE NAME]\n\nTERMS:\n1. POSITION: [JOB TITLE]\n2. COMMENCEMENT: [START DATE]\n3. SALARY: ₦[AMOUNT]\n"},
        {"id":"2","name":"Tenancy Agreement","cat":"Property","content":"TENANCY AGREEMENT\n\nMade on [DATE] between [LANDLORD] and [TENANT].\n"},
        {"id":"3","name":"Power of Attorney","cat":"Litigation","content":"GENERAL POWER OF ATTORNEY\n\nI, [GRANTOR], appoint [ATTORNEY] as my Attorney.\n"},
        {"id":"4","name":"Written Address","cat":"Litigation","content":"IN THE [COURT NAME]\nSUIT NO: [NUMBER]\n\nWRITTEN ADDRESS\n"},
        {"id":"5","name":"Affidavit","cat":"Litigation","content":"AFFIDAVIT IN SUPPORT OF [MOTION]\n\nI, [DEPONENT], make oath and state as follows:\n"},
        {"id":"6","name":"Legal Opinion","cat":"Corporate","content":"LEGAL OPINION\n\nTO: [CLIENT]\nRE: [SUBJECT]\n"},
        {"id":"7","name":"Demand Letter","cat":"Litigation","content":"[LETTERHEAD]\n[DATE]\n\nRE: DEMAND FOR ₦[AMOUNT]\n"},
        {"id":"8","name":"Board Resolution","cat":"Corporate","content":"BOARD RESOLUTION — [COMPANY]\n[DATE]\n\nRESOLVED:\n"},
    ]

# =============================================================================
# HELPERS
# =============================================================================
def _id() -> str:
    return uuid.uuid4().hex[:8]

def _cur(a: float) -> str:
    return f"₦{a:,.2f}"

def _esc(t: str) -> str:
    return html.escape(str(t))

def _fdate(s: str) -> str:
    try:
        return datetime.fromisoformat(s).strftime("%B %d, %Y")
    except Exception:
        return str(s)

def _days(s: str) -> int:
    try:
        return (datetime.fromisoformat(s).date() - datetime.now().date()).days
    except Exception:
        return 999

def _rel(s: str) -> str:
    d = _days(s)
    if d == 0:
        return "Today"
    if d == 1:
        return "Tomorrow"
    if d == -1:
        return "Yesterday"
    if 0 < d <= 7:
        return f"In {d} days"
    if -7 <= d < 0:
        return f"{abs(d)} days ago"
    return _fdate(s)

def _norm(n: str) -> str:
    c = (n or "").strip()
    m = MODEL_MIGRATION_MAP.get(c, c)
    return m if m in SUPPORTED_MODELS else DEFAULT_MODEL

def _model() -> str:
    return _norm(st.session_state.get("gemini_model", DEFAULT_MODEL))

def _sec(k: str, d: str = "") -> str:
    try:
        return st.secrets[k]
    except Exception:
        return d

def build_scope_instruction(task: str, mode: str) -> str:
    if mode == "quick":
        return """
SCOPE MODE: QUICK
- Give a short, direct answer.
- Stay tightly within the user's question.
- Do not provide extended background unless necessary.
- If the answer depends on missing facts, state only the top 1-3 variables.
- Prioritize instruction adherence and brevity.
"""
    if mode == "standard":
        return """
SCOPE MODE: STANDARD
- Give a clear, reasonably complete answer.
- Stay within the user's question.
- Include only necessary nuance and practical points.
- Avoid long memo structures unless clearly needed.
"""
    return """
SCOPE MODE: DEEP
- Give a full professional analysis where appropriate.
- Include issue spotting, legal nuance, strategy, and practical points.
- Still remain responsive to the exact instruction.
"""

def length_instruction(length_key: str) -> str:
    return {
        "short": "Keep the answer short and tightly focused.",
        "medium": "Give a balanced answer with necessary detail only.",
        "long": "Provide a fuller answer with nuance and practical detail."
    }.get(length_key, "Give a balanced answer.")

def is_simple_query(text: str) -> bool:
    t = text.lower().strip()
    triggers = [
        "what is", "define", "meaning of", "explain", "briefly explain",
        "short note on", "difference between"
    ]
    return any(t.startswith(x) for x in triggers) and len(t.split()) < 20

# =============================================================================
# FILE EXTRACTION
# =============================================================================
@st.cache_data(show_spinner=False)
def extract_file_cached(file_name: str, file_bytes: bytes) -> dict:
    name = file_name.lower()

    if name.endswith(".pdf"):
        if not PDF_SUPPORT:
            raise RuntimeError("PDF support missing. Install pdfplumber.")
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages = []
                for p in pdf.pages[:50]:
                    pages.append(p.extract_text() or "")
                text = "\n".join(pages)
        except Exception:
            if not PYPDF2_SUPPORT:
                raise RuntimeError("PDF fallback support missing. Install PyPDF2.")
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = "\n".join([(p.extract_text() or "") for p in reader.pages[:50]])

    elif name.endswith(".docx"):
        if not DOCX_SUPPORT:
            raise RuntimeError("DOCX support missing. Install python-docx.")
        doc = Document(io.BytesIO(file_bytes))
        text = "\n".join([p.text for p in doc.paragraphs if p.text])

    elif name.endswith(".txt"):
        text = file_bytes.decode("utf-8", errors="ignore")

    elif name.endswith(".csv"):
        text = pd.read_csv(io.BytesIO(file_bytes)).to_string(index=False)

    elif name.endswith(".xlsx"):
        if not XLSX_SUPPORT:
            raise RuntimeError("XLSX support missing. Install openpyxl.")
        text = pd.read_excel(io.BytesIO(file_bytes)).to_string(index=False)

    else:
        raise ValueError(f"Unsupported file type: {file_name}")

    preview = text[:4000]
    return {
        "preview": preview,
        "full_text": text,
        "char_count": len(text),
        "word_count": len(text.split()),
    }

# =============================================================================
# DATABASE
# =============================================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_history (
            id TEXT PRIMARY KEY,
            created_at TEXT,
            task TEXT,
            mode TEXT,
            query TEXT,
            response TEXT,
            issue_spot TEXT,
            ambiguity TEXT,
            critique TEXT,
            grade TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_history_entry(task: str, mode: str, query: str, result: dict[str, str]):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ai_history (
            id, created_at, task, mode, query, response, issue_spot, ambiguity, critique, grade
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        _id(),
        datetime.now().isoformat(),
        task,
        mode,
        query,
        result.get("main", ""),
        result.get("issue_spot", ""),
        result.get("ambiguity", ""),
        result.get("critique", ""),
        result.get("grade", ""),
    ))
    conn.commit()
    conn.close()

def load_history(limit: int = 100):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, created_at, task, mode, query, response, grade
        FROM ai_history
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

# =============================================================================
# SESSION STATE
# =============================================================================
for _k, _v in {
    "api_key": "",
    "api_configured": False,
    "cases": [],
    "clients": [],
    "time_entries": [],
    "invoices": [],
    "gemini_model": DEFAULT_MODEL,
    "loaded_template": "",
    "theme": "🌿 Emerald",
    "admin_unlocked": False,
    "imported_doc": None,
    "last_response": "",
    "research_results": "",
    "issue_spot_result": "",
    "ambiguity_result": "",
    "critique_result": "",
    "quality_grade": "",
    "show_reasoning_chain": True,
    "enable_self_critique": True,
    "response_mode": "standard",
    "answer_length": "medium",
    "conversation_history": [],
    "conversation_context_str": "",
    "original_query": "",
    "current_query_draft": "",
    "followup_input": "",
    "upload_nonce": str(uuid.uuid4()),
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

st.markdown(_BASE_CSS, unsafe_allow_html=True)
st.markdown(THEMES.get(st.session_state.theme, _THEME_EMERALD), unsafe_allow_html=True)

# =============================================================================
# API LAYER
# =============================================================================
def _key() -> str:
    for fn in [
        lambda: _sec("GEMINI_API_KEY"),
        lambda: os.getenv("GEMINI_API_KEY", ""),
        lambda: st.session_state.get("api_key", ""),
    ]:
        k = fn()
        if k and k.strip():
            return k.strip()
    return ""

def _cfg(k: str):
    genai.configure(api_key=k, transport="rest")

def api_connect(k: str, m: str | None = None) -> bool:
    sel = _norm(m or DEFAULT_MODEL)
    try:
        _cfg(k)
        genai.GenerativeModel(sel).generate_content("OK", generation_config={"max_output_tokens": 8})
        st.session_state.update(api_configured=True, api_key=k, gemini_model=sel)
        return True
    except Exception as e:
        s = str(e)
        if "403" in s:
            st.error("API key invalid or lacks permission.")
        elif "429" in s:
            st.error("Rate limit exceeded.")
        else:
            st.error(f"API error: {s}")
        return False

def _auto():
    if st.session_state.api_configured:
        return
    k = _key()
    if k and len(k) >= 10:
        _cfg(k)
        st.session_state.update(api_key=k, api_configured=True)
        m = _sec("GEMINI_MODEL") or os.getenv("GEMINI_MODEL", "")
        if m:
            st.session_state.gemini_model = _norm(m)

def _gen(prompt: str, sys: str, gen_cfg: dict | None = None) -> str:
    k = _key()
    if not k:
        return "⚠️ No API key configured."
    _cfg(k)
    cfg = gen_cfg or GEN_CONFIG_DEEP
    try:
        model = genai.GenerativeModel(_model(), system_instruction=sys)
    except TypeError:
        model = genai.GenerativeModel(_model())
        prompt = f"{sys}\n\n{prompt}"
    for attempt in range(3):
        try:
            return model.generate_content(prompt, generation_config=cfg).text
        except Exception as e:
            if attempt == 2:
                return f"Error: {e}"
            time.sleep(1.2 * (attempt + 1))
    return "Error: generation failed."

# =============================================================================
# AI ENGINE
# =============================================================================
def _pass1_issue_spot(query: str) -> str:
    return _gen(f"LEGAL SCENARIO:\n\n{query}", ISSUE_SPOTTING_INSTRUCTION, GEN_CONFIG_FAST)

def _pass2_ambiguity(query: str, issues: str) -> str:
    return _gen(
        f"QUERY:\n{query}\n\nISSUES FOUND:\n{issues}\n\nNow identify the top ambiguity factors.",
        AMBIGUITY_INSTRUCTION,
        GEN_CONFIG_FAST
    )

def _pass3_deep_analysis(query: str, task: str, issues: str, ambiguity: str, conv_ctx: str = "") -> str:
    sys = TASK_INSTRUCTIONS.get(task, GENERAL_INSTRUCTION)
    label = TASK_TYPES.get(task, {}).get("label", "General Query")
    ctx = f"\nPRIOR CONTEXT:\n{conv_ctx}\n" if conv_ctx else ""
    prompt = (
        f"TASK TYPE: {label}\n"
        f"DATE: {datetime.now().strftime('%d %B %Y')}\n\n"
        f"ISSUE SPOTTING:\n{issues}\n\n"
        f"AMBIGUITY FACTORS:\n{ambiguity}\n"
        f"{ctx}\n"
        f"USER QUERY:\n{query}\n\n"
        f"INSTRUCTION:\n"
        f"- Address the actual question asked.\n"
        f"- Use the pre-analysis only where helpful.\n"
        f"- Stay on scope.\n"
        f"- Be legally rigorous but not needlessly verbose.\n"
    )
    return _gen(prompt, sys, GEN_CONFIG_DEEP)

def _pass4_critique(query: str, analysis: str, issues: str) -> str:
    return _gen(
        f"QUERY:\n{query}\n\nISSUES FOUND:\n{issues}\n\nANALYSIS TO CRITIQUE:\n{analysis}",
        SELF_CRITIQUE_INSTRUCTION,
        GEN_CONFIG_CRITIQUE
    )

def _extract_grade(text: str) -> str:
    m = re.search(r'OVERALL GRADE:\s*([A-D])', text, re.IGNORECASE)
    return m.group(1).upper() if m else ""

def run_legal_engine(query: str, task: str, mode: str) -> dict[str, str]:
    result = {"issue_spot": "", "ambiguity": "", "main": "", "critique": "", "grade": ""}

    if not st.session_state.api_configured:
        result["main"] = "⚠️ Configure API key first."
        return result

    actual_mode = mode
    if is_simple_query(query) and mode == "deep":
        actual_mode = "quick"

    scope_instruction = build_scope_instruction(task, actual_mode)
    system_instruction = TASK_INSTRUCTIONS.get(task, GENERAL_INSTRUCTION)

    if actual_mode in ("quick", "standard"):
        cfg = {
            "temperature": RESPONSE_MODES[actual_mode]["temperature"],
            "top_p": 0.9,
            "top_k": 30,
            "max_output_tokens": RESPONSE_MODES[actual_mode]["max_tokens"],
        }
        prompt = f"""
{scope_instruction}

{length_instruction(st.session_state.answer_length)}

DATE: {datetime.now().strftime('%d %B %Y')}
TASK TYPE: {TASK_TYPES.get(task, {}).get("label", "General Query")}

USER QUERY:
{query}

INSTRUCTION:
Answer exactly what was asked.
Do not go beyond scope.
If a short answer is sufficient, keep it short.
"""
        result["main"] = _gen(prompt, system_instruction, cfg)
        return result

    result["issue_spot"] = _pass1_issue_spot(query)
    result["ambiguity"] = _pass2_ambiguity(query, result["issue_spot"])
    result["main"] = _pass3_deep_analysis(query, task, result["issue_spot"], result["ambiguity"], st.session_state.get("conversation_context_str", ""))

    if st.session_state.enable_self_critique and result["main"] and not result["main"].startswith(("Error", "⚠️")):
        result["critique"] = _pass4_critique(query, result["main"], result["issue_spot"])
        result["grade"] = _extract_grade(result["critique"])

    return result

def run_followup(orig_q: str, orig_resp: str, followup: str, task: str) -> str:
    if not st.session_state.api_configured:
        return "⚠️ Configure API key first."
    return _gen(
        f"ORIGINAL QUERY:\n{orig_q}\n\nPREVIOUS RESPONSE:\n{orig_resp}\n\nFOLLOW-UP:\n{followup}\n\nRespond only to the new follow-up.",
        FOLLOWUP_INSTRUCTION,
        GEN_CONFIG_DEEP
    )

def ai_research(q: str) -> str:
    if not st.session_state.api_configured:
        return "⚠️ Configure API key first."
    issues = _pass1_issue_spot(q)
    return _gen(
        f"ISSUE SCAN:\n{issues}\n\nRESEARCH QUESTION:\n{q}\n\nAnswer the research question directly and clearly.",
        RESEARCH_INSTRUCTION,
        GEN_CONFIG_DEEP
    )

# =============================================================================
# RESET
# =============================================================================
def clear_ai_state():
    keys_to_clear = [
        "last_response",
        "issue_spot_result",
        "ambiguity_result",
        "critique_result",
        "quality_grade",
        "loaded_template",
        "original_query",
        "conversation_context_str",
        "followup_input",
        "current_query_draft",
    ]
    for k in keys_to_clear:
        st.session_state[k] = ""
    st.session_state.conversation_history = []
    st.session_state.imported_doc = None
    st.session_state.upload_nonce = str(uuid.uuid4())

# =============================================================================
# CRUD
# =============================================================================
def add_case(d):
    d.update(id=_id(), created_at=datetime.now().isoformat())
    st.session_state.cases.append(d)

def upd_case(cid, u):
    for c in st.session_state.cases:
        if c["id"] == cid:
            c.update(u)
            c["updated_at"] = datetime.now().isoformat()
            return

def del_case(cid):
    st.session_state.cases = [c for c in st.session_state.cases if c["id"] != cid]

def add_client(d):
    d.update(id=_id(), created_at=datetime.now().isoformat())
    st.session_state.clients.append(d)

def del_client(cid):
    st.session_state.clients = [c for c in st.session_state.clients if c["id"] != cid]

def client_name(cid):
    for c in st.session_state.clients:
        if c["id"] == cid:
            return c["name"]
    return "—"

def add_entry(d):
    d.update(id=_id(), created_at=datetime.now().isoformat(), amount=d["hours"] * d["rate"])
    st.session_state.time_entries.append(d)

def del_entry(eid):
    st.session_state.time_entries = [e for e in st.session_state.time_entries if e["id"] != eid]

def make_invoice(cid):
    ents = [e for e in st.session_state.time_entries if e.get("client_id") == cid]
    if not ents:
        return None
    inv = {
        "id": _id(),
        "invoice_no": f"INV-{datetime.now():%Y%m%d}-{_id()[:4].upper()}",
        "client_id": cid,
        "client_name": client_name(cid),
        "entries": ents,
        "total": sum(e["amount"] for e in ents),
        "date": datetime.now().isoformat(),
        "status": "Draft",
    }
    st.session_state.invoices.append(inv)
    return inv

def _tb():
    return sum(e.get("amount", 0) for e in st.session_state.time_entries)

def _th():
    return sum(e.get("hours", 0) for e in st.session_state.time_entries)

def _cb(cid):
    return sum(e.get("amount", 0) for e in st.session_state.time_entries if e.get("client_id") == cid)

def _cc(cid):
    return sum(1 for c in st.session_state.cases if c.get("client_id") == cid)

def _hearings(n=10):
    h = [
        {"id": c["id"], "title": c["title"], "date": c["next_hearing"], "court": c.get("court", ""), "suit": c.get("suit_no", "")}
        for c in st.session_state.cases if c.get("next_hearing") and c.get("status") == "Active"
    ]
    h.sort(key=lambda x: x["date"])
    return h[:n]

# =============================================================================
# EXPORT HELPERS
# =============================================================================
def export_dataframe_csv(data: list[dict], filename: str, label: str):
    if data:
        df = pd.DataFrame(data)
        st.download_button(label, df.to_csv(index=False), filename, "text/csv", use_container_width=True)

# =============================================================================
# SIDEBAR
# =============================================================================
def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚖️ LexiAssist v6.1")
        st.caption("Instruction-Adherent Legal AI")
        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Active", len([c for c in st.session_state.cases if c.get("status") == "Active"]))
        with c2:
            st.metric("Hearings", len(_hearings()))

        st.divider()
        st.markdown("### 🎨 Theme")
        th = st.selectbox("Theme", list(THEMES.keys()), index=0, label_visibility="collapsed")
        if th != st.session_state.theme:
            st.session_state.theme = th
            st.rerun()

        st.divider()
        st.markdown("### 🤖 AI Engine")
        if st.session_state.api_configured:
            st.success(f"✅ Connected · `{_model()}`")
        else:
            st.warning("⚠️ Not connected")

        idx = SUPPORTED_MODELS.index(_model()) if _model() in SUPPORTED_MODELS else 0
        sel = st.selectbox("Model", SUPPORTED_MODELS, index=idx)
        if _norm(sel) != st.session_state.gemini_model:
            st.session_state.gemini_model = _norm(sel)
            st.session_state.api_configured = False
            st.rerun()

        st.divider()
        st.markdown("### 🧠 Response Settings")
        selected_mode = st.radio(
            "Answer Mode",
            list(RESPONSE_MODES.keys()),
            index=list(RESPONSE_MODES.keys()).index(st.session_state.get("response_mode", "standard")),
            format_func=lambda k: f"{RESPONSE_MODES[k]['label']} — {RESPONSE_MODES[k]['desc']}",
        )
        st.session_state.response_mode = selected_mode

        st.session_state.answer_length = st.selectbox(
            "Answer Length",
            list(ANSWER_LENGTHS.keys()),
            index=list(ANSWER_LENGTHS.keys()).index(st.session_state.get("answer_length", "medium")),
            format_func=lambda k: ANSWER_LENGTHS[k],
        )

        st.session_state.show_reasoning_chain = st.toggle("Show reasoning panels", value=st.session_state.show_reasoning_chain)
        st.session_state.enable_self_critique = st.toggle("Enable quality check in Deep mode", value=st.session_state.enable_self_critique)

        st.divider()
        st.markdown("### 🔐 API Access")
        ki = st.text_input("API Key", type="password", value=st.session_state.api_key, label_visibility="collapsed", placeholder="Paste Gemini API key…")
        if st.button("Connect", type="primary", use_container_width=True):
            if ki and len(ki.strip()) >= 10:
                if api_connect(ki.strip(), st.session_state.gemini_model):
                    st.success("Connected.")
                    st.rerun()
            else:
                st.warning("Enter a valid key.")
        st.caption("[Get key →](https://aistudio.google.com/app/apikey)")

        st.divider()
        st.markdown("### 💾 Data Export")
        st.download_button(
            "📥 Export All JSON",
            json.dumps({
                "cases": st.session_state.cases,
                "clients": st.session_state.clients,
                "time_entries": st.session_state.time_entries,
                "invoices": st.session_state.invoices,
            }, indent=2),
            f"lexiassist_{datetime.now():%Y%m%d}.json",
            "application/json",
            use_container_width=True
        )
        export_dataframe_csv(st.session_state.cases, "cases.csv", "📥 Export Cases CSV")
        export_dataframe_csv(st.session_state.clients, "clients.csv", "📥 Export Clients CSV")
        export_dataframe_csv(st.session_state.time_entries, "time_entries.csv", "📥 Export Time Entries CSV")

        st.divider()
        st.markdown("### 📤 Import Document")
        up = st.file_uploader(
            "Upload",
            type=["json", "pdf", "docx", "txt", "csv", "xlsx"],
            key=f"uploader_{st.session_state.upload_nonce}",
            label_visibility="collapsed",
        )
        if up:
            try:
                ext = up.name.split(".")[-1].lower()
                if ext == "json":
                    data = json.load(up)
                    for k in ["cases", "clients", "time_entries", "invoices"]:
                        st.session_state[k] = data.get(k, [])
                    st.success("JSON imported.")
                    st.rerun()
                else:
                    raw = up.getvalue()
                    extracted = extract_file_cached(up.name, raw)
                    st.session_state.imported_doc = {
                        "name": up.name,
                        "type": ext,
                        "size": len(raw),
                        "preview": extracted["preview"],
                        "full_text": extracted["full_text"],
                        "char_count": extracted["char_count"],
                        "word_count": extracted["word_count"],
                    }
                    st.success(f"{up.name} loaded.")
                    st.rerun()
            except Exception as e:
                st.error(f"Import failed: {e}")

# =============================================================================
# HOME
# =============================================================================
def render_landing():
    api_status = "🟢 Ready" if st.session_state.api_configured else "🔴 Configure API in Sidebar"
    st.markdown(f"""
    <div class="hero">
        <div class="hero-badge">{api_status}</div>
        <h1>Elite Legal Reasoning<br>for Nigerian Lawyers</h1>
        <p>Built for practical legal work: instruction adherence, adjustable depth, document support, billing, case management, and saved AI history.</p>
        <div class="hero-badge">🇳🇬 Nigerian Law · Fast/Standard/Deep Modes · Saved History</div>
    </div>
    """, unsafe_allow_html=True)

    active = len([c for c in st.session_state.cases if c.get("status") == "Active"])
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{active}</div><div class="stat-label">📁 Active Cases</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card t-blue"><div class="stat-value">{len(st.session_state.clients)}</div><div class="stat-label">👥 Clients</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card t-purple"><div class="stat-value">{_esc(_cur(_tb()))}</div><div class="stat-label">💰 Billable</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card t-amber"><div class="stat-value">{len(_hearings())}</div><div class="stat-label">📅 Hearings</div></div>', unsafe_allow_html=True)

# =============================================================================
# AI ASSISTANT
# =============================================================================
def render_ai():
    st.markdown(
        '<div class="page-header"><h1>🧠 AI Legal Assistant</h1><p>Instruction-adherent legal analysis with Quick, Standard, and Deep modes</p></div>',
        unsafe_allow_html=True
    )

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key in the sidebar to activate the AI assistant.")

    if st.session_state.imported_doc:
        with st.expander("📄 Imported Document", expanded=True):
            doc = st.session_state.imported_doc
            st.caption(f"`{doc['name']}` · {doc['type'].upper()} · {doc['word_count']:,} words · {doc['char_count']:,} chars")
            st.text_area("Preview", doc["preview"], height=180, disabled=True)
            a, b = st.columns(2)
            with a:
                if st.button("✅ Load into Editor", use_container_width=True, type="primary"):
                    txt = doc["full_text"]
                    if len(txt) > MAX_DOC_INPUT_CHARS:
                        txt = txt[:MAX_DOC_INPUT_CHARS] + "\n\n[Document truncated for performance]"
                    st.session_state.loaded_template = txt
                    st.success("Document loaded into editor.")
                    st.rerun()
            with b:
                if st.button("🗑️ Remove Document", use_container_width=True):
                    st.session_state.imported_doc = None
                    st.rerun()

    task_keys = list(TASK_TYPES.keys())
    chosen_task = st.selectbox(
        "🎯 Task Type",
        task_keys,
        index=task_keys.index("analysis"),
        format_func=lambda k: f"{TASK_TYPES[k]['icon']} {TASK_TYPES[k]['label']} — {TASK_TYPES[k]['desc']}",
        key="task_type_selectbox",
    )

    prefill = st.session_state.pop("loaded_template", st.session_state.get("current_query_draft", ""))
    user_input = st.text_area(
        "📝 Your Legal Query or Instructions",
        value=prefill,
        height=260,
        placeholder="Ask narrowly for a short answer, or ask for deep analysis if you want a fuller opinion."
    )
    st.session_state.current_query_draft = user_input

    if user_input:
        wc = len(user_input.split())
        st.caption(f"📝 Query length: {wc} words")

    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        generate = st.button("🧠 Generate Answer", type="primary", use_container_width=True, disabled=not st.session_state.api_configured)
    with c2:
        spot_only = st.button("🔍 Issue Spot Only", use_container_width=True, disabled=not st.session_state.api_configured)
    with c3:
        clear = st.button("🗑️ Clear All", use_container_width=True)

    if spot_only and user_input.strip():
        with st.spinner("Spotting issues..."):
            st.session_state.issue_spot_result = _pass1_issue_spot(user_input)
            st.session_state.ambiguity_result = ""
            st.session_state.last_response = ""
            st.session_state.critique_result = ""
            st.session_state.quality_grade = ""

    if generate:
        if user_input.strip():
            mode = st.session_state.response_mode
            with st.spinner(f"Generating {mode} response..."):
                result = run_legal_engine(user_input, chosen_task, mode)

            st.session_state.issue_spot_result = result.get("issue_spot", "")
            st.session_state.ambiguity_result = result.get("ambiguity", "")
            st.session_state.last_response = result.get("main", "")
            st.session_state.critique_result = result.get("critique", "")
            st.session_state.quality_grade = result.get("grade", "")
            st.session_state.original_query = user_input

            if st.session_state.last_response and not st.session_state.last_response.startswith(("Error", "⚠️")):
                save_history_entry(chosen_task, mode, user_input, result)
                st.session_state.conversation_context_str = (
                    f"Previous query: {user_input[:500]}\nPrevious response: {st.session_state.last_response[:1500]}"
                )
        else:
            st.warning("Please enter a query first.")

    if clear:
        clear_ai_state()
        st.rerun()

    if st.session_state.issue_spot_result and st.session_state.show_reasoning_chain:
        with st.expander("🔍 Issue Spotting", expanded=False):
            st.markdown(f'<div class="issue-spot-box">{_esc(st.session_state.issue_spot_result)}</div>', unsafe_allow_html=True)

    if st.session_state.ambiguity_result and st.session_state.show_reasoning_chain:
        with st.expander("⚠️ It Depends Factors", expanded=False):
            st.markdown(f'<div class="ambiguity-box">{_esc(st.session_state.ambiguity_result)}</div>', unsafe_allow_html=True)

    if st.session_state.last_response:
        st.markdown("---")
        text = st.session_state.last_response
        wc = len(text.split())
        depth = "🟢 Comprehensive" if wc > 800 else ("🟡 Moderate" if wc > 300 else "🔹 Focused")

        grade = st.session_state.quality_grade
        grade_html = ""
        if grade:
            gc = {"A": "grade-a", "B": "grade-b", "C": "grade-c", "D": "grade-d"}.get(grade, "grade-b")
            grade_html = f' <span class="quality-grade {gc}">Grade: {grade}</span>'

        st.markdown(f"#### 📄 AI Output{grade_html}", unsafe_allow_html=True)
        st.caption(f"📝 {wc:,} words · Mode: {st.session_state.response_mode} · Depth: {depth}")

        st.download_button("📥 Download TXT", text, f"LexiAssist_{datetime.now():%Y%m%d_%H%M}.txt", "text/plain")
        st.markdown(f'<div class="response-box">{_esc(text)}</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated legal information for professional reference. Verify all authorities independently and apply professional judgment.</div>',
            unsafe_allow_html=True
        )

    if st.session_state.critique_result and st.session_state.show_reasoning_chain:
        with st.expander("✅ Quality Critique", expanded=False):
            st.markdown(f'<div class="critique-box">{_esc(st.session_state.critique_result)}</div>', unsafe_allow_html=True)

    if st.session_state.last_response:
        st.markdown("---")
        st.markdown("#### 💬 Follow-Up Question")
        followup = st.text_input(
            "Ask a follow-up",
            placeholder="E.g. go deeper on limitation, or explain in simpler terms",
            key="followup_input"
        )
        if st.button("💬 Submit Follow-Up", disabled=not bool(followup.strip())):
            with st.spinner("Answering follow-up..."):
                result = run_followup(
                    st.session_state.original_query,
                    st.session_state.last_response,
                    followup,
                    st.session_state.get("task_type_selectbox", "analysis"),
                )
                if not result.startswith(("Error", "⚠️")):
                    st.session_state.last_response = result
                    st.session_state.conversation_context_str = (
                        f"Original: {st.session_state.original_query[:300]}\n"
                        f"Follow-up: {followup[:300]}\n"
                        f"Latest response: {result[:1500]}"
                    )
                    save_history_entry(
                        st.session_state.get("task_type_selectbox", "analysis"),
                        "followup",
                        followup,
                        {"main": result, "issue_spot": "", "ambiguity": "", "critique": "", "grade": ""}
                    )
                    st.rerun()
                else:
                    st.error(result)

# =============================================================================
# HISTORY
# =============================================================================
def render_history():
    st.markdown('<div class="page-header"><h1>🕘 AI History</h1><p>Saved prompts and outputs</p></div>', unsafe_allow_html=True)

    rows = load_history(100)
    if not rows:
        st.info("No saved AI history yet.")
        return

    search = st.text_input("🔍 Search History", placeholder="Search by query, task, mode, or response...")
    filtered = rows
    if search.strip():
        q = search.lower().strip()
        filtered = [
            row for row in rows
            if q in str(row[1]).lower() or q in str(row[2]).lower() or q in str(row[3]).lower()
            or q in str(row[4]).lower() or q in str(row[5]).lower() or q in str(row[6]).lower()
        ]

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Clear All History", use_container_width=True):
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("DELETE FROM ai_history")
            conn.commit()
            conn.close()
            st.success("History cleared.")
            st.rerun()
    with c2:
        if filtered:
            df = pd.DataFrame([{"Date": r[1], "Task": r[2], "Mode": r[3], "Query": r[4], "Grade": r[6]} for r in filtered])
            st.download_button("📥 Export History CSV", df.to_csv(index=False), "lexiassist_history.csv", "text/csv", use_container_width=True)

    st.markdown("---")
    for row in filtered:
        row_id, created_at, task, mode, query, response, grade = row
        with st.expander(f"{created_at[:19]} · {task} · {mode} · Grade {grade or '—'}"):
            st.markdown("**Query**")
            st.write(query)
            st.markdown("**Response**")
            st.write(response)
            a, b = st.columns(2)
            with a:
                if st.button("📄 Load Response", key=f"load_hist_{row_id}", use_container_width=True):
                    st.session_state.last_response = response
                    st.session_state.original_query = query
                    st.success("Response loaded into AI Assistant.")
            with b:
                st.download_button("📥 Download TXT", response, f"history_{row_id}.txt", "text/plain", key=f"dl_hist_{row_id}", use_container_width=True)

# =============================================================================
# RESEARCH
# =============================================================================
def render_research():
    st.markdown('<div class="page-header"><h1>📚 Legal Research</h1><p>Research memos for Nigerian legal questions</p></div>', unsafe_allow_html=True)

    q = st.text_input("🔍 Research Query", placeholder="E.g. employer liability for workplace injuries under Nigerian law")
    c1, c2 = st.columns([3, 1])
    with c1:
        go = st.button("📚 Run Research", type="primary", use_container_width=True, disabled=not st.session_state.api_configured)
    with c2:
        clr = st.button("🗑️ Clear", use_container_width=True, key="research_clear")

    if go and q.strip():
        with st.spinner("Running research..."):
            st.session_state.research_results = ai_research(q)

    if clr:
        st.session_state.research_results = ""
        st.rerun()

    if st.session_state.research_results:
        text = st.session_state.research_results
        st.download_button("📥 Export TXT", text, f"Research_{datetime.now():%Y%m%d_%H%M}.txt", "text/plain")
        st.markdown(f'<div class="response-box">{_esc(text)}</div>', unsafe_allow_html=True)

# =============================================================================
# CASES
# =============================================================================
def render_cases():
    st.markdown('<div class="page-header"><h1>📁 Case Management</h1><p>Track suits, hearings, and case progress</p></div>', unsafe_allow_html=True)

    search_q = st.text_input("🔍 Search Cases", placeholder="Type to search by title, suit number, court, or notes…")
    filt = st.selectbox("Filter by Status", ["All"] + CASE_STATUSES, key="cfilt")

    cases = st.session_state.cases
    if filt != "All":
        cases = [c for c in cases if c.get("status") == filt]
    if search_q:
        cases = [c for c in cases if search_q.lower() in json.dumps(c).lower()]

    with st.expander("➕ Add New Case", expanded=not bool(st.session_state.cases)):
        with st.form("cf"):
            a, b = st.columns(2)
            with a:
                title = st.text_input("Case Title *")
                suit = st.text_input("Suit Number *")
                court = st.text_input("Court")
            with b:
                nh = st.date_input("Next Hearing")
                status = st.selectbox("Status", CASE_STATUSES)
                cn = ["—"] + [c["name"] for c in st.session_state.clients]
                ci = st.selectbox("Client", range(len(cn)), format_func=lambda i: cn[i])
            notes = st.text_area("Notes")
            if st.form_submit_button("Save Case", type="primary"):
                if title.strip() and suit.strip():
                    cid = st.session_state.clients[ci - 1]["id"] if ci > 0 else None
                    add_case({
                        "title": title.strip(),
                        "suit_no": suit.strip(),
                        "court": court.strip(),
                        "next_hearing": nh.isoformat() if nh else None,
                        "status": status,
                        "client_id": cid,
                        "notes": notes.strip()
                    })
                    st.success("Case added.")
                    st.rerun()
                else:
                    st.error("Title and Suit Number are required.")

    if not cases:
        st.info("No cases match your criteria.")
        return

    for case in cases:
        bc = {"Active": "success", "Pending": "warning", "Completed": "info", "Archived": "danger"}.get(case.get("status", ""), "info")
        a, b = st.columns([5, 1])
        with a:
            st.markdown(
                f'<div class="custom-card"><h4>{_esc(case["title"])} <span class="badge badge-{bc}">{_esc(case.get("status", ""))}</span></h4>'
                f'<p>⚖️ {_esc(case.get("suit_no", ""))} · 🏛️ {_esc(case.get("court", ""))} · 👤 {_esc(client_name(case.get("client_id", "")))}</p></div>',
                unsafe_allow_html=True
            )
        with b:
            ns = st.selectbox("Update Status", CASE_STATUSES, index=CASE_STATUSES.index(case["status"]), key=f"s{case['id']}", label_visibility="collapsed")
            if ns != case.get("status"):
                upd_case(case["id"], {"status": ns})
                st.rerun()
            if st.button("🗑️ Delete", key=f"d{case['id']}"):
                del_case(case["id"])
                st.rerun()

# =============================================================================
# CALENDAR
# =============================================================================
def render_calendar():
    st.markdown('<div class="page-header"><h1>📅 Court Calendar</h1><p>Upcoming hearings at a glance</p></div>', unsafe_allow_html=True)
    hearings = _hearings()
    if not hearings:
        st.info("No upcoming hearings scheduled.")
        return

    for h in hearings:
        d = _days(h["date"])
        u = "urgent" if d <= 3 else ("warn" if d <= 7 else "ok")
        b = "danger" if d <= 3 else ("warning" if d <= 7 else "success")
        st.markdown(
            f'<div class="cal-event {u}"><h4>{_esc(h["title"])}</h4><p>⚖️ {_esc(h["suit"])} · 🏛️ {_esc(h["court"])}</p><p>📅 {_esc(_fdate(h["date"]))} <span class="badge badge-{b}">{_esc(_rel(h["date"]))}</span></p></div>',
            unsafe_allow_html=True
        )

    df = pd.DataFrame([{"Case": h["title"], "Days Until": max(_days(h["date"]), 0), "Date": _fdate(h["date"])} for h in hearings])
    fig = px.bar(df, x="Days Until", y="Case", orientation="h", text="Date", color="Days Until", color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"])
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False, height=400)
    st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# TEMPLATES
# =============================================================================
def render_templates():
    st.markdown('<div class="page-header"><h1>📋 Document Templates</h1><p>Professional Nigerian legal templates</p></div>', unsafe_allow_html=True)
    templates = get_templates()
    cats = sorted({t["cat"] for t in templates})
    sel = st.selectbox("Filter by Category", ["All"] + cats, key="tcat")
    vis = templates if sel == "All" else [t for t in templates if t["cat"] == sel]

    cols = st.columns(2)
    for i, t in enumerate(vis):
        with cols[i % 2]:
            st.markdown(f'<div class="tmpl-card"><h4>📄 {_esc(t["name"])}</h4><span class="badge badge-success">{_esc(t["cat"])}</span></div>', unsafe_allow_html=True)
            a, b = st.columns(2)
            with a:
                if st.button("📋 Load to AI", key=f"u{t['id']}", use_container_width=True):
                    st.session_state.loaded_template = t["content"]
                    st.rerun()
            with b:
                if st.button("👁️ Preview", key=f"p{t['id']}", use_container_width=True):
                    st.session_state["pv"] = t

    pv = st.session_state.get("pv")
    if pv:
        st.markdown(f"### 🔍 Preview: {pv['name']}")
        st.code(pv["content"], language=None)
        if st.button("Close Preview"):
            del st.session_state["pv"]
            st.rerun()

# =============================================================================
# CLIENTS
# =============================================================================
def render_clients():
    st.markdown('<div class="page-header"><h1>👥 Client Management</h1><p>Manage clients, linked cases, and billables</p></div>', unsafe_allow_html=True)

    search_q = st.text_input("🔍 Search Clients", placeholder="Search by name, email, type, or address…")
    with st.expander("➕ Add New Client", expanded=not bool(st.session_state.clients)):
        with st.form("clf"):
            a, b = st.columns(2)
            with a:
                name = st.text_input("Full Name *")
                email = st.text_input("Email")
                phone = st.text_input("Phone")
            with b:
                ct = st.selectbox("Client Type", CLIENT_TYPES)
                addr = st.text_input("Address")
                notes = st.text_area("Notes")
            if st.form_submit_button("Save Client", type="primary"):
                if name.strip():
                    add_client({"name": name.strip(), "email": email.strip(), "phone": phone.strip(), "type": ct, "address": addr.strip(), "notes": notes.strip()})
                    st.success("Client added.")
                    st.rerun()
                else:
                    st.error("Name is required.")

    clients = st.session_state.clients
    if search_q:
        clients = [c for c in clients if search_q.lower() in json.dumps(c).lower()]

    if not clients:
        st.info("No clients found.")
        return

    cols = st.columns(2)
    for i, cl in enumerate(clients):
        with cols[i % 2]:
            cc, cb = _cc(cl["id"]), _cb(cl["id"])
            st.markdown(
                f'<div class="custom-card"><h4>{_esc(cl["name"])} <span class="badge badge-info">{_esc(cl.get("type", ""))}</span></h4>'
                f'<div style="display:flex;justify-content:space-around;text-align:center"><div><div style="font-size:1.5rem;font-weight:700;color:#059669">{cc}</div><div style="font-size:.7rem;color:#64748b">CASES</div></div>'
                f'<div><div style="font-size:1.5rem;font-weight:700;color:#7c3aed">{_esc(_cur(cb))}</div><div style="font-size:.7rem;color:#64748b">BILLABLE</div></div></div></div>',
                unsafe_allow_html=True
            )
            a, b = st.columns(2)
            with a:
                if cb > 0 and st.button("📄 Generate Invoice", key=f"iv{cl['id']}", use_container_width=True):
                    inv = make_invoice(cl["id"])
                    if inv:
                        st.success(f"Invoice {inv['invoice_no']} created.")
                        st.rerun()
            with b:
                if st.button("🗑️ Delete", key=f"dc{cl['id']}", use_container_width=True):
                    del_client(cl["id"])
                    st.rerun()

# =============================================================================
# BILLING
# =============================================================================
def render_billing():
    st.markdown('<div class="page-header"><h1>💰 Billing & Time Tracking</h1><p>Log billable hours and generate invoices</p></div>', unsafe_allow_html=True)

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{_esc(_cur(_tb()))}</div><div class="stat-label">💰 Total Billable</div></div>', unsafe_allow_html=True)
    with s2:
        st.markdown(f'<div class="stat-card t-blue"><div class="stat-value">{_th():.1f}h</div><div class="stat-label">⏱️ Hours Logged</div></div>', unsafe_allow_html=True)
    with s3:
        st.markdown(f'<div class="stat-card t-purple"><div class="stat-value">{len(st.session_state.invoices)}</div><div class="stat-label">📄 Invoices</div></div>', unsafe_allow_html=True)

    with st.expander("⏱️ Log Time Entry", expanded=False):
        with st.form("tf"):
            a, b = st.columns(2)
            with a:
                cn = ["—"] + [c["name"] for c in st.session_state.clients]
                ci = st.selectbox("Client *", range(len(cn)), format_func=lambda i: cn[i])
                csn = ["—"] + [c["title"] for c in st.session_state.cases]
                csi = st.selectbox("Case (optional)", range(len(csn)), format_func=lambda i: csn[i])
                ed = st.date_input("Date", datetime.now())
            with b:
                hrs = st.number_input("Hours *", 0.25, step=0.25, value=1.0)
                rate = st.number_input("Hourly Rate (₦) *", 0, value=50000, step=5000)
                st.markdown(f"**Total: {_cur(hrs * rate)}**")
            desc = st.text_area("Work Description *")
            if st.form_submit_button("Save Entry", type="primary"):
                if ci > 0 and desc.strip():
                    add_entry({
                        "client_id": st.session_state.clients[ci - 1]["id"],
                        "case_id": st.session_state.cases[csi - 1]["id"] if csi > 0 else None,
                        "date": ed.isoformat(),
                        "hours": hrs,
                        "rate": rate,
                        "description": desc.strip(),
                    })
                    st.success("Time entry logged.")
                    st.rerun()
                else:
                    st.error("Select a client and add a description.")

    if not st.session_state.time_entries:
        st.info("No time entries yet.")
        return

    rows = [{
        "Date": _fdate(e["date"]),
        "Client": client_name(e.get("client_id", "")),
        "Description": e["description"][:60] + ("…" if len(e["description"]) > 60 else ""),
        "Hours": f"{e['hours']}h",
        "Rate": _cur(e["rate"]),
        "Amount": _cur(e["amount"]),
        "ID": e["id"]
    } for e in reversed(st.session_state.time_entries)]

    st.dataframe(pd.DataFrame(rows).drop(columns=["ID"]), use_container_width=True, hide_index=True)

# =============================================================================
# TOOLS
# =============================================================================
def render_tools():
    st.markdown('<div class="page-header"><h1>🇳🇬 Nigerian Legal Tools</h1><p>Quick references, calculators, and maxims</p></div>', unsafe_allow_html=True)

    tabs = st.tabs(["⏱️ Limitation Periods", "💹 Interest Calculator", "🏛️ Court Hierarchy", "📖 Legal Maxims"])

    with tabs[0]:
        s = st.text_input("Search limitation periods", "", placeholder="e.g. contract, land, injury…")
        data = [l for l in LIMITATION_PERIODS if s.lower() in l["cause"].lower()] if s else LIMITATION_PERIODS
        st.dataframe(pd.DataFrame(data).rename(columns={"cause": "Cause", "period": "Period", "authority": "Authority"}), use_container_width=True, hide_index=True)

    with tabs[1]:
        with st.form("ic"):
            a, b = st.columns(2)
            with a:
                p = st.number_input("Principal Amount (₦)", 0.0, value=1_000_000.0, step=50_000.0)
                r = st.number_input("Annual Interest Rate (%)", 0.0, value=10.0, step=0.5)
            with b:
                m = st.number_input("Term (Months)", 1, value=12)
                ct = st.selectbox("Interest Type", ["Simple", "Compound (Monthly)"])
            calc = st.form_submit_button("Calculate", type="primary")

        if calc:
            interest = p * (r / 100) * (m / 12) if ct == "Simple" else p * ((1 + (r / 100) / 12) ** m) - p
            total = p + interest
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Principal", _cur(p))
            with c2:
                st.metric("Interest", _cur(interest))
            with c3:
                st.metric("Total Payable", _cur(total))

    with tabs[2]:
        for c in COURT_HIERARCHY:
            indent = "　" * (c["level"] - 1)
            marker = "🔸" if c["level"] == 1 else "├─"
            st.markdown(f"{indent}{marker} **{c['icon']} {c['name']}**")
            st.caption(f"{indent}　　{c['desc']}")

    with tabs[3]:
        sq = st.text_input("Search legal maxims", "", placeholder="e.g. nemo, audi, precedent…")
        mx = [m for m in LEGAL_MAXIMS if sq.lower() in m["maxim"].lower() or sq.lower() in m["meaning"].lower()] if sq else LEGAL_MAXIMS
        for m in mx:
            st.markdown(f'<div class="tool-card"><h4 style="font-style:italic;color:#7c3aed">{_esc(m["maxim"])}</h4><p>{_esc(m["meaning"])}</p></div>', unsafe_allow_html=True)

# =============================================================================
# MAIN
# =============================================================================
def main():
    init_db()
    _auto()
    render_sidebar()

    tabs = st.tabs([
        "🏠 Home",
        "🧠 AI Assistant",
        "🕘 History",
        "📚 Research",
        "📁 Cases",
        "📅 Calendar",
        "📋 Templates",
        "👥 Clients",
        "💰 Billing",
        "🇳🇬 Legal Tools",
    ])

    with tabs[0]:
        render_landing()
    with tabs[1]:
        render_ai()
    with tabs[2]:
        render_history()
    with tabs[3]:
        render_research()
    with tabs[4]:
        render_cases()
    with tabs[5]:
        render_calendar()
    with tabs[6]:
        render_templates()
    with tabs[7]:
        render_clients()
    with tabs[8]:
        render_billing()
    with tabs[9]:
        render_tools()

    st.markdown(
        '<div class="app-footer">'
        '<p>⚖️ <strong>LexiAssist v6.1</strong> · Elite Nigerian Legal Reasoning Engine</p>'
        '<p>Built for Nigerian Lawyers · Powered by Google Gemini</p>'
        '<p style="font-size:.78rem;margin-top:.5rem">⚠️ LexiAssist provides legal information and analytical support, not legal advice. Verify all authorities independently and apply professional judgment.</p>'
        '<p style="font-size:.75rem;margin-top:.25rem">© 2026 LexiAssist. All rights reserved.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
