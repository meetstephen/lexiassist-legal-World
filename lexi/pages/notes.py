"""LexiAssist notes-to-brief converter."""
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
# PAGE: NOTES → LEGAL BRIEF CONVERTER
# ═══════════════════════════════════════════════════════
def render_notes_converter():
    st.markdown("""<div class="page-header">
        <h2>📝 Notes → Legal Brief Converter</h2>
        <p>Paste raw client meeting notes — get a structured legal brief,
        retainer letter, letter of demand, or formal advice letter</p>
    </div>""", unsafe_allow_html=True)
    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key first.")
        return
    output_types = {
        "brief":    "📋 Legal Brief (Internal Memo)",
        "retainer": "🤝 Client Retainer Letter",
        "demand":   "📩 Letter of Demand",
        "advice":   "📄 Formal Legal Advice Letter",
        "opinion":  "⚖️ Formal Legal Opinion",
        "proof":    "📜 Proof of Evidence (Witness Statement)",
    }
    nc1, nc2 = st.columns([2, 1])
    with nc1:
        notes_input = st.text_area(
            "Raw Meeting Notes",
            height=280,
            placeholder="""Paste your raw, unstructured meeting notes here. Example:

Met with Mrs Adaobi today. Her husband died intestate in March.
3 kids. House in Lekki worth maybe 50M. Brother in law is claiming
the house saying it was given to him verbally. She has receipts from
when they bought it in 2011. No will. She wants to know if she can
stop him from selling. Court? How long? Cost?""",
            key="notes_input_ta",
        )
    with nc2:
        output_type = st.selectbox(
            "Convert To",
            list(output_types.keys()),
            format_func=lambda x: output_types[x],
            key="notes_output_type",
        )
        client_name = st.text_input(
            "Client Name",
            placeholder="Mrs Adaobi Okafor",
            key="notes_client_name",
        )
        matter_ref = st.text_input(
            "Matter Reference",
            placeholder="MO/2024/001",
            key="notes_matter_ref",
        )
        mode = st.session_state.response_mode
        st.info(f"Mode: {RESPONSE_MODES[mode]['label']}")
        convert_btn = st.button(
            "✨ Convert Notes",
            type="primary", use_container_width=True,
            disabled=not notes_input.strip(),
            key="notes_convert_btn",
        )
    if convert_btn and notes_input.strip():
        type_prompts = {
            "brief": f"""Convert these raw client meeting notes into a structured
internal legal brief using Nigerian law.
Format strictly as:
CLIENT DETAILS / FACTS AS UNDERSTOOD / ISSUES IDENTIFIED /
APPLICABLE LAW & AUTHORITIES / PRELIMINARY ADVICE /
RECOMMENDED ACTION / RISKS & EXPOSURES
Client: {client_name or '[CLIENT]'} | Ref: {matter_ref or '[REF]'}
Be thorough. Cite Nigerian statutes and cases where relevant.""",
            "retainer": f"""Convert these raw meeting notes into a formal Client
Retainer Letter on Nigerian law firm letterhead format.
Include: scope of engagement, fees structure (use [AMOUNT] placeholders),
our obligations, client obligations, confidentiality clause,
governing law, termination clause, and full signature block.
Client: {client_name or '[CLIENT]'} | Ref: {matter_ref or '[REF]'}
Use standard Nigerian solicitor letter format throughout.""",
            "demand": f"""Convert these raw meeting notes into a formal Letter of
Demand in standard Nigerian solicitor format.
Include: full heading with OUR REF and DATE, RE: line, facts paragraph,
legal position with applicable law, specific demand with exact amount
if mentioned, deadline (7/14/21 days as appropriate), and clear
consequences of non-compliance.
Client: {client_name or '[CLIENT]'} | Ref: {matter_ref or '[REF]'}""",
            "advice": f"""Convert these raw meeting notes into a formal Legal Advice
Letter addressed to the client.
Format: Introduction / Facts as Understood / Legal Position /
Our Advice / Recommended Next Steps / Costs Estimate / Disclaimer
Write in plain English the client can understand.
Explain all legal terms used. No unnecessary Latin.
Client: {client_name or '[CLIENT]'} | Ref: {matter_ref or '[REF]'}""",
            "opinion": f"""Convert these raw meeting notes into a formal Legal Opinion
in the standard Nigerian law firm format.
Structure STRICTLY as:
1. INTRODUCTION & INSTRUCTIONS
2. DOCUMENTS/FACTS CONSIDERED
3. ISSUES FOR OPINION
4. LAW APPLICABLE
5. OPINION (one firm paragraph per issue — no hedging)
6. CONCLUSION
7. CAVEATS & LIMITATIONS
Sign off: "This Opinion is rendered in good faith and is based on Nigerian law
as at the date hereof. It does not constitute legal advice for any other purpose."
Client: {client_name or '[CLIENT]'} | Ref: {matter_ref or '[REF]'}""",
            "proof": f"""Convert these raw meeting notes into a formal Proof of Evidence
(Witness Statement) for use in Nigerian court proceedings.
Structure:
- Court heading with suit number (use [SUIT NO] if not stated)
- Title: WITNESS STATEMENT ON OATH OF [WITNESS NAME]
- Numbered paragraphs (each containing one fact only)
- Use first person: "I am..." "I say that..."
- End with: "I make this statement knowing that it will be relied upon
  in the above proceedings and believing that the facts stated herein
  are true to the best of my knowledge and belief."
- Jurat block at the end
- Note: Stamp duty ₦200 flat (Stamp Duties Act) — affix before swearing
Client: {client_name or '[CLIENT]'} | Ref: {matter_ref or '[REF]'}""",
        }
        full_prompt = (
            type_prompts[output_type]
            + f"\n\nRAW MEETING NOTES:\n{notes_input.strip()}"
        )
        system = build_system_prompt("drafting", mode)
        with st.spinner(f"✨ Converting notes to {output_types[output_type]}..."):
            result = generate(full_prompt, system, mode, "drafting")

        # Persist everything we need to re-render the result block on
        # subsequent reruns (download / save clicks). Without this, the
        # whole output disappears the moment the user clicks any button.
        st.session_state["notes_result"] = result
        st.session_state["notes_result_type"] = output_type
        st.session_state["notes_result_label"] = output_types[output_type]
        st.session_state["notes_result_client"] = client_name
        st.session_state["notes_result_preview"] = notes_input[:120]
        add_to_history(
            f"[Notes→{output_type.title()}] {notes_input[:80]}",
            result, "drafting", mode,
        )
        st.rerun()

    # ── Render persisted converter result (reads from session_state so
    # downloads and Save-to-Case clicks don't blank the page).
    notes_result = st.session_state.get("notes_result", "")
    if notes_result and notes_result.strip():
        result_label = st.session_state.get("notes_result_label", "Converted Notes")
        result_type = st.session_state.get("notes_result_type", "brief")
        result_client = st.session_state.get("notes_result_client", "")
        result_preview = st.session_state.get("notes_result_preview", "")

        st.markdown("---")
        st.markdown(f"### {result_label}")
        fname = f"LexiAssist_{result_type}_{(result_client or 'client').replace(' ','_')}_{datetime.now():%Y%m%d_%H%M}"
        ex1, ex2, ex3, ex4 = st.columns(4)
        with ex1:
            st.download_button(
                "📥 TXT",
                export_txt(notes_result, result_label),
                f"{fname}.txt", "text/plain",
                key="notes_dl_txt", use_container_width=True,
            )
        with ex2:
            st.download_button(
                "📥 HTML",
                export_html(notes_result, result_label),
                f"{fname}.html", "text/html",
                key="notes_dl_html", use_container_width=True,
            )
        with ex3:
            safe_pdf_download(notes_result, result_label, fname, "notes_dl_pdf")
        with ex4:
            safe_docx_download(notes_result, result_label, fname, "notes_dl_docx")
        st.markdown(
            f'<div class="response-box">{esc(notes_result)}</div>',
            unsafe_allow_html=True,
        )
        cases = st.session_state.cases
        if cases:
            st.markdown("### 💾 Save to Case")
            sc1, sc2 = st.columns([3, 1])
            with sc1:
                case_names = [
                    f"{c.get('title','Untitled')} ({c.get('suit_no','—')})"
                    for c in cases
                ]
                sel = st.selectbox(
                    "Select case:", case_names,
                    key="notes_save_case_sel",
                    label_visibility="collapsed",
                )
            with sc2:
                if st.button("💾 Save", key="notes_save_case_btn",
                             type="primary", use_container_width=True):
                    idx = case_names.index(sel)
                    save_analysis_to_case(
                        cases[idx]["id"],
                        f"[Notes→{result_type}] {result_preview}",
                        notes_result, "drafting", mode,
                    )
                    st.success(f"✅ Saved to: {cases[idx].get('title','')}")
        if st.button("🗑️ Clear Result", key="notes_clear_btn"):
            for k in (
                "notes_result", "notes_result_type", "notes_result_label",
                "notes_result_client", "notes_result_preview",
            ):
                st.session_state.pop(k, None)
            st.rerun()
        st.markdown("""<div class="disclaimer">
            <strong>⚖️ Disclaimer:</strong> Review all AI-generated documents
            before sending to clients or filing. Verify all legal positions
            and citations independently.
        </div>""", unsafe_allow_html=True)
    elif "notes_result" in st.session_state:
        # The conversion ran but came back empty — give a friendly retry
        # nudge instead of a silent blank.
        st.markdown("---")
        st.warning(
            "⚠️ The AI returned an empty response. This is usually a "
            "transient model timeout. Click **Convert Notes** again to retry."
        )
