"""LexiAssist document templates page."""
from __future__ import annotations

# Barrel import: mirrors the global namespace of the original single-file
# app.py exactly. The original code below is unchanged.
from ..runtime import *      # noqa: F401, F403
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
# PAGE: TEMPLATES (FULL CRUD)
# ═══════════════════════════════════════════════════════
def render_templates():
    st.markdown("""<div class="page-header">
        <h2>📋 Document Templates</h2>
        <p>Built-in and custom Nigerian legal document templates</p>
    </div>""", unsafe_allow_html=True)

    tab_browse, tab_add, tab_manage = st.tabs(["📄 Browse Templates", "➕ Add Custom", "⚙️ Manage Custom"])

    all_templates = get_all_templates()

    with tab_browse:
        cats = sorted(set(t["cat"] for t in all_templates))
        sel_cat = st.selectbox("Filter by Category", ["All"] + cats, key="tmpl_cat_sel")

        templates = all_templates if sel_cat == "All" else [t for t in all_templates if t["cat"] == sel_cat]

        for t in templates:
            is_builtin = t.get("builtin", False)
            badge_html = '<span class="badge badge-ok">Built-in</span>' if is_builtin else '<span class="badge badge-info">Custom</span>'
            st.markdown(f"""<div class="custom-card">
                <h4>{esc(t['name'])}</h4>
                <span class="badge badge-info">{esc(t['cat'])}</span> {badge_html}
            </div>""", unsafe_allow_html=True)

            tc1, tc2, tc3 = st.columns(3)
            with tc1:
                if st.button("👁️ Preview", key=f"prev_t_{t['id']}", use_container_width=True):
                    st.code(t["content"], language=None)
            with tc2:
                if st.button("📋 Load to AI", key=f"load_t_{t['id']}", use_container_width=True):
                    st.session_state.loaded_template = t["content"]
                    st.session_state["_active_fill_tmpl"] = t["id"]
                    st.success(f"✅ '{t['name']}' loaded! Go to AI Assistant tab.")
            with tc3:
                _fill_active = st.session_state.get("_active_fill_tmpl") == t["id"]
                _fill_label = "✏️ Close Form" if _fill_active else "✏️ Fill Template"
                if st.button(_fill_label, key=f"fill_t_{t['id']}", use_container_width=True):
                    if _fill_active:
                        st.session_state.pop("_active_fill_tmpl", None)
                    else:
                        st.session_state["_active_fill_tmpl"] = t["id"]
                    st.rerun()

            # ── Phase 4: Placeholder fill form — always rendered from session state, survives reruns ──
            if st.session_state.get("_active_fill_tmpl") == t["id"]:
                placeholders = re.findall(r'\[([A-Z][A-Z0-9 _/]+)\]', t["content"])
                placeholders = list(dict.fromkeys(placeholders))  # dedupe, preserve order
                if placeholders:
                    st.info(
                        f"📋 This template has **{len(placeholders)} placeholder(s)**. "
                        "Fill them in below to get a ready-to-use draft."
                    )
                    with st.expander("✏️ Fill Placeholders", expanded=True):
                        fill_vals = {}
                        cols_per_row = 2
                        ph_rows = [placeholders[i:i+cols_per_row] for i in range(0, len(placeholders), cols_per_row)]
                        for row in ph_rows:
                            row_cols = st.columns(len(row))
                            for col, ph in zip(row_cols, row):
                                with col:
                                    fill_vals[ph] = st.text_input(
                                        ph.replace("_", " ").title(),
                                        key=f"ph_{t['id']}_{ph}",
                                        placeholder=f"Enter {ph.lower()}…",
                                    )
                        if st.button("⚡ Generate Filled Draft", key=f"fill_btn_{t['id']}", type="primary", use_container_width=True):
                            filled = t["content"]
                            for ph, val in fill_vals.items():
                                if val.strip():
                                    filled = filled.replace(f"[{ph}]", val.strip())
                            unfilled = re.findall(r'\[[A-Z][A-Z0-9 _/]+\]', filled)
                            if unfilled:
                                st.warning(f"⚠️ {len(unfilled)} placeholder(s) still empty: {', '.join(unfilled[:5])}")
                            st.session_state[f"filled_template_{t['id']}"] = filled
                            st.success("✅ Draft generated! See below.")
                else:
                    st.info("ℹ️ This template has no placeholders — use 'Load to AI' directly.")

            # Show filled draft if available
            filled_key = f"filled_template_{t.get('id','')}"
            if st.session_state.get(filled_key):
                filled_draft = st.session_state[filled_key]
                st.markdown("##### 📄 Filled Draft")
                st.text_area("Review / Edit", filled_draft, height=300, key=f"filled_ta_{t.get('id','')}")
                ft_fname = f"LexiAssist_FilledTemplate_{datetime.now():%Y%m%d_%H%M}"
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    st.download_button(
                        "📥 TXT", export_txt(filled_draft, t.get("title","")),
                        f"{ft_fname}.txt", "text/plain", key=f"ft_dl_txt_{t.get('id','')}", use_container_width=True,
                    )
                with fc2:
                    safe_pdf_download(filled_draft, t.get("title","Template"), ft_fname, f"ft_dl_pdf_{t.get('id','')}")
                with fc3:
                    safe_docx_download(filled_draft, t.get("title","Template"), ft_fname, f"ft_dl_docx_{t.get('id','')}")
                if st.button("🧠 Send to AI for Polish", key=f"ft_ai_{t.get('id','')}", use_container_width=True):
                    with st.spinner("🧠 AI polishing…"):
                        polish_prompt = (
                            "Polish the following Nigerian legal document. "
                            "Ensure grammatical correctness, professional tone, "
                            "and legal completeness. Do not change the substantive "
                            "legal meaning or any specific details. Return the full document:\n\n"
                            + filled_draft
                        )
                        polished = generate(polish_prompt, IDENTITY_CORE, "standard", "drafting")
                    st.session_state[filled_key] = polished
                    st.success("✅ Polished! Scroll up to review.")
                    st.rerun()

            # ── Raw download of template (moved from old tc3) ──
            dl1, dl2, dl3 = st.columns(3)
            with dl1:
                st.download_button(
                    "📥 Download", t["content"],
                    f"{t['name'].replace(' ', '_')}.txt", "text/plain",
                    key=f"dl_t_{t['id']}", use_container_width=True,
                )

    with tab_add:
        st.markdown("#### ➕ Create Custom Template")
        with st.form("add_template_form", clear_on_submit=True):
            tmpl_name = st.text_input("Template Name *", key="tmpl_name_inp")
            tmpl_cat = st.text_input("Category *", placeholder="e.g. Corporate, Litigation, Property", key="tmpl_cat_inp")
            tmpl_content = st.text_area("Template Content *", height=300,
                                        placeholder="Type your template here.\nUse [PLACEHOLDER] for variable fields.",
                                        key="tmpl_content_inp")

            if st.form_submit_button("➕ Add Template", type="primary"):
                if tmpl_name.strip() and tmpl_cat.strip() and tmpl_content.strip():
                    new_tmpl = {
                        "id": f"custom_{new_id()}",
                        "name": tmpl_name.strip(),
                        "cat": tmpl_cat.strip(),
                        "content": tmpl_content.strip(),
                        "builtin": False,
                        "created_at": datetime.now().isoformat(),
                    }
                    st.session_state.custom_templates.append(new_tmpl)
                    persist("custom_templates")
                    st.success(f"✅ Template '{tmpl_name}' created!")
                    st.rerun()
                else:
                    st.error("❌ All fields are required.")

    with tab_manage:
        custom = st.session_state.custom_templates
        if not custom:
            st.info("No custom templates yet. Add one in the ➕ Add Custom tab.")
            return

        st.caption(f"{len(custom)} custom template(s)")
        for i, t in enumerate(custom):
            st.markdown(f"""<div class="custom-card">
                <h4>{esc(t['name'])}</h4>
                <span class="badge badge-info">{esc(t['cat'])}</span>
                <span class="badge badge-info">Custom</span>
                <small> · Created: {esc(fmt_date(t.get('created_at', '')))}</small>
            </div>""", unsafe_allow_html=True)

            with st.expander(f"✏️ Edit / Delete: {t['name']}", expanded=False):
                edit_name = st.text_input("Name", value=t["name"], key=f"et_name_{t['id']}")
                edit_cat = st.text_input("Category", value=t["cat"], key=f"et_cat_{t['id']}")
                edit_content = st.text_area("Content", value=t["content"], height=200, key=f"et_content_{t['id']}")

                ec1, ec2 = st.columns(2)
                with ec1:
                    if st.button("💾 Save Changes", key=f"et_save_{t['id']}", use_container_width=True):
                        st.session_state.custom_templates[i]["name"] = edit_name.strip()
                        st.session_state.custom_templates[i]["cat"] = edit_cat.strip()
                        st.session_state.custom_templates[i]["content"] = edit_content.strip()
                        st.session_state.custom_templates[i]["updated_at"] = datetime.now().isoformat()
                        persist("custom_templates")
                        st.success("✅ Template updated!")
                        st.rerun()
                with ec2:
                    if st.button("🗑️ Delete Template", key=f"et_del_{t['id']}", type="secondary", use_container_width=True):
                        st.session_state.custom_templates.pop(i)
                        persist("custom_templates")
                        st.success("✅ Deleted!")
                        st.rerun()

