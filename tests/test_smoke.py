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
