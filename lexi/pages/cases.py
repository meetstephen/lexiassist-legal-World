"""LexiAssist cases page."""
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
# END OF PART 2 — Continue with Part 3 below this line
# ═══════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════
# PART 3: Cases, Calendar, Templates (CRUD), Clients,
#          Billing (+ Cost Tracker), Tools (editable),
#          Profile, and main() entry point
# ═══════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════
# PAGE: CASES (WITH SAVED ANALYSES)
# ═══════════════════════════════════════════════════════
def render_cases():
    st.markdown("""<div class="page-header">
        <h2>📁 Case Manager</h2>
        <p>Track cases, hearings, deadlines, suit numbers, and saved analyses</p>
    </div>""", unsafe_allow_html=True)

    tab_list, tab_add = st.tabs(["📋 All Cases", "➕ Add Case"])

    with tab_add:
        with st.form("add_case_form", clear_on_submit=True):
            st.markdown("#### ➕ New Case")
            ac1, ac2 = st.columns(2)
            with ac1:
                title = st.text_input("Case Title *", key="case_title_inp")
                suit_no = st.text_input("Suit Number", key="case_suit_inp")
                court = st.text_input("Court", key="case_court_inp")
            with ac2:
                status = st.selectbox("Status", CASE_STATUSES, key="case_status_inp")
                client_opts = ["— None —"] + [c.get("name", "?") for c in st.session_state.clients]
                client_sel = st.selectbox("Client", client_opts, key="case_client_inp")
                next_hearing = st.date_input("Next Hearing", value=None, key="case_hearing_inp")
            notes = st.text_area("Notes", height=80, key="case_notes_inp")

            if st.form_submit_button("➕ Add Case", type="primary"):
                if title.strip():
                    client_id = ""
                    if client_sel != "— None —":
                        cidx = client_opts.index(client_sel) - 1
                        if 0 <= cidx < len(st.session_state.clients):
                            client_id = st.session_state.clients[cidx]["id"]
                    add_case({
                        "title": title.strip(), "suit_no": suit_no.strip(),
                        "court": court.strip(), "status": status,
                        "client_id": client_id,
                        "next_hearing": str(next_hearing) if next_hearing else "",
                        "notes": notes.strip(),
                    })
                    st.success(f"✅ Case '{title}' added!")
                    st.rerun()
                else:
                    st.error("❌ Case title is required.")

    with tab_list:
        cases = st.session_state.cases
        if not cases:
            st.markdown(
                '<div style="text-align:center;padding:2.5rem 1rem;border:2px dashed '
                'var(--la-border);border-radius:12px;margin-top:1rem;">'
                '<div style="font-size:3rem;margin-bottom:0.6rem;">📁</div>'
                '<h3 style="margin:0 0 0.4rem 0;">No Cases Yet</h3>'
                '<p style="color:var(--la-text2);margin:0 0 1rem 0;max-width:360px;'
                'margin-left:auto;margin-right:auto;">Track your matters, hearings, deadlines '
                'and AI analyses all in one place.</p>'
                '<p style="font-size:0.82rem;color:var(--la-text2);">'
                '<strong>Example:</strong> <em>ABC Ltd v XYZ Ltd — Debt Recovery · '
                'Federal High Court Lagos · Suit No: FHC/L/CS/001/2026</em></p>'
                '<p style="font-size:0.82rem;color:var(--la-text2);">'
                '👆 Click the <strong>➕ Add Case</strong> tab above to get started.'
                '</p></div>',
                unsafe_allow_html=True,
            )
            return

        fc1, fc2 = st.columns([1, 2])
        with fc1:
            filt_status = st.selectbox("Filter by Status", ["All"] + CASE_STATUSES, key="case_filter_sel")
        with fc2:
            filt_search = st.text_input("🔍 Search cases", key="case_search_inp", placeholder="Title, suit number, court…")

        filtered = cases
        if filt_status != "All":
            filtered = [c for c in filtered if c.get("status") == filt_status]
        if filt_search.strip():
            s = filt_search.strip().lower()
            filtered = [c for c in filtered if s in c.get("title", "").lower() or s in c.get("suit_no", "").lower() or s in c.get("court", "").lower()]

        st.caption(f"Showing {len(filtered)} of {len(cases)} cases")

        for c in filtered:
            d = days_until(c.get("next_hearing", ""))
            badge = "badge-err" if d <= 3 else ("badge-warn" if d <= 7 else "badge-ok")
            hearing_txt = fmt_date(c.get("next_hearing", ""))
            cname = get_client_name(c.get("client_id", ""))

            st.markdown(f"""<div class="custom-card">
                <h4>{esc(c.get('title', 'Untitled'))}</h4>
                <span class="badge badge-info">{esc(c.get('status', ''))}</span>
                Suit: <strong>{esc(c.get('suit_no', '—'))}</strong> ·
                Court: {esc(c.get('court', '—'))} ·
                Client: {esc(cname)} ·
                Hearing: {esc(hearing_txt)}
                <span class="badge {badge}">{esc(relative_date(c.get('next_hearing', '')))}</span>
            </div>""", unsafe_allow_html=True)

            with st.expander(f"✏️ Manage: {c.get('title', '')[:50]}", expanded=False):
                manage_tab, analyses_tab = st.tabs(["⚙️ Details", "📎 Saved Analyses"])

                with manage_tab:
                    mc1, mc2 = st.columns(2)
                    with mc1:
                        new_status = st.selectbox(
                            "Status", CASE_STATUSES,
                            index=CASE_STATUSES.index(c["status"]) if c.get("status") in CASE_STATUSES else 0,
                            key=f"cs_{c['id']}",
                        )
                        new_hearing = st.date_input("Hearing", value=None, key=f"ch_{c['id']}")
                        new_notes = st.text_area("Notes", value=c.get("notes", ""), height=60, key=f"cn_{c['id']}")
                        if st.button("💾 Save Changes", key=f"save_{c['id']}", use_container_width=True):
                            upd = {"status": new_status, "notes": new_notes}
                            if new_hearing:
                                upd["next_hearing"] = str(new_hearing)
                            update_case(c["id"], upd)
                            st.success("✅ Updated!")
                            st.rerun()
                    with mc2:
                        st.markdown(f"**Created:** {esc(fmt_date(c.get('created_at', '')))}")
                        if c.get("updated_at"):
                            st.markdown(f"**Updated:** {esc(fmt_date(c['updated_at']))}")
                        if c.get("notes"):
                            st.caption(f"📝 {c['notes'][:300]}")
                        st.markdown("")
                        if st.button("🗑️ Delete Case", key=f"del_{c['id']}", type="secondary", use_container_width=True):
                            delete_case(c["id"])
                            st.success("✅ Deleted!")
                            st.rerun()

                with analyses_tab:
                    db = get_db()
                    saved = db.get_case_analyses(c["id"])
                    if saved:
                        st.caption(f"{len(saved)} saved analysis(es) for this case")
                        for sa in saved:
                            task_lbl = TASK_TYPES.get(sa.get("task", ""), {}).get("label", sa.get("task", ""))
                            mode_lbl = RESPONSE_MODES.get(sa.get("mode", ""), {}).get("label", sa.get("mode", ""))
                            st.markdown(f"""<div class="history-item">
                                <strong>{esc(sa.get('query', '')[:120])}</strong><br>
                                <small>{esc(fmt_date(sa.get('timestamp', '')))} · {esc(task_lbl)} · {esc(mode_lbl)}</small>
                            </div>""", unsafe_allow_html=True)

                            sa_view, sa_export, sa_del = st.columns([2, 2, 1])
                            with sa_view:
                                # Toggle view via session-state flag so a single
                                # click doesn't get wiped by the next rerun.
                                view_key = f"_view_sa_{sa['id']}"
                                view_open = st.session_state.get(view_key, False)
                                view_label = "👁️ Hide" if view_open else "👁️ View"
                                if st.button(view_label, key=f"view_sa_{sa['id']}", use_container_width=True):
                                    st.session_state[view_key] = not view_open
                                    st.rerun()
                            with sa_export:
                                sa_fname = f"Case_Analysis_{sa['id']}"
                                st.download_button(
                                    "📥 TXT", export_txt(sa["response"], f"Case Analysis — {c.get('title', '')}"),
                                    f"{sa_fname}.txt", "text/plain",
                                    key=f"sa_dl_{sa['id']}", use_container_width=True,
                                )
                            with sa_del:
                                if st.button("🗑️", key=f"del_sa_{sa['id']}", use_container_width=True, help="Delete this analysis"):
                                    db.delete_case_analysis(sa["id"])
                                    st.session_state.pop(f"_view_sa_{sa['id']}", None)
                                    st.success("Deleted!")
                                    st.rerun()
                            # Render the analysis body when the view flag is on,
                            # outside the button branch so it persists across reruns.
                            if st.session_state.get(f"_view_sa_{sa['id']}", False):
                                st.markdown(
                                    f'<div class="response-box">{esc(sa["response"])}</div>',
                                    unsafe_allow_html=True,
                                )
                    
                    # ── Phase 3: Case Bundle PDF Export ──────────────────────────────────
                        st.markdown("---")
                        bundle_key = f"_case_bundle_{c['id']}"
                        if st.button(
                            "📦 Export Full Case Bundle (PDF)",
                            key=f"bundle_{c['id']}",
                            use_container_width=True,
                            type="primary",
                            help="Generates a single PDF with case facts, all saved analyses, hearings, and billing entries",
                        ):
                            with st.spinner("📦 Building case bundle…"):
                                # Assemble bundle text
                                client_name = get_client_name(c.get("client_id",""))
                                firm = get_firm_name()
                                profile = st.session_state.get("profile", {})
                                lawyer = profile.get("lawyer_name", "")
                                bundle_lines = [
                                    f"{BRAND_LABEL.upper()} — CASE BUNDLE",
                                    f"{'='*60}",
                                    f"Case Title    : {c.get('title','')}",
                                    f"Suit Number   : {c.get('suit_no','—')}",
                                    f"Court         : {c.get('court','—')}",
                                    f"Status        : {c.get('status','—')}",
                                    f"Client        : {client_name}",
                                    f"Next Hearing  : {fmt_date(c.get('next_hearing',''))}",
                                    f"Handling Counsel: {lawyer}",
                                    f"Firm          : {firm}",
                                    f"Generated     : {datetime.now():%d %B %Y at %H:%M}",
                                    f"{'='*60}",
                                    "",
                                    "CASE NOTES",
                                    "-"*40,
                                    c.get("notes","None provided."),
                                    "",
                                ]
                                # All saved analyses
                                if saved:
                                    bundle_lines.append(f"SAVED ANALYSES ({len(saved)})")
                                    bundle_lines.append("-"*40)
                                    for idx2, sa in enumerate(saved, 1):
                                        task_lbl2 = TASK_TYPES.get(sa.get("task",""),{}).get("label","")
                                        mode_lbl2 = RESPONSE_MODES.get(sa.get("mode",""),{}).get("label","")
                                        bundle_lines.append(f"\n[{idx2}] {sa.get('timestamp','')[:10]} · {task_lbl2} · {mode_lbl2}")
                                        bundle_lines.append(f"Query: {sa.get('query','')}")
                                        bundle_lines.append("-"*30)
                                        bundle_lines.append(sa.get("response",""))
                                        bundle_lines.append("")

                                # Billing entries for this case's client
                                billing = [
                                    e for e in st.session_state.get("time_entries", [])
                                    if e.get("client_id") == c.get("client_id","")
                                ]
                                if billing:
                                    bundle_lines.append(f"\nBILLING SUMMARY ({len(billing)} entries)")
                                    bundle_lines.append("-"*40)
                                    total_bill = sum(e.get("amount",0) for e in billing)
                                    total_hr   = sum(e.get("hours",0) for e in billing)
                                    for e in billing:
                                        bundle_lines.append(
                                            f"  {e.get('date','')[:10]} · {e.get('description','')[:60]} · "
                                            f"{e.get('hours',0)}h · ₦{e.get('amount',0):,.0f}"
                                        )
                                    bundle_lines.append(f"\nTotal: {total_hr:.1f} hours · ₦{total_bill:,.2f}")

                                bundle_lines.append(f"\n{'='*60}")
                                bundle_lines.append("⚠️ AI-generated content. Not legal advice. Verify all citations independently.")
                                bundle_lines.append(f"{'='*60}")

                                bundle_text = "\n".join(bundle_lines)
                                # Persist so download buttons survive reruns.
                                st.session_state[bundle_key] = {
                                    "text": bundle_text,
                                    "n_saved": len(saved),
                                    "n_billing": len(billing),
                                    "title": c.get("title", ""),
                                }
                                st.rerun()

                        # Render persisted bundle download buttons (outside the
                        # build-button branch) so a download click doesn't blank
                        # the row.
                        bundle_data = st.session_state.get(bundle_key)
                        if bundle_data:
                            bundle_text = bundle_data["text"]
                            bundle_fname = (
                                f"LexiAssist_CaseBundle_"
                                f"{bundle_data['title'].replace(' ','_')[:30]}"
                                f"_{datetime.now():%Y%m%d}"
                            )
                            bnd1, bnd2, bnd3 = st.columns([2, 2, 1])
                            with bnd1:
                                st.download_button(
                                    "📥 Download TXT Bundle",
                                    bundle_text.encode("utf-8"),
                                    f"{bundle_fname}.txt", "text/plain",
                                    key=f"bndl_txt_{c['id']}",
                                    use_container_width=True,
                                )
                            with bnd2:
                                safe_pdf_download(
                                    bundle_text, f"Case Bundle — {bundle_data['title']}",
                                    bundle_fname, f"bndl_pdf_{c['id']}",
                                )
                            with bnd3:
                                if st.button(
                                    "🗑️", key=f"bndl_clear_{c['id']}",
                                    use_container_width=True, help="Clear bundle",
                                ):
                                    st.session_state.pop(bundle_key, None)
                                    st.rerun()
                            st.success(
                                f"✅ Bundle ready — "
                                f"{bundle_data['n_saved']} analysis(es) · "
                                f"{bundle_data['n_billing']} billing entry(ies)"
                            )
                    
                    else:
                        st.info("No analyses saved to this case yet. Use 'Save to Case' in the AI Assistant or Research tab.")

