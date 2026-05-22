"""LexiAssist theme system — colour palettes, plotly colour helpers, and
the big CSS string returned by ``get_theme_css()``.
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════
# THEMES (CSS)
# ═══════════════════════════════════════════════════════
THEMES = {
    "⚖️ Corporate": {
        "display_name": "⚖️ Corporate",
        "description": "Deep navy & gold — professional law firm portal.",
        "bg":               "#f4f6f9",
        "bg_secondary":     "#e8edf4",
        "card_bg":          "#ffffff",
        "border":           "#c5d0e0",
        "text":             "#1a2e4a",
        "text_secondary":   "#4a6080",
        "accent":           "#1a2e4a",
        "accent_secondary": "#c9a84c",
        "positive":         "#059669",
        "negative":         "#dc2626",
        "warning":          "#d97706",
        "sidebar_bg":       "#1a2e4a",
        "input_bg":         "#ffffff",
        "header_gradient":  "linear-gradient(135deg, #1a2e4a, #2d4a6e)",
    },
    "🌿 Emerald": {
        "display_name": "🌿 Emerald",
        "description": "Fresh greens — calm and focused.",
        "bg":               "#f8faf9",
        "bg_secondary":     "#edf7f2",
        "card_bg":          "#ffffff",
        "border":           "#a7d4bc",
        "text":             "#1e293b",
        "text_secondary":   "#3d6b54",
        "accent":           "#047857",
        "accent_secondary": "#0d9488",
        "positive":         "#10b981",
        "negative":         "#dc2626",
        "warning":          "#d97706",
        "sidebar_bg":       "#064e3b",
        "input_bg":         "#ffffff",
        "header_gradient":  "linear-gradient(135deg, #059669, #0d9488)",
    },
    "🌊 Deep Ocean": {
        "display_name": "🌊 Deep Ocean",
        "description": "Calm deep blues — focused and serene.",
        "bg":               "#0B1120",
        "bg_secondary":     "#111B2E",
        "card_bg":          "#14203A",
        "border":           "#1E3A5F",
        "text":             "#E0E7FF",
        "text_secondary":   "#8899BB",
        "accent":           "#64FFDA",
        "accent_secondary": "#7BDFF2",
        "positive":         "#52D68A",
        "negative":         "#FF7675",
        "warning":          "#FFD93D",
        "sidebar_bg":       "#0D1526",
        "input_bg":         "#162040",
        "header_gradient":  "linear-gradient(135deg, #0D1526, #1E3A5F)",
    },
    "🌙 Midnight": {
        "display_name": "🌙 Midnight",
        "description": "Deep purples — contemplative and restful.",
        "bg":               "#0D0B1A",
        "bg_secondary":     "#131024",
        "card_bg":          "#1A1530",
        "border":           "#2E2660",
        "text":             "#E0DCFF",
        "text_secondary":   "#9990CC",
        "accent":           "#A29BFE",
        "accent_secondary": "#C4B5FD",
        "positive":         "#6BCB77",
        "negative":         "#FF6B6B",
        "warning":          "#FFD93D",
        "sidebar_bg":       "#0A0818",
        "input_bg":         "#1E1838",
        "header_gradient":  "linear-gradient(135deg, #0A0818, #2E2660)",
    },
    "🔥 Ember": {
        "display_name": "🔥 Ember",
        "description": "Dark with warm amber — bold and intense.",
        "bg":               "#1A1210",
        "bg_secondary":     "#221812",
        "card_bg":          "#2A1E18",
        "border":           "#5C3D2E",
        "text":             "#FFE4CC",
        "text_secondary":   "#C4977A",
        "accent":           "#FF9800",
        "accent_secondary": "#FFB74D",
        "positive":         "#66BB6A",
        "negative":         "#EF5350",
        "warning":          "#FFD54F",
        "sidebar_bg":       "#16100C",
        "input_bg":         "#30241C",
        "header_gradient":  "linear-gradient(135deg, #16100C, #5C3D2E)",
    },
    "💜 Lavender": {
        "display_name": "💜 Lavender",
        "description": "Soft purples — soothing and creative.",
        "bg":               "#14101A",
        "bg_secondary":     "#1C1626",
        "card_bg":          "#221C30",
        "border":           "#3D3060",
        "text":             "#E8E0F0",
        "text_secondary":   "#A898C8",
        "accent":           "#B388FF",
        "accent_secondary": "#CE93D8",
        "positive":         "#69F0AE",
        "negative":         "#FF8A80",
        "warning":          "#FFE57F",
        "sidebar_bg":       "#110D16",
        "input_bg":         "#281E3A",
        "header_gradient":  "linear-gradient(135deg, #110D16, #3D3060)",
    },
    "☁️ Cloud": {
        "display_name": "☁️ Cloud",
        "description": "Light grays and sky blues — clean and airy.",
        "bg":               "#F5F7FA",
        "bg_secondary":     "#E8ECF1",
        "card_bg":          "#FFFFFF",
        "border":           "#D1D9E6",
        "text":             "#1a202c",
        "text_secondary":   "#4a5568",
        "accent":           "#2563EB",
        "accent_secondary": "#3B82F6",
        "positive":         "#48BB78",
        "negative":         "#FC8181",
        "warning":          "#ECC94B",
        "sidebar_bg":       "#2D3748",
        "input_bg":         "#FFFFFF",
        "header_gradient":  "linear-gradient(135deg, #2D3748, #4299E1)",
    },
    "🌅 Sunset": {
        "display_name": "🌅 Sunset",
        "description": "Warm oranges and ambers — vibrant and expressive.",
        "bg":               "#1A100D",
        "bg_secondary":     "#221610",
        "card_bg":          "#2C1D16",
        "border":           "#6B3A28",
        "text":             "#FFE8D6",
        "text_secondary":   "#C49A7E",
        "accent":           "#FF6B35",
        "accent_secondary": "#FF9F1C",
        "positive":         "#7DCE82",
        "negative":         "#FF4757",
        "warning":          "#FFBE0B",
        "sidebar_bg":       "#15100A",
        "input_bg":         "#30221A",
       "header_gradient":  "linear-gradient(135deg, #15100A, #6B3A28)",
    },
    # ── NEW THEMES (from MindMirror theme engine) ──────────────────────
    "🌸 Cherry Blossom": {
        "display_name": "🌸 Cherry Blossom",
        "description": "Soft pinks and warm whites — gentle and warm.",
        "bg":               "#1A1215",
        "bg_secondary":     "#221A1E",
        "card_bg":          "#2A1F24",
        "border":           "#5C3A47",
        "text":             "#FFE4EC",
        "text_secondary":   "#C9929F",
        "accent":           "#FF8FAB",
        "accent_secondary": "#FFB3C6",
        "positive":         "#A8E6CF",
        "negative":         "#FF6B6B",
        "warning":          "#FFE66D",
        "sidebar_bg":       "#150E12",
        "input_bg":         "#2E2228",
        "header_gradient":  "linear-gradient(135deg, #150E12, #5C3A47)",
    },
    "🌲 Forest": {
        "display_name": "🌲 Forest",
        "description": "Earthy greens and browns — grounded and natural.",
        "bg":               "#0E1A0E",
        "bg_secondary":     "#142014",
        "card_bg":          "#1A2B1A",
        "border":           "#2E5E2E",
        "text":             "#D4E8D4",
        "text_secondary":   "#88AA88",
        "accent":           "#4CAF50",
        "accent_secondary": "#81C784",
        "positive":         "#66BB6A",
        "negative":         "#EF5350",
        "warning":          "#FFC107",
        "sidebar_bg":       "#0B140B",
        "input_bg":         "#1E301E",
        "header_gradient":  "linear-gradient(135deg, #0B140B, #2E5E2E)",
    },
}

THEME_NAMES = list(THEMES.keys()) 


def get_theme(name: str) -> dict:
    return THEMES.get(name, THEMES["⚖️ Corporate"])


def get_plotly_colors(name: str) -> dict:
    """Return Plotly-compatible colour config matching the active theme."""
    t = get_theme(name)
    return {
        "paper":  t["card_bg"],
        "text":   t["text"],
        "grid":   t["border"],
        "accent": t["accent"],
        "colors": [
            t["accent"], t["accent_secondary"], t["positive"],
            t["negative"], t["warning"], t["text_secondary"],
            "#FF6B6B", "#48DBFB", "#FECA57", "#FF9FF3",
        ],
    }


def get_theme_recommendation(avg_sentiment: float):
    """Suggest themes by mood/sentiment score. avg_sentiment in range [-1, 1]."""
    if avg_sentiment > 0.3:
        return ["🌅 Sunset", "🌸 Cherry Blossom", "🔥 Ember"]
    elif avg_sentiment > 0.0:
        return ["🌊 Deep Ocean", "☁️ Cloud", "🌲 Forest"]
    elif avg_sentiment > -0.3:
        return ["💜 Lavender", "🌙 Midnight", "🌊 Deep Ocean"]
    else:
        return ["🌙 Midnight", "💜 Lavender", "🌲 Forest"]


def get_theme_css(
    theme_name: str,
    font_size_scale: float = 1.0,
    high_contrast: bool = False,
    reduce_motion: bool = False,
) -> str:
    t = get_theme(theme_name)

    text_color = "#362E2EFF" if high_contrast else t["text"]
    text_sec   = "#CCCCCC" if high_contrast else t["text_secondary"]
    bg_color   = "#000000" if (high_contrast and int(t["bg"][1:3], 16) < 0x33) else t["bg"]
    base_font  = round(16 * font_size_scale, 1)
    input_font = round(base_font * 0.94, 1)
    mobile_font = round(base_font * 0.92, 1)

    is_light        = int(t["card_bg"].lstrip("#")[0:2], 16) >= 0x77
    is_dark_sidebar = int(t["sidebar_bg"].lstrip("#")[0:2], 16) < 0x44

    if is_light:
        shadow_card  = "0 1px 3px rgba(0,0,0,0.05),0 2px 10px rgba(0,0,0,0.06)"
        shadow_hover = "0 4px 20px rgba(0,0,0,0.09),0 2px 8px rgba(0,0,0,0.05)"
    else:
        shadow_card  = f"0 0 0 1px {t['border']}"
        shadow_hover = f"0 0 0 1px {t['accent']}55"

    sb_text     = "#e6edf8" if is_dark_sidebar else t["text"]
    sb_text_2   = "#8fa5c8" if is_dark_sidebar else t["text_secondary"]
    sb_line     = "rgba(255,255,255,0.08)" if is_dark_sidebar else t["border"]
    sb_input_bg = t["input_bg"]
    sb_input_tx = t["text"]
    sb_hover_bg = "rgba(255,255,255,0.06)" if is_dark_sidebar else t["bg_secondary"]

    badge_ok_bg   = "#dcfce7" if is_light else "#14532d55"
    badge_ok_tx   = "#15803d" if is_light else "#4ade80"
    badge_warn_bg = "#fef9c3" if is_light else "#71360055"
    badge_warn_tx = "#854d0e" if is_light else "#facc15"
    badge_err_bg  = "#fee2e2" if is_light else "#7f1d1d55"
    badge_err_tx  = "#b91c1c" if is_light else "#f87171"
    badge_inf_bg  = f"{t['accent']}18"
    badge_inf_tx  = t["accent"]

    ph_col      = "rgba(30,46,80,0.40)" if is_light else "rgba(200,215,240,0.35)"
    disc_bg     = t["warning"] + ("15" if is_light else "20")
    disc_tx     = "#78350f" if is_light else text_sec

    motion_css = ""
    if reduce_motion:
        motion_css = "*, *::before, *::after { animation-duration:0.01ms!important; transition-duration:0.01ms!important; }"

    acc = t["accent"]
    acc2 = t["accent_secondary"]
    warn = t["warning"]
    pos = t["positive"]
    border = t["border"]
    card = t["card_bg"]
    bg2 = t["bg_secondary"]
    inp = t["input_bg"]
    grad = t["header_gradient"]
    sidebar_bg = t["sidebar_bg"]

    return f"""<style>
/* ── Google Fonts — loaded inside style tag (no external link tags) ── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block');

/* ── Custom properties ── */
:root {{
  --la-bg:{bg_color};--la-bg2:{bg2};--la-card:{card};--la-border:{border};
  --la-text:{text_color};--la-text2:{text_sec};
  --la-acc:{acc};--la-acc2:{acc2};--la-pos:{pos};--la-neg:{t['negative']};--la-warn:{warn};
  --la-input:{inp};--la-sidebar:{sidebar_bg};
  --r-xs:4px;--r-sm:6px;--r-md:10px;--r-lg:14px;--r-xl:18px;--r-2xl:24px;--r-pill:999px;
  --ease:cubic-bezier(.4,0,.2,1);--ease-out:cubic-bezier(0,0,.2,1);
  --tf:.12s var(--ease);--tb:.18s var(--ease);--ts:.28s var(--ease);
  --font:'Plus Jakarta Sans',-apple-system,BlinkMacSystemFont,'SF Pro Display','Segoe UI Variable Display','Segoe UI',system-ui,sans-serif;
  --mono:'JetBrains Mono','Fira Code','Cascadia Code','SF Mono',Consolas,monospace;
  --sh-card:{shadow_card};--sh-hover:{shadow_hover};
}}

/* ── Reduce motion ── */
{motion_css}

/* ── Global ── */
.stApp{{background:var(--la-bg)!important;color:var(--la-text)!important;
  font-family:var(--font)!important;font-size:{base_font}px!important;
  font-feature-settings:"kern" 1,"liga" 1,"calt" 1!important;
  -webkit-font-smoothing:antialiased!important;-moz-osx-font-smoothing:grayscale!important;
  text-rendering:optimizeLegibility!important;}}

/* ── Universal text sharpening ── */
p,li,td,th,caption,figcaption,label,div,
.stMarkdown,.stMarkdown p,.stMarkdown li,.stMarkdown span,
[data-testid="stMarkdownContainer"] *,[data-testid="stText"],[data-testid="stCaptionContainer"],
.stRadio label,.stRadio div,.stCheckbox label,.stCheckbox div,
.stSelectbox label,.stMultiSelect label,.stTextInput label,.stTextArea label,
.stNumberInput label,.stDateInput label,.stSlider label,
.stFileUploader label,.stFileUploader span,.stExpander label,.stExpander p{{
  color:var(--la-text)!important;-webkit-font-smoothing:antialiased!important;
  -moz-osx-font-smoothing:grayscale!important;font-family:var(--font)!important;}}
.stCaption,[data-testid="stCaptionContainer"] p,small,.stHelp{{
  color:var(--la-text2)!important;-webkit-font-smoothing:antialiased!important;}}

/* ── CRITICAL: Restore Material Symbols font for ALL Streamlit icon spans ── */
/* Without this, icon ligatures like arrow_right show as raw text */
span.material-symbols-rounded,
span.material-symbols-outlined,
span.material-symbols-sharp,
span.material-icons,
span.material-icons-outlined,
span.material-icons-round,
span.material-icons-sharp,
[class*="material-symbols"],
[class*="material-icons"],
.stButton>button span[class*="material"],
.stDownloadButton>button span[class*="material"],
.stFormSubmitButton>button span[class*="material"],
button span[class*="material"],
[data-testid="stSidebarCollapsedControl"] span,
[data-testid="stSidebarCollapseButton"] span,
[data-testid="stExpander"] summary span[class*="material"],
[data-testid="stBaseButton-header"] span[class*="material"],
section[data-testid="stSidebar"] button span{{
  font-family:'Material Symbols Rounded','Material Icons','Material Icons Outlined',
    'Material Icons Round','Material Icons Sharp' !important;
  font-feature-settings:'liga' 1 !important;
  -webkit-font-feature-settings:'liga' 1 !important;
  font-variation-settings:'FILL' 0,'wght' 400,'GRAD' 0,'opsz' 24 !important;
  font-style:normal !important;
  display:inline-block !important;
  white-space:nowrap !important;
  letter-spacing:normal !important;
  text-transform:none !important;
  word-wrap:normal !important;
  direction:ltr !important;
  -webkit-font-smoothing:antialiased !important;}}

/* ── Headings ── */
h1,h2,h3,h4,h5,h6,
.stMarkdown h1,.stMarkdown h2,.stMarkdown h3,.stMarkdown h4,.stMarkdown h5,.stMarkdown h6{{
  color:var(--la-text)!important;font-family:var(--font)!important;
  letter-spacing:-0.025em!important;line-height:1.2!important;
  -webkit-font-smoothing:antialiased!important;}}
.stMarkdown h1{{font-size:1.75rem!important;font-weight:800!important;}}
.stMarkdown h2{{font-size:1.35rem!important;font-weight:700!important;}}
.stMarkdown h3{{font-size:1.1rem!important;font-weight:600!important;}}
.stMarkdown h4{{font-size:0.95rem!important;font-weight:600!important;}}
code,pre,.stMarkdown code,.stMarkdown pre{{
  font-family:var(--mono)!important;font-size:0.88em!important;
  -webkit-font-smoothing:antialiased!important;}}

/* ── Hero ── */
.hero,.hero *,.hero h1,.hero h2,.hero p,.hero span,.hero label{{
  color:#fff!important;-webkit-font-smoothing:antialiased!important;}}
.hero{{background:{grad};padding:2.4rem 2.6rem 2.2rem;border-radius:var(--r-xl);
  margin-bottom:1.8rem;border:1px solid rgba(255,255,255,0.08);
  position:relative;overflow:hidden;}}
.hero::before{{content:'';position:absolute;inset:0;
  background:repeating-linear-gradient(-45deg,transparent,transparent 40px,
  rgba(255,255,255,0.015) 40px,rgba(255,255,255,0.015) 41px);pointer-events:none;}}
.hero::after{{content:'\2696';position:absolute;right:1.5rem;top:50%;
  transform:translateY(-50%);font-size:11rem;line-height:1;opacity:0.08;
  pointer-events:none;user-select:none;color:#fff;filter:blur(0.5px);}}
.hero h1{{font-size:3.1rem!important;font-weight:900!important;
  letter-spacing:-0.045em!important;margin:0!important;line-height:1.05!important;}}
.hero p{{font-size:1rem!important;opacity:.85;margin:.55rem 0 0 0!important;
  font-weight:400!important;line-height:1.55!important;letter-spacing:.005em!important;}}

/* ── Page sub-header ── */
.page-header,.page-header *,.page-header h2,.page-header p{{
  color:#fff!important;-webkit-font-smoothing:antialiased!important;}}
.page-header{{background:{grad};padding:1.3rem 1.8rem 1.2rem;border-radius:var(--r-lg);
  margin-bottom:1.5rem;border:1px solid rgba(255,255,255,0.07);}}
.page-header h2{{margin:0!important;font-size:1.4rem!important;font-weight:700!important;
  letter-spacing:-0.025em!important;}}
.page-header p{{margin:.3rem 0 0 0!important;opacity:.82;font-size:.9rem!important;
  letter-spacing:.005em!important;font-weight:400!important;}}

/* ── Sidebar ── */
section[data-testid="stSidebar"]{{
  background:{sidebar_bg}!important;border-right:1px solid {sb_line}!important;}}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] li,
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stText"],
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] .stCheckbox label,
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stSlider label{{
  color:{sb_text}!important;-webkit-font-smoothing:antialiased!important;}}
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p{{
  color:{sb_text_2}!important;font-size:.75rem!important;
  -webkit-font-smoothing:antialiased!important;}}
section[data-testid="stSidebar"] hr{{
  border-color:{sb_line}!important;margin:.5rem 0!important;}}
section[data-testid="stSidebar"] .stTextInput input,
section[data-testid="stSidebar"] .stTextArea textarea,
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] *,
section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] *,
section[data-testid="stSidebar"] .stNumberInput input{{
  color:{sb_input_tx}!important;background-color:{sb_input_bg}!important;
  -webkit-font-smoothing:antialiased!important;}}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] section p,
section[data-testid="stSidebar"] [data-testid="stFileUploader"] section span,
section[data-testid="stSidebar"] [data-testid="stFileDropzoneInstructions"],
section[data-testid="stSidebar"] [data-testid="stFileDropzoneInstructions"] span{{
  color:{sb_input_tx}!important;}}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] small,
section[data-testid="stSidebar"] .stCaption p{{color:{sb_text_2}!important;}}
section[data-testid="stSidebar"] .stButton>button{{
  background:{sb_hover_bg}!important;border:1px solid {sb_line}!important;
  color:{sb_text}!important;border-radius:var(--r-md)!important;
  font-weight:500!important;transition:var(--tb)!important;}}
section[data-testid="stSidebar"] .stButton>button:hover{{
  background:{acc}22!important;border-color:{acc}55!important;}}

/* ── Sidebar collapse/expand toggle arrow (all Streamlit versions) ── */
/* CRITICAL: must sit ABOVE the white header bar AND above the sidebar itself
   when sidebar is open on mobile, so the close arrow is always reachable */
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"]{{
  background:transparent!important;
  border:none!important;
  display:flex!important;align-items:center!important;justify-content:center!important;
  visibility:visible!important;opacity:1!important;
  z-index:9999999!important;
  position:fixed!important;
  top:0.5rem!important;
  left:0.5rem!important;
  pointer-events:auto!important;}}

/* The IN-SIDEBAR collapse button — must float ABOVE sidebar content
   especially on mobile where sidebar takes full width */
[data-testid="stSidebarCollapseButton"],
section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"],
section[data-testid="stSidebar"] button[kind="header"]{{
  position:absolute!important;
  top:0.5rem!important;
  right:0.5rem!important;
  z-index:9999999!important;
  background:rgba(255,255,255,0.15)!important;
  border:1px solid rgba(255,255,255,0.25)!important;
  border-radius:50%!important;
  width:2.2rem!important;
  height:2.2rem!important;
  min-width:2.2rem!important;
  display:flex!important;align-items:center!important;justify-content:center!important;
  visibility:visible!important;opacity:1!important;
  pointer-events:auto!important;
  cursor:pointer!important;
  backdrop-filter:blur(4px);
  -webkit-backdrop-filter:blur(4px);}}

[data-testid="stSidebarCollapseButton"]:hover,
section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"]:hover{{
  background:rgba(255,255,255,0.28)!important;
  border-color:rgba(255,255,255,0.4)!important;}}

[data-testid="stSidebarCollapseButton"] svg,
section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] svg{{
  width:1.1rem!important;height:1.1rem!important;
  fill:#ffffff!important;color:#ffffff!important;
  visibility:visible!important;opacity:1!important;}}

/* Force Streamlit's top header bar (the white tile) to be transparent
   so it never covers the sidebar toggle */
[data-testid="stHeader"],
header[data-testid="stHeader"],
div[data-testid="stHeader"]{{
  background:transparent!important;
  background-color:transparent!important;
  height:auto!important;
  z-index:1!important;}}

/* Also kill any decoration bar that overlaps the toggle */
[data-testid="stDecoration"]{{
  display:none!important;}}

/* ── MOBILE-SPECIFIC sidebar fixes ── */
@media (max-width:768px){{
  /* When sidebar is open on mobile, ensure close button is reachable */
  section[data-testid="stSidebar"][aria-expanded="true"]{{
    width:85vw!important;
    min-width:280px!important;
    max-width:340px!important;}}
  /* Push sidebar contents down to make room for close button */
  section[data-testid="stSidebar"] > div:first-child{{
    padding-top:3rem!important;}}
  /* Make close button bigger and easier to tap on mobile */
  [data-testid="stSidebarCollapseButton"],
  section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"]{{
    width:2.6rem!important;
    height:2.6rem!important;
    min-width:2.6rem!important;
    top:0.6rem!important;
    right:0.6rem!important;}}
  [data-testid="stSidebarCollapseButton"] svg{{
    width:1.3rem!important;height:1.3rem!important;}}
}}


[data-testid="stSidebarCollapsedControl"] button,
[data-testid="collapsedControl"] button,
[data-testid="stSidebarCollapseButton"] button,
button[data-testid="stSidebarCollapseButton"],
button[data-testid="stBaseButton-header"]{{
  background:{sb_hover_bg}!important;border:1px solid {sb_line}!important;
  border-radius:var(--r-md)!important;color:{sb_text}!important;
  visibility:visible!important;opacity:1!important;
  width:2rem!important;height:2rem!important;min-width:2rem!important;
  display:flex!important;align-items:center!important;justify-content:center!important;
  padding:0!important;}}
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="collapsedControl"] svg,
[data-testid="stSidebarCollapseButton"] svg,
button[data-testid="stSidebarCollapseButton"] svg,
button[data-testid="stBaseButton-header"] svg,
section[data-testid="stSidebar"] [data-testid="stBaseButton-header"] svg,
section[data-testid="stSidebar"] button[kind="header"] svg,
section[data-testid="stSidebar"] > div > div > div > button svg{{
  fill:{sb_text}!important;stroke:{sb_text}!important;color:{sb_text}!important;
  background:transparent!important;visibility:visible!important;
  opacity:1!important;display:block!important;width:1.1rem!important;height:1.1rem!important;}}

/* ── Buttons ── */
.stButton>button{{
  -webkit-font-smoothing:antialiased!important;border-radius:var(--r-md)!important;
  font-weight:500!important;letter-spacing:.005em!important;
  transition:var(--tb)!important;transform:translateZ(0);}}
/* Button label text (not the icon span) */
.stButton>button p,
.stButton>button div:not([class*="material"]):not([class*="icon"]),
.stDownloadButton>button p{{
  font-family:var(--font)!important;-webkit-font-smoothing:antialiased!important;}}
.stButton>button[kind="primary"],
.stButton>button[data-testid="baseButton-primary"]{{
  background:{acc}!important;color:#fff!important;border:none!important;
  box-shadow:0 1px 3px {acc}55,0 2px 10px {acc}22!important;font-weight:600!important;}}
.stButton>button[kind="primary"]:hover,
.stButton>button[data-testid="baseButton-primary"]:hover{{
  filter:brightness(1.1)!important;
  box-shadow:0 2px 8px {acc}66,0 4px 18px {acc}33!important;
  transform:translateY(-1px)!important;}}
.stButton>button[kind="primary"]:active,
.stButton>button[data-testid="baseButton-primary"]:active{{
  filter:brightness(.97)!important;transform:translateY(0)!important;
  box-shadow:0 1px 3px {acc}44!important;}}
.stButton>button[kind="secondary"],
.stButton>button[data-testid="baseButton-secondary"]{{
  background:transparent!important;color:var(--la-text)!important;
  border:1px solid var(--la-border)!important;font-weight:500!important;}}
.stButton>button[kind="secondary"]:hover,
.stButton>button[data-testid="baseButton-secondary"]:hover{{
  background:var(--la-bg2)!important;border-color:{acc}66!important;
  color:var(--la-acc)!important;}}
.stButton>button:not([kind]){{
  background:transparent!important;color:var(--la-text)!important;
  border:1px solid var(--la-border)!important;}}
.stButton>button:focus:not(:active){{
  box-shadow:0 0 0 3px {acc}33!important;outline:none!important;}}
.stDownloadButton>button{{
  background:var(--la-bg2)!important;color:var(--la-text)!important;
  border:1px solid var(--la-border)!important;border-radius:var(--r-md)!important;
  font-family:var(--font)!important;font-weight:500!important;
  transition:var(--tb)!important;-webkit-font-smoothing:antialiased!important;}}
.stDownloadButton>button:hover{{
  border-color:var(--la-acc)!important;color:var(--la-acc)!important;}}

/* ── Inputs ── */
.stTextInput input,.stTextArea textarea,.stNumberInput input,.stDateInput input{{
  background-color:var(--la-input)!important;color:var(--la-text)!important;
  border:1px solid var(--la-border)!important;border-radius:var(--r-md)!important;
  font-family:var(--font)!important;font-size:{input_font}px!important;
  -webkit-font-smoothing:antialiased!important;
  transition:border-color var(--tf),box-shadow var(--tf)!important;
  padding:.45rem .8rem!important;}}
.stTextInput input:focus,.stTextArea textarea:focus,.stNumberInput input:focus{{
  border-color:var(--la-acc)!important;
  box-shadow:0 0 0 3px {acc}25!important;outline:none!important;}}
.stTextInput>label,.stTextArea>label,.stSelectbox>label,
.stNumberInput>label,.stMultiSelect>label,.stDateInput>label,
.stSlider>label,.stFileUploader>label{{
  color:var(--la-text)!important;font-weight:500!important;
  font-size:.86rem!important;letter-spacing:.01em!important;
  -webkit-font-smoothing:antialiased!important;}}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{{
  color:{ph_col}!important;opacity:1!important;font-style:italic!important;}}
section[data-testid="stSidebar"] .stTextInput input::placeholder,
section[data-testid="stSidebar"] .stTextArea textarea::placeholder{{
  color:{ph_col}!important;opacity:1!important;font-style:italic!important;}}
/* ── Selectbox & MultiSelect — full value visibility fix ── */
.stSelectbox div[data-baseweb="select"]>div,
.stMultiSelect div[data-baseweb="select"]>div{{
  background-color:var(--la-input)!important;
  border-color:var(--la-border)!important;border-radius:var(--r-md)!important;}}
/* Selected value text, placeholder text, typed input */
.stSelectbox div[data-baseweb="select"] [class*="singleValue"],
.stSelectbox div[data-baseweb="select"] [class*="SingleValue"],
.stSelectbox div[data-baseweb="select"] [class*="placeholder"],
.stSelectbox div[data-baseweb="select"] [class*="Placeholder"],
.stSelectbox div[data-baseweb="select"] input,
.stMultiSelect div[data-baseweb="select"] [class*="singleValue"],
.stMultiSelect div[data-baseweb="select"] [class*="SingleValue"],
.stMultiSelect div[data-baseweb="select"] [class*="placeholder"],
.stMultiSelect div[data-baseweb="select"] input,
.stMultiSelect div[data-baseweb="select"] [data-baseweb="tag"],
.stMultiSelect div[data-baseweb="select"] [data-baseweb="tag"] span{{
  color:var(--la-text)!important;background-color:transparent!important;
  font-family:var(--font)!important;-webkit-font-smoothing:antialiased!important;}}
/* Value container wrapper */
.stSelectbox div[data-baseweb="select"] [class*="ValueContainer"],
.stMultiSelect div[data-baseweb="select"] [class*="ValueContainer"]{{
  background-color:transparent!important;}}
/* Arrow/chevron SVG icon */
.stSelectbox div[data-baseweb="select"] svg,
.stMultiSelect div[data-baseweb="select"] svg{{
  fill:var(--la-text)!important;color:var(--la-text)!important;
  background-color:transparent!important;display:block!important;
  visibility:visible!important;opacity:1!important;}}
/* Dropdown open — option list */
[data-baseweb="menu"],[data-baseweb="menu"] ul,[data-baseweb="popover"]{{
  background-color:var(--la-card)!important;}}
[data-baseweb="menu"] li,[data-baseweb="popover"] li,
[data-baseweb="menu"] [role="option"],[data-baseweb="popover"] [role="option"]{{
  background-color:var(--la-card)!important;color:var(--la-text)!important;
  font-family:var(--font)!important;-webkit-font-smoothing:antialiased!important;}}
[data-baseweb="menu"] li:hover,[data-baseweb="popover"] li:hover,
[data-baseweb="menu"] [role="option"]:hover{{
  background-color:{acc}18!important;color:var(--la-acc)!important;}}
/* ── CRITICAL: Dropdown HIGHLIGHTED / FOCUSED / SELECTED states ──
   BaseWeb uses [aria-selected] for the currently-selected option and
   [data-highlighted] / [aria-activedescendant] for the keyboard- or
   scroll-focused option. Without these rules the focus indicator
   defaults to white in BaseWeb's stylesheet — invisible on dark themes
   and washing out items on light themes. */
[data-baseweb="menu"] [role="option"][aria-selected="true"],
[data-baseweb="popover"] [role="option"][aria-selected="true"],
[data-baseweb="menu"] li[aria-selected="true"],
[data-baseweb="popover"] li[aria-selected="true"]{{
  background-color:{acc}28!important;
  color:var(--la-acc)!important;
  font-weight:600!important;
  border-left:3px solid var(--la-acc)!important;
  padding-left:calc(1rem - 3px)!important;}}
[data-baseweb="menu"] [role="option"][data-highlighted="true"],
[data-baseweb="popover"] [role="option"][data-highlighted="true"],
[data-baseweb="menu"] [role="option"][aria-selected="true"][data-highlighted="true"],
[data-baseweb="menu"] li[data-highlighted="true"],
[data-baseweb="popover"] li[data-highlighted="true"]{{
  background-color:{acc}38!important;
  color:var(--la-acc)!important;
  outline:none!important;}}
[data-baseweb="menu"] [role="option"]:focus,
[data-baseweb="popover"] [role="option"]:focus,
[data-baseweb="menu"] [role="option"]:focus-visible,
[data-baseweb="popover"] [role="option"]:focus-visible{{
  background-color:{acc}38!important;
  color:var(--la-acc)!important;
  outline:2px solid var(--la-acc)!important;
  outline-offset:-2px!important;}}
/* MultiSelect — highlighted option in the dropdown panel */
.stMultiSelect [data-baseweb="menu"] [role="option"][aria-selected="true"],
.stMultiSelect [data-baseweb="popover"] [role="option"][aria-selected="true"]{{
  background-color:{acc}28!important;color:var(--la-acc)!important;}}
/* Radio list item highlight (the "list of items" with focus bar) */
.stRadio [role="radiogroup"] [role="radio"][aria-checked="true"],
.stRadio [role="radiogroup"] label[data-checked="true"]{{
  background-color:{acc}18!important;
  border-left:3px solid var(--la-acc)!important;
  padding-left:calc(0.5rem - 3px)!important;
  border-radius:var(--r-sm)!important;}}
/* Streamlit's virtual list (large dropdowns) — focused row */
[data-baseweb="virtual-list"] > div > div:hover,
[data-baseweb="virtual-list"] [role="option"]:hover{{
  background-color:{acc}18!important;color:var(--la-acc)!important;}}
[data-baseweb="virtual-list"] [role="option"][aria-selected="true"],
[data-baseweb="virtual-list"] [role="option"][data-highlighted="true"]{{
  background-color:{acc}28!important;color:var(--la-acc)!important;
  font-weight:600!important;}}
/* ── File uploader — fully functional & visible on all themes ── */
/* Dropzone area */
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploader"] section{{
  background-color:var(--la-input)!important;
  border:1.5px dashed var(--la-border)!important;
  border-radius:var(--r-md)!important;
  padding:.9rem!important;
  position:relative!important;
  pointer-events:auto!important;}}
/* Instruction text — specific tags only, NO wildcard */
[data-testid="stFileDropzoneInstructions"] span,
[data-testid="stFileDropzoneInstructions"] p,
[data-testid="stFileDropzoneInstructions"] small{{
  color:var(--la-text)!important;
  background-color:transparent!important;
  -webkit-font-smoothing:antialiased!important;
  line-height:1.5!important;}}
/* Upload icon SVG */
[data-testid="stFileUploaderDropzone"] svg,
[data-testid="stFileUploader"] section svg{{
  fill:var(--la-text2)!important;color:var(--la-text2)!important;
  background:transparent!important;pointer-events:none!important;}}
/* ── Browse Files button — the actual click target ── */
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stFileUploader"] section button{{
  background-color:var(--la-bg2)!important;
  color:var(--la-text)!important;
  border:1px solid var(--la-border)!important;
  border-radius:var(--r-md)!important;
  font-family:var(--font)!important;
  font-size:.87rem!important;
  font-weight:500!important;
  padding:.4rem 1.1rem!important;
  cursor:pointer!important;
  pointer-events:none!important;
  display:inline-flex!important;
  align-items:center!important;
  -webkit-font-smoothing:antialiased!important;
  transition:background var(--tb),border-color var(--tb)!important;}}
[data-testid="stFileUploaderDropzone"] button:hover,
[data-testid="stFileUploader"] section button:hover{{
  background-color:{acc}18!important;
  border-color:{acc}88!important;
  color:var(--la-acc)!important;}}
/* Caption / size limit text */
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] .stCaption,
[data-testid="stFileUploader"] .stCaption p,
[data-testid="stFileUploader"] [data-testid="stCaptionContainer"] p{{
  color:var(--la-text2)!important;font-size:.78rem!important;
  background-color:transparent!important;}}
/* Sidebar file uploader — text colour only, no structural overrides */
section[data-testid="stSidebar"] [data-testid="stFileDropzoneInstructions"] span,
section[data-testid="stSidebar"] [data-testid="stFileDropzoneInstructions"] p,
section[data-testid="stSidebar"] [data-testid="stFileDropzoneInstructions"] small{{
  color:{sb_input_tx}!important;}}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button,
section[data-testid="stSidebar"] [data-testid="stFileUploader"] section button{{
  color:{sb_text}!important;background-color:{sb_hover_bg}!important;
  border-color:{sb_line}!important;}}
/* ── Hidden file input — must be topmost so OS file picker fires on click ── */
[data-testid="stFileUploaderDropzoneInput"],
[data-testid="stFileUploaderDropzone"] input[type="file"],
[data-testid="stFileUploader"] input[type="file"]{{
  position:absolute!important;inset:0!important;
  width:100%!important;height:100%!important;
  opacity:0!important;z-index:100!important;
  cursor:pointer!important;pointer-events:auto!important;}}
/* ── Restore Browse button appearance when uploader is inside a tab ── */
div[data-testid="stTabs"] [data-testid="stFileUploaderDropzone"] button,
div[data-testid="stTabs"] [data-testid="stFileUploader"] section button{{
  background-color:var(--la-bg2)!important;border:1px solid var(--la-border)!important;
  border-radius:var(--r-md)!important;padding:.4rem 1.1rem!important;
  pointer-events:none!important;}}
/* ── File uploader hidden input — MUST sit above the styled button (z-index:10)
   so clicks reach the real <input type="file"> and open the file dialog ── */
[data-testid="stFileUploaderDropzoneInput"]{{
  position:absolute!important;inset:0!important;
  z-index:20!important;opacity:0!important;
  cursor:pointer!important;pointer-events:auto!important;}}

/* ── Stat cards ── */
.stat-card{{background:var(--la-card);border:1px solid var(--la-border);
  border-radius:var(--r-lg);padding:1.2rem 1rem 1.1rem;text-align:center;
  box-shadow:var(--sh-card);
  transition:box-shadow var(--tb),transform var(--tb);
  position:relative;overflow:hidden;}}
.stat-card::after{{content:'';position:absolute;top:0;left:10%;right:10%;height:2px;
  background:linear-gradient(90deg,transparent,{acc}88,transparent);
  border-radius:0 0 2px 2px;}}
.stat-card .stat-value{{font-size:1.95rem!important;font-weight:800!important;
  color:var(--la-acc)!important;line-height:1!important;letter-spacing:-0.03em!important;
  -webkit-font-smoothing:antialiased!important;font-family:var(--font)!important;}}
.stat-card .stat-label{{font-size:.72rem!important;font-weight:600!important;
  color:var(--la-text2)!important;margin-top:.45rem!important;
  text-transform:uppercase!important;letter-spacing:.08em!important;
  -webkit-font-smoothing:antialiased!important;}}

/* ── Custom cards ── */
.custom-card{{background:var(--la-card);border:1px solid var(--la-border);
  border-radius:var(--r-lg);padding:1.1rem 1.35rem;margin-bottom:.7rem;
  box-shadow:var(--sh-card);
  transition:box-shadow var(--tb),border-color var(--tb),transform var(--tb);
  position:relative;}}
.custom-card::before{{content:'';position:absolute;left:0;top:20%;bottom:20%;
  width:3px;border-radius:0 2px 2px 0;background:var(--la-acc);opacity:.8;}}
.custom-card:hover{{box-shadow:var(--sh-hover)!important;
  border-color:{acc}44!important;transform:translateY(-1px);}}
.custom-card h4{{margin:0 0 .3rem 0!important;color:var(--la-text)!important;
  font-size:.93rem!important;font-weight:600!important;letter-spacing:-.01em!important;
  -webkit-font-smoothing:antialiased!important;}}
.custom-card p,.custom-card span{{color:var(--la-text)!important;}}

/* ── History / tool / login cards ── */
.history-item{{background:var(--la-card);border:1px solid var(--la-border);
  border-radius:var(--r-md);padding:.7rem 1rem;margin-bottom:.4rem;cursor:pointer;
  transition:border-color var(--tb),background var(--tb);}}
.history-item:hover{{border-color:{acc}66!important;background:var(--la-bg2)!important;}}
.tool-card{{background:var(--la-card);border:1px solid var(--la-border);
  border-radius:var(--r-md);padding:.9rem 1.1rem;margin-bottom:.5rem;}}
.login-card{{background:var(--la-card);border:1px solid var(--la-border);
  border-top:3px solid var(--la-acc);border-radius:var(--r-xl);
  padding:2.2rem 2.4rem;box-shadow:var(--sh-card);}}

/* ── AI response box ── */
.response-box{{background:var(--la-card);border:1px solid var(--la-border);
  border-radius:var(--r-lg);padding:1.8rem 2rem;
  line-height:1.78!important;font-size:{input_font}px!important;
  font-family:var(--font)!important;white-space:pre-wrap;
  color:var(--la-text)!important;-webkit-font-smoothing:antialiased!important;
  box-shadow:var(--sh-card);position:relative;}}
.response-box::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,var(--la-acc),var(--la-acc2));
  border-radius:var(--r-lg) var(--r-lg) 0 0;}}

/* ── Disclaimer ── */
.disclaimer{{background:{disc_bg};border-left:3px solid {warn};
  border-radius:0 var(--r-md) var(--r-md) 0;padding:.85rem 1.1rem;margin-top:1rem;
  font-size:.83rem!important;color:{disc_tx}!important;
  line-height:1.55!important;-webkit-font-smoothing:antialiased!important;}}

/* ── Badges ── */
.badge{{display:inline-flex;align-items:center;padding:.2rem .6rem;
  border-radius:var(--r-sm);font-size:.71rem!important;font-weight:600!important;
  letter-spacing:.04em!important;text-transform:uppercase!important;
  -webkit-font-smoothing:antialiased!important;font-family:var(--font)!important;
  white-space:nowrap;}}
.badge-ok{{background:{badge_ok_bg};color:{badge_ok_tx}!important;}}
.badge-warn{{background:{badge_warn_bg};color:{badge_warn_tx}!important;}}
.badge-err{{background:{badge_err_bg};color:{badge_err_tx}!important;}}
.badge-info{{background:{badge_inf_bg};color:{badge_inf_tx}!important;}}

/* ── Tabs ── */
div[data-testid="stTabs"] button{{font-family:var(--font)!important;
  font-weight:500!important;font-size:.86rem!important;
  color:var(--la-text2)!important;background:transparent!important;
  border:none!important;border-bottom:2px solid transparent!important;
  border-radius:0!important;padding:.55rem .9rem!important;
  transition:color var(--tb),border-color var(--tb)!important;
  -webkit-font-smoothing:antialiased!important;letter-spacing:.005em!important;}}
div[data-testid="stTabs"] button:hover{{color:var(--la-acc)!important;
  background:{acc}0d!important;border-radius:var(--r-sm) var(--r-sm) 0 0!important;}}
div[data-testid="stTabs"] button[aria-selected="true"]{{color:var(--la-acc)!important;
  font-weight:600!important;background:transparent!important;
  border-bottom:2px solid var(--la-acc)!important;}}

/* ── Expanders — fix arrow visibility + prevent text overlap ── */
.streamlit-expanderHeader,
[data-testid="stExpander"] summary,
[data-testid="stExpander"] > details > summary{{
  background:var(--la-bg2)!important;color:var(--la-text)!important;
  border-radius:var(--r-md)!important;border:1px solid var(--la-border)!important;
  font-weight:500!important;
  transition:background var(--tb),border-color var(--tb)!important;
  -webkit-font-smoothing:antialiased!important;
  display:flex!important;align-items:center!important;
  flex-direction:row!important;gap:.5rem!important;
  padding:.55rem .9rem!important;list-style:none!important;
  cursor:pointer!important;line-height:1.4!important;
  min-height:2.4rem!important;box-sizing:border-box!important;}}
/* Arrow SVG inside expander header */
.streamlit-expanderHeader svg,
[data-testid="stExpander"] summary svg,
[data-testid="stExpander"] > details > summary svg{{
  fill:var(--la-text)!important;color:var(--la-text)!important;
  min-width:1rem!important;width:1rem!important;height:1rem!important;
  flex-shrink:0!important;visibility:visible!important;
  opacity:1!important;display:inline-block!important;}}
/* Expander label text — prevent overlap */
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] > details > summary p,
.streamlit-expanderHeader p{{
  color:var(--la-text)!important;margin:0!important;padding:0!important;
  line-height:1.4!important;flex:1!important;
  -webkit-font-smoothing:antialiased!important;}}
/* Remove default browser triangle marker */
[data-testid="stExpander"] summary::-webkit-details-marker,
[data-testid="stExpander"] > details > summary::-webkit-details-marker{{display:none!important;}}
[data-testid="stExpander"] summary::marker,
[data-testid="stExpander"] > details > summary::marker{{display:none!important;}}
/* Expander hover */
.streamlit-expanderHeader:hover,
[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] > details > summary:hover{{
  background:var(--la-card)!important;border-color:{acc}55!important;}}
/* Expander body */
.streamlit-expanderContent,
[data-testid="stExpander"] details,
[data-testid="stExpander"] > details{{
  background:var(--la-card)!important;border:1px solid var(--la-border)!important;
  border-top:none!important;border-radius:0 0 var(--r-md) var(--r-md)!important;}}
/* Widgets inside expander — prevent stacking/collision */
[data-testid="stExpander"] [data-testid="stWidgetLabel"],
[data-testid="stExpander"] .stSlider,
[data-testid="stExpander"] .stCheckbox,
[data-testid="stExpander"] .stRadio{{
  margin-top:.4rem!important;margin-bottom:.4rem!important;
  display:block!important;clear:both!important;}}
[data-testid="stExpander"] [data-testid="stWidgetLabel"] p{{
  line-height:1.4!important;margin-bottom:.25rem!important;
  display:block!important;}}

/* ── Metrics ── */
[data-testid="stMetric"]{{background:var(--la-card)!important;
  border:1px solid var(--la-border)!important;border-radius:var(--r-lg)!important;
  padding:.9rem 1.1rem!important;box-shadow:var(--sh-card)!important;}}
[data-testid="stMetricLabel"] p,div[data-testid="metric-container"] label{{
  color:var(--la-text2)!important;font-size:.74rem!important;font-weight:600!important;
  text-transform:uppercase!important;letter-spacing:.07em!important;
  -webkit-font-smoothing:antialiased!important;}}
[data-testid="stMetricValue"],
div[data-testid="metric-container"] div[data-testid="stMetricValue"]{{
  color:var(--la-acc)!important;font-weight:700!important;
  letter-spacing:-.02em!important;-webkit-font-smoothing:antialiased!important;}}
[data-testid="stMetricDelta"]{{color:var(--la-pos)!important;}}

/* ── Radio & Checkbox ── */
.stRadio>div>label,.stCheckbox>label,
.stRadio [data-testid="stMarkdownContainer"] p,
.stCheckbox [data-testid="stMarkdownContainer"] p{{
  color:var(--la-text)!important;-webkit-font-smoothing:antialiased!important;}}

/* ── Dropdowns ── */
[data-baseweb="menu"],[data-baseweb="menu"] li,[data-baseweb="popover"] li{{
  background-color:var(--la-card)!important;color:var(--la-text)!important;
  font-family:var(--font)!important;-webkit-font-smoothing:antialiased!important;}}
[data-baseweb="menu"] li:hover,[data-baseweb="popover"] li:hover{{
  background-color:{acc}18!important;color:var(--la-acc)!important;}}

/* ── Progress ── */
.stProgress>div>div{{background-color:var(--la-acc)!important;}}
.stProgress{{background-color:var(--la-bg2)!important;border-radius:var(--r-pill)!important;}}

/* ── Chat ── */
[data-testid="stChatMessage"]{{background:var(--la-card)!important;
  border:1px solid var(--la-border)!important;border-radius:var(--r-lg)!important;
  margin-bottom:.6rem!important;}}
[data-testid="stChatMessage"] p{{color:var(--la-text)!important;
  -webkit-font-smoothing:antialiased!important;}}

/* ── Dataframes ── */
.stDataFrame{{border:1px solid var(--la-border)!important;
  border-radius:var(--r-md)!important;overflow:hidden!important;}}
.stDataFrame th{{background:var(--la-bg2)!important;color:var(--la-text)!important;
  font-weight:600!important;font-size:.82rem!important;letter-spacing:.03em!important;
  -webkit-font-smoothing:antialiased!important;}}
.stDataFrame td{{color:var(--la-text)!important;-webkit-font-smoothing:antialiased!important;}}


/* ── Alerts & info boxes — force background + text so dark themes don't get white boxes ── */
[data-testid="stAlert"]{{
  background-color:var(--la-card)!important;
  border-color:var(--la-border)!important;border-radius:var(--r-md)!important;}}
[data-testid="stAlert"] p,
[data-testid="stAlert"] span,
[data-testid="stAlert"] div,
[data-testid="stAlert"] li,
[data-testid="stInfo"],
[data-testid="stSuccess"],
[data-testid="stWarning"],
[data-testid="stError"]{{
  color:var(--la-text)!important;-webkit-font-smoothing:antialiased!important;}}
/* Force all Streamlit alert flavours to use card bg */
div[data-testid="stAlert"][data-baseweb="notification"],
div[class*="stAlert"]{{
  background-color:var(--la-card)!important;color:var(--la-text)!important;}}
/* Tool-card, custom info box text visibility */
.tool-card,.tool-card *,.tool-card p,.tool-card span,
.tool-card h4,.tool-card li{{
  color:var(--la-text)!important;-webkit-font-smoothing:antialiased!important;}}
/* Expander inner content text */
[data-testid="stExpander"] details *,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] li,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] span,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] h4{{
  color:var(--la-text)!important;background-color:transparent!important;
  -webkit-font-smoothing:antialiased!important;}}
/* Streamlit native info/success/warning/error notification text */
[data-testid="stNotification"] p,
[data-testid="stNotification"] span,
[data-testid="stNotification"] div{{
  color:var(--la-text)!important;-webkit-font-smoothing:antialiased!important;}}

/* ── Scrollbar ── */
::-webkit-scrollbar{{width:5px;height:5px;}}
::-webkit-scrollbar-track{{background:transparent;}}
::-webkit-scrollbar-thumb{{background:{border};border-radius:var(--r-pill);
  transition:background var(--tb);}}
::-webkit-scrollbar-thumb:hover{{background:{acc}88;}}
::selection{{background:{acc}30;color:var(--la-text);}}

/* ── Reduce-motion (prefers) ── */
@media (prefers-reduced-motion:reduce){{
  *,*::before,*::after{{animation-duration:.01ms!important;transition-duration:.01ms!important;}}}}

/* ── Mobile ── */
@media (max-width:768px){{
  .stApp{{font-size:{mobile_font}px!important;}}
  .hero{{padding:1.4rem 1.3rem!important;border-radius:var(--r-lg)!important;}}
  .hero h1{{font-size:1.9rem!important;}}
  .hero::after{{font-size:6rem!important;}}
  .hero p{{font-size:.88rem!important;}}
  .page-header{{padding:1rem 1.2rem!important;}}
  .page-header h2{{font-size:1.1rem!important;}}
  .stat-card .stat-value{{font-size:1.45rem!important;}}
  .custom-card{{padding:.75rem .9rem!important;}}
  .response-box{{padding:1rem!important;font-size:.88rem!important;}}
  .stButton>button{{width:100%!important;min-height:2.4rem!important;}}
  div[data-testid="stTabs"] button{{font-size:.72rem!important;padding:.35rem .5rem!important;}}
  .login-card{{padding:1.3rem 1rem!important;}}
  [data-testid="stMetric"]{{padding:.7rem .9rem!important;}}}}
@media (max-width:480px){{
  .hero h1{{font-size:1.6rem!important;}}
  .stat-card .stat-value{{font-size:1.15rem!important;}}
  .badge{{font-size:.64rem!important;}}}}

/* ── Streamlit 1.38+ structural fixes ── */
/* Fix column gap and alignment */
div[data-testid="stHorizontalBlock"]{{
  gap:.75rem!important;align-items:flex-start!important;}}
/* Prevent double-stacked label/widget overlap — use small gap, NOT zero */
div[data-testid="stVerticalBlock"]>div[data-testid="element-container"]{{
  margin-top:.15rem!important;margin-bottom:.15rem!important;}}
/* Stat-card markdown inside columns */
div[data-testid="stColumn"] div[data-testid="stMarkdownContainer"]{{
  margin-bottom:0!important;}}
/* Ensure button text is always on one line and not clipped */
.stButton>button,
.stDownloadButton>button,
.stFormSubmitButton>button{{
  white-space:nowrap!important;overflow:visible!important;
  text-overflow:clip!important;line-height:1.4!important;
  padding:.45rem 1rem!important;min-height:2.2rem!important;}}
/* Accessibility / settings widgets: ensure label and control don't collide */
.stSlider,
.stCheckbox,
.stRadio,
[data-testid="stWidgetLabel"]{{
  margin-bottom:.4rem!important;margin-top:.2rem!important;
  display:block!important;clear:both!important;
  position:relative!important;}}
[data-testid="stWidgetLabel"] p,
.stSlider label,
.stCheckbox label,
.stRadio label{{
  line-height:1.4!important;margin-bottom:.25rem!important;
  display:block!important;}}
/* Prevent slider track from overlapping label */
.stSlider > div {{
  margin-top:.15rem!important;}}
/* Sidebar-specific: give each widget proper breathing room */
section[data-testid="stSidebar"] .stSlider,
section[data-testid="stSidebar"] .stCheckbox,
section[data-testid="stSidebar"] .stRadio{{
  padding:.1rem 0!important;margin-bottom:.5rem!important;}}
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{{
  color:{sb_text}!important;}}
/* ── Sidebar scroll: smooth and full-height ── */
section[data-testid="stSidebar"]{{
  scroll-behavior:smooth!important;
  overflow-y:auto!important;
  overflow-x:hidden!important;
}}
section[data-testid="stSidebarContent"]{{
  scroll-behavior:smooth!important;
  overflow-y:auto!important;
  padding-bottom:3rem!important;
}}
/* ── Sidebar auto-collapse: on mobile, clicking main content closes sidebar ── */
@media (max-width: 768px){{
  /* When sidebar is open, the main block shifts right.
     Clicking the main area fires the collapse button via JS overlay. */
  .main .block-container{{
    cursor:pointer;
  }}
}}
/* ── Tab list scroll: smooth horizontal swipe ── */
div[data-testid="stTabs"] [role="tablist"]{{
  overflow-x:auto!important;
  overflow-y:hidden!important;
  flex-wrap:nowrap!important;
  -webkit-overflow-scrolling:touch!important;
  scroll-behavior:smooth!important;
  scrollbar-width:thin!important;
}}
div[data-testid="stTabs"] [role="tablist"] button{{
  flex-shrink:0!important;
  white-space:nowrap!important;
}}
/* Hide zero-height keep-alive iframe cleanly */
iframe[height="0"],iframe[style*="height: 0"]{{
  display:none!important;height:0!important;min-height:0!important;
  padding:0!important;margin:0!important;border:none!important;}}

/* ══════════════════════════════════════════════════════════════════════
   FIX: White background covering text — force all container elements
   to use theme background instead of Streamlit's default white
   ══════════════════════════════════════════════════════════════════════ */

/* Main app container and all block containers */
.stApp > header,
.stApp [data-testid="stHeader"],
.stApp > div > header {{
  background:transparent!important;
  background-color:transparent!important;}}

/* Block containers that Streamlit wraps content in */
.block-container,
[data-testid="stMainBlockContainer"],
[data-testid="block-container"],
.main .block-container {{
  background:transparent!important;
  background-color:transparent!important;}}

/* Form containers — often render with white bg */
[data-testid="stForm"],
.stForm,
form[data-testid="stForm"] {{
  background-color:var(--la-card)!important;
  border:1px solid var(--la-border)!important;
  border-radius:var(--r-lg)!important;
  padding:1rem!important;}}

/* Popover / dialog / modal backgrounds */
[data-testid="stPopover"],
[data-baseweb="popover"],
[role="dialog"],
[data-baseweb="modal"] {{
  background-color:var(--la-card)!important;}}
[data-baseweb="popover"] *,
[role="dialog"] p,
[role="dialog"] span {{
  color:var(--la-text)!important;}}

/* Toast notifications — prevent white flash */
[data-testid="stToast"],
[data-testid="toastContainer"],
div[data-testid="stToast"] > div {{
  background-color:var(--la-card)!important;
  border:1px solid var(--la-border)!important;
  color:var(--la-text)!important;}}
[data-testid="stToast"] p,
[data-testid="stToast"] span {{
  color:var(--la-text)!important;}}

/* Streamlit's main block and element containers — override white */
[data-testid="stVerticalBlock"],
[data-testid="element-container"],
[data-testid="stVerticalBlockBorderWrapper"] {{
  background:transparent!important;}}

/* Column backgrounds */
[data-testid="stColumn"],
[data-testid="column"] {{
  background:transparent!important;}}

/* Markdown text inside all containers */
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] td,
[data-testid="stMarkdownContainer"] th {{
  color:var(--la-text)!important;
  background-color:transparent!important;}}

/* Code blocks inside markdown — ensure readable */
[data-testid="stMarkdownContainer"] code {{
  background-color:var(--la-bg2)!important;
  color:var(--la-text)!important;
  padding:0.15rem 0.4rem!important;
  border-radius:var(--r-xs)!important;}}

/* Inline HTML rendered with unsafe_allow_html — fix text in styled divs */
.stMarkdown div,
.stMarkdown table,
.stMarkdown table td,
.stMarkdown table th {{
  color:var(--la-text)!important;}}

/* Strong/bold text visibility */
strong, b, .stMarkdown strong, .stMarkdown b {{
  color:var(--la-text)!important;}}

/* Fix white overlay on the main content area top */
.stApp > div:first-child {{
  background:transparent!important;}}

/* Spinner overlay background */
[data-testid="stSpinner"],
.stSpinner {{
  background:transparent!important;}}
[data-testid="stSpinner"] span,
.stSpinner span {{
  color:var(--la-text)!important;}}

/* Fix white band at top (deploy button / Streamlit branding) */
[data-testid="stToolbar"],
[data-testid="stStatusWidget"] {{
  background:transparent!important;}}

/* Bottom fixed container (if present) */
[data-testid="stBottomBlockContainer"] {{
  background-color:var(--la-bg)!important;
  border-top:1px solid var(--la-border)!important;}}

/* Link colors for visibility */
a, .stMarkdown a {{
  color:var(--la-acc)!important;}}
a:hover, .stMarkdown a:hover {{
  color:var(--la-acc2)!important;}}

/* Ensure divider/hr is visible */
hr, .stMarkdown hr, [data-testid="stSeparator"] {{
  border-color:var(--la-border)!important;}}

/* ══════════════════════════════════════════════════════════════════════
   DISABLED INPUTS — ensure text stays readable on dark themes
   (the doc-preview text area in AI Assistant uses disabled=True)
   ══════════════════════════════════════════════════════════════════════ */
.stTextArea textarea:disabled,
.stTextInput input:disabled,
.stNumberInput input:disabled,
textarea[disabled],
input[disabled] {{
  background-color:var(--la-bg2)!important;
  color:var(--la-text)!important;
  opacity:0.85!important;
  -webkit-text-fill-color:var(--la-text)!important;
  cursor:not-allowed!important;
  border:1px solid var(--la-border)!important;}}

/* Dropdown scrollbar — make it visible on dark themes */
[data-baseweb="menu"]::-webkit-scrollbar,
[data-baseweb="popover"]::-webkit-scrollbar,
[data-baseweb="virtual-list"]::-webkit-scrollbar {{
  width:8px!important;height:8px!important;}}
[data-baseweb="menu"]::-webkit-scrollbar-thumb,
[data-baseweb="popover"]::-webkit-scrollbar-thumb,
[data-baseweb="virtual-list"]::-webkit-scrollbar-thumb {{
  background:{acc}66!important;
  border-radius:var(--r-pill)!important;}}
[data-baseweb="menu"]::-webkit-scrollbar-thumb:hover,
[data-baseweb="popover"]::-webkit-scrollbar-thumb:hover,
[data-baseweb="virtual-list"]::-webkit-scrollbar-thumb:hover {{
  background:var(--la-acc)!important;}}
</style>"""

