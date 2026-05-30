"""LexiAssist database layer — PostgreSQL persistence for every piece
of user-scoped state, plus session-data bootstrap helpers.
"""
from __future__ import annotations

from .runtime import (
    st, os, re, json, logger, datetime, date,
    psycopg2, hashlib, uuid,
    Optional,
    new_id, hash_session_token,
)
import logging
from .crypto import encrypt_secret, decrypt_secret
from .constants import _get_db_url
from .citations import VERIFIED_NIGERIAN_CASES
from .migrator import run_migrations

# ═══════════════════════════════════════════════════════
# DATABASE LAYER
# ═══════════════════════════════════════════════════════
class Database:
    """PostgreSQL persistence for all LexiAssist data."""

    def __init__(self):
        self.url = _get_db_url()
        self.conn = self._connect()
        run_migrations(self.conn)  # versioned migrations

    def _connect(self):
        conn = psycopg2.connect(self.url)
        conn.autocommit = False
        return conn

    def _execute(self, sql: str, params=None):
        """Execute with auto-reconnect and transaction-error recovery."""
        try:
            cur = self.conn.cursor()
            cur.execute(sql, params or ())
            return cur
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            # Stale connection — reconnect and retry
            try:
                self.conn.rollback()
            except Exception:
                pass
            self.conn = self._connect()
            cur = self.conn.cursor()
            cur.execute(sql, params or ())
            return cur
        except psycopg2.Error:
            # Transaction aborted — roll back so the connection is usable again
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise

    def _exec_ddl(self, sql: str):
        """Run a single DDL statement in its own isolated transaction.
        If it fails (e.g. object already exists in a different form), roll back
        cleanly so the connection stays usable for the next statement."""
        try:
            cur = self.conn.cursor()
            cur.execute(sql)
            self.conn.commit()
        except psycopg2.Error as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            logger.warning(f"DDL skipped (non-fatal): {e!s:.120}")

    def _init_tables(self):
        # Each statement runs in its own transaction so one failure never
        # poisons subsequent DDL (PostgreSQL aborts the whole txn on error).
        ddl_statements = [
            """CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT '[]'
            )""",
            """CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT DEFAULT '',
                password_hash TEXT NOT NULL,
                firm_name TEXT DEFAULT '',
                lawyer_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                address TEXT DEFAULT '',
                role TEXT DEFAULT 'user',
                created_at TEXT DEFAULT '',
                last_login TEXT DEFAULT ''
            )""",
            """CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                firm_name TEXT DEFAULT '',
                lawyer_name TEXT DEFAULT '',
                email TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                address TEXT DEFAULT '',
                password_hash TEXT DEFAULT ''
            )""",
            """CREATE TABLE IF NOT EXISTS cost_logs (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                model TEXT,
                task TEXT,
                mode TEXT,
                input_chars INTEGER DEFAULT 0,
                output_chars INTEGER DEFAULT 0,
                estimated_cost REAL DEFAULT 0,
                query_preview TEXT DEFAULT '',
                user_id TEXT DEFAULT 'legacy'
            )""",
            """CREATE TABLE IF NOT EXISTS case_analyses (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                query TEXT,
                response TEXT,
                task TEXT,
                mode TEXT,
                timestamp TEXT,
                user_id TEXT DEFAULT 'legacy'
            )""",
            """CREATE TABLE IF NOT EXISTS user_sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_used TEXT DEFAULT '',
                device_hint TEXT DEFAULT ''
            )""",
        # ── Phase 2: Audit Log (append-only, hash-chained) ──
            """CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                detail TEXT DEFAULT '',
                prev_hash TEXT DEFAULT '',
                entry_hash TEXT DEFAULT ''
            )""",
            # ── Phase 2: Statute Chunks (RAG grounding) ──
            """CREATE TABLE IF NOT EXISTS statute_chunks (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                section_label TEXT NOT NULL,
                content TEXT NOT NULL,
                keywords TEXT DEFAULT '',
                created_at TEXT DEFAULT ''
            )""",
        ]
        for stmt in ddl_statements:
            self._exec_ddl(stmt)

        # Safely add columns to existing tables — each in its own transaction
        for tbl in ("cost_logs", "case_analyses"):
            self._exec_ddl(
                f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS user_id TEXT DEFAULT 'legacy'"
            )

        # ── Performance indexes (CREATE INDEX IF NOT EXISTS = safe to re-run) ──
        index_statements = [
            # users — fast lookup by username (login path)
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)",
            # case_analyses — filter by user and by case
            "CREATE INDEX IF NOT EXISTS idx_case_analyses_user_id ON case_analyses (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_case_analyses_case_id ON case_analyses (case_id)",
            "CREATE INDEX IF NOT EXISTS idx_case_analyses_user_case ON case_analyses (user_id, case_id)",
            # cost_logs — reporting queries filter by user and time
            "CREATE INDEX IF NOT EXISTS idx_cost_logs_user_id ON cost_logs (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_cost_logs_timestamp ON cost_logs (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_cost_logs_user_ts ON cost_logs (user_id, timestamp)",
            # audit_log — tail queries and user-specific views
            "CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log (action)",
            # user_sessions — validation and cleanup by user and expiry
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions (expires_at)",
            # statute_chunks — keyword search
            "CREATE INDEX IF NOT EXISTS idx_statute_chunks_source ON statute_chunks (source)",
        ]
        for idx_stmt in index_statements:
            self._exec_ddl(idx_stmt)

        # Ensure legacy profile row exists
        self._exec_ddl(
            "INSERT INTO user_profile (id) VALUES (1) ON CONFLICT DO NOTHING"
        )

    def _uid(self) -> str:
        """Return current user_id from Streamlit session, fallback to 'legacy'."""
        try:
            uid = st.session_state.get("current_user_id", "")
            return uid if uid else "legacy"
        except Exception:
            return "legacy"

    # ── KV Store — raw (keep for internal use) ──
    def _save_list_raw(self, key: str, data: list):
        self._execute(
            "INSERT INTO kv_store (key, value) VALUES (%s, %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (key, json.dumps(data, default=str)),
        )
        self.conn.commit()

    def _load_list_raw(self, key: str) -> list:
        cur = self._execute("SELECT value FROM kv_store WHERE key = %s", (key,))
        row = cur.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                return []
        return []

    # ── KV Store — user-namespaced (primary API) ──
    def save_list(self, key: str, data: list):
        """Save data namespaced to the current user."""
        uid = self._uid()
        self._save_list_raw(f"u:{uid}:{key}", data)

    def load_list(self, key: str) -> list:
        """Load data namespaced to the current user."""
        uid = self._uid()
        return self._load_list_raw(f"u:{uid}:{key}")

    # ── User Profile ──
    def get_profile(self) -> dict:
        """Load current user's profile from users table + extended kv fields."""
        uid = self._uid()
        if uid and uid != "legacy":
            return self.get_user_profile(uid)
        # Fallback for legacy / unauthenticated
        cur = self._execute(
            "SELECT firm_name, lawyer_name, email, phone, address, password_hash "
            "FROM user_profile WHERE id = 1"
        )
        row = cur.fetchone()
        if row:
            return {
                "firm_name": row[0] or "", "lawyer_name": row[1] or "",
                "email": row[2] or "", "phone": row[3] or "",
                "address": row[4] or "", "password_hash": row[5] or "",
            }
        return {"firm_name": "", "lawyer_name": "", "email": "", "phone": "", "address": "", "password_hash": ""}

    def save_profile(self, profile: dict):
        """Save current user's profile."""
        uid = self._uid()
        if uid and uid != "legacy":
            self.save_user_profile(uid, profile)
        else:
            self._execute(
                "UPDATE user_profile SET firm_name=%s, lawyer_name=%s, email=%s, "
                "phone=%s, address=%s, password_hash=%s WHERE id=1",
                (
                    profile.get("firm_name", ""), profile.get("lawyer_name", ""),
                    profile.get("email", ""), profile.get("phone", ""),
                    profile.get("address", ""), profile.get("password_hash", ""),
                ),
            )
            self.conn.commit()

    # ── Users table CRUD ──
    def has_any_users(self) -> bool:
        cur = self._execute("SELECT COUNT(*) FROM users")
        return cur.fetchone()[0] > 0

    def create_user(self, data: dict) -> bool:
        try:
            self._execute(
                "INSERT INTO users (user_id, username, email, password_hash, firm_name, "
                "lawyer_name, phone, address, role, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    data.get("user_id", uuid.uuid4().hex[:12]),
                    data.get("username", "").lower().strip(),
                    data.get("email", ""),
                    data.get("password_hash", ""),
                    data.get("firm_name", ""),
                    data.get("lawyer_name", ""),
                    data.get("phone", ""),
                    data.get("address", ""),
                    data.get("role", "user"),
                    datetime.now().isoformat(),
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"create_user failed: {e}")
            try:
                self.conn.rollback()
            except Exception:
                pass
            return False

    def get_user_by_username(self, username: str) -> Optional[dict]:
        cur = self._execute(
            "SELECT user_id, username, email, password_hash, firm_name, lawyer_name, "
            "phone, address, role, created_at, last_login FROM users WHERE username = %s",
            (username.lower().strip(),),
        )
        row = cur.fetchone()
        if row:
            return {
                "user_id": row[0], "username": row[1], "email": row[2],
                "password_hash": row[3], "firm_name": row[4], "lawyer_name": row[5],
                "phone": row[6], "address": row[7], "role": row[8],
                "created_at": row[9], "last_login": row[10],
            }
        return None

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        cur = self._execute(
            "SELECT user_id, username, email, password_hash, firm_name, lawyer_name, "
            "phone, address, role, created_at, last_login FROM users WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if row:
            return {
                "user_id": row[0], "username": row[1], "email": row[2],
                "password_hash": row[3], "firm_name": row[4], "lawyer_name": row[5],
                "phone": row[6], "address": row[7], "role": row[8],
                "created_at": row[9], "last_login": row[10],
            }
        return None

    def list_users(self) -> list:
        cur = self._execute(
            "SELECT user_id, username, email, firm_name, lawyer_name, role, created_at, last_login "
            "FROM users ORDER BY created_at ASC"
        )
        rows = cur.fetchall()
        return [
            {
                "user_id": r[0], "username": r[1], "email": r[2],
                "firm_name": r[3], "lawyer_name": r[4], "role": r[5],
                "created_at": r[6], "last_login": r[7],
            }
            for r in rows
        ]

    def update_user(self, user_id: str, updates: dict):
        allowed = ("email", "password_hash", "firm_name", "lawyer_name",
                   "phone", "address", "role", "last_login")
        fields = [f"{k} = %s" for k in updates if k in allowed]
        values = [v for k, v in updates.items() if k in allowed]
        if not fields:
            return
        values.append(user_id)
        self._execute(f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s", values)
        self.conn.commit()

    def delete_user(self, user_id: str):
        self._execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        self._execute("DELETE FROM case_analyses WHERE user_id = %s", (user_id,))
        self._execute("DELETE FROM cost_logs WHERE user_id = %s", (user_id,))
        self._execute("DELETE FROM kv_store WHERE key LIKE %s", (f"u:{user_id}:%",))
        self._execute("DELETE FROM user_sessions WHERE user_id = %s", (user_id,))
        self.conn.commit()

    def update_user_last_login(self, user_id: str):
        self.update_user(user_id, {"last_login": datetime.now().isoformat()})

    def get_user_profile(self, user_id: str) -> dict:
        user = self.get_user_by_id(user_id)
        base = {
            "firm_name": "", "lawyer_name": "", "email": "",
            "phone": "", "address": "", "password_hash": "",
        }
        if user:
            base.update({
                "firm_name": user.get("firm_name", ""),
                "lawyer_name": user.get("lawyer_name", ""),
                "email": user.get("email", ""),
                "phone": user.get("phone", ""),
                "address": user.get("address", ""),
                "password_hash": user.get("password_hash", ""),
            })
        # Merge extended profile fields (notification settings etc.)
        ext_data = self._load_list_raw(f"u:{user_id}:profile_extended")
        if ext_data and isinstance(ext_data, list) and ext_data:
            base.update(ext_data[0])
        return base

    def save_user_profile(self, user_id: str, profile: dict):
        core_fields = ("firm_name", "lawyer_name", "email", "phone", "address", "password_hash")
        core = {k: profile.get(k, "") for k in core_fields}
        self.update_user(user_id, core)
        # Save extended fields (notifications etc.) separately
        extended = {k: v for k, v in profile.items() if k not in core_fields}
        if extended:
            self._save_list_raw(f"u:{user_id}:profile_extended", [extended])

    # ── Cost Logs (user-scoped) ──
    def add_cost_log(self, entry: dict):
        uid = self._uid()
        self._execute(
            "INSERT INTO cost_logs "
            "(id, timestamp, model, task, mode, input_chars, output_chars, "
            "estimated_cost, query_preview, user_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (
                entry.get("id", uuid.uuid4().hex[:8]),
                entry.get("timestamp", datetime.now().isoformat()),
                entry.get("model", ""), entry.get("task", ""), entry.get("mode", ""),
                entry.get("input_chars", 0), entry.get("output_chars", 0),
                entry.get("estimated_cost", 0.0), entry.get("query_preview", ""), uid,
            ),
        )
        self.conn.commit()

    def get_cost_logs(self, limit: int = 200) -> list:
        uid = self._uid()
        cur = self._execute(
            "SELECT id, timestamp, model, task, mode, input_chars, output_chars, "
            "estimated_cost, query_preview FROM cost_logs "
            "WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s",
            (uid, limit),
        )
        rows = cur.fetchall()
        return [
            {
                "id": r[0], "timestamp": r[1], "model": r[2], "task": r[3],
                "mode": r[4], "input_chars": r[5], "output_chars": r[6],
                "estimated_cost": r[7], "query_preview": r[8],
            }
            for r in rows
        ]

    def get_cost_summary(self) -> dict:
        uid = self._uid()
        today = date.today().isoformat()
        month_start = date.today().replace(day=1).isoformat()
        total = self._execute(
            "SELECT COALESCE(SUM(estimated_cost),0), COUNT(*) FROM cost_logs WHERE user_id = %s",
            (uid,)
        ).fetchone()
        daily = self._execute(
            "SELECT COALESCE(SUM(estimated_cost),0), COUNT(*) FROM cost_logs "
            "WHERE user_id = %s AND timestamp >= %s", (uid, today)
        ).fetchone()
        monthly = self._execute(
            "SELECT COALESCE(SUM(estimated_cost),0), COUNT(*) FROM cost_logs "
            "WHERE user_id = %s AND timestamp >= %s", (uid, month_start)
        ).fetchone()
        return {
            "total_cost": total[0], "total_calls": total[1],
            "daily_cost": daily[0], "daily_calls": daily[1],
            "monthly_cost": monthly[0], "monthly_calls": monthly[1],
        }

    # ── Case Analyses (user-scoped) ──
    def add_case_analysis(self, case_id: str, data: dict):
        uid = self._uid()
        self._execute(
            "INSERT INTO case_analyses (id, case_id, query, response, task, mode, timestamp, user_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (
                data.get("id", uuid.uuid4().hex[:8]), case_id,
                data.get("query", ""), data.get("response", ""),
                data.get("task", ""), data.get("mode", ""),
                data.get("timestamp", datetime.now().isoformat()), uid,
            ),
        )
        self.conn.commit()

    def get_case_analyses(self, case_id: str) -> list:
        uid = self._uid()
        cur = self._execute(
            "SELECT id, query, response, task, mode, timestamp FROM case_analyses "
            "WHERE case_id = %s AND user_id = %s ORDER BY timestamp DESC",
            (case_id, uid),
        )
        rows = cur.fetchall()
        return [
            {
                "id": r[0], "query": r[1], "response": r[2],
                "task": r[3], "mode": r[4], "timestamp": r[5],
            }
            for r in rows
        ]

    def delete_case_analysis(self, analysis_id: str):
        self._execute("DELETE FROM case_analyses WHERE id = %s", (analysis_id,))
        self.conn.commit()

    def delete_case_analyses_for_case(self, case_id: str):
        uid = self._uid()
        self._execute(
            "DELETE FROM case_analyses WHERE case_id = %s AND user_id = %s",
            (case_id, uid)
        )
        self.conn.commit()

    # ── Lifecycle (user-scoped via namespaced kv) ──
    def save_lifecycle(self, case_id: str, data: dict):
        self.save_list(f"lifecycle_{case_id}", [data])

    def load_lifecycle(self, case_id: str) -> dict:
        result = self.load_list(f"lifecycle_{case_id}")
        if result and isinstance(result, list) and len(result) > 0:
            return result[0]
        return {}

    def save_lifecycle_progress(self, case_id: str, progress: dict):
        self.save_list(f"lifecycle_progress_{case_id}", [progress])

    def load_lifecycle_progress(self, case_id: str) -> dict:
        result = self.load_list(f"lifecycle_progress_{case_id}")
        if result and isinstance(result, list) and len(result) > 0:
            return result[0]
        return {}

    # ── Migration: copy legacy un-namespaced data to a new user account ──
    def has_legacy_data(self) -> bool:
        for key in ("cases", "clients", "time_entries", "invoices", "chat_history"):
            cur = self._execute("SELECT value FROM kv_store WHERE key = %s", (key,))
            row = cur.fetchone()
            if row and row[0] and row[0] not in ("[]", "{}", ""):
                try:
                    if json.loads(row[0]):
                        return True
                except Exception:
                    pass
        return False

    def migrate_legacy_data_to_user(self, user_id: str) -> int:
        migrated = 0
        legacy_keys = ["cases", "clients", "time_entries", "invoices", "chat_history",
                       "custom_templates", "custom_limitation_periods", "custom_maxims"]
        for key in legacy_keys:
            cur = self._execute("SELECT value FROM kv_store WHERE key = %s", (key,))
            row = cur.fetchone()
            if row and row[0] and row[0] != "[]":
                namespaced = f"u:{user_id}:{key}"
                self._execute(
                    "INSERT INTO kv_store (key, value) VALUES (%s, %s) "
                    "ON CONFLICT (key) DO NOTHING",
                    (namespaced, row[0]),
                )
                migrated += 1
        # Migrate lifecycle keys
        cur2 = self._execute(
            "SELECT key, value FROM kv_store WHERE key LIKE 'lifecycle_%'"
        )
        for lkey, lval in (cur2.fetchall() or []):
            nkey = f"u:{user_id}:{lkey}"
            self._execute(
                "INSERT INTO kv_store (key, value) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (nkey, lval),
            )
            migrated += 1
        # Migrate case analyses
        self._execute(
            "UPDATE case_analyses SET user_id = %s WHERE user_id IN ('legacy', '') OR user_id IS NULL",
            (user_id,)
        )
        # Migrate cost logs
        self._execute(
            "UPDATE cost_logs SET user_id = %s WHERE user_id IN ('legacy', '') OR user_id IS NULL",
            (user_id,)
        )
        self.conn.commit()
        return migrated

    # ── Session Tokens ──
    def create_session_token(self, user_id: str, days: int = 30, device_hint: str = "") -> str:
        """
        Create a persistent session token.
        SECURITY: Returns raw token to app session. Stores only SHA-256(token) in DB.
        """
        import datetime as _dt
        token = uuid.uuid4().hex + uuid.uuid4().hex
        token_hash = hash_session_token(token)
        now = datetime.now()
        expires = now + _dt.timedelta(days=days)
        try:
            self._execute(
                "INSERT INTO user_sessions "
                "(token, user_id, created_at, expires_at, last_used, device_hint) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (token_hash, user_id, now.isoformat(), expires.isoformat(),
                 now.isoformat(), device_hint),
            )
            self.conn.commit()
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            logger.error(f"create_session_token failed: {e}")
        return token

    def validate_session_token(self, token: str) -> Optional[dict]:
        """Validate a raw session token. DB stores only token hash."""
        if not token or len(token) < 32:
            return None
        token_hash = hash_session_token(token)
        try:
            cur = self._execute(
                "SELECT user_id, expires_at FROM user_sessions WHERE token = %s", (token_hash,)
            )
            row = cur.fetchone()
            if not row:
                return None
            user_id, expires_at = row
            try:
                exp = datetime.fromisoformat(expires_at)
                if datetime.now() > exp:
                    self.revoke_session_token(token)
                    return None
            except Exception:
                return None
            try:
                self._execute(
                    "UPDATE user_sessions SET last_used = %s WHERE token = %s",
                    (datetime.now().isoformat(), token_hash),
                )
                self.conn.commit()
            except Exception:
                try:
                    self.conn.rollback()
                except Exception:
                    pass
            return self.get_user_by_id(user_id)
        except Exception:
            return None

    def revoke_session_token(self, token: str):
        """Delete a single session token. Accepts raw token or already-hashed token."""
        try:
            token_key = hash_session_token(token) if not re.fullmatch(r"[a-f0-9]{64}", token) else token
            self._execute("DELETE FROM user_sessions WHERE token = %s", (token_key,))
            self.conn.commit()
        except Exception:
            try:
                self.conn.rollback()
            except Exception:
                pass

    def revoke_all_user_sessions(self, user_id: str):
        """Delete all session tokens for a user (sign out all devices)."""
        try:
            self._execute("DELETE FROM user_sessions WHERE user_id = %s", (user_id,))
            self.conn.commit()
        except Exception:
            try:
                self.conn.rollback()
            except Exception:
                pass

    def get_token_last_used(self, token: str) -> Optional[float]:
        """Return Unix timestamp of when this token was last used. None if not found."""
        import time as _t
        if not token or len(token) < 32:
            return None
        token_hash = hash_session_token(token)
        try:
            cur = self._execute(
                "SELECT last_used FROM user_sessions WHERE token = %s", (token_hash,)
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return None
            return datetime.fromisoformat(str(row[0])).timestamp()
        except Exception:
            return None

    def touch_session_token(self, token: str) -> None:
        """Update last_used timestamp for this token. Called periodically while user is active."""
        if not token or len(token) < 32:
            return
        token_hash = hash_session_token(token)
        try:
            self._execute(
                "UPDATE user_sessions SET last_used = %s WHERE token = %s",
                (datetime.now().isoformat(), token_hash),
            )
            self.conn.commit()
        except Exception:
            try:
                self.conn.rollback()
            except Exception:
                pass

    def get_user_sessions(self, user_id: str) -> list:
        """List all active (non-expired) sessions for a user."""
        try:
            now = datetime.now().isoformat()
            cur = self._execute(
                "SELECT token, created_at, expires_at, last_used, device_hint "
                "FROM user_sessions WHERE user_id = %s AND expires_at > %s "
                "ORDER BY last_used DESC",
                (user_id, now),
            )
            rows = cur.fetchall()
            return [
                {
                    "token": r[0], "created_at": r[1], "expires_at": r[2],
                    "last_used": r[3], "device_hint": r[4],
                }
                for r in rows
            ]
        except Exception:
            return []
# ── Phase 2: Audit Log ──────────────────────────────────────────────
    def append_audit(self, action: str, detail: str = "") -> None:
        """Append an immutable, hash-chained audit entry. Never updates — only inserts."""
        import hashlib as _hl
        uid = self._uid()
        entry_id = new_id()
        ts = datetime.now().isoformat()
        # Get the hash of the most recent entry to chain onto
        cur = self._execute(
            "SELECT entry_hash FROM audit_log ORDER BY timestamp DESC LIMIT 1"
        )
        row = cur.fetchone()
        prev_hash = row[0] if row else "GENESIS"
        raw = f"{entry_id}|{ts}|{uid}|{action}|{detail}|{prev_hash}"
        entry_hash = _hl.sha256(raw.encode()).hexdigest()
        self._execute(
            "INSERT INTO audit_log (id, timestamp, user_id, action, detail, prev_hash, entry_hash) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (entry_id, ts, uid, action, detail[:2000], prev_hash, entry_hash),
        )
        self.conn.commit()

    def get_audit_log(self, limit: int = 150) -> list:
        uid = self._uid()
        cur = self._execute(
            "SELECT id, timestamp, action, detail, entry_hash FROM audit_log "
            "WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s",
            (uid, limit),
        )
        return [
            {"id": r[0], "timestamp": r[1], "action": r[2],
             "detail": r[3], "entry_hash": r[4]}
            for r in (cur.fetchall() or [])
        ]

    def get_all_audit_log_admin(self, limit: int = 500) -> list:
        """Admin view — all users."""
        cur = self._execute(
            "SELECT id, timestamp, user_id, action, detail, entry_hash FROM audit_log "
            "ORDER BY timestamp DESC LIMIT %s", (limit,)
        )
        return [
            {"id": r[0], "timestamp": r[1], "user_id": r[2],
             "action": r[3], "detail": r[4], "entry_hash": r[5]}
            for r in (cur.fetchall() or [])
        ]

    def verify_audit_chain(self) -> dict:
        """
        Verify hash-chain integrity of the audit log.
        Returns {"ok": bool, "checked": int, "broken_at": str, "message": str}
        """
        import hashlib as _hl
        try:
            cur = self._execute(
                "SELECT id, timestamp, user_id, action, detail, prev_hash, entry_hash "
                "FROM audit_log ORDER BY timestamp ASC"
            )
            rows = cur.fetchall() or []
            prev_hash = "GENESIS"
            checked = 0
            for r in rows:
                entry_id, ts, uid, action, detail, stored_prev, stored_hash = r
                if stored_prev != prev_hash:
                    return {"ok": False, "checked": checked,
                            "broken_at": entry_id, "message": "Previous hash mismatch."}
                raw = f"{entry_id}|{ts}|{uid}|{action}|{detail}|{stored_prev}"
                computed = _hl.sha256(raw.encode()).hexdigest()
                if computed != stored_hash:
                    return {"ok": False, "checked": checked,
                            "broken_at": entry_id, "message": "Entry hash mismatch."}
                prev_hash = stored_hash
                checked += 1
            return {"ok": True, "checked": checked, "broken_at": "",
                    "message": "Audit chain verified."}
        except Exception as e:
            return {"ok": False, "checked": 0, "broken_at": "",
                    "message": f"Verification failed: {e}"}

    # ── Phase 2: RAG — statute chunk storage ────────────────────────────
    def upsert_statute_chunk(self, chunk_id: str, source: str, section_label: str,
                             content: str, keywords: str) -> None:
        self._execute(
            "INSERT INTO statute_chunks (id, source, section_label, content, keywords, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (id) DO UPDATE SET content=EXCLUDED.content, keywords=EXCLUDED.keywords",
            (chunk_id, source, section_label, content, keywords, datetime.now().isoformat()),
        )
        self.conn.commit()

    def search_statute_chunks(self, query_keywords: list[str], limit: int = 8) -> list:
        """Keyword-ranked search over statute chunks (no embedding API required)."""
        if not query_keywords:
            return []
        results = []
        cur = self._execute("SELECT id, source, section_label, content, keywords FROM statute_chunks")
        rows = cur.fetchall() or []
        q_set = {w.lower() for w in query_keywords if len(w) > 3}
        for row in rows:
            chunk_kw = {k.strip() for k in row[4].lower().split(",") if k.strip()}
            content_words = set(row[3].lower().split())
            kw_hits = len(q_set & chunk_kw)
            content_hits = len(q_set & content_words)
            score = kw_hits * 3 + content_hits
            # Precision gate: require a tagged-keyword hit or >=2 distinct
            # content-term overlaps, so a single incidental word (e.g. "act",
            # "person") does not surface an unrelated statute provision.
            if kw_hits >= 1 or content_hits >= 2:
                results.append({
                    "source": row[1], "section": row[2],
                    "content": row[3], "score": score,
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def count_statute_chunks(self) -> int:
        cur = self._execute("SELECT COUNT(*) FROM statute_chunks")
        row = cur.fetchone()
        return row[0] if row else 0

    # ── Beta Feedback (private-beta lawyer trial) ───────────────────────
    def add_beta_feedback(self, entry: dict) -> bool:
        """Persist a piece of beta feedback. Returns True on success."""
        try:
            self._execute(
                "INSERT INTO beta_feedback "
                "(id, timestamp, user_id, username, category, severity, page, "
                "message, contact_ok, app_version, status) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    entry.get("id", new_id()),
                    entry.get("timestamp", datetime.now().isoformat()),
                    entry.get("user_id", self._uid()),
                    entry.get("username", ""),
                    entry.get("category", "comment"),
                    entry.get("severity", "normal"),
                    entry.get("page", ""),
                    entry.get("message", ""),
                    bool(entry.get("contact_ok", False)),
                    entry.get("app_version", ""),
                    entry.get("status", "open"),
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"add_beta_feedback failed: {e}")
            try:
                self.conn.rollback()
            except Exception:
                pass
            return False

    def list_beta_feedback(self, limit: int = 200, status: str = "") -> list:
        """Return all beta feedback (admin only — caller must enforce)."""
        try:
            if status:
                cur = self._execute(
                    "SELECT id, timestamp, user_id, username, category, severity, "
                    "page, message, contact_ok, app_version, status "
                    "FROM beta_feedback WHERE status = %s "
                    "ORDER BY timestamp DESC LIMIT %s",
                    (status, limit),
                )
            else:
                cur = self._execute(
                    "SELECT id, timestamp, user_id, username, category, severity, "
                    "page, message, contact_ok, app_version, status "
                    "FROM beta_feedback ORDER BY timestamp DESC LIMIT %s",
                    (limit,),
                )
            return [
                {
                    "id": r[0], "timestamp": r[1], "user_id": r[2],
                    "username": r[3], "category": r[4], "severity": r[5],
                    "page": r[6], "message": r[7], "contact_ok": bool(r[8]),
                    "app_version": r[9], "status": r[10],
                }
                for r in (cur.fetchall() or [])
            ]
        except Exception as e:
            logger.warning(f"list_beta_feedback failed: {e}")
            return []

    def update_beta_feedback_status(self, feedback_id: str, status: str) -> bool:
        try:
            self._execute(
                "UPDATE beta_feedback SET status = %s WHERE id = %s",
                (status, feedback_id),
            )
            self.conn.commit()
            return True
        except Exception:
            try:
                self.conn.rollback()
            except Exception:
                pass
            return False

# ── Firm-wide Admin Announcement ────────────────────────────────────
    # Stored in kv_store under the key 'firm_announcement' as a single-item
    # list. Schema:
    #   {
    #     "text":     str,                         # announcement body (markdown OK)
    #     "level":    "info" | "warning" | "success",
    #     "expires":  ISO date 'YYYY-MM-DD',       # auto-hides after this date
    #     "active":   bool,                        # admin can toggle off without deleting
    #     "updated_by": str,                       # username
    #     "updated_at": ISO datetime,
    #   }
    # An announcement is shown to all users iff active==True and date.today()
    # ≤ expires. Users can dismiss it for the current Streamlit session via
    # session_state; admin can clear it permanently by setting active=False.
    def set_announcement(self, data: dict) -> bool:
        """Save the firm-wide announcement. Returns True on success."""
        try:
            self._save_list_raw("firm_announcement", [data])
            return True
        except Exception as e:
            logger.error(f"set_announcement failed: {e}")
            return False

    def get_announcement(self) -> dict:
        """Return current firm-wide announcement dict, or empty dict if none."""
        try:
            rows = self._load_list_raw("firm_announcement") or []
            if rows and isinstance(rows, list) and isinstance(rows[0], dict):
                return rows[0]
        except Exception as e:
            logger.warning(f"get_announcement failed: {e}")
        return {}

    def clear_announcement(self) -> bool:
        """Permanently clear the firm-wide announcement."""
        try:
            self._save_list_raw("firm_announcement", [])
            return True
        except Exception:
            return False


    def cleanup_expired_sessions(self):
        """Remove expired tokens (call periodically)."""
        try:
            self._execute(
                "DELETE FROM user_sessions WHERE expires_at < %s",
                (datetime.now().isoformat(),),
            )
            self.conn.commit()
        except Exception:
            try:
                self.conn.rollback()
            except Exception:
                pass

    def close(self):
        self.conn.close()

    def ensure_connected(self):
        """Ping the connection; reconnect + re-init tables if dead."""
        try:
            self.conn.cursor().execute("SELECT 1")
        except Exception:
            try:
                self.conn.rollback()
            except Exception:
                pass
            try:
                self.conn = self._connect()
                run_migrations(self.conn)  # versioned migrations
            except Exception as e:
                logger.error(f"DB reconnect failed: {e}")


@st.cache_resource
def get_db() -> Database:
    """Singleton DB connection per Streamlit server process."""
    return Database()

def persist(key: str):
    """Save a session_state list to DB under the current user's namespace."""
    get_db().save_list(key, st.session_state.get(key, []))


def persist_profile():
    """Save current user's full profile to DB."""
    get_db().save_profile(st.session_state.get("profile", {}))


def _bootstrap_verified_cases() -> None:
    """Load admin-added cases from DB into VERIFIED_NIGERIAN_CASES on startup.
    Called every session so custom cases survive server restarts.
    """
    try:
        db = get_db()
        new_cases = db._load_list_raw("law_updates_new_cases") or []
        injected = 0
        for nc in new_cases:
            name = nc.get("name", "").strip()
            if name and name not in VERIFIED_NIGERIAN_CASES:
                VERIFIED_NIGERIAN_CASES[name] = {
                    "citation": nc.get("citation", ""),
                    "court": nc.get("court", "Supreme Court"),
                    "year": int(nc["year"]) if str(nc.get("year", "")).isdigit() else date.today().year,
                    "principle": nc.get("principle", ""),
                }
                injected += 1
        if injected:
            logging.info("LexiAssist: bootstrapped %d custom verified cases from DB", injected)
    except Exception as e:
        logging.warning("LexiAssist: could not bootstrap verified cases: %s", e)


def load_user_data():
    """Load all user-specific data from DB into session state. Called once after login."""
    if not st.session_state.get("current_user_id"):
        return
    db = get_db()
    _bootstrap_verified_cases()  # Ensure custom admin cases are available every session
    st.session_state.cases = db.load_list("cases") or []
    st.session_state.clients = db.load_list("clients") or []
    st.session_state.time_entries = db.load_list("time_entries") or []
    st.session_state.tasks = db.load_list("tasks") or []
    st.session_state.invoices = db.load_list("invoices") or []
    st.session_state.chat_history = db.load_list("chat_history") or []
    st.session_state.custom_templates = db.load_list("custom_templates") or []
    st.session_state.custom_limitation_periods = db.load_list("custom_limitation_periods") or []
    st.session_state.custom_maxims = db.load_list("custom_maxims") or []
    st.session_state.profile = db.get_profile()


