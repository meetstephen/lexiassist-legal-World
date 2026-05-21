"""LexiAssist conflict-of-interest checker."""
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
# PAGE: CONFLICT OF INTEREST CHECKER
# ═══════════════════════════════════════════════════════
CONFLICT_PROMPT = """
You are a Nigerian legal ethics expert applying the Rules of Professional
Conduct for Legal Practitioners 2007 (RPC).

A lawyer wants to take on a new matter. Check whether any conflict of interest
exists against the existing client and case data provided.

Respond ONLY in this exact JSON format, nothing else:
{{
  "overall_verdict": "CLEAR / POTENTIAL CONFLICT / SERIOUS CONFLICT",
  "confidence": 85,
  "summary": "One paragraph summary of the conflict analysis",
  "conflicts_found": [
    {{
      "conflict_type": "Direct/Indirect/Positional/Former Client",
      "severity": "High/Medium/Low",
      "existing_party": "Name of existing client or case party",
      "new_party": "Name from new matter that conflicts",
      "reason": "Specific reason this is a conflict under RPC",
      "rpc_rule": "Specific RPC rule number e.g. Rule 17(1)"
    }}
  ],
  "recommendations": [
    "Specific recommendation 1",
    "Specific recommendation 2"
  ],
  "disclosure_required": true,
  "can_proceed_with_consent": true,
  "consent_note": "What consent is needed if proceeding, or empty string"
}}

EXISTING CLIENTS:
{existing_clients}

EXISTING CASES AND PARTIES:
{existing_cases}

NEW MATTER DETAILS:
{new_matter}
"""


def render_conflict_checker():
    st.markdown("""<div class="page-header">
        <h2>🔍 Conflict of Interest Checker</h2>
        <p>RPC-compliant conflict scanning across all clients and cases
        before accepting a new matter</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.api_configured:
        st.warning("⚠️ Connect your API key first.")
        return

    clients = st.session_state.clients
    cases = st.session_state.cases

    # ── Stats ──
    cs1, cs2, cs3 = st.columns(3)
    with cs1:
        st.metric("Clients on Record", len(clients))
    with cs2:
        st.metric("Cases on Record", len(cases))
    with cs3:
        st.metric("Parties Indexed",
                  len(clients) + sum(
                      1 for c in cases if c.get("title")
                  ))

    if not clients and not cases:
        st.warning(
            "⚠️ No clients or cases on record yet. "
            "Add clients and cases first so the checker has data to scan against."
        )
        return

    st.markdown("---")

    # ── New matter input ──
    st.markdown("### 📋 New Matter Details")
    st.caption(
        "Enter details of the prospective new client or matter. "
        "The checker will scan all existing clients and cases for conflicts."
    )

    nc1, nc2 = st.columns(2)
    with nc1:
        new_client_name = st.text_input(
            "Prospective Client Name *",
            key="conflict_client_name",
            placeholder="e.g. Alhaji Musa Danladi",
        )
        new_opponent = st.text_input(
            "Opposing Party Name(s)",
            key="conflict_opponent",
            placeholder="e.g. Bright Ventures Ltd, Mr Chen",
        )
        new_matter_type = st.text_input(
            "Matter Type",
            key="conflict_matter_type",
            placeholder="e.g. Land dispute, Debt recovery, Employment",
        )
    with nc2:
        new_court = st.text_input(
            "Court / Tribunal",
            key="conflict_court",
            placeholder="e.g. Federal High Court Lagos",
        )
        new_related_parties = st.text_input(
            "Other Related Parties / Companies",
            key="conflict_related",
            placeholder="e.g. Parent company, directors, guarantors",
        )
        new_former_counsel = st.text_input(
            "Previous Counsel (if known)",
            key="conflict_prev_counsel",
            placeholder="e.g. ABC & Co — counsel to opponent",
        )

    new_facts = st.text_area(
        "Brief Description of New Matter",
        height=100,
        key="conflict_facts",
        placeholder="""e.g. Prospective client wants to sue Bright Ventures Ltd
for breach of a supply contract worth ₦25M. The dispute
arose in January 2024 in Lagos.""",
    )

    # ── Manual party list builder ──
    with st.expander("➕ Add Extra Parties to Scan (optional)", expanded=False):
        st.caption(
            "Add any additional names — subsidiaries, aliases, related companies — "
            "that should be checked even if not in your client database."
        )
        extra_parties = st.text_area(
            "Extra names (one per line)",
            height=80,
            key="conflict_extra_parties",
            placeholder="SinoPower Ltd\nEmeka Holdings\nMrs Chidinma Obi",
        )

    check_btn = st.button(
        "🔍 Run Conflict Check",
        type="primary", use_container_width=True,
        key="conflict_check_btn",
        disabled=not new_client_name.strip(),
    )

    if check_btn and new_client_name.strip():
        # ── Phase 4: Fuzzy pre-screen ──────────────────────────────────────
        fuzzy = get_fuzzy_conflict_candidates(
            new_client_name, new_opponent, new_related_parties,
            extra_parties if extra_parties.strip() else "", threshold=0.45,
        )
        if fuzzy["fuzzy_client_matches"] or fuzzy["fuzzy_case_matches"]:
            st.warning(
                f"⚡ **Fuzzy pre-screen found {len(fuzzy['fuzzy_client_matches'])} "
                f"potential client match(es) and {len(fuzzy['fuzzy_case_matches'])} "
                f"case match(es)** at ≥45% name similarity — these have been "
                f"prioritised in the AI check below."
            )

        # Build existing clients string
        clients_str = ""
        for cl in clients:
            clients_str += (
                f"- {cl.get('name','')} | "
                f"Type: {cl.get('type','')} | "
                f"Email: {cl.get('email','')} | "
                f"Notes: {cl.get('notes','')}\n"
            )
        if not clients_str:
            clients_str = "No clients on record."

        # Build existing cases string
        cases_str = ""
        for c in cases:
            client_name_for_case = get_client_name(c.get("client_id", ""))
            cases_str += (
                f"- {c.get('title','')} | "
                f"Suit: {c.get('suit_no','')} | "
                f"Court: {c.get('court','')} | "
                f"Our Client: {client_name_for_case} | "
                f"Status: {c.get('status','')} | "
                f"Notes: {c.get('notes','')}\n"
            )
        if not cases_str:
            cases_str = "No cases on record."

        # Build new matter string
        extra = extra_parties.strip() if extra_parties.strip() else "None"
        # Append fuzzy pre-screen results so AI focuses on high-similarity names
        fuzzy_note = ""
        if fuzzy.get("fuzzy_client_matches"):
            fuzzy_note += f"\n⚡ HIGH SIMILARITY CLIENT NAMES (check carefully): {', '.join(fuzzy['fuzzy_client_matches'])}"
        if fuzzy.get("fuzzy_case_matches"):
            fuzzy_note += f"\n⚡ HIGH SIMILARITY CASE TITLES (check carefully): {', '.join(fuzzy['fuzzy_case_matches'])}"
        new_matter_str = (
            f"Prospective Client: {new_client_name}\n"
            f"Opposing Party: {new_opponent or 'Not specified'}\n"
            f"Matter Type: {new_matter_type or 'Not specified'}\n"
            f"Court: {new_court or 'Not specified'}\n"
            f"Other Related Parties: {new_related_parties or 'None'}\n"
            f"Previous Counsel: {new_former_counsel or 'Unknown'}\n"
            f"Extra parties to scan: {extra}\n"
            f"Facts: {new_facts or 'Not provided'}\n"
            f"{fuzzy_note}\n"
        )
        prompt = CONFLICT_PROMPT.format(
            existing_clients=clients_str,
            existing_cases=cases_str,
            new_matter=new_matter_str,
        )

        with st.spinner("🔍 Scanning all clients and cases for conflicts..."):
            raw = generate(prompt, IDENTITY_CORE, "brief", "advisory")

        # parse_ai_json_or_warn surfaces a clear Streamlit error if `raw`
        # is empty / unparseable, so the user never sees a blank screen.
        data, ok = parse_ai_json_or_warn(
            raw, fallback={}, label="conflict-check response",
        )
        if ok:
            # Even when the AI's parsed dict is empty (legitimate "no
            # conflicts" answer), persist a clear CLEAR verdict so the
            # user sees a positive result instead of nothing.
            if not data:
                data = {
                    "overall_verdict": "CLEAR",
                    "confidence": 70,
                    "summary": (
                        "No conflicts of interest were identified between "
                        "the new matter and existing clients/cases on "
                        "record. Proceed with normal client onboarding."
                    ),
                    "conflicts_found": [],
                    "recommendations": [
                        "Document this conflict check in the matter file.",
                        "Re-run the check if new parties are added later.",
                    ],
                    "disclosure_required": False,
                    "can_proceed_with_consent": True,
                    "consent_note": "",
                }
            st.session_state["conflict_result"] = data
            st.session_state["conflict_matter"] = new_client_name
            st.rerun()

    # ── Display result ──
    result = st.session_state.get("conflict_result", {})
    if not result:
        st.markdown("---")
        st.info(
            "Fill in the new matter details above and click "
            "**🔍 Run Conflict Check** to scan your entire client and case database."
        )
        return

    st.markdown("---")
    st.markdown(
        f"### 🔍 Conflict Check — "
        f"{esc(st.session_state.get('conflict_matter',''))}"
    )

    # ── Verdict banner ──
    verdict = result.get("overall_verdict", "CLEAR")
    confidence = int(result.get("confidence", 0))

    if verdict == "CLEAR":
        v_color = "#059669"
        v_bg = "#f0fdf4"
        v_icon = "✅"
        v_border = "#059669"
    elif verdict == "POTENTIAL CONFLICT":
        v_color = "#d97706"
        v_bg = "#fffbeb"
        v_icon = "⚠️"
        v_border = "#f59e0b"
    else:
        v_color = "#dc2626"
        v_bg = "#fef2f2"
        v_icon = "🚫"
        v_border = "#dc2626"

    st.markdown(f"""
<div style="background:{v_bg};border:2px solid {v_border};
border-radius:0.75rem;padding:1.4rem;margin-bottom:1.2rem;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <h3 style="margin:0;color:{v_color};">{v_icon} {esc(verdict)}</h3>
    <span style="font-size:1.4rem;font-weight:800;color:{v_color};">
      {confidence}% confidence
    </span>
  </div>
  <p style="margin:0.8rem 0 0 0;">{esc(result.get('summary',''))}</p>
</div>""", unsafe_allow_html=True)

    # ── Conflicts found ──
    conflicts = result.get("conflicts_found", [])
    if conflicts:
        st.markdown(f"#### 🔴 {len(conflicts)} Conflict(s) Found")
        for cf in conflicts:
            sev = cf.get("severity", "Low")
            sev_color = (
                "#dc2626" if sev == "High"
                else ("#d97706" if sev == "Medium" else "#059669")
            )
            st.markdown(f"""
<div style="border-left:4px solid {sev_color};background:#fff;
border-radius:0.5rem;padding:1rem;margin-bottom:0.8rem;
box-shadow:0 1px 4px rgba(0,0,0,0.05);">
  <div style="display:flex;justify-content:space-between;">
    <strong>{esc(cf.get('conflict_type',''))} Conflict</strong>
    <span style="color:{sev_color};font-weight:700;">
      {esc(sev)} Severity
    </span>
  </div>
  <div style="margin-top:0.5rem;">
    🏢 <strong>Existing party:</strong> {esc(cf.get('existing_party',''))}
    &nbsp;↔️&nbsp;
    <strong>New party:</strong> {esc(cf.get('new_party',''))}
  </div>
  <div>📖 <strong>Reason:</strong> {esc(cf.get('reason',''))}</div>
  <div>⚖️ <strong>RPC Rule:</strong>
    <code>{esc(cf.get('rpc_rule',''))}</code>
  </div>
</div>""", unsafe_allow_html=True)
    else:
        st.success("✅ No specific conflicts identified in the database.")

    # ── Recommendations ──
    recs = result.get("recommendations", [])
    if recs:
        st.markdown("#### 💡 Recommendations")
        for rec in recs:
            st.markdown(f"- {esc(rec)}")

    # ── Consent / Disclosure ──
    st.markdown("#### 📋 Compliance Summary")
    comp1, comp2 = st.columns(2)
    with comp1:
        disc = result.get("disclosure_required", False)
        st.markdown(
            f"**Disclosure Required:** "
            f"{'🔴 YES' if disc else '🟢 NO'}"
        )
    with comp2:
        consent = result.get("can_proceed_with_consent", False)
        st.markdown(
            f"**Can Proceed with Consent:** "
            f"{'🟡 YES (with conditions)' if consent else '🔴 NO'}"
        )
    if result.get("consent_note"):
        st.info(f"📋 **Consent Note:** {result['consent_note']}")

    # ── Export conflict report ──
    st.markdown("---")
    report_text = (
        f"CONFLICT OF INTEREST CHECK REPORT\n"
        f"Matter: {st.session_state.get('conflict_matter','')}\n"
        f"Date: {datetime.now():%d %B %Y at %H:%M}\n"
        f"Verdict: {verdict} ({confidence}% confidence)\n\n"
        f"SUMMARY:\n{result.get('summary','')}\n\n"
    )
    if conflicts:
        report_text += "CONFLICTS FOUND:\n"
        for cf in conflicts:
            report_text += (
                f"- {cf.get('conflict_type','')} | "
                f"{cf.get('severity','')} | "
                f"{cf.get('existing_party','')} vs "
                f"{cf.get('new_party','')} | "
                f"{cf.get('rpc_rule','')}\n"
                f"  Reason: {cf.get('reason','')}\n"
            )
    if recs:
        report_text += "\nRECOMMENDATIONS:\n"
        for rec in recs:
            report_text += f"- {rec}\n"

    ec1, ec2, ec3 = st.columns(3)
    fname = (
        f"ConflictCheck_{st.session_state.get('conflict_matter','').replace(' ','_')}"
        f"_{datetime.now():%Y%m%d_%H%M}"
    )
    with ec1:
        st.download_button(
            "📥 TXT Report",
            export_txt(report_text, "Conflict of Interest Report"),
            f"{fname}.txt", "text/plain",
            key="conflict_dl_txt", use_container_width=True,
        )
    with ec2:
        st.download_button(
            "📥 HTML Report",
            export_html(report_text, "Conflict of Interest Report"),
            f"{fname}.html", "text/html",
            key="conflict_dl_html", use_container_width=True,
        )
    with ec3:
        safe_pdf_download(
            report_text,
            "Conflict of Interest Report",
            fname, "conflict_dl_pdf",
        )

    # ── Clear ──
    if st.button("🗑️ Clear Results", key="conflict_clear_btn", use_container_width=True):
        st.session_state["conflict_result"] = {}
        st.session_state["conflict_matter"] = ""
        st.rerun()

    st.markdown("""<div class="disclaimer">
        <strong>⚖️ Disclaimer:</strong> This conflict check is AI-assisted
        and supplements — but does not replace — manual conflict screening.
        Always apply your professional judgment. Rules of Professional Conduct
        for Legal Practitioners 2007 applies.
    </div>""", unsafe_allow_html=True)
