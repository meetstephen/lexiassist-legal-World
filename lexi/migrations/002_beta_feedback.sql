-- Migration 002: Beta feedback table
-- Captures lawyer feedback during the private beta — bug reports, feature
-- requests, and general comments. Each entry includes the page the lawyer
-- was on when they submitted, so admins can correlate feedback with context.

CREATE TABLE IF NOT EXISTS beta_feedback (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT DEFAULT '',
    category TEXT NOT NULL,
    severity TEXT DEFAULT 'normal',
    page TEXT DEFAULT '',
    message TEXT NOT NULL,
    contact_ok BOOLEAN DEFAULT FALSE,
    app_version TEXT DEFAULT '',
    status TEXT DEFAULT 'open'
);

CREATE INDEX IF NOT EXISTS idx_beta_feedback_user_id ON beta_feedback (user_id);
CREATE INDEX IF NOT EXISTS idx_beta_feedback_timestamp ON beta_feedback (timestamp);
CREATE INDEX IF NOT EXISTS idx_beta_feedback_status ON beta_feedback (status);
CREATE INDEX IF NOT EXISTS idx_beta_feedback_category ON beta_feedback (category);
