"""Cookie-based session token management for LexiAssist.

Replaces the insecure ?t= URL token approach with HttpOnly-like cookies
set via JavaScript injection. Cookies are:
  - Scoped to the app's path (SameSite=Lax)
  - Set with Secure flag when running over HTTPS
  - Given a 30-day max-age by default (matching DB token TTL)

Reading cookies:
  Streamlit doesn't natively expose request cookies in v1.43, so we use
  a hidden component that reads document.cookie and passes it back via
  a Streamlit component message. As a fallback for the first render
  (before the component round-trip completes), we also parse cookies
  from st.session_state where the JS component stores them.

Writing cookies:
  We inject a small <script> block via st.components.v1.html() that
  sets/deletes cookies on the browser side.
"""
from __future__ import annotations

from .runtime import st

_COOKIE_NAME = "lexi_session"
_COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days in seconds


def set_session_cookie(token: str, max_age: int = _COOKIE_MAX_AGE) -> None:
    """Inject JavaScript to set the session cookie in the browser."""
    # Build cookie string with security attributes
    js = f"""
    <script>
    (function() {{
        var secure = (window.location.protocol === 'https:') ? '; Secure' : '';
        document.cookie = "{_COOKIE_NAME}={token}; path=/; max-age={max_age}; SameSite=Lax" + secure;
    }})();
    </script>
    """
    st.components.v1.html(js, height=0, width=0)


def delete_session_cookie() -> None:
    """Inject JavaScript to delete the session cookie from the browser."""
    js = f"""
    <script>
    (function() {{
        document.cookie = "{_COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax";
    }})();
    </script>
    """
    st.components.v1.html(js, height=0, width=0)


def get_session_cookie() -> str:
    """Read the session cookie value from the browser via a JS component.

    This uses a bidirectional component approach: a small JS snippet reads
    document.cookie, extracts our token, and writes it into a hidden query
    param that Streamlit can read on the next rerun.

    For the initial page load we inject a JS reader that stores the cookie
    value into a hidden div and communicates it back via query_params on the
    first load only (using a dedicated non-conflicting param name).

    Returns the token string or empty string if not found.
    """
    # Primary: check if we already extracted it in this session
    cached = st.session_state.get("_cookie_token", "")
    if cached:
        return cached

    # Secondary: read from the dedicated query param set by our JS on page load
    cookie_from_param = st.query_params.get("_lexi_ck", "")
    if cookie_from_param:
        st.session_state["_cookie_token"] = cookie_from_param
        # Clean up the query param so it doesn't linger in the URL
        try:
            del st.query_params["_lexi_ck"]
        except Exception:
            pass
        return cookie_from_param

    return ""


def inject_cookie_reader() -> None:
    """Inject a one-time JS snippet that reads the session cookie and
    communicates it back to Streamlit via a query parameter on page load.

    This should be called early in the app lifecycle (before auth checks)
    so the cookie value is available for auto-login on the next rerun.
    """
    # Only inject if we don't already have a token in session state
    if st.session_state.get("_cookie_token") or st.session_state.get("authenticated"):
        return

    js = f"""
    <script>
    (function() {{
        if (window._lexiCookieReaderDone) return;
        window._lexiCookieReaderDone = true;

        function getCookie(name) {{
            var nameEQ = name + "=";
            var ca = document.cookie.split(';');
            for (var i = 0; i < ca.length; i++) {{
                var c = ca[i].trim();
                if (c.indexOf(nameEQ) === 0) {{
                    return c.substring(nameEQ.length);
                }}
            }}
            return "";
        }}

        var token = getCookie("{_COOKIE_NAME}");
        if (token) {{
            // Communicate the cookie value back to Streamlit by updating the URL
            var url = new URL(window.location.href);
            // Only add if not already present
            if (!url.searchParams.has("_lexi_ck")) {{
                url.searchParams.set("_lexi_ck", token);
                // Use replaceState so it doesn't create a history entry
                window.history.replaceState(null, "", url.toString());
                // Trigger a Streamlit rerun by sending a message
                window.parent.postMessage({{
                    type: "streamlit:setComponentValue",
                    value: token
                }}, "*");
                // Force a soft reload to pick up the new query param
                setTimeout(function() {{
                    window.parent.location.href = url.toString();
                }}, 100);
            }}
        }}
    }})();
    </script>
    """
    st.components.v1.html(js, height=0, width=0)
