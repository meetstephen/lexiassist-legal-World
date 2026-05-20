"""LexiAssist due-diligence engine."""
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
# PAGE: DUE DILIGENCE ENGINE
# ═══════════════════════════════════════════════════════
def render_due_diligence():
    st.markdown("""<div class="page-header">
        <h2>🔎 Due Diligence Engine</h2>
        <p>AI-generated Nigerian-law due diligence checklists · CAC searches ·
        Title verification · Regulatory approvals · Transaction risk flags</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key first.")
        return

    st.markdown("""
<div style="background:var(--la-card);border-left:3px solid var(--la-pos);padding:0.8rem 1.1rem;
border-radius:0.5rem;margin-bottom:1rem;font-size:0.9rem;color:var(--la-text);">
  💡 <strong>How it works:</strong> Select your transaction type, describe the deal,
  and the AI generates a comprehensive Nigerian-law due diligence checklist tailored
  to your specific matter — with search requirements, risk flags, and a critical path.
</div>""", unsafe_allow_html=True)

    dd1, dd2 = st.columns([3, 2])
    with dd1:
        dd_description = st.text_area(
            "Transaction Description *",
            height=180,
            key="dd_desc_ta",
            placeholder="""Describe the transaction briefly. E.g.:

Client (Sunrise Properties Ltd) intends to acquire a 3-plot commercial property
in Victoria Island, Lagos from Apex Holdings Ltd for ₦450M. The vendor claims
a C of O has been registered in their name. The property currently has a tenant.
Client wants to develop a 12-storey mixed-use building on the site. The vendor
is a company with 3 directors. No prior relationship with vendor.""",
        )
        dd_concerns = st.text_area(
            "Special Concerns / Red Flags (optional)",
            height=80, key="dd_concerns_ta",
            placeholder="E.g. Vendor is a company with recent change of directors. Prior occupant dispute. Area prone to government acquisition.",
        )
    with dd2:
        dd_type = st.selectbox(
            "Transaction Type *",
            list(DD_TRANSACTION_TYPES.keys()),
            format_func=lambda k: DD_TRANSACTION_TYPES[k],
            key="dd_type_sel",
        )
        dd_value = st.number_input(
            "Transaction Value (₦)",
            min_value=0.0, value=100_000_000.0, step=5_000_000.0,
            format="%.2f", key="dd_value_inp",
        )
        st.caption(f"Value: **{fmt_currency(dd_value)}**")
        dd_jurisdiction = st.selectbox(
            "Jurisdiction",
            ["Lagos State", "Abuja (FCT)", "Rivers State", "Kano State",
             "Ogun State", "Oyo State", "Delta State", "Anambra State",
             "Cross River State", "Edo State", "Other — specify in description"],
            key="dd_jur_sel",
        )
        dd_parties = st.text_input(
            "Parties",
            placeholder="Buyer: Sunrise Properties Ltd | Seller: Apex Holdings Ltd",
            key="dd_parties_inp",
        )
        mode = st.session_state.response_mode
        st.info(f"Mode: {RESPONSE_MODES[mode]['label']}")

    dd_btn = st.button(
        f"🔎 Generate Due Diligence Checklist",
        type="primary", use_container_width=True, key="dd_gen_btn",
        disabled=not dd_description.strip(),
    )

    if dd_btn and dd_description.strip():
        prompt = DD_PROMPT.format(
            transaction_type=DD_TRANSACTION_TYPES[dd_type],
            transaction_value=f"{dd_value:,.2f}",
            jurisdiction=dd_jurisdiction,
            parties=dd_parties.strip() or "As described",
            description=dd_description.strip(),
            special_concerns=dd_concerns.strip() or "None stated",
        )
        with st.spinner(f"🔎 Generating {DD_TRANSACTION_TYPES[dd_type]} due diligence checklist…"):
            raw = generate(prompt, DD_SYSTEM, mode, "advisory")
        st.session_state["dd_result"] = raw
        st.session_state["dd_label"] = f"{DD_TRANSACTION_TYPES[dd_type]} — {dd_jurisdiction}"
        add_to_history(
            f"[Due Diligence] {DD_TRANSACTION_TYPES[dd_type]} — {dd_value:,.0f}",
            raw, "advisory", mode,
        )
        st.rerun()

    result = st.session_state.get("dd_result", "")
    dd_label = st.session_state.get("dd_label", "Due Diligence")

    if result:
        st.markdown("---")
        st.markdown(f"### 🔎 {esc(dd_label)}")

        # Render with themed response box
        st.markdown(
            f'<div class="response-box">{esc(result)}</div>',
            unsafe_allow_html=True,
        )

        # Save to case
        cases = st.session_state.cases
        if cases:
            st.markdown("---")
            dv1, dv2 = st.columns([3, 1])
            with dv1:
                dd_case_id = st.selectbox("Save to Case File", [c["id"] for c in cases],
                    format_func=lambda x: next((c["title"] for c in cases if c["id"] == x), x),
                    key="dd_save_case_sel")
            with dv2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 Save to Case", key="dd_save_btn",
                             type="primary", use_container_width=True):
                    save_analysis_to_case(dd_case_id, f"[DD Checklist] {dd_label}",
                                          result, "advisory", mode)
                    st.success("✅ Saved to case file.")

        # Export
        fname = f"DueDiligence_{dd_type}_{datetime.now():%Y%m%d_%H%M}"
        de1, de2, de3, de4 = st.columns(4)
        with de1:
            st.download_button("📥 TXT", export_txt(result, f"Due Diligence — {dd_label}"),
                f"{fname}.txt", "text/plain", key="dd_dl_txt", use_container_width=True)
        with de2:
            st.download_button("📥 HTML", export_html(result, f"Due Diligence — {dd_label}"),
                f"{fname}.html", "text/html", key="dd_dl_html", use_container_width=True)
        with de3:
            safe_pdf_download(result, f"Due Diligence — {dd_label}", fname, "dd_dl_pdf")
        with de4:
            safe_docx_download(result, f"Due Diligence — {dd_label}", fname, "dd_dl_docx", doc_type="due_diligence", meta={"subject": dd_label})

        if st.button("🗑️ Clear", key="dd_clear_btn", use_container_width=True):
            st.session_state["dd_result"] = ""
            st.rerun()

        st.markdown("""<div class="disclaimer">
            <strong>⚖️ Disclaimer:</strong> This checklist is AI-generated and must be reviewed
            by counsel with knowledge of the specific transaction. It does not replace physical
            inspection, official searches, or independent legal advice. All searches must be
            conducted at the relevant registries before advising clients to proceed.
        </div>""", unsafe_allow_html=True)


