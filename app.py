# ═══════════════════════════════════════════════════════
# ⚖️ LexiAssist v8.0 — Elite AI Legal Engine
# Nigerian Legal Practice Management & AI Assistant
# Single-file Streamlit application with SQLite persistence
# ═══════════════════════════════════════════════════════

import streamlit as st
import sqlite3
import json
import hashlib
import os
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from html import escape as esc

# ── Optional imports (graceful degradation) ──
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import plotly.express as px
    HAS_PLOTLY = bool(pd) and True
except ImportError:
    px = None
    HAS_PLOTLY = False

try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# ── Page Configuration ──
st.set_page_config(
    page_title="LexiAssist v8.0 · AI Legal Engine",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ═══════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════
ANALYSIS_TYPES = [
    "💬 General Query",
    "🔍 Legal Analysis",
    "📄 Document Drafting",
    "📚 Legal Research",
    "📋 Procedural Guidance",
    "🎯 Strategic Advisory",
    "⚖️ Statutory Interpretation",
    "📑 Contract Review",
]

RESPONSE_MODES = {
    "⚡ Brief": {"tokens": 1200, "desc": "Direct answer, 3-5 sentences"},
    "📝 Standard": {"tokens": 6000, "desc": "Structured analysis with strategy layer"},
    "🔬 Comprehensive": {"tokens": 16384, "desc": "Full CREAC + Devil's Advocate + Risk Matrix"},
}

CASE_STATUSES = ["Active", "Pending", "Adjourned", "Settled", "Closed", "Appeal", "Archived"]
CLIENT_TYPES = ["Individual", "Corporate", "Government", "NGO", "Institutional", "Other"]

COURT_HIERARCHY = [
    {"name": "Supreme Court of Nigeria", "level": 1, "icon": "🏛️",
     "desc": "Apex court · Final appellate jurisdiction · Constitutional interpretation"},
    {"name": "Court of Appeal", "level": 2, "icon": "⚖️",
     "desc": "Appellate jurisdiction from Federal & State High Courts, NIC, CCT"},
    {"name": "Federal High Court", "level": 3, "icon": "🏦",
     "desc": "Revenue, admiralty, banking, IP, federal offences, EFCC/ICPC matters"},
    {"name": "State High Court", "level": 3, "icon": "🏫",
     "desc": "General civil & criminal jurisdiction within the state"},
    {"name": "National Industrial Court", "level": 3, "icon": "🏗️",
     "desc": "Labour, employment, trade unions, industrial disputes"},
    {"name": "Sharia Court of Appeal", "level": 3, "icon": "🕌",
     "desc": "Islamic personal law appeals in states that adopted Sharia"},
    {"name": "Customary Court of Appeal", "level": 3, "icon": "📜",
     "desc": "Customary law appeals from Area/Customary Courts"},
    {"name": "Code of Conduct Tribunal", "level": 4, "icon": "📋",
     "desc": "Trial of public officers for breach of Code of Conduct"},
    {"name": "Magistrate Court", "level": 4, "icon": "🏠",
     "desc": "Summary criminal jurisdiction · Limited civil jurisdiction"},
    {"name": "District / Area / Customary Court", "level": 5, "icon": "🏘️",
     "desc": "Customary law matters, minor disputes, local jurisdiction"},
]

DEFAULT_LIMITATION_PERIODS = [
    {"cause": "Simple Contract", "period": "6 years", "authority": "Various State Limitation Laws (e.g., Limitation Law of Lagos State, Cap. L84)"},
    {"cause": "Tort (General)", "period": "6 years", "authority": "Various State Limitation Laws"},
    {"cause": "Personal Injury", "period": "3 years", "authority": "State Limitation Laws (e.g., Lagos, Ogun, Rivers)"},
    {"cause": "Land / Recovery of Land", "period": "12 years", "authority": "State Limitation Laws; Limitation Act (Northern States, Cap. 118 LFN 1958)"},
    {"cause": "Defamation", "period": "3 years", "authority": "State Limitation Laws"},
    {"cause": "Contract under Deed / Specialty", "period": "12 years", "authority": "Various State Limitation Laws"},
    {"cause": "Recovery of Debt (Simple Contract)", "period": "6 years", "authority": "State Limitation Laws"},
    {"cause": "Enforcement of Judgement", "period": "12 years", "authority": "Sheriffs & Civil Process Act, LFN 2004; State Limitation Laws"},
    {"cause": "Contribution between Tortfeasors", "period": "2 years", "authority": "State Limitation Laws"},
    {"cause": "Fundamental Rights Enforcement", "period": "None (no statutory limitation)", "authority": "CFRN 1999, Chapter IV; FREP Rules 2009"},
    {"cause": "Maritime Claims", "period": "2 years", "authority": "Admiralty Jurisdiction Act, 1991; International Conventions"},
    {"cause": "Tax Assessment / Recovery", "period": "6 years", "authority": "FIRS (Est.) Act 2007; State Revenue Laws"},
]

DEFAULT_MAXIMS = [
    {"maxim": "Audi alteram partem", "meaning": "Hear the other side — no one should be condemned unheard"},
    {"maxim": "Nemo judex in causa sua", "meaning": "No one should be a judge in their own cause"},
    {"maxim": "Ubi jus ibi remedium", "meaning": "Where there is a right, there is a remedy"},
    {"maxim": "Actus curiae neminem gravabit", "meaning": "An act of the court shall prejudice no one"},
    {"maxim": "Ei incumbit probatio qui dicit", "meaning": "The burden of proof lies on him who asserts"},
    {"maxim": "Nemo dat quod non habet", "meaning": "No one gives what they do not have"},
    {"maxim": "Res judicata pro veritate accipitur", "meaning": "A matter adjudged is accepted as truth"},
    {"maxim": "Delegatus non potest delegare", "meaning": "A delegate cannot further delegate"},
    {"maxim": "Volenti non fit injuria", "meaning": "No injury is done to one who consents"},
    {"maxim": "Ignorantia juris non excusat", "meaning": "Ignorance of the law is no excuse"},
    {"maxim": "Expressio unius est exclusio alterius", "meaning": "The mention of one thing implies exclusion of another"},
    {"maxim": "Pacta sunt servanda", "meaning": "Agreements must be kept"},
    {"maxim": "Stare decisis", "meaning": "To stand by things decided — the doctrine of precedent"},
    {"maxim": "Qui facit per alium facit per se", "meaning": "He who acts through another acts himself"},
    {"maxim": "Ex turpi causa non oritur actio", "meaning": "No action arises from a dishonourable cause"},
]

DEFAULT_TEMPLATES = [
    {"name": "Power of Attorney (General)", "cat": "Property",
     "content": """GENERAL POWER OF ATTORNEY\n\nBY THIS POWER OF ATTORNEY made this [DATE] day of [MONTH], [YEAR]\n\nI, [DONOR NAME], of [ADDRESS], (hereinafter called "the Donor")\n\nDO HEREBY APPOINT [ATTORNEY NAME], of [ADDRESS], (hereinafter called "the Attorney")\n\nAS MY TRUE AND LAWFUL ATTORNEY to act for me and on my behalf in the following matters:\n\n1. To manage, administer, and deal with all my properties…\n2. To execute all deeds, documents, and instruments…\n3. To receive and give valid receipts for all monies due to me…\n4. To institute, prosecute, or defend legal proceedings…\n5. To do all acts and things as I might do personally…\n\nAND I HEREBY RATIFY AND CONFIRM all acts lawfully done by the Attorney.\n\nIN WITNESS WHEREOF I have hereunto set my hand and seal.\n\nSIGNED, SEALED AND DELIVERED\nby the Donor:\n\n________________________\n[DONOR NAME]\n\nIN THE PRESENCE OF:\n\nName: ________________\nAddress: ______________\nOccupation: ___________\nSignature: ____________"""},
    {"name": "Demand Letter (Debt Recovery)", "cat": "Litigation",
     "content": """[FIRM LETTERHEAD]\n[DATE]\n\nWITHOUT PREJUDICE\n\nThe Managing Director\n[COMPANY NAME]\n[ADDRESS]\n\nDear Sir/Madam,\n\nRE: DEMAND FOR PAYMENT OF THE SUM OF ₦[AMOUNT] BEING [DESCRIPTION]\n\nWe are Solicitors to [CLIENT NAME] (hereinafter referred to as "our Client") on whose behalf and instruction we write you this letter.\n\nOur Client instructs us that [FACTS OF THE INDEBTEDNESS].\n\nDespite repeated demands, you have failed, refused, and/or neglected to pay the said sum.\n\nTAKE NOTICE that unless payment of the sum of ₦[AMOUNT] is made within [14] days from the date of this letter, we have our Client's firm instructions to commence legal proceedings against you without further notice.\n\nYou will bear the cost of such proceedings.\n\nYours faithfully,\n\n________________________\n[LAWYER NAME]\n[FIRM NAME]\n[NBA ENROLLMENT NUMBER]"""},
    {"name": "Tenancy Agreement", "cat": "Property",
     "content": """TENANCY AGREEMENT\n\nTHIS AGREEMENT is made this [DATE] day of [MONTH], [YEAR]\n\nBETWEEN\n\n[LANDLORD NAME] of [ADDRESS] (hereinafter called "the Landlord")\n\nAND\n\n[TENANT NAME] of [ADDRESS] (hereinafter called "the Tenant")\n\n1. PREMISES: The Landlord lets and the Tenant takes ALL THAT property known as [PROPERTY ADDRESS].\n\n2. TERM: [DURATION] commencing from [START DATE].\n\n3. RENT: The sum of ₦[AMOUNT] per annum payable in advance.\n\n4. TENANT'S COVENANTS: The Tenant covenants:\n   (a) To pay rent on due dates\n   (b) To keep the premises in good repair\n   (c) Not to assign or sublet without consent\n   (d) To use premises for residential purposes only\n   (e) To permit the Landlord to inspect upon reasonable notice\n\n5. LANDLORD'S COVENANTS: The Landlord covenants:\n   (a) Quiet enjoyment of the premises\n   (b) To maintain structural integrity\n   (c) To pay property rates and land charges\n\n6. FORFEITURE: The Landlord may re-enter if rent is in arrears for [DAYS] days.\n\n7. NOTICE: Either party shall give [NOTICE PERIOD] notice to quit.\n\n8. GOVERNING LAW: This Agreement is governed by the Laws of [STATE] State.\n\nSIGNED:\n\nLandlord: _______________     Tenant: _______________\nWitness:  _______________     Witness: _______________"""},
    {"name": "Written Address (Template)", "cat": "Litigation",
     "content": """IN THE HIGH COURT OF [STATE] STATE\nIN THE [JUDICIAL DIVISION] JUDICIAL DIVISION\nHOLDEN AT [CITY]\n\nSUIT NO: [SUIT NUMBER]\n\nBETWEEN:\n[CLAIMANT NAME] .............. CLAIMANT\n\nAND\n\n[DEFENDANT NAME] .............. DEFENDANT\n\nWRITTEN ADDRESS OF THE [CLAIMANT/DEFENDANT]\n\nMY LORD,\n\n1.0 INTRODUCTION\nThis is the Written Address of the [Claimant/Defendant] in support of [the Originating Process / the Application / in reply to the Defendant's address].\n\n2.0 ISSUES FOR DETERMINATION\nThe sole/following issue(s) arise(s) for determination:\n(i) Whether [ISSUE 1]\n(ii) Whether [ISSUE 2]\n\n3.0 ARGUMENTS\n\n3.1 On Issue One:\n[ARGUMENTS WITH CASE LAW]\n\n3.2 On Issue Two:\n[ARGUMENTS WITH CASE LAW]\n\n4.0 CONCLUSION\nIn the light of the foregoing submissions, we humbly urge this Honourable Court to [RELIEF SOUGHT].\n\nDated this _____ day of ____________, [YEAR].\n\n________________________\n[COUNSEL NAME]\n[FIRM NAME]\nCounsel to the [Claimant/Defendant]\n[NBA ENROLLMENT NUMBER]\n[FIRM ADDRESS]"""},
]


# ═══════════════════════════════════════════════════════
# THEMES & CSS (token-based — no f-string brace issues)
# ═══════════════════════════════════════════════════════
THEMES = {
    "Emerald": {"bg": "#f8faf9", "card": "#ffffff", "accent": "#059669", "text": "#1e293b", "sidebar": "#f0fdf4"},
    "Midnight": {"bg": "#0f172a", "card": "#1e293b", "accent": "#38bdf8", "text": "#e2e8f0", "sidebar": "#1e293b"},
    "Royal": {"bg": "#faf5ff", "card": "#ffffff", "accent": "#7c3aed", "text": "#1e1b4b", "sidebar": "#f3e8ff"},
    "Crimson": {"bg": "#fff5f5", "card": "#ffffff", "accent": "#dc2626", "text": "#1e293b", "sidebar": "#fee2e2"},
    "Sunset": {"bg": "#fffbeb", "card": "#ffffff", "accent": "#d97706", "text": "#1e293b", "sidebar": "#fef3c7"},
}


def get_theme_css(theme_name: str) -> str:
    t = THEMES.get(theme_name, THEMES["Emerald"])

    # Build CSS as a plain string with TK_ tokens — avoids all f-string brace issues
    css = """
    <style>
    .stApp {
        background-color: TK_BG;
    }

    [data-testid="stSidebar"] {
        background-color: TK_SIDEBAR;
        border-right: 2px solid TK_ACCENT;
    }

    .custom-card {
        background: TK_CARD;
        border-left: 4px solid TK_ACCENT;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin: 0.75rem 0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }

    .page-header h2 {
        color: TK_ACCENT;
        margin-bottom: 0.25rem;
    }

    .page-header p {
        color: TK_TEXT;
        opacity: 0.7;
    }

    .response-box {
        background: TK_CARD;
        border: 1px solid TK_ACCENT;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        white-space: pre-wrap;
        line-height: 1.7;
        color: TK_TEXT;
    }

    .metric-card {
        background: TK_CARD;
        border-radius: 10px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        border-top: 3px solid TK_ACCENT;
    }

    .metric-card .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: TK_ACCENT;
    }

    .metric-card .metric-label {
        font-size: 0.85rem;
        color: TK_TEXT;
        opacity: 0.7;
    }

    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.1rem;
    }

    .badge-ok {
        background: #d1fae5;
        color: #065f46;
    }

    .badge-warn {
        background: #fef3c7;
        color: #92400e;
    }

    .badge-error {
        background: #fee2e2;
        color: #991b1b;
    }

    .badge-info {
        background: #dbeafe;
        color: #1e40af;
    }

    .tool-card {
        background: TK_CARD;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin: 0.4rem 0;
        border: 1px solid rgba(0,0,0,0.06);
    }

    div.stButton > button {
        border-radius: 8px;
    }

    div.stButton > button[kind="primary"] {
        background-color: TK_ACCENT;
        border-color: TK_ACCENT;
    }

    .stTextArea textarea {
        border-radius: 8px;
    }
    </style>
    """

    return (css
        .replace("TK_BG", t["bg"])
        .replace("TK_CARD", t["card"])
        .replace("TK_ACCENT", t["accent"])
        .replace("TK_TEXT", t["text"])
        .replace("TK_SIDEBAR", t["sidebar"])
    )


# ═══════════════════════════════════════════════════════
# SESSION STATE INITIALIZATION
# ═══════════════════════════════════════════════════════
DEFAULTS = {
    "api_configured": False,
    "model": None,
    "chat_session": None,
    "theme": "Emerald",
    "authenticated": False,
    "loaded_template": None,
    "document_context": "",
    "context_enabled": False,
}

for _k, _v in DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ═══════════════════════════════════════════════════════
# SUPPORTED MODELS (configurable)
# ═══════════════════════════════════════════════════════
def _load_supported_models() -> list:
    sources = []
    try:
        sources.append(st.secrets.get("GEMINI_MODELS", ""))
    except Exception:
        pass
    sources.append(os.environ.get("GEMINI_MODELS", ""))
    for s in sources:
        if s and s.strip():
            return [m.strip() for m in s.split(",") if m.strip()]
    return ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

SUPPORTED_MODELS = _load_supported_models()


# ═══════════════════════════════════════════════════════
# DATABASE SETUP (SQLite)
# ═══════════════════════════════════════════════════════
DB_PATH = Path("lexiassist_data.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    suit_number TEXT DEFAULT '',
    court TEXT DEFAULT '',
    judge TEXT DEFAULT '',
    status TEXT DEFAULT 'Active',
    client_id INTEGER DEFAULT 0,
    client_name TEXT DEFAULT '',
    case_type TEXT DEFAULT '',
    description TEXT DEFAULT '',
    next_hearing TEXT DEFAULT '',
    date_filed TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS case_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    note_type TEXT DEFAULT 'general',
    title TEXT DEFAULT '',
    content TEXT DEFAULT '',
    created_at TEXT DEFAULT '',
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    type TEXT DEFAULT 'Individual',
    address TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS time_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER DEFAULT 0,
    client_name TEXT DEFAULT '',
    description TEXT DEFAULT '',
    hours REAL DEFAULT 0,
    rate REAL DEFAULT 0,
    amount REAL DEFAULT 0,
    entry_date TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT DEFAULT '',
    client_id INTEGER DEFAULT 0,
    client_name TEXT DEFAULT '',
    entries_json TEXT DEFAULT '[]',
    total REAL DEFAULT 0,
    status TEXT DEFAULT 'Draft',
    created_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT DEFAULT '',
    response TEXT DEFAULT '',
    analysis_type TEXT DEFAULT '',
    response_mode TEXT DEFAULT '',
    model TEXT DEFAULT '',
    timestamp TEXT DEFAULT '',
    tokens_used INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cat TEXT DEFAULT 'Custom',
    content TEXT DEFAULT '',
    builtin INTEGER DEFAULT 0,
    created_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS limitation_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cause TEXT NOT NULL,
    period TEXT DEFAULT '',
    authority TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS maxims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    maxim TEXT NOT NULL,
    meaning TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS cost_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT DEFAULT '',
    prompt_tokens INTEGER DEFAULT 0,
    response_tokens INTEGER DEFAULT 0,
    total_cost REAL DEFAULT 0,
    query_preview TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    firm_name TEXT DEFAULT '',
    user_name TEXT DEFAULT '',
    email TEXT DEFAULT '',
    password_hash TEXT DEFAULT '',
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT ''
);
"""


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def ensure_db():
    conn = _get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()

        # Seed limitation periods
        cur = conn.execute("SELECT COUNT(*) FROM limitation_periods")
        if cur.fetchone()[0] == 0:
            for lp in DEFAULT_LIMITATION_PERIODS:
                conn.execute(
                    "INSERT INTO limitation_periods (cause, period, authority) VALUES (?, ?, ?)",
                    (lp["cause"], lp["period"], lp["authority"]),
                )
            conn.commit()

        # Seed maxims
        cur = conn.execute("SELECT COUNT(*) FROM maxims")
        if cur.fetchone()[0] == 0:
            for m in DEFAULT_MAXIMS:
                conn.execute(
                    "INSERT INTO maxims (maxim, meaning) VALUES (?, ?)",
                    (m["maxim"], m["meaning"]),
                )
            conn.commit()

        # Seed built-in templates
        cur = conn.execute("SELECT COUNT(*) FROM templates WHERE builtin = 1")
        if cur.fetchone()[0] == 0:
            for tmpl in DEFAULT_TEMPLATES:
                conn.execute(
                    "INSERT INTO templates (name, cat, content, builtin, created_at) VALUES (?, ?, ?, 1, ?)",
                    (tmpl["name"], tmpl["cat"], tmpl["content"], datetime.now().isoformat()),
                )
            conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════
# DATABASE HELPERS (generic)
# ═══════════════════════════════════════════════════════
def db_execute(sql: str, params: tuple = ()) -> int:
    conn = _get_conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def db_fetch_all(table: str, order: str = "id DESC", where: str = "", params: tuple = ()) -> list:
    conn = _get_conn()
    try:
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        sql += f" ORDER BY {order}"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def db_fetch_one(table: str, row_id: int) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def db_insert(table: str, data: dict) -> int:
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    return db_execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", tuple(data.values()))


def db_update(table: str, row_id: int, data: dict) -> None:
    sets = ", ".join(f"{k} = ?" for k in data.keys())
    db_execute(f"UPDATE {table} SET {sets} WHERE id = ?", (*data.values(), row_id))


def db_delete(table: str, row_id: int) -> None:
    db_execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))


def db_count(table: str, where: str = "", params: tuple = ()) -> int:
    conn = _get_conn()
    try:
        sql = f"SELECT COUNT(*) FROM {table}"
        if where:
            sql += f" WHERE {where}"
        return conn.execute(sql, params).fetchone()[0]
    finally:
        conn.close()
# ═══════════════════════════════════════════════════════
# PART 2 — AI ENGINE · DOCUMENT PARSER · REFERENCES · UI
# ═══════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────
#  AI ENGINE
# ───────────────────────────────────────────────────────
def _resolve_api_key() -> str:
    """Resolve API key: secrets → env → session state."""
    k = safe_secret("GEMINI_API_KEY", "")
    if k and len(k.strip()) >= 10:
        return k.strip()
    k = os.environ.get("GEMINI_API_KEY", "")
    if k and len(k.strip()) >= 10:
        return k.strip()
    return st.session_state.get("api_key_input", "").strip()


def count_tokens(text: str) -> int:
    """Rough token estimate (words × 1.3)."""
    return int(len(text.split()) * 1.3)


def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Estimate Gemini API cost in USD."""
    pricing = {
        "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
        "gemini-2.5-flash-lite": {"input": 0.075, "output": 0.30},
    }
    rates = pricing.get(model, {"input": 0.15, "output": 0.60})
    return round(
        (input_tokens / 1_000_000) * rates["input"]
        + (output_tokens / 1_000_000) * rates["output"],
        6,
    )


RESPONSE_MODE_INSTRUCTIONS = {
    "Brief": (
        "Respond concisely in 2-4 paragraphs. Focus on the direct answer, "
        "key authority, and one actionable recommendation."
    ),
    "Standard": (
        "Provide a balanced analysis in 4-8 paragraphs. Include: (1) Direct answer, "
        "(2) Applicable law and leading authority, (3) Application to facts, "
        "(4) Strategic recommendations with at least one alternative angle, "
        "(5) Practical next steps."
    ),
    "Comprehensive": (
        "Deliver a full CREAC analysis: Conclusion → Rule → Explanation → Application → Conclusion. "
        "Include: all relevant statutes and case law with citations, procedural requirements, "
        "limitation periods, court hierarchy considerations, a Devil's Advocate section "
        "highlighting opposing arguments, and a detailed action plan with timelines."
    ),
}


def build_system_prompt(mode: str = "Standard", contract_mode: bool = False) -> str:
    """Construct the LexiAssist system prompt for Gemini."""
    base = (
        "You are LexiAssist — an elite, aggressive AI legal partner specialising in Nigerian law. "
        "You think like a seasoned Senior Advocate of Nigeria (SAN) who leaves no stone unturned.\n\n"
        "CORE DIRECTIVES:\n"
        "1. Jurisdiction: Nigerian legal system — Constitution, statutes, case law (Supreme Court, "
        "Court of Appeal, Federal & State High Courts, National Industrial Court, Sharia & Customary courts).\n"
        "2. Citations: Always cite real statutes (e.g., Companies and Allied Matters Act 2020, s.XXX) "
        "and real case law (e.g., Registered Trustees of National Association of Community Health "
        "Practitioners of Nigeria v. Medical & Health Workers Union of Nigeria [2008] 2 NWLR "
        "(Pt. 1070) 1) where available. Never fabricate citations.\n"
        "3. Accuracy: If uncertain about a specific citation, say so explicitly rather than inventing one.\n"
        "4. Strategy: Always include a practical strategy layer — don't just state the law, advise on "
        "how to use it, what pitfalls to avoid, and what the opponent may argue.\n"
        "5. Limitation periods: Flag applicable limitation periods proactively.\n"
        "6. Tone: Professional, authoritative, direct. Write for a lawyer, not a layperson.\n"
        "7. Format: Use clear headings, numbered points where helpful, and bold key terms.\n\n"
    )

    mode_instruction = RESPONSE_MODE_INSTRUCTIONS.get(mode, RESPONSE_MODE_INSTRUCTIONS["Standard"])

    if contract_mode:
        contract_layer = (
            "CONTRACT REVIEW MODE ACTIVE:\n"
            "Perform a clause-by-clause review. For each material clause:\n"
            "• Identify the clause and its purpose\n"
            "• Flag risks, ambiguities, or missing protections\n"
            "• Check compliance with Nigerian law (e.g., CAMA 2020, Labour Act, Land Use Act)\n"
            "• Suggest specific redline edits with replacement language\n"
            "• Rate each clause: ✅ Acceptable | ⚠️ Needs Attention | 🚨 High Risk\n"
            "End with an Executive Summary of overall risk level and top 5 recommendations.\n\n"
        )
        return base + contract_layer + f"RESPONSE MODE: {mode}\n{mode_instruction}"

    return base + f"RESPONSE MODE: {mode}\n{mode_instruction}"


def call_gemini(
    prompt: str,
    mode: str = "Standard",
    context: str = "",
    contract_mode: bool = False,
    user_id: str = "",
    model_override: str = "",
) -> dict:
    """Send a prompt to Gemini and return structured result."""
    api_key = _resolve_api_key()
    if not api_key:
        return {"error": "No API key configured.", "text": "", "tokens": {}, "cost": 0.0}

    model_name = model_override or st.session_state.get(
        "selected_model", safe_secret("GEMINI_MODEL", DEFAULT_MODEL)
    )

    system_prompt = build_system_prompt(mode, contract_mode)

    full_prompt = prompt
    if context:
        full_prompt = f"REFERENCE DOCUMENT:\n{context[:15000]}\n\n---\nUSER QUERY:\n{prompt}"

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
        )
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.4,
                max_output_tokens=8192,
            ),
        )

        # Handle blocked responses
        if not response.parts:
            return {
                "error": "Response blocked by safety filters. Try rephrasing your query.",
                "text": "",
                "tokens": {},
                "cost": 0.0,
            }

        text = response.text or ""

        # Token counting — use API metadata if available, else estimate
        input_tokens = count_tokens(system_prompt + full_prompt)
        output_tokens = count_tokens(text)
        try:
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                um = response.usage_metadata
                input_tokens = getattr(um, "prompt_token_count", input_tokens) or input_tokens
                output_tokens = getattr(um, "candidates_token_count", output_tokens) or output_tokens
        except Exception:
            pass

        cost = estimate_cost(input_tokens, output_tokens, model_name)

        # Persist usage stats
        if user_id:
            save_usage(user_id, model_name, input_tokens, output_tokens, cost)

        return {
            "text": text,
            "error": "",
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens,
            },
            "cost": cost,
            "model": model_name,
        }

    except Exception as e:
        return {"error": str(e), "text": "", "tokens": {}, "cost": 0.0}


# ───────────────────────────────────────────────────────
#  DOCUMENT PARSER
# ───────────────────────────────────────────────────────
def parse_pdf(file) -> str:
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return "\n\n".join(text_parts) if text_parts else "[No extractable text in PDF]"
    except Exception as e:
        return f"[PDF parse error: {e}]"


def parse_docx_file(file) -> str:
    try:
        doc = Document(file)
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        return f"[DOCX parse error: {e}]"


def parse_txt(file) -> str:
    try:
        raw = file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        return raw
    except Exception as e:
        return f"[TXT parse error: {e}]"


def parse_xlsx(file) -> str:
    try:
        df = pd.read_excel(file, engine="openpyxl")
        return df.to_string(index=False)
    except Exception as e:
        return f"[XLSX parse error: {e}]"


def parse_csv_file(file) -> str:
    try:
        df = pd.read_csv(file)
        return df.to_string(index=False)
    except Exception as e:
        return f"[CSV parse error: {e}]"


def parse_json_file(file) -> str:
    try:
        raw = file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        data = json.loads(raw)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"[JSON parse error: {e}]"


def parse_uploaded_file(file) -> str:
    """Route uploaded file to the correct parser."""
    if file is None:
        return ""
    name = file.name.lower()
    if name.endswith(".pdf"):
        return parse_pdf(file)
    elif name.endswith(".docx"):
        return parse_docx_file(file)
    elif name.endswith((".txt", ".rtf", ".text")):
        return parse_txt(file)
    elif name.endswith((".xlsx", ".xls")):
        return parse_xlsx(file)
    elif name.endswith(".csv"):
        return parse_csv_file(file)
    elif name.endswith(".json"):
        return parse_json_file(file)
    else:
        return parse_txt(file)


# ───────────────────────────────────────────────────────
#  REFERENCE DATA (Nigerian Legal System)
# ───────────────────────────────────────────────────────
def get_default_limitation_periods() -> list:
    return [
        {"category": "Simple Contract", "period": "6 years", "statute": "Limitation Act (various states)"},
        {"category": "Land Recovery", "period": "12 years", "statute": "Limitation Act (various states)"},
        {"category": "Tort (General)", "period": "6 years", "statute": "Limitation Act (various states)"},
        {"category": "Personal Injury", "period": "3 years", "statute": "Limitation Act (various states)"},
        {"category": "Defamation", "period": "3 years", "statute": "Limitation Act (various states)"},
        {"category": "Debt Recovery", "period": "6 years", "statute": "Limitation Act (various states)"},
        {"category": "Fundamental Rights", "period": "12 months", "statute": "Fundamental Rights (Enforcement Procedure) Rules 2009"},
        {"category": "Tax Appeal", "period": "30 days", "statute": "Federal Inland Revenue Service (Est.) Act 2007"},
        {"category": "Election Petition", "period": "21 days", "statute": "Electoral Act 2022, s.285(5) CFRN"},
        {"category": "Winding Up Petition", "period": "21 days (statutory demand)", "statute": "CAMA 2020, s.572"},
        {"category": "Appeal (Court of Appeal)", "period": "90 days (civil) / 90 days (criminal)", "statute": "Court of Appeal Act, s.27"},
        {"category": "Appeal (Supreme Court)", "period": "90 days", "statute": "Supreme Court Act, s.31"},
        {"category": "Judicial Review", "period": "3 months", "statute": "Various High Court Civil Procedure Rules"},
        {"category": "Labour / Employment", "period": "12 months", "statute": "National Industrial Court Act 2006"},
    ]


def get_court_hierarchy() -> list:
    return [
        {"court": "Supreme Court of Nigeria", "level": 1, "description": "Final appellate court. Decisions bind all lower courts."},
        {"court": "Court of Appeal", "level": 2, "description": "Intermediate appellate court. Divisions across Nigeria."},
        {"court": "Federal High Court", "level": 3, "description": "Exclusive jurisdiction: revenue, admiralty, banking, IP, federal agencies."},
        {"court": "State High Court", "level": 3, "description": "General civil and criminal jurisdiction within each state."},
        {"court": "National Industrial Court", "level": 3, "description": "Exclusive jurisdiction: labour, employment, trade unions."},
        {"court": "FCT High Court", "level": 3, "description": "High Court for the Federal Capital Territory, Abuja."},
        {"court": "Sharia Court of Appeal", "level": 4, "description": "Appellate jurisdiction on Islamic personal law matters."},
        {"court": "Customary Court of Appeal", "level": 4, "description": "Appellate jurisdiction on customary law matters."},
        {"court": "Magistrate / District Court", "level": 5, "description": "Summary jurisdiction. Limited monetary and criminal thresholds."},
        {"court": "Area / Customary Court", "level": 6, "description": "Local customary law disputes. Varies by state."},
    ]


def get_latin_maxims() -> list:
    return [
        {"maxim": "Audi alteram partem", "meaning": "Hear the other side — a fundamental rule of natural justice."},
        {"maxim": "Nemo judex in causa sua", "meaning": "No one should be a judge in their own cause."},
        {"maxim": "Actus curiae neminem gravabit", "meaning": "An act of the court shall prejudice no one."},
        {"maxim": "Ei incumbit probatio qui dicit", "meaning": "The burden of proof lies on the one who asserts."},
        {"maxim": "Res judicata pro veritate accipitur", "meaning": "A matter adjudged is accepted as truth."},
        {"maxim": "Stare decisis", "meaning": "Stand by decided matters — the doctrine of precedent."},
        {"maxim": "Ubi jus ibi remedium", "meaning": "Where there is a right, there is a remedy."},
        {"maxim": "Volenti non fit injuria", "meaning": "No injury is done to one who consents."},
        {"maxim": "Caveat emptor", "meaning": "Let the buyer beware."},
        {"maxim": "Nemo dat quod non habet", "meaning": "No one gives what they do not have."},
        {"maxim": "Expressio unius est exclusio alterius", "meaning": "The expression of one thing is the exclusion of another."},
        {"maxim": "Ignorantia juris non excusat", "meaning": "Ignorance of the law is no excuse."},
        {"maxim": "Pacta sunt servanda", "meaning": "Agreements must be kept."},
        {"maxim": "Ultra vires", "meaning": "Beyond the powers — an act beyond legal authority."},
        {"maxim": "De minimis non curat lex", "meaning": "The law does not concern itself with trifles."},
        {"maxim": "Doli incapax", "meaning": "Incapable of committing wrong — applied to minors."},
        {"maxim": "Locus standi", "meaning": "The right or capacity to bring an action before a court."},
        {"maxim": "Obiter dictum", "meaning": "A remark made in passing — not binding but persuasive."},
        {"maxim": "Ratio decidendi", "meaning": "The reason for the decision — the binding principle."},
        {"maxim": "Sub judice", "meaning": "Under judicial consideration — not yet decided."},
    ]


def get_user_references(user_id: str, ref_type: str) -> list:
    """Return user-customised references or defaults."""
    saved = load_references(user_id)
    if saved and ref_type in saved:
        return saved[ref_type]
    defaults = {
        "limitation_periods": get_default_limitation_periods(),
        "court_hierarchy": get_court_hierarchy(),
        "latin_maxims": get_latin_maxims(),
    }
    return defaults.get(ref_type, [])


# ───────────────────────────────────────────────────────
#  SESSION STATE INIT
# ───────────────────────────────────────────────────────
def init_session_state():
    """Initialise all session state keys with defaults."""
    defaults = {
        "authenticated": False,
        "user_id": "",
        "username": "",
        "chat_history": [],
        "uploaded_context": "",
        "uploaded_filename": "",
        "selected_model": safe_secret("GEMINI_MODEL", DEFAULT_MODEL),
        "response_mode": "Standard",
        "contract_mode": False,
        "current_page": "AI Assistant",
        "last_result": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ───────────────────────────────────────────────────────
#  REUSABLE UI COMPONENTS
# ───────────────────────────────────────────────────────
def render_export_buttons(text: str, title: str = "LexiAssist Output", key_prefix: str = "exp"):
    """Render TXT / HTML / PDF / DOCX download buttons."""
    if not text:
        return
    cols = st.columns(4)
    with cols[0]:
        st.download_button(
            "📄 TXT", export_text(text, title),
            file_name=f"{title}.txt", mime="text/plain",
            key=f"{key_prefix}_txt", use_container_width=True,
        )
    with cols[1]:
        st.download_button(
            "🌐 HTML", export_html(text, title),
            file_name=f"{title}.html", mime="text/html",
            key=f"{key_prefix}_html", use_container_width=True,
        )
    with cols[2]:
        st.download_button(
            "📑 PDF", export_pdf(text, title),
            file_name=f"{title}.pdf", mime="application/pdf",
            key=f"{key_prefix}_pdf", use_container_width=True,
        )
    with cols[3]:
        st.download_button(
            "📝 DOCX", export_docx(text, title),
            file_name=f"{title}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key=f"{key_prefix}_docx", use_container_width=True,
        )


def render_token_display(result: dict):
    """Show model, token counts and estimated cost."""
    if not result or "tokens" not in result or not result["tokens"]:
        return
    tokens = result["tokens"]
    cost = result.get("cost", 0.0)
    model = result.get("model", "unknown")
    cols = st.columns(4)
    cols[0].metric("Model", model.split("/")[-1])
    cols[1].metric("Input Tokens", f"{tokens.get('input', 0):,}")
    cols[2].metric("Output Tokens", f"{tokens.get('output', 0):,}")
    cols[3].metric("Est. Cost", f"${cost:.6f}")


def render_save_to_case(text: str, user_id: str, key_prefix: str = "save"):
    """One-click save an analysis snippet into an existing case."""
    cases = load_cases(user_id)
    if not cases:
        return
    case_options = {c.get("title", f"Case {i+1}"): i for i, c in enumerate(cases)}
    col1, col2 = st.columns([3, 1])
    with col1:
        selected = st.selectbox(
            "Save analysis to case:",
            options=list(case_options.keys()),
            key=f"{key_prefix}_case_select",
        )
    with col2:
        if st.button("💾 Save to Case", key=f"{key_prefix}_save_btn", use_container_width=True):
            idx = case_options[selected]
            if "analyses" not in cases[idx]:
                cases[idx]["analyses"] = []
            cases[idx]["analyses"].append({
                "date": datetime.now().isoformat(),
                "content": text[:5000],
            })
            save_cases(user_id, cases)
            st.success(f"✅ Saved to **{selected}**")


def render_sidebar():
    """Render the full sidebar: branding, model, mode, upload, nav, logout."""
    with st.sidebar:
        st.markdown(f"### ⚖️ {APP_TITLE}")
        st.caption(f"v{VERSION}")

        if st.session_state.get("authenticated"):
            st.markdown(f"👤 **{st.session_state.get('username', 'User')}**")
            st.divider()

            # ── Model selection ──
            model_str = safe_secret("GEMINI_MODELS", ", ".join(AVAILABLE_MODELS))
            models = [m.strip() for m in model_str.split(",") if m.strip()]
            current = st.session_state.get("selected_model", DEFAULT_MODEL)
            if current not in models:
                models.insert(0, current)
            st.session_state["selected_model"] = st.selectbox(
                "🤖 AI Model", models,
                index=models.index(current), key="sb_model",
            )

            # ── Response mode ──
            modes = list(RESPONSE_MODE_INSTRUCTIONS.keys())
            current_mode = st.session_state.get("response_mode", "Standard")
            st.session_state["response_mode"] = st.selectbox(
                "📊 Response Mode", modes,
                index=modes.index(current_mode), key="sb_mode",
            )

            # ── Contract review toggle ──
            st.session_state["contract_mode"] = st.toggle(
                "📋 Contract Review Mode",
                value=st.session_state.get("contract_mode", False),
                key="sb_contract",
            )

            st.divider()

            # ── File upload ──
            uploaded = st.file_uploader(
                "📎 Upload Document",
                type=["pdf", "docx", "txt", "rtf", "xlsx", "csv", "json"],
                key="sb_file_upload",
            )
            if uploaded:
                if uploaded.name != st.session_state.get("uploaded_filename", ""):
                    with st.spinner("Parsing document..."):
                        content = parse_uploaded_file(uploaded)
                        st.session_state["uploaded_context"] = content
                        st.session_state["uploaded_filename"] = uploaded.name
                    st.success(f"✅ {uploaded.name} loaded ({len(content):,} chars)")
                else:
                    st.info(f"📄 {uploaded.name} active")

            if st.session_state.get("uploaded_context"):
                if st.button("🗑️ Clear Document", key="sb_clear_doc"):
                    st.session_state["uploaded_context"] = ""
                    st.session_state["uploaded_filename"] = ""
                    st.rerun()

            st.divider()

            # ── Navigation ──
            pages = [
                "AI Assistant",
                "Cases & Hearings",
                "Clients & Billing",
                "Legal References",
                "Document Templates",
                "AI Usage & Costs",
                "Settings",
            ]
            icons = {
                "AI Assistant": "🤖",
                "Cases & Hearings": "📂",
                "Clients & Billing": "👥",
                "Legal References": "📚",
                "Document Templates": "📝",
                "AI Usage & Costs": "📊",
                "Settings": "⚙️",
            }
            current_page = st.session_state.get("current_page", "AI Assistant")
            for page in pages:
                btn_type = "primary" if page == current_page else "secondary"
                if st.button(
                    f"{icons.get(page, '📄')} {page}",
                    key=f"nav_{page}",
                    use_container_width=True,
                    type=btn_type,
                ):
                    st.session_state["current_page"] = page
                    st.rerun()

            st.divider()

            # ── Logout ──
            if st.button("🚪 Logout", key="sb_logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
# ═══════════════════════════════════════════════════════
# PART 3 — APPLICATION PAGES
# ═══════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────
#  LOGIN & REGISTRATION
# ───────────────────────────────────────────────────────
def page_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            "<h1 style='text-align:center'>⚖️ LexiAssist</h1>"
            "<p style='text-align:center;color:#64748b'>"
            "AI-Powered Legal Workspace for Nigerian Lawyers</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter username")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                if st.form_submit_button("Login", type="primary", use_container_width=True):
                    if not username or not password:
                        st.error("Please fill in all fields.")
                    else:
                        user = authenticate_user(username, password)
                        if user:
                            st.session_state.update({
                                "authenticated": True,
                                "user_id": user["id"],
                                "username": user["username"],
                                "chat_history": load_chat_history(user["id"]),
                            })
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")

        with tab_register:
            with st.form("register_form"):
                new_user = st.text_input("Choose Username", placeholder="Pick a username")
                new_pass = st.text_input("Choose Password", type="password", placeholder="Min. 6 characters")
                confirm = st.text_input("Confirm Password", type="password")
                if st.form_submit_button("Create Account", use_container_width=True):
                    if not new_user or not new_pass:
                        st.error("All fields are required.")
                    elif len(new_pass) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif new_pass != confirm:
                        st.error("Passwords do not match.")
                    elif create_user(new_user, new_pass):
                        st.success("✅ Account created! Please log in.")
                    else:
                        st.error("Username already taken.")


# ───────────────────────────────────────────────────────
#  AI ASSISTANT
# ───────────────────────────────────────────────────────
def page_ai_assistant():
    user_id = st.session_state.get("user_id", "")
    mode = st.session_state.get("response_mode", "Standard")
    contract_mode = st.session_state.get("contract_mode", False)

    hdr = "🤖 AI Legal Assistant"
    if contract_mode:
        hdr += "  •  📋 Contract Review"
    st.header(hdr)

    # Context indicator
    if st.session_state.get("uploaded_context"):
        st.info(
            f"📎 **{st.session_state.get('uploaded_filename')}** loaded "
            f"({len(st.session_state['uploaded_context']):,} chars)"
        )

    # Display chat history
    for msg in st.session_state.get("chat_history", []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask LexiAssist about Nigerian law..."):
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        result = {}
        with st.chat_message("assistant"):
            with st.spinner("⚖️ Analyzing..."):
                result = call_gemini(
                    prompt=prompt,
                    mode=mode,
                    context=st.session_state.get("uploaded_context", ""),
                    contract_mode=contract_mode,
                    user_id=user_id,
                )

            if result.get("error"):
                st.error(f"❌ {result['error']}")
                st.session_state["last_result"] = None
            else:
                st.markdown(result["text"])
                st.session_state["last_result"] = result
                st.session_state["chat_history"].append(
                    {"role": "assistant", "content": result["text"]}
                )
                save_chat_history(user_id, st.session_state["chat_history"][-50:])

        # Controls below chat
        if result and not result.get("error") and result.get("text"):
            render_token_display(result)
            render_export_buttons(result["text"], key_prefix="chat_exp")
            render_save_to_case(result["text"], user_id, key_prefix="chat_save")

    # Persistent controls for last result
    elif st.session_state.get("last_result"):
        r = st.session_state["last_result"]
        if not r.get("error") and r.get("text"):
            with st.expander("📊 Last Response Controls", expanded=False):
                render_token_display(r)
                render_export_buttons(r["text"], key_prefix="last_exp")
                render_save_to_case(r["text"], user_id, key_prefix="last_save")

    # ── Comparison tool ──
    with st.expander("🔄 Compare Analyses"):
        st.caption("Re-run your last query in a different mode for side-by-side comparison.")
        user_msgs = [m for m in st.session_state.get("chat_history", []) if m["role"] == "user"]
        if user_msgs:
            last_query = user_msgs[-1]["content"]
            st.text_area("Query:", value=last_query, height=80, disabled=True, key="cmp_q")
            other_modes = [m for m in RESPONSE_MODE_INSTRUCTIONS if m != mode]
            cmp_mode = st.selectbox("Compare in mode:", other_modes, key="cmp_mode")
            if st.button("⚡ Run Comparison", key="cmp_run"):
                with st.spinner("Running comparison..."):
                    cmp_result = call_gemini(
                        prompt=last_query,
                        mode=cmp_mode,
                        context=st.session_state.get("uploaded_context", ""),
                        contract_mode=contract_mode,
                        user_id=user_id,
                    )
                if cmp_result.get("error"):
                    st.error(cmp_result["error"])
                else:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader(f"📄 {mode}")
                        asst_msgs = [m for m in st.session_state.get("chat_history", []) if m["role"] == "assistant"]
                        st.markdown(asst_msgs[-1]["content"] if asst_msgs else "_No previous response_")
                    with c2:
                        st.subheader(f"📄 {cmp_mode}")
                        st.markdown(cmp_result["text"])
        else:
            st.info("Send a query first to enable comparison.")

    # Clear chat
    if st.session_state.get("chat_history"):
        if st.button("🗑️ Clear Chat History", key="clear_chat"):
            st.session_state["chat_history"] = []
            st.session_state["last_result"] = None
            save_chat_history(user_id, [])
            st.rerun()


# ───────────────────────────────────────────────────────
#  CASES & HEARINGS
# ───────────────────────────────────────────────────────
def page_cases():
    user_id = st.session_state.get("user_id", "")
    st.header("📂 Cases & Hearings")
    cases = load_cases(user_id)

    tab_list, tab_add, tab_hearings = st.tabs(
        ["📋 My Cases", "➕ Add Case", "📅 Upcoming Hearings"]
    )

    # ── Add case ──
    with tab_add:
        with st.form("add_case_form"):
            st.subheader("New Case")
            title = st.text_input("Case Title / Matter Name*")
            case_number = st.text_input("Suit Number", placeholder="e.g., FHC/L/CS/123/2025")
            court = st.selectbox("Court", [
                "Supreme Court of Nigeria", "Court of Appeal",
                "Federal High Court", "State High Court",
                "National Industrial Court", "FCT High Court",
                "Magistrate Court", "Customary Court",
                "Sharia Court", "Other",
            ])
            c1, c2 = st.columns(2)
            with c1:
                claimant = st.text_input("Claimant / Applicant")
            with c2:
                defendant = st.text_input("Defendant / Respondent")
            status = st.selectbox("Status", [
                "Active", "Pending", "Adjourned", "Closed", "Settled", "Struck Out",
            ])
            next_hearing = st.date_input("Next Hearing Date", value=None)
            notes = st.text_area("Notes", placeholder="Brief description of the matter...")

            if st.form_submit_button("💾 Save Case", type="primary", use_container_width=True):
                if not title:
                    st.error("Case title is required.")
                else:
                    cases.append({
                        "id": hashlib.md5(
                            f"{title}{datetime.now().isoformat()}".encode()
                        ).hexdigest()[:12],
                        "title": title,
                        "case_number": case_number,
                        "court": court,
                        "claimant": claimant,
                        "defendant": defendant,
                        "status": status,
                        "next_hearing": str(next_hearing) if next_hearing else "",
                        "notes": notes,
                        "hearings": [],
                        "analyses": [],
                        "created": datetime.now().isoformat(),
                    })
                    save_cases(user_id, cases)
                    st.success(f"✅ Case **{title}** saved!")
                    st.rerun()

    # ── Case list ──
    with tab_list:
        if not cases:
            st.info("No cases yet. Add your first case in the **Add Case** tab.")
        else:
            st.caption(f"{len(cases)} case(s) on record")
            status_filter = st.multiselect(
                "Filter by status:",
                ["Active", "Pending", "Adjourned", "Closed", "Settled", "Struck Out"],
                default=["Active", "Pending", "Adjourned"],
            )

            for i, case in enumerate(cases):
                if status_filter and case.get("status") not in status_filter:
                    continue

                icon = {"Active": "🟢", "Pending": "🟡", "Closed": "🔴"}.get(
                    case.get("status", ""), "⚪"
                )
                with st.expander(
                    f"{icon} {case.get('title', 'Untitled')} — "
                    f"{case.get('case_number', 'No suit number')}"
                ):
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Court", case.get("court", "N/A"))
                    mc2.metric("Status", case.get("status", "N/A"))
                    mc3.metric("Next Hearing", case.get("next_hearing", "Not set"))

                    st.markdown(
                        f"**Parties:** {case.get('claimant', 'N/A')} v. "
                        f"{case.get('defendant', 'N/A')}"
                    )
                    if case.get("notes"):
                        st.markdown(f"**Notes:** {case['notes']}")

                    # Hearings
                    hearings = case.get("hearings", [])
                    if hearings:
                        st.markdown("**Hearing History:**")
                        for h in hearings:
                            st.markdown(
                                f"- {h.get('date', '?')} — {h.get('purpose', 'General')} "
                                f"({h.get('outcome', 'Pending')})"
                            )

                    # Add hearing sub-form
                    with st.form(f"hearing_{i}"):
                        st.markdown("**Add Hearing:**")
                        hc1, hc2 = st.columns(2)
                        with hc1:
                            h_date = st.date_input("Date", key=f"hd_{i}")
                            h_purpose = st.text_input(
                                "Purpose", placeholder="e.g., Cross-examination",
                                key=f"hp_{i}",
                            )
                        with hc2:
                            h_time = st.text_input(
                                "Time", placeholder="9:00 AM", key=f"ht_{i}"
                            )
                            h_outcome = st.selectbox(
                                "Outcome",
                                ["Pending", "Adjourned", "Heard", "Struck Out", "Settled"],
                                key=f"ho_{i}",
                            )
                        h_notes = st.text_input("Hearing Notes", key=f"hn_{i}")

                        if st.form_submit_button("Add Hearing"):
                            cases[i].setdefault("hearings", []).append({
                                "date": str(h_date),
                                "time": h_time,
                                "purpose": h_purpose,
                                "outcome": h_outcome,
                                "notes": h_notes,
                            })
                            save_cases(user_id, cases)
                            st.success("✅ Hearing added!")
                            st.rerun()

                    # Saved analyses
                    analyses = case.get("analyses", [])
                    if analyses:
                        st.markdown(f"**Saved Analyses ({len(analyses)}):**")
                        for j, a in enumerate(analyses):
                            with st.expander(f"Analysis — {a.get('date', '?')[:10]}"):
                                st.markdown(a.get("content", ""))
                                render_export_buttons(
                                    a.get("content", ""),
                                    title=f"{case.get('title', 'Case')}_Analysis_{j+1}",
                                    key_prefix=f"ca_{i}_{j}",
                                )

                    # Delete
                    if st.button("🗑️ Delete Case", key=f"del_case_{i}"):
                        cases.pop(i)
                        save_cases(user_id, cases)
                        st.rerun()

    # ── Upcoming hearings ──
    with tab_hearings:
        st.subheader("📅 Upcoming Hearings")
        all_hearings = []
        for case in cases:
            if case.get("next_hearing"):
                all_hearings.append({
                    "Case": case.get("title", "Untitled"),
                    "Suit No.": case.get("case_number", ""),
                    "Date": case["next_hearing"],
                    "Court": case.get("court", "N/A"),
                    "Purpose": "Next scheduled hearing",
                })
            for h in case.get("hearings", []):
                if h.get("outcome") == "Pending":
                    all_hearings.append({
                        "Case": case.get("title", "Untitled"),
                        "Suit No.": case.get("case_number", ""),
                        "Date": h.get("date", ""),
                        "Court": case.get("court", "N/A"),
                        "Purpose": h.get("purpose", ""),
                    })
        if all_hearings:
            all_hearings.sort(key=lambda x: x.get("Date", ""))
            st.dataframe(pd.DataFrame(all_hearings), use_container_width=True, hide_index=True)
        else:
            st.info("No upcoming hearings. Add hearing dates to your cases.")


# ───────────────────────────────────────────────────────
#  CLIENTS & BILLING
# ───────────────────────────────────────────────────────
def page_clients_billing():
    user_id = st.session_state.get("user_id", "")
    st.header("👥 Clients & Billing")
    clients = load_clients(user_id)
    billing = load_billing(user_id)

    tab_clients, tab_add, tab_billing, tab_invoices = st.tabs(
        ["📋 Clients", "➕ Add Client", "⏱️ Time & Billing", "🧾 Invoices"]
    )

    # ── Add client ──
    with tab_add:
        with st.form("add_client"):
            st.subheader("New Client")
            c_name = st.text_input("Client Name*")
            c1, c2 = st.columns(2)
            with c1:
                c_email = st.text_input("Email", placeholder="client@example.com")
                c_phone = st.text_input("Phone", placeholder="+234...")
            with c2:
                c_type = st.selectbox("Type", ["Individual", "Corporate", "Government", "NGO"])
                c_status = st.selectbox("Status", ["Active", "Inactive", "Prospective"])
            c_address = st.text_input("Address")
            c_notes = st.text_area("Notes")

            if st.form_submit_button("💾 Save Client", type="primary", use_container_width=True):
                if not c_name:
                    st.error("Client name is required.")
                else:
                    clients.append({
                        "id": hashlib.md5(
                            f"{c_name}{datetime.now().isoformat()}".encode()
                        ).hexdigest()[:12],
                        "name": c_name, "email": c_email, "phone": c_phone,
                        "type": c_type, "status": c_status,
                        "address": c_address, "notes": c_notes,
                        "created": datetime.now().isoformat(),
                    })
                    save_clients(user_id, clients)
                    st.success(f"✅ Client **{c_name}** saved!")
                    st.rerun()

    # ── Client list ──
    with tab_clients:
        if not clients:
            st.info("No clients yet. Add your first client.")
        else:
            st.caption(f"{len(clients)} client(s)")
            for i, cl in enumerate(clients):
                icon = "🟢" if cl.get("status") == "Active" else "⚪"
                with st.expander(f"{icon} {cl.get('name', 'Unnamed')} — {cl.get('type', '')}"):
                    cc1, cc2, cc3 = st.columns(3)
                    cc1.write(f"📧 {cl.get('email', 'N/A')}")
                    cc2.write(f"📞 {cl.get('phone', 'N/A')}")
                    cc3.write(f"📍 {cl.get('address', 'N/A')}")
                    if cl.get("notes"):
                        st.markdown(f"**Notes:** {cl['notes']}")
                    client_total = sum(
                        b.get("amount", 0) for b in billing if b.get("client") == cl.get("name")
                    )
                    st.metric("Total Billed", f"₦{client_total:,.2f}")
                    if st.button("🗑️ Delete", key=f"del_cl_{i}"):
                        clients.pop(i)
                        save_clients(user_id, clients)
                        st.rerun()

    # ── Time & billing ──
    with tab_billing:
        st.subheader("⏱️ Log Time Entry")
        with st.form("billing_form"):
            client_names = (
                [c.get("name") for c in clients]
                if clients
                else ["(No clients — add one first)"]
            )
            b_client = st.selectbox("Client", client_names)
            bc1, bc2 = st.columns(2)
            with bc1:
                b_date = st.date_input("Date")
                b_hours = st.number_input("Hours", min_value=0.0, step=0.25, value=1.0)
            with bc2:
                b_rate = st.number_input("Hourly Rate (₦)", min_value=0, step=5000, value=50000)
                b_status = st.selectbox("Status", ["Unbilled", "Billed", "Paid"])
            b_desc = st.text_input("Description*", placeholder="e.g., Drafting motion on notice")

            if st.form_submit_button("💾 Log Entry", type="primary", use_container_width=True):
                if not b_desc:
                    st.error("Description is required.")
                elif b_client.startswith("(No"):
                    st.error("Please add a client first.")
                else:
                    amount = b_hours * b_rate
                    billing.append({
                        "id": hashlib.md5(
                            f"{b_client}{datetime.now().isoformat()}".encode()
                        ).hexdigest()[:12],
                        "client": b_client, "date": str(b_date),
                        "description": b_desc, "hours": b_hours,
                        "rate": b_rate, "amount": amount,
                        "status": b_status,
                        "created": datetime.now().isoformat(),
                    })
                    save_billing(user_id, billing)
                    st.success(f"✅ ₦{amount:,.2f} logged for **{b_client}**")
                    st.rerun()

        if billing:
            st.divider()
            st.subheader("📊 Billing Summary")
            df = pd.DataFrame(billing)
            show = [c for c in ["date", "client", "description", "hours", "rate", "amount", "status"] if c in df.columns]
            st.dataframe(df[show], use_container_width=True, hide_index=True)
            s1, s2, s3 = st.columns(3)
            s1.metric("Total Billed", f"₦{df['amount'].sum():,.2f}")
            s2.metric("Total Hours", f"{df['hours'].sum():,.1f}")
            paid = df[df["status"] == "Paid"]["amount"].sum() if "status" in df.columns else 0
            s3.metric("Paid", f"₦{paid:,.2f}")

    # ── Invoices ──
    with tab_invoices:
        st.subheader("🧾 Generate Invoice")
        if not clients or not billing:
            st.info("Add clients and billing entries first.")
        else:
            inv_client = st.selectbox(
                "Client", [c.get("name") for c in clients], key="inv_cl"
            )
            unbilled = [
                b for b in billing
                if b.get("client") == inv_client and b.get("status") != "Paid"
            ]
            if unbilled:
                inv_df = pd.DataFrame(unbilled)
                st.dataframe(
                    inv_df[["date", "description", "hours", "rate", "amount"]],
                    use_container_width=True, hide_index=True,
                )
                total = sum(e.get("amount", 0) for e in unbilled)
                st.markdown(f"### Total: ₦{total:,.2f}")

                if st.button("📄 Generate Invoice", key="gen_inv"):
                    inv_no = hashlib.md5(
                        f"{inv_client}{datetime.now().isoformat()}".encode()
                    ).hexdigest()[:6].upper()
                    lines = [
                        "INVOICE",
                        "=" * 50,
                        f"To: {inv_client}",
                        f"Date: {datetime.now():%d %B %Y}",
                        f"Invoice No: INV-{inv_no}",
                        "=" * 50, "",
                    ]
                    for e in unbilled:
                        lines.append(
                            f"{e.get('date')} | {e.get('description')} | "
                            f"{e.get('hours')}hrs × ₦{e.get('rate'):,.0f} = ₦{e.get('amount'):,.2f}"
                        )
                    lines += [
                        "", "=" * 50,
                        f"TOTAL DUE: ₦{total:,.2f}", "",
                        "Payment is due within 30 days.",
                        "Thank you for your patronage.",
                    ]
                    invoice_text = "\n".join(lines)
                    st.text_area("Invoice Preview", invoice_text, height=300, key="inv_prev")
                    render_export_buttons(invoice_text, title=f"Invoice_{inv_client}", key_prefix="inv_exp")
            else:
                st.info(f"No outstanding entries for {inv_client}.")


# ───────────────────────────────────────────────────────
#  LEGAL REFERENCES
# ───────────────────────────────────────────────────────
def page_references():
    user_id = st.session_state.get("user_id", "")
    st.header("📚 Legal References")

    tab_lim, tab_courts, tab_maxims = st.tabs(
        ["⏳ Limitation Periods", "🏛️ Court Hierarchy", "📜 Latin Maxims"]
    )

    for tab, ref_type, label, default_fn in [
        (tab_lim, "limitation_periods", "Limitation Periods", get_default_limitation_periods),
        (tab_courts, "court_hierarchy", "Court Hierarchy", get_court_hierarchy),
        (tab_maxims, "latin_maxims", "Latin Maxims", get_latin_maxims),
    ]:
        with tab:
            st.subheader(label)
            data = get_user_references(user_id, ref_type)
            df = pd.DataFrame(data)
            edited = st.data_editor(
                df, use_container_width=True, num_rows="dynamic", key=f"ed_{ref_type}"
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 Save Changes", key=f"save_{ref_type}"):
                    refs = load_references(user_id) or {}
                    refs[ref_type] = edited.to_dict("records")
                    save_references(user_id, refs)
                    st.success("✅ Saved!")
            with c2:
                if st.button("🔄 Reset to Defaults", key=f"reset_{ref_type}"):
                    refs = load_references(user_id) or {}
                    refs[ref_type] = default_fn()
                    save_references(user_id, refs)
                    st.success("Reset to defaults.")
                    st.rerun()


# ───────────────────────────────────────────────────────
#  DOCUMENT TEMPLATES
# ───────────────────────────────────────────────────────
DEFAULT_TEMPLATES = [
    {"name": "Contract of Sale", "category": "Commercial",
     "description": "Sale of goods or property under Nigerian law."},
    {"name": "Tenancy Agreement", "category": "Real Property",
     "description": "Residential or commercial lease compliant with state tenancy laws."},
    {"name": "Power of Attorney", "category": "General",
     "description": "General or special power of attorney."},
    {"name": "Demand / Pre-Action Letter", "category": "Litigation",
     "description": "Formal demand letter preceding legal action."},
    {"name": "Written Address", "category": "Litigation",
     "description": "Written address (legal submission) for court proceedings."},
    {"name": "Employment Contract", "category": "Labour",
     "description": "Employment agreement compliant with the Labour Act."},
    {"name": "Non-Disclosure Agreement", "category": "Commercial",
     "description": "Mutual or unilateral NDA for business dealings."},
    {"name": "Board Resolution", "category": "Corporate",
     "description": "Board resolution compliant with CAMA 2020."},
    {"name": "Affidavit", "category": "Litigation",
     "description": "General-purpose affidavit for court proceedings."},
    {"name": "Memorandum of Understanding", "category": "Commercial",
     "description": "MOU for preliminary agreements or partnerships."},
]


def page_templates():
    user_id = st.session_state.get("user_id", "")
    st.header("📝 Document Templates")
    custom_templates = load_templates(user_id)
    all_templates = DEFAULT_TEMPLATES + custom_templates

    tab_gen, tab_custom = st.tabs(["📄 Generate from Template", "➕ Custom Templates"])

    with tab_gen:
        names = [t["name"] for t in all_templates]
        selected_name = st.selectbox("Template:", names, key="tmpl_sel")
        selected = next((t for t in all_templates if t["name"] == selected_name), None)

        if selected:
            st.caption(
                f"**{selected.get('category', 'General')}** — "
                f"{selected.get('description', '')}"
            )
            with st.form("template_form"):
                st.markdown("**Fill in the details:**")
                tc1, tc2 = st.columns(2)
                with tc1:
                    party_a = st.text_input("Party A (First Party)")
                    party_a_addr = st.text_input("Party A Address")
                with tc2:
                    party_b = st.text_input("Party B (Second Party)")
                    party_b_addr = st.text_input("Party B Address")
                subject = st.text_input("Subject Matter",
                    placeholder="e.g., Sale of Plot 24, Lekki Phase 1")
                consideration = st.text_input("Consideration / Value",
                    placeholder="e.g., ₦50,000,000")
                additional = st.text_area("Additional Instructions / Special Terms")

                if st.form_submit_button(
                    "⚡ Generate Document", type="primary", use_container_width=True
                ):
                    gen_prompt = (
                        f"Generate a complete, professional {selected['name']} "
                        f"under Nigerian law.\n\n"
                        f"Party A: {party_a or '[Party A]'} of {party_a_addr or '[Address]'}\n"
                        f"Party B: {party_b or '[Party B]'} of {party_b_addr or '[Address]'}\n"
                        f"Subject: {subject or '[Subject Matter]'}\n"
                        f"Consideration: {consideration or '[To be agreed]'}\n"
                        f"Special terms: {additional or 'None'}\n\n"
                        f"Include: recitals, definitions, operative clauses, boilerplate "
                        f"(governing law, dispute resolution, severability, entire agreement), "
                        f"and execution block with signature and witness lines.\n"
                        f"Ensure compliance with all relevant Nigerian statutes."
                    )
                    with st.spinner(f"⚡ Drafting {selected['name']}..."):
                        result = call_gemini(
                            prompt=gen_prompt, mode="Comprehensive", user_id=user_id,
                        )
                    if result.get("error"):
                        st.error(result["error"])
                    else:
                        st.markdown("### 📄 Generated Document")
                        st.markdown(result["text"])
                        render_token_display(result)
                        render_export_buttons(
                            result["text"], title=selected["name"], key_prefix="tmpl_exp"
                        )

    with tab_custom:
        st.subheader("➕ Add Custom Template")
        with st.form("custom_tmpl"):
            ct_name = st.text_input("Template Name*")
            ct_cat = st.text_input("Category", placeholder="e.g., Commercial")
            ct_desc = st.text_area("Description / Instructions")
            if st.form_submit_button("💾 Save Template", use_container_width=True):
                if not ct_name:
                    st.error("Template name is required.")
                else:
                    custom_templates.append({
                        "name": ct_name,
                        "category": ct_cat or "General",
                        "description": ct_desc,
                    })
                    save_templates(user_id, custom_templates)
                    st.success(f"✅ Template **{ct_name}** saved!")
                    st.rerun()

        if custom_templates:
            st.divider()
            st.subheader("Your Custom Templates")
            for i, ct in enumerate(custom_templates):
                cc1, cc2 = st.columns([4, 1])
                cc1.markdown(
                    f"**{ct['name']}** ({ct.get('category', '')}) — "
                    f"{ct.get('description', '')[:80]}"
                )
                if cc2.button("🗑️", key=f"del_tmpl_{i}"):
                    custom_templates.pop(i)
                    save_templates(user_id, custom_templates)
                    st.rerun()


# ───────────────────────────────────────────────────────
#  AI USAGE & COSTS
# ───────────────────────────────────────────────────────
def page_usage():
    user_id = st.session_state.get("user_id", "")
    st.header("📊 AI Usage & Costs")
    usage = load_usage(user_id)

    if not usage:
        st.info("No usage data yet. Start using the AI Assistant to track stats.")
        return

    df = pd.DataFrame(usage)

    # Summary
    u1, u2, u3, u4 = st.columns(4)
    u1.metric("Total Queries", len(df))
    u2.metric("Input Tokens", f"{df['input_tokens'].sum():,}")
    u3.metric("Output Tokens", f"{df['output_tokens'].sum():,}")
    u4.metric("Total Cost", f"${df['cost'].sum():.4f}")

    # By model
    st.subheader("🤖 By Model")
    if "model" in df.columns:
        model_stats = df.groupby("model").agg(
            queries=("model", "count"),
            input_tokens=("input_tokens", "sum"),
            output_tokens=("output_tokens", "sum"),
            cost=("cost", "sum"),
        ).reset_index()
        st.dataframe(model_stats, use_container_width=True, hide_index=True)

    # Charts
    st.subheader("📅 Over Time")
    if "timestamp" in df.columns:
        df["date"] = pd.to_datetime(df["timestamp"]).dt.date
        daily = df.groupby("date").agg(
            queries=("date", "count"),
            cost=("cost", "sum"),
        ).reset_index()
        try:
            import plotly.express as px
            fig = px.bar(
                daily, x="date", y="queries", title="Queries per Day",
                color_discrete_sequence=["#059669"],
            )
            st.plotly_chart(fig, use_container_width=True)
            fig2 = px.line(
                daily, x="date", y="cost", title="Daily Cost ($)",
                color_discrete_sequence=["#059669"],
            )
            st.plotly_chart(fig2, use_container_width=True)
        except ImportError:
            st.line_chart(daily.set_index("date")[["queries"]])
            st.line_chart(daily.set_index("date")[["cost"]])

    # Log + export
    with st.expander("📋 Full Usage Log"):
        show = [c for c in ["timestamp", "model", "input_tokens", "output_tokens", "cost"] if c in df.columns]
        st.dataframe(df[show], use_container_width=True, hide_index=True)

    st.download_button(
        "📥 Export CSV", df.to_csv(index=False).encode("utf-8"),
        file_name="lexiassist_usage.csv", mime="text/csv",
    )


# ───────────────────────────────────────────────────────
#  SETTINGS
# ───────────────────────────────────────────────────────
def page_settings():
    user_id = st.session_state.get("user_id", "")
    st.header("⚙️ Settings")

    tab_profile, tab_api, tab_data = st.tabs(
        ["👤 Profile", "🔑 API Key", "💾 Data Management"]
    )

    with tab_profile:
        profile = get_user_profile(user_id)

        with st.form("profile_form"):
            display_name = st.text_input(
                "Display Name",
                value=profile.get("display_name", st.session_state.get("username", "")),
            )
            email = st.text_input("Email", value=profile.get("email", ""))
            firm = st.text_input("Firm / Chambers", value=profile.get("firm", ""))
            if st.form_submit_button("💾 Update Profile", use_container_width=True):
                update_user_profile(user_id, {
                    "display_name": display_name, "email": email, "firm": firm,
                })
                st.success("✅ Profile updated!")

        st.divider()
        st.subheader("🔒 Change Password")
        with st.form("pw_form"):
            old_pw = st.text_input("Current Password", type="password")
            new_pw = st.text_input("New Password", type="password")
            confirm_pw = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("🔒 Change Password", use_container_width=True):
                if not old_pw or not new_pw:
                    st.error("All fields are required.")
                elif len(new_pw) < 6:
                    st.error("Minimum 6 characters.")
                elif new_pw != confirm_pw:
                    st.error("Passwords do not match.")
                elif change_password(user_id, old_pw, new_pw):
                    st.success("✅ Password changed!")
                else:
                    st.error("Current password is incorrect.")

    with tab_api:
        current_key = _resolve_api_key()
        if current_key:
            masked = current_key[:8] + "•" * max(len(current_key) - 12, 0) + current_key[-4:]
            st.success(f"✅ API key active: `{masked}`")
        else:
            st.warning("⚠️ No API key configured.")

        new_key = st.text_input(
            "Set Gemini API Key (this session only):",
            type="password", key="set_api",
            placeholder="Paste your key...",
        )
        if new_key:
            st.session_state["api_key_input"] = new_key
            st.success("✅ Key set for this session.")
        st.caption(
            "For persistent keys, use Streamlit Cloud dashboard or "
            "`.streamlit/secrets.toml`."
        )

    with tab_data:
        st.subheader("💾 Export All Data")
        if st.button("📥 Export as JSON", key="exp_all", use_container_width=True):
            payload = {
                "cases": load_cases(user_id),
                "clients": load_clients(user_id),
                "billing": load_billing(user_id),
                "chat_history": load_chat_history(user_id),
                "references": load_references(user_id),
                "templates": load_templates(user_id),
                "usage": load_usage(user_id),
                "exported": datetime.now().isoformat(),
            }
            st.download_button(
                "⬇️ Download Backup",
                json.dumps(payload, indent=2, default=str).encode("utf-8"),
                file_name=f"lexiassist_backup_{datetime.now():%Y%m%d}.json",
                mime="application/json", key="dl_backup",
            )

        st.divider()
        st.markdown("**⚠️ Danger Zone**")
        with st.expander("🗑️ Clear All Data"):
            st.warning(
                "This permanently deletes all cases, clients, billing, "
                "chat history, and custom references."
            )
            confirm_txt = st.text_input("Type DELETE to confirm:", key="del_confirm")
            if st.button("🗑️ Delete Everything", type="primary", key="nuke"):
                if confirm_txt == "DELETE":
                    for fn, empty in [
                        (save_cases, []), (save_clients, []),
                        (save_billing, []), (save_chat_history, []),
                        (save_references, {}), (save_templates, []),
                    ]:
                        fn(user_id, empty)
                    st.session_state["chat_history"] = []
                    st.session_state["last_result"] = None
                    st.success("All data cleared.")
                    st.rerun()
                else:
                    st.error("Type DELETE to confirm.")
# ═══════════════════════════════════════════════════════
# PART 4 — MAIN APP ENTRY POINT
# ═══════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────
#  CUSTOM CSS
# ───────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
    /* ── Global ── */
    .stApp {
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }

    /* ── Sidebar branding ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
        border-right: 1px solid #e2e8f0;
    }
    [data-testid="stSidebar"] h3 {
        color: #059669;
        font-weight: 700;
    }

    /* ── Chat messages ── */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
        margin-bottom: 0.5rem;
        border: 1px solid #e2e8f0;
    }

    /* ── Buttons ── */
    .stButton > button[kind="primary"] {
        background-color: #059669;
        border: none;
        color: white;
        border-radius: 8px;
        font-weight: 600;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #047857;
    }
    .stButton > button[kind="secondary"] {
        border-radius: 8px;
        border: 1px solid #cbd5e1;
    }

    /* ── Metrics ── */
    [data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px 16px;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.1rem;
        font-weight: 700;
        color: #059669;
    }

    /* ── Expanders ── */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #1e293b;
    }

    /* ── Data editor ── */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }

    /* ── Download buttons ── */
    .stDownloadButton > button {
        border-radius: 8px;
        font-size: 0.85rem;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        color: #059669;
        border-bottom-color: #059669;
    }

    /* ── Form borders ── */
    [data-testid="stForm"] {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
    }

    /* ── Footer ── */
    .app-footer {
        text-align: center;
        padding: 2rem 1rem 1rem;
        color: #94a3b8;
        font-size: 0.8rem;
        border-top: 1px solid #e2e8f0;
        margin-top: 3rem;
    }
    .app-footer a {
        color: #059669;
        text-decoration: none;
    }

    /* ── Hide default Streamlit footer ── */
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
</style>
"""

# ───────────────────────────────────────────────────────
#  FOOTER
# ───────────────────────────────────────────────────────
FOOTER_HTML = """
<div class="app-footer">
    ⚖️ <strong>LexiAssist</strong> — AI-Powered Legal Workspace for Nigerian Lawyers<br>
    <em>AI-generated content is for informational purposes only. Always verify citations
    and consult qualified counsel before acting on any legal analysis.</em><br><br>
    Built with ❤️ for the Nigerian Legal Community
</div>
"""


# ───────────────────────────────────────────────────────
#  PAGE ROUTER
# ───────────────────────────────────────────────────────
PAGE_MAP = {
    "AI Assistant": page_ai_assistant,
    "Cases & Hearings": page_cases,
    "Clients & Billing": page_clients_billing,
    "Legal References": page_references,
    "Document Templates": page_templates,
    "AI Usage & Costs": page_usage,
    "Settings": page_settings,
}


# ───────────────────────────────────────────────────────
#  MAIN
# ───────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Initialise DB + session
    init_db()
    init_session_state()

    # ── Not logged in → show login page ──
    if not st.session_state.get("authenticated"):
        page_login()
        st.markdown(FOOTER_HTML, unsafe_allow_html=True)
        return

    # ── Authenticated → full app ──
    render_sidebar()

    current_page = st.session_state.get("current_page", "AI Assistant")
    page_fn = PAGE_MAP.get(current_page, page_ai_assistant)

    try:
        page_fn()
    except Exception as e:
        st.error(f"Something went wrong loading **{current_page}**.")
        with st.expander("🔍 Error Details"):
            st.code(str(e))
        st.info("Try refreshing or switching to another page.")

    # Footer
    st.markdown(FOOTER_HTML, unsafe_allow_html=True)


# ───────────────────────────────────────────────────────
#  ENTRY POINT
# ───────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
