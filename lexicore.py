"""
lexicore.py — LexiAssist v7.0 Backend Engine
Smart legal AI with instruction adherence, response-length control, and persistence.
"""
from __future__ import annotations

import html, io, json, logging, os, re, time, uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import google.generativeai as genai
import pandas as pd

try:
    import pdfplumber
    HAS_PDF_READ = True
except ImportError:
    HAS_PDF_READ = False

try:
    from docx import Document as DocxDoc
    from docx.shared import Pt, Inches
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    from fpdf import FPDF
    HAS_PDF_WRITE = True
except ImportError:
    HAS_PDF_WRITE = False

try:
    import openpyxl
    HAS_XLSX = True
except ImportError:
    HAS_XLSX = False

logger = logging.getLogger("LexiAssist")

# ═══════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════
SUPPORTED_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
DEFAULT_MODEL = "gemini-2.5-flash"
MODEL_MIGRATION = {
    "gemini-2.0-flash": "gemini-2.5-flash",
    "gemini-2.0-flash-001": "gemini-2.5-flash",
    "gemini-2.0-flash-lite": "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite-001": "gemini-2.5-flash-lite",
}
CASE_STATUSES = ["Active", "Pending", "Completed", "Archived"]
CLIENT_TYPES = ["Individual", "Corporate", "Government"]
HISTORY_FILE = Path(".lexiassist_history.json")
MAX_UPLOAD_MB = 10

TASK_TYPES = {
    "general":        {"label": "General Query",            "desc": "Any legal question",               "icon": "💬"},
    "analysis":       {"label": "Legal Analysis",           "desc": "Issue spotting & reasoning",        "icon": "🔍"},
    "drafting":       {"label": "Document Drafting",        "desc": "Contracts, pleadings, affidavits",  "icon": "📄"},
    "research":       {"label": "Legal Research",           "desc": "Case law, statutes, authorities",   "icon": "📚"},
    "procedure":      {"label": "Procedural Guidance",      "desc": "Court filing, rules, deadlines",    "icon": "📋"},
    "interpretation": {"label": "Statutory Interpretation", "desc": "Analyze legislation",               "icon": "⚖️"},
    "advisory":       {"label": "Client Advisory",          "desc": "Strategic advice & risk",           "icon": "🎯"},
}

RESPONSE_MODES = {
    "brief":         {"label": "⚡ Brief",         "desc": "Direct answer · 2-5 sentences",           "tokens": 600},
    "standard":      {"label": "📝 Standard",      "desc": "Key issues + guidance · 3-8 paragraphs",  "tokens": 2500},
    "comprehensive": {"label": "🔬 Comprehensive", "desc": "Full multi-pass analysis · CREAC",         "tokens": 10000},
}

# ═══════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════
_CORE = """You are LexiAssist — an expert Nigerian legal AI assistant.
Jurisdiction: Nigeria (Constitution 1999 as amended, Federal/State Acts, Nigerian case law).

STRICT RULES:
1. NEVER fabricate case names, citations, or section numbers. If uncertain, state the principle and mark [Citation to be verified].
2. Answer ONLY what is asked. Do NOT add unrequested sections or go beyond the user's scope.
3. Match your response length EXACTLY to the response mode specified below.
4. Be precise, practical, and professionally rigorous.
5. If you don't know, say so. If it depends, say on what — concretely."""

SYSTEM_PROMPTS = {
    "brief": _CORE + """

RESPONSE MODE: BRIEF — Maximum 2-5 sentences.
- Direct legal answer. No headers, no preamble, no bullet lists.
- If missing facts matter, say "it depends on [X]" in ONE sentence.
- If there is a critical deadline risk, note it in ONE sentence.
- Do NOT elaborate beyond what is asked. Brevity is paramount.""",

    "standard": _CORE + """

RESPONSE MODE: STANDARD — 3-8 focused paragraphs.
- Answer the specific question asked. Do NOT write beyond scope.
- Cover: legal position, key authority/statute, main exception, practical next step.
- Use headers ONLY if there are 3+ genuinely distinct sub-issues.
- Briefly note critical missing facts and how they would change the answer.
- Do NOT write a treatise. Focus on what matters most to the user's question.""",

    "comprehensive": _CORE + """

RESPONSE MODE: COMPREHENSIVE — Full structured analysis.
For each issue identified:
- Apply CREAC: Conclusion → Rule (statute + case law) → Explanation → Application → Conclusion
- For each principle: GENERAL RULE → EXCEPTIONS → MINORITY VIEW
- Distinguish: strict law vs equity vs practical enforceability in Nigeria
- DEVIL'S ADVOCATE: state the strongest counter-argument honestly
- Note missing facts and how each would change the analysis
- STRATEGIC: probability assessment, risk, recommended actions with deadlines
- Mark citation confidence: [HIGH CONFIDENCE] / [MODERATE CONFIDENCE] / [VERIFY]
- Flag deadline risks with 🚨 DEADLINE ALERT
- Identify HIDDEN ISSUES the questioner didn't ask about but a Senior Counsel would spot. Mark: ⚠️ HIDDEN ISSUE""",
}

TASK_MODS = {
    "general": "",
    "analysis": "\nTask focus: Legal analysis. Spot issues including hidden ones. Apply structured reasoning to the question asked.",
    "drafting": "\nTask focus: Draft the requested document to professional Nigerian standard. Use [PLACEHOLDER] for missing information. Note required formalities for validity.",
    "research": "\nTask focus: Legal research memo. Cite relevant statutes and case law. Note conflicting authorities and minority views. Mark uncertain citations.",
    "procedure": "\nTask focus: Procedural guidance. Specify correct court, applicable rules, filing requirements, service, deadlines. Flag limitation risks with 🚨.",
    "interpretation": "\nTask focus: Statutory interpretation. Apply literal, golden, and mischief/purposive rules. Note how Nigerian courts have interpreted the provision.",
    "advisory": "\nTask focus: Client advisory. Present viable options with risk/benefit for each. Recommend a strategy. List immediate action items with deadlines.",
}

ISSUE_SPOT_SYSTEM = _CORE + """

YOUR SOLE TASK: Quick issue identification (under 250 words, structured).
- OBVIOUS ISSUES: List each (ISSUE 1, 2…) with area of law and governing principle.
- HIDDEN ISSUES: Issues a junior would miss (HIDDEN A, B…) — limitation traps, locus standi, procedural prerequisites, regulatory dimensions, equitable claims.
- TOP 3-5 MISSING FACTS that would materially change analysis.
- COMPLEXITY RATING: Straightforward / Moderate / Complex / Highly Complex
Do NOT provide full analysis. Issue decomposition ONLY."""

CRITIQUE_SYSTEM = _CORE + """

YOUR SOLE TASK: Brief quality check of the analysis below (under 150 words).
Score 1-5 each: Issue Completeness, Legal Accuracy, Practical Value.
List 1-3 specific gaps with why they matter.
OVERALL GRADE: A / B / C / D. One sentence overall assessment."""

FOLLOWUP_SYSTEM = _CORE + """

Continuing a legal conversation. You have original query, previous analysis, and follow-up question.
- Do NOT repeat previous analysis — focus ONLY on what the follow-up asks.
- If follow-up reveals new issue, address it fresh.
- If asking to go deeper, drill further with additional authority.
- Match response length to the specified mode."""

# ═══════════════════════════════════════════════════════
# REFERENCE DATA
# ═══════════════════════════════════════════════════════
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
    {"cause": "Election Petition", "period": "21 days after declaration", "authority": "Electoral Act 2022, s. 133(1)"},
    {"cause": "Judicial Review", "period": "3 months", "authority": "FHC Rules, Order 34 r. 3"},
]

COURT_HIERARCHY = [
    {"level": 1, "name": "Supreme Court of Nigeria", "desc": "Final appellate — 7 or 5 Justices", "icon": "🏛️"},
    {"level": 2, "name": "Court of Appeal", "desc": "Intermediate appellate — 16 Divisions", "icon": "⚖️"},
    {"level": 3, "name": "Federal High Court", "desc": "Federal causes: admiralty, revenue, IP, banking", "icon": "🏢"},
    {"level": 3, "name": "State High Courts", "desc": "General civil & criminal per state", "icon": "🏢"},
    {"level": 3, "name": "National Industrial Court", "desc": "Labour & employment disputes", "icon": "🏢"},
    {"level": 3, "name": "Sharia Court of Appeal", "desc": "Islamic personal law appeals", "icon": "🏢"},
    {"level": 3, "name": "Customary Court of Appeal", "desc": "Customary law appeals", "icon": "🏢"},
    {"level": 4, "name": "Magistrate / District Courts", "desc": "Summary jurisdiction", "icon": "📋"},
    {"level": 4, "name": "Area / Customary Courts", "desc": "Customary law first instance", "icon": "📋"},
    {"level": 4, "name": "Sharia Courts", "desc": "Islamic personal law first instance", "icon": "📋"},
    {"level": 5, "name": "Tribunals & Panels", "desc": "Election, Tax Appeal, Code of Conduct", "icon": "📌"},
]

LEGAL_MAXIMS = [
    {"maxim": "Audi alteram partem", "meaning": "Hear the other side — pillar of natural justice"},
    {"maxim": "Nemo judex in causa sua", "meaning": "No one should judge their own cause"},
    {"maxim": "Actus non facit reum nisi mens sit rea", "meaning": "No guilt without guilty mind"},
    {"maxim": "Res judicata", "meaning": "A matter decided — cannot be re-litigated"},
    {"maxim": "Stare decisis", "meaning": "Stand by what has been decided"},
    {"maxim": "Ubi jus ibi remedium", "meaning": "Where there is a right, there is a remedy"},
    {"maxim": "Volenti non fit injuria", "meaning": "No injury to one who consents"},
    {"maxim": "Pacta sunt servanda", "meaning": "Agreements must be honoured"},
    {"maxim": "Nemo dat quod non habet", "meaning": "No one gives what they don't have"},
    {"maxim": "Ignorantia legis neminem excusat", "meaning": "Ignorance of law excuses no one"},
    {"maxim": "Qui facit per alium facit per se", "meaning": "He who acts through another acts himself"},
    {"maxim": "Ex turpi causa non oritur actio", "meaning": "No action from an immoral cause"},
    {"maxim": "Expressio unius est exclusio alterius", "meaning": "Express mention of one excludes others"},
    {"maxim": "Ejusdem generis", "meaning": "General words limited by specific preceding words"},
    {"maxim": "Locus standi", "meaning": "Right or capacity to bring an action"},
    {"maxim": "He who comes to equity must come with clean hands", "meaning": "Equitable relief denied to unconscionable conduct"},
    {"maxim": "Equity regards as done that which ought to be done", "meaning": "Equity treats intended transactions as completed"},
    {"maxim": "Delegatus non potest delegare", "meaning": "A delegate cannot further delegate"},
    {"maxim": "Generalia specialibus non derogant", "meaning": "General provisions don't override specific ones"},
    {"maxim": "Equity follows the law", "meaning": "Equity does not override legal rules except to prevent unconscionability"},
]

# ═══════════════════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════════════════
TEMPLATES = [
    {"id": "1", "name": "Employment Contract", "cat": "Corporate",
     "content": "EMPLOYMENT CONTRACT\n\nThis Employment Contract is made on [DATE] between:\n\n1. [EMPLOYER NAME] (\"the Employer\")\n   Address: [EMPLOYER ADDRESS] | RC: [NUMBER]\n\n2. [EMPLOYEE NAME] (\"the Employee\")\n   Address: [EMPLOYEE ADDRESS]\n\nTERMS:\n\n1. POSITION: [JOB TITLE]\n2. COMMENCEMENT: [START DATE]\n3. PROBATION: [PERIOD] months\n4. SALARY: N[AMOUNT] monthly\n5. HOURS: [HOURS]/week, Mon-Fri\n6. LEAVE: [NUMBER] days annual\n7. TERMINATION: [NOTICE PERIOD] written notice\n8. CONFIDENTIALITY: Employee maintains confidentiality\n9. GOVERNING LAW: Labour Act of Nigeria\n\nSIGNED:\n_______________ _______________\nEmployer        Employee"},
    {"id": "2", "name": "Tenancy Agreement", "cat": "Property",
     "content": "TENANCY AGREEMENT\n\nMade on [DATE] BETWEEN:\n[LANDLORD] of [ADDRESS] (\"Landlord\")\nAND\n[TENANT] of [ADDRESS] (\"Tenant\")\n\n1. PREMISES: [PROPERTY ADDRESS]\n2. TERM: [DURATION] from [START DATE]\n3. RENT: N[AMOUNT] per [PERIOD]\n4. DEPOSIT: N[AMOUNT] refundable\n5. USE: [Residential/Commercial] only\n6. MAINTENANCE: Tenant keeps premises in good condition\n7. ALTERATIONS: None without Landlord's consent\n8. TERMINATION: [NOTICE PERIOD] written notice\n9. LAW: Lagos Tenancy Law (or applicable state law)\n\nSIGNED:\n_______________ _______________\nLandlord        Tenant"},
    {"id": "3", "name": "Power of Attorney", "cat": "Litigation",
     "content": "GENERAL POWER OF ATTORNEY\n\nI, [GRANTOR NAME], of [ADDRESS], appoint [ATTORNEY NAME] of [ADDRESS] as my Attorney to:\n\n1. Demand, sue for, recover and collect all monies due\n2. Sign and execute contracts and documents\n3. Appear before any court or tribunal\n4. Operate bank accounts\n5. Manage properties and collect rents\n6. Execute and register deeds\n\nThis Power remains in force until revoked in writing.\n\nDated: [DATE]\n_______________\n[GRANTOR NAME]\nWITNESS: _______________"},
    {"id": "4", "name": "Written Address", "cat": "Litigation",
     "content": "IN THE [COURT NAME]\nSUIT NO: [NUMBER]\n\n[PLAINTIFF] v. [DEFENDANT]\n\nWRITTEN ADDRESS OF THE [PLAINTIFF/DEFENDANT]\n\n1.0 INTRODUCTION\n2.0 FACTS\n3.0 ISSUES\n4.0 ARGUMENTS\n5.0 CONCLUSION\n\nDated: [DATE]\n_______________\n[COUNSEL]\nFor: [LAW FIRM]"},
    {"id": "5", "name": "Affidavit", "cat": "Litigation",
     "content": "IN THE [COURT NAME]\nSUIT NO: [NUMBER]\n\nAFFIDAVIT IN SUPPORT OF [MOTION]\n\nI, [DEPONENT], make oath:\n1. I am the [Party].\n2. [Fact 1]\n3. [Fact 2]\n4. This Affidavit is made in good faith.\n\n_______________\nDEPONENT\nSworn at [Location] this [DATE]\nBefore: _______________ COMMISSIONER FOR OATHS"},
    {"id": "6", "name": "Legal Opinion", "cat": "Corporate",
     "content": "LEGAL OPINION — PRIVATE & CONFIDENTIAL\n\nTO: [CLIENT] | FROM: [LAW FIRM] | DATE: [DATE]\nRE: [SUBJECT]\n\n1.0 INTRODUCTION\n2.0 FACTS\n3.0 ISSUES\n4.0 LEGAL FRAMEWORK\n5.0 ANALYSIS\n6.0 CONCLUSION\n7.0 CAVEATS\n\n_______________\n[PARTNER]\nFor: [LAW FIRM]"},
    {"id": "7", "name": "Demand Letter", "cat": "Litigation",
     "content": "[LETTERHEAD]\n[DATE]\n\n[RECIPIENT]\n\nRE: DEMAND FOR N[AMOUNT]\nOUR CLIENT: [CLIENT NAME]\n\nWe are Solicitors to [CLIENT].\n\nFacts: [Background]\n\nPay within 7 DAYS or we institute proceedings.\n\nGovern yourself accordingly.\n\n_______________\n[COUNSEL]\nFor: [LAW FIRM]"},
    {"id": "8", "name": "Board Resolution", "cat": "Corporate",
     "content": "BOARD RESOLUTION — [COMPANY] (RC: [NUMBER])\n[VENUE] — [DATE]\n\nPRESENT: [Directors]\nIN ATTENDANCE: [Company Secretary]\n\nRESOLVED:\n1. [Resolution]\n2. Any Director authorized to execute documents.\n3. Company Secretary to file returns with CAC.\n\nCERTIFIED TRUE COPY\n_______________\nCompany Secretary"},
]
# ═══════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════
def gen_id() -> str:
    return uuid.uuid4().hex[:12]


def esc(text: str) -> str:
    if not text:
        return ""
    return html.escape(str(text))


def normalize_model(name: str) -> str:
    return MODEL_MIGRATION.get(name, name if name in SUPPORTED_MODELS else DEFAULT_MODEL)


def fmt_currency(amount: float) -> str:
    try:
        return f"₦{float(amount):,.2f}"
    except (ValueError, TypeError):
        return "₦0.00"


def fmt_date(dt_str: str) -> str:
    if not dt_str:
        return "—"
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(dt_str[:19], fmt[:len(dt_str[:19])]).strftime("%d %b %Y")
        except ValueError:
            continue
    return str(dt_str)[:10]


def days_until(dt_str: str) -> int:
    if not dt_str:
        return 999
    try:
        target = datetime.strptime(dt_str[:10], "%Y-%m-%d").date()
        return (target - datetime.now().date()).days
    except (ValueError, TypeError):
        return 999


def relative_date(dt_str: str) -> str:
    d = days_until(dt_str)
    if d < 0:
        return f"{abs(d)}d overdue"
    if d == 0:
        return "Today"
    if d == 1:
        return "Tomorrow"
    if d <= 7:
        return f"{d} days"
    if d <= 30:
        return f"{d // 7}w {d % 7}d"
    return f"{d // 30}mo"


# ═══════════════════════════════════════════════════════
# API
# ═══════════════════════════════════════════════════════
def get_api_key(secrets_fn=None, session_key: str = "") -> str:
    if secrets_fn:
        try:
            k = secrets_fn()
            if k:
                return k
        except Exception:
            pass
    env_key = os.environ.get("GEMINI_API_KEY", "")
    if env_key:
        return env_key
    return session_key or ""


def configure_api(key: str):
    if key and len(key) >= 10:
        genai.configure(api_key=key)


def test_connection(key: str, model_name: str = DEFAULT_MODEL) -> tuple[bool, str]:
    try:
        genai.configure(api_key=key)
        m = genai.GenerativeModel(model_name)
        r = m.generate_content("Reply: OK", generation_config={"max_output_tokens": 10})
        return True, "Connected"
    except Exception as e:
        return False, str(e)[:200]


def generate(prompt: str, system: str, model_name: str, config: dict | None = None) -> str:
    try:
        cfg = config or {"temperature": 0.3, "top_p": 0.9, "top_k": 40, "max_output_tokens": 2500}
        m = genai.GenerativeModel(model_name, system_instruction=system)
        r = m.generate_content(prompt, generation_config=cfg)
        if r and r.text:
            return r.text.strip()
        return "⚠️ No response generated. Try rephrasing."
    except Exception as e:
        return f"Error: {str(e)[:300]}"


# ═══════════════════════════════════════════════════════
# PIPELINE
# ═══════════════════════════════════════════════════════
def run_pipeline(
    query: str, task: str, mode: str, model: str,
    doc_context: str = "", conversation_context: str = "",
) -> dict:
    results = {"issue_spot": "", "main": "", "critique": "", "grade": ""}
    mode_cfg = RESPONSE_MODES.get(mode, RESPONSE_MODES["standard"])
    system = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["standard"])
    system += TASK_MODS.get(task, "")
    gen_config = {
        "temperature": 0.3 if mode != "comprehensive" else 0.35,
        "top_p": 0.9,
        "top_k": 40,
        "max_output_tokens": mode_cfg["tokens"],
    }

    prompt_parts = []
    if doc_context:
        prompt_parts.append(f"UPLOADED DOCUMENT CONTEXT:\n{doc_context}\n\n---\n")
    if conversation_context and mode != "brief":
        prompt_parts.append(f"PREVIOUS CONVERSATION:\n{conversation_context}\n\n---\n")
    prompt_parts.append(f"LEGAL QUERY:\n{query}")
    full_prompt = "\n".join(prompt_parts)

    if mode == "comprehensive":
        spot = generate(
            f"LEGAL SCENARIO:\n\n{query}",
            ISSUE_SPOT_SYSTEM, model,
            {"temperature": 0.15, "top_p": 0.85, "top_k": 25, "max_output_tokens": 800},
        )
        results["issue_spot"] = spot
        if not spot.startswith(("Error", "⚠️")):
            full_prompt += f"\n\n---\nISSUE ANALYSIS (for reference):\n{spot}"

    main_response = generate(full_prompt, system, model, gen_config)
    results["main"] = main_response

    if mode == "comprehensive" and not main_response.startswith(("Error", "⚠️")):
        critique_prompt = f"QUERY:\n{query}\n\nANALYSIS TO CRITIQUE:\n{main_response[:4000]}"
        critique = generate(
            critique_prompt, CRITIQUE_SYSTEM, model,
            {"temperature": 0.2, "top_p": 0.85, "top_k": 25, "max_output_tokens": 500},
        )
        results["critique"] = critique
        grade_match = re.search(r"OVERALL\s*GRADE\s*:\s*([ABCD])", critique, re.IGNORECASE)
        results["grade"] = grade_match.group(1).upper() if grade_match else ""

    return results


def run_research(query: str, mode: str, model: str) -> str:
    system = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["standard"])
    system += TASK_MODS.get("research", "")
    cfg = RESPONSE_MODES.get(mode, RESPONSE_MODES["standard"])
    return generate(
        f"RESEARCH QUERY:\n{query}", system, model,
        {"temperature": 0.25, "top_p": 0.9, "top_k": 40, "max_output_tokens": cfg["tokens"]},
    )


def run_followup(
    original_query: str, previous_response: str,
    followup: str, mode: str, task: str, model: str,
) -> str:
    system = FOLLOWUP_SYSTEM + TASK_MODS.get(task, "")
    mode_label = RESPONSE_MODES.get(mode, RESPONSE_MODES["standard"])["label"]
    cfg = RESPONSE_MODES.get(mode, RESPONSE_MODES["standard"])
    prompt = (
        f"RESPONSE MODE: {mode_label}\n\n"
        f"ORIGINAL QUERY:\n{original_query[:1000]}\n\n"
        f"PREVIOUS ANALYSIS:\n{previous_response[:3000]}\n\n"
        f"FOLLOW-UP QUESTION:\n{followup}"
    )
    return generate(
        prompt, system, model,
        {"temperature": 0.3, "top_p": 0.9, "top_k": 40, "max_output_tokens": cfg["tokens"]},
    )


# ═══════════════════════════════════════════════════════
# FILE EXTRACTION
# ═══════════════════════════════════════════════════════
def extract_file_text(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    data = uploaded_file.getvalue()

    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"File exceeds {MAX_UPLOAD_MB}MB limit.")

    if name.endswith(".txt"):
        return data.decode("utf-8", errors="replace")
    elif name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(data))
        return df.to_string(index=False)
    elif name.endswith(".xlsx"):
        if not HAS_XLSX:
            raise ValueError("openpyxl not installed.")
        df = pd.read_excel(io.BytesIO(data), engine="openpyxl")
        return df.to_string(index=False)
    elif name.endswith(".pdf"):
        if not HAS_PDF_READ:
            raise ValueError("pdfplumber not installed.")
        pages = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for p in pdf.pages[:50]:
                t = p.extract_text()
                if t:
                    pages.append(t)
        return "\n\n".join(pages) if pages else "⚠️ Could not extract text."
    elif name.endswith(".docx"):
        if not HAS_DOCX:
            raise ValueError("python-docx not installed.")
        doc = DocxDoc(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    else:
        raise ValueError(f"Unsupported file type: {name.split('.')[-1]}")


# ═══════════════════════════════════════════════════════
# EXPORT — ALL FIXES APPLIED
# ═══════════════════════════════════════════════════════
def export_txt(text: str, title: str = "LexiAssist Analysis") -> str:
    header = f"{'=' * 60}\n{title}\nGenerated: {datetime.now():%Y-%m-%d %H:%M}\n{'=' * 60}\n\n"
    footer = (
        f"\n\n{'=' * 60}\n"
        "Disclaimer: AI-generated legal information. Not legal advice.\n"
        "Verify all citations independently.\n"
        f"{'=' * 60}"
    )
    return header + text + footer


def export_html(text: str, title: str = "LexiAssist Analysis") -> str:
    escaped = esc(text)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{esc(title)}</title>
<style>
body{{font-family:Georgia,serif;max-width:800px;margin:2rem auto;padding:0 1rem;color:#1e293b;line-height:1.8}}
h1{{color:#059669;border-bottom:3px solid #059669;padding-bottom:.5rem}}
.content{{white-space:pre-wrap;font-size:1rem}}
.disclaimer{{background:#fef3c7;border-left:4px solid #f59e0b;padding:1rem;margin-top:2rem;font-size:.85rem}}
.footer{{text-align:center;color:#94a3b8;margin-top:2rem;font-size:.8rem}}
</style></head><body>
<h1>⚖️ {esc(title)}</h1>
<p style="color:#64748b">Generated: {datetime.now():%Y-%m-%d %H:%M}</p>
<div class="content">{escaped}</div>
<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated legal information. Not legal advice. Verify all citations.</div>
<div class="footer">LexiAssist v7.0 · Smart Legal AI</div>
</body></html>"""


def export_pdf(text: str, title: str = "LexiAssist Analysis") -> bytes:
    """Export text to PDF. Returns bytes or empty bytes if fpdf2 not installed."""
    if not HAS_PDF_WRITE:
        return b""
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 12, title, ln=True, align="C")
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(0, 6, f"Generated: {datetime.now():%Y-%m-%d %H:%M}", ln=True, align="C")
        pdf.ln(8)
        pdf.set_font("Helvetica", "", 10)
        clean = text.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 5, clean)
        pdf.ln(10)
        pdf.set_font("Helvetica", "I", 8)
        pdf.multi_cell(0, 4, "Disclaimer: AI-generated legal information. Not legal advice. Verify all citations.")
        # FIX: wrap in bytes() so Streamlit accepts it
        return bytes(pdf.output())
    except Exception:
        return b""


def export_docx(text: str, title: str = "LexiAssist Analysis") -> bytes:
    """Export text to DOCX. Returns bytes or empty bytes if python-docx not installed."""
    if not HAS_DOCX:
        return b""
    try:
        doc = DocxDoc()
        doc.add_heading(title, level=1)
        doc.add_paragraph(f"Generated: {datetime.now():%Y-%m-%d %H:%M}").italic = True
        doc.add_paragraph("")
        for para in text.split("\n"):
            p = doc.add_paragraph(para)
            for run in p.runs:
                run.font.size = Pt(11)
        doc.add_paragraph("")
        disclaimer = doc.add_paragraph(
            "Disclaimer: AI-generated legal information. Not legal advice. Verify all citations."
        )
        disclaimer.italic = True
        buf = io.BytesIO()
        doc.save(buf)
        # FIX: wrap in bytes() so Streamlit accepts it
        return bytes(buf.getvalue())
    except Exception:
        return b""


def export_all_data(cases, clients, time_entries, invoices) -> str:
    return json.dumps(
        {
            "export_date": datetime.now().isoformat(),
            "version": "7.0",
            "cases": cases,
            "clients": clients,
            "time_entries": time_entries,
            "invoices": invoices,
        },
        indent=2, default=str,
    )


# ═══════════════════════════════════════════════════════
# HISTORY (PERSISTENT)
# ═══════════════════════════════════════════════════════
def load_history() -> list:
    try:
        if HISTORY_FILE.exists():
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data[-100:]
    except Exception:
        pass
    return []


def save_history(history: list):
    try:
        trimmed = history[-100:]
        HISTORY_FILE.write_text(json.dumps(trimmed, indent=2, default=str), encoding="utf-8")
    except Exception:
        pass


def clear_history():
    try:
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
    except Exception:
        pass


# ═══════════════════════════════════════════════════════
# CASE MANAGEMENT
# ═══════════════════════════════════════════════════════
def add_case(cases: list, data: dict) -> dict:
    case = {
        "id": gen_id(),
        "created": datetime.now().isoformat(),
        **data,
    }
    cases.append(case)
    return case


def update_case(cases: list, case_id: str, updates: dict):
    for c in cases:
        if c["id"] == case_id:
            c.update(updates)
            return c
    return None


def delete_case(cases: list, case_id: str) -> list:
    return [c for c in cases if c["id"] != case_id]


def get_hearings(cases: list) -> list:
    hearings = []
    for c in cases:
        if c.get("status") == "Active" and c.get("next_hearing"):
            hearings.append({
                "title": c.get("title", "Untitled"),
                "suit": c.get("suit_no", ""),
                "court": c.get("court", ""),
                "date": c["next_hearing"],
            })
    hearings.sort(key=lambda h: h["date"])
    return hearings


# ═══════════════════════════════════════════════════════
# CLIENT MANAGEMENT
# ═══════════════════════════════════════════════════════
def add_client(clients: list, data: dict) -> dict:
    client = {
        "id": gen_id(),
        "created": datetime.now().isoformat(),
        **data,
    }
    clients.append(client)
    return client


def delete_client(clients: list, client_id: str) -> list:
    return [c for c in clients if c["id"] != client_id]


def client_name(clients: list, client_id: str) -> str:
    for c in clients:
        if c["id"] == client_id:
            return c.get("name", "Unknown")
    return "—"


def client_case_count(cases: list, client_id: str) -> int:
    return sum(1 for c in cases if c.get("client_id") == client_id)


def client_billable(time_entries: list, client_id: str) -> float:
    return sum(e.get("amount", 0) for e in time_entries if e.get("client_id") == client_id)


# ═══════════════════════════════════════════════════════
# BILLING
# ═══════════════════════════════════════════════════════
def add_time_entry(entries: list, data: dict) -> dict:
    entry = {
        "id": gen_id(),
        "created": datetime.now().isoformat(),
        "amount": float(data.get("hours", 0)) * float(data.get("rate", 0)),
        **data,
    }
    entries.append(entry)
    return entry


def total_billable(entries: list) -> float:
    return sum(e.get("amount", 0) for e in entries)


def total_hours(entries: list) -> float:
    return sum(e.get("hours", 0) for e in entries)


def make_invoice(invoices: list, time_entries: list, clients: list, client_id: str) -> dict | None:
    entries = [e for e in time_entries if e.get("client_id") == client_id]
    if not entries:
        return None
    name = client_name(clients, client_id)
    inv = {
        "id": gen_id(),
        "invoice_no": f"INV-{datetime.now():%Y%m%d}-{gen_id()[:4].upper()}",
        "date": datetime.now().isoformat(),
        "client_id": client_id,
        "client_name": name,
        "entries": entries,
        "total": sum(e.get("amount", 0) for e in entries),
    }
    invoices.append(inv)
    return inv
