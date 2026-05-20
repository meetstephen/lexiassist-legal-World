"""LexiAssist clients page."""
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
# PAGE: CLIENTS
# ═══════════════════════════════════════════════════════
def render_clients():
    st.markdown("""<div class="page-header">
        <h2>👥 Client Manager</h2>
        <p>Manage your client database and track engagement</p>
    </div>""", unsafe_allow_html=True)

    tab_list, tab_add = st.tabs(["👥 All Clients", "➕ Add Client"])

    with tab_add:
        with st.form("add_client_form", clear_on_submit=True):
            st.markdown("#### ➕ New Client")
            cc1, cc2 = st.columns(2)
            with cc1:
                name = st.text_input("Client Name *", key="cl_name_inp")
                email = st.text_input("Email", key="cl_email_inp")
                phone = st.text_input("Phone", key="cl_phone_inp")
            with cc2:
                cl_type = st.selectbox("Type", CLIENT_TYPES, key="cl_type_inp")
                address = st.text_area("Address", height=80, key="cl_addr_inp")
            notes = st.text_input("Notes", key="cl_notes_inp")

            if st.form_submit_button("➕ Add Client", type="primary"):
                if name.strip():
                    add_client({
                        "name": name.strip(), "email": email.strip(),
                        "phone": phone.strip(), "type": cl_type,
                        "address": address.strip(), "notes": notes.strip(),
                    })
                    st.success(f"✅ Client '{name}' added!")
                    st.rerun()
                else:
                    st.error("❌ Client name is required.")

    with tab_list:
        clients = st.session_state.clients
        if not clients:
            st.markdown(
                '<div style="text-align:center;padding:2.5rem 1rem;border:2px dashed '
                'var(--la-border);border-radius:12px;margin-top:1rem;">'
                '<div style="font-size:3rem;margin-bottom:0.6rem;">👥</div>'
                '<h3 style="margin:0 0 0.4rem 0;">No Clients Yet</h3>'
                '<p style="color:var(--la-text2);margin:0 0 1rem 0;max-width:360px;'
                'margin-left:auto;margin-right:auto;">Build your client database — link clients '
                'to cases and track billables automatically.</p>'
                '<p style="font-size:0.82rem;color:var(--la-text2);">'
                '<strong>Example:</strong> <em>Adekunle Adeyemi (Individual) · '
                '07012345678 · Lagos Island — debt recovery matter</em></p>'
                '<p style="font-size:0.82rem;color:var(--la-text2);">'
                '👆 Click the <strong>➕ Add Client</strong> tab above to get started.'
                '</p></div>',
                unsafe_allow_html=True,
            )
            return

        search = st.text_input("🔍 Search clients", key="cl_search_inp", placeholder="Name, email, type…")
        filtered = clients
        if search.strip():
            s = search.strip().lower()
            filtered = [c for c in filtered if s in c.get("name", "").lower() or s in c.get("email", "").lower() or s in c.get("type", "").lower()]

        for cl in filtered:
            cc = client_case_count(cl["id"])
            bill = client_billable(cl["id"])
            st.markdown(f"""<div class="custom-card">
                <h4>{esc(cl.get('name', ''))}</h4>
                <span class="badge badge-info">{esc(cl.get('type', ''))}</span>
                📧 {esc(cl.get('email', '—'))} · 📞 {esc(cl.get('phone', '—'))}<br>
                📁 {cc} case{'s' if cc != 1 else ''} · 💰 {esc(fmt_currency(bill))}
                {f" · 📝 {esc(cl.get('notes', '')[:80])}" if cl.get('notes') else ""}
            </div>""", unsafe_allow_html=True)

            bc1, bc2 = st.columns([1, 4])
            with bc1:
                if st.button("🗑️ Delete", key=f"del_cl_{cl['id']}", use_container_width=True):
                    delete_client(cl["id"])
                    st.success("✅ Deleted!")
                    st.rerun()

