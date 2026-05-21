"""LexiAssist settlement + ADR advisor."""
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
# PAGE: SETTLEMENT & ADR ADVISOR
# ═══════════════════════════════════════════════════════
def render_settlement_advisor():
    st.markdown("""<div class="page-header">
        <h2>🤝 Settlement & ADR Advisor</h2>
        <p>AI-powered negotiation strategy · Settlement value analysis ·
        Without-prejudice offer drafting · ADR route recommendation</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key first.")
        return

    st.markdown("""
<div style="background:var(--la-card);border-left:3px solid var(--la-acc);padding:0.8rem 1.1rem;
border-radius:0.5rem;margin-bottom:1rem;font-size:0.9rem;color:var(--la-text);">
  💡 <strong>How to use:</strong> Fill in the matter details below. The more specific
  your inputs (especially claim amount and case facts), the more actionable the output.
  The AI will take a firm position on the optimal settlement figure and strategy.
</div>""", unsafe_allow_html=True)

    sa1, sa2 = st.columns([3, 2])
    with sa1:
        sa_facts = st.text_area(
            "Case Facts *",
            height=200,
            key="sa_facts_ta",
            placeholder="""E.g. Client (ABC Ltd) entered into a construction contract with XYZ Builders Ltd
in January 2023 for ₦85M. XYZ abandoned the site in August 2023 after collecting
₦60M (70%). Completion was 35%. ABC incurred ₦25M additional costs to complete
with another contractor. ABC also suffered 6 months' revenue loss estimated at ₦15M.
XYZ claims ABC refused to pay the last instalment of ₦10M. ABC disputes this.""",
        )
        sa_case_type = st.selectbox(
            "Case Type",
            [
                "Breach of Contract", "Debt Recovery", "Property Dispute",
                "Employment / Wrongful Termination", "Company Dispute",
                "Personal Injury / Negligence", "Defamation", "Matrimonial",
                "Construction / Engineering", "Banking & Finance",
                "Intellectual Property", "Other",
            ],
            key="sa_case_type_sel",
        )

    with sa2:
        sa_instructing = st.text_input("Instructing Party", placeholder="ABC Ltd (Claimant)",
                                       key="sa_instruct_inp")
        sa_opposing = st.text_input("Opposing Party", placeholder="XYZ Builders Ltd (Defendant)",
                                    key="sa_oppose_inp")
        sa_amount = st.number_input("Total Claim / Dispute Value (₦)",
            min_value=0.0, value=100_000_000.0, step=1_000_000.0,
            format="%.2f", key="sa_amount_inp")
        st.caption(f"Claim: **{fmt_currency(sa_amount)}**")
        sa_court = st.selectbox("Current Stage",
            ["Pre-litigation", "Letter of Demand sent", "Writ filed / Suit pending",
             "Pleadings stage", "Pre-trial / Mediation ordered", "Trial ongoing",
             "Judgment obtained", "Appeal pending", "Arbitration commenced"],
            key="sa_court_sel")
        sa_strength = st.select_slider(
            "Your Case Strength",
            options=["Very Weak", "Weak", "Moderate", "Strong", "Very Strong"],
            value="Moderate", key="sa_strength_sl",
        )
        sa_urgency = st.selectbox("Time Pressure",
            ["None", "Client needs cash urgently", "Court deadline approaching",
             "Business disruption ongoing", "Preservation risk (assets at risk)",
             "Limitation period approaching"],
            key="sa_urgency_sel")

    mode = st.session_state.response_mode
    st.info(f"Mode: {RESPONSE_MODES[mode]['label']}")
    sa_btn = st.button(
        "🤝 Generate Settlement Strategy",
        type="primary", use_container_width=True, key="sa_gen_btn",
        disabled=not (sa_facts.strip() and sa_instructing.strip()),
    )

    if sa_btn and sa_facts.strip() and sa_instructing.strip():
        prompt = SETTLEMENT_PROMPT.format(
            instructing_party=sa_instructing.strip(),
            opposing_party=sa_opposing.strip() or "Opposing party",
            case_type=sa_case_type,
            claim_amount=f"{sa_amount:,.2f}",
            court_stage=sa_court,
            strength=sa_strength,
            urgency=sa_urgency,
            case_facts=sa_facts.strip(),
        )
        with st.spinner("🤝 Analysing settlement position and generating strategy…"):
            raw = generate(prompt, SETTLEMENT_SYSTEM, mode, "advisory")
        st.session_state["sa_result"] = raw
        st.session_state["sa_matter_label"] = sa_instructing.strip()
        add_to_history(f"[Settlement] {sa_instructing.strip()} vs {sa_opposing.strip()}", raw, "advisory", mode)
        st.rerun()

    result = st.session_state.get("sa_result", "")
    matter_label = st.session_state.get("sa_matter_label", "Settlement")

    if result and result.strip():
        st.markdown("---")

        # Parse sections
        def _get_section(text, header):
            lines = text.split("\n")
            capture, collected = False, []
            for line in lines:
                if header.upper() in line.upper() and "═" in line:
                    capture = True; continue
                if capture and "═══" in line and collected:
                    break
                if capture:
                    collected.append(line)
            return "\n".join(collected).strip()

        sec1 = _get_section(result, "SETTLEMENT VALUE")
        sec2 = _get_section(result, "NEGOTIATION STRATEGY")
        sec3 = _get_section(result, "ADR ROUTE")
        sec4 = _get_section(result, "WITHOUT PREJUDICE")
        sec5 = _get_section(result, "RISK IF NO SETTLEMENT")

        if sec1 and sec2:
            t1, t2, t3, t4, t5 = st.tabs([
                "💰 Settlement Value",
                "♟️ Negotiation Strategy",
                "🏛️ ADR Route",
                "✉️ Without Prejudice Offer",
                "⚠️ Litigation Risk",
            ])
            tab_configs = [
                (t1, sec1, "#059669"),
                (t2, sec2, "#3b82f6"),
                (t3, sec3, "#7c3aed"),
                (t4, sec4, "#f59e0b"),
                (t5, sec5, "#dc2626"),
            ]
            for tab, content, border in tab_configs:
                with tab:
                    st.markdown(
                        f'<div style="background:var(--la-card);border-left:4px solid {border};'
                        f'border-radius:0.75rem;padding:1.5rem;line-height:1.8;'
                        f'white-space:pre-wrap;font-size:0.95rem;color:var(--la-text);">'
                        f'{esc(content)}</div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown(f'<div class="response-box">{esc(result)}</div>', unsafe_allow_html=True)

        # Save to case
        cases = st.session_state.cases
        if cases:
            st.markdown("---")
            sv1, sv2 = st.columns([3, 1])
            with sv1:
                sc_id = st.selectbox("Save to Case", [c["id"] for c in cases],
                    format_func=lambda x: next((c["title"] for c in cases if c["id"] == x), x),
                    key="sa_save_case_sel")
            with sv2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 Save", key="sa_save_btn", type="primary", use_container_width=True):
                    save_analysis_to_case(sc_id, f"[Settlement] {matter_label}", result, "advisory", mode)
                    st.success("✅ Saved to case.")

        # Export
        fname = f"Settlement_{matter_label.replace(' ','_')}_{datetime.now():%Y%m%d_%H%M}"
        e1, e2, e3, e4 = st.columns(4)
        with e1:
            st.download_button("📥 TXT", export_txt(result, f"Settlement Strategy — {matter_label}"),
                f"{fname}.txt", "text/plain", key="sa_dl_txt", use_container_width=True)
        with e2:
            st.download_button("📥 HTML", export_html(result, f"Settlement Strategy — {matter_label}"),
                f"{fname}.html", "text/html", key="sa_dl_html", use_container_width=True)
        with e3:
            safe_pdf_download(result, f"Settlement Strategy — {matter_label}", fname, "sa_dl_pdf")
        with e4:
            safe_docx_download(result, f"Settlement Strategy — {matter_label}", fname, "sa_dl_docx", doc_type="settlement", meta={"matter": matter_label})

        if st.button("🗑️ Clear", key="sa_clear_btn", use_container_width=True):
            st.session_state["sa_result"] = ""
            st.rerun()

        st.markdown("""<div class="disclaimer">
            <strong>⚖️ Disclaimer:</strong> Settlement strategy is AI-assisted advisory.
            All without-prejudice communications must be reviewed by counsel before transmission.
            Counsel remains professionally responsible for all advice and negotiations.
        </div>""", unsafe_allow_html=True)
    elif st.session_state.get("sa_matter_label", "").strip():
        # Run was attempted but the AI returned an empty body — surface
        # a friendly retry nudge instead of a silent blank.
        st.markdown("---")
        st.warning(
            "⚠️ The AI returned an empty response. Click "
            "**Generate Settlement Strategy** again to retry."
        )
    # ← render_settlement_advisor ends here — firm admin block removed from this scope



