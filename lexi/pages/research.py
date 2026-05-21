"""LexiAssist legal-research, authority-verification, and source-backed research pages."""
from __future__ import annotations

# Barrel import: mirrors the global namespace of the original single-file
# app.py exactly. The original code below is unchanged.
from ..runtime import *      # noqa: F401, F403
from ..crypto import *       # noqa: F401, F403
from ..constants import *    # noqa: F401, F403
from ..prompts import *      # noqa: F401, F403
from ..legal_data import *   # noqa: F401, F403
from ..citations import *    # noqa: F401, F403
from ..themes import *       # noqa: F401, F403
from ..rag import *          # noqa: F401, F403
from ..fuzzy import *        # noqa: F401, F403
from ..exports import *      # noqa: F401, F403
from ..database import *     # noqa: F401, F403
from ..auth import *         # noqa: F401, F403
from ..helpers import *      # noqa: F401, F403

# ═══════════════════════════════════════════════════════
# PAGE: LEGAL RESEARCH
# ═══════════════════════════════════════════════════════
def render_research():
    st.markdown("""<div class="page-header">
        <h2>📚 Legal Research</h2>
        <p>Case law · Statutes · Authorities · Research Memoranda</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key first.")
        return

    mode = st.session_state.response_mode
    mode_info = RESPONSE_MODES[mode]
    st.info(f"**Research Mode: {mode_info['label']}** — {mode_info['desc']}")

    query = st.text_area(
        "🔍 Research Query", height=140,
        placeholder="E.g.: 'What are the grounds for setting aside an arbitral award under the Arbitration and Mediation Act 2023?'",
        key="research_query_ta",
    )

    # ── Quick Precedent Finder (grounded against verified Nigerian case DB) ──
    with st.expander("🔖 Quick Precedent Finder", expanded=False):
        st.caption(
            "Returns Nigerian cases grounded against LexiAssist's verified case "
            "database. Every result is tagged ✅ Verified or ⚠️ Unverified — "
            "the AI is forbidden from inventing citations."
        )
        prec_cols = st.columns([3, 1])
        with prec_cols[0]:
            prec_query = st.text_input(
                "Legal Issue",
                placeholder="e.g. unlawful termination of employment, right of pre-emption in land law",
                key="prec_query_inp",
                label_visibility="collapsed",
            )
        with prec_cols[1]:
            prec_btn = st.button(
                "🔖 Find Cases",
                key="prec_btn",
                disabled=not prec_query.strip(), use_container_width=True,
                type="primary",
            )
        if prec_btn and prec_query.strip():
            # 1. Retrieval — pull candidates from the verified DB so the AI is
            #    ranking real cases, not inventing them.
            grounded = find_relevant_verified_cases(prec_query.strip(), top_k=8)
            if grounded:
                grounding_block = (
                    "═══ VERIFIED CANDIDATE CASES (from the LexiAssist verified Nigerian case database) ═══\n"
                    "These are the ONLY cases you should rank and explain. Use the citation EXACTLY as given.\n"
                    "Do NOT invent additional cases.\n\n"
                    + "\n".join(
                        f"- {g['name']} {g['citation']} ({g['court']}, {g['year']}) — {g['principle']}"
                        for g in grounded
                    )
                    + "\n═══ END CANDIDATES ═══\n"
                )
                target_n = min(5, len(grounded))
                instruction = (
                    f"From the VERIFIED CANDIDATE CASES above, select the TOP {target_n} most "
                    f"relevant to the legal issue and explain each. You MUST return at least "
                    f"one case from the candidate list — do NOT return an empty array when "
                    f"candidates have been provided. Use the citation EXACTLY as provided. "
                    f"Do NOT add any case that is not in the candidate list."
                )
            else:
                # No DB matches — ask AI for well-known cases on this topic.
                # Encourage at least one suggestion since "there is a case for
                # every legal matter".
                grounding_block = (
                    "═══ NO VERIFIED CANDIDATES FOUND ═══\n"
                    "The LexiAssist verified database has no matching cases for this issue, "
                    "so suggest well-established Nigerian precedents you are confident about.\n"
                    "═══ END ═══\n"
                )
                target_n = 5
                instruction = (
                    f"Provide UP TO {target_n} well-established Nigerian precedents on this "
                    f"legal issue. Always return at least one case — every Nigerian legal "
                    f"issue has at least one leading authority. Each citation MUST be one you "
                    f"are confident is real (e.g. classic cases like Madukolu v Nkemdilim, "
                    f"Ariori v Elemo, etc.). Do not invent obscure citations."
                )

            prec_prompt = f"""{grounding_block}

LEGAL ISSUE: {prec_query.strip()}

{instruction}

Respond ONLY in this exact JSON format, nothing else:
{{
  "cases": [
    {{
      "name": "Full case name (X v Y)",
      "citation": "(year) volume report (Pt. X) page",
      "court": "Supreme Court | Court of Appeal | Federal High Court | National Industrial Court",
      "year": "YYYY",
      "ratio": "One sentence — the legal principle established",
      "relevance": "One sentence — why this case applies to the issue"
    }}
  ]
}}

HARD RULES:
1. NEVER invent a case name or citation.
2. When candidates have been provided, ALWAYS pick at least one — never return [].
3. Use the candidate citations EXACTLY as written above.
"""
            with st.spinner("🔖 Searching Nigerian precedents…"):
                raw = generate(prec_prompt, IDENTITY_CORE, "brief", "research")

            # Persist the run so results survive Streamlit reruns and we
            # can render outside this button-click branch (which means
            # users no longer see a momentary screen that goes blank when
            # ``prec_btn`` flips back to False on the next rerun).
            st.session_state["_prec_query"] = prec_query.strip()
            st.session_state["_prec_grounded"] = grounded
            st.session_state["_prec_raw"] = raw

        # ── Render persisted Quick Precedent Finder results ─────────────
        # Reads from session_state so results survive reruns. Falls back
        # gracefully and silently — no error banners, no "AI declined"
        # messages — because there is a case for every legal matter, and
        # the verified DB usually has at least one good candidate.
        prec_raw_persisted = st.session_state.get("_prec_raw")
        if prec_raw_persisted is not None:
            grounded_persisted = st.session_state.get("_prec_grounded", []) or []

            # Silent JSON parse — no warnings displayed for this feature.
            # If parsing fails we treat ai_cases as empty and fall through
            # to the grounded-DB rendering path.
            data = safe_json_loads(prec_raw_persisted, fallback={"cases": []})
            ai_cases = data.get("cases", []) if isinstance(data, dict) else []

            verified_count = 0
            unverified_count = 0
            grounded_names = {g["name"].lower() for g in grounded_persisted}

            def _render_case_card(
                idx, canonical_name, canonical_court, canonical, canonical_year,
                ratio, relevance, badge_label, badge_bg, badge_border,
                badge_color, note,
            ):
                if "Supreme" in canonical_court:
                    court_badge = "badge-err"
                elif "Appeal" in canonical_court:
                    court_badge = "badge-warn"
                else:
                    court_badge = "badge-ok"
                st.markdown(
                    f"""
<div class="custom-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;flex-wrap:wrap;">
    <h4 style="margin:0;">#{idx} · {esc(canonical_name)}</h4>
    <div style="display:flex;gap:0.4rem;flex-wrap:wrap;">
      <span class="badge {court_badge}">{esc(canonical_court)}</span>
      <span style="display:inline-block;background:{badge_bg};border:1px solid {badge_border};
                   color:{badge_color};padding:2px 8px;border-radius:999px;
                   font-size:0.72rem;font-weight:700;">{badge_label}</span>
    </div>
  </div>
  <div style="margin:0.4rem 0;">
    📖 <code>{esc(canonical)}</code> · 📅 {esc(canonical_year)}
  </div>
  <div><strong>Ratio:</strong> {esc(ratio)}</div>
  <div style="color:var(--la-text2);">
    <strong>Why relevant:</strong> {esc(relevance)}
  </div>
  <div style="margin-top:0.4rem;font-size:0.78rem;color:{badge_color};">
    {esc(note)}
  </div>
</div>""",
                    unsafe_allow_html=True,
                )

            # Decide what to render. Three scenarios, all handled silently.
            if ai_cases:
                cases_to_render = ai_cases
                render_mode = "ai"
            elif grounded_persisted:
                # AI returned nothing parseable but the verified DB has
                # candidates. Synthesise card data from the DB so the user
                # always sees relevant authorities.
                cases_to_render = [
                    {
                        "name": g.get("name", ""),
                        "court": g.get("court", ""),
                        "citation": g.get("citation", ""),
                        "year": str(g.get("year", "")),
                        "ratio": g.get("principle", ""),
                        "relevance": (
                            "Verified Nigerian authority surfaced for this issue from "
                            "the LexiAssist case database."
                        ),
                    }
                    for g in grounded_persisted[:5]
                ]
                render_mode = "grounded"
            else:
                cases_to_render = []
                render_mode = "empty"

            for i, case in enumerate(cases_to_render, 1):
                name = (case.get("name") or "").strip()
                court = (case.get("court") or "").strip()
                ai_citation = (case.get("citation") or "").strip()
                year = (case.get("year") or "").strip()
                ratio = (case.get("ratio") or "").strip()
                relevance = (case.get("relevance") or "").strip()

                # Authoritative lookup against the verified DB.
                match = verify_case_name(name) if name else None
                # Treat as verified if either the AI picked a candidate we
                # passed in, OR the name matches the DB at all, OR we
                # rendered straight from the grounded DB list.
                is_grounded_pick = name.lower() in grounded_names
                is_verified = bool(match) or is_grounded_pick or render_mode == "grounded"

                # Use canonical citation from DB whenever possible, so the AI
                # cannot accidentally drift the citation.
                if match:
                    canonical = match["citation"]
                    canonical_court = match.get("court", court)
                    canonical_year = str(match.get("year", year))
                    canonical_name = match["name"]
                else:
                    canonical = ai_citation
                    canonical_court = court
                    canonical_year = year
                    canonical_name = name

                if is_verified:
                    verified_count += 1
                    badge_label = "✅ Verified"
                    badge_bg = "#dcfce7"
                    badge_border = "#16a34a"
                    badge_color = "#14532d"
                    note = (
                        "Citation taken from the LexiAssist verified Nigerian case database."
                        if (match or render_mode == "grounded") else
                        "Selected from the verified candidate set passed to the AI."
                    )
                else:
                    unverified_count += 1
                    badge_label = "⚠️ Unverified"
                    badge_bg = "#fef2f2"
                    badge_border = "#dc2626"
                    badge_color = "#991b1b"
                    note = (
                        "Not found in the LexiAssist verified database. "
                        "Verify on NWLR / LPELR / LawPavilion before citing or filing."
                    )

                _render_case_card(
                    i, canonical_name, canonical_court, canonical, canonical_year,
                    ratio, relevance, badge_label, badge_bg, badge_border,
                    badge_color, note,
                )

            # Summary banner — only when we actually rendered something.
            if cases_to_render:
                if unverified_count == 0 and verified_count > 0:
                    st.success(
                        f"✅ All {verified_count} case(s) above are grounded in the "
                        f"verified Nigerian case database."
                    )
                elif verified_count > 0 and unverified_count > 0:
                    st.warning(
                        f"⚠️ {verified_count} verified · {unverified_count} unverified. "
                        f"Treat the unverified entries as suggestions only — confirm in "
                        f"NWLR / LPELR / LawPavilion before relying on them."
                    )
                else:
                    st.warning(
                        f"⚠️ {unverified_count} suggested case(s) above could not be "
                        f"matched against the verified database. Confirm on "
                        f"NWLR / LPELR / LawPavilion before citing."
                    )
            # When literally nothing came back (no DB candidates AND no AI
            # cases) we deliberately stay quiet — the user can either
            # rephrase the legal issue or use the full Research flow below.

            # Always offer a way to clear stale results.
            if st.button("🗑️ Clear Precedent Results", key="prec_clear_btn"):
                for k in ("_prec_raw", "_prec_grounded", "_prec_query"):
                    st.session_state.pop(k, None)
                st.rerun()
    st.markdown("---")
    rc1, rc2 = st.columns([1, 1])
    with rc1:
        research_btn = st.button(
            f"📚 Research ({mode_info['label']})",
            type="primary", use_container_width=True,
            disabled=not query.strip(), key="research_go_btn",
        )
    with rc2:
        clear_btn = st.button("🗑️ Clear Results", use_container_width=True, key="research_clear_btn")

    if clear_btn:
        st.session_state.research_results = ""
        st.rerun()

    if research_btn and query.strip():
        with st.spinner("📚 Researching…"):
            start_t = time.time()
            result = run_research(query.strip(), mode)
            elapsed = time.time() - start_t
        st.session_state.research_results = result
        add_to_history(f"[Research] {query.strip()}", result, "research", mode)
        st.caption(f"⏱️ {elapsed:.1f}s · {len(result.split()):,} words")

    result = st.session_state.research_results
    if result:
        st.markdown("---")
        fname = f"LexiAssist_Research_{datetime.now():%Y%m%d_%H%M}"
        ex1, ex2, ex3, ex4 = st.columns(4)
        with ex1:
            st.download_button("📥 TXT", export_txt(result, "Legal Research"), f"{fname}.txt", "text/plain", key="res_dl_txt", use_container_width=True)
        with ex2:
            st.download_button("📥 HTML", export_html(result, "Legal Research"), f"{fname}.html", "text/html", key="res_dl_html", use_container_width=True)
        with ex3:
            safe_pdf_download(result, "Legal Research", fname, "res_dl_pdf")
        with ex4:
            safe_docx_download(result, "Legal Research", fname, "res_dl_docx", doc_type="research")

        st.markdown(f'<div class="response-box">{esc(result)}</div>', unsafe_allow_html=True)

        # Save research to case
        cases = st.session_state.cases
        if cases:
            st.markdown("### 💾 Save to Case")
            stc1, stc2 = st.columns([3, 1])
            with stc1:
                case_names_r = [f"{c.get('title', 'Untitled')} ({c.get('suit_no', '—')})" for c in cases]
                sel_case_r = st.selectbox("Select case:", case_names_r, key="res_save_case_sel", label_visibility="collapsed")
            with stc2:
                if st.button("💾 Save", key="res_save_case_btn", type="primary", use_container_width=True):
                    cidx = case_names_r.index(sel_case_r)
                    target = cases[cidx]
                    save_analysis_to_case(target["id"], f"[Research] {query.strip()}", result, "research", mode)
                    st.success(f"✅ Research saved to case: {target.get('title', '')}")

        st.markdown('<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated research. Verify all citations independently.</div>', unsafe_allow_html=True)


def render_authority_verification():
    st.markdown("""<div class="page-header">
        <h2>🔍 Authority Verification Mode</h2>
        <p>Check cases, statutes, repealed laws, foreign authorities, and possible hallucinations</p>
    </div>""", unsafe_allow_html=True)

    st.markdown(
        '<div style="background:var(--la-bg2);border:1px solid var(--la-border);'
        'border-left:4px solid #3b82f6;border-radius:8px;'
        'padding:0.75rem 1rem;margin-bottom:1rem;font-size:0.85rem;">'
        '<strong>How it works:</strong> LexiAssist first performs deterministic checks '
        'against its verified Nigerian case database and repealed-law map, then classifies '
        'every authority found. Always verify independently before filing.'
        '</div>',
        unsafe_allow_html=True,
    )

    av_text = st.text_area(
        "Paste legal text, AI output, pleading, research memo, or authorities to verify",
        height=260,
        key="authority_verify_text",
        placeholder=(
            "Example:\n"
            "The court has jurisdiction under Madukolu v Nkemdilim. "
            "The Companies and Allied Matters Act 1990 applies. "
            "See Donoghue v Stevenson on duty of care."
        ),
    )

    run_btn = st.button(
        "🔍 Verify Authorities",
        type="primary",
        use_container_width=True,
        disabled=not av_text.strip(),
        key="authority_verify_btn",
    )

    if run_btn:
        deterministic = []

        # Case-name extraction and deterministic case verification
        case_names_found = extract_case_names(av_text)
        for name in case_names_found:
            match = verify_case_name(name)
            if match:
                deterministic.append({
                    "authority": match["name"],
                    "type": "Case",
                    "status": "Verified",
                    "problem": "",
                    "fix": f"Verified: {match.get('citation', '')} — {match.get('principle', '')}",
                    "confidence": 95,
                })
            else:
                deterministic.append({
                    "authority": name,
                    "type": "Case",
                    "status": "Unverified",
                    "problem": "Case name not found in the local verified Nigerian case database.",
                    "fix": "Verify on NWLR, LPELR, LawPavilion, or official law report before citing.",
                    "confidence": 60,
                })

        deterministic.extend(scan_repealed_laws(av_text))
        deterministic.extend(scan_foreign_authorities(av_text))

        # Citation-shaped strings
        citations = extract_citations(av_text)
        for c in citations:
            raw_cit = c.get("raw", "")
            if raw_cit and not any(r["authority"] == raw_cit for r in deterministic):
                deterministic.append({
                    "authority": raw_cit,
                    "type": "Citation",
                    "status": "Needs Verification",
                    "problem": "Citation format detected, but citation-to-case mapping is not confirmed locally.",
                    "fix": "Verify the citation against NWLR/LPELR/LawPavilion before relying.",
                    "confidence": 70,
                })

        if not deterministic:
            deterministic.append({
                "authority": "No authorities detected",
                "type": "None",
                "status": "No Authority Found",
                "problem": "The text does not appear to contain case names or citation-shaped references.",
                "fix": "If this is a legal argument, add specific statutes, rules, or case authorities.",
                "confidence": 80,
            })

        st.session_state["_authority_results"] = deterministic

    results = st.session_state.get("_authority_results", [])

    if results:
        st.markdown("---")
        st.markdown(f"### Verification Results — {len(results)} item(s)")

        counts = {}
        for r in results:
            counts[r["status"]] = counts.get(r["status"], 0) + 1

        cols = st.columns(min(4, max(1, len(counts))))
        for col, (status, count) in zip(cols, counts.items()):
            with col:
                st.metric(status, count)

        status_meta = {
            "Verified":           ("#16a34a", "#f0fdf4", "✅"),
            "Unverified":         ("#d97706", "#fffbeb", "⚠️"),
            "Repealed":           ("#dc2626", "#fef2f2", "🚫"),
            "Foreign":            ("#0891b2", "#ecfeff", "🌍"),
            "Needs Verification": ("#7c3aed", "#faf5ff", "📌"),
            "No Authority Found": ("#64748b", "#f8fafc", "ℹ️"),
        }

        for r in results:
            colour, bg, icon = status_meta.get(r["status"], ("#64748b", "#f8fafc", "❓"))
            st.markdown(
                f'<div style="background:{bg};border:1px solid {colour};'
                f'border-left:4px solid {colour};border-radius:8px;'
                f'padding:0.85rem 1rem;margin-bottom:0.55rem;">'
                f'<strong style="color:{colour};">{icon} {esc(r["authority"])}</strong> '
                f'<span style="font-size:0.75rem;color:{colour};font-weight:700;">'
                f'[{esc(r["type"])} · {esc(r["status"])} · {r.get("confidence", 0)}%]</span>'
                f'<br><small><strong>Problem:</strong> {esc(r.get("problem", "") or "None")}</small>'
                f'<br><small><strong>Fix:</strong> {esc(r.get("fix", ""))}</small>'
                f'</div>',
                unsafe_allow_html=True,
            )

        report = "AUTHORITY VERIFICATION REPORT\n"
        report += f"Generated: {datetime.now():%d %B %Y at %H:%M}\n"
        report += "=" * 60 + "\n\n"
        for r in results:
            report += f"Authority: {r['authority']}\n"
            report += f"Type: {r['type']}\n"
            report += f"Status: {r['status']}\n"
            report += f"Confidence: {r.get('confidence', 0)}%\n"
            report += f"Problem: {r.get('problem', '')}\n"
            report += f"Fix: {r.get('fix', '')}\n\n"

        st.download_button(
            "📥 Download Verification Report",
            export_txt(report, "Authority Verification Report"),
            f"Authority_Verification_{datetime.now():%Y%m%d_%H%M}.txt",
            "text/plain",
            key="authority_report_download",
            use_container_width=True,
        )

        st.markdown(
            '<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> '
            'This verification tool is a screening aid. Always confirm authorities from '
            'official law reports, NWLR, LPELR, LawPavilion, court rules, or primary legislation.'
            '</div>',
            unsafe_allow_html=True,
        )


def render_source_backed_research():
    st.markdown("""<div class="page-header">
        <h2>🔗 Source-Backed Research</h2>
        <p>Research from user-provided statutes, case extracts, regulator publications, URLs, or pasted source text</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key first.")
        return

    st.markdown(
        '<div style="background:var(--la-bg2);border:1px solid var(--la-border);'
        'border-left:4px solid #059669;border-radius:8px;'
        'padding:0.75rem 1rem;margin-bottom:1rem;font-size:0.85rem;">'
        '<strong>Best for beta:</strong> Paste source extracts from statutes, judgments, regulator pages, '
        'law reports, court rules, or official publications. LexiAssist will analyse only the provided material '
        'and clearly flag what still needs verification.'
        '</div>',
        unsafe_allow_html=True,
    )

    query = st.text_area(
        "Research Question",
        height=120,
        key="sbr_query",
        placeholder="E.g. What is the current position on setting aside arbitral awards under the Arbitration and Conciliation Act 2023?",
    )

    sources = st.text_area(
        "Provided Sources / Extracts / URLs",
        height=260,
        key="sbr_sources",
        placeholder=(
            "Paste source extracts here.\n\n"
            "Example:\n"
            "SOURCE 1: Arbitration and Conciliation Act 2023, section ...\n"
            "Extract: ...\n\n"
            "SOURCE 2: Supreme Court case extract ...\n"
            "Extract: ...\n\n"
            "URL-only sources may be included but must be independently verified."
        ),
    )

    mode = st.session_state.response_mode

    run_btn = st.button(
        "🔗 Run Source-Backed Research",
        type="primary",
        use_container_width=True,
        disabled=not (query.strip() and sources.strip()),
        key="sbr_run_btn",
    )

    if run_btn:
        prompt = (
            f"RESEARCH QUESTION:\n{query.strip()}\n\n"
            f"USER-PROVIDED SOURCES:\n{sanitize_doc_context(sources.strip())}\n\n"
            "Prepare a source-backed Nigerian legal research memorandum.\n\n"
            "Required structure:\n"
            "1. Short Answer\n"
            "2. Sources Reviewed\n"
            "3. What the Sources Establish\n"
            "4. Nigerian Legal Analysis\n"
            "5. Unsupported / To Verify\n"
            "6. Practical Implications for Counsel\n"
            "7. Verification Checklist"
        )
        with st.spinner("🔗 Analysing provided sources..."):
            result = generate(prompt, SOURCE_BACKED_RESEARCH_SYSTEM, mode, "analysis")

        st.session_state["sbr_result"] = result
        add_to_history(f"[Source-Backed Research] {query[:100]}", result, "analysis", mode)
        st.rerun()

    result = st.session_state.get("sbr_result", "")
    if result and result.strip():
        st.markdown("---")
        st.markdown("### 🔗 Source-Backed Research Result")

        fname = f"SourceBackedResearch_{datetime.now():%Y%m%d_%H%M}"
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.download_button("📥 TXT", export_txt(result, "Source-Backed Research"),
                               f"{fname}.txt", "text/plain", key="sbr_txt", use_container_width=True)
        with c2:
            st.download_button("📥 HTML", export_html(result, "Source-Backed Research"),
                               f"{fname}.html", "text/html", key="sbr_html", use_container_width=True)
        with c3:
            safe_pdf_download(result, "Source-Backed Research", fname, "sbr_pdf")
        with c4:
            safe_docx_download(result, "Source-Backed Research", fname, "sbr_docx", doc_type="research")

        st.markdown(f'<div class="response-box">{esc(result)}</div>', unsafe_allow_html=True)

        st.markdown(
            '<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> Source-backed research is only as reliable '
            'as the supplied sources. Verify all source extracts against official/publication copies before relying.</div>',
            unsafe_allow_html=True,
        )
    elif "sbr_result" in st.session_state:
        # We ran the analysis but the model returned nothing usable —
        # surface a friendly message so the user knows to retry, instead
        # of leaving them staring at a silent blank.
        st.markdown("---")
        st.warning(
            "⚠️ The AI returned an empty response. This usually means a "
            "transient model timeout. Click **Run Source-Backed Research** "
            "again to retry."
        )

