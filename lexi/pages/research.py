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

    # ── Quick Precedent Finder (combines local verified DB + online AI knowledge) ──
    with st.expander("🔖 Quick Precedent Finder", expanded=False):
        st.caption(
            "Combines LexiAssist's verified case database with AI online knowledge "
            "to find relevant Nigerian cases. Verified cases from the local database "
            "are always prioritised. All results are tagged with confidence tiers: "
            "✅ Verified · 🟡 High Confidence · ⚠️ Needs Verification."
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
            from ..web_search import search_cases_online, render_online_case_card

            # Always combine local DB + online search
            with st.spinner("🔖 Searching Nigerian precedents (verified DB + online)…"):
                combined_results = search_cases_online(prec_query.strip(), max_results=10)

            st.session_state["_prec_online_results"] = combined_results
            st.session_state["_prec_query"] = prec_query.strip()
            st.session_state["_prec_mode"] = "combined"
            # Clear any old-style results
            st.session_state.pop("_prec_raw", None)
            st.session_state.pop("_prec_grounded", None)
            st.rerun()

        # ── Render persisted results ─────────────────────────────────────
        prec_mode = st.session_state.get("_prec_mode")

        if prec_mode in ("online", "combined"):
            from ..web_search import render_online_case_card
            online_results = st.session_state.get("_prec_online_results", [])

            if online_results:
                # Summary stats
                verified_n = sum(1 for r in online_results if r["confidence_tier"] == "verified")
                high_conf_n = sum(1 for r in online_results if r["confidence_tier"] == "high_confidence")
                needs_ver_n = sum(1 for r in online_results if r["confidence_tier"] == "needs_verification")
                local_n = sum(1 for r in online_results if r.get("source") == "local_db")
                online_n = sum(1 for r in online_results if r.get("source") == "online")

                summary_parts = []
                if verified_n:
                    summary_parts.append(f"✅ {verified_n} verified")
                if high_conf_n:
                    summary_parts.append(f"🟡 {high_conf_n} high confidence")
                if needs_ver_n:
                    summary_parts.append(f"⚠️ {needs_ver_n} needs verification")

                source_info = ""
                if local_n and online_n:
                    source_info = f" &nbsp;|&nbsp; 📁 {local_n} from DB · 🌐 {online_n} online"
                elif local_n:
                    source_info = f" &nbsp;|&nbsp; 📁 {local_n} from verified DB"

                st.markdown(
                    f'<div style="background:var(--la-bg2);border:1px solid var(--la-border);'
                    f'border-radius:8px;padding:0.6rem 1rem;margin-bottom:0.8rem;font-size:0.85rem;">'
                    f'<strong>📊 Results:</strong> {" · ".join(summary_parts)}{source_info}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                for i, case in enumerate(online_results, 1):
                    st.markdown(render_online_case_card(i, case), unsafe_allow_html=True)

                # Research notes
                notes = st.session_state.get("_online_research_notes", "")
                if notes:
                    st.info(f"📝 **Research Notes:** {notes}")

                suggested = st.session_state.get("_online_suggested_statutes", [])
                if suggested:
                    st.markdown("**📜 Also consider these statutes:**")
                    for s in suggested:
                        st.markdown(f"- {s}")

                # Summary message
                if needs_ver_n > 0 and verified_n > 0:
                    st.warning(
                        f"⚠️ {verified_n} verified case(s) prioritised from the local database. "
                        f"{needs_ver_n} additional case(s) from online search require independent "
                        f"verification on NWLR / LPELR / LawPavilion before citing."
                    )
                elif needs_ver_n > 0:
                    st.warning(
                        f"⚠️ {needs_ver_n} case(s) above require independent verification. "
                        f"Check NWLR / LPELR / LawPavilion before citing in any filing."
                    )
                elif high_conf_n > 0 and verified_n > 0:
                    st.success(
                        f"✅ {verified_n} case(s) verified from the local database. "
                        f"{high_conf_n} additional case(s) have valid citation format — "
                        f"confirm on NWLR/LPELR before relying."
                    )
                elif verified_n > 0 and high_conf_n == 0 and needs_ver_n == 0:
                    st.success(f"✅ All {verified_n} case(s) are verified in the local database.")

            if st.button("🗑️ Clear Precedent Results", key="prec_clear_btn"):
                for k in ("_prec_raw", "_prec_grounded", "_prec_query",
                          "_prec_online_results", "_prec_mode",
                          "_online_research_notes", "_online_suggested_statutes"):
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

