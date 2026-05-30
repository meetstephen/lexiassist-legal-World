"""LexiAssist runtime — third-party imports, version, environment helpers,
optional-dependency feature flags, logger, and a few low-level utilities
(`esc`, `safe_json_loads`) that are shared by every other module.

This module is the bottom of the dependency chain — every other module in
the `lexi` package imports from it.
"""
from __future__ import annotations

# ── Standard library ──────────────────────────────────────────────────
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
import html as html_mod
import json
import logging
import os
import re
try:
    import psycopg2
except ImportError:
    import psycopg2cffi as psycopg2  # type: ignore
import uuid
from datetime import datetime, date
from io import BytesIO
from typing import Any, Optional

# ── Third-party (always required) ─────────────────────────────────────
from google import genai
from google.genai import types as _genai_types
import pandas as pd
import streamlit as st

# ═══════════════════════════════════════════════════════
# VERSION (single source of truth)
# ═══════════════════════════════════════════════════════
# Bump on every user-visible release. Referenced by:
#   - module docstring (manually kept in sync)
#   - st.set_page_config(page_title=..., menu_items["About"])
#   - IDENTITY_CORE system prompt
#   - PDF/DOCX export footers
#   - README.md (manually kept in sync)
__version__ = "9.10.0"

# ── Public-facing brand version ───────────────────────────────────────
# The internal semver above keeps climbing with every change, which looks
# noisy to end users. ``BRAND_LABEL`` is the friendly, stable name shown in
# the UI / exports / emails (e.g. "LexiAssist 2.0"); ``__version__`` stays as
# the precise build number for data records, migrations and debugging.
BRAND_VERSION = "2.0"
BRAND_LABEL = f"LexiAssist {BRAND_VERSION}"

# ── Optional / guarded imports ────────────────────────────────────────
# Each block defines all symbols (even on import failure) so downstream
# modules can do `from .runtime import FPDF, DocxDocument, ...` safely.
# Symbols set to ``None`` on failure are only referenced inside
# ``if HAS_*:`` guards by callers.
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    px = None
    HAS_PLOTLY = False

try:
    import pdfplumber
    HAS_PDF_READ = True
except ImportError:
    pdfplumber = None
    HAS_PDF_READ = False

try:
    from docx import Document as DocxDocument
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn as _docx_qn
    from docx.oxml import OxmlElement as _OxmlElement
    HAS_DOCX = True
except ImportError:
    DocxDocument = None
    Pt = RGBColor = Inches = None
    WD_ALIGN_PARAGRAPH = None
    _docx_qn = None
    _OxmlElement = None
    HAS_DOCX = False

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    FPDF = None
    HAS_FPDF = False

try:
    import openpyxl
    HAS_XLSX = True
except ImportError:
    openpyxl = None
    HAS_XLSX = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LexiAssist")

# ═══════════════════════════════════════════════════════
# RUNTIME / ENVIRONMENT HELPERS
# ═══════════════════════════════════════════════════════
def app_env() -> str:
    """Return current app environment: development, beta, or production."""
    try:
        return str(st.secrets.get("APP_ENV", os.getenv("APP_ENV", "development"))).lower().strip()
    except Exception:
        return os.getenv("APP_ENV", "development").lower().strip()

def is_production() -> bool:
    return app_env() == "production"

def is_beta() -> bool:
    return app_env() in ("beta", "private_beta", "private-beta")

def require_secret(name: str) -> str:
    """Return a required secret or stop the app with a clear error."""
    val = ""
    try:
        val = st.secrets.get(name, "")
    except Exception:
        val = os.getenv(name, "")
    if not val:
        st.error(f"❌ Required secret `{name}` is missing. Add it to Streamlit secrets or environment variables.")
        st.stop()
    return str(val).strip()

def _extract_first_json_blob(text: str) -> str:
    """Best-effort extraction of the first balanced JSON object/array
    from a string that may also contain prose, commentary, or stray
    code-fence markers.

    Returns ``""`` if no JSON-shaped substring is found. The caller is
    still responsible for parsing — this only narrows the haystack.
    """
    if not text:
        return ""
    # Walk char-by-char tracking brace/bracket depth, ignoring those
    # inside string literals so a ``"}"`` inside a value doesn't trip us.
    start = -1
    opener = ""
    closer = ""
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if start == -1:
            if ch in "{[":
                start = i
                opener = ch
                closer = "}" if ch == "{" else "]"
                depth = 1
            continue
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return ""


def safe_json_loads(raw: str, fallback=None):
    """Safely parse JSON returned by LLMs.

    Robust to common LLM output quirks:
      * Markdown code fences (``` or ```json).
      * Leading/trailing prose around the JSON object.
      * Trailing commas before ``}`` / ``]`` (mild, not fully spec-compliant
        — only the simplest case).

    Returns ``fallback`` (default ``{}``) on any parse failure or when
    ``raw`` is empty / None.
    """
    if fallback is None:
        fallback = {}
    if not raw or not str(raw).strip():
        return fallback
    cleaned = str(raw).strip()
    # Strip code fences in any common form.
    cleaned = re.sub(r"^```(?:json|JSON)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    cleaned = cleaned.strip()
    # First attempt: parse as-is.
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # Second attempt: extract the first balanced JSON blob from prose.
    blob = _extract_first_json_blob(cleaned)
    if blob:
        try:
            return json.loads(blob)
        except Exception:
            # Third attempt: tolerate trailing commas.
            try:
                repaired = re.sub(r",(\s*[}\]])", r"\1", blob)
                return json.loads(repaired)
            except Exception:
                pass
    return fallback


def parse_ai_json_or_warn(
    raw: str,
    *,
    fallback=None,
    label: str = "AI response",
    show_raw_on_failure: bool = True,
) -> tuple:
    """Parse JSON from an LLM response and, on failure, render a clear
    diagnostic in the Streamlit UI so the user is never left staring at
    a blank screen.

    Returns ``(data, ok)``:
      * ``data`` — the parsed object, or the supplied ``fallback`` (default
        ``{}``) when parsing failed.
      * ``ok``   — ``True`` only when parsing succeeded and produced a
        non-empty container.

    The function purposefully calls ``st.error`` / ``st.warning`` /
    ``st.markdown`` itself; callers should handle the falsey ``ok`` by
    simply returning early after surfacing any extra context. This is
    the central guard against the historical "AI responded but the page
    rendered nothing" failure mode.
    """
    if fallback is None:
        fallback = {}
    raw_str = "" if raw is None else str(raw)
    raw_stripped = raw_str.strip()

    # Empty / whitespace-only response — most likely the API call returned
    # an error string ("⚠️ …") that was already stripped, or generation
    # was blocked. Either way, the user gets a clear message.
    if not raw_stripped:
        st.error(
            f"⚠️ The {label} came back empty. This usually means the AI "
            "model returned no content (rate limit, safety filter, or a "
            "transient network error). Please try again, or rephrase your "
            "input to be slightly different."
        )
        return fallback, False

    # If the model returned one of our own ⚠️/🚫 sentinel strings from
    # ``generate()``, surface it verbatim — it already explains itself.
    if raw_stripped.startswith(("⚠️", "🚫", "⏳")):
        st.warning(raw_stripped)
        return fallback, False

    data = safe_json_loads(raw_stripped, fallback=None)
    if data is None:
        st.error(
            f"⚠️ Could not parse the {label} as structured data. "
            "The AI may have returned commentary instead of JSON. "
            "Please try again — if it keeps happening, rephrase your input."
        )
        if show_raw_on_failure:
            with st.expander("Show raw AI output", expanded=False):
                st.markdown(
                    f'<div class="response-box">{esc(raw_stripped)}</div>',
                    unsafe_allow_html=True,
                )
        return fallback, False

    # Successful parse but empty container — caller decides what to do
    # with the data; we still flag ok=True so the UI can branch on
    # ``data`` itself rather than re-checking emptiness here.
    return data, True


# ═══════════════════════════════════════════════════════
# LOW-LEVEL HELPERS (used package-wide; live here to keep
# database / auth / helpers free of circular imports)
# ═══════════════════════════════════════════════════════
def esc(text: str) -> str:
    """HTML-escape a value. Empty input returns empty string."""
    if not text:
        return ""
    return html_mod.escape(str(text))


def new_id() -> str:
    """Generate a short, URL-safe identifier (8 hex chars).

    Centralised here because both lexi.database and lexi.helpers need
    it; routing through one of them would create a circular import.
    """
    return uuid.uuid4().hex[:8]


def hash_session_token(token: str) -> str:
    """Hash a session token before storing or comparing in the database.

    Centralised here for the same reason as ``new_id`` — both
    lexi.database and lexi.auth need this primitive.
    """
    return hashlib.sha256(token.encode()).hexdigest()
