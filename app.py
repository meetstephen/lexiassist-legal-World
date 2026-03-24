"""
LexiAssist v8.0 — Elite AI Legal Engine for Nigerian Lawyers
Single-file deployment with SQLite persistence, user profiles,
cost tracking, contract review, analysis comparison, and enhanced AI.
"""
from __future__ import annotations

import html as html_mod
import hashlib
import json
import logging
import os
import re
import sqlite3
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
    import openpyxl  # noqa: F401
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
# GLOBAL SETTINGS
# ═══════════════════════════════════════════════════════
DB_PATH = os.getenv("LEXIASSIST_DB", "lexiassist_data.db")


def safe_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return default


def _get_supported_models() -> list[str]:
    custom = safe_secret("GEMINI_MODELS") or os.getenv("GEMINI_MODELS", "")
    if custom.strip():
        return [m.strip() for m in custom.split(",") if m.strip()]
    return ["gemini-2.5-flash", "gemini-2.5-flash-lite"]


SUPPORTED_MODELS = _get_supported_models()
DEFAULT_MODEL = (
    safe_secret("GEMINI_MODEL")
    or os.getenv("GEMINI_MODEL", "")
    or (SUPPORTED_MODELS[0] if SUPPORTED_MODELS else "gemini-2.5-flash")
)

# ═══════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════
CASE_STATUSES = ["Active", "Pending", "Completed", "Archived"]
CLIENT_TYPES = ["Individual", "Corporate", "Government", "NGO"]

TASK_TYPES = {
    "general":         {"label": "💬 General Query",            "desc": "Any legal question"},
    "analysis":        {"label": "🔍 Legal Analysis",           "desc": "Issue spotting, CREAC reasoning"},
    "drafting":        {"label": "📄 Document Drafting",        "desc": "Contracts, pleadings, affidavits"},
    "research":        {"label": "📚 Legal Research",           "desc": "Case law, statutes, authorities"},
    "procedure":       {"label": "📋 Procedural Guidance",      "desc": "Filing rules, court practice"},
    "advisory":        {"label": "🎯 Strategic Advisory",       "desc": "Risk mapping, options, strategy"},
    "interpret":       {"label": "⚖️ Statutory Interpretation", "desc": "Legislation analysis"},
    "contract_review": {"label": "📑 Contract Review",          "desc": "Clause-by-clause + red flags"},
}

RESPONSE_MODES = {
    "brief":         {"label": "⚡ Brief",         "desc": "Direct answer, 3-5 sentences",        "tokens": 1200,  "temp": 0.1},
    "standard":      {"label": "📝 Standard",      "desc": "Structured analysis, 5-10 paragraphs", "tokens": 6000,  "temp": 0.15},
    "comprehensive": {"label": "🔬 Comprehensive", "desc": "Full CREAC + Strategy + Risk Ranking",  "tokens": 16384, "temp": 0.2},
}

UPLOAD_TYPES = ["pdf", "docx", "doc", "txt", "xlsx", "xls", "csv", "json", "rtf"]

# Cost per 1M tokens (USD) — update as pricing changes
GEMINI_COST_PER_1M = {
    "gemini-2.5-flash":      {"input": 0.15,  "output": 0.60},
    "gemini-2.5-flash-lite": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash":      {"input": 0.10,  "output": 0.40},
    "gemini-1.5-flash":      {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro":        {"input": 1.25,  "output": 5.00},
}

# ═══════════════════════════════════════════════════════
# SYSTEM PROMPTS
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

LIMITATION NOTE: Nigeria does NOT have a single federal "Limitation Act."
Limitation periods are governed by STATE LAWS (e.g. Limitation Law of Lagos State,
Cap L84, Laws of Lagos State 2015; Limitation Law of Ogun State, etc.).
Some federal statutes contain their own limitation provisions.
ALWAYS cite the applicable STATE limitation law or specific federal statute.

CITATION INTEGRITY: NEVER fabricate case names or section numbers.
If uncertain, state the legal principle and mark as [CITATION TO BE VERIFIED].
If a case is well-known and established, cite it confidently.

CRITICAL RULES:
1. TAKE POSITIONS — Say "X IS liable because…" not "X may be liable"
2. ALWAYS identify the WEAKEST PARTY and explain why
3. NEVER end abruptly — complete every section you start
4. When multiple parties are involved, RANK their risk exposure
5. Write to COMPLETION — do not stop mid-analysis"""

STRATEGY_BLOCK = """
MANDATORY STRATEGY LAYER (Standard & Comprehensive modes):
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
- You have ample token space — USE IT for thorough coverage
- Every paragraph must add value — no repetition""",

    "comprehensive": IDENTITY_CORE + STRATEGY_BLOCK + """
RESPONSE MODE: COMPREHENSIVE (DEEP ANALYSIS)
- This is your MOST THOROUGH mode. Use ALL available space.
- For EACH issue use CREAC: CONCLUSION → RULE → EXPLANATION → APPLICATION → CONCLUSION
- Identify ALL issues: obvious, hidden, procedural, jurisdictional, limitation
- For EACH issue cite the governing statute AND at least one leading case
- Include DEVIL'S ADVOCATE section: strongest counter-argument
- Include MANDATORY STRATEGY LAYER (detailed version)
- Include PRACTICAL CHECKLIST of immediate actions
- You have 16,000 tokens — write a COMPLETE, exhaustive analysis
- NEVER stop mid-analysis — analyze every issue fully
- End with SUMMARY OF POSITIONS table""",
}

TASK_MODIFIERS = {
    "general":   "\nApply the general legal framework. Take a clear position.",
    "analysis":  "\nFocus on deep issue-spotting. Apply CREAC to each issue. Distinguish facts carefully.",
    "drafting":  "\nDraft a professional Nigerian-standard document. Use [PLACEHOLDER] for missing data. Include formality requirements (execution, stamping, filing). Do NOT add strategy/risk sections.",
    "research":  "\nWrite a formal Legal Research Memorandum. For each authority: state the principle, quote the ratio (if known), and explain relevance.",
    "procedure": "\nProvide step-by-step procedural guidance. Include: which court, which form/process, filing fees (if known), timelines, and common pitfalls.",
    "advisory":  "\nFocus on strategic advisory. Emphasize risk mitigation, commercial impact, and optimal paths. Include risk matrix.",
    "interpret": "\nApply the three rules of statutory interpretation (Literal, Golden, Mischief). State which rule yields the best result and WHY.",
    "contract_review": """
CONTRACT REVIEW MODE:
Analyze the document clause by clause. For each significant clause:
1. 📋 CLAUSE SUMMARY — What it says plainly.
2. 🔴 RED FLAGS — Risks, ambiguities, one-sided terms.
3. ⚖️ LEGAL COMPLIANCE — Nigerian law requirements, cite statute if non-compliant.
4. 💡 RECOMMENDATION — Specific redraft language or negotiation point.

After clause analysis include:
═══ CONTRACT RISK SUMMARY ═══
▸ Overall Risk Level: HIGH / MEDIUM / LOW
▸ Top 5 Red Flags (ranked by severity)
▸ Missing Clauses (what should exist but doesn't)
▸ Mandatory Regulatory Requirements (stamps, registration, approvals)
▸ Recommended Actions Before Signing
═══════════════════════════════""",
}

ISSUE_SPOT_PROMPT = IDENTITY_CORE + """
TASK: Rapid Issue Decomposition (max 250 words)
- CORE ISSUES: each with area of law + governing principle
- HIDDEN ISSUES: procedural traps, limitation, standing, regulatory overlap
- MISSING FACTS: top 3-5 facts that would change the analysis
- COMPLEXITY: Straightforward / Moderate / Complex / Highly Complex
Decomposition ONLY — no full analysis."""

CRITIQUE_PROMPT = IDENTITY_CORE + """
TASK: Quality Assessment of the analysis below (max 150 words).
Score 1-5: Completeness, Legal Accuracy, Strategic Value.
List 1-3 critical gaps. GRADE: A/B/C/D. One sentence verdict."""

FOLLOWUP_PROMPT = IDENTITY_CORE + STRATEGY_BLOCK + """
You are continuing a legal conversation.
Context: Original query, previous analysis, and a follow-up question.
Address the follow-up directly with the same rigor. Match the response mode."""

COMPARE_PROMPT = IDENTITY_CORE + """
TASK: Compare two legal analyses side by side (max 500 words).
For each analysis: summarize the conclusion, authorities cited, risk assessment.
Highlight key DIFFERENCES, GAPS in either, and declare which is STRONGER with reasons.
Present as a structured comparison."""

# ═══════════════════════════════════════════════════════
# REFERENCE DATA (CORRECTED — state-based limitation)
# ═══════════════════════════════════════════════════════
DEFAULT_LIMITATION_PERIODS = [
    {"cause": "Simple Contract", "period": "6 years", "authority": "State Limitation Laws (e.g. Lagos Limitation Law Cap L84, s. 8(1)(a))", "editable": True},
    {"cause": "Tort / Negligence", "period": "6 years", "authority": "State Limitation Laws (e.g. Lagos Limitation Law, s. 8(1)(a))", "editable": True},
    {"cause": "Personal Injury", "period": "3 years", "authority": "State Limitation Laws (e.g. Lagos Limitation Law, s. 8(1)(b))", "editable": True},
    {"cause": "Defamation", "period": "3 years", "authority": "State Limitation Laws (varies by state)", "editable": True},
    {"cause": "Recovery of Land", "period": "12 years", "authority": "State Limitation Laws (e.g. Lagos, s. 16; some states differ)", "editable": True},
    {"cause": "Mortgage Foreclosure", "period": "12 years", "authority": "State Limitation Laws (e.g. Lagos, s. 18)", "editable": True},
    {"cause": "Recovery of Rent", "period": "6 years", "authority": "State Limitation Laws", "editable": True},
    {"cause": "Judgment Enforcement", "period": "12 years", "authority": "State Limitation Laws / Sheriffs & Civil Process Act", "editable": True},
    {"cause": "Public Officers (POPA)", "period": "3 months notice + 12 months to sue", "authority": "Public Officers Protection Act, s. 2(a)", "editable": True},
    {"cause": "Fundamental Rights", "period": "12 months", "authority": "FREP Rules 2009, Order II r. 1", "editable": True},
    {"cause": "Election Petition", "period": "21 days post-declaration", "authority": "Electoral Act 2022, s. 133(1)", "editable": True},
    {"cause": "Admiralty Claims", "period": "2 years", "authority": "Admiralty Jurisdiction Act, s. 10", "editable": True},
    {"cause": "Tax Assessment Appeal", "period": "30 days", "authority": "FIRS (Est.) Act / CITA / PITA (varies)", "editable": True},
]

COURT_HIERARCHY = [
    {"level": 1, "name": "Supreme Court of Nigeria", "desc": "Final appellate court — binding on all", "icon": "🏛️"},
    {"level": 2, "name": "Court of Appeal", "desc": "Intermediate appellate — binding on courts below", "icon": "⚖️"},
    {"level": 3, "name": "Federal High Court", "desc": "Federal causes, tax, admiralty, IP, banks", "icon": "🏢"},
    {"level": 3, "name": "State High Courts", "desc": "General civil & criminal jurisdiction", "icon": "🏢"},
    {"level": 3, "name": "National Industrial Court", "desc": "Labour, employment, trade unions", "icon": "🏢"},
    {"level": 3, "name": "FCT High Court", "desc": "Matters arising in Abuja FCT", "icon": "🏢"},
    {"level": 4, "name": "Magistrate / District Courts", "desc": "Summary jurisdiction — monetary limits apply", "icon": "📋"},
    {"level": 4, "name": "Customary Court of Appeal", "desc": "Appeals from customary courts", "icon": "📋"},
    {"level": 4, "name": "Sharia Court of Appeal", "desc": "Appeals from Sharia courts (applicable states)", "icon": "📋"},
    {"level": 5, "name": "Customary / Area Courts", "desc": "Personal law — marriage, inheritance, land", "icon": "📌"},
    {"level": 5, "name": "Sharia Courts", "desc": "Islamic personal law matters", "icon": "📌"},
]

DEFAULT_LEGAL_MAXIMS = [
    {"maxim": "Audi alteram partem", "meaning": "Hear the other side — fundamental natural justice"},
    {"maxim": "Nemo judex in causa sua", "meaning": "No one should judge their own cause — bias rule"},
    {"maxim": "Stare decisis", "meaning": "Stand by decided cases — binding precedent"},
    {"maxim": "Ubi jus ibi remedium", "meaning": "Where there is a right, there is a remedy"},
    {"maxim": "Volenti non fit injuria", "meaning": "No injury to one who consents"},
    {"maxim": "Pacta sunt servanda", "meaning": "Agreements must be honoured"},
    {"maxim": "Nemo dat quod non habet", "meaning": "No one gives what they don't have"},
    {"maxim": "Res judicata", "meaning": "A decided matter cannot be re-litigated between same parties"},
    {"maxim": "Actus non facit reum nisi mens sit rea", "meaning": "No guilt without a guilty mind"},
    {"maxim": "Ignorantia legis neminem excusat", "meaning": "Ignorance of law excuses no one"},
    {"maxim": "Qui facit per alium facit per se", "meaning": "He who acts through another acts himself — agency"},
    {"maxim": "Generalia specialibus non derogant", "meaning": "General provisions do not override specific ones"},
    {"maxim": "Expressio unius est exclusio alterius", "meaning": "Express mention of one excludes others"},
    {"maxim": "Ejusdem generis", "meaning": "General words after specific ones are limited to same class"},
    {"maxim": "Ex turpi causa non oritur actio", "meaning": "No action arises from a wrongful cause"},
    {"maxim": "Noscitur a sociis", "meaning": "A word is known by the company it keeps"},
]

DEFAULT_TEMPLATES = [
    {"id": "t1", "name": "Employment Contract", "cat": "Corporate", "builtin": True,
     "content": "EMPLOYMENT CONTRACT\n\nMade on [DATE] between:\n\n1. [EMPLOYER NAME] (\"Employer\")\n   RC: [NUMBER]\n\n2. [EMPLOYEE NAME] (\"Employee\")\n\nTERMS:\n1. Position: [TITLE]\n2. Commencement: [DATE]\n3. Probation: [MONTHS] months\n4. Salary: N[AMOUNT]/month\n5. Working Hours: [X] hrs/week\n6. Annual Leave: [X] days/year\n7. Termination: [NOTICE PERIOD] written notice by either party\n8. Confidentiality: Employee shall not disclose proprietary information\n9. Governing Law: Labour Act, Cap L1 LFN 2004\n\nSigned:\n_______________ (Employer)\n_______________ (Employee)\nDate: _______________"},

    {"id": "t2", "name": "Tenancy Agreement", "cat": "Property", "builtin": True,
     "content": "TENANCY AGREEMENT\n\nMade on [DATE] BETWEEN:\n[LANDLORD NAME] of [ADDRESS] (\"Landlord\")\nAND\n[TENANT NAME] of [ADDRESS] (\"Tenant\")\n\nPREMISES: [FULL ADDRESS OF PROPERTY]\n\n1. Term: [DURATION] commencing from [START DATE]\n2. Rent: N[AMOUNT] per [annum/month], payable [in advance/quarterly]\n3. Security Deposit: N[AMOUNT] (refundable subject to conditions)\n4. Permitted Use: [Residential/Commercial]\n5. Repairs: Structural — Landlord; Internal — Tenant\n6. Assignment: Not without Landlord's prior written consent\n7. Termination: [NOTICE PERIOD] written notice\n8. Governing Law: [Applicable State] Tenancy Law\n\nSigned:\n_______________ (Landlord)\n_______________ (Tenant)\nWitness:\n_______________"},

    {"id": "t3", "name": "Power of Attorney", "cat": "Litigation", "builtin": True,
     "content": "GENERAL POWER OF ATTORNEY\n\nBY THIS POWER OF ATTORNEY made on [DATE]\n\nI, [GRANTOR FULL NAME], of [ADDRESS], hereby appoint\n[ATTORNEY FULL NAME], of [ADDRESS], as my lawful Attorney to:\n\n1. Recover debts, rents, and execute settlements on my behalf\n2. Manage, let, sell, or otherwise deal with my real and personal property\n3. Appear before any court, tribunal, or regulatory body\n4. Execute all documents and instruments as may be necessary\n5. [ADDITIONAL SPECIFIC POWERS]\n\nThis Power of Attorney is [REVOCABLE/IRREVOCABLE] for [PERIOD].\n\nIN WITNESS WHEREOF I have set my hand this [DAY] day of [MONTH] [YEAR].\n\nSigned: _______________\nGrantor: [NAME]\n\nWitness 1: _______________ (Name, Address, Occupation)\nWitness 2: _______________ (Name, Address, Occupation)"},

    {"id": "t4", "name": "Written Address (Skeleton)", "cat": "Litigation", "builtin": True,
     "content": "IN THE [HIGH COURT OF [STATE] / FEDERAL HIGH COURT]\nIN THE [JUDICIAL DIVISION]\nSUIT NO: [NUMBER]\n\nBETWEEN:\n[CLAIMANT/APPLICANT NAME] ............ Claimant/Applicant\n\nAND\n\n[DEFENDANT/RESPONDENT NAME] ........... Defendant/Respondent\n\nWRITTEN ADDRESS OF THE [CLAIMANT/DEFENDANT]\n\n1.0 INTRODUCTION\n[Brief introduction of counsel, client, and nature of address]\n\n2.0 BRIEF FACTS\n[Concise statement of material facts]\n\n3.0 ISSUES FOR DETERMINATION\nIssue 1: Whether [ISSUE]\nIssue 2: Whether [ISSUE]\n\n4.0 ARGUMENTS\n4.1 On Issue One\n[Arguments with authorities]\n\n4.2 On Issue Two\n[Arguments with authorities]\n\n5.0 CONCLUSION\n[Summary and prayer]\n\nDated this [DAY] day of [MONTH] [YEAR]\n\n_______________\n[COUNSEL NAME]\n[FIRM NAME]\n[FIRM ADDRESS]\nCounsel to the [Claimant/Defendant]"},

    {"id": "t5", "name": "Demand Letter", "cat": "Commercial", "builtin": True,
     "content": "OUR REF: [FIRM/REF]\nYOUR REF: [IF KNOWN]\nDATE: [DATE]\n\n[RECIPIENT NAME]\n[RECIPIENT ADDRESS]\n\nDear Sir/Madam,\n\nRE: DEMAND FOR PAYMENT OF THE SUM OF N[AMOUNT] ([AMOUNT IN WORDS])\n\nWe are Solicitors to [CLIENT NAME] (\"our Client\") on whose firm instructions we write you this letter.\n\nOur Client instructs us as follows:\n[DETAILED FACTS GIVING RISE TO THE CLAIM]\n\nDespite repeated demands, you have failed, refused, and/or neglected to pay the said sum.\n\nWe hereby DEMAND that you pay the sum of N[AMOUNT] to our Client within [NUMBER] days of receipt of this letter.\n\nTake notice that failure to comply will leave us with no option but to institute legal proceedings against you for the recovery of the said sum, together with interest and costs, without further reference to you.\n\nYours faithfully,\n\n_______________\n[SOLICITOR NAME]\n[FIRM NAME]\n[Address | Phone | Email]"},

    {"id": "t6", "name": "Affidavit (General)", "cat": "Litigation", "builtin": True,
     "content": "IN THE [COURT NAME]\nSUIT NO: [NUMBER]\n\nBETWEEN:\n[CLAIMANT] ............ Claimant\nAND\n[DEFENDANT] ........... Defendant\n\nAFFIDAVIT OF [NAME]\n\nI, [FULL NAME], [Gender], [Religion], Nigerian citizen, of [ADDRESS], do hereby make oath and state as follows:\n\n1. I am the [Claimant/Defendant/[Relationship]] in this suit and I depose to this affidavit from facts within my personal knowledge.\n\n2. [FACT 1]\n\n3. [FACT 2]\n\n4. [FACT 3]\n\n5. I depose to this affidavit in good faith believing the contents to be true and correct and in accordance with the Oaths Act, Cap O1 LFN 2004.\n\n_______________\nDeponent\n\nSworn to at the [COURT] Registry, [LOCATION]\nThis [DAY] day of [MONTH] [YEAR]\n\nBEFORE ME\n\n_______________\nCommissioner for Oaths"},
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
# SQLITE PERSISTENCE LAYER
# ═══════════════════════════════════════════════════════
def _get_db() -> sqlite3.Connection:
    """Return a SQLite connection. Creates DB file if absent."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = _get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS user_profile (
        id TEXT PRIMARY KEY,
        firm_name TEXT DEFAULT '',
        user_name TEXT DEFAULT '',
        email TEXT DEFAULT '',
        password_hash TEXT DEFAULT '',
        created_at TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS clients (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        type TEXT DEFAULT 'Individual',
        address TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS cases (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        suit_no TEXT DEFAULT '',
        court TEXT DEFAULT '',
        status TEXT DEFAULT 'Active',
        client_id TEXT DEFAULT '',
        next_hearing TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS case_notes (
        id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        content TEXT NOT NULL,
        note_type TEXT DEFAULT 'ai_analysis',
        source_query TEXT DEFAULT '',
        created_at TEXT,
        FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS time_entries (
        id TEXT PRIMARY KEY,
        client_id TEXT DEFAULT '',
        client_name TEXT DEFAULT '',
        description TEXT DEFAULT '',
        hours REAL DEFAULT 0,
        rate REAL DEFAULT 0,
        amount REAL DEFAULT 0,
        entry_date TEXT DEFAULT '',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS invoices (
        id TEXT PRIMARY KEY,
        invoice_no TEXT DEFAULT '',
        client_id TEXT DEFAULT '',
        client_name TEXT DEFAULT '',
        entries_json TEXT DEFAULT '[]',
        total REAL DEFAULT 0,
        status TEXT DEFAULT 'Draft',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS chat_history (
        id TEXT PRIMARY KEY,
        timestamp TEXT,
        query TEXT,
        response TEXT,
        task TEXT DEFAULT 'general',
        mode TEXT DEFAULT 'standard',
        word_count INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS cost_log (
        id TEXT PRIMARY KEY,
        model TEXT,
        prompt_tokens INTEGER DEFAULT 0,
        response_tokens INTEGER DEFAULT 0,
        input_cost REAL DEFAULT 0,
        output_cost REAL DEFAULT 0,
        total_cost REAL DEFAULT 0,
        query_preview TEXT DEFAULT '',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS user_templates (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        cat TEXT DEFAULT 'Custom',
        content TEXT DEFAULT '',
# ═══════════════════════════════════════════════════════
# SESSION STATE INIT & DB SYNC
# ═══════════════════════════════════════════════════════
_DEFAULTS: dict[str, Any] = {
    "api_key": "",
    "api_configured": False,
    "gemini_model": DEFAULT_MODEL,
    "theme": "🌿 Emerald",
    "response_mode": "standard",
    "last_response": "",
    "original_query": "",
    "research_results": "",
    "loaded_template": "",
    "imported_doc": None,
    "selected_history_idx": None,
    "context_enabled": False,
    "authenticated": False,
    "user_id": "",
    "db_initialized": False,
}

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


def ensure_db():
    """Initialize DB + seed defaults once per session."""
    if not st.session_state.db_initialized:
        init_db()
        seed_defaults()
        st.session_state.db_initialized = True


# ═══════════════════════════════════════════════════════
# USER PROFILE / AUTH
# ═══════════════════════════════════════════════════════
def get_user_profile() -> dict | None:
    rows = db_fetch_all("user_profile", "created_at ASC")
    return rows[0] if rows else None


def save_user_profile(firm_name: str, user_name: str, email: str, password: str = ""):
    profile = get_user_profile()
    now = datetime.now().isoformat()
    data = {
        "firm_name": firm_name.strip(),
        "user_name": user_name.strip(),
        "email": email.strip(),
        "updated_at": now,
    }
    if password.strip():
        data["password_hash"] = hash_password(password.strip())

    if profile:
        db_update("user_profile", profile["id"], data)
    else:
        data["id"] = new_id()
        data["created_at"] = now
        if "password_hash" not in data:
            data["password_hash"] = ""
        db_insert("user_profile", data)
    return True


def check_auth() -> bool:
    """Check if authentication is needed and passed."""
    profile = get_user_profile()
    if not profile or not profile.get("password_hash"):
        return True
    return st.session_state.get("authenticated", False)


# ═══════════════════════════════════════════════════════
# COST TRACKING
# ═══════════════════════════════════════════════════════
def log_cost(model: str, prompt_text: str, response_text: str, query_preview: str = ""):
    """Log API call cost to the database."""
    prompt_tokens = estimate_tokens(prompt_text)
    response_tokens = estimate_tokens(response_text)

    pricing = GEMINI_COST_PER_1M.get(model, GEMINI_COST_PER_1M.get("default", {"input": 0.10, "output": 0.40}))
    if pricing is None:
        pricing = {"input": 0.10, "output": 0.40}

    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (response_tokens / 1_000_000) * pricing["output"]

    db_insert("cost_log", {
        "id": new_id(),
        "model": model,
        "prompt_tokens": prompt_tokens,
        "response_tokens": response_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": input_cost + output_cost,
        "query_preview": (query_preview or prompt_text)[:200],
        "created_at": datetime.now().isoformat(),
    })


def get_cost_summary() -> dict:
    """Return aggregate cost data."""
    conn = _get_db()
    row = conn.execute("""
        SELECT
            COUNT(*) as total_calls,
            COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
            COALESCE(SUM(response_tokens), 0) as total_response_tokens,
            COALESCE(SUM(total_cost), 0) as total_cost
        FROM cost_log
    """).fetchone()

    today_row = conn.execute("""
        SELECT
            COUNT(*) as calls,
            COALESCE(SUM(total_cost), 0) as cost
        FROM cost_log WHERE DATE(created_at) = DATE('now')
    """).fetchone()

    month_row = conn.execute("""
        SELECT
            COUNT(*) as calls,
            COALESCE(SUM(total_cost), 0) as cost
        FROM cost_log WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
    """).fetchone()

    conn.close()
    return {
        "total_calls": row["total_calls"],
        "total_prompt_tokens": row["total_prompt_tokens"],
        "total_response_tokens": row["total_response_tokens"],
        "total_cost": row["total_cost"],
        "today_calls": today_row["calls"],
        "today_cost": today_row["cost"],
        "month_calls": month_row["calls"],
        "month_cost": month_row["cost"],
    }


# ═══════════════════════════════════════════════════════
# API LAYER
# ═══════════════════════════════════════════════════════
def _resolve_api_key() -> str:
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
    """Core generation with retry, cost tracking, and proper token limits."""
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

    current_model = st.session_state.gemini_model
    model = genai.GenerativeModel(current_model, system_instruction=system)

    full_prompt = system + "\n\n" + prompt  # for cost estimation

    for attempt in range(3):
        try:
            resp = model.generate_content(prompt, generation_config=gen_config)
            if resp and resp.text:
                # Log cost
                try:
                    log_cost(current_model, full_prompt, resp.text, prompt[:200])
                except Exception:
                    pass
                return resp.text
            return "⚠️ Empty response from AI. Try rephrasing your query."
        except Exception as e:
            if attempt == 2:
                return f"⚠️ Generation error after 3 attempts: {str(e)[:200]}"
            time.sleep(2 * (attempt + 1))

    return "⚠️ Generation failed. Please try again."


def build_system_prompt(task: str, mode: str) -> str:
    base = PROMPTS_BY_MODE.get(mode, PROMPTS_BY_MODE["standard"])
    modifier = TASK_MODIFIERS.get(task, TASK_MODIFIERS["general"])
    return base + modifier


# ═══════════════════════════════════════════════════════
# AI OPERATION FUNCTIONS
# ═══════════════════════════════════════════════════════
def run_ai_query(query: str, task: str, mode: str, context: str = "") -> str:
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
    prompt = f"ORIGINAL QUERY:\n{original}\n\nPREVIOUS ANALYSIS:\n{previous}\n\nFOLLOW-UP:\n{followup}"
    return generate(prompt, FOLLOWUP_PROMPT, mode)


def run_research(query: str, mode: str) -> str:
    system = build_system_prompt("research", mode)
    return generate(query, system, mode)


def run_compare(analysis_a: str, analysis_b: str) -> str:
    prompt = f"ANALYSIS A:\n{analysis_a[:6000]}\n\n{'='*40}\n\nANALYSIS B:\n{analysis_b[:6000]}"
    return generate(prompt, COMPARE_PROMPT, "standard")


# ═══════════════════════════════════════════════════════
# FILE EXTRACTION
# ═══════════════════════════════════════════════════════
def extract_file_text(uploaded_file) -> str:
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
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            raise ValueError(f"Unsupported file type: {name}")


# ═══════════════════════════════════════════════════════
# EXPORT FUNCTIONS
# ═══════════════════════════════════════════════════════
def export_pdf(text: str, title: str = "LexiAssist Analysis") -> bytes:
    if not HAS_FPDF:
        return b"%PDF-1.0\nPDF generation unavailable. Install fpdf2."

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    safe_title = title.encode("latin-1", errors="replace").decode("latin-1")
    pdf.cell(0, 12, txt=safe_title, ln=True, align="C")
    pdf.ln(4)

    # Date line
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, txt=f"Generated: {datetime.now():%d %B %Y at %H:%M}", ln=True, align="C")

    # Firm name if set
    profile = get_user_profile()
    if profile and profile.get("firm_name"):
        firm = profile["firm_name"].encode("latin-1", errors="replace").decode("latin-1")
        pdf.cell(0, 6, txt=firm, ln=True, align="C")
    pdf.ln(6)

    # Divider
    pdf.set_draw_color(100, 100, 100)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    # Body
    pdf.set_font("Helvetica", size=10)
    clean = text.encode("latin-1", errors="replace").decode("latin-1")
    for line in clean.split("\n"):
        pdf.multi_cell(0, 6, txt=line)
        pdf.ln(1)

    # Footer
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, txt="Generated by LexiAssist v8.0 — Verify all citations independently", ln=True, align="C")

    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1", errors="replace")
    if isinstance(raw, bytearray):
        return bytes(raw)
    return raw


def export_docx(text: str, title: str = "LexiAssist Analysis") -> bytes:
    if not HAS_DOCX:
        return b"DOCX generation unavailable."
    bio = BytesIO()
    doc = DocxDocument()
    doc.add_heading(title, level=0)

    profile = get_user_profile()
    meta_line = f"Generated: {datetime.now():%d %B %Y at %H:%M}"
    if profile and profile.get("firm_name"):
        meta_line += f" | {profile['firm_name']}"
    doc.add_paragraph(meta_line)
    doc.add_paragraph("")

    for para in text.split("\n\n"):
        if para.strip():
            doc.add_paragraph(para.strip())

    doc.add_paragraph("")
    footer = doc.add_paragraph("Generated by LexiAssist v8.0 — Verify all citations independently")
    if footer.runs:
        footer.runs[0].font.size = Pt(8)
    doc.save(bio)
    return bio.getvalue()


def export_txt(text: str, title: str = "LexiAssist Analysis") -> str:
    profile = get_user_profile()
    firm = ""
    if profile and profile.get("firm_name"):
        firm = f"\n{profile['firm_name']}"
    header = f"{'='*60}\n{title}{firm}\nGenerated: {datetime.now():%d %B %Y at %H:%M}\n{'='*60}\n\n"
    footer = f"\n\n{'='*60}\nGenerated by LexiAssist v8.0\n{'='*60}"
    return header + text + footer


def export_html(text: str, title: str = "LexiAssist Analysis") -> str:
    profile = get_user_profile()
    firm_line = ""
    if profile and profile.get("firm_name"):
        firm_line = f'<div class="meta">{esc(profile["firm_name"])}</div>'
    body = esc(text).replace("\n", "<br>")
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>{esc(title)}</title>
<style>body{{font-family:Georgia,serif;max-width:800px;margin:2rem auto;padding:1rem;line-height:1.7;color:#1e293b}}
h1{{color:#059669;border-bottom:2px solid #059669;padding-bottom:0.5rem}}
.meta{{color:#64748b;font-size:0.9rem;margin-bottom:0.5rem}}
.disclaimer{{background:#fef3c7;border-left:4px solid #f59e0b;padding:1rem;margin-top:2rem;font-size:0.85rem}}</style>
</head><body>
<h1>{esc(title)}</h1>
{firm_line}
<div class="meta">Generated: {datetime.now():%d %B %Y at %H:%M}</div>
<div>{body}</div>
<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated. Verify all citations independently.</div>
</body></html>"""


def safe_pdf_download(text: str, title: str, fname: str, key: str):
    try:
        pdf_data = export_pdf(text, title)
        if not isinstance(pdf_data, bytes):
            pdf_data = bytes(pdf_data)
        st.download_button(
            "📥 PDF", data=pdf_data, file_name=f"{fname}.pdf",
            mime="application/pdf", key=key, use_container_width=True,
        )
    except Exception as e:
        st.button("📥 PDF (unavailable)", disabled=True, key=key, use_container_width=True)
        logger.warning(f"PDF export failed: {e}")


def safe_docx_download(text: str, title: str, fname: str, key: str):
    try:
        docx_data = export_docx(text, title)
        st.download_button(
            "📥 DOCX", data=docx_data, file_name=f"{fname}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key=key, use_container_width=True,
        )
    except Exception as e:
        st.button("📥 DOCX (unavailable)", disabled=True, key=key, use_container_width=True)
        logger.warning(f"DOCX export failed: {e}")


# ═══════════════════════════════════════════════════════
# DATA CRUD (DB-BACKED)
# ═══════════════════════════════════════════════════════

# ── Cases ──
def add_case(data: dict):
    data["id"] = new_id()
    data["created_at"] = datetime.now().isoformat()
    data["updated_at"] = datetime.now().isoformat()
    db_insert("cases", data)


def update_case(cid: str, updates: dict):
    updates["updated_at"] = datetime.now().isoformat()
    db_update("cases", cid, updates)


def delete_case(cid: str):
    db_delete("cases", cid)


def get_all_cases() -> list[dict]:
    return db_fetch_all("cases", "created_at DESC")


def get_active_cases() -> list[dict]:
    return db_fetch_where("cases", "status", "Active", "next_hearing ASC")


def get_hearings() -> list[dict]:
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM cases WHERE next_hearing != '' AND status IN ('Active', 'Pending') ORDER BY next_hearing ASC"
    ).fetchall()
    conn.close()
    hearings = []
    for r in rows:
        d = dict(r)
        hearings.append({
            "id": d["id"], "title": d.get("title", ""),
            "date": d.get("next_hearing", ""), "court": d.get("court", ""),
            "suit": d.get("suit_no", ""), "status": d.get("status", ""),
        })
    return hearings


# ── Case Notes (Save AI to Case) ──
def save_to_case(case_id: str, content: str, source_query: str = "", note_type: str = "ai_analysis"):
    db_insert("case_notes", {
        "id": new_id(),
        "case_id": case_id,
        "content": content,
        "note_type": note_type,
        "source_query": source_query[:500],
        "created_at": datetime.now().isoformat(),
    })


def get_case_notes(case_id: str) -> list[dict]:
    return db_fetch_where("case_notes", "case_id", case_id, "created_at DESC")


# ── Clients ──
def add_client(data: dict):
    data["id"] = new_id()
    data["created_at"] = datetime.now().isoformat()
    data["updated_at"] = datetime.now().isoformat()
    db_insert("clients", data)


def delete_client(cid: str):
    db_delete("clients", cid)


def get_all_clients() -> list[dict]:
    return db_fetch_all("clients", "name ASC")


def get_client_name(cid: str) -> str:
    if not cid:
        return "—"
    rows = db_fetch_where("clients", "id", cid)
    return rows[0].get("name", "—") if rows else "—"


def client_case_count(cid: str) -> int:
    return db_count("cases", "client_id", cid)


def client_billable(cid: str) -> float:
    return db_sum("time_entries", "amount", "client_id", cid)


# ── Time Entries ──
def add_time_entry(data: dict):
    data["id"] = new_id()
    data["created_at"] = datetime.now().isoformat()
    data["amount"] = data.get("hours", 0) * data.get("rate", 0)
    db_insert("time_entries", data)


def delete_time_entry(eid: str):
    db_delete("time_entries", eid)


def get_all_time_entries() -> list[dict]:
    return db_fetch_all("time_entries", "created_at DESC")


def total_hours() -> float:
    return db_sum("time_entries", "hours")


def total_billable() -> float:
    return db_sum("time_entries", "amount")


# ── Invoices ──
def make_invoice(client_id: str) -> dict | None:
    entries = db_fetch_where("time_entries", "client_id", client_id, "created_at ASC")
    if not entries:
        return None
    inv = {
        "id": new_id(),
        "invoice_no": f"INV-{datetime.now():%Y%m%d}-{new_id()[:4].upper()}",
        "client_id": client_id,
        "client_name": get_client_name(client_id),
        "entries_json": json.dumps(entries, default=str),
        "total": sum(e.get("amount", 0) for e in entries),
        "status": "Draft",
        "created_at": datetime.now().isoformat(),
    }
    db_insert("invoices", inv)
    return inv


def get_all_invoices() -> list[dict]:
    rows = db_fetch_all("invoices", "created_at DESC")
    for r in rows:
        try:
            r["entries"] = json.loads(r.get("entries_json", "[]"))
        except Exception:
            r["entries"] = []
    return rows


# ── Chat History ──
def add_to_history(query: str, response: str, task: str, mode: str) -> dict:
    entry = {
        "id": new_id(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "query": query,
        "response": response,
        "task": task,
        "mode": mode,
        "word_count": len(response.split()),
        "created_at": datetime.now().isoformat(),
    }
    db_insert("chat_history", entry)
    return entry


def get_chat_history(limit: int = 50) -> list[dict]:
    conn = _get_db()
    rows = conn.execute(
        f"SELECT * FROM chat_history ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── User Templates ──
def get_all_templates() -> list[dict]:
    return db_fetch_all("user_templates", "cat ASC, name ASC")


def add_user_template(name: str, cat: str, content: str):
    db_insert("user_templates", {
        "id": new_id(),
        "name": name, "cat": cat, "content": content,
        "builtin": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    })


def update_user_template(tid: str, name: str, cat: str, content: str):
    db_update("user_templates", tid, {
        "name": name, "cat": cat, "content": content,
        "updated_at": datetime.now().isoformat(),
    })


def delete_user_template(tid: str):
    db_delete("user_templates", tid)


# ── User Reference Data ──
def get_limitation_periods() -> list[dict]:
    return db_fetch_all("user_limitation_periods", "cause ASC")


def add_limitation_period(cause: str, period: str, authority: str):
    db_insert("user_limitation_periods", {
        "id": new_id(), "cause": cause, "period": period,
        "authority": authority,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    })


def update_limitation_period(lid: str, cause: str, period: str, authority: str):
    db_update("user_limitation_periods", lid, {
        "cause": cause, "period": period, "authority": authority,
        "updated_at": datetime.now().isoformat(),
    })


def delete_limitation_period(lid: str):
    db_delete("user_limitation_periods", lid)


def get_user_maxims() -> list[dict]:
    return db_fetch_all("user_maxims", "maxim ASC")


def add_user_maxim(maxim: str, meaning: str):
    db_insert("user_maxims", {
        "id": new_id(), "maxim": maxim, "meaning": meaning,
        "created_at": datetime.now().isoformat(),
    })


def delete_user_maxim(mid: str):
    db_delete("user_maxims", mid)


# ═══════════════════════════════════════════════════════
# FULL JSON EXPORT / IMPORT (for backup compatibility)
# ═══════════════════════════════════════════════════════
def full_data_export() -> str:
    """Export ALL persistent data as JSON for backup."""
    data = {
        "export_date": datetime.now().isoformat(),
        "version": "8.0",
        "cases": get_all_cases(),
        "case_notes": db_fetch_all("case_notes"),
        "clients": get_all_clients(),
        "time_entries": get_all_time_entries(),
        "invoices": get_all_invoices(),
        "chat_history": get_chat_history(limit=9999),
        "cost_log": db_fetch_all("cost_log"),
        "templates": get_all_templates(),
        "limitation_periods": get_limitation_periods(),
        "maxims": get_user_maxims(),
        "user_profile": get_user_profile(),
    }
    return json.dumps(data, indent=2, default=str)


def full_data_import(raw_json: str) -> bool:
    """Import a LexiAssist JSON backup into the database."""
    try:
        data = json.loads(raw_json)
    except Exception:
        return False

    if not isinstance(data, dict):
        return False

    table_map = {
        "cases": "cases",
        "clients": "clients",
        "time_entries": "time_entries",
        "chat_history": "chat_history",
        "cost_log": "cost_log",
    }

    conn = _get_db()
    for json_key, table in table_map.items():
        if json_key in data and isinstance(data[json_key], list):
            for row in data[json_key]:
                if isinstance(row, dict) and "id" in row:
                    cols = ", ".join(row.keys())
                    placeholders = ", ".join(["?"] * len(row))
                    try:
                        conn.execute(
                            f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders})",
                            list(row.values()),
                        )
                    except Exception:
                        continue

    # Case notes
    if "case_notes" in data and isinstance(data["case_notes"], list):
        for row in data["case_notes"]:
            if isinstance(row, dict) and "id" in row:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO case_notes (id, case_id, content, note_type, source_query, created_at) VALUES (?,?,?,?,?,?)",
                        (row.get("id",""), row.get("case_id",""), row.get("content",""),
                         row.get("note_type",""), row.get("source_query",""), row.get("created_at","")),
                    )
                except Exception:
                    continue

    # Templates
    if "templates" in data and isinstance(data["templates"], list):
        for row in data["templates"]:
            if isinstance(row, dict) and "id" in row:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO user_templates (id, name, cat, content, builtin, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                        (row.get("id",""), row.get("name",""), row.get("cat",""),
                         row.get("content",""), row.get("builtin", 0),
                         row.get("created_at",""), row.get("updated_at","")),
                    )
                except Exception:
                    continue

    # Limitation periods
    if "limitation_periods" in data and isinstance(data["limitation_periods"], list):
        for row in data["limitation_periods"]:
            if isinstance(row, dict) and "id" in row:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO user_limitation_periods (id, cause, period, authority, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                        (row.get("id",""), row.get("cause",""), row.get("period",""),
                         row.get("authority",""), row.get("created_at",""), row.get("updated_at","")),
                    )
                except Exception:
                    continue

    # Maxims
    if "maxims" in data and isinstance(data["maxims"], list):
        for row in data["maxims"]:
            if isinstance(row, dict) and "id" in row:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO user_maxims (id, maxim, meaning, created_at) VALUES (?,?,?,?)",
                        (row.get("id",""), row.get("maxim",""), row.get("meaning",""), row.get("created_at","")),
                    )
                except Exception:
                    continue

    conn.commit()
    conn.close()
    return True


# ═══════════════════════════════════════════════════════
# END OF PART 2 — Continue with Part 3 below
# ═══════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════
# RENDER: SECURE SETUP SCREEN
# ═══════════════════════════════════════════════════════
def render_setup_screen():
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
            "Google Gemini API Key", type="password",
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
# RENDER: AUTH GATE
# ═══════════════════════════════════════════════════════
def render_auth_gate():
    """Show login screen if user profile has a password set."""
    st.markdown("""
    <div class="hero">
        <h1>⚖️ LexiAssist v8.0</h1>
        <p>Please log in to continue</p>
    </div>
    """, unsafe_allow_html=True)

    profile = get_user_profile()
    firm = profile.get("firm_name", "") if profile else ""
    if firm:
        st.markdown(f"### 🏢 {esc(firm)}")

    with st.form("auth_form"):
        password = st.text_input("Password", type="password", placeholder="Enter your password…")
        submitted = st.form_submit_button("🔓 Log In", type="primary", use_container_width=True)
        if submitted:
            if profile and verify_password(password, profile.get("password_hash", "")):
                st.session_state.authenticated = True
                st.success("✅ Authenticated!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Incorrect password.")


# ═══════════════════════════════════════════════════════
# RENDER: SIDEBAR
# ═══════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚖️ LexiAssist v8.0")

        profile = get_user_profile()
        if profile and profile.get("firm_name"):
            st.caption(f"🏢 {profile['firm_name']}")
        else:
            st.caption("Elite AI Legal Engine")
        st.divider()

        # ── Status Metrics ──
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Active Cases", len(get_active_cases()))
        with c2:
            st.metric("AI Sessions", db_count("chat_history"))

        st.divider()

        # ── Response Mode ──
        st.markdown("##### 🧠 Response Mode")
        modes = list(RESPONSE_MODES.keys())
        current_idx = modes.index(st.session_state.response_mode) if st.session_state.response_mode in modes else 1
        mode = st.radio(
            "Depth", modes, index=current_idx,
            format_func=lambda x: RESPONSE_MODES[x]["label"],
            key="sidebar_mode_radio", label_visibility="collapsed",
        )
        if mode != st.session_state.response_mode:
            st.session_state.response_mode = mode
            st.rerun()

        sel_mode = RESPONSE_MODES[st.session_state.response_mode]
        st.caption(f"{sel_mode['desc']} · {sel_mode['tokens']:,} tokens")

        st.divider()

        # ── Theme ──
        st.markdown("##### 🎨 Theme")
        theme_names = list(THEMES.keys())
        current_theme_idx = theme_names.index(st.session_state.theme) if st.session_state.theme in theme_names else 0
        theme = st.selectbox(
            "Theme", theme_names, index=current_theme_idx,
            key="sidebar_theme_sel", label_visibility="collapsed",
        )
        if theme != st.session_state.theme:
            st.session_state.theme = theme
            st.rerun()

        st.divider()

        # ── AI Engine ──
        st.markdown("##### 🤖 AI Engine")
        if st.session_state.api_configured:
            st.success(f"✅ `{st.session_state.gemini_model}`")
            model_sel = st.selectbox(
                "Switch Model", SUPPORTED_MODELS,
                index=SUPPORTED_MODELS.index(st.session_state.gemini_model) if st.session_state.gemini_model in SUPPORTED_MODELS else 0,
                key="sidebar_model_sel", label_visibility="collapsed",
            )
            if model_sel != st.session_state.gemini_model:
                st.session_state.gemini_model = model_sel
                st.rerun()

            # Cost summary
            cs = get_cost_summary()
            if cs["total_calls"] > 0:
                st.caption(f"💰 Today: ${cs['today_cost']:.4f} ({cs['today_calls']} calls)")
                st.caption(f"💰 Month: ${cs['month_cost']:.4f} ({cs['month_calls']} calls)")
        else:
            st.error("🔴 Not connected")

        st.divider()

        # ── Data Management ──
        st.markdown("##### 💾 Data")

        if st.button("📥 Export Backup (JSON)", use_container_width=True, key="sidebar_export_btn"):
            export_str = full_data_export()
            st.download_button(
                "⬇️ Download", export_str,
                f"lexiassist_backup_{datetime.now():%Y%m%d_%H%M}.json",
                "application/json", key="sidebar_dl_json", use_container_width=True,
            )

        uploaded = st.file_uploader(
            "📤 Import", type=UPLOAD_TYPES, accept_multiple_files=False,
            key="sidebar_file_upload", label_visibility="collapsed",
            help="Supports: PDF, DOCX, TXT, XLSX, CSV, JSON, RTF",
        )
        if uploaded:
            try:
                ext = uploaded.name.split(".")[-1].lower()
                if ext == "json":
                    raw = uploaded.getvalue().decode("utf-8", errors="ignore")
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict) and any(k in parsed for k in ["cases", "clients", "version"]):
                        if full_data_import(raw):
                            st.success("✅ Backup imported!")
                            st.rerun()
                        else:
                            st.error("❌ Import failed.")
                    else:
                        text = json.dumps(parsed, indent=2)
                        st.session_state.imported_doc = {
                            "name": uploaded.name, "type": ext,
                            "size": len(uploaded.getvalue()),
                            "full_text": text, "preview": text[:600],
                        }
                        st.session_state.context_enabled = True
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
                    st.session_state.context_enabled = True
                    st.success(f"✅ {uploaded.name} loaded → AI Assistant")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Import error: {e}")

        st.divider()
        st.caption("⚖️ LexiAssist v8.0 © 2026")
        st.caption("🧠 Elite AI · 🇳🇬 Nigerian Law")


# ═══════════════════════════════════════════════════════
# RENDER: HOME / DASHBOARD
# ═══════════════════════════════════════════════════════
def render_home():
    st.markdown("""
    <div class="hero">
        <h1>⚖️ LexiAssist v8.0</h1>
        <p>Elite AI Legal Engine for Nigerian Lawyers<br>
        Position-taking · Strategy-driven · Risk-ranked · Litigator-minded</p>
    </div>
    """, unsafe_allow_html=True)

    all_cases = get_all_cases()
    active = get_active_cases()
    clients = get_all_clients()
    th = total_hours()
    sessions = db_count("chat_history")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{len(all_cases)}</div><div class="stat-label">Total Cases</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{len(active)}</div><div class="stat-label">Active Cases</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{len(clients)}</div><div class="stat-label">Clients</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{th:.1f}h</div><div class="stat-label">Billable Hours</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{sessions}</div><div class="stat-label">AI Sessions</div></div>', unsafe_allow_html=True)

    st.markdown("")

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
        history = get_chat_history(limit=6)
        if history:
            for entry in history:
                mode_lbl = RESPONSE_MODES.get(entry.get("mode", ""), {}).get("label", "")
                q = entry.get("query", "")
                st.markdown(f"""<div class="history-item">
                    <strong>{esc(q[:80])}{'…' if len(q) > 80 else ''}</strong><br>
                    <small>{esc(entry.get('timestamp', ''))} · {esc(mode_lbl)} · {entry.get('word_count', 0)} words</small>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No AI sessions yet. Go to AI Assistant to start.")

        # Cost overview
        cs = get_cost_summary()
        if cs["total_calls"] > 0:
            st.markdown("### 💰 AI Cost Tracker")
            cc1, cc2 = st.columns(2)
            with cc1:
                st.metric("This Month", f"${cs['month_cost']:.4f}")
            with cc2:
                st.metric("All Time", f"${cs['total_cost']:.4f}")

    st.markdown("---")
    st.markdown("### 🏆 Elite Features")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        st.markdown('<div class="custom-card"><h4>🎯 Position-Taking</h4><p>Firm conclusions backed by authority — no hedging</p></div>', unsafe_allow_html=True)
    with f2:
        st.markdown('<div class="custom-card"><h4>📊 Risk Ranking</h4><p>Parties ranked by exposure: High / Medium / Low</p></div>', unsafe_allow_html=True)
    with f3:
        st.markdown('<div class="custom-card"><h4>📑 Contract Review</h4><p>Clause-by-clause analysis with red flag matrix</p></div>', unsafe_allow_html=True)
    with f4:
        st.markdown('<div class="custom-card"><h4>💾 Persistent Data</h4><p>Cases, clients, and history survive restarts</p></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# RENDER: AI ASSISTANT
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

    # ── Document Context ──
    doc_context = ""
    if st.session_state.imported_doc:
        doc = st.session_state.imported_doc
        with st.expander(f"📎 Imported: {doc['name']}", expanded=False):
            st.caption(f"Type: {doc['type'].upper()} · Size: {doc['size']:,} bytes")
            st.text_area("Preview", doc["preview"], height=120, disabled=True, key="doc_preview_ta")
            dc1, dc2 = st.columns(2)
            with dc1:
                ctx_toggle = st.checkbox(
                    "Use as context for query",
                    value=st.session_state.context_enabled,
                    key="ctx_toggle",
                )
                st.session_state.context_enabled = ctx_toggle
            with dc2:
                if st.button("🗑️ Clear Document", key="clear_doc_btn", use_container_width=True):
                    st.session_state.imported_doc = None
                    st.session_state.context_enabled = False
                    st.rerun()

        if st.session_state.context_enabled and st.session_state.imported_doc:
            doc_context = st.session_state.imported_doc.get("full_text", "")

    # ── Clickable History ──
    history = get_chat_history(limit=15)
    if history:
        with st.expander(f"📚 Session History ({db_count('chat_history')} total)", expanded=False):
            for i, entry in enumerate(history):
                mode_lbl = RESPONSE_MODES.get(entry.get("mode", ""), {}).get("label", "")
                hc1, hc2 = st.columns([5, 1])
                with hc1:
                    q = entry.get("query", "")
                    st.markdown(f"""<div class="history-item">
                        <strong>{esc(q[:100])}</strong><br>
                        <small>{esc(entry.get('timestamp', ''))} · {esc(mode_lbl)} · {entry.get('word_count', 0)} words</small>
                    </div>""", unsafe_allow_html=True)
                with hc2:
                    if st.button("📖", key=f"load_hist_{entry['id']}", use_container_width=True, help="Load this session"):
                        st.session_state.selected_history_idx = entry["id"]
                        st.session_state.last_response = entry.get("response", "")
                        st.session_state.original_query = entry.get("query", "")
                        st.rerun()

    # ── Show selected history entry ──
    if st.session_state.selected_history_idx is not None:
        sel_id = st.session_state.selected_history_idx
        rows = db_fetch_where("chat_history", "id", sel_id)
        if rows:
            entry = rows[0]
            st.markdown("---")
            st.markdown(f"### 📖 Viewing: Session from {entry.get('timestamp', '')}")
            st.markdown(f"**Query:** {esc(entry['query'])}")
            st.markdown(f'<div class="response-box">{esc(entry["response"])}</div>', unsafe_allow_html=True)

            fname = f"LexiAssist_{entry.get('timestamp', '').replace(' ', '_').replace(':', '')}"
            hx1, hx2, hx3, hx4 = st.columns(4)
            with hx1:
                st.download_button("📥 TXT", export_txt(entry["response"]), f"{fname}.txt", "text/plain", key=f"hist_dl_txt_{sel_id}", use_container_width=True)
            with hx2:
                st.download_button("📥 HTML", export_html(entry["response"]), f"{fname}.html", "text/html", key=f"hist_dl_html_{sel_id}", use_container_width=True)
            with hx3:
                safe_pdf_download(entry["response"], "Legal Analysis", fname, f"hist_dl_pdf_{sel_id}")
            with hx4:
                safe_docx_download(entry["response"], "Legal Analysis", fname, f"hist_dl_docx_{sel_id}")

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
            "Task Type", task_keys,
            format_func=lambda x: f"{TASK_TYPES[x]['label']} — {TASK_TYPES[x]['desc']}",
            key="ai_task_sel",
        )
    with tc2:
        st.markdown("")
        st.markdown(f"**Mode:** {mode_info['label']}")
        st.caption(f"Max: {mode_info['tokens']:,} tokens")

    prefill = st.session_state.pop("loaded_template", "") if st.session_state.get("loaded_template") else ""
    query = st.text_area(
        "Your Legal Query", value=prefill, height=200,
        placeholder="Describe your legal question in detail…\n\nFor Contract Review: paste or upload the contract text and select 📑 Contract Review as task type.",
        key="ai_query_ta",
    )

    # ── Action Buttons ──
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        generate_btn = st.button(
            f"🧠 Generate ({mode_info['label']})", type="primary",
            use_container_width=True, disabled=not query.strip(), key="ai_generate_btn",
        )
    with bc2:
        issue_btn = st.button(
            "🔍 Issue Spot", use_container_width=True,
            disabled=not query.strip(), key="ai_issue_btn",
        )
    with bc3:
        clear_btn = st.button("🗑️ Clear", use_container_width=True, key="ai_clear_btn")

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

        # ── Save to Case ──
        cases = get_all_cases()
        if cases:
            with st.expander("💾 Save to Case File", expanded=False):
                case_names = [f"{c.get('title', 'Untitled')} ({c.get('suit_no', 'No suit#')})" for c in cases]
                selected_case = st.selectbox("Select Case", case_names, key="save_to_case_sel")
                if st.button("💾 Save Analysis to Case", key="save_to_case_btn", type="primary", use_container_width=True):
                    case_idx = case_names.index(selected_case)
                    case_id = cases[case_idx]["id"]
                    save_to_case(case_id, response, st.session_state.original_query)
                    st.success(f"✅ Analysis saved to: {cases[case_idx].get('title', '')}")

        # ── Quality Critique ──
        if mode in ("standard", "comprehensive"):
            with st.expander("🔎 Quality Assessment", expanded=False):
                if st.button("Run Critique", key="run_critique_btn"):
                    with st.spinner("Assessing quality…"):
                        critique = run_critique(st.session_state.original_query, response)
                    st.markdown(f'<div class="response-box">{esc(critique)}</div>', unsafe_allow_html=True)

        # ── Follow-up ──
        st.markdown("### 🔄 Follow-Up Question")
        followup = st.text_input(
            "Ask a follow-up based on the analysis above:",
            placeholder="E.g.: 'What if the contract had an arbitration clause?'",
            key="followup_input",
        )
        if st.button("🔄 Follow Up", disabled=not followup.strip(), key="followup_btn"):
            with st.spinner("🔄 Processing follow-up…"):
                fu_result = run_followup(
                    st.session_state.original_query, response,
                    followup.strip(), mode,
                )
            st.session_state.last_response = fu_result
            add_to_history(f"[Follow-up] {followup.strip()}", fu_result, "general", mode)
            st.rerun()

        st.markdown('<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated legal analysis. This does not constitute legal advice. Verify all citations and authorities independently before reliance.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# RENDER: LEGAL RESEARCH
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
        "🔍 Research Query", height=140,
        placeholder="E.g.: 'What are the grounds for setting aside an arbitral award under the Arbitration and Mediation Act 2023?'",
        key="research_query_ta",
    )

    rc1, rc2 = st.columns([1, 1])
    with rc1:
        research_btn = st.button(
            f"📚 Research ({mode_info['label']})", type="primary",
            use_container_width=True, disabled=not query.strip(), key="research_go_btn",
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

        # Save to case
        cases = get_all_cases()
        if cases:
            with st.expander("💾 Save to Case File", expanded=False):
                case_names = [f"{c.get('title', 'Untitled')} ({c.get('suit_no', '')})" for c in cases]
                sel = st.selectbox("Select Case", case_names, key="res_save_case_sel")
                if st.button("💾 Save Research to Case", key="res_save_case_btn", type="primary", use_container_width=True):
                    cidx = case_names.index(sel)
                    save_to_case(cases[cidx]["id"], result, st.session_state.get("research_query_ta", ""), "research")
                    st.success(f"✅ Saved to: {cases[cidx].get('title', '')}")

        st.markdown('<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated research. Verify all citations independently.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# RENDER: CASES
# ═══════════════════════════════════════════════════════
def render_cases():
    st.markdown("""<div class="page-header">
        <h2>📁 Case Manager</h2>
        <p>Track cases, hearings, deadlines, and attached AI analyses</p>
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
                clients = get_all_clients()
                client_opts = ["— None —"] + [c.get("name", "?") for c in clients]
                client_sel = st.selectbox("Client", client_opts, key="case_client_inp")
                next_hearing = st.date_input("Next Hearing", value=None, key="case_hearing_inp")
            notes = st.text_area("Notes", height=80, key="case_notes_inp")

            if st.form_submit_button("➕ Add Case", type="primary"):
                if title.strip():
                    client_id = ""
                    if client_sel != "— None —":
                        cidx = client_opts.index(client_sel) - 1
                        if 0 <= cidx < len(clients):
                            client_id = clients[cidx]["id"]
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
        cases = get_all_cases()
        if not cases:
            st.info("No cases yet. Add one in the ➕ Add Case tab.")
            return

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
            cname = get_client_name(c.get("client_id", ""))
            notes_count = len(get_case_notes(c["id"]))

            st.markdown(f"""<div class="custom-card">
                <h4>{esc(c.get('title', 'Untitled'))}</h4>
                <span class="badge badge-info">{esc(c.get('status', ''))}</span>
                {f'<span class="badge badge-ok">{notes_count} saved analyses</span>' if notes_count else ''}
                <br>Suit: <strong>{esc(c.get('suit_no', '—'))}</strong> ·
                Court: {esc(c.get('court', '—'))} ·
                Client: {esc(cname)} ·
                Hearing: {esc(fmt_date(c.get('next_hearing', '')))}
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

                # ── Attached Case Notes / AI Analyses ──
                case_notes = get_case_notes(c["id"])
                if case_notes:
                    st.markdown("---")
                    st.markdown(f"##### 📎 Saved Analyses ({len(case_notes)})")
                    for cn in case_notes:
                        with st.expander(f"📄 {cn.get('note_type', 'note').replace('_', ' ').title()} — {fmt_date(cn.get('created_at', ''))}", expanded=False):
                            if cn.get("source_query"):
                                st.caption(f"**Query:** {cn['source_query'][:200]}")
                            st.markdown(f'<div class="response-box">{esc(cn.get("content", "")[:3000])}</div>', unsafe_allow_html=True)
                            cn_fname = f"CaseNote_{c.get('suit_no', c['id'])}_{cn['id']}"
                            cn1, cn2 = st.columns(2)
                            with cn1:
                                st.download_button(
                                    "📥 TXT", export_txt(cn.get("content", ""), f"Case Note - {c.get('title', '')}"),
                                    f"{cn_fname}.txt", "text/plain", key=f"cn_txt_{cn['id']}", use_container_width=True,
                                )
                            with cn2:
                                safe_pdf_download(cn.get("content", ""), f"Case Note - {c.get('title', '')}", cn_fname, f"cn_pdf_{cn['id']}")


# ═══════════════════════════════════════════════════════
# RENDER: CALENDAR
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
            badge_class, border_color = "badge-err", "#dc2626"
        elif d <= 3:
            badge_class, border_color = "badge-err", "#dc2626"
        elif d <= 7:
            badge_class, border_color = "badge-warn", "#f59e0b"
        else:
            badge_class, border_color = "badge-ok", "#059669"

        st.markdown(f"""<div class="custom-card" style="border-left: 4px solid {border_color};">
            <h4>{esc(h['title'])}</h4>
            Suit: <strong>{esc(h['suit'])}</strong> · Court: {esc(h['court'])} · Status: {esc(h['status'])}<br>
            📅 <strong>{esc(fmt_date(h['date']))}</strong>
            <span class="badge {badge_class}">{esc(relative_date(h['date']))}</span>
        </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# END OF PART 3 — Continue with Part 4 below
# ═══════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════
# RENDER: TEMPLATES (with user-editable)
# ═══════════════════════════════════════════════════════
def render_templates():
    st.markdown("""<div class="page-header">
        <h2>📋 Document Templates</h2>
        <p>Built-in and custom Nigerian legal document templates</p>
    </div>""", unsafe_allow_html=True)

    tab_browse, tab_add = st.tabs(["📋 Browse Templates", "➕ Add Custom Template"])

    with tab_add:
        with st.form("add_template_form", clear_on_submit=True):
            st.markdown("#### ➕ New Custom Template")
            t_name = st.text_input("Template Name *", key="tmpl_name_inp")
            t_cat = st.text_input("Category", value="Custom", key="tmpl_cat_inp",
                                  help="E.g.: Corporate, Litigation, Property, Commercial")
            t_content = st.text_area("Template Content *", height=350, key="tmpl_content_inp",
                                     placeholder="Paste or type your template here…\nUse [PLACEHOLDER] for fields to fill in.")
            if st.form_submit_button("➕ Add Template", type="primary"):
                if t_name.strip() and t_content.strip():
                    add_user_template(t_name.strip(), t_cat.strip() or "Custom", t_content.strip())
                    st.success(f"✅ Template '{t_name}' saved!")
                    st.rerun()
                else:
                    st.error("❌ Name and content are required.")

    with tab_browse:
        templates = get_all_templates()
        if not templates:
            st.info("No templates found. Built-in templates should appear automatically.")
            return

        cats = sorted(set(t.get("cat", "Other") for t in templates))
        sel_cat = st.selectbox("Filter by Category", ["All"] + cats, key="tmpl_cat_sel")

        filtered = templates if sel_cat == "All" else [t for t in templates if t.get("cat") == sel_cat]
        st.caption(f"Showing {len(filtered)} template{'s' if len(filtered) != 1 else ''}")

        for t in filtered:
            is_builtin = t.get("builtin", 0) == 1
            label = "Built-in" if is_builtin else "Custom"
            badge = "badge-info" if is_builtin else "badge-ok"

            st.markdown(f"""<div class="custom-card">
                <h4>{esc(t.get('name', 'Untitled'))}</h4>
                <span class="badge {badge}">{label}</span>
                <span class="badge badge-info">{esc(t.get('cat', ''))}</span>
            </div>""", unsafe_allow_html=True)

            tc1, tc2, tc3, tc4 = st.columns(4)
            with tc1:
                if st.button("👁️ Preview", key=f"prev_t_{t['id']}", use_container_width=True):
                    st.code(t.get("content", ""), language=None)
            with tc2:
                if st.button("📋 Load to AI", key=f"load_t_{t['id']}", use_container_width=True):
                    st.session_state.loaded_template = t.get("content", "")
                    st.success(f"✅ '{t['name']}' loaded! Go to AI Assistant tab.")
            with tc3:
                st.download_button(
                    "📥 Download", t.get("content", ""),
                    f"{t.get('name', 'template').replace(' ', '_')}.txt",
                    "text/plain", key=f"dl_t_{t['id']}", use_container_width=True,
                )
            with tc4:
                if not is_builtin:
                    if st.button("🗑️ Delete", key=f"del_t_{t['id']}", use_container_width=True):
                        delete_user_template(t["id"])
                        st.success("✅ Deleted!")
                        st.rerun()
                else:
                    st.button("🔒 Built-in", disabled=True, key=f"lock_t_{t['id']}", use_container_width=True)

            # Edit custom templates
            if not is_builtin:
                with st.expander(f"✏️ Edit: {t.get('name', '')[:40]}", expanded=False):
                    e_name = st.text_input("Name", value=t.get("name", ""), key=f"edit_tn_{t['id']}")
                    e_cat = st.text_input("Category", value=t.get("cat", ""), key=f"edit_tc_{t['id']}")
                    e_content = st.text_area("Content", value=t.get("content", ""), height=250, key=f"edit_tx_{t['id']}")
                    if st.button("💾 Save Changes", key=f"save_t_{t['id']}", use_container_width=True):
                        update_user_template(t["id"], e_name.strip(), e_cat.strip(), e_content.strip())
                        st.success("✅ Updated!")
                        st.rerun()


# ═══════════════════════════════════════════════════════
# RENDER: CLIENTS
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
        clients = get_all_clients()
        if not clients:
            st.info("No clients yet. Add one in the ➕ Add Client tab.")
            return

        search = st.text_input("🔍 Search clients", key="cl_search_inp", placeholder="Name, email, type…")
        filtered = clients
        if search.strip():
            s = search.strip().lower()
            filtered = [c for c in filtered if
                        s in c.get("name", "").lower() or
                        s in c.get("email", "").lower() or
                        s in c.get("type", "").lower()]

        st.caption(f"Showing {len(filtered)} of {len(clients)} clients")

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

            if st.button("🗑️ Delete", key=f"del_cl_{cl['id']}", use_container_width=True):
                delete_client(cl["id"])
                st.success("✅ Deleted!")
                st.rerun()


# ═══════════════════════════════════════════════════════
# RENDER: BILLING
# ═══════════════════════════════════════════════════════
def render_billing():
    st.markdown("""<div class="page-header">
        <h2>💰 Billing Manager</h2>
        <p>Time entries, invoicing, financial reports, and AI cost tracking</p>
    </div>""", unsafe_allow_html=True)

    tab_time, tab_inv, tab_report, tab_cost = st.tabs([
        "⏱️ Time Entries", "📄 Invoices", "📊 Reports", "🤖 AI Costs"
    ])

    # ── Time Entries ──
    with tab_time:
        with st.form("add_time_form", clear_on_submit=True):
            st.markdown("#### ➕ New Time Entry")
            bt1, bt2 = st.columns(2)
            with bt1:
                clients = get_all_clients()
                cl_names = [c.get("name", "?") for c in clients]
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
                        "client_id": clients[cidx]["id"],
                        "client_name": cl_sel_b,
                        "description": desc.strip(),
                        "hours": hours, "rate": rate,
                        "entry_date": str(entry_date),
                    })
                    st.success(f"✅ {hours}h @ {fmt_currency(rate)}/hr added!")
                    st.rerun()
                else:
                    st.error("❌ Fill all required fields.")

        entries = get_all_time_entries()
        if entries:
            st.markdown("#### 📋 Recent Entries")
            for te in entries[:20]:
                st.markdown(f"""<div class="custom-card">
                    <strong>{esc(te.get('description', ''))}</strong><br>
                    {esc(te.get('client_name', ''))} ·
                    {te.get('hours', 0)}h @ {esc(fmt_currency(te.get('rate', 0)))}/hr ·
                    <strong>{esc(fmt_currency(te.get('amount', 0)))}</strong> ·
                    {esc(fmt_date(te.get('entry_date', '')))}
                </div>""", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_te_{te['id']}", help="Delete entry"):
                    delete_time_entry(te["id"])
                    st.rerun()

    # ── Invoices ──
    with tab_inv:
        st.markdown("#### 📄 Generate Invoice")
        clients = get_all_clients()
        if clients:
            cl_names_inv = [c.get("name", "?") for c in clients]
            inv_client = st.selectbox("Client", cl_names_inv, key="inv_cl_sel")
            if st.button("📄 Generate Invoice", type="primary", key="gen_inv_btn", use_container_width=True):
                cidx = cl_names_inv.index(inv_client)
                cid = clients[cidx]["id"]
                inv = make_invoice(cid)
                if inv:
                    st.success(f"✅ Invoice {inv['invoice_no']} — {fmt_currency(inv['total'])}")
                    st.rerun()
                else:
                    st.warning("No billable entries for this client.")
        else:
            st.info("Add clients first.")

        invoices = get_all_invoices()
        if invoices:
            st.markdown("#### 📋 All Invoices")
            for inv in invoices:
                inv_entries = inv.get("entries", [])
                inv_text = (
                    f"INVOICE: {inv.get('invoice_no', '')}\n"
                    f"Date: {fmt_date(inv.get('created_at', ''))}\n"
                    f"Client: {inv.get('client_name', '')}\n"
                    f"Status: {inv.get('status', '')}\n\n"
                    f"{'='*40}\n"
                )
                for e in inv_entries:
                    inv_text += f"{e.get('description', '')} | {e.get('hours', 0)}h | {fmt_currency(e.get('amount', 0))}\n"
                inv_text += f"{'='*40}\nTOTAL: {fmt_currency(inv.get('total', 0))}\n"

                profile = get_user_profile()
                if profile and profile.get("firm_name"):
                    inv_text = f"{profile['firm_name']}\n\n" + inv_text

                st.markdown(f"""<div class="custom-card">
                    <h4>{esc(inv.get('invoice_no', ''))}</h4>
                    {esc(inv.get('client_name', ''))} · {esc(fmt_date(inv.get('created_at', '')))} ·
                    <strong>{esc(fmt_currency(inv.get('total', 0)))}</strong> ·
                    <span class="badge badge-info">{esc(inv.get('status', ''))}</span>
                </div>""", unsafe_allow_html=True)

                ic1, ic2, ic3 = st.columns(3)
                with ic1:
                    st.download_button(
                        "📥 TXT", export_txt(inv_text, f"Invoice {inv.get('invoice_no', '')}"),
                        f"Invoice_{inv.get('invoice_no', '')}.txt", "text/plain",
                        key=f"inv_txt_{inv['id']}", use_container_width=True,
                    )
                with ic2:
                    safe_pdf_download(inv_text, f"Invoice {inv.get('invoice_no', '')}",
                                      f"Invoice_{inv.get('invoice_no', '')}", f"inv_pdf_{inv['id']}")
                with ic3:
                    safe_docx_download(inv_text, f"Invoice {inv.get('invoice_no', '')}",
                                       f"Invoice_{inv.get('invoice_no', '')}", f"inv_docx_{inv['id']}")

    # ── Reports ──
    with tab_report:
        st.markdown("#### 📊 Billing Summary")
        entries = get_all_time_entries()
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
                    fig = px.bar(chart_df, x="Client", y="Amount",
                                 title="Billable Amount by Client",
                                 color_discrete_sequence=["#059669"])
                    st.plotly_chart(fig, use_container_width=True)

                if "entry_date" in df.columns and "hours" in df.columns:
                    df["entry_date"] = pd.to_datetime(df["entry_date"], errors="coerce")
                    time_df = df.dropna(subset=["entry_date"]).groupby("entry_date")["hours"].sum().reset_index()
                    if not time_df.empty:
                        fig2 = px.line(time_df, x="entry_date", y="hours",
                                       title="Hours Over Time",
                                       color_discrete_sequence=["#059669"])
                        st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No time entries to report.")

    # ── AI Cost Tracker ──
    with tab_cost:
        st.markdown("#### 🤖 Gemini API Cost Tracker")
        cs = get_cost_summary()

        if cs["total_calls"] == 0:
            st.info("No API calls recorded yet. Costs are tracked automatically when you use the AI Assistant.")
        else:
            mc1, mc2, mc3, mc4 = st.columns(4)
            with mc1:
                st.metric("Total Calls", cs["total_calls"])
            with mc2:
                st.metric("Today", f"${cs['today_cost']:.4f}")
            with mc3:
                st.metric("This Month", f"${cs['month_cost']:.4f}")
            with mc4:
                st.metric("All Time", f"${cs['total_cost']:.4f}")

            st.markdown("---")

            tk1, tk2 = st.columns(2)
            with tk1:
                st.metric("Total Input Tokens", f"{cs['total_prompt_tokens']:,}")
            with tk2:
                st.metric("Total Output Tokens", f"{cs['total_response_tokens']:,}")

            # Cost log table
            cost_rows = db_fetch_all("cost_log", "created_at DESC")
            if cost_rows and HAS_PLOTLY:
                df_cost = pd.DataFrame(cost_rows)
                if "created_at" in df_cost.columns:
                    df_cost["date"] = pd.to_datetime(df_cost["created_at"], errors="coerce").dt.date
                    daily = df_cost.groupby("date")["total_cost"].sum().reset_index()
                    daily.columns = ["Date", "Cost (USD)"]
                    if not daily.empty:
                        fig_cost = px.bar(daily, x="Date", y="Cost (USD)",
                                          title="Daily API Cost",
                                          color_discrete_sequence=["#059669"])
                        st.plotly_chart(fig_cost, use_container_width=True)

            if cost_rows:
                st.markdown("##### 📋 Recent API Calls")
                for cr in cost_rows[:15]:
                    st.markdown(f"""<div class="custom-card">
                        <strong>{esc(cr.get('model', ''))}</strong> ·
                        In: {cr.get('prompt_tokens', 0):,} · Out: {cr.get('response_tokens', 0):,} ·
                        <strong>${cr.get('total_cost', 0):.6f}</strong> ·
                        {esc(fmt_date(cr.get('created_at', '')))}<br>
                        <small>{esc(cr.get('query_preview', '')[:120])}</small>
                    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# RENDER: TOOLS (with editable references)
# ═══════════════════════════════════════════════════════
def render_tools():
    st.markdown("""<div class="page-header">
        <h2>🔧 Legal Reference Tools</h2>
        <p>Limitation periods · Court hierarchy · Latin maxims (editable)</p>
    </div>""", unsafe_allow_html=True)

    tab_lim, tab_court, tab_maxim = st.tabs([
        "⏳ Limitation Periods", "🏛️ Court Hierarchy", "📜 Legal Maxims"
    ])

    # ── Limitation Periods (editable) ──
    with tab_lim:
        st.markdown("#### ⏳ Limitation Periods (Nigeria)")
        st.caption("State-specific limitation laws apply. These are general references — verify for your jurisdiction.")

        periods = get_limitation_periods()
        if periods:
            df_lim = pd.DataFrame(periods)
            display_cols = ["cause", "period", "authority"]
            available = [c for c in display_cols if c in df_lim.columns]
            if available:
                df_display = df_lim[available].copy()
                df_display.columns = [c.title() for c in available]
                st.dataframe(df_display, use_container_width=True, hide_index=True)

                st.download_button(
                    "📥 Download CSV", df_display.to_csv(index=False),
                    "limitation_periods_nigeria.csv", "text/csv", key="dl_lim_csv",
                )

        # Edit existing
        with st.expander("✏️ Edit Limitation Periods", expanded=False):
            for lp in periods:
                with st.container():
                    lc1, lc2, lc3, lc4 = st.columns([2, 1, 3, 1])
                    with lc1:
                        e_cause = st.text_input("Cause", value=lp.get("cause", ""), key=f"lp_c_{lp['id']}", label_visibility="collapsed")
                    with lc2:
                        e_period = st.text_input("Period", value=lp.get("period", ""), key=f"lp_p_{lp['id']}", label_visibility="collapsed")
                    with lc3:
                        e_auth = st.text_input("Authority", value=lp.get("authority", ""), key=f"lp_a_{lp['id']}", label_visibility="collapsed")
                    with lc4:
                        col_save, col_del = st.columns(2)
                        with col_save:
                            if st.button("💾", key=f"lp_save_{lp['id']}", help="Save"):
                                update_limitation_period(lp["id"], e_cause, e_period, e_auth)
                                st.rerun()
                        with col_del:
                            if st.button("🗑️", key=f"lp_del_{lp['id']}", help="Delete"):
                                delete_limitation_period(lp["id"])
                                st.rerun()

        # Add new
        with st.expander("➕ Add Limitation Period", expanded=False):
            with st.form("add_lp_form", clear_on_submit=True):
                alc1, alc2, alc3 = st.columns([2, 1, 3])
                with alc1:
                    n_cause = st.text_input("Cause of Action *", key="new_lp_cause")
                with alc2:
                    n_period = st.text_input("Period *", key="new_lp_period")
                with alc3:
                    n_auth = st.text_input("Authority", key="new_lp_auth")
                if st.form_submit_button("➕ Add", type="primary"):
                    if n_cause.strip() and n_period.strip():
                        add_limitation_period(n_cause.strip(), n_period.strip(), n_auth.strip())
                        st.success("✅ Added!")
                        st.rerun()
                    else:
                        st.error("❌ Cause and Period are required.")

    # ── Court Hierarchy ──
    with tab_court:
        st.markdown("#### 🏛️ Nigerian Court Hierarchy")
        st.caption("From the Supreme Court down to courts of first instance")
        for c in COURT_HIERARCHY:
            indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * (c["level"] - 1)
            level_label = {1: "APEX", 2: "APPELLATE", 3: "SUPERIOR", 4: "INTERMEDIATE", 5: "LOWER"}.get(c["level"], "")
            st.markdown(f"""<div class="tool-card">
                {indent}{c['icon']} <strong>{esc(c['name'])}</strong>
                <span class="badge badge-info">{level_label}</span><br>
                {indent}&nbsp;&nbsp;&nbsp;&nbsp;<small>{esc(c['desc'])}</small>
            </div>""", unsafe_allow_html=True)

    # ── Legal Maxims (editable) ──
    with tab_maxim:
        st.markdown("#### 📜 Legal Maxims")

        maxims = get_user_maxims()
        search = st.text_input("🔍 Search maxims", key="maxim_search_inp", placeholder="E.g. 'nemo' or 'remedy'")
        if search.strip():
            s = search.strip().lower()
            maxims = [m for m in maxims if s in m.get("maxim", "").lower() or s in m.get("meaning", "").lower()]

        st.caption(f"Showing {len(maxims)} maxim{'s' if len(maxims) != 1 else ''}")
        for m in maxims:
            mc1, mc2 = st.columns([6, 1])
            with mc1:
                st.markdown(f"""<div class="tool-card">
                    <strong><em>{esc(m.get('maxim', ''))}</em></strong><br>
                    {esc(m.get('meaning', ''))}
                </div>""", unsafe_allow_html=True)
            with mc2:
                if st.button("🗑️", key=f"del_mx_{m['id']}", help="Delete maxim"):
                    delete_user_maxim(m["id"])
                    st.rerun()

        with st.expander("➕ Add Maxim", expanded=False):
            with st.form("add_maxim_form", clear_on_submit=True):
                mx_latin = st.text_input("Latin Maxim *", key="new_mx_latin")
                mx_meaning = st.text_input("Meaning *", key="new_mx_meaning")
                if st.form_submit_button("➕ Add", type="primary"):
                    if mx_latin.strip() and mx_meaning.strip():
                        add_user_maxim(mx_latin.strip(), mx_meaning.strip())
                        st.success("✅ Added!")
                        st.rerun()
                    else:
                        st.error("❌ Both fields are required.")


# ═══════════════════════════════════════════════════════
# RENDER: COMPARE TOOL
# ═══════════════════════════════════════════════════════
def render_compare():
    st.markdown("""<div class="page-header">
        <h2>🔀 Analysis Comparison</h2>
        <p>Compare two AI analyses side by side</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.api_configured:
        st.warning("⚠️ AI not connected.")
        return

    history = get_chat_history(limit=50)
    if len(history) < 2:
        st.info("You need at least 2 AI sessions in history to use the comparison tool. Use the AI Assistant first.")
        return

    st.markdown("Select two analyses from your history to compare:")

    labels = [
        f"{h.get('timestamp', '')} — {h.get('query', '')[:80]}"
        for h in history
    ]

    cmp1, cmp2 = st.columns(2)
    with cmp1:
        st.markdown("##### Analysis A")
        sel_a = st.selectbox("Select first analysis", labels, index=0, key="cmp_sel_a")
    with cmp2:
        st.markdown("##### Analysis B")
        default_b = min(1, len(labels) - 1)
        sel_b = st.selectbox("Select second analysis", labels, index=default_b, key="cmp_sel_b")

    idx_a = labels.index(sel_a)
    idx_b = labels.index(sel_b)

    # Preview both
    prev1, prev2 = st.columns(2)
    with prev1:
        st.markdown("**Query A:**")
        st.caption(history[idx_a].get("query", "")[:300])
        with st.expander("Full Response A", expanded=False):
            st.text(history[idx_a].get("response", "")[:2000])
    with prev2:
        st.markdown("**Query B:**")
        st.caption(history[idx_b].get("query", "")[:300])
        with st.expander("Full Response B", expanded=False):
            st.text(history[idx_b].get("response", "")[:2000])

    if idx_a == idx_b:
        st.warning("⚠️ Please select two different analyses to compare.")
        return

    if st.button("🔀 Compare Analyses", type="primary", use_container_width=True, key="run_compare_btn"):
        with st.spinner("🔀 Comparing…"):
            result = run_compare(
                history[idx_a].get("response", ""),
                history[idx_b].get("response", ""),
            )
        st.markdown("### 📊 Comparison Result")
        st.markdown(f'<div class="response-box">{esc(result)}</div>', unsafe_allow_html=True)

        fname = f"LexiAssist_Comparison_{datetime.now():%Y%m%d_%H%M}"
        ec1, ec2 = st.columns(2)
        with ec1:
            st.download_button("📥 TXT", export_txt(result, "Analysis Comparison"),
                               f"{fname}.txt", "text/plain", key="cmp_dl_txt", use_container_width=True)
        with ec2:
            safe_pdf_download(result, "Analysis Comparison", fname, "cmp_dl_pdf")


# ═══════════════════════════════════════════════════════
# RENDER: USER PROFILE
# ═══════════════════════════════════════════════════════
def render_profile():
    st.markdown("""<div class="page-header">
        <h2>👤 User Profile</h2>
        <p>Firm details, branding, and optional password protection</p>
    </div>""", unsafe_allow_html=True)

    profile = get_user_profile()

    st.markdown("#### 🏢 Firm Details")
    st.caption("These details appear on exported documents (PDF, DOCX, HTML).")

    with st.form("profile_form"):
        pf1, pf2 = st.columns(2)
        with pf1:
            firm_name = st.text_input("Firm Name", value=profile.get("firm_name", "") if profile else "", key="pf_firm")
            user_name = st.text_input("Your Name", value=profile.get("user_name", "") if profile else "", key="pf_name")
        with pf2:
            email = st.text_input("Email", value=profile.get("email", "") if profile else "", key="pf_email")
            st.markdown("")
            has_pw = bool(profile and profile.get("password_hash"))
            st.caption(f"🔒 Password: {'Set ✅' if has_pw else 'Not set'}")

        st.markdown("---")
        st.markdown("#### 🔐 Password Protection (Optional)")
        st.caption("Set a password to require login on each app start. Leave blank to keep current or disable.")

        pw1, pw2 = st.columns(2)
        with pw1:
            new_pw = st.text_input("New Password", type="password", key="pf_pw1", placeholder="Leave blank to skip")
        with pw2:
            confirm_pw = st.text_input("Confirm Password", type="password", key="pf_pw2", placeholder="Re-enter password")

        remove_pw = st.checkbox("🔓 Remove password protection", key="pf_remove_pw")

        if st.form_submit_button("💾 Save Profile", type="primary"):
            password_to_save = ""
            if remove_pw:
                # Clear password — save with empty hash
                if profile:
                    db_update("user_profile", profile["id"], {
                        "firm_name": firm_name.strip(),
                        "user_name": user_name.strip(),
                        "email": email.strip(),
                        "password_hash": "",
                        "updated_at": datetime.now().isoformat(),
                    })
                    st.success("✅ Profile saved. Password removed.")
                    st.rerun()
                else:
                    save_user_profile(firm_name, user_name, email, "")
                    st.success("✅ Profile saved.")
                    st.rerun()
            elif new_pw.strip():
                if new_pw != confirm_pw:
                    st.error("❌ Passwords do not match.")
                elif len(new_pw) < 4:
                    st.error("❌ Password must be at least 4 characters.")
                else:
                    password_to_save = new_pw
                    save_user_profile(firm_name, user_name, email, password_to_save)
                    st.success("✅ Profile saved with password protection!")
                    st.rerun()
            else:
                save_user_profile(firm_name, user_name, email, "")
                st.success("✅ Profile saved!")
                st.rerun()

    # ── Data Statistics ──
    st.markdown("---")
    st.markdown("#### 📊 Database Statistics")

    ds1, ds2, ds3, ds4, ds5 = st.columns(5)
    with ds1:
        st.metric("Cases", db_count("cases"))
    with ds2:
        st.metric("Clients", db_count("clients"))
    with ds3:
        st.metric("Time Entries", db_count("time_entries"))
    with ds4:
        st.metric("AI Sessions", db_count("chat_history"))
    with ds5:
        st.metric("Case Notes", db_count("case_notes"))

    st.markdown("---")
    st.markdown("#### 🗄️ Database Management")
    st.caption(f"Database file: `{DB_PATH}`")

    dm1, dm2 = st.columns(2)
    with dm1:
        if st.button("📥 Full Backup (JSON)", use_container_width=True, key="pf_backup_btn"):
            backup = full_data_export()
            st.download_button(
                "⬇️ Download Backup", backup,
                f"lexiassist_full_backup_{datetime.now():%Y%m%d_%H%M}.json",
                "application/json", key="pf_dl_backup", use_container_width=True,
            )
    with dm2:
        restore_file = st.file_uploader("📤 Restore from Backup", type=["json"], key="pf_restore_upload")
        if restore_file:
            raw = restore_file.getvalue().decode("utf-8", errors="ignore")
            if full_data_import(raw):
                st.success("✅ Data restored from backup!")
                st.rerun()
            else:
                st.error("❌ Invalid backup file.")


# ═══════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════
def main():
    # Initialize database
    ensure_db()

    # Auto-connect API from secrets/env
    auto_connect()

    # Apply theme CSS
    st.markdown(get_theme_css(st.session_state.theme), unsafe_allow_html=True)

    # Auth gate (if password is set)
    if not check_auth():
        render_auth_gate()
        return

    # If no API key, show setup screen
    if not st.session_state.api_configured:
        render_setup_screen()
        return

    # Sidebar
    render_sidebar()

    # ── Main Navigation Tabs ──
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
        "🔀 Compare",
        "👤 Profile",
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
    with tabs[9]:
        render_compare()
    with tabs[10]:
        render_profile()

    # Footer
    st.markdown("---")
    st.caption("⚖️ LexiAssist v8.0 © 2026 · Elite AI Legal Engine for Nigerian Lawyers · Data persisted in local database · ⚠️ AI-generated information — not legal advice — verify all citations independently")


if __name__ == "__main__":
    main()
