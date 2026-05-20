"""LexiAssist smart pleadings drafter."""
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
# PAGE: SMART PLEADINGS DRAFTER
# ═══════════════════════════════════════════════════════
PLEADING_TYPES = {
    "statement_of_claim": {
        "label": "📄 Statement of Claim",
        "desc": "Originating pleading setting out claimant's facts and reliefs",
    },
    "statement_of_defence": {
        "label": "🛡️ Statement of Defence",
        "desc": "Defendant's response admitting or denying each allegation",
    },
    "reply": {
        "label": "↩️ Reply to Defence",
        "desc": "Claimant's response to new matters raised in defence",
    },
    "counterclaim": {
        "label": "⚔️ Counter-Claim",
        "desc": "Defendant's claim against the claimant",
    },
    "defence_to_counterclaim": {
        "label": "🛡️ Defence to Counter-Claim",
        "desc": "Claimant's reply to the defendant's counter-claim",
    },
    "originating_summons": {
        "label": "📋 Originating Summons",
        "desc": "For matters begun by summons — questions of law or document construction",
    },
    "motion_on_notice": {
        "label": "📬 Motion on Notice",
        "desc": "Interlocutory application on notice with supporting affidavit",
    },
    "ex_parte_motion": {
        "label": "⚡ Ex Parte Motion (Urgent)",
        "desc": "Urgent motion without notice — injunctions, Mareva, Anton Piller",
    },
    "affidavit": {
        "label": "📜 Supporting Affidavit",
        "desc": "Sworn statement of facts in support of a motion or application",
    },
    "counter_affidavit": {
        "label": "📜 Counter-Affidavit",
        "desc": "Respondent's sworn reply to the applicant's affidavit",
    },
    "written_address": {
        "label": "✍️ Written Address / Final Address",
        "desc": "Final address or skeleton argument for court",
    },
    "notice_of_appeal": {
        "label": "🔔 Notice of Appeal",
        "desc": "Formal notice of appeal with grounds and relief sought",
    },
    "writ_of_summons": {
        "label": "📃 Writ of Summons",
        "desc": "Originating process for High Court actions (States & FCT)",
    },
    "petition": {
        "label": "📝 Petition",
        "desc": "Election petition, winding-up petition, or matrimonial petition",
    },
    "fundamental_rights_motion": {
        "label": "⚖️ Fundamental Rights Enforcement Motion",
        "desc": "Application under FREP Rules 2009 — CFRN Chapter IV rights",
    },
    "mareva_injunction": {
        "label": "🔒 Mareva Injunction Application",
        "desc": "Asset-freezing order to prevent dissipation pending judgment",
    },
    "interpleader_summons": {
        "label": "🔀 Interpleader Summons",
        "desc": "Where a third party holds property claimed by two parties",
    },
    "garnishee_order_nisi": {
        "label": "💰 Garnishee Proceedings (Order Nisi)",
        "desc": "Post-judgment enforcement — attaching debts owed to judgment debtor",
    },
}

PLEADING_PROMPT = """
You are a senior Nigerian litigation lawyer and Senior Advocate (SAN-standard) drafting court documents.
Draft the {pleading_type} described below in full, professional Nigerian court format.

STRICT DRAFTING RULES:
1. Use EXACT suit number, parties' names, and court provided — no modifications
2. Use [PLACEHOLDER] ONLY for genuinely missing information — fill everything you can from the facts
3. Include ALL mandatory formal requirements for this document type in Nigerian courts
4. Number every paragraph correctly (1, 2, 3... for pleadings; i, ii, iii... for grounds)
5. Include proper heading, document title, body, relief/prayers section, date line, and signature block
6. Apply the correct Rules of Court for the specified court (Lagos HCCPR 2019, FHC (CPR) 2019, etc.)
7. For affidavits: use deponent language ("I STATE as follows:"), number every paragraph, end with jurat
8. For written addresses: use Issues for Determination, structured arguments with case law, conclusion with prayers
9. For notices of appeal: state specific errors of law or fact with particulars; state relief sought precisely
10. Do NOT add strategy commentary or analysis — pure court document only
11. Include stamp duty note where applicable (Affidavit: ₦200 flat; Deed: per Stamp Duties Act)
12. For Mareva/injunction applications: include undertaking as to damages reminder

CASE DETAILS:
Case Title: {case_title}
Suit Number: {suit_no}
Court: {court}
Claimant / Applicant: {claimant}
Defendant / Respondent: {defendant}
Case Type: {case_type}
Key Facts: {facts}
Specific Instructions: {instructions}

Draft the complete, court-ready {pleading_type} now. Write every word of the document — do not summarise or use shorthand:
"""


def render_pleadings():
    st.markdown("""<div class="page-header">
        <h2>📜 Smart Pleadings Drafter</h2>
        <p>Generate court-ready pleadings pulled directly from your case file —
        no manual typing of parties, court, or suit number</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key first.")
        return

    cases = st.session_state.cases
    if not cases:
        st.info("No cases found. Add a case in the 📁 Cases tab first — "
                "the drafter pulls parties, court, and suit number from your case file automatically.")
        return

    # ── Case selector ──
    st.markdown("### 📁 Select Case")
    st.caption("All case details are pulled automatically from your saved case file.")

    case_names = [
        f"{c.get('title', 'Untitled')} ({c.get('suit_no', '—')})"
        for c in cases
    ]
    pc1, pc2 = st.columns([3, 1])
    with pc1:
        selected_case_name = st.selectbox(
            "Choose case",
            case_names,
            key="pleading_case_sel",
            label_visibility="collapsed",
        )
    selected_idx = case_names.index(selected_case_name)
    selected_case = cases[selected_idx]

    with pc2:
        st.metric("Status", selected_case.get("status", "—"))

    # ── Auto-populated case details ──
    st.markdown("---")
    st.markdown("### 📋 Case Details (Auto-Populated)")
    st.caption("Review and edit any field before generating.")

    pd1, pd2 = st.columns(2)
    with pd1:
        case_title = st.text_input(
            "Case Title",
            value=selected_case.get("title", ""),
            key="pl_case_title",
        )
        suit_no = st.text_input(
            "Suit Number",
            value=selected_case.get("suit_no", ""),
            key="pl_suit_no",
        )
        court = st.text_input(
            "Court",
            value=selected_case.get("court", ""),
            key="pl_court",
        )
    with pd2:
        claimant = st.text_input(
            "Claimant / Applicant",
            value="",
            placeholder="e.g. Chief Emeka Obi",
            key="pl_claimant",
        )
        defendant = st.text_input(
            "Defendant / Respondent",
            value="",
            placeholder="e.g. Lagos State Government",
            key="pl_defendant",
        )
        case_type_pl = st.text_input(
            "Case Type",
            value="",
            placeholder="e.g. Breach of Contract, Land Dispute",
            key="pl_case_type",
        )

    facts = st.text_area(
        "Key Facts",
        value=selected_case.get("notes", ""),
        height=120,
        key="pl_facts",
        placeholder="""e.g. Claimant and Defendant entered into a contract on 1 Jan 2023.
Defendant received goods worth ₦12M and refused payment.
Demand letters sent on 1 March and 1 April 2023. No response.""",
    )

    # ── Pleading type selector ──
    st.markdown("---")
    st.markdown("### 📄 Select Document to Draft")

    pl_keys = list(PLEADING_TYPES.keys())
    pleading_type_key = st.selectbox(
        "Document Type",
        pl_keys,
        format_func=lambda x: f"{PLEADING_TYPES[x]['label']} — {PLEADING_TYPES[x]['desc']}",
        key="pleading_type_sel",
    )
    selected_pleading = PLEADING_TYPES[pleading_type_key]

    # Special instructions
    instructions = st.text_area(
        "Special Instructions (optional)",
        height=80,
        key="pl_instructions",
        placeholder="""e.g. Include a claim for general damages of ₦5M and special damages of ₦12M.
Add an application for accelerated hearing.
This is a counter-claim so defendant becomes counter-claimant.""",
    )

    mode = st.session_state.response_mode
    st.info(f"**Mode:** {RESPONSE_MODES[mode]['label']} — "
            f"Comprehensive mode produces the most complete pleadings.")

    # ── Generate button ──
    generate_btn = st.button(
        f"📜 Draft {selected_pleading['label']}",
        type="primary", use_container_width=True,
        key="pleading_generate_btn",
        disabled=not (case_title.strip() and court.strip()),
    )

    if generate_btn:
        prompt = PLEADING_PROMPT.format(
            pleading_type=selected_pleading["label"],
            case_title=case_title.strip(),
            suit_no=suit_no.strip() or "[SUIT NUMBER TO BE ASSIGNED]",
            court=court.strip(),
            claimant=claimant.strip() or "[CLAIMANT NAME]",
            defendant=defendant.strip() or "[DEFENDANT NAME]",
            case_type=case_type_pl.strip() or "General Civil Matter",
            facts=facts.strip() or "As will be adduced at trial",
            instructions=instructions.strip() or "None",
        )
        system = build_system_prompt("drafting", mode)
        with st.spinner(
            f"📜 Drafting {selected_pleading['label']}..."
        ):
            result = generate(prompt, system, mode, "drafting")

        st.session_state["pleading_result"] = result
        st.session_state["pleading_title"] = selected_pleading["label"]
        st.session_state["pleading_case_id"] = selected_case["id"]
        st.session_state["pleading_case_title"] = case_title
        add_to_history(
            f"[Pleading] {selected_pleading['label']} — {case_title}",
            result, "drafting", mode,
        )
        st.rerun()

    # ── Display result ──
    result = st.session_state.get("pleading_result", "")
    pleading_title = st.session_state.get("pleading_title", "Pleading")
    pleading_case_id = st.session_state.get("pleading_case_id", "")
    pleading_case_title = st.session_state.get("pleading_case_title", "")

    if result:
        st.markdown("---")
        st.markdown(f"### {pleading_title}")
        st.caption(f"Case: {esc(pleading_case_title)}")

        # ── Export row ──
        fname = (
            f"LexiAssist_{pleading_type_key}_{pleading_case_title.replace(' ','_')}"
            f"_{datetime.now():%Y%m%d_%H%M}"
        )
        ex1, ex2, ex3, ex4 = st.columns(4)
        with ex1:
            st.download_button(
                "📥 TXT",
                export_txt(result, pleading_title),
                f"{fname}.txt", "text/plain",
                key="pl_dl_txt", use_container_width=True,
            )
        with ex2:
            st.download_button(
                "📥 HTML",
                export_html(result, pleading_title),
                f"{fname}.html", "text/html",
                key="pl_dl_html", use_container_width=True,
            )
        with ex3:
            safe_pdf_download(result, pleading_title, fname, "pl_dl_pdf")
        with ex4:
            safe_docx_download(result, pleading_title, fname, "pl_dl_docx", doc_type="pleading")

        st.markdown(
            f'<div class="response-box">{esc(result)}</div>',
            unsafe_allow_html=True,
        )

        # ── Save to Case ──
        if pleading_case_id:
            sv1, sv2 = st.columns([3, 1])
            with sv1:
                st.caption(f"Save this pleading to: **{esc(pleading_case_title)}**")
            with sv2:
                if st.button(
                    "💾 Save to Case",
                    key="pl_save_case_btn",
                    type="primary", use_container_width=True,
                ):
                    save_analysis_to_case(
                        pleading_case_id,
                        f"[{pleading_title}]",
                        result, "drafting", mode,
                    )
                    st.success(
                        f"✅ {pleading_title} saved to case: {pleading_case_title}"
                    )

        # ── Clear ──
        if st.button("🗑️ Clear Draft", key="pl_clear_btn", use_container_width=True):
            st.session_state["pleading_result"] = ""
            st.session_state["pleading_title"] = ""
            st.rerun()

        st.markdown("""<div class="disclaimer">
            <strong>⚖️ Disclaimer:</strong> Review all AI-drafted pleadings
            carefully before filing. Verify all facts, parties, and reliefs
            against your instructions. Counsel remains responsible for all
            documents filed in court.
        </div>""", unsafe_allow_html=True)
