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
# SECURITY & USER PROFILE
# ═══════════════════════════════════════════════════════
def safe_secret(key, default=""):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def hash_password(password):
    salt = os.environ.get("LEXIASSIST_SALT", "lexiassist_v8")
    return hashlib.sha256((password + salt).encode()).hexdigest()


def verify_password(password, hashed):
    return hash_password(password) == hashed


def get_user_profile():
    rows = db_fetch_all("user_profile", order="id ASC")
    return rows[0] if rows else None


def save_user_profile(data):
    existing = get_user_profile()
    now = datetime.now().isoformat(timespec="seconds")
    if existing:
        data["updated_at"] = now
        db_update("user_profile", existing["id"], data)
    else:
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        db_insert("user_profile", data)


def ensure_profile_exists():
    if not get_user_profile():
        save_user_profile({"firm_name": "", "user_name": "", "email": "", "password_hash": ""})


# ═══════════════════════════════════════════════════════
# API CONFIGURATION
# ═══════════════════════════════════════════════════════
def _resolve_api_key():
    for src in [safe_secret("GEMINI_API_KEY"), os.environ.get("GEMINI_API_KEY", ""), st.session_state.get("api_key_input", "")]:
        if src and len(src.strip()) >= 10:
            return src.strip()
    return ""


def configure_gemini(model_name=None):
    if not HAS_GENAI:
        st.session_state["api_error"] = "google-generativeai not installed."
        return False
    api_key = _resolve_api_key()
    if not api_key:
        st.session_state["api_error"] = "No valid API key."
        return False
    try:
        genai.configure(api_key=api_key)
        st.session_state["api_configured"] = True
        st.session_state["model"] = model_name or safe_secret("GEMINI_MODEL", SUPPORTED_MODELS[0])
        st.session_state.pop("api_error", None)
        return True
    except Exception as err:
        st.session_state["api_error"] = str(err)
        st.session_state["api_configured"] = False
        return False


def get_available_models():
    if "available_models" not in st.session_state:
        st.session_state["available_models"] = SUPPORTED_MODELS
    return st.session_state["available_models"]


def ensure_api_configured():
    if not st.session_state.get("api_configured"):
        configure_gemini(st.session_state.get("model", SUPPORTED_MODELS[0]))


# ═══════════════════════════════════════════════════════
# DOCUMENT PARSING
# ═══════════════════════════════════════════════════════
def parse_uploaded_file(upload):
    if not upload:
        return ""
    suffix = Path(upload.name).suffix.lower()
    try:
        if suffix in [".txt", ".md", ".rtf"]:
            data = upload.read()
            return data.decode("utf-8", errors="ignore") if isinstance(data, bytes) else data
        if suffix == ".pdf" and HAS_PDF:
            chunks = []
            with pdfplumber.open(upload) as pdf:
                for page in pdf.pages[:10]:
                    chunks.append(page.extract_text() or "")
            return "\n\n".join(chunks).strip()
        if suffix in [".docx", ".doc"] and HAS_DOCX:
            doc = DocxDocument(upload)
            return "\n".join(p.text for p in doc.paragraphs if p.text).strip()
        if suffix == ".json":
            return json.dumps(json.load(upload), indent=2)
        if suffix == ".csv" and pd:
            return pd.read_csv(upload).to_string()
        if suffix in [".xlsx", ".xls"] and pd:
            return pd.read_excel(upload).to_string()
        return upload.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        return f"Parse error: {exc}"


# ═══════════════════════════════════════════════════════
# AI PROMPT ENGINE
# ═══════════════════════════════════════════════════════
def build_prompt_instructions(query, analysis_type, response_mode, user_context, doc_context, client_name):
    mode = RESPONSE_MODES.get(response_mode, RESPONSE_MODES["📝 Standard"])
    ctx = []
    if client_name:
        ctx.append(f"Client: {client_name}")
    if user_context:
        ctx.append(f"User Context:\n{user_context.strip()}")
    if doc_context:
        ctx.append(f"Document Context:\n{doc_context.strip()}")
    ctx_text = "\n\n".join(ctx).strip()
    instructions = f"""You are LexiAssist v8.0, an elite AI legal engine for Nigerian lawyers.
Analysis type: {analysis_type}. Response mode: {response_mode} (~{mode['tokens']} tokens).
Core rules:
- Cite Nigerian statutes/cases with proper party names and year.
- Apply CREAC/ILAC where relevant.
- Highlight procedural steps with timelines.
- Map risks with mitigation strategies.
- Use formal Nigerian legal drafting tone.
- If data is missing, state assumptions clearly.

Query:
\"\"\"{query.strip()}\"\"\""""
    if ctx_text:
        instructions += f"\n\nContext:\n{ctx_text}"
    if analysis_type == "📑 Contract Review":
        instructions += "\n\nDeliverables:\n- Clause-by-clause red flag analysis\n- Risk rating per clause\n"
    else:
        instructions += "\n\nDeliverables:\n- Structured analysis with conclusions and recommendations\n"
    return instructions.strip()


def call_gemini(prompt, model_name, response_mode):
    ensure_api_configured()
    model_name = model_name or st.session_state.get("model", SUPPORTED_MODELS[0])
    mode = RESPONSE_MODES.get(response_mode, RESPONSE_MODES["📝 Standard"])
    gen_config = {
        "temperature": 0.3 if response_mode == "🔬 Comprehensive" else 0.5,
        "top_p": 0.95, "top_k": 40,
        "max_output_tokens": mode["tokens"],
    }
    safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in
              ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
               "HARM_CATEGORY_SEXUAL_CONTENT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt, generation_config=gen_config, safety_settings=safety)
        text = response.text or "(No response.)"
        usage = getattr(response, "usage_metadata", None)
        tokens = {
            "prompt": getattr(usage, "prompt_token_count", 0) if usage else 0,
            "candidates": getattr(usage, "candidates_token_count", 0) if usage else 0,
            "total": getattr(usage, "total_token_count", 0) if usage else 0,
        }
        return text.strip(), tokens
    except Exception as exc:
        raise RuntimeError(f"Gemini API error: {exc}") from exc


# ═══════════════════════════════════════════════════════
# COST TRACKING
# ═══════════════════════════════════════════════════════
def log_cost(model, tokens, query_preview):
    total = tokens.get("total", tokens.get("prompt", 0) + tokens.get("candidates", 0))
    db_insert("cost_log", {
        "model": model, "prompt_tokens": tokens.get("prompt", 0),
        "response_tokens": tokens.get("candidates", 0),
        "total_cost": total * 0.0000025, "query_preview": query_preview[:200],
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })


def summarize_costs(period="all"):
    conn = _get_conn()
    try:
        sql = "SELECT SUM(prompt_tokens) AS p, SUM(response_tokens) AS r, SUM(total_cost) AS c FROM cost_log"
        params = ()
        if period in ("24h", "7d"):
            sql += " WHERE created_at >= ?"
            delta = timedelta(hours=24) if period == "24h" else timedelta(days=7)
            params = ((datetime.now() - delta).isoformat(timespec="seconds"),)
        row = conn.execute(sql, params).fetchone()
        return {"prompt": row["p"] or 0, "response": row["r"] or 0, "cost": row["c"] or 0.0}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════
# EXPORT UTILITIES
# ═══════════════════════════════════════════════════════
def export_text(content):
    return content or ""


def export_html(content, title="Legal Analysis"):
    profile = get_user_profile()
    firm = profile.get("firm_name", "LexiAssist v8.0") if profile else "LexiAssist v8.0"
    ts = datetime.now().strftime("%B %d, %Y")
    gt = datetime.now().strftime("%Y-%m-%d %H:%M")
    css = ("body{font-family:Georgia,serif;max-width:800px;margin:2rem auto;padding:1rem;"
           "line-height:1.7;color:#1e293b}h1{color:#059669;border-bottom:2px solid #059669;"
           "padding-bottom:.5rem}.header{text-align:center;margin-bottom:2rem}"
           ".content{white-space:pre-wrap}.footer{margin-top:3rem;padding-top:1rem;"
           "border-top:1px solid #ccc;font-size:.85rem;color:#666}")
    return ("<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
            f"<title>{esc(title)}</title><style>{css}</style></head><body>"
            f"<div class='header'><h1>{esc(firm)}</h1><p>{esc(title)}</p>"
            f"<p><small>{ts}</small></p></div><div class='content'>{content}</div>"
            f"<div class='footer'>Generated by LexiAssist v8.0 · {gt}"
            " · AI-generated — verify independently</div></body></html>")


def export_docx(content, title="LexiAssist Output"):
    if not HAS_DOCX:
        raise RuntimeError("python-docx not installed.")
    profile = get_user_profile()
    firm = profile.get("firm_name", "LexiAssist v8.0") if profile else "LexiAssist v8.0"
    doc = DocxDocument()
    doc.add_heading(firm, level=1)
    doc.add_paragraph(title)
    doc.add_paragraph(datetime.now().strftime("%B %d, %Y"))
    for line in content.split("\n"):
        doc.add_paragraph(line)
    return doc


def export_pdf(content, title="LexiAssist Output"):
    if not HAS_FPDF:
        raise RuntimeError("fpdf2 not installed.")
    profile = get_user_profile()
    firm = profile.get("firm_name", "LexiAssist v8.0") if profile else "LexiAssist v8.0"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, firm, ln=True, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, title, ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    for line in content.split("\n"):
        pdf.multi_cell(0, 6, line)
    return pdf.output(dest="S").encode("latin1", errors="ignore")


# ═══════════════════════════════════════════════════════
# BACKUP / RESTORE
# ═══════════════════════════════════════════════════════
def export_database_snapshot():
    conn = _get_conn()
    tables = ["cases", "case_notes", "clients", "time_entries", "invoices",
              "chat_history", "templates", "limitation_periods", "maxims", "cost_log", "user_profile"]
    snapshot = {"exported_at": datetime.now().isoformat(timespec="seconds")}
    try:
        for t in tables:
            snapshot[t] = [dict(r) for r in conn.execute(f"SELECT * FROM {t}").fetchall()]
    finally:
        conn.close()
    return snapshot


def restore_database_snapshot(snapshot):
    conn = _get_conn()
    tables = ["cases", "case_notes", "clients", "time_entries", "invoices",
              "chat_history", "templates", "limitation_periods", "maxims", "cost_log", "user_profile"]
    try:
        for t in tables:
            conn.execute(f"DELETE FROM {t}")
        for t in tables:
            rows = snapshot.get(t, [])
            if not rows:
                continue
            cols = list(rows[0].keys())
            sql = f"INSERT INTO {t} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})"
            conn.executemany(sql, [tuple(r[c] for c in cols) for r in rows])
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════
# UI HELPERS
# ═══════════════════════════════════════════════════════
def section_header(title, subtitle=""):
    st.markdown(f"<div class='page-header'><h2>{esc(title)}</h2><p>{esc(subtitle)}</p></div>", unsafe_allow_html=True)


def metric_card(label, value, help_text=""):
    h = f"<div style='font-size:.75rem;opacity:.7'>{esc(help_text)}</div>" if help_text else ""
    st.markdown(f"<div class='metric-card'><div class='metric-value'>{esc(str(value))}</div><div class='metric-label'>{esc(label)}</div>{h}</div>", unsafe_allow_html=True)


def badge(text, kind="info"):
    cls = {"ok": "badge-ok", "warn": "badge-warn", "error": "badge-error"}.get(kind, "badge-info")
    return f"<span class='badge {cls}'>{esc(text)}</span>"


# ═══════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("## ⚖️ LexiAssist v8.0")
        st.caption("AI legal workspace for Nigerian lawyers")
        theme = st.selectbox("Theme", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state["theme"]))
        st.session_state["theme"] = theme
        st.markdown("---")
        st.markdown("### 🤖 AI Configuration")
        models = get_available_models()
        cur = st.session_state.get("model") or models[0]
        idx = models.index(cur) if cur in models else 0
        st.session_state["model"] = st.selectbox("Gemini Model", models, index=idx)

        auth_enabled = str(safe_secret("AUTH_ENABLED", "false")).lower() == "true"
        profile = get_user_profile()
        if auth_enabled and profile and profile.get("password_hash") and not st.session_state.get("authenticated"):
            st.warning("🔒 Login required")
            pwd = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", use_container_width=True):
                if verify_password(pwd, profile["password_hash"]):
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Invalid password.")
        else:
            st.session_state["authenticated"] = True

        st.markdown("---")
        st.markdown("### 🔑 API Key")
        resolved = _resolve_api_key()
        if resolved:
            st.success("API key detected")
        else:
            st.info("Enter API key below")
            st.text_input("Gemini API Key", type="password", key="api_key_input")
        if st.button("Configure Gemini", use_container_width=True):
            if configure_gemini(st.session_state.get("model")):
                st.success("Configured!")
            else:
                st.error(st.session_state.get("api_error", "Failed."))

        st.markdown("---")
        st.markdown("### 📦 Backup & Restore")
        snap = export_database_snapshot()
        st.download_button("⬇️ Export Backup", data=json.dumps(snap, indent=2),
                           file_name=f"lexiassist_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                           mime="application/json", use_container_width=True)
        rf = st.file_uploader("Restore Backup", type=["json"], key="restore_backup")
        if rf and st.button("♻️ Restore", use_container_width=True):
            try:
                restore_database_snapshot(json.load(rf))
                st.success("Restored!")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        st.markdown("---")
        st.caption("Built with Streamlit + Gemini")


# ═══════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════
def render_dashboard():
    section_header("🏠 Dashboard", "Overview of cases, clients, billing, and AI usage")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Active Cases", db_count("cases", "status IN ('Active','Pending','Adjourned')"))
    with c2:
        metric_card("Clients", db_count("clients"))
    with c3:
        invoices = db_fetch_all("invoices")
        total_billed = sum(float(i.get("total", 0) or 0) for i in invoices)
        metric_card("Total Invoiced", f"₦{total_billed:,.2f}")
    with c4:
        cs = summarize_costs("7d")
        metric_card("AI Cost (7d)", f"${cs['cost']:.4f}")

    st.markdown("### 📅 Upcoming Hearings")
    cases = db_fetch_all("cases")
    upcoming = []
    today = date.today()
    for c in cases:
        nh = c.get("next_hearing", "")
        if nh:
            try:
                hd = datetime.strptime(nh, "%Y-%m-%d").date()
                if hd >= today:
                    upcoming.append({**c, "days_left": (hd - today).days})
            except Exception:
                pass
    upcoming.sort(key=lambda x: x["days_left"])
    if upcoming:
        for item in upcoming[:10]:
            kind = "ok" if item["days_left"] > 7 else "warn" if item["days_left"] > 2 else "error"
            st.markdown(f"<div class='custom-card'><strong>{esc(item['title'])}</strong><br>"
                        f"Suit: {esc(item.get('suit_number','—'))} · Court: {esc(item.get('court','—'))}<br>"
                        f"Hearing: {esc(item.get('next_hearing','—'))} {badge(f'{item[\"days_left\"]}d', kind)}</div>",
                        unsafe_allow_html=True)
    else:
        st.info("No upcoming hearings.")


# ═══════════════════════════════════════════════════════
# AI LEGAL ASSISTANT
# ═══════════════════════════════════════════════════════
def save_chat_history(query, response, analysis_type, response_mode, model, tokens=0):
    db_insert("chat_history", {"query": query, "response": response, "analysis_type": analysis_type,
              "response_mode": response_mode, "model": model,
              "timestamp": datetime.now().isoformat(timespec="seconds"), "tokens_used": tokens})


def render_ai_assistant():
    section_header("🤖 AI Legal Assistant", "Research, drafting, procedural guidance, and contract review")
    col1, col2 = st.columns([2, 1])
    with col2:
        st.markdown("### ⚙️ Options")
        analysis_type = st.selectbox("Task Type", ANALYSIS_TYPES)
        response_mode = st.selectbox("Response Mode", list(RESPONSE_MODES.keys()), index=1)
        client_name = st.text_input("Client / Matter Reference")
        extra_context = st.text_area("Additional Instructions", height=120)
        st.markdown("### 📎 Document Context")
        uploaded = st.file_uploader("Upload document", type=["pdf", "docx", "doc", "txt", "rtf", "xlsx", "xls", "csv", "json"])
        if uploaded:
            parsed = parse_uploaded_file(uploaded)
            st.session_state["document_context"] = parsed
            st.session_state["context_enabled"] = True
            st.success("Document loaded.")
            with st.expander("Preview"):
                st.text(parsed[:5000])
        else:
            st.session_state["context_enabled"] = False
            st.session_state["document_context"] = ""

    with col1:
        prompt = st.text_area("Enter your legal query", height=220,
                              placeholder="Example: Draft a written address opposing a preliminary objection...")
        run = st.button("🚀 Generate Response", type="primary", use_container_width=True)
        if run:
            if not st.session_state.get("authenticated"):
                st.error("Please authenticate first.")
                return
            if not prompt.strip():
                st.error("Enter a legal query.")
                return
            if not _resolve_api_key():
                st.error("API key not configured.")
                return
            try:
                with st.spinner("Analyzing..."):
                    fp = build_prompt_instructions(prompt, analysis_type, response_mode, extra_context,
                                                   st.session_state.get("document_context", "") if st.session_state.get("context_enabled") else "",
                                                   client_name)
                    result, tokens = call_gemini(fp, st.session_state.get("model"), response_mode)
                st.success("Analysis complete.")
                st.markdown(f"<div class='response-box'>{result}</div>", unsafe_allow_html=True)
                save_chat_history(prompt, result, analysis_type, response_mode, st.session_state.get("model", ""), tokens.get("total", 0))
                log_cost(st.session_state.get("model", ""), tokens, prompt)
                st.markdown("### 💾 Export")
                ec1, ec2, ec3, ec4 = st.columns(4)
                with ec1:
                    st.download_button("TXT", data=export_text(result), file_name="output.txt", mime="text/plain", use_container_width=True)
                with ec2:
                    st.download_button("HTML", data=export_html(result, analysis_type), file_name="output.html", mime="text/html", use_container_width=True)
                with ec3:
                    if HAS_DOCX:
                        try:
                            import io
                            doc = export_docx(result, analysis_type)
                            buf = io.BytesIO()
                            doc.save(buf)
                            st.download_button("DOCX", data=buf.getvalue(), file_name="output.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
                        except Exception:
                            st.caption("DOCX unavailable")
                    else:
                        st.caption("DOCX unavailable")
                with ec4:
                    if HAS_FPDF:
                        try:
                            st.download_button("PDF", data=export_pdf(result, analysis_type), file_name="output.pdf", mime="application/pdf", use_container_width=True)
                        except Exception:
                            st.caption("PDF unavailable")
                    else:
                        st.caption("PDF unavailable")
                st.markdown("### 📌 Save to Case")
                cases = db_fetch_all("cases", order="title ASC")
                if cases:
                    opts = {f"{c['title']} ({c.get('suit_number','')})": c["id"] for c in cases}
                    sel = st.selectbox("Select case", list(opts.keys()), key="save_case_sel")
                    nt = st.text_input("Note title", value=f"{analysis_type} · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                    if st.button("Save to Case", use_container_width=True):
                        db_insert("case_notes", {"case_id": opts[sel], "note_type": "ai_analysis", "title": nt, "content": result, "created_at": datetime.now().isoformat(timespec="seconds")})
                        st.success("Saved!")
                else:
                    st.info("Create a case first.")
            except Exception as exc:
                st.error(str(exc))

    st.markdown("### 🕘 Recent History")
    history = db_fetch_all("chat_history", order="id DESC")
    for item in history[:10]:
        with st.expander(f"{item['analysis_type']} · {item['timestamp']}"):
            st.markdown(f"**Query:** {item['query']}")
            st.markdown(f"<div class='response-box'>{item['response']}</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# CASE MANAGEMENT
# ═══════════════════════════════════════════════════════
def render_cases():
    section_header("📁 Case Management", "Track suits, courts, deadlines, and case-linked notes")
    tab1, tab2 = st.tabs(["➕ New Case", "📂 Existing Cases"])
    with tab1:
        with st.form("new_case_form", clear_on_submit=True):
            title = st.text_input("Case Title *")
            suit_number = st.text_input("Suit Number")
            court = st.text_input("Court")
            judge = st.text_input("Presiding Judge")
            status = st.selectbox("Status", CASE_STATUSES)
            client_name = st.text_input("Client Name")
            case_type = st.text_input("Case Type")
            date_filed = st.date_input("Date Filed", value=date.today())
            next_hearing = st.date_input("Next Hearing", value=date.today())
            description = st.text_area("Description", height=140)
            notes = st.text_area("Notes", height=120)
            if st.form_submit_button("Create Case", use_container_width=True):
                if not title.strip():
                    st.error("Title required.")
                else:
                    now = datetime.now().isoformat(timespec="seconds")
                    db_insert("cases", {"title": title.strip(), "suit_number": suit_number.strip(),
                              "court": court.strip(), "judge": judge.strip(), "status": status,
                              "client_name": client_name.strip(), "case_type": case_type.strip(),
                              "description": description.strip(),
                              "next_hearing": next_hearing.strftime("%Y-%m-%d") if next_hearing else "",
                              "date_filed": date_filed.strftime("%Y-%m-%d") if date_filed else "",
                              "notes": notes.strip(), "created_at": now, "updated_at": now})
                    st.success("Case created.")
                    st.rerun()
    with tab2:
        cases = db_fetch_all("cases", order="updated_at DESC")
        if not cases:
            st.info("No cases.")
            return
        for c in cases:
            with st.expander(f"{c['title']} · {c.get('suit_number','—')} · {c.get('status','')}"):
                st.markdown(f"<div class='custom-card'><strong>Court:</strong> {esc(c.get('court','—'))}<br>"
                            f"<strong>Judge:</strong> {esc(c.get('judge','—'))}<br>"
                            f"<strong>Client:</strong> {esc(c.get('client_name','—'))}<br>"
                            f"<strong>Filed:</strong> {esc(c.get('date_filed','—'))}<br>"
                            f"<strong>Next Hearing:</strong> {esc(c.get('next_hearing','—'))}</div>", unsafe_allow_html=True)
                st.write(c.get("description", "") or "—")
                notes = db_fetch_all("case_notes", where="case_id = ?", params=(c["id"],), order="id DESC")
                if notes:
                    for n in notes:
                        with st.expander(f"{n.get('title','Note')} · {n.get('created_at','')}"):
                            st.write(n.get("content", ""))
                            if st.button("Delete Note", key=f"dn_{n['id']}"):
                                db_delete("case_notes", n["id"])
                                st.rerun()
                bc1, bc2, bc3 = st.columns(3)
                with bc1:
                    if st.button("Archive", key=f"arc_{c['id']}", use_container_width=True):
                        db_update("cases", c["id"], {"status": "Archived", "updated_at": datetime.now().isoformat(timespec="seconds")})
                        st.rerun()
                with bc2:
                    if st.button("Close", key=f"cls_{c['id']}", use_container_width=True):
                        db_update("cases", c["id"], {"status": "Closed", "updated_at": datetime.now().isoformat(timespec="seconds")})
                        st.rerun()
                with bc3:
                    if st.button("Delete", key=f"del_{c['id']}", use_container_width=True):
                        db_delete("cases", c["id"])
                        st.rerun()


# ═══════════════════════════════════════════════════════
# CLIENT MANAGEMENT
# ═══════════════════════════════════════════════════════
def render_clients():
    section_header("👥 Client Management", "Manage client records")
    tab1, tab2 = st.tabs(["➕ New Client", "📋 All Clients"])
    with tab1:
        with st.form("new_client_form", clear_on_submit=True):
            name = st.text_input("Client Name *")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            client_type = st.selectbox("Type", CLIENT_TYPES)
            address = st.text_area("Address", height=80)
            notes = st.text_area("Notes", height=100)
            if st.form_submit_button("Create Client", use_container_width=True):
                if not name.strip():
                    st.error("Name required.")
                else:
                    db_insert("clients", {"name": name.strip(), "email": email.strip(), "phone": phone.strip(),
                              "type": client_type, "address": address.strip(), "notes": notes.strip(),
                              "created_at": datetime.now().isoformat(timespec="seconds")})
                    st.success("Client created.")
                    st.rerun()
    with tab2:
        clients = db_fetch_all("clients", order="name ASC")
        if not clients:
            st.info("No clients.")
            return
        for cl in clients:
            with st.expander(f"{cl['name']} · {cl.get('type','')}"):
                st.markdown(f"<div class='custom-card'>📧 {esc(cl.get('email','—'))} · 📞 {esc(cl.get('phone','—'))}<br>"
                            f"📍 {esc(cl.get('address','—'))}<br>Notes: {esc(cl.get('notes','—'))}</div>", unsafe_allow_html=True)
                if st.button("Delete", key=f"dcl_{cl['id']}", use_container_width=True):
                    db_delete("clients", cl["id"])
                    st.rerun()


# ═══════════════════════════════════════════════════════
# BILLING & INVOICING
# ═══════════════════════════════════════════════════════
def render_billing():
    section_header("💰 Billing & Invoicing", "Time entries and invoice generation")
    tab1, tab2, tab3 = st.tabs(["⏱️ Time Entry", "🧾 Invoices", "📊 Summary"])
    with tab1:
        clients = db_fetch_all("clients", order="name ASC")
        client_opts = {c["name"]: c["id"] for c in clients} if clients else {}
        with st.form("time_entry_form", clear_on_submit=True):
            cn = st.selectbox("Client", ["(No Client)"] + list(client_opts.keys()))
            desc = st.text_area("Work Description", height=100)
            tc1, tc2 = st.columns(2)
            with tc1:
                hours = st.number_input("Hours", min_value=0.0, step=0.25, value=1.0)
            with tc2:
                rate = st.number_input("Rate (₦/hr)", min_value=0.0, step=1000.0, value=50000.0)
            ed = st.date_input("Date", value=date.today())
            if st.form_submit_button("Log Time", use_container_width=True):
                amt = hours * rate
                db_insert("time_entries", {"client_id": client_opts.get(cn, 0),
                          "client_name": cn if cn != "(No Client)" else "", "description": desc.strip(),
                          "hours": hours, "rate": rate, "amount": amt,
                          "entry_date": ed.strftime("%Y-%m-%d"),
                          "created_at": datetime.now().isoformat(timespec="seconds")})
                st.success(f"Logged: ₦{amt:,.2f}")
                st.rerun()
        entries = db_fetch_all("time_entries", order="id DESC")
        for e in entries[:20]:
            st.markdown(f"<div class='custom-card'><strong>{esc(e.get('client_name','—'))}</strong> · {esc(e.get('entry_date',''))}<br>"
                        f"{esc(e.get('description','')[:120])}<br>"
                        f"{e.get('hours',0):.2f}hrs × ₦{e.get('rate',0):,.0f} = <strong>₦{e.get('amount',0):,.2f}</strong></div>", unsafe_allow_html=True)
    with tab2:
        clients_inv = db_fetch_all("clients", order="name ASC")
        if not clients_inv:
            st.info("Add clients first.")
        else:
            inv_cl = st.selectbox("Invoice Client", [c["name"] for c in clients_inv], key="inv_cl_sel")
            unbilled = db_fetch_all("time_entries", where="client_name = ?", params=(inv_cl,))
            if unbilled:
                total = sum(float(e.get("amount", 0) or 0) for e in unbilled)
                st.write(f"**{len(unbilled)}** entries · **₦{total:,.2f}**")
                if st.button("Generate Invoice", type="primary", use_container_width=True):
                    inv_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    db_insert("invoices", {"invoice_no": inv_no, "client_id": 0, "client_name": inv_cl,
                              "entries_json": json.dumps([dict(e) for e in unbilled]),
                              "total": total, "status": "Draft",
                              "created_at": datetime.now().isoformat(timespec="seconds")})
                    st.success(f"Invoice {inv_no}: ₦{total:,.2f}")
                    st.rerun()
            else:
                st.info(f"No entries for {inv_cl}.")
        invoices = db_fetch_all("invoices", order="id DESC")
        for inv in invoices:
            with st.expander(f"{inv['invoice_no']} · {inv['client_name']} · ₦{inv.get('total',0):,.2f}"):
                ic1, ic2, ic3 = st.columns(3)
                with ic1:
                    if st.button("Sent", key=f"is_{inv['id']}"):
                        db_update("invoices", inv["id"], {"status": "Sent"})
                        st.rerun()
                with ic2:
                    if st.button("Paid", key=f"ip_{inv['id']}"):
                        db_update("invoices", inv["id"], {"status": "Paid"})
                        st.rerun()
                with ic3:
                    if st.button("Delete", key=f"id_{inv['id']}"):
                        db_delete("invoices", inv["id"])
                        st.rerun()
    with tab3:
        entries = db_fetch_all("time_entries")
        invoices = db_fetch_all("invoices")
        s1, s2, s3 = st.columns(3)
        with s1:
            metric_card("Logged", f"₦{sum(float(e.get('amount',0) or 0) for e in entries):,.2f}")
        with s2:
            metric_card("Invoiced", f"₦{sum(float(i.get('total',0) or 0) for i in invoices):,.2f}")
        with s3:
            metric_card("Paid", f"₦{sum(float(i.get('total',0) or 0) for i in invoices if i.get('status')=='Paid'):,.2f}")


# ═══════════════════════════════════════════════════════
# LEGAL REFERENCE TOOLS
# ═══════════════════════════════════════════════════════
def render_legal_tools():
    section_header("📚 Legal Reference Tools", "Court hierarchy, limitation periods, Latin maxims, templates")
    tab1, tab2, tab3, tab4 = st.tabs(["🏛️ Courts", "⏳ Limitation", "📜 Maxims", "📝 Templates"])
    with tab1:
        for court in COURT_HIERARCHY:
            indent = "—" * (court["level"] - 1)
            st.markdown(f"<div class='custom-card'><strong>{court['icon']} {indent} {esc(court['name'])}</strong> (L{court['level']})<br>"
                        f"<span style='opacity:.75'>{esc(court['desc'])}</span></div>", unsafe_allow_html=True)
    with tab2:
        for lp in db_fetch_all("limitation_periods", order="cause ASC"):
            st.markdown(f"<div class='custom-card'><strong>{esc(lp['cause'])}</strong><br>"
                        f"Period: <strong>{esc(lp['period'])}</strong><br>Authority: {esc(lp.get('authority','—'))}</div>", unsafe_allow_html=True)
        with st.form("add_lim", clear_on_submit=True):
            lc = st.text_input("Cause of Action")
            lp2 = st.text_input("Period")
            la = st.text_input("Authority")
            if st.form_submit_button("Add"):
                if lc.strip():
                    db_insert("limitation_periods", {"cause": lc.strip(), "period": lp2.strip(), "authority": la.strip()})
                    st.rerun()
    with tab3:
        search = st.text_input("Search maxims")
        maxims = db_fetch_all("maxims", order="maxim ASC")
        filtered = [m for m in maxims if search.lower() in m["maxim"].lower() or search.lower() in m["meaning"].lower()] if search else maxims
        for m in filtered:
            st.markdown(f"<div class='custom-card'><strong><em>{esc(m['maxim'])}</em></strong><br>{esc(m['meaning'])}</div>", unsafe_allow_html=True)
        with st.form("add_maxim", clear_on_submit=True):
            mm = st.text_input("Maxim (Latin)")
            mn = st.text_input("Meaning")
            if st.form_submit_button("Add"):
                if mm.strip():
                    db_insert("maxims", {"maxim": mm.strip(), "meaning": mn.strip()})
                    st.rerun()
    with tab4:
        templates = db_fetch_all("templates", order="name ASC")
        for tmpl in templates:
            with st.expander(f"{tmpl['name']} · {tmpl.get('cat','')}"):
                st.code(tmpl.get("content", ""), language=None)
                if st.button("Load", key=f"lt_{tmpl['id']}"):
                    st.session_state["loaded_template"] = tmpl.get("content", "")
                    st.success("Loaded — go to Editor tab.")
                if not tmpl.get("builtin"):
                    if st.button("Delete", key=f"dt_{tmpl['id']}"):
                        db_delete("templates", tmpl["id"])
                        st.rerun()
        with st.form("add_tmpl", clear_on_submit=True):
            tn = st.text_input("Template Name")
            tc = st.text_input("Category", value="Custom")
            tt = st.text_area("Content", height=300)
            if st.form_submit_button("Save"):
                if tn.strip() and tt.strip():
                    db_insert("templates", {"name": tn.strip(), "cat": tc.strip(), "content": tt.strip(), "builtin": 0, "created_at": datetime.now().isoformat(timespec="seconds")})
                    st.rerun()


# ═══════════════════════════════════════════════════════
# TEMPLATE EDITOR
# ═══════════════════════════════════════════════════════
def render_template_editor():
    section_header("✍️ Template Editor", "Edit templates or draft documents with AI")
    loaded = st.session_state.get("loaded_template", "")
    content = st.text_area("Document Editor", value=loaded, height=450, key="tmpl_editor")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("💾 Download TXT", data=content or "", file_name="document.txt", mime="text/plain", use_container_width=True)
    with c2:
        if HAS_DOCX and content.strip():
            try:
                import io
                doc = export_docx(content, "Document")
                buf = io.BytesIO()
                doc.save(buf)
                st.download_button("💾 Download DOCX", data=buf.getvalue(), file_name="document.docx",
                                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            except Exception:
                pass
    instruction = st.text_input("AI editing instruction", placeholder="e.g. Make more formal, add penalty clauses")
    if st.button("Apply AI Edit", type="primary", use_container_width=True):
        if not content.strip() or not instruction.strip():
            st.error("Need content and instruction.")
        elif not _resolve_api_key():
            st.error("API key not configured.")
        else:
            try:
                with st.spinner("Editing..."):
                    result, tokens = call_gemini(
                        f"You are a Nigerian legal document editor. Apply this instruction to the document below.\n"
                        f"Return ONLY the revised document.\n\nInstruction: {instruction.strip()}\n\nDocument:\n{content.strip()}",
                        st.session_state.get("model"), "📝 Standard")
                st.session_state["loaded_template"] = result
                log_cost(st.session_state.get("model", ""), tokens, "Template edit")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


# ═══════════════════════════════════════════════════════
# COST TRACKER PAGE
# ═══════════════════════════════════════════════════════
def render_cost_tracker():
    section_header("📊 AI Cost Tracker", "Token usage and cost monitoring")
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("All Time", f"${summarize_costs('all')['cost']:.4f}")
    with c2:
        metric_card("7 Days", f"${summarize_costs('7d')['cost']:.4f}")
    with c3:
        metric_card("24h", f"${summarize_costs('24h')['cost']:.4f}")
    logs = db_fetch_all("cost_log", order="id DESC")
    for log in logs[:30]:
        st.markdown(f"<div class='custom-card'><strong>{esc(log.get('model',''))}</strong> · {esc(log.get('created_at',''))}<br>"
                    f"P:{log.get('prompt_tokens',0):,} R:{log.get('response_tokens',0):,} · ${log.get('total_cost',0):.6f}<br>"
                    f"<span style='opacity:.6'>{esc(log.get('query_preview','')[:120])}</span></div>", unsafe_allow_html=True)
    if logs and st.button("🗑️ Clear Cost Logs", use_container_width=True):
        db_execute("DELETE FROM cost_log")
        st.rerun()


# ═══════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════
def render_settings():
    section_header("⚙️ Settings & Profile", "Firm details, password, system info")
    profile = get_user_profile() or {}
    st.markdown("### 🏢 Firm Profile")
    with st.form("profile_form"):
        fn = st.text_input("Firm Name", value=profile.get("firm_name", ""))
        un = st.text_input("Your Name", value=profile.get("user_name", ""))
        em = st.text_input("Email", value=profile.get("email", ""))
        if st.form_submit_button("Save Profile", use_container_width=True):
            save_user_profile({"firm_name": fn.strip(), "user_name": un.strip(), "email": em.strip()})
            st.success("Saved.")
    st.markdown("### 🔐 Password")
    with st.form("pw_form"):
        np = st.text_input("New Password", type="password")
        cp = st.text_input("Confirm Password", type="password")
        if st.form_submit_button("Set Password", use_container_width=True):
            if not np:
                st.error("Empty.")
            elif np != cp:
                st.error("Mismatch.")
            else:
                save_user_profile({"password_hash": hash_password(np)})
                st.success("Password set.")
    st.markdown("### 🖥️ System")
    st.markdown(f"<div class='custom-card'><strong>Version:</strong> v8.0<br>"
                f"<strong>Model:</strong> {esc(st.session_state.get('model','Not set'))}<br>"
                f"<strong>API:</strong> {'Yes' if st.session_state.get('api_configured') else 'No'}<br>"
                f"<strong>PDF:</strong> {'Yes' if HAS_PDF else 'No'} · <strong>DOCX:</strong> {'Yes' if HAS_DOCX else 'No'} · "
                f"<strong>Charts:</strong> {'Yes' if HAS_PLOTLY else 'No'}</div>", unsafe_allow_html=True)
    st.markdown("### 🗄️ Database")
    dc1, dc2 = st.columns(2)
    with dc1:
        if st.button("Clear AI History", use_container_width=True):
            db_execute("DELETE FROM chat_history")
            st.rerun()
    with dc2:
        if st.button("Clear All Data", use_container_width=True):
            for t in ["cases", "case_notes", "clients", "time_entries", "invoices", "chat_history", "templates", "limitation_periods", "maxims", "cost_log"]:
                db_execute(f"DELETE FROM {t}")
            st.success("Cleared. Restart to re-seed.")
            st.rerun()


# ═══════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════
def main():
    ensure_db()
    ensure_profile_exists()
    ensure_api_configured()
    st.markdown(get_theme_css(st.session_state["theme"]), unsafe_allow_html=True)
    render_sidebar()
    if not st.session_state.get("authenticated"):
        st.warning("🔒 Please log in from the sidebar.")
        return
    tabs = st.tabs(["🏠 Dashboard", "🤖 AI Assistant", "📁 Cases", "👥 Clients",
                     "💰 Billing", "📚 Legal Tools", "✍️ Editor", "📊 Costs", "⚙️ Settings"])
    with tabs[0]:
        render_dashboard()
    with tabs[1]:
        render_ai_assistant()
    with tabs[2]:
        render_cases()
    with tabs[3]:
        render_clients()
    with tabs[4]:
        render_billing()
    with tabs[5]:
        render_legal_tools()
    with tabs[6]:
        render_template_editor()
    with tabs[7]:
        render_cost_tracker()
    with tabs[8]:
        render_settings()


if __name__ == "__main__":
    main()
