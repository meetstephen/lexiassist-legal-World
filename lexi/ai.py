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
    RESPONSE_MODES, THINKING_BUDGETS, USD_TO_NGN,
)
from .database import get_db


# ═══════════════════════════════════════════════════════
# NATIVE THINKING / REASONING BUDGET RESOLUTION
# ═══════════════════════════════════════════════════════
def _resolve_thinking_budget(model: str, mode: str) -> Optional[int]:
    """Resolve the native ``thinking_budget`` for a given model + response mode.

    The base budget comes from ``THINKING_BUDGETS[mode]`` (calibrated for
    gemini-2.5-flash) and is then clamped to the specific model's supported
    range. This is what lets a lightweight Flash model *reason internally*
    before answering — the reasoning lives in the model's thinking phase,
    not in the prompt string.

    Returns:
        * an ``int`` budget (``-1`` = dynamic, ``0`` = disabled), or
        * ``None`` when the model is not known to support a thinking budget,
          in which case the caller MUST NOT attach a ``thinking_config``.

    Per-model ranges (Gemini 2.5 series, April 2026):
        Pro        : 128–32,768  (cannot be disabled)
        Flash      : 0–24,576    (0 disables)
        Flash-Lite : 512–24,576  (off by default; -1/0 allowed)
    """
    base = THINKING_BUDGETS.get(mode, THINKING_BUDGETS["standard"])
    m = (model or "").lower()

    # Only the Gemini 2.5 / 3 reasoning families accept a thinking budget.
    # Attaching thinking_config to an older model (1.5 / 2.0 non-thinking)
    # raises an API error, so we signal "don't attach" with None.
    supports_thinking = (
        "2.5" in m
        or "gemini-3" in m
        or "2.0-flash-thinking" in m
    )
    if not supports_thinking:
        return None

    # Pro: thinking cannot be disabled; clamp to 128–32768 (or dynamic).
    if "pro" in m:
        if base == -1:
            return -1
        return max(128, min(int(base), 32768))

    # Flash-Lite: thinking is off by default; when enabling, min 512.
    if "flash-lite" in m or "flash_lite" in m:
        if base == -1:
            return -1
        if base <= 0:
            return 0
        return max(512, min(int(base), 24576))

    # Flash (and any other 2.5/3 model): 0–24576, or dynamic.
    if base == -1:
        return -1
    return max(0, min(int(base), 24576))


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
# REASONING PANEL (renders the model's native "thinking")
# ═══════════════════════════════════════════════════════
def render_reasoning_panel(reasoning: str, streaming: bool = False) -> str:
    """Render the model's internal reasoning (thought summary) as a styled,
    theme-aware panel. This makes the "think before answering" step visible
    and verifiable to the lawyer, without cluttering the final answer box.

    ``streaming=True`` adds a subtle live indicator while thoughts arrive.
    """
    text = (reasoning or "").strip()
    if not text:
        return ""
    header = "🧠 Reasoning" + ("  ·  thinking…" if streaming else "")
    cursor = '<span style="opacity:0.5;">▌</span>' if streaming else ""
    return f"""
<div style="background:var(--la-bg2);color:var(--la-text2);
border:1px dashed var(--la-border);border-left:3px solid #6366f1;
border-radius:0.6rem;padding:0.7rem 1rem;margin:0.6rem 0;
font-size:0.82rem;line-height:1.55;">
  <div style="font-weight:700;color:#6366f1;margin-bottom:0.35rem;
  letter-spacing:0.02em;">{header}</div>
  <div style="white-space:pre-wrap;">{esc(text)}{cursor}</div>
</div>"""


def render_sources_panel(grounding: dict, title: str = "🌐 Live web sources") -> str:
    """Render the REAL source URLs the model retrieved via Google Search as a
    panel of clickable links, plus the actual search queries it ran. This is
    the verifiable, click-to-check evidence behind a grounded answer."""
    if not grounding or not isinstance(grounding, dict):
        return ""
    sources = grounding.get("sources") or []
    queries = grounding.get("queries") or []
    if not sources and not queries:
        return ""

    link_items = ""
    for i, s in enumerate(sources, 1):
        uri = esc(s.get("uri", ""))
        ttl = esc(s.get("title") or s.get("uri", ""))
        dom = s.get("domain") or ""
        dom_html = (
            f' <span style="color:var(--la-text2);font-size:0.74rem;">· {esc(dom)}</span>'
            if dom else ""
        )
        link_items += (
            f'<li style="margin:0.25rem 0;">'
            f'<a href="{uri}" target="_blank" rel="noopener noreferrer" '
            f'style="color:#2563eb;font-weight:600;text-decoration:none;">{ttl}</a>'
            f'{dom_html}</li>'
        )

    queries_html = ""
    if queries:
        queries_html = (
            '<div style="font-size:0.76rem;color:var(--la-text2);margin-top:0.5rem;">'
            '🔎 Searches run: ' + esc("  ·  ".join(queries)) + '</div>'
        )

    sources_block = (
        f'<ol style="margin:0.3rem 0 0 1.1rem;padding:0;font-size:0.84rem;line-height:1.5;">{link_items}</ol>'
        if link_items else
        '<div style="font-size:0.82rem;color:var(--la-text2);">No source links were returned for this query.</div>'
    )

    return f"""
<div style="background:var(--la-bg2);color:var(--la-text2);
border:1px solid var(--la-border);border-left:3px solid #2563eb;
border-radius:0.6rem;padding:0.75rem 1rem;margin:0.6rem 0;font-size:0.85rem;">
  <div style="font-weight:700;color:#2563eb;margin-bottom:0.35rem;">{esc(title)}</div>
  <div style="font-size:0.76rem;color:var(--la-text2);margin-bottom:0.3rem;">
    Retrieved live from Google Search. Always open and verify each source before relying on it.
  </div>
  {sources_block}
  {queries_html}
</div>"""


# ═══════════════════════════════════════════════════════
# CORE GENERATION
# ═══════════════════════════════════════════════════════
def generate(prompt: str, system: str, mode: str, task: str = "general", query: str = "",
             stream_to: Optional[Any] = None, enable_quality_gate: bool = True,
             use_web_search: Optional[bool] = None) -> str:
    """Core generation with streaming, quality gate, retry, cost logging,
    budget enforcement, and per-user rate limiting.

    Web grounding:
      * ``use_web_search=True``  → force live Google Search grounding.
      * ``use_web_search=False`` → force OFF (e.g. for internal/meta calls
        like the quality-gate self-critique where web search is pointless).
      * ``use_web_search=None`` (default) → defer to the app-wide switch
        ``st.session_state['global_web_grounding']``. This is what lets a
        SINGLE user-facing toggle put EVERY generating feature (all task
        types, issue-spot, follow-up, settlement, due diligence, witness,
        etc.) online at once, without each call site having to opt in.

    When grounding is active the model is given Google Search as a tool so its
    answer is grounded in real, live web results instead of training-data
    memory, and the real source URLs it used are captured into
    ``st.session_state['_last_grounding']`` so the UI can show verifiable
    citations (this is what keeps the news feed / research factual, not
    hallucinated).
    """
    # Resolve the effective grounding decision (explicit arg wins; otherwise
    # fall back to the global app-wide switch, default off).
    if use_web_search is None:
        try:
            use_web_search = bool(st.session_state.get("global_web_grounding", False))
        except Exception:
            use_web_search = False

    k = _resolve_api_key()
    if not k:
        return "⚠️ No API key configured. Please set up your key."

    # ── Monthly AI budget enforcement (admin-configured) ────────────────
    # Two layers:
    #   (1) Reactive — if the cumulative spend already meets/exceeds the
    #       budget, refuse outright.
    #   (2) Predictive — if THIS call's worst-case cost would push us over,
    #       refuse before billing the API. Worst-case = full input chars
    #       plus max_output_tokens for the selected mode (Brief/Standard/
    #       Comprehensive). Prevents a single Comprehensive call from
    #       silently overshooting a near-empty budget.
    # Failures of the check itself are logged (not silently swallowed) so
    # that broken DB connectivity doesn't disable enforcement invisibly.
    try:
        firm_cfg = st.session_state.get("profile", {}).get("firm_config", {})
        monthly_budget_ngn = float(firm_cfg.get("monthly_ai_budget", 0) or 0)
        if monthly_budget_ngn > 0:
            summary = get_db().get_cost_summary()
            spent_ngn = float(summary.get("monthly_cost", 0)) * USD_TO_NGN

            # Already over: hard block.
            if spent_ngn >= monthly_budget_ngn:
                logger.info(
                    f"AI call blocked — budget exhausted "
                    f"(spent ₦{spent_ngn:,.0f} / ₦{monthly_budget_ngn:,.0f})"
                )
                try:
                    get_db().append_audit(
                        "AI_BUDGET_BLOCKED",
                        f"reason=exhausted spent_ngn={spent_ngn:.0f} "
                        f"budget_ngn={monthly_budget_ngn:.0f} mode={mode}",
                    )
                except Exception:  # noqa: BLE001 — audit best-effort
                    pass
                return (
                    f"🚫 **Monthly AI budget exceeded** — "
                    f"₦{spent_ngn:,.0f} of ₦{monthly_budget_ngn:,.0f} used this month. "
                    f"Contact your firm admin to raise the limit."
                )

            # Predictive check — worst-case cost of this specific call.
            # Thinking tokens are billed as output tokens, so include the
            # resolved thinking budget in the worst-case output projection
            # (dynamic/-1 is estimated conservatively) — otherwise enabling
            # native reasoning could silently overshoot a near-empty budget.
            mode_tokens = RESPONSE_MODES.get(mode, RESPONSE_MODES["standard"]).get("tokens", 32000)
            _think_b = _resolve_thinking_budget(st.session_state.gemini_model, mode) or 0
            if _think_b == -1:
                _think_tokens = 4096   # conservative estimate for "dynamic"
            else:
                _think_tokens = max(0, _think_b)
            input_tokens = (len(prompt) + len(system)) / 4
            projected_usd = (
                (input_tokens / 1_000_000) * COST_PER_1M_INPUT
                + ((mode_tokens + _think_tokens) / 1_000_000) * COST_PER_1M_OUTPUT
            )
            projected_ngn = projected_usd * USD_TO_NGN

            if spent_ngn + projected_ngn > monthly_budget_ngn:
                remaining = monthly_budget_ngn - spent_ngn
                logger.info(
                    f"AI call blocked — projected overshoot "
                    f"(remaining ₦{remaining:,.0f}, projected ₦{projected_ngn:,.0f}, mode={mode})"
                )
                try:
                    get_db().append_audit(
                        "AI_BUDGET_BLOCKED",
                        f"reason=would_overshoot remaining_ngn={remaining:.0f} "
                        f"projected_ngn={projected_ngn:.0f} mode={mode}",
                    )
                except Exception:  # noqa: BLE001 — audit best-effort
                    pass
                return (
                    f"🚫 **Insufficient AI budget for this call** — "
                    f"this {mode} request could cost up to ₦{projected_ngn:,.0f} but only "
                    f"₦{remaining:,.0f} is left this month. "
                    f"Try a shorter query in Brief mode, or contact your admin to raise the limit."
                )

            # 90%+ used: warn but allow.
            if spent_ngn >= monthly_budget_ngn * 0.9:
                try:
                    st.toast(
                        f"⚠️ AI budget at {int(spent_ngn / monthly_budget_ngn * 100)}% — "
                        f"₦{monthly_budget_ngn - spent_ngn:,.0f} remaining this month",
                        icon="⚠️",
                    )
                except Exception:  # noqa: BLE001 — toast best-effort
                    pass
    except Exception as _budget_err:  # noqa: BLE001 — fail-open by design, but log
        logger.warning(f"Budget enforcement check failed (allowing call): {_budget_err}")

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

    # ── Native "thinking loop" ──────────────────────────────────────────
    # We push the reasoning out of the prompt string and into the model's
    # native thinking phase: before emitting any final answer, the model
    # spends a budget of private reasoning tokens working through the law.
    # include_thoughts=True asks the API to return summarised reasoning so
    # we can surface "how it reasoned" to the lawyer for verification.
    thinking_budget = _resolve_thinking_budget(st.session_state.gemini_model, mode)

    _base_cfg = dict(
        system_instruction=system,
        temperature=mode_cfg["temp"],
        top_p=0.92,
        top_k=40,
        max_output_tokens=mode_cfg["tokens"],
    )
    # ── Live web grounding (Google Search tool) ─────────────────────────
    # Attaching the google_search tool makes the model actually search the
    # web and ground its answer in real results, returning real source URLs
    # in the response's grounding_metadata. This is the antidote to
    # hallucinated "news" — the content is tied to live sources.
    _tools = None
    if use_web_search:
        try:
            _tools = [_genai_types.Tool(google_search=_genai_types.GoogleSearch())]
        except Exception as _ws_err:  # noqa: BLE001 — degrade to ungrounded
            logger.warning(f"Google Search tool unavailable, proceeding ungrounded: {_ws_err}")

    def _build_cfg(with_thinking: bool, with_tools: bool) -> Any:
        """Compose a GenerateContentConfig, degrading gracefully if the
        thinking_config can't be constructed."""
        kw = dict(_base_cfg)
        if with_tools and _tools:
            kw["tools"] = _tools
        if with_thinking and thinking_budget is not None:
            try:
                return _genai_types.GenerateContentConfig(
                    thinking_config=_genai_types.ThinkingConfig(
                        thinking_budget=thinking_budget,
                        include_thoughts=True,
                    ),
                    **kw,
                )
            except Exception as _tc_err:  # noqa: BLE001 — degrade gracefully
                logger.warning(f"ThinkingConfig unavailable, proceeding without it: {_tc_err}")
        return _genai_types.GenerateContentConfig(**kw)

    # Three layers, tried in order on the relevant failure:
    #   gen_config         → thinking + (optional) web search   [primary]
    #   gen_config_nothink → web search only  (thinking rejected)
    #   gen_config_plain   → neither          (search tool rejected)
    gen_config         = _build_cfg(with_thinking=True,  with_tools=True)
    gen_config_nothink = _build_cfg(with_thinking=False, with_tools=True)
    gen_config_plain   = _build_cfg(with_thinking=False, with_tools=False)

    client = _get_genai_client(k)

    # Reset captured reasoning + grounding for this call (surfaced in UI after).
    st.session_state["_last_reasoning"] = ""
    st.session_state["_last_grounding"] = None

    def _split_parts(resp_or_chunk: Any) -> tuple[str, str]:
        """Return (answer_text, thought_text) from a response/stream chunk by
        inspecting candidate parts. Falls back to ('', '') when the structure
        isn't present so callers can use the convenience .text accessor."""
        answer = ""
        thought = ""
        try:
            cands = getattr(resp_or_chunk, "candidates", None) or []
            if not cands:
                return "", ""
            content = getattr(cands[0], "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                ptext = getattr(part, "text", None)
                if not ptext:
                    continue
                if getattr(part, "thought", False):
                    thought += ptext
                else:
                    answer += ptext
        except Exception:
            return "", ""
        return answer, thought

    def _accumulate_grounding(resp_or_chunk: Any) -> None:
        """Pull real source URLs / search queries from a response or stream
        chunk's grounding_metadata and merge (de-duped) into
        ``st.session_state['_last_grounding']``. No-op when there's no
        grounding (e.g. ungrounded calls)."""
        try:
            cands = getattr(resp_or_chunk, "candidates", None) or []
            if not cands:
                return
            gm = getattr(cands[0], "grounding_metadata", None)
            if not gm:
                return
            sources = []
            for ch in (getattr(gm, "grounding_chunks", None) or []):
                web = getattr(ch, "web", None)
                uri = getattr(web, "uri", None) if web else None
                if not uri:
                    continue
                sources.append({
                    "uri": uri,
                    "title": (getattr(web, "title", None) or uri),
                    "domain": (getattr(web, "domain", None) or ""),
                })
            queries = list(getattr(gm, "web_search_queries", None) or [])
            sep = getattr(gm, "search_entry_point", None)
            search_html = getattr(sep, "rendered_content", "") if sep else ""
            if not sources and not queries and not search_html:
                return
            store = st.session_state.get("_last_grounding") or {
                "sources": [], "queries": [], "search_html": "",
            }
            seen = {s["uri"] for s in store["sources"]}
            for s in sources:
                if s["uri"] not in seen:
                    store["sources"].append(s)
                    seen.add(s["uri"])
            for q in queries:
                if q not in store["queries"]:
                    store["queries"].append(q)
            if search_html:
                store["search_html"] = search_html
            st.session_state["_last_grounding"] = store
        except Exception:
            return

    def _do_generate(use_stream: bool, config: "Any") -> str:
        """Single attempt. Streams to UI if stream_to is set. Separates the
        model's thinking (rendered live in a reasoning panel) from the final
        answer (rendered in the response box), and stashes the reasoning in
        ``st.session_state['_last_reasoning']`` for later display."""
        if use_stream and stream_to is not None:
            answer_text = ""
            thought_text = ""
            reason_ph = stream_to.empty()
            answer_ph = stream_to.empty()
            try:
                stream = client.models.generate_content_stream(
                    model=st.session_state.gemini_model,
                    contents=prompt,
                    config=config,
                )
                for chunk in stream:
                    a, t = _split_parts(chunk)
                    _accumulate_grounding(chunk)
                    if not a and not t:
                        # Fallback to the convenience accessor for SDKs/models
                        # that don't expose per-part thought flags.
                        try:
                            if chunk.text:
                                a = chunk.text
                        except Exception:
                            a = ""
                    if t:
                        thought_text += t
                    if a:
                        answer_text += a
                    if thought_text:
                        reason_ph.markdown(
                            render_reasoning_panel(thought_text, streaming=True),
                            unsafe_allow_html=True,
                        )
                    answer_ph.markdown(
                        f'<div class="response-box">{esc(answer_text)}<span style="opacity:0.5;">▌</span></div>',
                        unsafe_allow_html=True,
                    )
                # Final render (drop the cursor)
                if thought_text:
                    reason_ph.markdown(
                        render_reasoning_panel(thought_text, streaming=False),
                        unsafe_allow_html=True,
                    )
                else:
                    reason_ph.empty()
                answer_ph.markdown(
                    f'<div class="response-box">{esc(answer_text)}</div>',
                    unsafe_allow_html=True,
                )
                st.session_state["_last_reasoning"] = thought_text
                return answer_text
            except Exception as e:
                # Re-raise thinking-related errors so the caller can retry
                # without thinking_config; otherwise fall back to non-stream.
                _e = str(e).lower()
                if "think" in _e or "thought" in _e or "budget" in _e:
                    raise
                logger.warning(f"Streaming failed, falling back to non-stream: {e}")
        # Non-streaming path
        resp = client.models.generate_content(
            model=st.session_state.gemini_model,
            contents=prompt,
            config=config,
        )
        answer_text, thought_text = _split_parts(resp)
        _accumulate_grounding(resp)
        if not answer_text:
            answer_text = resp.text if resp and getattr(resp, "text", None) else ""
        if thought_text:
            st.session_state["_last_reasoning"] = thought_text
        return answer_text

    result = ""
    active_config = gen_config
    for attempt in range(3):
        try:
            result = _do_generate(use_stream=(stream_to is not None), config=active_config)
            if result:
                break
        except Exception as e:
            err_str = str(e)
            el = err_str.lower()
            # If the model/API rejected the thinking_config, drop it and retry
            # immediately (don't burn an attempt or sleep on a config mismatch).
            if active_config is gen_config and any(
                tok in el for tok in ("think", "thought", "budget")
            ):
                logger.warning(f"Thinking config rejected by model; retrying without it: {err_str[:160]}")
                active_config = gen_config_nothink
                continue
            # If the Google Search tool was rejected (model/tier doesn't allow
            # grounding), degrade to an ungrounded call rather than hard-failing.
            if _tools and active_config is not gen_config_plain and any(
                tok in el for tok in ("search", "tool", "grounding", "function", "not supported", "unsupported")
            ):
                logger.warning(f"Web-search tool rejected; retrying ungrounded: {err_str[:160]}")
                active_config = gen_config_plain
                continue
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
                regen = _do_generate(use_stream=False, config=active_config)
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
        bar_color = "#16a34a"; label = "HIGH CONFIDENCE"; bg = "rgba(5,150,105,0.10)"
    elif overall >= 6:
        bar_color = "#f59e0b"; label = "MODERATE CONFIDENCE"; bg = "rgba(245,158,11,0.10)"
    elif overall >= 4:
        bar_color = "#fb923c"; label = "LOW CONFIDENCE — VERIFY"; bg = "rgba(234,88,12,0.10)"
    else:
        bar_color = "#ef4444"; label = "VERY LOW — DO NOT RELY"; bg = "rgba(220,38,38,0.10)"

    def axis_bar(name: str, score: int) -> str:
        ax_color = "#16a34a" if score >= 7 else ("#f59e0b" if score >= 5 else "#ef4444")
        return f"""
<div style="margin-bottom:0.45rem;">
  <div style="display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:2px;">
    <span style="color:var(--la-text2);font-weight:500;">{esc(name)}</span>
    <span style="color:{ax_color};font-weight:700;">{score}/10</span>
  </div>
  <div style="background:rgba(128,128,128,0.25);border-radius:999px;height:6px;">
    <div style="width:{score*10}%;background:{ax_color};height:6px;border-radius:999px;"></div>
  </div>
</div>"""

    return f"""
<div style="background:{bg};color:var(--la-text);
border:1.5px solid {bar_color};border-radius:0.7rem;
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
