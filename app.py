"""
LexiAssist v3.0 — AI-Powered Legal Practice Management for Nigerian Lawyers.
"""
from __future__ import annotations

import html
import json
import logging
import os
import time
import uuid
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional

import google.generativeai as genai
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("LexiAssist")

st.set_page_config(
    page_title="LexiAssist — Legal Practice Management",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "# LexiAssist v3.0\nAI-Powered Legal Practice Management for Nigerian Lawyers."},
)

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════
CASE_STATUSES = ["Active", "Pending", "Completed", "Archived"]
CLIENT_TYPES = ["Individual", "Corporate", "Government"]
TASK_TYPES: dict[str, dict[str, str]] = {
    "drafting":       {"label": "Document Drafting",       "description": "Contracts, pleadings, applications, affidavits", "icon": "📄"},
    "analysis":       {"label": "Legal Analysis",          "description": "Issue spotting, IRAC / FILAC reasoning",         "icon": "🔍"},
    "research":       {"label": "Legal Research",          "description": "Case law, statutes, authorities",                "icon": "📚"},
    "procedure":      {"label": "Procedural Guidance",     "description": "Court filing, evidence rules",                   "icon": "📋"},
    "interpretation": {"label": "Statutory Interpretation", "description": "Analyze and explain legislation",               "icon": "⚖️"},
    "general":        {"label": "General Query",           "description": "Ask anything legal-related",                     "icon": "💬"},
}
MODEL_MIGRATION_MAP = {
    "gemini-2.0-flash": "gemini-2.5-flash", "gemini-2.0-flash-001": "gemini-2.5-flash",
    "gemini-2.0-flash-lite": "gemini-2.5-flash-lite", "gemini-2.0-flash-lite-001": "gemini-2.5-flash-lite",
}
SUPPORTED_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
DEFAULT_MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = (
    "You are LexiAssist, an advanced AI legal assistant designed specifically for Nigerian lawyers.\n\n"
    "JURISDICTION: Nigeria — Constitution of the Federal Republic of Nigeria 1999 (as amended), "
    "Federal and State Acts, subsidiary legislation, Rules of Court, and Nigerian case law.\n\n"
    "CORE PRINCIPLES:\n"
    "1. Use step-by-step reasoning (IRAC / FILAC methods where applicable).\n"
    "2. Provide legal information and analysis — NEVER definitive legal conclusions.\n"
    "3. Never fabricate cases, statutes, or authorities. State uncertainty clearly.\n"
    "4. Include relevant statutory and case references when available.\n"
    "5. Use professional tone suitable for Nigerian legal practice.\n"
    "6. Format responses with clear headings and numbered points.\n\n"
    "RESPONSE STRUCTURE:\n"
    "1. Brief restatement of the request.\n2. Key assumptions (if any).\n"
    "3. Detailed analysis or document draft.\n4. Relevant legal authorities.\n5. Caveats and recommendations."
)
RESEARCH_INSTRUCTION = (
    SYSTEM_INSTRUCTION +
    "\n\nFor legal research, additionally provide:\n"
    "• Relevant Nigerian statutes with specific sections and recent amendments.\n"
    "• Key case law: names, citations, holdings, court level.\n"
    "• Legal principles and how Nigerian courts interpret them.\n"
    "• Practical application: procedural requirements, limitation periods, jurisdiction.\n"
    "• Pitfalls, strategic considerations, ADR options.\n"
    "• If uncertain about a citation, state the general principle instead."
)
GENERATION_CONFIG = {"temperature": 0.7, "top_p": 0.95, "top_k": 40, "max_output_tokens": 8192}

# ── Nigerian Legal Reference Data ────────────────────────────
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
    {"cause": "Tax Assessment Appeal", "period": "30 days", "authority": "FIRS (Est.) Act, s. 59"},
    {"cause": "Public Officer Liability", "period": "3 months notice / 12 months", "authority": "Public Officers Protection Act, s. 2"},
    {"cause": "Insurance Claims", "period": "12 months after disclaimer", "authority": "Insurance Act 2003, s. 72"},
    {"cause": "Winding-Up Petition", "period": "21 days from demand", "authority": "CAMA 2020, s. 572"},
]
COURT_HIERARCHY = [
    {"level": 1, "name": "Supreme Court of Nigeria", "desc": "Final appellate court — 7 or 5 Justices", "icon": "🏛️"},
    {"level": 2, "name": "Court of Appeal", "desc": "Intermediate appellate court — 16 Divisions", "icon": "⚖️"},
    {"level": 3, "name": "Federal High Court", "desc": "Federal causes: admiralty, revenue, IP, banking", "icon": "🏢"},
    {"level": 3, "name": "State High Courts", "desc": "General civil & criminal jurisdiction per state", "icon": "🏢"},
    {"level": 3, "name": "National Industrial Court", "desc": "Labour & employment disputes", "icon": "🏢"},
    {"level": 3, "name": "Sharia Court of Appeal", "desc": "Islamic personal law appeals", "icon": "🏢"},
    {"level": 3, "name": "Customary Court of Appeal", "desc": "Customary law appeals", "icon": "🏢"},
    {"level": 4, "name": "Magistrate / District Courts", "desc": "Summary jurisdiction, minor offences", "icon": "📋"},
    {"level": 4, "name": "Area / Customary Courts", "desc": "Customary law at first instance", "icon": "📋"},
    {"level": 4, "name": "Sharia Courts", "desc": "Islamic personal law at first instance", "icon": "📋"},
    {"level": 5, "name": "Tribunals & Panels", "desc": "Election Petition, Tax Appeal, Code of Conduct", "icon": "📌"},
]
LEGAL_MAXIMS = [
    {"maxim": "Audi alteram partem", "meaning": "Hear the other side — pillar of natural justice"},
    {"maxim": "Nemo judex in causa sua", "meaning": "No one should judge their own cause"},
    {"maxim": "Actus non facit reum nisi mens sit rea", "meaning": "An act doesn't make one guilty unless the mind is guilty"},
    {"maxim": "Res judicata", "meaning": "A matter already decided — cannot be re-litigated"},
    {"maxim": "Stare decisis", "meaning": "Stand by what has been decided — doctrine of precedent"},
    {"maxim": "Ubi jus ibi remedium", "meaning": "Where there is a right, there is a remedy"},
    {"maxim": "Volenti non fit injuria", "meaning": "No injury is done to one who consents"},
    {"maxim": "Pacta sunt servanda", "meaning": "Agreements must be honoured"},
    {"maxim": "Nemo dat quod non habet", "meaning": "No one gives what they don't have"},
    {"maxim": "Ignorantia legis neminem excusat", "meaning": "Ignorance of the law excuses no one"},
    {"maxim": "Qui facit per alium facit per se", "meaning": "He who acts through another acts himself"},
    {"maxim": "Ex turpi causa non oritur actio", "meaning": "No action arises from an immoral cause"},
    {"maxim": "Expressio unius est exclusio alterius", "meaning": "Express mention of one excludes others"},
    {"maxim": "Ejusdem generis", "meaning": "Of the same kind — general words limited by specific ones"},
    {"maxim": "Locus standi", "meaning": "Right or capacity to bring an action before a court"},
]

# ═══════════════════════════════════════════════════════════════
# CSS THEMES
# ═══════════════════════════════════════════════════════════════
_BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*{font-family:'Inter',sans-serif}
.main .block-container{padding-top:1.5rem;padding-bottom:2rem;max-width:1200px}
.main-header{padding:2rem 2.5rem;border-radius:1.25rem;margin-bottom:1.5rem;color:white;position:relative;overflow:hidden}
.main-header::before{content:'⚖';position:absolute;right:2rem;top:50%;transform:translateY(-50%);font-size:6rem;opacity:.12}
.main-header h1{margin:0;font-size:2.2rem;font-weight:700;letter-spacing:-.02em}
.main-header p{margin:.5rem 0 0;opacity:.85;font-size:.95rem;font-weight:400}
.custom-card{border-radius:1rem;padding:1.5rem;margin-bottom:1rem;transition:all .25s ease;border:1px solid}
.custom-card:hover{transform:translateY(-3px);box-shadow:0 12px 36px rgba(0,0,0,.1)}
.stat-card{border-radius:1rem;padding:1.25rem;text-align:center;border:1px solid;transition:all .25s ease}
.stat-card:hover{transform:translateY(-2px)}
.stat-value{font-size:1.75rem;font-weight:700;letter-spacing:-.02em}
.stat-label{font-size:.8rem;margin-top:.25rem;font-weight:500;text-transform:uppercase;letter-spacing:.05em}
.badge{display:inline-block;padding:.2rem .65rem;border-radius:9999px;font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.03em}
.badge-success{background:#dcfce7;color:#166534}
.badge-warning{background:#fef3c7;color:#92400e}
.badge-info{background:#dbeafe;color:#1e40af}
.badge-danger{background:#fee2e2;color:#991b1b}
.response-box{border:1px solid;border-radius:.75rem;padding:1.75rem;margin:1rem 0;white-space:pre-wrap;font-family:'Georgia','Times New Roman',serif;line-height:1.9;font-size:.95rem}
.disclaimer{border-left:4px solid #f59e0b;padding:1rem 1.25rem;border-radius:0 .5rem .5rem 0;margin-top:1rem;font-size:.85rem}
.calendar-event{padding:1rem 1.25rem;border-radius:.75rem;margin-bottom:.75rem;border-left:4px solid}
.calendar-event.urgent{background:#fee2e2;border-color:#ef4444}
.calendar-event.warning{background:#fef3c7;border-color:#f59e0b}
.calendar-event.normal{background:#f0fdf4;border-color:#10b981}
.template-card{border:1px solid;border-radius:.75rem;padding:1.25rem;margin-bottom:1rem;transition:all .2s ease}
.template-card:hover{box-shadow:0 6px 16px rgba(0,0,0,.08);transform:translateY(-2px)}
.tool-card{border-radius:1rem;padding:1.25rem;margin-bottom:1rem;border:1px solid}
.feature-card{border-radius:1rem;padding:1.5rem;text-align:center;border:1px solid;transition:all .3s ease;height:100%}
.feature-card:hover{transform:translateY(-4px);box-shadow:0 12px 36px rgba(0,0,0,.1)}
.feature-card .feature-icon{font-size:2.5rem;margin-bottom:.75rem}
.feature-card h4{margin:0 0 .5rem;font-size:1rem;font-weight:600}
.feature-card p{margin:0;font-size:.85rem;line-height:1.5}
.welcome-steps{counter-reset:step;list-style:none;padding:0}
.welcome-step{counter-increment:step;padding:1rem 1rem 1rem 3.5rem;position:relative;margin-bottom:.75rem;border-radius:.75rem;border:1px solid}
.welcome-step::before{content:counter(step);position:absolute;left:1rem;top:50%;transform:translateY(-50%);width:2rem;height:2rem;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.85rem}
.quick-action-btn{border-radius:.75rem;padding:1rem;text-align:center;border:1px solid;transition:all .2s ease;cursor:pointer}
.quick-action-btn:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.08)}
#MainMenu{visibility:hidden}footer{visibility:hidden}
.stTabs [data-baseweb="tab-list"]{gap:.25rem;background:transparent}
.stTabs [data-baseweb="tab"]{border-radius:.5rem .5rem 0 0;padding:.6rem 1rem;font-weight:600;font-size:.85rem}
div[data-testid="stRadio"] > div{gap:.5rem!important}
</style>
"""

_THEME_EMERALD = """<style>
.main-header{background:linear-gradient(135deg,#059669 0%,#0d9488 50%,#065f46 100%);box-shadow:0 12px 40px rgba(5,150,105,.25)}
.custom-card{background:#fff;border-color:#e2e8f0}.stat-card{background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:#bbf7d0}
.stat-card .stat-value{color:#059669}.stat-card.blue{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#bfdbfe}
.stat-card.blue .stat-value{color:#2563eb}.stat-card.purple{background:linear-gradient(135deg,#faf5ff,#f3e8ff);border-color:#e9d5ff}
.stat-card.purple .stat-value{color:#7c3aed}.stat-card.amber{background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fde68a}
.stat-card.amber .stat-value{color:#d97706}.stat-label{color:#64748b}
.response-box{background:#f8fafc;border-color:#e2e8f0}.disclaimer{background:#fef3c7}
.template-card,.tool-card,.feature-card{background:#fff;border-color:#e2e8f0}
.welcome-step{background:#f0fdf4;border-color:#bbf7d0}.welcome-step::before{background:#059669;color:white}
.quick-action-btn{background:#fff;border-color:#e2e8f0}
</style>"""

_THEME_MIDNIGHT = """<style>
[data-testid="stAppViewContainer"]{background-color:#0f172a!important;color:#e2e8f0!important}
[data-testid="stSidebar"]{background-color:#1e293b!important}
[data-testid="stHeader"]{background-color:#0f172a!important}
.main-header{background:linear-gradient(135deg,#1e40af 0%,#6d28d9 50%,#1e3a5f 100%);box-shadow:0 12px 40px rgba(30,64,175,.3)}
.custom-card{background:#1e293b;border-color:#334155;color:#e2e8f0}
.stat-card{background:linear-gradient(135deg,#1e293b,#334155);border-color:#475569}
.stat-card .stat-value{color:#34d399}
.stat-card.blue{background:linear-gradient(135deg,#1e293b,#1e3a5f);border-color:#2563eb}.stat-card.blue .stat-value{color:#60a5fa}
.stat-card.purple{background:linear-gradient(135deg,#1e293b,#2e1065);border-color:#7c3aed}.stat-card.purple .stat-value{color:#a78bfa}
.stat-card.amber{background:linear-gradient(135deg,#1e293b,#451a03);border-color:#d97706}.stat-card.amber .stat-value{color:#fbbf24}
.stat-label{color:#94a3b8}.response-box{background:#1e293b;border-color:#334155;color:#e2e8f0}
.disclaimer{background:#451a03;color:#fef3c7}.template-card,.tool-card,.feature-card{background:#1e293b;border-color:#334155;color:#e2e8f0}
.calendar-event.urgent{background:#450a0a;border-color:#ef4444;color:#fecaca}
.calendar-event.warning{background:#451a03;border-color:#f59e0b;color:#fef3c7}
.calendar-event.normal{background:#052e16;border-color:#10b981;color:#d1fae5}
.welcome-step{background:#334155;border-color:#475569;color:#e2e8f0}.welcome-step::before{background:#6d28d9;color:white}
.quick-action-btn{background:#1e293b;border-color:#334155;color:#e2e8f0}
[data-testid="stAppViewContainer"] h1,[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3,[data-testid="stAppViewContainer"] h4{color:#f1f5f9!important}
[data-testid="stAppViewContainer"] p,[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] span,[data-testid="stAppViewContainer"] label{color:#cbd5e1!important}
[data-testid="stSidebar"] *{color:#e2e8f0!important}
</style>"""

_THEME_ROYAL = """<style>
.main-header{background:linear-gradient(135deg,#1e3a5f 0%,#1e40af 50%,#0f2557 100%);box-shadow:0 12px 40px rgba(30,58,95,.3)}
.custom-card{background:#f8faff;border-color:#bfdbfe}.stat-card{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#93c5fd}
.stat-card .stat-value{color:#1e40af}
.stat-card.blue{background:linear-gradient(135deg,#eef2ff,#e0e7ff);border-color:#a5b4fc}.stat-card.blue .stat-value{color:#4f46e5}
.stat-card.purple{background:linear-gradient(135deg,#faf5ff,#f3e8ff);border-color:#e9d5ff}.stat-card.purple .stat-value{color:#7c3aed}
.stat-card.amber{background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fde68a}.stat-card.amber .stat-value{color:#d97706}
.stat-label{color:#64748b}.response-box{background:#f0f5ff;border-color:#bfdbfe}.disclaimer{background:#fef3c7}
.template-card,.tool-card,.feature-card{background:#f8faff;border-color:#bfdbfe}
.welcome-step{background:#eff6ff;border-color:#bfdbfe}.welcome-step::before{background:#1e40af;color:white}
.quick-action-btn{background:#f8faff;border-color:#bfdbfe}
</style>"""

THEMES = {"🌿 Emerald": _THEME_EMERALD, "🌙 Midnight": _THEME_MIDNIGHT, "👔 Royal Blue": _THEME_ROYAL}


# ═══════════════════════════════════════════════════════════════
# TEMPLATES (cached)
# ═══════════════════════════════════════════════════════════════
@st.cache_data
def get_templates() -> list[dict[str, str]]:
    return [
        {"id":"1","name":"Employment Contract","category":"Corporate","content":"EMPLOYMENT CONTRACT\n\nThis Employment Contract is made on [DATE] between:\n\n1. [EMPLOYER NAME] (\"the Employer\")\n   Address: [EMPLOYER ADDRESS] | RC: [NUMBER]\n\n2. [EMPLOYEE NAME] (\"the Employee\")\n   Address: [EMPLOYEE ADDRESS]\n\nTERMS:\n\n1. POSITION: [JOB TITLE]\n2. COMMENCEMENT: [START DATE]\n3. PROBATION: [PERIOD] months\n4. SALARY: N[AMOUNT] monthly\n5. HOURS: [HOURS]/week, Mon-Fri\n6. LEAVE: [NUMBER] days annual\n7. TERMINATION: [NOTICE PERIOD] written notice\n8. CONFIDENTIALITY: Employee maintains confidentiality\n9. GOVERNING LAW: Labour Act of Nigeria\n\nSIGNED:\n_______________ _______________\nEmployer        Employee\n"},
        {"id":"2","name":"Tenancy Agreement","category":"Property","content":"TENANCY AGREEMENT\n\nMade on [DATE] BETWEEN:\n[LANDLORD NAME] of [ADDRESS] (\"Landlord\")\nAND\n[TENANT NAME] of [ADDRESS] (\"Tenant\")\n\n1. PREMISES: [PROPERTY ADDRESS]\n2. TERM: [DURATION] from [START DATE]\n3. RENT: N[AMOUNT] per [PERIOD]\n4. DEPOSIT: N[AMOUNT] refundable\n5. USE: [Residential/Commercial] only\n6. MAINTENANCE: Tenant keeps premises in good condition\n7. ALTERATIONS: None without Landlord's written consent\n8. ASSIGNMENT: No subletting without consent\n9. TERMINATION: [NOTICE PERIOD] written notice\n10. LAW: Lagos State Tenancy Law (or applicable state law)\n\nSIGNED:\n_______________ _______________\nLandlord        Tenant\n\nWITNESS: _______________\n"},
        {"id":"3","name":"Power of Attorney","category":"Litigation","content":"GENERAL POWER OF ATTORNEY\n\nKNOW ALL MEN BY THESE PRESENTS:\n\nI, [GRANTOR NAME], of [ADDRESS], [OCCUPATION], appoint [ATTORNEY NAME] of [ADDRESS] as my Attorney to:\n\n1. Demand, sue for, recover and collect all monies due\n2. Sign and execute contracts and documents\n3. Appear before any court or tribunal\n4. Operate bank accounts\n5. Manage properties and collect rents\n6. Execute and register deeds\n\nThis Power remains in force until revoked in writing.\n\nDated: [DATE]\n\n_______________\n[GRANTOR NAME]\n\nWITNESS: _______________\n"},
        {"id":"4","name":"Written Address","category":"Litigation","content":"IN THE [COURT NAME]\nHOLDEN AT [LOCATION]\nSUIT NO: [NUMBER]\n\n[PLAINTIFF] v. [DEFENDANT]\n\nWRITTEN ADDRESS OF THE [PLAINTIFF/DEFENDANT]\n\n1.0 INTRODUCTION\n1.1 Filed pursuant to the Rules of this Honourable Court.\n\n2.0 FACTS\n[Narration]\n\n3.0 ISSUES FOR DETERMINATION\n3.1 Whether [Issue 1]\n3.2 Whether [Issue 2]\n\n4.0 ARGUMENTS\n4.1 ON ISSUE ONE\n[Arguments with authorities]\n\n5.0 CONCLUSION\nWe urge this Court to:\n(a) [Prayer 1]\n(b) [Prayer 2]\n\nDated: [DATE]\n_______________\n[COUNSEL NAME]\nFor: [LAW FIRM]\n"},
        {"id":"5","name":"Affidavit","category":"Litigation","content":"IN THE [COURT NAME]\nSUIT NO: [NUMBER]\n\n[PLAINTIFF] v. [DEFENDANT]\n\nAFFIDAVIT IN SUPPORT OF [MOTION]\n\nI, [DEPONENT], [Gender], [Religion], Nigerian, of [ADDRESS], make oath:\n\n1. I am the [Party] and familiar with the facts.\n2. I have authority to depose.\n3. [Fact 1]\n4. [Fact 2]\n5. This Affidavit is made in good faith.\n6. Facts stated are true to my knowledge and belief.\n\n_______________\nDEPONENT\n\nSworn at [Location] this [DATE]\nBefore: _______________\nCOMMISSIONER FOR OATHS\n"},
        {"id":"6","name":"Legal Opinion","category":"Corporate","content":"LEGAL OPINION\nPRIVATE & CONFIDENTIAL\n\nTO: [CLIENT]\nFROM: [LAW FIRM]\nDATE: [DATE]\nRE: [SUBJECT]\n\n1.0 INTRODUCTION\n[Instruction summary]\n\n2.0 FACTS\n[Background]\n\n3.0 ISSUES\n3.1 [Issue 1]\n3.2 [Issue 2]\n\n4.0 LEGAL FRAMEWORK\n[Statutes, regulations, case law]\n\n5.0 ANALYSIS\n[Detailed analysis per issue]\n\n6.0 CONCLUSION\n[Conclusions and recommendations]\n\n7.0 CAVEATS\nBased solely on Nigerian law and facts provided.\n\n_______________\n[PARTNER NAME]\nFor: [LAW FIRM]\n"},
        {"id":"7","name":"Demand Letter","category":"Litigation","content":"[LETTERHEAD]\n[DATE]\n\n[RECIPIENT NAME & ADDRESS]\n\nRE: DEMAND FOR N[AMOUNT] — [DESCRIPTION]\nOUR CLIENT: [CLIENT NAME]\n\nDear Sir/Madam,\n\nWe are Solicitors to [CLIENT] and write on their instruction.\n\nFacts:\n1. [Background]\n2. [Obligation]\n3. [Breach/Default]\n\nYou owe N[AMOUNT]. Despite demands, you have failed to pay.\n\nTAKE NOTICE: Pay within 7 DAYS or we institute proceedings without further notice, seeking:\n(a) Interest at [RATE]% p.a.\n(b) Legal costs\n(c) General damages\n\nGovern yourself accordingly.\n\n_______________\n[COUNSEL]\nFor: [LAW FIRM]\nc.c: Client\n"},
        {"id":"8","name":"Board Resolution","category":"Corporate","content":"BOARD RESOLUTION\n[COMPANY NAME] (RC: [NUMBER])\n[VENUE] — [DATE] [TIME]\n\nPRESENT:\n1. [NAME] - Chairman\n2. [NAME] - Director\n3. [NAME] - Director\n\nIN ATTENDANCE: [NAME] - Company Secretary\n\nRESOLUTION [NUMBER]: [TITLE]\n\nWHEREAS:\nA. [Background]\nB. [Reason]\n\nRESOLVED:\n1. [Resolution 1]\n2. [Resolution 2]\n3. Any Director authorized to execute necessary documents.\n4. Company Secretary to file returns with CAC.\n\nCERTIFIED TRUE COPY\n_______________\nCompany Secretary\nDate: [DATE]\n"},
    ]


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
def generate_id() -> str: return uuid.uuid4().hex[:8]
def format_currency(a: float) -> str: return f"₦{a:,.2f}"
def safe_html(t: str) -> str: return html.escape(str(t))

def format_date(s: str) -> str:
    try: return datetime.fromisoformat(s).strftime("%B %d, %Y")
    except (ValueError, TypeError): return str(s)

def get_days_until(s: str) -> int:
    try: return (datetime.fromisoformat(s).date() - datetime.now().date()).days
    except (ValueError, TypeError): return 999

def get_relative_date(s: str) -> str:
    d = get_days_until(s)
    if d == 0: return "Today"
    if d == 1: return "Tomorrow"
    if d == -1: return "Yesterday"
    if 0 < d <= 7: return f"In {d} days"
    if -7 <= d < 0: return f"{abs(d)} days ago"
    return format_date(s)

def normalize_model(n: str) -> str:
    c = (n or "").strip()
    m = MODEL_MIGRATION_MAP.get(c, c)
    return m if m in SUPPORTED_MODELS else DEFAULT_MODEL

def get_active_model() -> str:
    return normalize_model(st.session_state.get("gemini_model", DEFAULT_MODEL))

def _secret(key: str, default: str = "") -> str:
    try: return st.secrets[key]
    except (KeyError, FileNotFoundError, AttributeError): return default


# ═══════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════
_DEFAULTS: dict[str, Any] = {
    "api_key": "", "api_configured": False, "cases": [], "clients": [],
    "time_entries": [], "invoices": [], "last_response": "", "research_results": "",
    "selected_task_type": "general", "gemini_model": DEFAULT_MODEL,
    "loaded_template": "", "theme": "🌿 Emerald", "admin_unlocked": False,
}
def init_session_state():
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v
init_session_state()

# Apply theme
st.markdown(_BASE_CSS, unsafe_allow_html=True)
st.markdown(THEMES.get(st.session_state.theme, _THEME_EMERALD), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# RETRY DECORATOR
# ═══════════════════════════════════════════════════════════════
def with_retry(attempts: int = 2, delay: float = 1.5):
    def dec(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            for i in range(1, attempts + 1):
                try: return fn(*a, **kw)
                except Exception as e:
                    if i == attempts: raise
                    time.sleep(delay * (2 ** (i - 1)))
        return wrapper
    return dec


# ═══════════════════════════════════════════════════════════════
# GEMINI API
# ═══════════════════════════════════════════════════════════════
def _load_key() -> str:
    for src in [lambda: _secret("GEMINI_API_KEY"), lambda: os.getenv("GEMINI_API_KEY", ""), lambda: st.session_state.get("api_key", "")]:
        k = src()
        if k and k.strip(): return k.strip()
    return ""

def _configure(key: str): genai.configure(api_key=key, transport="rest")

def configure_gemini(key: str, model: str | None = None) -> bool:
    sel = normalize_model(model or DEFAULT_MODEL)
    try:
        _configure(key)
        genai.GenerativeModel(sel).generate_content("OK", generation_config={"max_output_tokens": 8})
        st.session_state.update(api_configured=True, api_key=key, gemini_model=sel)
        return True
    except Exception as e:
        msg = str(e)
        if "403" in msg: st.error("API key invalid or lacks permission.")
        elif "429" in msg: st.error("Rate limit exceeded. Wait and retry.")
        else: st.error(f"API error: {msg}")
        return False

def auto_configure():
    if st.session_state.api_configured: return
    key = _load_key()
    if key and len(key) >= 10:
        _configure(key)
        st.session_state.update(api_key=key, api_configured=True)
        m = _secret("GEMINI_MODEL") or os.getenv("GEMINI_MODEL", "")
        if m: st.session_state.gemini_model = normalize_model(m)

@with_retry()
def _call(prompt: str, sys: str) -> str:
    key = _load_key()
    if not key: raise RuntimeError("No API key")
    _configure(key)
    try: model = genai.GenerativeModel(get_active_model(), system_instruction=sys)
    except TypeError:
        model = genai.GenerativeModel(get_active_model())
        prompt = f"{sys}\n\n{prompt}"
    return model.generate_content(prompt, generation_config=GENERATION_CONFIG).text

def generate_response(prompt: str, task_type: str) -> str:
    if not st.session_state.api_configured: return "⚠️ Configure your API key first."
    label = TASK_TYPES.get(task_type, {}).get("label", "General Query")
    try: return _call(f"[Task: {label}]\n\n{prompt}", SYSTEM_INSTRUCTION)
    except Exception as e: return f"Error: {e}"

def do_research(query: str) -> str:
    if not st.session_state.api_configured: return "⚠️ Configure your API key first."
    try: return _call(query, RESEARCH_INSTRUCTION)
    except Exception as e: return f"Error: {e}"


# ═══════════════════════════════════════════════════════════════
# DATA CRUD
# ═══════════════════════════════════════════════════════════════
def add_case(d):
    d.update(id=generate_id(), created_at=datetime.now().isoformat())
    st.session_state.cases.append(d); return d

def update_case(cid, u):
    for c in st.session_state.cases:
        if c["id"] == cid: c.update(u); c["updated_at"] = datetime.now().isoformat(); return True
    return False

def delete_case(cid): st.session_state.cases = [c for c in st.session_state.cases if c["id"] != cid]

def add_client(d):
    d.update(id=generate_id(), created_at=datetime.now().isoformat())
    st.session_state.clients.append(d); return d

def delete_client(cid): st.session_state.clients = [c for c in st.session_state.clients if c["id"] != cid]

def get_client_name(cid):
    for c in st.session_state.clients:
        if c["id"] == cid: return c["name"]
    return "Unknown"

def add_time_entry(d):
    d.update(id=generate_id(), created_at=datetime.now().isoformat(), amount=d["hours"] * d["rate"])
    st.session_state.time_entries.append(d); return d

def delete_time_entry(eid): st.session_state.time_entries = [e for e in st.session_state.time_entries if e["id"] != eid]

def generate_invoice(cid):
    entries = [e for e in st.session_state.time_entries if e.get("client_id") == cid]
    if not entries: return None
    inv = {"id": generate_id(), "invoice_no": f"INV-{datetime.now():%Y%m%d}-{generate_id()[:4].upper()}",
           "client_id": cid, "client_name": get_client_name(cid), "entries": entries,
           "total": sum(e["amount"] for e in entries), "date": datetime.now().isoformat(), "status": "Draft"}
    st.session_state.invoices.append(inv); return inv

def total_billable(): return sum(e.get("amount", 0) for e in st.session_state.time_entries)
def total_hours(): return sum(e.get("hours", 0) for e in st.session_state.time_entries)
def client_billable(cid): return sum(e.get("amount", 0) for e in st.session_state.time_entries if e.get("client_id") == cid)
def client_cases(cid): return sum(1 for c in st.session_state.cases if c.get("client_id") == cid)

def upcoming_hearings(limit=10):
    h = [{"case_id": c["id"], "title": c["title"], "date": c["next_hearing"],
          "court": c.get("court", ""), "suit_no": c.get("suit_no", "")}
         for c in st.session_state.cases if c.get("next_hearing") and c.get("status") == "Active"]
    h.sort(key=lambda x: x["date"]); return h[:limit]
    # ═══════════════════════════════════════════════════════════════
# UI: HEADER & STATS
# ═══════════════════════════════════════════════════════════════
def render_header():
    st.markdown(
        '<div class="main-header"><h1>⚖️ LexiAssist</h1>'
        '<p>AI-Powered Legal Practice Management for Nigerian Lawyers · Powered by Google Gemini</p></div>',
        unsafe_allow_html=True)

def render_stats():
    c1, c2, c3, c4 = st.columns(4)
    active = len([c for c in st.session_state.cases if c.get("status") == "Active"])
    with c1: st.markdown(f'<div class="stat-card"><div class="stat-value">{active}</div><div class="stat-label">📁 Active Cases</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-card blue"><div class="stat-value">{len(st.session_state.clients)}</div><div class="stat-label">👥 Clients</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="stat-card purple"><div class="stat-value">{safe_html(format_currency(total_billable()))}</div><div class="stat-label">💰 Billable</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="stat-card amber"><div class="stat-value">{len(upcoming_hearings())}</div><div class="stat-label">📅 Hearings</div></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# UI: SIDEBAR
# ═══════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("### 🎨 Appearance")
        theme = st.selectbox("Theme", list(THEMES.keys()),
            index=list(THEMES.keys()).index(st.session_state.theme) if st.session_state.theme in THEMES else 0,
            label_visibility="collapsed")
        if theme != st.session_state.theme:
            st.session_state.theme = theme; st.rerun()

        st.divider()
        st.markdown("### 🤖 AI Engine")
        if st.session_state.api_configured:
            st.success(f"✅ Ready · `{get_active_model()}`")
        else:
            st.warning("⚠️ Not configured")

        idx = SUPPORTED_MODELS.index(get_active_model()) if get_active_model() in SUPPORTED_MODELS else 0
        sel = st.selectbox("Model", SUPPORTED_MODELS, index=idx)
        if normalize_model(sel) != st.session_state.gemini_model:
            st.session_state.gemini_model = normalize_model(sel)
            st.session_state.api_configured = False; st.rerun()

        # Admin / API Key
        has_secret = bool(_secret("GEMINI_API_KEY"))
        admin_pw = _secret("ADMIN_PASSWORD")
        show_input = False

        if not has_secret:
            if admin_pw:
                with st.expander("🔒 Admin"):
                    if st.text_input("Password", type="password", key="apw") == admin_pw:
                        st.session_state.admin_unlocked = True
                    if st.session_state.admin_unlocked: show_input = True
            else:
                show_input = True
        else:
            if admin_pw:
                with st.expander("🔒 Admin"):
                    if st.text_input("Password", type="password", key="apw") == admin_pw:
                        st.session_state.admin_unlocked = True
                    if st.session_state.admin_unlocked: show_input = True

        if show_input:
            st.markdown("#### 🔑 API Key")
            ki = st.text_input("Key", type="password", value=st.session_state.api_key, label_visibility="collapsed")
            if st.button("Connect", type="primary"):
                if ki and len(ki.strip()) >= 10:
                    with st.spinner("Connecting…"):
                        if configure_gemini(ki.strip(), st.session_state.gemini_model):
                            st.success("✅ Connected!"); st.rerun()
                else: st.warning("Enter a valid key.")
            st.caption("[Get free key →](https://aistudio.google.com/app/apikey)")

        st.divider()
        st.markdown("### 💾 Data")
        if st.button("📥 Export All", use_container_width=True):
            p = {"cases": st.session_state.cases, "clients": st.session_state.clients,
                 "time_entries": st.session_state.time_entries, "invoices": st.session_state.invoices,
                 "exported_at": datetime.now().isoformat()}
            st.download_button("Download JSON", json.dumps(p, indent=2),
                               f"lexiassist_{datetime.now():%Y%m%d}.json", "application/json")
        up = st.file_uploader("📤 Import", type=["json"])
        if up:
            try:
                d = json.load(up)
                for k in ["cases", "clients", "time_entries", "invoices"]:
                    st.session_state[k] = d.get(k, [])
                st.success("Imported!"); st.rerun()
            except Exception as e: st.error(str(e))

        st.divider()
        st.markdown("### ⚡ Quick")
        if st.button("➕ New Case", use_container_width=True): st.rerun()
        if st.button("👤 New Client", use_container_width=True): st.rerun()

        st.divider()
        st.caption("**LexiAssist v3.0** · © 2026\n\n🤖 Gemini · 🎈 Streamlit · 🐍 Python")


# ═══════════════════════════════════════════════════════════════
# PAGE: DASHBOARD (NEW)
# ═══════════════════════════════════════════════════════════════
def render_dashboard():
    st.markdown("### 🏠 Welcome to LexiAssist")
    st.markdown("Your intelligent legal practice companion — purpose-built for Nigerian lawyers.")

    # Feature cards
    features = [
        ("🤖", "AI Legal Assistant", "Draft documents, analyze issues, and get instant legal guidance powered by Gemini AI."),
        ("📚", "Legal Research", "Research Nigerian statutes, case law, and legal principles with AI-powered depth."),
        ("📁", "Case Management", "Track cases, hearings, court dates, and case notes in one organized place."),
        ("📅", "Court Calendar", "Never miss a hearing — visual timeline with urgency-coded reminders."),
        ("📋", "Document Templates", "8 ready-made Nigerian legal templates: contracts, affidavits, opinions, and more."),
        ("👥", "Client Management", "Manage client records, link to cases, and track billing per client."),
        ("💰", "Billing & Invoicing", "Log billable hours, set rates, and generate professional invoices instantly."),
        ("🇳🇬", "Nigerian Legal Tools", "Limitation periods, interest calculator, court hierarchy, and legal maxims."),
    ]
    cols = st.columns(4)
    for i, (icon, title, desc) in enumerate(features):
        with cols[i % 4]:
            st.markdown(f'<div class="feature-card"><div class="feature-icon">{icon}</div><h4>{title}</h4><p>{desc}</p></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Two-column layout: upcoming + getting started
    left, right = st.columns([3, 2])
    with left:
        hearings = upcoming_hearings(5)
        if hearings:
            st.markdown("#### 📅 Upcoming Hearings")
            for h in hearings:
                d = get_days_until(h["date"])
                urg = "urgent" if d <= 3 else ("warning" if d <= 7 else "normal")
                badge = "danger" if d <= 3 else ("warning" if d <= 7 else "success")
                st.markdown(
                    f'<div class="calendar-event {urg}"><strong>{safe_html(h["title"])}</strong> · '
                    f'{safe_html(h["suit_no"])}<br>{safe_html(format_date(h["date"]))} '
                    f'<span class="badge badge-{badge}">{safe_html(get_relative_date(h["date"]))}</span></div>',
                    unsafe_allow_html=True)
        else:
            st.info("📅 No upcoming hearings. Add hearing dates to active cases to see them here.")

        if st.session_state.cases:
            st.markdown("#### 📁 Recent Cases")
            for case in st.session_state.cases[-5:]:
                bc = {"Active": "success", "Pending": "warning", "Completed": "info"}.get(case.get("status", ""), "info")
                st.markdown(f'<div class="custom-card" style="padding:1rem"><strong>{safe_html(case["title"])}</strong> '
                    f'<span class="badge badge-{bc}">{safe_html(case.get("status",""))}</span><br>'
                    f'<small>{safe_html(case.get("suit_no",""))} · {safe_html(case.get("court",""))}</small></div>',
                    unsafe_allow_html=True)

    with right:
        st.markdown("#### 🚀 Getting Started")
        steps = [
            ("Configure your API key", "Add your free Google AI Studio key in the sidebar to unlock AI features."),
            ("Add your clients", "Go to the Clients tab and add client details to link them to cases."),
            ("Create your first case", "Track cases with suit numbers, courts, hearing dates, and notes."),
            ("Try the AI Assistant", "Draft documents, get legal analysis, or conduct research instantly."),
            ("Log billable hours", "Track time entries and generate invoices from the Billing tab."),
        ]
        for title, desc in steps:
            st.markdown(f'<div class="welcome-step"><strong>{title}</strong><br><small>{desc}</small></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📊 Practice Overview")
        total_c = len(st.session_state.cases)
        active_c = len([c for c in st.session_state.cases if c.get("status") == "Active"])
        st.metric("Total Cases", total_c, f"{active_c} active")
        st.metric("Total Clients", len(st.session_state.clients))
        st.metric("Hours Logged", f"{total_hours():.1f}h")


# ═══════════════════════════════════════════════════════════════
# PAGE: AI ASSISTANT (FIXED — uses st.radio)
# ═══════════════════════════════════════════════════════════════
def render_ai_assistant():
    st.markdown("### 🤖 AI Legal Assistant")
    st.markdown("Draft documents, analyze legal issues, interpret statutes, and get expert guidance — all powered by AI.")

    # ── TASK TYPE: st.radio — guaranteed to work ─────────────
    st.markdown("#### Select Task Type")
    task_keys = list(TASK_TYPES.keys())
    current_idx = task_keys.index(st.session_state.selected_task_type) if st.session_state.selected_task_type in task_keys else 5

    selected_task = st.radio(
        "task_type_radio",
        task_keys,
        index=current_idx,
        format_func=lambda k: f"{TASK_TYPES[k]['icon']} {TASK_TYPES[k]['label']}",
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state.selected_task_type = selected_task

    # Show description of selected task
    sel = TASK_TYPES[selected_task]
    st.caption(f"**{sel['icon']} {sel['label']}** — {sel['description']}")

    st.markdown("---")

    # ── Input ────────────────────────────────────────────────
    default_text = st.session_state.pop("loaded_template", "")
    st.markdown("#### Describe Your Legal Task")
    user_input = st.text_area("query_input", value=default_text, height=200,
        placeholder="Example: Draft a commercial lease agreement for property in Victoria Island, Lagos, "
                    "with a 3-year term, annual rent review clause, and break option after 18 months…",
        label_visibility="collapsed")

    bc1, bc2, bc3 = st.columns([2, 1, 1])
    with bc1:
        gen = st.button("✨ Generate Response", type="primary", use_container_width=True,
                        disabled=not st.session_state.api_configured)
    with bc2:
        st.button("📋 Load Template", use_container_width=True, key="load_tmpl_btn")
    with bc3:
        clear = st.button("🗑️ Clear Response", use_container_width=True,
                          disabled=not st.session_state.last_response)

    if gen:
        if user_input.strip():
            with st.spinner("⚖️ LexiAssist is working…"):
                result = generate_response(user_input, st.session_state.selected_task_type)
                if not result.startswith("Error"):
                    st.session_state.last_response = result
                else:
                    st.error(result)
        else:
            st.warning("Please enter your legal query or task.")

    if clear:
        st.session_state.last_response = ""
        st.rerun()

    if not st.session_state.api_configured:
        st.info("💡 **Tip:** Add your free Google AI Studio API key in the sidebar to unlock the AI assistant.")

    # ── Response Display ─────────────────────────────────────
    if st.session_state.last_response:
        st.markdown("---")
        st.markdown("#### 📄 LexiAssist Response")

        ec1, ec2, ec3, ec4 = st.columns([1, 1, 1, 3])
        with ec1:
            st.download_button("📥 Text", st.session_state.last_response,
                f"LexiAssist_{datetime.now():%Y%m%d_%H%M}.txt", "text/plain")
        with ec2:
            escaped = safe_html(st.session_state.last_response)
            html_doc = (
                "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>LexiAssist</title>"
                "<style>body{font-family:Georgia,serif;line-height:1.8;max-width:800px;margin:40px auto;padding:20px}"
                "h1{color:#059669;border-bottom:3px solid #059669;padding-bottom:12px}.c{white-space:pre-wrap}"
                ".d{background:#fef3c7;border-left:4px solid #f59e0b;padding:16px;margin-top:32px}"
                "</style></head><body><h1>⚖️ LexiAssist Legal Document</h1>"
                f"<div class='c'>{escaped}</div>"
                "<div class='d'><b>Disclaimer:</b> For informational purposes only.</div>"
                f"<p style='text-align:center;color:#64748b;font-size:12px;margin-top:32px'>"
                f"Generated {datetime.now():%B %d, %Y %I:%M %p}</p></body></html>"
            )
            st.download_button("📥 HTML", html_doc,
                f"LexiAssist_{datetime.now():%Y%m%d_%H%M}.html", "text/html")
        with ec3:
            if st.button("🗑️ Clear", key="clear2"):
                st.session_state.last_response = ""; st.rerun()

        st.markdown(f'<div class="response-box">{safe_html(st.session_state.last_response)}</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="disclaimer"><strong>⚖️ Professional Disclaimer:</strong> '
            'This response is for informational purposes only and does not constitute legal advice. '
            'All legal work should be reviewed by a qualified Nigerian lawyer. Always verify case citations '
            'and statutory references independently.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: RESEARCH
# ═══════════════════════════════════════════════════════════════
def render_research():
    st.markdown("### 📚 Legal Research")
    st.markdown("AI-powered research across Nigerian statutes, case law, and legal principles.")
    query = st.text_input("query", placeholder="E.g. 'employer liability for workplace injury under Nigerian law'", label_visibility="collapsed")

    rc1, rc2 = st.columns([3, 1])
    with rc1:
        search = st.button("🔍 Research", type="primary", disabled=not st.session_state.api_configured, use_container_width=True)
    with rc2:
        r_clear = st.button("🗑️ Clear Results", disabled=not st.session_state.research_results, use_container_width=True)

    if search and query.strip():
        with st.spinner("📚 Researching…"):
            st.session_state.research_results = do_research(query)
    if r_clear:
        st.session_state.research_results = ""; st.rerun()
    if not st.session_state.api_configured:
        st.info("💡 Configure your API key in the sidebar to use legal research.")
    if st.session_state.research_results:
        st.markdown("---")
        st.download_button("📥 Export", st.session_state.research_results,
            f"Research_{datetime.now():%Y%m%d_%H%M}.txt", "text/plain")
        st.markdown(f'<div class="response-box">{safe_html(st.session_state.research_results)}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: CASES
# ═══════════════════════════════════════════════════════════════
def render_cases():
    st.markdown("### 📁 Case Management")
    with st.expander("➕ Add New Case", expanded=not bool(st.session_state.cases)):
        with st.form("case_form"):
            c1, c2 = st.columns(2)
            with c1:
                title = st.text_input("Case Title *", placeholder="John Doe v. State")
                suit = st.text_input("Suit Number *", placeholder="FHC/L/CS/123/2024")
                court = st.text_input("Court", placeholder="Federal High Court, Lagos")
            with c2:
                nh = st.date_input("Next Hearing")
                status = st.selectbox("Status", CASE_STATUSES)
                cn = ["— Select —"] + [c["name"] for c in st.session_state.clients]
                ci = st.selectbox("Client", range(len(cn)), format_func=lambda i: cn[i])
            notes = st.text_area("Notes")
            if st.form_submit_button("Save Case", type="primary"):
                if title.strip() and suit.strip():
                    cid = st.session_state.clients[ci - 1]["id"] if ci > 0 else None
                    add_case({"title": title.strip(), "suit_no": suit.strip(), "court": court.strip(),
                              "next_hearing": nh.isoformat() if nh else None, "status": status,
                              "client_id": cid, "notes": notes.strip()})
                    st.success("✅ Case added!"); st.rerun()
                else: st.error("Title and Suit Number required.")

    filt = st.selectbox("Filter", ["All"] + CASE_STATUSES, key="case_filt")
    cases = st.session_state.cases if filt == "All" else [c for c in st.session_state.cases if c.get("status") == filt]
    if not cases:
        st.info("📁 No cases. Add your first case above!"); return
    for case in cases:
        bc = {"Active":"success","Pending":"warning","Completed":"info","Archived":""}.get(case.get("status",""),"")
        hh = f"<p><strong>Next Hearing:</strong> {safe_html(format_date(case['next_hearing']))} ({safe_html(get_relative_date(case['next_hearing']))})</p>" if case.get("next_hearing") else ""
        nh_text = f"<p><em>{safe_html(case['notes'])}</em></p>" if case.get("notes") else ""
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(f'<div class="custom-card"><h4>{safe_html(case["title"])} <span class="badge badge-{bc}">{safe_html(case.get("status",""))}</span></h4>'
                f'<p><strong>Suit No:</strong> {safe_html(case.get("suit_no",""))}</p>'
                f'<p><strong>Court:</strong> {safe_html(case.get("court",""))}</p>'
                f'<p><strong>Client:</strong> {safe_html(get_client_name(case.get("client_id","")))}</p>'
                f'{hh}{nh_text}</div>', unsafe_allow_html=True)
        with c2:
            ci2 = CASE_STATUSES.index(case["status"]) if case.get("status") in CASE_STATUSES else 0
            ns = st.selectbox("St", CASE_STATUSES, index=ci2, key=f"s_{case['id']}", label_visibility="collapsed")
            if ns != case.get("status"): update_case(case["id"], {"status": ns}); st.rerun()
            if st.button("🗑️", key=f"d_{case['id']}"): delete_case(case["id"]); st.rerun()


# ═══════════════════════════════════════════════════════════════
# PAGE: CALENDAR
# ═══════════════════════════════════════════════════════════════
def render_calendar():
    st.markdown("### 📅 Court Calendar")
    hearings = upcoming_hearings()
    if not hearings:
        st.info("📅 No upcoming hearings. Add hearing dates to active cases."); return
    for h in hearings:
        d = get_days_until(h["date"])
        u = "urgent" if d <= 3 else ("warning" if d <= 7 else "normal")
        b = "danger" if d <= 3 else ("warning" if d <= 7 else "success")
        st.markdown(f'<div class="calendar-event {u}"><h4>{safe_html(h["title"])}</h4>'
            f'<p><strong>Suit No:</strong> {safe_html(h["suit_no"])} · <strong>Court:</strong> {safe_html(h["court"])}</p>'
            f'<p><strong>Date:</strong> {safe_html(format_date(h["date"]))} '
            f'<span class="badge badge-{b}">{safe_html(get_relative_date(h["date"]))}</span></p></div>', unsafe_allow_html=True)
    st.markdown("---")
    df = pd.DataFrame([{"Case": h["title"], "Days": max(get_days_until(h["date"]), 0), "Date": format_date(h["date"])} for h in hearings])
    fig = px.bar(df, x="Days", y="Case", orientation="h", text="Date",
        color="Days", color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"], title="Days Until Hearings")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: TEMPLATES
# ═══════════════════════════════════════════════════════════════
def render_templates():
    st.markdown("### 📋 Document Templates")
    st.markdown("Professional Nigerian legal document templates — ready to customize or load into the AI Assistant.")
    templates = get_templates()
    cats = sorted({t["category"] for t in templates})
    sel = st.selectbox("Category", ["All"] + cats, key="tmpl_cat")
    vis = templates if sel == "All" else [t for t in templates if t["category"] == sel]
    cols = st.columns(2)
    for i, t in enumerate(vis):
        with cols[i % 2]:
            st.markdown(f'<div class="template-card"><h4>📄 {safe_html(t["name"])}</h4>'
                f'<span class="badge badge-success">{safe_html(t["category"])}</span>'
                f'<p style="margin-top:.5rem;color:#64748b;font-size:.85rem">{safe_html(t["content"][:120])}…</p></div>', unsafe_allow_html=True)
            tc1, tc2 = st.columns(2)
            with tc1:
                if st.button("📋 Use in AI", key=f"u_{t['id']}", use_container_width=True):
                    st.session_state.loaded_template = t["content"]
                    st.success(f"'{t['name']}' loaded!"); st.rerun()
            with tc2:
                if st.button("👁️ Preview", key=f"p_{t['id']}", use_container_width=True):
                    st.session_state["preview_tmpl"] = t
    pv = st.session_state.get("preview_tmpl")
    if pv:
        st.markdown("---")
        st.markdown(f"### Preview: {pv['name']}")
        st.code(pv["content"], language=None)
        pc1, pc2 = st.columns([1, 4])
        with pc1:
            if st.button("Close"): del st.session_state["preview_tmpl"]; st.rerun()
        with pc2:
            st.download_button("📥 Download", pv["content"], f"{pv['name'].replace(' ','_')}.txt", "text/plain")


# ═══════════════════════════════════════════════════════════════
# PAGE: CLIENTS
# ═══════════════════════════════════════════════════════════════
def render_clients():
    st.markdown("### 👥 Client Management")
    with st.expander("➕ Add New Client", expanded=not bool(st.session_state.clients)):
        with st.form("client_form"):
            c1, c2 = st.columns(2)
            with c1: name = st.text_input("Name *"); email = st.text_input("Email"); phone = st.text_input("Phone")
            with c2: ctype = st.selectbox("Type", CLIENT_TYPES); addr = st.text_input("Address"); notes = st.text_area("Notes")
            if st.form_submit_button("Save", type="primary"):
                if name.strip():
                    add_client({"name": name.strip(), "email": email.strip(), "phone": phone.strip(),
                                "type": ctype, "address": addr.strip(), "notes": notes.strip()})
                    st.success("✅ Added!"); st.rerun()
                else: st.error("Name required.")
    if not st.session_state.clients:
        st.info("👥 No clients yet."); return
    cols = st.columns(2)
    for i, cl in enumerate(st.session_state.clients):
        with cols[i % 2]:
            cc, cb = client_cases(cl["id"]), client_billable(cl["id"])
            el = f"<p>📧 {safe_html(cl['email'])}</p>" if cl.get("email") else ""
            pl = f"<p>📱 {safe_html(cl['phone'])}</p>" if cl.get("phone") else ""
            al = f"<p>📍 {safe_html(cl['address'])}</p>" if cl.get("address") else ""
            st.markdown(f'<div class="custom-card"><h4>{safe_html(cl["name"])} '
                f'<span class="badge badge-info">{safe_html(cl.get("type",""))}</span></h4>'
                f'{el}{pl}{al}<hr style="margin:1rem 0">'
                f'<div style="display:flex;justify-content:space-around;text-align:center">'
                f'<div><div style="font-size:1.5rem;font-weight:700;color:#059669">{cc}</div><div style="font-size:.75rem;color:#64748b">Cases</div></div>'
                f'<div><div style="font-size:1.5rem;font-weight:700;color:#7c3aed">{safe_html(format_currency(cb))}</div><div style="font-size:.75rem;color:#64748b">Billable</div></div>'
                f'</div></div>', unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            with b1:
                if cb > 0 and st.button("📄 Invoice", key=f"iv_{cl['id']}", use_container_width=True):
                    inv = generate_invoice(cl["id"])
                    if inv: st.success(f"{inv['invoice_no']} created!"); st.rerun()
            with b2:
                if st.button("🗑️ Delete", key=f"dc_{cl['id']}", use_container_width=True):
                    delete_client(cl["id"]); st.rerun()


# ═══════════════════════════════════════════════════════════════
# PAGE: BILLING
# ═══════════════════════════════════════════════════════════════
def render_billing():
    st.markdown("### 💰 Billing & Time Tracking")
    s1, s2, s3 = st.columns(3)
    with s1: st.markdown(f'<div class="stat-card"><div class="stat-value">{safe_html(format_currency(total_billable()))}</div><div class="stat-label">💰 Billable</div><div style="font-size:.75rem;color:#64748b">{len(st.session_state.time_entries)} entries</div></div>', unsafe_allow_html=True)
    with s2: st.markdown(f'<div class="stat-card blue"><div class="stat-value">{total_hours():.1f}h</div><div class="stat-label">⏱️ Hours</div></div>', unsafe_allow_html=True)
    with s3: st.markdown(f'<div class="stat-card purple"><div class="stat-value">{len(st.session_state.invoices)}</div><div class="stat-label">📄 Invoices</div></div>', unsafe_allow_html=True)
    st.markdown("---")

    with st.expander("⏱️ Log Time", expanded=False):
        with st.form("time_form"):
            c1, c2 = st.columns(2)
            with c1:
                cn = ["— Client —"] + [c["name"] for c in st.session_state.clients]
                ci = st.selectbox("Client *", range(len(cn)), format_func=lambda i: cn[i])
                csn = ["— Case —"] + [c["title"] for c in st.session_state.cases]
                csi = st.selectbox("Case", range(len(csn)), format_func=lambda i: csn[i])
                ed = st.date_input("Date", datetime.now())
            with c2:
                hrs = st.number_input("Hours *", .25, step=.25, value=1.0)
                rate = st.number_input("Rate (₦/hr) *", 0, value=50000, step=5000)
                st.markdown(f"**Total: {format_currency(hrs * rate)}**")
            desc = st.text_area("Description *")
            if st.form_submit_button("Save", type="primary"):
                if ci > 0 and desc.strip():
                    add_time_entry({"client_id": st.session_state.clients[ci-1]["id"],
                        "case_id": st.session_state.cases[csi-1]["id"] if csi > 0 else None,
                        "date": ed.isoformat(), "hours": hrs, "rate": rate, "description": desc.strip()})
                    st.success("✅ Logged!"); st.rerun()
                else: st.error("Select client, enter description.")

    st.markdown("#### 📋 Time Entries")
    if not st.session_state.time_entries:
        st.info("No entries yet."); return
    rows = [{"Date": format_date(e["date"]), "Client": get_client_name(e.get("client_id","")),
             "Description": e["description"][:50]+("…" if len(e["description"])>50 else ""),
             "Hours": f"{e['hours']}h", "Rate": format_currency(e["rate"]),
             "Amount": format_currency(e["amount"]), "ID": e["id"]} for e in reversed(st.session_state.time_entries)]
    st.dataframe(pd.DataFrame(rows).drop(columns=["ID"]), use_container_width=True, hide_index=True)
    labels = [f"{r['Date']} — {r['Client']} — {r['Description']}" for r in rows]
    sd = st.selectbox("Delete entry", ["None"] + labels, key="del_e")
    if sd != "None" and st.button("🗑️ Delete"):
        delete_time_entry(rows[labels.index(sd)]["ID"]); st.rerun()
    if len(rows) > 1:
        st.markdown("---")
        totals: dict[str, float] = {}
        for e in st.session_state.time_entries:
            cn2 = get_client_name(e.get("client_id",""))
            totals[cn2] = totals.get(cn2, 0) + e["amount"]
        fig = px.pie(values=list(totals.values()), names=list(totals.keys()), title="Billable by Client")
        st.plotly_chart(fig, use_container_width=True)
    if st.session_state.invoices:
        st.markdown("---")
        st.markdown("#### 📄 Invoices")
        for inv in reversed(st.session_state.invoices):
            with st.expander(f"📄 {inv['invoice_no']} — {inv['client_name']} — {format_currency(inv['total'])}"):
                st.markdown(f"**{inv['invoice_no']}** · {inv['client_name']} · {format_date(inv['date'])} · **{format_currency(inv['total'])}**")
                sep, dash = "="*60, "-"*60
                lines = [sep,"INVOICE",sep,"",f"Invoice: {inv['invoice_no']}",f"Date: {format_date(inv['date'])}","",
                         f"BILL TO: {inv['client_name']}","",dash,"TIME ENTRIES",dash]
                for idx, e in enumerate(inv["entries"], 1):
                    lines += ["",f"{idx}. {format_date(e['date'])}",f"   {e['description']}",
                              f"   {e['hours']}h @ {format_currency(e['rate'])}/hr = {format_currency(e['amount'])}"]
                lines += ["",dash,f"TOTAL: {format_currency(inv['total'])}",dash,"","Due upon receipt",sep]
                st.download_button("📥 Download", "\n".join(lines), f"{inv['invoice_no']}.txt", "text/plain", key=f"dl_{inv['id']}")


# ═══════════════════════════════════════════════════════════════
# PAGE: LEGAL TOOLS
# ═══════════════════════════════════════════════════════════════
def render_legal_tools():
    st.markdown("### 🇳🇬 Nigerian Legal Tools")
    tabs = st.tabs(["⏱️ Limitation Periods", "💹 Interest Calculator", "🏛️ Court Hierarchy", "📖 Legal Maxims"])

    with tabs[0]:
        st.markdown("#### ⏱️ Limitation Periods")
        st.caption("Common periods under Nigerian law. Always verify with the specific statute.")
        search = st.text_input("Search", placeholder="e.g. contract, land…", key="lim_s")
        data = LIMITATION_PERIODS
        if search: data = [l for l in data if search.lower() in l["cause"].lower()]
        if data:
            st.dataframe(pd.DataFrame(data, columns=["cause","period","authority"]).rename(
                columns={"cause":"Cause of Action","period":"Period","authority":"Authority"}),
                use_container_width=True, hide_index=True)
        else: st.info("No matches.")

    with tabs[1]:
        st.markdown("#### 💹 Interest Calculator")
        with st.form("int_calc"):
            c1, c2 = st.columns(2)
            with c1:
                principal = st.number_input("Principal (₦)", 0.0, value=1_000_000.0, step=50_000.0)
                rate_pct = st.number_input("Rate (% p.a.)", 0.0, value=10.0, step=0.5)
            with c2:
                months = st.number_input("Period (months)", 1, value=12)
                calc = st.selectbox("Type", ["Simple", "Compound (Monthly)"])
            if st.form_submit_button("Calculate", type="primary"):
                if calc == "Simple":
                    interest = principal * (rate_pct / 100) * (months / 12)
                else:
                    interest = principal * ((1 + (rate_pct/100)/12) ** months) - principal
                r1, r2, r3 = st.columns(3)
                with r1: st.metric("Principal", format_currency(principal))
                with r2: st.metric("Interest", format_currency(interest))
                with r3: st.metric("Total", format_currency(principal + interest))
                st.markdown(f'<div class="disclaimer"><strong>Draft clause:</strong> "…together with interest at '
                    f'{rate_pct}% per annum ({calc.lower()}) from [DATE] until payment, currently '
                    f'{safe_html(format_currency(interest))}."</div>', unsafe_allow_html=True)

    with tabs[2]:
        st.markdown("#### 🏛️ Court Hierarchy")
        st.caption("Under the 1999 Constitution (as amended)")
        for court in COURT_HIERARCHY:
            indent = "　" * (court["level"] - 1)
            mark = "🔸" if court["level"] == 1 else ("├─" if court["level"] < 5 else "└─")
            st.markdown(f"{indent}{mark} **{court['icon']} {court['name']}**")
            st.caption(f"{indent}　　{court['desc']}")

    with tabs[3]:
        st.markdown("#### 📖 Legal Maxims")
        sq = st.text_input("Search", placeholder="e.g. nemo, audi…", key="mx_s")
        mx = LEGAL_MAXIMS
        if sq: mx = [m for m in mx if sq.lower() in m["maxim"].lower() or sq.lower() in m["meaning"].lower()]
        if mx:
            for m in mx:
                st.markdown(f'<div class="tool-card"><h4 style="font-style:italic">{safe_html(m["maxim"])}</h4>'
                    f'<p>{safe_html(m["meaning"])}</p></div>', unsafe_allow_html=True)
        else: st.info("No matches.")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    auto_configure()
    render_header()
    render_sidebar()
    render_stats()
    st.markdown("---")

    tabs = st.tabs([
        "🏠 Dashboard", "🤖 AI Assistant", "📚 Research", "📁 Cases",
        "📅 Calendar", "📋 Templates", "👥 Clients", "💰 Billing", "🇳🇬 Legal Tools",
    ])
    with tabs[0]: render_dashboard()
    with tabs[1]: render_ai_assistant()
    with tabs[2]: render_research()
    with tabs[3]: render_cases()
    with tabs[4]: render_calendar()
    with tabs[5]: render_templates()
    with tabs[6]: render_clients()
    with tabs[7]: render_billing()
    with tabs[8]: render_legal_tools()

    st.markdown("---")
    st.markdown(
        '<div style="text-align:center;color:#64748b;font-size:.85rem;padding:1rem 0">'
        '<p>⚖️ <strong>LexiAssist v3.0</strong> — AI-Powered Legal Practice Management</p>'
        '<p>Purpose-built for Nigerian Lawyers · Powered by Google Gemini</p>'
        '<p style="font-size:.75rem;margin-top:.5rem">⚠️ This tool provides legal information, not legal advice. '
        'Always consult a qualified legal practitioner.</p>'
        '<p style="font-size:.75rem">© 2026 LexiAssist. All rights reserved.</p></div>',
        unsafe_allow_html=True)

if __name__ == "__main__":
    main()
