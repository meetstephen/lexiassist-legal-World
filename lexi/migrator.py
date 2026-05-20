"""LexiAssist database migrator — simple, forward-only, numbered SQL migrations.

How it works:
  1. On first run, creates a ``schema_version`` table to track state.
  2. Scans ``lexi/migrations/*.sql`` for files matching ``NNN_*.sql``.
  3. Runs any migration whose version number > the current DB version,
     in ascending order.
  4. Each migration runs in a single transaction (all-or-nothing).
  5. On success, records the version in ``schema_version``.

To add a new migration:
  - Create ``lexi/migrations/002_description.sql``
  - The app will pick it up automatically on next startup.

The migrator is called from ``Database.__init__()`` instead of the old
``_init_tables()`` method.
"""
from __future__ import annotations
from typing import Any

import re
from pathlib import Path

from .runtime import logger

_MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _ensure_schema_version_table(conn: "Any") -> None:
    """Create the schema_version table if it doesn't exist."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            filename TEXT DEFAULT ''
        )
    """)
    conn.commit()


def _get_current_version(conn: "Any") -> int:
    """Return the highest migration version that has been applied."""
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version")
    row = cur.fetchone()
    return row[0] if row else 0


def _discover_migrations() -> list[tuple[int, Path]]:
    """Find all migration SQL files and return sorted (version, path) pairs."""
    pattern = re.compile(r"^(\d{3})_.+\.sql$")
    migrations: list[tuple[int, Path]] = []
    if not _MIGRATIONS_DIR.exists():
        return migrations
    for f in sorted(_MIGRATIONS_DIR.iterdir()):
        m = pattern.match(f.name)
        if m:
            migrations.append((int(m.group(1)), f))
    return migrations


def run_migrations(conn: "Any") -> int:
    """Run all pending migrations. Returns the number of migrations applied.

    This function is safe to call on every startup — it's a no-op if the
    database is already up to date.

    Parameters
    ----------
    conn : psycopg2 connection
        An open, autocommit=False PostgreSQL connection.

    Returns
    -------
    int
        Number of migrations applied in this run (0 if already current).
    """
    _ensure_schema_version_table(conn)
    current = _get_current_version(conn)
    pending = [(v, p) for v, p in _discover_migrations() if v > current]

    if not pending:
        return 0

    applied = 0
    from .runtime import datetime

    for version, path in pending:
        sql = path.read_text(encoding="utf-8")
        try:
            cur = conn.cursor()
            # Execute the full migration file as a single transaction
            cur.execute(sql)
            # Record the version
            cur.execute(
                "INSERT INTO schema_version (version, applied_at, filename) "
                "VALUES (%s, %s, %s)",
                (version, datetime.now().isoformat(), path.name),
            )
            conn.commit()
            applied += 1
            logger.info(f"Migration {path.name} applied successfully (v{version})")
        except Exception as e:
            conn.rollback()
            logger.error(f"Migration {path.name} FAILED: {e}")
            raise RuntimeError(
                f"Database migration {path.name} failed: {e}. "
                f"The database is at version {current + applied}. "
                f"Fix the migration SQL and restart."
            ) from e

    return applied
