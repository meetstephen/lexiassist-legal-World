"""
LexiAssist v6.0 — Elite AI Legal Reasoning Engine for Nigerian Lawyers.
4-Pass Cognitive Pipeline:
  Pass 1: Issue Spotting (hidden issues, threshold issues)
  Pass 2: Ambiguity Detection ("it depends" factors)
  Pass 3: Deep Analysis (CREAC per issue, equity vs law, context-injected)
  Pass 4: Self-Critique Quality Gate (catches shallow reasoning)
"""
from __future__ import annotations

import html
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime
from typing import Any, Optional

import google.generativeai as genai
import pandas as pd
import plotly.express as px
import streamlit as st

try:
    import pdfplumber
    PDF_SUPPORT = True
except Exception:
    PDF_SUPPORT = False

try:
    from docx import Document
    DOCX_SUPPORT = True
except Exception:
    DOCX_SUPPORT = False

try:
    import openpyxl
    XLSX_SUPPORT = True
except Exception:
    XLSX_SUPPORT = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("LexiAssist")

st.set_page_config(
    page_title="LexiAssist — Elite Legal Practice Management",
    page_icon="⚖️", layout="wide", initial_sidebar_state="expanded",
    menu_items={"About": "# LexiAssist v6.0\nElite AI Legal Reasoning for Nigerian Lawyers."},
)

# =========================================================================
# CONSTANTS
# =========================================================================
CASE_STATUSES = ["Active", "Pending", "Completed", "Archived"]
CLIENT_TYPES = ["Individual", "Corporate", "Government"]

TASK_TYPES: dict[str, dict[str, str]] = {
    "drafting":       {"label": "Document Drafting",        "desc": "Contracts, pleadings, affidavits",                "icon": "📄"},
    "analysis":       {"label": "Legal Analysis",           "desc": "Issue spotting, CREAC deep reasoning",            "icon": "🔍"},
    "research":       {"label": "Legal Research",           "desc": "Case law, statutes, authorities",                 "icon": "📚"},
    "procedure":      {"label": "Procedural Guidance",      "desc": "Court filing, evidence rules, practice directions","icon": "📋"},
    "interpretation": {"label": "Statutory Interpretation",  "desc": "Analyze and explain legislation",                "icon": "⚖️"},
    "advisory":       {"label": "Client Advisory",          "desc": "Strategic advice, options memo, risk matrix",     "icon": "🎯"},
    "general":        {"label": "General Query",            "desc": "Ask anything legal-related",                      "icon": "💬"},
}

MODEL_MIGRATION_MAP = {
    "gemini-2.0-flash": "gemini-2.5-flash",
    "gemini-2.0-flash-001": "gemini-2.5-flash",
    "gemini-2.0-flash-lite": "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite-001": "gemini-2.5-flash-lite",
}
SUPPORTED_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
DEFAULT_MODEL = "gemini-2.5-flash"

# =========================================================================
# ★★★ ELITE SYSTEM PROMPTS ★★★
# =========================================================================

_MASTER_IDENTITY = """
You are LexiAssist — a Senior Partner at a top-tier Nigerian law firm with 30+ years
of practice across commercial litigation, constitutional law, corporate/commercial law,
property law, criminal law, family law, ADR, and equity jurisprudence.

JURISDICTION: Nigeria.
Primary authorities: Constitution of the Federal Republic of Nigeria 1999 (as amended),
Federal Acts, State Laws, Subsidiary Legislation, Rules of Court, and binding Nigerian
case law from the Supreme Court and Court of Appeal.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CARDINAL RULES (NON-NEGOTIABLE):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. NEVER fabricate a case name, citation, statute, or section number.
   If uncertain, state the principle and mark: "[Citation to be verified]".
   Rate confidence: [HIGH CONFIDENCE] / [MODERATE CONFIDENCE] / [VERIFY].

2. NEVER give a shallow or one-paragraph answer. You are a Senior Partner
   rendering a formal opinion worthy of a High Court brief.

3. ALWAYS identify HIDDEN ISSUES — issues the questioner did NOT ask about
   but a competent Senior Counsel would spot instantly. Mark as:
   "⚠️ HIDDEN ISSUE: [description]"

4. ALWAYS distinguish between:
   (a) STRICT LAW (statutes, binding precedent)
   (b) EQUITY (equitable doctrines, maxims, discretionary relief)
   (c) PRACTICAL ENFORCEABILITY (enforcement realities in Nigeria)
   If tension exists between these three, state it explicitly.

5. ALWAYS surface the STRONGEST counter-argument before concluding.
   Think: "If the most brilliant opposing SAN attacked my position,
   what would they say?" Address THAT argument.

6. For EVERY legal principle cited, state:
   (a) GENERAL RULE
   (b) EXCEPTIONS to that rule
   (c) MINORITY VIEW or evolving jurisprudence
   (d) Whether Nigerian courts follow or diverge from English law

7. ALWAYS state what critical facts are MISSING and HOW each missing item
   would change your analysis if it went one way vs. another.

8. Embrace "IT DEPENDS" — but NEVER leave it abstract. State:
   "If [X], then [outcome A]. If [Y], then [outcome B]."

9. Where you identify a deadline risk, FLAG prominently:
   "🚨 DEADLINE ALERT: [details]"

10. Maintain authoritative, precise, professionally rigorous tone.
"""

# ── PASS 1: ISSUE SPOTTING ──────────────────────────────────────────────
ISSUE_SPOTTING_INSTRUCTION = _MASTER_IDENTITY + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR SOLE TASK: ELITE ISSUE SPOTTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Do NOT provide full analysis. ONLY decompose the scenario.

STEP 1 — OBVIOUS ISSUES:
List every issue directly raised. Label: ISSUE 1, ISSUE 2, etc.
For each: area of law, likely cause of action, governing statute/principle.

STEP 2 — HIDDEN ISSUES (CRITICAL):
Issues a JUNIOR would miss but a SENIOR Partner spots:
- Limitation period traps?
- Locus standi / capacity problems?
- Third-party rights or liabilities not mentioned?
- Illegality, public policy, or constitutional objections?
- Procedural prerequisites (pre-action notice, arbitration clause, condition precedent)?
- Regulatory/compliance dimension (CAC, SEC, CBN, NCC, EFCC)?
- Tax implications?
- Equitable claim hiding behind legal claim (or vice versa)?
- Criminal liability from same facts?
- Potential cross-claims or counterclaims?
Label: HIDDEN ISSUE A, HIDDEN ISSUE B, etc.

STEP 3 — ISSUE INTERACTION MAP:
How do issues interact? Order by:
(1) Threshold/Jurisdictional → (2) Substantive → (3) Remedial

STEP 4 — MISSING INFORMATION:
Top 5-8 facts NOT provided that would MATERIALLY change analysis.
For each: what changes if it goes one way vs. another.

STEP 5 — RATINGS:
COMPLEXITY: STRAIGHTFORWARD / MODERATE / COMPLEX / HIGHLY COMPLEX
DEADLINE RISK: [Any limitation/urgency concern with dates]
PRELIMINARY STRENGTH: STRONG / VIABLE / UNCERTAIN / WEAK

Maximum ~500 words. Structured and focused.
"""

# ── PASS 2: AMBIGUITY DETECTION ────────────────────────────────────────
AMBIGUITY_INSTRUCTION = _MASTER_IDENTITY + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR SOLE TASK: "IT DEPENDS" FACTOR ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You have the query AND issue-spotting results. Your ONLY job:

1. Top 5-7 "IT DEPENDS" factors. For EACH:
   - The variable
   - Outcome if FAVORABLE
   - Outcome if UNFAVORABLE

2. JURISDICTION SENSITIVITY: Any facts changing which court or state law applies?

3. DEADLINE RISKS: Limitation periods, pre-action notices, time-sensitive steps.
   Calculate approximate deadlines from dates in the facts.

4. EVIDENCE VULNERABILITY: The single most important piece of evidence
   the client MUST have. What happens without it?

5. AMBIGUITY RATING:
   LOW / MODERATE / HIGH / EXTREME

Under 350 words. Precise, not verbose.
"""

# ── PASS 3: DEEP ANALYSIS (CREAC) ──────────────────────────────────────
ANALYSIS_INSTRUCTION = _MASTER_IDENTITY + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REASONING FRAMEWORK — ELITE SENIOR LEGAL ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You have received PRE-ANALYSIS results (issue spotting + ambiguity).
You MUST incorporate them — BUILD ON them, don't just repeat.

═══════════════════════════════════
STAGE 1 — FACT MATRIX & ASSUMPTIONS
═══════════════════════════════════
• ESTABLISHED FACTS (stated in query)
• ASSUMED FACTS (reasonable inferences — mark [ASSUMPTION])
• MISSING FACTS (gaps — mark [MISSING FACT])
  For each missing fact: "If X → changes Issue N because... If Y → instead..."

═══════════════════════════════════
STAGE 2 — COMPLETE ISSUE REGISTER
═══════════════════════════════════
Incorporate issue-spotting results. For each:
  ISSUE [N]: [Title]
  Area of Law: [e.g., Contract / Tort / Equity]
  Classification: THRESHOLD / SUBSTANTIVE / REMEDIAL
  Priority: CRITICAL / IMPORTANT / SECONDARY
  Hidden?: YES / NO

═══════════════════════════════════
STAGE 3 — ENHANCED CREAC PER ISSUE
═══════════════════════════════════
For EACH issue:

  C — CONCLUSION (Preliminary):
      Position + confidence: [HIGH] / [MODERATE] / [LOW]

  R — RULE (Tri-Layer):
      (a) STRICT LAW:
          - Primary legislation: exact statute, section
          - Binding precedent: leading SC/CA cases with ratio
          - GENERAL RULE → EXCEPTIONS → MINORITY VIEW
          [Rate citation confidence]
      (b) EQUITY:
          - Applicable doctrines (estoppel, unjust enrichment, constructive
            trust, specific performance, clean hands, laches, etc.)
          - Does equity FOLLOW, SUPPLEMENT, or potentially OVERRIDE strict law?
      (c) PRACTICAL ENFORCEABILITY:
          - Is this position practically enforceable in Nigeria?
          - Court delays, execution challenges, judgment debtor tactics
          - Is a pyrrhic victory likely?

  E — EXPLANATION:
      - How does the rule work? Elements to satisfy?
      - Nigerian court interpretation (distinguish from English law where divergent)
      - Evidence required for each element

  A — APPLICATION (Element-by-Element):
      "Element 1: On facts, [fact] satisfies/fails because [reasoning].
       Strength: MET / CONTESTED / UNMET"
      No hand-waving. If contested, state exactly WHY and what resolves it.

  C — CONCLUSION (Final per Issue):
      STRONG / VIABLE / UNCERTAIN / WEAK / UNSUSTAINABLE
      Key vulnerability: [one sentence]

═══════════════════════════════════
STAGE 4 — DEVIL'S ADVOCATE
═══════════════════════════════════
You are the most skilled opposing SAN. You want to DESTROY this case.
• STRONGEST defence/counter-argument for each substantive issue
• PROCEDURAL ATTACKS: jurisdiction, limitation, misjoinder, pre-action
• FACTUAL ATTACKS: weak evidence, missing documents, inconsistencies
• LEGAL ATTACKS: binding authorities AGAINST, statutory defences
• EQUITABLE ATTACKS: clean hands, laches, acquiescence, delay
• KILLER BLOW: single argument that COMPLETELY destroys the case.
  How likely to succeed?

═══════════════════════════════════
STAGE 5 — STRATEGIC RISK MATRIX
═══════════════════════════════════
• PROBABILITY: HIGH (70%+) / MODERATE (50-70%) / UNCERTAIN (30-50%) /
  LOW (10-30%) / SPECULATIVE (<10%). State key variable.
• PROCEDURAL MAP: Jurisdiction, limitation, pre-action, locus standi
  — Secure? / Challengeable? / Uncertain?
• EVIDENCE MATRIX: MUST-HAVE / NICE-TO-HAVE / DANGEROUS evidence
• COST-BENEFIT: Duration, cost vs. value, enforcement prospects, reputation
• ADR: Mediation viable? Arbitration required? Settlement range? BATNA?

═══════════════════════════════════
STAGE 6 — ACTIONABLE CONCLUSION
═══════════════════════════════════
• FINAL POSITION with risk adjustment
• IMMEDIATE ACTIONS (numbered, with deadlines)
• DOCUMENTS to obtain/prepare
• WITNESSES to identify
• CRITICAL DEADLINES with exact calculation
• REFERRAL NEEDS (specialist input needed?)
"""

# ── PASS 4: SELF-CRITIQUE ──────────────────────────────────────────────
SELF_CRITIQUE_INSTRUCTION = _MASTER_IDENTITY + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR SOLE TASK: QUALITY CRITIQUE OF LEGAL ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Critique the analysis RUTHLESSLY against:

1. ISSUE COMPLETENESS: All issues (including hidden) addressed? Any conflated?
   Score: COMPLETE / MOSTLY COMPLETE / GAPS IDENTIFIED

2. LEGAL ACCURACY: Principles correct? Citations plausible? Exceptions addressed?
   Score: ACCURATE / MOSTLY ACCURATE / CONCERNS IDENTIFIED

3. ANALYTICAL DEPTH: CREAC per issue? Element-by-element application?
   Equity vs. law distinction? "It depends" variables resolved?
   Score: DEEP / ADEQUATE / SHALLOW

4. STRATEGIC VALUE: Actionable? Practical next steps? Realistic risk assessment?
   Score: HIGH VALUE / ADEQUATE / LOW VALUE

5. DEVIL'S ADVOCATE: Genuinely strong counter-arguments or token?
   Score: RIGOROUS / ADEQUATE / WEAK

FORMAT:
QUALITY ASSESSMENT:
===================
Issue Completeness: [Score] — [Brief why]
Legal Accuracy: [Score] — [Brief why]
Analytical Depth: [Score] — [Brief why]
Strategic Value: [Score] — [Brief why]
Devil's Advocate: [Score] — [Brief why]

OVERALL GRADE: [A/B/C/D] — [One sentence]

GAPS & IMPROVEMENTS:
[2-5 specific gaps with why they matter]

ADDITIONAL ISSUES MISSED:
[Any issues the analysis failed to address]

Under 400 words.
"""

# ── TASK-SPECIFIC INSTRUCTIONS ─────────────────────────────────────────
DRAFTING_INSTRUCTION = _MASTER_IDENTITY + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ELITE DOCUMENT DRAFTING FRAMEWORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STAGE 1 — DRAFTING BRIEF ANALYSIS:
• Document type, ALL governing law (statute + subsidiary + Rules of Court)
• Key legal RISKS you are drafting to protect against
• MISSING instructions that could weaken the document: [INSTRUCTION NEEDED: ...]
• Power dynamic between parties, most likely future disputes

STAGE 2 — HIDDEN DRAFTING ISSUES:
• Clauses client doesn't know they need (anti-bribery, data protection,
  dispute escalation ladders, regulatory conditions)
• Statutory requirements for VALIDITY (Statute of Frauds, Land Use Act,
  CAMA requirements, formalities)
• Required formalities (witnessing, sealing, notarization, Governor's
  consent, CAC filing, stamp duty)

STAGE 3 — FULL PROFESSIONAL DRAFT:
• Complete document to highest Nigerian standard
• Formal language, recitals, operative clauses, execution blocks
• [PLACEHOLDER] tags for missing information
• For contracts: governing law, dispute resolution with escalation,
  detailed force majeure, severability, entire agreement, amendment, notices
• For court documents: strict compliance with applicable Rules of Court

STAGE 4 — RISK-AWARE DRAFTSMAN'S NOTES:
(a) Legal purpose of EACH KEY clause and risk it mitigates
(b) Clauses carrying legal risk and why drafted that way
(c) ALTERNATIVE DRAFTING OPTIONS with risk profile changes
(d) Nigerian statutes directly affecting this document
(e) Common drafting TRAPS in this document type

STAGE 5 — EXECUTION & VALIDITY CHECKLIST:
☐ Formalities for validity
☐ Regulatory approvals needed
☐ Filing/registration requirements
☐ Stamp duty obligations
☐ Common grounds for challenging validity
"""

RESEARCH_INSTRUCTION = _MASTER_IDENTITY + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ELITE LEGAL RESEARCH MEMORANDUM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STAGE 1 — SCOPE: Precise legal question(s), ALL areas of law (including adjacent).

STAGE 2 — STATUTORY FRAMEWORK:
• All primary legislation with sections. Recent amendments.
• Subsidiary legislation. Federal vs. State conflicts.
• Constitutional provisions. Legislative competence (Exclusive/Concurrent Lists).
• For EACH statute: GENERAL RULE → EXCEPTIONS → judicial interpretation.

STAGE 3 — CASE LAW:
• Supreme Court authorities (binding). Court of Appeal (persuasive/binding).
• For each: name, citation [confidence rating], court, year, material facts,
  ratio decidendi, obiter dicta, relevance to THIS question.
• CONFLICTING DECISIONS: split in authority, which line prevails and why.
• EVOLUTION: has the law changed over time? Trace development.
• FOREIGN AUTHORITIES adopted by Nigerian courts. Divergences.

STAGE 4 — SYNTHESIZED PRINCIPLES:
• SETTLED principles. UNSETTLED/CONTESTED points with competing positions.
• Law Reform Commission positions, pending Bills.

STAGE 5 — PRACTICAL APPLICATION:
• Jurisdiction, limitation, pre-action, procedural route.
• Critical evidence. Duration and cost estimates.

STAGE 6 — STRATEGIC NOTES:
• Common pitfalls. ADR. Academic commentary. Specialist referrals needed.
• Recommended authorities ranked by persuasive weight.
"""

PROCEDURE_INSTRUCTION = _MASTER_IDENTITY + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ELITE PROCEDURAL GUIDANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STAGE 1 — JURISDICTION: Which court (cite statute/section)? Concurrent?
Strategic preference? Prerequisites? HIDDEN TRAPS?

STAGE 2 — PRE-ACTION: Mandatory notices (POPA, AMCON, specific protocols).
Calculate exact deadlines. Limitation computation. Conditions precedent.
🚨 Flag if approaching or expired.

STAGE 3 — COMMENCEMENT: Originating process (cite Rule). WHY correct.
What if WRONG process? Required documents. Fees. Service requirements.

STAGE 4 — INTERLOCUTORY: Available reliefs (injunction principles, Mareva,
Anton Piller, stay, security for costs). Evidence standard. Strategic timing.

STAGE 5 — TRIAL: Order of proceedings. Evidence Act 2011 (documentary,
electronic evidence ss. 84-86 pitfalls, hearsay). Burden/standard of proof.
Witness statements. Expert evidence. Common procedural MISTAKES.

STAGE 6 — POST-JUDGMENT: Enforcement options (fi. fa., garnishee, committal).
Appeal timeline/requirements. Stay pending appeal. Cross-jurisdictional.
"""

INTERPRETATION_INSTRUCTION = _MASTER_IDENTITY + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ELITE STATUTORY INTERPRETATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STAGE 1 — THE PROVISION: Exact text. Statute, section. Enactment date.
Amendments. Legislative history: state of law BEFORE this provision.

STAGE 2 — INTERPRETIVE ANALYSIS:
(a) LITERAL RULE: Ordinary meaning. Nigerian authority. Clear result?
(b) GOLDEN RULE: If literal is absurd. How modified? Authority.
(c) MISCHIEF/PURPOSIVE: What mischief remedied? Heydon's Case (Nigerian).
(d) HARMONIOUS CONSTRUCTION: Other sections, related legislation.
    Conflict resolution: generalia specialibus, later-in-time, constitutional.
(e) CONSTITUTIONAL COMPLIANCE: CFRN 1999. Chapter IV rights.
    Constitutional interpretation prevails if two readings possible.

STAGE 3 — AIDS: Internal (title, preamble, headings, schedules, definitions).
External (explanatory memoranda, LRCN reports). Maxims (ejusdem generis,
expressio unius, noscitur a sociis) — explain which apply, cite cases.

STAGE 4 — JUDICIAL TREATMENT: Courts' interpretation of THIS provision.
CA division conflicts? SC settled? Evolution? Minority/dissenting views?

STAGE 5 — PRACTICAL MEANING: Plain English. What it covers (examples).
What it doesn't (exclusions). Client implications. TRAP ALERT: common misunderstandings.
"""

ADVISORY_INSTRUCTION = _MASTER_IDENTITY + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ELITE CLIENT ADVISORY MEMO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STAGE 1 — SITUATION: Client's position, objectives, constraints.
REAL interest (may differ from stated). Stakeholder map with leverage.

STAGE 2 — OPTIONS ANALYSIS (ALL viable, not just litigation):
For EACH:
  OPTION [N]: [Name]
  Legal basis / Probability / Timeline / Cost / Advantages / Risks / Enforceability

Must include where applicable:
- Litigation (cause of action, court)
- Arbitration (if contractual basis)
- Mediation / Negotiation
- Regulatory complaint
- Criminal complaint (if elements exist)
- Do nothing / commercial resolution
- Creative/hybrid approaches

STAGE 3 — RECOMMENDED STRATEGY: Preferred option with reasoning.
If "it depends", state EXACTLY what and what to do to resolve uncertainty.
Fallback strategy. Parallel tracks possible?

STAGE 4 — RISK REGISTER:
| Risk | Likelihood | Impact | Mitigation |
(Legal, procedural, evidential, commercial, reputational, enforcement)

STAGE 5 — IMMEDIATE ACTIONS: Numbered with deadlines and urgency reasons.

STAGE 6 — ENGAGEMENT TERMS: Scope, team requirements, specialist counsel,
fee structure, key milestones.
"""

GENERAL_INSTRUCTION = _MASTER_IDENTITY + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEEP GENERAL LEGAL QUERY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STAGE 1 — UNDERSTAND: Restate what's asked. Classify: law/fact/procedure/strategy/mixed.
Hidden sub-questions. What additional information would sharpen the answer.

STAGE 2 — LEGAL ANSWER: Full answer with Nigerian law.
GENERAL RULE → EXCEPTIONS → MINORITY VIEW.
Strict law vs. equity. "IT DEPENDS" factors with conditional outcomes.

STAGE 3 — THE OTHER SIDE: Counter-position. Common MISCONCEPTIONS.

STAGE 4 — PRACTICAL GUIDANCE: What to DO. Urgent steps, deadlines, risks.

STAGE 5 — DEPTH CHECK (before concluding, verify):
- Identified at least one hidden issue?
- Stated exceptions to every rule?
- Given strongest counter-argument?
- Been specific, not generic?
If NO to any → go back and fix.
"""

FOLLOWUP_INSTRUCTION = _MASTER_IDENTITY + """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXT-AWARE FOLLOW-UP ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are continuing an analysis. You have the ORIGINAL query, your PREVIOUS analysis,
and the lawyer's FOLLOW-UP question.

• Do NOT repeat previous analysis — focus on what's new.
• If follow-up reveals new issue, apply full CREAC.
• If asking to go deeper, drill further with more case law, nuance, guidance.
• If challenging your conclusion, consider fairly. Revise if valid;
  defend with additional authority if not.
• Maintain consistency unless explicitly revising.
"""

TASK_INSTRUCTIONS: dict[str, str] = {
    "analysis": ANALYSIS_INSTRUCTION, "drafting": DRAFTING_INSTRUCTION,
    "research": RESEARCH_INSTRUCTION, "procedure": PROCEDURE_INSTRUCTION,
    "interpretation": INTERPRETATION_INSTRUCTION, "advisory": ADVISORY_INSTRUCTION,
    "general": GENERAL_INSTRUCTION,
}

# ── GENERATION CONFIGS ─────────────────────────────────────────────────
GEN_CONFIG_DEEP = {"temperature": 0.2, "top_p": 0.88, "top_k": 35, "max_output_tokens": 16384}
GEN_CONFIG_FAST = {"temperature": 0.15, "top_p": 0.85, "top_k": 25, "max_output_tokens": 1000}
GEN_CONFIG_CRITIQUE = {"temperature": 0.15, "top_p": 0.85, "top_k": 25, "max_output_tokens": 800}

# =========================================================================
# REFERENCE DATA
# =========================================================================
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

# =========================================================================
# CSS (Base + All 8 Themes)
# =========================================================================
_BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*{font-family:'Inter',sans-serif}
.main .block-container{padding-top:1rem;padding-bottom:2rem;max-width:1200px}
@keyframes heroGradient{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.hero{padding:3rem;border-radius:1.5rem;color:white;position:relative;overflow:hidden;
  background:linear-gradient(-45deg,#059669,#0d9488,#065f46,#047857,#0f766e);
  background-size:300% 300%;animation:heroGradient 12s ease infinite;box-shadow:0 20px 60px rgba(5,150,105,.3)}
.hero::after{content:'⚖';position:absolute;right:3rem;bottom:1rem;font-size:8rem;opacity:.07}
.hero h1{font-size:2.8rem;font-weight:800;margin:0;letter-spacing:-.03em;line-height:1.15}
.hero p{font-size:1.05rem;margin:.75rem 0 0;opacity:.9;font-weight:300;max-width:600px;line-height:1.6}
.hero-badge{display:inline-block;padding:.35rem .85rem;background:rgba(255,255,255,.15);
  border-radius:9999px;font-size:.75rem;font-weight:600;margin-top:1.25rem;backdrop-filter:blur(4px);
  border:1px solid rgba(255,255,255,.2);letter-spacing:.05em;text-transform:uppercase}
.page-header{padding:1.5rem 2rem;border-radius:1.25rem;margin-bottom:1.5rem;color:white;
  background:linear-gradient(135deg,#059669,#0d9488);box-shadow:0 12px 40px rgba(5,150,105,.25)}
.page-header h1{margin:0;font-size:2rem;font-weight:700}.page-header p{margin:.25rem 0 0;opacity:.85;font-size:.9rem}
.custom-card{background:#fff;border:1px solid #e2e8f0;border-radius:1rem;padding:1.5rem;margin-bottom:1rem;
  transition:all .3s;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.custom-card:hover{transform:translateY(-4px);box-shadow:0 12px 36px rgba(0,0,0,.1)}
.stat-card{border-radius:1rem;padding:1.25rem;text-align:center;border:1px solid;transition:all .25s;
  background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.stat-value{font-size:1.75rem;font-weight:700;letter-spacing:-.02em}
.stat-label{font-size:.78rem;margin-top:.3rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#64748b}
.feat-card{background:#fff;border:1px solid #e2e8f0;border-radius:1.25rem;padding:1.75rem 1.25rem;
  text-align:center;transition:all .35s;height:100%;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.feat-card:hover{transform:translateY(-6px);box-shadow:0 16px 48px rgba(5,150,105,.12);border-color:#059669}
.feat-icon{font-size:2.75rem;margin-bottom:.75rem;display:block}
.feat-card h4{margin:0 0 .5rem;font-size:.95rem;font-weight:700;color:#1e293b}
.feat-card p{margin:0;font-size:.82rem;color:#64748b;line-height:1.55}
.value-card{background:linear-gradient(135deg,#f0fdf4,#ecfdf5);border:1px solid #bbf7d0;
  border-radius:1.25rem;padding:2rem 1.5rem;text-align:center;transition:all .3s;height:100%}
.value-card:hover{transform:translateY(-4px);box-shadow:0 12px 36px rgba(5,150,105,.1)}
.value-card .v-icon{font-size:2.5rem;margin-bottom:.75rem;display:block}
.value-card h4{margin:0 0 .5rem;font-size:1rem;font-weight:700;color:#065f46}
.value-card p{margin:0;font-size:.85rem;color:#047857;line-height:1.55}
.badge{display:inline-block;padding:.2rem .65rem;border-radius:9999px;font-size:.7rem;font-weight:600;text-transform:uppercase}
.badge-success{background:#dcfce7;color:#166534}.badge-warning{background:#fef3c7;color:#92400e}
.badge-info{background:#dbeafe;color:#1e40af}.badge-danger{background:#fee2e2;color:#991b1b}
.ambiguity-box{background:linear-gradient(135deg,#fefce8,#fef9c3);border:1px solid #fde047;
  border-left:5px solid #eab308;border-radius:.75rem;padding:1.25rem 1.5rem;margin:1rem 0;font-size:.88rem;line-height:1.7}
.ambiguity-box h5{margin:0 0 .5rem;color:#854d0e;font-size:.9rem;font-weight:700}
.issue-spot-box{background:linear-gradient(135deg,#eff6ff,#dbeafe);border:1px solid #93c5fd;
  border-left:5px solid #3b82f6;border-radius:.75rem;padding:1.25rem 1.5rem;margin:1rem 0;font-size:.88rem;line-height:1.7}
.issue-spot-box h5{margin:0 0 .5rem;color:#1e40af;font-size:.9rem;font-weight:700}
.critique-box{background:linear-gradient(135deg,#faf5ff,#f3e8ff);border:1px solid #d8b4fe;
  border-left:5px solid #8b5cf6;border-radius:.75rem;padding:1.25rem 1.5rem;margin:1rem 0;font-size:.88rem;line-height:1.7}
.critique-box h5{margin:0 0 .5rem;color:#5b21b6;font-size:.9rem;font-weight:700}
.quality-grade{display:inline-block;padding:.3rem .8rem;border-radius:.5rem;font-size:1rem;font-weight:800;margin-left:.5rem}
.grade-a{background:#dcfce7;color:#166534;border:2px solid #22c55e}
.grade-b{background:#dbeafe;color:#1e40af;border:2px solid #3b82f6}
.grade-c{background:#fef3c7;color:#92400e;border:2px solid #f59e0b}
.grade-d{background:#fee2e2;color:#991b1b;border:2px solid #ef4444}
.response-box{background:#f8fafc;border:1px solid #e2e8f0;border-radius:.75rem;padding:1.75rem;
  margin:1rem 0;white-space:pre-wrap;font-family:'Georgia','Times New Roman',serif;line-height:1.9;font-size:.95rem}
.disclaimer{background:#fef3c7;border-left:4px solid #f59e0b;padding:1rem 1.25rem;border-radius:0 .5rem .5rem 0;margin-top:1rem;font-size:.85rem}
.cal-event{padding:1rem 1.25rem;border-radius:.75rem;margin-bottom:.75rem;border-left:4px solid;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.cal-event.urgent{border-color:#ef4444;background:#fee2e2}
.cal-event.warn{border-color:#f59e0b;background:#fef3c7}
.cal-event.ok{border-color:#10b981;background:#f0fdf4}
.tmpl-card{background:#fff;border:1px solid #e2e8f0;border-radius:.75rem;padding:1.25rem;margin-bottom:1rem;transition:all .25s}
.tmpl-card:hover{box-shadow:0 6px 20px rgba(0,0,0,.08);transform:translateY(-2px)}
.tool-card{background:#fff;border:1px solid #e2e8f0;border-radius:1rem;padding:1.25rem;margin-bottom:1rem}
.reasoning-stage{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:.5rem;
  padding:.5rem 1rem;margin:.25rem 0;font-size:.78rem;color:#065f46;font-weight:600}
.pipeline-tracker{background:#f8fafc;border:1px solid #e2e8f0;border-radius:.75rem;padding:1rem;margin:.5rem 0}
.pipeline-step{display:inline-block;padding:.25rem .6rem;border-radius:.35rem;font-size:.7rem;
  font-weight:700;margin-right:.4rem;text-transform:uppercase;letter-spacing:.04em}
.step-done{background:#dcfce7;color:#166534}.step-active{background:#059669;color:white}
.step-pending{background:#f1f5f9;color:#94a3b8}
.app-footer{text-align:center;padding:2rem 1rem;color:#64748b;font-size:.85rem;border-top:1px solid #e2e8f0;margin-top:2rem}
.app-footer a{color:#059669;text-decoration:none;font-weight:500}
#MainMenu{visibility:hidden}footer{visibility:hidden}
.stTabs [data-baseweb="tab-list"]{gap:.25rem;background:transparent;border-bottom:2px solid #e2e8f0}
.stTabs [data-baseweb="tab"]{border-radius:.5rem .5rem 0 0;padding:.65rem 1.15rem;font-weight:600;font-size:.82rem}
@media(max-width:768px){.hero h1{font-size:2rem}.hero p{font-size:.9rem}}
</style>
"""

_THEME_EMERALD = """<style>
.stat-card{background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:#bbf7d0}.stat-card .stat-value{color:#059669}
.stat-card.t-blue{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#bfdbfe}.stat-card.t-blue .stat-value{color:#2563eb}
.stat-card.t-purple{background:linear-gradient(135deg,#faf5ff,#f3e8ff);border-color:#e9d5ff}.stat-card.t-purple .stat-value{color:#7c3aed}
.stat-card.t-amber{background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fde68a}.stat-card.t-amber .stat-value{color:#d97706}
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
.response-box{background:#1e293b!important;border-color:#334155!important;color:#e2e8f0!important}
.disclaimer{background:#451a03!important;color:#fef3c7!important}
.ambiguity-box,.issue-spot-box,.critique-box{background:#1e293b!important;color:#e2e8f0!important}
.app-footer{border-color:#334155!important;color:#94a3b8!important}
</style>"""
_THEME_ROYAL = """<style>.hero{background:linear-gradient(-45deg,#1e3a5f,#1e40af,#0f2557,#2563eb)!important}
.page-header{background:linear-gradient(135deg,#1e3a5f,#1e40af)!important}
.stat-card{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#93c5fd}.stat-card .stat-value{color:#1e40af}
.response-box{background:#f0f5ff;border-color:#bfdbfe}</style>"""
_THEME_CRIMSON = """<style>.hero{background:linear-gradient(-45deg,#7f1d1d,#991b1b,#b91c1c,#dc2626)!important}
.page-header{background:linear-gradient(135deg,#7f1d1d,#991b1b)!important}
.stat-card{background:linear-gradient(135deg,#fef2f2,#fee2e2);border-color:#fecaca}.stat-card .stat-value{color:#991b1b}
.response-box{background:#fef2f2;border-color:#fecaca}</style>"""
_THEME_SUNSET = """<style>.hero{background:linear-gradient(-45deg,#9a3412,#c2410c,#ea580c,#f97316)!important}
.page-header{background:linear-gradient(135deg,#9a3412,#c2410c)!important}
.stat-card{background:linear-gradient(135deg,#fff7ed,#ffedd5);border-color:#ffedd5}.stat-card .stat-value{color:#c2410c}
.response-box{background:#fff7ed;border-color:#ffedd5}</style>"""
_THEME_OBSIDIAN = """<style>.hero{background:linear-gradient(-45deg,#0f172a,#1e293b,#334155,#475569)!important}
.page-header{background:linear-gradient(135deg,#0f172a,#1e293b)!important}
.custom-card,.feat-card,.tmpl-card,.tool-card{background:#1e293b;border-color:#334155;color:#f8fafc}
.stat-card{background:linear-gradient(135deg,#1e293b,#334155);border-color:#475569}.stat-card .stat-value{color:#f8fafc}
.response-box{background:#1e293b;border-color:#334155;color:#e2e8f0}</style>"""
_THEME_NEON = """<style>.hero{background:linear-gradient(-45deg,#4c1d95,#5b21b6,#6d28d9,#7c3aed)!important}
.page-header{background:linear-gradient(135deg,#4c1d95,#5b21b6)!important}
.stat-card{background:linear-gradient(135deg,#f5f3ff,#ddd6fe);border-color:#ddd6fe}.stat-card .stat-value{color:#5b21b6}
.response-box{background:#f5f3ff;border-color:#ddd6fe}</style>"""
_THEME_PACIFIC = """<style>.hero{background:linear-gradient(-45deg,#0c4a6e,#075985,#0ea5e9,#38bdf8)!important}
.page-header{background:linear-gradient(135deg,#0c4a6e,#075985)!important}
.stat-card{background:linear-gradient(135deg,#f0f9ff,#bae6fd);border-color:#bae6fd}.stat-card .stat-value{color:#075985}
.response-box{background:#f0f9ff;border-color:#bae6fd}</style>"""

THEMES = {"🌿 Emerald":_THEME_EMERALD,"🌙 Midnight":_THEME_MIDNIGHT,"👔 Royal Blue":_THEME_ROYAL,
    "❤️ Crimson":_THEME_CRIMSON,"🌅 Sunset":_THEME_SUNSET,"🖤 Obsidian":_THEME_OBSIDIAN,
    "⚡ Neon":_THEME_NEON,"🌊 Pacific":_THEME_PACIFIC}

# =========================================================================
# TEMPLATES
# =========================================================================
@st.cache_data
def get_templates() -> list[dict[str, str]]:
    return [
        {"id":"1","name":"Employment Contract","cat":"Corporate","content":"EMPLOYMENT CONTRACT\n\nThis Employment Contract is made on [DATE] between:\n\n1. [EMPLOYER NAME] (\"the Employer\")\n   Address: [EMPLOYER ADDRESS] | RC: [NUMBER]\n\n2. [EMPLOYEE NAME] (\"the Employee\")\n   Address: [EMPLOYEE ADDRESS]\n\nTERMS:\n\n1. POSITION: [JOB TITLE]\n2. COMMENCEMENT: [START DATE]\n3. PROBATION: [PERIOD] months\n4. SALARY: N[AMOUNT] monthly\n5. HOURS: [HOURS]/week, Mon-Fri\n6. LEAVE: [NUMBER] days annual\n7. TERMINATION: [NOTICE PERIOD] written notice\n8. CONFIDENTIALITY: Employee maintains confidentiality\n9. GOVERNING LAW: Labour Act of Nigeria\n\nSIGNED:\n_______________ _______________\nEmployer        Employee\n"},
        {"id":"2","name":"Tenancy Agreement","cat":"Property","content":"TENANCY AGREEMENT\n\nMade on [DATE] BETWEEN:\n[LANDLORD] of [ADDRESS] (\"Landlord\")\nAND\n[TENANT] of [ADDRESS] (\"Tenant\")\n\n1. PREMISES: [PROPERTY ADDRESS]\n2. TERM: [DURATION] from [START DATE]\n3. RENT: N[AMOUNT] per [PERIOD]\n4. DEPOSIT: N[AMOUNT] refundable\n5. USE: [Residential/Commercial] only\n6. MAINTENANCE: Tenant keeps premises in good condition\n7. ALTERATIONS: None without Landlord's consent\n8. TERMINATION: [NOTICE PERIOD] written notice\n9. LAW: Lagos Tenancy Law (or applicable state law)\n\nSIGNED:\n_______________ _______________\nLandlord        Tenant\n"},
        {"id":"3","name":"Power of Attorney","cat":"Litigation","content":"GENERAL POWER OF ATTORNEY\n\nI, [GRANTOR NAME], of [ADDRESS], appoint [ATTORNEY NAME] of [ADDRESS] as my Attorney to:\n\n1. Demand, sue for, recover and collect all monies due\n2. Sign and execute contracts and documents\n3. Appear before any court or tribunal\n4. Operate bank accounts\n5. Manage properties and collect rents\n6. Execute and register deeds\n\nThis Power remains in force until revoked in writing.\n\nDated: [DATE]\n_______________\n[GRANTOR NAME]\nWITNESS: _______________\n"},
        {"id":"4","name":"Written Address","cat":"Litigation","content":"IN THE [COURT NAME]\nSUIT NO: [NUMBER]\n\n[PLAINTIFF] v. [DEFENDANT]\n\nWRITTEN ADDRESS OF THE [PLAINTIFF/DEFENDANT]\n\n1.0 INTRODUCTION\n2.0 FACTS\n3.0 ISSUES\n4.0 ARGUMENTS\n5.0 CONCLUSION\n\nDated: [DATE]\n_______________\n[COUNSEL]\nFor: [LAW FIRM]\n"},
        {"id":"5","name":"Affidavit","cat":"Litigation","content":"IN THE [COURT NAME]\nSUIT NO: [NUMBER]\n\nAFFIDAVIT IN SUPPORT OF [MOTION]\n\nI, [DEPONENT], make oath:\n1. I am the [Party].\n2. [Fact 1]\n3. [Fact 2]\n4. This Affidavit is made in good faith.\n\n_______________\nDEPONENT\nSworn at [Location] this [DATE]\nBefore: _______________ COMMISSIONER FOR OATHS\n"},
        {"id":"6","name":"Legal Opinion","cat":"Corporate","content":"LEGAL OPINION — PRIVATE & CONFIDENTIAL\n\nTO: [CLIENT] | FROM: [LAW FIRM] | DATE: [DATE]\nRE: [SUBJECT]\n\n1.0 INTRODUCTION\n2.0 FACTS\n3.0 ISSUES\n4.0 LEGAL FRAMEWORK\n5.0 ANALYSIS\n6.0 CONCLUSION\n7.0 CAVEATS\n\n_______________\n[PARTNER]\nFor: [LAW FIRM]\n"},
        {"id":"7","name":"Demand Letter","cat":"Litigation","content":"[LETTERHEAD]\n[DATE]\n\n[RECIPIENT]\n\nRE: DEMAND FOR N[AMOUNT]\nOUR CLIENT: [CLIENT NAME]\n\nWe are Solicitors to [CLIENT].\n\nFacts: [Background]\n\nPay within 7 DAYS or we institute proceedings.\n\nGovern yourself accordingly.\n\n_______________\n[COUNSEL]\nFor: [LAW FIRM]\n"},
        {"id":"8","name":"Board Resolution","cat":"Corporate","content":"BOARD RESOLUTION — [COMPANY] (RC: [NUMBER])\n[VENUE] — [DATE]\n\nPRESENT: [Directors]\nIN ATTENDANCE: [Company Secretary]\n\nRESOLVED:\n1. [Resolution]\n2. Any Director authorized to execute documents.\n3. Company Secretary to file returns with CAC.\n\nCERTIFIED TRUE COPY\n_______________\nCompany Secretary\n"},
    ]

# =========================================================================
# FILE EXTRACTION
# =========================================================================
def _extract_text_from_file(uploaded_file) -> str:
    import io
    name = uploaded_file.name.lower()
    data = uploaded_file.getvalue()
    if name.endswith(".pdf"):
        if not PDF_SUPPORT: raise RuntimeError("Install: pip install pdfplumber")
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages])
    elif name.endswith(".docx"):
        if not DOCX_SUPPORT: raise RuntimeError("Install: pip install python-docx")
        return "\n".join([p.text for p in Document(io.BytesIO(data)).paragraphs if p.text])
    elif name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")
    elif name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(data)).to_string(index=False)
    elif name.endswith(".xlsx"):
        if not XLSX_SUPPORT: raise RuntimeError("Install: pip install openpyxl")
        return pd.read_excel(io.BytesIO(data)).to_string(index=False)
    raise ValueError(f"Unsupported: {name}")

# =========================================================================
# HELPERS
# =========================================================================
def _id() -> str: return uuid.uuid4().hex[:8]
def _cur(a: float) -> str: return f"₦{a:,.2f}"
def _esc(t: str) -> str: return html.escape(str(t))
def _fdate(s: str) -> str:
    try: return datetime.fromisoformat(s).strftime("%B %d, %Y")
    except: return str(s)
def _days(s: str) -> int:
    try: return (datetime.fromisoformat(s).date() - datetime.now().date()).days
    except: return 999
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

# =========================================================================
# SESSION STATE
# =========================================================================
for _k, _v in {
    "api_key":"","api_configured":False,"cases":[],"clients":[],"time_entries":[],
    "invoices":[],"gemini_model":DEFAULT_MODEL,"loaded_template":"","theme":"🌿 Emerald",
    "admin_unlocked":False,"imported_doc":None,
    "last_response":"","research_results":"",
    "issue_spot_result":"","ambiguity_result":"","critique_result":"","quality_grade":"",
    "show_reasoning_chain":True,"enable_self_critique":True,"pipeline_depth":"full",
    "conversation_history":[],"original_query":"",
}.items():
    if _k not in st.session_state: st.session_state[_k] = _v

st.markdown(_BASE_CSS, unsafe_allow_html=True)
st.markdown(THEMES.get(st.session_state.theme, _THEME_EMERALD), unsafe_allow_html=True)

# =========================================================================
# API LAYER
# =========================================================================
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
        if "403" in s: st.error("API key invalid.")
        elif "429" in s: st.error("Rate limit.")
        else: st.error(f"API error: {s}")
        return False

def _auto():
    if st.session_state.api_configured: return
    k = _key()
    if k and len(k) >= 10:
        _cfg(k); st.session_state.update(api_key=k, api_configured=True)
        m = _sec("GEMINI_MODEL") or os.getenv("GEMINI_MODEL","")
        if m: st.session_state.gemini_model = _norm(m)

def _gen(prompt: str, sys: str, gen_cfg: dict | None = None) -> str:
    k = _key()
    if not k: return "⚠️ No API key configured."
    _cfg(k)
    cfg = gen_cfg or GEN_CONFIG_DEEP
    try:
        model = genai.GenerativeModel(_model(), system_instruction=sys)
    except TypeError:
        model = genai.GenerativeModel(_model())
        prompt = f"{sys}\n\n{prompt}"
    for attempt in range(3):
        try:
            return model.generate_content(prompt, generation_config=cfg).text
        except Exception as e:
            if attempt == 2: return f"Error: {e}"
            time.sleep(1.5 * (attempt + 1))
    return "Error: generation failed."

# =========================================================================
# ★★★ ELITE 4-PASS PIPELINE ★★★
# =========================================================================
def _pass1_issue_spot(query: str) -> str:
    return _gen(f"LEGAL SCENARIO:\n\n{query}", ISSUE_SPOTTING_INSTRUCTION, GEN_CONFIG_FAST)

def _pass2_ambiguity(query: str, issues: str) -> str:
    return _gen(
        f"QUERY:\n{query}\n\n━━━\nISSUE SPOTTING RESULTS:\n{issues}\n\n━━━\nNow perform IT DEPENDS analysis.",
        AMBIGUITY_INSTRUCTION, GEN_CONFIG_FAST)

def _pass3_deep_analysis(query: str, task: str, issues: str, ambiguity: str, conv_ctx: str = "") -> str:
    sys = TASK_INSTRUCTIONS.get(task, GENERAL_INSTRUCTION)
    label = TASK_TYPES.get(task, {}).get("label", "General")
    ctx = f"\n═══\nPRIOR CONTEXT:\n{conv_ctx}\n" if conv_ctx else ""
    prompt = (
        f"TASK: {label} | DATE: {datetime.now().strftime('%d %B %Y')}\n"
        f"\n═══ PASS 1 — ISSUE SPOTTING ═══\n{issues}\n"
        f"\n═══ PASS 2 — IT DEPENDS ═══\n{ambiguity}\n"
        f"{ctx}"
        f"\n═══ ORIGINAL QUERY ═══\n{query}\n"
        f"\n═══ INSTRUCTION ═══\n"
        f"1. Address EVERY issue from Pass 1 (including hidden issues).\n"
        f"2. Address each 'It Depends' factor conditionally.\n"
        f"3. Apply your FULL reasoning framework — every stage.\n"
        f"4. For every principle: GENERAL RULE → EXCEPTIONS → MINORITY VIEW.\n"
        f"5. Devil's Advocate must be genuinely STRONG, not token.\n"
        f"6. This is a Senior Partner's analysis for a practicing lawyer.\n"
    )
    return _gen(prompt, sys, GEN_CONFIG_DEEP)

def _pass4_critique(query: str, analysis: str, issues: str) -> str:
    return _gen(
        f"QUERY:\n{query}\n\n━━━\nISSUES TO ADDRESS:\n{issues}\n\n━━━\nANALYSIS TO CRITIQUE:\n{analysis}",
        SELF_CRITIQUE_INSTRUCTION, GEN_CONFIG_CRITIQUE)

def _extract_grade(text: str) -> str:
    m = re.search(r'OVERALL GRADE:\s*([A-D])', text, re.IGNORECASE)
    return m.group(1).upper() if m else "B"

def run_pipeline(query: str, task: str) -> dict[str, str]:
    r = {"issue_spot":"","ambiguity":"","main":"","critique":"","grade":""}
    if not st.session_state.api_configured:
        r["main"] = "⚠️ Configure API key first."; return r
    depth = st.session_state.pipeline_depth
    ctx = st.session_state.get("conversation_context_str", "")

    if depth in ("full", "fast"):
        r["issue_spot"] = _pass1_issue_spot(query)
        r["ambiguity"] = _pass2_ambiguity(query, r["issue_spot"])

    r["main"] = _pass3_deep_analysis(
        query, task,
        r["issue_spot"] or "No pre-analysis.",
        r["ambiguity"] or "No ambiguity analysis.",
        ctx)

    if depth == "full" and st.session_state.enable_self_critique:
        if not r["main"].startswith(("Error","⚠️")):
            r["critique"] = _pass4_critique(query, r["main"], r["issue_spot"])
            r["grade"] = _extract_grade(r["critique"])
    return r

def run_followup(orig_q: str, orig_resp: str, followup: str, task: str) -> str:
    if not st.session_state.api_configured: return "⚠️ Configure API key first."
    return _gen(
        f"═══ ORIGINAL QUERY ═══\n{orig_q}\n\n═══ PREVIOUS ANALYSIS ═══\n{orig_resp}\n\n"
        f"═══ FOLLOW-UP ═══\n{followup}\n\nAddress with same depth. Don't repeat — focus on what's new.",
        FOLLOWUP_INSTRUCTION, GEN_CONFIG_DEEP)

def ai_research(q: str) -> str:
    if not st.session_state.api_configured: return "⚠️ Configure API key first."
    issues = _pass1_issue_spot(q)
    return _gen(
        f"ISSUE SCAN:\n{issues}\n\n━━━\nRESEARCH QUESTION:\n{q}\n\n"
        f"Comprehensive memo. All stages. GENERAL RULE → EXCEPTIONS → MINORITY VIEW.\n"
        f"Mark uncertain citations: [Citation to be verified].",
        RESEARCH_INSTRUCTION, GEN_CONFIG_DEEP)

# =========================================================================
# DATA CRUD
# =========================================================================
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
    # =========================================================================
# SIDEBAR
# =========================================================================
def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚖️ LexiAssist v6.0")
        st.caption("Elite 4-Pass Legal Reasoning Engine")
        st.divider()
        c1, c2 = st.columns(2)
        with c1: st.metric("Active", len([c for c in st.session_state.cases if c.get("status")=="Active"]))
        with c2: st.metric("Hearings", len(_hearings()))
        st.divider()
        st.markdown("### 🎨 Theme")
        th = st.selectbox("Theme", list(THEMES.keys()),
            index=list(THEMES.keys()).index(st.session_state.theme) if st.session_state.theme in THEMES else 0,
            label_visibility="collapsed")
        if th != st.session_state.theme: st.session_state.theme = th; st.rerun()
        st.divider()
        st.markdown("### 🤖 AI Engine")
        if st.session_state.api_configured:
            st.success(f"✅ Connected · `{_model()}`")
            st.caption("🧠 Elite 4-Pass Pipeline Active")
        else: st.warning("⚠️ Not connected")
        idx = SUPPORTED_MODELS.index(_model()) if _model() in SUPPORTED_MODELS else 0
        sel = st.selectbox("Model", SUPPORTED_MODELS, index=idx)
        if _norm(sel) != st.session_state.gemini_model:
            st.session_state.gemini_model = _norm(sel); st.session_state.api_configured = False; st.rerun()

        st.divider()
        st.markdown("### 🧠 Pipeline Settings")
        st.session_state.pipeline_depth = st.radio("Depth", ["full","fast","analysis_only"],
            index=["full","fast","analysis_only"].index(st.session_state.pipeline_depth),
            format_func=lambda x: {"full":"🔬 Full (4-Pass)","fast":"⚡ Fast (3-Pass)","analysis_only":"📝 Analysis Only"}[x])
        st.session_state.show_reasoning_chain = st.toggle("Show Pre-Analysis", value=st.session_state.show_reasoning_chain)
        st.session_state.enable_self_critique = st.toggle("Quality Gate", value=st.session_state.enable_self_critique)

        has_sec = bool(_sec("GEMINI_API_KEY")); adm_pw = _sec("ADMIN_PASSWORD"); show = False
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
            ki = st.text_input("API Key", type="password", value=st.session_state.api_key,
                label_visibility="collapsed", placeholder="Gemini API key…")
            if st.button("Connect", type="primary", use_container_width=True):
                if ki and len(ki.strip()) >= 10:
                    with st.spinner("Connecting…"):
                        if api_connect(ki.strip(), st.session_state.gemini_model): st.success("✅"); st.rerun()
                else: st.warning("Enter valid key.")
            st.caption("[Get key →](https://aistudio.google.com/app/apikey)")

        st.divider()
        st.markdown("### 💾 Data")
        if st.button("📥 Export JSON", use_container_width=True):
            st.download_button("Download",
                json.dumps({"cases":st.session_state.cases,"clients":st.session_state.clients,
                    "time_entries":st.session_state.time_entries,"invoices":st.session_state.invoices},indent=2),
                f"lexiassist_{datetime.now():%Y%m%d}.json","application/json")
        up = st.file_uploader("📤 Import", type=["json","pdf","docx","txt","csv","xlsx"])
        if up:
            try:
                ext = up.name.split(".")[-1].lower()
                if ext == "json":
                    data = json.load(up)
                    for k in ["cases","clients","time_entries","invoices"]: st.session_state[k] = data.get(k,[])
                    st.success("✅ Imported!"); st.rerun()
                else:
                    text = _extract_text_from_file(up)
                    st.session_state.imported_doc = {"name":up.name,"type":ext,"size":len(up.getvalue()),
                        "preview":text[:500]+("…" if len(text)>500 else ""),"full_text":text}
                    st.success(f"✅ {up.name} loaded → AI Assistant"); st.rerun()
            except Exception as e: st.error(f"❌ {e}")
        st.divider()
        st.caption("**LexiAssist v6.0** © 2026\n🧠 Elite Pipeline · 🤖 Gemini · 🎈 Streamlit")


# =========================================================================
# PAGE: HOME
# =========================================================================
def render_landing():
    api_status = "🟢 Elite AI Ready" if st.session_state.api_configured else "🔴 Configure API in Sidebar"
    st.markdown(f"""<div class="hero"><div class="hero-badge">{api_status}</div>
    <h1>Elite Legal Reasoning<br>for Nigerian Lawyers</h1>
    <p>4-pass pipeline: Issue Spotting → Ambiguity → Deep CREAC → Self-Critique.
    Every response is stress-tested before it reaches you.</p>
    <div class="hero-badge" style="margin-top:.75rem">🇳🇬 Nigerian Law · 4-Pass · Hidden Issues · Equity vs Law · Quality Graded</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("")
    active = len([c for c in st.session_state.cases if c.get("status")=="Active"])
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f'<div class="stat-card"><div class="stat-value">{active}</div><div class="stat-label">📁 Active</div></div>',unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-card t-blue"><div class="stat-value">{len(st.session_state.clients)}</div><div class="stat-label">👥 Clients</div></div>',unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="stat-card t-purple"><div class="stat-value">{_esc(_cur(_tb()))}</div><div class="stat-label">💰 Billable</div></div>',unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="stat-card t-amber"><div class="stat-value">{len(_hearings())}</div><div class="stat-label">📅 Hearings</div></div>',unsafe_allow_html=True)
    st.markdown("")
    st.markdown("#### Key Capabilities")
    feats = [
        ("🧠","4-Pass Pipeline","Issue spot → Ambiguity → CREAC → Critique. No shallow answers."),
        ("🔍","Hidden Issues","Finds issues you didn't ask about — the ones that lose cases."),
        ("⚖️","Equity vs Law","Every analysis: strict law, equity, practical enforceability."),
        ("👹","Devil's Advocate","Strongest opposing argument before you see it in court."),
        ("📚","Deep Research","Statutes, case law, conflicting authorities, minority views."),
        ("💬","Follow-Up Drill","Context-aware follow-ups — go deeper on any issue."),
        ("✅","Quality Grading","Separate quality gate grades every analysis A-D."),
        ("🇳🇬","Nigerian Tools","Limitation periods, interest calc, court hierarchy, maxims."),
    ]
    cols = st.columns(4)
    for i,(ic,t,d) in enumerate(feats):
        with cols[i%4]:
            st.markdown(f'<div class="feat-card"><span class="feat-icon">{ic}</span><h4>{t}</h4><p>{d}</p></div>',unsafe_allow_html=True)

    hearings = _hearings(5)
    if hearings:
        st.markdown("#### 📅 Upcoming Hearings")
        for h in hearings:
            d = _days(h["date"])
            u = "urgent" if d<=3 else ("warn" if d<=7 else "ok")
            b = "danger" if d<=3 else ("warning" if d<=7 else "success")
            st.markdown(f'<div class="cal-event {u}"><strong>{_esc(h["title"])}</strong> · {_esc(h["suit"])}<br>{_esc(_fdate(h["date"]))} <span class="badge badge-{b}">{_esc(_rel(h["date"]))}</span></div>',unsafe_allow_html=True)


# =========================================================================
# PAGE: AI ASSISTANT — ELITE ENGINE
# =========================================================================
def render_ai():
    st.markdown('<div class="page-header"><h1>🧠 AI Legal Assistant — Elite Engine</h1>'
        '<p>4-Pass: Issue Spot → Ambiguity → Deep Analysis → Quality Critique</p></div>',unsafe_allow_html=True)

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect API key in sidebar.")

    with st.expander("ℹ️ How the 4-Pass Pipeline Works", expanded=False):
        st.markdown("""
| Pass | Purpose | Fed Into |
|---|---|---|
| **1. Issue Spotting** | All issues including hidden ones a junior would miss | Pass 2, 3 |
| **2. Ambiguity** | "IT DEPENDS" variables, deadline risks, evidence gaps | Pass 3 |
| **3. Deep Analysis** | Full CREAC per issue with Pass 1+2 as context | Pass 4 |
| **4. Self-Critique** | Catches shallow reasoning, missed issues, weak arguments | You |

**Why deeper:** Pass 3 receives Passes 1+2 as structured context with instructions to address EVERY issue found. Pass 4 catches what slipped through.
        """)

    if st.session_state.imported_doc:
        with st.expander("📄 Imported Document", expanded=True):
            doc = st.session_state.imported_doc
            st.caption(f"`{doc['name']}` · {doc['type'].upper()} · {doc['size']:,}B")
            st.text_area("Preview", doc["preview"], height=120, disabled=True)
            c1,c2 = st.columns(2)
            with c1:
                if st.button("✅ Load to Editor",type="primary",use_container_width=True):
                    st.session_state.loaded_template = doc["full_text"]; st.rerun()
            with c2:
                if st.button("🗑️ Dismiss",use_container_width=True):
                    st.session_state.imported_doc = None; st.rerun()

    # Task selector
    task_keys = list(TASK_TYPES.keys())
    chosen_task = st.selectbox("🎯 Task Type", task_keys, index=task_keys.index("analysis"),
        format_func=lambda k: f"{TASK_TYPES[k]['icon']} {TASK_TYPES[k]['label']} — {TASK_TYPES[k]['desc']}",
        key="task_type_selectbox")

    fw = {"analysis":"🔍 Enhanced CREAC — hidden issues, equity tri-layer, aggressive devil's advocate",
          "drafting":"📄 Risk-Aware Drafting — hidden clauses, alternatives, validity checklist",
          "research":"📚 Jurisprudential — conflicting authorities, minority views, evolution",
          "procedure":"📋 Procedural — jurisdiction traps, interlocutory strategy, enforcement",
          "interpretation":"⚖️ Statutory — literal/golden/mischief, aids, constitutional validity",
          "advisory":"🎯 Strategic Advisory — options matrix, risk register, engagement terms",
          "general":"💬 Deep General — hidden sub-questions, counter-position, depth check"}
    st.markdown(f'<div class="reasoning-stage">⚙️ Framework: {fw.get(chosen_task,"")}</div>',unsafe_allow_html=True)

    # Template loader
    with st.expander("📋 Load Template", expanded=False):
        templates = get_templates()
        chosen_tmpl = st.selectbox("Template", [t["name"] for t in templates], key="tmpl_chooser")
        if st.button("✅ Load", type="primary", use_container_width=True):
            for t in templates:
                if t["name"] == chosen_tmpl: st.session_state.loaded_template = t["content"]; st.rerun()

    st.markdown("---")

    # Input
    prefill = st.session_state.pop("loaded_template", "")
    user_input = st.text_area("📝 Your Legal Query", value=prefill, height=250,
        placeholder="Be specific for deeper analysis. Include dates, amounts, parties, and what happened.")

    if user_input:
        wc = len(user_input.split())
        depth_hint = "✅ Good detail" if wc > 40 else "⚠️ Add more facts for deeper analysis"
        st.caption(f"📝 {wc} words — {depth_hint}")

    c1,c2,c3 = st.columns([3,1,1])
    with c1:
        generate = st.button("🧠 Run Elite Analysis", type="primary", use_container_width=True,
            disabled=not st.session_state.api_configured)
    with c2:
        spot_only = st.button("🔍 Issue Spot Only", use_container_width=True,
            disabled=not st.session_state.api_configured)
    with c3:
        clear = st.button("🗑️ Clear All", use_container_width=True)

    # ── ISSUE SPOT ONLY ────────────────────────────────────────────────
    if spot_only and user_input.strip():
        with st.spinner("🔍 Pass 1: Spotting issues…"):
            st.session_state.issue_spot_result = _pass1_issue_spot(user_input)
            st.session_state.last_response = ""
            st.session_state.ambiguity_result = ""
            st.session_state.critique_result = ""

    # ── FULL PIPELINE ──────────────────────────────────────────────────
    if generate and user_input.strip():
        depth = st.session_state.pipeline_depth
        pipeline_steps = []

        if depth in ("full","fast"):
            pipeline_steps.append(("🔍 Pass 1: Issue Spotting…", "issue_spot"))
            pipeline_steps.append(("⚠️ Pass 2: Ambiguity Detection…", "ambiguity"))
        pipeline_steps.append(("🧠 Pass 3: Deep Analysis (this may take 20-40s)…", "main"))
        if depth == "full" and st.session_state.enable_self_critique:
            pipeline_steps.append(("✅ Pass 4: Quality Critique…", "critique"))

        results = {}
        progress = st.progress(0)

        for i, (label, key) in enumerate(pipeline_steps):
            progress.progress((i) / len(pipeline_steps), text=label)
            with st.spinner(label):
                if key == "issue_spot":
                    results["issue_spot"] = _pass1_issue_spot(user_input)
                elif key == "ambiguity":
                    results["ambiguity"] = _pass2_ambiguity(user_input, results.get("issue_spot",""))
                elif key == "main":
                    results["main"] = _pass3_deep_analysis(
                        user_input, chosen_task,
                        results.get("issue_spot","No pre-analysis."),
                        results.get("ambiguity","No ambiguity analysis."),
                        st.session_state.get("conversation_context_str",""))
                elif key == "critique":
                    if not results.get("main","").startswith(("Error","⚠️")):
                        results["critique"] = _pass4_critique(user_input, results["main"], results.get("issue_spot",""))

        progress.progress(1.0, text="✅ Pipeline complete!")
        time.sleep(0.5)
        progress.empty()

        st.session_state.issue_spot_result = results.get("issue_spot","")
        st.session_state.ambiguity_result = results.get("ambiguity","")
        st.session_state.last_response = results.get("main","")
        st.session_state.critique_result = results.get("critique","")
        st.session_state.quality_grade = _extract_grade(results.get("critique","")) if results.get("critique") else ""
        st.session_state.original_query = user_input

        # Update conversation context for follow-ups
        st.session_state.conversation_history.append({
            "role":"user","content":user_input,"timestamp":datetime.now().isoformat()})
        if st.session_state.last_response:
            st.session_state.conversation_history.append({
                "role":"assistant","content":st.session_state.last_response[:2000],
                "timestamp":datetime.now().isoformat()})
            st.session_state.conversation_context_str = (
                f"Previous query: {user_input[:500]}\nPrevious analysis summary: {st.session_state.last_response[:1500]}")

    if clear:
        for k in ["last_response","issue_spot_result","ambiguity_result","critique_result",
                   "quality_grade","original_query","conversation_history","conversation_context_str"]:
            st.session_state[k] = "" if isinstance(st.session_state.get(k), str) else []
        st.rerun()

    # ── DISPLAY RESULTS ────────────────────────────────────────────────

    # Pass 1: Issue Spotting
    if st.session_state.issue_spot_result and st.session_state.show_reasoning_chain:
        with st.expander("🔍 Pass 1 — Issue Spotting Results", expanded=False):
            st.markdown(f'<div class="issue-spot-box"><h5>🔍 ISSUE DECOMPOSITION (Including Hidden Issues)</h5>'
                f'{_esc(st.session_state.issue_spot_result)}</div>',unsafe_allow_html=True)

    # Pass 2: Ambiguity
    if st.session_state.ambiguity_result and st.session_state.show_reasoning_chain:
        with st.expander("⚠️ Pass 2 — 'It Depends' Factors", expanded=False):
            st.markdown(f'<div class="ambiguity-box"><h5>⚠️ CRITICAL VARIABLES & DEADLINE RISKS</h5>'
                f'{_esc(st.session_state.ambiguity_result)}</div>',unsafe_allow_html=True)

    # Pass 3: Main Analysis
    if st.session_state.last_response:
        st.markdown("---")
        text = st.session_state.last_response
        wc = len(text.split())
        depth = "🟢 Comprehensive" if wc>800 else ("🟡 Moderate" if wc>400 else "🔴 Brief")

        # Header with quality grade
        grade = st.session_state.quality_grade
        grade_html = ""
        if grade:
            gc = {"A":"grade-a","B":"grade-b","C":"grade-c","D":"grade-d"}.get(grade,"grade-b")
            grade_html = f' <span class="quality-grade {gc}">Grade: {grade}</span>'

        st.markdown(f"#### 📄 Senior Lawyer Analysis{grade_html}", unsafe_allow_html=True)
        st.caption(f"📝 **{wc:,} words** · Depth: {depth} · Pipeline: {st.session_state.pipeline_depth}")

        ec1,ec2,ec3 = st.columns([1,1,4])
        with ec1:
            st.download_button("📥 .txt", text, f"LexiAssist_{datetime.now():%Y%m%d_%H%M}.txt","text/plain")
        with ec2:
            html_doc = (f"<!DOCTYPE html><html><head><meta charset='UTF-8'><title>LexiAssist Analysis</title>"
                f"<style>body{{font-family:Georgia,serif;line-height:1.9;max-width:850px;margin:40px auto;padding:20px}}"
                f"h1{{color:#059669;border-bottom:3px solid #059669;padding-bottom:12px}}"
                f".c{{white-space:pre-wrap;font-size:15px}}"
                f".d{{background:#fef3c7;border-left:4px solid #f59e0b;padding:16px;margin-top:32px;border-radius:0 8px 8px 0}}"
                f"</style></head><body><h1>⚖️ LexiAssist Analysis</h1>"
                f"<div class='c'>{_esc(text)}</div>"
                f"<div class='d'><b>Disclaimer:</b> For reference only. Verify citations. Apply professional judgment.</div>"
                f"</body></html>")
            st.download_button("📥 .html", html_doc, f"LexiAssist_{datetime.now():%Y%m%d_%H%M}.html","text/html")

        st.markdown(f'<div class="response-box">{_esc(text)}</div>',unsafe_allow_html=True)

        st.markdown('<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated analysis for professional reference. '
            'Not legal advice. Verify all citations independently. Apply professional judgment.</div>',unsafe_allow_html=True)

    # Pass 4: Self-Critique
    if st.session_state.critique_result and st.session_state.show_reasoning_chain:
        with st.expander("✅ Pass 4 — Quality Critique", expanded=True):
            st.markdown(f'<div class="critique-box"><h5>✅ QUALITY GATE — SELF-CRITIQUE</h5>'
                f'{_esc(st.session_state.critique_result)}</div>',unsafe_allow_html=True)

    # ── FOLLOW-UP ──────────────────────────────────────────────────────
    if st.session_state.last_response:
        st.markdown("---")
        st.markdown("#### 💬 Follow-Up Question")
        st.caption("Ask a follow-up that carries full context from the analysis above.")
        followup = st.text_input("Your follow-up question", placeholder="e.g. 'Go deeper on the limitation issue' or 'What if the contract had an arbitration clause?'",
            key="followup_input")
        if st.button("💬 Submit Follow-Up", type="primary", disabled=not followup):
            with st.spinner("🧠 Analyzing follow-up with full context…"):
                result = run_followup(
                    st.session_state.original_query,
                    st.session_state.last_response,
                    followup,
                    st.session_state.get("task_type_selectbox","analysis"))
                if not result.startswith(("Error","⚠️")):
                    st.session_state.last_response = result
                    st.session_state.conversation_context_str = (
                        f"Original: {st.session_state.original_query[:300]}\n"
                        f"Follow-up: {followup}\nLatest analysis: {result[:1500]}")
                    st.rerun()
                else:
                    st.error(result)


# =========================================================================
# PAGE: RESEARCH
# =========================================================================
def render_research():
    st.markdown('<div class="page-header"><h1>📚 Legal Research</h1>'
        '<p>Issue-aware research memos · Statutes · Case law · Conflicting authorities</p></div>',unsafe_allow_html=True)
    q = st.text_input("🔍 Research Query", placeholder="e.g. 'employer liability for workplace injuries — statutes, cases, procedure'")
    rc1,rc2 = st.columns([3,1])
    with rc1: go = st.button("📚 Run Research", type="primary", use_container_width=True, disabled=not st.session_state.api_configured)
    with rc2: clr = st.button("🗑️ Clear", use_container_width=True, key="rclr")
    if go and q.strip():
        with st.spinner("📚 Researching (20-40s)…"):
            st.session_state.research_results = ai_research(q)
    if clr: st.session_state.research_results = ""; st.rerun()
    if st.session_state.research_results:
        st.markdown("---")
        wc = len(st.session_state.research_results.split())
        st.caption(f"📝 {wc:,} words")
        st.download_button("📥 Export", st.session_state.research_results, f"Research_{datetime.now():%Y%m%d}.txt","text/plain")
        st.markdown(f'<div class="response-box">{_esc(st.session_state.research_results)}</div>',unsafe_allow_html=True)


# =========================================================================
# PAGE: CASES
# =========================================================================
def render_cases():
    st.markdown('<div class="page-header"><h1>📁 Case Management</h1><p>Track suits, hearings, progress</p></div>',unsafe_allow_html=True)
    search_q = st.text_input("🔍 Search", placeholder="Title, suit number, court, notes…")
    filt = st.selectbox("Status", ["All"]+CASE_STATUSES, key="cfilt")
    cases = st.session_state.cases
    if filt != "All": cases = [c for c in cases if c.get("status")==filt]
    if search_q: cases = [c for c in cases if search_q.lower() in json.dumps(c).lower()]

    with st.expander("➕ Add Case", expanded=not bool(st.session_state.cases)):
        with st.form("cf"):
            a,b = st.columns(2)
            with a:
                title = st.text_input("Title *"); suit = st.text_input("Suit No *"); court = st.text_input("Court")
            with b:
                nh = st.date_input("Next Hearing"); status = st.selectbox("Status", CASE_STATUSES)
                cn = ["—"]+[c["name"] for c in st.session_state.clients]
                ci = st.selectbox("Client", range(len(cn)), format_func=lambda i: cn[i])
            notes = st.text_area("Notes")
            if st.form_submit_button("Save", type="primary"):
                if title.strip() and suit.strip():
                    cid = st.session_state.clients[ci-1]["id"] if ci>0 else None
                    add_case({"title":title.strip(),"suit_no":suit.strip(),"court":court.strip(),
                        "next_hearing":nh.isoformat() if nh else None,"status":status,"client_id":cid,"notes":notes.strip()})
                    st.success("✅ Added!"); st.rerun()
                else: st.error("Title and Suit No required.")

    if not cases: st.info("No cases match."); return
    for case in cases:
        bc = {"Active":"success","Pending":"warning","Completed":"info"}.get(case.get("status",""),"info")
        hh = f"<p>📅 {_esc(_fdate(case['next_hearing']))} <span class='badge badge-info'>{_esc(_rel(case['next_hearing']))}</span></p>" if case.get("next_hearing") else ""
        a,b = st.columns([5,1])
        with a:
            st.markdown(f'<div class="custom-card"><h4>{_esc(case["title"])} <span class="badge badge-{bc}">{_esc(case.get("status",""))}</span></h4>'
                f'<p>⚖️ {_esc(case.get("suit_no",""))} · 🏛️ {_esc(case.get("court",""))} · 👤 {_esc(client_name(case.get("client_id","")))}</p>{hh}</div>',unsafe_allow_html=True)
        with b:
            ns = st.selectbox("Status",CASE_STATUSES,index=CASE_STATUSES.index(case["status"]) if case.get("status") in CASE_STATUSES else 0,key=f"s{case['id']}",label_visibility="collapsed")
            if ns != case.get("status"): upd_case(case["id"],{"status":ns}); st.rerun()
            if st.button("🗑️",key=f"d{case['id']}"): del_case(case["id"]); st.rerun()


# =========================================================================
# PAGE: CALENDAR
# =========================================================================
def render_calendar():
    st.markdown('<div class="page-header"><h1>📅 Court Calendar</h1><p>Upcoming hearings</p></div>',unsafe_allow_html=True)
    hearings = _hearings()
    if not hearings: st.info("No upcoming hearings."); return
    for h in hearings:
        d = _days(h["date"]); u = "urgent" if d<=3 else ("warn" if d<=7 else "ok")
        b = "danger" if d<=3 else ("warning" if d<=7 else "success")
        st.markdown(f'<div class="cal-event {u}"><h4>{_esc(h["title"])}</h4><p>⚖️ {_esc(h["suit"])} · 🏛️ {_esc(h["court"])}</p>'
            f'<p>📅 {_esc(_fdate(h["date"]))} <span class="badge badge-{b}">{_esc(_rel(h["date"]))}</span></p></div>',unsafe_allow_html=True)
    df = pd.DataFrame([{"Case":h["title"],"Days":max(_days(h["date"]),0),"Date":_fdate(h["date"])} for h in hearings])
    fig = px.bar(df,x="Days",y="Case",orientation="h",text="Date",color="Days",
        color_continuous_scale=["#ef4444","#f59e0b","#10b981"],title="Days Until Hearing")
    fig.update_layout(yaxis={"categoryorder":"total ascending"},showlegend=False,height=400)
    st.plotly_chart(fig, use_container_width=True)


# =========================================================================
# PAGE: TEMPLATES
# =========================================================================
def render_templates():
    st.markdown('<div class="page-header"><h1>📋 Templates</h1><p>Professional Nigerian legal templates</p></div>',unsafe_allow_html=True)
    templates = get_templates()
    cats = sorted({t["cat"] for t in templates})
    sel = st.selectbox("Category", ["All"]+cats, key="tcat")
    vis = templates if sel=="All" else [t for t in templates if t["cat"]==sel]
    cols = st.columns(2)
    for i,t in enumerate(vis):
        with cols[i%2]:
            st.markdown(f'<div class="tmpl-card"><h4>📄 {_esc(t["name"])}</h4><span class="badge badge-success">{_esc(t["cat"])}</span></div>',unsafe_allow_html=True)
            a,b = st.columns(2)
            with a:
                if st.button("📋 Load",key=f"u{t['id']}",use_container_width=True):
                    st.session_state.loaded_template = t["content"]; st.success("✅"); st.rerun()
            with b:
                if st.button("👁️ View",key=f"p{t['id']}",use_container_width=True): st.session_state["pv"] = t
    pv = st.session_state.get("pv")
    if pv:
        st.markdown("---"); st.markdown(f"### {pv['name']}"); st.code(pv["content"],language=None)
        if st.button("Close"): del st.session_state["pv"]; st.rerun()


# =========================================================================
# PAGE: CLIENTS
# =========================================================================
def render_clients():
    st.markdown('<div class="page-header"><h1>👥 Clients</h1><p>Manage clients, cases, billing</p></div>',unsafe_allow_html=True)
    search_q = st.text_input("🔍 Search", placeholder="Name, email, type…")
    with st.expander("➕ Add Client", expanded=not bool(st.session_state.clients)):
        with st.form("clf"):
            a,b = st.columns(2)
            with a: name=st.text_input("Name *"); email=st.text_input("Email"); phone=st.text_input("Phone")
            with b: ct=st.selectbox("Type",CLIENT_TYPES); addr=st.text_input("Address"); notes=st.text_area("Notes")
            if st.form_submit_button("Save",type="primary"):
                if name.strip():
                    add_client({"name":name.strip(),"email":email.strip(),"phone":phone.strip(),"type":ct,"address":addr.strip(),"notes":notes.strip()})
                    st.success("✅"); st.rerun()
                else: st.error("Name required.")
    clients = st.session_state.clients
    if search_q: clients = [c for c in clients if search_q.lower() in json.dumps(c).lower()]
    if not clients: st.info("No clients."); return
    cols = st.columns(2)
    for i,cl in enumerate(clients):
        with cols[i%2]:
            cc,cb = _cc(cl["id"]),_cb(cl["id"])
            st.markdown(f'<div class="custom-card"><h4>{_esc(cl["name"])} <span class="badge badge-info">{_esc(cl.get("type",""))}</span></h4>'
                f'<div style="display:flex;justify-content:space-around;text-align:center;margin-top:.5rem">'
                f'<div><div style="font-size:1.5rem;font-weight:700;color:#059669">{cc}</div><div style="font-size:.7rem;color:#64748b">CASES</div></div>'
                f'<div><div style="font-size:1.5rem;font-weight:700;color:#7c3aed">{_esc(_cur(cb))}</div><div style="font-size:.7rem;color:#64748b">BILLABLE</div></div>'
                f'</div></div>',unsafe_allow_html=True)
            a,b = st.columns(2)
            with a:
                if cb>0 and st.button("📄 Invoice",key=f"iv{cl['id']}",use_container_width=True):
                    inv = make_invoice(cl["id"])
                    if inv: st.success(f"✅ {inv['invoice_no']}"); st.rerun()
            with b:
                if st.button("🗑️",key=f"dc{cl['id']}",use_container_width=True): del_client(cl["id"]); st.rerun()


# =========================================================================
# PAGE: BILLING
# =========================================================================
def render_billing():
    st.markdown('<div class="page-header"><h1>💰 Billing</h1><p>Time tracking & invoicing</p></div>',unsafe_allow_html=True)
    s1,s2,s3 = st.columns(3)
    with s1: st.markdown(f'<div class="stat-card"><div class="stat-value">{_esc(_cur(_tb()))}</div><div class="stat-label">💰 Total</div></div>',unsafe_allow_html=True)
    with s2: st.markdown(f'<div class="stat-card t-blue"><div class="stat-value">{_th():.1f}h</div><div class="stat-label">⏱️ Hours</div></div>',unsafe_allow_html=True)
    with s3: st.markdown(f'<div class="stat-card t-purple"><div class="stat-value">{len(st.session_state.invoices)}</div><div class="stat-label">📄 Invoices</div></div>',unsafe_allow_html=True)

    with st.expander("⏱️ Log Time", expanded=False):
        with st.form("tf"):
            a,b = st.columns(2)
            with a:
                cn=["—"]+[c["name"] for c in st.session_state.clients]
                ci=st.selectbox("Client *",range(len(cn)),format_func=lambda i:cn[i])
                ed=st.date_input("Date",datetime.now())
            with b:
                hrs=st.number_input("Hours *",0.25,step=0.25,value=1.0)
                rate=st.number_input("Rate (₦) *",0,value=50000,step=5000)
                st.markdown(f"**Total: {_cur(hrs*rate)}**")
            desc=st.text_area("Description *")
            if st.form_submit_button("Save",type="primary"):
                if ci>0 and desc.strip():
                    add_entry({"client_id":st.session_state.clients[ci-1]["id"],"case_id":None,
                        "date":ed.isoformat(),"hours":hrs,"rate":rate,"description":desc.strip()})
                    st.success("✅"); st.rerun()
                else: st.error("Select client, add description.")

    if st.session_state.time_entries:
        rows=[{"Date":_fdate(e["date"]),"Client":client_name(e.get("client_id","")),"Desc":e["description"][:60],
            "Hours":f"{e['hours']}h","Rate":_cur(e["rate"]),"Amount":_cur(e["amount"]),"ID":e["id"]}
            for e in reversed(st.session_state.time_entries)]
        st.dataframe(pd.DataFrame(rows).drop(columns=["ID"]),use_container_width=True,hide_index=True)

    if st.session_state.invoices:
        st.markdown("#### 📄 Invoices")
        for inv in reversed(st.session_state.invoices):
            with st.expander(f"📄 {inv['invoice_no']} — {inv['client_name']} — {_cur(inv['total'])}"):
                lines=[f"INVOICE {inv['invoice_no']}",f"Date: {_fdate(inv['date'])}",f"Client: {inv['client_name']}",""]
                for i,e in enumerate(inv["entries"],1):
                    lines.append(f"{i}. {_fdate(e['date'])} — {e['description']} — {e['hours']}h × {_cur(e['rate'])} = {_cur(e['amount'])}")
                lines += ["",f"TOTAL: {_cur(inv['total'])}"]
                st.download_button("📥 Download","\n".join(lines),f"{inv['invoice_no']}.txt","text/plain",key=f"dl{inv['id']}")


# =========================================================================
# PAGE: TOOLS
# =========================================================================
def render_tools():
    st.markdown('<div class="page-header"><h1>🇳🇬 Legal Tools</h1><p>References, calculators, maxims</p></div>',unsafe_allow_html=True)
    tabs = st.tabs(["⏱️ Limitation","💹 Interest","🏛️ Courts","📖 Maxims"])
    with tabs[0]:
        s = st.text_input("Search","",placeholder="e.g. contract, land…")
        data = [l for l in LIMITATION_PERIODS if s.lower() in l["cause"].lower()] if s else LIMITATION_PERIODS
        if data: st.dataframe(pd.DataFrame(data).rename(columns={"cause":"Cause","period":"Period","authority":"Authority"}),use_container_width=True,hide_index=True)
    with tabs[1]:
        with st.form("ic"):
            a,b = st.columns(2)
            with a: p=st.number_input("Principal (₦)",0.0,value=1e6,step=5e4); r=st.number_input("Rate (%)",0.0,value=10.0)
            with b: m=st.number_input("Months",1,value=12); ct=st.selectbox("Type",["Simple","Compound"])
            calc = st.form_submit_button("Calculate",type="primary")
        if calc:
            interest = p*(r/100)*(m/12) if ct=="Simple" else p*((1+(r/100)/12)**m)-p
            c1,c2,c3 = st.columns(3)
            with c1: st.metric("Principal",_cur(p))
            with c2: st.metric("Interest",_cur(interest))
            with c3: st.metric("Total",_cur(p+interest))
    with tabs[2]:
        for c in COURT_HIERARCHY:
            indent = "　"*(c["level"]-1); marker = "🔸" if c["level"]==1 else "├─"
            st.markdown(f"{indent}{marker} **{c['icon']} {c['name']}**"); st.caption(f"{indent}　　{c['desc']}")
    with tabs[3]:
        sq = st.text_input("Search maxims","",placeholder="e.g. nemo, audi…")
        mx = [m for m in LEGAL_MAXIMS if sq.lower() in m["maxim"].lower() or sq.lower() in m["meaning"].lower()] if sq else LEGAL_MAXIMS
        for m in mx:
            st.markdown(f'<div class="tool-card"><h4 style="font-style:italic;color:#7c3aed">{_esc(m["maxim"])}</h4><p>{_esc(m["meaning"])}</p></div>',unsafe_allow_html=True)


# =========================================================================
# MAIN
# =========================================================================
def main():
    _auto()
    render_sidebar()
    tabs = st.tabs(["🏠 Home","🧠 AI Assistant","📚 Research","📁 Cases","📅 Calendar","📋 Templates","👥 Clients","💰 Billing","🇳🇬 Tools"])
    with tabs[0]: render_landing()
    with tabs[1]: render_ai()
    with tabs[2]: render_research()
    with tabs[3]: render_cases()
    with tabs[4]: render_calendar()
    with tabs[5]: render_templates()
    with tabs[6]: render_clients()
    with tabs[7]: render_billing()
    with tabs[8]: render_tools()
    st.markdown('<div class="app-footer"><p>⚖️ <strong>LexiAssist v6.0</strong> · Elite 4-Pass Reasoning Engine</p>'
        '<p>Built for Nigerian Lawyers · <a href="https://ai.google.dev">Google Gemini</a></p>'
        '<p style="font-size:.78rem">⚠️ Legal information, not advice. Verify citations. Apply professional judgment.</p>'
        '<p style="font-size:.75rem">© 2026 LexiAssist</p></div>',unsafe_allow_html=True)

if __name__ == "__main__":
    main()
