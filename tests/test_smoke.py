"""Smoke tests — verify the package imports and all entry points exist.

These tests do NOT run the Streamlit app or call any rendering function.
They only verify the import graph is intact and the public API surface
is wired up correctly. They are the cheap guardrail for the modular
refactor and run in well under a second.

If anything here fails on a PR, the import graph is broken — fix that
before reviewing the rest of the change.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
# Ensure the repo root is on sys.path so `import lexi` works regardless
# of how pytest is invoked.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Foundation modules — must all import cleanly.
# ─────────────────────────────────────────────────────────────────────────────
FOUNDATION_MODULES = [
    "lexi",
    "lexi.runtime",
    "lexi.crypto",
    "lexi.constants",
    "lexi.prompts",
    "lexi.legal_data",
    "lexi.citations",
    "lexi.themes",
    "lexi.rag",
    "lexi.fuzzy",
    "lexi.exports",
    "lexi.database",
    "lexi.auth",
    "lexi.helpers",
    "lexi.migrator",
    "lexi.pages",
]


# ─────────────────────────────────────────────────────────────────────────────
# Page modules — the contract is "every page module exports its render_*
# function(s) as callables". This catches refactoring mistakes where a
# render function is renamed, deleted, or moved without updating app.main().
# ─────────────────────────────────────────────────────────────────────────────
PAGE_RENDERERS: dict[str, list[str]] = {
    "lexi.pages.sidebar":         ["render_sidebar"],
    "lexi.pages.home":            ["render_home", "render_tasks"],
    "lexi.pages.ai":              ["render_ai"],
    "lexi.pages.research":        [
        "render_research",
        "render_authority_verification",
        "render_source_backed_research",
    ],
    "lexi.pages.cases":           ["render_cases"],
    "lexi.pages.calendar":        ["render_calendar"],
    "lexi.pages.templates":       ["render_templates"],
    "lexi.pages.clients":         ["render_clients"],
    "lexi.pages.billing":         ["render_billing"],
    "lexi.pages.tools":           ["render_tools"],
    "lexi.pages.search":          ["render_global_search"],
    "lexi.pages.conflict":        ["render_conflict_checker"],
    "lexi.pages.pleadings":       ["render_pleadings"],
    "lexi.pages.lifecycle":       ["render_lifecycle"],
    "lexi.pages.witness":         ["render_witness_prep"],
    "lexi.pages.news":            ["render_legal_news"],
    "lexi.pages.notes":           ["render_notes_converter"],
    "lexi.pages.profile":         ["render_profile"],
    "lexi.pages.fee_calculator":  ["render_fee_calculator"],
    "lexi.pages.settlement":      ["render_settlement_advisor"],
    "lexi.pages.due_diligence":   ["render_due_diligence"],
    "lexi.pages.user_management": ["render_user_management"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _load_app_module():
    """Load app.py as a module without running `streamlit run`.

    Streamlit's `set_page_config()` call inside app.py is a no-op outside
    `streamlit run` (it just records the config), so this is safe.
    """
    spec = importlib.util.spec_from_file_location("_app_under_test", REPO_ROOT / "app.py")
    assert spec and spec.loader, "Could not build a spec for app.py"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("modname", FOUNDATION_MODULES)
def test_foundation_module_imports(modname):
    """Every foundation module imports cleanly."""
    importlib.import_module(modname)


@pytest.mark.parametrize("modname,fns", list(PAGE_RENDERERS.items()))
def test_page_renderers_callable(modname, fns):
    """Every page module exports its declared render_* functions as callables."""
    mod = importlib.import_module(modname)
    for fn in fns:
        attr = getattr(mod, fn, None)
        assert callable(attr), (
            f"{modname}.{fn} is not callable (got {type(attr).__name__}). "
            f"Either the function was renamed/removed, or the module failed "
            f"to import a symbol it needed."
        )


def test_app_module_loads():
    """app.py imports cleanly and exposes main() and __version__."""
    app = _load_app_module()
    assert callable(app.main), "app.main must be callable"
    assert isinstance(app.__version__, str) and app.__version__, (
        "app.__version__ must be a non-empty string"
    )


def test_version_consistency():
    """__version__ must match between app.py and lexi.runtime."""
    from lexi.runtime import __version__ as pkg_version

    app = _load_app_module()
    assert app.__version__ == pkg_version, (
        f"Version mismatch: app.py={app.__version__!r} vs "
        f"lexi.runtime={pkg_version!r}"
    )


def test_all_renderers_referenced_in_app_main():
    """Every render_* function declared in PAGE_RENDERERS must be referenced
    inside app.main(), or it is dead routing code.

    This catches the easy-to-miss bug where a new page module is added but
    main() is never updated to route to it.
    """
    import inspect

    app = _load_app_module()
    main_src = inspect.getsource(app.main)
    expected = sorted({fn for fns in PAGE_RENDERERS.values() for fn in fns})
    missing = [fn for fn in expected if fn not in main_src]
    assert not missing, (
        f"app.main() never references these render functions, so they "
        f"are unreachable from the UI: {missing}"
    )



# ─────────────────────────────────────────────────────────────────────────────
# Prompt composition contract — guards against regressions in the
# identity_core / strategy_block / mode / drafting prompt assembly.
# ─────────────────────────────────────────────────────────────────────────────
def test_prompts_compose_correctly():
    """All composed mode prompts must contain the Nigerian backbone.

    Pins the "single source of truth" refactor: ``IDENTITY_CORE`` content
    must propagate to every analysis mode, ``STRATEGY_BLOCK`` must be
    present in standard/comprehensive but absent in brief, and the
    drafting task modifier must include the Nigerian formality protocol.
    """
    from lexi.prompts import (
        IDENTITY_CORE, STRATEGY_BLOCK, PROMPTS_BY_MODE, TASK_MODIFIERS,
    )

    # Identity core anti-hallucination strengthening
    assert "HARD RULES ON CITATIONS" in IDENTITY_CORE, (
        "identity_core.txt is missing the strengthened citation rules"
    )

    # Every mode prompt inherits the identity backbone
    for mode_name in ("brief", "standard", "comprehensive"):
        composed = PROMPTS_BY_MODE[mode_name]
        for marker in ("CFRN 1999", "CAMA", "Evidence Act 2011",
                       "HARD RULES ON CITATIONS"):
            assert marker in composed, (
                f"mode={mode_name} missing {marker!r} after composition — "
                f"the identity_core inheritance is broken"
            )

    # Strategy block belongs in standard + comprehensive only
    assert "STRATEGIC POSITION" not in PROMPTS_BY_MODE["brief"], (
        "brief mode must NOT contain the STRATEGIC POSITION block"
    )
    assert "STRATEGIC POSITION" in PROMPTS_BY_MODE["standard"]
    assert "STRATEGIC POSITION" in PROMPTS_BY_MODE["comprehensive"]

    # Drafting task modifier is the comprehensive Nigerian protocol
    drafting = TASK_MODIFIERS["drafting"]
    for marker in (
        "NIGERIAN LEGAL DRAFTING PROTOCOL",
        "JURAT",
        "NBA Stamp & Seal",
        "SCN Enrolment",
        "Stamp Duties Act",
        "DATED this",
        "BETWEEN",
        "HOLDEN AT",
    ):
        assert marker in drafting, (
            f"task_drafting.txt missing required Nigerian marker {marker!r}"
        )


def test_drafting_skips_strategy_block():
    """build_system_prompt must NOT inject the STRATEGIC POSITION block
    into drafting outputs — drafts are operative documents, not analyses."""
    from lexi.helpers import build_system_prompt

    drafting_system = build_system_prompt("drafting", "comprehensive")
    assert "STRATEGIC POSITION" not in drafting_system, (
        "Drafting system prompt must not include the STRATEGIC POSITION "
        "block — it pollutes pleadings/affidavits with risk tables a "
        "lawyer would never sign their name to."
    )
    # But the drafting protocol must be present
    assert "NIGERIAN LEGAL DRAFTING PROTOCOL" in drafting_system

    # Analysis tasks DO get the strategy block
    analysis_system = build_system_prompt("general", "comprehensive")
    assert "STRATEGIC POSITION" in analysis_system


def test_precedent_grounding_helper():
    """find_relevant_verified_cases must surface real Nigerian cases for
    typical practice queries and refuse to invent matches for nonsense."""
    from lexi.citations import (
        find_relevant_verified_cases, VERIFIED_NIGERIAN_CASES,
    )

    # Land/title query → expect Idundun / Ogunleye / Adole
    land = find_relevant_verified_cases("proving title to land", top_k=5)
    land_names = {m["name"] for m in land}
    assert any(name in land_names for name in (
        "Idundun v Okumagba", "Ogunleye v Oni", "Adole v Gwar",
    )), f"land query returned only {land_names}"

    # Election petition → expect Buhari or Atiku
    election = find_relevant_verified_cases("election petition burden of proof", top_k=5)
    election_names = {m["name"] for m in election}
    assert any(name in election_names for name in (
        "Buhari v Obasanjo", "Atiku Abubakar v INEC",
    )), f"election query returned only {election_names}"

    # Junk → empty list (must NOT hallucinate matches)
    assert find_relevant_verified_cases("xyz1234 nonexistent topic") == []
    assert find_relevant_verified_cases("") == []

    # Every match must be a real entry in the verified DB
    for m in land + election:
        assert m["name"] in VERIFIED_NIGERIAN_CASES


def test_pdf_unicode_sanitiser():
    """PDF Unicode → ASCII fallback must handle every char that crashed
    production and produce strict latin-1 output."""
    from lexi.exports import _pdf_ascii_fallback

    cases = {
        # The exact banner that crashed production:
        "STRICTLY PRIVATE & CONFIDENTIAL \u2014 ATTORNEY WORK PRODUCT":
            ("\u2014", "-"),       # em-dash → hyphen
        "Pay \u20a65,000,000.00 within 7 days":
            ("\u20a6", "NGN"),     # Naira sign → NGN
        "the agreement was \u201cunenforceable\u201d.":
            ("\u201c", '"'),       # smart quote → straight quote
        "Order 13 \u2013 Rule 14":
            ("\u2013", "-"),       # en-dash → hyphen
        "section 84\u2026":
            ("\u2026", "..."),     # ellipsis → three dots
    }
    for inp, (forbidden, expected) in cases.items():
        out = _pdf_ascii_fallback(inp)
        assert forbidden not in out, f"sanitiser left {forbidden!r} in {out!r}"
        assert expected in out, f"sanitiser missing {expected!r} in {out!r}"
        # Every output must be encodable as latin-1 (otherwise fpdf crashes)
        out.encode("latin-1")
