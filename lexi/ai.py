"""LexiAssist AI generation layer.

Extracted from lexi.helpers (PR #5). Contains:
  - ``generate()`` — the core Gemini call with streaming, retry, quality
    gate, cost logging, budget enforcement, and per-user rate limiting.
  - ``_assess_response_quality()`` — cheap self-critique for the quality gate.
  - ``compute_confidence_score()`` / ``render_confidence_panel()`` — 4-axis
    heuristic confidence scoring and HTML renderer.
  - ``_get_genai_client()`` / ``_resolve_api_key()`` — Gemini client factory
    and key resolution.
  - ``manual_connect()`` / ``auto_connect()`` — API setup helpers.
  - ``estimate_cost()`` — cost estimation from token lengths.

This module depends only on:
  - lexi.runtime (stdlib + Streamlit + google-genai)
  - lexi.constants (RESPONSE_MODES, SUPPORTED_MODELS, COST_PER_*)
  - lexi.database.get_db (for cost logging)

It does NOT import lexi.helpers, so there is no circular dependency.
"""
from __future__ import annotations

from .runtime import (
    st, os, re, time, datetime, logger,
    Any, Optional,
    genai, _genai_types,
    esc, new_id, safe_json_loads,
)
from .constants import (
    SUPPORTED_MODELS, DEFAULT_MODEL,
    COST_PER_1M_INPUT, COST_PER_1M_OUTPUT,
    RESPONSE_MODES,
)
from .database import get_db


# ═══════════════════════════════════════════════════════
# GEMINI CLIENT + KEY RESOLUTION
# ═══════════════════════════════════════════════════════
def _get_genai_client(key: str) -> "Any":
    """Build a google.genai Client from an API key."""
    return genai.Client(api_key=key)


def _resolve_api_key() -> str:
    """Resolve the Gemini API key from secrets / env / session state."""
    for src in [
        lambda: _safe_secret("GEMINI_API_KEY"),
        lambda: os.getenv("GEMINI_API_KEY", ""),
        lambda: str(st.session_state.get("api_key", "")),
    ]:
        k = str(src() or "")
        if k and k.strip() and len(k.strip()) >= 10:
            return k.strip()
    return ""


def _safe_secret(key: str, default: str = "") -> str:
    """Read a Streamlit secret without raising if missing."""
    try:
        return str(st.secrets[key])
    except Exception:
        return default


# ═══════════════════════════════════════════════════════
# CONNECTION HELPERS
# ═══════════════════════════════════════════════════════
def auto_connect() -> None:
    """Silently configure the API key on first run if available in secrets/env."""
    if st.session_state.api_configured:
        return
    k = _resolve_api_key()
    if k:
        try:
            st.session_state.api_key = k
            st.session_state.api_configured = True
            m = _safe_secret("GEMINI_MODEL") or os.getenv("GEMINI_MODEL", "")
            if m and m in SUPPORTED_MODELS:
                st.session_state.gemini_model = m
        except Exception as e:
            logger.warning(f"Auto-connect failed: {e}")


def manual_connect(key: str) -> bool:
    """Test an API key by making a trivial generation call. Returns True on success."""
    try:
        client = _get_genai_client(key)
        client.models.generate_content(
            model=st.session_state.gemini_model,
            contents="Test",
            config=_genai_types.GenerateContentConfig(max_output_tokens=10),
        )
        st.session_state.api_key = key
        st.session_state.api_configured = True
        return True
    except Exception as e:
        err = str(e)
        if "403" in err:
            st.error("❌ Invalid API key.")
        elif "429" in err:
            st.error("⚠️ Rate limit — try again shortly.")
        else:
            st.error(f"❌ Connection failed: {err[:120]}")
        return False


# ═══════════════════════════════════════════════════════
# COST ESTIMATION
# ═══════════════════════════════════════════════════════
def estimate_cost(input_text: str, output_text: str) -> float:
    """Estimate API cost from text lengths (char/4 ≈ tokens)."""
    input_tokens = len(input_text) / 4
    output_tokens = len(output_text) / 4
    cost = (input_tokens / 1_000_000) * COST_PER_1M_INPUT + (output_tokens / 1_000_000) * COST_PER_1M_OUTPUT
    return float(round(cost, 6))


# ═══════════════════════════════════════════════════════
# CORE GENERATION
# ═══════════════════════════════════════════════════════
def generate(prompt: str, system: str, mode: str, task: str = "general", query: str = "",
             stream_to: Optional[Any] = None, enable_quality_gate: bool = True) -> str:
    """Core generation with streaming, quality gate, retry, cost logging,
    budget enforcement, and per-user rate limiting.
    """
    k = _resolve_api_key()
    if not k:
        return "⚠️ No API key configured. Please set up your key."

    # ── Monthly AI budget enforcement (admin-configured) ────────────────
    try:
        firm_cfg = st.session_state.get("profile", {}).get("firm_config", {})
        monthly_budget = float(firm_cfg.get("monthly_ai_budget", 0) or 0)
        if monthly_budget > 0:
            summary = get_db().get_cost_summary()
            monthly_ngn = float(summary.get("monthly_cost", 0)) * 1600
            if monthly_ngn >= monthly_budget:
                return (
                    f"🚫 **Monthly AI budget exceeded** — "
                    f"₦{monthly_ngn:,.0f} of ₦{monthly_budget:,.0f} used this month. "
                    f"Contact your firm admin to raise the limit."
                )
            elif monthly_ngn >= monthly_budget * 0.9:
                st.toast(
                    f"⚠️ AI budget at {int(monthly_ngn/monthly_budget*100)}% — "
                    f"₦{monthly_budget - monthly_ngn:,.0f} remaining this month",
                    icon="⚠️",
                )
    except Exception:
        pass

    # ── Per-user rate limit (max 30 AI calls per 60 seconds) ────────────
    try:
        import time as _time
        rl_key = "_rate_limit_calls"
        now_ts = _time.time()
        if rl_key not in st.session_state:
            st.session_state[rl_key] = []
        st.session_state[rl_key] = [
            t for t in st.session_state[rl_key] if now_ts - t < 60
        ]
        if len(st.session_state[rl_key]) >= 30:
            wait = int(60 - (now_ts - st.session_state[rl_key][0]))
            return (
                f"⏳ **Rate limit reached** — you've made 30 AI calls in the last minute. "
                f"Wait {wait} seconds and try again."
            )
        st.session_state[rl_key].append(now_ts)
    except Exception:
        pass

    mode_cfg = RESPONSE_MODES.get(mode, RESPONSE_MODES["standard"])
    gen_config = _genai_types.GenerateContentConfig(
        system_instruction=system,
        temperature=mode_cfg["temp"],
        top_p=0.92,
        top_k=40,
        max_output_tokens=mode_cfg["tokens"],
    )
    client = _get_genai_client(k)

    def _do_generate(use_stream: bool) -> str:
        """Single attempt. Streams to UI if stream_to is set."""
        if use_stream and stream_to is not None:
            full_text = ""
            placeholder = stream_to.empty()
            try:
                stream = client.models.generate_content_stream(
                    model=st.session_state.gemini_model,
                    contents=prompt,
                    config=gen_config,
                )
                for chunk in stream:
                    if chunk.text:
                        full_text += chunk.text
                        placeholder.markdown(
                            f'<div class="response-box">{esc(full_text)}<span style="opacity:0.5;">▌</span></div>',
                            unsafe_allow_html=True,
                        )
                placeholder.markdown(
                    f'<div class="response-box">{esc(full_text)}</div>',
                    unsafe_allow_html=True,
                )
                return full_text
            except Exception as e:
                logger.warning(f"Streaming failed, falling back to non-stream: {e}")
        # Non-streaming path
        resp = client.models.generate_content(
            model=st.session_state.gemini_model,
            contents=prompt,
            config=gen_config,
        )
        return resp.text if resp and resp.text else ""

    result = ""
    for attempt in range(3):
        try:
            result = _do_generate(use_stream=(stream_to is not None))
            if result:
                break
        except Exception as e:
            err_str = str(e)
            if attempt == 2:
                return f"⚠️ Generation error after 3 attempts: {err_str[:200]}"
            time.sleep(2 * (attempt + 1))

    if not result:
        return "⚠️ Empty response from AI. Try rephrasing your query."

    # ── Quality Gate (silent self-critique + auto-regenerate once) ──
    if enable_quality_gate and mode in ("standard", "comprehensive") and len(result.split()) > 100:
        quality_score = _assess_response_quality(result, prompt)
        if quality_score < 5:
            logger.info(f"Quality gate triggered (score {quality_score}/10) — regenerating")
            try:
                regen = _do_generate(use_stream=False)
                if regen:
                    new_score = _assess_response_quality(regen, prompt)
                    if new_score > quality_score:
                        result = regen
                        if stream_to is not None:
                            stream_to.markdown(
                                f'<div class="response-box">{esc(result)}</div>',
                                unsafe_allow_html=True,
                            )
            except Exception as e:
                logger.warning(f"Quality regeneration failed: {e}")

    # ── Cost logging ──
    try:
        cost = estimate_cost(prompt + system, result)
        get_db().add_cost_log({
            "id": new_id(),
            "timestamp": datetime.now().isoformat(),
            "model": st.session_state.gemini_model,
            "task": task,
            "mode": mode,
            "input_chars": len(prompt) + len(system),
            "output_chars": len(result),
            "estimated_cost": cost,
            "query_preview": prompt[:120],
        })
    except Exception as e:
        logger.warning(f"Cost logging failed: {e}")

    return result


# ═══════════════════════════════════════════════════════
# QUALITY ASSESSMENT
# ═══════════════════════════════════════════════════════
def _assess_response_quality(response: str, query: str) -> int:
    """Silent quality check. Returns 0-10 score using a cheap model call."""
    try:
        k = _resolve_api_key()
        if not k:
            return 7
        client = _get_genai_client(k)

        check_prompt = f"""Rate the following Nigerian legal analysis on a strict 0-10 scale.

Criteria:
- Does it cite at least one Nigerian statute or case? (+3)
- Does it take a firm position (no excessive hedging)? (+3)
- Is it complete (no abrupt cut-off)? (+2)
- Does it directly address the query? (+2)

Respond ONLY with a single integer 0-10, nothing else.

QUERY: {query[:500]}

ANALYSIS:
{response[:4000]}

SCORE:"""
        resp = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=check_prompt,
            config=_genai_types.GenerateContentConfig(
                temperature=0.0, max_output_tokens=10,
            ),
        )
        if resp and resp.text:
            match = re.search(r"\b([0-9]|10)\b", resp.text.strip())
            if match:
                return int(match.group(1))
    except Exception as e:
        logger.warning(f"Quality assessment failed: {e}")
    return 7


# ═══════════════════════════════════════════════════════
# CONFIDENCE SCORING (heuristic, no extra API call)
# ═══════════════════════════════════════════════════════
def compute_confidence_score(response: str, audit: dict) -> dict:
    """4-axis confidence scoring on an AI response. Pure heuristics.

    Returns: {statutory: int, case_law: int, procedural: int, position: int, overall: int}
    Each axis is 0-10. Overall is weighted average.
    """
    text = response or ""
    text_lower = text.lower()
    word_count = len(text.split())

    # ── Statutory grounding ──
    statute_patterns = [
        r"\b(?:CFRN|Constitution)\b",
        r"\b(?:CAMA|Companies and Allied Matters Act)\b",
        r"\b(?:ACJA|Administration of Criminal Justice Act)\b",
        r"\bEvidence Act\b", r"\bLabour Act\b", r"\bLand Use Act\b",
        r"\bCriminal Code\b", r"\bPenal Code\b",
        r"\bElectoral Act\b", r"\bArbitration\s+(?:and\s+)?(?:Conciliation|Mediation)\s+Act\b",
        r"\bPetroleum Industry Act\b", r"\bPIA\s+2021\b",
        r"\bFinance Act\b", r"\bCITA\b", r"\bPITA\b", r"\bVATA?\b",
        r"\bSection\s+\d+", r"\bs\.\s*\d+", r"\bSec\.\s*\d+",
        r"\bArticle\s+\d+", r"\bPart\s+[IVX]+",
    ]
    statute_hits = sum(1 for p in statute_patterns if re.search(p, text, re.IGNORECASE))
    statutory_score = min(10, statute_hits * 2)

    # ── Case law grounding ──
    verified = len(audit.get("verified_cases", []))
    unverified = len(audit.get("unverified_cases", []))
    citations = audit.get("citations_found", 0)
    if verified + unverified == 0 and citations == 0:
        case_score = 2
    elif verified == 0 and unverified > 0:
        case_score = 3
    else:
        case_score = min(10, (verified * 3) + max(0, citations - unverified) + (1 if verified > 0 else 0))

    # ── Procedural certainty ──
    proc_patterns = [
        r"\b(?:filing|file)\b", r"\bdeadline\b", r"\blimitation\b",
        r"\bjurisdic", r"\bvenue\b", r"\bservice of process\b",
        r"\bpre-action\b", r"\bnotice\b", r"\bappeal\b",
        r"\b\d+\s+days?\b", r"\b\d+\s+months?\b", r"\b\d+\s+years?\b",
        r"\bRules of Court\b", r"\bCivil Procedure\b",
    ]
    proc_hits = sum(1 for p in proc_patterns if re.search(p, text_lower))
    procedural_score = min(10, proc_hits + 2)

    # ── Position-taking ──
    hedge_patterns = [
        r"\bmay (?:be|have|need|require)\b", r"\bmight\b", r"\bcould (?:be|have)\b",
        r"\bperhaps\b", r"\bpossibly\b", r"\barguably\b",
        r"\bit (?:could|would) be argued\b", r"\bit depends\b",
    ]
    position_patterns = [
        r"\b(?:is|are) liable\b", r"\bmust\b", r"\bshall\b",
        r"\bclearly\b", r"\bunequivocally\b", r"\bestablished\b",
        r"\bthe (?:claimant|defendant|applicant) (?:wins|loses|succeeds|fails)\b",
        r"\bweakest party\b", r"\bbest claim\b", r"\bbest defence\b",
    ]
    hedge_count = sum(len(re.findall(p, text_lower)) for p in hedge_patterns)
    position_count = sum(len(re.findall(p, text_lower)) for p in position_patterns)
    if word_count < 100:
        position_score = 5
    else:
        hedge_density = (hedge_count / word_count) * 100
        position_density = (position_count / word_count) * 100
        position_score = max(0, min(10, int(7 + position_density - (hedge_density * 1.5))))

    # ── Overall weighted ──
    overall = round(
        statutory_score * 0.25
        + case_score * 0.30
        + procedural_score * 0.20
        + position_score * 0.25
    )

    return {
        "statutory": statutory_score,
        "case_law": case_score,
        "procedural": procedural_score,
        "position": position_score,
        "overall": overall,
    }


def render_confidence_panel(scores: dict) -> str:
    """Render the 4-axis confidence display as HTML."""
    overall = scores.get("overall", 0)

    if overall >= 8:
        bar_color = "#059669"; label = "HIGH CONFIDENCE"; bg = "#f0fdf4"
    elif overall >= 6:
        bar_color = "#d97706"; label = "MODERATE CONFIDENCE"; bg = "#fffbeb"
    elif overall >= 4:
        bar_color = "#ea580c"; label = "LOW CONFIDENCE — VERIFY"; bg = "#fff7ed"
    else:
        bar_color = "#dc2626"; label = "VERY LOW — DO NOT RELY"; bg = "#fef2f2"

    def axis_bar(name: str, score: int) -> str:
        ax_color = "#059669" if score >= 7 else ("#d97706" if score >= 5 else "#dc2626")
        return f"""
<div style="margin-bottom:0.45rem;">
  <div style="display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:2px;">
    <span style="color:var(--la-text2);font-weight:500;">{esc(name)}</span>
    <span style="color:{ax_color};font-weight:700;">{score}/10</span>
  </div>
  <div style="background:#e5e7eb;border-radius:999px;height:6px;">
    <div style="width:{score*10}%;background:{ax_color};height:6px;border-radius:999px;"></div>
  </div>
</div>"""

    return f"""
<div style="background:{bg};border:1.5px solid {bar_color};border-radius:0.7rem;
padding:1rem 1.2rem;margin:1rem 0;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.7rem;">
    <strong style="color:{bar_color};">📊 AI Confidence Score</strong>
    <span style="background:{bar_color};color:white;font-size:0.72rem;font-weight:700;
    padding:0.2rem 0.7rem;border-radius:1rem;">{label} · {overall}/10</span>
  </div>
  {axis_bar("Statutory grounding", scores.get("statutory", 0))}
  {axis_bar("Case law support", scores.get("case_law", 0))}
  {axis_bar("Procedural certainty", scores.get("procedural", 0))}
  {axis_bar("Firm position-taking", scores.get("position", 0))}
</div>"""
