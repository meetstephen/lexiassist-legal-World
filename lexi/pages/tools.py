"""LexiAssist legal-reference tools page."""
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
# PAGE: TOOLS (EDITABLE REFERENCES)
# ═══════════════════════════════════════════════════════
def render_tools():
    st.markdown("""<div class="page-header">
        <h2>🔧 Legal Reference Tools</h2>
        <p>Limitation periods · Court hierarchy · Legal maxims — view and customise</p>
    </div>""", unsafe_allow_html=True)

    # ── Phase 4: Legal data version banner ──
    ldv = LEGAL_DATA_VERSION
    st.markdown(
        f'<div style="background:var(--la-bg2);border:1px solid var(--la-border);'
        f'border-left:4px solid #059669;border-radius:8px;'
        f'padding:0.6rem 1rem;margin-bottom:1rem;font-size:0.82rem;color:var(--la-text);">'
        f'📋 <strong style="color:var(--la-text);">Legal Data {esc(ldv["version"])}</strong>'
        f'<span style="color:var(--la-text2);"> · Last updated: {esc(ldv["updated"])}'
        f' · {esc(ldv["last_act"])}</span><br>'
        f'<span style="color:var(--la-text2);font-size:0.76rem;">{esc(ldv["notes"][:160])}…</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    tab_lim, tab_calc, tab_court, tab_maxim, tab_aml, tab_checklist, tab_authority = st.tabs(
        ["⏳ Limitation Periods", "🧮 Deadline Calculator", "🏛️ Court Hierarchy", "📜 Legal Maxims", "🛡️ AML / SCUML", "📋 Court Process Checklist", "🔍 Authority Verification"]
    )

    # ── Limitation Periods (editable) ──
    with tab_lim:
        _render_tools_lim()

    # ── Smart Deadline Calculator ──
    with tab_calc:
        _render_tools_calc()

    # ── Court Hierarchy ──
    with tab_court:
        _render_tools_court()

    # ── Legal Maxims (editable) ──
    with tab_maxim:
        _render_tools_maxim()

    # ── AML / SCUML Compliance ──
    with tab_aml:
        _render_tools_aml()

    with tab_checklist:
        _render_tools_checklist()

    with tab_authority:
        _render_tools_authority()



def _render_tools_lim() -> None:
    """Render the "Limitation Periods (editable)" tab body of the Tools page."""
    sub_view, sub_add = st.tabs(["📋 View All", "➕ Add Custom"])

    with sub_view:
        st.markdown("#### ⏳ Limitation Periods (Nigeria)")
        all_lim = get_all_limitation_periods()
        df_lim = pd.DataFrame(all_lim)
        if not df_lim.empty:
            df_lim.columns = ["Cause of Action", "Limitation Period", "Authority"]
            st.dataframe(df_lim, use_container_width=True, hide_index=True)
            st.download_button(
                "📥 Download CSV", df_lim.to_csv(index=False),
                "limitation_periods_nigeria.csv", "text/csv", key="dl_lim_csv",
            )

        # Show custom entries with delete option
        custom_lim = st.session_state.custom_limitation_periods
        if custom_lim:
            st.markdown("---")
            st.markdown("##### ✏️ Custom Entries")
            for i, lp in enumerate(custom_lim):
                lc1, lc2 = st.columns([5, 1])
                with lc1:
                    st.markdown(f"""<div class="tool-card">
                        <strong>{esc(lp['cause'])}</strong> — {esc(lp['period'])}<br>
                        <small>{esc(lp['authority'])}</small>
                        <span class="badge badge-info">Custom</span>
                    </div>""", unsafe_allow_html=True)
                with lc2:
                    if st.button("🗑️", key=f"del_lim_{i}", help="Delete this entry"):
                        st.session_state.custom_limitation_periods.pop(i)
                        persist("custom_limitation_periods")
                        st.rerun()

    with sub_add:
        st.markdown("#### ➕ Add Custom Limitation Period")
        with st.form("add_lim_form", clear_on_submit=True):
            lim_cause = st.text_input("Cause of Action *", key="lim_cause_inp")
            lim_period = st.text_input("Limitation Period *", placeholder="e.g. 6 years", key="lim_period_inp")
            lim_auth = st.text_input("Authority *", placeholder="e.g. Limitation Act, s. X", key="lim_auth_inp")
            if st.form_submit_button("➕ Add", type="primary"):
                if lim_cause.strip() and lim_period.strip() and lim_auth.strip():
                    st.session_state.custom_limitation_periods.append({
                        "cause": lim_cause.strip(),
                        "period": lim_period.strip(),
                        "authority": lim_auth.strip(),
                    })
                    persist("custom_limitation_periods")
                    st.success("✅ Added!")
                    st.rerun()
                else:
                    st.error("❌ All fields required.")


    # ── Smart Deadline Calculator ──


def _render_tools_calc() -> None:
    """Render the "Smart Deadline Calculator" tab body of the Tools page."""
    st.markdown("#### 🧮 AI Limitation Deadline Calculator")
    st.caption("Describe your case facts and the AI will compute your exact limitation deadline and days remaining.")
    calc_facts = st.text_area(
        "Case Facts",
        height=150,
        placeholder="e.g. My client was involved in a road accident on 15 March 2022 in Lagos. The negligent driver works for a government ministry. No action has been filed yet.",
        key="calc_facts_ta",
    )
    calc_btn = st.button(
        "🧮 Calculate Deadline",
        type="primary",
        disabled=not calc_facts.strip(),
        key="calc_deadline_btn", use_container_width=True,
    )
    if calc_btn and calc_facts.strip():
        calc_prompt = f"""
You are a Nigerian limitation period expert. Analyse these facts and compute ALL applicable
limitation periods. Today's date is {date.today().strftime('%d %B %Y')}.

CRITICAL SAFETY RULES:
- If the limitation period depends on State law, say so and identify which State Limitation Law applies.
- If public officer rules may apply, flag POPA/pre-action notice requirements separately.
- If continuing injury, fraud, concealment, disability, or acknowledgment may affect time, flag it.
- Do NOT give a hard final deadline where jurisdiction-specific verification is required.
- Always include a verification warning in special_notes.
- Distinguish between Federal limitation law and applicable State Limitation Laws.

Respond ONLY in this exact JSON format, nothing else:
{{
  "causes_of_action": [
    {{
      "cause": "Negligence/Tort",
      "limitation_period": "3 years",
      "authority": "Limitation Act Cap L16 LFN 2004, s.8(1)(b)",
      "event_date": "2022-03-15",
      "deadline_date": "2025-03-15",
      "days_remaining": 0,
      "status": "EXPIRED/URGENT/WARNING/SAFE",
      "special_notes": "Any special rule e.g. POPA notice requirement"
    }}
  ],
  "most_urgent": "Name of most urgent cause of action",
  "immediate_action": "What lawyer must do right now"
}}

FACTS: {calc_facts}
"""
        with st.spinner("⏱️ Computing limitation deadlines..."):
            raw = generate(calc_prompt, IDENTITY_CORE, "brief", "analysis")
        try:
            clean = raw.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
            causes = data.get("causes_of_action", [])
            st.markdown("---")
            for ca in causes:
                status = ca.get("status", "SAFE")
                days = int(ca.get("days_remaining", 0))
                if status == "EXPIRED":
                    card_color = "#fee2e2"
                    badge_class = "badge-err"
                    icon = "🔴"
                    days_text = f"EXPIRED {abs(days)} days ago"
                elif status == "URGENT":
                    card_color = "#fef3c7"
                    badge_class = "badge-warn"
                    icon = "🟡"
                    days_text = f"{days} days remaining"
                elif status == "WARNING":
                    card_color = "#fefce8"
                    badge_class = "badge-warn"
                    icon = "🟠"
                    days_text = f"{days} days remaining"
                else:
                    card_color = "#f0fdf4"
                    badge_class = "badge-ok"
                    icon = "🟢"
                    days_text = f"{days} days remaining"
                st.markdown(f"""
<div style="background:{card_color};border-radius:0.75rem;padding:1.2rem;
margin-bottom:1rem;border:1px solid #e5e7eb;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <h4 style="margin:0;">{icon} {esc(ca.get('cause',''))}</h4>
    <span class="badge {badge_class}">{esc(days_text)}</span>
  </div>
  <div style="margin-top:0.5rem;">
    ⏳ <strong>Limitation Period:</strong> {esc(ca.get('limitation_period',''))}
    &nbsp;|&nbsp;
    📅 <strong>Deadline:</strong> {esc(ca.get('deadline_date',''))}
  </div>
  <div>📖 <strong>Authority:</strong> {esc(ca.get('authority',''))}</div>
  {f"<div>⚠️ <strong>Note:</strong> {esc(ca.get('special_notes',''))}</div>"
    if ca.get('special_notes') else ""}
</div>""", unsafe_allow_html=True)
            st.error(f"🚨 Most Urgent: **{data.get('most_urgent', '')}**")
            st.warning(f"⚡ Immediate Action: {data.get('immediate_action', '')}")
            st.markdown(
                '<div style="background:var(--la-bg2);border:1px solid #fde047;border-radius:8px;'
                'padding:0.8rem 1rem;margin-top:1rem;font-size:0.83rem;color:#713f12;">'
                '<strong>⚠️ Important — Verify Before Relying:</strong> These deadlines are '
                'AI-computed estimates. Limitation periods vary by jurisdiction, cause of action, '
                'public officer exceptions, continuing injury, fraud/concealment, and applicable '
                'State Limitation Law. Always verify against the specific statute and consult '
                'applicable State Limitation Law before advising a client.'
                '</div>',
                unsafe_allow_html=True,
            )
        except Exception:
            st.markdown(raw)
    # ── PRE-ACTION NOTICE CHECKER (merged into same tab) ──
    st.markdown("---")
    st.markdown("#### ⚠️ Pre-Action Notice & Compliance Checker")
    st.caption(
        "Find out exactly what you must do BEFORE filing suit — "
        "notices, time gaps, letters, and statutory requirements. "
        "Missing these kills cases before they start."
    )

    pre_facts = st.text_area(
        "Case Facts for Pre-Action Check",
        height=130,
        key="pre_action_facts_ta",
        placeholder="""e.g. Client wants to sue the Lagos State Government
for wrongful termination of a contract worth ₦50M.
The contract was terminated in January 2024.
No pre-action steps have been taken yet.""",
    )

    pre_btn = st.button(
        "⚠️ Check Pre-Action Requirements",
        type="primary",
        disabled=not pre_facts.strip(),
        key="pre_action_btn", use_container_width=True,
    )

    if pre_btn and pre_facts.strip():
        pre_prompt = f"""
You are a senior Nigerian litigation lawyer. Analyse the facts below and
identify ALL pre-action requirements that must be satisfied before filing
suit in Nigeria. Today's date is {date.today().strftime('%d %B %Y')}.

Respond ONLY in this exact JSON format, nothing else:
{{
  "can_sue_immediately": false,
  "overall_status": "PRE-ACTION REQUIRED / READY TO FILE / INCOMPLETE",
  "summary": "One paragraph explaining the pre-action position",
  "requirements": [
    {{
      "requirement": "Pre-Action Notice to Government",
      "authority": "Public Officers Protection Act, s.2 / Attorney General Notice",
      "is_mandatory": true,
      "deadline_to_comply": "30 days before filing",
      "action_required": "Serve statutory notice on the relevant Ministry",
      "sample_wording": "One sentence sample wording for the notice or letter",
      "consequence_of_omission": "Suit will be statute-barred / struck out",
      "status": "PENDING/DONE/NOT APPLICABLE"
    }}
  ],
  "total_waiting_period": "Total days to wait before filing e.g. 30 days",
  "earliest_filing_date": "Estimated earliest date suit can be filed",
  "immediate_actions": [
    "Action 1 to take right now",
    "Action 2 to take right now"
  ],
  "common_mistakes": [
    "Common mistake lawyers make in this type of case"
  ]
}}

CASE FACTS: {pre_facts}
"""
        with st.spinner("⚠️ Checking pre-action requirements..."):
            pre_raw = generate(
                pre_prompt, IDENTITY_CORE, "brief", "procedure"
            )
        try:
            pre_clean = (
                pre_raw.strip()
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )
            pre_data = json.loads(pre_clean)

            # ── Overall status banner ──
            overall = pre_data.get("overall_status", "PRE-ACTION REQUIRED")
            can_sue = pre_data.get("can_sue_immediately", False)

            if can_sue:
                banner_color = "#f0fdf4"
                banner_border = "#059669"
                banner_icon = "✅"
                banner_text_color = "#059669"
            else:
                banner_color = "#fef3c7"
                banner_border = "#f59e0b"
                banner_icon = "⚠️"
                banner_text_color = "#d97706"

            st.markdown(f"""
<div style="background:{banner_color};border:2px solid {banner_border};
border-radius:0.75rem;padding:1.2rem;margin:1rem 0;">
  <h4 style="margin:0;color:{banner_text_color};">
    {banner_icon} {esc(overall)}
  </h4>
  <p style="margin:0.6rem 0 0 0;">{esc(pre_data.get('summary',''))}</p>
  <div style="margin-top:0.6rem;">
    ⏳ <strong>Total waiting period:</strong>
    {esc(pre_data.get('total_waiting_period',''))} &nbsp;|&nbsp;
    📅 <strong>Earliest filing date:</strong>
    {esc(pre_data.get('earliest_filing_date',''))}
  </div>
</div>""", unsafe_allow_html=True)

            # ── Requirements ──
            reqs = pre_data.get("requirements", [])
            if reqs:
                st.markdown(
                    f"##### 📋 {len(reqs)} Pre-Action Requirement(s)"
                )
                for req in reqs:
                    is_mandatory = req.get("is_mandatory", False)
                    status = req.get("status", "PENDING")

                    if status == "NOT APPLICABLE":
                        req_bg = "#f8fafc"
                        req_border = "#cbd5e1"
                        status_badge = "badge-info"
                    elif status == "DONE":
                        req_bg = "#f0fdf4"
                        req_border = "#059669"
                        status_badge = "badge-ok"
                    else:
                        req_bg = "#fef3c7"
                        req_border = "#f59e0b"
                        status_badge = "badge-warn"

                    mandatory_html = (
                        '<span class="badge badge-err">MANDATORY</span>'
                        if is_mandatory
                        else '<span class="badge badge-info">Recommended</span>'
                    )

                    st.markdown(f"""
<div style="background:{req_bg};border-left:4px solid {req_border};
border-radius:0.5rem;padding:1rem;margin-bottom:0.8rem;">
  <div style="display:flex;justify-content:space-between;
  align-items:flex-start;margin-bottom:0.4rem;">
    <strong>{esc(req.get('requirement',''))}</strong>
    <div>
      {mandatory_html}
      <span class="badge {status_badge}">{esc(status)}</span>
    </div>
  </div>
  <div>
    📖 <strong>Authority:</strong>
    <code>{esc(req.get('authority',''))}</code>
  </div>
  <div>
    ⏱️ <strong>Deadline:</strong> {esc(req.get('deadline_to_comply',''))}
  </div>
  <div>
    ✅ <strong>Action:</strong> {esc(req.get('action_required',''))}
  </div>
  {f'<div>📝 <strong>Sample wording:</strong> <em>{esc(req.get("sample_wording",""))}</em></div>'
    if req.get('sample_wording') else ''}
  <div style="color:#dc2626;">
    🚫 <strong>If omitted:</strong>
    {esc(req.get('consequence_of_omission',''))}
  </div>
</div>""", unsafe_allow_html=True)

            # ── Immediate actions ──
            immediate = pre_data.get("immediate_actions", [])
            if immediate:
                st.markdown("##### ⚡ Immediate Actions")
                for ia in immediate:
                    st.markdown(f"- {esc(ia)}")

            # ── Common mistakes ──
            mistakes = pre_data.get("common_mistakes", [])
            if mistakes:
                with st.expander(
                    "🚨 Common Mistakes to Avoid", expanded=False
                ):
                    for m in mistakes:
                        st.markdown(f"- {esc(m)}")

            # ── Export ──
            pre_report = (
                f"PRE-ACTION COMPLIANCE REPORT\n"
                f"Date: {datetime.now():%d %B %Y at %H:%M}\n"
                f"Status: {overall}\n"
                f"Earliest Filing: "
                f"{pre_data.get('earliest_filing_date','')}\n\n"
                f"SUMMARY:\n{pre_data.get('summary','')}\n\n"
                f"REQUIREMENTS:\n"
            )
            for req in reqs:
                pre_report += (
                    f"- {req.get('requirement','')} | "
                    f"{req.get('authority','')} | "
                    f"Deadline: {req.get('deadline_to_comply','')}\n"
                    f"  Action: {req.get('action_required','')}\n"
                    f"  If omitted: "
                    f"{req.get('consequence_of_omission','')}\n\n"
                )
            if immediate:
                pre_report += "IMMEDIATE ACTIONS:\n"
                for ia in immediate:
                    pre_report += f"- {ia}\n"

            pre_fname = (
                f"PreAction_Report_{datetime.now():%Y%m%d_%H%M}"
            )
            pe1, pe2, pe3 = st.columns(3)
            with pe1:
                st.download_button(
                    "📥 TXT Report",
                    export_txt(
                        pre_report,
                        "Pre-Action Compliance Report",
                    ),
                    f"{pre_fname}.txt",
                    "text/plain",
                    key="pre_dl_txt", use_container_width=True,
                )
            with pe2:
                st.download_button(
                    "📥 HTML Report",
                    export_html(
                        pre_report,
                        "Pre-Action Compliance Report",
                    ),
                    f"{pre_fname}.html",
                    "text/html",
                    key="pre_dl_html", use_container_width=True,
                )
            with pe3:
                safe_pdf_download(
                    pre_report,
                    "Pre-Action Compliance Report",
                    pre_fname,
                    "pre_dl_pdf",
                )

            st.markdown("""<div class="disclaimer">
                <strong>⚖️ Disclaimer:</strong>
                Pre-action requirements vary by state, court, and
                defendant type. Always verify requirements for the
                specific jurisdiction and court before filing.
            </div>""", unsafe_allow_html=True)

        except Exception:
            st.markdown(pre_raw)

    # ── Court Hierarchy ──


def _render_tools_court() -> None:
    """Render the "Court Hierarchy" tab body of the Tools page."""
    st.markdown("#### 🏛️ Nigerian Court Hierarchy & Jurisdiction Guide")
    st.caption("From the Supreme Court down to specialised tribunals")
    FULL_HIERARCHY = [
        {"level": 1, "name": "Supreme Court of Nigeria", "desc": "Final court of appeal. Hears appeals from Court of Appeal on civil and criminal matters. Exclusive original jurisdiction in disputes between States, or between States and the Federation — CFRN s. 233.", "icon": "🏛️"},
        {"level": 2, "name": "Court of Appeal", "desc": "Intermediate appellate court. 21 divisions across Nigeria. Hears appeals from FHC, State High Courts, NIC, Sharia Court of Appeal, Customary Court of Appeal — CFRN s. 240.", "icon": "⚖️"},
        {"level": 3, "name": "Federal High Court (FHC)", "desc": "Federal subject-matter jurisdiction: revenue, admiralty, banking, IP, immigration, company law (CAMA), capital market, EFCC/ICPC prosecutions, fundamental rights (federal) — CFRN s. 251.", "icon": "🏢"},
        {"level": 3, "name": "State High Courts", "desc": "Unlimited civil and criminal jurisdiction within each state. Hears all matters not exclusively conferred on FHC or NIC. Also hear fundamental rights enforcement — CFRN s. 272.", "icon": "🏢"},
        {"level": 3, "name": "National Industrial Court (NIC)", "desc": "Exclusive jurisdiction over labour, employment, trade unions, industrial relations, and workplace safety matters. Appeals to Court of Appeal — NIC Act 2006; CFRN Third Alteration 2010.", "icon": "🏢"},
        {"level": 3, "name": "High Court of the FCT", "desc": "Exercises State High Court equivalent jurisdiction for the Federal Capital Territory, Abuja.", "icon": "🏢"},
        {"level": 4, "name": "Magistrate / District Courts", "desc": "Summary criminal and civil jurisdiction up to statutory limits (varies by state — Lagos: ₦500k civil; FCT: ₦1m). First instance for most minor offences.", "icon": "📋"},
        {"level": 4, "name": "Customary Courts / Area Courts", "desc": "Apply customary law in civil and minor criminal matters. Prevalent in Northern and Midwestern states. Appeals to Customary Court of Appeal.", "icon": "📋"},
        {"level": 4, "name": "Sharia Courts of Appeal", "desc": "Appellate jurisdiction over Islamic personal law (marriage, divorce, inheritance, wakf) in the Northern States that have adopted full Sharia — CFRN s. 277.", "icon": "📋"},
        {"level": 5, "name": "Tax Appeal Tribunal (TAT)", "desc": "Hears appeals from FIRS and State IRS tax assessments. Six zones. 30-day appeal window. Appeals go to Federal High Court — FIRSEA 2007; TAT Rules 2021.", "icon": "🧮"},
        {"level": 5, "name": "Investment & Securities Tribunal (IST)", "desc": "Exclusive jurisdiction over capital market disputes — SEC, NSE/NGX matters. Appeals to Court of Appeal — ISA 2007.", "icon": "📈"},
        {"level": 5, "name": "Code of Conduct Tribunal (CCT)", "desc": "Tries public officers for breaches of the Code of Conduct — failure to declare assets, conflict of interest. Appeals to Court of Appeal — CFRN Fifth Schedule.", "icon": "🛡️"},
        {"level": 5, "name": "National Information Technology Development Agency (NITDA) Tribunal", "desc": "Data protection and IT regulatory disputes under the Nigeria Data Protection Act 2023.", "icon": "💻"},
    ]
    level_label_map = {1: "APEX", 2: "APPELLATE", 3: "SUPERIOR COURT", 4: "LOWER COURT", 5: "TRIBUNAL"}
    level_colors    = {1: "#dc2626", 2: "#d97706", 3: "#059669", 4: "#3b82f6", 5: "#7c3aed"}

    # Group courts by level for expanders
    from itertools import groupby
    by_level = {}
    for court in FULL_HIERARCHY:
        by_level.setdefault(court["level"], []).append(court)

    level_titles = {
        1: "🔴 Level 1 — Apex Court",
        2: "🟡 Level 2 — Appellate Court",
        3: "🟢 Level 3 — Superior Courts of Record",
        4: "🔵 Level 4 — Lower Courts",
        5: "🟣 Level 5 — Specialised Tribunals",
    }

    for lvl in sorted(by_level.keys()):
        courts_in_level = by_level[lvl]
        col = level_colors.get(lvl, "#64748b")
        with st.expander(level_titles[lvl], expanded=(lvl <= 2)):
            for c in courts_in_level:
                st.markdown(
                    f'<div style="background:var(--la-card);border-left:4px solid {col};'
                    f'border-radius:8px;padding:0.8rem 1rem;margin-bottom:0.6rem;">'
                    f'<strong style="color:var(--la-text);">{c["icon"]} {esc(c["name"])}</strong>'
                    f'<span style="font-size:0.72rem;font-weight:700;color:{col};'
                    f'background:transparent;border:1px solid {col};border-radius:1rem;'
                    f'padding:0.1rem 0.5rem;margin-left:0.5rem;">'
                    f'{level_label_map.get(lvl,"")}</span><br>'
                    f'<small style="color:var(--la-text2);line-height:1.6;">'
                    f'{esc(c["desc"])}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Legal Maxims (editable) ──


def _render_tools_maxim() -> None:
    """Render the "Legal Maxims (editable)" tab body of the Tools page."""
    sub_maxim_view, sub_maxim_add = st.tabs(["📋 View All", "➕ Add Custom"])

    with sub_maxim_view:
        st.markdown("#### 📜 Legal Maxims")
        search = st.text_input("🔍 Search maxims", key="maxim_search_inp", placeholder="E.g. 'nemo' or 'remedy'")
        all_maxims = get_all_maxims()
        maxims = all_maxims
        if search.strip():
            s = search.strip().lower()
            maxims = [m for m in maxims if s in m["maxim"].lower() or s in m["meaning"].lower()]

        st.caption(f"Showing {len(maxims)} maxim{'s' if len(maxims) != 1 else ''}")
        for m in maxims:
            is_custom = m not in DEFAULT_LEGAL_MAXIMS
            badge_extra = ' <span class="badge badge-info">Custom</span>' if is_custom else ""
            st.markdown(f"""<div class="tool-card">
                <strong><em>{esc(m['maxim'])}</em></strong>{badge_extra}<br>
                {esc(m['meaning'])}
            </div>""", unsafe_allow_html=True)

        # Manage custom maxims
        custom_maxims = st.session_state.custom_maxims
        if custom_maxims:
            st.markdown("---")
            st.markdown("##### ✏️ Manage Custom Maxims")
            for i, m in enumerate(custom_maxims):
                mc1, mc2 = st.columns([5, 1])
                with mc1:
                    st.caption(f"**{m['maxim']}** — {m['meaning']}")
                with mc2:
                    if st.button("🗑️", key=f"del_maxim_{i}", help="Delete"):
                        st.session_state.custom_maxims.pop(i)
                        persist("custom_maxims")
                        st.rerun()

    with sub_maxim_add:
        st.markdown("#### ➕ Add Custom Maxim")
        with st.form("add_maxim_form", clear_on_submit=True):
            maxim_latin = st.text_input("Latin Maxim *", key="maxim_latin_inp")
            maxim_meaning = st.text_input("English Meaning *", key="maxim_meaning_inp")
            if st.form_submit_button("➕ Add Maxim", type="primary"):
                if maxim_latin.strip() and maxim_meaning.strip():
                    st.session_state.custom_maxims.append({
                        "maxim": maxim_latin.strip(),
                        "meaning": maxim_meaning.strip(),
                    })
                    persist("custom_maxims")
                    st.success("✅ Maxim added!")
                    st.rerun()
                else:
                    st.error("❌ Both fields required.")

    # ── AML / SCUML Compliance ──


def _render_tools_aml() -> None:
    """Render the "AML / SCUML Compliance" tab body of the Tools page."""
    st.markdown("""<div class="page-header" style="margin-bottom:1rem;">
        <h2>🛡️ AML / SCUML Compliance Guide</h2>
        <p>Money Laundering (Prevention & Prohibition) Act 2022 · SCUML Registration · Know Your Client obligations</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""
<div class="custom-card">
<h4>📋 SCUML Registration — Is Your Firm Registered?</h4>
<p>The <strong>Special Control Unit Against Money Laundering (SCUML)</strong> operates under the Federal Ministry of Finance.
Legal practitioners handling <em>any</em> of the trigger transactions below are <strong>Designated Non-Financial Businesses and Professions (DNFBPs)</strong>
and must register with SCUML — <em>Money Laundering (Prevention & Prohibition) Act 2022, s. 26.</em></p>
<p><strong>Non-registration</strong> is a criminal offence carrying up to <strong>₦10 million fine</strong> and/or <strong>5 years imprisonment</strong>.</p>
</div>""", unsafe_allow_html=True)

    aml_c1, aml_c2 = st.columns(2)
    with aml_c1:
        st.markdown("""
<div class="custom-card">
<h4>⚡ Trigger Transactions (Register Required)</h4>
<ul>
<li>Real estate transactions (buying, selling, leasing)</li>
<li>Company incorporations, mergers, acquisitions</li>
<li>Management of client funds, bank accounts, or assets</li>
<li>Trust and company service provision</li>
<li>Any cash transaction ≥ <strong>₦5,000,000</strong> (individual) or <strong>₦10,000,000</strong> (company)</li>
<li>Wire transfers or cross-border payments on behalf of clients</li>
</ul>
<small><em>Source: MLPPA 2022, s. 25; SCUML Registration Guidelines</em></small>
</div>""", unsafe_allow_html=True)

    with aml_c2:
        st.markdown("""
<div class="custom-card">
<h4>📑 KYC Obligations — What You Must Collect</h4>
<ul>
<li><strong>Individual clients:</strong> Full name, DoB, address, BVN, valid ID (NIN, Int'l Passport, Driver's Licence)</li>
<li><strong>Corporate clients:</strong> CAC CTC, MEMART, board resolution, BEN form (beneficial owner > 5%), director IDs</li>
<li><strong>Politically Exposed Persons (PEPs):</strong> Enhanced Due Diligence — source of funds, senior management approval</li>
<li>Retain KYC records for <strong>minimum 5 years</strong> after the business relationship ends</li>
<li>File <strong>Suspicious Transaction Reports (STRs)</strong> with NFIU within 24 hours of suspicion</li>
</ul>
<small><em>Source: MLPPA 2022, ss. 3, 6, 13; CBN/SCUML AML/CFT Regulations</em></small>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🤖 AML Compliance Check (AI-Assisted)")
    st.caption("Describe a client matter and the AI will flag AML/CFT risks and your specific compliance obligations.")

    aml_facts = st.text_area(
        "Matter Facts for AML Check",
        height=130,
        key="aml_facts_ta",
        placeholder="e.g. A new client (company) wants us to handle the purchase of a ₦450M property in Lekki. They want to pay partly in cash. The directors are not well known. No previous business relationship.",
    )
    aml_btn = st.button(
        "🛡️ Run AML Compliance Check",
        type="primary",
        disabled=not aml_facts.strip(),
        key="aml_check_btn", use_container_width=True,
    )

    if aml_btn and aml_facts.strip():
        aml_prompt = f"""
You are a Nigerian AML/CFT compliance expert. Analyse the matter below for money laundering risks
and the lawyer's specific obligations under the Money Laundering (Prevention & Prohibition) Act 2022,
SCUML Registration Guidelines, and NFIU regulations. Today: {date.today().strftime('%d %B %Y')}.

Respond ONLY in this exact JSON format, nothing else:
{{
  "risk_rating": "LOW / MEDIUM / HIGH / VERY HIGH",
  "risk_summary": "One paragraph explaining the overall risk",
  "red_flags": [
    {{
      "flag": "Description of the red flag",
      "authority": "MLPPA 2022, s.X or SCUML Guideline",
      "severity": "High / Medium / Low"
    }}
  ],
  "obligations": [
    {{
      "obligation": "Specific legal obligation",
      "authority": "Specific provision",
      "action_required": "What the lawyer must do now",
      "deadline": "When it must be done"
    }}
  ],
  "scuml_registration_required": true,
  "str_required": false,
  "str_note": "Whether and why an STR should be filed",
  "proceed_advice": "PROCEED / PROCEED WITH EDD / DO NOT PROCEED",
  "proceed_reason": "Why"
}}

MATTER FACTS: {aml_facts}
"""
        with st.spinner("🛡️ Checking AML/CFT compliance…"):
            aml_raw = generate(aml_prompt, IDENTITY_CORE, "brief", "advisory")
        try:
            aml_clean = aml_raw.strip().replace("```json", "").replace("```", "").strip()
            aml_data = json.loads(aml_clean)
            risk = aml_data.get("risk_rating", "MEDIUM")
            risk_colors = {"LOW": ("#f0fdf4","#059669","badge-ok"),
                           "MEDIUM": ("#fef9c3","#d97706","badge-warn"),
                           "HIGH": ("#fee2e2","#dc2626","badge-err"),
                           "VERY HIGH": ("#fee2e2","#991b1b","badge-err")}
            r_bg, r_border, r_badge = risk_colors.get(risk, risk_colors["MEDIUM"])
            proceed = aml_data.get("proceed_advice","PROCEED WITH EDD")
            p_colors = {"PROCEED":("#f0fdf4","#059669"), "PROCEED WITH EDD":("#fef9c3","#d97706"), "DO NOT PROCEED":("#fee2e2","#dc2626")}
            p_bg, p_border = p_colors.get(proceed, ("#fef9c3","#d97706"))

            st.markdown(f"""
<div style="display:flex;gap:1rem;margin:1rem 0;">
  <div style="flex:1;background:{r_bg};border:2px solid {r_border};border-radius:.75rem;padding:1rem;text-align:center;">
    <div style="font-size:1.6rem;font-weight:800;color:{r_border};">{risk}</div>
    <div style="font-size:.78rem;text-transform:uppercase;letter-spacing:.06em;color:{r_border};">AML Risk Rating</div>
  </div>
  <div style="flex:2;background:{p_bg};border:2px solid {p_border};border-radius:.75rem;padding:1rem;">
    <strong style="color:{p_border};">{proceed}</strong><br>
    <span style="font-size:.9rem;">{esc(aml_data.get('proceed_reason',''))}</span>
  </div>
</div>
<p>{esc(aml_data.get('risk_summary',''))}</p>
""", unsafe_allow_html=True)

            red_flags = aml_data.get("red_flags", [])
            if red_flags:
                st.markdown(f"##### 🚩 {len(red_flags)} Red Flag(s) Identified")
                for rf in red_flags:
                    sev = rf.get("severity","Medium")
                    sev_cls = "badge-err" if sev=="High" else ("badge-warn" if sev=="Medium" else "badge-ok")
                    st.markdown(f"""<div class="custom-card">
                        🚩 {esc(rf.get('flag',''))}
                        <span class="badge {sev_cls}">{sev}</span><br>
                        <small>{esc(rf.get('authority',''))}</small>
                    </div>""", unsafe_allow_html=True)

            obls = aml_data.get("obligations", [])
            if obls:
                st.markdown(f"##### ✅ {len(obls)} Compliance Obligation(s)")
                for ob in obls:
                    st.markdown(f"""<div class="custom-card">
                        <strong>{esc(ob.get('obligation',''))}</strong><br>
                        📌 {esc(ob.get('action_required',''))}<br>
                        <small>⏰ {esc(ob.get('deadline',''))} · {esc(ob.get('authority',''))}</small>
                    </div>""", unsafe_allow_html=True)

            if aml_data.get("str_required"):
                st.error(f"🚨 **STR Required:** {aml_data.get('str_note','')} — File with NFIU within 24 hours.")
            elif aml_data.get("str_note"):
                st.info(f"ℹ️ **STR Note:** {aml_data.get('str_note','')}")

        except Exception:
            st.markdown(aml_raw)


    # ══════════════════════════════════════════════════════
    # TAB: COURT PROCESS CHECKLIST
    # ══════════════════════════════════════════════════════


def _render_tools_checklist() -> None:
    st.markdown("""<div class="page-header" style="margin-bottom:1rem;">
        <h2>📋 Court Process Checklist</h2>
        <p>Generate a step-by-step Nigerian court filing checklist for any matter type</p>
    </div>""", unsafe_allow_html=True)

    st.markdown(
        '<div style="background:var(--la-bg2);border:1px solid var(--la-border);'
        'border-left:4px solid #3b82f6;border-radius:8px;'
        'padding:0.7rem 1rem;margin-bottom:1rem;font-size:0.83rem;color:var(--la-text);">'
        '📌 <strong>How to use:</strong> Select the court, matter type and briefly describe the facts. '
        'LexiAssist will generate a step-by-step checklist covering jurisdiction basis, '
        'pre-action requirements, documents, filing steps, frontloading, service and common defects.'
        '</div>',
        unsafe_allow_html=True,
    )

    ch1, ch2 = st.columns(2)
    with ch1:
        chk_court = st.selectbox(
            "Court *",
            [
                "Supreme Court of Nigeria",
                "Court of Appeal",
                "Federal High Court",
                "High Court of Lagos State",
                "High Court of Abuja (FCT)",
                "High Court of Rivers State",
                "High Court of Kano State",
                "High Court of Ogun State",
                "Magistrate Court (Lagos)",
                "National Industrial Court",
                "Investment & Securities Tribunal",
                "Tax Appeal Tribunal",
                "Customary Court",
            ],
            key="chk_court_sel",
        )
        chk_matter = st.selectbox(
            "Matter Type *",
            [
                "Debt Recovery / Money Claim",
                "General Contract Dispute",
                "Fundamental Rights Enforcement",
                "Land / Property Dispute",
                "Defamation",
                "Employment / Wrongful Termination",
                "Company / Insolvency Matter",
                "Criminal Defence",
                "Election Petition",
                "Appeal (Civil)",
                "Appeal (Criminal)",
                "Judicial Review",
                "Interlocutory Application",
                "Matrimonial Causes",
                "Probate / Administration of Estate",
            ],
            key="chk_matter_sel",
        )
    with ch2:
        chk_party = st.selectbox(
            "Acting for",
            ["Claimant / Applicant / Plaintiff", "Defendant / Respondent", "Appellant", "Both parties (advising generally)"],
            key="chk_party_sel",
        )
        chk_state = st.selectbox(
            "Applicable State Rules",
            ["Lagos", "FCT / Abuja", "Rivers", "Kano", "Ogun", "Oyo", "Anambra", "Enugu", "Delta", "Cross River", "Federal (FHC Rules)"],
            key="chk_state_sel",
        )

    chk_facts = st.text_area(
        "Brief Facts (optional but recommended)",
        height=120,
        key="chk_facts_ta",
        placeholder="E.g. Client is owed N15 million under a written contract. Debtor has refused to pay. No pre-action notice sent yet. Client is a company registered in Lagos.",
    )

    if st.button("📋 Generate Court Process Checklist", type="primary", key="chk_gen_btn", use_container_width=True):
        chk_facts_clean = chk_facts.strip() or "Not provided — generate based on typical matter of this type."
        chk_prompt = (
            "You are an elite Nigerian litigator generating a Court Process Checklist.\n\n"
            f"COURT: {chk_court}\n"
            f"MATTER TYPE: {chk_matter}\n"
            f"ACTING FOR: {chk_party}\n"
            f"APPLICABLE STATE RULES: {chk_state}\n"
            f"FACTS: {chk_facts_clean}\n\n"
            "Generate a comprehensive step-by-step checklist. Respond ONLY in this JSON format:\n"
            '{\n'
            '  "summary": "One sentence describing the filing task",\n'
            '  "jurisdiction_basis": "Specific section of law conferring jurisdiction",\n'
            '  "pre_action": [\n'
            '    {"step": "Send Pre-Action Notice", "detail": "30 days — Order 13 Rule 14, Lagos HCCPR 2019", "mandatory": true}\n'
            '  ],\n'
            '  "documents_to_file": [\n'
            '    {"doc": "Writ of Summons", "copies": 3, "notes": "Signed by counsel — Order 3 Rule 2"}\n'
            '  ],\n'
            '  "filing_steps": [\n'
            '    {"step": "File at the registry", "detail": "Pay filing fees, obtain suit number", "deadline": "Before hearing date"}\n'
            '  ],\n'
            '  "frontloading": [\n'
            '    {"item": "Witness Statement on Oath", "notes": "All witnesses — Order 32 Rule 1"}\n'
            '  ],\n'
            '  "service": {"method": "Personal service", "timeframe": "Not less than 5 days before hearing", "authority": "Order 9 Rule 1"},\n'
            '  "common_defects": [\n'
            '    {"defect": "Missing pre-action notice", "consequence": "Suit may be struck out for non-compliance"}\n'
            '  ],\n'
            '  "estimated_timeline": "4-8 weeks to first hearing",\n'
            '  "warnings": [\n'
            f'    "Verify current filing fees at {chk_court} registry before filing"\n'
            '  ]\n'
            '}\n'
            f"Be specific to {chk_court} and {chk_state} rules. Every step must cite the applicable rule, order or statute."
        )
        with st.spinner(f"📋 Generating {chk_matter} checklist for {chk_court}…"):
            chk_raw = generate(chk_prompt, IDENTITY_CORE, "standard", "analysis")
        try:
            chk_data = json.loads(chk_raw.strip().replace("```json", "").replace("```", "").strip())
            st.session_state["_last_checklist"] = chk_data
            st.session_state["_last_checklist_meta"] = f"{chk_matter} — {chk_court} ({chk_state})"
            st.session_state["_last_checklist_raw"] = ""
        except Exception:
            st.session_state["_last_checklist"] = None
            st.session_state["_last_checklist_raw"] = chk_raw

    chk_data = st.session_state.get("_last_checklist")
    chk_raw_fb = st.session_state.get("_last_checklist_raw", "")
    chk_meta = st.session_state.get("_last_checklist_meta", "")

    if chk_data:
        st.markdown("---")
        st.markdown(f"### 📋 {esc(chk_meta)}")
        st.markdown(
            f'<div style="background:var(--la-bg2);border-left:4px solid #6366f1;'
            f'border-radius:8px;padding:0.6rem 1rem;margin-bottom:1rem;font-size:0.9rem;">'
            f'<strong>{esc(chk_data.get("summary", ""))}</strong><br>'
            f'<small>Jurisdiction: {esc(chk_data.get("jurisdiction_basis", ""))}</small>'
            f'</div>',
            unsafe_allow_html=True,
        )

        for w in chk_data.get("warnings", []):
            st.warning(f"⚠️ {w}")

        col_a, col_b = st.columns(2)
        with col_a:
            if chk_data.get("pre_action"):
                st.markdown("#### 📨 Pre-Action Requirements")
                for i, s in enumerate(chk_data["pre_action"], 1):
                    mand = "🔴 MANDATORY" if s.get("mandatory") else "🟡 Recommended"
                    st.markdown(
                        f'<div style="background:var(--la-bg2);border:1px solid var(--la-border);'
                        f'border-radius:6px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;">'
                        f'<strong>{i}. {esc(s.get("step", ""))}</strong> '
                        f'<span style="font-size:0.75rem;color:var(--la-text2);">{mand}</span><br>'
                        f'<small>{esc(s.get("detail", ""))}</small></div>',
                        unsafe_allow_html=True,
                    )

            if chk_data.get("documents_to_file"):
                st.markdown("#### 📄 Documents to File")
                for d in chk_data["documents_to_file"]:
                    st.markdown(
                        f'<div style="background:var(--la-card);border:1px solid var(--la-border);border-left:4px solid #059669;'
                        f'border-radius:6px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;">'
                        f'📄 <strong>{esc(d.get("doc", ""))}</strong> — {esc(str(d.get("copies", "")))} copies<br>'
                        f'<small>{esc(d.get("notes", ""))}</small></div>',
                        unsafe_allow_html=True,
                    )

            if chk_data.get("frontloading"):
                st.markdown("#### 📎 Frontloading Requirements")
                for f in chk_data["frontloading"]:
                    st.markdown(
                        f'<div style="background:#fdf4ff;border:1px solid #e9d5ff;'
                        f'border-radius:6px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;">'
                        f'📎 <strong>{esc(f.get("item", ""))}</strong><br>'
                        f'<small>{esc(f.get("notes", ""))}</small></div>',
                        unsafe_allow_html=True,
                    )

        with col_b:
            if chk_data.get("filing_steps"):
                st.markdown("#### 🗂️ Filing Steps")
                for i, s in enumerate(chk_data["filing_steps"], 1):
                    deadline_txt = f" · ⏰ {esc(s['deadline'])}" if s.get("deadline") else ""
                    st.markdown(
                        f'<div style="background:var(--la-bg2);border:1px solid var(--la-border);'
                        f'border-radius:6px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;">'
                        f'<strong>{i}. {esc(s.get("step", ""))}</strong><br>'
                        f'<small>{esc(s.get("detail", ""))}{deadline_txt}</small></div>',
                        unsafe_allow_html=True,
                    )

            if chk_data.get("service"):
                srv = chk_data["service"]
                st.markdown("#### 📬 Service Requirements")
                st.markdown(
                    f'<div style="background:var(--la-bg2);border:1px solid var(--la-border);border-left:4px solid #3b82f6;'
                    f'border-radius:6px;padding:0.6rem 0.9rem;margin-bottom:0.6rem;">'
                    f'<strong>{esc(srv.get("method", ""))}</strong><br>'
                    f'<small>⏰ {esc(srv.get("timeframe", ""))} · {esc(srv.get("authority", ""))}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            if chk_data.get("common_defects"):
                st.markdown("#### 🚨 Common Filing Defects")
                for d in chk_data["common_defects"]:
                    st.markdown(
                        f'<div style="background:var(--la-card);border:1px solid var(--la-border);border-left:4px solid #dc2626;'
                        f'border-radius:6px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;">'
                        f'🚨 <strong>{esc(d.get("defect", ""))}</strong><br>'
                        f'<small style="color:#dc2626;">{esc(d.get("consequence", ""))}</small></div>',
                        unsafe_allow_html=True,
                    )

            if chk_data.get("estimated_timeline"):
                st.markdown("#### ⏱️ Estimated Timeline")
                st.info(f"⏱️ {chk_data['estimated_timeline']}")

        # Export to TXT
        chk_export = f"COURT PROCESS CHECKLIST\n{chk_meta}\n{'='*50}\n\n"
        chk_export += f"SUMMARY: {chk_data.get('summary', '')}\n"
        chk_export += f"JURISDICTION: {chk_data.get('jurisdiction_basis', '')}\n\n"
        for section, label, key1, key2 in [
            ("pre_action", "PRE-ACTION REQUIREMENTS", "step", "detail"),
            ("documents_to_file", "DOCUMENTS TO FILE", "doc", "notes"),
            ("filing_steps", "FILING STEPS", "step", "detail"),
            ("frontloading", "FRONTLOADING", "item", "notes"),
            ("common_defects", "COMMON FILING DEFECTS", "defect", "consequence"),
        ]:
            items = chk_data.get(section, [])
            if items:
                chk_export += f"\n{label}\n{'-'*40}\n"
                for it in items:
                    chk_export += f"  • {it.get(key1, '')}: {it.get(key2, '')}\n"
        if chk_data.get("service"):
            srv = chk_data["service"]
            chk_export += f"\nSERVICE\n{'-'*40}\n  Method: {srv.get('method','')}\n  Timeframe: {srv.get('timeframe','')}\n  Authority: {srv.get('authority','')}\n"
        if chk_data.get("warnings"):
            chk_export += f"\nWARNINGS\n{'-'*40}\n"
            for w in chk_data["warnings"]:
                chk_export += f"  ⚠️  {w}\n"
        chk_export += f"\n{'='*50}\nGenerated by LexiAssist · {datetime.now():%d %B %Y %H:%M}\n"
        chk_export += "⚠️ AI-generated. Verify all steps against current court rules before filing.\n"

        st.markdown("---")
        st.download_button(
            "📥 Download Checklist (TXT)",
            chk_export,
            f"LexiAssist_CourtChecklist_{datetime.now():%Y%m%d_%H%M}.txt",
            "text/plain",
            key="chk_dl_txt",
            use_container_width=True,
        )
        st.caption("⚠️ AI-generated checklist. Verify all steps and fees against current court rules before filing.")

    elif chk_raw_fb:
        st.markdown("---")
        st.markdown(f'<div class="response-box">{esc(chk_raw_fb)}</div>', unsafe_allow_html=True)



    # ══════════════════════════════════════════════════════
    # TAB: AUTHORITY VERIFICATION MODE
    # ══════════════════════════════════════════════════════


def _render_tools_authority() -> None:
    st.markdown("""<div class="page-header" style="margin-bottom:1rem;">
        <h2>🔍 Authority Verification Mode</h2>
        <p>Paste any AI-generated legal argument — LexiAssist will check every citation</p>
    </div>""", unsafe_allow_html=True)

    st.markdown(
        '<div style="background:var(--la-bg2);border:1px solid var(--la-border);'
        'border-left:4px solid #3b82f6;border-radius:8px;'
        'padding:0.7rem 1rem;margin-bottom:1rem;font-size:0.83rem;color:var(--la-text);">'
        '🔍 <strong>How it works:</strong> Paste AI-generated text or a legal argument. '
        'LexiAssist extracts every statute, case, and rule cited, then checks each one against '
        'its verified Nigerian legal database and flags hallucinations, repealed laws, and unverified authorities.'
        '</div>',
        unsafe_allow_html=True,
    )

    av_text = st.text_area(
        "Paste AI output or legal argument to verify *",
        height=220,
        key="av_input_text",
        placeholder=(
            "Paste any legal text here — e.g. an AI-generated analysis, a draft pleading, "
            "a research memo, or any text containing case names, statutes, or rules you want verified...\n\n"
            "Example:\n"
            "The applicant relies on Madukolu v Nkemdilim (1962) for the jurisdiction test. "
            "See also CAMA 2020 s. 394. The Companies Act 1990 applies to winding-up proceedings. "
            "Per Donoghue v Stevenson (1932), a duty of care arises..."
        ),
    )

    if st.button("🔍 Verify All Authorities", type="primary", key="av_verify_btn", use_container_width=True):
        if not av_text.strip():
            st.error("❌ Please paste some text to verify.")
        else:
            # Build the verified cases reference for context
            _known_cases = "\n".join(
                f"- {name}: {info.get('citation','')} ({info.get('court','')}, {info.get('year','')})"
                for name, info in list(VERIFIED_NIGERIAN_CASES.items())[:80]
            )

            av_prompt = (
                "You are a Nigerian legal citation verification expert.\n\n"
                "Extract EVERY legal authority from the text below — cases, statutes, regulations, rules, "
                "constitutional provisions — and verify each one.\n\n"
                "VERIFIED NIGERIAN CASES IN DATABASE:\n"
                f"{_known_cases}\n\n"
                "For each authority found, return this JSON array:\n"
                '[\n'
                '  {\n'
                '    "authority": "Madukolu v Nkemdilim",\n'
                '    "type": "Case",\n'
                '    "status": "Verified",\n'
                '    "problem": "",\n'
                '    "fix": "Good citation — use as stated",\n'
                '    "confidence": 95\n'
                '  },\n'
                '  {\n'
                '    "authority": "Companies Act 1990",\n'
                '    "type": "Statute",\n'
                '    "status": "Repealed",\n'
                '    "problem": "Repealed and replaced by CAMA 2020",\n'
                '    "fix": "Replace with CAMA 2020 and cite the specific section",\n'
                '    "confidence": 98\n'
                '  },\n'
                '  {\n'
                '    "authority": "Donoghue v Stevenson (1932)",\n'
                '    "type": "Case",\n'
                '    "status": "Foreign",\n'
                '    "problem": "English case — persuasive only, not binding in Nigerian courts",\n'
                '    "fix": "Find Nigerian equivalent or use as persuasive authority with caveat",\n'
                '    "confidence": 99\n'
                '  }\n'
                ']\n\n'
                'Status options: "Verified" | "Unverified" | "Possible Hallucination" | "Repealed" | '
                '"Foreign" | "Needs Section Number" | "Check Spelling"\n\n'
                'Respond ONLY with the JSON array. No preamble.\n\n'
                f'TEXT TO VERIFY:\n{av_text[:6000]}'
            )

            with st.spinner("🔍 Extracting and verifying authorities…"):
                av_raw = generate(av_prompt, IDENTITY_CORE, "brief", "analysis")

            try:
                av_results = json.loads(
                    av_raw.strip().replace("```json", "").replace("```", "").strip()
                )
                st.session_state["_av_results"] = av_results
                st.session_state["_av_source_text"] = av_text.strip()
            except Exception:
                st.session_state["_av_results"] = None
                st.session_state["_av_raw"] = av_raw

    av_results = st.session_state.get("_av_results")
    av_raw_fb  = st.session_state.get("_av_raw", "")

    if av_results:
        st.markdown("---")

        # Summary counts
        counts = {"Verified": 0, "Repealed": 0, "Foreign": 0,
                  "Unverified": 0, "Possible Hallucination": 0, "Other": 0}
        for r in av_results:
            s = r.get("status", "Other")
            if s in counts:
                counts[s] += 1
            else:
                counts["Other"] += 1

        total = len(av_results)
        st.markdown(f"### 🔍 Verification Results — {total} authorit{'y' if total == 1 else 'ies'} found")

        sc1, sc2, sc3, sc4, sc5 = st.columns(5)
        for col, label, key, colour in [
            (sc1, "✅ Verified",     "Verified",               "#16a34a"),
            (sc2, "⚠️ Unverified",  "Unverified",             "#d97706"),
            (sc3, "🚨 Hallucinated","Possible Hallucination",  "#dc2626"),
            (sc4, "🗑️ Repealed",   "Repealed",               "#7c3aed"),
            (sc5, "🌍 Foreign",     "Foreign",                 "#0891b2"),
        ]:
            with col:
                col.markdown(
                    f'<div style="background:var(--la-card);border:1px solid var(--la-border);'
                    f'border-radius:8px;padding:0.6rem;text-align:center;">'
                    f'<div style="font-size:1.4rem;font-weight:800;color:{colour};">{counts[key]}</div>'
                    f'<div style="font-size:0.72rem;color:var(--la-text2);">{label}</div></div>',
                    unsafe_allow_html=True,
                )

        st.markdown("")

        # Status colours and icons
        STATUS_META = {
            "Verified":               ("#16a34a", "#f0fdf4", "#bbf7d0", "✅"),
            "Unverified":             ("#d97706", "#fffbeb", "#fde68a", "⚠️"),
            "Possible Hallucination": ("#dc2626", "#fef2f2", "#fecaca", "🚨"),
            "Repealed":               ("#7c3aed", "#fdf4ff", "#e9d5ff", "🗑️"),
            "Foreign":                ("#0891b2", "#ecfeff", "#a5f3fc", "🌍"),
            "Needs Section Number":   ("#d97706", "#fffbeb", "#fde68a", "📌"),
            "Check Spelling":         ("#f59e0b", "#fffbeb", "#fde68a", "✏️"),
        }
        DEFAULT_META = ("#64748b", "var(--la-bg2)", "var(--la-border)", "❓")

        for r in av_results:
            status = r.get("status", "Unverified")
            colour, bg, border_c, icon = STATUS_META.get(status, DEFAULT_META)
            conf = r.get("confidence", 0)

            st.markdown(
                f'<div style="background:{bg};border:1px solid {border_c};'
                f'border-left:4px solid {colour};border-radius:8px;'
                f'padding:0.75rem 1rem;margin-bottom:0.5rem;">'
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:flex-start;flex-wrap:wrap;gap:0.3rem;">'
                f'<div>'
                f'<strong>{icon} {esc(r.get("authority",""))}</strong>'
                f' <span style="font-size:0.75rem;color:{colour};font-weight:600;">'
                f'[{esc(r.get("type",""))}] — {esc(status)}</span>'
                f'{"<br><span style=\'color:#dc2626;font-size:0.82rem;\'>⚠️ " + esc(r.get("problem","")) + "</span>" if r.get("problem") else ""}'
                f'{"<br><span style=\'color:#16a34a;font-size:0.82rem;\'>💡 " + esc(r.get("fix","")) + "</span>" if r.get("fix") else ""}'
                f'</div>'
                f'<div style="font-size:0.75rem;color:var(--la-text2);white-space:nowrap;">'
                f'Confidence: <strong style="color:{colour};">{conf}%</strong>'
                f'</div></div></div>',
                unsafe_allow_html=True,
            )

        # Export report
        av_export = "AUTHORITY VERIFICATION REPORT\n"
        av_export += f"Generated: {datetime.now():%d %B %Y %H:%M}\n"
        av_export += f"Total authorities checked: {total}\n"
        av_export += f"Verified: {counts['Verified']} | Unverified: {counts['Unverified']} | "
        av_export += f"Repealed: {counts['Repealed']} | Hallucinated: {counts['Possible Hallucination']} | Foreign: {counts['Foreign']}\n"
        av_export += "=" * 60 + "\n\n"
        for r in av_results:
            av_export += f"AUTHORITY: {r.get('authority','')}\n"
            av_export += f"  Type:       {r.get('type','')}\n"
            av_export += f"  Status:     {r.get('status','')}\n"
            av_export += f"  Confidence: {r.get('confidence',0)}%\n"
            if r.get("problem"):
                av_export += f"  Problem:    {r['problem']}\n"
            if r.get("fix"):
                av_export += f"  Fix:        {r['fix']}\n"
            av_export += "\n"
        av_export += "=" * 60 + "\n"
        av_export += "⚠️ AI-generated verification. Always independently confirm before relying in court.\n"

        st.markdown("---")
        st.download_button(
            "📥 Download Verification Report (TXT)",
            av_export,
            f"LexiAssist_AuthVerification_{datetime.now():%Y%m%d_%H%M}.txt",
            "text/plain",
            key="av_dl_btn",
            use_container_width=True,
        )
        st.caption("⚠️ AI-generated verification. Always independently confirm all authorities before relying on them in any court filing or client advice.")

    elif av_raw_fb:
        st.markdown("---")
        st.markdown(f'<div class="response-box">{esc(av_raw_fb)}</div>', unsafe_allow_html=True)
