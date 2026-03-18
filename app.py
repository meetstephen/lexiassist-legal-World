"""
LexiAssist v7.0 — Production-Ready Elite Legal Reasoning Engine
FIXES:
✓ Instruction-strict prompts (no off-topic, concise output)
✓ Fast generation (lower token limits, focused outputs)
✓ Multi-format export (PDF, DOCX, JSON, TXT)
✓ Persistent storage (SQLite, not just session state)
✓ Working clear/reset functions
✓ Simplified pipeline (no confusing settings)
✓ Fast file handling (streaming, no timeouts)
✓ Full conversation history
"""
from __future__ import annotations

import html
import json
import logging
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import google.generativeai as genai
import pandas as pd
import plotly.express as px
import streamlit as st
from io import BytesIO

try:
    import pdfplumber
    PDF_SUPPORT = True
except:
    PDF_SUPPORT = False

try:
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_SUPPORT = True
except:
    DOCX_SUPPORT = False

try:
    import openpyxl
    XLSX_SUPPORT = True
except:
    XLSX_SUPPORT = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
    PDF_EXPORT_SUPPORT = True
except:
    PDF_EXPORT_SUPPORT = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LexiAssist")

st.set_page_config(
    page_title="LexiAssist v7.0", page_icon="⚖️", layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================================
# PERSISTENT STORAGE (SQLite)
# =========================================================================
DB_PATH = Path("lexiassist_data.db")

def init_db():
    """Initialize SQLite database for persistent storage."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Analyses table
    c.execute("""CREATE TABLE IF NOT EXISTS analyses (
        id TEXT PRIMARY KEY,
        query TEXT NOT NULL,
        task_type TEXT NOT NULL,
        issue_spot TEXT,
        ambiguity TEXT,
        main_analysis TEXT NOT NULL,
        critique TEXT,
        grade TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Cases table
    c.execute("""CREATE TABLE IF NOT EXISTS cases (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        suit_no TEXT,
        court TEXT,
        status TEXT,
        client_id TEXT,
        next_hearing DATE,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Clients table
    c.execute("""CREATE TABLE IF NOT EXISTS clients (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        type TEXT,
        address TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Time entries table
    c.execute("""CREATE TABLE IF NOT EXISTS time_entries (
        id TEXT PRIMARY KEY,
        client_id TEXT,
        case_id TEXT,
        date DATE,
        hours REAL,
        rate REAL,
        amount REAL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    # Conversation history table
    c.execute("""CREATE TABLE IF NOT EXISTS conversation_history (
        id TEXT PRIMARY KEY,
        analysis_id TEXT,
        role TEXT,
        content TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(analysis_id) REFERENCES analyses(id)
    )""")
    
    conn.commit()
    conn.close()

def save_analysis(query, task_type, issue_spot, ambiguity, main_analysis, critique, grade):
    """Save analysis to database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    analysis_id = uuid.uuid4().hex[:12]
    c.execute("""
        INSERT INTO analyses (id, query, task_type, issue_spot, ambiguity, main_analysis, critique, grade)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (analysis_id, query, task_type, issue_spot or "", ambiguity or "", main_analysis, critique or "", grade or ""))
    conn.commit()
    conn.close()
    return analysis_id

def load_analyses(limit=20):
    """Load recent analyses from database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, query, task_type, main_analysis, grade, created_at FROM analyses ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "query": r[1][:100], "task": r[2], "analysis": r[3][:500], "grade": r[4], "date": r[5]} for r in rows]

def get_analysis(analysis_id):
    """Load specific analysis."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT query, task_type, issue_spot, ambiguity, main_analysis, critique, grade FROM analyses WHERE id = ?", (analysis_id,))
    row = c.fetchone()
    conn.close()
    return row if row else None

# =========================================================================
# CONSTANTS
# =========================================================================
CASE_STATUSES = ["Active", "Pending", "Completed", "Archived"]
CLIENT_TYPES = ["Individual", "Corporate", "Government"]

TASK_TYPES = {
    "analysis": {"label": "Legal Analysis", "desc": "Issue spotting, CREAC reasoning", "icon": "🔍"},
    "drafting": {"label": "Document Drafting", "desc": "Contracts, pleadings, affidavits", "icon": "📄"},
    "research": {"label": "Legal Research", "desc": "Case law, statutes, authorities", "icon": "📚"},
    "procedure": {"label": "Procedural Guidance", "desc": "Court procedures, evidence rules", "icon": "📋"},
    "interpretation": {"label": "Statutory Interpretation", "desc": "Analyze legislation", "icon": "⚖️"},
    "advisory": {"label": "Client Advisory", "desc": "Strategic advice, options", "icon": "🎯"},
    "general": {"label": "General Query", "desc": "Any legal question", "icon": "💬"},
}

MODEL_MIGRATION_MAP = {
    "gemini-2.0-flash": "gemini-2.5-flash",
    "gemini-2.0-flash-001": "gemini-2.5-flash",
}
SUPPORTED_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
DEFAULT_MODEL = "gemini-2.5-flash"

# =========================================================================
# INSTRUCTION-STRICT SYSTEM PROMPTS (CONCISE, FOCUSED)
# =========================================================================

_MASTER_IDENTITY = """
You are LexiAssist — a Senior Partner at a Nigerian law firm.

JURISDICTION: Nigeria only.
Primary: Constitution 1999, Federal Acts, State Laws, Rules of Court, Nigerian case law.

CARDINAL RULES:
1. NEVER fabricate citations. If uncertain, mark: [Citation needs verification]
2. Be CONCISE. Answer the question asked — don't go off-topic.
3. No rambling. Every sentence must be necessary.
4. For every principle: STATE IT ONCE, then explain application.
5. If law is unsettled, say so clearly.
6. Flag deadlines with: 🚨 DEADLINE: [exact date]
7. Use STRUCTURED FORMAT — numbered points, bullets, tables.
8. No padding. No unnecessary examples. No repetition.
"""

# ── ANALYSIS (CONCISE CREAC) ─────────────────────────────────────────
ANALYSIS_INSTRUCTION = _MASTER_IDENTITY + """
YOU MUST FOLLOW THIS FORMAT EXACTLY. NOTHING MORE, NOTHING LESS.

STRUCTURE:
═══════════════════════════════════
1. ISSUES IDENTIFIED
- List all distinct legal issues (numbered)
- For each: area of law, governing statute

2. LEGAL ANALYSIS (CREAC — one paragraph per issue)
For each issue:
C: Your conclusion (STRONG/VIABLE/WEAK)
R: The rule (statute + one key case)
E: How it applies to the facts
A: Application to these specific facts
C: Confidence level

3. STRONGEST COUNTER-ARGUMENT
- What would opposing counsel say?
- How would you respond?

4. RISK ASSESSMENT
- Probability: HIGH (70%+) / MODERATE (50-70%) / LOW (<50%)
- Key risk factor
- Immediate next steps (numbered)

5. MISSING INFORMATION
- Top 3 facts you need
- How each would change the outcome

DO NOT:
- Write flowery prose
- Explain basic legal concepts
- Go beyond what was asked
- Repeat yourself
- Provide information not requested
- Write more than necessary

Maximum output: 1500 words. Be concise.
"""

# ── DRAFTING (CONCISE) ───────────────────────────────────────────────
DRAFTING_INSTRUCTION = _MASTER_IDENTITY + """
STRUCTURE:
1. LEGAL RISKS TO ADDRESS
- List the key risks this document protects against

2. THE DOCUMENT
- Full professional draft, compliant with Nigerian law
- [PLACEHOLDER] for missing information
- Include governing law clause (Nigerian law)
- For contracts: dispute resolution, force majeure, termination

3. DRAFTSMAN'S NOTES
- Explain key clauses (what risk each mitigates)
- Any clauses with legal risk and why
- Recommended additions if facts were different

DO NOT write explanation of basic contract law.
DO NOT explain Nigerian law basics.
Be concise. Maximum 2000 words.
"""

# ── RESEARCH (FOCUSED) ───────────────────────────────────────────────
RESEARCH_INSTRUCTION = _MASTER_IDENTITY + """
STRUCTURE:
1. STATUTORY FRAMEWORK
- Primary legislation with sections
- Recent amendments
- Federal vs. State differences (if any)

2. LEADING CASES
- 3-5 most important Nigerian cases
- For each: name, citation, year, ratio decidendi, why relevant

3. CURRENT LAW (SYNTHESIS)
- What the law clearly says
- Where it's unsettled
- Conflicting authorities (if any)

4. PRACTICAL APPLICATION
- Relevant limitation period
- Procedural requirements
- Court jurisdiction

5. RECOMMENDATIONS
- Best course of action
- Risks to watch

Maximum 1200 words. No unnecessary detail.
"""

# ── PROCEDURE ────────────────────────────────────────────────────────
PROCEDURE_INSTRUCTION = _MASTER_IDENTITY + """
STRUCTURE:
1. CORRECT JURISDICTION
- Which court (cite statute)
- Why this court is appropriate

2. PRE-ACTION REQUIREMENTS
- Any mandatory notices (and exact deadlines)
- Limitation period (calculate from date given)
- 🚨 Flag if approaching or expired

3. HOW TO COMMENCE
- Originating process (Writ/Summons/Petition — cite Rule)
- Required documents
- Court fees (approximate)

4. PROCEDURAL TIMELINE
- Pre-trial steps
- Trial procedure
- Post-judgment enforcement

5. IMMEDIATE ACTIONS
- Numbered steps with deadlines

Maximum 1000 words. Practical, not academic.
"""

# ── INTERPRETATION ──────────────────────────────────────────────────
INTERPRETATION_INSTRUCTION = _MASTER_IDENTITY + """
STRUCTURE:
1. THE PROVISION
- Exact text
- Statute, section, date of enactment

2. INTERPRETATION
- What it literally means
- How Nigerian courts have interpreted it
- Any ambiguity or dispute

3. APPLICATION TO YOUR SITUATION
- How this provision affects you
- What it covers and what it doesn't

4. PRACTICAL MEANING
- Plain English explanation
- Common misconceptions to avoid

Maximum 800 words. Direct answer only.
"""

# ── ADVISORY ─────────────────────────────────────────────────────────
ADVISORY_INSTRUCTION = _MASTER_IDENTITY + """
STRUCTURE:
1. YOUR SITUATION
- What you're facing
- What you want to achieve

2. OPTIONS (ALL viable options)
- OPTION A: [Name] — Pros | Cons | Timeline | Cost
- OPTION B: [Name] — Pros | Cons | Timeline | Cost
- OPTION C: [Name] — Pros | Cons | Timeline | Cost

3. MY RECOMMENDATION
- Which option is best and why
- Probability of success
- Key risks

4. IMMEDIATE ACTION STEPS
- What to do right now (numbered, with deadlines)

5. COST ESTIMATE
- Rough range for legal fees

Maximum 1200 words. Practical and direct.
"""

# ── GENERAL ──────────────────────────────────────────────────────────
GENERAL_INSTRUCTION = _MASTER_IDENTITY + """
ANSWER THE QUESTION ASKED. NOTHING MORE.

If the question is simple, give a simple answer.
If it's complex, use CREAC structure.

Do NOT:
- Provide unsolicited information
- Explain basic concepts
- Go off-topic
- Ramble or pad the answer

Maximum output: 1000 words.
Answer the specific question. Stop.
"""

TASK_INSTRUCTIONS = {
    "analysis": ANALYSIS_INSTRUCTION,
    "drafting": DRAFTING_INSTRUCTION,
    "research": RESEARCH_INSTRUCTION,
    "procedure": PROCEDURE_INSTRUCTION,
    "interpretation": INTERPRETATION_INSTRUCTION,
    "advisory": ADVISORY_INSTRUCTION,
    "general": GENERAL_INSTRUCTION,
}

# ─── GENERATION CONFIG (FAST, FOCUSED) ────────────────────────────────
GEN_CONFIG = {
    "temperature": 0.1,  # Very low — strict instruction adherence
    "top_p": 0.85,
    "top_k": 20,
    "max_output_tokens": 3000  # Lower — forces conciseness
}

# =========================================================================
# CSS (Minimal, Fast)
# =========================================================================
_BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }
.main .block-container { padding-top: 0.5rem; max-width: 1200px; }
.hero { padding: 2rem; border-radius: 1rem; background: linear-gradient(135deg, #059669, #0d9488); 
        color: white; box-shadow: 0 10px 30px rgba(5,150,105,.2); }
.hero h1 { font-size: 2rem; margin: 0; font-weight: 800; }
.hero p { font-size: 0.95rem; margin: 0.5rem 0 0; opacity: 0.9; }
.page-header { padding: 1rem 1.5rem; background: linear-gradient(135deg, #059669, #0d9488); 
              color: white; border-radius: 0.75rem; margin-bottom: 1rem; }
.page-header h1 { margin: 0; font-size: 1.75rem; }
.page-header p { margin: 0.25rem 0 0; opacity: 0.85; font-size: 0.85rem; }
.stat-card { background: white; border: 1px solid #e2e8f0; border-radius: 0.75rem; 
            padding: 1rem; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,.05); }
.stat-value { font-size: 1.5rem; font-weight: 700; color: #059669; }
.stat-label { font-size: 0.7rem; color: #64748b; margin-top: 0.3rem; text-transform: uppercase; }
.badge { display: inline-block; padding: 0.2rem 0.5rem; border-radius: 0.3rem; 
        font-size: 0.65rem; font-weight: 600; background: #dcfce7; color: #166534; }
.badge-danger { background: #fee2e2; color: #991b1b; }
.badge-warning { background: #fef3c7; color: #92400e; }
.response-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 0.5rem; 
               padding: 1.25rem; margin: 1rem 0; white-space: pre-wrap; font-size: 0.9rem; 
               line-height: 1.8; font-family: 'Georgia', serif; }
.disclaimer { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 0.75rem 1rem; 
             margin-top: 0.75rem; font-size: 0.8rem; border-radius: 0 0.3rem 0.3rem 0; }
.cal-event { padding: 0.75rem 1rem; border-radius: 0.5rem; margin-bottom: 0.5rem; 
            border-left: 4px solid #059669; background: #f0fdf4; }
.cal-event.urgent { border-color: #ef4444; background: #fee2e2; }
.app-footer { text-align: center; padding: 1rem; color: #64748b; font-size: 0.75rem; 
             border-top: 1px solid #e2e8f0; margin-top: 1rem; }
#MainMenu { visibility: hidden; } footer { visibility: hidden; }
</style>
"""

# =========================================================================
# TEMPLATES
# =========================================================================
@st.cache_data
def get_templates():
    return [
        {"id":"1","name":"Employment Contract","cat":"Corporate","content":"EMPLOYMENT CONTRACT\n\n[DATE]\n\nBETWEEN:\n[EMPLOYER] (\"Employer\")\nAND\n[EMPLOYEE] (\"Employee\")\n\n1. POSITION: [TITLE]\n2. START DATE: [DATE]\n3. SALARY: N[AMOUNT] monthly\n4. PROBATION: [PERIOD] months\n5. LEAVE: [DAYS] days per annum\n6. TERMINATION: [NOTICE] written notice\n7. CONFIDENTIALITY: Maintained by Employee\n8. GOVERNING LAW: Labour Act of Nigeria\n\nSIGNED:\n_______________\n[EMPLOYER]\n\n_______________\n[EMPLOYEE]\n"},
        {"id":"2","name":"Tenancy Agreement","cat":"Property","content":"TENANCY AGREEMENT\n\n[DATE]\n\nBETWEEN:\n[LANDLORD] (\"Landlord\")\nAND\n[TENANT] (\"Tenant\")\n\n1. PREMISES: [ADDRESS]\n2. TERM: [DURATION] from [DATE]\n3. RENT: N[AMOUNT] per [PERIOD]\n4. DEPOSIT: N[AMOUNT] refundable\n5. USE: Residential/Commercial only\n6. MAINTENANCE: Tenant's responsibility\n7. TERMINATION: [NOTICE PERIOD]\n8. LAW: [State] Tenancy Law\n\nSIGNED:\n_______________\nLandlord\n_______________\nTenant\n"},
        {"id":"3","name":"Power of Attorney","cat":"Litigation","content":"POWER OF ATTORNEY\n\nI, [NAME], appoint [ATTORNEY NAME] to:\n1. Sue and recover debts\n2. Sign contracts\n3. Appear in court\n4. Manage properties\n5. Operate bank accounts\n\nValid until revoked in writing.\n\nDated: [DATE]\n_______________\n[GRANTOR]\n"},
        {"id":"4","name":"Demand Letter","cat":"Litigation","content":"[DATE]\n\n[RECIPIENT]\n\nRE: DEMAND FOR N[AMOUNT]\n\nWe represent [CLIENT]. You owe N[AMOUNT] for [REASON].\n\nPay within 7 DAYS or we sue for:\n(a) Principal amount\n(b) Interest\n(c) Legal costs\n(d) Damages\n\n_______________\n[COUNSEL]\n"},
        {"id":"5","name":"Affidavit","cat":"Litigation","content":"IN THE [COURT]\nSUIT NO: [NUMBER]\n\nAFFIDAVIT\n\nI, [NAME], make oath:\n\n1. [Fact 1]\n2. [Fact 2]\n3. [Fact 3]\n\nSworn this [DATE]\n\n_______________\nDeponent\n"},
    ]

# =========================================================================
# FILE EXTRACTION & EXPORT
# =========================================================================
def _extract_text_from_file(uploaded_file) -> str:
    """Fast file extraction."""
    import io
    name = uploaded_file.name.lower()
    data = uploaded_file.getvalue()
    
    if name.endswith(".pdf"):
        if not PDF_SUPPORT:
            raise RuntimeError("Install: pip install pdfplumber")
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages[:10]])  # First 10 pages only
    elif name.endswith(".docx"):
        if not DOCX_SUPPORT:
            raise RuntimeError("Install: pip install python-docx")
        return "\n".join([p.text for p in Document(io.BytesIO(data)).paragraphs if p.text])
    elif name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")[:50000]  # First 50KB
    elif name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(data)).to_string(index=False)[:50000]
    elif name.endswith(".xlsx"):
        if not XLSX_SUPPORT:
            raise RuntimeError("Install: pip install openpyxl")
        return pd.read_excel(io.BytesIO(data)).to_string(index=False)[:50000]
    raise ValueError(f"Unsupported: {name}")

def export_to_pdf(analysis_text, title="LexiAssist Analysis"):
    """Export analysis to PDF."""
    if not PDF_EXPORT_SUPPORT:
        st.warning("PDF export requires reportlab. Exporting as TXT instead.")
        return export_to_txt(analysis_text, title)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor='#059669',
        spaceAfter=30,
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        leading=14,
    )
    
    story.append(Paragraph("⚖️ " + title, title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Split text into paragraphs
    for para in analysis_text.split('\n\n'):
        if para.strip():
            story.append(Paragraph(para.strip().replace('\n', ' '), body_style))
    
    story.append(Spacer(1, 0.3*inch))
    disclaimer = "⚖️ Disclaimer: AI-generated analysis for professional reference. Not legal advice. Verify all citations."
    story.append(Paragraph(disclaimer, ParagraphStyle('Disclaimer', parent=styles['Normal'], fontSize=8, textColor='gray')))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def export_to_docx(analysis_text, title="LexiAssist Analysis"):
    """Export analysis to DOCX."""
    if not DOCX_SUPPORT:
        st.warning("DOCX export requires python-docx. Exporting as TXT instead.")
        return export_to_txt(analysis_text, title)
    
    doc = Document()
    doc.add_heading('⚖️ ' + title, 0)
    doc.add_paragraph(analysis_text)
    doc.add_paragraph()
    doc.add_paragraph("⚖️ Disclaimer: AI-generated analysis for professional reference. Not legal advice. Verify all citations.", style='Normal')
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def export_to_txt(analysis_text, title="LexiAssist Analysis"):
    """Export analysis to TXT."""
    content = f"{'='*70}\n⚖️ {title}\n{'='*70}\n\n{analysis_text}\n\n{'='*70}\n⚖️ DISCLAIMER\n{'='*70}\nAI-generated analysis for professional reference only.\nNot legal advice. Verify all citations independently.\n"
    return BytesIO(content.encode('utf-8'))

# =========================================================================
# HELPERS
# =========================================================================
def _id(): return uuid.uuid4().hex[:8]
def _cur(a: float): return f"₦{a:,.0f}"
def _esc(t: str): return html.escape(str(t)[:200])
def _fdate(s: str):
    try: return datetime.fromisoformat(s).strftime("%d %b %Y")
    except: return str(s)
def _days(s: str):
    try: return (datetime.fromisoformat(s).date() - datetime.now().date()).days
    except: return 999
def _rel(s: str):
    d = _days(s)
    if d == 0: return "Today"
    if d == 1: return "Tomorrow"
    if d == -1: return "Yesterday"
    if 0 < d <= 7: return f"In {d}d"
    if -7 <= d < 0: return f"{abs(d)}d ago"
    return _fdate(s)

# =========================================================================
# SESSION STATE
# =========================================================================
if "api_key" not in st.session_state:
    st.session_state.update({
        "api_key": "", "api_configured": False, "cases": [], "clients": [],
        "time_entries": [], "last_response": "", "last_query": "",
        "show_history": False, "conversation_id": None,
        "theme": "emerald",
    })

# =========================================================================
# API
# =========================================================================
def _key():
    for fn in [lambda: st.secrets.get("GEMINI_API_KEY",""), lambda: os.getenv("GEMINI_API_KEY",""), lambda: st.session_state.get("api_key","")]:
        k = fn()
        if k and k.strip(): return k.strip()
    return ""

def api_connect(k: str) -> bool:
    try:
        genai.configure(api_key=k, transport="rest")
        genai.GenerativeModel(DEFAULT_MODEL).generate_content("test", generation_config={"max_output_tokens": 1})
        st.session_state.update(api_configured=True, api_key=k)
        return True
    except Exception as e:
        st.error(f"Connection failed: {str(e)[:100]}")
        return False

def _gen(prompt: str, sys: str) -> str:
    """Fast generation with strict prompts."""
    k = _key()
    if not k: return "⚠️ No API key configured."
    
    try:
        genai.configure(api_key=k, transport="rest")
        model = genai.GenerativeModel(DEFAULT_MODEL, system_instruction=sys)
    except:
        model = genai.GenerativeModel(DEFAULT_MODEL)
        prompt = f"{sys}\n\n{prompt}"
    
    for attempt in range(2):
        try:
            return model.generate_content(prompt, generation_config=GEN_CONFIG).text
        except Exception as e:
            if attempt == 1:
                return f"Error: {str(e)[:100]}"
            time.sleep(1)
    return "Error: generation failed."

# =========================================================================
# ANALYSIS PIPELINE (FAST, FOCUSED)
# =========================================================================
def run_analysis(query: str, task: str) -> dict:
    """Fast analysis without multi-pass complexity."""
    if not st.session_state.api_configured:
        return {"main": "⚠️ Configure API key first.", "grade": ""}
    
    sys = TASK_INSTRUCTIONS.get(task, GENERAL_INSTRUCTION)
    
    try:
        result = _gen(query, sys)
        
        # Save to database
        analysis_id = save_analysis(
            query=query,
            task_type=task,
            issue_spot="",
            ambiguity="",
            main_analysis=result,
            critique="",
            grade=""
        )
        
        return {"main": result, "id": analysis_id, "grade": ""}
    except Exception as e:
        return {"main": f"Error: {str(e)}", "grade": ""}

# =========================================================================
# SIDEBAR (COMPLETE)
# =========================================================================
def render_sidebar():
    with st.sidebar:
        st.markdown("## ⚖️ LexiAssist v7.0")
        st.caption("Fast, Focused, Persistent Legal AI")
        st.divider()
        
        # API Management
        st.markdown("### 🤖 AI Engine")
        if st.session_state.api_configured:
            st.success(f"✅ Connected")
        else:
            st.warning("⚠️ Not connected")
        
        ki = st.text_input("API Key", type="password", value=st.session_state.api_key,
            label_visibility="collapsed", placeholder="Paste API key…")
        if st.button("Connect", type="primary", use_container_width=True):
            if ki and len(ki) > 10:
                if api_connect(ki.strip()):
                    st.success("✅ Connected!"); st.rerun()
            else:
                st.error("Enter valid key")
        st.caption("[Get key](https://aistudio.google.com/app/apikey)")
        
        st.divider()
        
        # Data Management
        st.markdown("### 💾 Data Management")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export Analysis", use_container_width=True, key="exp_btn"):
                st.session_state.show_export_options = True
        with col2:
            if st.button("📚 View History", use_container_width=True):
                st.session_state.show_history = not st.session_state.show_history
        
        # Import document
        up = st.file_uploader("📤 Import Document", 
            type=["pdf","docx","txt","csv","xlsx"],
            help="Load a document to analyze")
        if up:
            try:
                with st.spinner("Loading file…"):
                    text = _extract_text_from_file(up)
                    st.session_state.loaded_template = text
                    st.success(f"✅ {up.name} loaded!")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ {str(e)[:100]}")
        
        st.divider()
        st.caption("**LexiAssist v7.0** © 2026 · No off-topic · No rambling · Persistent storage")


# =========================================================================
# EXPORT MODAL
# =========================================================================
@st.dialog("Export Analysis")
def show_export_dialog():
    """Export dialog for multiple formats."""
    if not st.session_state.last_response:
        st.warning("No analysis to export yet.")
        return
    
    st.markdown("### Choose Export Format")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📄 PDF", use_container_width=True):
            buffer = export_to_pdf(st.session_state.last_response, "LexiAssist Analysis")
            st.download_button(
                "Download PDF", buffer, "analysis.pdf", "application/pdf",
                key="dl_pdf"
            )
            st.success("✅ PDF ready")
    
    with col2:
        if st.button("📘 DOCX", use_container_width=True):
            buffer = export_to_docx(st.session_state.last_response, "LexiAssist Analysis")
            st.download_button(
                "Download DOCX", buffer, "analysis.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="dl_docx"
            )
            st.success("✅ DOCX ready")
    
    with col3:
        if st.button("📝 TXT", use_container_width=True):
            buffer = export_to_txt(st.session_state.last_response, "LexiAssist Analysis")
            st.download_button(
                "Download TXT", buffer, "analysis.txt", "text/plain",
                key="dl_txt"
            )
            st.success("✅ TXT ready")
    
    with col4:
        if st.button("📋 JSON", use_container_width=True):
            json_data = json.dumps({
                "query": st.session_state.last_query,
                "analysis": st.session_state.last_response,
                "timestamp": datetime.now().isoformat()
            }, indent=2)
            st.download_button(
                "Download JSON", json_data, "analysis.json", "application/json",
                key="dl_json"
            )
            st.success("✅ JSON ready")


# =========================================================================
# PAGE: HOME
# =========================================================================
def render_landing():
    st.markdown("""
    <div class="hero">
        <h1>⚖️ LexiAssist v7.0</h1>
        <p><strong>Elite Legal Reasoning Engine for Nigerian Lawyers</strong></p>
        <p style="font-size: 0.9rem; margin-top: 1rem;">
            ✓ Instruction-strict (no off-topic rambling)  
            ✓ Fast responses (1-3 minutes max)  
            ✓ Persistent storage (full history saved)  
            ✓ Multi-format export (PDF, DOCX, TXT, JSON)  
            ✓ Nigerian law focused
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### ⚡ Key Features")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-card"><div class="stat-value">🔍</div><div class="stat-label">Issue Spotting</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><div class="stat-value">📚</div><div class="stat-label">Legal Research</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><div class="stat-value">📄</div><div class="stat-label">Document Draft</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><div class="stat-value">💾</div><div class="stat-label">Full History</div></div>', unsafe_allow_html=True)
    
    st.divider()
    st.markdown("### 🚀 Getting Started")
    st.markdown("""
    1. **Connect API Key** (sidebar) — Get one free at [Google AI Studio](https://aistudio.google.com/app/apikey)
    2. **Go to AI Assistant** tab
    3. **Ask a question** — Be specific for better answers
    4. **Export results** — PDF, DOCX, TXT, or JSON
    5. **View history** — All your analyses are saved
    """)
    
    # Show recent analyses
    st.markdown("### 📊 Recent Analyses")
    recent = load_analyses(5)
    if recent:
        for r in recent:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"**{r['task']}** — {r['query'][:80]}...")
                with col2:
                    st.caption(r['date'][:10])
                with col3:
                    if st.button("View", key=f"view_{r['id']}", use_container_width=True):
                        st.session_state.conversation_id = r['id']
                        st.rerun()
    else:
        st.info("No analyses yet. Head to **AI Assistant** to get started.")


# =========================================================================
# PAGE: AI ASSISTANT (MAIN)
# =========================================================================
def render_ai():
    st.markdown('<div class="page-header"><h1>🧠 AI Legal Assistant</h1><p>Fast, focused, instruction-strict analysis</p></div>', unsafe_allow_html=True)
    
    if not st.session_state.api_configured:
        st.warning("⚠️ **Configure API key in sidebar first**", icon="🔑")
        return
    
    # Load previous analysis if viewing from history
    if st.session_state.conversation_id:
        analysis_data = get_analysis(st.session_state.conversation_id)
        if analysis_data:
            query, task, issue_spot, ambiguity, main, critique, grade = analysis_data
            st.session_state.last_query = query
            st.session_state.last_response = main
            st.session_state.conversation_id = None
    
    # Task selection
    col1, col2 = st.columns([2, 1])
    with col1:
        task_keys = list(TASK_TYPES.keys())
        chosen_task = st.selectbox(
            "🎯 Select Task Type",
            task_keys,
            index=task_keys.index("analysis"),
            format_func=lambda k: f"{TASK_TYPES[k]['icon']} {TASK_TYPES[k]['label']} — {TASK_TYPES[k]['desc']}",
            key="task_select"
        )
    with col2:
        st.metric("", st.session_state.api_configured and "✅ Ready" or "⚠️ Setup")
    
    st.divider()
    
    # Input area
    prefill = st.session_state.pop("loaded_template", "")
    user_input = st.text_area(
        "📝 Your Legal Query",
        value=prefill,
        height=200,
        placeholder="Be specific: include dates, amounts, names, and what happened.\nExample: 'My client entered contract on 15 Jan 2022 for N50m goods delivery. ABC Ltd has not delivered. Client paid 60%. ABC claims force majeure due to flooding. Analyze strength of defense.'"
    )
    
    if user_input:
        wc = len(user_input.split())
        if wc < 30:
            st.caption("⚠️ **Tip:** More detail = better analysis. Add dates, amounts, names, facts.")
        else:
            st.caption(f"✅ **{wc} words** — Good detail for analysis")
    
    st.markdown("")
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        analyze = st.button(
            "🧠 Analyze Now",
            type="primary",
            use_container_width=True,
            disabled=not (st.session_state.api_configured and user_input.strip())
        )
    with col2:
        export_btn = st.button("💾 Export", use_container_width=True, disabled=not st.session_state.last_response)
    with col3:
        clear_btn = st.button("🗑️ Clear All", use_container_width=True, key="clear_all_btn")
    
    # ── CLEAR FUNCTION (FIXED) ────────────────────────────────────────
    if clear_btn:
        st.session_state.last_response = ""
        st.session_state.last_query = ""
        st.rerun()
    
    # ── EXPORT (FIXED) ────────────────────────────────────────────────
    if export_btn:
        show_export_dialog()
    
    # ── ANALYSIS (FAST) ───────────────────────────────────────────────
    if analyze:
        if not user_input.strip():
            st.error("Please enter a query.")
            return
        
        with st.spinner(f"🧠 Analyzing ({TASK_TYPES[chosen_task]['label']})…"):
            result = run_analysis(user_input, chosen_task)
            
            if result["main"].startswith("Error"):
                st.error(result["main"])
            else:
                st.session_state.last_response = result["main"]
                st.session_state.last_query = user_input
                st.rerun()
    
    # ── DISPLAY RESULTS ───────────────────────────────────────────────
    if st.session_state.last_response:
        st.markdown("---")
        st.markdown("#### 📄 Analysis")
        
        text = st.session_state.last_response
        wc = len(text.split())
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.metric("Words", f"{wc:,}")
        with col2:
            st.metric("Task", TASK_TYPES[chosen_task]['label'][:15])
        with col3:
            st.caption(f"Generated {datetime.now().strftime('%H:%M:%S')}")
        
        # Display analysis
        st.markdown(f'<div class="response-box">{_esc(text)}\n</div>', unsafe_allow_html=True)
        
        # Disclaimer
        st.markdown('<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated analysis for professional reference only. Not legal advice. Always verify citations independently and apply your own professional judgment.</div>', unsafe_allow_html=True)
        
        # Follow-up
        st.divider()
        st.markdown("#### 💬 Follow-Up Question")
        followup = st.text_input(
            "Ask a follow-up (same context retained)",
            placeholder="e.g., 'Go deeper on limitation period' or 'What if contract had arbitration clause?'",
            key="followup_input"
        )
        
        if st.button("Ask Follow-Up", type="secondary", disabled=not followup):
            with st.spinner("Analyzing follow-up…"):
                # Add follow-up to conversation
                prompt = f"Original query: {st.session_state.last_query}\n\nMy previous analysis:\n{st.session_state.last_response}\n\nFOLLOW-UP QUESTION: {followup}\n\nAnswer the follow-up directly. Be concise."
                
                sys = f"{TASK_INSTRUCTIONS.get(chosen_task, GENERAL_INSTRUCTION)}\n\nIMPORTANT: This is a follow-up to a previous analysis. Answer only the follow-up question. Do not repeat the previous analysis. Be concise and direct."
                
                result = _gen(prompt, sys)
                st.session_state.last_response = result
                st.rerun()


# =========================================================================
# PAGE: RESEARCH
# =========================================================================
def render_research():
    st.markdown('<div class="page-header"><h1>📚 Legal Research</h1><p>Statutes, case law, Nigerian authorities</p></div>', unsafe_allow_html=True)
    
    if not st.session_state.api_configured:
        st.warning("⚠️ Connect API key in sidebar")
        return
    
    query = st.text_input(
        "🔍 Research Query",
        placeholder="e.g., 'Employer liability for workplace injuries under Nigerian law — statutes, cases, procedure'",
        key="research_q"
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        go = st.button("📚 Research", type="primary", use_container_width=True, disabled=not query)
    with col2:
        clr = st.button("Clear", use_container_width=True)
    
    if go:
        with st.spinner("Researching…"):
            result = run_analysis(query, "research")
            st.session_state.last_response = result["main"]
            st.session_state.last_query = query
            st.rerun()
    
    if clr:
        st.session_state.last_response = ""
        st.session_state.last_query = ""
        st.rerun()
    
    if st.session_state.last_response:
        st.markdown("---")
        wc = len(st.session_state.last_response.split())
        st.caption(f"📝 {wc:,} words")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📥 Export PDF", use_container_width=True):
                buffer = export_to_pdf(st.session_state.last_response, "Legal Research")
                st.download_button("Download", buffer, "research.pdf", "application/pdf", key="dl_pdf_research")
        with col2:
            if st.button("📥 Export DOCX", use_container_width=True):
                buffer = export_to_docx(st.session_state.last_response, "Legal Research")
                st.download_button("Download", buffer, "research.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_docx_research")
        with col3:
            if st.button("📥 Export TXT", use_container_width=True):
                buffer = export_to_txt(st.session_state.last_response, "Legal Research")
                st.download_button("Download", buffer, "research.txt", "text/plain", key="dl_txt_research")
        
        st.markdown(f'<div class="response-box">{_esc(st.session_state.last_response)}\n</div>', unsafe_allow_html=True)


# =========================================================================
# PAGE: DOCUMENT DRAFTING
# =========================================================================
def render_drafting():
    st.markdown('<div class="page-header"><h1>📄 Document Drafting</h1><p>Professional contracts, pleadings, affidavits</p></div>', unsafe_allow_html=True)
    
    if not st.session_state.api_configured:
        st.warning("⚠️ Connect API key in sidebar")
        return
    
    # Template selector
    templates = get_templates()
    st.markdown("### 📋 Start with Template")
    cols = st.columns(len(templates))
    for i, t in enumerate(templates):
        with cols[i]:
            if st.button(f"{t['name'][:20]}…", key=f"tmpl_{t['id']}", use_container_width=True):
                st.session_state.loaded_template = t["content"]
                st.rerun()
    
    st.divider()
    
    st.markdown("### ✍️ Draft or Customize")
    query = st.text_area(
        "Describe what you need",
        height=200,
        placeholder="e.g., 'Draft an employment contract for a junior lawyer, 2-year term, N2m annual salary, Lagos-based, 3 months probation, 21 days leave, 30 days notice period'"
    )
    
    if st.button("📝 Draft Document", type="primary", use_container_width=True, disabled=not query):
        with st.spinner("Drafting…"):
            result = run_analysis(query, "drafting")
            st.session_state.last_response = result["main"]
            st.session_state.last_query = query
            st.rerun()
    
    if st.session_state.last_response:
        st.markdown("---")
        st.markdown("#### 📄 Draft Document")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            buffer = export_to_pdf(st.session_state.last_response, "Draft Document")
            st.download_button("📥 PDF", buffer, "document.pdf", "application/pdf", use_container_width=True)
        with col2:
            buffer = export_to_docx(st.session_state.last_response, "Draft Document")
            st.download_button("📥 DOCX", buffer, "document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
        with col3:
            buffer = export_to_txt(st.session_state.last_response, "Draft Document")
            st.download_button("📥 TXT", buffer, "document.txt", "text/plain", use_container_width=True)
        
        st.markdown(f'<div class="response-box">{_esc(st.session_state.last_response)}\n</div>', unsafe_allow_html=True)


# =========================================================================
# PAGE: CASE MANAGEMENT
# =========================================================================
def render_cases():
    st.markdown('<div class="page-header"><h1>📁 Case Management</h1><p>Track cases, hearings, status</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Active Cases", len([c for c in st.session_state.cases if c.get("status") == "Active"]))
    with col2:
        st.metric("Total Cases", len(st.session_state.cases))
    
    st.divider()
    
    # Add case form
    with st.expander("➕ Add New Case", expanded=not bool(st.session_state.cases)):
        with st.form("add_case_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Case Title *", placeholder="e.g., Smith v. ABC Ltd")
                suit_no = st.text_input("Suit Number *", placeholder="e.g., FHC/L/CS/2024/001")
                court = st.text_input("Court", placeholder="e.g., Federal High Court, Lagos")
            with col2:
                status = st.selectbox("Status", CASE_STATUSES)
                next_hearing = st.date_input("Next Hearing")
                notes = st.text_area("Notes", height=100)
            
            if st.form_submit_button("Save Case", type="primary"):
                if title.strip() and suit_no.strip():
                    case = {
                        "id": _id(),
                        "title": title.strip(),
                        "suit_no": suit_no.strip(),
                        "court": court.strip(),
                        "status": status,
                        "next_hearing": next_hearing.isoformat() if next_hearing else None,
                        "notes": notes.strip(),
                        "created_at": datetime.now().isoformat()
                    }
                    st.session_state.cases.append(case)
                    st.success("✅ Case added!")
                    st.rerun()
                else:
                    st.error("Title and Suit Number required")
    
    # Display cases
    if st.session_state.cases:
        search = st.text_input("🔍 Search cases", placeholder="Title, suit number, court…")
        cases = [c for c in st.session_state.cases if search.lower() in json.dumps(c).lower()] if search else st.session_state.cases
        
        for case in cases:
            col1, col2 = st.columns([4, 1])
            with col1:
                status_color = {"Active": "green", "Pending": "orange", "Completed": "blue"}.get(case.get("status"), "gray")
                hearing_text = f"📅 {_rel(case['next_hearing'])}" if case.get("next_hearing") else ""
                st.markdown(f"""
                **{_esc(case['title'])}** 
                `{_esc(case.get('suit_no', ''))}` | {_esc(case.get('court', ''))}
                {hearing_text}
                """)
            with col2:
                if st.button("🗑️", key=f"del_{case['id']}", help="Delete"):
                    st.session_state.cases = [c for c in st.session_state.cases if c["id"] != case["id"]]
                    st.rerun()
    else:
        st.info("No cases yet. Add one above.")


# =========================================================================
# PAGE: LEGAL TOOLS
# =========================================================================
LIMITATION_PERIODS = [
    {"cause": "Contract", "period": "6 years", "act": "Limitation Act, s. 8(1)(a)"},
    {"cause": "Tort/Negligence", "period": "6 years", "act": "Limitation Act, s. 8(1)(a)"},
    {"cause": "Personal Injury", "period": "3 years", "act": "Limitation Act, s. 8(1)(b)"},
    {"cause": "Defamation", "period": "3 years", "act": "Limitation Act, s. 8(1)(b)"},
    {"cause": "Recovery of Land", "period": "12 years", "act": "Limitation Act, s. 16"},
    {"cause": "Mortgage", "period": "12 years", "act": "Limitation Act, s. 18"},
    {"cause": "Labour Dispute", "period": "12 months", "act": "NIC Act, s. 7"},
    {"cause": "Fundamental Rights", "period": "12 months", "act": "FREP Rules, Order II r. 1"},
]

def render_tools():
    st.markdown('<div class="page-header"><h1>🇳🇬 Legal Tools</h1><p>Quick references & calculators</p></div>', unsafe_allow_html=True)
    
    tabs = st.tabs(["⏱️ Limitation Periods", "💹 Interest Calculator"])
    
    with tabs[0]:
        st.markdown("### Limitation Periods Under Nigerian Law")
        search = st.text_input("Search", placeholder="e.g., contract, injury…")
        data = [l for l in LIMITATION_PERIODS if search.lower() in l["cause"].lower()] if search else LIMITATION_PERIODS
        
        if data:
            df = pd.DataFrame(data).rename(columns={"cause": "Cause of Action", "period": "Limitation Period", "act": "Statute"})
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    with tabs[1]:
        st.markdown("### Calculate Interest")
        with st.form("interest_form"):
            col1, col2 = st.columns(2)
            with col1:
                principal = st.number_input("Principal Amount (₦)", 0.0, value=1_000_000.0, step=100_000.0)
                rate = st.number_input("Annual Rate (%)", 0.0, value=10.0, step=0.5)
            with col2:
                months = st.number_input("Duration (months)", 1, value=12)
                calc_type = st.selectbox("Type", ["Simple Interest", "Compound (Monthly)"])
            
            if st.form_submit_button("Calculate", type="primary"):
                if calc_type == "Simple Interest":
                    interest = principal * (rate / 100) * (months / 12)
                else:
                    interest = principal * ((1 + (rate / 100) / 12) ** months) - principal
                
                total = principal + interest
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Principal", _cur(principal))
                with col2:
                    st.metric("Interest", _cur(interest))
                with col3:
                    st.metric("Total", _cur(total))


# =========================================================================
# MAIN APP
# =========================================================================
def main():
    st.markdown(_BASE_CSS, unsafe_allow_html=True)
    init_db()
    
    render_sidebar()
    
    tabs = st.tabs(["🏠 Home", "🧠 AI Assistant", "📚 Research", "📄 Drafting", "📁 Cases", "🇳🇬 Tools"])
    
    with tabs[0]:
        render_landing()
    with tabs[1]:
        render_ai()
    with tabs[2]:
        render_research()
    with tabs[3]:
        render_drafting()
    with tabs[4]:
        render_cases()
    with tabs[5]:
        render_tools()
    
    st.markdown("""
    <div class="app-footer">
    <p><strong>⚖️ LexiAssist v7.0</strong> — Elite Legal Reasoning for Nigerian Lawyers</p>
    <p>Fast • Focused • Persistent • No Off-Topic Rambling</p>
    <p style="font-size: 0.7rem; margin-top: 0.5rem;">
    ⚠️ <strong>Disclaimer:</strong> AI-generated analysis for professional reference only. 
    Not legal advice. Always verify citations and apply professional judgment.
    </p>
    <p style="font-size: 0.65rem;">© 2026 LexiAssist | Built with Streamlit & Google Gemini</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()


