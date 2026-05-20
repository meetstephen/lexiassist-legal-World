"""LexiAssist sidebar — render_sidebar."""
from __future__ import annotations

# Barrel import: mirrors the global namespace of the original single-file
# app.py exactly. The original code below is unchanged.
from ..runtime import *      # noqa: F401, F403
# `import *` skips dunder names, so import __version__ explicitly.
from ..runtime import __version__  # noqa: F401
from ..crypto import *       # noqa: F401, F403
from ..constants import *    # noqa: F401, F403
from ..prompts import *      # noqa: F401, F403
from ..legal_data import *   # noqa: F401, F403
from ..citations import *    # noqa: F401, F403
from ..themes import *       # noqa: F401, F403
from ..rag import *          # noqa: F401, F403
from ..fuzzy import *        # noqa: F401, F403
from ..exports import *      # noqa: F401, F403
from ..database import *     # noqa: F401, F403
from ..auth import *         # noqa: F401, F403
from ..helpers import *      # noqa: F401, F403

# ═══════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════
def render_sidebar(group_names=None):
    if group_names is None:
        group_names = []
    # ── Override any login-screen CSS that hid the sidebar ──────────────
    # Force sidebar and ALL collapse-control variants visible + clickable
    st.markdown("""<style>
section[data-testid="stSidebar"]{
 display:flex!important;visibility:visible!important;opacity:1!important;}
section[data-testid="stSidebarContent"]{display:flex!important;}
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"]{
 display:flex!important;visibility:visible!important;opacity:1!important;
 z-index:999999!important;pointer-events:auto!important;}
[data-testid="stHeader"]{
 background:transparent!important;background-color:transparent!important;
 z-index:1!important;}
[data-testid="stDecoration"]{display:none!important;}
</style>""", unsafe_allow_html=True)

    with st.sidebar:
        firm = get_firm_name()
        corp = (st.session_state.get("theme", "⚖️ Corporate") == "⚖️ Corporate")
        name_display = firm if (firm and firm != "LexiAssist") else f"LexiAssist v{__version__}"
        tag_display  = f"Powered by LexiAssist v{__version__}" if (firm and firm != "LexiAssist") else "Elite AI Legal Engine"
        hdr_col = "#c9a84c" if corp else "#1a2e4a"
        cap_col = "#2b3e51" if corp else "#08074a"
        div_col = "#6508e7" if corp else "#090b0e"
        st.markdown(f"""
<div style="padding:1rem 0.4rem 0.8rem 0.4rem;border-bottom:1px solid {div_col};">
  <div style="font-size:1.05rem;font-weight:800;color:{hdr_col};letter-spacing:-0.01em;">⚖️ {esc(name_display)}</div>
  <div style="font-size:0.74rem;margin-top:0.15rem;color:{cap_col};">{esc(tag_display)}</div>
</div>""", unsafe_allow_html=True)
        # ── Navigation group selector — placed right after branding ──
        if group_names:
            st.markdown(
                '<p style="font-size:0.72rem;font-weight:700;letter-spacing:0.08em;'
                'color:var(--la-text-secondary);margin:0.8rem 0 0.2rem 0;">NAVIGATION</p>',
                unsafe_allow_html=True,
            )
            selected_group = st.radio(
                "Section", group_names,
                key="nav_group",
                label_visibility="collapsed",
            )
            st.markdown(
                '<div style="border-bottom:1px solid var(--la-border);margin:0.4rem 0 0.2rem 0;"></div>',
                unsafe_allow_html=True,
            )
        else:
            selected_group = None
        st.session_state["_selected_nav_group"] = selected_group
        uname = st.session_state.get("current_username","")
        urole = st.session_state.get("current_user_role","")
        if uname:
            role_icon = "🛡️ Admin" if urole=="admin" else "👤 User"
            bg_c = "#ffffff10" if corp else "#22c55e18"
            bd_c = "#ffffff00" if corp else "#22c55e55"
            tx_c = "#eeb10b"   if corp else "#02261A"
            st.markdown(f"""
<div style="margin:0.8rem 0 0.4rem 0;padding:0.6rem 0.8rem;background:{bg_c};border:1px solid {bd_c};border-radius:8px;">
  <div style="font-weight:700;font-size:0.9rem;color:{tx_c};">@{esc(uname)}</div>
  <div style="font-size:0.75rem;opacity:0.75;margin-top:0.1rem;">{role_icon}</div>
</div>""", unsafe_allow_html=True)
            if st.button("🚪 Sign Out", key="sidebar_logout_btn", use_container_width=True):
                do_logout()
        st.divider()
        c1,c2 = st.columns(2)
        with c1: st.metric("Cases",    len(get_active_cases()))
        with c2: st.metric("Sessions", len(st.session_state.chat_history))
        st.divider()
        st.markdown("**🧠 Response Mode**")
        modes = list(RESPONSE_MODES.keys())
        cur_m = modes.index(st.session_state.response_mode) if st.session_state.response_mode in modes else 1
        mode = st.radio("Depth", modes, index=cur_m,
            format_func=lambda x: RESPONSE_MODES[x]["label"],
            key="sidebar_mode_radio", label_visibility="collapsed")
        if mode != st.session_state.response_mode:
            st.session_state.response_mode = mode
        sel = RESPONSE_MODES[st.session_state.response_mode]
        st.caption(sel["desc"]); st.caption(f"Token limit: {sel['tokens']:,}")
        st.divider()
        st.markdown("**🎨 Theme**")
        theme_names = list(THEMES.keys())
        cur_t = theme_names.index(st.session_state.theme) if st.session_state.theme in theme_names else 0
        theme = st.selectbox(
            "Theme", theme_names, index=cur_t,
            key="sidebar_theme_sel", label_visibility="collapsed",
            help=THEMES[theme_names[cur_t]]["description"])
        if theme != st.session_state.theme:
            st.session_state.theme = theme
        # ── Accessibility controls ────────────────────────────────
        with st.expander("♿ Accessibility", expanded=False):
            fss = st.slider(
                "Font size", 0.85, 1.4, st.session_state.font_size_scale, 0.05,
                key="sidebar_font_scale",
                help="Scale all text up or down")
            if fss != st.session_state.font_size_scale:
                st.session_state.font_size_scale = fss
            hc = st.checkbox(
                "High contrast", value=st.session_state.high_contrast,
                key="sidebar_high_contrast",
                help="Maximise text/background contrast")
            if hc != st.session_state.high_contrast:
                st.session_state.high_contrast = hc
            rm = st.checkbox(
                "Reduce motion", value=st.session_state.reduce_motion,
                key="sidebar_reduce_motion",
                help="Disable all CSS animations and transitions")
            if rm != st.session_state.reduce_motion:
                st.session_state.reduce_motion = rm
        st.divider()
        st.markdown("**🤖 AI Engine**")
        if st.session_state.api_configured:
            st.success(f"✅ Connected · `{st.session_state.gemini_model}`")
            ms = st.selectbox("Model", SUPPORTED_MODELS,
                index=SUPPORTED_MODELS.index(st.session_state.gemini_model)
                      if st.session_state.gemini_model in SUPPORTED_MODELS else 0,
                key="sidebar_model_sel", label_visibility="collapsed")
            if ms != st.session_state.gemini_model:
                st.session_state.gemini_model = ms; st.rerun()
            summary = get_db().get_cost_summary()
            if summary["total_calls"] > 0:
                st.caption(f"💰 Today: ${summary['daily_cost']:.4f} ({summary['daily_calls']} calls)")
                st.caption(f"📅 Month: ${summary['monthly_cost']:.4f} ({summary['monthly_calls']} calls)")
        else:
            st.error("🔴 Not connected")
        st.divider()
        st.markdown("**💾 Data**")
        if st.button("📥 Export All Data (JSON)", use_container_width=True, key="sidebar_export_btn"):
            export_data = {
                "export_date": datetime.now().isoformat(), "version": __version__,
                "cases": st.session_state.cases,
                "clients": st.session_state.clients,
                "time_entries": st.session_state.time_entries,
                "invoices": st.session_state.invoices,
                "chat_history": st.session_state.chat_history,
                "custom_templates": st.session_state.custom_templates,
                "custom_limitation_periods": st.session_state.custom_limitation_periods,
                "custom_maxims": st.session_state.custom_maxims,
                "profile": st.session_state.profile,
                "cost_logs": get_db().get_cost_logs(500),
            }
            st.download_button("⬇️ Download JSON",
                json.dumps(export_data, indent=2, default=str),
                f"lexiassist_backup_{datetime.now():%Y%m%d_%H%M}.json",
                "application/json", key="sidebar_dl_json", use_container_width=True)
        st.markdown("**📤 Import Files**")
        uploaded = st.file_uploader("Upload", type=UPLOAD_TYPES, accept_multiple_files=False,
            key="sidebar_file_upload", label_visibility="collapsed",
            help="Supports: PDF, DOCX, TXT, XLSX, CSV, JSON, RTF")
        if uploaded:
            try:
                ext = uploaded.name.split(".")[-1].lower()
                if ext == "json":
                    raw = json.loads(uploaded.getvalue().decode("utf-8", errors="ignore"))
                    if isinstance(raw,dict) and any(k in raw for k in ["cases","clients"]):
                        for k in ["cases","clients","time_entries","invoices","chat_history",
                                  "custom_templates","custom_limitation_periods","custom_maxims"]:
                            if k in raw: st.session_state[k]=raw[k]; persist(k)
                        if "profile" in raw and isinstance(raw["profile"],dict):
                            st.session_state.profile.update(raw["profile"]); persist_profile()
                        st.success("✅ Data imported!"); st.rerun()
                    else:
                        text=json.dumps(raw,indent=2)
                        st.session_state.imported_doc={"name":uploaded.name,"type":ext,
                            "size":len(uploaded.getvalue()),"full_text":text,"preview":text[:600]}
                        st.success(f"✅ {uploaded.name} loaded → AI Assistant"); st.rerun()
                else:
                    text=extract_file_text(uploaded)
                    st.session_state.imported_doc={"name":uploaded.name,"type":ext,
                        "size":len(uploaded.getvalue()),"full_text":text,
                        "preview":text[:600]+("…" if len(text)>600 else "")}
                    st.success(f"✅ {uploaded.name} loaded → AI Assistant"); st.rerun()
            except Exception as e:
                st.error(f"❌ Import error: {e}")
        st.divider()
        st.caption(f"⚖️ LexiAssist v{__version__} © {datetime.now().year}")
        st.caption("🇳🇬 Nigerian Law · 🤖 AI-Powered")
        # NBA Annual Practicing Certificate reminder
        today = date.today()
        # NBA APC renewal runs January–March each year
        if today.month <= 3:
            days_left = (date(today.year, 3, 31) - today).days
            if days_left <= 60:
                st.warning(
                    f"⚠️ **NBA APC Reminder:** Annual Practicing Certificate renewal "
                    f"deadline is **31 March {today.year}**. "
                    f"{days_left} day(s) remaining.",
                )
        elif today.month == 12:
            st.info("ℹ️ **NBA APC:** Renewal opens January. Deadline: 31 March.")

    # ── JS: close sidebar when user clicks the main content area (mobile) ──
    # This restores the original Streamlit behaviour where clicking outside
    # the sidebar on mobile auto-collapses it without requiring a button tap.
    st.components.v1.html("""
<script>
(function() {
  function tryAttach() {
    var main = window.parent.document.querySelector(
      '.main, [data-testid="stMainBlockContainer"], section.main'
    );
    var collapseBtn = window.parent.document.querySelector(
      '[data-testid="collapsedControl"] button, button[aria-label="Close sidebar"]'
    );
    if (!main || !collapseBtn) { return; }

    main.addEventListener('click', function(e) {
      // Only close if sidebar is currently open (on mobile widths)
      var sidebar = window.parent.document.querySelector(
        '[data-testid="stSidebar"]'
      );
      if (!sidebar) return;
      var sidebarW = sidebar.getBoundingClientRect().width;
      // If sidebar is open (width > 50px) and screen is narrow (<=768px)
      if (sidebarW > 50 && window.parent.innerWidth <= 768) {
        collapseBtn.click();
      }
    }, false);
  }
  // Retry until the DOM is ready
  var attempts = 0;
  var interval = setInterval(function() {
    tryAttach();
    attempts++;
    if (attempts > 20) clearInterval(interval);
  }, 400);
})();
</script>
""", height=0)



