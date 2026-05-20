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
__version__ = "9.1.1"

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

def safe_json_loads(raw: str, fallback=None):
    """Safely parse JSON returned by LLMs."""
    if fallback is None:
        fallback = {}
    try:
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception:
        return fallback


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
    """Generate a short, URL-safe identifier (12 hex chars).

    Centralised here because both lexi.database and lexi.helpers need
    it; routing through one of them would create a circular import.
    """
    return uuid.uuid4().hex[:12]


def hash_session_token(token: str) -> str:
    """Hash a session token before storing or comparing in the database.

    Centralised here for the same reason as ``new_id`` — both
    lexi.database and lexi.auth need this primitive.
    """
    return hashlib.sha256(token.encode()).hexdigest()
