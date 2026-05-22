"""LexiAssist constants — DB URL resolver, Gemini model list, task / mode
catalogues, upload types, and cost-per-token figures.
"""
from __future__ import annotations

from .runtime import st, os

# ═══════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════
def _get_db_url() -> str:
    url = ""
    try:
        url = st.secrets["DATABASE_URL"]
    except Exception:
        url = os.getenv("DATABASE_URL", "")
    if not url or not url.strip():
        st.error("❌ DATABASE_URL is not set. Add it to your Streamlit secrets.")
        st.stop()
    # Streamlit Cloud / psycopg2 requires postgresql:// not postgres://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url.strip()

# ═══════════════════════════════════════════════════════
# GEMINI MODELS (Best Free Tier – April 2026)
# ═══════════════════════════════════════════════════════
def _parse_models_config():
    models_str = "" 
    try:
        models_str = st.secrets["GEMINI_MODELS"]
    except Exception:
        models_str = os.getenv("GEMINI_MODELS", "")
    if models_str and models_str.strip():
        return [m.strip() for m in models_str.split(",") if m.strip()]
    # Best free models available right now
    return [
        "gemini-2.5-pro",           # ← Highest reasoning quality
        "gemini-2.5-flash",         # ← Best everyday balance (recommended default)
        "gemini-2.5-flash-lite"     # ← Maximum volume when you hit limits
    ]

SUPPORTED_MODELS = _parse_models_config()
DEFAULT_MODEL = "gemini-2.5-flash"   # Change to "gemini-2.5-pro" if you want max quality by default

CASE_STATUSES = ["Active", "Pending", "Completed", "Archived"]
CLIENT_TYPES = ["Individual", "Corporate", "Government", "NGO"]

TASK_TYPES = {
    "general":          {"label": "💬 General Query",            "desc": "Any legal question"},
    "analysis":         {"label": "🔍 Legal Analysis",           "desc": "Issue spotting, CREAC reasoning"},
    "drafting":         {"label": "📄 Document Drafting",        "desc": "Contracts, pleadings, affidavits"},
    "research":         {"label": "📚 Legal Research",           "desc": "Case law, statutes, authorities"},
    "procedure":        {"label": "📋 Procedural Guidance",      "desc": "Filing rules, court practice"},
    "advisory":         {"label": "🎯 Strategic Advisory",       "desc": "Risk mapping, options, strategy"},
    "interpret":        {"label": "⚖️ Statutory Interpretation", "desc": "Legislation analysis"},
    "contract_review":  {"label": "📑 Contract Review",          "desc": "Clause-by-clause risk analysis"},
}

RESPONSE_MODES = {
    "brief":         {"label": "⚡ Brief",          "desc": "Direct answer, 3-5 sentences",        "tokens": 8000,   "temp": 0.1},
    "standard":      {"label": "📝 Standard",       "desc": "Structured analysis, 5-10 paragraphs", "tokens": 32000,  "temp": 0.15},
    "comprehensive": {"label": "🔬 Comprehensive",  "desc": "Full CREAC + Strategy + Risk Ranking",  "tokens": 131072, "temp": 0.2},
}

UPLOAD_TYPES = ["pdf", "docx", "doc", "txt", "xlsx", "xls", "csv", "json", "rtf"]

# Cost per 1M tokens (approx Gemini 2.5 Flash pricing)
COST_PER_1M_INPUT = 0.15
COST_PER_1M_OUTPUT = 0.60

# ═══════════════════════════════════════════════════════
# CASE TYPE OPTIONS (shared across pages)
# ═══════════════════════════════════════════════════════
CASE_TYPE_OPTIONS = [
    "Breach of Contract",
    "Land / Property Dispute",
    "Criminal Defence",
    "Employment / Wrongful Termination",
    "Fundamental Rights Enforcement",
    "Debt Recovery",
    "Matrimonial / Family Law",
    "Company / Commercial Dispute",
    "Defamation",
    "Personal Injury / Negligence",
    "Election Petition",
    "Judicial Review / Certiorari",
    "Tenancy / Landlord-Tenant",
    "Probate / Estate Administration",
    "Insurance / Subrogation",
    "Banking / Financial Dispute",
    "Intellectual Property",
    "Admiralty / Maritime",
    "Environmental Law",
    "Tax Dispute",
    "Other (describe below)",
]


# ═══════════════════════════════════════════════════════
# FX RATE — USD → NGN
# ═══════════════════════════════════════════════════════
# Used to convert Gemini's USD-denominated cost estimates into Naira so
# that the firm-wide monthly_ai_budget (set in NGN) can be enforced.
#
# This is intentionally NOT a live FX feed — a stale-but-conservative
# constant beats a flaky API call inside the hot path of every AI call.
# Override via Streamlit secret `USD_TO_NGN` or env var of the same name
# when the rate drifts materially. Bump the default in code on each major
# release so deployments without secrets stay reasonably current.
def _get_usd_to_ngn() -> float:
    raw = ""
    try:
        raw = str(st.secrets.get("USD_TO_NGN", ""))
    except Exception:
        raw = ""
    if not raw:
        raw = os.getenv("USD_TO_NGN", "")
    try:
        rate = float(raw) if raw else 0.0
        if rate > 0:
            return rate
    except (TypeError, ValueError):
        pass
    return 1600.0  # fallback default — review at every major release


USD_TO_NGN = _get_usd_to_ngn()
