-- Migration 001: Initial schema
-- This captures the schema that existed before versioned migrations were
-- introduced. For brand-new databases it creates everything from scratch.
-- For existing databases the migrator detects they're already at this state
-- and marks it as applied without re-running.

CREATE TABLE IF NOT EXISTS kv_store (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS users (
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
);

CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    firm_name TEXT DEFAULT '',
    lawyer_name TEXT DEFAULT '',
    email TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    address TEXT DEFAULT '',
    password_hash TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS cost_logs (
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
);

CREATE TABLE IF NOT EXISTS case_analyses (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    query TEXT,
    response TEXT,
    task TEXT,
    mode TEXT,
    timestamp TEXT,
    user_id TEXT DEFAULT 'legacy'
);

CREATE TABLE IF NOT EXISTS user_sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_used TEXT DEFAULT '',
    device_hint TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT DEFAULT '',
    prev_hash TEXT DEFAULT '',
    entry_hash TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS statute_chunks (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    section_label TEXT NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_case_analyses_user_id ON case_analyses (user_id);
CREATE INDEX IF NOT EXISTS idx_case_analyses_case_id ON case_analyses (case_id);
CREATE INDEX IF NOT EXISTS idx_case_analyses_user_case ON case_analyses (user_id, case_id);
CREATE INDEX IF NOT EXISTS idx_cost_logs_user_id ON cost_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_cost_logs_timestamp ON cost_logs (timestamp);
CREATE INDEX IF NOT EXISTS idx_cost_logs_user_ts ON cost_logs (user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log (timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log (action);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions (expires_at);
CREATE INDEX IF NOT EXISTS idx_statute_chunks_source ON statute_chunks (source);

-- Seed data
INSERT INTO user_profile (id) VALUES (1) ON CONFLICT DO NOTHING;
