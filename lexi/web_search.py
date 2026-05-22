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


def verify_online_case(case_name: str, citation: str = "", year: str = "") -> dict:
    """Verify a case against the local verified database and apply heuristic
    checks on the citation format.

    Returns a dict with:
      - verified: bool (True if found in local DB)
      - confidence_tier: "verified" | "high_confidence" | "needs_verification"
      - local_match: dict or None (the matching DB entry if found)
      - citation_format_valid: bool
      - notes: str
    """
    from .citations import verify_case_name

    # Check local DB
    local_match = verify_case_name(case_name)

    # Citation format heuristic for Nigerian law reports
    citation_valid = False
    if citation:
        # Common Nigerian citation formats:
        # (YYYY) NN NWLR (Pt. NNN) NNN
        # (YYYY) N SC NNN
        # (YYYY) N SCNLR NNN
        # (YYYY) LPELR-NNNNN(SC)
        nwlr_pattern = r"\(\d{4}\)\s+\d+\s+NWLR\s+\(Pt\.\s*\d+\)"
        sc_pattern = r"\(\d{4}\)\s+\d+\s+SC\s+\d+"
        scnlr_pattern = r"\(\d{4}\)\s+\d+\s+SCNLR\s+\d+"
        lpelr_pattern = r"LPELR[-\s]*\d+"
        other_pattern = r"\(\d{4}\)\s+\d+\s+(NWLR|WLR|FWLR|All NLR|ANLR)"

        if any(re.search(p, citation, re.IGNORECASE) for p in [
            nwlr_pattern, sc_pattern, scnlr_pattern, lpelr_pattern, other_pattern
        ]):
            citation_valid = True

    # Determine confidence tier
    if local_match:
        tier = "verified"
        notes = "Found in LexiAssist verified Nigerian case database."
    elif citation_valid and year and int(year) <= datetime.now().year:
        tier = "high_confidence"
        notes = (
            "Not in local DB but citation format is valid and consistent. "
            "High confidence — verify on NWLR/LPELR before citing in court."
        )
    else:
        tier = "needs_verification"
        notes = (
            "Not in local DB and citation format could not be validated. "
            "MUST verify on NWLR/LPELR/LawPavilion before relying."
        )

    return {
        "verified": bool(local_match),
        "confidence_tier": tier,
        "local_match": local_match,
        "citation_format_valid": citation_valid,
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
            "relevance": "Verified Nigerian authority directly relevant to this legal issue.",
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

    prompt = f"""You are a senior Nigerian legal research specialist with deep knowledge of
Nigerian case law from the Supreme Court, Court of Appeal, Federal High Court,
National Industrial Court, and State High Courts.

TASK: Find additional relevant Nigerian cases for the following legal issue.
You MUST only return cases you are HIGHLY CONFIDENT are real reported decisions.

LEGAL ISSUE: {legal_issue}{case_context}
JURISDICTION: {jurisdiction}{already_have}

STRICT RULES:
1. ONLY return cases you are confident exist in Nigerian law reports (NWLR, SC, SCNLR, FWLR, LPELR).
2. Prefer well-known, landmark decisions that are widely cited.
3. Include the FULL citation in standard Nigerian format: (YYYY) NN NWLR (Pt. NNN) NNN
4. If you cannot recall the exact citation, use the format you are most confident about.
5. Include a mix of Supreme Court and Court of Appeal decisions where possible.
6. For each case, state the RATIO DECIDENDI (the legal principle established).
7. Explain WHY the case is relevant to the specific legal issue raised.
8. NEVER invent a case name or fabricate a citation. If unsure, omit that case entirely.
9. Return UP TO {max(3, max_results - len(local_cases))} cases, ranked by relevance.
10. Do NOT repeat any case already listed above.

Respond ONLY in this exact JSON format:
{{
  "cases": [
    {{
      "name": "Full case name (Plaintiff v Defendant)",
      "citation": "(YYYY) NN NWLR (Pt. NNN) NNN",
      "court": "Supreme Court | Court of Appeal | Federal High Court | NIC",
      "year": "YYYY",
      "ratio": "The legal principle established in this case",
      "relevance": "Why this case is directly relevant to the legal issue"
    }}
  ],
  "research_notes": "Any important context about the state of law on this issue",
  "suggested_statutes": ["Relevant statutes to also consider"]
}}
"""

    raw = generate(prompt, identity, "standard", "research")

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

            if not name:
                continue

            # Skip duplicates
            if name.lower() in seen_names:
                continue
            seen_names.add(name.lower())

            # Run verification against local DB
            verification = verify_online_case(name, citation, year)

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

    # Sort: verified first, then high_confidence, then needs_verification
    tier_order = {"verified": 0, "high_confidence": 1, "needs_verification": 2}
    combined_results.sort(key=lambda x: tier_order.get(x["confidence_tier"], 3))

    return combined_results


def find_relevant_verified_cases(query: str, top_k: int = 5) -> list[dict]:
    """Re-export from citations for backward compatibility.
    Pages that barrel-import web_search will get this symbol.
    """
    from .citations import find_relevant_verified_cases as _real
    return _real(query, top_k=top_k)


def render_online_case_card(idx: int, case: dict) -> str:
    """Render a single online case result as styled HTML."""
    tier = case.get("confidence_tier", "needs_verification")
    name = esc(case.get("name", ""))
    citation = esc(case.get("citation", ""))
    court = esc(case.get("court", ""))
    year = esc(case.get("year", ""))
    ratio = esc(case.get("ratio", ""))
    relevance = esc(case.get("relevance", ""))

    # Tier-based styling
    if tier == "verified":
        badge_label = "✅ Verified"
        badge_bg = "#dcfce7"
        badge_border = "#16a34a"
        badge_color = "#14532d"
        note = "Confirmed in LexiAssist verified Nigerian case database."
    elif tier == "high_confidence":
        badge_label = "🟡 High Confidence"
        badge_bg = "#fef3c7"
        badge_border = "#d97706"
        badge_color = "#92400e"
        note = "Valid citation format. Verify on NWLR/LPELR before citing."
    else:
        badge_label = "⚠️ Needs Verification"
        badge_bg = "#fef2f2"
        badge_border = "#dc2626"
        badge_color = "#991b1b"
        note = "MUST verify on NWLR/LPELR/LawPavilion before relying."

    # Court badge
    if "Supreme" in court:
        court_badge = "badge-err"
    elif "Appeal" in court:
        court_badge = "badge-warn"
    else:
        court_badge = "badge-ok"

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
  <div style="margin-top:0.4rem;font-size:0.78rem;color:{badge_color};">
    {esc(note)}
  </div>
</div>"""
