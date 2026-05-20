"""LexiAssist matter-lifecycle automation."""
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
# PAGE: MATTER LIFECYCLE AUTOMATION
# ═══════════════════════════════════════════════════════
CASE_TYPE_OPTIONS = [
    "Breach of Contract",
    "Land / Property Dispute",
    "Criminal Defence",
    "Employment / Wrongful Termination",
    "Fundamental Rights Enforcement",
    "Debt Recovery",
    "Matrimonial / Family Law",
    "Company / Commercial Dispute",
    "Defamation",
    "Personal Injury / Negligence",
    "Election Petition",
    "Judicial Review / Certiorari",
    "Tenancy / Landlord-Tenant",
    "Probate / Estate Administration",
    "Other (describe below)",
]

LIFECYCLE_PROMPT = """
You are a senior Nigerian litigation lawyer. Generate a complete matter lifecycle workflow
for the case described below.

Respond ONLY in this exact JSON format, nothing else:
{{
  "case_type": "Breach of Contract",
  "court_recommendation": "Lagos State High Court",
  "estimated_duration": "12-18 months",
  "total_stages": 6,
  "stages": [
    {{
      "stage_number": 1,
      "stage_name": "Client Intake & Brief",
      "description": "One sentence describing this stage",
      "duration_estimate": "1-3 days",
      "required_documents": [
        "Instructions letter from client",
        "Copies of contract documents",
        "Evidence of breach"
      ],
      "required_actions": [
        "Obtain full instructions from client",
        "Review all contract documents",
        "Conduct conflict of interest check"
      ],
      "deadline_trigger": "Immediately on instruction",
      "warning": "Any critical warning for this stage or empty string"
    }}
  ],
  "limitation_alert": "Limitation period warning if any",
  "pre_action_requirements": [
    "Any pre-action notices required before filing"
  ],
  "top_risks": [
    "Top 3 risks for this matter"
  ],
  "immediate_next_step": "Single most important action to take right now"
}}

CASE DETAILS:
Case Type: {case_type}
Case Title: {case_title}
Court: {court}
Brief Facts: {facts}
"""


def render_lifecycle():
    st.markdown("""<div class="page-header">
        <h2>⚡ Matter Lifecycle Automation</h2>
        <p>Auto-generate complete case workflows · stages · deadlines · documents · actions</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key first.")
        return

    cases = st.session_state.cases
    if not cases:
        st.info("No cases found. Add a case in the 📁 Cases tab first, then return here to generate its lifecycle.")
        return

    db = get_db()

    # ── Case selector ──
    st.markdown("### 📁 Select a Case")
    lc1, lc2 = st.columns([3, 1])
    with lc1:
        case_names = [
            f"{c.get('title', 'Untitled')} ({c.get('suit_no', '—')})"
            for c in cases
        ]
        selected_case_name = st.selectbox(
            "Choose case",
            case_names,
            key="lifecycle_case_sel",
            label_visibility="collapsed",
        )
    selected_idx = case_names.index(selected_case_name)
    selected_case = cases[selected_idx]
    case_id = selected_case["id"]

    with lc2:
        st.metric("Status", selected_case.get("status", "—"))

    # ── Case type + facts input ──
    st.markdown("---")
    st.markdown("### ⚙️ Configure Lifecycle Generation")
    gc1, gc2 = st.columns(2)
    with gc1:
        case_type = st.selectbox(
            "Case Type *",
            CASE_TYPE_OPTIONS,
            key="lifecycle_case_type",
        )
        if case_type == "Other (describe below)":
            case_type = st.text_input(
                "Describe case type",
                key="lifecycle_custom_type",
                placeholder="e.g. Insurance claim dispute",
            )
    with gc2:
        court_input = st.text_input(
            "Court (if known)",
            value=selected_case.get("court", ""),
            key="lifecycle_court_inp",
            placeholder="e.g. Federal High Court Lagos",
        )

    facts_input = st.text_area(
        "Brief Facts (optional but improves accuracy)",
        height=120,
        key="lifecycle_facts_inp",
        placeholder="""e.g. Client entered into a supply contract with defendant in Jan 2023.
Defendant received goods worth ₦12M but refused to pay after 90 days.
Multiple demand letters sent. No response. Client wants to sue.""",
    )

    generate_btn = st.button(
        "⚡ Generate Matter Lifecycle",
        type="primary", use_container_width=True,
        key="lifecycle_generate_btn",
        disabled=not case_type,
    )

    if generate_btn:
        prompt = LIFECYCLE_PROMPT.format(
            case_type=case_type,
            case_title=selected_case.get("title", ""),
            court=court_input or "To be determined",
            facts=facts_input or "Not provided",
        )
        with st.spinner("⚡ Building matter lifecycle workflow..."):
            raw = generate(prompt, IDENTITY_CORE, "standard", "analysis")
        try:
            clean = raw.strip().replace("```json", "").replace("```", "").strip()
            lifecycle_data = json.loads(clean)
            db.save_lifecycle(case_id, lifecycle_data)
            # Initialise progress — all stages incomplete
            progress = {
                str(i): False
                for i in range(1, lifecycle_data.get("total_stages", 0) + 1)
            }
            existing_progress = db.load_lifecycle_progress(case_id)
            if not existing_progress:
                db.save_lifecycle_progress(case_id, progress)
            st.success("✅ Lifecycle generated and saved to this case!")
            st.rerun()
        except Exception:
            st.markdown(raw)

    # ── Display saved lifecycle ──
    lifecycle = db.load_lifecycle(case_id)
    if not lifecycle:
        st.info("No lifecycle generated for this case yet. Fill in the form above and click Generate.")
        return

    progress = db.load_lifecycle_progress(case_id)
    if not progress:
        progress = {
            str(i): False
            for i in range(1, lifecycle.get("total_stages", 0) + 1)
        }

    st.markdown("---")

    # ── Summary banner ──
    sc1, sc2, sc3, sc4 = st.columns(4)
    completed = sum(1 for v in progress.values() if v)
    total = lifecycle.get("total_stages", 0)
    pct = int((completed / total) * 100) if total else 0
    with sc1:
        st.metric("Case Type", lifecycle.get("case_type", "—"))
    with sc2:
        st.metric("Recommended Court", lifecycle.get("court_recommendation", "—"))
    with sc3:
        st.metric("Est. Duration", lifecycle.get("estimated_duration", "—"))
    with sc4:
        st.metric("Progress", f"{completed}/{total} stages ({pct}%)")

    # Progress bar
    st.markdown(f"""
<div style="background:#e5e7eb;border-radius:999px;height:16px;margin:0.5rem 0 1.5rem 0;">
  <div style="width:{pct}%;background:#059669;height:16px;border-radius:999px;
  transition:width 0.5s;"></div>
</div>""", unsafe_allow_html=True)

    # ── Alerts ──
    if lifecycle.get("limitation_alert"):
        st.error(f"⏳ **Limitation Alert:** {lifecycle['limitation_alert']}")
    if lifecycle.get("pre_action_requirements"):
        with st.expander("⚠️ Pre-Action Requirements (must complete before filing)", expanded=True):
            for req in lifecycle["pre_action_requirements"]:
                st.markdown(f"- {esc(req)}")
    if lifecycle.get("top_risks"):
        with st.expander("🔴 Top Risks for This Matter", expanded=False):
            for risk in lifecycle["top_risks"]:
                st.markdown(f"- {esc(risk)}")

    st.markdown(f"""
<div style="background:#f0fdf4;border-left:4px solid #059669;
padding:1rem;border-radius:0.5rem;margin-bottom:1.5rem;">
  <strong>⚡ Immediate Next Step:</strong> {esc(lifecycle.get('immediate_next_step', ''))}
</div>""", unsafe_allow_html=True)

    # ── Stages ──
    st.markdown("### 📋 Case Stages")
    stages = lifecycle.get("stages", [])

    for stage in stages:
        stage_num = str(stage.get("stage_number", ""))
        is_done = progress.get(stage_num, False)

        if is_done:
            card_color = "#f0fdf4"
            border_color = "#059669"
            status_icon = "✅"
        else:
            card_color = "#ffffff"
            border_color = "#e5e7eb"
            status_icon = "⬜"

        # Check if previous stage done (for sequential enforcement)
        prev_done = True
        if stage.get("stage_number", 1) > 1:
            prev_done = progress.get(str(stage.get("stage_number", 1) - 1), False)

        with st.expander(
            f"{status_icon} Stage {stage_num}: {stage.get('stage_name', '')} "
            f"— {stage.get('duration_estimate', '')}",
            expanded=not is_done,
        ):
            st.markdown(f"""
<div style="background:{card_color};border:1px solid {border_color};
border-radius:0.75rem;padding:1.2rem;">
  <p>{esc(stage.get('description', ''))}</p>
  <p><strong>⏱️ Duration:</strong> {esc(stage.get('duration_estimate', ''))} &nbsp;|&nbsp;
  <strong>📅 Trigger:</strong> {esc(stage.get('deadline_trigger', ''))}</p>
  {f'<div style="background:var(--la-bg2);border-left:3px solid #f59e0b;padding:0.6rem;border-radius:0.3rem;margin-top:0.5rem;"><strong>⚠️ Warning:</strong> {esc(stage.get("warning",""))}</div>' if stage.get("warning") else ""}
</div>""", unsafe_allow_html=True)

            dc1, dc2 = st.columns(2)
            with dc1:
                st.markdown("**📄 Required Documents:**")
                for doc in stage.get("required_documents", []):
                    st.markdown(f"- {esc(doc)}")
            with dc2:
                st.markdown("**✅ Required Actions:**")
                for action in stage.get("required_actions", []):
                    st.markdown(f"- {esc(action)}")

            st.markdown("")
            btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 1])
            with btn_col1:
                if not is_done:
                    if st.button(
                        f"✅ Mark Stage {stage_num} Complete",
                        key=f"lc_done_{case_id}_{stage_num}",
                        type="primary", use_container_width=True,
                    ):
                        progress[stage_num] = True
                        db.save_lifecycle_progress(case_id, progress)
                        st.success(f"Stage {stage_num} marked complete!")
                        st.rerun()
                else:
                    if st.button(
                        f"↩️ Reopen Stage {stage_num}",
                        key=f"lc_undo_{case_id}_{stage_num}", use_container_width=True,
                    ):
                        progress[stage_num] = False
                        db.save_lifecycle_progress(case_id, progress)
                        st.rerun()
            with btn_col2:
                # Generate document for this stage
                if st.button(
                    f"📄 Draft Stage Document",
                    key=f"lc_draft_{case_id}_{stage_num}", use_container_width=True,
                ):
                    draft_prompt = (
                        f"Case: {selected_case.get('title', '')}\n"
                        f"Court: {selected_case.get('court', '')}\n"
                        f"Suit No: {selected_case.get('suit_no', '')}\n"
                        f"Stage: {stage.get('stage_name', '')}\n"
                        f"Required Documents: {', '.join(stage.get('required_documents', []))}\n\n"
                        f"Draft the most important document needed for this stage. "
                        f"Use [PLACEHOLDER] for missing information."
                    )
                    system = build_system_prompt("drafting", "standard")
                    with st.spinner(f"📄 Drafting {stage.get('stage_name','')} document..."):
                        draft_result = generate(draft_prompt, system, "standard", "drafting")
                    st.markdown(f'<div class="response-box">{esc(draft_result)}</div>',
                                unsafe_allow_html=True)
                    save_analysis_to_case(
                        case_id,
                        f"[Lifecycle Stage {stage_num}] {stage.get('stage_name','')}",
                        draft_result, "drafting", "standard",
                    )
                    fname = f"Stage{stage_num}_{stage.get('stage_name','').replace(' ','_')}"
                    dl1, dl2 = st.columns(2)
                    with dl1:
                        st.download_button(
                            "📥 TXT", export_txt(draft_result, stage.get("stage_name", "")),
                            f"{fname}.txt", "text/plain",
                            key=f"lc_dl_txt_{case_id}_{stage_num}", use_container_width=True,
                        )
                    with dl2:
                        safe_docx_download(
                            draft_result, stage.get("stage_name", ""),
                            fname, f"lc_dl_docx_{case_id}_{stage_num}",
                        )

    # ── Regenerate ──
    st.markdown("---")
    rg1, rg2 = st.columns(2)
    with rg1:
        if st.button(
            "🔄 Regenerate Lifecycle",
            key="lifecycle_regen_btn", use_container_width=True,
        ):
            db.save_lifecycle(case_id, {})
            db.save_lifecycle_progress(case_id, {})
            st.success("Lifecycle cleared. Scroll up and regenerate.")
            st.rerun()
    with rg2:
        # Export full lifecycle as TXT
        lifecycle_text = f"MATTER LIFECYCLE — {selected_case.get('title','')}\n"
        lifecycle_text += f"Court: {lifecycle.get('court_recommendation','')}\n"
        lifecycle_text += f"Duration: {lifecycle.get('estimated_duration','')}\n\n"
        for s in stages:
            lifecycle_text += f"STAGE {s.get('stage_number','')}: {s.get('stage_name','')}\n"
            lifecycle_text += f"  {s.get('description','')}\n"
            lifecycle_text += f"  Documents: {', '.join(s.get('required_documents',[]))}\n"
            lifecycle_text += f"  Actions: {', '.join(s.get('required_actions',[]))}\n\n"
        st.download_button(
            "📥 Export Full Lifecycle (TXT)",
            export_txt(lifecycle_text, f"Matter Lifecycle — {selected_case.get('title','')}"),
            f"Lifecycle_{selected_case.get('title','').replace(' ','_')}.txt",
            "text/plain",
            key="lifecycle_export_btn", use_container_width=True,
        )
