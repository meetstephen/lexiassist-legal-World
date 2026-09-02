"""Browser-session compatibility helpers.

Persistent browser login was deliberately removed because Streamlit 1.43 cannot
set an HttpOnly cookie and the former implementation copied a bearer token into
the URL.  Authentication now remains in Streamlit's server-side session only.

A future persistent-login implementation must use a server-set HttpOnly,
Secure, SameSite=Strict cookie (for example behind an authentication proxy).
"""
from __future__ import annotations

from .runtime import st

_COOKIE_NAME = "lexi_session"


def set_session_cookie(token: str, max_age: int = 0) -> None:
    """No-op: never persist a bearer token in a JavaScript-readable cookie."""
    del token, max_age


def delete_session_cookie() -> None:
    """Delete a legacy cookie left by versions that used persistent sessions."""
    js = f"""
    <script>
    (function() {{
        document.cookie = "{_COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax";
        if (window.location.protocol === "https:") {{
            document.cookie = "{_COOKIE_NAME}=; path=/; max-age=0; SameSite=Strict; Secure";
        }}
    }})();
    </script>
    """
    st.components.v1.html(js, height=0, width=0)


def get_session_cookie() -> str:
    """Persistent token restoration is disabled until HttpOnly cookies exist."""
    return ""


def inject_cookie_reader() -> None:
    """Remove the legacy token cookie without ever reading or forwarding it."""
    if st.session_state.get("_legacy_cookie_cleared"):
        return
    delete_session_cookie()
    st.session_state["_legacy_cookie_cleared"] = True
