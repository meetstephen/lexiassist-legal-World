"""
LexiAssist v8.0 — Elite AI Legal Engine for Nigerian Lawyers
Single-file deployment. All logic self-contained.
"""
from __future__ import annotations

import html as html_mod
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, date
from io import BytesIO
from typing import Any

import google.generativeai as genai
import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import pdfplumber
    HAS_PDF_READ = True
except ImportError:
    HAS_PDF_READ = False

try:
    from docx import Document as DocxDocument
    from docx.shared import Pt
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

try:
    import openpyxl
    HAS_XLSX = True
except ImportError:
    HAS_XLSX = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LexiAssist")

# ═══════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════
st.set_page_config(
    page_title="LexiAssist v8.0 — Elite Legal AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════
SUPPORTED_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
DEFAULT_MODEL = "gemini-2.5-flash"

CASE_STATUSES = ["Active", "Pending", "Completed", "Archived"]
CLIENT_TYPES = ["Individual", "Corporate", "Government", "NGO"]

TASK_TYPES = {
    "general":   {"label": "💬 General Query",       "desc": "Any legal question"},
    "analysis":  {"label": "🔍 Legal Analysis",      "desc": "Issue spotting, CREAC reasoning"},
    "drafting":  {"label": "📄 Document Drafting",    "desc": "Contracts, pleadings, affidavits"},
    "research":  {"label": "📚 Legal Research",       "desc": "Case law, statutes, authorities"},
    "procedure": {"label": "📋 Procedural Guidance",  "desc": "Filing rules, court practice"},
    "advisory":  {"label": "🎯 Strategic Advisory",   "desc": "Risk mapping, options, strategy"},
    "interpret": {"label": "⚖️ Statutory Interpretation", "desc": "Legislation analysis"},
}

RESPONSE_MODES = {
    "brief":         {"label": "⚡ Brief",          "desc": "Direct answer, 3-5 sentences",       "tokens": 1200,  "temp": 0.1},
    "standard":      {"label": "📝 Standard",       "desc": "Structured analysis, 5-10 paragraphs","tokens": 6000,  "temp": 0.15},
    "comprehensive": {"label": "🔬 Comprehensive",  "desc": "Full CREAC + Strategy + Risk Ranking", "tokens": 16384, "temp": 0.2},
}

UPLOAD_TYPES = ["pdf", "docx", "doc", "txt", "xlsx", "xls", "csv", "json", "rtf"]

# ═══════════════════════════════════════════════════════
# ELITE SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════
IDENTITY_CORE = """You are LexiAssist v8.0 — an elite Senior Partner at a top-tier Nigerian law firm with
35+ years of practice across ALL areas of Nigerian law. You are known for:
- Taking FIRM, CLEAR POSITIONS (never hedging with "may" or "might" when facts permit a conclusion)
- Thinking like a LITIGATOR — always identifying best claim, best defence, weakest party
- Providing ACTIONABLE STRATEGY — not academic theory
- Being BRUTALLY HONEST about risks and exposure

JURISDICTION: Nigeria.
Primary: Constitution of the Federal Republic of Nigeria 1999 (as amended),
Federal Acts, State Laws, Subsidiary Legislation, Rules of Court,
binding case law from the Supreme Court of Nigeria and Court of Appeal.

CITATION INTEGRITY: NEVER fabricate case names or section numbers.
If uncertain, state the legal principle and mark as [CITATION TO BE VERIFIED].
If a case name is well-known and established, cite it confidently.

CRITICAL RULES:
1. TAKE POSITIONS — Say "X IS liable because…" not "X may be liable"
2. ALWAYS identify the WEAKEST PARTY and explain why
3. NEVER end abruptly — always complete your full analysis
4. If the query involves multiple parties, RANK their risk exposure
5. Write to COMPLETION — finish every section you start"""

STRATEGY_BLOCK = """
MANDATORY STRATEGY LAYER (for Standard & Comprehensive modes):
After your legal analysis, you MUST include:

═══ STRATEGIC POSITION ═══
▸ PRIMARY CONCLUSION: State WHO is most exposed and WHY (firm position, no hedging)
▸ RISK RANKING:
  🔴 HIGH RISK → [Party] — [Why]
  🟡 MEDIUM RISK → [Party] — [Why]
  🟢 LOW RISK → [Party] — [Why]

▸ STRATEGY PER PARTY:
  • [Party 1] → [Immediate action recommended]
  • [Party 2] → [Immediate action recommended]
  • [Party 3] → [Immediate action recommended]

▸ LITIGATION ASSESSMENT:
  • Best Claim: [What and by whom]
  • Best Defence: [What and by whom]
  • Weakest Party: [Who and why]
  • Critical Next Step: [Single most important action]
═══════════════════════════
"""

PROMPTS_BY_MODE = {
    "brief": IDENTITY_CORE + """
RESPONSE MODE: BRIEF
- Give the answer in 3-5 clear sentences maximum.
- State your position firmly. No headers, no bullet lists.
- If facts are missing, say: "The outcome turns on X."
- Be direct. Be definitive. No filler.""",

    "standard": IDENTITY_CORE + STRATEGY_BLOCK + """
RESPONSE MODE: STANDARD
- Structure: Issue Identification → Legal Position → Application → Strategy
- Write 5-10 substantial paragraphs of analysis
- Include the MANDATORY STRATEGY LAYER at the end
- COMPLETE your analysis fully — do NOT cut short
- You have ample token space — USE IT to give thorough coverage
- Every paragraph must add value — no repetition""",

    "comprehensive": IDENTITY_CORE + STRATEGY_BLOCK + """
RESPONSE MODE: COMPREHENSIVE (DEEP ANALYSIS)
- This is your MOST THOROUGH mode. Use ALL available space.
- Structure for EACH issue: CONCLUSION → RULE → EXPLANATION → APPLICATION → CONCLUSION (CREAC)
- Identify ALL issues: obvious, hidden, procedural, jurisdictional, limitation
- For EACH issue, cite the governing statute AND at least one leading case
- Include DEVIL'S ADVOCATE section: strongest counter-argument
- Include MANDATORY STRATEGY LAYER (detailed version)
- Include PRACTICAL CHECKLIST of immediate actions
- You have 16,000 tokens available — write a COMPLETE, exhaustive analysis
- NEVER stop mid-analysis — if you identify an issue, ANALYZE it fully
- End with a SUMMARY OF POSITIONS table""",
}

TASK_MODIFIERS = {
    "general": "\nApply the general legal framework. Take a clear position.",
    "analysis": "\nFocus on deep issue-spotting. Apply CREAC to each issue. Distinguish facts carefully.",
    "drafting": "\nDraft a professional Nigerian-standard document. Use [PLACEHOLDER] for missing data. Include all formality requirements (execution, stamping, filing). Do NOT add strategy/risk sections for drafting tasks.",
    "research": "\nWrite a formal Legal Research Memorandum. For each authority: state the principle, quote the ratio (if known), and explain relevance to the query.",
    "procedure": "\nProvide step-by-step procedural guidance. Include: which court, which form/process, filing fees (if known), timelines, and common pitfalls.",
    "advisory": "\nFocus on strategic advisory. Emphasize risk mitigation, commercial impact, and optimal paths. Include risk matrix.",
    "interpret": "\nApply the three rules of statutory interpretation (Literal, Golden, Mischief). State which rule yields the best result and WHY.",
}

ISSUE_SPOT_PROMPT = IDENTITY_CORE + """
TASK: Rapid Issue Decomposition (max 250 words)
- CORE ISSUES: List each with area of law and governing principle
- HIDDEN ISSUES: Procedural traps, limitation, standing, regulatory overlap
- MISSING FACTS: Top 3-5 facts that would change the analysis
- COMPLEXITY: Straightforward / Moderate / Complex / Highly Complex
Do NOT provide full analysis. Decomposition ONLY."""

CRITIQUE_PROMPT = IDENTITY_CORE + """
TASK: Quality Assessment of the analysis below (max 150 words).
Score 1-5: Completeness, Legal Accuracy, Strategic Value.
List 1-3 critical gaps. GRADE: A/B/C/D. One sentence overall."""

FOLLOWUP_PROMPT = IDENTITY_CORE + STRATEGY_BLOCK + """
You are continuing a legal conversation.
Context: Original query, previous analysis, and a follow-up question are provided.
- Address the follow-up directly with the same rigor
- Maintain the Litigator/Strategist tone
- Match the specified response mode"""

# ═══════════════════════════════════════════════════════
# REFERENCE DATA
# ═══════════════════════════════════════════════════════
LIMITATION_PERIODS = [
    {"cause": "Simple Contract", "period": "6 years", "authority": "Limitation Act, s. 8(1)(a)"},
    {"cause": "Tort / Negligence", "period": "6 years", "authority": "Limitation Act, s. 8(1)(a)"},
    {"cause": "Personal Injury", "period": "3 years", "authority": "Limitation Act, s. 8(1)(b)"},
    {"cause": "Defamation", "period": "3 years", "authority": "Limitation Act, s. 8(1)(b)"},
    {"cause": "Recovery of Land", "period": "12 years", "authority": "Limitation Act, s. 16"},
    {"cause": "Mortgage Foreclosure", "period": "12 years", "authority": "Limitation Act, s. 18"},
    {"cause": "Recovery of Rent", "period": "6 years", "authority": "Limitation Act, s. 19"},
    {"cause": "Judgment Enforcement", "period": "12 years", "authority": "Limitation Act, s. 8(1)(d)"},
    {"cause": "POPA (Public Officers)", "period": "3 months notice / 12 months suit", "authority": "POPA, s. 2"},
    {"cause": "Fundamental Rights", "period": "12 months", "authority": "FREP Rules, Order II r. 1"},
    {"cause": "Election Petition", "period": "21 days post-declaration", "authority": "Electoral Act 2022, s. 133(1)"},
]

COURT_HIERARCHY = [
    {"level": 1, "name": "Supreme Court of Nigeria", "desc": "Final appellate court", "icon": "🏛️"},
    {"level": 2, "name": "Court of Appeal", "desc": "Intermediate appellate", "icon": "⚖️"},
    {"level": 3, "name": "Federal High Court", "desc": "Federal causes, tax, admiralty", "icon": "🏢"},
    {"level": 3, "name": "State High Courts", "desc": "General civil & criminal", "icon": "🏢"},
    {"level": 3, "name": "National Industrial Court", "desc": "Labour & employment", "icon": "🏢"},
    {"level": 4, "name": "Magistrate / District Courts", "desc": "Summary jurisdiction", "icon": "📋"},
    {"level": 4, "name": "Customary / Sharia Courts", "desc": "Personal law matters", "icon": "📋"},
]

LEGAL_MAXIMS = [
    {"maxim": "Audi alteram partem", "meaning": "Hear the other side — natural justice"},
    {"maxim": "Nemo judex in causa sua", "meaning": "No one should judge their own cause"},
    {"maxim": "Stare decisis", "meaning": "Stand by decided cases — binding precedent"},
    {"maxim": "Ubi jus ibi remedium", "meaning": "Where there is a right, there is a remedy"},
    {"maxim": "Volenti non fit injuria", "meaning": "No injury to one who consents"},
    {"maxim": "Pacta sunt servanda", "meaning": "Agreements must be honoured"},
    {"maxim": "Nemo dat quod non habet", "meaning": "No one gives what they don't have"},
    {"maxim": "Res judicata", "meaning": "A decided matter cannot be re-litigated"},
    {"maxim": "Actus non facit reum nisi mens sit rea", "meaning": "No guilt without guilty mind"},
    {"maxim": "Ignorantia legis neminem excusat", "meaning": "Ignorance of law excuses no one"},
    {"maxim": "Qui facit per alium facit per se", "meaning": "He who acts through another acts himself"},
    {"maxim": "Generalia specialibus non derogant", "meaning": "General provisions don't override specific ones"},
]

TEMPLATES = [
    {"id": "1", "name": "Employment Contract", "cat": "Corporate",
     "content": "EMPLOYMENT CONTRACT\n\nMade on [DATE] between:\n\n1. [EMPLOYER NAME] (\"Employer\")\n   RC: [NUMBER]\n\n2. [EMPLOYEE NAME] (\"Employee\")\n\nTERMS:\n1. Position: [TITLE]\n2. Start: [DATE]\n3. Probation: [MONTHS]\n4. Salary: N[AMOUNT]/month\n5. Hours: [X] hrs/week\n6. Leave: [X] days/year\n7. Termination: [NOTICE] written notice\n8. Governing Law: Labour Act of Nigeria\n\nSigned:\n_______ (Employer)\n_______ (Employee)"},
    {"id": "2", "name": "Tenancy Agreement", "cat": "Property",
     "content": "TENANCY AGREEMENT\n\nMade on [DATE] BETWEEN:\n[LANDLORD] of [ADDRESS] (\"Landlord\")\nAND\n[TENANT] of [ADDRESS] (\"Tenant\")\n\n1. Premises: [ADDRESS]\n2. Term: [DURATION] from [START]\n3. Rent: N[AMOUNT] per [PERIOD]\n4. Deposit: N[AMOUNT]\n5. Use: [Residential/Commercial]\n6. Governing Law: Applicable State Tenancy Law\n\nSigned:\n_______ _______"},
    {"id": "3", "name": "Power of Attorney", "cat": "Litigation",
     "content": "GENERAL POWER OF ATTORNEY\n\nI, [GRANTOR], of [ADDRESS], appoint [ATTORNEY] of [ADDRESS] as my Attorney.\n\nPOWERS:\n1. Recover debts and execute settlements\n2. Manage real and personal property\n3. Appear before any court or tribunal\n\nIRREVOCABLE for [PERIOD].\n\nDated: [DATE]\nSigned: _______\nWitness: _______"},
    {"id": "4", "name": "Written Address (Skeleton)", "cat": "Litigation",
     "content": "IN THE [COURT NAME]\nSUIT NO: [NUMBER]\n\nBETWEEN:\n[CLAIMANT] ............ Claimant\nAND\n[DEFENDANT] ........... Defendant\n\nWRITTEN ADDRESS OF THE [PARTY]\n\n1.0 INTRODUCTION\n2.0 BRIEF FACTS\n3.0 ISSUES FOR DETERMINATION\n4.0 ARGUMENTS\n   4.1 Issue One\n   4.2 Issue Two\n5.0 CONCLUSION\n\nDated: [DATE]\nCounsel: _______"},
    {"id": "5", "name": "Demand Letter", "cat": "Commercial",
     "content": "OUR REF: [REF]\nDATE: [DATE]\n\n[RECIPIENT NAME]\n[ADDRESS]\n\nDear Sir/Madam,\n\nRE: DEMAND FOR PAYMENT OF N[AMOUNT]\n\nWe are Solicitors to [CLIENT NAME] on whose instructions we write.\n\nOur client instructs us that [FACTS].\n\nDEMAND: Pay N[AMOUNT] within [DAYS] days.\n\nFailing which, we have firm instructions to commence legal proceedings without further notice.\n\nYours faithfully,\n[FIRM NAME]"},
]

# ═══════════════════════════════════════════════════════
# THEMES (CSS)
# ═══════════════════════════════════════════════════════
THEMES = {
    "🌿 Emerald": {
        "primary": "#059669", "secondary": "#0d9488", "accent": "#10b981",
        "bg": "#f8faf9", "card_bg": "#ffffff", "text": "#1e293b",
        "header_gradient": "linear-gradient(135deg, #059669, #0d9488)",
        "sidebar_bg": "#f0fdf4",
    },
    "🌙 Midnight": {
        "primary": "#3b82f6", "secondary": "#6366f1", "accent": "#818cf8",
        "bg": "#0f172a", "card_bg": "#1e293b", "text": "#e2e8f0",
        "header_gradient": "linear-gradient(135deg, #1e3a5f, #3b82f6)",
        "sidebar_bg": "#1e293b",
    },
    "👔 Royal": {
        "primary": "#7c3aed", "secondary": "#6d28d9", "accent": "#a78bfa",
        "bg": "#faf5ff", "card_bg": "#ffffff", "text": "#1e1b4b",
        "header_gradient": "linear-gradient(135deg, #6d28d9, #7c3aed)",
        "sidebar_bg": "#f5f3ff",
    },
    "❤️ Crimson": {
        "primary": "#dc2626", "secondary": "#b91c1c", "accent": "#f87171",
        "bg": "#fef2f2", "card_bg": "#ffffff", "text": "#1f2937",
        "header_gradient": "linear-gradient(135deg, #b91c1c, #dc2626)",
        "sidebar_bg": "#fef2f2",
    },
    "🌅 Sunset": {
        "primary": "#ea580c", "secondary": "#d97706", "accent": "#fb923c",
        "bg": "#fffbeb", "card_bg": "#ffffff", "text": "#1c1917",
        "header_gradient": "linear-gradient(135deg, #d97706, #ea580c)",
        "sidebar_bg": "#fefce8",
    },
}

def get_theme_css(theme_name: str) -> str:
    t = THEMES.get(theme_name, THEMES["🌿 Emerald"])
    return f"""
<style>
    .stApp {{ background-color: {t['bg']}; color: {t['text']}; }}
    section[data-testid="stSidebar"] {{ background-color: {t['sidebar_bg']}; }}
    .hero {{
        background: {t['header_gradient']};
        color: white; padding: 2.5rem 2rem; border-radius: 1.2rem;
        margin-bottom: 1.5rem;
    }}
    .hero h1 {{ font-size: 2.4rem; font-weight: 800; margin: 0; }}
    .hero p {{ font-size: 1.1rem; opacity: 0.92; margin-top: 0.5rem; }}
    .page-header {{
        background: {t['header_gradient']};
        color: white; padding: 1.5rem 1.8rem; border-radius: 1rem;
        margin-bottom: 1.5rem;
    }}
    .page-header h2 {{ margin: 0; font-size: 1.6rem; font-weight: 700; }}
    .page-header p {{ margin: 0.3rem 0 0 0; opacity: 0.9; }}
    .stat-card {{
        background: {t['card_bg']}; border: 1px solid {t['primary']}22;
        border-radius: 0.9rem; padding: 1.2rem; text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}
    .stat-card .stat-value {{ font-size: 2rem; font-weight: 800; color: {t['primary']}; }}
    .stat-card .stat-label {{ font-size: 0.85rem; color: {t['text']}99; margin-top: 0.2rem; }}
    .custom-card {{
        background: {t['card_bg']}; border: 1px solid {t['primary']}15;
        border-radius: 0.85rem; padding: 1.2rem 1.4rem;
        margin-bottom: 0.9rem; box-shadow: 0 1px 6px rgba(0,0,0,0.03);
    }}
    .custom-card h4 {{ margin: 0 0 0.4rem 0; color: {t['primary']}; }}
    .response-box {{
        background: {t['card_bg']}; border: 1px solid {t['primary']}20;
        border-left: 4px solid {t['primary']};
        border-radius: 0.75rem; padding: 1.8rem;
        white-space: pre-wrap; line-height: 1.7; font-size: 0.95rem;
    }}
    .disclaimer {{
        background: #fef3c7; border-left: 4px solid #f59e0b;
        padding: 1rem 1.2rem; border-radius: 0.3rem; margin-top: 1rem;
        font-size: 0.88rem;
    }}
    .badge {{
        display: inline-block; padding: 0.2rem 0.7rem; border-radius: 1rem;
        font-size: 0.75rem; font-weight: 600;
    }}
    .badge-ok {{ background: #d1fae5; color: #065f46; }}
    .badge-warn {{ background: #fef3c7; color: #92400e; }}
    .badge-err {{ background: #fee2e2; color: #991b1b; }}
    .badge-info {{ background: {t['primary']}18; color: {t['primary']}; }}
    .history-item {{
        background: {t['card_bg']}; border: 1px solid {t['primary']}12;
        border-radius: 0.6rem; padding: 0.8rem 1rem;
        margin-bottom: 0.5rem; cursor: pointer;
    }}
    .history-item:hover {{ border-color: {t['primary']}; }}
    .tool-card {{
        background: {t['card_bg']}; border: 1px solid {t['primary']}10;
        border-radius: 0.6rem; padding: 1rem; margin-bottom: 0.6rem;
    }}
    div[data-testid="stTabs"] button {{
        font-weight: 600 !important; font-size: 0.92rem !important;
    }}
    div[data-testid="stTabs"] button[aria-selected="true"] {{
        color: {t['primary']} !important;
        border-bottom-color: {t['primary']} !important;
    }}
</style>"""

# ═══════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════
_DEFAULTS = {
    "api_key": "",
    "api_configured": False,
    "gemini_model": DEFAULT_MODEL,
    "theme": "🌿 Emerald",
    "response_mode": "standard",
    "cases": [],
    "clients": [],
    "time_entries": [],
    "invoices": [],
    "chat_history": [],
    "last_response": "",
    "original_query": "",
    "research_results": "",
    "loaded_template": "",
    "imported_doc": None,
    "selected_history_idx": None,
}

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ═══════════════════════════════════════════════════════
# HELPER UTILITIES
# ═══════════════════════════════════════════════════════
def esc(text: str) -> str:
    """HTML-escape text for safe rendering."""
    if not text:
        return ""
    return html_mod.escape(str(text))

def new_id() -> str:
    return uuid.uuid4().hex[:8]

def fmt_date(d) -> str:
    if not d:
        return "—"
    try:
        if isinstance(d, str):
            d = datetime.fromisoformat(d)
        return d.strftime("%d %b %Y")
    except Exception:
        return str(d)

def fmt_currency(amount) -> str:
    try:
        return f"₦{float(amount):,.2f}"
    except Exception:
        return "₦0.00"

def days_until(d) -> int:
    if not d:
        return 9999
    try:
        if isinstance(d, str):
            d = datetime.fromisoformat(d).date()
        if isinstance(d, datetime):
            d = d.date()
        return (d - date.today()).days
    except Exception:
        return 9999

def relative_date(d) -> str:
    n = days_until(d)
    if n == 9999:
        return "—"
    if n < 0:
        return f"{abs(n)}d overdue"
    if n == 0:
        return "TODAY"
    if n == 1:
        return "Tomorrow"
    if n <= 7:
        return f"{n} days"
    return f"{n} days away"

def safe_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return default

# ═══════════════════════════════════════════════════════
# SECURE API LAYER (NO KEY EXPOSED IN SIDEBAR)
# ═══════════════════════════════════════════════════════
def _resolve_api_key() -> str:
    """Get API key from secrets or env — NEVER from user input in sidebar."""
    for src in [
        lambda: safe_secret("GEMINI_API_KEY"),
        lambda: os.getenv("GEMINI_API_KEY", ""),
        lambda: st.session_state.get("api_key", ""),
    ]:
        k = src()
        if k and k.strip() and len(k.strip()) >= 10:
            return k.strip()
    return ""

def _configure_genai(key: str):
    genai.configure(api_key=key, transport="rest")

def auto_connect():
    """Auto-connect on app load using secrets/env only."""
    if st.session_state.api_configured:
        return
    k = _resolve_api_key()
    if k:
        try:
            _configure_genai(k)
            st.session_state.api_key = k
            st.session_state.api_configured = True
            m = safe_secret("GEMINI_MODEL") or os.getenv("GEMINI_MODEL", "")
            if m and m in SUPPORTED_MODELS:
                st.session_state.gemini_model = m
        except Exception as e:
            logger.warning(f"Auto-connect failed: {e}")

def manual_connect(key: str) -> bool:
    """One-time manual connection from secure setup screen."""
    try:
        _configure_genai(key)
        model = genai.GenerativeModel(st.session_state.gemini_model)
        model.generate_content("Test", generation_config={"max_output_tokens": 10})
        st.session_state.api_key = key
        st.session_state.api_configured = True
        return True
    except Exception as e:
        err = str(e)
        if "403" in err:
            st.error("❌ Invalid API key.")
        elif "429" in err:
            st.error("⚠️ Rate limit — try again shortly.")
        else:
            st.error(f"❌ Connection failed: {err[:120]}")
        return False

def generate(prompt: str, system: str, mode: str) -> str:
    """Core generation with retry and proper token limits."""
    k = _resolve_api_key()
    if not k:
        return "⚠️ No API key configured. Please set up your key."
    _configure_genai(k)

    mode_cfg = RESPONSE_MODES.get(mode, RESPONSE_MODES["standard"])
    gen_config = {
        "temperature": mode_cfg["temp"],
        "top_p": 0.92,
        "top_k": 40,
        "max_output_tokens": mode_cfg["tokens"],
    }

    model = genai.GenerativeModel(
        st.session_state.gemini_model,
        system_instruction=system,
    )

    for attempt in range(3):
        try:
            resp = model.generate_content(prompt, generation_config=gen_config)
            if resp and resp.text:
                return resp.text
            return "⚠️ Empty response from AI. Try rephrasing your query."
        except Exception as e:
            if attempt == 2:
                return f"⚠️ Generation error after 3 attempts: {str(e)[:200]}"
            time.sleep(2 * (attempt + 1))

    return "⚠️ Generation failed. Please try again."

def build_system_prompt(task: str, mode: str) -> str:
    """Combine mode prompt + task modifier."""
    base = PROMPTS_BY_MODE.get(mode, PROMPTS_BY_MODE["standard"])
    modifier = TASK_MODIFIERS.get(task, TASK_MODIFIERS["general"])
    return base + modifier

# ═══════════════════════════════════════════════════════
# FILE EXTRACTION (ALL TYPES)
# ═══════════════════════════════════════════════════════
def extract_file_text(uploaded_file) -> str:
    """Extract text from uploaded file — supports PDF, DOCX, TXT, XLSX, CSV, JSON."""
    name = uploaded_file.name.lower()
    data = uploaded_file.getvalue()

    if name.endswith(".pdf"):
        if not HAS_PDF_READ:
            raise ValueError("PDF support not available (install pdfplumber)")
        with pdfplumber.open(BytesIO(data)) as pdf:
            pages = []
            for p in pdf.pages:
                txt = p.extract_text()
                if txt:
                    pages.append(txt)
            return "\n\n".join(pages)

    elif name.endswith((".docx", ".doc")):
        if not HAS_DOCX:
            raise ValueError("DOCX support not available (install python-docx)")
        doc = DocxDocument(BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    elif name.endswith(".txt") or name.endswith(".rtf"):
        return data.decode("utf-8", errors="ignore")

    elif name.endswith((".xlsx", ".xls")):
        if not HAS_XLSX:
            raise ValueError("Excel support not available (install openpyxl)")
        df = pd.read_excel(BytesIO(data))
        return df.to_string(index=False)

    elif name.endswith(".csv"):
        df = pd.read_csv(BytesIO(data))
        return df.to_string(index=False)

    elif name.endswith(".json"):
        obj = json.loads(data.decode("utf-8", errors="ignore"))
        return json.dumps(obj, indent=2)

    else:
        # Try as plain text
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            raise ValueError(f"Unsupported file type: {name}")

# ═══════════════════════════════════════════════════════
# EXPORT FUNCTIONS (PDF FIX APPLIED)
# ═══════════════════════════════════════════════════════
def export_pdf(text: str, title: str = "LexiAssist Analysis") -> bytes:
    """Generate PDF bytes — ALWAYS returns bytes, never str."""
    if not HAS_FPDF:
        return b"%PDF-1.0\nPDF generation unavailable. Install fpdf2."

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, txt=title, ln=True, align="C")
    pdf.ln(4)

    # Date
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, txt=f"Generated: {datetime.now():%d %B %Y at %H:%M}", ln=True, align="C")
    pdf.ln(6)

    # Divider
    pdf.set_draw_color(100, 100, 100)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    # Body — handle encoding safely
    pdf.set_font("Helvetica", size=10)
    clean = text.encode("latin-1", errors="replace").decode("latin-1")
    for line in clean.split("\n"):
        pdf.multi_cell(0, 6, txt=line)
        pdf.ln(1)

    # Footer
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, txt="Generated by LexiAssist v8.0 — Verify all citations independently", ln=True, align="C")

    # OUTPUT — ensure bytes
    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1", errors="replace")
    if isinstance(raw, bytearray):
        return bytes(raw)
    return raw

def export_docx(text: str, title: str = "LexiAssist Analysis") -> bytes:
    """Generate DOCX bytes."""
    if not HAS_DOCX:
        return b"DOCX generation unavailable."
    bio = BytesIO()
    doc = DocxDocument()
    doc.add_heading(title, level=0)
    doc.add_paragraph(f"Generated: {datetime.now():%d %B %Y at %H:%M}")
    doc.add_paragraph("")
    for para in text.split("\n\n"):
        if para.strip():
            doc.add_paragraph(para.strip())
    doc.add_paragraph("")
    footer = doc.add_paragraph("Generated by LexiAssist v8.0 — Verify all citations independently")
    footer.runs[0].font.size = Pt(8)
    doc.save(bio)
    return bio.getvalue()

def export_txt(text: str, title: str = "LexiAssist Analysis") -> str:
    """Plain text export."""
    header = f"{'=' * 60}\n{title}\nGenerated: {datetime.now():%d %B %Y at %H:%M}\n{'=' * 60}\n\n"
    footer = f"\n\n{'=' * 60}\nGenerated by LexiAssist v8.0\n{'=' * 60}"
    return header + text + footer

def export_html(text: str, title: str = "LexiAssist Analysis") -> str:
    """HTML export."""
    body = esc(text).replace("\n", "<br>")
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>{esc(title)}</title>
<style>body{{font-family:Georgia,serif;max-width:800px;margin:2rem auto;padding:1rem;line-height:1.7;color:#1e293b}}
h1{{color:#059669;border-bottom:2px solid #059669;padding-bottom:0.5rem}}
.meta{{color:#64748b;font-size:0.9rem;margin-bottom:1.5rem}}
.disclaimer{{background:#fef3c7;border-left:4px solid #f59e0b;padding:1rem;margin-top:2rem;font-size:0.85rem}}</style>
</head><body>
<h1>{esc(title)}</h1>
<div class="meta">Generated: {datetime.now():%d %B %Y at %H:%M}</div>
<div>{body}</div>
<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated. Verify all citations independently.</div>
</body></html>"""

def safe_pdf_download(text: str, title: str, fname: str, key: str):
    """Wrapper that handles PDF download safely."""
    try:
        pdf_data = export_pdf(text, title)
        if not isinstance(pdf_data, bytes):
            pdf_data = bytes(pdf_data)
        st.download_button(
            "📥 PDF", data=pdf_data, file_name=f"{fname}.pdf",
            mime="application/pdf", key=key, use_container_width=True,
        )
    except Exception as e:
        st.button(f"📥 PDF (unavailable)", disabled=True, key=key, use_container_width=True)
        logger.warning(f"PDF export failed: {e}")

def safe_docx_download(text: str, title: str, fname: str, key: str):
    """Wrapper that handles DOCX download safely."""
    try:
        docx_data = export_docx(text, title)
        st.download_button(
            "📥 DOCX", data=docx_data, file_name=f"{fname}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key=key, use_container_width=True,
        )
    except Exception as e:
        st.button(f"📥 DOCX (unavailable)", disabled=True, key=key, use_container_width=True)
        logger.warning(f"DOCX export failed: {e}")

# ═══════════════════════════════════════════════════════
# DATA CRUD
# ═══════════════════════════════════════════════════════
def add_case(data: dict):
    data["id"] = new_id()
    data["created_at"] = datetime.now().isoformat()
    st.session_state.cases.append(data)

def update_case(cid: str, updates: dict):
    for c in st.session_state.cases:
        if c["id"] == cid:
            c.update(updates)
            c["updated_at"] = datetime.now().isoformat()
            return

def delete_case(cid: str):
    st.session_state.cases = [c for c in st.session_state.cases if c["id"] != cid]

def add_client(data: dict):
    data["id"] = new_id()
    data["created_at"] = datetime.now().isoformat()
    st.session_state.clients.append(data)

def delete_client(cid: str):
    st.session_state.clients = [c for c in st.session_state.clients if c["id"] != cid]

def get_client_name(cid: str) -> str:
    for c in st.session_state.clients:
        if c["id"] == cid:
            return c.get("name", "—")
    return "—"

def add_time_entry(data: dict):
    data["id"] = new_id()
    data["created_at"] = datetime.now().isoformat()
    data["amount"] = data.get("hours", 0) * data.get("rate", 0)
    st.session_state.time_entries.append(data)

def delete_time_entry(eid: str):
    st.session_state.time_entries = [e for e in st.session_state.time_entries if e["id"] != eid]

def make_invoice(client_id: str):
    entries = [e for e in st.session_state.time_entries if e.get("client_id") == client_id]
    if not entries:
        return None
    inv = {
        "id": new_id(),
        "invoice_no": f"INV-{datetime.now():%Y%m%d}-{new_id()[:4].upper()}",
        "client_id": client_id,
        "client_name": get_client_name(client_id),
        "entries": entries,
        "total": sum(e.get("amount", 0) for e in entries),
        "date": datetime.now().isoformat(),
        "status": "Draft",
    }
    st.session_state.invoices.append(inv)
    return inv

def total_hours() -> float:
    return sum(e.get("hours", 0) for e in st.session_state.time_entries)

def total_billable() -> float:
    return sum(e.get("amount", 0) for e in st.session_state.time_entries)

def client_case_count(cid: str) -> int:
    return sum(1 for c in st.session_state.cases if c.get("client_id") == cid)

def client_billable(cid: str) -> float:
    return sum(e.get("amount", 0) for e in st.session_state.time_entries if e.get("client_id") == cid)

def get_active_cases() -> list:
    return [c for c in st.session_state.cases if c.get("status") == "Active"]

def get_hearings() -> list:
    h = []
    for c in st.session_state.cases:
        if c.get("next_hearing") and c.get("status") in ("Active", "Pending"):
            h.append({
                "id": c["id"], "title": c.get("title", ""),
                "date": c["next_hearing"], "court": c.get("court", ""),
                "suit": c.get("suit_no", ""), "status": c.get("status", ""),
            })
    h.sort(key=lambda x: x.get("date", "z"))
    return h

# ═══════════════════════════════════════════════════════
# AI HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════
def run_ai_query(query: str, task: str, mode: str, context: str = "") -> str:
    """Run main AI query with proper system prompt."""
    system = build_system_prompt(task, mode)
    full_prompt = query
    if context:
        full_prompt = f"DOCUMENT CONTEXT:\n{context[:8000]}\n\nQUERY:\n{query}"
    return generate(full_prompt, system, mode)

def run_issue_spot(query: str) -> str:
    return generate(query, ISSUE_SPOT_PROMPT, "brief")

def run_critique(query: str, analysis: str) -> str:
    prompt = f"ORIGINAL QUERY:\n{query}\n\nANALYSIS TO REVIEW:\n{analysis}"
    return generate(prompt, CRITIQUE_PROMPT, "brief")

def run_followup(original: str, previous: str, followup: str, mode: str) -> str:
    prompt = f"ORIGINAL QUERY:\n{original}\n\nPREVIOUS ANALYSIS:\n{previous}\n\nFOLLOW-UP QUESTION:\n{followup}"
    return generate(prompt, FOLLOWUP_PROMPT, mode)

def run_research(query: str, mode: str) -> str:
    system = build_system_prompt("research", mode)
    return generate(query, system, mode)

def add_to_history(query: str, response: str, task: str, mode: str):
    """Save to chat history with metadata."""
    entry = {
        "id": new_id(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "query": query,
        "response": response,
        "task": task,
        "mode": mode,
        "word_count": len(response.split()),
    }
    st.session_state.chat_history.append(entry)
    return entry

# ═══════════════════════════════════════════════════════
# SECURE API SETUP SCREEN (REPLACES SIDEBAR KEY INPUT)
# ═══════════════════════════════════════════════════════
def render_setup_screen():
    """Show ONE-TIME secure setup if API key is missing. Never in sidebar."""
    st.markdown("""
    <div class="hero">
        <h1>⚖️ LexiAssist v8.0</h1>
        <p>Elite AI Legal Engine for Nigerian Lawyers</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔐 Secure API Configuration")
    st.markdown("""
    Your API key is required to power the AI engine. It is **never displayed**
    in the sidebar or stored outside this session.

    **Recommended:** Add your key to Streamlit Secrets (`.streamlit/secrets.toml`)
    or set the `GEMINI_API_KEY` environment variable so this screen never appears.
    """)

    with st.form("api_setup_form"):
        key_input = st.text_input(
            "Google Gemini API Key",
            type="password",
            placeholder="Paste your API key here…",
            help="Get a key at https://aistudio.google.com/app/apikey",
        )
        model_sel = st.selectbox("AI Model", SUPPORTED_MODELS, index=0)
        submitted = st.form_submit_button("🔗 Connect", type="primary", use_container_width=True)

        if submitted:
            if key_input and len(key_input.strip()) >= 10:
                st.session_state.gemini_model = model_sel
                with st.spinner("🔗 Connecting to Gemini…"):
                    if manual_connect(key_input.strip()):
                        st.success("✅ Connected! Redirecting…")
                        time.sleep(1)
                        st.rerun()
            else:
                st.error("❌ Please enter a valid API key.")

    st.divider()
    st.caption("💡 **Tip:** To skip this screen permanently, add to `.streamlit/secrets.toml`:")
    st.code('GEMINI_API_KEY = "your-key-here"', language="toml")

# ═══════════════════════════════════════════════════════
# SIDEBAR (NO API KEY — CLEAN & PROFESSIONAL)
# ═══════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚖️ LexiAssist v8.0")
        st.caption("Elite AI Legal Engine")
        st.divider()

        # ── Status Metrics ──
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Cases", len(get_active_cases()))
        with c2:
            st.metric("Sessions", len(st.session_state.chat_history))

        st.divider()

        # ── Response Mode ──
        st.markdown("### 🧠 Response Mode")
        modes = list(RESPONSE_MODES.keys())
        current_idx = modes.index(st.session_state.response_mode) if st.session_state.response_mode in modes else 1
        mode = st.radio(
            "Depth",
            modes,
            index=current_idx,
            format_func=lambda x: RESPONSE_MODES[x]["label"],
            key="sidebar_mode_radio",
            label_visibility="collapsed",
        )
        if mode != st.session_state.response_mode:
            st.session_state.response_mode = mode
            st.rerun()

        sel_mode = RESPONSE_MODES[st.session_state.response_mode]
        st.caption(f"{sel_mode['desc']}")
        st.caption(f"Token limit: {sel_mode['tokens']:,}")

        st.divider()

        # ── Theme ──
        st.markdown("### 🎨 Theme")
        theme_names = list(THEMES.keys())
        current_theme_idx = theme_names.index(st.session_state.theme) if st.session_state.theme in theme_names else 0
        theme = st.selectbox(
            "Select Theme",
            theme_names,
            index=current_theme_idx,
            key="sidebar_theme_sel",
            label_visibility="collapsed",
        )
        if theme != st.session_state.theme:
            st.session_state.theme = theme
            st.rerun()

        st.divider()

        # ── AI Engine Status ──
        st.markdown("### 🤖 AI Engine")
        if st.session_state.api_configured:
            st.success(f"✅ Connected · `{st.session_state.gemini_model}`")
            model_sel = st.selectbox(
                "Switch Model",
                SUPPORTED_MODELS,
                index=SUPPORTED_MODELS.index(st.session_state.gemini_model) if st.session_state.gemini_model in SUPPORTED_MODELS else 0,
                key="sidebar_model_sel",
                label_visibility="collapsed",
            )
            if model_sel != st.session_state.gemini_model:
                st.session_state.gemini_model = model_sel
                st.rerun()
        else:
            st.error("🔴 Not connected")

        st.divider()

        # ── Data Import / Export ──
        st.markdown("### 💾 Data Management")

        # Export
        if st.button("📥 Export All Data (JSON)", use_container_width=True, key="sidebar_export_btn"):
            export_data = {
                "export_date": datetime.now().isoformat(),
                "version": "8.0",
                "cases": st.session_state.cases,
                "clients": st.session_state.clients,
                "time_entries": st.session_state.time_entries,
                "invoices": st.session_state.invoices,
                "chat_history": st.session_state.chat_history,
            }
            st.download_button(
                "⬇️ Download JSON",
                json.dumps(export_data, indent=2, default=str),
                f"lexiassist_backup_{datetime.now():%Y%m%d_%H%M}.json",
                "application/json",
                key="sidebar_dl_json",
                use_container_width=True,
            )

        # Import — accepts ALL file types
        st.markdown("##### 📤 Import Files")
        uploaded = st.file_uploader(
            "Upload",
            type=UPLOAD_TYPES,
            accept_multiple_files=False,
            key="sidebar_file_upload",
            label_visibility="collapsed",
            help="Supports: PDF, DOCX, TXT, XLSX, CSV, JSON, RTF",
        )
        if uploaded:
            try:
                ext = uploaded.name.split(".")[-1].lower()
                if ext == "json":
                    raw = json.loads(uploaded.getvalue().decode("utf-8", errors="ignore"))
                    # Check if it's a LexiAssist backup
                    if isinstance(raw, dict) and any(k in raw for k in ["cases", "clients"]):
                        for k in ["cases", "clients", "time_entries", "invoices", "chat_history"]:
                            if k in raw:
                                st.session_state[k] = raw[k]
                        st.success("✅ LexiAssist data imported!")
                        st.rerun()
                    else:
                        # Treat as document
                        text = json.dumps(raw, indent=2)
                        st.session_state.imported_doc = {
                            "name": uploaded.name, "type": ext,
                            "size": len(uploaded.getvalue()),
                            "full_text": text,
                            "preview": text[:600],
                        }
                        st.success(f"✅ {uploaded.name} loaded → AI Assistant")
                        st.rerun()
                else:
                    text = extract_file_text(uploaded)
                    st.session_state.imported_doc = {
                        "name": uploaded.name, "type": ext,
                        "size": len(uploaded.getvalue()),
                        "full_text": text,
                        "preview": text[:600] + ("…" if len(text) > 600 else ""),
                    }
                    st.success(f"✅ {uploaded.name} loaded → AI Assistant")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Import error: {e}")

        st.divider()
        st.caption("⚖️ LexiAssist v8.0 © 2026")
        st.caption("🧠 Elite AI · 🇳🇬 Nigerian Law")

# ═══════════════════════════════════════════════════════
# PAGE: HOME / DASHBOARD
# ═══════════════════════════════════════════════════════
def render_home():
    st.markdown(f"""
    <div class="hero">
        <h1>⚖️ LexiAssist v8.0</h1>
        <p>Elite AI Legal Engine for Nigerian Lawyers<br>
        Position-taking · Strategy-driven · Risk-ranked · Litigator-minded</p>
    </div>
    """, unsafe_allow_html=True)

    # Stats row
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{len(st.session_state.cases)}</div><div class="stat-label">Total Cases</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{len(get_active_cases())}</div><div class="stat-label">Active Cases</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{len(st.session_state.clients)}</div><div class="stat-label">Clients</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{total_hours():.1f}h</div><div class="stat-label">Billable Hours</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{len(st.session_state.chat_history)}</div><div class="stat-label">AI Sessions</div></div>', unsafe_allow_html=True)

    st.markdown("")

    # Upcoming hearings
    col_left, col_right = st.columns([3, 2])
    with col_left:
        st.markdown("### 📅 Upcoming Hearings")
        hearings = get_hearings()
        if hearings:
            for h in hearings[:8]:
                d = days_until(h["date"])
                badge = "badge-err" if d <= 3 else ("badge-warn" if d <= 7 else "badge-ok")
                st.markdown(f"""<div class="custom-card">
                    <h4>{esc(h['title'])}</h4>
                    Suit: {esc(h['suit'])} · Court: {esc(h['court'])}<br>
                    📅 {esc(fmt_date(h['date']))}
                    <span class="badge {badge}">{esc(relative_date(h['date']))}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No upcoming hearings. Add cases with hearing dates.")

    with col_right:
        st.markdown("### 🧠 Recent AI Sessions")
        history = st.session_state.chat_history
        if history:
            for entry in reversed(history[-6:]):
                mode_lbl = RESPONSE_MODES.get(entry.get("mode", ""), {}).get("label", "")
                st.markdown(f"""<div class="history-item">
                    <strong>{esc(entry.get('query', '')[:80])}{'…' if len(entry.get('query', '')) > 80 else ''}</strong><br>
                    <small>{esc(entry.get('timestamp', ''))} · {esc(mode_lbl)} · {entry.get('word_count', 0)} words</small>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No AI sessions yet. Go to AI Assistant to start.")

    # Features showcase
    st.markdown("---")
    st.markdown("### 🏆 Elite Features")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        st.markdown("""<div class="custom-card">
            <h4>🎯 Position-Taking</h4>
            <p>No more "may be liable" — firm conclusions backed by authority</p>
        </div>""", unsafe_allow_html=True)
    with f2:
        st.markdown("""<div class="custom-card">
            <h4>📊 Risk Ranking</h4>
            <p>Parties ranked by exposure: High / Medium / Low</p>
        </div>""", unsafe_allow_html=True)
    with f3:
        st.markdown("""<div class="custom-card">
            <h4>⚔️ Strategy Layer</h4>
            <p>Actionable next steps per party — litigator-grade advice</p>
        </div>""", unsafe_allow_html=True)
    with f4:
        st.markdown("""<div class="custom-card">
            <h4>🔬 Comprehensive</h4>
            <p>Full CREAC + Devil's Advocate + 16K token depth</p>
        </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# PAGE: AI ASSISTANT (FULL-FEATURED)
# ═══════════════════════════════════════════════════════
def render_ai():
    st.markdown("""<div class="page-header">
        <h2>🧠 AI Legal Assistant</h2>
        <p>Position-taking · Strategy-driven · Risk-ranked</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.api_configured:
        st.warning("⚠️ AI not connected. Configure your API key on the setup screen.")
        return

    mode = st.session_state.response_mode
    mode_info = RESPONSE_MODES[mode]
    st.info(f"**Mode: {mode_info['label']}** — {mode_info['desc']} (up to {mode_info['tokens']:,} tokens)")

    # ── Imported Document Context ──
    doc_context = ""
    if st.session_state.imported_doc:
        with st.expander(f"📎 Imported: {st.session_state.imported_doc['name']}", expanded=False):
            doc = st.session_state.imported_doc
            st.caption(f"Type: {doc['type'].upper()} · Size: {doc['size']:,} bytes")
            st.text_area("Preview", doc["preview"], height=120, disabled=True, key="doc_preview_ta")
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("📋 Use as Context", key="use_doc_ctx_btn", use_container_width=True):
                    doc_context = doc["full_text"]
                    st.success("✅ Document loaded as context for your query.")
            with dc2:
                if st.button("🗑️ Clear Document", key="clear_doc_btn", use_container_width=True):
                    st.session_state.imported_doc = None
                    st.rerun()
        if not doc_context and st.session_state.imported_doc:
            doc_context = st.session_state.imported_doc.get("full_text", "")

    # ── Clickable History ──
    if st.session_state.chat_history:
        with st.expander(f"📚 Session History ({len(st.session_state.chat_history)} entries)", expanded=False):
            for i, entry in enumerate(reversed(st.session_state.chat_history[-15:])):
                real_idx = len(st.session_state.chat_history) - 1 - i
                mode_lbl = RESPONSE_MODES.get(entry.get("mode", ""), {}).get("label", "")
                hc1, hc2 = st.columns([5, 1])
                with hc1:
                    st.markdown(f"""<div class="history-item">
                        <strong>{esc(entry.get('query', '')[:100])}</strong><br>
                        <small>{esc(entry.get('timestamp', ''))} · {esc(mode_lbl)} · {entry.get('word_count', 0)} words</small>
                    </div>""", unsafe_allow_html=True)
                with hc2:
                    if st.button("📖 Load", key=f"load_hist_{real_idx}", use_container_width=True):
                        st.session_state.selected_history_idx = real_idx
                        st.session_state.last_response = entry["response"]
                        st.session_state.original_query = entry["query"]
                        st.rerun()

    # ── Show selected history entry ──
    if st.session_state.selected_history_idx is not None:
        idx = st.session_state.selected_history_idx
        if 0 <= idx < len(st.session_state.chat_history):
            entry = st.session_state.chat_history[idx]
            st.markdown("---")
            st.markdown(f"### 📖 Viewing: Session from {entry.get('timestamp', '')}")
            st.markdown(f"**Query:** {esc(entry['query'])}")
            st.markdown(f'<div class="response-box">{esc(entry["response"])}</div>', unsafe_allow_html=True)

            # Export buttons for loaded history
            fname = f"LexiAssist_{entry.get('timestamp', '').replace(' ', '_').replace(':', '')}"
            hx1, hx2, hx3, hx4 = st.columns(4)
            with hx1:
                st.download_button("📥 TXT", export_txt(entry["response"]), f"{fname}.txt", "text/plain", key=f"hist_dl_txt_{idx}", use_container_width=True)
            with hx2:
                st.download_button("📥 HTML", export_html(entry["response"]), f"{fname}.html", "text/html", key=f"hist_dl_html_{idx}", use_container_width=True)
            with hx3:
                safe_pdf_download(entry["response"], "Legal Analysis", fname, f"hist_dl_pdf_{idx}")
            with hx4:
                safe_docx_download(entry["response"], "Legal Analysis", fname, f"hist_dl_docx_{idx}")

            if st.button("✖️ Close", key="close_hist_view"):
                st.session_state.selected_history_idx = None
                st.rerun()
            st.markdown("---")

    # ── Main Query Input ──
    st.markdown("### 💬 New Query")
    tc1, tc2 = st.columns([2, 1])
    with tc1:
        task_keys = list(TASK_TYPES.keys())
        task = st.selectbox(
            "Task Type",
            task_keys,
            format_func=lambda x: f"{TASK_TYPES[x]['label']} — {TASK_TYPES[x]['desc']}",
            key="ai_task_sel",
        )
    with tc2:
        st.markdown("")
        st.markdown(f"**Mode:** {mode_info['label']}")
        st.caption(f"Max output: {mode_info['tokens']:,} tokens")

    prefill = st.session_state.pop("loaded_template", "")
    query = st.text_area(
        "Your Legal Query",
        value=prefill,
        height=200,
        placeholder="Describe your legal question in detail…\n\nE.g.: 'A contractor failed to complete a building project. The employer has paid 70% of the contract sum. The contractor claims variation orders. Advise the employer on their legal options.'",
        key="ai_query_ta",
    )

    # ── Action Buttons ──
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        generate_btn = st.button(
            f"🧠 Generate ({mode_info['label']})",
            type="primary",
            use_container_width=True,
            disabled=not query.strip(),
            key="ai_generate_btn",
        )
    with bc2:
        issue_btn = st.button(
            "🔍 Issue Spot",
            use_container_width=True,
            disabled=not query.strip(),
            key="ai_issue_btn",
        )
    with bc3:
        clear_btn = st.button(
            "🗑️ Clear",
            use_container_width=True,
            key="ai_clear_btn",
        )

    if clear_btn:
        st.session_state.last_response = ""
        st.session_state.original_query = ""
        st.session_state.selected_history_idx = None
        st.rerun()

    # ── Issue Spotting ──
    if issue_btn and query.strip():
        with st.spinner("🔍 Decomposing issues…"):
            result = run_issue_spot(query.strip())
        st.markdown("### 🔍 Issue Decomposition")
        st.markdown(f'<div class="response-box">{esc(result)}</div>', unsafe_allow_html=True)

    # ── Main Generation ──
    if generate_btn and query.strip():
        with st.spinner(f"🧠 Generating {mode_info['label']} analysis…"):
            start_t = time.time()
            result = run_ai_query(query.strip(), task, mode, doc_context)
            elapsed = time.time() - start_t

        st.session_state.last_response = result
        st.session_state.original_query = query.strip()
        st.session_state.selected_history_idx = None
        add_to_history(query.strip(), result, task, mode)
        st.caption(f"⏱️ Generated in {elapsed:.1f}s · {len(result.split()):,} words")

    # ── Display Response ──
    if st.session_state.last_response and st.session_state.selected_history_idx is None:
        response = st.session_state.last_response
        st.markdown("---")
        st.markdown("### 📋 Analysis Result")

        # Export row
        fname = f"LexiAssist_Analysis_{datetime.now():%Y%m%d_%H%M}"
        ex1, ex2, ex3, ex4 = st.columns(4)
        with ex1:
            st.download_button("📥 TXT", export_txt(response), f"{fname}.txt", "text/plain", key="resp_dl_txt", use_container_width=True)
        with ex2:
            st.download_button("📥 HTML", export_html(response), f"{fname}.html", "text/html", key="resp_dl_html", use_container_width=True)
        with ex3:
            safe_pdf_download(response, "Legal Analysis", fname, "resp_dl_pdf")
        with ex4:
            safe_docx_download(response, "Legal Analysis", fname, "resp_dl_docx")

        st.markdown(f'<div class="response-box">{esc(response)}</div>', unsafe_allow_html=True)

        # Quality critique
        if mode in ("standard", "comprehensive"):
            with st.expander("🔎 Quality Assessment", expanded=False):
                if st.button("Run Critique", key="run_critique_btn"):
                    with st.spinner("Assessing quality…"):
                        critique = run_critique(st.session_state.original_query, response)
                    st.markdown(f'<div class="response-box">{esc(critique)}</div>', unsafe_allow_html=True)

        # Follow-up
        st.markdown("### 🔄 Follow-Up Question")
        followup = st.text_input(
            "Ask a follow-up based on the analysis above:",
            placeholder="E.g.: 'What if the contract had an arbitration clause?'",
            key="followup_input",
        )
        if st.button("🔄 Follow Up", disabled=not followup.strip(), key="followup_btn"):
            with st.spinner("🔄 Processing follow-up…"):
                fu_result = run_followup(
                    st.session_state.original_query,
                    response,
                    followup.strip(),
                    mode,
                )
            st.session_state.last_response = fu_result
            add_to_history(f"[Follow-up] {followup.strip()}", fu_result, "general", mode)
            st.rerun()

        st.markdown('<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated legal analysis. This does not constitute legal advice. Verify all citations and authorities independently before reliance.</div>', unsafe_allow_html=True)
        # ═══════════════════════════════════════════════════════
# PAGE: LEGAL RESEARCH
# ═══════════════════════════════════════════════════════
def render_research():
    st.markdown("""<div class="page-header">
        <h2>📚 Legal Research</h2>
        <p>Case law · Statutes · Authorities · Research Memoranda</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key first.")
        return

    mode = st.session_state.response_mode
    mode_info = RESPONSE_MODES[mode]
    st.info(f"**Research Mode: {mode_info['label']}** — {mode_info['desc']}")

    query = st.text_area(
        "🔍 Research Query",
        height=140,
        placeholder="E.g.: 'What are the grounds for setting aside an arbitral award under the Arbitration and Mediation Act 2023?'",
        key="research_query_ta",
    )

    rc1, rc2 = st.columns([1, 1])
    with rc1:
        research_btn = st.button(
            f"📚 Research ({mode_info['label']})",
            type="primary", use_container_width=True,
            disabled=not query.strip(),
            key="research_go_btn",
        )
    with rc2:
        clear_btn = st.button("🗑️ Clear Results", use_container_width=True, key="research_clear_btn")

    if clear_btn:
        st.session_state.research_results = ""
        st.rerun()

    if research_btn and query.strip():
        with st.spinner("📚 Researching…"):
            start_t = time.time()
            result = run_research(query.strip(), mode)
            elapsed = time.time() - start_t
        st.session_state.research_results = result
        add_to_history(f"[Research] {query.strip()}", result, "research", mode)
        st.caption(f"⏱️ {elapsed:.1f}s · {len(result.split()):,} words")

    result = st.session_state.research_results
    if result:
        st.markdown("---")

        fname = f"LexiAssist_Research_{datetime.now():%Y%m%d_%H%M}"
        ex1, ex2, ex3, ex4 = st.columns(4)
        with ex1:
            st.download_button("📥 TXT", export_txt(result, "Legal Research"), f"{fname}.txt", "text/plain", key="res_dl_txt", use_container_width=True)
        with ex2:
            st.download_button("📥 HTML", export_html(result, "Legal Research"), f"{fname}.html", "text/html", key="res_dl_html", use_container_width=True)
        with ex3:
            safe_pdf_download(result, "Legal Research", fname, "res_dl_pdf")
        with ex4:
            safe_docx_download(result, "Legal Research", fname, "res_dl_docx")

        st.markdown(f'<div class="response-box">{esc(result)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated research. Verify all citations independently.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# PAGE: CASES
# ═══════════════════════════════════════════════════════
def render_cases():
    st.markdown("""<div class="page-header">
        <h2>📁 Case Manager</h2>
        <p>Track cases, hearings, deadlines, and suit numbers</p>
    </div>""", unsafe_allow_html=True)

    tab_list, tab_add = st.tabs(["📋 All Cases", "➕ Add Case"])

    with tab_add:
        with st.form("add_case_form", clear_on_submit=True):
            st.markdown("#### ➕ New Case")
            ac1, ac2 = st.columns(2)
            with ac1:
                title = st.text_input("Case Title *", key="case_title_inp")
                suit_no = st.text_input("Suit Number", key="case_suit_inp")
                court = st.text_input("Court", key="case_court_inp")
            with ac2:
                status = st.selectbox("Status", CASE_STATUSES, key="case_status_inp")
                client_opts = ["— None —"] + [c.get("name", "?") for c in st.session_state.clients]
                client_sel = st.selectbox("Client", client_opts, key="case_client_inp")
                next_hearing = st.date_input("Next Hearing", value=None, key="case_hearing_inp")
            notes = st.text_area("Notes", height=80, key="case_notes_inp")

            if st.form_submit_button("➕ Add Case", type="primary"):
                if title.strip():
                    client_id = ""
                    if client_sel != "— None —":
                        cidx = client_opts.index(client_sel) - 1
                        if 0 <= cidx < len(st.session_state.clients):
                            client_id = st.session_state.clients[cidx]["id"]
                    add_case({
                        "title": title.strip(), "suit_no": suit_no.strip(),
                        "court": court.strip(), "status": status,
                        "client_id": client_id,
                        "next_hearing": str(next_hearing) if next_hearing else "",
                        "notes": notes.strip(),
                    })
                    st.success(f"✅ Case '{title}' added!")
                    st.rerun()
                else:
                    st.error("❌ Case title is required.")

    with tab_list:
        cases = st.session_state.cases
        if not cases:
            st.info("No cases yet. Add one in the ➕ Add Case tab.")
            return

        # Filters
        fc1, fc2 = st.columns([1, 2])
        with fc1:
            filt_status = st.selectbox("Filter by Status", ["All"] + CASE_STATUSES, key="case_filter_sel")
        with fc2:
            filt_search = st.text_input("🔍 Search cases", key="case_search_inp", placeholder="Title, suit number, court…")

        filtered = cases
        if filt_status != "All":
            filtered = [c for c in filtered if c.get("status") == filt_status]
        if filt_search.strip():
            s = filt_search.strip().lower()
            filtered = [c for c in filtered if s in c.get("title", "").lower() or s in c.get("suit_no", "").lower() or s in c.get("court", "").lower()]

        st.caption(f"Showing {len(filtered)} of {len(cases)} cases")

        for c in filtered:
            d = days_until(c.get("next_hearing", ""))
            badge = "badge-err" if d <= 3 else ("badge-warn" if d <= 7 else "badge-ok")
            hearing_txt = fmt_date(c.get("next_hearing", ""))
            cname = get_client_name(c.get("client_id", ""))

            st.markdown(f"""<div class="custom-card">
                <h4>{esc(c.get('title', 'Untitled'))}</h4>
                <span class="badge badge-info">{esc(c.get('status', ''))}</span>
                Suit: <strong>{esc(c.get('suit_no', '—'))}</strong> ·
                Court: {esc(c.get('court', '—'))} ·
                Client: {esc(cname)} ·
                Hearing: {esc(hearing_txt)}
                <span class="badge {badge}">{esc(relative_date(c.get('next_hearing', '')))}</span>
            </div>""", unsafe_allow_html=True)

            with st.expander(f"✏️ Manage: {c.get('title', '')[:50]}", expanded=False):
                mc1, mc2 = st.columns(2)
                with mc1:
                    new_status = st.selectbox(
                        "Status", CASE_STATUSES,
                        index=CASE_STATUSES.index(c["status"]) if c.get("status") in CASE_STATUSES else 0,
                        key=f"cs_{c['id']}",
                    )
                    new_hearing = st.date_input("Hearing", value=None, key=f"ch_{c['id']}")
                    new_notes = st.text_area("Notes", value=c.get("notes", ""), height=60, key=f"cn_{c['id']}")
                    if st.button("💾 Save Changes", key=f"save_{c['id']}", use_container_width=True):
                        upd = {"status": new_status, "notes": new_notes}
                        if new_hearing:
                            upd["next_hearing"] = str(new_hearing)
                        update_case(c["id"], upd)
                        st.success("✅ Updated!")
                        st.rerun()
                with mc2:
                    st.markdown(f"**Created:** {esc(fmt_date(c.get('created_at', '')))}")
                    if c.get("updated_at"):
                        st.markdown(f"**Updated:** {esc(fmt_date(c['updated_at']))}")
                    if c.get("notes"):
                        st.caption(f"📝 {c['notes'][:300]}")
                    st.markdown("")
                    if st.button("🗑️ Delete Case", key=f"del_{c['id']}", type="secondary", use_container_width=True):
                        delete_case(c["id"])
                        st.success("✅ Deleted!")
                        st.rerun()


# ═══════════════════════════════════════════════════════
# PAGE: CALENDAR
# ═══════════════════════════════════════════════════════
def render_calendar():
    st.markdown("""<div class="page-header">
        <h2>📅 Hearing Calendar</h2>
        <p>Upcoming hearings and deadlines at a glance</p>
    </div>""", unsafe_allow_html=True)

    hearings = get_hearings()
    if not hearings:
        st.info("No upcoming hearings. Add cases with hearing dates in the Case Manager.")
        return

    # Summary
    overdue = [h for h in hearings if days_until(h["date"]) < 0]
    today_h = [h for h in hearings if days_until(h["date"]) == 0]
    week_h = [h for h in hearings if 0 < days_until(h["date"]) <= 7]

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.metric("Total Hearings", len(hearings))
    with sc2:
        st.metric("⚠️ Overdue", len(overdue))
    with sc3:
        st.metric("📍 Today", len(today_h))
    with sc4:
        st.metric("This Week", len(week_h))

    st.markdown("---")

    for h in hearings:
        d = days_until(h["date"])
        if d < 0:
            badge_class = "badge-err"
            border_color = "#dc2626"
        elif d <= 3:
            badge_class = "badge-err"
            border_color = "#dc2626"
        elif d <= 7:
            badge_class = "badge-warn"
            border_color = "#f59e0b"
        else:
            badge_class = "badge-ok"
            border_color = "#059669"

        st.markdown(f"""<div class="custom-card" style="border-left: 4px solid {border_color};">
            <h4>{esc(h['title'])}</h4>
            Suit: <strong>{esc(h['suit'])}</strong> · Court: {esc(h['court'])} · Status: {esc(h['status'])}<br>
            📅 <strong>{esc(fmt_date(h['date']))}</strong>
            <span class="badge {badge_class}">{esc(relative_date(h['date']))}</span>
        </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# PAGE: TEMPLATES
# ═══════════════════════════════════════════════════════
def render_templates():
    st.markdown("""<div class="page-header">
        <h2>📋 Document Templates</h2>
        <p>Professional Nigerian legal document templates</p>
    </div>""", unsafe_allow_html=True)

    cats = sorted(set(t["cat"] for t in TEMPLATES))
    sel_cat = st.selectbox("Filter by Category", ["All"] + cats, key="tmpl_cat_sel")

    templates = TEMPLATES if sel_cat == "All" else [t for t in TEMPLATES if t["cat"] == sel_cat]

    for t in templates:
        st.markdown(f"""<div class="custom-card">
            <h4>{esc(t['name'])}</h4>
            <span class="badge badge-info">{esc(t['cat'])}</span>
        </div>""", unsafe_allow_html=True)

        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            if st.button(f"👁️ Preview", key=f"prev_t_{t['id']}", use_container_width=True):
                st.code(t["content"], language=None)
        with tc2:
            if st.button(f"📋 Load to AI", key=f"load_t_{t['id']}", use_container_width=True):
                st.session_state.loaded_template = t["content"]
                st.success(f"✅ '{t['name']}' loaded! Go to AI Assistant tab.")
        with tc3:
            st.download_button(
                "📥 Download",
                t["content"],
                f"{t['name'].replace(' ', '_')}.txt",
                "text/plain",
                key=f"dl_t_{t['id']}",
                use_container_width=True,
            )


# ═══════════════════════════════════════════════════════
# PAGE: CLIENTS
# ═══════════════════════════════════════════════════════
def render_clients():
    st.markdown("""<div class="page-header">
        <h2>👥 Client Manager</h2>
        <p>Manage your client database and track engagement</p>
    </div>""", unsafe_allow_html=True)

    tab_list, tab_add = st.tabs(["👥 All Clients", "➕ Add Client"])

    with tab_add:
        with st.form("add_client_form", clear_on_submit=True):
            st.markdown("#### ➕ New Client")
            cc1, cc2 = st.columns(2)
            with cc1:
                name = st.text_input("Client Name *", key="cl_name_inp")
                email = st.text_input("Email", key="cl_email_inp")
                phone = st.text_input("Phone", key="cl_phone_inp")
            with cc2:
                cl_type = st.selectbox("Type", CLIENT_TYPES, key="cl_type_inp")
                address = st.text_area("Address", height=80, key="cl_addr_inp")
            notes = st.text_input("Notes", key="cl_notes_inp")

            if st.form_submit_button("➕ Add Client", type="primary"):
                if name.strip():
                    add_client({
                        "name": name.strip(), "email": email.strip(),
                        "phone": phone.strip(), "type": cl_type,
                        "address": address.strip(), "notes": notes.strip(),
                    })
                    st.success(f"✅ Client '{name}' added!")
                    st.rerun()
                else:
                    st.error("❌ Client name is required.")

    with tab_list:
        clients = st.session_state.clients
        if not clients:
            st.info("No clients yet. Add one in the ➕ Add Client tab.")
            return

        search = st.text_input("🔍 Search clients", key="cl_search_inp", placeholder="Name, email, type…")
        filtered = clients
        if search.strip():
            s = search.strip().lower()
            filtered = [c for c in filtered if s in c.get("name", "").lower() or s in c.get("email", "").lower() or s in c.get("type", "").lower()]

        for cl in filtered:
            cc = client_case_count(cl["id"])
            bill = client_billable(cl["id"])
            st.markdown(f"""<div class="custom-card">
                <h4>{esc(cl.get('name', ''))}</h4>
                <span class="badge badge-info">{esc(cl.get('type', ''))}</span>
                📧 {esc(cl.get('email', '—'))} · 📞 {esc(cl.get('phone', '—'))}<br>
                📁 {cc} case{'s' if cc != 1 else ''} · 💰 {esc(fmt_currency(bill))}
                {f" · 📝 {esc(cl.get('notes', '')[:80])}" if cl.get('notes') else ""}
            </div>""", unsafe_allow_html=True)

            bc1, bc2 = st.columns([1, 4])
            with bc1:
                if st.button("🗑️ Delete", key=f"del_cl_{cl['id']}", use_container_width=True):
                    delete_client(cl["id"])
                    st.success("✅ Deleted!")
                    st.rerun()


# ═══════════════════════════════════════════════════════
# PAGE: BILLING
# ═══════════════════════════════════════════════════════
def render_billing():
    st.markdown("""<div class="page-header">
        <h2>💰 Billing Manager</h2>
        <p>Time entries, invoicing, and financial reports</p>
    </div>""", unsafe_allow_html=True)

    tab_time, tab_inv, tab_report = st.tabs(["⏱️ Time Entries", "📄 Invoices", "📊 Reports"])

    # ── Time Entries ──
    with tab_time:
        with st.form("add_time_form", clear_on_submit=True):
            st.markdown("#### ➕ New Time Entry")
            bt1, bt2 = st.columns(2)
            with bt1:
                cl_names = [c.get("name", "?") for c in st.session_state.clients]
                if not cl_names:
                    st.warning("Add a client first.")
                    cl_sel_b = None
                else:
                    cl_sel_b = st.selectbox("Client *", cl_names, key="bill_cl_inp")
                desc = st.text_input("Description *", key="bill_desc_inp")
            with bt2:
                hours = st.number_input("Hours *", min_value=0.0, step=0.25, key="bill_hrs_inp")
                rate = st.number_input("Rate (₦/hr) *", min_value=0.0, step=1000.0, value=50000.0, key="bill_rate_inp")
                entry_date = st.date_input("Date", key="bill_date_inp")

            if st.form_submit_button("➕ Add Entry", type="primary"):
                if cl_sel_b and desc.strip() and hours > 0:
                    cidx = cl_names.index(cl_sel_b)
                    add_time_entry({
                        "client_id": st.session_state.clients[cidx]["id"],
                        "client_name": cl_sel_b,
                        "description": desc.strip(),
                        "hours": hours, "rate": rate,
                        "date": str(entry_date),
                    })
                    st.success(f"✅ {hours}h @ {fmt_currency(rate)}/hr added!")
                    st.rerun()
                else:
                    st.error("❌ Fill all required fields.")

        entries = st.session_state.time_entries
        if entries:
            st.markdown("#### 📋 Recent Entries")
            for te in reversed(entries[-20:]):
                st.markdown(f"""<div class="custom-card">
                    <strong>{esc(te.get('description', ''))}</strong><br>
                    {esc(te.get('client_name', ''))} ·
                    {te.get('hours', 0)}h @ {esc(fmt_currency(te.get('rate', 0)))}/hr ·
                    <strong>{esc(fmt_currency(te.get('amount', 0)))}</strong> ·
                    {esc(fmt_date(te.get('date', '')))}
                </div>""", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_te_{te['id']}", help="Delete entry"):
                    delete_time_entry(te["id"])
                    st.rerun()

    # ── Invoices ──
    with tab_inv:
        st.markdown("#### 📄 Generate Invoice")
        if st.session_state.clients:
            cl_names_inv = [c.get("name", "?") for c in st.session_state.clients]
            inv_client = st.selectbox("Client", cl_names_inv, key="inv_cl_sel")
            if st.button("📄 Generate Invoice", type="primary", key="gen_inv_btn", use_container_width=True):
                cidx = cl_names_inv.index(inv_client)
                cid = st.session_state.clients[cidx]["id"]
                inv = make_invoice(cid)
                if inv:
                    st.success(f"✅ Invoice {inv['invoice_no']} — {fmt_currency(inv['total'])}")
                    st.rerun()
                else:
                    st.warning("No billable entries for this client.")
        else:
            st.info("Add clients first.")

        if st.session_state.invoices:
            st.markdown("#### 📋 All Invoices")
            for inv in reversed(st.session_state.invoices):
                inv_text = (
                    f"INVOICE: {inv['invoice_no']}\n"
                    f"Date: {fmt_date(inv['date'])}\n"
                    f"Client: {inv['client_name']}\n"
                    f"Status: {inv['status']}\n\n"
                    f"{'='*40}\n"
                )
                for e in inv.get("entries", []):
                    inv_text += f"{e.get('description', '')} | {e.get('hours', 0)}h | {fmt_currency(e.get('amount', 0))}\n"
                inv_text += f"{'='*40}\nTOTAL: {fmt_currency(inv['total'])}\n"

                st.markdown(f"""<div class="custom-card">
                    <h4>{esc(inv['invoice_no'])}</h4>
                    {esc(inv['client_name'])} · {esc(fmt_date(inv['date']))} ·
                    <strong>{esc(fmt_currency(inv['total']))}</strong> ·
                    <span class="badge badge-info">{esc(inv['status'])}</span>
                </div>""", unsafe_allow_html=True)

                ic1, ic2, ic3 = st.columns(3)
                with ic1:
                    st.download_button("📥 TXT", export_txt(inv_text, f"Invoice {inv['invoice_no']}"), f"Invoice_{inv['invoice_no']}.txt", "text/plain", key=f"inv_txt_{inv['id']}", use_container_width=True)
                with ic2:
                    safe_pdf_download(inv_text, f"Invoice {inv['invoice_no']}", f"Invoice_{inv['invoice_no']}", f"inv_pdf_{inv['id']}")
                with ic3:
                    safe_docx_download(inv_text, f"Invoice {inv['invoice_no']}", f"Invoice_{inv['invoice_no']}", f"inv_docx_{inv['id']}")

    # ── Reports ──
    with tab_report:
        st.markdown("#### 📊 Billing Summary")
        entries = st.session_state.time_entries
        if entries:
            th = total_hours()
            tb = total_billable()
            avg = tb / th if th else 0

            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                st.metric("Total Hours", f"{th:.1f}")
            with rc2:
                st.metric("Total Billable", fmt_currency(tb))
            with rc3:
                st.metric("Avg Rate/hr", fmt_currency(avg))

            if HAS_PLOTLY:
                df = pd.DataFrame(entries)
                if "client_name" in df.columns and "amount" in df.columns:
                    chart_df = df.groupby("client_name")["amount"].sum().reset_index()
                    chart_df.columns = ["Client", "Amount"]
                    fig = px.bar(chart_df, x="Client", y="Amount", title="Billable Amount by Client", color_discrete_sequence=["#059669"])
                    st.plotly_chart(fig, use_container_width=True)

                if "date" in df.columns and "hours" in df.columns:
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")
                    time_df = df.dropna(subset=["date"]).groupby("date")["hours"].sum().reset_index()
                    if not time_df.empty:
                        fig2 = px.line(time_df, x="date", y="hours", title="Hours Over Time", color_discrete_sequence=["#059669"])
                        st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No time entries to report.")


# ═══════════════════════════════════════════════════════
# PAGE: TOOLS
# ═══════════════════════════════════════════════════════
def render_tools():
    st.markdown("""<div class="page-header">
        <h2>🔧 Legal Reference Tools</h2>
        <p>Limitation periods · Court hierarchy · Latin maxims</p>
    </div>""", unsafe_allow_html=True)

    tab_lim, tab_court, tab_maxim = st.tabs(["⏳ Limitation Periods", "🏛️ Court Hierarchy", "📜 Legal Maxims"])

    with tab_lim:
        st.markdown("#### ⏳ Limitation Periods (Nigeria)")
        st.caption("Key limitation periods under Nigerian law")
        df_lim = pd.DataFrame(LIMITATION_PERIODS)
        df_lim.columns = ["Cause of Action", "Limitation Period", "Authority"]
        st.dataframe(df_lim, use_container_width=True, hide_index=True)

        st.download_button(
            "📥 Download CSV",
            df_lim.to_csv(index=False),
            "limitation_periods_nigeria.csv",
            "text/csv",
            key="dl_lim_csv",
        )

    with tab_court:
        st.markdown("#### 🏛️ Nigerian Court Hierarchy")
        st.caption("From the Supreme Court down to courts of first instance")
        for c in COURT_HIERARCHY:
            indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * (c["level"] - 1)
            level_label = {1: "APEX", 2: "APPELLATE", 3: "SUPERIOR", 4: "LOWER"}.get(c["level"], "")
            st.markdown(f"""<div class="tool-card">
                {indent}{c['icon']} <strong>{esc(c['name'])}</strong>
                <span class="badge badge-info">{level_label}</span><br>
                {indent}&nbsp;&nbsp;&nbsp;&nbsp;<small>{esc(c['desc'])}</small>
            </div>""", unsafe_allow_html=True)

    with tab_maxim:
        st.markdown("#### 📜 Legal Maxims")
        search = st.text_input("🔍 Search maxims", key="maxim_search_inp", placeholder="E.g. 'nemo' or 'remedy'")
        maxims = LEGAL_MAXIMS
        if search.strip():
            s = search.strip().lower()
            maxims = [m for m in maxims if s in m["maxim"].lower() or s in m["meaning"].lower()]

        st.caption(f"Showing {len(maxims)} maxim{'s' if len(maxims) != 1 else ''}")
        for m in maxims:
            st.markdown(f"""<div class="tool-card">
                <strong><em>{esc(m['maxim'])}</em></strong><br>
                {esc(m['meaning'])}
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════
def main():
    # Auto-connect from secrets/env
    auto_connect()

    # Apply selected theme CSS
    st.markdown(get_theme_css(st.session_state.theme), unsafe_allow_html=True)

    # If no API key available, show secure setup screen
    if not st.session_state.api_configured:
        render_setup_screen()
        return

    # Render sidebar (clean — no API key shown)
    render_sidebar()

    # ── TOP NAVIGATION TABS (not in sidebar) ──
    tabs = st.tabs([
        "🏠 Home",
        "🧠 AI Assistant",
        "📚 Research",
        "📁 Cases",
        "📅 Calendar",
        "📋 Templates",
        "👥 Clients",
        "💰 Billing",
        "🔧 Tools",
    ])

    with tabs[0]:
        render_home()
    with tabs[1]:
        render_ai()
    with tabs[2]:
        render_research()
    with tabs[3]:
        render_cases()
    with tabs[4]:
        render_calendar()
    with tabs[5]:
        render_templates()
    with tabs[6]:
        render_clients()
    with tabs[7]:
        render_billing()
    with tabs[8]:
        render_tools()

    # Footer
    st.markdown("---")
    st.caption("⚖️ LexiAssist v8.0 © 2026 · Elite AI Legal Engine for Nigerian Lawyers · ⚠️ AI-generated information — not legal advice — verify all citations independently")


if __name__ == "__main__":
    main()
