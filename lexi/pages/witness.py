"""LexiAssist witness preparation engine."""
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
# PAGE: WITNESS PREPARATION ENGINE
# ═══════════════════════════════════════════════════════
def _wp_extract_section(text: str, header_fragment: str) -> str:
    """Extract text between two witness prep section headers."""
    lines = text.split("\n")
    capture = False
    collected = []
    for line in lines:
        if header_fragment.upper() in line.upper() and "═" in line:
            capture = True
            continue
        if capture and "═══" in line and collected:
            break
        if capture:
            collected.append(line)
    return "\n".join(collected).strip()


def render_witness_prep():
    st.markdown("""<div class="page-header">
        <h2>🎯 Witness Preparation Engine</h2>
        <p>Input case facts and witness role → Examination-in-chief · Cross-exam risks ·
        Re-examination · Coaching notes · Multi-witness contradiction check</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key first.")
        return

    # Ensure session log exists
    if "wp_witness_log" not in st.session_state:
        st.session_state["wp_witness_log"] = []

    # ── Main tabs ──
    tab_prep, tab_log, tab_contra = st.tabs([
        "🎯 Prepare a Witness",
        f"👥 Witness Log ({len(st.session_state['wp_witness_log'])})",
        "🔍 Contradiction Check",
    ])

    # ═══════════════════════════════════════════════════
    # TAB 1 — PREPARE A WITNESS
    # ═══════════════════════════════════════════════════
    with tab_prep:
        wp1, wp2 = st.columns([2, 1])
        with wp1:
            wp_facts = st.text_area(
                "Case Facts *",
                height=210,
                key="wp_facts_ta",
                placeholder="""Describe the key facts of the case as they relate to this witness.

Example: The witness, Mrs Amaka Obi, is a neighbour of the claimant. She was present on
3 January 2024 when the defendant's vehicle collided with the claimant's gate at Ikeja.
She heard the crash, came outside within 2 minutes, saw the defendant exit the vehicle,
and heard him say 'I lost control'. She took three photographs on her phone.
Opponent may argue she was too far away to hear clearly and has a prior land dispute
with the defendant.""",
            )
        with wp2:
            wp_role = st.text_input(
                "Witness Role *",
                key="wp_role_inp",
                placeholder="e.g. Eyewitness, Expert (valuation), Claimant",
            )
            wp_name = st.text_input(
                "Witness Name (optional)",
                key="wp_name_inp",
                placeholder="e.g. Mrs Amaka Obi",
            )
            wp_case_type = st.selectbox(
                "Case Type (optional)",
                ["— Select —"] + CASE_TYPE_OPTIONS,
                key="wp_case_type_sel",
            )
            case_type_val = "" if wp_case_type == "— Select —" else wp_case_type
            mode = st.session_state.response_mode
            st.info(f"Mode: {RESPONSE_MODES[mode]['label']}")
            wp_generate_btn = st.button(
                "🎯 Prepare Witness",
                type="primary", use_container_width=True,
                key="wp_generate_btn",
                disabled=not (wp_facts.strip() and wp_role.strip()),
            )

        if wp_generate_btn and wp_facts.strip() and wp_role.strip():
            prompt = WITNESS_PREP_PROMPT.format(
                case_facts=wp_facts.strip(),
                witness_role=wp_role.strip(),
                case_type=case_type_val or "Not specified",
            )
            with st.spinner("🎯 Preparing witness brief…"):
                raw = generate(prompt, WITNESS_PREP_SYSTEM, mode, "analysis")
            label = wp_name.strip() or wp_role.strip()
            st.session_state["wp_result"] = raw
            st.session_state["wp_role_label"] = label
            st.session_state["wp_facts_saved"] = wp_facts.strip()
            # Add to witness log only if the AI actually returned content
            # — avoids polluting the log with empty entries.
            if raw and raw.strip():
                st.session_state["wp_witness_log"].append({
                    "id": new_id(),
                    "name": wp_name.strip() or f"Witness {len(st.session_state['wp_witness_log'])+1}",
                    "role": wp_role.strip(),
                    "case_type": case_type_val or "Not specified",
                    "facts": wp_facts.strip(),
                    "result": raw,
                    "timestamp": datetime.now().strftime("%d %b %Y %H:%M"),
                })
            st.rerun()

        # ── Display result ──
        result = st.session_state.get("wp_result", "")
        role_label = st.session_state.get("wp_role_label", "Witness")
        facts_saved = st.session_state.get("wp_facts_saved", "")

        if result and result.strip():
            st.markdown("---")
            sec1 = _wp_extract_section(result, "EXAMINATION-IN-CHIEF")
            sec2 = _wp_extract_section(result, "CROSS-EXAMINATION")
            sec3 = _wp_extract_section(result, "COACHING NOTES")

            if not (sec1 and sec2 and sec3):
                st.markdown(f'<div class="response-box">{esc(result)}</div>', unsafe_allow_html=True)
            else:
                s1_tab, s2_tab, s3_tab, s4_tab = st.tabs([
                    "📋 Examination-in-Chief",
                    "⚔️ Cross-Examination Risks",
                    "🧭 Coaching Notes",
                    "↩️ Re-Examination",
                ])

                with s1_tab:
                    st.markdown(f"""
<div style="background:#f0fdf4;border-left:4px solid #059669;border-radius:0.75rem;
padding:1.5rem;line-height:1.8;">
  <h4 style="margin:0 0 1rem 0;color:#059669;">📋 Examination-in-Chief — {esc(role_label)}</h4>
  <div style="white-space:pre-wrap;font-size:0.95rem;">{esc(sec1)}</div>
</div>""", unsafe_allow_html=True)

                with s2_tab:
                    st.markdown(f"""
<div style="background:#fef2f2;border-left:4px solid #dc2626;border-radius:0.75rem;
padding:1.5rem;line-height:1.8;">
  <h4 style="margin:0 0 1rem 0;color:#dc2626;">⚔️ Cross-Examination Risks</h4>
  <div style="white-space:pre-wrap;font-size:0.95rem;">{esc(sec2)}</div>
</div>""", unsafe_allow_html=True)

                with s3_tab:
                    st.markdown(f"""
<div style="background:#fffbeb;border-left:4px solid #f59e0b;border-radius:0.75rem;
padding:1.5rem;line-height:1.8;">
  <h4 style="margin:0 0 1rem 0;color:#d97706;">🧭 Coaching Notes for the Witness</h4>
  <div style="white-space:pre-wrap;font-size:0.95rem;">{esc(sec3)}</div>
</div>""", unsafe_allow_html=True)

                with s4_tab:
                    st.markdown("""
<div style="background:#eff6ff;border-left:4px solid #3b82f6;border-radius:0.6rem;
padding:0.9rem 1.2rem;margin-bottom:1rem;">
  <strong style="color:#1d4ed8;">↩️ Re-Examination Questions</strong><br>
  <small style="color:var(--la-text2);">Generated from the cross-examination attack points above.
  Re-examination is limited to matters arising from cross-examination (Evidence Act 2011, s.215).</small>
</div>""", unsafe_allow_html=True)

                    reexam_result = st.session_state.get("wp_reexam_result", "")
                    if not reexam_result:
                        if st.button(
                            "↩️ Generate Re-Examination Questions",
                            type="primary",
                            key="wp_reexam_btn", use_container_width=True,
                        ):
                            reexam_p = REEXAM_PROMPT.format(
                                witness_role=role_label,
                                case_facts=facts_saved,
                                cross_exam_risks=sec2,
                            )
                            with st.spinner("↩️ Generating re-examination questions…"):
                                reexam_result = generate(reexam_p, REEXAM_SYSTEM, "standard", "analysis")
                            st.session_state["wp_reexam_result"] = reexam_result
                            st.rerun()
                    else:
                        st.markdown(f"""
<div style="background:#eff6ff;border-left:4px solid #3b82f6;border-radius:0.75rem;
padding:1.5rem;line-height:1.8;white-space:pre-wrap;font-size:0.95rem;">
{esc(reexam_result)}</div>""", unsafe_allow_html=True)
                        re1, re2 = st.columns(2)
                        with re1:
                            st.download_button(
                                "📥 Download Re-Examination (TXT)",
                                export_txt(reexam_result, f"Re-Examination — {role_label}"),
                                f"ReExam_{role_label.replace(' ','_')}_{datetime.now():%Y%m%d}.txt",
                                "text/plain", key="wp_reexam_dl_txt", use_container_width=True,
                            )
                        with re2:
                            if st.button("🔄 Regenerate", key="wp_reexam_regen", use_container_width=True):
                                st.session_state["wp_reexam_result"] = ""
                                st.rerun()

            # ── Save to Case ──
            st.markdown("---")
            cases = st.session_state.cases
            if cases:
                st.markdown("##### 💾 Save to Case File")
                sv1, sv2 = st.columns([3, 1])
                with sv1:
                    save_case_options = {c["id"]: f"{c.get('title','Untitled')} [{c.get('status','')}]"
                                         for c in cases}
                    save_case_id = st.selectbox(
                        "Select Case",
                        list(save_case_options.keys()),
                        format_func=lambda x: save_case_options[x],
                        key="wp_save_case_sel",
                    )
                with sv2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Save", type="primary", key="wp_save_case_btn", use_container_width=True):
                        save_analysis_to_case(
                            save_case_id,
                            f"[Witness Prep] {role_label}",
                            result, "analysis", mode,
                        )
                        st.success(f"✅ Saved to case: {save_case_options[save_case_id]}")

            # ── Export row ──
            st.markdown("##### 📥 Export")
            fname = f"WitnessPrep_{role_label.replace(' ','_')}_{datetime.now():%Y%m%d_%H%M}"
            ex1, ex2, ex3, ex4 = st.columns(4)
            with ex1:
                st.download_button("📥 TXT", export_txt(result, f"Witness Prep — {role_label}"),
                    f"{fname}.txt", "text/plain", key="wp_dl_txt", use_container_width=True)
            with ex2:
                st.download_button("📥 HTML", export_html(result, f"Witness Prep — {role_label}"),
                    f"{fname}.html", "text/html", key="wp_dl_html", use_container_width=True)
            with ex3:
                safe_pdf_download(result, f"Witness Prep — {role_label}", fname, "wp_dl_pdf")
            with ex4:
                safe_docx_download(result, f"Witness Prep — {role_label}", fname, "wp_dl_docx", doc_type="witness", meta={"role": role_label})

            if st.button("🗑️ Clear Current Brief", key="wp_clear_btn", use_container_width=True):
                for k in ["wp_result", "wp_role_label", "wp_facts_saved", "wp_reexam_result"]:
                    st.session_state[k] = ""
                st.rerun()

            st.markdown("""<div class="disclaimer">
                <strong>⚖️ Disclaimer:</strong> AI-generated witness preparation materials are a
                drafting aid only. Review all questions against actual witness statements. Do not
                share coaching notes or cross-exam analysis with opposing counsel.
            </div>""", unsafe_allow_html=True)
        elif st.session_state.get("wp_facts_saved", "").strip():
            # Facts saved but no result body — the generation came back
            # empty. Give a friendly retry nudge instead of a silent blank.
            st.markdown("---")
            st.warning(
                "⚠️ The witness brief came back empty. Click "
                "**Prepare Witness** again to retry."
            )

    # ═══════════════════════════════════════════════════
    # TAB 2 — WITNESS SESSION LOG
    # ═══════════════════════════════════════════════════
    with tab_log:
        log = st.session_state["wp_witness_log"]
        if not log:
            st.info("No witnesses prepared yet in this session. Use the 'Prepare a Witness' tab to get started.")
        else:
            st.markdown(f"##### 👥 {len(log)} Witness(es) Prepared This Session")
            st.caption("All witness briefs are held in memory for this session. Use the Contradiction Check tab to compare accounts.")

            for i, entry in enumerate(log):
                with st.expander(
                    f"{'👤'} {esc(entry['name'])} — {esc(entry['role'])} "
                    f"· {esc(entry['timestamp'])}",
                    expanded=False,
                ):
                    log_sec1 = _wp_extract_section(entry["result"], "EXAMINATION-IN-CHIEF")
                    log_sec2 = _wp_extract_section(entry["result"], "CROSS-EXAMINATION")
                    log_sec3 = _wp_extract_section(entry["result"], "COACHING NOTES")

                    if log_sec1 and log_sec2 and log_sec3:
                        lt1, lt2, lt3 = st.tabs(["📋 Exam-in-Chief", "⚔️ Cross-Exam Risks", "🧭 Coaching"])
                        with lt1:
                            st.markdown(f'<div style="white-space:pre-wrap;font-size:0.9rem;'
                                        f'background:#f0fdf4;padding:1rem;border-radius:0.5rem;">'
                                        f'{esc(log_sec1)}</div>', unsafe_allow_html=True)
                        with lt2:
                            st.markdown(f'<div style="white-space:pre-wrap;font-size:0.9rem;'
                                        f'background:#fef2f2;padding:1rem;border-radius:0.5rem;">'
                                        f'{esc(log_sec2)}</div>', unsafe_allow_html=True)
                        with lt3:
                            st.markdown(f'<div style="white-space:pre-wrap;font-size:0.9rem;'
                                        f'background:#fffbeb;padding:1rem;border-radius:0.5rem;">'
                                        f'{esc(log_sec3)}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="response-box" style="font-size:0.88rem;">'
                                    f'{esc(entry["result"])}</div>', unsafe_allow_html=True)

                    # Quick export per witness
                    loge1, loge2, loge3 = st.columns(3)
                    lname = entry["name"].replace(" ", "_")
                    with loge1:
                        st.download_button(
                            "📥 TXT", export_txt(entry["result"], f"Witness Prep — {entry['name']}"),
                            f"WitnessPrep_{lname}.txt", "text/plain",
                            key=f"wp_log_dl_{i}", use_container_width=True,
                        )
                    with loge2:
                        safe_pdf_download(
                            entry["result"], f"Witness Prep — {entry['name']}",
                            f"WitnessPrep_{lname}", f"wp_log_pdf_{i}",
                        )
                    with loge3:
                        if st.button("🗑️ Remove from Log", key=f"wp_log_del_{i}", use_container_width=True):
                            st.session_state["wp_witness_log"].pop(i)
                            st.rerun()

            if st.button("🗑️ Clear Entire Witness Log", key="wp_log_clear_all", use_container_width=True):
                st.session_state["wp_witness_log"] = []
                st.rerun()

    # ═══════════════════════════════════════════════════
    # TAB 3 — CONTRADICTION CHECK
    # ═══════════════════════════════════════════════════
    with tab_contra:
        log = st.session_state["wp_witness_log"]
        st.markdown("#### 🔍 Multi-Witness Contradiction Detector")
        st.caption(
            "Select two or more witnesses from your session log. "
            "AI will identify contradictions, gaps, and corroborations between their accounts — "
            "and suggest how to reconcile them before trial."
        )

        if len(log) < 2:
            st.warning(
                "⚠️ You need at least 2 prepared witnesses in your session log to run a contradiction check. "
                "Prepare more witnesses first."
            )
        else:
            # Multi-select from log
            witness_options = {entry["id"]: f"{entry['name']} ({entry['role']})" for entry in log}
            selected_ids = st.multiselect(
                "Select Witnesses to Compare (minimum 2)",
                list(witness_options.keys()),
                format_func=lambda x: witness_options[x],
                default=list(witness_options.keys())[:min(2, len(witness_options))],
                key="wp_contra_sel",
            )

            contra_btn = st.button(
                "🔍 Run Contradiction Check",
                type="primary", use_container_width=True,
                key="wp_contra_btn",
                disabled=len(selected_ids) < 2,
            )

            if contra_btn and len(selected_ids) >= 2:
                selected_entries = [e for e in log if e["id"] in selected_ids]
                summaries = ""
                for idx, entry in enumerate(selected_entries, 1):
                    summaries += f"\n{'='*50}\nWITNESS {idx}: {entry['name']} ({entry['role']})\n"
                    summaries += f"Case Type: {entry['case_type']}\n\n"
                    summaries += f"PREPARED BRIEF:\n{entry['result'][:3000]}\n"

                contra_prompt = CONTRADICTION_PROMPT.format(
                    count=len(selected_entries),
                    witness_summaries=summaries,
                )
                with st.spinner(f"🔍 Analysing {len(selected_entries)} witnesses for contradictions…"):
                    contra_result = generate(contra_prompt, CONTRADICTION_SYSTEM, "standard", "analysis")
                st.session_state["wp_contra_result"] = contra_result
                st.rerun()

            contra_result = st.session_state.get("wp_contra_result", "")
            if contra_result:
                st.markdown("---")
                st.markdown(f'<div class="response-box">{esc(contra_result)}</div>',
                            unsafe_allow_html=True)
                st.markdown("---")
                cd1, cd2, cd3 = st.columns(3)
                with cd1:
                    st.download_button(
                        "📥 Export Contradiction Report (TXT)",
                        export_txt(contra_result, "Witness Contradiction Analysis"),
                        f"ContradictionCheck_{datetime.now():%Y%m%d_%H%M}.txt",
                        "text/plain", key="wp_contra_dl_txt", use_container_width=True,
                    )
                with cd2:
                    safe_pdf_download(
                        contra_result, "Witness Contradiction Analysis",
                        f"ContradictionCheck_{datetime.now():%Y%m%d_%H%M}", "wp_contra_dl_pdf",
                    )
                with cd3:
                    if st.button("🗑️ Clear Result", key="wp_contra_clear", use_container_width=True):
                        st.session_state["wp_contra_result"] = ""
                        st.rerun()

                st.markdown("""<div class="disclaimer">
                    <strong>⚖️ Disclaimer:</strong> Contradiction analysis is AI-assisted.
                    Counsel must independently review all witness statements before trial.
                    Intra-party contradictions must be resolved before witnesses take the box.
                </div>""", unsafe_allow_html=True)

