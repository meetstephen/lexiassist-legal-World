"""Smoke tests for the v9.1.2 beta feedback feature.

These tests do not require a real database — they only verify that the
new public surface exists, the migration file is well-formed, and the
render path imports cleanly.
"""
from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_database_class_exposes_beta_feedback_methods():
    """The Database class must expose the three CRUD methods."""
    db_mod = importlib.import_module("lexi.database")
    Database = getattr(db_mod, "Database")
    for method_name in (
        "add_beta_feedback",
        "list_beta_feedback",
        "update_beta_feedback_status",
    ):
        attr = getattr(Database, method_name, None)
        assert callable(attr), (
            f"Database.{method_name} should exist as a method but is "
            f"{type(attr).__name__}"
        )


def test_migration_002_present_and_well_formed():
    """The 002 migration must exist and create the beta_feedback table."""
    migrations_dir = REPO_ROOT / "lexi" / "migrations"
    files = sorted(migrations_dir.glob("0*.sql"))
    names = [f.name for f in files]
    assert any(n.startswith("002_") for n in names), (
        f"Expected migration 002_* in lexi/migrations/, found: {names}"
    )
    sql_002 = next(f for f in files if f.name.startswith("002_")).read_text()
    # Must create the table and at least one index
    assert re.search(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+beta_feedback",
                     sql_002, re.IGNORECASE), (
        "Migration 002 must create the beta_feedback table"
    )
    assert "CREATE INDEX" in sql_002.upper(), (
        "Migration 002 should add at least one index for query performance"
    )


def test_sidebar_imports_with_feedback_widget():
    """The sidebar module imports cleanly even with the new feedback form."""
    importlib.import_module("lexi.pages.sidebar")


def test_user_management_renders_feedback_inbox_tab():
    """User management page module must still import after adding the inbox tab."""
    mod = importlib.import_module("lexi.pages.user_management")
    assert callable(getattr(mod, "render_user_management", None))


def test_version_is_valid_semver_at_or_after_baseline():
    """Sanity: __version__ is valid semver and at/after the 9.1.2 baseline.

    (Version-agnostic so routine version bumps don't break CI; we only
    guard against an invalid string or a regression below the baseline.)
    """
    runtime = importlib.import_module("lexi.runtime")
    v = runtime.__version__
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v.strip())
    assert m, f"__version__ must be semver MAJOR.MINOR.PATCH; got {v!r}"
    parts = tuple(int(x) for x in m.groups())
    assert parts >= (9, 1, 2), (
        f"version regressed below the 9.1.2 baseline; got {v}"
    )
