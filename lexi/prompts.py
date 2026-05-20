"""LexiAssist prompt strings — system prompts for every AI mode and task.

Prompt text is loaded from ``lexi/prompt_data/*.txt`` files at import time.
This makes prompts editable by non-developers without touching Python code.

The ``{version}`` placeholder in text files is replaced with the current
``__version__`` at load time.

Public API (unchanged from the original single-file version):
  IDENTITY_CORE, STRATEGY_BLOCK, PROMPTS_BY_MODE, TASK_MODIFIERS,
  ISSUE_SPOT_PROMPT, CRITIQUE_PROMPT, FOLLOWUP_PROMPT,
  SOURCE_BACKED_RESEARCH_SYSTEM, COMPARISON_PROMPT,
  WITNESS_PREP_SYSTEM, WITNESS_PREP_PROMPT,
  NEWS_FEED_SUBJECTS, NEWS_FEED_SYSTEM, NEWS_FEED_PROMPT,
  REEXAM_SYSTEM, REEXAM_PROMPT,
  CONTRADICTION_SYSTEM, CONTRADICTION_PROMPT,
  NEWS_DEEPDIVE_SYSTEM, NEWS_DEEPDIVE_PROMPT,
  NEWS_RELEVANCE_SYSTEM, NEWS_RELEVANCE_PROMPT,
  SETTLEMENT_SYSTEM, SETTLEMENT_PROMPT,
  DD_TRANSACTION_TYPES, DD_SYSTEM, DD_PROMPT,
"""
from __future__ import annotations

from pathlib import Path

from .runtime import __version__

# ═══════════════════════════════════════════════════════
# FILE LOADER
# ═══════════════════════════════════════════════════════
_PROMPT_DIR = Path(__file__).resolve().parent / "prompt_data"


def _load(filename: str) -> str:
    """Load a prompt template and resolve the {version} placeholder."""
    text = (_PROMPT_DIR / filename).read_text(encoding="utf-8")
    return text.replace("{version}", __version__)


# ═══════════════════════════════════════════════════════
# CORE BUILDING BLOCKS
# ═══════════════════════════════════════════════════════
IDENTITY_CORE = _load("identity_core.txt")
STRATEGY_BLOCK = _load("strategy_block.txt")

# ═══════════════════════════════════════════════════════
# MODE PROMPTS
#
# Composed at import time from IDENTITY_CORE + (optional) STRATEGY_BLOCK +
# mode-specific suffix. This keeps a SINGLE source of truth for the
# Nigerian backbone (jurisdiction, authorities, ethics, anti-hallucination
# rules) — any future edit to identity_core.txt or strategy_block.txt
# automatically propagates to every analysis mode.
#
# - brief         : identity only, no strategy block (concise answers)
# - standard      : identity + strategy + standard mode suffix
# - comprehensive : identity + strategy + comprehensive mode suffix
# ═══════════════════════════════════════════════════════
PROMPTS_BY_MODE = {
    "brief":         IDENTITY_CORE + "\n" + _load("mode_brief.txt"),
    "standard":      IDENTITY_CORE + STRATEGY_BLOCK + "\n" + _load("mode_standard.txt"),
    "comprehensive": IDENTITY_CORE + STRATEGY_BLOCK + "\n" + _load("mode_comprehensive.txt"),
}

# ═══════════════════════════════════════════════════════
# TASK MODIFIERS (appended to the mode prompt)
# ═══════════════════════════════════════════════════════
TASK_MODIFIERS = {
    "general": "\nApply the general legal framework. Take a clear position.",
    "analysis": "\nFocus on deep issue-spotting. Apply CREAC to each issue. Distinguish facts carefully.",
    "drafting": _load("task_drafting.txt"),
    "research": "\nWrite a formal Legal Research Memorandum. For each authority: state the principle, quote the ratio (if known), and explain relevance to the query.",
    "procedure": "\nProvide step-by-step procedural guidance. Include: which court, which form/process, filing fees (if known), timelines, and common pitfalls.",
    "advisory": "\nFocus on strategic advisory. Emphasize risk mitigation, commercial impact, and optimal paths. Include risk matrix.",
    "interpret": "\nApply the three rules of statutory interpretation (Literal, Golden, Mischief). State which rule yields the best result and WHY.",
    "contract_review": _load("task_contract_review.txt"),
}

# ═══════════════════════════════════════════════════════
# SPECIALISED PROMPTS (fully composed, loaded from files)
# ═══════════════════════════════════════════════════════
ISSUE_SPOT_PROMPT = _load("issue_spot_prompt.txt")
CRITIQUE_PROMPT = _load("critique_prompt.txt")
FOLLOWUP_PROMPT = _load("followup_prompt.txt")
SOURCE_BACKED_RESEARCH_SYSTEM = _load("source_backed_research_system.txt")
COMPARISON_PROMPT = _load("comparison_prompt.txt")

# ── Witness Preparation ──
WITNESS_PREP_SYSTEM = _load("witness_prep_system.txt")
WITNESS_PREP_PROMPT = _load("witness_prep_prompt.txt")

# ── Re-examination ──
REEXAM_SYSTEM = _load("reexam_system.txt")
REEXAM_PROMPT = _load("reexam_prompt.txt")

# ── Contradiction Detector ──
CONTRADICTION_SYSTEM = _load("contradiction_system.txt")
CONTRADICTION_PROMPT = _load("contradiction_prompt.txt")

# ── News Feed ──
NEWS_FEED_SUBJECTS = [
    "All Areas",
    "Constitutional Law",
    "Criminal Law & Procedure",
    "Commercial / Contract Law",
    "Company Law",
    "Land / Property Law",
    "Employment & Labour Law",
    "Tax Law",
    "Banking & Finance",
    "Intellectual Property",
    "Family Law",
    "Admiralty / Maritime",
    "Human Rights",
    "Electoral Law",
    "Oil & Gas / Energy",
    "Practice Directions & Court Rules",
    "Legislation Updates",
]
NEWS_FEED_SYSTEM = _load("news_feed_system.txt")
NEWS_FEED_PROMPT = _load("news_feed_prompt.txt")

# ── News Deep-Dive ──
NEWS_DEEPDIVE_SYSTEM = _load("news_deepdive_system.txt")
NEWS_DEEPDIVE_PROMPT = _load("news_deepdive_prompt.txt")

# ── News Relevance Scan ──
NEWS_RELEVANCE_SYSTEM = _load("news_relevance_system.txt")
NEWS_RELEVANCE_PROMPT = _load("news_relevance_prompt.txt")

# ── Settlement Advisor ──
SETTLEMENT_SYSTEM = _load("settlement_system.txt")
SETTLEMENT_PROMPT = _load("settlement_prompt.txt")

# ── Due Diligence ──
DD_TRANSACTION_TYPES = {
    "property_purchase":    "🏠 Property / Land Acquisition",
    "company_acquisition":  "🏢 Company / Business Acquisition",
    "loan_security":        "💳 Loan & Security / Debenture",
    "joint_venture":        "🤝 Joint Venture / Partnership",
    "franchise":            "🏪 Franchise Agreement",
    "employment_senior":    "👔 Senior Employment / Directorship",
    "oil_gas_block":        "⛽ Oil & Gas Block / Farm-in",
    "real_estate_dev":      "🏗️ Real Estate Development",
    "ipo_capital_market":   "📈 IPO / Capital Market Transaction",
    "fintech_regulatory":   "📱 Fintech / Payment Service",
}
DD_SYSTEM = _load("dd_system.txt")
DD_PROMPT = _load("dd_prompt.txt")
