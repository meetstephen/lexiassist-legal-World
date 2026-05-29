"""LexiAssist profile page."""
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
# PAGE: PROFILE
# ═══════════════════════════════════════════════════════
def render_profile():
    st.markdown("""<div class="page-header">
        <h2>👤 User Profile</h2>
        <p>Firm branding, contact details, and security settings</p>
    </div>""", unsafe_allow_html=True)

    profile = st.session_state.profile

    _is_admin = st.session_state.get("current_user_role") == "admin"
    _tab_labels = ["🏢 Firm Details", "🔐 Security", "🔔 Notifications", "💾 Data Management"]
    if _is_admin:
        _tab_labels.append("⚙️ Firm Admin Settings")
    _tabs = st.tabs(_tab_labels)
    tab_info, tab_security, tab_notif, tab_data = _tabs[:4]
    tab_firm_admin = _tabs[4] if _is_admin else None

    # ── Firm Details ──
    with tab_info:
        st.markdown("#### 🏢 Firm / Lawyer Profile")
        st.caption("This information appears on exported documents (PDF, DOCX, HTML, TXT).")

        with st.form("profile_form"):
            p1, p2 = st.columns(2)
            with p1:
                firm_name = st.text_input("Firm Name", value=profile.get("firm_name", ""), key="prof_firm_inp",
                                          placeholder="e.g. Adekunle & Associates")
                lawyer_name = st.text_input("Lawyer Name", value=profile.get("lawyer_name", ""), key="prof_lawyer_inp",
                                            placeholder="e.g. Barr. Chidi Adekunle")
                email = st.text_input("Email", value=profile.get("email", ""), key="prof_email_inp")
                nba_branch = st.text_input("NBA Branch", value=profile.get("nba_branch", ""), key="prof_nba_branch",
                                           placeholder="e.g. Lagos, Abuja, Port Harcourt")
            with p2:
                phone = st.text_input("Phone", value=profile.get("phone", ""), key="prof_phone_inp")
                address = st.text_area("Address", value=profile.get("address", ""), height=82, key="prof_addr_inp")
                nba_enroll = st.text_input("NBA Enrollment No. (SCN Call No.)", value=profile.get("nba_enroll", ""),
                                           key="prof_nba_enroll", placeholder="e.g. 2009/SCN/12345",
                                           help="Your Supreme Court of Nigeria enrollment number as it appears on your call certificate")
                call_year = st.text_input("Year Called to Bar", value=profile.get("call_year", ""),
                                          key="prof_call_year", placeholder="e.g. 2009")

            if st.form_submit_button("💾 Save Profile", type="primary"):
                st.session_state.profile["firm_name"] = firm_name.strip()
                st.session_state.profile["lawyer_name"] = lawyer_name.strip()
                st.session_state.profile["email"] = email.strip()
                st.session_state.profile["phone"] = phone.strip()
                st.session_state.profile["address"] = address.strip()
                st.session_state.profile["nba_enroll"] = nba_enroll.strip()
                st.session_state.profile["call_year"] = call_year.strip()
                st.session_state.profile["nba_branch"] = nba_branch.strip()
                persist_profile()
                st.success("✅ Profile saved! Firm name will appear on all exports.")
                st.rerun()

        # Preview
        if profile.get("firm_name"):
            st.markdown("---")
            st.markdown("#### 📄 Export Header Preview")
            nba_line = ""
            if profile.get("nba_enroll") or profile.get("call_year"):
                nba_line = f"NBA Enroll. No: {esc(profile.get('nba_enroll',''))} · Called: {esc(profile.get('call_year',''))}<br>"
            branch_line = f"NBA Branch: {esc(profile.get('nba_branch',''))}<br>" if profile.get("nba_branch") else ""
            st.markdown(
                f'<div class="custom-card" style="color:var(--la-text);">'
                f'<h4 style="color:var(--la-text);margin:0 0 0.4rem 0;">'
                f'{esc(profile.get("firm_name", ""))}</h4>'
                f'<p style="color:var(--la-text);margin:0 0 0.2rem 0;">'
                f'{esc(profile.get("lawyer_name", ""))}</p>'
                + (f'<p style="color:var(--la-text2);margin:0 0 0.2rem 0;font-size:0.84rem;">'
                   f'{nba_line}{branch_line}</p>' if (nba_line or branch_line) else '')
                + f'<p style="color:var(--la-text2);margin:0 0 0.2rem 0;font-size:0.84rem;">'
                f'📧 {esc(profile.get("email", ""))} · 📞 {esc(profile.get("phone", ""))}</p>'
                f'<p style="color:var(--la-text2);margin:0;font-size:0.84rem;">'
                f'📍 {esc(profile.get("address", ""))}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Notifications ──
    with tab_notif:
        st.markdown("#### 🔔 Hearing Reminder Emails")
        st.caption("Receive automatic email alerts 7 days and 1 day before each hearing.")
        st.info("💡 Requires a Gmail account with an App Password. Get one at: Google Account → Security → 2-Step Verification → App Passwords")
        with st.form("notif_form"):
            notif_email = st.text_input(
                "Your Email Address (recipient)",
                value=st.session_state.profile.get("notif_email", ""),
                placeholder="yourname@gmail.com",
                key="notif_email_inp",
            )
            notif_smtp_user = st.text_input(
                "Gmail Address (sender)",
                value=st.session_state.profile.get("notif_smtp_user", ""),
                placeholder="sender@gmail.com",
                key="notif_smtp_inp",
            )
            notif_smtp_pass = st.text_input(
                "Gmail App Password",
                type="password",
                key="notif_smtp_pass_inp",
                help="16-character app password from Google Account → Security → App Passwords",
            )
            if st.form_submit_button("💾 Save Notification Settings", type="primary"):
                st.session_state.profile["notif_email"] = notif_email.strip()
                st.session_state.profile["notif_smtp_user"] = notif_smtp_user.strip()
                # Encrypt password before storing — decrypt_secret() will unwrap it at send-time.
                # If the user left the field blank (masked), keep the existing stored value.
                raw_pass = notif_smtp_pass.strip()
                if raw_pass:
                    st.session_state.profile["notif_smtp_pass"] = encrypt_secret(raw_pass)
                # (else: field was blank/masked — don't overwrite the stored encrypted value)
                persist_profile()
                st.success("✅ Notification settings saved!" +
                           (" 🔒 Password encrypted." if raw_pass and HAS_CRYPTO else
                            " ⚠️ Install `cryptography` to encrypt stored passwords." if raw_pass else ""))
        st.markdown("---")
        st.markdown("##### 📬 Send Reminders Now")
        hearings = get_hearings()
        upcoming = [h for h in hearings if 0 <= days_until(h["date"]) <= 7]
        has_email_config = (
            st.session_state.profile.get("notif_email") and
            st.session_state.profile.get("notif_smtp_user") and
            st.session_state.profile.get("notif_smtp_pass")
        )
        if upcoming and has_email_config:
            st.markdown(f"**{len(upcoming)} hearing(s)** within the next 7 days:")
            for h in upcoming:
                d = days_until(h["date"])
                badge = "badge-err" if d <= 1 else ("badge-warn" if d <= 3 else "badge-ok")
                st.markdown(f"""<div class="history-item">
                    <strong>{esc(h['title'])}</strong> ·
                    {esc(h['court'])} ·
                    📅 {esc(fmt_date(h['date']))}
                    <span class="badge {badge}">{esc(relative_date(h['date']))}</span>
                </div>""", unsafe_allow_html=True)
            if st.button(
                "📬 Send Reminder Emails for All Upcoming Hearings",
                key="send_reminders_btn",
                type="primary", use_container_width=True,
            ):
                sent, failed = 0, 0
                firm = get_firm_name()
                for h in upcoming:
                    try:
                        msg = MIMEMultipart("alternative")
                        msg["Subject"] = f"⚖️ Hearing Reminder: {h['title']} — {fmt_date(h['date'])}"
                        msg["From"] = st.session_state.profile["notif_smtp_user"]
                        msg["To"] = st.session_state.profile["notif_email"]
                        body = f"""
<html>
<body style="font-family:Georgia,serif;max-width:600px;margin:auto;padding:20px;color:#1a2e4a;background:#ffffff;">
  <h2 style="color:#059669;border-bottom:2px solid #059669;padding-bottom:10px;">
    ⚖️ LexiAssist Hearing Reminder
  </h2>
  <div style="background:#f0fdf4;border-left:4px solid #059669;
  padding:15px;border-radius:8px;margin:20px 0;color:#1a2e4a;">
    <h3 style="margin:0 0 10px 0;color:#0f3d2e;">{esc(h['title'])}</h3>
    <p style="margin:5px 0;"><strong>Suit Number:</strong> {esc(h['suit'])}</p>
    <p style="margin:5px 0;"><strong>Court:</strong> {esc(h['court'])}</p>
    <p style="margin:5px 0;"><strong>Hearing Date:</strong> {esc(fmt_date(h['date']))}</p>
    <p style="margin:5px 0;"><strong>Days Remaining:</strong>
      <span style="color:#dc2626;font-weight:bold;">{days_until(h['date'])} day(s)</span>
    </p>
  </div>
  <p style="background:#f4f6f9;padding:10px;border-radius:6px;color:#1a2e4a;">
    ⚠️ Please ensure all court processes, briefs, and appearances
    are prepared well in advance.
  </p>
  <p style="color:#64748b;font-size:12px;margin-top:30px;
  border-top:1px solid #e5e7eb;padding-top:10px;">
    Sent by <strong>{esc(firm)}</strong> via LexiAssist v{__version__} ·
    {datetime.now().strftime('%d %B %Y at %H:%M')}
  </p>
</body>
</html>"""
                        msg.attach(MIMEText(body, "html"))
                        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                            server.login(
                                st.session_state.profile["notif_smtp_user"],
                                decrypt_secret(st.session_state.profile["notif_smtp_pass"]),
                            )
                            server.sendmail(
                                st.session_state.profile["notif_smtp_user"],
                                st.session_state.profile["notif_email"],
                                msg.as_string(),
                            )
                        sent += 1
                    except Exception as e:
                        failed += 1
                        logger.warning(f"Email send failed: {e}")
                if sent:
                    st.success(f"✅ {sent} reminder email(s) sent to {st.session_state.profile['notif_email']}")
                if failed:
                    st.error(f"❌ {failed} email(s) failed. Check your Gmail App Password and make sure 2-Step Verification is enabled.")
        elif not has_email_config:
            st.info("⚙️ Configure your email settings in the form above to enable reminders.")
        else:
            st.info("✅ No hearings within the next 7 days. You are clear.")
    # ── Security / Account ──
    with tab_security:
        st.markdown("#### 🔐 Account Security")
        st.caption(f"Logged in as: **@{esc(st.session_state.get('current_username',''))}** · "
                   f"Role: **{esc(st.session_state.get('current_user_role','').title())}**")

        st.markdown("##### 🔑 Change Password")
        with st.form("change_pw_form"):
            current_pw = st.text_input("Current Password", type="password", key="cur_pw_inp")
            new_pw = st.text_input("New Password", type="password", key="new_pw_inp")
            confirm_pw = st.text_input("Confirm New Password", type="password", key="confirm_pw_inp")
            if st.form_submit_button("🔐 Update Password", type="primary"):
                if not verify_password(current_pw, profile.get("password_hash", "")):
                    st.error("❌ Current password is incorrect.")
                elif not new_pw:
                    st.error("❌ New password cannot be empty.")
                elif len(new_pw) < 6:
                    st.error("❌ Password must be at least 6 characters.")
                elif new_pw != confirm_pw:
                    st.error("❌ New passwords do not match.")
                else:
                    st.session_state.profile["password_hash"] = hash_password(new_pw)
                    persist_profile()
                    st.success("✅ Password updated successfully!")
                    st.rerun()

        st.markdown("---")
        st.markdown("##### 📋 Account Information")
        uid = st.session_state.get("current_user_id", "")
        if uid:
            user_rec = get_db().get_user_by_id(uid)
            if user_rec:
                ai1, ai2 = st.columns(2)
                with ai1:
                    st.metric("Username", f"@{user_rec.get('username','')}")
                    st.metric("Role", user_rec.get("role", "").title())
                with ai2:
                    st.metric("Joined", fmt_date(user_rec.get("created_at", "")))
                    st.metric("Last Login", fmt_date(user_rec.get("last_login", "")))

        st.markdown("---")
        with st.expander("📱 Active Sessions", expanded=False):
            st.caption("These are all devices and browsers where you are currently signed in.")
            current_token = st.session_state.get("_session_token", "")
            if uid:
                sessions = get_db().get_user_sessions(uid)
                if not sessions:
                    st.info("No active sessions found.")
                else:
                    for i, sess in enumerate(sessions):
                        is_current = (sess["token"] == current_token)
                        border_col = "#059669" if is_current else "var(--la-border)"
                        badge = (
                            '<span style="background:#059669;color:#ffffff;font-size:0.72rem;'
                            'padding:0.15rem 0.5rem;border-radius:1rem;font-weight:600;'
                            'margin-left:0.4rem;">This device</span>'
                            if is_current else ""
                        )
                        st.markdown(
                            f'<div style="background:var(--la-card);'
                            f'border:1px solid {border_col};'
                            f'border-left:4px solid {border_col};'
                            f'border-radius:0.6rem;padding:0.8rem 1rem;margin-bottom:0.5rem;">'
                            f'<div style="color:var(--la-text);">'
                            f'🖥️ <strong style="color:var(--la-text);">Session {i+1}</strong>{badge}</div>'
                            f'<div style="color:var(--la-text2);font-size:0.8rem;margin-top:0.25rem;">'
                            f'Created: {esc(fmt_date(sess.get("created_at","")))} · '
                            f'Last used: {esc(fmt_date(sess.get("last_used","")))} · '
                            f'Expires: {esc(fmt_date(sess.get("expires_at","")))}'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )
                        if not is_current:
                            if st.button(f"🚫 Revoke Session {i+1}", key=f"revoke_sess_{i}", use_container_width=True):
                                get_db().revoke_session_token(sess["token"])
                                st.success("✅ Session revoked.")
                                st.rerun()

                st.markdown("")
                if st.button("🚫 Sign Out All Other Devices", key="revoke_all_others", use_container_width=True):
                    db2 = get_db()
                    all_sess = db2.get_user_sessions(uid)
                    for sess in all_sess:
                        if sess["token"] != current_token:
                            db2.revoke_session_token(sess["token"])
                    st.success("✅ All other sessions revoked.")
                    st.rerun()

        st.markdown("---")
        st.markdown("##### 🚪 Sign Out")
        st.caption("Signs you out of this device. Your data is saved.")
        if st.button("🚪 Sign Out Now", key="profile_logout_btn", use_container_width=True, type="primary"):
            do_logout()

    # ── Data Management ──
    with tab_data:
        st.markdown("#### 💾 Full Backup & Restore")

        # Backup
        st.markdown("##### 📥 Export Full Backup")
        st.caption("Downloads all cases, clients, billing, chat history, templates, references, profile, and cost logs as a single JSON file.")
        if st.button("📦 Generate Full Backup", key="profile_backup_btn", use_container_width=True, type="primary"):
            export_data = {
                "export_date": datetime.now().isoformat(),
                "version": "8.0",
                "cases": st.session_state.cases,
                "clients": st.session_state.clients,
                "time_entries": st.session_state.time_entries,
                "invoices": st.session_state.invoices,
                "chat_history": st.session_state.chat_history,
                "custom_templates": st.session_state.custom_templates,
                "custom_limitation_periods": st.session_state.custom_limitation_periods,
                "custom_maxims": st.session_state.custom_maxims,
                "profile": {k: v for k, v in st.session_state.profile.items() if k != "password_hash"},
                "cost_logs": get_db().get_cost_logs(500),
            }
            # Track backup date for admin dashboard reminder
            st.session_state.profile["last_backup_date"] = date.today().isoformat()
            persist_profile()
            try:
                get_db().append_audit(
                    "DATA_EXPORTED",
                    f"backup by={st.session_state.get('current_username','')} "
                    f"items={len(export_data.get('cases',[]))} cases, "
                    f"{len(export_data.get('clients',[]))} clients"
                )
            except Exception:
                pass
            st.download_button(
                "⬇️ Download Full Backup",
                json.dumps(export_data, indent=2, default=str),
                f"lexiassist_full_backup_{datetime.now():%Y%m%d_%H%M}.json",
                "application/json", key="profile_dl_backup", use_container_width=True,
            )


        st.markdown("---")

        # Restore
        st.markdown("##### 📤 Restore from Backup")
        st.caption("Upload a previously exported JSON backup to restore all data.")
        restore_file = st.file_uploader("Upload backup JSON", type=["json"], key="profile_restore_upload")
        if restore_file:
            try:
                raw = json.loads(restore_file.getvalue().decode("utf-8", errors="ignore"))
                if isinstance(raw, dict):
                    st.markdown(f"""<div class="custom-card">
                        <h4>📦 Backup Details</h4>
                        Version: {esc(str(raw.get('version', '?')))} ·
                        Date: {esc(fmt_date(raw.get('export_date', '')))} ·
                        Cases: {len(raw.get('cases', []))} ·
                        Clients: {len(raw.get('clients', []))} ·
                        History: {len(raw.get('chat_history', []))}
                    </div>""", unsafe_allow_html=True)

                    if st.button("⚠️ Restore This Backup (Overwrites Current Data)", type="primary",
                                 key="confirm_restore_btn", use_container_width=True):
                        for k in ["cases", "clients", "time_entries", "invoices", "chat_history",
                                   "custom_templates", "custom_limitation_periods", "custom_maxims"]:
                            if k in raw:
                                st.session_state[k] = raw[k]
                                persist(k)
                        if "profile" in raw and isinstance(raw["profile"], dict):
                            for pk, pv in raw["profile"].items():
                                if pk != "password_hash":
                                    st.session_state.profile[pk] = pv
                            persist_profile()
                        st.success("✅ Backup restored successfully!")
                        st.rerun()
                else:
                    st.error("❌ Invalid backup file format.")
            except Exception as e:
                st.error(f"❌ Error reading backup: {e}")

        st.markdown("---")

        # Data stats
        st.markdown("##### 📊 Current Data Summary")
        ds1, ds2, ds3, ds4 = st.columns(4)
        with ds1:
            st.metric("Cases", len(st.session_state.cases))
            st.metric("Clients", len(st.session_state.clients))
        with ds2:
            st.metric("Time Entries", len(st.session_state.time_entries))
            st.metric("Invoices", len(st.session_state.invoices))
        with ds3:
            st.metric("AI Sessions", len(st.session_state.chat_history))
            st.metric("Custom Templates", len(st.session_state.custom_templates))
        with ds4:
            cost_s = get_db().get_cost_summary()
            st.metric("API Calls Logged", cost_s["total_calls"])
            st.metric("Custom Maxims", len(st.session_state.custom_maxims))

        st.markdown("---")

        # Danger zone
        st.markdown("##### ⚠️ Danger Zone")
        st.caption("These actions cannot be undone. Export a backup first!")
        dz1, dz2 = st.columns(2)
        with dz1:
            if st.button("🗑️ Clear All Chat History", key="clear_all_history", use_container_width=True):
                st.session_state.chat_history = []
                persist("chat_history")
                st.success("✅ Chat history cleared.")
                st.rerun()
        with dz2:
            if st.button("🗑️ Reset All Data", key="reset_all_data", type="secondary", use_container_width=True):
                for k in ["cases", "clients", "time_entries", "invoices", "chat_history",
                           "custom_templates", "custom_limitation_periods", "custom_maxims"]:
                    st.session_state[k] = []
                    persist(k)
                st.session_state.last_response = ""
                st.session_state.original_query = ""
                st.session_state.research_results = ""
                st.success("✅ All data reset. Profile and password preserved.")
                st.rerun()

    # ── Firm Admin Settings — CORRECT SCOPE (inside render_profile) ───────
    if _is_admin and tab_firm_admin is not None:
        with tab_firm_admin:
            st.markdown("#### ⚙️ Firm-Wide Admin Settings")
            st.caption(
                "These settings apply across the whole firm deployment. "
                "Visible to admins only."
            )
            firm_cfg = st.session_state.profile.get("firm_config", {})
            fa1, fa2 = st.columns(2)

            with fa1:
                st.markdown("##### 💰 Default Billing Rates")
                default_hourly = st.number_input(
                    "Default Hourly Rate (₦)",
                    min_value=0, max_value=5_000_000,
                    value=int(firm_cfg.get("default_hourly_rate", 50000)),
                    step=5000, key="fa_hourly_rate",
                    help="Used as the default when creating new time entries",
                )
                default_currency = st.selectbox(
                    "Billing Currency",
                    ["NGN (₦)", "USD ($)", "GBP (£)", "EUR (€)"],
                    index=["NGN (₦)", "USD ($)", "GBP (£)", "EUR (€)"].index(
                        firm_cfg.get("billing_currency", "NGN (₦)")
                    ),
                    key="fa_currency",
                )
                vat_rate = st.number_input(
                    "VAT Rate (%)", min_value=0.0, max_value=30.0,
                    value=float(firm_cfg.get("vat_rate", 7.5)),
                    step=0.5, format="%.1f", key="fa_vat_rate",
                    help="Applied to invoices (Nigeria standard VAT is 7.5%)",
                )
                wht_rate = st.number_input(
                    "WHT Rate (%) — Withholding Tax",
                    min_value=0.0, max_value=20.0,
                    value=float(firm_cfg.get("wht_rate", 5.0)),
                    step=0.5, format="%.1f", key="fa_wht_rate",
                    help="Withholding Tax (typically 5% or 10%)",
                )
                st.markdown("##### 🏛️ Default Jurisdictions")
                _courts = [
                    "Federal High Court", "High Court of Lagos State",
                    "High Court of Abuja (FCT)", "High Court of Rivers State",
                    "High Court of Kano State", "Court of Appeal",
                    "Supreme Court of Nigeria", "National Industrial Court",
                    "Magistrate Court",
                ]
                default_court = st.selectbox(
                    "Default Court", _courts,
                    index=_courts.index(firm_cfg["default_court"])
                          if firm_cfg.get("default_court") in _courts else 0,
                    key="fa_default_court",
                )
                _states = [
                    "Lagos", "FCT / Abuja", "Rivers", "Kano", "Ogun", "Oyo",
                    "Anambra", "Enugu", "Delta", "Cross River", "Federal",
                ]
                default_state = st.selectbox(
                    "Default State / Jurisdiction", _states,
                    index=_states.index(firm_cfg["default_state"])
                          if firm_cfg.get("default_state") in _states else 0,
                    key="fa_default_state",
                )

            with fa2:
                st.markdown("##### 🤖 AI & Monthly Budget")
                monthly_ai_budget = st.number_input(
                    "Monthly AI Budget (₦)",
                    min_value=0, max_value=10_000_000,
                    value=int(firm_cfg.get("monthly_ai_budget", 0)),
                    step=1000, key="fa_ai_budget",
                    help="Set to 0 for no limit.",
                )
                allowed_models = st.multiselect(
                    "Allowed AI Models", SUPPORTED_MODELS,
                    default=[m for m in firm_cfg.get("allowed_models", SUPPORTED_MODELS)
                             if m in SUPPORTED_MODELS],
                    key="fa_allowed_models",
                )
                st.markdown("##### 📋 Letterhead & Exports")
                letterhead_footer = st.text_area(
                    "Default Letterhead Footer",
                    value=firm_cfg.get("letterhead_footer", ""),
                    height=80, key="fa_lh_footer",
                    placeholder="e.g. Solicitors & Advocates · RC No. 123456",
                )
                bank_name = st.text_input(
                    "Bank Name (for invoices)",
                    value=firm_cfg.get("bank_name", ""), key="fa_bank_name",
                    placeholder="e.g. First Bank of Nigeria",
                )
                bank_account = st.text_input(
                    "Account Number",
                    value=firm_cfg.get("bank_account", ""), key="fa_bank_acct",
                    placeholder="e.g. 1234567890",
                )
                bank_sort_code = st.text_input(
                    "Sort Code / Account Name",
                    value=firm_cfg.get("bank_sort_code", ""), key="fa_bank_sort",
                    placeholder="e.g. Adekunle & Associates",
                )
                st.markdown("##### 🔐 User Permissions")
                allow_self_register = st.toggle(
                    "Allow self-registration",
                    value=firm_cfg.get("allow_self_register", True),
                    key="fa_self_reg",
                )
                require_admin_approval = st.toggle(
                    "Require admin approval for new accounts",
                    value=firm_cfg.get("require_admin_approval", False),
                    key="fa_admin_approval",
                )
                allow_user_api_key = st.toggle(
                    "Allow users to set their own API key",
                    value=firm_cfg.get("allow_user_api_key", True),
                    key="fa_user_api_key",
                )

            st.markdown("---")
            if st.button(
                "💾 Save Firm Admin Settings", type="primary",
                key="fa_save_btn", use_container_width=True,
            ):
                st.session_state.profile["firm_config"] = {
                    "default_hourly_rate":    default_hourly,
                    "billing_currency":       default_currency,
                    "vat_rate":               vat_rate,
                    "wht_rate":               wht_rate,
                    "default_court":          default_court,
                    "default_state":          default_state,
                    "monthly_ai_budget":      monthly_ai_budget,
                    "allowed_models":         allowed_models,
                    "letterhead_footer":      letterhead_footer.strip(),
                    "bank_name":              bank_name.strip(),
                    "bank_account":           bank_account.strip(),
                    "bank_sort_code":         bank_sort_code.strip(),
                    "allow_self_register":    allow_self_register,
                    "require_admin_approval": require_admin_approval,
                    "allow_user_api_key":     allow_user_api_key,
                }
                persist_profile()
                get_db().append_audit(
                    "FIRM_SETTINGS_UPDATED",
                    f"admin={st.session_state.get('current_username', '')}",
                )
                st.success("✅ Firm admin settings saved.")
                st.rerun()

            st.markdown("---")
            st.markdown("##### 💰 Billing Preview")
            _sym = {"NGN (₦)": "₦", "USD ($)": "$",
                    "GBP (£)": "£", "EUR (€)": "€"}.get(
                firm_cfg.get("billing_currency", "NGN (₦)"), "₦"
            )
            _sub = 5.0 * firm_cfg.get("default_hourly_rate", 50000)
            _vat = _sub * (firm_cfg.get("vat_rate", 7.5) / 100)
            _wht = _sub * (firm_cfg.get("wht_rate", 5.0) / 100)
            _tot = _sub + _vat - _wht
            st.markdown(
                f'<div style="background:var(--la-bg2);border:1px solid var(--la-border);'
                f'border-radius:8px;padding:0.9rem 1.2rem;font-size:0.86rem;color:var(--la-text);">'
                f'<strong>Sample Invoice — 5 hrs @ {_sym}'
                f'{firm_cfg.get("default_hourly_rate", 50000):,.0f}/hr</strong><br><br>'
                f'Subtotal: <strong>{_sym}{_sub:,.2f}</strong><br>'
                f'VAT ({firm_cfg.get("vat_rate",7.5)}%): <strong>{_sym}{_vat:,.2f}</strong><br>'
                f'WHT ({firm_cfg.get("wht_rate",5.0)}%): <strong>−{_sym}{_wht:,.2f}</strong><br>'
                f'<hr style="margin:0.4rem 0;border-color:var(--la-border);">'
                f'<strong>Total Payable: {_sym}{_tot:,.2f}</strong>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # ── Firm-wide announcement banner ────────────────────────────
            # Lets the admin push a single message to every user's screen
            # without emailing them. Common uses during the trial:
            #   "Maintenance tonight 21:00–22:00"
            #   "Try the new ⚡ Lifecycle Automation page"
            #   "v9.1.2 deployed — see release notes"
            st.markdown("---")
            st.markdown("##### 📣 Firm-Wide Announcement")
            st.caption(
                "Pin a short message to the top of every user's page until "
                "it expires or you clear it. Useful for maintenance windows, "
                "release notes, and trial reminders."
            )
            current = get_db().get_announcement() or {}
            with st.form("firm_announcement_form"):
                ann_text = st.text_area(
                    "Message",
                    value=current.get("text", ""),
                    height=80,
                    placeholder=(
                        "e.g. Scheduled maintenance tomorrow 21:00–22:00 WAT. "
                        "AI calls may pause briefly. — IT Team"
                    ),
                    key="ann_text_ta",
                )
                ac1, ac2, ac3 = st.columns([1.2, 1.2, 1.2])
                with ac1:
                    ann_level = st.selectbox(
                        "Level",
                        ["info", "success", "warning"],
                        index=["info", "success", "warning"].index(
                            current.get("level", "info")
                        ),
                        key="ann_level_sel",
                        help="info = blue · success = green · warning = amber",
                    )
                with ac2:
                    # Default expiry: 7 days from now
                    from datetime import timedelta as _td
                    _default_expires = current.get("expires", "")
                    try:
                        _default_expires_d = (
                            date.fromisoformat(_default_expires)
                            if _default_expires
                            else date.today() + _td(days=7)
                        )
                    except Exception:
                        _default_expires_d = date.today() + _td(days=7)
                    ann_expires = st.date_input(
                        "Expires on",
                        value=_default_expires_d,
                        min_value=date.today(),
                        key="ann_expires_inp",
                        help="Banner auto-hides after this date.",
                    )
                with ac3:
                    ann_active = st.checkbox(
                        "Active",
                        value=current.get("active", True),
                        key="ann_active_chk",
                        help="Uncheck to hide the banner without deleting.",
                    )

                af1, af2 = st.columns(2)
                with af1:
                    save_ann = st.form_submit_button(
                        "💾 Publish Announcement", type="primary",
                        use_container_width=True,
                    )
                with af2:
                    clear_ann = st.form_submit_button(
                        "🗑️ Clear Announcement",
                        use_container_width=True,
                    )

                if save_ann:
                    if not ann_text.strip():
                        st.error("❌ Message cannot be empty.")
                    else:
                        ok = get_db().set_announcement({
                            "text":       ann_text.strip(),
                            "level":      ann_level,
                            "expires":    ann_expires.isoformat(),
                            "active":     bool(ann_active),
                            "updated_by": st.session_state.get(
                                "current_username", "admin"
                            ),
                            "updated_at": datetime.now().isoformat(),
                        })
                        if ok:
                            try:
                                get_db().append_audit(
                                    "ANNOUNCEMENT_PUBLISHED",
                                    f"level={ann_level} expires={ann_expires.isoformat()} "
                                    f"active={ann_active} chars={len(ann_text.strip())}",
                                )
                            except Exception:
                                pass
                            st.success(
                                "✅ Announcement published. Users will see it "
                                "on their next page load."
                            )
                            st.rerun()
                        else:
                            st.error("❌ Could not save announcement. Try again.")

                if clear_ann:
                    if get_db().clear_announcement():
                        try:
                            get_db().append_audit(
                                "ANNOUNCEMENT_CLEARED", ""
                            )
                        except Exception:
                            pass
                        st.success("✅ Announcement cleared for all users.")
                        st.rerun()
                    else:
                        st.error("❌ Could not clear announcement.")

            # Live preview so admin can confirm before publishing
            if current and current.get("active"):
                st.caption(
                    f"Currently live · level={current.get('level','info')} · "
                    f"expires {current.get('expires','—')} · "
                    f"published by @{current.get('updated_by','?')}"
                )




