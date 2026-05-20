"""LexiAssist admin user-management page."""
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
# PAGE: ADMIN — USER MANAGEMENT
# ═══════════════════════════════════════════════════════
def render_user_management():
    if st.session_state.get("current_user_role") != "admin":
        st.error("🚫 Admin access required.")
        return

    st.markdown("""<div class="page-header">
        <h2>🛡️ User Management</h2>
        <p>Create accounts, manage roles, reset passwords, and remove users</p>
    </div>""", unsafe_allow_html=True)

    db = get_db()
    um_list, um_create, um_stats, um_audit, um_law = st.tabs([
        "👥 All Users", "➕ Create User", "📊 Usage Stats", "🗂️ Audit Log", "📚 Law Updates"
    ])

    # ── All Users ──
    with um_list:
        users = db.list_users()
        current_uid = st.session_state.get("current_user_id", "")
        st.markdown(f"##### 👥 {len(users)} Registered User(s)")

        for user in users:
            uid = user["user_id"]
            is_self = (uid == current_uid)
            role_color = "#059669" if user["role"] == "admin" else "#3b82f6"
            role_label = "🛡️ Admin" if user["role"] == "admin" else "👤 User"

            with st.expander(
                f"{role_label} · @{user['username']} — {user.get('lawyer_name','') or user.get('firm_name','') or ''}",
                expanded=False,
            ):
                u1, u2, u3 = st.columns(3)
                with u1:
                    st.markdown(f"**Username:** @{esc(user['username'])}")
                    st.markdown(f"**Role:** {role_label}")
                    st.markdown(f"**Email:** {esc(user.get('email','') or '—')}")
                with u2:
                    st.markdown(f"**Full Name:** {esc(user.get('lawyer_name','') or '—')}")
                    st.markdown(f"**Firm:** {esc(user.get('firm_name','') or '—')}")
                with u3:
                    st.markdown(f"**Joined:** {esc(fmt_date(user.get('created_at','')))}")
                    st.markdown(f"**Last Login:** {esc(fmt_date(user.get('last_login','')))}")

                st.markdown("---")
                act1, act2, act3 = st.columns(3)

                # Change role
                with act1:
                    if not is_self:
                        new_role = "user" if user["role"] == "admin" else "admin"
                        role_btn_label = f"⬇️ Demote to User" if user["role"] == "admin" else "⬆️ Promote to Admin"
                        if st.button(role_btn_label, key=f"um_role_{uid}", use_container_width=True):
                            db.update_user(uid, {"role": new_role})
                            db.append_audit("ROLE_CHANGED", f"target={user['username']} old={user['role']} new={new_role}")
                            st.success(f"✅ @{user['username']} is now {new_role}.")
                            st.rerun()
                    else:
                        st.caption("(Your own account)")

                # Reset password
                with act2:
                    with st.popover(f"🔑 Reset Password"):
                        with st.form(f"reset_pw_{uid}"):
                            new_temp_pw = st.text_input("New Password", type="password", key=f"tmp_pw_{uid}")
                            if st.form_submit_button("✅ Set Password"):
                                if len(new_temp_pw) < 6:
                                    st.error("Min 6 characters.")
                                else:
                                    db.update_user(uid, {"password_hash": hash_password(new_temp_pw)})
                                    db.append_audit("PASSWORD_RESET", f"target_user={user['username']}")
                                    st.success(f"✅ Password reset for @{user['username']}.")

                # Delete user
                with act3:
                    if not is_self:
                        with st.popover(f"🗑️ Delete User"):
                            st.warning(f"Delete @{user['username']}? ALL their data will be permanently erased.")
                            if st.button(f"⚠️ Confirm Delete @{user['username']}",
                                         key=f"um_del_confirm_{uid}", type="primary"):
                                db.append_audit("USER_DELETED", f"deleted_user={user['username']}")
                                db.delete_user(uid)
                                st.success(f"✅ @{user['username']} deleted.")
                                st.rerun()
                    else:
                        st.caption("Cannot delete yourself.")

    # ── Create User ──
    with um_create:
        st.markdown("##### ➕ Create a New User Account")
        st.caption("Create accounts for colleagues at your firm. They can log in immediately.")
        render_register_form("admin_new_user", admin_mode=True)

    # ── Usage Stats ──
    with um_stats:
        st.markdown("##### 📊 Platform Usage by User")
        users = db.list_users()
        if not users:
            st.info("No users yet.")
        else:
            for user in users:
                uid = user["user_id"]
                cur = db._execute(
                    "SELECT COUNT(*), COALESCE(SUM(estimated_cost),0) FROM cost_logs WHERE user_id = %s",
                    (uid,)
                )
                row = cur.fetchone()
                calls, cost = (row[0], row[1]) if row else (0, 0)
                cur2 = db._execute(
                    "SELECT COUNT(*) FROM kv_store WHERE key LIKE %s", (f"u:{uid}:cases",)
                )
                # Get case count from namespaced kv
                st.markdown(f"""
<div class="custom-card">
  <div style="display:flex;justify-content:space-between;">
    <strong>@{esc(user['username'])}</strong>
    <span class="badge {'badge-ok' if user['role'] == 'admin' else 'badge-info'}">
      {'Admin' if user['role'] == 'admin' else 'User'}
    </span>
  </div>
  <small>🤖 {calls} AI calls · 💰 ${cost:.4f} estimated cost · 
  🕐 Last login: {esc(fmt_date(user.get('last_login','')))}
  </small>
</div>""", unsafe_allow_html=True)

    with um_audit:
        st.markdown("#### 🗂️ Immutable Audit Log")
        st.caption(
            "Every significant action in LexiAssist is recorded here in an append-only, "
            "hash-chained log. Entries cannot be modified or deleted. "
            "Each entry's hash covers its content AND the previous entry's hash, "
            "making retroactive tampering detectable."
        )
        vc1, vc2 = st.columns([1, 3])
        with vc1:
            if st.button("🔐 Verify Audit Chain", key="verify_audit_chain_btn", use_container_width=True):
                chain_result = db.verify_audit_chain()
                if chain_result["ok"]:
                    st.success(f"✅ {chain_result['message']} Checked {chain_result['checked']} entries.")
                else:
                    st.error(
                        f"🚨 Audit chain problem: {chain_result['message']} "
                        f"Broken at: {chain_result.get('broken_at', '—')}"
                    )
        with vc2:
            st.caption("Use this to detect tampering or accidental modification of audit records.")
        is_super_admin = st.session_state.get("current_username", "") in ("admin", "superadmin")
        if is_super_admin:
            audit_rows = db.get_all_audit_log_admin(limit=500)
            st.caption(f"Showing all users · {len(audit_rows)} entries")
        else:
            audit_rows = db.get_audit_log(limit=150)
            st.caption(f"Your entries · {len(audit_rows)} shown")

        if not audit_rows:
            st.info("No audit entries yet. Actions will appear here as you use the app.")
        else:
            action_types = sorted(set(r["action"] for r in audit_rows))
            filt = st.multiselect(
                "Filter by action", action_types, default=action_types, key="audit_filt"
            )
            filtered = [r for r in audit_rows if r["action"] in filt]
            st.caption(f"{len(filtered)} entries after filter")

            for r in filtered:
                action_color = {
                    "AI_QUERY":        "#6366f1",
                    "CASE_ADDED":      "#059669",
                    "CASE_DELETED":    "#dc2626",
                    "CLIENT_ADDED":    "#0891b2",
                    "CLIENT_DELETED":  "#dc2626",
                    "LOGIN":           "#d97706",
                    "LOGIN_FAILED":    "#ef4444",
                    "LOGOUT":          "#64748b",
                    "PASSWORD_RESET":  "#7c3aed",
                    "USER_DELETED":    "#dc2626",
                    "USER_CREATED":    "#059669",
                    "ROLE_CHANGED":    "#7c3aed",
                    "ANALYSIS_SAVED":  "#0891b2",
                    "TASK_CREATED":    "#059669",
                    "TASK_UPDATED":    "#0891b2",
                    "TASK_DELETED":    "#dc2626",
                }.get(r["action"], "#64748b")
                uid_txt = f" · @{esc(r.get('user_id',''))}" if is_super_admin else ""
                st.markdown(
                    f'<div class="history-item" style="border-left:3px solid {action_color};">'
                    f'<strong style="color:{action_color};">{esc(r["action"])}</strong>'
                    f'{uid_txt} · '
                    f'<small style="color:var(--la-text-secondary);">'
                    f'{esc(r["timestamp"][:19])}</small><br>'
                    f'<small>{esc(r.get("detail","")[:200])}</small><br>'
                    f'<code style="font-size:0.65rem;color:var(--la-text2);">'
                    f'hash: {esc(r["entry_hash"][:16])}…</code>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            if st.button("📥 Export Audit Log CSV", key="audit_export_btn"):
                import csv, io
                buf = io.StringIO()
                writer = csv.DictWriter(
                    buf,
                    fieldnames=["id", "timestamp", "action", "detail", "entry_hash"],
                )
                writer.writeheader()
                writer.writerows(filtered)
                st.download_button(
                    "⬇️ Download CSV", buf.getvalue().encode(),
                    "lexiassist_audit.csv", "text/csv", key="audit_dl_btn",
                )

    with um_law:
        st.markdown("#### 📚 Legal Currency Dashboard")
        st.caption(
            "Track repealed laws, recent amendments, and new cases. "
            "Entries here are injected as a CURRENCY NOTE into every AI prompt automatically."
        )

        # ── Current legal data version display ──
        ldv = LEGAL_DATA_VERSION
        st.markdown(
            f'<div style="background:var(--la-bg2);border:1px solid var(--la-border);'
            f'border-left:4px solid #059669;border-radius:8px;'
            f'padding:0.8rem 1rem;margin-bottom:1rem;color:var(--la-text);">'
            f'<strong style="color:var(--la-text);">📋 Current Version: '
            f'{esc(ldv["version"])}</strong>'
            f'<span style="color:var(--la-text2);"> · Updated: {esc(ldv["updated"])}'
            f' · {esc(ldv["last_act"])}</span><br>'
            f'<small style="color:var(--la-text2);">{esc(ldv["notes"])}</small>'
            f'</div>',
            unsafe_allow_html=True,
        )
        

        law_tab1, law_tab2, law_tab3 = st.tabs([
            "⚠️ Repealed Laws", "📝 Recent Amendments", "⚖️ New Cases"
        ])

        # ── Store updates in DB via kv_store ──
        def _load_law_updates(key: str) -> list:
            try:
                return get_db()._load_list_raw(f"law_updates_{key}") or []
            except Exception:
                return []

        def _save_law_updates(key: str, data: list):
            try:
                get_db()._save_list_raw(f"law_updates_{key}", data)
            except Exception:
                pass

        with law_tab1:
            st.markdown("##### ⚠️ Repealed / Superseded Laws")
            st.caption("Add laws that have been repealed so the AI knows to stop citing them.")
            repealed = _load_law_updates("repealed")
            if repealed:
                for i, r in enumerate(repealed):
                    col_a, col_b = st.columns([5, 1])
                    with col_a:
                        st.markdown(
                            f'<div class="history-item">'
                            f'<strong style="color:#dc2626;">🚫 {esc(r.get("old",""))}</strong>'
                            f' → replaced by <strong style="color:#059669;">'
                            f'{esc(r.get("new",""))}</strong><br>'
                            f'<small>{esc(r.get("note",""))} · Added: {esc(r.get("date",""))}</small>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    with col_b:
                        if st.button("🗑️", key=f"del_rep_{i}", help="Remove"):
                            repealed.pop(i)
                            _save_law_updates("repealed", repealed)
                            st.rerun()

            with st.form("add_repealed_form"):
                st.markdown("**Add repealed law:**")
                rc1, rc2 = st.columns(2)
                with rc1:
                    old_act = st.text_input("Repealed Act", placeholder="e.g. Arbitration Act 1988")
                with rc2:
                    new_act = st.text_input("Replaced by", placeholder="e.g. Arbitration and Conciliation Act 2023")
                rep_note = st.text_input("Note", placeholder="e.g. Fully repealed — cite 2023 Act only")
                if st.form_submit_button("➕ Add", type="primary"):
                    if old_act.strip():
                        repealed.append({
                            "old": old_act.strip(),
                            "new": new_act.strip(),
                            "note": rep_note.strip(),
                            "date": date.today().isoformat(),
                        })
                        _save_law_updates("repealed", repealed)
                        st.success("✅ Added.")
                        st.rerun()

        with law_tab2:
            st.markdown("##### 📝 Recent Amendments & Finance Acts")
            st.caption("Track amendments that change specific provisions the AI might cite incorrectly.")
            amendments = _load_law_updates("amendments")
            if amendments:
                for i, a in enumerate(amendments):
                    ca1, ca2 = st.columns([5, 1])
                    with ca1:
                        st.markdown(
                            f'<div class="history-item">'
                            f'<strong>{esc(a.get("act",""))}</strong> — '
                            f'{esc(a.get("provision",""))}<br>'
                            f'<small style="color:#d97706;">{esc(a.get("change",""))}'
                            f' · {esc(a.get("date",""))}</small>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    with ca2:
                        if st.button("🗑️", key=f"del_amd_{i}", help="Remove"):
                            amendments.pop(i)
                            _save_law_updates("amendments", amendments)
                            st.rerun()

            with st.form("add_amendment_form"):
                st.markdown("**Add amendment:**")
                am1, am2 = st.columns(2)
                with am1:
                    amd_act = st.text_input("Act / Statute", placeholder="e.g. Stamp Duties Act")
                with am2:
                    amd_prov = st.text_input("Provision", placeholder="e.g. Section 89A")
                amd_change = st.text_area(
                    "What changed", height=80,
                    placeholder="e.g. Finance Act 2020 introduced 0.5% levy on electronic transfers above ₦10,000"
                )
                if st.form_submit_button("➕ Add", type="primary"):
                    if amd_act.strip() and amd_change.strip():
                        amendments.append({
                            "act": amd_act.strip(),
                            "provision": amd_prov.strip(),
                            "change": amd_change.strip(),
                            "date": date.today().isoformat(),
                        })
                        _save_law_updates("amendments", amendments)
                        st.success("✅ Added.")
                        st.rerun()

        with law_tab3:
            st.markdown("##### ⚖️ New Verified Cases")
            st.caption(
                "Add new Supreme Court / Court of Appeal decisions to the verified case database. "
                "They will be recognised immediately by the citation audit."
            )
            new_cases = _load_law_updates("new_cases")
            if new_cases:
                for i, nc in enumerate(new_cases):
                    nc1, nc2 = st.columns([5, 1])
                    with nc1:
                        st.markdown(
                            f'<div class="history-item">'
                            f'<strong>{esc(nc.get("name",""))}</strong> '
                            f'<code style="background:#f0fdf4;padding:0.1rem 0.4rem;'
                            f'border-radius:3px;">{esc(nc.get("citation",""))}</code><br>'
                            f'<small>{esc(nc.get("principle",""))} · '
                            f'{esc(nc.get("court",""))} {esc(nc.get("year",""))}</small>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    with nc2:
                        if st.button("🗑️", key=f"del_nc_{i}", help="Remove"):
                            new_cases.pop(i)
                            _save_law_updates("new_cases", new_cases)
                            st.rerun()

                # Auto-inject into VERIFIED_NIGERIAN_CASES at runtime
                for nc in new_cases:
                    if nc.get("name") and nc.get("name") not in VERIFIED_NIGERIAN_CASES:
                        VERIFIED_NIGERIAN_CASES[nc["name"]] = {
                            "citation": nc.get("citation", ""),
                            "court": nc.get("court", "Supreme Court"),
                            "year": int(nc.get("year", date.today().year)),
                            "principle": nc.get("principle", ""),
                        }

            with st.form("add_case_form"):
                st.markdown("**Add new verified case:**")
                ncc1, ncc2 = st.columns(2)
                with ncc1:
                    nc_name = st.text_input(
                        "Case Name", placeholder="e.g. Dangote v FRN"
                    )
                    nc_citation = st.text_input(
                        "Citation", placeholder="e.g. (2024) 5 NWLR (Pt. 1900) 1"
                    )
                with ncc2:
                    nc_court = st.selectbox(
                        "Court",
                        ["Supreme Court", "Court of Appeal", "Federal High Court",
                         "National Industrial Court", "Other"],
                        key="nc_court_sel",
                    )
                    nc_year = st.text_input(
                        "Year", placeholder=str(date.today().year)
                    )
                nc_principle = st.text_area(
                    "Legal Principle / Ratio",
                    height=80,
                    placeholder="e.g. Corporate veil lifted where company used as instrument of fraud",
                )
                if st.form_submit_button("➕ Add to Verified Database", type="primary"):
                    if nc_name.strip() and nc_citation.strip():
                        new_cases.append({
                            "name": nc_name.strip(),
                            "citation": nc_citation.strip(),
                            "court": nc_court,
                            "year": nc_year.strip() or str(date.today().year),
                            "principle": nc_principle.strip(),
                        })
                        _save_law_updates("new_cases", new_cases)
                        # Immediately inject into live runtime dict
                        VERIFIED_NIGERIAN_CASES[nc_name.strip()] = {
                            "citation": nc_citation.strip(),
                            "court": nc_court,
                            "year": int(nc_year.strip()) if nc_year.strip().isdigit() else date.today().year,
                            "principle": nc_principle.strip(),
                        }
                        st.success(
                            f"✅ '{nc_name.strip()}' added to verified case database. "
                            "Citation audit will now recognise it immediately."
                        )
                        st.rerun()
