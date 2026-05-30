"""LexiAssist web-based case research — online case search with
verification against the internal verified database.

This module provides:
  - ``search_cases_online()`` — uses the Gemini model's knowledge to find
    relevant Nigerian cases beyond the local verified database, then
    cross-checks each result against the verified DB for authenticity.
  - ``verify_online_case()`` — multi-step verification of a single case
    (name match, citation format check, cross-reference).
  - ``enrich_research_with_online()`` — augments standard research output
    with online case findings.

Design philosophy:
  - The AI is instructed to ONLY return cases it is highly confident are
    real (well-known Nigerian authorities).
  - Each returned case is then cross-verified against the local DB.
  - Cases NOT in the local DB are clearly flagged as "Online — Verify
    before citing" so lawyers know to check NWLR/LPELR/LawPavilion.
  - A confidence tier system (Verified > High-Confidence > Needs Verification)
    helps lawyers quickly assess reliability.
"""
from __future__ import annotations

from .runtime import st, re, datetime, logger, esc, safe_json_loads, new_id
from .constants import RESPONSE_MODES
from .citations import VERIFIED_NIGERIAN_CASES


def _get_generate():
    """Lazy import to avoid circular dependency."""
    from .ai import generate
    return generate


def _get_identity_core():
    """Lazy import to avoid circular dependency."""
    from .prompts import IDENTITY_CORE
    return IDENTITY_CORE


def verify_online_case(case_name: str, citation: str = "", year: str = "",
                       grounded: bool = False) -> dict:
    """Classify an online-sourced case by how strongly its AUTHENTICITY is
    actually evidenced — never overstating what was checked.

    Honest tiers (the previous version wrongly called a regex-shape match
    "high confidence", which would pass a hallucinated citation that merely
    had the right format):
      - "verified"        → the case name matches LexiAssist's hand-verified
                            local database. This is a genuine real-case match.
      - "web_sourced"     → NOT in the local DB, but it came from a search that
                            actually reached the live web (``grounded=True``)
                            AND the citation has a valid Nigerian-report shape.
                            This means "a live web search surfaced it" — the
                            lawyer must still open the cited source/report to
                            confirm. It is NOT a guarantee of existence.
      - "needs_verification" → anything else: no live grounding occurred (the
                            model may have used memory), or the citation shape
                            is invalid. MUST be independently verified.

    Returns: verified(bool), confidence_tier, local_match, citation_format_valid,
    grounded(bool), notes.
    """
    from .citations import verify_case_name

    # Check local DB
    local_match = verify_case_name(case_name)

    # Citation format heuristic for Nigerian law reports (shape ONLY — this
    # proves nothing about whether the case actually exists).
    citation_valid = False
    if citation:
        nwlr_pattern = r"\(\d{4}\)\s+\d+\s+NWLR\s+\(Pt\.\s*\d+\)"
        sc_pattern = r"\(\d{4}\)\s+\d+\s+SC\s+\d+"
        scnlr_pattern = r"\(\d{4}\)\s+\d+\s+SCNLR\s+\d+"
        lpelr_pattern = r"LPELR[-\s]*\d+"
        other_pattern = r"\(\d{4}\)\s+\d+\s+(NWLR|WLR|FWLR|All NLR|ANLR)"
        if any(re.search(p, citation, re.IGNORECASE) for p in [
            nwlr_pattern, sc_pattern, scnlr_pattern, lpelr_pattern, other_pattern
        ]):
            citation_valid = True

    year_ok = False
    if year:
        try:
            year_ok = int(year) <= datetime.now().year
        except (ValueError, TypeError):
            year_ok = False

    # Determine the honest confidence tier.
    if local_match:
        tier = "verified"
        notes = "Found in LexiAssist verified Nigerian case database — genuine, real case."
    elif grounded and citation_valid and year_ok:
        tier = "web_sourced"
        notes = (
            "Surfaced by a LIVE web search with a valid citation format. This is "
            "NOT a guarantee it exists — open the linked source(s) below and "
            "confirm the report (NWLR/LPELR/LawPavilion) before citing."
        )
    else:
        tier = "needs_verification"
        if not grounded:
            notes = (
                "The live web search returned no confirming sources for this case "
                "(it may be from model memory). Treat as UNVERIFIED — confirm on "
                "NWLR/LPELR/LawPavilion before relying."
            )
        else:
            notes = (
                "Citation format could not be validated. MUST verify on "
                "NWLR/LPELR/LawPavilion before relying."
            )

    return {
        "verified": bool(local_match),
        "confidence_tier": tier,
        "local_match": local_match,
        "citation_format_valid": citation_valid,
        "grounded": bool(grounded),
        "notes": notes,
    }


def search_cases_online(
    legal_issue: str,
    case_type: str = "",
    jurisdiction: str = "Nigeria",
    max_results: int = 8,
) -> list[dict]:
    """Search for relevant cases combining BOTH the local verified database
    AND AI online knowledge, then verify each result.

    Strategy:
      1. First, pull all matching cases from the local verified DB (these are
         guaranteed genuine and get "verified" tier).
      2. Then, ask the AI for additional cases it knows about for the issue.
      3. Cross-check AI results against the local DB (avoids duplicates).
      4. Combine both sets, with verified local cases ALWAYS listed first.

    Returns a list of dicts, each containing:
      - name: str
      - citation: str
      - court: str
      - year: str
      - ratio: str (the legal principle)
      - relevance: str (why it's relevant to the issue)
      - confidence_tier: "verified" | "high_confidence" | "needs_verification"
      - verification: dict (full verification result)
      - source: "local_db" | "online"
    """
    generate = _get_generate()
    identity = _get_identity_core()
    from .citations import find_relevant_verified_cases as _find_local

    # ── Step 1: Get local verified cases first (always genuine) ──
    local_cases = _find_local(legal_issue, top_k=max_results)
    combined_results = []
    seen_names = set()

    for lc in local_cases:
        name = lc.get("name", "")
        combined_results.append({
            "name": name,
            "citation": lc.get("citation", ""),
            "court": lc.get("court", ""),
            "year": str(lc.get("year", "")),
            "ratio": lc.get("principle", ""),
            "relevance": "Verified Nigerian authority from the local database, retrieved as a possible match — confirm it is on-point for your specific issue.",
            "confidence_tier": "verified",
            "verification": {
                "verified": True,
                "confidence_tier": "verified",
                "local_match": lc,
                "citation_format_valid": True,
                "notes": "Found in LexiAssist verified Nigerian case database.",
            },
            "source": "local_db",
        })
        seen_names.add(name.lower())

    # ── Step 2: Search online for additional cases ──
    case_context = f"\nCase Type: {case_type}" if case_type else ""

    # Tell AI which cases we already have so it doesn't repeat them
    already_have = ""
    if local_cases:
        already_have = (
            "\n\nCASES ALREADY FOUND (do NOT repeat these — find DIFFERENT ones):\n"
            + "\n".join(f"- {lc['name']}" for lc in local_cases)
            + "\n"
        )

    prompt = f"""You are a senior Nigerian legal research specialist with LIVE Google Search
access and deep knowledge of Nigerian case law from the Supreme Court, Court of
Appeal, Federal High Court, National Industrial Court, and State High Courts.

TASK: Using live web search, find additional REAL, reported Nigerian cases for
the following legal issue. Confirm each case against what the search results
actually show — do not rely on memory alone.

LEGAL ISSUE: {legal_issue}{case_context}
JURISDICTION: {jurisdiction}{already_have}

STRICT RULES:
1. Base every case on what your live web search results actually show. Prefer
   cases reported in NWLR, SC, SCNLR, FWLR, LPELR or carried by reputable
   Nigerian legal sources (judiciary sites, law-report publishers, NBA, etc.).
2. Strongly prefer landmark and RECENT decisions relevant to the issue.
3. Include the FULL citation in standard Nigerian format: (YYYY) NN NWLR (Pt. NNN) NNN
4. For each case, state the RATIO DECIDENDI (the legal principle established).
5. Explain WHY the case is relevant to the specific legal issue raised.
6. NEVER invent a case name or fabricate a citation. If the search does not
   confirm a case, OMIT it entirely — fewer real cases beats any fabrication.
7. Return UP TO {max(3, max_results - len(local_cases))} cases, ranked by relevance.
8. Do NOT repeat any case already listed above.

Respond ONLY in this exact JSON format:
{{
  "cases": [
    {{
      "name": "Full case name (Plaintiff v Defendant)",
      "citation": "(YYYY) NN NWLR (Pt. NNN) NNN",
      "court": "Supreme Court | Court of Appeal | Federal High Court | NIC",
      "year": "YYYY",
      "ratio": "The legal principle established in this case",
      "relevance": "Why this case is directly relevant to the legal issue",
      "source_url": "The exact web URL where you found/confirmed this case (empty string if none)"
    }}
  ],
  "research_notes": "Any important context about the state of law on this issue",
  "suggested_statutes": ["Relevant statutes to also consider"]
}}

Rule: if you cannot give a real source_url for a case from your search results, do not include that case.
"""

    # Go ONLINE for real: ground the search in live Google Search results so
    # the "online" cases are sourced from the web, not training memory. The
    # real source URLs are captured for display alongside the results.
    raw = generate(prompt, identity, "standard", "research", use_web_search=True)
    _grounding = st.session_state.get("_last_grounding")
    st.session_state["_prec_grounding"] = _grounding
    # Did the search actually reach the web? (real sources were returned)
    _did_ground = bool(_grounding and _grounding.get("sources"))

    if raw and not raw.startswith(("⚠️", "🚫", "⏳")):
        data = safe_json_loads(raw, fallback={"cases": []})
        cases = data.get("cases", []) if isinstance(data, dict) else []

        # Verify each online case and add to combined results
        for case in cases:
            name = (case.get("name") or "").strip()
            citation = (case.get("citation") or "").strip()
            court = (case.get("court") or "").strip()
            year = (case.get("year") or "").strip()
            ratio = (case.get("ratio") or "").strip()
            relevance = (case.get("relevance") or "").strip()
            source_url = (case.get("source_url") or "").strip()

            if not name:
                continue

            # Skip duplicates
            if name.lower() in seen_names:
                continue
            seen_names.add(name.lower())

            # Run verification against local DB, grounding-aware so we never
            # overstate authenticity for an ungrounded (memory-only) result.
            verification = verify_online_case(name, citation, year, grounded=_did_ground)

            # If verified locally, use the canonical citation from DB
            if verification["local_match"]:
                match = verification["local_match"]
                citation = match.get("citation", citation)
                court = match.get("court", court)
                year = str(match.get("year", year))
                if not ratio:
                    ratio = match.get("principle", "")

            combined_results.append({
                "name": name,
                "citation": citation,
                "court": court,
                "year": year,
                "ratio": ratio,
                "relevance": relevance,
                "source_url": source_url,
                "confidence_tier": verification["confidence_tier"],
                "verification": verification,
                "source": "online",
            })

        # Store research notes and suggested statutes in session
        if isinstance(data, dict):
            st.session_state["_online_research_notes"] = data.get("research_notes", "")
            st.session_state["_online_suggested_statutes"] = data.get("suggested_statutes", [])
    else:
        st.session_state["_online_research_notes"] = ""
        st.session_state["_online_suggested_statutes"] = []

    # Sort: verified first, then web_sourced, then needs_verification
    tier_order = {"verified": 0, "web_sourced": 1, "needs_verification": 2}
    combined_results.sort(key=lambda x: tier_order.get(x["confidence_tier"], 3))

    return combined_results


def find_relevant_verified_cases(query: str, top_k: int = 5) -> list[dict]:
    """Re-export from citations for backward compatibility.
    Pages that barrel-import web_search will get this symbol.
    """
    from .citations import find_relevant_verified_cases as _real
    return _real(query, top_k=top_k)


def verify_citations_online(case_names: list, citations: list = None) -> str:
    """Confirm, via LIVE Google Search, whether the cited Nigerian cases /
    citations are REAL reported decisions (closing the gap where a genuine
    case simply isn't in the local verified database).

    The model is grounded on real web results and instructed never to guess —
    anything it cannot confirm from a real source is marked NOT FOUND. The real
    source URLs it used are captured into ``st.session_state['_last_grounding']``
    for display. Returns the verification text (or an error string).
    """
    generate = _get_generate()
    names = [str(n).strip() for n in (case_names or []) if n and str(n).strip()]
    cites = [str(c).strip() for c in (citations or []) if c and str(c).strip()]
    # De-dupe while preserving order.
    names = list(dict.fromkeys(names))
    cites = list(dict.fromkeys(cites))
    if not names and not cites:
        return ""

    name_block = "\n".join(f"{i}. {n}" for i, n in enumerate(names, 1)) or "(none)"
    cite_block = ""
    if cites:
        cite_block = "\nRAW CITATIONS ALSO MENTIONED:\n" + "\n".join(f"- {c}" for c in cites)

    system = (
        "You are a meticulous Nigerian legal citation verifier with LIVE Google "
        "Search access. Your ONLY job is to confirm, using real web search "
        "results, whether each case or citation below is a REAL, reported "
        "Nigerian decision. NEVER guess and NEVER invent a citation, court, "
        "year, or source URL. Rely solely on what the search results actually "
        "show. Be conservative: only mark a case REAL when a credible source "
        "clearly establishes it exists. If you cannot confirm a case from a "
        "real source, mark it NOT FOUND."
    )

    prompt = f"""Using live web search, verify each of the following Nigerian cases.

CASES TO VERIFY:
{name_block}
{cite_block}

For EACH case, output exactly one line in this format:
- <Case name> — STATUS: [REAL | NOT FOUND | UNCERTAIN] — Correct citation (if found): <citation or "—"> — Court/Year: <or "—"> — Source: <real URL or "none">

Hard rules:
1. Base every STATUS strictly on what the web search results actually show.
2. If no credible real source confirms a case, mark it NOT FOUND and put "none" as the source. Do NOT fabricate a citation or URL.
3. Mark UNCERTAIN only when sources are conflicting or ambiguous.
4. End with a one-line summary: "Summary: X REAL, Y NOT FOUND, Z UNCERTAIN."
"""

    return generate(
        prompt, system, "standard", "research",
        use_web_search=True, enable_quality_gate=False,
    )


def build_case_context(query: str, top_k: int = 6) -> str:
    """Retrieve the most relevant verified Nigerian cases for a query and
    format as grounding context. Mirrors ``build_rag_context()`` (which does
    the same for statutes) so AI calls are grounded against real case law.

    The injected block tells the AI to PREFER these cases over its own memory
    — the cases here have been hand-curated, so citations cannot drift.

    Returns empty string if no relevant verified cases are found, which lets
    the AI fall back to its own knowledge.
    """
    if not query or not query.strip():
        return ""

    from .citations import find_relevant_verified_cases
    matches = find_relevant_verified_cases(query, top_k=top_k)
    if not matches:
        return ""

    lines = [
        "═══ CANDIDATE VERIFIED NIGERIAN CASES (from LexiAssist verified database) ═══",
        "These cases are REAL (citations hand-verified) and were retrieved as",
        "POSSIBLY relevant to the query by keyword match. You MUST judge each one's",
        "actual relevance yourself:",
        "  • Cite a case ONLY if it genuinely supports the legal point at hand.",
        "  • SILENTLY IGNORE any listed case that is not on-point — do not mention",
        "    or cite an irrelevant case just because it appears here.",
        "  • When you do cite one, use its citation EXACTLY as shown below.",
        "  • You may also cite other landmark Nigerian cases you are confident are",
        "    real, but never invent or guess a citation.",
        "",
    ]
    for i, c in enumerate(matches, 1):
        name = c.get("name", "")
        citation = c.get("citation", "")
        court = c.get("court", "")
        year = c.get("year", "")
        principle = c.get("principle", "")
        lines.append(f"[{i}] {name} {citation} ({court}, {year})")
        if principle:
            lines.append(f"    Principle: {principle}")
        lines.append("")
    lines.append("═══ END VERIFIED CASE AUTHORITIES ═══")
    return "\n".join(lines)


def render_online_case_card(idx: int, case: dict) -> str:
    """Render a single online case result as styled HTML, with an honest
    authenticity badge and a clickable source link when one is available."""
    tier = case.get("confidence_tier", "needs_verification")
    name = esc(case.get("name", ""))
    citation = esc(case.get("citation", ""))
    court = esc(case.get("court", ""))
    year = esc(case.get("year", ""))
    ratio = esc(case.get("ratio", ""))
    relevance = esc(case.get("relevance", ""))
    source_url = (case.get("source_url") or "").strip()
    note = esc(case.get("verification", {}).get("note", "") or case.get("verification", {}).get("notes", ""))

    # Tier-based styling (translucent tints → readable on light AND dark themes)
    if tier == "verified":
        badge_label = "✅ Verified (in database)"
        badge_bg = "rgba(22,163,74,0.14)"
        badge_border = "#16a34a"
        badge_color = "#16a34a"
        if not note:
            note = "Confirmed in LexiAssist verified Nigerian case database — genuine, real case."
    elif tier == "web_sourced":
        badge_label = "🌐 Web-sourced — confirm source"
        badge_bg = "rgba(37,99,235,0.14)"
        badge_border = "#2563eb"
        badge_color = "#2563eb"
        if not note:
            note = ("Surfaced by a live web search with a valid citation format. "
                    "Open the source below and confirm the report before citing.")
    else:
        badge_label = "⚠️ Needs Verification"
        badge_bg = "rgba(220,38,38,0.12)"
        badge_border = "#dc2626"
        badge_color = "#dc2626"
        if not note:
            note = "MUST verify on NWLR/LPELR/LawPavilion before relying."

    # Court badge
    if "Supreme" in court:
        court_badge = "badge-err"
    elif "Appeal" in court:
        court_badge = "badge-warn"
    else:
        court_badge = "badge-ok"

    # Per-case source link (real evidence the lawyer can click)
    source_html = ""
    if source_url:
        safe_url = esc(source_url)
        source_html = (
            f'<div style="margin-top:0.4rem;font-size:0.82rem;">'
            f'🔗 <a href="{safe_url}" target="_blank" rel="noopener noreferrer" '
            f'style="color:#2563eb;font-weight:600;text-decoration:none;">'
            f'Open source to confirm</a></div>'
        )
    elif tier != "verified":
        source_html = (
            '<div style="margin-top:0.4rem;font-size:0.78rem;color:#dc2626;">'
            '⚠️ No source link returned for this case — treat as unconfirmed.</div>'
        )

    return f"""
<div class="custom-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;flex-wrap:wrap;">
    <h4 style="margin:0;">#{idx} · {name}</h4>
    <div style="display:flex;gap:0.4rem;flex-wrap:wrap;">
      <span class="badge {court_badge}">{court}</span>
      <span style="display:inline-block;background:{badge_bg};border:1px solid {badge_border};
                   color:{badge_color};padding:2px 8px;border-radius:999px;
                   font-size:0.72rem;font-weight:700;">{badge_label}</span>
    </div>
  </div>
  <div style="margin:0.4rem 0;">
    📖 <code>{citation}</code> · 📅 {year}
  </div>
  <div><strong>Ratio:</strong> {ratio}</div>
  <div style="color:var(--la-text2);">
    <strong>Why relevant:</strong> {relevance}
  </div>
  {source_html}
  <div style="margin-top:0.4rem;font-size:0.78rem;color:var(--la-text2);">
    {note}
  </div>
</div>"""
