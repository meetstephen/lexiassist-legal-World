"""LexiAssist crypto — Fernet-based encryption for stored credentials.

Public API: ``HAS_CRYPTO``, ``encrypt_secret``, ``decrypt_secret``.
"""
from __future__ import annotations

from .runtime import st, os, logger, is_production, is_beta

# ═══════════════════════════════════════════════════════
# ENCRYPTION (Fernet-based, for stored credentials)
# ═══════════════════════════════════════════════════════
try:
    from cryptography.fernet import Fernet, InvalidToken
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def _get_encryption_key() -> bytes:
    """
    Resolve Fernet key from secrets or env.
    Production/beta: ENCRYPTION_KEY is REQUIRED.
    Development: generates a temporary session key if missing.
    """
    key = ""
    try:
        key = st.secrets.get("ENCRYPTION_KEY", "")
    except Exception:
        key = os.getenv("ENCRYPTION_KEY", "")
    if not key:
        if is_production() or is_beta():
            st.error(
                "❌ ENCRYPTION_KEY is required in beta/production. "
                "Generate a Fernet key and add it to Streamlit secrets."
            )
            st.code(
                'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"',
                language="bash",
            )
            st.stop()
        # Development fallback only
        if "_session_fernet_key" not in st.session_state:
            if HAS_CRYPTO:
                st.session_state["_session_fernet_key"] = Fernet.generate_key().decode()
            else:
                st.session_state["_session_fernet_key"] = ""
        key = st.session_state["_session_fernet_key"]
    return key.encode() if isinstance(key, str) else key


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a string. Returns Fernet token prefixed with enc:."""
    if not plaintext:
        return ""
    if not HAS_CRYPTO:
        if is_production() or is_beta():
            st.error("❌ `cryptography` package is required for beta/production secret storage.")
            st.stop()
        logger.warning("cryptography not installed; storing secret as plaintext in development only.")
        return plaintext
    try:
        key = _get_encryption_key()
        if not key:
            return plaintext
        f = Fernet(key)
        token = f.encrypt(plaintext.encode())
        return "enc:" + token.decode()
    except Exception as e:
        if is_production() or is_beta():
            logger.error("Encryption failed in a protected environment; refusing to persist plaintext.")
            raise RuntimeError("Secret encryption failed; plaintext storage is disabled.") from e
        logger.warning(f"Encryption failed in development: {e}")
        return plaintext


def decrypt_secret(token: str) -> str:
    """Decrypt a Fernet token. Returns plaintext, or original string if not encrypted."""
    if not token or not HAS_CRYPTO:
        return token
    if not token.startswith("enc:"):
        return token  # Legacy plaintext, or already decrypted
    try:
        key = _get_encryption_key()
        if not key:
            return ""
        f = Fernet(key)
        plaintext = f.decrypt(token[4:].encode())
        return plaintext.decode()
    except (InvalidToken, Exception) as e:
        logger.warning(f"Decryption failed: {e}")
        return ""
