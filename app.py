"""
LexiAssist v9.1.1 — Elite AI Legal Workflow Engine for Nigerian Lawyers
Streamlit entry point. PostgreSQL persistence.

Private-beta ready features:
Contract Review · Cost Tracking · User Profiles · Analysis Comparison · Save to Case
Editable References · Custom Templates · Auth Support · Authority Verification
Practice Update Generator · Source-Backed Research · Citation Audit

IMPORTANT:
AI-generated outputs are drafting aids only. Lawyers must independently verify
all authorities, limitation periods, court rules, filing fees, and legal conclusions
before relying on them for client advice or court filings.

Code organisation:
The bulk of the implementation lives in the ``lexi`` package:
  - lexi.runtime, lexi.crypto, lexi.constants, lexi.prompts,
    lexi.legal_data, lexi.citations, lexi.themes, lexi.rag, lexi.fuzzy,
    lexi.exports, lexi.database, lexi.auth, lexi.helpers
  - lexi.pages.*  — one render_* function group per module
This file is now only the Streamlit entry point: ``st.set_page_config``,
the ``main()`` routing function, and the ``if __name__ == "__main__"`` block.
"""
from __future__ import annotations

# ── Streamlit MUST be the first thing imported and `set_page_config` MUST
#    be the first Streamlit call in the script. We pull `st` and `__version__`
#    from the runtime module (which performs all third-party imports) and
#    then call `set_page_config` before importing anything else from `lexi`.
from lexi.runtime import st, __version__, datetime, esc
from lexi.runtime import is_beta, is_production

st.set_page_config(
    page_title=f"LexiAssist v{__version__} — Elite AI Legal Engine for Nigerian Lawyers",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://aistudio.google.com/app/apikey",
        "About": f"LexiAssist v{__version__} — AI-powered legal assistant for Nigerian legal practice. Powered by Google Gemini.",
    },
)

# ── Now load the rest of the package ────────────────────────────────────────
from lexi.legal_data import LEGAL_DATA_VERSION
from lexi.themes import get_theme_css
from lexi.database import get_db, load_user_data
from lexi.auth import (
    do_auto_login_from_token,
    do_logout,
    render_create_admin_screen,
    render_login_screen,
    render_reauth_screen,
    render_setup_screen,
)
from lexi.helpers import (
    auto_connect,
    get_firm_name,
    init_session_state,
    _maybe_send_hearing_reminders,
)
from lexi.pages.sidebar import render_sidebar
from lexi.pages.home import render_home, render_tasks
from lexi.pages.ai import render_ai
from lexi.pages.research import (
    render_research,
    render_authority_verification,
    render_source_backed_research,
)
from lexi.pages.cases import render_cases
from lexi.pages.calendar import render_calendar
from lexi.pages.templates import render_templates
from lexi.pages.clients import render_clients
from lexi.pages.billing import render_billing
from lexi.pages.tools import render_tools
from lexi.pages.search import render_global_search
from lexi.pages.conflict import render_conflict_checker
from lexi.pages.pleadings import render_pleadings
from lexi.pages.lifecycle import render_lifecycle
from lexi.pages.witness import render_witness_prep
from lexi.pages.news import render_legal_news
from lexi.pages.notes import render_notes_converter
from lexi.pages.profile import render_profile
from lexi.pages.fee_calculator import render_fee_calculator
from lexi.pages.settlement import render_settlement_advisor
from lexi.pages.due_diligence import render_due_diligence
from lexi.pages.user_management import render_user_management


# ═══════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════
def main():
    # ── Health-check endpoint for keep-alive pingers ──
    # If URL contains ?healthcheck=1, return minimal HTML and exit before the
    # heavy app loads. This lets external pingers verify the container is alive
    # without consuming AI tokens or DB queries.
    try:
        qp = st.query_params
        if qp.get("healthcheck") == "1":
            st.markdown(
                f"<html><body><h1>OK</h1><p>{datetime.now().isoformat()}</p></body></html>",
                unsafe_allow_html=True,
            )
            st.stop()
    except Exception:
        pass

    init_session_state()
    auto_connect()
    st.markdown(get_theme_css(

        st.session_state.theme,
        font_size_scale=st.session_state.get("font_size_scale", 1.0),
        high_contrast=st.session_state.get("high_contrast", False),
        reduce_motion=st.session_state.get("reduce_motion", False),
    ), unsafe_allow_html=True)

    # ── API setup gate ──
    if not st.session_state.api_configured:
        render_setup_screen()
        return

    db = get_db()
    db.ensure_connected()  # heal stale/aborted connections before any DB work

    # ── Auto-login via URL token (idle-aware) ────────────────────────────
    # Token lives in ?t= URL param (survives refresh). If the session was
    # idle for longer than the firm's idle limit we show a locked re-auth
    # screen instead of silently restoring — so an unattended computer is
    # protected while a deliberate refresh feels instant.
    if not st.session_state.authenticated:
        _url_token = st.query_params.get("t", "")
        if _url_token:
            _lu = db.get_token_last_used(_url_token)
            # Firm-configurable idle limit (default 30 min)
            try:
                _firm_idle_min = int(
                    st.session_state.get("profile", {})
                    .get("firm_config", {})
                    .get("idle_timeout_minutes", 30)
                )
            except Exception:
                _firm_idle_min = 30
            _firm_idle_limit = _firm_idle_min * 60
            import time as _time_mod_tok
            if _lu is not None and (_time_mod_tok.time() - _lu) > _firm_idle_limit:
                # Token valid but idle too long → show locked re-auth screen
                _locked_user = db.validate_session_token(_url_token)
                if _locked_user:
                    render_reauth_screen(_url_token, _locked_user["username"])
                    return
                # Token expired/invalid → fall through to normal login
            else:
                # Active session or first restore → silent auto-login
                do_auto_login_from_token(_url_token)

    # ── Auth gate ──
    if not st.session_state.authenticated:
        if not db.has_any_users():
            render_create_admin_screen()
        else:
            render_login_screen()
        return

    # ── Load user data exactly once per session ──
    if not st.session_state.user_data_loaded:
        load_user_data()
        st.session_state.user_data_loaded = True

    # ── Idle session timeout (30 minutes of inactivity) ────────────────
    import time as _time_mod
    _IDLE_LIMIT = 30 * 60 # 30 minutes
    _WARN_AT = 25 * 60 # warn at 25 minutes
    _now = _time_mod.time()
    _last_activity = st.session_state.get("_last_activity", _now)
    _idle_for = _now - _last_activity

    if _idle_for > _IDLE_LIMIT:
        st.warning("🔒 You were signed out automatically after 30 minutes of inactivity.")
        try:
            get_db().append_audit("AUTO_LOGOUT_IDLE", f"idle_seconds={int(_idle_for)}")
        except Exception:
            pass
        do_logout()
        return
    elif _idle_for > _WARN_AT:
        _remaining = _IDLE_LIMIT - _idle_for
        st.toast(
            f"⏳ Auto-logout in {int(_remaining/60)} min {int(_remaining%60)}s — "
            f"any click resets the timer.",
            icon="⏳",
        )

    # Update last activity on every interaction
    st.session_state["_last_activity"] = _now

    # Persist last_used to DB every ~60 s so refresh-idle detection stays accurate
    _touch_key = "_last_token_touch"
    if _now - st.session_state.get(_touch_key, 0) > 60:
        _active_tok = st.session_state.get("_session_token", "")
        if _active_tok:
            try:
                db.touch_session_token(_active_tok)
            except Exception:
                pass
        st.session_state[_touch_key] = _now

    # ── Global private-beta / legal reliability banner ──

    if is_beta() or is_production():
        st.markdown(
            '<div style="background:var(--la-bg2);border:1px solid #f59e0b;'
            'border-left:4px solid #f59e0b;border-radius:8px;'
            'padding:0.55rem 1rem;margin-bottom:0.8rem;font-size:0.82rem;">'
            '<strong>🔬 Private Beta:</strong> LexiAssist outputs are AI-generated drafting aids. '
            'Verify all authorities, limitation periods, court rules, filing fees, and legal conclusions '
            'before advising clients or filing in court.'
            '</div>',
            unsafe_allow_html=True,
        )

        _maybe_send_hearing_reminders()

    # ── Self-ping: refresh activity every render to delay cloud-sleep ──
    # This injects a tiny iframe that re-pings the healthcheck endpoint every
    # 7 minutes while a tab is open, keeping the WebSocket alive.
    try:
        st.components.v1.html(
            """
            <script>
            (function() {
              if (window._lexiPingStarted) return;
              window._lexiPingStarted = true;
              setInterval(function() {
                fetch(window.location.origin + '/?healthcheck=1', {
                  method: 'GET',
                  cache: 'no-store',
                  credentials: 'omit'
                }).catch(function() {});
              }, 420000); // 7 minutes
            })();
            </script>
            """,
            height=0,
        )
    except Exception:
        pass

    is_admin = (st.session_state.current_user_role == "admin")


    # ── TOP NAVIGATION TABS ──
    # ── Grouped Navigation (Phase 3 — #11) ──────────────────────────────
    GROUPS = {
        "⚖️ Practice": [
            ("🏠 Home",            render_home),
            ("🧠 AI Assistant",    render_ai),
            ("📚 Research",        render_research),
            ("🔗 Source Research", render_source_backed_research),
            ("📝 Notes → Brief",   render_notes_converter),
        ],
        "📁 Matters": [
            ("📁 Cases",           render_cases),
            ("✅ Tasks",           render_tasks),
            ("⚡ Lifecycle",       render_lifecycle),
            ("📜 Pleadings",       render_pleadings),
            ("📅 Calendar",        render_calendar),
            ("🔍 Conflict Check",  render_conflict_checker),
        ],
        "👥 Clients & Billing": [
            ("👥 Clients",         render_clients),
            ("💰 Billing",         render_billing),
            ("⚖️ Fee Calculator",  render_fee_calculator),
        ],
        "🔧 Tools": [
            ("🔧 Tools",           render_tools),
            ("🔍 Authority Verify", render_authority_verification),
            ("🎯 Witness Prep",    render_witness_prep),
            ("🤝 Settlement",      render_settlement_advisor),
            ("🔎 Due Diligence",   render_due_diligence),
            ("📋 Templates",       render_templates),
            ("📰 Practice Updates", render_legal_news),
            ("🔎 Search",          render_global_search),
        ],
        "👤 Account": [
            ("👤 Profile",         render_profile),
        ],
    }
    if is_admin:
        GROUPS["👤 Account"].append(("🛡️ Admin", render_user_management))

    # ── Navigation ───────────────────────────────────────────────────────
    group_names = list(GROUPS.keys())
    render_sidebar(group_names)
    selected_group = st.session_state.get("nav_group", group_names[0])
    if selected_group not in GROUPS:
        selected_group = group_names[0]

    group_pages = GROUPS[selected_group]
    page_labels = [p[0] for p in group_pages]
    page_fns    = [p[1] for p in group_pages]

    if len(page_labels) == 1:
        page_fns[0]()
    else:
        # Tab position remembered per group via session state key
        tabs = st.tabs(page_labels)
        for i, (tab, fn) in enumerate(zip(tabs, page_fns)):
            with tab:
                fn()

    # Footer
    st.markdown("---")
    firm = get_firm_name()
    firm_text = f"{esc(firm)} · " if firm and firm != "LexiAssist" else ""
    uname = st.session_state.get("current_username", "")
    user_text = f" · Signed in as @{esc(uname)}" if uname else ""
    ldv = LEGAL_DATA_VERSION
    st.markdown(
        f"""
    <div style="text-align:center;font-size:0.82rem;color:var(--la-text2);
                margin-top:1.5rem;padding:1rem 1rem 0.5rem;
                border-top:1px solid var(--la-border);">
        <span style="color:#ef4444;font-weight:700;font-size:0.85rem;">
            ⚠️ AI-Generated Analysis — Not Legal Advice
        </span><br>
        <span style="font-size:0.75rem;line-height:2;">
            <strong>Engine:</strong> {esc(ldv['version'])} &nbsp;|&nbsp;
            <strong>Updated:</strong> {esc(ldv['updated'])} &nbsp;|&nbsp;
            <strong>Latest Act:</strong> {esc(ldv['last_act'])}
        </span><br>
        <span style="font-size:0.72rem;opacity:0.7;">
            {firm_text}{"Signed in as @" + esc(uname) if uname else ""}
        </span>
    </div>""",
        unsafe_allow_html=True,
    )

    # ── Keep-Alive Ping ──────────────────────────────────────────────────────────
    st.components.v1.html("", height=0)
    # ────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    main()
