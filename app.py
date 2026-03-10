"""
LexiAssist v3.5 — AI-Powered Legal Practice Management for Nigerian Lawyers.
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
    menu_items={"About": "# LexiAssist v3.5\nAI Legal Practice Management for Nigerian Lawyers."},
)

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════
CASE_STATUSES = ["Active", "Pending", "Completed", "Archived"]
CLIENT_TYPES = ["Individual", "Corporate", "Government"]

TASK_TYPES: dict[str, dict[str, str]] = {
    "drafting":       {"label": "Document Drafting",        "desc": "Contracts, pleadings, applications, affidavits",  "icon": "📄"},
    "analysis":       {"label": "Legal Analysis",           "desc": "Issue spotting, IRAC / FILAC reasoning",          "icon": "🔍"},
    "research":       {"label": "Legal Research",           "desc": "Case law, statutes, authorities",                 "icon": "📚"},
    "procedure":      {"label": "Procedural Guidance",      "desc": "Court filing, evidence rules, practice directions","icon": "📋"},
    "interpretation": {"label": "Statutory Interpretation",  "desc": "Analyze and explain legislation",                "icon": "⚖️"},
    "general":        {"label": "General Query",            "desc": "Ask anything legal-related",                      "icon": "💬"},
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
    "- Relevant Nigerian statutes with specific sections and recent amendments.\n"
    "- Key case law: names, citations, holdings, court level.\n"
    "- Legal principles and Nigerian court interpretations.\n"
    "- Practical application: procedural requirements, limitation periods, jurisdiction.\n"
    "- Pitfalls, strategic considerations, and ADR options.\n"
    "- If uncertain about a citation, state the general principle."
)
GEN_CONFIG = {"temperature": 0.7, "top_p": 0.95, "top_k": 40, "max_output_tokens": 8192}

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
    {"level": 2, "name": "Court of Appeal", "desc": "Intermediate appellate — 16 Divisions nationwide", "icon": "⚖️"},
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
    {"maxim": "Actus non facit reum nisi mens sit rea", "meaning": "An act does not make one guilty unless the mind is guilty"},
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
    {"maxim": "Ejusdem generis", "meaning": "General words limited by specific preceding words"},
    {"maxim": "Locus standi", "meaning": "The right or capacity to bring an action before a court"},
]


# ═══════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════
_BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*{font-family:'Inter',sans-serif}
.main .block-container{padding-top:1rem;padding-bottom:2rem;max-width:1200px}

/* Hero */
@keyframes heroGradient{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.hero{padding:3rem;border-radius:1.5rem;color:white;position:relative;overflow:hidden;
  background:linear-gradient(-45deg,#059669,#0d9488,#065f46,#047857,#0f766e);
  background-size:300% 300%;animation:heroGradient 12s ease infinite;
  box-shadow:0 20px 60px rgba(5,150,105,.3)}
.hero::before{content:'';position:absolute;top:-50%;right:-20%;width:500px;height:500px;
  background:radial-gradient(circle,rgba(255,255,255,.08) 0%,transparent 70%);border-radius:50%}
.hero::after{content:'⚖';position:absolute;right:3rem;bottom:1rem;font-size:8rem;opacity:.07}
.hero h1{font-size:2.8rem;font-weight:800;margin:0;letter-spacing:-.03em;line-height:1.15}
.hero p{font-size:1.05rem;margin:.75rem 0 0;opacity:.9;font-weight:300;max-width:600px;line-height:1.6}
.hero-badge{display:inline-block;padding:.35rem .85rem;background:rgba(255,255,255,.15);
  border-radius:9999px;font-size:.75rem;font-weight:600;margin-top:1.25rem;backdrop-filter:blur(4px);
  border:1px solid rgba(255,255,255,.2);letter-spacing:.05em;text-transform:uppercase}

/* Compact header for inner pages */
.page-header{padding:1.5rem 2rem;border-radius:1.25rem;margin-bottom:1.5rem;color:white;
  background:linear-gradient(135deg,#059669,#0d9488);box-shadow:0 12px 40px rgba(5,150,105,.25)}
.page-header h1{margin:0;font-size:2rem;font-weight:700}.page-header p{margin:.25rem 0 0;opacity:.85;font-size:.9rem}

/* Cards */
.custom-card{background:#fff;border:1px solid #e2e8f0;border-radius:1rem;padding:1.5rem;margin-bottom:1rem;transition:all .3s ease}
.custom-card:hover{transform:translateY(-3px);box-shadow:0 12px 36px rgba(0,0,0,.1)}
.stat-card{border-radius:1rem;padding:1.25rem;text-align:center;border:1px solid;transition:all .25s ease}
.stat-card:hover{transform:translateY(-2px)}
.stat-value{font-size:1.75rem;font-weight:700;letter-spacing:-.02em}
.stat-label{font-size:.78rem;margin-top:.3rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em}

/* Feature cards */
@keyframes fadeUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
.feat-card{background:#fff;border:1px solid #e2e8f0;border-radius:1.25rem;padding:1.75rem 1.25rem;
  text-align:center;transition:all .35s ease;animation:fadeUp .5s ease forwards;height:100%}
.feat-card:hover{transform:translateY(-6px);box-shadow:0 16px 48px rgba(5,150,105,.12);border-color:#059669}
.feat-icon{font-size:2.75rem;margin-bottom:.75rem;display:block}
.feat-card h4{margin:0 0 .5rem;font-size:.95rem;font-weight:700;color:#1e293b}
.feat-card p{margin:0;font-size:.82rem;color:#64748b;line-height:1.55}

/* Value props */
.value-card{background:linear-gradient(135deg,#f0fdf4,#ecfdf5);border:1px solid #bbf7d0;
  border-radius:1.25rem;padding:2rem 1.5rem;text-align:center;transition:all .3s ease;height:100%}
.value-card:hover{transform:translateY(-4px);box-shadow:0 12px 36px rgba(5,150,105,.1)}
.value-card .v-icon{font-size:2.5rem;margin-bottom:.75rem;display:block}
.value-card h4{margin:0 0 .5rem;font-size:1rem;font-weight:700;color:#065f46}
.value-card p{margin:0;font-size:.85rem;color:#047857;line-height:1.55}

/* Badges */
.badge{display:inline-block;padding:.2rem .65rem;border-radius:9999px;font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.03em}
.badge-success{background:#dcfce7;color:#166534}.badge-warning{background:#fef3c7;color:#92400e}
.badge-info{background:#dbeafe;color:#1e40af}.badge-danger{background:#fee2e2;color:#991b1b}

/* Response */
.response-box{background:#f8fafc;border:1px solid #e2e8f0;border-radius:.75rem;padding:1.75rem;
  margin:1rem 0;white-space:pre-wrap;font-family:'Georgia','Times New Roman',serif;line-height:1.9;font-size:.95rem}
.disclaimer{background:#fef3c7;border-left:4px solid #f59e0b;padding:1rem 1.25rem;border-radius:0 .5rem .5rem 0;margin-top:1rem;font-size:.85rem}

/* Calendar */
.cal-event{padding:1rem 1.25rem;border-radius:.75rem;margin-bottom:.75rem;border-left:4px solid}
.cal-event.urgent{background:#fee2e2;border-color:#ef4444}
.cal-event.warn{background:#fef3c7;border-color:#f59e0b}
.cal-event.ok{background:#f0fdf4;border-color:#10b981}

/* Template & tool cards */
.tmpl-card{background:#fff;border:1px solid #e2e8f0;border-radius:.75rem;padding:1.25rem;margin-bottom:1rem;transition:all .25s ease}
.tmpl-card:hover{box-shadow:0 6px 20px rgba(0,0,0,.08);transform:translateY(-2px)}
.tool-card{background:#fff;border:1px solid #e2e8f0;border-radius:1rem;padding:1.25rem;margin-bottom:1rem}

/* Footer */
.app-footer{text-align:center;padding:2rem 1rem;color:#64748b;font-size:.85rem;border-top:1px solid #e2e8f0;margin-top:2rem}
.app-footer a{color:#059669;text-decoration:none;font-weight:500}

/* Misc */
#MainMenu{visibility:hidden}footer{visibility:hidden}
.stTabs [data-baseweb="tab-list"]{gap:.25rem;background:transparent;border-bottom:2px solid #e2e8f0}
.stTabs [data-baseweb="tab"]{border-radius:.5rem .5rem 0 0;padding:.65rem 1.15rem;font-weight:600;font-size:.82rem}
</style>
"""

# Theme overrides
_THEME_EMERALD = """<style>
.stat-card{background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:#bbf7d0}
.stat-card .stat-value{color:#059669}.stat-label{color:#64748b}
.stat-card.t-blue{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#bfdbfe}
.stat-card.t-blue .stat-value{color:#2563eb}
.stat-card.t-purple{background:linear-gradient(135deg,#faf5ff,#f3e8ff);border-color:#e9d5ff}
.stat-card.t-purple .stat-value{color:#7c3aed}
.stat-card.t-amber{background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fde68a}
.stat-card.t-amber .stat-value{color:#d97706}
</style>"""

_THEME_MIDNIGHT = """<style>
[data-testid="stAppViewContainer"]{background:#0f172a!important;color:#e2e8f0!important}
[data-testid="stSidebar"]{background:#1e293b!important}[data-testid="stHeader"]{background:#0f172a!important}
.hero{background:linear-gradient(-45deg,#1e40af,#6d28d9,#1e3a5f,#4f46e5)!important}
.page-header{background:linear-gradient(135deg,#1e40af,#6d28d9)!important}
.custom-card,.feat-card,.tmpl-card,.tool-card{background:#1e293b!important;border-color:#334155!important;color:#e2e8f0!important}
.feat-card h4{color:#f1f5f9!important}.feat-card p,.stat-label{color:#94a3b8!important}
.value-card{background:linear-gradient(135deg,#1e293b,#0f2557)!important;border-color:#334155!important}
.value-card h4{color:#a78bfa!important}.value-card p{color:#94a3b8!important}
.stat-card{background:linear-gradient(135deg,#1e293b,#334155)!important;border-color:#475569!important}
.stat-card .stat-value{color:#34d399!important}
.stat-card.t-blue{background:linear-gradient(135deg,#1e293b,#1e3a5f)!important;border-color:#2563eb!important}
.stat-card.t-blue .stat-value{color:#60a5fa!important}
.stat-card.t-purple{background:linear-gradient(135deg,#1e293b,#2e1065)!important;border-color:#7c3aed!important}
.stat-card.t-purple .stat-value{color:#a78bfa!important}
.stat-card.t-amber{background:linear-gradient(135deg,#1e293b,#451a03)!important;border-color:#d97706!important}
.stat-card.t-amber .stat-value{color:#fbbf24!important}
.response-box{background:#1e293b!important;border-color:#334155!important;color:#e2e8f0!important}
.disclaimer{background:#451a03!important;color:#fef3c7!important}
.cal-event.urgent{background:#450a0a!important;color:#fecaca!important}
.cal-event.warn{background:#451a03!important;color:#fef3c7!important}
.cal-event.ok{background:#052e16!important;color:#d1fae5!important}
.app-footer{border-color:#334155!important;color:#94a3b8!important}
[data-testid="stAppViewContainer"] h1,[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3,[data-testid="stAppViewContainer"] h4{color:#f1f5f9!important}
[data-testid="stAppViewContainer"] p,[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] span,[data-testid="stAppViewContainer"] label,
[data-testid="stSidebar"] *{color:#e2e8f0!important}
</style>"""

_THEME_ROYAL = """<style>
.hero{background:linear-gradient(-45deg,#1e3a5f,#1e40af,#0f2557,#2563eb)!important}
.page-header{background:linear-gradient(135deg,#1e3a5f,#1e40af)!important}
.custom-card,.feat-card,.tmpl-card,.tool-card{background:#f8faff;border-color:#bfdbfe}
.feat-card h4{color:#1e3a5f}.value-card{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#93c5fd}
.value-card h4{color:#1e40af}.value-card p{color:#2563eb}
.stat-card{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#93c5fd}
.stat-card .stat-value{color:#1e40af}
.stat-card.t-blue{background:linear-gradient(135deg,#eef2ff,#e0e7ff);border-color:#a5b4fc}
.stat-card.t-blue .stat-value{color:#4f46e5}
.stat-card.t-purple{background:linear-gradient(135deg,#faf5ff,#f3e8ff);border-color:#e9d5ff}
.stat-card.t-purple .stat-value{color:#7c3aed}
.stat-card.t-amber{background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fde68a}
.stat-card.t-amber .stat-value{color:#d97706}
.response-box{background:#f0f5ff;border-color:#bfdbfe}
</style>"""

THEMES = {"🌿 Emerald": _THEME_EMERALD, "🌙 Midnight": _THEME_MIDNIGHT, "👔 Royal Blue": _THEME_ROYAL}


# ═══════════════════════════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════════════════════════
@st.cache_data
def get_templates() -> list[dict[str, str]]:
    return [
        {"id":"1","name":"Employment Contract","cat":"Corporate","content":"EMPLOYMENT CONTRACT\n\nThis Employment Contract is made on [DATE] between:\n\n1. [EMPLOYER NAME] (\"the Employer\")\n   Address: [EMPLOYER ADDRESS] | RC: [NUMBER]\n\n2. [EMPLOYEE NAME] (\"the Employee\")\n   Address: [EMPLOYEE ADDRESS]\n\nTERMS:\n\n1. POSITION: [JOB TITLE]\n2. COMMENCEMENT: [START DATE]\n3. PROBATION: [PERIOD] months\n4. SALARY: N[AMOUNT] monthly\n5. HOURS: [HOURS]/week, Mon-Fri\n6. LEAVE: [NUMBER] days annual\n7. TERMINATION: [NOTICE PERIOD] written notice\n8. CONFIDENTIALITY: Employee maintains confidentiality\n9. GOVERNING LAW: Labour Act of Nigeria\n\nSIGNED:\n_______________ _______________\nEmployer        Employee\n"},
        {"id":"2","name":"Tenancy Agreement","cat":"Property","content":"TENANCY AGREEMENT\n\nMade on [DATE] BETWEEN:\n[LANDLORD NAME] of [ADDRESS] (\"Landlord\")\nAND\n[TENANT NAME] of [ADDRESS] (\"Tenant\")\n\n1. PREMISES: [PROPERTY ADDRESS]\n2. TERM: [DURATION] from [START DATE]\n3. RENT: N[AMOUNT] per [PERIOD]\n4. DEPOSIT: N[AMOUNT] refundable\n5. USE: [Residential/Commercial] only\n6. MAINTENANCE: Tenant keeps premises in good condition\n7. ALTERATIONS: None without Landlord's consent\n8. TERMINATION: [NOTICE PERIOD] written notice\n9. LAW: Lagos Tenancy Law (or applicable state law)\n\nSIGNED:\n_______________ _______________\nLandlord        Tenant\nWITNESS: _______________\n"},
        {"id":"3","name":"Power of Attorney","cat":"Litigation","content":"GENERAL POWER OF ATTORNEY\n\nI, [GRANTOR NAME], of [ADDRESS], appoint [ATTORNEY NAME] of [ADDRESS] as my Attorney to:\n\n1. Demand, sue for, recover and collect all monies due\n2. Sign and execute contracts and documents\n3. Appear before any court or tribunal\n4. Operate bank accounts\n5. Manage properties and collect rents\n6. Execute and register deeds\n\nThis Power remains in force until revoked in writing.\n\nDated: [DATE]\n_______________\n[GRANTOR NAME]\nWITNESS: _______________\n"},
        {"id":"4","name":"Written Address","cat":"Litigation","content":"IN THE [COURT NAME]\nSUIT NO: [NUMBER]\n\n[PLAINTIFF] v. [DEFENDANT]\n\nWRITTEN ADDRESS OF THE [PLAINTIFF/DEFENDANT]\n\n1.0 INTRODUCTION\nFiled pursuant to the Rules of this Honourable Court.\n\n2.0 FACTS\n[Narration]\n\n3.0 ISSUES\n3.1 Whether [Issue 1]\n3.2 Whether [Issue 2]\n\n4.0 ARGUMENTS\n[Arguments with authorities]\n\n5.0 CONCLUSION\nWe urge this Court to: (a) [Prayer 1] (b) [Prayer 2]\n\nDated: [DATE]\n_______________\n[COUNSEL]\nFor: [LAW FIRM]\n"},
        {"id":"5","name":"Affidavit","cat":"Litigation","content":"IN THE [COURT NAME]\nSUIT NO: [NUMBER]\n\n[PLAINTIFF] v. [DEFENDANT]\n\nAFFIDAVIT IN SUPPORT OF [MOTION]\n\nI, [DEPONENT], [Gender], [Religion], Nigerian, of [ADDRESS], make oath:\n\n1. I am the [Party] and familiar with the facts.\n2. [Fact 1]\n3. [Fact 2]\n4. This Affidavit is made in good faith.\n5. Facts are true to my knowledge and belief.\n\n_______________\nDEPONENT\n\nSworn at [Location] this [DATE]\nBefore: _______________\nCOMMISSIONER FOR OATHS\n"},
        {"id":"6","name":"Legal Opinion","cat":"Corporate","content":"LEGAL OPINION — PRIVATE & CONFIDENTIAL\n\nTO: [CLIENT] | FROM: [LAW FIRM] | DATE: [DATE]\nRE: [SUBJECT]\n\n1.0 INTRODUCTION\n[Instruction summary]\n\n2.0 FACTS\n[Background]\n\n3.0 ISSUES\n[Issues for consideration]\n\n4.0 LEGAL FRAMEWORK\n[Statutes, regulations, case law]\n\n5.0 ANALYSIS\n[Analysis per issue]\n\n6.0 CONCLUSION\n[Conclusions and recommendations]\n\n7.0 CAVEATS\nBased solely on Nigerian law and facts provided.\n\n_______________\n[PARTNER]\nFor: [LAW FIRM]\n"},
        {"id":"7","name":"Demand Letter","cat":"Litigation","content":"[LETTERHEAD]\n[DATE]\n\n[RECIPIENT]\n\nRE: DEMAND FOR N[AMOUNT] — [DESCRIPTION]\nOUR CLIENT: [CLIENT NAME]\n\nWe are Solicitors to [CLIENT] and write on instruction.\n\nFacts:\n1. [Background]\n2. [Obligation]\n3. [Breach]\n\nYou owe N[AMOUNT]. Despite demands you have failed to pay.\n\nPay within 7 DAYS or we institute proceedings, seeking:\n(a) Interest at [RATE]% p.a.\n(b) Legal costs\n(c) General damages\n\nGovern yourself accordingly.\n\n_______________\n[COUNSEL]\nFor: [LAW FIRM]\n"},
        {"id":"8","name":"Board Resolution","cat":"Corporate","content":"BOARD RESOLUTION — [COMPANY] (RC: [NUMBER])\n[VENUE] — [DATE]\n\nPRESENT: [Directors]\nIN ATTENDANCE: [Company Secretary]\n\nRESOLUTION: [TITLE]\n\nWHEREAS: [Background and reason]\n\nRESOLVED:\n1. [Resolution]\n2. Any Director authorized to execute necessary documents.\n3. Company Secretary to file returns with CAC.\n\nCERTIFIED TRUE COPY\n_______________\nCompany Secretary\n"},
    ]


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
def _id() -> str: return uuid.uuid4().hex[:8]
def _cur(a: float) -> str: return f"₦{a:,.2f}"
def _esc(t: str) -> str: return html.escape(str(t))

def _fdate(s: str) -> str:
    try: return datetime.fromisoformat(s).strftime("%B %d, %Y")
    except (ValueError, TypeError): return str(s)

def _days(s: str) -> int:
    try: return (datetime.fromisoformat(s).date() - datetime.now().date()).days
    except (ValueError, TypeError): return 999

def _rel(s: str) -> str:
    d = _days(s)
    if d == 0: return "Today"
    if d == 1: return "Tomorrow"
    if d == -1: return "Yesterday"
    if 0 < d <= 7: return f"In {d} days"
    if -7 <= d < 0: return f"{abs(d)} days ago"
    return _fdate(s)

def _norm(n: str) -> str:
    c = (n or "").strip(); m = MODEL_MIGRATION_MAP.get(c, c)
    return m if m in SUPPORTED_MODELS else DEFAULT_MODEL

def _model() -> str: return _norm(st.session_state.get("gemini_model", DEFAULT_MODEL))

def _sec(k: str, d: str = "") -> str:
    try: return st.secrets[k]
    except: return d


# ═══════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════
for _k, _v in {"api_key": "", "api_configured": False, "cases": [], "clients": [],
    "time_entries": [], "invoices": [], "last_response": "", "research_results": "",
    "gemini_model": DEFAULT_MODEL, "loaded_template": "", "theme": "🌿 Emerald",
    "admin_unlocked": False}.items():
    if _k not in st.session_state: st.session_state[_k] = _v

st.markdown(_BASE_CSS, unsafe_allow_html=True)
st.markdown(THEMES.get(st.session_state.theme, _THEME_EMERALD), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# API LAYER
# ═══════════════════════════════════════════════════════════════
def _key() -> str:
    for fn in [lambda: _sec("GEMINI_API_KEY"), lambda: os.getenv("GEMINI_API_KEY",""), lambda: st.session_state.get("api_key","")]:
        k = fn()
        if k and k.strip(): return k.strip()
    return ""

def _cfg(k: str): genai.configure(api_key=k, transport="rest")

def api_connect(k: str, m: str | None = None) -> bool:
    sel = _norm(m or DEFAULT_MODEL)
    try:
        _cfg(k); genai.GenerativeModel(sel).generate_content("OK", generation_config={"max_output_tokens": 8})
        st.session_state.update(api_configured=True, api_key=k, gemini_model=sel); return True
    except Exception as e:
        s = str(e)
        if "403" in s: st.error("API key invalid or lacks permission.")
        elif "429" in s: st.error("Rate limit exceeded.")
        else: st.error(f"API error: {s}")
        return False

def _auto():
    if st.session_state.api_configured: return
    k = _key()
    if k and len(k) >= 10:
        _cfg(k); st.session_state.update(api_key=k, api_configured=True)
        m = _sec("GEMINI_MODEL") or os.getenv("GEMINI_MODEL","")
        if m: st.session_state.gemini_model = _norm(m)

def _gen(prompt: str, sys: str) -> str:
    k = _key()
    if not k: return "⚠️ No API key configured."
    _cfg(k)
    try: model = genai.GenerativeModel(_model(), system_instruction=sys)
    except TypeError:
        model = genai.GenerativeModel(_model()); prompt = f"{sys}\n\n{prompt}"
    for attempt in range(2):
        try: return model.generate_content(prompt, generation_config=GEN_CONFIG).text
        except Exception as e:
            if attempt == 1: return f"Error: {e}"
            time.sleep(1.5)
    return "Error: generation failed."

def ai_respond(prompt: str, task: str) -> str:
    if not st.session_state.api_configured: return "⚠️ Configure your API key first."
    label = TASK_TYPES.get(task, {}).get("label", "General Query")
    return _gen(f"[Task: {label}]\n\n{prompt}", SYSTEM_INSTRUCTION)

def ai_research(q: str) -> str:
    if not st.session_state.api_configured: return "⚠️ Configure your API key first."
    return _gen(q, RESEARCH_INSTRUCTION)


# ═══════════════════════════════════════════════════════════════
# DATA CRUD
# ═══════════════════════════════════════════════════════════════
def add_case(d): d.update(id=_id(), created_at=datetime.now().isoformat()); st.session_state.cases.append(d)
def upd_case(cid, u):
    for c in st.session_state.cases:
        if c["id"]==cid: c.update(u); c["updated_at"]=datetime.now().isoformat(); return
def del_case(cid): st.session_state.cases=[c for c in st.session_state.cases if c["id"]!=cid]
def add_client(d): d.update(id=_id(), created_at=datetime.now().isoformat()); st.session_state.clients.append(d)
def del_client(cid): st.session_state.clients=[c for c in st.session_state.clients if c["id"]!=cid]
def client_name(cid):
    for c in st.session_state.clients:
        if c["id"]==cid: return c["name"]
    return "—"
def add_entry(d): d.update(id=_id(), created_at=datetime.now().isoformat(), amount=d["hours"]*d["rate"]); st.session_state.time_entries.append(d)
def del_entry(eid): st.session_state.time_entries=[e for e in st.session_state.time_entries if e["id"]!=eid]
def make_invoice(cid):
    ents=[e for e in st.session_state.time_entries if e.get("client_id")==cid]
    if not ents: return None
    inv={"id":_id(),"invoice_no":f"INV-{datetime.now():%Y%m%d}-{_id()[:4].upper()}","client_id":cid,
         "client_name":client_name(cid),"entries":ents,"total":sum(e["amount"] for e in ents),
         "date":datetime.now().isoformat(),"status":"Draft"}
    st.session_state.invoices.append(inv); return inv

def _tb(): return sum(e.get("amount",0) for e in st.session_state.time_entries)
def _th(): return sum(e.get("hours",0) for e in st.session_state.time_entries)
def _cb(cid): return sum(e.get("amount",0) for e in st.session_state.time_entries if e.get("client_id")==cid)
def _cc(cid): return sum(1 for c in st.session_state.cases if c.get("client_id")==cid)

def _hearings(n=10):
    h=[{"id":c["id"],"title":c["title"],"date":c["next_hearing"],"court":c.get("court",""),"suit":c.get("suit_no","")}
       for c in st.session_state.cases if c.get("next_hearing") and c.get("status")=="Active"]
    h.sort(key=lambda x:x["date"]); return h[:n]
    # ═══════════════════════════════════════════════════════════════
# UI: SIDEBAR
# ═══════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("### 🎨 Theme")
        th = st.selectbox("t", list(THEMES.keys()),
            index=list(THEMES.keys()).index(st.session_state.theme) if st.session_state.theme in THEMES else 0,
            label_visibility="collapsed")
        if th != st.session_state.theme: st.session_state.theme = th; st.rerun()

        st.divider()
        st.markdown("### 🤖 AI Engine")
        if st.session_state.api_configured: st.success(f"✅ Connected · `{_model()}`")
        else: st.warning("⚠️ Not connected")
        idx = SUPPORTED_MODELS.index(_model()) if _model() in SUPPORTED_MODELS else 0
        sel = st.selectbox("Model", SUPPORTED_MODELS, index=idx)
        if _norm(sel) != st.session_state.gemini_model:
            st.session_state.gemini_model = _norm(sel); st.session_state.api_configured = False; st.rerun()

        has_sec = bool(_sec("GEMINI_API_KEY")); adm_pw = _sec("ADMIN_PASSWORD")
        show = False
        if not has_sec:
            if adm_pw:
                with st.expander("🔒 Admin"):
                    if st.text_input("Password", type="password", key="apw") == adm_pw: st.session_state.admin_unlocked = True
                    if st.session_state.admin_unlocked: show = True
            else: show = True
        elif adm_pw:
            with st.expander("🔒 Admin"):
                if st.text_input("Password", type="password", key="apw") == adm_pw: st.session_state.admin_unlocked = True
                if st.session_state.admin_unlocked: show = True

        if show:
            ki = st.text_input("API Key", type="password", value=st.session_state.api_key, label_visibility="collapsed",
                               placeholder="Paste your Gemini API key…")
            if st.button("Connect", type="primary", use_container_width=True):
                if ki and len(ki.strip()) >= 10:
                    with st.spinner("Connecting…"):
                        if api_connect(ki.strip(), st.session_state.gemini_model): st.success("✅ Done!"); st.rerun()
                else: st.warning("Enter a valid key.")
            st.caption("[Get free key →](https://aistudio.google.com/app/apikey)")

        st.divider()
        st.markdown("### 💾 Data")
        if st.button("📥 Export All", use_container_width=True):
            st.download_button("Download", json.dumps({"cases":st.session_state.cases,"clients":st.session_state.clients,
                "time_entries":st.session_state.time_entries,"invoices":st.session_state.invoices}, indent=2),
                f"lexiassist_{datetime.now():%Y%m%d}.json", "application/json")
        up = st.file_uploader("📤 Import", type=["json"])
        if up:
            try:
                d = json.load(up)
                for k in ["cases","clients","time_entries","invoices"]: st.session_state[k] = d.get(k, [])
                st.success("Imported!"); st.rerun()
            except Exception as e: st.error(str(e))
        st.divider()
        st.caption("**LexiAssist v3.5** · © 2026\n\n🤖 Gemini · 🎈 Streamlit · 🐍 Python")


# ═══════════════════════════════════════════════════════════════
# PAGE: LANDING (complete redesign)
# ═══════════════════════════════════════════════════════════════
def render_landing():
    # Hero
    api_status = "🟢 AI Ready" if st.session_state.api_configured else "🔴 Configure API Key in Sidebar"
    st.markdown(f"""
    <div class="hero">
        <div class="hero-badge">{api_status}</div>
        <h1>The Future of<br>Legal Practice in Nigeria</h1>
        <p>AI-powered tools built exclusively for Nigerian lawyers. Draft documents, research case law,
        manage cases, track billing — all in one intelligent platform powered by Google Gemini.</p>
        <div class="hero-badge" style="margin-top:.75rem">🇳🇬 Made for Nigerian Law · CFRN 1999 · Federal & State Legislation · Case Law</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    # Stats
    active = len([c for c in st.session_state.cases if c.get("status") == "Active"])
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="stat-card"><div class="stat-value">{active}</div><div class="stat-label">📁 Active Cases</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-card t-blue"><div class="stat-value">{len(st.session_state.clients)}</div><div class="stat-label">👥 Clients</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="stat-card t-purple"><div class="stat-value">{_esc(_cur(_tb()))}</div><div class="stat-label">💰 Billable</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="stat-card t-amber"><div class="stat-value">{len(_hearings())}</div><div class="stat-label">📅 Hearings</div></div>', unsafe_allow_html=True)

    st.markdown("")

    # Features
    st.markdown("#### What Can LexiAssist Do?")
    features = [
        ("🤖", "AI Legal Assistant", "Draft contracts, analyze issues, interpret statutes — instant AI-powered legal guidance."),
        ("📚", "Legal Research", "Deep research across Nigerian statutes, case law, and legal principles."),
        ("📁", "Case Management", "Track suits, hearing dates, statuses, notes, and client linkages."),
        ("📅", "Court Calendar", "Visual hearing timeline with urgency-coded reminders so you never miss a date."),
        ("📋", "Document Templates", "8 professional Nigerian templates — contracts, affidavits, opinions, resolutions."),
        ("👥", "Client Management", "Client records, case counts, and per-client billing at a glance."),
        ("💰", "Billing & Invoicing", "Log hours, set rates, and generate downloadable professional invoices."),
        ("🇳🇬", "Nigerian Legal Tools", "Limitation periods, interest calculator, court hierarchy, legal maxims."),
    ]
    cols = st.columns(4)
    for i, (ic, t, d) in enumerate(features):
        with cols[i % 4]:
            st.markdown(f'<div class="feat-card"><span class="feat-icon">{ic}</span><h4>{t}</h4><p>{d}</p></div>', unsafe_allow_html=True)

    st.markdown("")

    # Value propositions
    st.markdown("#### Why Nigerian Lawyers Choose LexiAssist")
    v1, v2, v3 = st.columns(3)
    with v1: st.markdown('<div class="value-card"><span class="v-icon">🇳🇬</span><h4>Built for Nigerian Law</h4><p>Trained on the Constitution, Federal & State Acts, Rules of Court, and landmark Nigerian case law. Not a generic tool — purpose-built for your jurisdiction.</p></div>', unsafe_allow_html=True)
    with v2: st.markdown('<div class="value-card"><span class="v-icon">🤖</span><h4>Powered by Google Gemini</h4><p>State-of-the-art AI that understands legal reasoning, IRAC methodology, and can draft, analyze, and research with remarkable depth.</p></div>', unsafe_allow_html=True)
    with v3: st.markdown('<div class="value-card"><span class="v-icon">🔒</span><h4>Private & Secure</h4><p>Your API key stays in your session. No data is stored on external servers. Your practice data remains entirely under your control.</p></div>', unsafe_allow_html=True)

    st.markdown("")

    # Upcoming hearings & recent cases (only if data exists)
    hearings = _hearings(5)
    recent = st.session_state.cases[-5:] if st.session_state.cases else []
    if hearings or recent:
        left, right = st.columns(2)
        if hearings:
            with left:
                st.markdown("#### 📅 Upcoming Hearings")
                for h in hearings:
                    d = _days(h["date"])
                    u = "urgent" if d <= 3 else ("warn" if d <= 7 else "ok")
                    b = "danger" if d <= 3 else ("warning" if d <= 7 else "success")
                    st.markdown(f'<div class="cal-event {u}"><strong>{_esc(h["title"])}</strong> · {_esc(h["suit"])}<br>'
                        f'{_esc(_fdate(h["date"]))} <span class="badge badge-{b}">{_esc(_rel(h["date"]))}</span></div>', unsafe_allow_html=True)
        if recent:
            with right:
                st.markdown("#### 📁 Recent Cases")
                for c in reversed(recent):
                    bc = {"Active":"success","Pending":"warning","Completed":"info"}.get(c.get("status",""),"info")
                    st.markdown(f'<div class="custom-card" style="padding:1rem"><strong>{_esc(c["title"])}</strong> '
                        f'<span class="badge badge-{bc}">{_esc(c.get("status",""))}</span><br>'
                        f'<small>{_esc(c.get("suit_no",""))} · {_esc(c.get("court",""))}</small></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: AI ASSISTANT (REBUILT — bulletproof selectbox + template loader)
# ═══════════════════════════════════════════════════════════════
def render_ai():
    st.markdown('<div class="page-header"><h1>🤖 AI Legal Assistant</h1><p>Draft · Analyze · Research · Interpret — powered by Google Gemini</p></div>', unsafe_allow_html=True)

    if not st.session_state.api_configured:
        st.warning("⚠️ **Connect your API key** in the sidebar to activate the AI assistant.")

    # ── Task Type: st.selectbox — 100% reliable ─────────────
    task_keys = list(TASK_TYPES.keys())
    task_labels = {k: f"{v['icon']} {v['label']} — {v['desc']}" for k, v in TASK_TYPES.items()}

    chosen_task = st.selectbox(
        "🎯 Task Type",
        task_keys,
        index=task_keys.index("general"),
        format_func=lambda k: task_labels[k],
        key="task_type_selectbox",
    )

    st.markdown("---")

    # ── Template Loader — inline expander ────────────────────
    with st.expander("📋 Load a Document Template", expanded=False):
        templates = get_templates()
        tmpl_names = [t["name"] for t in templates]
        chosen_tmpl = st.selectbox("Choose template", tmpl_names, key="tmpl_chooser")
        if st.button("✅ Load into Editor Below", type="primary", use_container_width=True):
            for t in templates:
                if t["name"] == chosen_tmpl:
                    st.session_state.loaded_template = t["content"]
                    st.rerun()

    # ── Input ────────────────────────────────────────────────
    prefill = st.session_state.pop("loaded_template", "")
    user_input = st.text_area(
        "📝 Your Legal Query or Instructions",
        value=prefill, height=220,
        placeholder="Example: Draft a commercial lease agreement for property in Victoria Island, Lagos, "
                    "with a 3-year term, annual rent review clause, and break option after 18 months…")

    c1, c2 = st.columns([3, 1])
    with c1:
        generate = st.button("✨ Generate Response", type="primary", use_container_width=True,
                             disabled=not st.session_state.api_configured)
    with c2:
        clear = st.button("🗑️ Clear Response", use_container_width=True,
                          disabled=not bool(st.session_state.last_response))

    if generate:
        if user_input.strip():
            with st.spinner("⚖️ LexiAssist is working…"):
                task_key = st.session_state.get("task_type_selectbox", "general")
                result = ai_respond(user_input, task_key)
                if not result.startswith("Error") and not result.startswith("⚠️"):
                    st.session_state.last_response = result
                else:
                    st.error(result)
        else:
            st.warning("Please enter a query or load a template first.")

    if clear:
        st.session_state.last_response = ""; st.rerun()

    # ── Response ─────────────────────────────────────────────
    if st.session_state.last_response:
        st.markdown("---")
        st.markdown("#### 📄 Response")
        ec1, ec2, ec3 = st.columns([1, 1, 4])
        with ec1:
            st.download_button("📥 .txt", st.session_state.last_response,
                f"LexiAssist_{datetime.now():%Y%m%d_%H%M}.txt", "text/plain")
        with ec2:
            esc = _esc(st.session_state.last_response)
            doc = (f"<!DOCTYPE html><html><head><meta charset='UTF-8'><title>LexiAssist</title>"
                f"<style>body{{font-family:Georgia,serif;line-height:1.8;max-width:800px;margin:40px auto;padding:20px}}"
                f"h1{{color:#059669;border-bottom:3px solid #059669;padding-bottom:12px}}.c{{white-space:pre-wrap}}"
                f".d{{background:#fef3c7;border-left:4px solid #f59e0b;padding:16px;margin-top:32px}}</style></head>"
                f"<body><h1>⚖️ LexiAssist</h1><div class='c'>{esc}</div>"
                f"<div class='d'><b>Disclaimer:</b> For informational purposes only.</div>"
                f"<p style='text-align:center;color:#64748b;font-size:12px;margin-top:32px'>"
                f"Generated {datetime.now():%B %d, %Y %I:%M %p}</p></body></html>")
            st.download_button("📥 .html", doc, f"LexiAssist_{datetime.now():%Y%m%d_%H%M}.html", "text/html")
        with ec3:
            if st.button("🗑️ Clear", key="clr2"): st.session_state.last_response = ""; st.rerun()

        st.markdown(f'<div class="response-box">{_esc(st.session_state.last_response)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> This response is for informational purposes only. '
            'It does not constitute legal advice. Verify all citations and consult a qualified legal practitioner.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: RESEARCH
# ═══════════════════════════════════════════════════════════════
def render_research():
    st.markdown('<div class="page-header"><h1>📚 Legal Research</h1><p>AI-powered research across Nigerian statutes, case law & legal principles</p></div>', unsafe_allow_html=True)
    q = st.text_input("🔍 Research Query", placeholder="E.g. 'employer liability for workplace injury under Nigerian law'")
    rc1, rc2 = st.columns([3, 1])
    with rc1:
        go = st.button("🔍 Research", type="primary", use_container_width=True, disabled=not st.session_state.api_configured)
    with rc2:
        clr = st.button("🗑️ Clear", use_container_width=True, disabled=not bool(st.session_state.research_results), key="rclr")
    if go and q.strip():
        with st.spinner("📚 Researching…"): st.session_state.research_results = ai_research(q)
    if clr: st.session_state.research_results = ""; st.rerun()
    if not st.session_state.api_configured: st.info("💡 Connect your API key in the sidebar.")
    if st.session_state.research_results:
        st.markdown("---")
        st.download_button("📥 Export", st.session_state.research_results, f"Research_{datetime.now():%Y%m%d_%H%M}.txt", "text/plain")
        st.markdown(f'<div class="response-box">{_esc(st.session_state.research_results)}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: CASES
# ═══════════════════════════════════════════════════════════════
def render_cases():
    st.markdown('<div class="page-header"><h1>📁 Case Management</h1><p>Track suits, hearings, and case progress</p></div>', unsafe_allow_html=True)
    with st.expander("➕ Add New Case", expanded=not bool(st.session_state.cases)):
        with st.form("cf"):
            a, b = st.columns(2)
            with a: title=st.text_input("Case Title *"); suit=st.text_input("Suit Number *"); court=st.text_input("Court")
            with b:
                nh=st.date_input("Next Hearing"); status=st.selectbox("Status",CASE_STATUSES)
                cn=["—"]+[c["name"] for c in st.session_state.clients]
                ci=st.selectbox("Client",range(len(cn)),format_func=lambda i:cn[i])
            notes=st.text_area("Notes")
            if st.form_submit_button("Save", type="primary"):
                if title.strip() and suit.strip():
                    cid=st.session_state.clients[ci-1]["id"] if ci>0 else None
                    add_case({"title":title.strip(),"suit_no":suit.strip(),"court":court.strip(),
                        "next_hearing":nh.isoformat() if nh else None,"status":status,"client_id":cid,"notes":notes.strip()})
                    st.success("✅ Added!"); st.rerun()
                else: st.error("Title and Suit Number required.")

    filt=st.selectbox("Filter",["All"]+CASE_STATUSES,key="cfilt")
    cases=st.session_state.cases if filt=="All" else [c for c in st.session_state.cases if c.get("status")==filt]
    if not cases: st.info("📁 No cases. Add one above!"); return
    for case in cases:
        bc={"Active":"success","Pending":"warning","Completed":"info","Archived":""}.get(case.get("status",""),"")
        hh=f"<p>📅 <strong>Next:</strong> {_esc(_fdate(case['next_hearing']))} ({_esc(_rel(case['next_hearing']))})</p>" if case.get("next_hearing") else ""
        nn=f"<p style='color:#64748b'><em>{_esc(case['notes'])}</em></p>" if case.get("notes") else ""
        a,b=st.columns([5,1])
        with a:
            st.markdown(f'<div class="custom-card"><h4>{_esc(case["title"])} <span class="badge badge-{bc}">{_esc(case.get("status",""))}</span></h4>'
                f'<p>⚖️ {_esc(case.get("suit_no",""))} · 🏛️ {_esc(case.get("court",""))} · 👤 {_esc(client_name(case.get("client_id","")))}</p>'
                f'{hh}{nn}</div>', unsafe_allow_html=True)
        with b:
            ns=st.selectbox("S",CASE_STATUSES,index=CASE_STATUSES.index(case["status"]) if case.get("status") in CASE_STATUSES else 0,key=f"s{case['id']}",label_visibility="collapsed")
            if ns!=case.get("status"): upd_case(case["id"],{"status":ns}); st.rerun()
            if st.button("🗑️",key=f"d{case['id']}"): del_case(case["id"]); st.rerun()


# ═══════════════════════════════════════════════════════════════
# PAGE: CALENDAR
# ═══════════════════════════════════════════════════════════════
def render_calendar():
    st.markdown('<div class="page-header"><h1>📅 Court Calendar</h1><p>Upcoming hearings at a glance</p></div>', unsafe_allow_html=True)
    hearings=_hearings()
    if not hearings: st.info("📅 No upcoming hearings. Add hearing dates to active cases."); return
    for h in hearings:
        d=_days(h["date"]); u="urgent" if d<=3 else ("warn" if d<=7 else "ok"); b="danger" if d<=3 else ("warning" if d<=7 else "success")
        st.markdown(f'<div class="cal-event {u}"><h4>{_esc(h["title"])}</h4>'
            f'<p>⚖️ {_esc(h["suit"])} · 🏛️ {_esc(h["court"])}</p>'
            f'<p>📅 {_esc(_fdate(h["date"]))} <span class="badge badge-{b}">{_esc(_rel(h["date"]))}</span></p></div>', unsafe_allow_html=True)
    st.markdown("---")
    df=pd.DataFrame([{"Case":h["title"],"Days":max(_days(h["date"]),0),"Date":_fdate(h["date"])} for h in hearings])
    fig=px.bar(df,x="Days",y="Case",orientation="h",text="Date",color="Days",
        color_continuous_scale=["#ef4444","#f59e0b","#10b981"],title="Days Until Hearings")
    fig.update_layout(yaxis={"categoryorder":"total ascending"},showlegend=False); st.plotly_chart(fig,use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: TEMPLATES
# ═══════════════════════════════════════════════════════════════
def render_templates():
    st.markdown('<div class="page-header"><h1>📋 Document Templates</h1><p>Professional Nigerian legal templates</p></div>', unsafe_allow_html=True)
    templates=get_templates(); cats=sorted({t["cat"] for t in templates})
    sel=st.selectbox("Category",["All"]+cats,key="tcat")
    vis=templates if sel=="All" else [t for t in templates if t["cat"]==sel]
    cols=st.columns(2)
    for i,t in enumerate(vis):
        with cols[i%2]:
            st.markdown(f'<div class="tmpl-card"><h4>📄 {_esc(t["name"])}</h4>'
                f'<span class="badge badge-success">{_esc(t["cat"])}</span>'
                f'<p style="margin-top:.5rem;color:#64748b;font-size:.82rem">{_esc(t["content"][:120])}…</p></div>', unsafe_allow_html=True)
            a,b=st.columns(2)
            with a:
                if st.button("📋 Load to AI",key=f"u{t['id']}",use_container_width=True):
                    st.session_state.loaded_template=t["content"]; st.success(f"'{t['name']}' loaded!"); st.rerun()
            with b:
                if st.button("👁️ Preview",key=f"p{t['id']}",use_container_width=True): st.session_state["pv"]=t
    pv=st.session_state.get("pv")
    if pv:
        st.markdown("---"); st.markdown(f"### {pv['name']}"); st.code(pv["content"],language=None)
        a,b=st.columns([1,4])
        with a:
            if st.button("Close"): del st.session_state["pv"]; st.rerun()
        with b: st.download_button("📥 Download",pv["content"],f"{pv['name'].replace(' ','_')}.txt","text/plain")


# ═══════════════════════════════════════════════════════════════
# PAGE: CLIENTS
# ═══════════════════════════════════════════════════════════════
def render_clients():
    st.markdown('<div class="page-header"><h1>👥 Client Management</h1><p>Manage clients, link to cases & billing</p></div>', unsafe_allow_html=True)
    with st.expander("➕ Add Client",expanded=not bool(st.session_state.clients)):
        with st.form("clf"):
            a,b=st.columns(2)
            with a: name=st.text_input("Name *"); email=st.text_input("Email"); phone=st.text_input("Phone")
            with b: ct=st.selectbox("Type",CLIENT_TYPES); addr=st.text_input("Address"); notes=st.text_area("Notes")
            if st.form_submit_button("Save",type="primary"):
                if name.strip():
                    add_client({"name":name.strip(),"email":email.strip(),"phone":phone.strip(),"type":ct,"address":addr.strip(),"notes":notes.strip()})
                    st.success("✅ Added!"); st.rerun()
                else: st.error("Name required.")
    if not st.session_state.clients: st.info("👥 No clients yet."); return
    cols=st.columns(2)
    for i,cl in enumerate(st.session_state.clients):
        with cols[i%2]:
            cc,cb=_cc(cl["id"]),_cb(cl["id"])
            el=f"<p>📧 {_esc(cl['email'])}</p>" if cl.get("email") else ""
            pl=f"<p>📱 {_esc(cl['phone'])}</p>" if cl.get("phone") else ""
            al=f"<p>📍 {_esc(cl['address'])}</p>" if cl.get("address") else ""
            st.markdown(f'<div class="custom-card"><h4>{_esc(cl["name"])} <span class="badge badge-info">{_esc(cl.get("type",""))}</span></h4>'
                f'{el}{pl}{al}<hr style="margin:.75rem 0">'
                f'<div style="display:flex;justify-content:space-around;text-align:center">'
                f'<div><div style="font-size:1.5rem;font-weight:700;color:#059669">{cc}</div><div style="font-size:.7rem;color:#64748b">CASES</div></div>'
                f'<div><div style="font-size:1.5rem;font-weight:700;color:#7c3aed">{_esc(_cur(cb))}</div><div style="font-size:.7rem;color:#64748b">BILLABLE</div></div>'
                f'</div></div>', unsafe_allow_html=True)
            a,b=st.columns(2)
            with a:
                if cb>0 and st.button("📄 Invoice",key=f"iv{cl['id']}",use_container_width=True):
                    inv=make_invoice(cl["id"])
                    if inv: st.success(f"{inv['invoice_no']}!"); st.rerun()
            with b:
                if st.button("🗑️",key=f"dc{cl['id']}",use_container_width=True): del_client(cl["id"]); st.rerun()


# ═══════════════════════════════════════════════════════════════
# PAGE: BILLING
# ═══════════════════════════════════════════════════════════════
def render_billing():
    st.markdown('<div class="page-header"><h1>💰 Billing & Time Tracking</h1><p>Log hours, generate invoices</p></div>', unsafe_allow_html=True)
    s1,s2,s3=st.columns(3)
    with s1: st.markdown(f'<div class="stat-card"><div class="stat-value">{_esc(_cur(_tb()))}</div><div class="stat-label">💰 Total</div></div>', unsafe_allow_html=True)
    with s2: st.markdown(f'<div class="stat-card t-blue"><div class="stat-value">{_th():.1f}h</div><div class="stat-label">⏱️ Hours</div></div>', unsafe_allow_html=True)
    with s3: st.markdown(f'<div class="stat-card t-purple"><div class="stat-value">{len(st.session_state.invoices)}</div><div class="stat-label">📄 Invoices</div></div>', unsafe_allow_html=True)
    st.markdown("---")
    with st.expander("⏱️ Log Time",expanded=False):
        with st.form("tf"):
            a,b=st.columns(2)
            with a:
                cn=["—"]+[c["name"] for c in st.session_state.clients]; ci=st.selectbox("Client *",range(len(cn)),format_func=lambda i:cn[i])
                csn=["—"]+[c["title"] for c in st.session_state.cases]; csi=st.selectbox("Case",range(len(csn)),format_func=lambda i:csn[i])
                ed=st.date_input("Date",datetime.now())
            with b:
                hrs=st.number_input("Hours *",.25,step=.25,value=1.0); rate=st.number_input("Rate (₦/hr) *",0,value=50000,step=5000)
                st.markdown(f"**Total: {_cur(hrs*rate)}**")
            desc=st.text_area("Description *")
            if st.form_submit_button("Save",type="primary"):
                if ci>0 and desc.strip():
                    add_entry({"client_id":st.session_state.clients[ci-1]["id"],
                        "case_id":st.session_state.cases[csi-1]["id"] if csi>0 else None,
                        "date":ed.isoformat(),"hours":hrs,"rate":rate,"description":desc.strip()})
                    st.success("✅ Logged!"); st.rerun()
                else: st.error("Select client + description.")
    if not st.session_state.time_entries: st.info("No entries yet."); return
    rows=[{"Date":_fdate(e["date"]),"Client":client_name(e.get("client_id","")),"Desc":e["description"][:50]+("…" if len(e["description"])>50 else ""),
           "Hours":f"{e['hours']}h","Rate":_cur(e["rate"]),"Amount":_cur(e["amount"]),"ID":e["id"]} for e in reversed(st.session_state.time_entries)]
    st.dataframe(pd.DataFrame(rows).drop(columns=["ID"]),use_container_width=True,hide_index=True)
    labs=[f"{r['Date']} — {r['Client']} — {r['Desc']}" for r in rows]
    sd=st.selectbox("Delete entry",["None"]+labs,key="de")
    if sd!="None" and st.button("🗑️ Delete"): del_entry(rows[labs.index(sd)]["ID"]); st.rerun()
    if len(rows)>1:
        st.markdown("---"); tots:dict[str,float]={}
        for e in st.session_state.time_entries: cn2=client_name(e.get("client_id","")); tots[cn2]=tots.get(cn2,0)+e["amount"]
        st.plotly_chart(px.pie(values=list(tots.values()),names=list(tots.keys()),title="Billable by Client"),use_container_width=True)
    if st.session_state.invoices:
        st.markdown("---"); st.markdown("#### 📄 Invoices")
        for inv in reversed(st.session_state.invoices):
            with st.expander(f"📄 {inv['invoice_no']} — {inv['client_name']} — {_cur(inv['total'])}"):
                sep,dash="="*60,"-"*60
                lines=[sep,"INVOICE",sep,"",f"No: {inv['invoice_no']}",f"Date: {_fdate(inv['date'])}","",f"TO: {inv['client_name']}","",dash,"ENTRIES",dash]
                for i,e in enumerate(inv["entries"],1): lines+=["",f"{i}. {_fdate(e['date'])} — {e['description']}",f"   {e['hours']}h × {_cur(e['rate'])} = {_cur(e['amount'])}"]
                lines+=["",dash,f"TOTAL: {_cur(inv['total'])}",dash,"","Due upon receipt",sep]
                st.download_button("📥","\n".join(lines),f"{inv['invoice_no']}.txt","text/plain",key=f"dl{inv['id']}")


# ═══════════════════════════════════════════════════════════════
# PAGE: LEGAL TOOLS
# ═══════════════════════════════════════════════════════════════
def render_tools():
    st.markdown('<div class="page-header"><h1>🇳🇬 Nigerian Legal Tools</h1><p>Quick-access references & calculators</p></div>', unsafe_allow_html=True)
    tabs=st.tabs(["⏱️ Limitation Periods","💹 Interest Calculator","🏛️ Court Hierarchy","📖 Legal Maxims"])
    with tabs[0]:
        s=st.text_input("Search","",placeholder="e.g. contract, land…",key="ls")
        data=[l for l in LIMITATION_PERIODS if s.lower() in l["cause"].lower()] if s else LIMITATION_PERIODS
        if data: st.dataframe(pd.DataFrame(data).rename(columns={"cause":"Cause","period":"Period","authority":"Authority"}),use_container_width=True,hide_index=True)
        else: st.info("No match.")
    with tabs[1]:
        with st.form("ic"):
            a,b=st.columns(2)
            with a: p=st.number_input("Principal (₦)",0.0,value=1e6,step=5e4); r=st.number_input("Rate (% p.a.)",0.0,value=10.0,step=0.5)
            with b: m=st.number_input("Months",1,value=12); ct=st.selectbox("Type",["Simple","Compound (Monthly)"])
            if st.form_submit_button("Calculate",type="primary"):
                interest=p*(r/100)*(m/12) if ct=="Simple" else p*((1+(r/100)/12)**m)-p
                r1,r2,r3=st.columns(3)
                with r1: st.metric("Principal",_cur(p))
                with r2: st.metric("Interest",_cur(interest))
                with r3: st.metric("Total",_cur(p+interest))
                st.markdown(f'<div class="disclaimer"><strong>Draft clause:</strong> "…with interest at {r}% p.a. ({ct.lower()}) from [DATE], currently {_esc(_cur(interest))}."</div>',unsafe_allow_html=True)
    with tabs[2]:
        for c in COURT_HIERARCHY:
            ind="　"*(c["level"]-1); mk="🔸" if c["level"]==1 else "├─"
            st.markdown(f"{ind}{mk} **{c['icon']} {c['name']}**"); st.caption(f"{ind}　　{c['desc']}")
    with tabs[3]:
        sq=st.text_input("Search","",placeholder="e.g. nemo, audi…",key="ms")
        mx=[m for m in LEGAL_MAXIMS if sq.lower() in m["maxim"].lower() or sq.lower() in m["meaning"].lower()] if sq else LEGAL_MAXIMS
        if mx:
            for m in mx: st.markdown(f'<div class="tool-card"><h4 style="font-style:italic">{_esc(m["maxim"])}</h4><p>{_esc(m["meaning"])}</p></div>',unsafe_allow_html=True)
        else: st.info("No match.")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    _auto()
    render_sidebar()

    tabs = st.tabs([
        "🏠 Home", "🤖 AI Assistant", "📚 Research", "📁 Cases",
        "📅 Calendar", "📋 Templates", "👥 Clients", "💰 Billing", "🇳🇬 Legal Tools",
    ])
    with tabs[0]: render_landing()
    with tabs[1]: render_ai()
    with tabs[2]: render_research()
    with tabs[3]: render_cases()
    with tabs[4]: render_calendar()
    with tabs[5]: render_templates()
    with tabs[6]: render_clients()
    with tabs[7]: render_billing()
    with tabs[8]: render_tools()

    st.markdown(
        '<div class="app-footer">'
        '<p>⚖️ <strong>LexiAssist v3.5</strong></p>'
        '<p>Purpose-Built for Nigerian Lawyers · Powered by <a href="https://ai.google.dev" target="_blank">Google Gemini</a></p>'
        '<p style="font-size:.78rem;margin-top:.5rem">⚠️ LexiAssist provides legal information, not legal advice. '
        'Always verify references and consult a qualified legal practitioner.</p>'
        '<p style="font-size:.75rem;margin-top:.25rem">© 2026 LexiAssist. All rights reserved.</p>'
        '</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
