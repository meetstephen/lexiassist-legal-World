"""LexiAssist AI Assistant page."""
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
# PAGE: AI ASSISTANT (FULL-FEATURED)
# ═══════════════════════════════════════════════════════
def render_ai():
    st.markdown("""<div class="page-header">
        <h2>🧠 AI Legal Assistant</h2>
        <p>Position-taking · Strategy-driven · Risk-ranked · Contract Review</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.api_configured:
        st.warning("⚠️ AI not connected. Configure your API key on the setup screen.")
        return

    mode = st.session_state.response_mode
    mode_info = RESPONSE_MODES[mode]
    st.info(f"**Mode: {mode_info['label']}** — {mode_info['desc']} (up to {mode_info['tokens']:,} tokens)")

    # ── Imported Document Context ──
    doc_context = ""
    if st.session_state.imported_doc:
        with st.expander(f"📎 Imported: {st.session_state.imported_doc['name']}", expanded=False):
            doc = st.session_state.imported_doc
            st.caption(f"Type: {doc['type'].upper()} · Size: {doc['size']:,} bytes")
            st.text_area("Preview", doc["preview"], height=120, disabled=True, key="doc_preview_ta")
            dc1, dc2 = st.columns(2)
            with dc1:
                if st.button("📋 Use as Context", key="use_doc_ctx_btn", use_container_width=True):
                    doc_context = doc["full_text"]
                    st.success("✅ Document loaded as context for your query.")
            with dc2:
                if st.button("🗑️ Clear Document", key="clear_doc_btn", use_container_width=True):
                    st.session_state.imported_doc = None
                    st.rerun()
        if not doc_context and st.session_state.imported_doc:
            doc_context = st.session_state.imported_doc.get("full_text", "")

    # ── Session History with Compare Selection ──
    if st.session_state.chat_history:
        with st.expander(f"📚 Session History ({len(st.session_state.chat_history)} entries) — select 2 to compare", expanded=False):
            # Compare selections
            compare_sels = st.session_state.get("compare_selections", [])

            for i, entry in enumerate(reversed(st.session_state.chat_history[-20:])):
                real_idx = len(st.session_state.chat_history) - 1 - i
                mode_lbl = RESPONSE_MODES.get(entry.get("mode", ""), {}).get("label", "")
                task_lbl = TASK_TYPES.get(entry.get("task", ""), {}).get("label", "")

                hc1, hc2, hc3 = st.columns([0.5, 4.5, 1])
                with hc1:
                    is_checked = real_idx in compare_sels
                    checked = st.checkbox(
                        "Sel", value=is_checked, key=f"cmp_chk_{real_idx}",
                        label_visibility="collapsed",
                    )
                    if checked and real_idx not in compare_sels:
                        compare_sels.append(real_idx)
                        if len(compare_sels) > 2:
                            compare_sels.pop(0)
                        st.session_state.compare_selections = compare_sels
                    elif not checked and real_idx in compare_sels:
                        compare_sels.remove(real_idx)
                        st.session_state.compare_selections = compare_sels

                with hc2:
                    st.markdown(f"""<div class="history-item">
                        <strong>{esc(entry.get('query', '')[:100])}</strong><br>
                        <small>{esc(entry.get('timestamp', ''))} · {esc(task_lbl)} · {esc(mode_lbl)} · {entry.get('word_count', 0)} words</small>
                    </div>""", unsafe_allow_html=True)
                with hc3:
                    if st.button("📖", key=f"load_hist_{real_idx}", use_container_width=True, help="Load this session"):
                        st.session_state.selected_history_idx = real_idx
                        st.session_state.last_response = entry["response"]
                        st.session_state.original_query = entry["query"]
                        st.session_state.last_task = entry.get("task", "general")
                        st.session_state.last_mode = entry.get("mode", "standard")
                        st.rerun()

            # Compare button
            compare_sels = st.session_state.get("compare_selections", [])
            if len(compare_sels) == 2:
                st.markdown("---")
                st.markdown(f"**📊 Compare:** Session {compare_sels[0]+1} vs Session {compare_sels[1]+1}")
                if st.button("🔬 Run Analysis Comparison", type="primary", key="run_compare_btn", use_container_width=True):
                    entry_a = st.session_state.chat_history[compare_sels[0]]
                    entry_b = st.session_state.chat_history[compare_sels[1]]
                    with st.spinner("🔬 Comparing analyses…"):
                        verdict = run_comparison(entry_a, entry_b)
                    st.session_state["comparison_result"] = verdict
                    st.rerun()
            elif len(compare_sels) == 1:
                st.caption("☑️ Select one more session to enable comparison.")

    # ── Show comparison result ──
    if st.session_state.get("comparison_result"):
        st.markdown("---")
        st.markdown("### 📊 Analysis Comparison Verdict")
        verdict = st.session_state["comparison_result"]
        st.markdown(f'<div class="response-box">{esc(verdict)}</div>', unsafe_allow_html=True)

        fname = f"LexiAssist_Comparison_{datetime.now():%Y%m%d_%H%M}"
        vc1, vc2, vc3, vc4 = st.columns(4)
        with vc1:
            st.download_button("📥 TXT", export_txt(verdict, "Analysis Comparison"), f"{fname}.txt", "text/plain", key="cmp_dl_txt", use_container_width=True)
        with vc2:
            st.download_button("📥 HTML", export_html(verdict, "Analysis Comparison"), f"{fname}.html", "text/html", key="cmp_dl_html", use_container_width=True)
        with vc3:
            safe_pdf_download(verdict, "Analysis Comparison", fname, "cmp_dl_pdf")
        with vc4:
            safe_docx_download(verdict, "Analysis Comparison", fname, "cmp_dl_docx")

        if st.button("✖️ Close Comparison", key="close_cmp_btn"):
            st.session_state["comparison_result"] = ""
            st.session_state.compare_selections = []
            st.rerun()
        st.markdown("---")

    # ── Show selected history entry ──
    if st.session_state.selected_history_idx is not None:
        idx = st.session_state.selected_history_idx
        if 0 <= idx < len(st.session_state.chat_history):
            entry = st.session_state.chat_history[idx]
            st.markdown("---")
            st.markdown(f"### 📖 Viewing: Session from {entry.get('timestamp', '')}")
            task_lbl = TASK_TYPES.get(entry.get("task", ""), {}).get("label", "")
            mode_lbl = RESPONSE_MODES.get(entry.get("mode", ""), {}).get("label", "")
            st.caption(f"{task_lbl} · {mode_lbl} · {entry.get('word_count', 0)} words")
            st.markdown(f"**Query:** {esc(entry['query'])}")
            st.markdown(f'<div class="response-box">{esc(entry["response"])}</div>', unsafe_allow_html=True)

            fname = f"LexiAssist_{entry.get('timestamp', '').replace(' ', '_').replace(':', '')}"
            hx1, hx2, hx3, hx4 = st.columns(4)
            with hx1:
                st.download_button("📥 TXT", export_txt(entry["response"]), f"{fname}.txt", "text/plain", key=f"hist_dl_txt_{idx}", use_container_width=True)
            with hx2:
                st.download_button("📥 HTML", export_html(entry["response"]), f"{fname}.html", "text/html", key=f"hist_dl_html_{idx}", use_container_width=True)
            with hx3:
                safe_pdf_download(entry["response"], "Legal Analysis", fname, f"hist_dl_pdf_{idx}")
            with hx4:
                safe_docx_download(entry["response"], "Legal Analysis", fname, f"hist_dl_docx_{idx}")

            if st.button("✖️ Close", key="close_hist_view"):
                st.session_state.selected_history_idx = None
                st.rerun()
            st.markdown("---")

    # ── Main Query Input ──
    st.markdown("### 💬 New Query")
    tc1, tc2 = st.columns([2, 1])
    with tc1:
        task_keys = list(TASK_TYPES.keys())
        task = st.selectbox(
            "Task Type", task_keys,
            format_func=lambda x: f"{TASK_TYPES[x]['label']} — {TASK_TYPES[x]['desc']}",
            key="ai_task_sel",
        )
    with tc2:
        st.markdown("")
        st.markdown(f"**Mode:** {mode_info['label']}")
        st.caption(f"Max output: {mode_info['tokens']:,} tokens")

    # Special hint for contract review
    if task == "contract_review":
        st.info("📑 **Contract Review Mode:** Paste or upload a contract. The AI will analyse each clause for risk, flag issues, and provide a red flag matrix with an overall signability grade.")

    # ── Phase 3: Contract Version Diffing ────────────────────────────────
        with st.expander("📄 Compare Contract Versions (V1 vs V2)", expanded=False):
            st.caption(
                "Paste two versions of the same contract to get a visual diff and "
                "AI explanation of what changed and the legal significance of each change."
            )
            diff_c1, diff_c2 = st.columns(2)
            with diff_c1:
                contract_v1 = st.text_area(
                    "Version 1 (Original / Older)",
                    height=200, key="diff_v1",
                    placeholder="Paste the original contract text here…",
                )
            with diff_c2:
                contract_v2 = st.text_area(
                    "Version 2 (Amended / Newer)",
                    height=200, key="diff_v2",
                    placeholder="Paste the amended contract text here…",
                )

            diff_btn = st.button(
                "🔬 Analyse Differences", key="diff_btn", type="primary",
                use_container_width=True,
                disabled=not (contract_v1.strip() and contract_v2.strip()),
            )

            if diff_btn and contract_v1.strip() and contract_v2.strip():
                import difflib

                # ── Visual line-by-line diff ──
                v1_lines = contract_v1.strip().splitlines(keepends=True)
                v2_lines = contract_v2.strip().splitlines(keepends=True)
                differ  = difflib.HtmlDiff(wrapcolumn=80)
                diff_html = differ.make_table(
                    v1_lines, v2_lines,
                    fromdesc="Version 1", todesc="Version 2",
                    context=True, numlines=3,
                )
                # Style the diff table inline
                styled_diff = (
                    '<style>'
                    '.diff_header{background:#1e3a5f;color:#fff;padding:2px 6px;font-size:0.78rem;}'
                    '.diff_next{background:#374151;color:#fff;}'
                    'td.diff_add{background:#d1fae5;}'
                    'td.diff_chg{background:var(--la-bg2);}'
                    'td.diff_sub{background:#fee2e2;}'
                    '.diff table{font-size:0.75rem;font-family:monospace;width:100%;}'
                    '</style>'
                    f'<div class="diff">{diff_html}</div>'
                )

                # ── AI legal significance analysis ──
                # Compute unified diff as text for the AI
                unified = "\n".join(
                    difflib.unified_diff(v1_lines, v2_lines, fromfile="V1", tofile="V2", lineterm="")
                )
                diff_prompt = (
                    "You are reviewing the following changes between two versions of a Nigerian contract.\n\n"
                    "UNIFIED DIFF (lines starting with '+' are NEW in V2, lines with '-' are REMOVED from V1):\n\n"
                    f"{unified[:6000]}\n\n"
                    "For EACH changed section:\n"
                    "1. WHAT CHANGED: Plain English explanation of the change\n"
                    "2. LEGAL SIGNIFICANCE: Risk level (🔴 High / 🟡 Medium / 🟢 Low) and why\n"
                    "3. WHO BENEFITS: Which party benefits from this change\n"
                    "4. RECOMMENDATION: Accept / Reject / Negotiate — and what counter-clause to propose\n\n"
                    "After all changes, provide:\n"
                    "═══ OVERALL ASSESSMENT ═══\n"
                    "▸ Net effect on Client's position: Stronger / Weaker / Neutral\n"
                    "▸ Most dangerous change: [what and why]\n"
                    "▸ Accept V2 as-is: Yes / No / Conditional"
                )
                with st.spinner("⚖️ Analysing legal significance of changes…"):
                    diff_analysis = generate(diff_prompt, IDENTITY_CORE, "standard", "contract_review")
                # Persist so the diff + analysis survive download-button reruns.
                st.session_state["diff_styled_html"] = styled_diff
                st.session_state["diff_analysis"] = diff_analysis
                st.rerun()

            # ── Render persisted diff results (outside the button branch) ──
            persisted_diff = st.session_state.get("diff_styled_html", "")
            persisted_diff_analysis = st.session_state.get("diff_analysis", "")
            if persisted_diff and persisted_diff_analysis:
                st.markdown("##### 📊 Visual Diff")
                st.markdown(persisted_diff, unsafe_allow_html=True)
                st.markdown("##### ⚖️ Legal Significance Analysis")
                st.markdown(
                    f'<div class="response-box">{esc(persisted_diff_analysis)}</div>',
                    unsafe_allow_html=True,
                )
                diff_fname = f"LexiAssist_ContractDiff_{datetime.now():%Y%m%d_%H%M}"
                dlc1, dlc2 = st.columns([3, 1])
                with dlc1:
                    st.download_button(
                        "📥 Download Analysis (TXT)",
                        export_txt(persisted_diff_analysis, "Contract Version Analysis"),
                        f"{diff_fname}.txt", "text/plain",
                        key="diff_dl_txt", use_container_width=True,
                    )
                with dlc2:
                    if st.button("🗑️ Clear Diff", key="diff_clear_btn",
                                 use_container_width=True):
                        st.session_state.pop("diff_styled_html", None)
                        st.session_state.pop("diff_analysis", None)
                        st.rerun()
    
    # ── Example queries (one-click prefill) ────────────────────────────
    # Lawyers in their first 5 minutes don't know what to type. These four
    # chips demonstrate the AI's strongest capabilities — limitation maths,
    # pre-action procedure, drafting, contract review — across a Nigerian
    # legal context. Click → fills the text area → user can edit or run.
    EXAMPLE_QUERIES = [
        ("⏳ Limitation",
         "Compute the limitation period: my client was injured in a road "
         "accident on 15 March 2022 in Lagos. The negligent driver works "
         "for the Federal Ministry of Health. No action has been filed "
         "yet. What deadlines apply, and which Limitation Law governs?"),
        ("📨 Pre-action",
         "Client wants to sue Lagos State Government for breach of a "
         "contract worth ₦50M, terminated in January 2024. No pre-action "
         "steps taken yet. Walk me through every pre-action requirement "
         "I must satisfy, in order, with statutory authority and "
         "consequences of omission."),
        ("📜 Drafting",
         "Draft a Memorandum of Understanding between two Nigerian "
         "private companies for a joint venture in Lagos: shared "
         "R&D, 60/40 profit split, 3-year term, Lagos arbitration "
         "clause. Use [PLACEHOLDER] for missing details."),
        ("📑 Contract risk",
         'Review this clause for risks acting for the Client: '
         '"The Service Provider may suspend or terminate this Agreement '
         'at any time, with or without cause, without liability to the '
         'Client." Give a risk grade, who benefits, and a counter-clause.'),
    ]
    prefill = st.session_state.pop("loaded_template", "") if "loaded_template" in st.session_state and st.session_state.get("loaded_template") else ""
    # If the user clicked an example chip on the previous run, that text now
    # lives in _ai_example_prefill and we use it as the seed value here.
    if not prefill and st.session_state.get("_ai_example_prefill"):
        prefill = st.session_state.pop("_ai_example_prefill", "")

    if not st.session_state.get("ai_query_ta", "") and not prefill:
        st.caption("✨ Try one of these to see what LexiAssist can do:")
        ex_cols = st.columns(len(EXAMPLE_QUERIES))
        for col, (label, text) in zip(ex_cols, EXAMPLE_QUERIES):
            with col:
                if st.button(
                    label, key=f"ai_example_{label}",
                    use_container_width=True,
                    help="Click to load this example into the query box below.",
                ):
                    st.session_state["_ai_example_prefill"] = text
                    st.rerun()

    query = st.text_area(
        "Your Legal Query",
        value=prefill,
        height=200,
        placeholder="Describe your legal question in detail…\n\nFor Contract Review: paste the full contract text here, or upload the document via the sidebar.",
        key="ai_query_ta",
    )

    # ── Action Buttons ──
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        generate_btn = st.button(
            f"🧠 Generate ({mode_info['label']})",
            type="primary", use_container_width=True,
            disabled=not query.strip(), key="ai_generate_btn",
        )
    with bc2:
        issue_btn = st.button(
            "🔍 Issue Spot", use_container_width=True,
            disabled=not query.strip(), key="ai_issue_btn",
        )
    with bc3:
        clear_btn = st.button(
            "🗑️ Clear", use_container_width=True, key="ai_clear_btn",
        )

    if clear_btn:
        st.session_state.last_response = ""
        st.session_state.original_query = ""
        st.session_state.selected_history_idx = None
        st.session_state["comparison_result"] = ""
        st.session_state.compare_selections = []
        st.rerun()

    # ── Empty-query guard ──
    if (generate_btn or issue_btn) and not query.strip():
        st.warning("⚠️ Please enter your legal query before generating a response.")

    # ── Issue Spotting ──
    if issue_btn and query.strip():
        with st.spinner("🔍 Decomposing issues…"):
            result = run_issue_spot(query.strip())
        # Persist so the result survives reruns from any subsequent click.
        st.session_state["issue_spot_result"] = result
        st.session_state["issue_spot_query"] = query.strip()
        st.rerun()

    # Render persisted issue-spot output (outside the button branch).
    issue_result = st.session_state.get("issue_spot_result", "")
    if issue_result and issue_result.strip():
        st.markdown("### 🔍 Issue Decomposition")
        st.markdown(f'<div class="response-box">{esc(issue_result)}</div>',
                    unsafe_allow_html=True)
        if st.button("🗑️ Clear Issue Decomposition", key="issue_spot_clear_btn"):
            st.session_state.pop("issue_spot_result", None)
            st.session_state.pop("issue_spot_query", None)
            st.rerun()

    # ── Main Generation (with streaming + audit + confidence) ──
    if generate_btn and query.strip():
        st.markdown("### 📋 Analysis (streaming…)")
        stream_container = st.container()
        start_t = time.time()

        # Build prompt with optional document context
        system = build_system_prompt(task, mode, query.strip())
        full_prompt = query.strip()
        if doc_context:
            full_prompt = f"DOCUMENT CONTEXT:\n{sanitize_doc_context(doc_context)[:8500]}\n\nQUERY:\n{query.strip()}"

        with st.spinner(f"🧠 Streaming {mode_info['label']} analysis…"):
            result = generate(full_prompt, system, mode, task, stream_to=stream_container)
        elapsed = time.time() - start_t

        # Citation audit + confidence scoring
        audit = verify_response_citations(result)
        confidence = compute_confidence_score(result, audit)

        st.session_state.last_response = result
        st.session_state.last_audit = audit
        st.session_state.last_confidence = confidence
        st.session_state.original_query = query.strip()
        st.session_state.last_task = task
        st.session_state.last_mode = mode
        st.session_state.selected_history_idx = None
        add_to_history(query.strip(), result, task, mode)

        get_db().append_audit("AI_QUERY", f"task={task} mode={mode} words={len(result.split())} q={query.strip()[:120]}")
        st.caption(f"⏱️ Generated in {elapsed:.1f}s · {len(result.split()):,} words · "
                   f"Confidence: {confidence['overall']}/10")

    # ── Display Response (extracted) ──
    _render_ai_response(mode)




def _render_ai_response(mode: str) -> None:
    """Render the AI response display: confidence panel, citation audit,
    structured output, case strength meter, follow-up, exports, save-to-case."""
    # ── Display Response ──
    if st.session_state.last_response and st.session_state.selected_history_idx is None:
        response = st.session_state.last_response
        st.markdown("---")
        task_lbl = TASK_TYPES.get(st.session_state.get("last_task", "general"), {}).get("label", "Analysis")
        st.markdown(f"### 📋 {task_lbl} Result")
        # ── Confidence + Citation Audit panels ──
        confidence = st.session_state.get("last_confidence", {})
        audit = st.session_state.get("last_audit", {})
        if confidence:
            st.markdown(render_confidence_panel(confidence), unsafe_allow_html=True)
        if audit:
            st.markdown(render_citation_audit(audit), unsafe_allow_html=True)

        # Export row
        fname = f"LexiAssist_Analysis_{datetime.now():%Y%m%d_%H%M}"
        ex1, ex2, ex3, ex4 = st.columns(4)
        with ex1:
            st.download_button("📥 TXT", export_txt(response), f"{fname}.txt", "text/plain", key="resp_dl_txt", use_container_width=True)
        with ex2:
            st.download_button("📥 HTML", export_html(response), f"{fname}.html", "text/html", key="resp_dl_html", use_container_width=True)
        with ex3:
            safe_pdf_download(response, "Legal Analysis", fname, "resp_dl_pdf")
        with ex4:
            safe_docx_download(response, "Legal Analysis", fname, "resp_dl_docx")

        # ── Structured output: Verified Law / Analysis / To Confirm ──
        with st.expander("🗂️ Structured Output — Law · Analysis · To Verify", expanded=False):
            st.caption(
                "LexiAssist automatically categorises output into three sections. "
                "Always verify 'To Confirm' items before advising any client."
            )
            _struct_prompt = f"""
Analyse this legal response and extract content into exactly three JSON sections.
Respond ONLY in this JSON format, nothing else:
{{
  "verified_law": [
    {{"item": "CAMA 2020 s. 141 — minimum share capital for private companies", "type": "Statute"}},
    {{"item": "Madukolu v Nkemdilim (1962) — jurisdiction test", "type": "Case"}}
  ],
  "analysis": [
    {{"item": "Based on CAMA 2020, the company has failed to comply with minimum capital requirements"}}
  ],
  "to_confirm": [
    {{"item": "Current Lagos High Court filing fees — verify at registry", "reason": "Fees change without notice"}},
    {{"item": "Recent Court of Appeal decision on similar facts", "reason": "AI may not have latest authority"}}
  ]
}}

Rules:
- verified_law: only confirmed Nigerian statutes, regulations, and well-known case authorities explicitly cited
- analysis: the substantive legal reasoning, strategy, or advice drawn from the law
- to_confirm: anything requiring independent verification — fees, recent cases, uncertain facts, state-specific rules

RESPONSE TO ANALYSE:
{response[:5000]}
"""
            if st.button("⚡ Generate Structured View", key="struct_view_btn", type="primary"):
                with st.spinner("Extracting structured sections…"):
                    _struct_raw = generate(_struct_prompt, IDENTITY_CORE, "brief", "analysis")
                try:
                    _s = json.loads(_struct_raw.strip().replace("```json","").replace("```","").strip())
                    st.session_state["_struct_output"] = _s
                except Exception:
                    st.warning("Could not parse structured output. Try again.")
            _struct = st.session_state.get("_struct_output", {})
            if _struct:
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    st.markdown("##### ✅ Verified Law")
                    for _it in _struct.get("verified_law", []):
                        _badge = "🏛️" if _it.get("type") == "Case" else "📜"
                        st.markdown(
                            f'<div style="background:#f0fdf4;border-left:3px solid #16a34a;'
                            f'border-radius:6px;padding:0.4rem 0.7rem;margin-bottom:0.4rem;'
                            f'font-size:0.82rem;">{_badge} {esc(_it.get("item",""))}</div>',
                            unsafe_allow_html=True,
                        )
                    if not _struct.get("verified_law"):
                        st.caption("No specific authorities extracted.")
                with sc2:
                    st.markdown("##### 🧠 Analysis")
                    for _it in _struct.get("analysis", []):
                        st.markdown(
                            f'<div style="background:var(--la-bg2);border-left:3px solid #6366f1;'
                            f'border-radius:6px;padding:0.4rem 0.7rem;margin-bottom:0.4rem;'
                            f'font-size:0.82rem;">{esc(_it.get("item",""))}</div>',
                            unsafe_allow_html=True,
                        )
                    if not _struct.get("analysis"):
                        st.caption("No analysis points extracted.")
                with sc3:
                    st.markdown("##### ⚠️ To Confirm")
                    for _it in _struct.get("to_confirm", []):
                        st.markdown(
                            f'<div style="background:var(--la-bg2);border-left:3px solid #f59e0b;'
                            f'border-radius:6px;padding:0.4rem 0.7rem;margin-bottom:0.4rem;'
                            f'font-size:0.82rem;"><strong>{esc(_it.get("item",""))}</strong>'
                            f'<br><small style="color:var(--la-text);">{esc(_it.get("reason",""))}</small></div>',
                            unsafe_allow_html=True,
                        )
                    if not _struct.get("to_confirm"):
                        st.caption("Nothing flagged for verification.")

        st.markdown(f'<div class="response-box">{esc(response)}</div>', unsafe_allow_html=True)

        # ── Copy to clipboard (iframe-safe fallback) ──
        _copy_html = f"""
<style>
#la-copy-btn {{
    display:inline-flex; align-items:center; gap:6px;
    padding:5px 14px; border-radius:6px; border:1px solid rgba(128,128,128,0.35);
    background:transparent; cursor:pointer; font-size:13px;
    color:inherit; font-family:inherit; margin-bottom:4px;
    transition:background 0.15s;
}}
#la-copy-btn:hover {{ background:rgba(128,128,128,0.12); }}
</style>
<textarea id="la-copy-src" style="position:fixed;opacity:0;pointer-events:none;top:-9999px;left:-9999px;">{html_mod.escape(response)}</textarea>
<div style="text-align:right; padding:4px 0 0 0;">
  <button id="la-copy-btn" onclick="(function(){{
    var b=document.getElementById('la-copy-btn');
    var txt=document.getElementById('la-copy-src');
    txt.value=txt.textContent;
    function markOk(){{b.innerHTML='&#10003;&nbsp;Copied!';b.style.color='#16a34a';setTimeout(function(){{b.innerHTML='&#128203;&nbsp;Copy response';b.style.color=''}},2200);}}
    function markFail(){{b.innerHTML='&#10007;&nbsp;Try Ctrl+C';b.style.color='#dc2626';setTimeout(function(){{b.innerHTML='&#128203;&nbsp;Copy response';b.style.color=''}},2200);}}
    if(navigator.clipboard && window.isSecureContext){{
      navigator.clipboard.writeText(txt.value).then(markOk).catch(function(){{
        txt.select();try{{document.execCommand('copy')?markOk():markFail()}}catch(e){{markFail()}}
      }});
    }} else {{
      txt.select();txt.setSelectionRange(0,999999);
      try{{document.execCommand('copy')?markOk():markFail()}}catch(e){{markFail()}}
    }}
  }})()">&#128203;&nbsp;Copy response</button>
</div>"""
        st.components.v1.html(_copy_html, height=60)

        # ── CASE STRENGTH METER ──
        if st.session_state.get("last_task") in ("analysis", "advisory", "contract_review"):
            with st.expander("📊 Case Strength Meter", expanded=True):
                st.caption("AI-assessed win probability per party based on the analysis above.")
                if st.button("⚡ Generate Strength Assessment", key="strength_meter_btn", type="primary"):
                    strength_prompt = f"""
Based on this legal analysis, extract ALL parties mentioned and estimate each party's
litigation strength as a percentage.
Respond ONLY in this exact JSON format, nothing else:
{{
  "parties": [
    {{"name": "Party Name", "role": "Claimant/Defendant/Third Party", "strength": 75, "reason": "One sentence why"}},
    {{"name": "Party Name", "role": "Defendant", "strength": 35, "reason": "One sentence why"}}
  ],
  "overall_complexity": "Low/Medium/High/Extreme",
  "recommended_action": "One sentence immediate action"
}}
ANALYSIS:
{response[:6000]}
"""
                    with st.spinner("Calculating case strength..."):
                        raw = generate(strength_prompt, IDENTITY_CORE, "brief", "analysis")
                    # Persist parsed data so reruns (e.g. from Save / Follow-up
                    # button clicks) don't blank the strength bars.
                    parsed = safe_json_loads(raw, fallback=None)
                    if parsed:
                        st.session_state["strength_data"] = parsed
                        st.session_state.pop("strength_raw_fb", None)
                    else:
                        st.session_state["strength_data"] = None
                        st.session_state["strength_raw_fb"] = raw
                    st.rerun()

                # ── Render persisted strength assessment ──
                strength_data = st.session_state.get("strength_data")
                if strength_data:
                    for p in strength_data.get("parties", []):
                        strength = int(p.get("strength", 50))
                        color = "#dc2626" if strength < 40 else ("#f59e0b" if strength < 65 else "#059669")
                        bar_html = f"""
<div style="margin-bottom:1rem;">
  <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
    <strong>{esc(p['name'])}</strong>
    <span class="badge badge-info">{esc(p['role'])}</span>
    <strong style="color:{color};">{strength}%</strong>
  </div>
  <div style="background:#e5e7eb;border-radius:999px;height:14px;">
    <div style="width:{strength}%;background:{color};height:14px;border-radius:999px;"></div>
  </div>
  <small style="color:var(--la-text2);">{esc(p.get('reason',''))}</small>
</div>"""
                        st.markdown(bar_html, unsafe_allow_html=True)
                    st.markdown(f"**Complexity:** `{strength_data.get('overall_complexity','—')}`")
                    st.markdown(f"**Immediate Action:** {esc(strength_data.get('recommended_action','—'))}")
                else:
                    strength_raw_fb = st.session_state.get("strength_raw_fb", "")
                    if strength_raw_fb and strength_raw_fb.strip():
                        st.warning(
                            "⚠️ Could not parse the case-strength response. "
                            "Showing raw AI output below:"
                        )
                        st.markdown(
                            f'<div class="response-box">{esc(strength_raw_fb)}</div>',
                            unsafe_allow_html=True,
                        )
                    elif "strength_raw_fb" in st.session_state:
                        st.warning(
                            "⚠️ The AI returned an empty response. Click "
                            "**Generate Strength Assessment** again to retry."
                        )

                # ── STRATEGY SIMULATOR (inside same expander) ──
                st.markdown("---")
                st.markdown("#### 🎯 Strategy Simulator — *What If We Do X?*")
                st.caption("Simulate any litigation move and get AI probability, risks, and opponent counter-strategy.")

                sim_cols = st.columns([3, 1])
                with sim_cols[0]:
                    sim_action = st.text_input(
                        "Proposed Action",
                        placeholder="e.g. File a preliminary objection challenging jurisdiction",
                        key="sim_action_inp",
                        label_visibility="collapsed",
                    )
                with sim_cols[1]:
                    sim_btn = st.button(
                        "🎯 Simulate",
                        key="sim_run_btn",
                        type="primary", use_container_width=True,
                        disabled=not sim_action.strip(),
                    )

                # Quick action buttons
                st.caption("Quick simulations:")
                qa1, qa2, qa3, qa4 = st.columns(4)
                with qa1:
                    if st.button("Preliminary Objection", key="qa1_btn", use_container_width=True):
                        st.session_state["sim_prefill"] = "File a preliminary objection challenging the court's jurisdiction"
                        st.rerun()
                with qa2:
                    if st.button("Strike Out Application", key="qa2_btn", use_container_width=True):
                        st.session_state["sim_prefill"] = "File an application to strike out the suit for want of locus standi"
                        st.rerun()
                with qa3:
                    if st.button("Interlocutory Injunction", key="qa3_btn", use_container_width=True):
                        st.session_state["sim_prefill"] = "Apply for an interlocutory injunction to preserve the subject matter"
                        st.rerun()
                with qa4:
                    if st.button("Settlement Offer", key="qa4_btn", use_container_width=True):
                        st.session_state["sim_prefill"] = "Make a without-prejudice settlement offer to the opposing party"
                        st.rerun()

                # Apply prefill if set
                if st.session_state.get("sim_prefill"):
                    sim_action = st.session_state.pop("sim_prefill")

                if sim_btn and sim_action.strip():
                    sim_prompt = f"""
You are a senior Nigerian litigation strategist. A lawyer is considering the following
litigation action in the case described below. Analyse it fully.

Respond ONLY in this exact JSON format, nothing else:
{{
  "action": "The proposed action",
  "probability_of_success": 72,
  "verdict": "RECOMMENDED/RISKY/DO NOT PROCEED",
  "reasoning": "2-3 sentences explaining the probability",
  "risks": [
    "Risk 1",
    "Risk 2",
    "Risk 3"
  ],
  "opponent_counter_strategy": [
    "What opponent will likely do in response 1",
    "What opponent will likely do in response 2"
  ],
  "our_counter_to_counter": [
    "How we neutralise opponent response 1",
    "How we neutralise opponent response 2"
  ],
  "better_alternative": "A better action to consider, or empty string if this is already optimal",
  "nigerian_authority": "The most relevant Nigerian case or statute supporting or opposing this action"
}}

CASE ANALYSIS CONTEXT:
{response[:5000]}

PROPOSED ACTION: {sim_action}
"""
                    with st.spinner("🎯 Simulating strategy..."):
                        sim_raw = generate(sim_prompt, IDENTITY_CORE, "brief", "advisory")
                    # Persist so the simulation survives subsequent reruns.
                    parsed_sim = safe_json_loads(sim_raw, fallback=None)
                    if parsed_sim:
                        st.session_state["sim_data"] = parsed_sim
                        st.session_state["sim_action_text"] = sim_action.strip()
                        st.session_state.pop("sim_raw_fb", None)
                        # Save simulation to case history
                        if st.session_state.cases:
                            sim_text = (
                                f"STRATEGY SIMULATION\n"
                                f"Action: {parsed_sim.get('action','')}\n"
                                f"Probability: {parsed_sim.get('probability_of_success',0)}%\n"
                                f"Verdict: {parsed_sim.get('verdict','')}\n"
                                f"Reasoning: {parsed_sim.get('reasoning','')}\n"
                            )
                            add_to_history(
                                f"[Strategy Sim] {sim_action[:80]}",
                                sim_text, "advisory", "brief",
                            )
                    else:
                        st.session_state["sim_data"] = None
                        st.session_state["sim_raw_fb"] = sim_raw
                    st.rerun()

                # ── Render persisted simulation result ──
                sim_data = st.session_state.get("sim_data")
                if sim_data:
                    prob = int(sim_data.get("probability_of_success", 50))
                    verdict = sim_data.get("verdict", "RISKY")

                    if verdict == "RECOMMENDED":
                        verdict_color = "#059669"
                        verdict_bg = "#f0fdf4"
                        verdict_icon = "✅"
                    elif verdict == "DO NOT PROCEED":
                        verdict_color = "#dc2626"
                        verdict_bg = "#fef2f2"
                        verdict_icon = "🚫"
                    else:
                        verdict_color = "#d97706"
                        verdict_bg = "#fffbeb"
                        verdict_icon = "⚠️"

                    prob_color = "#dc2626" if prob < 40 else ("#f59e0b" if prob < 65 else "#059669")

                    st.markdown(f"""
<div style="background:{verdict_bg};border:2px solid {verdict_color};
border-radius:0.75rem;padding:1.2rem;margin-top:1rem;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem;">
    <h4 style="margin:0;color:{verdict_color};">
      {verdict_icon} {esc(sim_data.get('action',''))}
    </h4>
    <span style="font-size:1.6rem;font-weight:800;color:{prob_color};">{prob}%</span>
  </div>
  <div style="background:#e5e7eb;border-radius:999px;height:12px;margin-bottom:0.8rem;">
    <div style="width:{prob}%;background:{prob_color};height:12px;border-radius:999px;"></div>
  </div>
  <p style="margin:0;">{esc(sim_data.get('reasoning',''))}</p>
</div>""", unsafe_allow_html=True)

                    sr1, sr2 = st.columns(2)
                    with sr1:
                        st.markdown("**🔴 Risks:**")
                        for r in sim_data.get("risks", []):
                            st.markdown(f"- {esc(r)}")
                        st.markdown("**⚔️ Opponent Will:**")
                        for c in sim_data.get("opponent_counter_strategy", []):
                            st.markdown(f"- {esc(c)}")
                    with sr2:
                        st.markdown("**🛡️ Our Counter:**")
                        for cc in sim_data.get("our_counter_to_counter", []):
                            st.markdown(f"- {esc(cc)}")
                        if sim_data.get("nigerian_authority"):
                            st.markdown(f"**📖 Authority:** {esc(sim_data['nigerian_authority'])}")

                    if sim_data.get("better_alternative"):
                        st.info(f"💡 **Better Alternative:** {sim_data['better_alternative']}")
                else:
                    sim_raw_fb = st.session_state.get("sim_raw_fb", "")
                    if sim_raw_fb and sim_raw_fb.strip():
                        st.warning(
                            "⚠️ Could not parse the strategy simulation. "
                            "Showing raw AI output below:"
                        )
                        st.markdown(
                            f'<div class="response-box">{esc(sim_raw_fb)}</div>',
                            unsafe_allow_html=True,
                        )
                    elif "sim_raw_fb" in st.session_state:
                        st.warning(
                            "⚠️ The AI returned an empty response. Click "
                            "**Simulate** again to retry."
                        )

        # ── SAVE TO CASE ──
        cases = st.session_state.cases
        if cases:
            st.markdown("### 💾 Save to Case")
            stc1, stc2 = st.columns([3, 1])
            with stc1:
                case_names = [f"{c.get('title', 'Untitled')} ({c.get('suit_no', '—')})" for c in cases]
                selected_case = st.selectbox(
                    "Select case to attach this analysis:",
                    case_names, key="save_to_case_sel", label_visibility="collapsed",
                )
            with stc2:
                if st.button("💾 Save", key="save_to_case_btn", type="primary", use_container_width=True):
                    case_idx = case_names.index(selected_case)
                    target_case = cases[case_idx]
                    save_analysis_to_case(
                        target_case["id"],
                        st.session_state.original_query,
                        response,
                        st.session_state.get("last_task", "general"),
                        st.session_state.get("last_mode", "standard"),
                    )
                    st.success(f"✅ Analysis saved to case: {target_case.get('title', '')}")

        # Quality critique
        if mode in ("standard", "comprehensive"):
            with st.expander("🔎 Quality Assessment", expanded=False):
                if st.button("Run Critique", key="run_critique_btn"):
                    with st.spinner("Assessing quality…"):
                        critique = run_critique(st.session_state.original_query, response)
                    st.session_state["critique_result"] = critique
                    st.rerun()
                # Render persisted critique outside the button branch.
                critique_result = st.session_state.get("critique_result", "")
                if critique_result and critique_result.strip():
                    st.markdown(
                        f'<div class="response-box">{esc(critique_result)}</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button("🗑️ Clear Critique", key="critique_clear_btn"):
                        st.session_state.pop("critique_result", None)
                        st.rerun()
                elif "critique_result" in st.session_state:
                    st.warning(
                        "⚠️ The critique came back empty. Click "
                        "**Run Critique** again to retry."
                    )

        # Follow-up
        st.markdown("### 🔄 Follow-Up Question")
        followup = st.text_input(
            "Ask a follow-up based on the analysis above:",
            placeholder="E.g.: 'What if the contract had an arbitration clause?'",
            key="followup_input",
        )
        if st.button("🔄 Follow Up", disabled=not followup.strip(), key="followup_btn"):
            with st.spinner("🔄 Processing follow-up…"):
                fu_result = run_followup(
                    st.session_state.original_query,
                    response, followup.strip(), mode,
                )
            st.session_state.last_response = fu_result
            add_to_history(f"[Follow-up] {followup.strip()}", fu_result, "general", mode)
            st.rerun()

        st.markdown('<div class="disclaimer"><strong>⚖️ Disclaimer:</strong> AI-generated legal analysis. This does not constitute legal advice. Verify all citations and authorities independently before reliance.</div>', unsafe_allow_html=True)
