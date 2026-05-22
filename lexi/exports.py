"""LexiAssist export functions — PDF / DOCX / TXT / HTML output with
firm branding and optional Streamlit download buttons.

This module references ``get_firm_name`` (defined in ``lexi.helpers``);
that lookup is done lazily inside each function to avoid a circular
import.

PDF rendering strategy (v9.1.2+):
  1. At import time, scan the OS for a Unicode TTF font (DejaVuSans /
     NotoSans / Liberation). If found, all subsequent ``export_pdf``
     calls register and use it — every Naira sign, em-dash, smart quote,
     and accented character renders correctly.
  2. If no Unicode font is available we fall back to fpdf2's built-in
     ``Helvetica`` core font. Helvetica is Latin-1 only, so the body is
     pre-sanitised through a comprehensive Unicode → ASCII map
     (``_PDF_ASCII_MAP``) instead of being silently mangled by a lossy
     ``encode('latin-1', errors='replace')``. ₦ becomes ``NGN``, em-dash
     becomes ``-``, etc.
  3. fpdf2 ≥ 2.7 deprecations (``txt=``, ``ln=True``, ``rotate(...)``,
     ``output(dest='S')``) are handled via the new API
     (``text=``, ``new_x``/``new_y``, ``rotation()`` context manager,
     plain ``output()``) with backward-compatible try/except fallbacks.
"""
from __future__ import annotations

import os
from pathlib import Path

from .runtime import (
    st, html_mod, datetime, BytesIO, logger,
    HAS_FPDF, FPDF,
    HAS_DOCX, DocxDocument, Pt, RGBColor, Inches, WD_ALIGN_PARAGRAPH,
    _docx_qn, _OxmlElement,
    __version__,
)


def get_firm_name() -> str:
    # Lazy indirection to break import cycle (helpers imports exports).
    from .helpers import get_firm_name as _real
    return _real()


# ═══════════════════════════════════════════════════════
# PDF UNICODE SUPPORT — font discovery + sanitisation
# ═══════════════════════════════════════════════════════

# Common system paths for Unicode TTF fonts on Linux/Mac (Streamlit Cloud is
# Debian-based; DejaVu Sans is part of the base ``fonts-dejavu-core`` package
# and is reliably present at this path).
_FONT_CANDIDATES = [
    # (family_label, regular, bold, italic, bold_italic)
    ("DejaVuSans", [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
    ], [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/DejaVuSans-Bold.ttf",
        "/usr/local/share/fonts/DejaVuSans-Bold.ttf",
    ], [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Oblique.ttf",
    ], [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-BoldOblique.ttf",
    ]),
    ("NotoSans", [
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/noto/NotoSans-Regular.ttf",
    ], [
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/noto/NotoSans-Bold.ttf",
    ], [
        "/usr/share/fonts/truetype/noto/NotoSans-Italic.ttf",
        "/usr/share/fonts/noto/NotoSans-Italic.ttf",
    ], [
        "/usr/share/fonts/truetype/noto/NotoSans-BoldItalic.ttf",
        "/usr/share/fonts/noto/NotoSans-BoldItalic.ttf",
    ]),
    ("LiberationSans", [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    ], [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    ], [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Italic.ttf",
    ], [
        "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf",
        "/usr/share/fonts/liberation/LiberationSans-BoldItalic.ttf",
    ]),
]


def _find_font_files() -> tuple[str, str, str | None, str | None, str | None] | None:
    """Return (family_label, regular_path, bold_path|None, italic_path|None,
    bold_italic_path|None) for the first font family found, or None if no
    Unicode font is available on this system.
    """
    def _first_existing(paths):
        for p in paths:
            if p and os.path.exists(p):
                return p
        return None

    for label, regs, bolds, ital, bital in _FONT_CANDIDATES:
        regular = _first_existing(regs)
        if not regular:
            continue
        return (
            label,
            regular,
            _first_existing(bolds),
            _first_existing(ital),
            _first_existing(bital),
        )
    return None


# Unicode → ASCII fallback map for when no Unicode font is available.
# Covers the punctuation Nigerian legal drafts actually use.
_PDF_ASCII_MAP = {
    # Currency (Helvetica core has no Naira glyph)
    "\u20a6": "NGN ",        # ₦  Naira sign → "NGN"
    "\u00a3": "GBP ",        # £
    "\u20ac": "EUR ",        # €
    "\u00a5": "JPY ",        # ¥
    # Dashes
    "\u2013": "-",            # – en-dash
    "\u2014": "-",            # — em-dash
    "\u2015": "-",            # ― horizontal bar
    "\u2212": "-",            # − minus
    # Quotes
    "\u2018": "'",            # ‘
    "\u2019": "'",            # ’
    "\u201a": ",",            # ‚
    "\u201b": "'",            # ‛
    "\u201c": '"',            # “
    "\u201d": '"',            # ”
    "\u201e": ',,',           # „
    "\u00ab": '"',            # «
    "\u00bb": '"',            # »
    "\u2032": "'",            # ′ prime
    "\u2033": '"',            # ″ double prime
    # Spaces / breaks
    "\u00a0": " ",            # NBSP
    "\u2002": " ",            # en space
    "\u2003": " ",            # em space
    "\u2009": " ",            # thin space
    "\u202f": " ",            # narrow NBSP
    "\u200b": "",             # ZWSP
    "\u200c": "",             # ZWNJ
    "\u200d": "",             # ZWJ
    "\ufeff": "",             # BOM
    # Punctuation
    "\u2026": "...",         # …
    "\u00b7": "-",            # · middle dot (kept simple)
    "\u2022": "*",            # • bullet
    "\u25aa": "*",            # ▪
    "\u25cf": "*",            # ●
    "\u25e6": "o",            # ◦
    "\u00a7": "Sec.",        # § section
    "\u00b6": "Para.",       # ¶ pilcrow
    # Box-drawing (used in our headings)
    "\u2550": "=", "\u2500": "-", "\u2501": "-",
    "\u2502": "|", "\u2503": "|",
    "\u250c": "+", "\u2510": "+", "\u2514": "+", "\u2518": "+",
    "\u251c": "+", "\u2524": "+", "\u252c": "+", "\u2534": "+", "\u253c": "+",
    # Arrows
    "\u2192": "->",           # →
    "\u2190": "<-",           # ←
    "\u21d2": "=>",           # ⇒
    "\u21d4": "<=>",         # ⇔
    "\u25b8": ">",            # ▸ (used in our headings)
    "\u25b6": ">",            # ▶
    # Math / misc that lawyers occasionally type
    "\u00d7": "x",            # ×
    "\u00f7": "/",            # ÷
    "\u2260": "!=",           # ≠
    "\u2264": "<=",           # ≤
    "\u2265": ">=",           # ≥
    "\u00b1": "+/-",         # ±
    "\u00b0": " deg",        # °
    # Fractions (rarely used but cheap to map)
    "\u00bc": "1/4", "\u00bd": "1/2", "\u00be": "3/4",
    # Common ligatures
    "\u0152": "OE", "\u0153": "oe",
    "\u00c6": "AE", "\u00e6": "ae",
    # Stars / warnings (we use these in disclaimers)
    "\u2605": "*", "\u2606": "*", "\u26a0": "!",
    "\u2713": "v", "\u2714": "v", "\u2717": "x", "\u2718": "x",
    # Trademark / copyright / registered (Helvetica DOES have these but be safe)
    # We deliberately don't remap (c) (R) (TM) — Helvetica handles them.
}


def _pdf_ascii_fallback(text: str) -> str:
    """When no Unicode font is registered, replace troublesome unicode
    characters with sensible ASCII equivalents (and final round-trip
    everything else through Latin-1 to stay safe).
    """
    if not text:
        return ""
    # 1. Apply explicit map
    out = []
    for ch in text:
        if ch in _PDF_ASCII_MAP:
            out.append(_PDF_ASCII_MAP[ch])
        else:
            out.append(ch)
    s = "".join(out)
    # 2. Strip any remaining emoji / surrogate pairs / non-BMP characters
    #    to avoid latin-1 substitution noise.
    s = "".join(ch if ord(ch) < 0x10000 else "" for ch in s)
    # 3. Final lossy fallback for anything outside Latin-1.
    return s.encode("latin-1", errors="replace").decode("latin-1")


# Cached font discovery — runs once per process.
_FONT_INFO: dict | None = None


def _get_pdf_font_info() -> dict:
    """Discover available Unicode font once and cache the result.

    Returns dict with keys:
      - family:       'DejaVuSans' | 'NotoSans' | 'LiberationSans' | 'Helvetica'
      - has_unicode:  bool
      - reg/bold/italic/bold_italic: TTF paths (only if has_unicode)
    """
    global _FONT_INFO
    if _FONT_INFO is not None:
        return _FONT_INFO
    found = _find_font_files()
    if found:
        label, reg, bold, ital, bital = found
        _FONT_INFO = {
            "family": label,
            "has_unicode": True,
            "reg": reg,
            "bold": bold or reg,           # fall back to regular for missing variants
            "italic": ital or reg,
            "bold_italic": bital or bold or reg,
        }
        logger.info(f"PDF: Unicode font registered ({label} from {reg})")
    else:
        _FONT_INFO = {"family": "Helvetica", "has_unicode": False}
        logger.warning(
            "PDF: No Unicode TTF font found on system. Falling back to Helvetica "
            "with ASCII-mapped sanitiser. ₦ will render as 'NGN', em-dash as '-'. "
            "Install fonts-dejavu-core (Debian/Ubuntu) for native Unicode rendering."
        )
    return _FONT_INFO


def _register_pdf_fonts(pdf, info: dict) -> str:
    """Register Unicode fonts on a fresh FPDF instance and return the family
    name to pass into ``set_font``.
    """
    if not info.get("has_unicode"):
        return "Helvetica"
    fam = info["family"]
    try:
        pdf.add_font(fam, "",  info["reg"],         uni=True)
        pdf.add_font(fam, "B", info["bold"],        uni=True)
        pdf.add_font(fam, "I", info["italic"],      uni=True)
        pdf.add_font(fam, "BI", info["bold_italic"], uni=True)
        return fam
    except TypeError:
        # fpdf2 ≥ 2.7 dropped the deprecated ``uni`` kwarg.
        try:
            pdf.add_font(fam, "",  info["reg"])
            pdf.add_font(fam, "B", info["bold"])
            pdf.add_font(fam, "I", info["italic"])
            pdf.add_font(fam, "BI", info["bold_italic"])
            return fam
        except Exception as e:
            logger.warning(f"PDF: failed to register {fam}, falling back to Helvetica: {e}")
            return "Helvetica"
    except Exception as e:
        logger.warning(f"PDF: failed to register {fam}, falling back to Helvetica: {e}")
        return "Helvetica"


def _pdf_text(s: str, has_unicode: bool) -> str:
    """Sanitise a string for the active PDF font. Identity when a Unicode
    font is registered; ASCII-fallback otherwise.
    """
    if s is None:
        return ""
    if has_unicode:
        # Strip null bytes only; leave everything else for the Unicode font.
        return s.replace("\x00", "")
    return _pdf_ascii_fallback(s)


def _cell(pdf, w, h, txt, *, align: str = "L", new_line: bool = True, has_unicode: bool = True):
    """Wrapper around ``pdf.cell`` that uses the modern fpdf2 API
    (``text=``, ``new_x=``/``new_y=``) with a try/except fallback to the
    legacy API (``txt=``, ``ln=True``) so we work on every fpdf2 ≥ 2.5.
    """
    safe = _pdf_text(txt, has_unicode)
    try:
        from fpdf.enums import XPos, YPos  # fpdf2 ≥ 2.7
        if new_line:
            pdf.cell(w, h, text=safe, align=align, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            pdf.cell(w, h, text=safe, align=align, new_x=XPos.RIGHT, new_y=YPos.TOP)
    except Exception:
        # Legacy API fallback
        try:
            pdf.cell(w, h, txt=safe, align=align, ln=1 if new_line else 0)
        except Exception as e:
            logger.warning(f"PDF cell render failed for {safe!r}: {e}")


def _multi_cell(pdf, w, h, txt, *, align: str = "L", has_unicode: bool = True):
    safe = _pdf_text(txt, has_unicode)
    try:
        pdf.multi_cell(w, h, text=safe, align=align)
    except Exception:
        try:
            pdf.multi_cell(w, h, txt=safe, align=align)
        except Exception as e:
            logger.warning(f"PDF multi_cell render failed: {e}")


# ═══════════════════════════════════════════════════════
# EXPORT FUNCTIONS (WITH FIRM BRANDING)
# ═══════════════════════════════════════════════════════
def export_pdf(text: str, title: str = "LexiAssist Analysis") -> bytes:
    """Generate a confidential, branded PDF of an AI analysis or draft.

    Always uses a Unicode font when one is available on the system; otherwise
    falls back to Helvetica with a comprehensive Unicode → ASCII sanitiser
    so that ₦, em-dashes and smart quotes never crash the renderer.
    """
    if not HAS_FPDF:
        return b"%PDF-1.0\nPDF generation unavailable. Install fpdf2."

    firm = get_firm_name()
    profile = st.session_state.get("profile", {})
    lawyer = profile.get("lawyer_name", "")
    nba_no = profile.get("nba_enroll", "")
    nba_branch = profile.get("nba_branch", "")

    info = _get_pdf_font_info()
    has_uni = info.get("has_unicode", False)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    fam = _register_pdf_fonts(pdf, info)
    pdf.add_page()

    # ── Confidentiality banner ─────────────────────────────────────
    pdf.set_font(fam, "B", 8)
    pdf.set_text_color(180, 30, 30)
    _cell(
        pdf, 0, 5,
        "STRICTLY PRIVATE & CONFIDENTIAL — ATTORNEY WORK PRODUCT — NOT FOR DISCLOSURE",
        align="C", has_unicode=has_uni,
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    # ── Title ──────────────────────────────────────────────────────
    pdf.set_font(fam, "B", 16)
    _cell(pdf, 0, 12, title, align="C", has_unicode=has_uni)
    pdf.ln(2)
    if firm and firm != "LexiAssist":
        pdf.set_font(fam, "B", 11)
        _cell(pdf, 0, 7, firm, align="C", has_unicode=has_uni)
    if lawyer:
        pdf.set_font(fam, "", 10)
        counsel_line = f"Counsel: {lawyer}"
        if nba_no:
            counsel_line += f"  ·  SCN Enroll. No: {nba_no}"
        if nba_branch:
            counsel_line += f"  ·  NBA {nba_branch} Branch"
        _cell(pdf, 0, 6, counsel_line, align="C", has_unicode=has_uni)
    pdf.set_font(fam, "I", 9)
    _cell(
        pdf, 0, 6,
        f"Generated: {datetime.now():%d %B %Y at %H:%M}",
        align="C", has_unicode=has_uni,
    )
    pdf.ln(6)
    pdf.set_draw_color(100, 100, 100)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    # ── Body ───────────────────────────────────────────────────────
    pdf.set_font(fam, "", 10)
    body = text if text else ""
    for line in body.split("\n"):
        _multi_cell(pdf, 0, 6, line, has_unicode=has_uni)
        pdf.ln(1)

    # ── Diagonal "CONFIDENTIAL" watermark ──────────────────────────
    try:
        pdf.set_font(fam, "B", 60)
        pdf.set_text_color(230, 230, 230)
        # Prefer the modern context-manager API
        if hasattr(pdf, "rotation"):
            with pdf.rotation(45, x=105, y=150):
                pdf.text(40, 150, _pdf_text("CONFIDENTIAL", has_uni))
        else:
            pdf.rotate(45, x=105, y=150)
            pdf.text(40, 150, _pdf_text("CONFIDENTIAL", has_uni))
            pdf.rotate(0)
        pdf.set_text_color(0, 0, 0)
    except Exception:
        # rotate() / rotation() not available — silent fallback.
        pdf.set_text_color(0, 0, 0)

    # ── Footer ─────────────────────────────────────────────────────
    pdf.ln(8)
    pdf.set_font(fam, "I", 8)
    pdf.set_text_color(100, 100, 100)
    _cell(
        pdf, 0, 5,
        f"Generated by {firm} via LexiAssist v{__version__} — Verify all citations independently",
        align="C", has_unicode=has_uni,
    )
    _cell(
        pdf, 0, 5,
        "This document contains confidential information protected by attorney-client privilege.",
        align="C", has_unicode=has_uni,
    )
    pdf.set_text_color(0, 0, 0)

    # ── Output (handle every fpdf2 version) ───────────────────────
    try:
        raw = pdf.output()           # fpdf2 ≥ 2.7 returns bytearray directly
    except TypeError:
        raw = pdf.output(dest="S")   # older API
    if isinstance(raw, str):
        return raw.encode("latin-1", errors="replace")
    if isinstance(raw, bytearray):
        return bytes(raw)
    return raw


# ── DOCX helper functions ────────────────────────────────────────────────────
def _docx_shade_paragraph(para, fill_hex: str) -> None:
    pPr = para._p.get_or_add_pPr()
    for x in pPr.findall(_docx_qn("w:shd")): pPr.remove(x)
    shd = _OxmlElement("w:shd")
    shd.set(_docx_qn("w:val"),  "clear"); shd.set(_docx_qn("w:color"), "auto")
    shd.set(_docx_qn("w:fill"), fill_hex.lstrip("#")); pPr.append(shd)

def _docx_set_cell_bg(cell, fill_hex: str) -> None:
    tc = cell._tc; tcPr = tc.get_or_add_tcPr()
    for x in tcPr.findall(_docx_qn("w:shd")): tcPr.remove(x)
    shd = _OxmlElement("w:shd")
    shd.set(_docx_qn("w:val"),  "clear"); shd.set(_docx_qn("w:color"), "auto")
    shd.set(_docx_qn("w:fill"), fill_hex.lstrip("#")); tcPr.append(shd)

def _docx_add_footer(doc, firm: str) -> None:
    section = doc.sections[0]
    section.different_first_page_header_footer = False
    footer = section.footer
    para   = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    para.clear(); para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pPr  = para._p.get_or_add_pPr()
    pBdr = _OxmlElement("w:pBdr"); top = _OxmlElement("w:top")
    top.set(_docx_qn("w:val"),  "single"); top.set(_docx_qn("w:sz"),    "4")
    top.set(_docx_qn("w:space"),"1");      top.set(_docx_qn("w:color"), "1a2e4a")
    pBdr.append(top); pPr.append(pBdr)
    tabs_el = _OxmlElement("w:tabs"); tab = _OxmlElement("w:tab")
    tab.set(_docx_qn("w:val"),"right"); tab.set(_docx_qn("w:pos"),"9026")
    tabs_el.append(tab); pPr.append(tabs_el)
    grey = RGBColor(0x6b,0x72,0x80)
    ft   = firm if firm and firm != "LexiAssist" else f"LexiAssist v{__version__}"
    disc = f"{ft}  \u00b7  LexiAssist v{__version__}  \u00b7  Verify all citations independently"
    def _sr(t, bold=False):
        r=para.add_run(t); r.font.name="Calibri"; r.font.size=Pt(8); r.font.bold=bold; r.font.color.rgb=grey
    def _fr(instr):
        r=para.add_run(); r.font.name="Calibri"; r.font.size=Pt(8); r.font.color.rgb=grey
        b=_OxmlElement("w:fldChar"); b.set(_docx_qn("w:fldCharType"),"begin")
        it=_OxmlElement("w:instrText")
        it.set("{http://www.w3.org/XML/1998/namespace}space","preserve"); it.text=f" {instr} "
        e=_OxmlElement("w:fldChar"); e.set(_docx_qn("w:fldCharType"),"end")
        r._r.extend([b,it,e])
    _sr(disc); _sr("\t"); _sr("Page "); _fr("PAGE"); _sr(" of "); _fr("NUMPAGES")

def _docx_parse_output(text: str) -> list:
    blocks = []
    for line in text.split("\n"):
        s = line.strip()
        if not s: continue
        if "\u2550\u2550\u2550" in s:
            inner = s.replace("\u2550","").strip()
            if inner: blocks.append({"type":"heading2","content":inner})
            continue
        if len(s)>3 and all(c in "\u2550\u2500\u2501\u2014=-*" for c in s): continue
        if s.startswith("\u25b8"):
            blocks.append({"type":"subheading","content":s[1:].strip()}); continue
        if s[:1] in ("\U0001f534","\U0001f7e1","\U0001f7e2"):
            lvl = "HIGH" if "\U0001f534" in s[:4] else ("MEDIUM" if "\U0001f7e1" in s[:4] else "LOW")
            body = s
            for pfx in ("\U0001f534 HIGH RISK \u2192","\U0001f7e1 MEDIUM RISK \u2192","\U0001f7e2 LOW RISK \u2192",
                        "\U0001f534","\U0001f7e1","\U0001f7e2"):
                if body.startswith(pfx): body=body[len(pfx):].strip(); break
            sep = " \u2014 " if " \u2014 " in body else (" - " if " - " in body else None)
            party,reason = body.split(sep,1) if sep else (body,"")
            blocks.append({"type":"risk_row","level":lvl,"party":party.strip(),"reason":reason.strip()})
            continue
        if s.startswith(("\u2022 ","\u25aa ","\u00b7 ")):
            blocks.append({"type":"bullet","content":s[2:].strip()}); continue
        if s.startswith(("  \u2022","  -","\t\u2022","\t-")):
            blocks.append({"type":"bullet","content":s.strip().lstrip("\u2022-").strip()}); continue
        if s.endswith(":") and 5<len(s)<60 and not any(c in s for c in ".?!"):
            blocks.append({"type":"subheading","content":s}); continue
        blocks.append({"type":"body","content":s})
    return blocks

def export_docx(text: str, title: str = "LexiAssist Analysis",
                doc_type: str = "general", meta: dict = None) -> bytes:
    """Professional DOCX: letterhead, risk tables, per-type preambles."""
    if not HAS_DOCX:
        return b"DOCX generation unavailable - install python-docx."
    meta=meta or {}
    NAVY=RGBColor(0x1a,0x2e,0x4a); GOLD=RGBColor(0xc9,0xa8,0x4c)
    DARK_GREY=RGBColor(0x37,0x41,0x51); MID_GREY=RGBColor(0x6b,0x72,0x80)
    LIGHT_BLU=RGBColor(0xa0,0xbc,0xd8)
    firm=get_firm_name() or "LexiAssist"; date_str=datetime.now().strftime("%d %B %Y")
    bio=BytesIO(); doc=DocxDocument()
    sec=doc.sections[0]
    sec.page_width=int(8.27*914400); sec.page_height=int(11.69*914400)
    sec.left_margin=Inches(1.0); sec.right_margin=Inches(1.0)
    sec.top_margin=Inches(0.8); sec.bottom_margin=Inches(0.9)
    def _sb(style,sz,bold=False,col=None,sb=0,sa=6):
        style.font.name="Calibri"; style.font.size=Pt(sz); style.font.bold=bold
        if col: style.font.color.rgb=col
        style.paragraph_format.space_before=Pt(sb)
        style.paragraph_format.space_after=Pt(sa)
        style.paragraph_format.line_spacing=Pt(sz*1.3)
    _sb(doc.styles["Normal"],11,col=DARK_GREY,sa=6)
    _sb(doc.styles["Heading 1"],18,True,NAVY,8,4)
    _sb(doc.styles["Heading 2"],13,True,NAVY,14,4)
    _sb(doc.styles["Heading 3"],11,True,DARK_GREY,10,2)
    doc.styles["Heading 1"].paragraph_format.keep_with_next=True
    doc.styles["Heading 2"].paragraph_format.keep_with_next=True
    try: _sb(doc.styles["List Bullet"],11,col=DARK_GREY,sa=3)
    except: pass
    hdr=doc.sections[0].header
    hp=hdr.paragraphs[0] if hdr.paragraphs else hdr.add_paragraph()
    hp.clear(); hp.alignment=WD_ALIGN_PARAGRAPH.LEFT
    _docx_shade_paragraph(hp,"1a2e4a")
    hp.paragraph_format.space_before=Pt(5); hp.paragraph_format.space_after=Pt(5)
    rf=hp.add_run(firm.upper() if firm!="LexiAssist" else "LEXIASSIST")
    rf.font.name="Calibri"; rf.font.size=Pt(12); rf.font.bold=True; rf.font.color.rgb=GOLD
    rt=hp.add_run(f"   \u00b7   Legal Analysis   \u00b7   Confidential   \u00b7   {date_str}")
    rt.font.name="Calibri"; rt.font.size=Pt(9); rt.font.color.rgb=LIGHT_BLU
    _docx_add_footer(doc,firm)
    doc.add_paragraph(title,style="Heading 1")
    mp=doc.add_paragraph(); mp.paragraph_format.space_after=Pt(14)
    rm=mp.add_run(f"{firm}   \u00b7   {date_str}   \u00b7   Generated by LexiAssist v{__version__}")
    rm.font.name="Calibri"; rm.font.size=Pt(9); rm.font.color.rgb=MID_GREY
    pPr=mp._p.get_or_add_pPr(); pBdr=_OxmlElement("w:pBdr"); btm=_OxmlElement("w:bottom")
    btm.set(_docx_qn("w:val"),"single"); btm.set(_docx_qn("w:sz"),"6")
    btm.set(_docx_qn("w:space"),"1"); btm.set(_docx_qn("w:color"),"1a2e4a")
    pBdr.append(btm); pPr.append(pBdr)
    def _pr(label,value):
        if not value: return
        p=doc.add_paragraph()
        p.paragraph_format.space_before=Pt(0); p.paragraph_format.space_after=Pt(2)
        rl=p.add_run(f"{label}:  ")
        rl.font.name="Calibri"; rl.font.size=Pt(10); rl.font.bold=True; rl.font.color.rgb=NAVY
        rv=p.add_run(value)
        rv.font.name="Calibri"; rv.font.size=Pt(10); rv.font.color.rgb=DARK_GREY
    def _sp(): s=doc.add_paragraph(); s.paragraph_format.space_after=Pt(6)
    if doc_type=="pleading":
        for line,sz,bold in [
            (meta.get("court","IN THE FEDERAL HIGH COURT OF NIGERIA"),11,True),
            (meta.get("division",""),10,False),
            ("HOLDEN AT "+meta.get("location","ABUJA"),10,False),
            ("",9,False),("SUIT NO: "+meta.get("suit_no","_______________"),10,True),
            ("",9,False),("BETWEEN",10,True),
            (meta.get("claimant","_______________"),11,True),
            ("(CLAIMANT / APPELLANT)",9,False),("AND",10,True),
            (meta.get("defendant","_______________"),11,True),
            ("(DEFENDANT / RESPONDENT)",9,False),
        ]:
            if not line: _sp(); continue
            p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before=Pt(1); p.paragraph_format.space_after=Pt(1)
            r=p.add_run(line); r.font.name="Calibri"; r.font.size=Pt(sz)
            r.font.bold=bold; r.font.color.rgb=NAVY
        _sp(); _sp()
    elif doc_type=="research":
        doc.add_paragraph("LEGAL RESEARCH MEMORANDUM",style="Heading 2")
        _pr("Prepared by",firm); _pr("Prepared for",meta.get("prepared_for",""))
        _pr("Date",date_str); _pr("Subject",title)
        _pr("Area of law",meta.get("area","")); _pr("Jurisdiction",meta.get("jurisdiction","Nigeria")); _sp()
    elif doc_type in ("invoice","fee_note"):
        doc.add_paragraph("PROFESSIONAL FEE NOTE / INVOICE",style="Heading 2")
        _pr("Invoice No.",meta.get("invoice_no","")); _pr("Date",date_str)
        _pr("Client",meta.get("client","")); _pr("Matter",meta.get("matter",""))
        _pr("Amount",meta.get("amount","")); _pr("Due Date",meta.get("due_date","")); _sp()
    elif doc_type=="witness":
        doc.add_paragraph("WITNESS PREPARATION BRIEF",style="Heading 2")
        _pr("Witness",meta.get("witness","")); _pr("Role",meta.get("role",""))
        _pr("Matter",meta.get("matter","")); _pr("Prepared by",firm); _pr("Date",date_str)
        p=doc.add_paragraph()
        r=p.add_run("STRICTLY CONFIDENTIAL \u2014 Attorney-Client Privilege. Not for disclosure to opposing counsel.")
        r.font.name="Calibri"; r.font.size=Pt(9); r.font.bold=True
        r.font.color.rgb=RGBColor(0x99,0x1b,0x1b); _sp()
    elif doc_type=="settlement":
        doc.add_paragraph("SETTLEMENT STRATEGY BRIEF",style="Heading 2")
        _pr("Matter",meta.get("matter","")); _pr("Prepared by",firm); _pr("Date",date_str)
        p=doc.add_paragraph(); r=p.add_run("CONFIDENTIAL \u2014 Without Prejudice")
        r.font.name="Calibri"; r.font.size=Pt(10); r.font.bold=True
        r.font.color.rgb=RGBColor(0x92,0x40,0x0e); _sp()
    elif doc_type=="due_diligence":
        doc.add_paragraph("DUE DILIGENCE REPORT",style="Heading 2")
        _pr("Subject",meta.get("subject","")); _pr("Prepared by",firm)
        _pr("Date",date_str); _pr("Classification","STRICTLY CONFIDENTIAL"); _sp()
    blocks=_docx_parse_output(text); risk_buf=[]
    RCFG={"HIGH":  {"fill":"fef2f2","text":RGBColor(0x7f,0x1d,0x1d)},
          "MEDIUM":{"fill":"fefce8","text":RGBColor(0x71,0x3f,0x12)},
          "LOW":   {"fill":"f0fdf4","text":RGBColor(0x14,0x53,0x2d)}}
    def _flush():
        nonlocal risk_buf
        if not risk_buf: return
        cw=[int(1.7*914400),int(1.1*914400),int(3.47*914400)]
        tbl=doc.add_table(rows=1,cols=3); tbl.style="Table Grid"; tbl.autofit=False
        for i,cell in enumerate(tbl.rows[0].cells): cell.width=cw[i]
        for cell,lbl in zip(tbl.rows[0].cells,["PARTY","RISK","EXPOSURE / REASON"]):
            _docx_set_cell_bg(cell,"1a2e4a"); p=cell.paragraphs[0]; p.clear()
            r=p.add_run(lbl); r.font.name="Calibri"; r.font.size=Pt(9)
            r.font.bold=True; r.font.color.rgb=GOLD
            p.paragraph_format.space_before=Pt(3); p.paragraph_format.space_after=Pt(3)
        for rb in risk_buf:
            lvl=rb.get("level","LOW"); cfg=RCFG.get(lvl,RCFG["LOW"]); row=tbl.add_row()
            for i,cell in enumerate(row.cells):
                cell.width=cw[i]; _docx_set_cell_bg(cell,cfg["fill"])
                p=cell.paragraphs[0]; p.clear()
                p.paragraph_format.space_before=Pt(3); p.paragraph_format.space_after=Pt(3)
                r=p.add_run(rb.get("party","") if i==0 else lvl if i==1 else rb.get("reason",""))
                r.font.name="Calibri"; r.font.size=Pt(10 if i!=1 else 9)
                r.font.bold=(i==0 or i==1); r.font.color.rgb=cfg["text"]
        s=doc.add_paragraph(); s.paragraph_format.space_after=Pt(4); risk_buf=[]
    for block in blocks:
        bt=block["type"]
        if bt=="risk_row": risk_buf.append(block); continue
        else: _flush()
        if bt=="heading2":
            doc.add_paragraph(block["content"],style="Heading 2")
        elif bt=="subheading":
            p=doc.add_paragraph()
            p.paragraph_format.space_before=Pt(8); p.paragraph_format.space_after=Pt(2)
            r=p.add_run(block["content"])
            r.font.name="Calibri"; r.font.size=Pt(11); r.font.bold=True; r.font.color.rgb=NAVY
        elif bt=="bullet":
            try:
                p=doc.add_paragraph(block["content"],style="List Bullet")
                p.paragraph_format.space_after=Pt(3)
                for run in p.runs: run.font.name="Calibri"; run.font.size=Pt(11); run.font.color.rgb=DARK_GREY
            except:
                p=doc.add_paragraph(); r=p.add_run(f"\u2022  {block['content']}")
                r.font.name="Calibri"; r.font.size=Pt(11); r.font.color.rgb=DARK_GREY
        elif bt=="body":
            p=doc.add_paragraph(block["content"]); p.style=doc.styles["Normal"]
    _flush()
    doc.add_paragraph()
    disc=doc.add_paragraph()
    pPr2=disc._p.get_or_add_pPr(); pBdr2=_OxmlElement("w:pBdr"); dt=_OxmlElement("w:top")
    dt.set(_docx_qn("w:val"),"single"); dt.set(_docx_qn("w:sz"),"4")
    dt.set(_docx_qn("w:space"),"1"); dt.set(_docx_qn("w:color"),"cccccc")
    pBdr2.append(dt); pPr2.append(pBdr2)
    rd=disc.add_run(f"\u26a0  AI-generated via LexiAssist v{__version__}. Not legal advice. "
        f"Verify all citations independently. \u00a9 {datetime.now().year} {firm}.")
    rd.font.name="Calibri"; rd.font.size=Pt(8); rd.font.color.rgb=MID_GREY
    doc.save(bio); return bio.getvalue()

def export_txt(text: str, title: str = "LexiAssist Analysis") -> str:
    firm   = get_firm_name()
    profile = st.session_state.get("profile", {})
    lawyer = profile.get("lawyer_name", "")
    nba_no = profile.get("nba_enroll", "")
    nba_branch = profile.get("nba_branch", "")
    nba_line = ""
    if lawyer:
        nba_line = f"Counsel: {lawyer}"
        if nba_no:
            nba_line += f"  |  SCN Enroll. No: {nba_no}"
        if nba_branch:
            nba_line += f"  |  NBA {nba_branch} Branch"
        nba_line += "\n"
    header = (
        f"{'=' * 70}\n"
        f"STRICTLY PRIVATE & CONFIDENTIAL - ATTORNEY WORK PRODUCT\n"
        f"{'=' * 70}\n\n"
        f"{title.upper()}\n"
        f"{'-' * len(title)}\n\n"
        f"Firm:      {firm}\n"
        f"{nba_line}"
        f"Date:      {datetime.now():%d %B %Y at %H:%M}\n"
        f"Generated: LexiAssist v{__version__}\n\n"
        f"{'=' * 70}\n\n"
    )
    footer = (
        f"\n\n{'=' * 70}\n"
        f"DISCLAIMER\n"
        f"{'-' * 70}\n"
        f"This document is an AI-generated drafting aid produced by LexiAssist\n"
        f"v{__version__}. It does NOT constitute legal advice.\n\n"
        f"All citations, authorities, limitation periods, court rules, and legal\n"
        f"conclusions MUST be independently verified before relying on this output\n"
        f"for client advice or court filings.\n\n"
        f"(c) {datetime.now().year} {firm}\n"
        f"{'=' * 70}\n"
    )
    return header + text + footer

def export_html(text: str, title: str = "LexiAssist Analysis") -> str:
    firm = get_firm_name()
    profile = st.session_state.get("profile", {})
    lawyer = profile.get("lawyer_name", "")
    nba_no = profile.get("nba_enroll", "")
    nba_branch = profile.get("nba_branch", "")
    import html as html_mod
    safe = html_mod.escape(text).replace("\n","<br>")
    meta_parts = [html_mod.escape(firm)]
    if lawyer:
        meta_parts.append(html_mod.escape(lawyer))
    if nba_no:
        meta_parts.append(f"SCN Enroll. No: {html_mod.escape(nba_no)}")
    if nba_branch:
        meta_parts.append(f"NBA {html_mod.escape(nba_branch)} Branch")
    meta_parts.append(f"Generated {datetime.now():%d %B %Y}")
    meta_parts.append(f"LexiAssist v{__version__}")
    meta_str = " &middot; ".join(meta_parts)
    return (f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<title>{html_mod.escape(title)}</title>"
            f"<style>"
            f"body{{font-family:'Calibri','Segoe UI',Arial,sans-serif;max-width:900px;"
            f"margin:2rem auto;padding:0 1.5rem;color:#1a2e4a;line-height:1.6;"
            f"background:#ffffff;}}"
            f"h1{{color:#1a2e4a;border-bottom:3px solid #c9a84c;padding-bottom:.5rem;"
            f"font-size:1.6rem;margin-top:0;}}"
            f".confidential{{background:#fef2f2;border:1px solid #dc2626;"
            f"border-radius:4px;padding:0.5rem 1rem;text-align:center;"
            f"font-size:0.8rem;font-weight:700;color:#991b1b;margin-bottom:1.5rem;"
            f"text-transform:uppercase;letter-spacing:0.05em;}}"
            f".meta{{color:#6b7280;font-size:.85rem;margin-bottom:1.5rem;"
            f"padding-bottom:0.8rem;border-bottom:1px solid #e5e7eb;}}"
            f".body{{line-height:1.8;white-space:pre-wrap;font-size:0.95rem;}}"
            f".footer{{margin-top:2rem;padding-top:1rem;border-top:2px solid #1a2e4a;"
            f"color:#6b7280;font-size:.78rem;}}"
            f".footer strong{{color:#dc2626;}}"
            f"@media print{{body{{margin:0;padding:1cm;}} .confidential{{border:2px solid #000;}}}}"
            f"</style></head>"
            f"<body>"
            f"<div class='confidential'>Strictly Private &amp; Confidential &mdash; "
            f"Attorney Work Product</div>"
            f"<h1>{html_mod.escape(title)}</h1>"
            f"<div class='meta'>{meta_str}</div>"
            f"<div class='body'>{safe}</div>"
            f"<div class='footer'>"
            f"<strong>\u26a0 IMPORTANT:</strong> AI-generated via LexiAssist v{__version__}. "
            f"This document is a drafting aid only and does NOT constitute legal advice. "
            f"Verify all citations, authorities, and legal conclusions independently before "
            f"relying on this output for client advice or court filings.<br><br>"
            f"&copy; {datetime.now().year} {html_mod.escape(firm)}"
            f"</div></body></html>")

def safe_pdf_download(text: str, title: str, fname: str, key: str):
    """Render a PDF download button with VISIBLE error reporting on failure.

    Previously, any PDF generation error was silently logged and the user
    saw a greyed-out 'PDF (unavailable)' button with no explanation. Now
    we surface the error inline and offer a TXT fallback so the user is
    never stuck.
    """
    try:
        pdf_data = export_pdf(text, title)
        if pdf_data and pdf_data[:5] == b"%PDF-":
            st.download_button(
                "📥 PDF", data=pdf_data, file_name=f"{fname}.pdf",
                mime="application/pdf", key=key, use_container_width=True,
            )
        else:
            # export_pdf returned the "fpdf2 missing" placeholder bytes
            st.button("📥 PDF (fpdf2 not installed)", disabled=True,
                      key=key, use_container_width=True)
            st.caption("ℹ️ Install `fpdf2` to enable PDF exports — TXT/DOCX still work.")
    except Exception as e:
        # Don't hide the bug — show it AND offer a TXT fallback in its place.
        st.button("📥 PDF (failed)", disabled=True, key=key,
                  use_container_width=True)
        st.caption(f"⚠️ PDF generation failed: {e}")
        try:
            st.download_button(
                "📥 TXT (fallback)", data=export_txt(text, title),
                file_name=f"{fname}.txt", mime="text/plain",
                key=f"{key}_txt_fallback", use_container_width=True,
            )
        except Exception:
            pass
        logger.warning(f"PDF export failed: {e}")

def safe_docx_download(text: str, title: str, fname: str, key: str,
                        doc_type: str = "general", meta: dict = None):
    try:
        docx_data = export_docx(text, title, doc_type=doc_type, meta=meta or {})
        st.download_button("📥 DOCX", data=docx_data, file_name=f"{fname}.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           key=key, use_container_width=True)
    except Exception as e:
        st.button("📥 DOCX (unavailable)", disabled=True, key=key, use_container_width=True)
        st.caption(f"⚠️ DOCX generation failed: {e}")
        logger.warning(f"DOCX export failed: {e}")
