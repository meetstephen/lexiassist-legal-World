"""Extract the large prompt text blocks from lexi/prompts.py into .txt files."""
from __future__ import annotations
import sys
from pathlib import Path

REPO = Path(".")
sys.path.insert(0, str(REPO))

# Import the module properly as a package
import lexi.prompts as mod

OUT_DIR = REPO / "lexi" / "prompt_data"
OUT_DIR.mkdir(exist_ok=True)

BIG_PROMPTS = [
    ("IDENTITY_CORE", "identity_core.txt"),
    ("STRATEGY_BLOCK", "strategy_block.txt"),
    ("ISSUE_SPOT_PROMPT", "issue_spot_prompt.txt"),
    ("CRITIQUE_PROMPT", "critique_prompt.txt"),
    ("FOLLOWUP_PROMPT", "followup_prompt.txt"),
    ("SOURCE_BACKED_RESEARCH_SYSTEM", "source_backed_research_system.txt"),
    ("COMPARISON_PROMPT", "comparison_prompt.txt"),
    ("WITNESS_PREP_SYSTEM", "witness_prep_system.txt"),
    ("WITNESS_PREP_PROMPT", "witness_prep_prompt.txt"),
    ("NEWS_FEED_SYSTEM", "news_feed_system.txt"),
    ("NEWS_FEED_PROMPT", "news_feed_prompt.txt"),
    ("REEXAM_SYSTEM", "reexam_system.txt"),
    ("REEXAM_PROMPT", "reexam_prompt.txt"),
    ("CONTRADICTION_SYSTEM", "contradiction_system.txt"),
    ("CONTRADICTION_PROMPT", "contradiction_prompt.txt"),
    ("NEWS_DEEPDIVE_SYSTEM", "news_deepdive_system.txt"),
    ("NEWS_DEEPDIVE_PROMPT", "news_deepdive_prompt.txt"),
    ("NEWS_RELEVANCE_SYSTEM", "news_relevance_system.txt"),
    ("NEWS_RELEVANCE_PROMPT", "news_relevance_prompt.txt"),
    ("SETTLEMENT_SYSTEM", "settlement_system.txt"),
    ("SETTLEMENT_PROMPT", "settlement_prompt.txt"),
    ("DD_SYSTEM", "dd_system.txt"),
    ("DD_PROMPT", "dd_prompt.txt"),
]

version = mod.__version__
written = 0
for var_name, fname in BIG_PROMPTS:
    val = getattr(mod, var_name, None)
    if val and isinstance(val, str) and len(val) > 100:
        val_templated = val.replace(version, "{version}")
        (OUT_DIR / fname).write_text(val_templated)
        written += 1
        print(f"  {fname:45s} {len(val):5d} chars")

# Mode prompts
for mode_name, mode_prompt in mod.PROMPTS_BY_MODE.items():
    fname = f"mode_{mode_name}.txt"
    templated = mode_prompt.replace(version, "{version}")
    (OUT_DIR / fname).write_text(templated)
    written += 1
    print(f"  {fname:45s} {len(mode_prompt):5d} chars")

# Task modifier for contract_review
cr = mod.TASK_MODIFIERS.get("contract_review", "")
if len(cr) > 100:
    (OUT_DIR / "task_contract_review.txt").write_text(cr)
    written += 1
    print(f"  {'task_contract_review.txt':45s} {len(cr):5d} chars")

print(f"\nTotal files: {written}")
