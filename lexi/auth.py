"""LexiAssist multi-user authentication — login, register, admin
bootstrap, session-token handling, and the password-policy helpers used
by the login / re-auth / setup screens.

``load_user_data`` and ``manual_connect`` live in ``lexi.helpers``; the
imports here are lazy because helpers itself depends on auth-adjacent
state.
"""
from __future__ import annotations

from .runtime import st, os, re, hashlib, time, datetime, uuid, logger, esc
from .crypto import encrypt_secret, decrypt_secret
from .constants import SUPPORTED_MODELS
from .themes import get_theme_css
from .database import get_db, load_user_data
from .cookies import set_session_cookie, delete_session_cookie


def manual_connect(key: str) -> bool:
    # Lazy indirection — defined in lexi.helpers; called only at runtime.
    from .helpers import manual_connect as _real
    return _real(key)

# ═══════════════════════════════════════════════════════
# MULTI-USER AUTH
# ═══════════════════════════════════════════════════════
def hash_session_token(token: str) -> str:
    """Hash a session token before storing or comparing in DB."""
    return hashlib.sha256(token.encode()).hexdigest()


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 with random salt. Format: pbkdf2$<salt>$<dk>"""
    import secrets as _sec
    salt = _sec.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"pbkdf2${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify against PBKDF2 hash, or legacy plain SHA-256 (auto-upgrades on login).
    Uses hmac.compare_digest() throughout to prevent timing attacks.
    """
    import hmac as _hmac
    if stored.startswith("pbkdf2$"):
        try:
            _, salt, dk_hex = stored.split("$")
            dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
            # compare_digest prevents timing-based username enumeration
            return _hmac.compare_digest(dk.hex(), dk_hex)
        except Exception:
            return False
    # Legacy SHA-256 path — also constant-time
    candidate = hashlib.sha256(password.encode()).hexdigest()
    return _hmac.compare_digest(candidate, stored)


def is_allow_registration() -> bool:
    try:
        return str(st.secrets.get("ALLOW_REGISTRATION", "false")).lower() == "true"
    except Exception:
        return os.getenv("ALLOW_REGISTRATION", "false").lower() == "true"


def do_login(username: str, password: str, remember_me: bool = True) -> bool:
    """Authenticate user, load their data into session. Returns True on success.
    Uses persistent (DB-backed) lockout per username — survives browser tabs / refreshes.
    """
    db = get_db()
    uname_clean = username.strip().lower()

    # ── Persistent lockout check (5 fails → 15 min lock per username) ──
    try:
        lock_data = db._load_list_raw(f"login_lock:{uname_clean}") or []
        if lock_data and isinstance(lock_data, list) and len(lock_data) > 0:
            lock_info = lock_data[0]
            locked_until = float(lock_info.get("locked_until", 0))
            import time as _t
            if _t.time() < locked_until:
                wait_min = int((locked_until - _t.time()) / 60) + 1
                logger.warning(f"Login blocked (locked) for {uname_clean} — {wait_min} min remaining")
                return False
    except Exception:
        pass

    user = db.get_user_by_username(uname_clean)
    if not user:
        _record_login_failure(uname_clean)
        return False
    if not verify_password(password, user["password_hash"]):
        _record_login_failure(uname_clean)
        return False

    # ── Successful login: clear failure record ──
    try:
        db._save_list_raw(f"login_lock:{uname_clean}", [])
    except Exception:
        pass

    # Auto-upgrade legacy SHA-256 → PBKDF2 on next login
    if not user["password_hash"].startswith("pbkdf2$"):
        get_db().update_user(user["user_id"], {"password_hash": hash_password(password)})
    uid = user["user_id"]
    st.session_state.authenticated = True
    st.session_state.current_user_id = uid
    st.session_state.current_username = user["username"]
    st.session_state.current_user_role = user["role"]
    db.update_user_last_login(uid)
    db.append_audit("LOGIN", f"user={uname_clean}")
    load_user_data()
    st.session_state.user_data_loaded = True
    # ── Session token: stored in HttpOnly-like cookie, NOT in URL ──
    if remember_me:
        token = db.create_session_token(uid, days=30)
        st.session_state["_session_token"] = token
        st.session_state["_cookie_token"] = token
        set_session_cookie(token)
    return True

def _record_login_failure(uname_clean: str) -> None:
    """Track failed login attempts persistently. Locks account after 5 fails for 15 min."""
    import time as _t
    try:
        db = get_db()
        rec = db._load_list_raw(f"login_lock:{uname_clean}") or []
        info = rec[0] if rec else {"fail_count": 0, "first_fail": _t.time(), "locked_until": 0}
        # Reset counter if more than 1 hour since first failure
        if _t.time() - info.get("first_fail", 0) > 3600:
            info = {"fail_count": 1, "first_fail": _t.time(), "locked_until": 0}
        else:
            info["fail_count"] = info.get("fail_count", 0) + 1
        if info["fail_count"] >= 5:
            info["locked_until"] = _t.time() + 15 * 60  # 15-minute lockout
            db.append_audit("ACCOUNT_LOCKED", f"user={uname_clean} fails={info['fail_count']}")
        db._save_list_raw(f"login_lock:{uname_clean}", [info])
    except Exception as e:
        logger.warning(f"Could not record login failure: {e}")



def do_auto_login_from_token(token: str) -> bool:
    """Silently restore a session from a persistent cookie token. Returns True if valid."""
    if not token:
        return False
    db = get_db()
    db.cleanup_expired_sessions()
    user = db.validate_session_token(token)
    if not user:
        return False  # Token invalid/expired
    uid = user["user_id"]
    st.session_state.authenticated = True
    st.session_state.current_user_id = uid
    st.session_state.current_username = user["username"]
    st.session_state.current_user_role = user["role"]
    st.session_state["_session_token"] = token
    st.session_state["_cookie_token"] = token
    load_user_data()
    st.session_state.user_data_loaded = True
    return True


def render_reauth_screen(token: str, username: str) -> None:
    """
    Locked-session re-authentication screen.
    Shown when a valid token exists but the session was idle too long.
    The user sees their own username (read-only) and must enter only their password.
    A random person at the desk cannot proceed without the password.
    After 5 failed attempts the token is revoked and a full login is required.
    """
    import time as _time
    _fail_key = "_reauth_fails"
    _fails = st.session_state.get(_fail_key, 0)

    st.markdown(
        '<div style="max-width:420px;margin:6vh auto 0;">'
        '<div style="background:var(--la-card);border:1px solid var(--la-border);'
        'border-radius:14px;padding:2rem 2rem 1.6rem;box-shadow:0 4px 24px #0002;">'
        '<div style="text-align:center;font-size:2.4rem;margin-bottom:0.4rem;">🔒</div>'
        '<h2 style="text-align:center;font-size:1.25rem;margin:0 0 0.3rem;color:var(--la-text);">'
        'Session Locked</h2>'
        '<p style="text-align:center;font-size:0.83rem;color:var(--la-text2);margin:0 0 1.4rem;">'
        'Your session was inactive. Enter your password to continue.</p>',
        unsafe_allow_html=True,
    )

    # Read-only username badge — confirms whose session this is
    st.markdown(
        f'<div style="background:var(--la-bg2);border:1px solid var(--la-border);'
        f'border-radius:8px;padding:0.55rem 1rem;margin-bottom:1rem;'
        f'font-size:0.9rem;color:var(--la-text2);text-align:center;">'
        f'👤 <strong style="color:var(--la-text);">@{esc(username)}</strong>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.form("reauth_form", clear_on_submit=True):
        reauth_pw = st.text_input(
            "Password", type="password",
            placeholder="Enter your password to unlock",
            key="reauth_pw_input",
        )
        col_unlock, col_signout = st.columns(2)
        with col_unlock:
            unlock_btn = st.form_submit_button(
                "🔓 Unlock", type="primary", use_container_width=True
            )
        with col_signout:
            signout_btn = st.form_submit_button(
                "↩️ Sign Out", use_container_width=True
            )

    if signout_btn:
        # Revoke token and go to login
        try:
            get_db().revoke_session_token(token)
            get_db().append_audit("REAUTH_SIGNOUT", f"user={username}")
        except Exception:
            pass
        delete_session_cookie()
        st.session_state.pop("_cookie_token", None)
        st.session_state.pop("_session_token", None)
        st.rerun()
        return

    if unlock_btn:
        if not reauth_pw:
            st.error("❌ Enter your password.")
        else:
            db = get_db()
            user_rec = db.get_user_by_username(username)
            if user_rec and verify_password(reauth_pw, user_rec["password_hash"]):
                # ✅ Correct password — restore session fully
                st.session_state.pop(_fail_key, None)
                uid = user_rec["user_id"]
                st.session_state.authenticated = True
                st.session_state.current_user_id = uid
                st.session_state.current_username = user_rec["username"]
                st.session_state.current_user_role = user_rec["role"]
                st.session_state["_session_token"] = token
                # Reset last_used so idle clock restarts from now
                db.touch_session_token(token)
                load_user_data()
                st.session_state.user_data_loaded = True
                st.session_state["_last_activity"] = _time.time()
                db.append_audit("REAUTH_SUCCESS", f"user={username}")
                st.rerun()
            else:
                _fails += 1
                st.session_state[_fail_key] = _fails
                db.append_audit("REAUTH_FAILED", f"user={username} attempt={_fails}")
                if _fails >= 5:
                    # Too many failures — revoke token, force full login
                    try:
                        db.revoke_session_token(token)
                        delete_session_cookie()
                        st.session_state.pop("_cookie_token", None)
                    except Exception:
                        pass
                    st.error("🔒 Too many failed attempts. You have been signed out.")
                    st.rerun()
                elif _fails >= 3:
                    st.error(f"❌ Wrong password. {5 - _fails} attempt(s) remaining.")
                else:
                    st.error("❌ Incorrect password.")

    st.markdown('</div></div>', unsafe_allow_html=True)


def do_logout():
    """Revoke session token, delete cookie, and wipe session state."""
    db = get_db()
    token = st.session_state.get("_session_token", "")
    uname = st.session_state.get("current_username", "unknown")
    db.append_audit("LOGOUT", f"user={uname}")
    if token:
        db.revoke_session_token(token)
    # Remove the session cookie from the browser
    delete_session_cookie()
    clear_keys = [
        "authenticated", "current_user_id", "current_username", "current_user_role",
        "user_data_loaded", "_session_token", "_cookie_token",
        "cases", "clients", "time_entries", "invoices",
        "chat_history", "custom_templates", "custom_limitation_periods", "custom_maxims",
        "profile", "last_response", "original_query", "research_results",
        "loaded_template", "imported_doc",
        "wp_result", "wp_role_label", "wp_facts_saved", "wp_reexam_result",
        "wp_witness_log", "wp_contra_result",
        "nf_feed_data", "nf_subject_loaded", "nf_deepdive", "nf_bookmarks", "nf_scan_result",
    ]
    for k in clear_keys:
        st.session_state.pop(k, None)
    st.rerun()


def render_login_screen():
    # Hide sidebar ONLY on login screen (re-shown after auth via render_sidebar override)
    st.markdown("""<style>
section[data-testid="stSidebar"]{display:none!important;}
[data-testid="stSidebarCollapsedControl"]{display:none!important;}
[data-testid="collapsedControl"]{display:none!important;}
[data-testid="stSidebarCollapseButton"]{display:none!important;}
</style>""", unsafe_allow_html=True)
    st.markdown(get_theme_css(st.session_state.get("theme", "⚖️ Corporate")), unsafe_allow_html=True)

    # ── Hero block — same style as render_home() ──
    st.markdown("""
<style>
.lexi-hero {
position: relative;
overflow: hidden;
background: linear-gradient(135deg, #1e3a5f 0%, #0f2440 60%, #162d4a 100%);
border-radius: 16px;
padding: 2.6rem 2.8rem 2.3rem;
margin-bottom: 1.8rem;
border: 1px solid rgba(255,255,255,0.08);
box-shadow: 0 8px 32px rgba(0,0,0,0.25);
}
.lexi-hero-watermark {
position: absolute;
right: 2rem;
top: 50%;
transform: translateY(-50%);
font-size: 13rem;
line-height: 1;
opacity: 0.07;
color: #ffffff;
pointer-events: none;
user-select: none;
filter: blur(1px);
font-family: serif;
}
.lexi-hero h1 {
font-size: 3.4rem !important;
font-weight: 900 !important;
letter-spacing: -0.04em !important;
color: #ffffff !important;
margin: 0 0 0.4rem 0 !important;
line-height: 1 !important;
position: relative;
z-index: 1;
}
.lexi-hero p {
font-size: 1rem !important;
color: rgba(255,255,255,0.82) !important;
margin: 0 !important;
position: relative;
z-index: 1;
line-height: 1.6;
}
@media (max-width: 768px) {
.lexi-hero h1 { font-size: 2.5rem !important; }
.lexi-hero-watermark { font-size: 7rem !important; opacity: 0.05 !important; }
}
</style>
<div class="lexi-hero">
<div class="lexi-hero-watermark">&#9878;</div>
        <h1>⚖️ LexiAssist</h1>
        <p>Elite AI Legal Engine &nbsp;&middot;&nbsp; Nigerian Law &nbsp;&middot;&nbsp; Built for Practitioners<br>

Position-taking &middot; Strategy-driven &middot; Risk-ranked &middot; Litigator-minded</p>
</div>
""", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("#### 🔒 Sign In to Your Workspace")
        st.markdown("<hr style='margin:0.6rem 0 1rem 0;border-color:#1a2e4a18'>", unsafe_allow_html=True)
        login_tabs = ["🔒 Login", "📝 Register"] if is_allow_registration() else ["🔒 Login"]
        if len(login_tabs) > 1:
            tab_login, tab_reg = st.tabs(login_tabs)
        else:
            tab_login = st.container(); tab_reg = None
        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                username_inp = st.text_input("Username", placeholder="your.username", key="login_username_inp")
                password_inp = st.text_input("Password", type="password", key="login_password_inp")
                remember_me  = st.checkbox("Stay signed in for 30 days", value=True, key="login_remember_me")
                if st.form_submit_button("🔒 Sign In", type="primary", use_container_width=True):
                    import time as _time
                    _locked_until = st.session_state.get("_login_locked_until", 0.0)
                    _fail_count   = st.session_state.get("_login_fail_count", 0)
                    if _time.time() < _locked_until:
                        _wait = int(_locked_until - _time.time())
                        st.error(f"🔒 Too many failed attempts. Try again in {_wait} seconds.")
                    elif not username_inp.strip() or not password_inp:
                        st.error("❌ Enter both username and password.")
                    else:
                        # Check persistent DB lockout BEFORE attempting login
                        _uname_check = username_inp.strip().lower()
                        try:
                            _lock = get_db()._load_list_raw(f"login_lock:{_uname_check}") or []
                            if _lock and isinstance(_lock, list) and _lock:
                                _li = _lock[0]
                                _lu = float(_li.get("locked_until", 0))
                                if _time.time() < _lu:
                                    _mins = int((_lu - _time.time()) / 60) + 1
                                    st.error(f"🔒 Account temporarily locked after repeated failures. Try again in {_mins} minute(s) or contact your admin.")
                                    st.stop()
                        except Exception:
                            pass
                        if do_login(username_inp.strip(), password_inp, remember_me):
                            st.session_state["_login_fail_count"] = 0
                            st.success(f"✅ Welcome back, @{st.session_state.current_username}!")
                            time.sleep(0.3); st.rerun()
                        else:
                            _fail_count += 1
                            st.session_state["_login_fail_count"] = _fail_count
                            if _fail_count >= 5:
                                st.session_state["_login_locked_until"] = _time.time() + 300
                                st.error("🔒 Too many failed attempts. Locked for 5 minutes (this device) — and if this continues, your account will be locked across all devices for 15 minutes.")
                            elif _fail_count >= 3:
                                st.error(f"❌ Invalid credentials. {5 - _fail_count} attempt(s) remaining.")
                            else:
                                st.error("❌ Invalid username or password.")
                            try:
                                get_db().append_audit("LOGIN_FAILED", f"user={username_inp.strip()[:60]} attempt={_fail_count}")
                            except Exception:
                                pass

        if tab_reg is not None:
            with tab_reg: render_register_form("reg_self")
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Forgot Password? Self-service recovery flow ──
        render_forgot_password_section()

        st.markdown(
            "<div style='text-align:center;margin-top:1.2rem;color:var(--la-text2);font-size:0.82rem;'>"
            "Need a new account? Contact your firm administrator.</div>",
            unsafe_allow_html=True)


def render_register_form(key_prefix: str, admin_mode: bool = False):
    """Reusable registration / account-creation form."""
    db = get_db()
    is_first_user = not db.has_any_users()

    with st.form(f"{key_prefix}_form", clear_on_submit=True):
        r1, r2 = st.columns(2)
        with r1:
            reg_username = st.text_input("Username *", placeholder="e.g. amaka.obi", key=f"{key_prefix}_uname")
            reg_pw = st.text_input("Password *", type="password", key=f"{key_prefix}_pw")
            reg_confirm = st.text_input("Confirm Password *", type="password", key=f"{key_prefix}_confirm")
        with r2:
            reg_lawyer = st.text_input("Full Name *", placeholder="Barr. Amaka Obi", key=f"{key_prefix}_lname")
            reg_firm = st.text_input("Firm Name", placeholder="Obi & Associates", key=f"{key_prefix}_firm")
            reg_email = st.text_input("Email", placeholder="amaka@obilaw.com", key=f"{key_prefix}_email")

        role_options = ["user", "admin"] if admin_mode else ["user"]
        reg_role = st.selectbox("Role", role_options, key=f"{key_prefix}_role") if admin_mode else "user"

        # ── NDPA 2023 / NDPR Privacy Consent (mandatory for Nigerian deployment) ──
        st.markdown("---")
        st.markdown(
            '<div style="background:var(--la-bg2);border:1px solid var(--la-border);'
            'border-left:4px solid #6366f1;border-radius:8px;'
            'padding:0.7rem 1rem;font-size:0.78rem;color:var(--la-text);">'
            '<strong>📜 Privacy & Data Protection Notice (NDPA 2023):</strong><br>'
            'By creating an account, you acknowledge that LexiAssist will store the personal data '
            'you supply (name, email, phone) and any client/case data you create, on encrypted '
            'PostgreSQL infrastructure. This data is used solely to provide legal practice '
            'management services. You retain all rights as a data subject under the '
            '<em>Nigeria Data Protection Act 2023</em> — including access, rectification, '
            'erasure, and portability. You are responsible for ensuring you have lawful basis '
            '(client consent, retainer, legal obligation) before entering any third-party data. '
            '</div>',
            unsafe_allow_html=True,
        )
        consent_ndpa = st.checkbox(
            "I have read and accept the Privacy & Data Protection Notice above, "
            "and confirm I will only enter client data where I have a lawful basis to do so.",
            key=f"{key_prefix}_consent_ndpa",
        )

        btn_label = "🛡️ Create Admin Account" if is_first_user else "✅ Create Account"
        if st.form_submit_button(btn_label, type="primary", use_container_width=True):
            if not consent_ndpa:
                st.error("❌ You must accept the Privacy Notice to create an account.")
                return False

            uname = reg_username.strip().lower()
            if not uname or not reg_pw or not reg_lawyer.strip():
                st.error("❌ Username, password, and full name are required.")
                return False
            if len(uname) < 3:
                st.error("❌ Username must be at least 3 characters.")
                return False
            if reg_pw != reg_confirm:
                st.error("❌ Passwords do not match.")
                return False
            if len(reg_pw) < 6:
                st.error("❌ Password must be at least 6 characters.")
                return False
            if db.get_user_by_username(uname):
                st.error(f"❌ Username '{uname}' is already taken.")
                return False

            role = "admin" if (is_first_user or reg_role == "admin") else "user"
            user_id = uuid.uuid4().hex[:12]
            ok = db.create_user({
                "user_id": user_id,
                "username": uname,
                "password_hash": hash_password(reg_pw),
                "firm_name": reg_firm.strip(),
                "lawyer_name": reg_lawyer.strip(),
                "email": reg_email.strip(),
                "role": role,
            })
            if ok:
                if is_first_user:
                    # Migrate any legacy data to this admin account
                    migrated = db.migrate_legacy_data_to_user(user_id)
                    if migrated > 0:
                        st.info(f"ℹ️ {migrated} legacy data item(s) migrated to your account.")
                db.append_audit("USER_CREATED", f"new_user={uname} role={role}")
                if not admin_mode:
                    # Auto-login after self-registration
                    do_login(uname, reg_pw)
                    st.success(f"✅ Account created! Welcome, {reg_lawyer.strip()}.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.success(f"✅ Account created for {reg_lawyer.strip()} (@{uname}) [{role}].")
                return True
            else:
                st.error("❌ Account creation failed. Try a different username.")
                return False
    return False


def render_create_admin_screen():
    """First-run screen: no users exist yet."""
    st.markdown("""<style>
section[data-testid="stSidebar"]{display:none!important;}
[data-testid="stSidebarCollapsedControl"]{display:none!important;}
[data-testid="collapsedControl"]{display:none!important;}
[data-testid="stSidebarCollapseButton"]{display:none!important;}
</style>""", unsafe_allow_html=True)
    st.markdown(get_theme_css(st.session_state.get("theme", "⚖️ Corporate")), unsafe_allow_html=True)

    # ── Hero block — same style as home page ──
    st.markdown("""
 <style>
 .lexi-hero {
 position: relative;
 overflow: hidden;
 background: linear-gradient(135deg, #1e3a5f 0%, #0f2440 60%, #162d4a 100%);
 border-radius: 16px;
 padding: 2.6rem 2.8rem 2.3rem;
 margin-bottom: 1.8rem;
 border: 1px solid rgba(255,255,255,0.08);
 box-shadow: 0 8px 32px rgba(0,0,0,0.25);
 }
 .lexi-hero-watermark {
 position: absolute;
 right: 2rem;
 top: 50%;
 transform: translateY(-50%);
 font-size: 13rem;
 line-height: 1;
 opacity: 0.07;
 color: #ffffff;
 pointer-events: none;
 user-select: none;
 filter: blur(1px);
 font-family: serif;
 }
 .lexi-hero h1 {
 font-size: 3.4rem !important;
 font-weight: 900 !important;
 letter-spacing: -0.04em !important;
 color: #ffffff !important;
 margin: 0 0 0.4rem 0 !important;
 line-height: 1 !important;
 position: relative;
 z-index: 1;
 }
 .lexi-hero p {
 font-size: 1rem !important;
 color: rgba(255,255,255,0.82) !important;
 margin: 0 !important;
 position: relative;
 z-index: 1;
 line-height: 1.6;
 }
 @media (max-width: 768px) {
 .lexi-hero h1 { font-size: 2.5rem !important; }
 .lexi-hero-watermark { font-size: 7rem !important; opacity: 0.05 !important; }
 }
 </style>
 <div class="lexi-hero">
 <div class="lexi-hero-watermark">&#9878;</div>
        <h1>⚖️ LexiAssist</h1>
        <p>First-time setup &nbsp;&middot;&nbsp; Create your administrator account below</p>

 </div>
 """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("#### 🛡️ Create Administrator Account")
        st.info("ℹ️ No accounts exist yet. The first account you create becomes the admin.")
        st.markdown("<hr style='margin:0.6rem 0 1rem 0;border-color:#1a2e4a18'>", unsafe_allow_html=True)
        render_register_form("first_admin")
        st.markdown("</div>", unsafe_allow_html=True)


def render_setup_screen():
    st.markdown("""<style>
[data-testid="stSidebar"]{display:none!important;}
[data-testid="collapsedControl"]{display:none!important;}
</style>""", unsafe_allow_html=True)
    st.markdown("""
    <div class="hero">
        <h1>⚖️ LexiAssist </h1>
        <p>Elite AI Legal Engine for Nigerian Lawyers</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔐 Secure API Configuration")
    st.markdown("""
    Your API key is required to power the AI engine. It is **never displayed**
    in the sidebar or stored outside this session.

    **Recommended:** Add your key to Streamlit Secrets (`.streamlit/secrets.toml`)
    or set the `GEMINI_API_KEY` environment variable so this screen never appears.
    """)

    with st.form("api_setup_form"):
        key_input = st.text_input(
            "Google Gemini API Key",
            type="password",
            placeholder="Paste your API key here…",
            help="Get a key at https://aistudio.google.com/app/apikey",
        )
        model_sel = st.selectbox("AI Model", SUPPORTED_MODELS, index=0)
        submitted = st.form_submit_button("🔗 Connect", type="primary", use_container_width=True)

        if submitted:
            if key_input and len(key_input.strip()) >= 10:
                st.session_state.gemini_model = model_sel
                with st.spinner("🔗 Connecting to Gemini…"):
                    if manual_connect(key_input.strip()):
                        st.success("✅ Connected! Redirecting…")
                        time.sleep(1)
                        st.rerun()
            else:
                st.error("❌ Please enter a valid API key.")

    st.divider()
    st.caption("💡 **Tip:** To skip this screen permanently, add to `.streamlit/secrets.toml`:")
    st.code('GEMINI_API_KEY = "your-key-here"\nGEMINI_MODEL = "gemini-2.5-flash"\n# ALLOW_REGISTRATION = "true"  # let users self-register', language="toml")




# ═══════════════════════════════════════════════════════
# PASSWORD RECOVERY (self-service)
# ═══════════════════════════════════════════════════════
# Two-stage flow:
#   Stage 1 — user enters their username; if found AND has email AND any
#             admin has SMTP configured, a 6-digit one-time code is sent
#             to the user's email. The code's hash is stored in kv_store
#             with a 15-minute expiry.
#   Stage 2 — user enters the code + new password; on success the password
#             is updated and the code is consumed.
#
# Falls back gracefully when SMTP is not available — instructs the user
# to ask their firm admin (who can reset passwords from User Management
# → 🔑 Reset Password).
#
# Rate-limit: max 3 reset requests per username per hour to prevent abuse.


def _generate_reset_code() -> str:
    """Generate a 6-digit numeric code (e.g. '482910')."""
    import secrets as _sec
    return f"{_sec.randbelow(900_000) + 100_000:06d}"


def _hash_reset_code(code: str, salt: str) -> str:
    """Salted SHA-256 — same scheme as session tokens. We never store the
    plaintext code so even DB compromise can't be used to log in."""
    import hashlib as _h
    return _h.sha256(f"{salt}:{code}".encode()).hexdigest()


def _find_smtp_sender() -> tuple[str, str, str] | tuple[None, None, None]:
    """Return (smtp_user, smtp_pass_plaintext, sender_email) for the first
    admin user whose profile has SMTP configured. Returns (None, None, None)
    if no admin has set up SMTP — caller must show fallback message.

    Rationale: per-user SMTP lives in profile['notif_smtp_user'] /
    notif_smtp_pass / notif_email. We pick any admin's config as the
    firm-wide sender because the admin already trusts these credentials
    for hearing-reminder emails.
    """
    db = get_db()
    try:
        admins = [u for u in db.list_users() if u.get("role") == "admin"]
        for adm in admins:
            uid = adm.get("user_id")
            if not uid:
                continue
            # Profile is per-user — load this admin's profile directly
            prof_rows = db._load_list_raw(f"u:{uid}:profile") or []
            if not prof_rows or not isinstance(prof_rows, list):
                continue
            prof = prof_rows[0] if isinstance(prof_rows[0], dict) else {}
            smtp_user = (prof.get("notif_smtp_user") or "").strip()
            smtp_pass_enc = (prof.get("notif_smtp_pass") or "").strip()
            if smtp_user and smtp_pass_enc:
                smtp_pass = decrypt_secret(smtp_pass_enc)
                if smtp_pass:
                    return smtp_user, smtp_pass, smtp_user
    except Exception as e:
        logger.warning(f"Could not look up admin SMTP config: {e}")
    return None, None, None


def _send_reset_email(to_email: str, username: str, code: str,
                      smtp_user: str, smtp_pass: str) -> bool:
    """Send the password-reset code via Gmail SMTP. Returns True on success."""
    try:
        import smtplib as _smtplib
        from email.mime.multipart import MIMEMultipart as _MM
        from email.mime.text import MIMEText as _MT

        msg = _MM()
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg["Subject"] = "🔒 LexiAssist — Password Reset Code"

        body = (
            f"Hello,\n\n"
            f"A password reset has been requested for the LexiAssist account "
            f"@{username}.\n\n"
            f"Your one-time reset code is:\n\n"
            f"        {code}\n\n"
            f"This code expires in 15 minutes and can only be used once.\n\n"
            f"If you did not request a password reset, please ignore this email "
            f"and notify your firm administrator — your account remains secure.\n\n"
            f"---\n"
            f"LexiAssist · Elite AI Legal Engine for Nigerian Lawyers\n"
            f"Do not reply to this email."
        )
        msg.attach(_MT(body, "plain"))

        with _smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return True
    except Exception as e:
        logger.warning(f"Password-reset email failed: {e}")
        return False


def _mask_email(email: str) -> str:
    """Mask an email for display: 'amaka@example.com' → 'a****@example.com'."""
    if not email or "@" not in email:
        return email
    local, _, domain = email.partition("@")
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}{'*' * (len(local) - 1)}@{domain}"


def _request_password_reset(username: str) -> dict:
    """Initiate a password-reset request. Returns a dict with keys:
      - ok: bool
      - message: str (user-facing)
      - email_masked: str (only when ok=True)
      - admin_contact: str (only when ok=False due to no SMTP)
    """
    import time as _time
    import secrets as _sec

    db = get_db()
    uname_clean = username.strip().lower()
    if not uname_clean:
        return {"ok": False, "message": "Please enter a username."}

    # Rate limit: max 3 requests per username per hour
    rl_key = f"pwreset_rl:{uname_clean}"
    rl = db._load_list_raw(rl_key) or []
    rl_info = rl[0] if rl else {"count": 0, "first_request": _time.time()}
    # Reset counter after 1 hour
    if _time.time() - rl_info.get("first_request", 0) > 3600:
        rl_info = {"count": 0, "first_request": _time.time()}
    if rl_info.get("count", 0) >= 3:
        wait_min = int((rl_info["first_request"] + 3600 - _time.time()) / 60) + 1
        return {
            "ok": False,
            "message": f"Too many reset requests. Try again in {wait_min} minute(s) "
                       f"or contact your firm administrator.",
        }
    rl_info["count"] = rl_info.get("count", 0) + 1
    db._save_list_raw(rl_key, [rl_info])

    user = db.get_user_by_username(uname_clean)
    if not user:
        # Don't leak whether the username exists — say the same thing either way
        db.append_audit("PWRESET_UNKNOWN_USER", f"attempted_user={uname_clean[:60]}")
        return {
            "ok": False,
            "message": "If that username exists, instructions have been sent. "
                       "If you don't receive an email, contact your firm administrator.",
        }

    user_email = (user.get("email") or "").strip()
    if not user_email or "@" not in user_email:
        # Find admin contact for fallback
        admins = [u for u in db.list_users() if u.get("role") == "admin"]
        admin_contact = ""
        for adm in admins:
            ae = (adm.get("email") or "").strip()
            if ae:
                admin_contact = f"{adm.get('lawyer_name', '') or adm.get('username','admin')} <{ae}>"
                break
        db.append_audit("PWRESET_NO_EMAIL", f"user={uname_clean}")
        return {
            "ok": False,
            "message": "Your account has no email on file, so a self-service reset "
                       "is not possible. Please contact your firm administrator to "
                       "reset your password.",
            "admin_contact": admin_contact,
        }

    # Look up SMTP — needed to actually send the code
    smtp_user, smtp_pass, _sender = _find_smtp_sender()
    if not smtp_user or not smtp_pass:
        admins = [u for u in db.list_users() if u.get("role") == "admin"]
        admin_contact = ""
        for adm in admins:
            ae = (adm.get("email") or "").strip()
            if ae:
                admin_contact = f"{adm.get('lawyer_name', '') or adm.get('username','admin')} <{ae}>"
                break
        db.append_audit("PWRESET_NO_SMTP", f"user={uname_clean}")
        return {
            "ok": False,
            "message": "Self-service password reset is not available because "
                       "your firm has not configured email notifications yet. "
                       "Please contact your firm administrator — they can reset "
                       "your password from the User Management page.",
            "admin_contact": admin_contact,
        }

    # Generate code, salt, and hash; store with 15-min expiry
    code = _generate_reset_code()
    salt = _sec.token_hex(16)
    code_hash = _hash_reset_code(code, salt)
    expires_at = _time.time() + 15 * 60  # 15 minutes

    reset_record = {
        "user_id": user["user_id"],
        "username": uname_clean,
        "code_hash": code_hash,
        "salt": salt,
        "expires_at": expires_at,
        "attempts": 0,
        "created_at": _time.time(),
    }
    db._save_list_raw(f"pwreset:{uname_clean}", [reset_record])

    # Send the email
    sent = _send_reset_email(user_email, uname_clean, code, smtp_user, smtp_pass)
    if not sent:
        db.append_audit("PWRESET_EMAIL_FAILED", f"user={uname_clean}")
        return {
            "ok": False,
            "message": "We could not send the reset email at this time. "
                       "Please try again in a few minutes or contact your firm administrator.",
        }

    db.append_audit("PWRESET_REQUESTED", f"user={uname_clean}")
    return {
        "ok": True,
        "message": "A 6-digit reset code has been sent to your email. "
                   "It expires in 15 minutes.",
        "email_masked": _mask_email(user_email),
    }


def _verify_reset_code(username: str, code: str, new_password: str) -> dict:
    """Verify the reset code and update the password. Returns {ok, message}."""
    import time as _time
    import hmac as _hmac

    db = get_db()
    uname_clean = username.strip().lower()
    code_clean = code.strip()
    if not uname_clean or not code_clean:
        return {"ok": False, "message": "Please enter both username and code."}
    if len(new_password) < 6:
        return {"ok": False, "message": "New password must be at least 6 characters."}

    rec_list = db._load_list_raw(f"pwreset:{uname_clean}") or []
    if not rec_list:
        return {
            "ok": False,
            "message": "No active reset request for this username. "
                       "Request a new code first.",
        }
    rec = rec_list[0] if isinstance(rec_list, list) and rec_list else {}

    # Expiry check
    if _time.time() > float(rec.get("expires_at", 0)):
        db._save_list_raw(f"pwreset:{uname_clean}", [])
        return {
            "ok": False,
            "message": "Your reset code has expired. Request a new one.",
        }

    # Attempt limit (5 wrong codes per request)
    attempts = int(rec.get("attempts", 0))
    if attempts >= 5:
        db._save_list_raw(f"pwreset:{uname_clean}", [])
        db.append_audit("PWRESET_TOO_MANY_ATTEMPTS", f"user={uname_clean}")
        return {
            "ok": False,
            "message": "Too many incorrect attempts. The reset request has been "
                       "cancelled. Request a new code if you still need to reset.",
        }

    # Constant-time code comparison
    expected = _hash_reset_code(code_clean, rec.get("salt", ""))
    if not _hmac.compare_digest(expected, rec.get("code_hash", "")):
        rec["attempts"] = attempts + 1
        db._save_list_raw(f"pwreset:{uname_clean}", [rec])
        remaining = 5 - rec["attempts"]
        return {
            "ok": False,
            "message": f"Incorrect code. {remaining} attempt(s) remaining.",
        }

    # Code matches — update password, consume the reset record, clear lockout
    user_id = rec.get("user_id", "")
    if not user_id:
        return {"ok": False, "message": "Reset request is malformed. Try again."}

    db.update_user(user_id, {"password_hash": hash_password(new_password)})
    db._save_list_raw(f"pwreset:{uname_clean}", [])
    # Clear any login lockout so the user can sign in immediately
    db._save_list_raw(f"login_lock:{uname_clean}", [])
    db.append_audit("PWRESET_SUCCESS", f"user={uname_clean}")

    return {
        "ok": True,
        "message": "Password reset successful. You can now sign in with your new password.",
    }


def render_forgot_password_section():
    """Render the 'Forgot Password?' UI as an expander on the login screen.
    Two-stage flow with state persisted in session_state."""
    with st.expander("🤔 Forgot your password?", expanded=False):
        # Stage indicator stored in session
        stage = st.session_state.get("_pwreset_stage", "request")

        if stage == "request":
            st.caption(
                "Enter your username. If your account has an email on file "
                "and your firm has email notifications configured, we'll send "
                "you a 6-digit code to reset your password."
            )
            with st.form("pwreset_request_form"):
                pwr_username = st.text_input(
                    "Username", placeholder="your.username", key="pwr_username_inp",
                )
                req_btn = st.form_submit_button(
                    "📧 Send Reset Code", type="primary", use_container_width=True,
                )
            if req_btn:
                if not pwr_username.strip():
                    st.error("❌ Please enter your username.")
                else:
                    with st.spinner("Processing reset request…"):
                        result = _request_password_reset(pwr_username.strip())
                    if result["ok"]:
                        st.success(
                            f"✅ {result['message']} (Sent to "
                            f"{result.get('email_masked','your email')})"
                        )
                        st.session_state["_pwreset_stage"] = "verify"
                        st.session_state["_pwreset_username"] = pwr_username.strip().lower()
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.warning(result["message"])
                        if result.get("admin_contact"):
                            st.info(
                                f"📞 **Your firm admin:** {result['admin_contact']}"
                            )

        else:  # stage == "verify"
            saved_username = st.session_state.get("_pwreset_username", "")
            st.caption(
                f"A 6-digit code was sent for **@{saved_username}**. "
                f"Enter the code below along with your new password. "
                f"The code expires in 15 minutes."
            )
            with st.form("pwreset_verify_form"):
                pwr_code = st.text_input(
                    "Reset Code", placeholder="6-digit code from email",
                    max_chars=6, key="pwr_code_inp",
                )
                pwr_new = st.text_input(
                    "New Password", type="password",
                    placeholder="Minimum 6 characters", key="pwr_new_inp",
                )
                pwr_confirm = st.text_input(
                    "Confirm New Password", type="password",
                    key="pwr_confirm_inp",
                )
                vc1, vc2 = st.columns(2)
                with vc1:
                    verify_btn = st.form_submit_button(
                        "🔓 Reset Password", type="primary", use_container_width=True,
                    )
                with vc2:
                    cancel_btn = st.form_submit_button(
                        "↩️ Start Over", use_container_width=True,
                    )

            if cancel_btn:
                st.session_state.pop("_pwreset_stage", None)
                st.session_state.pop("_pwreset_username", None)
                st.rerun()

            if verify_btn:
                if pwr_new != pwr_confirm:
                    st.error("❌ Passwords do not match.")
                elif len(pwr_new) < 6:
                    st.error("❌ Password must be at least 6 characters.")
                elif not pwr_code.strip():
                    st.error("❌ Enter the 6-digit code from your email.")
                else:
                    with st.spinner("Verifying code and updating password…"):
                        result = _verify_reset_code(
                            saved_username, pwr_code.strip(), pwr_new,
                        )
                    if result["ok"]:
                        st.success(f"✅ {result['message']}")
                        st.session_state.pop("_pwreset_stage", None)
                        st.session_state.pop("_pwreset_username", None)
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error(f"❌ {result['message']}")
