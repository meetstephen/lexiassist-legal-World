"""
app.py — LexiAssist v7.0 Frontend
Streamlit UI with smart response modes, persistent history, multi-format export.
"""
import json
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import core

# ═══════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════
st.set_page_config(
    page_title="LexiAssist v7.0 — Smart Legal AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "# LexiAssist v7.0\nSmart Legal AI for Nigerian Lawyers."},
)

# ═══════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════
_BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*{font-family:'Inter',sans-serif}
.main .block-container{padding-top:1rem;padding-bottom:2rem;max-width:1200px}
@keyframes heroGradient{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.hero{padding:3rem;border-radius:1.5rem;color:white;position:relative;overflow:hidden;
  background:linear-gradient(-45deg,#059669,#0d9488,#065f46,#047857,#0f766e);
  background-size:300% 300%;animation:heroGradient 12s ease infinite;box-shadow:0 20px 60px rgba(5,150,105,.3)}
.hero::after{content:'⚖';position:absolute;right:3rem;bottom:1rem;font-size:8rem;opacity:.07}
.hero h1{font-size:2.8rem;font-weight:800;margin:0;letter-spacing:-.03em;line-height:1.15}
.hero p{font-size:1.05rem;margin:.75rem 0 0;opacity:.9;font-weight:300;max-width:600px;line-height:1.6}
.hero-badge{display:inline-block;padding:.35rem .85rem;background:rgba(255,255,255,.15);
  border-radius:9999px;font-size:.75rem;font-weight:600;margin-top:1.25rem;backdrop-filter:blur(4px);
  border:1px solid rgba(255,255,255,.2);letter-spacing:.05em;text-transform:uppercase}
.page-header{padding:1.5rem 2rem;border-radius:1.25rem;margin-bottom:1.5rem;color:white;
  background:linear-gradient(135deg,#059669,#0d9488);box-shadow:0 12px 40px rgba(5,150,105,.25)}
.page-header h1{margin:0;font-size:2rem;font-weight:700}.page-header p{margin:.25rem 0 0;opacity:.85;font-size:.9rem}
.custom-card{background:#fff;border:1px solid #e2e8f0;border-radius:1rem;padding:1.5rem;margin-bottom:1rem;
  transition:all .3s;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.custom-card:hover{transform:translateY(-4px);box-shadow:0 12px 36px rgba(0,0,0,.1)}
.stat-card{border-radius:1rem;padding:1.25rem;text-align:center;border:1px solid;transition:all .25s;
  background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.stat-value{font-size:1.75rem;font-weight:700;letter-spacing:-.02em}
.stat-label{font-size:.78rem;margin-top:.3rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#64748b}
.feat-card{background:#fff;border:1px solid #e2e8f0;border-radius:1.25rem;padding:1.75rem 1.25rem;
  text-align:center;transition:all .35s;height:100%;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.feat-card:hover{transform:translateY(-6px);box-shadow:0 16px 48px rgba(5,150,105,.12);border-color:#059669}
.feat-icon{font-size:2.75rem;margin-bottom:.75rem;display:block}
.feat-card h4{margin:0 0 .5rem;font-size:.95rem;font-weight:700;color:#1e293b}
.feat-card p{margin:0;font-size:.82rem;color:#64748b;line-height:1.55}
.badge{display:inline-block;padding:.2rem .65rem;border-radius:9999px;font-size:.7rem;font-weight:600;text-transform:uppercase}
.badge-success{background:#dcfce7;color:#166534}.badge-warning{background:#fef3c7;color:#92400e}
.badge-info{background:#dbeafe;color:#1e40af}.badge-danger{background:#fee2e2;color:#991b1b}
.issue-spot-box{background:linear-gradient(135deg,#eff6ff,#dbeafe);border:1px solid #93c5fd;
  border-left:5px solid #3b82f6;border-radius:.75rem;padding:1.25rem 1.5rem;margin:1rem 0;font-size:.88rem;line-height:1.7}
.issue-spot-box h5{margin:0 0 .5rem;color:#1e40af;font-size:.9rem;font-weight:700}
.critique-box{background:linear-gradient(135deg,#faf5ff,#f3e8ff);border:1px solid #d8b4fe;
  border-left:5px solid #8b5cf6;border-radius:.75rem;padding:1.25rem 1.5rem;margin:1rem 0;font-size:.88rem;line-height:1.7}
.critique-box h5{margin:0 0 .5rem;color:#5b21b6;font-size:.9rem;font-weight:700}
.quality-grade{display:inline-block;padding:.3rem .8rem;border-radius:.5rem;font-size:1rem;font-weight:800;margin-left:.5rem}
.grade-a{background:#dcfce7;color:#166534;border:2px solid #22c55e}
.grade-b{background:#dbeafe;color:#1e40af;border:2px solid #3b82f6}
.grade-c{background:#fef3c7;color:#92400e;border:2px solid #f59e0b}
.grade-d{background:#fee2e2;color:#991b1b;border:2px solid #ef4444}
.response-box{background:#f8fafc;border:1px solid #e2e8f0;border-radius:.75rem;padding:1.75rem;
  margin:1rem 0;white-space:pre-wrap;font-family:'Georgia','Times New Roman',serif;line-height:1.9;font-size:.95rem}
.disclaimer{background:#fef3c7;border-left:4px solid #f59e0b;padding:1rem 1.25rem;border-radius:0 .5rem .5rem 0;margin-top:1rem;font-size:.85rem}
.cal-event{padding:1rem 1.25rem;border-radius:.75rem;margin-bottom:.75rem;border-left:4px solid;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.cal-event.urgent{border-color:#ef4444;background:#fee2e2}
.cal-event.warn{border-color:#f59e0b;background:#fef3c7}
.cal-event.ok{border-color:#10b981;background:#f0fdf4}
.tmpl-card{background:#fff;border:1px solid #e2e8f0;border-radius:.75rem;padding:1.25rem;margin-bottom:1rem;transition:all .25s}
.tmpl-card:hover{box-shadow:0 6px 20px rgba(0,0,0,.08);transform:translateY(-2px)}
.tool-card{background:#fff;border:1px solid #e2e8f0;border-radius:1rem;padding:1.25rem;margin-bottom:1rem}
.mode-card{border-radius:.75rem;padding:1rem;border:2px solid;cursor:pointer;text-align:center;transition:all .2s}
.mode-card.active{border-color:#059669;background:#f0fdf4}
.mode-card.inactive{border-color:#e2e8f0;background:#fff}
.history-item{background:#f8fafc;border:1px solid #e2e8f0;border-radius:.5rem;padding:.75rem 1rem;margin-bottom:.5rem;font-size:.85rem}
.app-footer{text-align:center;padding:2rem 1rem;color:#64748b;font-size:.85rem;border-top:1px solid #e2e8f0;margin-top:2rem}
#MainMenu{visibility:hidden}footer{visibility:hidden}
.stTabs [data-baseweb="tab-list"]{gap:.25rem;background:transparent;border-bottom:2px solid #e2e8f0}
.stTabs [data-baseweb="tab"]{border-radius:.5rem .5rem 0 0;padding:.65rem 1.15rem;font-weight:600;font-size:.82rem}
</style>
"""

THEMES = {
    "🌿 Emerald": """<style>.stat-card{background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:#bbf7d0}.stat-card .stat-value{color:#059669}
.stat-card.t-blue{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#bfdbfe}.stat-card.t-blue .stat-value{color:#2563eb}
.stat-card.t-purple{background:linear-gradient(135deg,#faf5ff,#f3e8ff);border-color:#e9d5ff}.stat-card.t-purple .stat-value{color:#7c3aed}
.stat-card.t-amber{background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fde68a}.stat-card.t-amber .stat-value{color:#d97706}</style>""",
    "🌙 Midnight": """<style>[data-testid="stAppViewContainer"]{background:#0f172a!important;color:#e2e8f0!important}
[data-testid="stSidebar"]{background:#1e293b!important}[data-testid="stHeader"]{background:#0f172a!important}
.hero{background:linear-gradient(-45deg,#1e40af,#6d28d9,#1e3a5f,#4f46e5)!important}
.page-header{background:linear-gradient(135deg,#1e40af,#6d28d9)!important}
.custom-card,.feat-card,.tmpl-card,.tool-card{background:#1e293b!important;border-color:#334155!important;color:#e2e8f0!important}
.feat-card h4{color:#f1f5f9!important}.feat-card p,.stat-label{color:#94a3b8!important}
.stat-card{background:linear-gradient(135deg,#1e293b,#334155)!important;border-color:#475569!important}
.stat-card .stat-value{color:#34d399!important}
.response-box{background:#1e293b!important;border-color:#334155!important;color:#e2e8f0!important}
.disclaimer{background:#451a03!important;color:#fef3c7!important}
.issue-spot-box,.critique-box{background:#1e293b!important;color:#e2e8f0!important}
.app-footer{border-color:#334155!important;color:#94a3b8!important}</style>""",
    "👔 Royal Blue": """<style>.hero{background:linear-gradient(-45deg,#1e3a5f,#1e40af,#0f2557,#2563eb)!important}
.page-header{background:linear-gradient(135deg,#1e3a5f,#1e40af)!important}
.stat-card{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#93c5fd}.stat-card .stat-value{color:#1e40af}</style>""",
    "❤️ Crimson": """<style>.hero{background:linear-gradient(-45deg,#7f1d1d,#991b1b,#b91c1c,#dc2626)!important}
.page-header{background:linear-gradient(135deg,#7f1d1d,#991b1b)!important}
.stat-card{background:linear-gradient(135deg,#fef2f2,#fee2e2);border-color:#fecaca}.stat-card .stat-value{color:#991b1b}</style>""",
    "🌅 Sunset": """<style>.hero{background:linear-gradient(-45deg,#9a3412,#c2410c,#ea580c,#f97316)!important}
.page-header{background:linear-gradient(135deg,#9a3412,#c2410c)!important}
.stat-card{background:linear-gradient(135deg,#fff7ed,#ffedd5);border-color:#ffedd5}.stat-card .stat-value{color:#c2410c}</style>""",
    "🖤 Obsidian": """<style>.hero{background:linear-gradient(-45deg,#0f172a,#1e293b,#334155,#475569)!important}
.page-header{background:linear-gradient(135deg,#0f172a,#1e293b)!important}
.custom-card,.feat-card,.tmpl-card,.tool-card{background:#1e293b;border-color:#334155;color:#f8fafc}
.stat-card{background:linear-gradient(135deg,#1e293b,#334155);border-color:#475569}.stat-card .stat-value{color:#f8fafc}</style>""",
    "⚡ Neon": """<style>.hero{background:linear-gradient(-45deg,#4c1d95,#5b21b6,#6d28d9,#7c3aed)!important}
.page-header{background:linear-gradient(135deg,#4c1d95,#5b21b6)!important}
.stat-card{background:linear-gradient(135deg,#f5f3ff,#ddd6fe);border-color:#ddd6fe}.stat-card .stat-value{color:#5b21b6}</style>""",
    "🌊 Pacific": """<style>.hero{background:linear-gradient(-45deg,#0c4a6e,#075985,#0ea5e9,#38bdf8)!important}
.page-header{background:linear-gradient(135deg,#0c4a6e,#075985)!important}
.stat-card{background:linear-gradient(135deg,#f0f9ff,#bae6fd);border-color:#bae6fd}.stat-card .stat-value{color:#075985}</style>""",
}

# ═══════════════════════════════════════════════════════
# SESSION STATE INIT
# ═══════════════════════════════════════════════════════
_DEFAULTS = {
    "api_key": "", "api_configured": False,
    "gemini_model": core.DEFAULT_MODEL,
    "theme": "🌿 Emerald",
    "cases": [], "clients": [], "time_entries": [], "invoices": [],
    # AI state
    "response_mode": "standard",
    "last_response": "", "issue_spot_result": "", "critique_result": "",
    "quality_grade": "", "original_query": "",
    "research_results": "",
    "imported_doc": None, "loaded_template": "",
    "conversation_context": "",
    # History
    "history": [],
    "admin_unlocked": False,
}

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# Load history from file on first run
if "history_loaded" not in st.session_state:
    st.session_state.history = core.load_history()
    st.session_state.history_loaded = True

# Apply CSS
st.markdown(_BASE_CSS, unsafe_allow_html=True)
st.markdown(THEMES.get(st.session_state.theme, list(THEMES.values())[0]), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# HELPER: secrets access
# ═══════════════════════════════════════════════════════
def _sec(k: str) -> str:
    try:
        return st.secrets[k]
    except Exception:
        return ""


def _get_key() -> str:
    return core.get_api_key(
        secrets_fn=lambda: _sec("GEMINI_API_KEY"),
        session_key=st.session_state.get("api_key", ""),
    )


def _auto_connect():
    """Auto-connect on startup if key available."""
    if st.session_state.api_configured:
        return
    k = _get_key()
    if k and len(k) >= 10:
        core.configure_api(k)
        st.session_state.api_key = k
        st.session_state.api_configured = True
        m = _sec("GEMINI_MODEL") or ""
        if m:
            st.session_state.gemini_model = core.normalize_model(m)


# ═══════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚖️ LexiAssist v7.0")
        st.caption("Smart Legal AI · Instruction-Adherent")
        st.divider()

        hearings = core.get_hearings(st.session_state.cases)
        active = len([c for c in st.session_state.cases if c.get("status") == "Active"])
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Active", active)
        with c2:
            st.metric("Hearings", len(hearings))
        st.divider()

        # Theme
        st.markdown("### 🎨 Theme")
        th = st.selectbox(
            "Theme", list(THEMES.keys()),
            index=list(THEMES.keys()).index(st.session_state.theme)
            if st.session_state.theme in THEMES else 0,
            label_visibility="collapsed",
        )
        if th != st.session_state.theme:
            st.session_state.theme = th
            st.rerun()
        st.divider()

        # AI Engine
        st.markdown("### 🤖 AI Engine")
        if st.session_state.api_configured:
            st.success(f"✅ Connected · `{st.session_state.gemini_model}`")
        else:
            st.warning("⚠️ Not connected")

        idx = (core.SUPPORTED_MODELS.index(st.session_state.gemini_model)
               if st.session_state.gemini_model in core.SUPPORTED_MODELS else 0)
        sel = st.selectbox("Model", core.SUPPORTED_MODELS, index=idx)
        new_model = core.normalize_model(sel)
        if new_model != st.session_state.gemini_model:
            st.session_state.gemini_model = new_model
            st.session_state.api_configured = False
            st.rerun()

        st.divider()

        # Response Mode (replaces confusing pipeline settings)
        st.markdown("### 📏 Response Mode")
        for mode_key, mode_info in core.RESPONSE_MODES.items():
            is_active = st.session_state.response_mode == mode_key
            if st.button(
                f"{mode_info['label']}  —  {mode_info['desc']}",
                key=f"mode_{mode_key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.response_mode = mode_key
                st.rerun()
        st.caption(f"Current: **{core.RESPONSE_MODES[st.session_state.response_mode]['label']}**")

        st.divider()

        # Admin / API Key
        has_secret = bool(_sec("GEMINI_API_KEY"))
        admin_pw = _sec("ADMIN_PASSWORD")
        show_key_input = False

        if not has_secret:
            if admin_pw:
                with st.expander("🔒 Admin"):
                    if st.text_input("Password", type="password", key="apw_input") == admin_pw:
                        st.session_state.admin_unlocked = True
                    if st.session_state.admin_unlocked:
                        show_key_input = True
            else:
                show_key_input = True
        elif admin_pw:
            with st.expander("🔒 Admin"):
                if st.text_input("Password", type="password", key="apw_input") == admin_pw:
                    st.session_state.admin_unlocked = True
                if st.session_state.admin_unlocked:
                    show_key_input = True

        if show_key_input:
            ki = st.text_input(
                "API Key", type="password", value=st.session_state.api_key,
                label_visibility="collapsed", placeholder="Gemini API key…",
            )
            if st.button("Connect", type="primary", use_container_width=True, key="connect_btn"):
                if ki and len(ki.strip()) >= 10:
                    with st.spinner("Connecting…"):
                        ok, msg = core.test_connection(ki.strip(), st.session_state.gemini_model)
                        if ok:
                            core.configure_api(ki.strip())
                            st.session_state.api_key = ki.strip()
                            st.session_state.api_configured = True
                            st.success("✅ Connected!")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
                else:
                    st.warning("Enter a valid key.")
            st.caption("[Get key →](https://aistudio.google.com/app/apikey)")

        st.divider()

        # Data Export / Import
        st.markdown("### 💾 Data")
        exp_data = core.export_all_data(
            st.session_state.cases, st.session_state.clients,
            st.session_state.time_entries, st.session_state.invoices,
        )
        st.download_button(
            "📥 Export All Data (JSON)", exp_data,
            f"lexiassist_{datetime.now():%Y%m%d}.json", "application/json",
            use_container_width=True, key="export_data_btn",
        )

        up = st.file_uploader(
            "📤 Import", type=["json", "pdf", "docx", "txt", "csv", "xlsx"],
            key="sidebar_uploader", help=f"Max {core.MAX_UPLOAD_MB}MB",
        )
        if up:
            try:
                ext = up.name.split(".")[-1].lower()
                if ext == "json":
                    data = json.load(up)
                    for k in ["cases", "clients", "time_entries", "invoices"]:
                        st.session_state[k] = data.get(k, [])
                    st.success("✅ Data imported!")
                    st.rerun()
                else:
                    with st.spinner(f"Processing {up.name}…"):
                        text = core.extract_file_text(up)
                    st.session_state.imported_doc = {
                        "name": up.name, "type": ext,
                        "size": len(up.getvalue()),
                        "preview": text[:500] + ("…" if len(text) > 500 else ""),
                        "full_text": text,
                    }
                    st.success(f"✅ {up.name} loaded → AI Assistant")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ {e}")

        st.divider()
        st.caption("**LexiAssist v7.0** © 2026\n🤖 Gemini · 🎈 Streamlit")


# ═══════════════════════════════════════════════════════
# PAGE: HOME
# ═══════════════════════════════════════════════════════
def render_home():
    api_status = "🟢 AI Ready" if st.session_state.api_configured else "🔴 Configure API in Sidebar"
    mode_label = core.RESPONSE_MODES[st.session_state.response_mode]["label"]
    st.markdown(f"""<div class="hero">
    <div class="hero-badge">{api_status}</div>
    <h1>Smart Legal AI<br>for Nigerian Lawyers</h1>
    <p>Answers that match your question — brief when brief is right, deep when depth is needed.
    No more treatises for simple questions.</p>
    <div class="hero-badge" style="margin-top:.75rem">🇳🇬 Nigerian Law · Mode: {mode_label} · History Saved</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("")
    active = len([c for c in st.session_state.cases if c.get("status") == "Active"])
    hearings = core.get_hearings(st.session_state.cases)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{active}</div>'
                     f'<div class="stat-label">📁 Active Cases</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card t-blue"><div class="stat-value">{len(st.session_state.clients)}</div>'
                     f'<div class="stat-label">👥 Clients</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card t-purple"><div class="stat-value">'
                     f'{core.esc(core.fmt_currency(core.total_billable(st.session_state.time_entries)))}</div>'
                     f'<div class="stat-label">💰 Billable</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card t-amber"><div class="stat-value">{len(hearings)}</div>'
                     f'<div class="stat-label">📅 Hearings</div></div>', unsafe_allow_html=True)

    st.markdown("")
    st.markdown("#### What's New in v7.0")
    feats = [
        ("📏", "Response Modes", "Brief / Standard / Comprehensive — you choose the depth."),
        ("🎯", "Instruction Adherent", "Answers what you ask. Doesn't go off-topic or ramble."),
        ("⚡", "Fast by Default", "Standard mode = 1 API call. Brief = instant answers."),
        ("💾", "Persistent History", "Responses saved to file. Reload anytime."),
        ("📥", "Multi-Format Export", "TXT, HTML, PDF, DOCX — download in any format."),
        ("🗑️", "Working Clear/Reset", "Clear button actually clears everything."),
        ("📄", "Document Upload", "Upload PDF, DOCX, TXT, CSV, XLSX for AI analysis."),
        ("🇳🇬", "Nigerian Tools", "Limitation periods, interest calc, court hierarchy, maxims."),
    ]
    cols = st.columns(4)
    for i, (ic, t, d) in enumerate(feats):
        with cols[i % 4]:
            st.markdown(f'<div class="feat-card"><span class="feat-icon">{ic}</span>'
                         f'<h4>{t}</h4><p>{d}</p></div>', unsafe_allow_html=True)

    # Upcoming hearings
    if hearings:
        st.markdown("#### 📅 Upcoming Hearings")
        for h in hearings[:5]:
            d = core.days_until(h["date"])
            u = "urgent" if d <= 3 else ("warn" if d <= 7 else "ok")
            b = "danger" if d <= 3 else ("warning" if d <= 7 else "success")
            st.markdown(
                f'<div class="cal-event {u}"><strong>{core.esc(h["title"])}</strong> · '
                f'{core.esc(h["suit"])}<br>{core.esc(core.fmt_date(h["date"]))} '
                f'<span class="badge badge-{b}">{core.esc(core.relative_date(h["date"]))}</span></div>',
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════
# PAGE: AI ASSISTANT
# ═══════════════════════════════════════════════════════
def render_ai():
    st.markdown(
        '<div class="page-header"><h1>🧠 AI Legal Assistant</h1>'
        '<p>Ask legal questions · Get answers that match your scope</p></div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key in the sidebar first.")

    # Current mode display
    mode = st.session_state.response_mode
    mode_info = core.RESPONSE_MODES[mode]
    st.info(f"**Response Mode: {mode_info['label']}** — {mode_info['desc']}  ·  Change in sidebar.")

    # Imported document
    if st.session_state.imported_doc:
        with st.expander("📄 Uploaded Document", expanded=True):
            doc = st.session_state.imported_doc
            st.caption(f"`{doc['name']}` · {doc['type'].upper()} · {doc['size']:,} bytes")
            st.text_area("Preview", doc["preview"], height=100, disabled=True, key="doc_preview_area")
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("✅ Use in Query", type="primary", use_container_width=True, key="use_doc_btn"):
                    st.session_state.loaded_template = doc["full_text"][:2000]
                    st.rerun()
            with dc2:
                if st.button("🗑️ Remove Document", use_container_width=True, key="remove_doc_btn"):
                    st.session_state.imported_doc = None
                    st.rerun()

    # Task type
    task_keys = list(core.TASK_TYPES.keys())
    chosen_task = st.selectbox(
        "🎯 Task Type", task_keys, index=0,
        format_func=lambda k: f"{core.TASK_TYPES[k]['icon']} {core.TASK_TYPES[k]['label']} — {core.TASK_TYPES[k]['desc']}",
        key="task_selector",
    )

    # Template loader
    with st.expander("📋 Load Template", expanded=False):
        tmpl_names = [t["name"] for t in core.TEMPLATES]
        chosen_tmpl = st.selectbox("Template", tmpl_names, key="tmpl_chooser")
        if st.button("✅ Load Template", type="primary", use_container_width=True, key="load_tmpl_btn"):
            for t in core.TEMPLATES:
                if t["name"] == chosen_tmpl:
                    st.session_state.loaded_template = t["content"]
                    st.rerun()

    st.markdown("---")

    # Input area
    prefill = st.session_state.get("loaded_template", "") or ""
    if prefill:
        st.session_state.loaded_template = ""
    user_input = st.text_area(
        "📝 Your Legal Query", value=prefill, height=200,
        placeholder="Type your legal question here. Be specific for better results.",
        key="query_input",
    )

    # Action buttons
    bc1, bc2, bc3 = st.columns([3, 1, 1])
    with bc1:
        generate_btn = st.button(
            f"🧠 Generate ({mode_info['label']})", type="primary",
            use_container_width=True, disabled=not st.session_state.api_configured,
            key="generate_btn",
        )
    with bc2:
        spot_btn = st.button(
            "🔍 Issues Only", use_container_width=True,
            disabled=not st.session_state.api_configured, key="spot_btn",
        )
    with bc3:
        clear_btn = st.button("🗑️ Clear All", use_container_width=True, key="clear_all_btn")

    # ── CLEAR ALL ──────────────────────────────────────
    if clear_btn:
        for k in ["last_response", "issue_spot_result", "critique_result",
                   "quality_grade", "original_query", "conversation_context",
                   "research_results", "imported_doc"]:
            if k == "imported_doc":
                st.session_state[k] = None
            else:
                st.session_state[k] = ""
        st.success("✅ Cleared!")
        st.rerun()

    # ── ISSUE SPOT ONLY ────────────────────────────────
    if spot_btn and user_input.strip():
        with st.spinner("🔍 Spotting issues…"):
            core.configure_api(st.session_state.api_key)
            result = core.generate(
                f"LEGAL SCENARIO:\n\n{user_input}",
                core.ISSUE_SPOT_SYSTEM,
                st.session_state.gemini_model,
                {"temperature": 0.15, "top_p": 0.85, "top_k": 25, "max_output_tokens": 800},
            )
            st.session_state.issue_spot_result = result
            st.session_state.last_response = ""
            st.session_state.critique_result = ""
            st.session_state.quality_grade = ""

    # ── GENERATE ───────────────────────────────────────
    if generate_btn and user_input.strip():
        core.configure_api(st.session_state.api_key)
        doc_ctx = ""
        if st.session_state.imported_doc:
            doc_ctx = st.session_state.imported_doc.get("full_text", "")[:3000]

        if mode == "comprehensive":
            progress = st.progress(0, text="🔍 Pass 1: Issue Spotting…")
            with st.spinner("🔍 Issue Spotting…"):
                results = {"issue_spot": "", "main": "", "critique": "", "grade": ""}
                results["issue_spot"] = core.generate(
                    f"LEGAL SCENARIO:\n\n{user_input}",
                    core.ISSUE_SPOT_SYSTEM,
                    st.session_state.gemini_model,
                    {"temperature": 0.15, "top_p": 0.85, "top_k": 25, "max_output_tokens": 800},
                )
            progress.progress(33, text="🧠 Pass 2: Deep Analysis…")
            with st.spinner("🧠 Deep Analysis…"):
                results = core.run_pipeline(
                    user_input, chosen_task, mode,
                    st.session_state.gemini_model, doc_ctx,
                    st.session_state.conversation_context,
                )
            progress.progress(100, text="✅ Complete!")
            time.sleep(0.3)
            progress.empty()
        else:
            with st.spinner(f"🧠 Generating ({mode_info['label']})…"):
                results = core.run_pipeline(
                    user_input, chosen_task, mode,
                    st.session_state.gemini_model, doc_ctx,
                    st.session_state.conversation_context,
                )

        # Store results
        st.session_state.issue_spot_result = results.get("issue_spot", "")
        st.session_state.last_response = results.get("main", "")
        st.session_state.critique_result = results.get("critique", "")
        st.session_state.quality_grade = results.get("grade", "")
        st.session_state.original_query = user_input
        st.session_state.conversation_context = (
            f"Previous query: {user_input[:500]}\n"
            f"Previous response: {results.get('main', '')[:1500]}"
        )

        # Save to history
        if results.get("main") and not results["main"].startswith(("Error", "⚠️")):
            entry = {
                "id": core.gen_id(),
                "timestamp": datetime.now().isoformat(),
                "query": user_input[:500],
                "task": chosen_task,
                "mode": mode,
                "response": results["main"][:3000],
                "grade": results.get("grade", ""),
            }
            st.session_state.history.append(entry)
            core.save_history(st.session_state.history)

        st.rerun()

    # ── DISPLAY RESULTS ────────────────────────────────

    # Issue spotting (comprehensive mode only)
    if st.session_state.issue_spot_result and mode == "comprehensive":
        with st.expander("🔍 Issue Spotting Results", expanded=False):
            st.markdown(
                f'<div class="issue-spot-box"><h5>🔍 Issues Identified</h5>'
                f'{core.esc(st.session_state.issue_spot_result)}</div>',
                unsafe_allow_html=True,
            )

    # Main response
    if st.session_state.last_response:
        st.markdown("---")
        text = st.session_state.last_response
        wc = len(text.split())
        grade = st.session_state.quality_grade
        grade_html = ""
        if grade:
            gc = {"A": "grade-a", "B": "grade-b", "C": "grade-c", "D": "grade-d"}.get(grade, "grade-b")
            grade_html = f' <span class="quality-grade {gc}">Grade: {grade}</span>'

        st.markdown(f"#### 📄 Response{grade_html}", unsafe_allow_html=True)
        st.caption(f"📝 {wc:,} words · Mode: {core.RESPONSE_MODES[mode]['label']}")

        # Multi-format export
        st.markdown("**Export:**")
        ex1, ex2, ex3, ex4 = st.columns(4)
        fname = f"LexiAssist_{datetime.now():%Y%m%d_%H%M}"
        with ex1:
            st.download_button("📥 TXT", core.export_txt(text), f"{fname}.txt",
                               "text/plain", key="dl_txt", use_container_width=True)
        with ex2:
            st.download_button("📥 HTML", core.export_html(text), f"{fname}.html",
                               "text/html", key="dl_html", use_container_width=True)
        with ex3:
            pdf_bytes = core.export_pdf(text)
            if pdf_bytes:
                st.download_button("📥 PDF", pdf_bytes, f"{fname}.pdf",
                                   "application/pdf", key="dl_pdf", use_container_width=True)
            else:
                st.button("PDF N/A", disabled=True, key="dl_pdf_na", use_container_width=True)
        with ex4:
            docx_bytes = core.export_docx(text)
            if docx_bytes:
                st.download_button("📥 DOCX", docx_bytes, f"{fname}.docx",
                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                   key="dl_docx", use_container_width=True)
            else:
                st.button("DOCX N/A", disabled=True, key="dl_docx_na", use_container_width=True)

        # Response display
        st.markdown(f'<div class="response-box">{core.esc(text)}</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated legal information. '
            'Not legal advice. Verify all citations. Apply professional judgment.</div>',
            unsafe_allow_html=True,
        )

    # Critique (comprehensive mode only)
    if st.session_state.critique_result and mode == "comprehensive":
        with st.expander("✅ Quality Critique", expanded=True):
            st.markdown(
                f'<div class="critique-box"><h5>✅ Quality Assessment</h5>'
                f'{core.esc(st.session_state.critique_result)}</div>',
                unsafe_allow_html=True,
            )

    # ── FOLLOW-UP ──────────────────────────────────────
    if st.session_state.last_response:
        st.markdown("---")
        st.markdown("#### 💬 Follow-Up")
        followup = st.text_input(
            "Ask a follow-up", placeholder="e.g. 'What about the limitation issue?' or 'Draft a demand letter for this'",
            key="followup_input",
        )
        if st.button("💬 Submit Follow-Up", type="primary", key="followup_btn", disabled=not followup):
            core.configure_api(st.session_state.api_key)
            with st.spinner("Processing follow-up…"):
                result = core.run_followup(
                    st.session_state.original_query,
                    st.session_state.last_response,
                    followup, mode, chosen_task,
                    st.session_state.gemini_model,
                )
                if not result.startswith(("Error", "⚠️")):
                    st.session_state.last_response = result
                    st.session_state.conversation_context = (
                        f"Original: {st.session_state.original_query[:300]}\n"
                        f"Follow-up: {followup}\nResponse: {result[:1500]}"
                    )
                    # Save follow-up to history
                    entry = {
                        "id": core.gen_id(),
                        "timestamp": datetime.now().isoformat(),
                        "query": f"[Follow-up] {followup[:400]}",
                        "task": chosen_task, "mode": mode,
                        "response": result[:3000], "grade": "",
                    }
                    st.session_state.history.append(entry)
                    core.save_history(st.session_state.history)
                    st.rerun()
                else:
                    st.error(result)

    # ── HISTORY ────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📜 Response History")
    history = st.session_state.history
    if not history:
        st.caption("No history yet. Generate a response to start saving.")
    else:
        hc1, hc2 = st.columns([4, 1])
        with hc2:
            if st.button("🗑️ Clear History", key="clear_history_btn", use_container_width=True):
                st.session_state.history = []
                core.clear_history()
                st.success("History cleared!")
                st.rerun()

        for i, h in enumerate(reversed(history[-20:])):
            with st.expander(
                f"{'🔍' if '[Follow-up]' not in h.get('query','') else '💬'} "
                f"{h.get('query', '')[:80]}… · "
                f"{core.fmt_date(h.get('timestamp', ''))} · "
                f"{core.RESPONSE_MODES.get(h.get('mode', 'standard'), {}).get('label', '')}",
                expanded=False,
            ):
                st.caption(
                    f"Task: {core.TASK_TYPES.get(h.get('task', 'general'), {}).get('label', 'General')} · "
                    f"Grade: {h.get('grade', '—') or '—'}"
                )
                st.markdown(
                    f'<div class="response-box" style="max-height:300px;overflow-y:auto">'
                    f'{core.esc(h.get("response", ""))}</div>',
                    unsafe_allow_html=True,
                )
                rc1, rc2 = st.columns(2)
                with rc1:
                    if st.button("🔄 Restore to View", key=f"restore_{h['id']}_{i}", use_container_width=True):
                        st.session_state.last_response = h.get("response", "")
                        st.session_state.original_query = h.get("query", "")
                        st.session_state.quality_grade = h.get("grade", "")
                        st.rerun()
                with rc2:
                    st.download_button(
                        "📥 TXT", core.export_txt(h.get("response", "")),
                        f"history_{h['id']}.txt", "text/plain",
                        key=f"dl_hist_{h['id']}_{i}", use_container_width=True,
                    )

# ═══════════════════════════════════════════════════════
# PAGE: RESEARCH
# ═══════════════════════════════════════════════════════
def render_research():
    st.markdown(
        '<div class="page-header"><h1>📚 Legal Research</h1>'
        '<p>Focused research memos · Statutes · Case law · Authorities</p></div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key in the sidebar first.")

    mode = st.session_state.response_mode
    mode_info = core.RESPONSE_MODES[mode]
    st.info(f"**Response Mode: {mode_info['label']}** — {mode_info['desc']}")

    q = st.text_input(
        "🔍 Research Query",
        placeholder="e.g. 'employer liability for workplace injuries — statutes, cases, procedure'",
        key="research_query_input",
    )

    rc1, rc2 = st.columns([3, 1])
    with rc1:
        go = st.button(
            f"📚 Run Research ({mode_info['label']})", type="primary",
            use_container_width=True, disabled=not st.session_state.api_configured,
            key="research_go_btn",
        )
    with rc2:
        clr = st.button("🗑️ Clear", use_container_width=True, key="research_clear_btn")

    if clr:
        st.session_state.research_results = ""
        st.rerun()

    if go and q.strip():
        core.configure_api(st.session_state.api_key)
        with st.spinner(f"📚 Researching ({mode_info['label']})…"):
            st.session_state.research_results = core.run_research(
                q, mode, st.session_state.gemini_model,
            )
        # Save to history
        if st.session_state.research_results and not st.session_state.research_results.startswith(("Error", "⚠️")):
            entry = {
                "id": core.gen_id(),
                "timestamp": datetime.now().isoformat(),
                "query": f"[Research] {q[:400]}",
                "task": "research", "mode": mode,
                "response": st.session_state.research_results[:3000],
                "grade": "",
            }
            st.session_state.history.append(entry)
            core.save_history(st.session_state.history)

    if st.session_state.research_results:
        st.markdown("---")
        text = st.session_state.research_results
        wc = len(text.split())
        st.caption(f"📝 {wc:,} words")

        # Multi-format export
        fname = f"Research_{datetime.now():%Y%m%d_%H%M}"
        ex1, ex2, ex3, ex4 = st.columns(4)
        with ex1:
            st.download_button("📥 TXT", core.export_txt(text, "Legal Research"),
                               f"{fname}.txt", "text/plain", key="res_dl_txt", use_container_width=True)
        with ex2:
            st.download_button("📥 HTML", core.export_html(text, "Legal Research"),
                               f"{fname}.html", "text/html", key="res_dl_html", use_container_width=True)
        with ex3:
            pdf_bytes = core.export_pdf(text, "Legal Research")
            if pdf_bytes:
                st.download_button("📥 PDF", pdf_bytes, f"{fname}.pdf",
                                   "application/pdf", key="res_dl_pdf", use_container_width=True)
            else:
                st.button("PDF N/A", disabled=True, key="res_pdf_na", use_container_width=True)
        with ex4:
            docx_bytes = core.export_docx(text, "Legal Research")
            if docx_bytes:
                st.download_button("📥 DOCX", docx_bytes, f"{fname}.docx",
                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                   key="res_dl_docx", use_container_width=True)
            else:
                st.button("DOCX N/A", disabled=True, key="res_docx_na", use_container_width=True)

        st.markdown(f'<div class="response-box">{core.esc(text)}</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated research. '
            'Verify all citations independently.</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════
# PAGE: CASES
# ═══════════════════════════════════════════════════════
def render_cases():
    st.markdown(
        '<div class="page-header"><h1>📁 Case Management</h1>'
        '<p>Track suits, hearings, progress</p></div>',
        unsafe_allow_html=True,
    )

    search_q = st.text_input("🔍 Search", placeholder="Title, suit number, court, notes…", key="case_search")
    filt = st.selectbox("Status Filter", ["All"] + core.CASE_STATUSES, key="case_filter")

    cases = st.session_state.cases
    if filt != "All":
        cases = [c for c in cases if c.get("status") == filt]
    if search_q:
        cases = [c for c in cases if search_q.lower() in json.dumps(c).lower()]

    with st.expander("➕ Add New Case", expanded=not bool(st.session_state.cases)):
        with st.form("add_case_form"):
            a, b = st.columns(2)
            with a:
                title = st.text_input("Title *", key="cf_title")
                suit = st.text_input("Suit No *", key="cf_suit")
                court = st.text_input("Court", key="cf_court")
            with b:
                nh = st.date_input("Next Hearing", key="cf_nh")
                status = st.selectbox("Status", core.CASE_STATUSES, key="cf_status")
                cn = ["— None —"] + [c["name"] for c in st.session_state.clients]
                ci = st.selectbox("Client", range(len(cn)), format_func=lambda i: cn[i], key="cf_client")
            notes = st.text_area("Notes", key="cf_notes")
            if st.form_submit_button("Save Case", type="primary"):
                if title.strip() and suit.strip():
                    cid = st.session_state.clients[ci - 1]["id"] if ci > 0 else None
                    core.add_case(st.session_state.cases, {
                        "title": title.strip(), "suit_no": suit.strip(), "court": court.strip(),
                        "next_hearing": nh.isoformat() if nh else None,
                        "status": status, "client_id": cid, "notes": notes.strip(),
                    })
                    st.success("✅ Case added!")
                    st.rerun()
                else:
                    st.error("Title and Suit No are required.")

    if not cases:
        st.info("No cases match your search/filter.")
        return

    for case in cases:
        bc = {"Active": "success", "Pending": "warning", "Completed": "info"}.get(case.get("status", ""), "info")
        hearing_html = ""
        if case.get("next_hearing"):
            hearing_html = (
                f"<p>📅 {core.esc(core.fmt_date(case['next_hearing']))} "
                f"<span class='badge badge-info'>{core.esc(core.relative_date(case['next_hearing']))}</span></p>"
            )
        cl_name = core.client_name(st.session_state.clients, case.get("client_id", ""))

        a, b = st.columns([5, 1])
        with a:
            st.markdown(
                f'<div class="custom-card"><h4>{core.esc(case["title"])} '
                f'<span class="badge badge-{bc}">{core.esc(case.get("status", ""))}</span></h4>'
                f'<p>⚖️ {core.esc(case.get("suit_no", ""))} · 🏛️ {core.esc(case.get("court", ""))} '
                f'· 👤 {core.esc(cl_name)}</p>{hearing_html}</div>',
                unsafe_allow_html=True,
            )
        with b:
            ns = st.selectbox(
                "Status", core.CASE_STATUSES,
                index=core.CASE_STATUSES.index(case["status"]) if case.get("status") in core.CASE_STATUSES else 0,
                key=f"cs_{case['id']}", label_visibility="collapsed",
            )
            if ns != case.get("status"):
                core.update_case(st.session_state.cases, case["id"], {"status": ns})
                st.rerun()
            if st.button("🗑️", key=f"cd_{case['id']}"):
                st.session_state.cases = core.delete_case(st.session_state.cases, case["id"])
                st.rerun()


# ═══════════════════════════════════════════════════════
# PAGE: CALENDAR
# ═══════════════════════════════════════════════════════
def render_calendar():
    st.markdown(
        '<div class="page-header"><h1>📅 Court Calendar</h1>'
        '<p>Upcoming hearings at a glance</p></div>',
        unsafe_allow_html=True,
    )

    hearings = core.get_hearings(st.session_state.cases)
    if not hearings:
        st.info("No upcoming hearings. Add active cases with hearing dates.")
        return

    for h in hearings:
        d = core.days_until(h["date"])
        u = "urgent" if d <= 3 else ("warn" if d <= 7 else "ok")
        b = "danger" if d <= 3 else ("warning" if d <= 7 else "success")
        st.markdown(
            f'<div class="cal-event {u}"><h4>{core.esc(h["title"])}</h4>'
            f'<p>⚖️ {core.esc(h["suit"])} · 🏛️ {core.esc(h["court"])}</p>'
            f'<p>📅 {core.esc(core.fmt_date(h["date"]))} '
            f'<span class="badge badge-{b}">{core.esc(core.relative_date(h["date"]))}</span></p></div>',
            unsafe_allow_html=True,
        )

    # Chart
    df = pd.DataFrame([
        {"Case": h["title"], "Days": max(core.days_until(h["date"]), 0), "Date": core.fmt_date(h["date"])}
        for h in hearings
    ])
    if not df.empty:
        fig = px.bar(
            df, x="Days", y="Case", orientation="h", text="Date", color="Days",
            color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
            title="Days Until Hearing",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════
# PAGE: TEMPLATES
# ═══════════════════════════════════════════════════════
def render_templates():
    st.markdown(
        '<div class="page-header"><h1>📋 Templates</h1>'
        '<p>Professional Nigerian legal document templates</p></div>',
        unsafe_allow_html=True,
    )

    cats = sorted({t["cat"] for t in core.TEMPLATES})
    sel = st.selectbox("Category", ["All"] + cats, key="tmpl_cat_filter")
    vis = core.TEMPLATES if sel == "All" else [t for t in core.TEMPLATES if t["cat"] == sel]

    cols = st.columns(2)
    for i, t in enumerate(vis):
        with cols[i % 2]:
            st.markdown(
                f'<div class="tmpl-card"><h4>📄 {core.esc(t["name"])}</h4>'
                f'<span class="badge badge-success">{core.esc(t["cat"])}</span></div>',
                unsafe_allow_html=True,
            )
            a, b = st.columns(2)
            with a:
                if st.button("📋 Load to AI", key=f"tl_{t['id']}", use_container_width=True):
                    st.session_state.loaded_template = t["content"]
                    st.success("✅ Loaded! Go to AI Assistant.")
            with b:
                if st.button("👁️ Preview", key=f"tp_{t['id']}", use_container_width=True):
                    st.session_state[f"preview_{t['id']}"] = not st.session_state.get(f"preview_{t['id']}", False)

            if st.session_state.get(f"preview_{t['id']}", False):
                st.code(t["content"], language=None)


# ═══════════════════════════════════════════════════════
# PAGE: CLIENTS
# ═══════════════════════════════════════════════════════
def render_clients():
    st.markdown(
        '<div class="page-header"><h1>👥 Clients</h1>'
        '<p>Manage clients, track cases and billing</p></div>',
        unsafe_allow_html=True,
    )

    search_q = st.text_input("🔍 Search", placeholder="Name, email, type…", key="client_search")

    with st.expander("➕ Add Client", expanded=not bool(st.session_state.clients)):
        with st.form("add_client_form"):
            a, b = st.columns(2)
            with a:
                name = st.text_input("Name *", key="clf_name")
                email = st.text_input("Email", key="clf_email")
                phone = st.text_input("Phone", key="clf_phone")
            with b:
                ct = st.selectbox("Type", core.CLIENT_TYPES, key="clf_type")
                addr = st.text_input("Address", key="clf_addr")
                notes = st.text_area("Notes", key="clf_notes")
            if st.form_submit_button("Save Client", type="primary"):
                if name.strip():
                    core.add_client(st.session_state.clients, {
                        "name": name.strip(), "email": email.strip(),
                        "phone": phone.strip(), "type": ct,
                        "address": addr.strip(), "notes": notes.strip(),
                    })
                    st.success("✅ Client added!")
                    st.rerun()
                else:
                    st.error("Name is required.")

    clients = st.session_state.clients
    if search_q:
        clients = [c for c in clients if search_q.lower() in json.dumps(c).lower()]

    if not clients:
        st.info("No clients found.")
        return

    cols = st.columns(2)
    for i, cl in enumerate(clients):
        with cols[i % 2]:
            cc = core.client_case_count(st.session_state.cases, cl["id"])
            cb = core.client_billable(st.session_state.time_entries, cl["id"])
            st.markdown(
                f'<div class="custom-card"><h4>{core.esc(cl["name"])} '
                f'<span class="badge badge-info">{core.esc(cl.get("type", ""))}</span></h4>'
                f'<div style="display:flex;justify-content:space-around;text-align:center;margin-top:.5rem">'
                f'<div><div style="font-size:1.5rem;font-weight:700;color:#059669">{cc}</div>'
                f'<div style="font-size:.7rem;color:#64748b">CASES</div></div>'
                f'<div><div style="font-size:1.5rem;font-weight:700;color:#7c3aed">'
                f'{core.esc(core.fmt_currency(cb))}</div>'
                f'<div style="font-size:.7rem;color:#64748b">BILLABLE</div></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            a, b = st.columns(2)
            with a:
                if cb > 0 and st.button("📄 Invoice", key=f"inv_{cl['id']}", use_container_width=True):
                    inv = core.make_invoice(
                        st.session_state.invoices, st.session_state.time_entries,
                        st.session_state.clients, cl["id"],
                    )
                    if inv:
                        st.success(f"✅ Invoice {inv['invoice_no']} created!")
                        st.rerun()
            with b:
                if st.button("🗑️ Delete", key=f"dc_{cl['id']}", use_container_width=True):
                    st.session_state.clients = core.delete_client(st.session_state.clients, cl["id"])
                    st.rerun()


# ═══════════════════════════════════════════════════════
# PAGE: BILLING
# ═══════════════════════════════════════════════════════
def render_billing():
    st.markdown(
        '<div class="page-header"><h1>💰 Billing</h1>'
        '<p>Time tracking & invoicing</p></div>',
        unsafe_allow_html=True,
    )

    tb = core.total_billable(st.session_state.time_entries)
    th = core.total_hours(st.session_state.time_entries)
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(
            f'<div class="stat-card"><div class="stat-value">{core.esc(core.fmt_currency(tb))}</div>'
            f'<div class="stat-label">💰 Total Billable</div></div>',
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            f'<div class="stat-card t-blue"><div class="stat-value">{th:.1f}h</div>'
            f'<div class="stat-label">⏱️ Total Hours</div></div>',
            unsafe_allow_html=True,
        )
    with s3:
        st.markdown(
            f'<div class="stat-card t-purple"><div class="stat-value">{len(st.session_state.invoices)}</div>'
            f'<div class="stat-label">📄 Invoices</div></div>',
            unsafe_allow_html=True,
        )

    with st.expander("⏱️ Log Time Entry", expanded=False):
        with st.form("add_time_form"):
            a, b = st.columns(2)
            with a:
                cn = ["— Select Client —"] + [c["name"] for c in st.session_state.clients]
                ci = st.selectbox("Client *", range(len(cn)), format_func=lambda i: cn[i], key="tf_client")
                ed = st.date_input("Date", datetime.now(), key="tf_date")
            with b:
                hrs = st.number_input("Hours *", 0.25, step=0.25, value=1.0, key="tf_hours")
                rate = st.number_input("Rate (₦) *", 0, value=50000, step=5000, key="tf_rate")
                st.markdown(f"**Total: {core.fmt_currency(hrs * rate)}**")
            desc = st.text_area("Description *", key="tf_desc")
            if st.form_submit_button("Save Entry", type="primary"):
                if ci > 0 and desc.strip():
                    core.add_time_entry(st.session_state.time_entries, {
                        "client_id": st.session_state.clients[ci - 1]["id"],
                        "case_id": None,
                        "date": ed.isoformat(),
                        "hours": hrs,
                        "rate": rate,
                        "description": desc.strip(),
                    })
                    st.success("✅ Time entry saved!")
                    st.rerun()
                else:
                    st.error("Select a client and add a description.")

    # Time entries table
    if st.session_state.time_entries:
        st.markdown("#### ⏱️ Time Entries")
        rows = [
            {
                "Date": core.fmt_date(e["date"]),
                "Client": core.client_name(st.session_state.clients, e.get("client_id", "")),
                "Description": e["description"][:60],
                "Hours": f"{e['hours']}h",
                "Rate": core.fmt_currency(e["rate"]),
                "Amount": core.fmt_currency(e["amount"]),
            }
            for e in reversed(st.session_state.time_entries)
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Invoices
    if st.session_state.invoices:
        st.markdown("#### 📄 Invoices")
        for inv in reversed(st.session_state.invoices):
            with st.expander(
                f"📄 {inv['invoice_no']} — {inv['client_name']} — {core.fmt_currency(inv['total'])}"
            ):
                lines = [
                    f"INVOICE: {inv['invoice_no']}",
                    f"Date: {core.fmt_date(inv['date'])}",
                    f"Client: {inv['client_name']}",
                    "",
                ]
                for idx, e in enumerate(inv["entries"], 1):
                    lines.append(
                        f"{idx}. {core.fmt_date(e['date'])} — {e['description']} — "
                        f"{e['hours']}h × {core.fmt_currency(e['rate'])} = {core.fmt_currency(e['amount'])}"
                    )
                lines += ["", f"TOTAL: {core.fmt_currency(inv['total'])}"]
                invoice_text = "\n".join(lines)

                ic1, ic2, ic3 = st.columns(3)
                with ic1:
                    st.download_button(
                        "📥 TXT", invoice_text, f"{inv['invoice_no']}.txt",
                        "text/plain", key=f"inv_txt_{inv['id']}", use_container_width=True,
                    )
                with ic2:
                    pdf_bytes = core.export_pdf(invoice_text, f"Invoice {inv['invoice_no']}")
                    if pdf_bytes:
                        st.download_button(
                            "📥 PDF", pdf_bytes, f"{inv['invoice_no']}.pdf",
                            "application/pdf", key=f"inv_pdf_{inv['id']}", use_container_width=True,
                        )
                with ic3:
                    docx_bytes = core.export_docx(invoice_text, f"Invoice {inv['invoice_no']}")
                    if docx_bytes:
                        st.download_button(
                            "📥 DOCX", docx_bytes, f"{inv['invoice_no']}.docx",
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"inv_docx_{inv['id']}", use_container_width=True,
                        )


# ═══════════════════════════════════════════════════════
# PAGE: TOOLS
# ═══════════════════════════════════════════════════════
def render_tools():
    st.markdown(
        '<div class="page-header"><h1>🇳🇬 Legal Tools</h1>'
        '<p>References, calculators, maxims</p></div>',
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["⏱️ Limitation Periods", "💹 Interest Calculator", "🏛️ Court Hierarchy", "📖 Legal Maxims"])

    # Limitation Periods
    with tabs[0]:
        s = st.text_input("Search", "", placeholder="e.g. contract, land, election…", key="lim_search")
        data = core.LIMITATION_PERIODS
        if s:
            data = [lp for lp in data if s.lower() in lp["cause"].lower() or s.lower() in lp["authority"].lower()]
        if data:
            st.dataframe(
                pd.DataFrame(data).rename(columns={"cause": "Cause of Action", "period": "Period", "authority": "Authority"}),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No matching limitation periods found.")

    # Interest Calculator
    with tabs[1]:
        with st.form("interest_calc_form"):
            a, b = st.columns(2)
            with a:
                principal = st.number_input("Principal (₦)", 0.0, value=1_000_000.0, step=50_000.0, key="ic_principal")
                rate = st.number_input("Annual Rate (%)", 0.0, value=10.0, key="ic_rate")
            with b:
                months = st.number_input("Period (Months)", 1, value=12, key="ic_months")
                calc_type = st.selectbox("Type", ["Simple", "Compound"], key="ic_type")
            calc_btn = st.form_submit_button("Calculate", type="primary")
        if calc_btn:
            if calc_type == "Simple":
                interest = principal * (rate / 100) * (months / 12)
            else:
                interest = principal * ((1 + (rate / 100) / 12) ** months) - principal
            r1, r2, r3 = st.columns(3)
            with r1:
                st.metric("Principal", core.fmt_currency(principal))
            with r2:
                st.metric("Interest", core.fmt_currency(interest))
            with r3:
                st.metric("Total", core.fmt_currency(principal + interest))

    # Court Hierarchy
    with tabs[2]:
        for c in core.COURT_HIERARCHY:
            indent = "　" * (c["level"] - 1)
            marker = "🔸" if c["level"] == 1 else "├─"
            st.markdown(f"{indent}{marker} **{c['icon']} {c['name']}**")
            st.caption(f"{indent}　　{c['desc']}")

    # Legal Maxims
    with tabs[3]:
        sq = st.text_input("Search maxims", "", placeholder="e.g. nemo, audi, equity…", key="maxim_search")
        mx = core.LEGAL_MAXIMS
        if sq:
            mx = [m for m in mx if sq.lower() in m["maxim"].lower() or sq.lower() in m["meaning"].lower()]
        if mx:
            for m in mx:
                st.markdown(
                    f'<div class="tool-card"><h4 style="font-style:italic;color:#7c3aed">'
                    f'{core.esc(m["maxim"])}</h4><p>{core.esc(m["meaning"])}</p></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No matching maxims found.")


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════
def main():
    _auto_connect()
    render_sidebar()

    tabs = st.tabs([
        "🏠 Home",
        "🧠 AI Assistant",
        "📚 Research",
        "📁 Cases",
        "📅 Calendar",
        "📋 Templates",
        "👥 Clients",
        "💰 Billing",
        "🇳🇬 Tools",
    ])

    with tabs[0]:
        render_home()
    with tabs[1]:
        render_ai()
    with tabs[2]:
        render_research()
    with tabs[3]:
        render_cases()
    with tabs[4]:
        render_calendar()
    with tabs[5]:
        render_templates()
    with tabs[6]:
        render_clients()
    with tabs[7]:
        render_billing()
    with tabs[8]:
        render_tools()

    # Footer
    st.markdown(
        '<div class="app-footer">'
        '<p>⚖️ <strong>LexiAssist v7.0</strong> · Smart Legal AI</p>'
        '<p>Built for Nigerian Lawyers · <a href="https://ai.google.dev">Google Gemini</a></p>'
        '<p style="font-size:.78rem">⚠️ AI-generated legal information, not legal advice. '
        'Verify all citations. Apply professional judgment.</p>'
        '<p style="font-size:.75rem">© 2026 LexiAssist</p>'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
