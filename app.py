"""
LexiAssist v2.0 — AI-Powered Legal Practice Management for Nigerian Lawyers.

Requirements:
    streamlit>=1.32.0
    google-generativeai>=0.8.0
    pandas>=2.0.0
    plotly>=5.18.0
"""

from __future__ import annotations

import html
import json
import logging
import os
import time
import uuid
from datetime import datetime, date
from functools import wraps
from typing import Any, Callable, Optional

import google.generativeai as genai
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("LexiAssist")

# ── Page Configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="LexiAssist — Legal Practice Management",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            "# LexiAssist v2.0\n"
            "AI-Powered Legal Practice Management for Nigerian Lawyers."
        ),
    },
)

# ── Constants ────────────────────────────────────────────────────────────────
CASE_STATUSES: list[str] = ["Active", "Pending", "Completed", "Archived"]
CLIENT_TYPES: list[str] = ["Individual", "Corporate", "Government"]

TASK_TYPES: dict[str, dict[str, str]] = {
    "drafting": {
        "label": "📄 Document Drafting",
        "description": "Contracts, pleadings, applications, affidavits",
        "icon": "📄",
    },
    "analysis": {
        "label": "🔍 Legal Analysis",
        "description": "Issue spotting, IRAC/FILAC reasoning",
        "icon": "🔍",
    },
    "research": {
        "label": "📚 Legal Research",
        "description": "Case law, statutes, authorities",
        "icon": "📚",
    },
    "procedure": {
        "label": "📋 Procedural Guidance",
        "description": "Court filing, evidence rules",
        "icon": "📋",
    },
    "interpretation": {
        "label": "⚖️ Statutory Interpretation",
        "description": "Analyze and explain legislation",
        "icon": "⚖️",
    },
    "general": {
        "label": "💬 General Query",
        "description": "Ask anything legal-related",
        "icon": "💬",
    },
}

# ── Model Configuration ─────────────────────────────────────────────────────
MODEL_MIGRATION_MAP: dict[str, str] = {
    "gemini-2.0-flash": "gemini-2.5-flash",
    "gemini-2.0-flash-001": "gemini-2.5-flash",
    "gemini-2.0-flash-lite": "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite-001": "gemini-2.5-flash-lite",
}
SUPPORTED_MODELS: list[str] = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
DEFAULT_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_INSTRUCTION: str = (
    "You are LexiAssist, an advanced AI legal assistant designed specifically "
    "for Nigerian lawyers.\n\n"
    "JURISDICTION: Nigeria — Constitution of the Federal Republic of Nigeria 1999 "
    "(as amended), Federal and State Acts, subsidiary legislation, Rules of Court, "
    "and Nigerian case law.\n\n"
    "CORE PRINCIPLES:\n"
    "1. Use step-by-step reasoning (IRAC / FILAC methods where applicable).\n"
    "2. Provide legal information and analysis — NEVER definitive legal conclusions.\n"
    "3. Never fabricate cases, statutes, or authorities. State uncertainty clearly.\n"
    "4. Include relevant statutory and case references when available.\n"
    "5. Use professional tone suitable for Nigerian legal practice.\n"
    "6. Format responses with clear headings and numbered points.\n\n"
    "RESPONSE STRUCTURE:\n"
    "1. Brief restatement of the request.\n"
    "2. Key assumptions (if any).\n"
    "3. Detailed analysis or document draft.\n"
    "4. Relevant legal authorities.\n"
    "5. Caveats and recommendations."
)

RESEARCH_INSTRUCTION: str = (
    SYSTEM_INSTRUCTION
    + "\n\nFor legal research tasks, additionally provide:\n"
    "• Relevant Nigerian statutes with specific sections and any recent amendments.\n"
    "• Key case law: case names, citations (where known), holdings, and court level.\n"
    "• Fundamental legal principles and how Nigerian courts have interpreted them.\n"
    "• Practical application: procedural requirements, limitation periods, jurisdiction.\n"
    "• Common pitfalls, strategic considerations, and ADR options where relevant.\n"
    "• If uncertain about a specific citation, state the general principle instead."
)

GENERATION_CONFIG: dict[str, Any] = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}


def normalize_model_name(name: str) -> str:
    """Migrate deprecated model IDs and return a supported model name."""
    clean = (name or "").strip()
    migrated = MODEL_MIGRATION_MAP.get(clean, clean)
    return migrated if migrated in SUPPORTED_MODELS else DEFAULT_MODEL


def get_active_model() -> str:
    """Return the currently selected Gemini model."""
    return normalize_model_name(
        st.session_state.get("gemini_model", DEFAULT_MODEL)
    )


# ── Retry Decorator ─────────────────────────────────────────────────────────
def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retryable: tuple[type[Exception], ...] = (Exception,),
) -> Callable:
    """Retry a function with exponential back-off."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable as exc:
                    if attempt == max_attempts:
                        raise
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "Attempt %d/%d for %s failed: %s — retrying in %.1fs",
                        attempt,
                        max_attempts,
                        func.__name__,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

        return wrapper

    return decorator


# ── CSS ──────────────────────────────────────────────────────────────────────
_CSS = """
<style>
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}
.main-header {
    background: linear-gradient(135deg, #059669 0%, #0d9488 100%);
    padding: 1.5rem 2rem;
    border-radius: 1rem;
    margin-bottom: 2rem;
    color: white;
    box-shadow: 0 10px 40px rgba(5,150,105,.3);
}
.main-header h1 { margin:0; font-size:2.5rem; font-weight:700; }
.main-header p  { margin:.5rem 0 0; opacity:.9; font-size:1rem; }
.custom-card {
    background:#fff; border-radius:1rem; padding:1.5rem;
    box-shadow:0 4px 20px rgba(0,0,0,.08); border:1px solid #e2e8f0;
    margin-bottom:1rem; transition:all .3s ease;
}
.custom-card:hover {
    box-shadow:0 8px 30px rgba(0,0,0,.12); transform:translateY(-2px);
}
.stat-card {
    background:linear-gradient(135deg,#f0fdf4 0%,#dcfce7 100%);
    border-radius:1rem; padding:1.5rem; text-align:center;
    border:1px solid #bbf7d0;
}
.stat-card.blue   { background:linear-gradient(135deg,#eff6ff,#dbeafe); border-color:#bfdbfe; }
.stat-card.purple { background:linear-gradient(135deg,#faf5ff,#f3e8ff); border-color:#e9d5ff; }
.stat-card.amber  { background:linear-gradient(135deg,#fffbeb,#fef3c7); border-color:#fde68a; }
.stat-value { font-size:2rem; font-weight:700; color:#059669; }
.stat-card.blue   .stat-value { color:#2563eb; }
.stat-card.purple .stat-value { color:#7c3aed; }
.stat-card.amber  .stat-value { color:#d97706; }
.stat-label { font-size:.875rem; color:#64748b; margin-top:.25rem; }
.badge {
    display:inline-block; padding:.25rem .75rem; border-radius:9999px;
    font-size:.75rem; font-weight:600; text-transform:uppercase;
}
.badge-success { background:#dcfce7; color:#166534; }
.badge-warning { background:#fef3c7; color:#92400e; }
.badge-info    { background:#dbeafe; color:#1e40af; }
.badge-danger  { background:#fee2e2; color:#991b1b; }
.response-box {
    background:#f8fafc; border:1px solid #e2e8f0; border-radius:.75rem;
    padding:1.5rem; margin:1rem 0; white-space:pre-wrap;
    font-family:'Georgia',serif; line-height:1.8;
}
.disclaimer {
    background:#fef3c7; border-left:4px solid #f59e0b;
    padding:1rem; border-radius:0 .5rem .5rem 0;
    margin-top:1rem; font-size:.875rem;
}
.calendar-event {
    padding:1rem; border-radius:.75rem; margin-bottom:.75rem; border-left:4px solid;
}
.calendar-event.urgent  { background:#fee2e2; border-color:#ef4444; }
.calendar-event.warning { background:#fef3c7; border-color:#f59e0b; }
.calendar-event.normal  { background:#f0fdf4; border-color:#10b981; }
.template-card {
    background:#fff; border:1px solid #e2e8f0; border-radius:.75rem;
    padding:1rem; margin-bottom:1rem; transition:all .2s ease;
}
.template-card:hover { box-shadow:0 4px 12px rgba(0,0,0,.1); }
#MainMenu {visibility:hidden;}
footer    {visibility:hidden;}
.stTabs [data-baseweb="tab-list"] { gap:.5rem; }
.stTabs [data-baseweb="tab"]      { border-radius:.5rem; padding:.5rem 1rem; font-weight:600; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)


# ── Templates ────────────────────────────────────────────────────────────────
DEFAULT_TEMPLATES: list[dict[str, str]] = [
    {
        "id": "1",
        "name": "Employment Contract",
        "category": "Corporate",
        "content": (
            "EMPLOYMENT CONTRACT\n\n"
            "This Employment Contract is made on [DATE] between:\n\n"
            "1. [EMPLOYER NAME] (hereinafter called \"the Employer\")\n"
            "   Address: [EMPLOYER ADDRESS]\n"
            "   RC Number: [REGISTRATION NUMBER]\n\n"
            "2. [EMPLOYEE NAME] (hereinafter called \"the Employee\")\n"
            "   Address: [EMPLOYEE ADDRESS]\n\n"
            "TERMS AND CONDITIONS:\n\n"
            "1. POSITION AND DUTIES\n"
            "The Employee is employed as [JOB TITLE] and shall perform such duties as may be assigned.\n\n"
            "2. COMMENCEMENT DATE\n"
            "Employment shall commence on [START DATE].\n\n"
            "3. PROBATION PERIOD\n"
            "The Employee shall be on probation for a period of [PERIOD] months.\n\n"
            "4. REMUNERATION\n"
            "The Employee shall receive a monthly salary of N[AMOUNT] payable on [DATE] of each month.\n\n"
            "5. WORKING HOURS\n"
            "Normal working hours shall be [HOURS] per week, Monday to Friday.\n\n"
            "6. LEAVE ENTITLEMENT\n"
            "The Employee shall be entitled to [NUMBER] working days annual leave.\n\n"
            "7. TERMINATION\n"
            "Either party may terminate this contract by giving [NOTICE PERIOD] notice in writing.\n\n"
            "8. CONFIDENTIALITY\n"
            "The Employee agrees to maintain confidentiality of all company information.\n\n"
            "9. GOVERNING LAW\n"
            "This contract shall be governed by the Labour Act of Nigeria and other applicable laws.\n\n"
            "SIGNED:\n"
            "_____________________ _____________________\n"
            "Employer              Employee\n"
            "Date:                 Date:\n"
        ),
    },
    {
        "id": "2",
        "name": "Tenancy Agreement",
        "category": "Property",
        "content": (
            "TENANCY AGREEMENT\n\n"
            "This Agreement is made on [DATE] BETWEEN:\n\n"
            "[LANDLORD NAME] of [LANDLORD ADDRESS] (hereinafter called \"the Landlord\")\n\n"
            "AND\n\n"
            "[TENANT NAME] of [TENANT ADDRESS] (hereinafter called \"the Tenant\")\n\n"
            "WHEREBY IT IS AGREED AS FOLLOWS:\n\n"
            "1. PREMISES\nThe Landlord agrees to let and the Tenant agrees to take the property known as: [PROPERTY ADDRESS]\n\n"
            "2. TERM\nThe tenancy shall be for a period of [DURATION] commencing from [START DATE].\n\n"
            "3. RENT\nThe rent shall be N[AMOUNT] per [PERIOD], payable in advance on [DATE].\n\n"
            "4. SECURITY DEPOSIT\nThe Tenant shall pay a security deposit of N[AMOUNT] refundable at the end of tenancy.\n\n"
            "5. USE OF PREMISES\nThe premises shall be used solely for [residential/commercial] purposes.\n\n"
            "6. MAINTENANCE\nThe Tenant shall keep the premises in good and tenantable condition.\n\n"
            "7. ALTERATIONS\nNo structural alterations shall be made without the Landlord's written consent.\n\n"
            "8. ASSIGNMENT\nThe Tenant shall not assign or sublet without the Landlord's written consent.\n\n"
            "9. TERMINATION\nEither party may terminate by giving [NOTICE PERIOD] notice in writing.\n\n"
            "10. GOVERNING LAW\nThis agreement shall be governed by the Lagos State Tenancy Law (or applicable state law).\n\n"
            "SIGNED:\n"
            "_____________________ _____________________\n"
            "Landlord              Tenant\n"
            "Date:                 Date:\n\n"
            "WITNESS:\nName: _____________________\nAddress: __________________\nSignature: ________________\n"
        ),
    },
    {
        "id": "3",
        "name": "Power of Attorney",
        "category": "Litigation",
        "content": (
            "GENERAL POWER OF ATTORNEY\n\n"
            "KNOW ALL MEN BY THESE PRESENTS:\n\n"
            "I, [GRANTOR NAME], of [ADDRESS], [OCCUPATION], do hereby appoint "
            "[ATTORNEY NAME] of [ATTORNEY ADDRESS] as my true and lawful Attorney "
            "to act for me and on my behalf in the following matters:\n\n"
            "POWERS GRANTED:\n\n"
            "1. To demand, sue for, recover, collect, and receive all sums of money, "
            "debts, dues, and demands whatsoever which are now or shall hereafter become due.\n\n"
            "2. To sign, execute, and deliver all contracts, agreements, and documents.\n\n"
            "3. To appear before any court, tribunal, or authority and to institute, "
            "prosecute, defend, or settle any legal proceedings.\n\n"
            "4. To operate my bank accounts and perform banking transactions.\n\n"
            "5. To manage my properties and collect rents.\n\n"
            "6. To execute and register any deed or document.\n\n"
            "AND I HEREBY DECLARE that this Power of Attorney shall remain in force "
            "until revoked by me in writing.\n\n"
            "IN WITNESS WHEREOF, I have hereunto set my hand this [DATE].\n\n"
            "_____________________\n[GRANTOR NAME]\n\n"
            "SIGNED AND DELIVERED by the above named in the presence of:\n\n"
            "Name: _____________________\nAddress: __________________\n"
            "Occupation: _______________\nSignature: ________________\n"
        ),
    },
    {
        "id": "4",
        "name": "Written Address",
        "category": "Litigation",
        "content": (
            "IN THE [COURT NAME]\nIN THE [JUDICIAL DIVISION]\nHOLDEN AT [LOCATION]\n\n"
            "SUIT NO: [NUMBER]\n\nBETWEEN:\n\n"
            "[PLAINTIFF NAME] ........................... PLAINTIFF/APPLICANT\n\nAND\n\n"
            "[DEFENDANT NAME] ........................... DEFENDANT/RESPONDENT\n\n"
            "WRITTEN ADDRESS OF THE [PLAINTIFF/DEFENDANT]\n\n"
            "MAY IT PLEASE THIS HONOURABLE COURT:\n\n"
            "1.0 INTRODUCTION\n1.1 This Written Address is filed pursuant to the Rules of this Honourable Court.\n"
            "1.2 [Brief background of the matter]\n\n"
            "2.0 FACTS OF THE CASE\n2.1 [Detailed facts]\n2.2 [Chronological narration]\n\n"
            "3.0 ISSUES FOR DETERMINATION\n3.1 Whether [First Issue]\n3.2 Whether [Second Issue]\n\n"
            "4.0 ARGUMENTS\n4.1 ON ISSUE ONE\n[Detailed legal arguments with authorities]\n"
            "4.2 ON ISSUE TWO\n[Detailed legal arguments with authorities]\n\n"
            "5.0 CONCLUSION\n5.1 Based on the foregoing submissions, it is humbly urged that this Honourable Court:\n"
            "(a) [Prayer 1]\n(b) [Prayer 2]\n(c) [Any other order]\n\n"
            "Dated this [DATE]\n\n_____________________\n[COUNSEL NAME]\n[Law Firm Name]\n"
            "[Address]\n[Phone Number]\n[Email]\n\nCounsel to the [Plaintiff/Defendant]\n"
        ),
    },
    {
        "id": "5",
        "name": "Affidavit",
        "category": "Litigation",
        "content": (
            "IN THE [COURT NAME]\nIN THE [JUDICIAL DIVISION]\nHOLDEN AT [LOCATION]\n\n"
            "SUIT NO: [NUMBER]\n\nBETWEEN:\n\n"
            "[PLAINTIFF NAME] ........................... PLAINTIFF/APPLICANT\n\nAND\n\n"
            "[DEFENDANT NAME] ........................... DEFENDANT/RESPONDENT\n\n"
            "AFFIDAVIT IN SUPPORT OF [MOTION/APPLICATION]\n\n"
            "I, [DEPONENT NAME], [Gender], [Religion], Nigerian citizen, of [ADDRESS], "
            "[OCCUPATION], do hereby make oath and state as follows:\n\n"
            "1. That I am the [Plaintiff/Defendant/Applicant] in this suit and by virtue "
            "of my position, I am familiar with the facts of this case.\n\n"
            "2. That I have the authority and consent of the [Party] to depose to this Affidavit.\n\n"
            "3. That [State first fact].\n\n4. That [State second fact].\n\n"
            "5. That [Continue with numbered paragraphs].\n\n"
            "6. That I make this Affidavit in good faith and in support of the [Motion/Application].\n\n"
            "7. That I verily believe the facts stated herein to be true and correct to the best "
            "of my knowledge, information, and belief.\n\n"
            "_____________________\nDEPONENT\n\n"
            "SWORN TO at the [Court Registry] at [Location] this [DATE]\n\n"
            "BEFORE ME:\n_____________________\nCOMMISSIONER FOR OATHS\n"
        ),
    },
    {
        "id": "6",
        "name": "Legal Opinion",
        "category": "Corporate",
        "content": (
            "LEGAL OPINION\n\nPRIVATE AND CONFIDENTIAL\nPRIVILEGED COMMUNICATION\n\n"
            "TO: [CLIENT NAME]\n[CLIENT ADDRESS]\n\n"
            "FROM: [LAW FIRM NAME]\n[LAW FIRM ADDRESS]\n\nDATE: [DATE]\n\n"
            "RE: [SUBJECT MATTER]\n\n"
            "1.0 INTRODUCTION\nWe have been instructed to provide a legal opinion on [subject matter]. "
            "This opinion is based on the facts and documents provided to us and the applicable laws "
            "of the Federal Republic of Nigeria.\n\n"
            "2.0 BACKGROUND FACTS\n[Detailed background of the matter]\n\n"
            "3.0 ISSUES FOR CONSIDERATION\n3.1 [First Issue]\n3.2 [Second Issue]\n3.3 [Third Issue]\n\n"
            "4.0 APPLICABLE LEGAL FRAMEWORK\n4.1 [Relevant Statutes]\n4.2 [Relevant Regulations]\n"
            "4.3 [Relevant Case Law]\n\n"
            "5.0 ANALYSIS\n5.1 On the First Issue\n[Detailed legal analysis]\n"
            "5.2 On the Second Issue\n[Detailed legal analysis]\n"
            "5.3 On the Third Issue\n[Detailed legal analysis]\n\n"
            "6.0 CONCLUSION AND RECOMMENDATIONS\nBased on our analysis:\n"
            "6.1 [First Conclusion]\n6.2 [Second Conclusion]\n6.3 [Recommendations]\n\n"
            "7.0 CAVEATS\nThis opinion is:\n"
            "- Based solely on Nigerian law as at the date hereof\n"
            "- Based on the facts and documents provided to us\n"
            "- For the sole use of the addressee\n"
            "- Not to be relied upon by any third party\n\n"
            "Yours faithfully,\n\n_____________________\n[PARTNER NAME]\nFor: [LAW FIRM NAME]\n"
        ),
    },
    {
        "id": "7",
        "name": "Demand Letter",
        "category": "Litigation",
        "content": (
            "[LAW FIRM LETTERHEAD]\n\n[DATE]\n\nBY HAND/REGISTERED POST/EMAIL\n\n"
            "[RECIPIENT NAME]\n[RECIPIENT ADDRESS]\n\nDear Sir/Madam,\n\n"
            "RE: DEMAND FOR PAYMENT OF THE SUM OF N[AMOUNT] BEING [DESCRIPTION OF DEBT]\n\n"
            "OUR CLIENT: [CLIENT NAME]\n\n"
            "We are Solicitors to [CLIENT NAME] (hereinafter referred to as \"our Client\") "
            "on whose behalf and instruction we write you this letter.\n\n"
            "Our Client has instructed us on the following facts:\n\n"
            "1. [State the background facts]\n2. [State the obligation/agreement]\n"
            "3. [State the breach/default]\n\n"
            "By virtue of the foregoing, you are indebted to our Client in the sum of N[AMOUNT] "
            "being [description].\n\n"
            "Despite several demands, you have failed, refused, and/or neglected to pay the said sum.\n\n"
            "TAKE NOTICE that unless you pay the sum of N[AMOUNT] to our Client within SEVEN (7) DAYS "
            "of your receipt of this letter, we shall have no option but to institute legal proceedings "
            "against you without further notice.\n\n"
            "Please be advised that in addition to the principal sum, our Client shall seek:\n"
            "(a) Interest at [RATE]% per annum\n(b) Cost of legal proceedings\n(c) General damages\n\n"
            "Govern yourself accordingly.\n\nYours faithfully,\n\n_____________________\n[COUNSEL NAME]\n"
            "For: [LAW FIRM NAME]\n\nc.c: Our Client\n"
        ),
    },
    {
        "id": "8",
        "name": "Board Resolution",
        "category": "Corporate",
        "content": (
            "CERTIFIED TRUE COPY OF RESOLUTION PASSED AT A MEETING OF THE BOARD OF DIRECTORS "
            "OF [COMPANY NAME] (RC: [REGISTRATION NUMBER]) HELD AT [VENUE] ON [DATE] AT [TIME]\n\n"
            "PRESENT:\n1. [NAME] - Chairman\n2. [NAME] - Director\n3. [NAME] - Director\n\n"
            "IN ATTENDANCE:\n[NAME] - Company Secretary\n\n"
            "RESOLUTION [NUMBER]\n\n[TITLE OF RESOLUTION]\n\n"
            "WHEREAS:\nA. [Recital/Background]\nB. [Reason for Resolution]\n\n"
            "IT WAS RESOLVED THAT:\n"
            "1. [First Resolution]\n2. [Second Resolution]\n"
            "3. That any Director of the Company be and is hereby authorized to execute all "
            "documents and do all things necessary to give effect to this Resolution.\n"
            "4. That the Company Secretary be and is hereby directed to file the necessary "
            "returns with the Corporate Affairs Commission.\n\n"
            "CERTIFIED TRUE COPY\n\n_____________________\n[NAME]\nCompany Secretary\n\n"
            "Date: [DATE]\n\nCompany Seal:\n"
        ),
    },
]


# ── Helper Functions ─────────────────────────────────────────────────────────
def generate_id() -> str:
    return uuid.uuid4().hex[:8]


def format_currency(amount: float) -> str:
    return f"₦{amount:,.2f}"


def format_date(date_str: str) -> str:
    try:
        return datetime.fromisoformat(date_str).strftime("%B %d, %Y")
    except (ValueError, TypeError):
        return str(date_str)


def get_days_until(date_str: str) -> int:
    try:
        target = datetime.fromisoformat(date_str).date()
        return (target - datetime.now().date()).days
    except (ValueError, TypeError):
        return 999


def get_relative_date(date_str: str) -> str:
    days = get_days_until(date_str)
    if days == 0:
        return "Today"
    if days == 1:
        return "Tomorrow"
    if days == -1:
        return "Yesterday"
    if 0 < days <= 7:
        return f"In {days} days"
    if -7 <= days < 0:
        return f"{abs(days)} days ago"
    return format_date(date_str)


def safe_html(text: str) -> str:
    """Escape text for safe rendering inside HTML blocks."""
    return html.escape(str(text))


# ── Session State ────────────────────────────────────────────────────────────
_SESSION_DEFAULTS: dict[str, Any] = {
    "api_key": "",
    "api_configured": False,
    "cases": [],
    "clients": [],
    "time_entries": [],
    "invoices": [],
    "last_response": "",
    "selected_task_type": "general",
    "gemini_model": normalize_model_name(DEFAULT_MODEL),
    "loaded_template": "",
}


def init_session_state() -> None:
    for key, default in _SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


init_session_state()


# ── Gemini API Layer ─────────────────────────────────────────────────────────
def _configure_transport(api_key: str) -> None:
    """Configure the genai module with REST transport (avoids gRPC issues on Streamlit Cloud)."""
    genai.configure(api_key=api_key, transport="rest")


def validate_api_key(key: str) -> bool:
    """Basic format check before hitting the network."""
    cleaned = key.strip()
    return bool(cleaned) and len(cleaned) >= 10 and cleaned.isascii()


def configure_gemini(api_key: str, model_name: Optional[str] = None) -> bool:
    """Validate the API key by sending a lightweight probe request."""
    selected = normalize_model_name(model_name or DEFAULT_MODEL)
    try:
        _configure_transport(api_key)
        model = genai.GenerativeModel(selected)
        model.generate_content(
            "Respond with exactly: OK",
            generation_config={"max_output_tokens": 16},
        )
        st.session_state.api_configured = True
        st.session_state.api_key = api_key
        st.session_state.gemini_model = selected
        logger.info("Gemini API configured successfully with model %s", selected)
        return True
    except Exception as exc:
        logger.error("API configuration failed: %s", exc)
        _surface_api_error(exc)
        return False


def _surface_api_error(exc: Exception) -> None:
    """Show a user-friendly Streamlit error based on common API error codes."""
    msg = str(exc)
    st.error(f"API error: {msg}")
    if "403" in msg:
        st.warning("The API key appears invalid or lacks permission. "
                    "Verify it at https://aistudio.google.com/app/apikey")
    elif "429" in msg:
        st.warning("Rate limit exceeded. Wait a moment and try again.")
    elif "503" in msg or "504" in msg:
        st.warning("Google's servers are temporarily overloaded. Try again shortly.")


def check_available_models(api_key: str) -> None:
    """List models available under the given API key (debugging helper)."""
    try:
        _configure_transport(api_key)
        models = genai.list_models()
        available = [
            m.name.replace("models/", "")
            for m in models
            if "generateContent" in m.supported_generation_methods
        ]
        if available:
            with st.expander("Available Gemini Models"):
                for name in available:
                    marker = " ⚠️ deprecated" if name in MODEL_MIGRATION_MAP else ""
                    st.code(f"{name}{marker}")
        else:
            st.warning("No generateContent-capable models found for this key.")
    except Exception as exc:
        st.error(f"Could not list models: {exc}")


@with_retry(max_attempts=2, base_delay=1.5)
def _call_gemini(
    prompt: str,
    system_instruction: str,
) -> str:
    """Low-level Gemini call with retry logic."""
    _configure_transport(st.session_state.api_key)
    model = genai.GenerativeModel(
        model_name=get_active_model(),
        system_instruction=system_instruction,
    )
    response = model.generate_content(
        prompt,
        generation_config=GENERATION_CONFIG,
    )
    return response.text


def generate_legal_response(prompt: str, task_type: str) -> str:
    if not st.session_state.api_configured:
        return "⚠️ Please configure your Gemini API key first."
    task_label = TASK_TYPES.get(task_type, {}).get("label", "General Query")
    user_content = f"[Task Type: {task_label}]\n\n{prompt}"
    try:
        return _call_gemini(user_content, SYSTEM_INSTRUCTION)
    except Exception as exc:
        logger.error("generate_legal_response failed: %s", exc)
        return f"Error generating response: {exc}"


def conduct_legal_research(query: str) -> str:
    if not st.session_state.api_configured:
        return "⚠️ Please configure your Gemini API key first."
    try:
        return _call_gemini(query, RESEARCH_INSTRUCTION)
    except Exception as exc:
        logger.error("conduct_legal_research failed: %s", exc)
        return f"Error conducting research: {exc}"


# ── Data CRUD ────────────────────────────────────────────────────────────────
def add_case(data: dict[str, Any]) -> dict[str, Any]:
    data["id"] = generate_id()
    data["created_at"] = datetime.now().isoformat()
    st.session_state.cases.append(data)
    return data


def update_case(case_id: str, updates: dict[str, Any]) -> bool:
    for case in st.session_state.cases:
        if case["id"] == case_id:
            case.update(updates)
            case["updated_at"] = datetime.now().isoformat()
            return True
    return False


def delete_case(case_id: str) -> None:
    st.session_state.cases = [c for c in st.session_state.cases if c["id"] != case_id]


def add_client(data: dict[str, Any]) -> dict[str, Any]:
    data["id"] = generate_id()
    data["created_at"] = datetime.now().isoformat()
    st.session_state.clients.append(data)
    return data


def delete_client(client_id: str) -> None:
    st.session_state.clients = [c for c in st.session_state.clients if c["id"] != client_id]


def get_client_name(client_id: str) -> str:
    for c in st.session_state.clients:
        if c["id"] == client_id:
            return c["name"]
    return "Unknown Client"


def add_time_entry(data: dict[str, Any]) -> dict[str, Any]:
    data["id"] = generate_id()
    data["created_at"] = datetime.now().isoformat()
    data["amount"] = data["hours"] * data["rate"]
    st.session_state.time_entries.append(data)
    return data


def delete_time_entry(entry_id: str) -> None:
    st.session_state.time_entries = [
        e for e in st.session_state.time_entries if e["id"] != entry_id
    ]


def generate_invoice(client_id: str) -> Optional[dict[str, Any]]:
    entries = [e for e in st.session_state.time_entries if e.get("client_id") == client_id]
    if not entries:
        return None
    total = sum(e["amount"] for e in entries)
    invoice: dict[str, Any] = {
        "id": generate_id(),
        "invoice_no": f"INV-{datetime.now().strftime('%Y%m%d')}-{generate_id()[:4].upper()}",
        "client_id": client_id,
        "client_name": get_client_name(client_id),
        "entries": entries,
        "total": total,
        "date": datetime.now().isoformat(),
        "status": "Draft",
    }
    st.session_state.invoices.append(invoice)
    return invoice


# ── Aggregate Queries ────────────────────────────────────────────────────────
def get_total_billable() -> float:
    return sum(e.get("amount", 0) for e in st.session_state.time_entries)


def get_total_hours() -> float:
    return sum(e.get("hours", 0) for e in st.session_state.time_entries)


def get_client_billable(client_id: str) -> float:
    return sum(
        e.get("amount", 0)
        for e in st.session_state.time_entries
        if e.get("client_id") == client_id
    )


def get_client_case_count(client_id: str) -> int:
    return sum(1 for c in st.session_state.cases if c.get("client_id") == client_id)


def get_upcoming_hearings(limit: int = 10) -> list[dict[str, Any]]:
    hearings = [
        {
            "case_id": c["id"],
            "case_title": c["title"],
            "date": c["next_hearing"],
            "court": c.get("court", ""),
            "suit_no": c.get("suit_no", ""),
        }
        for c in st.session_state.cases
        if c.get("next_hearing") and c.get("status") == "Active"
    ]
    hearings.sort(key=lambda h: h["date"])
    return hearings[:limit]


# ── UI: Header & Stats ──────────────────────────────────────────────────────
def render_header() -> None:
    st.markdown(
        '<div class="main-header">'
        "<h1>⚖️ LexiAssist</h1>"
        "<p>AI-Powered Legal Practice Management for Nigerian Lawyers · Google Gemini</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_stats() -> None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="stat-card"><div class="stat-value">{len(st.session_state.cases)}</div>'
            '<div class="stat-label">📁 Active Cases</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="stat-card blue"><div class="stat-value">{len(st.session_state.clients)}</div>'
            '<div class="stat-label">👥 Clients</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="stat-card purple"><div class="stat-value">{safe_html(format_currency(get_total_billable()))}</div>'
            '<div class="stat-label">💰 Billable</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="stat-card amber"><div class="stat-value">{len(get_upcoming_hearings())}</div>'
            '<div class="stat-label">📅 Upcoming Hearings</div></div>',
            unsafe_allow_html=True,
        )


# ── UI: Sidebar ──────────────────────────────────────────────────────────────
def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")

        # -- API Key ----------------------------------------------------------
        st.markdown("#### 🔑 Gemini API Key")
        api_key_input = st.text_input(
            "Enter your API key",
            type="password",
            value=st.session_state.api_key,
            help="Get your key from https://aistudio.google.com/app/apikey",
        )

        current = get_active_model()
        idx = SUPPORTED_MODELS.index(current) if current in SUPPORTED_MODELS else 0
        selected_model = st.selectbox(
            "Gemini model",
            SUPPORTED_MODELS,
            index=idx,
            help="Gemini 2.0 models retire June 2026. Use 2.5 models.",
        )
        st.session_state.gemini_model = normalize_model_name(selected_model)

        if st.button("Configure API", type="primary"):
            if api_key_input and validate_api_key(api_key_input):
                with st.spinner("Validating API key (REST transport)…"):
                    if configure_gemini(api_key_input.strip(), st.session_state.gemini_model):
                        st.success("✅ API configured!")
                        check_available_models(api_key_input.strip())
                    else:
                        st.error("❌ Configuration failed.")
            else:
                st.warning("Please enter a valid API key.")

        if st.session_state.api_configured:
            st.success("✅ API ready")
            st.caption(f"Model: `{get_active_model()}`")
        else:
            st.warning("⚠️ API not configured")

        st.markdown(
            "**Get your free API key:**\n"
            "1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)\n"
            "2. Sign in with Google\n"
            "3. Create an API key\n"
            "4. Paste it above"
        )

        st.divider()

        # -- Data Management ---------------------------------------------------
        st.markdown("#### 💾 Data Management")
        if st.button("📥 Export All Data"):
            payload = {
                "cases": st.session_state.cases,
                "clients": st.session_state.clients,
                "time_entries": st.session_state.time_entries,
                "invoices": st.session_state.invoices,
                "exported_at": datetime.now().isoformat(),
            }
            st.download_button(
                "Download JSON",
                data=json.dumps(payload, indent=2),
                file_name=f"lexiassist_backup_{datetime.now():%Y%m%d}.json",
                mime="application/json",
            )

        uploaded = st.file_uploader("📤 Import Data", type=["json"])
        if uploaded is not None:
            try:
                data = json.load(uploaded)
                st.session_state.cases = data.get("cases", [])
                st.session_state.clients = data.get("clients", [])
                st.session_state.time_entries = data.get("time_entries", [])
                st.session_state.invoices = data.get("invoices", [])
                st.success("Data imported!")
                st.rerun()
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                st.error(f"Import failed: {exc}")

        st.divider()

        # -- Quick Actions -----------------------------------------------------
        st.markdown("#### ⚡ Quick Actions")
        if st.button("➕ New Case", use_container_width=True):
            st.session_state.current_tab = "Cases"
            st.rerun()
        if st.button("👤 New Client", use_container_width=True):
            st.session_state.current_tab = "Clients"
            st.rerun()
        if st.button("⏱️ Log Time", use_container_width=True):
            st.session_state.current_tab = "Billing"
            st.rerun()

        st.divider()
        st.markdown(
            "#### ℹ️ About\n\n"
            "**LexiAssist v2.0**\n\n"
            "AI-Powered Legal Practice Management designed for Nigerian Lawyers.\n\n"
            "Built with 🤖 Google Gemini · 🎈 Streamlit · 🐍 Python\n\n"
            "© 2026 LexiAssist"
        )


# ── Page: AI Assistant ───────────────────────────────────────────────────────
def render_ai_assistant() -> None:
    st.markdown("### 🤖 AI Legal Assistant")
    st.markdown("Get AI-powered assistance with legal drafting, analysis, and research.")

    # Task type selector
    st.markdown("#### Select Task Type")
    cols = st.columns(3)
    for i, (key, task) in enumerate(TASK_TYPES.items()):
        with cols[i % 3]:
            is_selected = st.session_state.selected_task_type == key
            if st.button(
                f"{task['icon']} {task['label'].split(' ', 1)[1]}\n\n{task['description']}",
                key=f"task_{key}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.selected_task_type = key
                st.rerun()

    st.markdown("---")

    # Pre-populate from loaded template
    default_text = st.session_state.pop("loaded_template", "")

    st.markdown("#### Describe Your Legal Task or Query")
    user_input = st.text_area(
        "Enter your query",
        value=default_text,
        height=200,
        placeholder=(
            "Example: Draft a lease agreement for commercial property "
            "in Lagos with 2-year term and rent review clause…"
        ),
        label_visibility="collapsed",
    )

    c1, c2 = st.columns([3, 1])
    with c1:
        gen_disabled = not st.session_state.api_configured
        if st.button(
            "✨ Generate Legal Response",
            type="primary",
            use_container_width=True,
            disabled=gen_disabled,
        ):
            if user_input.strip():
                with st.spinner("Generating response…"):
                    result = generate_legal_response(
                        user_input, st.session_state.selected_task_type
                    )
                    if not result.startswith("Error"):
                        st.session_state.last_response = result
                    else:
                        st.error(result)
            else:
                st.warning("Please enter your legal query or task.")
    with c2:
        if st.button("📋 Use Template", use_container_width=True):
            st.session_state.current_tab = "Templates"
            st.rerun()

    if not st.session_state.api_configured:
        st.info("⚠️ Configure your Gemini API key in the sidebar to use the AI assistant.")

    # Display response
    if st.session_state.last_response:
        st.markdown("---")
        st.markdown("#### 📄 LexiAssist Response")
        c1, c2, c3 = st.columns([1, 1, 4])
        with c1:
            st.download_button(
                "📥 TXT",
                data=st.session_state.last_response,
                file_name=f"LexiAssist_{datetime.now():%Y%m%d_%H%M}.txt",
                mime="text/plain",
            )
        with c2:
            escaped_body = safe_html(st.session_state.last_response)
            html_doc = (
                "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
                "<title>LexiAssist Document</title>"
                "<style>body{font-family:Georgia,serif;line-height:1.8;"
                "max-width:800px;margin:40px auto;padding:20px}"
                "h1{color:#059669;border-bottom:3px solid #059669;padding-bottom:12px}"
                ".content{white-space:pre-wrap}"
                ".disclaimer{background:#fef3c7;border-left:4px solid #f59e0b;padding:16px;margin-top:32px}"
                ".footer{text-align:center;margin-top:32px;color:#64748b;font-size:12px}"
                "</style></head><body>"
                "<h1>⚖️ LexiAssist Legal Document</h1>"
                f'<div class="content">{escaped_body}</div>'
                '<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> '
                "This document is for informational purposes only.</div>"
                f'<div class="footer"><p>Generated {datetime.now():%B %d, %Y at %I:%M %p}</p></div>'
                "</body></html>"
            )
            st.download_button(
                "📥 HTML",
                data=html_doc,
                file_name=f"LexiAssist_{datetime.now():%Y%m%d_%H%M}.html",
                mime="text/html",
            )

        st.markdown(
            f'<div class="response-box">{safe_html(st.session_state.last_response)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="disclaimer"><strong>⚖️ Professional Disclaimer:</strong> '
            "This response is for informational purposes only and does not constitute "
            "legal advice. All legal work should be reviewed by a qualified Nigerian lawyer.</div>",
            unsafe_allow_html=True,
        )


# ── Page: Research ───────────────────────────────────────────────────────────
def render_research() -> None:
    st.markdown("### 📚 Legal Research")
    st.markdown("AI-powered legal research for Nigerian law.")

    query = st.text_input(
        "Research Query",
        placeholder="E.g., 'breach of contract remedies Nigeria' or 'landlord tenant rights Lagos'",
        label_visibility="collapsed",
    )
    if st.button("🔍 Conduct Research", type="primary", disabled=not st.session_state.api_configured):
        if query.strip():
            with st.spinner("Researching…"):
                st.session_state["research_results"] = conduct_legal_research(query)
        else:
            st.warning("Please enter a research query.")

    if not st.session_state.api_configured:
        st.info("⚠️ Configure your Gemini API key in the sidebar to use legal research.")

    results = st.session_state.get("research_results", "")
    if results:
        st.markdown("---")
        st.markdown("#### 📋 Research Results")
        st.download_button(
            "📥 Export",
            data=results,
            file_name=f"Legal_Research_{datetime.now():%Y%m%d_%H%M}.txt",
            mime="text/plain",
        )
        st.markdown(
            f'<div class="response-box">{safe_html(results)}</div>',
            unsafe_allow_html=True,
        )


# ── Page: Cases ──────────────────────────────────────────────────────────────
def render_cases() -> None:
    st.markdown("### 📁 Case Management")

    with st.expander("➕ Add New Case", expanded=False):
        with st.form("add_case_form"):
            c1, c2 = st.columns(2)
            with c1:
                title = st.text_input("Case Title *", placeholder="John Doe v. State")
                suit_no = st.text_input("Suit Number *", placeholder="FHC/L/CS/123/2024")
                court = st.text_input("Court", placeholder="Federal High Court, Lagos")
            with c2:
                next_hearing = st.date_input("Next Hearing Date")
                status = st.selectbox("Status", CASE_STATUSES)
                client_names = ["— Select Client —"] + [c["name"] for c in st.session_state.clients]
                client_idx = st.selectbox(
                    "Client", range(len(client_names)), format_func=lambda i: client_names[i]
                )
            notes = st.text_area("Notes", placeholder="Additional case notes…")

            if st.form_submit_button("Save Case", type="primary"):
                if title.strip() and suit_no.strip():
                    cid = (
                        st.session_state.clients[client_idx - 1]["id"]
                        if client_idx > 0
                        else None
                    )
                    add_case(
                        {
                            "title": title.strip(),
                            "suit_no": suit_no.strip(),
                            "court": court.strip(),
                            "next_hearing": next_hearing.isoformat() if next_hearing else None,
                            "status": status,
                            "client_id": cid,
                            "notes": notes.strip(),
                        }
                    )
                    st.success("✅ Case added!")
                    st.rerun()
                else:
                    st.error("Title and Suit Number are required.")

    st.markdown("#### 🔍 Filter Cases")
    filter_status = st.selectbox("Filter by Status", ["All"] + CASE_STATUSES)
    filtered = (
        st.session_state.cases
        if filter_status == "All"
        else [c for c in st.session_state.cases if c.get("status") == filter_status]
    )

    if not filtered:
        st.info("📁 No cases found. Add your first case above!")
        return

    for case in filtered:
        badge_class = {
            "Active": "success",
            "Pending": "warning",
            "Completed": "info",
            "Archived": "",
        }.get(case.get("status", ""), "")

        hearing_html = ""
        if case.get("next_hearing"):
            hearing_html = (
                f"<p><strong>Next Hearing:</strong> {safe_html(format_date(case['next_hearing']))} "
                f"({safe_html(get_relative_date(case['next_hearing']))})</p>"
            )
        notes_html = f"<p><em>{safe_html(case['notes'])}</em></p>" if case.get("notes") else ""

        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(
                f'<div class="custom-card">'
                f'<h4>{safe_html(case["title"])} '
                f'<span class="badge badge-{badge_class}">{safe_html(case.get("status", ""))}</span></h4>'
                f'<p><strong>Suit No:</strong> {safe_html(case.get("suit_no", "N/A"))}</p>'
                f'<p><strong>Court:</strong> {safe_html(case.get("court", "N/A"))}</p>'
                f'<p><strong>Client:</strong> {safe_html(get_client_name(case.get("client_id", "")))}</p>'
                f"{hearing_html}{notes_html}</div>",
                unsafe_allow_html=True,
            )
        with c2:
            current_idx = (
                CASE_STATUSES.index(case["status"])
                if case.get("status") in CASE_STATUSES
                else 0
            )
            new_status = st.selectbox(
                "Status",
                CASE_STATUSES,
                index=current_idx,
                key=f"status_{case['id']}",
                label_visibility="collapsed",
            )
            if new_status != case.get("status"):
                update_case(case["id"], {"status": new_status})
                st.rerun()
            if st.button("🗑️", key=f"del_{case['id']}", help="Delete case"):
                delete_case(case["id"])
                st.rerun()


# ── Page: Calendar ───────────────────────────────────────────────────────────
def render_calendar() -> None:
    st.markdown("### 📅 Court Calendar")
    hearings = get_upcoming_hearings()

    if hearings:
        st.markdown("#### Upcoming Hearings")
        for h in hearings:
            days = get_days_until(h["date"])
            if days <= 3:
                urgency, badge = "urgent", "danger"
            elif days <= 7:
                urgency, badge = "warning", "warning"
            else:
                urgency, badge = "normal", "success"
            st.markdown(
                f'<div class="calendar-event {urgency}">'
                f"<h4>{safe_html(h['case_title'])}</h4>"
                f"<p><strong>Suit No:</strong> {safe_html(h['suit_no'])}</p>"
                f"<p><strong>Court:</strong> {safe_html(h['court'])}</p>"
                f'<p><strong>Date:</strong> {safe_html(format_date(h["date"]))} '
                f'<span class="badge badge-{badge}">{safe_html(get_relative_date(h["date"]))}</span></p>'
                "</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("#### 📊 Hearing Timeline")
        chart_data = [
            {
                "Case": h["case_title"],
                "Days Until Hearing": max(get_days_until(h["date"]), 0),
                "Date": format_date(h["date"]),
            }
            for h in hearings
        ]
        df = pd.DataFrame(chart_data)
        fig = px.bar(
            df,
            x="Days Until Hearing",
            y="Case",
            orientation="h",
            text="Date",
            color="Days Until Hearing",
            color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
            title="Days Until Upcoming Hearings",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📅 No upcoming hearings. Add hearing dates to your active cases.")

    st.markdown("---")
    st.markdown(
        '<div class="custom-card">'
        "<h4>📌 Calendar Legend</h4>"
        '<p><span class="badge badge-danger">Red</span> — Within 3 days (urgent)</p>'
        '<p><span class="badge badge-warning">Yellow</span> — Within 7 days</p>'
        '<p><span class="badge badge-success">Green</span> — Future hearings</p>'
        "</div>",
        unsafe_allow_html=True,
    )


# ── Page: Templates ──────────────────────────────────────────────────────────
def render_templates() -> None:
    st.markdown("### 📋 Document Templates")
    st.markdown("Legal document templates for Nigerian practice.")

    categories = sorted({t["category"] for t in DEFAULT_TEMPLATES})
    sel_cat = st.selectbox("Filter by Category", ["All"] + categories)
    templates = (
        DEFAULT_TEMPLATES
        if sel_cat == "All"
        else [t for t in DEFAULT_TEMPLATES if t["category"] == sel_cat]
    )

    cols = st.columns(2)
    for i, tmpl in enumerate(templates):
        with cols[i % 2]:
            st.markdown(
                f'<div class="template-card">'
                f"<h4>📄 {safe_html(tmpl['name'])}</h4>"
                f'<span class="badge badge-success">{safe_html(tmpl["category"])}</span>'
                f'<p style="margin-top:.5rem;color:#64748b;font-size:.875rem;">'
                f"{safe_html(tmpl['content'][:100])}…</p></div>",
                unsafe_allow_html=True,
            )
            tc1, tc2 = st.columns(2)
            with tc1:
                if st.button("📋 Use", key=f"use_{tmpl['id']}", use_container_width=True):
                    st.session_state.loaded_template = tmpl["content"]
                    st.success(f"Template '{tmpl['name']}' loaded into AI Assistant!")
                    st.rerun()
            with tc2:
                if st.button("👁️ Preview", key=f"prev_{tmpl['id']}", use_container_width=True):
                    st.session_state["preview_template"] = tmpl

    preview = st.session_state.get("preview_template")
    if preview:
        st.markdown("---")
        st.markdown(f"### Preview: {preview['name']}")
        st.code(preview["content"], language=None)
        pc1, pc2 = st.columns([1, 4])
        with pc1:
            if st.button("Close Preview"):
                del st.session_state["preview_template"]
                st.rerun()
        with pc2:
            st.download_button(
                "📥 Download Template",
                data=preview["content"],
                file_name=f"{preview['name'].replace(' ', '_')}.txt",
                mime="text/plain",
            )


# ── Page: Clients ────────────────────────────────────────────────────────────
def render_clients() -> None:
    st.markdown("### 👥 Client Management")

    with st.expander("➕ Add New Client", expanded=False):
        with st.form("add_client_form"):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Client Name *", placeholder="Full Name or Company")
                email = st.text_input("Email", placeholder="email@example.com")
                phone = st.text_input("Phone", placeholder="+234 xxx xxx xxxx")
            with c2:
                client_type = st.selectbox("Client Type", CLIENT_TYPES)
                address = st.text_input("Address", placeholder="Physical Address")
                notes = st.text_area("Notes", placeholder="Additional information…")
            if st.form_submit_button("Save Client", type="primary"):
                if name.strip():
                    add_client(
                        {
                            "name": name.strip(),
                            "email": email.strip(),
                            "phone": phone.strip(),
                            "type": client_type,
                            "address": address.strip(),
                            "notes": notes.strip(),
                        }
                    )
                    st.success("✅ Client added!")
                    st.rerun()
                else:
                    st.error("Please enter client name.")

    if not st.session_state.clients:
        st.info("👥 No clients yet. Add your first client above!")
        return

    cols = st.columns(2)
    for i, client in enumerate(st.session_state.clients):
        with cols[i % 2]:
            cases = get_client_case_count(client["id"])
            billable = get_client_billable(client["id"])
            email_line = f"<p>📧 {safe_html(client['email'])}</p>" if client.get("email") else ""
            phone_line = f"<p>📱 {safe_html(client['phone'])}</p>" if client.get("phone") else ""
            addr_line = f"<p>📍 {safe_html(client['address'])}</p>" if client.get("address") else ""
            st.markdown(
                f'<div class="custom-card">'
                f"<h4>{safe_html(client['name'])} "
                f'<span class="badge badge-info">{safe_html(client.get("type", "Individual"))}</span></h4>'
                f"{email_line}{phone_line}{addr_line}"
                '<hr style="margin:1rem 0">'
                '<div style="display:flex;justify-content:space-around;text-align:center">'
                f'<div><div style="font-size:1.5rem;font-weight:bold;color:#059669">{cases}</div>'
                '<div style="font-size:.75rem;color:#64748b">Cases</div></div>'
                f'<div><div style="font-size:1.5rem;font-weight:bold;color:#7c3aed">'
                f"{safe_html(format_currency(billable))}</div>"
                '<div style="font-size:.75rem;color:#64748b">Billable</div></div>'
                "</div></div>",
                unsafe_allow_html=True,
            )
            bc1, bc2 = st.columns(2)
            with bc1:
                if billable > 0 and st.button(
                    "📄 Invoice", key=f"inv_{client['id']}", use_container_width=True
                ):
                    inv = generate_invoice(client["id"])
                    if inv:
                        st.success(f"Invoice {inv['invoice_no']} generated!")
                        st.rerun()
            with bc2:
                if st.button("🗑️ Delete", key=f"delc_{client['id']}", use_container_width=True):
                    delete_client(client["id"])
                    st.rerun()


# ── Page: Billing ────────────────────────────────────────────────────────────
def render_billing() -> None:
    st.markdown("### 💰 Billing & Time Tracking")

    # Summary
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown(
            f'<div class="stat-card"><div class="stat-value">'
            f"{safe_html(format_currency(get_total_billable()))}</div>"
            f'<div class="stat-label">💰 Total Billable</div>'
            f'<div style="font-size:.75rem;color:#64748b;margin-top:.5rem">'
            f"{len(st.session_state.time_entries)} entries</div></div>",
            unsafe_allow_html=True,
        )
    with sc2:
        st.markdown(
            f'<div class="stat-card blue"><div class="stat-value">'
            f"{get_total_hours():.1f}h</div>"
            '<div class="stat-label">⏱️ Total Hours</div></div>',
            unsafe_allow_html=True,
        )
    with sc3:
        st.markdown(
            f'<div class="stat-card purple"><div class="stat-value">'
            f"{len(st.session_state.invoices)}</div>"
            '<div class="stat-label">📄 Invoices</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Time entry form
    with st.expander("⏱️ Log Time Entry", expanded=False):
        with st.form("add_time_form"):
            c1, c2 = st.columns(2)
            with c1:
                cli_names = ["— Select Client —"] + [c["name"] for c in st.session_state.clients]
                cli_idx = st.selectbox(
                    "Client *", range(len(cli_names)), format_func=lambda i: cli_names[i]
                )
                case_names = ["— Select Case (optional) —"] + [
                    c["title"] for c in st.session_state.cases
                ]
                case_idx = st.selectbox(
                    "Case", range(len(case_names)), format_func=lambda i: case_names[i]
                )
                entry_date = st.date_input("Date", value=datetime.now())
            with c2:
                hours = st.number_input("Hours *", min_value=0.25, step=0.25, value=1.0)
                rate = st.number_input("Hourly Rate (₦) *", min_value=0, value=50000, step=5000)
                st.markdown(f"**Total:** {format_currency(hours * rate)}")
            description = st.text_area("Description *", placeholder="Describe the work performed…")

            if st.form_submit_button("Save Entry", type="primary"):
                if cli_idx > 0 and description.strip():
                    add_time_entry(
                        {
                            "client_id": st.session_state.clients[cli_idx - 1]["id"],
                            "case_id": (
                                st.session_state.cases[case_idx - 1]["id"]
                                if case_idx > 0
                                else None
                            ),
                            "date": entry_date.isoformat(),
                            "hours": hours,
                            "rate": rate,
                            "description": description.strip(),
                        }
                    )
                    st.success("✅ Time entry logged!")
                    st.rerun()
                else:
                    st.error("Please select a client and enter a description.")

    # Time entries table
    st.markdown("#### 📋 Time Entries")
    if not st.session_state.time_entries:
        st.info("⏱️ No time entries yet. Log your first entry above!")
    else:
        rows = [
            {
                "Date": format_date(e["date"]),
                "Client": get_client_name(e.get("client_id", "")),
                "Description": (
                    e["description"][:50] + "…" if len(e["description"]) > 50 else e["description"]
                ),
                "Hours": f"{e['hours']}h",
                "Rate": format_currency(e["rate"]),
                "Amount": format_currency(e["amount"]),
                "ID": e["id"],
            }
            for e in reversed(st.session_state.time_entries)
        ]
        df = pd.DataFrame(rows)
        st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)
        labels = [
            f"{r['Date']} — {r['Client']} — {r['Description']}" for r in rows
        ]
        entry_to_delete = st.selectbox(
            "Select entry to delete",
            ["None"] + labels,
            key="delete_entry_select",
        )
        if entry_to_delete != "None" and st.button("🗑️ Delete Selected Entry"):
            idx = labels.index(entry_to_delete)
            delete_time_entry(rows[idx]["ID"])
            st.success("Entry deleted!")
            st.rerun()

        # Billing chart
        if len(rows) > 1:
            st.markdown("---")
            st.markdown("#### 📊 Billing Overview")
            client_totals: dict[str, float] = {}
            for entry in st.session_state.time_entries:
                cname = get_client_name(entry.get("client_id", ""))
                client_totals[cname] = client_totals.get(cname, 0) + entry["amount"]
            fig = px.pie(
                values=list(client_totals.values()),
                names=list(client_totals.keys()),
                title="Billable Amount by Client",
            )
            st.plotly_chart(fig, use_container_width=True)

    # Invoices
    if st.session_state.invoices:
        st.markdown("---")
        st.markdown("#### 📄 Generated Invoices")
        for inv in reversed(st.session_state.invoices):
            with st.expander(
                f"📄 {inv['invoice_no']} — {inv['client_name']} — {format_currency(inv['total'])}"
            ):
                st.markdown(
                    f"**Invoice Number:** {inv['invoice_no']}  \n"
                    f"**Client:** {inv['client_name']}  \n"
                    f"**Date:** {format_date(inv['date'])}  \n"
                    f"**Status:** {inv['status']}  \n"
                    f"**Total:** {format_currency(inv['total'])}"
                )
                separator = "=" * 60
                dash = "-" * 60
                lines = [
                    separator,
                    "INVOICE",
                    separator,
                    "",
                    f"Invoice Number: {inv['invoice_no']}",
                    f"Date: {format_date(inv['date'])}",
                    f"Status: {inv['status']}",
                    "",
                    f"BILL TO: {inv['client_name']}",
                    "",
                    dash,
                    "TIME ENTRIES",
                    dash,
                ]
                for idx, entry in enumerate(inv["entries"], 1):
                    lines.extend(
                        [
                            "",
                            f"{idx}. Date: {format_date(entry['date'])}",
                            f"   Description: {entry['description']}",
                            f"   Hours: {entry['hours']} @ {format_currency(entry['rate'])}/hr",
                            f"   Amount: {format_currency(entry['amount'])}",
                        ]
                    )
                lines.extend(
                    [
                        "",
                        dash,
                        f"TOTAL AMOUNT DUE: {format_currency(inv['total'])}",
                        dash,
                        "",
                        "Payment Terms: Due upon receipt",
                        "Thank you for your business.",
                        "",
                        separator,
                        "Generated by LexiAssist Legal Practice Management System",
                        separator,
                    ]
                )
                invoice_text = "\n".join(lines)
                st.download_button(
                    "📥 Download Invoice",
                    data=invoice_text,
                    file_name=f"{inv['invoice_no']}.txt",
                    mime="text/plain",
                    key=f"dl_inv_{inv['id']}",
                )


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    render_header()
    render_sidebar()
    render_stats()
    st.markdown("---")

    tabs = st.tabs(
        [
            "🤖 AI Assistant",
            "📚 Research",
            "📁 Cases",
            "📅 Calendar",
            "📋 Templates",
            "👥 Clients",
            "💰 Billing",
        ]
    )
    with tabs[0]:
        render_ai_assistant()
    with tabs[1]:
        render_research()
    with tabs[2]:
        render_cases()
    with tabs[3]:
        render_calendar()
    with tabs[4]:
        render_templates()
    with tabs[5]:
        render_clients()
    with tabs[6]:
        render_billing()

    st.markdown("---")
    st.markdown(
        '<div style="text-align:center;color:#64748b;font-size:.875rem">'
        "<p>⚖️ <strong>LexiAssist v2.0</strong> — AI-Powered Legal Practice Management</p>"
        "<p>Designed for Nigerian Lawyers · Powered by Google Gemini</p>"
        "<p>© 2026 LexiAssist. All rights reserved.</p>"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
