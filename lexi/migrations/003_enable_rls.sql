-- Migration 003: Block PostgREST access to LexiAssist application tables.
-- LexiAssist connects with its server-side PostgreSQL role.  Enabling RLS
-- without public policies denies anonymous and browser API access while the
-- table owner/server role continues to operate normally.  Do NOT use FORCE
-- ROW LEVEL SECURITY here without first verifying the deployment DB role.

ALTER TABLE IF EXISTS public.schema_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.kv_store ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.cost_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.case_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.statute_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.beta_feedback ENABLE ROW LEVEL SECURITY;
