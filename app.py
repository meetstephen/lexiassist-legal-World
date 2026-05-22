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
from lexi.themes import get_theme_css
from lexi.database import get_db, load_user_data
from lexi.cookies import get_session_cookie, inject_cookie_reader
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
from lexi.pages.legal import render_privacy_policy, render_terms_of_service


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

    # ── Auto-login via cookie token (idle-aware) ────────────────────────────
    # Token lives in a browser cookie (replaces the old ?t= URL param approach
    # which leaked tokens in browser history, server logs, and shared links).
    # If the session was idle for longer than the firm's idle limit we show a
    # locked re-auth screen instead of silently restoring — so an unattended
    # computer is protected while a deliberate refresh feels instant.
    if not st.session_state.authenticated:
        # Inject the cookie reader JS (will trigger a rerun with the token on first load)
        inject_cookie_reader()
        _cookie_token = get_session_cookie()
        if _cookie_token:
            _lu = db.get_token_last_used(_cookie_token)
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
                _locked_user = db.validate_session_token(_cookie_token)
                if _locked_user:
                    render_reauth_screen(_cookie_token, _locked_user["username"])
                    return
                # Token expired/invalid → fall through to normal login
            else:
                # Active session or first restore → silent auto-login
                do_auto_login_from_token(_cookie_token)

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

    # ── Keep-alive: client-side ping while tab is open ──────────────────
    # Strategy: Two layers prevent Streamlit Cloud from sleeping the app.
    # 1. This JS fires a GET to /?healthcheck=1 every 4 min while any user
    #    has a tab open — the primary keep-alive mechanism. Also pings on
    #    visibility change (user returns to tab).
    # 2. A GitHub Actions cron (keep_alive.yml) pings the healthcheck every
    #    14 minutes as a safety net for zero-user periods.
    # No Puppeteer/Selenium/headless browser needed — a simple HTTP GET
    # to the healthcheck endpoint is sufficient to prevent deep sleep.
    try:
        st.components.v1.html(
            """
            <script>
            (function() {
              if (window._lexiPingStarted) return;
              window._lexiPingStarted = true;
              var baseUrl = window.location.origin + '/?healthcheck=1';
              function ping() {
                fetch(baseUrl, {method:'GET',cache:'no-store',credentials:'omit'}).catch(function(){});
              }
              setInterval(ping, 240000);
              document.addEventListener('visibilitychange', function() {
                if (!document.hidden) { ping(); }
              });
              setTimeout(ping, 5000);
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
            ("📜 Privacy",         render_privacy_policy),
            ("📋 Terms",           render_terms_of_service),
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

    # ── Footer (Option 3: pro-firm letterhead style) ────────────────────
    # Three lines:
    #   1. Disclaimer banner — "LexiAssist · AI-Generated Drafting Aid · Not Legal Advice · Verify all authorities"
    #   2. Firm letterhead    — "{Firm}  |  Powered by LexiAssist v{__version__}  |  © {year}"
    #   3. Legal links        — "Privacy Notice · Terms of Service" pointing into Account tab
    # Username intentionally omitted (cleaner for screenshots / screen-shares).
    # Legal-data version, "updated", and "last act" lines are intentionally
    # removed; they still surface in Tools and Admin Settings for users who
    # want to see them, but the global footer stays clean.
    st.markdown("---")
    firm = get_firm_name() or "LexiAssist"
    year = datetime.now().year
    st.markdown(
        f"""
    <div style="text-align:center;color:var(--la-text2);
                margin-top:1.5rem;padding:1rem 1rem 0.5rem;
                border-top:1px solid var(--la-border);">
        <div style="color:#ef4444;font-weight:700;font-size:0.84rem;line-height:1.6;">
            LexiAssist &middot; AI-Generated Drafting Aid &middot; Not Legal Advice &middot; Verify all authorities
        </div>
        <div style="margin-top:0.45rem;font-size:0.78rem;line-height:1.6;opacity:0.85;">
            <strong>{esc(firm)}</strong> &nbsp;|&nbsp;
            Powered by LexiAssist v{esc(__version__)} &nbsp;|&nbsp;
            &copy; {year}
        </div>
        <div style="margin-top:0.3rem;font-size:0.72rem;line-height:1.6;opacity:0.65;">
            <em>Privacy Notice &middot; Terms of Service &mdash; see &ldquo;👤 Account&rdquo; tab</em>
        </div>
    </div>""",
        unsafe_allow_html=True,
    )

    # ────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    main()
