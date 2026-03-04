"""
LexiAssist v2.1 — AI-Powered Legal Practice Management for Nigerian Lawyers.

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
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Optional

import google.generativeai as genai
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("LexiAssist")

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="LexiAssist — Legal Practice Management",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "# LexiAssist v2.1\nAI-Powered Legal Practice Management for Nigerian Lawyers."},
)

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════
CASE_STATUSES: list[str] = ["Active", "Pending", "Completed", "Archived"]
CLIENT_TYPES: list[str] = ["Individual", "Corporate", "Government"]

TASK_TYPES: dict[str, dict[str, str]] = {
    "drafting":       {"label": "📄 Document Drafting",       "description": "Contracts, pleadings, applications, affidavits", "icon": "📄"},
    "analysis":       {"label": "🔍 Legal Analysis",          "description": "Issue spotting, IRAC/FILAC reasoning",          "icon": "🔍"},
    "research":       {"label": "📚 Legal Research",           "description": "Case law, statutes, authorities",               "icon": "📚"},
    "procedure":      {"label": "📋 Procedural Guidance",     "description": "Court filing, evidence rules",                  "icon": "📋"},
    "interpretation": {"label": "⚖️ Statutory Interpretation", "description": "Analyze and explain legislation",               "icon": "⚖️"},
    "general":        {"label": "💬 General Query",            "description": "Ask anything legal-related",                    "icon": "💬"},
}

MODEL_MIGRATION_MAP: dict[str, str] = {
    "gemini-2.0-flash": "gemini-2.5-flash",
    "gemini-2.0-flash-001": "gemini-2.5-flash",
    "gemini-2.0-flash-lite": "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite-001": "gemini-2.5-flash-lite",
}
SUPPORTED_MODELS: list[str] = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
DEFAULT_MODEL: str = "gemini-2.5-flash"

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
    "1. Brief restatement of the request.\n"
    "2. Key assumptions (if any).\n"
    "3. Detailed analysis or document draft.\n"
    "4. Relevant legal authorities.\n"
    "5. Caveats and recommendations."
)

RESEARCH_INSTRUCTION = (
    SYSTEM_INSTRUCTION
    + "\n\nFor legal research tasks, additionally provide:\n"
    "• Relevant Nigerian statutes with specific sections and any recent amendments.\n"
    "• Key case law: case names, citations (where known), holdings, and court level.\n"
    "• Fundamental legal principles and how Nigerian courts have interpreted them.\n"
    "• Practical application: procedural requirements, limitation periods, jurisdiction.\n"
    "• Common pitfalls, strategic considerations, and ADR options where relevant.\n"
    "• If uncertain about a specific citation, state the general principle instead."
)

GENERATION_CONFIG: dict[str, Any] = {"temperature": 0.7, "top_p": 0.95, "top_k": 40, "max_output_tokens": 8192}

# ── Nigerian Legal Data ──────────────────────────────────────
LIMITATION_PERIODS: list[dict[str, str]] = [
    {"cause": "Simple Contract", "period": "6 years", "authority": "Limitation Act, s. 8(1)(a)"},
    {"cause": "Tort / Negligence", "period": "6 years", "authority": "Limitation Act, s. 8(1)(a)"},
    {"cause": "Personal Injury", "period": "3 years", "authority": "Limitation Act, s. 8(1)(b) (varies by state)"},
    {"cause": "Defamation", "period": "3 years", "authority": "Limitation Act, s. 8(1)(b) (varies by state)"},
    {"cause": "Recovery of Land", "period": "12 years", "authority": "Limitation Act, s. 16"},
    {"cause": "Mortgage", "period": "12 years", "authority": "Limitation Act, s. 18"},
    {"cause": "Recovery of Rent", "period": "6 years", "authority": "Limitation Act, s. 19"},
    {"cause": "Enforcement of Judgment", "period": "12 years", "authority": "Limitation Act, s. 8(1)(d)"},
    {"cause": "Maritime Claims", "period": "2 years", "authority": "Admiralty Jurisdiction Act, s. 10"},
    {"cause": "Labour / Employment Disputes", "period": "12 months", "authority": "National Industrial Court Act, s. 7(1)(e)"},
    {"cause": "Fundamental Rights Enforcement", "period": "12 months", "authority": "FREP Rules, Order II r. 1"},
    {"cause": "Tax Assessment Appeal", "period": "30 days", "authority": "FIRS (Est.) Act, s. 59"},
    {"cause": "Public Officer Liability", "period": "3 months (pre-action notice) / 12 months", "authority": "Public Officers Protection Act, s. 2"},
    {"cause": "Insurance Claims", "period": "12 months after disclaimer", "authority": "Insurance Act 2003, s. 72"},
    {"cause": "Companies Winding-Up Petition", "period": "21 days from statutory demand", "authority": "CAMA 2020, s. 572"},
]

COURT_HIERARCHY: list[dict[str, Any]] = [
    {"level": 1, "name": "Supreme Court of Nigeria", "description": "Final appellate court — 7 or 5 Justices", "icon": "🏛️"},
    {"level": 2, "name": "Court of Appeal", "description": "Intermediate appellate court — 16 Divisions", "icon": "⚖️"},
    {"level": 3, "name": "Federal High Court", "description": "Federal causes: admiralty, revenue, IP, banking", "icon": "🏢"},
    {"level": 3, "name": "State High Courts", "description": "General civil & criminal jurisdiction per state", "icon": "🏢"},
    {"level": 3, "name": "National Industrial Court", "description": "Labour & employment disputes", "icon": "🏢"},
    {"level": 3, "name": "Sharia Court of Appeal", "description": "Islamic personal law appeals (Northern states)", "icon": "🏢"},
    {"level": 3, "name": "Customary Court of Appeal", "description": "Customary law appeals", "icon": "🏢"},
    {"level": 4, "name": "Magistrate / District Courts", "description": "Summary jurisdiction, minor offences", "icon": "📋"},
    {"level": 4, "name": "Area / Customary Courts", "description": "Customary law matters at first instance", "icon": "📋"},
    {"level": 4, "name": "Sharia Courts", "description": "Islamic personal law at first instance", "icon": "📋"},
    {"level": 5, "name": "Tribunals & Panels", "description": "Election Petition, Tax Appeal, Code of Conduct, etc.", "icon": "📌"},
]

LEGAL_MAXIMS: list[dict[str, str]] = [
    {"maxim": "Audi alteram partem", "meaning": "Hear the other side — a pillar of natural justice"},
    {"maxim": "Nemo judex in causa sua", "meaning": "No one should be a judge in their own cause"},
    {"maxim": "Actus non facit reum nisi mens sit rea", "meaning": "An act does not make one guilty unless the mind is guilty"},
    {"maxim": "Res judicata", "meaning": "A matter already judicially decided — cannot be re-litigated"},
    {"maxim": "Stare decisis", "meaning": "Stand by what has been decided — doctrine of precedent"},
    {"maxim": "Ubi jus ibi remedium", "meaning": "Where there is a right, there is a remedy"},
    {"maxim": "Volenti non fit injuria", "meaning": "No injury is done to one who consents"},
    {"maxim": "Pacta sunt servanda", "meaning": "Agreements must be honoured"},
    {"maxim": "Nemo dat quod non habet", "meaning": "No one gives what they do not have"},
    {"maxim": "Ignorantia legis neminem excusat", "meaning": "Ignorance of the law excuses no one"},
    {"maxim": "Qui facit per alium facit per se", "meaning": "He who acts through another acts himself (vicarious liability)"},
    {"maxim": "Ex turpi causa non oritur actio", "meaning": "No action arises from an immoral cause"},
    {"maxim": "Expressio unius est exclusio alterius", "meaning": "The express mention of one thing excludes others"},
    {"maxim": "Ejusdem generis", "meaning": "Of the same kind — general words limited by specific preceding words"},
    {"maxim": "Locus standi", "meaning": "The right or capacity to bring an action before a court"},
]


# ═══════════════════════════════════════════════════════════════
# THEMES
# ═══════════════════════════════════════════════════════════════
_BASE_CSS = """
<style>
.main .block-container{padding-top:2rem;padding-bottom:2rem;max-width:1200px}
.main-header{padding:1.5rem 2rem;border-radius:1rem;margin-bottom:2rem;color:white;box-shadow:0 10px 40px rgba(0,0,0,.2)}
.main-header h1{margin:0;font-size:2.5rem;font-weight:700}
.main-header p{margin:.5rem 0 0;opacity:.9;font-size:1rem}
.custom-card{border-radius:1rem;padding:1.5rem;box-shadow:0 4px 20px rgba(0,0,0,.08);border:1px solid;margin-bottom:1rem;transition:all .3s ease}
.custom-card:hover{box-shadow:0 8px 30px rgba(0,0,0,.12);transform:translateY(-2px)}
.stat-card{border-radius:1rem;padding:1.5rem;text-align:center;border:1px solid}
.stat-value{font-size:2rem;font-weight:700}
.stat-label{font-size:.875rem;margin-top:.25rem}
.badge{display:inline-block;padding:.25rem .75rem;border-radius:9999px;font-size:.75rem;font-weight:600;text-transform:uppercase}
.badge-success{background:#dcfce7;color:#166534}
.badge-warning{background:#fef3c7;color:#92400e}
.badge-info{background:#dbeafe;color:#1e40af}
.badge-danger{background:#fee2e2;color:#991b1b}
.response-box{border:1px solid;border-radius:.75rem;padding:1.5rem;margin:1rem 0;white-space:pre-wrap;font-family:'Georgia',serif;line-height:1.8}
.disclaimer{border-left:4px solid #f59e0b;padding:1rem;border-radius:0 .5rem .5rem 0;margin-top:1rem;font-size:.875rem}
.calendar-event{padding:1rem;border-radius:.75rem;margin-bottom:.75rem;border-left:4px solid}
.calendar-event.urgent{background:#fee2e2;border-color:#ef4444}
.calendar-event.warning{background:#fef3c7;border-color:#f59e0b}
.calendar-event.normal{background:#f0fdf4;border-color:#10b981}
.template-card{border:1px solid;border-radius:.75rem;padding:1rem;margin-bottom:1rem;transition:all .2s ease}
.template-card:hover{box-shadow:0 4px 12px rgba(0,0,0,.1)}
.tool-card{border-radius:1rem;padding:1.5rem;margin-bottom:1rem;border:1px solid}
#MainMenu{visibility:hidden}footer{visibility:hidden}
.stTabs [data-baseweb="tab-list"]{gap:.5rem}
.stTabs [data-baseweb="tab"]{border-radius:.5rem;padding:.5rem 1rem;font-weight:600}
</style>
"""

_THEME_EMERALD = """
<style>
.main-header{background:linear-gradient(135deg,#059669,#0d9488)}
.custom-card{background:#fff;border-color:#e2e8f0}
.stat-card{background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:#bbf7d0}
.stat-card .stat-value{color:#059669}
.stat-card.blue{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#bfdbfe}
.stat-card.blue .stat-value{color:#2563eb}
.stat-card.purple{background:linear-gradient(135deg,#faf5ff,#f3e8ff);border-color:#e9d5ff}
.stat-card.purple .stat-value{color:#7c3aed}
.stat-card.amber{background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fde68a}
.stat-card.amber .stat-value{color:#d97706}
.stat-label{color:#64748b}
.response-box{background:#f8fafc;border-color:#e2e8f0}
.disclaimer{background:#fef3c7}
.template-card{background:#fff;border-color:#e2e8f0}
.tool-card{background:#fff;border-color:#e2e8f0}
</style>
"""

_THEME_MIDNIGHT = """
<style>
[data-testid="stAppViewContainer"]{background-color:#0f172a!important;color:#e2e8f0!important}
[data-testid="stSidebar"]{background-color:#1e293b!important;color:#e2e8f0!important}
[data-testid="stHeader"]{background-color:#0f172a!important}
.main-header{background:linear-gradient(135deg,#1e40af,#7c3aed)}
.custom-card{background:#1e293b;border-color:#334155;color:#e2e8f0}
.stat-card{background:linear-gradient(135deg,#1e293b,#334155);border-color:#475569}
.stat-card .stat-value{color:#34d399}
.stat-card.blue{background:linear-gradient(135deg,#1e293b,#1e3a5f);border-color:#2563eb}
.stat-card.blue .stat-value{color:#60a5fa}
.stat-card.purple{background:linear-gradient(135deg,#1e293b,#2e1065);border-color:#7c3aed}
.stat-card.purple .stat-value{color:#a78bfa}
.stat-card.amber{background:linear-gradient(135deg,#1e293b,#451a03);border-color:#d97706}
.stat-card.amber .stat-value{color:#fbbf24}
.stat-label{color:#94a3b8}
.response-box{background:#1e293b;border-color:#334155;color:#e2e8f0}
.disclaimer{background:#451a03;color:#fef3c7}
.template-card{background:#1e293b;border-color:#334155;color:#e2e8f0}
.tool-card{background:#1e293b;border-color:#334155;color:#e2e8f0}
.calendar-event.urgent{background:#450a0a;border-color:#ef4444;color:#fecaca}
.calendar-event.warning{background:#451a03;border-color:#f59e0b;color:#fef3c7}
.calendar-event.normal{background:#052e16;border-color:#10b981;color:#d1fae5}
[data-testid="stAppViewContainer"] h1,[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3,[data-testid="stAppViewContainer"] h4{color:#f1f5f9!important}
[data-testid="stAppViewContainer"] p,[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] span{color:#cbd5e1}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,[data-testid="stSidebar"] p,[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label{color:#e2e8f0!important}
</style>
"""

_THEME_ROYAL_BLUE = """
<style>
.main-header{background:linear-gradient(135deg,#1e3a5f,#1e40af)}
.custom-card{background:#f8faff;border-color:#bfdbfe}
.stat-card{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#93c5fd}
.stat-card .stat-value{color:#1e40af}
.stat-card.blue{background:linear-gradient(135deg,#eef2ff,#e0e7ff);border-color:#a5b4fc}
.stat-card.blue .stat-value{color:#4f46e5}
.stat-card.purple{background:linear-gradient(135deg,#faf5ff,#f3e8ff);border-color:#e9d5ff}
.stat-card.purple .stat-value{color:#7c3aed}
.stat-card.amber{background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fde68a}
.stat-card.amber .stat-value{color:#d97706}
.stat-label{color:#64748b}
.response-box{background:#f0f5ff;border-color:#bfdbfe}
.disclaimer{background:#fef3c7}
.template-card{background:#f8faff;border-color:#bfdbfe}
.tool-card{background:#f8faff;border-color:#bfdbfe}
</style>
"""

THEMES: dict[str, str] = {
    "🌿 Emerald": _THEME_EMERALD,
    "🌙 Midnight": _THEME_MIDNIGHT,
    "👔 Royal Blue": _THEME_ROYAL_BLUE,
}


# ═══════════════════════════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════════════════════════
@st.cache_data
def get_templates() -> list[dict[str, str]]:
    return [
        {"id": "1", "name": "Employment Contract", "category": "Corporate",
         "content": "EMPLOYMENT CONTRACT\n\nThis Employment Contract is made on [DATE] between:\n\n1. [EMPLOYER NAME] (hereinafter called \"the Employer\")\n   Address: [EMPLOYER ADDRESS]\n   RC Number: [REGISTRATION NUMBER]\n\n2. [EMPLOYEE NAME] (hereinafter called \"the Employee\")\n   Address: [EMPLOYEE ADDRESS]\n\nTERMS AND CONDITIONS:\n\n1. POSITION AND DUTIES\nThe Employee is employed as [JOB TITLE] and shall perform such duties as may be assigned.\n\n2. COMMENCEMENT DATE\nEmployment shall commence on [START DATE].\n\n3. PROBATION PERIOD\nThe Employee shall be on probation for a period of [PERIOD] months.\n\n4. REMUNERATION\nThe Employee shall receive a monthly salary of N[AMOUNT] payable on [DATE] of each month.\n\n5. WORKING HOURS\nNormal working hours shall be [HOURS] per week, Monday to Friday.\n\n6. LEAVE ENTITLEMENT\nThe Employee shall be entitled to [NUMBER] working days annual leave.\n\n7. TERMINATION\nEither party may terminate this contract by giving [NOTICE PERIOD] notice in writing.\n\n8. CONFIDENTIALITY\nThe Employee agrees to maintain confidentiality of all company information.\n\n9. GOVERNING LAW\nThis contract shall be governed by the Labour Act of Nigeria and other applicable laws.\n\nSIGNED:\n_____________________ _____________________\nEmployer              Employee\nDate:                 Date:\n"},
        {"id": "2", "name": "Tenancy Agreement", "category": "Property",
         "content": "TENANCY AGREEMENT\n\nThis Agreement is made on [DATE] BETWEEN:\n\n[LANDLORD NAME] of [LANDLORD ADDRESS] (hereinafter called \"the Landlord\")\n\nAND\n\n[TENANT NAME] of [TENANT ADDRESS] (hereinafter called \"the Tenant\")\n\nWHEREBY IT IS AGREED AS FOLLOWS:\n\n1. PREMISES\nThe Landlord agrees to let and the Tenant agrees to take the property known as: [PROPERTY ADDRESS]\n\n2. TERM\nThe tenancy shall be for a period of [DURATION] commencing from [START DATE].\n\n3. RENT\nThe rent shall be N[AMOUNT] per [PERIOD], payable in advance on [DATE].\n\n4. SECURITY DEPOSIT\nThe Tenant shall pay a security deposit of N[AMOUNT] refundable at the end of tenancy.\n\n5. USE OF PREMISES\nThe premises shall be used solely for [residential/commercial] purposes.\n\n6. MAINTENANCE\nThe Tenant shall keep the premises in good and tenantable condition.\n\n7. ALTERATIONS\nNo structural alterations shall be made without the Landlord's written consent.\n\n8. ASSIGNMENT\nThe Tenant shall not assign or sublet without the Landlord's written consent.\n\n9. TERMINATION\nEither party may terminate by giving [NOTICE PERIOD] notice in writing.\n\n10. GOVERNING LAW\nThis agreement shall be governed by the Lagos State Tenancy Law (or applicable state law).\n\nSIGNED:\n_____________________ _____________________\nLandlord              Tenant\nDate:                 Date:\n\nWITNESS:\nName: _____________________\nAddress: __________________\nSignature: ________________\n"},
        {"id": "3", "name": "Power of Attorney", "category": "Litigation",
         "content": "GENERAL POWER OF ATTORNEY\n\nKNOW ALL MEN BY THESE PRESENTS:\n\nI, [GRANTOR NAME], of [ADDRESS], [OCCUPATION], do hereby appoint [ATTORNEY NAME] of [ATTORNEY ADDRESS] as my true and lawful Attorney to act for me and on my behalf in the following matters:\n\nPOWERS GRANTED:\n\n1. To demand, sue for, recover, collect, and receive all sums of money, debts, dues, and demands whatsoever which are now or shall hereafter become due.\n\n2. To sign, execute, and deliver all contracts, agreements, and documents.\n\n3. To appear before any court, tribunal, or authority and to institute, prosecute, defend, or settle any legal proceedings.\n\n4. To operate my bank accounts and perform banking transactions.\n\n5. To manage my properties and collect rents.\n\n6. To execute and register any deed or document.\n\nAND I HEREBY DECLARE that this Power of Attorney shall remain in force until revoked by me in writing.\n\nIN WITNESS WHEREOF, I have hereunto set my hand this [DATE].\n\n_____________________\n[GRANTOR NAME]\n\nSIGNED AND DELIVERED by the above named in the presence of:\n\nName: _____________________\nAddress: __________________\nOccupation: _______________\nSignature: ________________\n"},
        {"id": "4", "name": "Written Address", "category": "Litigation",
         "content": "IN THE [COURT NAME]\nIN THE [JUDICIAL DIVISION]\nHOLDEN AT [LOCATION]\n\nSUIT NO: [NUMBER]\n\nBETWEEN:\n\n[PLAINTIFF NAME] ........................... PLAINTIFF/APPLICANT\n\nAND\n\n[DEFENDANT NAME] ........................... DEFENDANT/RESPONDENT\n\nWRITTEN ADDRESS OF THE [PLAINTIFF/DEFENDANT]\n\nMAY IT PLEASE THIS HONOURABLE COURT:\n\n1.0 INTRODUCTION\n1.1 This Written Address is filed pursuant to the Rules of this Honourable Court.\n1.2 [Brief background of the matter]\n\n2.0 FACTS OF THE CASE\n2.1 [Detailed facts]\n2.2 [Chronological narration]\n\n3.0 ISSUES FOR DETERMINATION\n3.1 Whether [First Issue]\n3.2 Whether [Second Issue]\n\n4.0 ARGUMENTS\n4.1 ON ISSUE ONE\n[Detailed legal arguments with authorities]\n4.2 ON ISSUE TWO\n[Detailed legal arguments with authorities]\n\n5.0 CONCLUSION\n5.1 Based on the foregoing submissions, it is humbly urged that this Honourable Court:\n(a) [Prayer 1]\n(b) [Prayer 2]\n(c) [Any other order]\n\nDated this [DATE]\n\n_____________________\n[COUNSEL NAME]\n[Law Firm Name]\n[Address]\n[Phone Number]\n[Email]\n\nCounsel to the [Plaintiff/Defendant]\n"},
        {"id": "5", "name": "Affidavit", "category": "Litigation",
         "content": "IN THE [COURT NAME]\nIN THE [JUDICIAL DIVISION]\nHOLDEN AT [LOCATION]\n\nSUIT NO: [NUMBER]\n\nBETWEEN:\n\n[PLAINTIFF NAME] ........................... PLAINTIFF/APPLICANT\n\nAND\n\n[DEFENDANT NAME] ........................... DEFENDANT/RESPONDENT\n\nAFFIDAVIT IN SUPPORT OF [MOTION/APPLICATION]\n\nI, [DEPONENT NAME], [Gender], [Religion], Nigerian citizen, of [ADDRESS], [OCCUPATION], do hereby make oath and state as follows:\n\n1. That I am the [Plaintiff/Defendant/Applicant] in this suit.\n\n2. That I have the authority and consent of the [Party] to depose to this Affidavit.\n\n3. That [State first fact].\n\n4. That [State second fact].\n\n5. That [Continue with numbered paragraphs].\n\n6. That I make this Affidavit in good faith and in support of the [Motion/Application].\n\n7. That I verily believe the facts stated herein to be true and correct to the best of my knowledge, information, and belief.\n\n_____________________\nDEPONENT\n\nSWORN TO at the [Court Registry] at [Location] this [DATE]\n\nBEFORE ME:\n_____________________\nCOMMISSIONER FOR OATHS\n"},
        {"id": "6", "name": "Legal Opinion", "category": "Corporate",
         "content": "LEGAL OPINION\n\nPRIVATE AND CONFIDENTIAL\nPRIVILEGED COMMUNICATION\n\nTO: [CLIENT NAME]\n[CLIENT ADDRESS]\n\nFROM: [LAW FIRM NAME]\n[LAW FIRM ADDRESS]\n\nDATE: [DATE]\n\nRE: [SUBJECT MATTER]\n\n1.0 INTRODUCTION\nWe have been instructed to provide a legal opinion on [subject matter]. This opinion is based on the facts and documents provided to us and the applicable laws of the Federal Republic of Nigeria.\n\n2.0 BACKGROUND FACTS\n[Detailed background of the matter]\n\n3.0 ISSUES FOR CONSIDERATION\n3.1 [First Issue]\n3.2 [Second Issue]\n\n4.0 APPLICABLE LEGAL FRAMEWORK\n4.1 [Relevant Statutes]\n4.2 [Relevant Case Law]\n\n5.0 ANALYSIS\n5.1 On the First Issue\n[Detailed legal analysis]\n5.2 On the Second Issue\n[Detailed legal analysis]\n\n6.0 CONCLUSION AND RECOMMENDATIONS\n6.1 [First Conclusion]\n6.2 [Recommendations]\n\n7.0 CAVEATS\nThis opinion is based solely on Nigerian law as at the date hereof and the facts provided to us.\n\nYours faithfully,\n\n_____________________\n[PARTNER NAME]\nFor: [LAW FIRM NAME]\n"},
        {"id": "7", "name": "Demand Letter", "category": "Litigation",
         "content": "[LAW FIRM LETTERHEAD]\n\n[DATE]\n\nBY HAND/REGISTERED POST/EMAIL\n\n[RECIPIENT NAME]\n[RECIPIENT ADDRESS]\n\nDear Sir/Madam,\n\nRE: DEMAND FOR PAYMENT OF THE SUM OF N[AMOUNT] BEING [DESCRIPTION OF DEBT]\n\nOUR CLIENT: [CLIENT NAME]\n\nWe are Solicitors to [CLIENT NAME] (hereinafter referred to as \"our Client\") on whose behalf and instruction we write you this letter.\n\nOur Client has instructed us on the following facts:\n\n1. [State the background facts]\n2. [State the obligation/agreement]\n3. [State the breach/default]\n\nBy virtue of the foregoing, you are indebted to our Client in the sum of N[AMOUNT] being [description].\n\nDespite several demands, you have failed, refused, and/or neglected to pay the said sum.\n\nTAKE NOTICE that unless you pay the sum of N[AMOUNT] to our Client within SEVEN (7) DAYS of your receipt of this letter, we shall have no option but to institute legal proceedings against you without further notice.\n\nGovern yourself accordingly.\n\nYours faithfully,\n\n_____________________\n[COUNSEL NAME]\nFor: [LAW FIRM NAME]\n\nc.c: Our Client\n"},
        {"id": "8", "name": "Board Resolution", "category": "Corporate",
         "content": "CERTIFIED TRUE COPY OF RESOLUTION PASSED AT A MEETING OF THE BOARD OF DIRECTORS OF [COMPANY NAME] (RC: [REGISTRATION NUMBER]) HELD AT [VENUE] ON [DATE] AT [TIME]\n\nPRESENT:\n1. [NAME] - Chairman\n2. [NAME] - Director\n3. [NAME] - Director\n\nIN ATTENDANCE:\n[NAME] - Company Secretary\n\nRESOLUTION [NUMBER]\n\n[TITLE OF RESOLUTION]\n\nWHEREAS:\nA. [Recital/Background]\nB. [Reason for Resolution]\n\nIT WAS RESOLVED THAT:\n1. [First Resolution]\n2. [Second Resolution]\n3. That any Director be authorized to execute all documents necessary to give effect to this Resolution.\n4. That the Company Secretary file the necessary returns with the CAC.\n\nCERTIFIED TRUE COPY\n\n_____________________\n[NAME]\nCompany Secretary\n\nDate: [DATE]\n\nCompany Seal:\n"},
    ]


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
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
        return (datetime.fromisoformat(date_str).date() - datetime.now().date()).days
    except (ValueError, TypeError):
        return 999

def get_relative_date(date_str: str) -> str:
    d = get_days_until(date_str)
    if d == 0: return "Today"
    if d == 1: return "Tomorrow"
    if d == -1: return "Yesterday"
    if 0 < d <= 7: return f"In {d} days"
    if -7 <= d < 0: return f"{abs(d)} days ago"
    return format_date(date_str)

def safe_html(text: str) -> str:
    return html.escape(str(text))

def normalize_model_name(name: str) -> str:
    clean = (name or "").strip()
    migrated = MODEL_MIGRATION_MAP.get(clean, clean)
    return migrated if migrated in SUPPORTED_MODELS else DEFAULT_MODEL

def get_active_model() -> str:
    return normalize_model_name(st.session_state.get("gemini_model", DEFAULT_MODEL))

def _get_secret(key: str, default: str = "") -> str:
    """Safely read from st.secrets (works even if no secrets file exists)."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError, AttributeError):
        return default


# ═══════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════
_DEFAULTS: dict[str, Any] = {
    "api_key": "",
    "api_configured": False,
    "cases": [],
    "clients": [],
    "time_entries": [],
    "invoices": [],
    "last_response": "",
    "selected_task_type": "general",
    "gemini_model": DEFAULT_MODEL,
    "loaded_template": "",
    "theme": "🌿 Emerald",
    "admin_unlocked": False,
}

def init_session_state() -> None:
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()


# ═══════════════════════════════════════════════════════════════
# APPLY THEME (must run after session state init)
# ═══════════════════════════════════════════════════════════════
st.markdown(_BASE_CSS, unsafe_allow_html=True)
st.markdown(THEMES.get(st.session_state.theme, _THEME_EMERALD), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# RETRY DECORATOR
# ═══════════════════════════════════════════════════════════════
def with_retry(max_attempts: int = 3, base_delay: float = 1.0) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    if attempt == max_attempts:
                        raise
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning("Attempt %d/%d for %s failed: %s — retrying in %.1fs", attempt, max_attempts, func.__name__, exc, delay)
                    time.sleep(delay)
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════
# GEMINI API LAYER
# ═══════════════════════════════════════════════════════════════
def _load_api_key() -> str:
    """Priority: secrets > env > session state."""
    key = _get_secret("GEMINI_API_KEY")
    if key:
        return key.strip()
    key = os.getenv("GEMINI_API_KEY", "")
    if key:
        return key.strip()
    return st.session_state.get("api_key", "").strip()


def _configure_transport(api_key: str) -> None:
    genai.configure(api_key=api_key, transport="rest")


def configure_gemini(api_key: str, model_name: Optional[str] = None) -> bool:
    selected = normalize_model_name(model_name or DEFAULT_MODEL)
    try:
        _configure_transport(api_key)
        model = genai.GenerativeModel(selected)
        model.generate_content("Respond with exactly: OK", generation_config={"max_output_tokens": 16})
        st.session_state.api_configured = True
        st.session_state.api_key = api_key
        st.session_state.gemini_model = selected
        logger.info("Gemini configured with model %s", selected)
        return True
    except Exception as exc:
        logger.error("API configuration failed: %s", exc)
        msg = str(exc)
        if "403" in msg:
            st.error("API key invalid or lacks permission. Check Google AI Studio.")
        elif "429" in msg:
            st.error("Rate limit exceeded. Wait a moment and retry.")
        else:
            st.error(f"API error: {msg}")
        return False


def auto_configure_api() -> None:
    """Silently configure API if a key is available from secrets/env."""
    if st.session_state.api_configured:
        return
    key = _load_api_key()
    if key and len(key) >= 10:
        _configure_transport(key)
        st.session_state.api_key = key
        st.session_state.api_configured = True
        model_env = _get_secret("GEMINI_MODEL") or os.getenv("GEMINI_MODEL", "")
        if model_env:
            st.session_state.gemini_model = normalize_model_name(model_env)
        logger.info("API auto-configured from secrets/env")


@with_retry(max_attempts=2, base_delay=1.5)
def _call_gemini(prompt: str, system_instruction: str) -> str:
    api_key = _load_api_key()
    if not api_key:
        raise RuntimeError("No API key available")
    _configure_transport(api_key)
    try:
        model = genai.GenerativeModel(model_name=get_active_model(), system_instruction=system_instruction)
    except TypeError:
        model = genai.GenerativeModel(model_name=get_active_model())
        prompt = f"{system_instruction}\n\n{prompt}"
    response = model.generate_content(prompt, generation_config=GENERATION_CONFIG)
    return response.text


def generate_legal_response(prompt: str, task_type: str) -> str:
    if not st.session_state.api_configured:
        return "⚠️ Please configure your Gemini API key first."
    task_label = TASK_TYPES.get(task_type, {}).get("label", "General Query")
    try:
        return _call_gemini(f"[Task Type: {task_label}]\n\n{prompt}", SYSTEM_INSTRUCTION)
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


# ═══════════════════════════════════════════════════════════════
# DATA CRUD
# ═══════════════════════════════════════════════════════════════
def add_case(data: dict) -> dict:
    data["id"] = generate_id()
    data["created_at"] = datetime.now().isoformat()
    st.session_state.cases.append(data)
    return data

def update_case(case_id: str, updates: dict) -> bool:
    for c in st.session_state.cases:
        if c["id"] == case_id:
            c.update(updates)
            c["updated_at"] = datetime.now().isoformat()
            return True
    return False

def delete_case(case_id: str) -> None:
    st.session_state.cases = [c for c in st.session_state.cases if c["id"] != case_id]

def add_client(data: dict) -> dict:
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

def add_time_entry(data: dict) -> dict:
    data["id"] = generate_id()
    data["created_at"] = datetime.now().isoformat()
    data["amount"] = data["hours"] * data["rate"]
    st.session_state.time_entries.append(data)
    return data

def delete_time_entry(entry_id: str) -> None:
    st.session_state.time_entries = [e for e in st.session_state.time_entries if e["id"] != entry_id]

def generate_invoice(client_id: str) -> Optional[dict]:
    entries = [e for e in st.session_state.time_entries if e.get("client_id") == client_id]
    if not entries:
        return None
    total = sum(e["amount"] for e in entries)
    inv = {
        "id": generate_id(),
        "invoice_no": f"INV-{datetime.now().strftime('%Y%m%d')}-{generate_id()[:4].upper()}",
        "client_id": client_id,
        "client_name": get_client_name(client_id),
        "entries": entries,
        "total": total,
        "date": datetime.now().isoformat(),
        "status": "Draft",
    }
    st.session_state.invoices.append(inv)
    return inv

def get_total_billable() -> float:
    return sum(e.get("amount", 0) for e in st.session_state.time_entries)

def get_total_hours() -> float:
    return sum(e.get("hours", 0) for e in st.session_state.time_entries)

def get_client_billable(cid: str) -> float:
    return sum(e.get("amount", 0) for e in st.session_state.time_entries if e.get("client_id") == cid)

def get_client_case_count(cid: str) -> int:
    return sum(1 for c in st.session_state.cases if c.get("client_id") == cid)

def get_upcoming_hearings(limit: int = 10) -> list[dict]:
    hearings = [
        {"case_id": c["id"], "case_title": c["title"], "date": c["next_hearing"],
         "court": c.get("court", ""), "suit_no": c.get("suit_no", "")}
        for c in st.session_state.cases
        if c.get("next_hearing") and c.get("status") == "Active"
    ]
    hearings.sort(key=lambda h: h["date"])
    return hearings[:limit]
    # ═══════════════════════════════════════════════════════════════
# UI: HEADER & STATS
# ═══════════════════════════════════════════════════════════════
def render_header() -> None:
    st.markdown(
        '<div class="main-header"><h1>⚖️ LexiAssist</h1>'
        '<p>AI-Powered Legal Practice Management for Nigerian Lawyers · Google Gemini</p></div>',
        unsafe_allow_html=True,
    )

def render_stats() -> None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{len(st.session_state.cases)}</div><div class="stat-label">📁 Active Cases</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card blue"><div class="stat-value">{len(st.session_state.clients)}</div><div class="stat-label">👥 Clients</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card purple"><div class="stat-value">{safe_html(format_currency(get_total_billable()))}</div><div class="stat-label">💰 Billable</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card amber"><div class="stat-value">{len(get_upcoming_hearings())}</div><div class="stat-label">📅 Upcoming</div></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# UI: SIDEBAR
# ═══════════════════════════════════════════════════════════════
def render_sidebar() -> None:
    with st.sidebar:
        # ── Theme ────────────────────────────────────────────
        st.markdown("### 🎨 Theme")
        theme_choice = st.selectbox(
            "Select theme",
            list(THEMES.keys()),
            index=list(THEMES.keys()).index(st.session_state.theme) if st.session_state.theme in THEMES else 0,
            label_visibility="collapsed",
        )
        if theme_choice != st.session_state.theme:
            st.session_state.theme = theme_choice
            st.rerun()

        st.divider()

        # ── API Status ───────────────────────────────────────
        st.markdown("### ⚙️ AI Status")
        if st.session_state.api_configured:
            st.success(f"✅ AI ready · `{get_active_model()}`")
        else:
            st.warning("⚠️ AI not configured")

        # ── Model Selector (always visible, not sensitive) ───
        current = get_active_model()
        idx = SUPPORTED_MODELS.index(current) if current in SUPPORTED_MODELS else 0
        selected_model = st.selectbox("Gemini model", SUPPORTED_MODELS, index=idx)
        if normalize_model_name(selected_model) != st.session_state.gemini_model:
            st.session_state.gemini_model = normalize_model_name(selected_model)
            st.session_state.api_configured = False
            st.rerun()

        st.divider()

        # ── Admin Panel (protected) ──────────────────────────
        admin_pw_stored = _get_secret("ADMIN_PASSWORD")
        has_secret_key = bool(_get_secret("GEMINI_API_KEY"))

        # If no admin password is set AND no secret key — local dev mode: show input directly
        # If secret key exists — key is pre-loaded, admin panel for overrides
        # If admin password exists — require password first
        show_key_input = False

        if not has_secret_key:
            # No pre-configured key — need manual input
            if admin_pw_stored:
                with st.expander("🔒 Admin Settings"):
                    pw = st.text_input("Admin password", type="password", key="admin_pw_input")
                    if pw and pw == admin_pw_stored:
                        st.session_state.admin_unlocked = True
                    if st.session_state.admin_unlocked:
                        show_key_input = True
            else:
                # No password, no secret key — open access (local dev)
                show_key_input = True
        else:
            # Key is from secrets — show admin override behind password
            if admin_pw_stored:
                with st.expander("🔒 Admin Settings"):
                    pw = st.text_input("Admin password", type="password", key="admin_pw_input")
                    if pw and pw == admin_pw_stored:
                        st.session_state.admin_unlocked = True
                    if st.session_state.admin_unlocked:
                        show_key_input = True

        if show_key_input:
            st.markdown("#### 🔑 API Key")
            api_key_input = st.text_input("Gemini API Key", type="password", value=st.session_state.api_key)
            if st.button("Configure API", type="primary"):
                if api_key_input and len(api_key_input.strip()) >= 10:
                    with st.spinner("Validating…"):
                        if configure_gemini(api_key_input.strip(), st.session_state.gemini_model):
                            st.success("✅ Configured!")
                            st.rerun()
                else:
                    st.warning("Enter a valid API key.")
            st.caption("[Get a free key →](https://aistudio.google.com/app/apikey)")

        st.divider()

        # ── Data Management ──────────────────────────────────
        st.markdown("### 💾 Data")
        if st.button("📥 Export All Data"):
            payload = {
                "cases": st.session_state.cases,
                "clients": st.session_state.clients,
                "time_entries": st.session_state.time_entries,
                "invoices": st.session_state.invoices,
                "exported_at": datetime.now().isoformat(),
            }
            st.download_button("Download JSON", data=json.dumps(payload, indent=2),
                               file_name=f"lexiassist_backup_{datetime.now():%Y%m%d}.json", mime="application/json")

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

        # ── Quick Actions ────────────────────────────────────
        st.markdown("### ⚡ Quick Actions")
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
            "#### ℹ️ About\n\n**LexiAssist v2.1**\n\n"
            "Built with 🤖 Google Gemini · 🎈 Streamlit · 🐍 Python\n\n© 2026 LexiAssist"
        )


# ═══════════════════════════════════════════════════════════════
# PAGE: AI ASSISTANT  (task type fix — uses on_click callbacks)
# ═══════════════════════════════════════════════════════════════
def _set_task(key: str) -> None:
    st.session_state.selected_task_type = key


def render_ai_assistant() -> None:
    st.markdown("### 🤖 AI Legal Assistant")
    st.markdown("Get AI-powered assistance with legal drafting, analysis, and research.")

    st.markdown("#### Select Task Type")
    cols = st.columns(3)
    for i, (key, task) in enumerate(TASK_TYPES.items()):
        with cols[i % 3]:
            is_sel = st.session_state.selected_task_type == key
            st.button(
                f"{task['icon']} {task['label'].split(' ', 1)[1]}\n\n{task['description']}",
                key=f"task_{key}",
                use_container_width=True,
                type="primary" if is_sel else "secondary",
                on_click=_set_task,
                args=(key,),
            )

    sel_task = TASK_TYPES.get(st.session_state.selected_task_type, {})
    st.info(f"**Active:** {sel_task.get('icon', '')} {sel_task.get('label', '')} — {sel_task.get('description', '')}")

    st.markdown("---")

    # Pre-fill from template
    default_text = st.session_state.pop("loaded_template", "")

    st.markdown("#### Describe Your Legal Task or Query")
    user_input = st.text_area(
        "query", value=default_text, height=200,
        placeholder="Example: Draft a lease agreement for commercial property in Lagos with 2-year term…",
        label_visibility="collapsed",
    )

    c1, c2 = st.columns([3, 1])
    with c1:
        if st.button("✨ Generate Legal Response", type="primary", use_container_width=True,
                      disabled=not st.session_state.api_configured):
            if user_input.strip():
                with st.spinner("Generating response…"):
                    result = generate_legal_response(user_input, st.session_state.selected_task_type)
                    if not result.startswith("Error"):
                        st.session_state.last_response = result
                    else:
                        st.error(result)
            else:
                st.warning("Please enter your legal query.")
    with c2:
        if st.button("📋 Use Template", use_container_width=True):
            st.session_state.current_tab = "Templates"
            st.rerun()

    if not st.session_state.api_configured:
        st.info("⚠️ Configure your Gemini API key to use the AI assistant.")

    if st.session_state.last_response:
        st.markdown("---")
        st.markdown("#### 📄 LexiAssist Response")
        ec1, ec2, ec3 = st.columns([1, 1, 4])
        with ec1:
            st.download_button("📥 TXT", data=st.session_state.last_response,
                               file_name=f"LexiAssist_{datetime.now():%Y%m%d_%H%M}.txt", mime="text/plain")
        with ec2:
            escaped = safe_html(st.session_state.last_response)
            html_doc = (
                "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>LexiAssist</title>"
                "<style>body{font-family:Georgia,serif;line-height:1.8;max-width:800px;margin:40px auto;padding:20px}"
                "h1{color:#059669;border-bottom:3px solid #059669;padding-bottom:12px}.content{white-space:pre-wrap}"
                ".disclaimer{background:#fef3c7;border-left:4px solid #f59e0b;padding:16px;margin-top:32px}</style>"
                f"</head><body><h1>⚖️ LexiAssist</h1><div class='content'>{escaped}</div>"
                "<div class='disclaimer'><strong>Disclaimer:</strong> For informational purposes only.</div>"
                f"<p style='text-align:center;color:#64748b;font-size:12px;margin-top:32px'>"
                f"Generated {datetime.now():%B %d, %Y at %I:%M %p}</p></body></html>"
            )
            st.download_button("📥 HTML", data=html_doc,
                               file_name=f"LexiAssist_{datetime.now():%Y%m%d_%H%M}.html", mime="text/html")
        st.markdown(f'<div class="response-box">{safe_html(st.session_state.last_response)}</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="disclaimer"><strong>⚖️ Professional Disclaimer:</strong> '
            'This response is for informational purposes only and does not constitute legal advice. '
            'All legal work should be reviewed by a qualified Nigerian lawyer.</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════
# PAGE: RESEARCH
# ═══════════════════════════════════════════════════════════════
def render_research() -> None:
    st.markdown("### 📚 Legal Research")
    query = st.text_input("Research Query", placeholder="E.g., 'breach of contract remedies Nigeria'", label_visibility="collapsed")
    if st.button("🔍 Conduct Research", type="primary", disabled=not st.session_state.api_configured):
        if query.strip():
            with st.spinner("Researching…"):
                st.session_state["research_results"] = conduct_legal_research(query)
        else:
            st.warning("Enter a research query.")
    if not st.session_state.api_configured:
        st.info("⚠️ Configure your Gemini API key to use legal research.")
    results = st.session_state.get("research_results", "")
    if results:
        st.markdown("---")
        st.download_button("📥 Export", data=results, file_name=f"Research_{datetime.now():%Y%m%d_%H%M}.txt", mime="text/plain")
        st.markdown(f'<div class="response-box">{safe_html(results)}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# PAGE: CASES
# ═══════════════════════════════════════════════════════════════
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
                cli_names = ["— Select —"] + [c["name"] for c in st.session_state.clients]
                cli_idx = st.selectbox("Client", range(len(cli_names)), format_func=lambda i: cli_names[i])
            notes = st.text_area("Notes")
            if st.form_submit_button("Save Case", type="primary"):
                if title.strip() and suit_no.strip():
                    cid = st.session_state.clients[cli_idx - 1]["id"] if cli_idx > 0 else None
                    add_case({"title": title.strip(), "suit_no": suit_no.strip(), "court": court.strip(),
                              "next_hearing": next_hearing.isoformat() if next_hearing else None,
                              "status": status, "client_id": cid, "notes": notes.strip()})
                    st.success("✅ Case added!")
                    st.rerun()
                else:
                    st.error("Title and Suit Number are required.")

    filt = st.selectbox("Filter by Status", ["All"] + CASE_STATUSES)
    filtered = st.session_state.cases if filt == "All" else [c for c in st.session_state.cases if c.get("status") == filt]

    if not filtered:
        st.info("📁 No cases found. Add your first case above!")
        return
    for case in filtered:
        badge_cls = {"Active": "success", "Pending": "warning", "Completed": "info", "Archived": ""}.get(case.get("status", ""), "")
        hearing_html = (f"<p><strong>Next Hearing:</strong> {safe_html(format_date(case['next_hearing']))} ({safe_html(get_relative_date(case['next_hearing']))})</p>" if case.get("next_hearing") else "")
        notes_html = f"<p><em>{safe_html(case['notes'])}</em></p>" if case.get("notes") else ""
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(
                f'<div class="custom-card"><h4>{safe_html(case["title"])} <span class="badge badge-{badge_cls}">{safe_html(case.get("status",""))}</span></h4>'
                f'<p><strong>Suit No:</strong> {safe_html(case.get("suit_no","N/A"))}</p>'
                f'<p><strong>Court:</strong> {safe_html(case.get("court","N/A"))}</p>'
                f'<p><strong>Client:</strong> {safe_html(get_client_name(case.get("client_id","")))}</p>'
                f'{hearing_html}{notes_html}</div>', unsafe_allow_html=True)
        with c2:
            cur_idx = CASE_STATUSES.index(case["status"]) if case.get("status") in CASE_STATUSES else 0
            new_st = st.selectbox("Status", CASE_STATUSES, index=cur_idx, key=f"st_{case['id']}", label_visibility="collapsed")
            if new_st != case.get("status"):
                update_case(case["id"], {"status": new_st})
                st.rerun()
            if st.button("🗑️", key=f"del_{case['id']}", help="Delete"):
                delete_case(case["id"])
                st.rerun()


# ═══════════════════════════════════════════════════════════════
# PAGE: CALENDAR
# ═══════════════════════════════════════════════════════════════
def render_calendar() -> None:
    st.markdown("### 📅 Court Calendar")
    hearings = get_upcoming_hearings()
    if hearings:
        for h in hearings:
            days = get_days_until(h["date"])
            urgency = "urgent" if days <= 3 else ("warning" if days <= 7 else "normal")
            badge = "danger" if days <= 3 else ("warning" if days <= 7 else "success")
            st.markdown(
                f'<div class="calendar-event {urgency}"><h4>{safe_html(h["case_title"])}</h4>'
                f'<p><strong>Suit No:</strong> {safe_html(h["suit_no"])}</p>'
                f'<p><strong>Court:</strong> {safe_html(h["court"])}</p>'
                f'<p><strong>Date:</strong> {safe_html(format_date(h["date"]))} '
                f'<span class="badge badge-{badge}">{safe_html(get_relative_date(h["date"]))}</span></p></div>',
                unsafe_allow_html=True)
        st.markdown("---")
        df = pd.DataFrame([{"Case": h["case_title"], "Days Until Hearing": max(get_days_until(h["date"]), 0),
                             "Date": format_date(h["date"])} for h in hearings])
        fig = px.bar(df, x="Days Until Hearing", y="Case", orientation="h", text="Date",
                     color="Days Until Hearing", color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
                     title="Days Until Upcoming Hearings")
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📅 No upcoming hearings.")


# ═══════════════════════════════════════════════════════════════
# PAGE: TEMPLATES
# ═══════════════════════════════════════════════════════════════
def render_templates() -> None:
    st.markdown("### 📋 Document Templates")
    templates = get_templates()
    categories = sorted({t["category"] for t in templates})
    sel = st.selectbox("Filter by Category", ["All"] + categories)
    visible = templates if sel == "All" else [t for t in templates if t["category"] == sel]
    cols = st.columns(2)
    for i, tmpl in enumerate(visible):
        with cols[i % 2]:
            st.markdown(
                f'<div class="template-card"><h4>📄 {safe_html(tmpl["name"])}</h4>'
                f'<span class="badge badge-success">{safe_html(tmpl["category"])}</span>'
                f'<p style="margin-top:.5rem;color:#64748b;font-size:.875rem">{safe_html(tmpl["content"][:100])}…</p></div>',
                unsafe_allow_html=True)
            tc1, tc2 = st.columns(2)
            with tc1:
                if st.button("📋 Use", key=f"use_{tmpl['id']}", use_container_width=True):
                    st.session_state.loaded_template = tmpl["content"]
                    st.success(f"'{tmpl['name']}' loaded into AI Assistant!")
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
            st.download_button("📥 Download", data=preview["content"],
                               file_name=f"{preview['name'].replace(' ', '_')}.txt", mime="text/plain")


# ═══════════════════════════════════════════════════════════════
# PAGE: CLIENTS
# ═══════════════════════════════════════════════════════════════
def render_clients() -> None:
    st.markdown("### 👥 Client Management")
    with st.expander("➕ Add New Client", expanded=False):
        with st.form("add_client_form"):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Client Name *")
                email = st.text_input("Email")
                phone = st.text_input("Phone")
            with c2:
                ctype = st.selectbox("Type", CLIENT_TYPES)
                address = st.text_input("Address")
                notes = st.text_area("Notes")
            if st.form_submit_button("Save Client", type="primary"):
                if name.strip():
                    add_client({"name": name.strip(), "email": email.strip(), "phone": phone.strip(),
                                "type": ctype, "address": address.strip(), "notes": notes.strip()})
                    st.success("✅ Client added!")
                    st.rerun()
                else:
                    st.error("Name is required.")
    if not st.session_state.clients:
        st.info("👥 No clients yet.")
        return
    cols = st.columns(2)
    for i, client in enumerate(st.session_state.clients):
        with cols[i % 2]:
            cases = get_client_case_count(client["id"])
            billable = get_client_billable(client["id"])
            email_l = f"<p>📧 {safe_html(client['email'])}</p>" if client.get("email") else ""
            phone_l = f"<p>📱 {safe_html(client['phone'])}</p>" if client.get("phone") else ""
            addr_l = f"<p>📍 {safe_html(client['address'])}</p>" if client.get("address") else ""
            st.markdown(
                f'<div class="custom-card"><h4>{safe_html(client["name"])} '
                f'<span class="badge badge-info">{safe_html(client.get("type","Individual"))}</span></h4>'
                f'{email_l}{phone_l}{addr_l}'
                f'<hr style="margin:1rem 0"><div style="display:flex;justify-content:space-around;text-align:center">'
                f'<div><div style="font-size:1.5rem;font-weight:bold;color:#059669">{cases}</div>'
                f'<div style="font-size:.75rem;color:#64748b">Cases</div></div>'
                f'<div><div style="font-size:1.5rem;font-weight:bold;color:#7c3aed">{safe_html(format_currency(billable))}</div>'
                f'<div style="font-size:.75rem;color:#64748b">Billable</div></div></div></div>',
                unsafe_allow_html=True)
            bc1, bc2 = st.columns(2)
            with bc1:
                if billable > 0 and st.button("📄 Invoice", key=f"inv_{client['id']}", use_container_width=True):
                    inv = generate_invoice(client["id"])
                    if inv:
                        st.success(f"Invoice {inv['invoice_no']} generated!")
                        st.rerun()
            with bc2:
                if st.button("🗑️ Delete", key=f"delc_{client['id']}", use_container_width=True):
                    delete_client(client["id"])
                    st.rerun()


# ═══════════════════════════════════════════════════════════════
# PAGE: BILLING
# ═══════════════════════════════════════════════════════════════
def render_billing() -> None:
    st.markdown("### 💰 Billing & Time Tracking")
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{safe_html(format_currency(get_total_billable()))}</div><div class="stat-label">💰 Total Billable</div><div style="font-size:.75rem;color:#64748b;margin-top:.5rem">{len(st.session_state.time_entries)} entries</div></div>', unsafe_allow_html=True)
    with sc2:
        st.markdown(f'<div class="stat-card blue"><div class="stat-value">{get_total_hours():.1f}h</div><div class="stat-label">⏱️ Hours</div></div>', unsafe_allow_html=True)
    with sc3:
        st.markdown(f'<div class="stat-card purple"><div class="stat-value">{len(st.session_state.invoices)}</div><div class="stat-label">📄 Invoices</div></div>', unsafe_allow_html=True)
    st.markdown("---")

    with st.expander("⏱️ Log Time Entry", expanded=False):
        with st.form("add_time_form"):
            c1, c2 = st.columns(2)
            with c1:
                cli_names = ["— Select Client —"] + [c["name"] for c in st.session_state.clients]
                cli_idx = st.selectbox("Client *", range(len(cli_names)), format_func=lambda i: cli_names[i])
                case_names = ["— Select Case —"] + [c["title"] for c in st.session_state.cases]
                case_idx = st.selectbox("Case", range(len(case_names)), format_func=lambda i: case_names[i])
                entry_date = st.date_input("Date", value=datetime.now())
            with c2:
                hours = st.number_input("Hours *", min_value=0.25, step=0.25, value=1.0)
                rate = st.number_input("Hourly Rate (₦) *", min_value=0, value=50000, step=5000)
                st.markdown(f"**Total:** {format_currency(hours * rate)}")
            desc = st.text_area("Description *", placeholder="Describe work performed…")
            if st.form_submit_button("Save Entry", type="primary"):
                if cli_idx > 0 and desc.strip():
                    add_time_entry({"client_id": st.session_state.clients[cli_idx - 1]["id"],
                                    "case_id": st.session_state.cases[case_idx - 1]["id"] if case_idx > 0 else None,
                                    "date": entry_date.isoformat(), "hours": hours, "rate": rate, "description": desc.strip()})
                    st.success("✅ Logged!")
                    st.rerun()
                else:
                    st.error("Select a client and enter a description.")

    st.markdown("#### 📋 Time Entries")
    if not st.session_state.time_entries:
        st.info("⏱️ No entries yet.")
    else:
        rows = [{"Date": format_date(e["date"]), "Client": get_client_name(e.get("client_id", "")),
                 "Description": e["description"][:50] + ("…" if len(e["description"]) > 50 else ""),
                 "Hours": f"{e['hours']}h", "Rate": format_currency(e["rate"]),
                 "Amount": format_currency(e["amount"]), "ID": e["id"]} for e in reversed(st.session_state.time_entries)]
        df = pd.DataFrame(rows)
        st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)
        labels = [f"{r['Date']} — {r['Client']} — {r['Description']}" for r in rows]
        sel_del = st.selectbox("Select entry to delete", ["None"] + labels, key="del_entry_sel")
        if sel_del != "None" and st.button("🗑️ Delete Selected"):
            delete_time_entry(rows[labels.index(sel_del)]["ID"])
            st.rerun()
        if len(rows) > 1:
            st.markdown("---")
            totals: dict[str, float] = {}
            for e in st.session_state.time_entries:
                cn = get_client_name(e.get("client_id", ""))
                totals[cn] = totals.get(cn, 0) + e["amount"]
            fig = px.pie(values=list(totals.values()), names=list(totals.keys()), title="Billable by Client")
            st.plotly_chart(fig, use_container_width=True)

    if st.session_state.invoices:
        st.markdown("---")
        st.markdown("#### 📄 Invoices")
        for inv in reversed(st.session_state.invoices):
            with st.expander(f"📄 {inv['invoice_no']} — {inv['client_name']} — {format_currency(inv['total'])}"):
                st.markdown(f"**Invoice:** {inv['invoice_no']}  \n**Client:** {inv['client_name']}  \n"
                            f"**Date:** {format_date(inv['date'])}  \n**Total:** {format_currency(inv['total'])}")
                sep, dash = "=" * 60, "-" * 60
                lines = [sep, "INVOICE", sep, "", f"Invoice: {inv['invoice_no']}", f"Date: {format_date(inv['date'])}",
                         "", f"BILL TO: {inv['client_name']}", "", dash, "TIME ENTRIES", dash]
                for idx, entry in enumerate(inv["entries"], 1):
                    lines += ["", f"{idx}. {format_date(entry['date'])}", f"   {entry['description']}",
                              f"   {entry['hours']}h @ {format_currency(entry['rate'])}/hr = {format_currency(entry['amount'])}"]
                lines += ["", dash, f"TOTAL: {format_currency(inv['total'])}", dash, "", "Payment Terms: Due upon receipt", sep]
                st.download_button("📥 Download", data="\n".join(lines), file_name=f"{inv['invoice_no']}.txt",
                                   mime="text/plain", key=f"dl_{inv['id']}")


# ═══════════════════════════════════════════════════════════════
# PAGE: LEGAL TOOLS  (NEW)
# ═══════════════════════════════════════════════════════════════
def render_legal_tools() -> None:
    st.markdown("### 🇳🇬 Nigerian Legal Tools")
    st.markdown("Quick-access references and calculators for Nigerian legal practice.")

    tool_tabs = st.tabs(["⏱️ Limitation Periods", "💹 Interest Calculator", "🏛️ Court Hierarchy", "📖 Legal Maxims"])

    # ── Limitation Periods ───────────────────────────────────
    with tool_tabs[0]:
        st.markdown("#### ⏱️ Limitation Periods Under Nigerian Law")
        st.markdown("*Common limitation periods. Always verify with the specific statute for your jurisdiction and cause of action.*")
        df_lim = pd.DataFrame(LIMITATION_PERIODS)
        df_lim.columns = ["Cause of Action", "Limitation Period", "Authority"]
        st.dataframe(df_lim, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("##### 🔍 Quick Lookup")
        search = st.text_input("Search by cause of action", placeholder="e.g., contract, land, employment…", key="lim_search")
        if search:
            matches = [lp for lp in LIMITATION_PERIODS if search.lower() in lp["cause"].lower()]
            if matches:
                for m in matches:
                    st.markdown(
                        f'<div class="tool-card"><h4>{safe_html(m["cause"])}</h4>'
                        f'<p><strong>Period:</strong> {safe_html(m["period"])}</p>'
                        f'<p><strong>Authority:</strong> {safe_html(m["authority"])}</p></div>',
                        unsafe_allow_html=True)
            else:
                st.info("No matching cause of action found.")

    # ── Interest Calculator ──────────────────────────────────
    with tool_tabs[1]:
        st.markdown("#### 💹 Interest Calculator")
        st.markdown("Calculate interest for demand letters, judgments, and claims.")
        with st.form("interest_calc"):
            ic1, ic2 = st.columns(2)
            with ic1:
                principal = st.number_input("Principal Amount (₦)", min_value=0.0, value=1000000.0, step=50000.0)
                rate_pct = st.number_input("Annual Interest Rate (%)", min_value=0.0, value=10.0, step=0.5)
            with ic2:
                period_months = st.number_input("Period (months)", min_value=1, value=12, step=1)
                calc_type = st.selectbox("Calculation Type", ["Simple Interest", "Compound Interest (Monthly)"])
            if st.form_submit_button("Calculate", type="primary"):
                if calc_type == "Simple Interest":
                    interest = principal * (rate_pct / 100) * (period_months / 12)
                else:
                    monthly_rate = (rate_pct / 100) / 12
                    compound = principal * ((1 + monthly_rate) ** period_months)
                    interest = compound - principal

                total = principal + interest
                rc1, rc2, rc3 = st.columns(3)
                with rc1:
                    st.metric("Principal", format_currency(principal))
                with rc2:
                    st.metric("Interest", format_currency(interest))
                with rc3:
                    st.metric("Total Due", format_currency(total))

                st.markdown(
                    f'<div class="disclaimer"><strong>Suggested clause:</strong> '
                    f'"…together with interest at the rate of {rate_pct}% per annum '
                    f'({calc_type.lower()}) from [DATE] until the date of final payment, '
                    f'currently amounting to {safe_html(format_currency(interest))}."</div>',
                    unsafe_allow_html=True)

    # ── Court Hierarchy ──────────────────────────────────────
    with tool_tabs[2]:
        st.markdown("#### 🏛️ Nigerian Court Hierarchy")
        st.markdown("*Under the 1999 Constitution (as amended)*")
        current_level = 0
        for court in COURT_HIERARCHY:
            lvl = court["level"]
            indent = "│  " * (lvl - 1)
            connector = "├─" if lvl > 1 else "🔸"
            if lvl != current_level:
                if lvl == 1:
                    st.markdown(f"### {court['icon']} {court['name']}")
                elif lvl == 2:
                    st.markdown(f"#### {indent}{connector} {court['icon']} {court['name']}")
                else:
                    st.markdown(f"{indent}{connector} **{court['name']}**")
                current_level = lvl
            else:
                st.markdown(f"{indent}{connector} **{court['name']}**")
            st.caption(f"{indent}   {court['description']}")

        st.markdown("---")
        st.markdown(
            '<div class="disclaimer"><strong>Note:</strong> '
            'Tribunals (Election Petition, Tax Appeal, Code of Conduct, Investment Disputes) '
            'have specialized jurisdiction. Appeals from tribunals typically lie to the Court of Appeal.</div>',
            unsafe_allow_html=True)

    # ── Legal Maxims ─────────────────────────────────────────
    with tool_tabs[3]:
        st.markdown("#### 📖 Common Legal Maxims in Nigerian Courts")
        search_m = st.text_input("Search maxims", placeholder="e.g., nemo, audi…", key="maxim_search")
        filtered_maxims = LEGAL_MAXIMS
        if search_m:
            q = search_m.lower()
            filtered_maxims = [m for m in LEGAL_MAXIMS if q in m["maxim"].lower() or q in m["meaning"].lower()]

        if filtered_maxims:
            for m in filtered_maxims:
                st.markdown(
                    f'<div class="tool-card">'
                    f'<h4 style="font-style:italic">{safe_html(m["maxim"])}</h4>'
                    f'<p>{safe_html(m["meaning"])}</p></div>',
                    unsafe_allow_html=True)
        else:
            st.info("No matching maxims found.")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def main() -> None:
    auto_configure_api()
    render_header()
    render_sidebar()
    render_stats()
    st.markdown("---")

    tabs = st.tabs([
        "🤖 AI Assistant", "📚 Research", "📁 Cases", "📅 Calendar",
        "📋 Templates", "👥 Clients", "💰 Billing", "🇳🇬 Legal Tools",
    ])
    with tabs[0]: render_ai_assistant()
    with tabs[1]: render_research()
    with tabs[2]: render_cases()
    with tabs[3]: render_calendar()
    with tabs[4]: render_templates()
    with tabs[5]: render_clients()
    with tabs[6]: render_billing()
    with tabs[7]: render_legal_tools()

    st.markdown("---")
    st.markdown(
        '<div style="text-align:center;color:#64748b;font-size:.875rem">'
        '<p>⚖️ <strong>LexiAssist v2.1</strong> — AI-Powered Legal Practice Management</p>'
        '<p>Designed for Nigerian Lawyers · Powered by Google Gemini</p>'
        '<p>© 2026 LexiAssist. All rights reserved.</p></div>',
        unsafe_allow_html=True)


if __name__ == "__main__":
    main()
