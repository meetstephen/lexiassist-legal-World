"""
app.py — LexiAssist v7.0 Frontend
Smart Legal AI · Nigerian Law
"""
from __future__ import annotations

import json
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import lexicore as core

# ═══════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════
st.set_page_config(
    page_title="LexiAssist — Smart Legal AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root{--pri:#059669;--pri-d:#047857;--accent:#7c3aed;--bg:#f8fafc;--card:#ffffff;
--text:#1e293b;--muted:#64748b;--border:#e2e8f0;--danger:#ef4444;--warn:#f59e0b;--ok:#10b981}
html,body,[class*="css"]{font-family:'Inter',sans-serif}
.page-header{background:linear-gradient(135deg,var(--pri),var(--accent));color:white;
padding:2rem;border-radius:16px;margin-bottom:2rem;text-align:center}
.page-header h1{margin:0;font-size:2rem}.page-header p{margin:.5rem 0 0;opacity:.9}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:12px;
padding:1.5rem;text-align:center;border-top:4px solid var(--pri)}
.stat-card.t-blue{border-top-color:#3b82f6}
.stat-card.t-purple{border-top-color:var(--accent)}
.stat-card.t-amber{border-top-color:var(--warn)}
.stat-value{font-size:2rem;font-weight:700;color:var(--text)}
.stat-label{font-size:.8rem;color:var(--muted);margin-top:.25rem}
.custom-card{background:var(--card);border:1px solid var(--border);border-radius:12px;
padding:1.25rem;margin-bottom:1rem}
.custom-card h4{margin:0 0 .5rem}
.response-box{background:var(--card);border:1px solid var(--border);border-radius:12px;
padding:1.5rem;white-space:pre-wrap;line-height:1.8;font-size:.97rem;color:var(--text)}
.badge{display:inline-block;padding:.15rem .6rem;border-radius:20px;font-size:.75rem;font-weight:600}
.badge-success{background:#d1fae5;color:#065f46}
.badge-warning{background:#fef3c7;color:#92400e}
.badge-danger{background:#fee2e2;color:#991b1b}
.badge-info{background:#dbeafe;color:#1e40af}
.cal-event{border-left:4px solid var(--ok);padding:1rem;margin:.75rem 0;
background:var(--card);border-radius:0 12px 12px 0}
.cal-event.urgent{border-left-color:var(--danger);background:#fef2f2}
.cal-event.warn{border-left-color:var(--warn);background:#fffbeb}
.cal-event h4{margin:0 0 .3rem}
.tmpl-card{background:var(--card);border:1px solid var(--border);border-radius:12px;
padding:1rem;margin-bottom:.75rem}
.tool-card{background:var(--card);border:1px solid var(--border);border-radius:12px;
padding:1rem;margin-bottom:.75rem}
.disclaimer{background:#fef3c7;border-left:4px solid var(--warn);padding:1rem;
border-radius:0 8px 8px 0;margin-top:1.5rem;font-size:.85rem}
.app-footer{text-align:center;padding:2rem 0;color:var(--muted);border-top:1px solid var(--border);
margin-top:3rem;font-size:.85rem}
.sidebar .stButton>button{width:100%}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════
_DEFAULTS = {
    "api_key": "",
    "api_configured": False,
    "gemini_model": core.DEFAULT_MODEL,
    "response_mode": "standard",
    "task_type": "general",
    # AI results
    "ai_results": {},
    "followup_results": [],
    "research_results": "",
    # Data
    "cases": [],
    "clients": [],
    "time_entries": [],
    "invoices": [],
    "history": [],
    # Upload
    "doc_text": "",
    "doc_name": "",
    # Template
    "loaded_template": "",
}

for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Load history once
if not st.session_state.history:
    st.session_state.history = core.load_history()


# ═══════════════════════════════════════════════════════
# AUTO-CONNECT
# ═══════════════════════════════════════════════════════
def _auto_connect():
    if st.session_state.api_configured:
        return
    key = core.get_api_key(
        secrets_fn=lambda: st.secrets.get("GEMINI_API_KEY", ""),
        session_key=st.session_state.api_key,
    )
    if key and len(key) >= 10:
        st.session_state.api_key = key
        core.configure_api(key)
        st.session_state.api_configured = True


# ═══════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("## ⚖️ LexiAssist v7.0")
        st.caption("Smart Legal AI for Nigerian Lawyers")

        # API Key
        st.markdown("### 🔑 API Key")
        key_input = st.text_input(
            "Gemini API Key",
            value=st.session_state.api_key,
            type="password",
            placeholder="Enter key or set in secrets",
            key="sidebar_api_key_input",
        )
        if key_input != st.session_state.api_key:
            st.session_state.api_key = key_input
            if len(key_input) >= 10:
                core.configure_api(key_input)
                st.session_state.api_configured = True

        if st.session_state.api_configured:
            st.success("✅ API Connected")
        else:
            st.warning("⚠️ Enter API key")
            st.markdown("[Get free key →](https://aistudio.google.com/apikey)")

        # Model
        st.markdown("### 🤖 Model")
        current = core.normalize_model(st.session_state.gemini_model)
        idx = core.SUPPORTED_MODELS.index(current) if current in core.SUPPORTED_MODELS else 0
        model = st.selectbox("Model", core.SUPPORTED_MODELS, index=idx, key="sidebar_model_select")
        st.session_state.gemini_model = model

        # Response Mode
        st.markdown("### 📏 Response Mode")
        modes = list(core.RESPONSE_MODES.keys())
        labels = [core.RESPONSE_MODES[m]["label"] for m in modes]
        mi = modes.index(st.session_state.response_mode) if st.session_state.response_mode in modes else 1
        sel = st.radio("Mode", labels, index=mi, key="sidebar_mode_radio")
        st.session_state.response_mode = modes[labels.index(sel)]
        st.caption(core.RESPONSE_MODES[st.session_state.response_mode]["desc"])

        # Export All
        st.markdown("### 💾 Data")
        if st.download_button(
            "📦 Export All Data",
            core.export_all_data(
                st.session_state.cases, st.session_state.clients,
                st.session_state.time_entries, st.session_state.invoices,
            ),
            f"LexiAssist_Backup_{datetime.now():%Y%m%d}.json",
            "application/json",
            use_container_width=True,
            key="sidebar_export_btn",
        ):
            st.success("✅ Downloaded!")

        # Stats
        st.markdown("---")
        st.caption(f"📁 {len(st.session_state.cases)} cases · 👥 {len(st.session_state.clients)} clients")
        st.caption(f"📜 {len(st.session_state.history)} history entries")


# ═══════════════════════════════════════════════════════
# SAFE DOWNLOAD HELPER
# ═══════════════════════════════════════════════════════
def safe_pdf_button(text: str, title: str, fname: str, key: str):
    """Render PDF download button with error handling."""
    try:
        pdf_bytes = core.export_pdf(text, title)
        if pdf_bytes and len(pdf_bytes) > 0:
            st.download_button(
                "📥 PDF", pdf_bytes, f"{fname}.pdf",
                "application/pdf", key=key, use_container_width=True,
            )
        else:
            st.button("PDF N/A", disabled=True, key=f"{key}_na", use_container_width=True)
    except Exception:
        st.button("PDF N/A", disabled=True, key=f"{key}_err", use_container_width=True)


def safe_docx_button(text: str, title: str, fname: str, key: str):
    """Render DOCX download button with error handling."""
    try:
        docx_bytes = core.export_docx(text, title)
        if docx_bytes and len(docx_bytes) > 0:
            st.download_button(
                "📥 DOCX", docx_bytes, f"{fname}.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key=key, use_container_width=True,
            )
        else:
            st.button("DOCX N/A", disabled=True, key=f"{key}_na", use_container_width=True)
    except Exception:
        st.button("DOCX N/A", disabled=True, key=f"{key}_err", use_container_width=True)


# ═══════════════════════════════════════════════════════
# PAGE: HOME
# ═══════════════════════════════════════════════════════
def render_home():
    st.markdown(
        '<div class="page-header"><h1>⚖️ LexiAssist v7.0</h1>'
        '<p>AI-Powered Legal Assistant for Nigerian Lawyers</p></div>',
        unsafe_allow_html=True,
    )

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(
            f'<div class="stat-card"><div class="stat-value">{len(st.session_state.cases)}</div>'
            f'<div class="stat-label">📁 Cases</div></div>',
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            f'<div class="stat-card t-blue"><div class="stat-value">{len(st.session_state.clients)}</div>'
            f'<div class="stat-label">👥 Clients</div></div>',
            unsafe_allow_html=True,
        )
    with s3:
        hearings = core.get_hearings(st.session_state.cases)
        st.markdown(
            f'<div class="stat-card t-amber"><div class="stat-value">{len(hearings)}</div>'
            f'<div class="stat-label">📅 Hearings</div></div>',
            unsafe_allow_html=True,
        )
    with s4:
        tb = core.total_billable(st.session_state.time_entries)
        st.markdown(
            f'<div class="stat-card t-purple"><div class="stat-value">{core.esc(core.fmt_currency(tb))}</div>'
            f'<div class="stat-label">💰 Billable</div></div>',
            unsafe_allow_html=True,
        )

    # Urgent hearings
    if hearings:
        st.markdown("### 📅 Upcoming Hearings")
        for h in hearings[:5]:
            d = core.days_until(h["date"])
            b = "danger" if d <= 3 else ("warning" if d <= 7 else "success")
            st.markdown(
                f'<div class="custom-card"><strong>{core.esc(h["title"])}</strong> · '
                f'{core.esc(h["suit"])} · {core.esc(core.fmt_date(h["date"]))} '
                f'<span class="badge badge-{b}">{core.esc(core.relative_date(h["date"]))}</span></div>',
                unsafe_allow_html=True,
            )

    # Quick actions
    st.markdown("### ⚡ Quick Actions")
    qa1, qa2, qa3 = st.columns(3)
    with qa1:
        st.markdown(
            '<div class="custom-card"><h4>🧠 AI Assistant</h4>'
            '<p>Ask legal questions, draft documents</p></div>',
            unsafe_allow_html=True,
        )
    with qa2:
        st.markdown(
            '<div class="custom-card"><h4>📚 Research</h4>'
            '<p>Case law, statutes, authorities</p></div>',
            unsafe_allow_html=True,
        )
    with qa3:
        st.markdown(
            '<div class="custom-card"><h4>📋 Templates</h4>'
            '<p>Professional legal documents</p></div>',
            unsafe_allow_html=True,
        )

    # History
    if st.session_state.history:
        st.markdown("### 📜 Recent History")
        for entry in reversed(st.session_state.history[-5:]):
            ts = core.fmt_date(entry.get("timestamp", ""))
            grade = entry.get("grade", "")
            grade_html = f' <span class="badge badge-success">{core.esc(grade)}</span>' if grade else ""
            st.markdown(
                f'<div class="custom-card"><strong>{core.esc(entry.get("query", "")[:100])}</strong>'
                f'{grade_html}<br><small>{ts} · {core.esc(entry.get("mode", ""))}'
                f' · {core.esc(entry.get("task", ""))}</small></div>',
                unsafe_allow_html=True,
            )

        hc1, hc2 = st.columns(2)
        with hc1:
            if st.button("🗑️ Clear History", key="clear_history_home_btn"):
                core.clear_history()
                st.session_state.history = []
                st.rerun()
        with hc2:
            hist_json = json.dumps(st.session_state.history, indent=2, default=str)
            st.download_button(
                "📥 Export History", hist_json,
                f"LexiAssist_History_{datetime.now():%Y%m%d}.json",
                "application/json", key="export_history_home_btn",
                use_container_width=True,
            )


# ═══════════════════════════════════════════════════════
# PAGE: AI ASSISTANT
# ═══════════════════════════════════════════════════════
def render_ai():
    st.markdown(
        '<div class="page-header"><h1>🧠 AI Legal Assistant</h1>'
        '<p>Expert Nigerian legal analysis · Drafting · Research</p></div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key in the sidebar first.")

    mode = st.session_state.response_mode
    mode_info = core.RESPONSE_MODES[mode]
    st.info(f"**Response Mode: {mode_info['label']}** — {mode_info['desc']}")

    # Task type
    task_keys = list(core.TASK_TYPES.keys())
    task_labels = [f"{core.TASK_TYPES[t]['icon']} {core.TASK_TYPES[t]['label']}" for t in task_keys]
    ti = task_keys.index(st.session_state.task_type) if st.session_state.task_type in task_keys else 0
    sel_task = st.selectbox("Task Type", task_labels, index=ti, key="ai_task_select")
    st.session_state.task_type = task_keys[task_labels.index(sel_task)]

    # Document upload
    with st.expander("📎 Upload Document (optional)", expanded=False):
        uploaded = st.file_uploader(
            "Upload", type=["pdf", "docx", "txt", "csv", "xlsx"],
            key="ai_file_upload",
        )
        if uploaded:
            with st.spinner("📄 Extracting text…"):
                try:
                    text = core.extract_file_text(uploaded)
                    st.session_state.doc_text = text[:15000]
                    st.session_state.doc_name = uploaded.name
                    st.success(f"✅ {uploaded.name} — {len(text):,} chars extracted")
                except Exception as e:
                    st.error(f"❌ {e}")
        if st.session_state.doc_name:
            st.caption(f"📄 Active: {st.session_state.doc_name}")
            if st.button("❌ Remove Document", key="ai_remove_doc_btn"):
                st.session_state.doc_text = ""
                st.session_state.doc_name = ""
                st.rerun()

    # Loaded template
    if st.session_state.loaded_template:
        st.info("📋 Template loaded — it will be included in your query context.")
        if st.button("❌ Remove Template", key="ai_remove_tmpl_btn"):
            st.session_state.loaded_template = ""
            st.rerun()

    # Query input
    query = st.text_area(
        "💬 Your Legal Question",
        height=140,
        placeholder="e.g. 'What is the limitation period for breach of contract under Nigerian law?'",
        key="ai_query_input",
    )

    # Action buttons
    bc1, bc2 = st.columns([3, 1])
    with bc1:
        go = st.button(
            f"🧠 Analyze ({mode_info['label']})", type="primary",
            use_container_width=True,
            disabled=not st.session_state.api_configured,
            key="ai_go_btn",
        )
    with bc2:
        clr = st.button("🗑️ Clear All", use_container_width=True, key="clear_all_btn")

    if clr:
        st.session_state.ai_results = {}
        st.session_state.followup_results = []
        st.session_state.doc_text = ""
        st.session_state.doc_name = ""
        st.session_state.loaded_template = ""
        st.rerun()

    # Run analysis
    if go and query.strip():
        core.configure_api(st.session_state.api_key)
        full_query = query.strip()
        if st.session_state.loaded_template:
            full_query += f"\n\n[TEMPLATE CONTEXT]\n{st.session_state.loaded_template}"

        with st.spinner(f"🧠 Analyzing ({mode_info['label']})…"):
            results = core.run_pipeline(
                full_query,
                st.session_state.task_type,
                mode,
                st.session_state.gemini_model,
                doc_context=st.session_state.doc_text,
            )
            st.session_state.ai_results = results
            st.session_state.followup_results = []

        # Save to history
        if results.get("main") and not results["main"].startswith(("Error", "⚠️")):
            entry = {
                "id": core.gen_id(),
                "timestamp": datetime.now().isoformat(),
                "query": query[:400],
                "task": st.session_state.task_type,
                "mode": mode,
                "response": results["main"][:3000],
                "grade": results.get("grade", ""),
            }
            st.session_state.history.append(entry)
            core.save_history(st.session_state.history)

    # Display results
    results = st.session_state.ai_results
    if results and results.get("main"):
        st.markdown("---")
        text = results["main"]
        wc = len(text.split())
        grade = results.get("grade", "")

        # Header
        hdr = f"📝 {wc:,} words"
        if grade:
            hdr += f" · Grade: **{grade}**"
        st.caption(hdr)

        # Export buttons
        fname = f"LexiAssist_{datetime.now():%Y%m%d_%H%M}"
        ex1, ex2, ex3, ex4 = st.columns(4)
        with ex1:
            st.download_button(
                "📥 TXT", core.export_txt(text),
                f"{fname}.txt", "text/plain",
                key="dl_txt", use_container_width=True,
            )
        with ex2:
            st.download_button(
                "📥 HTML", core.export_html(text),
                f"{fname}.html", "text/html",
                key="dl_html", use_container_width=True,
            )
        with ex3:
            safe_pdf_button(text, "LexiAssist Analysis", fname, "dl_pdf")
        with ex4:
            safe_docx_button(text, "LexiAssist Analysis", fname, "dl_docx")

        # Issue spot (comprehensive only)
        if results.get("issue_spot"):
            with st.expander("🔍 Issue Decomposition", expanded=False):
                st.markdown(
                    f'<div class="response-box">{core.esc(results["issue_spot"])}</div>',
                    unsafe_allow_html=True,
                )

        # Main response
        st.markdown(
            f'<div class="response-box">{core.esc(text)}</div>',
            unsafe_allow_html=True,
        )

        # Critique (comprehensive only)
        if results.get("critique"):
            with st.expander("📊 Quality Assessment", expanded=False):
                st.markdown(
                    f'<div class="response-box">{core.esc(results["critique"])}</div>',
                    unsafe_allow_html=True,
                )

        # Disclaimer
        st.markdown(
            '<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated legal information. '
            'Not legal advice. Verify all citations independently.</div>',
            unsafe_allow_html=True,
        )

        # Follow-up section
        st.markdown("---")
        st.markdown("### 💬 Follow-Up Question")
        fq = st.text_input(
            "Ask a follow-up", placeholder="e.g. 'What about limitation?'",
            key="followup_input",
        )
        if st.button("💬 Ask Follow-Up", key="followup_btn", disabled=not st.session_state.api_configured):
            if fq.strip():
                core.configure_api(st.session_state.api_key)
                with st.spinner("💬 Processing follow-up…"):
                    prev_context = text[:3000]
                    fu_result = core.run_followup(
                        query if query else "", prev_context,
                        fq.strip(), mode, st.session_state.task_type,
                        st.session_state.gemini_model,
                    )
                    st.session_state.followup_results.append({
                        "question": fq.strip(),
                        "answer": fu_result,
                    })

        # Show follow-ups
        for i, fu in enumerate(st.session_state.followup_results):
            st.markdown(
                f'<div class="custom-card"><strong>Q: {core.esc(fu["question"])}</strong></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="response-box">{core.esc(fu["answer"])}</div>',
                unsafe_allow_html=True,
            )

# ═══════════════════════════════════════════════════════
# PAGE: RESEARCH
# ═══════════════════════════════════════════════════════
def render_research():
    st.markdown(
        '<div class="page-header"><h1>📚 Legal Research</h1>'
        '<p>Case law · Statutes · Authorities</p></div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key in the sidebar first.")

    mode = st.session_state.response_mode
    mode_info = core.RESPONSE_MODES[mode]
    st.info(f"**Research Mode: {mode_info['label']}** — {mode_info['desc']}")

    query = st.text_area(
        "🔍 Research Query",
        height=120,
        placeholder="e.g. 'What are the grounds for setting aside an arbitral award under Nigerian law?'",
        key="research_query_input",
    )

    if st.button(
        f"📚 Research ({mode_info['label']})", type="primary",
        use_container_width=True,
        disabled=not st.session_state.api_configured,
        key="research_go_btn",
    ):
        if query.strip():
            core.configure_api(st.session_state.api_key)
            with st.spinner("📚 Researching…"):
                result = core.run_research(
                    query.strip(), mode, st.session_state.gemini_model,
                )
                st.session_state.research_results = result

    result = st.session_state.research_results
    if result:
        st.markdown("---")
        wc = len(result.split())
        st.caption(f"📝 {wc:,} words")

        fname = f"LexiAssist_Research_{datetime.now():%Y%m%d_%H%M}"
        ex1, ex2, ex3, ex4 = st.columns(4)
        with ex1:
            st.download_button(
                "📥 TXT", core.export_txt(result, "Legal Research"),
                f"{fname}.txt", "text/plain",
                key="res_dl_txt", use_container_width=True,
            )
        with ex2:
            st.download_button(
                "📥 HTML", core.export_html(result, "Legal Research"),
                f"{fname}.html", "text/html",
                key="res_dl_html", use_container_width=True,
            )
        with ex3:
            safe_pdf_button(result, "Legal Research", fname, "res_dl_pdf")
        with ex4:
            safe_docx_button(result, "Legal Research", fname, "res_dl_docx")

        st.markdown(
            f'<div class="response-box">{core.esc(result)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated legal research. '
            'Verify all citations independently.</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════
# PAGE: CASES
# ═══════════════════════════════════════════════════════
def render_cases():
    st.markdown(
        '<div class="page-header"><h1>📁 Case Manager</h1>'
        '<p>Track your cases, hearings, and deadlines</p></div>',
        unsafe_allow_html=True,
    )

    tab_list, tab_add = st.tabs(["📋 All Cases", "➕ Add Case"])

    with tab_add:
        with st.form("add_case_form", clear_on_submit=True):
            st.markdown("### ➕ New Case")
            c1, c2 = st.columns(2)
            with c1:
                title = st.text_input("Case Title *", key="case_title_inp")
                suit_no = st.text_input("Suit Number", key="case_suit_inp")
                court = st.text_input("Court", key="case_court_inp")
            with c2:
                status = st.selectbox("Status", core.CASE_STATUSES, key="case_status_inp")
                client_names = ["— None —"] + [c.get("name", "?") for c in st.session_state.clients]
                client_sel = st.selectbox("Client", client_names, key="case_client_inp")
                next_hearing = st.date_input("Next Hearing", value=None, key="case_hearing_inp")
            notes = st.text_area("Notes", height=80, key="case_notes_inp")

            if st.form_submit_button("➕ Add Case", type="primary"):
                if title.strip():
                    client_id = ""
                    if client_sel != "— None —":
                        idx = client_names.index(client_sel) - 1
                        client_id = st.session_state.clients[idx]["id"]
                    case_data = {
                        "title": title.strip(),
                        "suit_no": suit_no.strip(),
                        "court": court.strip(),
                        "status": status,
                        "client_id": client_id,
                        "next_hearing": str(next_hearing) if next_hearing else "",
                        "notes": notes.strip(),
                    }
                    core.add_case(st.session_state.cases, case_data)
                    st.success(f"✅ Case '{title}' added!")
                    st.rerun()
                else:
                    st.error("❌ Case title is required.")

    with tab_list:
        cases = st.session_state.cases
        if not cases:
            st.info("No cases yet. Add one above.")
        else:
            # Filter
            statuses = ["All"] + core.CASE_STATUSES
            filt = st.selectbox("Filter by Status", statuses, key="case_filter_sel")
            filtered = cases if filt == "All" else [c for c in cases if c.get("status") == filt]

            for c in filtered:
                d = core.days_until(c.get("next_hearing", ""))
                badge_cls = "danger" if d <= 3 else ("warning" if d <= 7 else "success")
                hearing_txt = core.fmt_date(c.get("next_hearing", "")) if c.get("next_hearing") else "—"
                client_name = core.client_name(st.session_state.clients, c.get("client_id", ""))

                st.markdown(
                    f'<div class="custom-card">'
                    f'<h4>{core.esc(c.get("title", "Untitled"))}</h4>'
                    f'<span class="badge badge-info">{core.esc(c.get("status", ""))}</span> '
                    f'Suit: {core.esc(c.get("suit_no", "—"))} · '
                    f'Court: {core.esc(c.get("court", "—"))} · '
                    f'Client: {core.esc(client_name)} · '
                    f'Hearing: {core.esc(hearing_txt)} '
                    f'<span class="badge badge-{badge_cls}">{core.esc(core.relative_date(c.get("next_hearing", "")))}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                with st.expander(f"✏️ Manage: {c.get('title', '')[:40]}", expanded=False):
                    mc1, mc2 = st.columns(2)
                    with mc1:
                        new_status = st.selectbox(
                            "Update Status",
                            core.CASE_STATUSES,
                            index=core.CASE_STATUSES.index(c["status"]) if c.get("status") in core.CASE_STATUSES else 0,
                            key=f"case_status_{c['id']}",
                        )
                        new_hearing = st.date_input("Update Hearing", value=None, key=f"case_hear_{c['id']}")
                        if st.button("💾 Save", key=f"save_case_{c['id']}"):
                            updates = {"status": new_status}
                            if new_hearing:
                                updates["next_hearing"] = str(new_hearing)
                            core.update_case(st.session_state.cases, c["id"], updates)
                            st.success("✅ Updated!")
                            st.rerun()
                    with mc2:
                        if c.get("notes"):
                            st.caption(f"📝 {c['notes'][:200]}")
                        if st.button("🗑️ Delete Case", key=f"del_case_{c['id']}"):
                            st.session_state.cases = core.delete_case(st.session_state.cases, c["id"])
                            st.success("✅ Deleted!")
                            st.rerun()


# ═══════════════════════════════════════════════════════
# PAGE: CALENDAR
# ═══════════════════════════════════════════════════════
def render_calendar():
    st.markdown(
        '<div class="page-header"><h1>📅 Hearing Calendar</h1>'
        '<p>Upcoming hearings and deadlines</p></div>',
        unsafe_allow_html=True,
    )

    hearings = core.get_hearings(st.session_state.cases)
    if not hearings:
        st.info("No upcoming hearings. Add cases with hearing dates.")
        return

    for h in hearings:
        d = core.days_until(h["date"])
        cls = "urgent" if d <= 3 else ("warn" if d <= 7 else "")
        st.markdown(
            f'<div class="cal-event {cls}">'
            f'<h4>{core.esc(h["title"])}</h4>'
            f'Suit: {core.esc(h["suit"])} · Court: {core.esc(h["court"])}<br>'
            f'📅 {core.esc(core.fmt_date(h["date"]))} '
            f'<span class="badge badge-{"danger" if d <= 3 else ("warning" if d <= 7 else "success")}">'
            f'{core.esc(core.relative_date(h["date"]))}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════
# PAGE: TEMPLATES
# ═══════════════════════════════════════════════════════
def render_templates():
    st.markdown(
        '<div class="page-header"><h1>📋 Document Templates</h1>'
        '<p>Professional Nigerian legal document templates</p></div>',
        unsafe_allow_html=True,
    )

    cats = sorted(set(t["cat"] for t in core.TEMPLATES))
    sel_cat = st.selectbox("Category", ["All"] + cats, key="tmpl_cat_sel")

    templates = core.TEMPLATES if sel_cat == "All" else [t for t in core.TEMPLATES if t["cat"] == sel_cat]

    for t in templates:
        st.markdown(
            f'<div class="tmpl-card"><strong>{core.esc(t["name"])}</strong> '
            f'<span class="badge badge-info">{core.esc(t["cat"])}</span></div>',
            unsafe_allow_html=True,
        )
        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            if st.button(f"👁️ Preview", key=f"preview_tmpl_{t['id']}"):
                st.code(t["content"], language=None)
        with tc2:
            if st.button(f"📋 Load to AI", key=f"load_tmpl_{t['id']}"):
                st.session_state.loaded_template = t["content"]
                st.success(f"✅ '{t['name']}' loaded! Go to AI Assistant.")
        with tc3:
            st.download_button(
                "📥 Download",
                t["content"],
                f"{t['name'].replace(' ', '_')}.txt",
                "text/plain",
                key=f"dl_tmpl_{t['id']}",
            )


# ═══════════════════════════════════════════════════════
# PAGE: CLIENTS
# ═══════════════════════════════════════════════════════
def render_clients():
    st.markdown(
        '<div class="page-header"><h1>👥 Client Manager</h1>'
        '<p>Manage your client database</p></div>',
        unsafe_allow_html=True,
    )

    tab_list, tab_add = st.tabs(["👥 All Clients", "➕ Add Client"])

    with tab_add:
        with st.form("add_client_form", clear_on_submit=True):
            st.markdown("### ➕ New Client")
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Client Name *", key="client_name_inp")
                email = st.text_input("Email", key="client_email_inp")
                phone = st.text_input("Phone", key="client_phone_inp")
            with c2:
                client_type = st.selectbox("Type", core.CLIENT_TYPES, key="client_type_inp")
                address = st.text_area("Address", height=80, key="client_addr_inp")

            if st.form_submit_button("➕ Add Client", type="primary"):
                if name.strip():
                    client_data = {
                        "name": name.strip(),
                        "email": email.strip(),
                        "phone": phone.strip(),
                        "type": client_type,
                        "address": address.strip(),
                    }
                    core.add_client(st.session_state.clients, client_data)
                    st.success(f"✅ Client '{name}' added!")
                    st.rerun()
                else:
                    st.error("❌ Client name is required.")

    with tab_list:
        clients = st.session_state.clients
        if not clients:
            st.info("No clients yet. Add one above.")
        else:
            for cl in clients:
                cc = core.client_case_count(st.session_state.cases, cl["id"])
                bill = core.client_billable(st.session_state.time_entries, cl["id"])
                st.markdown(
                    f'<div class="custom-card">'
                    f'<h4>{core.esc(cl.get("name", ""))}</h4>'
                    f'<span class="badge badge-info">{core.esc(cl.get("type", ""))}</span> '
                    f'📧 {core.esc(cl.get("email", "—"))} · 📞 {core.esc(cl.get("phone", "—"))} · '
                    f'📁 {cc} cases · 💰 {core.esc(core.fmt_currency(bill))}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button(f"🗑️ Delete", key=f"del_client_{cl['id']}"):
                    st.session_state.clients = core.delete_client(st.session_state.clients, cl["id"])
                    st.success("✅ Deleted!")
                    st.rerun()


# ═══════════════════════════════════════════════════════
# PAGE: BILLING
# ═══════════════════════════════════════════════════════
def render_billing():
    st.markdown(
        '<div class="page-header"><h1>💰 Billing Manager</h1>'
        '<p>Time entries, invoicing, and financials</p></div>',
        unsafe_allow_html=True,
    )

    tab_time, tab_inv, tab_report = st.tabs(["⏱️ Time Entries", "📄 Invoices", "📊 Reports"])

    with tab_time:
        with st.form("add_time_form", clear_on_submit=True):
            st.markdown("### ➕ New Time Entry")
            t1, t2 = st.columns(2)
            with t1:
                client_names = [c.get("name", "?") for c in st.session_state.clients]
                if not client_names:
                    st.warning("Add a client first.")
                    client_sel_b = None
                else:
                    client_sel_b = st.selectbox("Client *", client_names, key="bill_client_inp")
                desc = st.text_input("Description *", key="bill_desc_inp")
            with t2:
                hours = st.number_input("Hours *", min_value=0.0, step=0.25, key="bill_hours_inp")
                rate = st.number_input("Rate (₦/hr) *", min_value=0.0, step=1000.0, value=50000.0, key="bill_rate_inp")
                entry_date = st.date_input("Date", key="bill_date_inp")

            if st.form_submit_button("➕ Add Entry", type="primary"):
                if client_sel_b and desc.strip() and hours > 0:
                    idx = client_names.index(client_sel_b)
                    entry_data = {
                        "client_id": st.session_state.clients[idx]["id"],
                        "client_name": client_sel_b,
                        "description": desc.strip(),
                        "hours": hours,
                        "rate": rate,
                        "date": str(entry_date),
                    }
                    core.add_time_entry(st.session_state.time_entries, entry_data)
                    st.success(f"✅ {hours}h @ {core.fmt_currency(rate)}/hr added!")
                    st.rerun()
                else:
                    st.error("❌ Fill all required fields.")

        # List entries
        if st.session_state.time_entries:
            st.markdown("### 📋 Recent Entries")
            for te in reversed(st.session_state.time_entries[-20:]):
                st.markdown(
                    f'<div class="custom-card">'
                    f'<strong>{core.esc(te.get("description", ""))}</strong><br>'
                    f'{core.esc(te.get("client_name", ""))} · '
                    f'{te.get("hours", 0)}h @ {core.esc(core.fmt_currency(te.get("rate", 0)))}/hr · '
                    f'<strong>{core.esc(core.fmt_currency(te.get("amount", 0)))}</strong> · '
                    f'{core.esc(core.fmt_date(te.get("date", "")))}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    with tab_inv:
        st.markdown("### 📄 Generate Invoice")
        if st.session_state.clients:
            client_names_inv = [c.get("name", "?") for c in st.session_state.clients]
            inv_client = st.selectbox("Client", client_names_inv, key="inv_client_sel")
            if st.button("📄 Generate Invoice", type="primary", key="gen_inv_btn"):
                idx = client_names_inv.index(inv_client)
                cid = st.session_state.clients[idx]["id"]
                inv = core.make_invoice(
                    st.session_state.invoices, st.session_state.time_entries,
                    st.session_state.clients, cid,
                )
                if inv:
                    st.success(f"✅ Invoice {inv['invoice_no']} generated — {core.fmt_currency(inv['total'])}")
                else:
                    st.warning("No time entries found for this client.")
        else:
            st.info("Add clients first.")

        # Show invoices
        if st.session_state.invoices:
            st.markdown("### 📋 Invoices")
            for inv in reversed(st.session_state.invoices):
                inv_text = (
                    f"INVOICE: {inv['invoice_no']}\n"
                    f"Date: {core.fmt_date(inv['date'])}\n"
                    f"Client: {inv['client_name']}\n"
                    f"Total: {core.fmt_currency(inv['total'])}\n\n"
                    "ENTRIES:\n"
                )
                for e in inv.get("entries", []):
                    inv_text += f"- {e.get('description', '')} | {e.get('hours', 0)}h | {core.fmt_currency(e.get('amount', 0))}\n"

                st.markdown(
                    f'<div class="custom-card">'
                    f'<h4>{core.esc(inv["invoice_no"])}</h4>'
                    f'{core.esc(inv["client_name"])} · '
                    f'{core.esc(core.fmt_date(inv["date"]))} · '
                    f'<strong>{core.esc(core.fmt_currency(inv["total"]))}</strong>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                inv_c1, inv_c2, inv_c3 = st.columns(3)
                with inv_c1:
                    st.download_button(
                        "📥 TXT", core.export_txt(inv_text, f"Invoice {inv['invoice_no']}"),
                        f"Invoice_{inv['invoice_no']}.txt", "text/plain",
                        key=f"inv_dl_txt_{inv['id']}", use_container_width=True,
                    )
                with inv_c2:
                    safe_pdf_button(
                        inv_text, f"Invoice {inv['invoice_no']}",
                        f"Invoice_{inv['invoice_no']}", f"inv_dl_pdf_{inv['id']}",
                    )
                with inv_c3:
                    safe_docx_button(
                        inv_text, f"Invoice {inv['invoice_no']}",
                        f"Invoice_{inv['invoice_no']}", f"inv_dl_docx_{inv['id']}",
                    )

    with tab_report:
        st.markdown("### 📊 Billing Summary")
        entries = st.session_state.time_entries
        if entries:
            total_h = core.total_hours(entries)
            total_b = core.total_billable(entries)
            r1, r2, r3 = st.columns(3)
            with r1:
                st.metric("Total Hours", f"{total_h:.1f}")
            with r2:
                st.metric("Total Billable", core.fmt_currency(total_b))
            with r3:
                avg = total_b / total_h if total_h else 0
                st.metric("Avg Rate", core.fmt_currency(avg))

            # Chart
            df = pd.DataFrame(entries)
            if "client_name" in df.columns and "amount" in df.columns:
                chart_df = df.groupby("client_name")["amount"].sum().reset_index()
                chart_df.columns = ["Client", "Amount"]
                fig = px.bar(
                    chart_df, x="Client", y="Amount",
                    title="Billable Amount by Client",
                    color_discrete_sequence=["#059669"],
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No time entries to report.")


# ═══════════════════════════════════════════════════════
# PAGE: TOOLS
# ═══════════════════════════════════════════════════════
def render_tools():
    st.markdown(
        '<div class="page-header"><h1>🔧 Legal Tools</h1>'
        '<p>Reference tools for Nigerian lawyers</p></div>',
        unsafe_allow_html=True,
    )

    tab_lim, tab_court, tab_maxim = st.tabs(["⏳ Limitation Periods", "🏛️ Court Hierarchy", "📜 Legal Maxims"])

    with tab_lim:
        st.markdown("### ⏳ Limitation Periods (Nigeria)")
        df_lim = pd.DataFrame(core.LIMITATION_PERIODS)
        st.dataframe(df_lim, use_container_width=True, hide_index=True)

    with tab_court:
        st.markdown("### 🏛️ Nigerian Court Hierarchy")
        for c in core.COURT_HIERARCHY:
            indent = "—" * (c["level"] - 1)
            st.markdown(
                f'<div class="tool-card">'
                f'{c["icon"]} {indent} <strong>{core.esc(c["name"])}</strong><br>'
                f'<small>{core.esc(c["desc"])}</small></div>',
                unsafe_allow_html=True,
            )

    with tab_maxim:
        st.markdown("### 📜 Legal Maxims")
        search = st.text_input("🔍 Search maxims", key="maxim_search")
        maxims = core.LEGAL_MAXIMS
        if search:
            s = search.lower()
            maxims = [m for m in maxims if s in m["maxim"].lower() or s in m["meaning"].lower()]
        for m in maxims:
            st.markdown(
                f'<div class="tool-card"><strong><em>{core.esc(m["maxim"])}</em></strong><br>'
                f'{core.esc(m["meaning"])}</div>',
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════
def main():
    _auto_connect()
    render_sidebar()

    pages = {
        "🏠 Home": render_home,
        "🧠 AI Assistant": render_ai,
        "📚 Research": render_research,
        "📁 Cases": render_cases,
        "📅 Calendar": render_calendar,
        "📋 Templates": render_templates,
        "👥 Clients": render_clients,
        "💰 Billing": render_billing,
        "🔧 Tools": render_tools,
    }

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📌 Navigation")
        page = st.radio("Go to", list(pages.keys()), label_visibility="collapsed", key="nav_radio")

    pages[page]()

    st.markdown(
        '<div class="app-footer">⚖️ LexiAssist v7.0 · Smart Legal AI for Nigerian Lawyers<br>'
        '⚠️ AI-generated information · Not legal advice · Verify all citations</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
