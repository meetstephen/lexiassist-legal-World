"""LexiAssist legal fee + stamp duty calculator."""
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
# PAGE: LEGAL FEE & STAMP DUTY CALCULATOR
# ═══════════════════════════════════════════════════════
def render_fee_calculator():
    st.markdown("""<div class="page-header">
        <h2>⚖️ Legal Fee & Stamp Duty Calculator</h2>
        <p>Nigerian scale fees · Stamp duty on instruments · Court filing fees · Professional fee note</p>
    </div>""", unsafe_allow_html=True)

    tab_land, tab_stamp, tab_court, tab_feenote = st.tabs([
        "🏠 Solicitor's Scale Fees",
        "📄 Stamp Duty",
        "🏛️ Court Filing Fees",
        "🧾 Generate Fee Note",
    ])

    # ═══════════════════════════════════════
    # TAB 1 — SOLICITOR'S SCALE FEES (LAND)
    # ═══════════════════════════════════════
    with tab_land:
        st.markdown("#### 🏠 Land Matters Remuneration Scale")
        st.caption(
            "Based on the Legal Practitioners (Remuneration for Legal Documentation "
            "and Other Land Matters) Order. Applies to: Deeds of Assignment, Conveyances, "
            "Governor's Consent, Mortgages, and related documentation."
        )
        lf1, lf2 = st.columns([2, 1])
        with lf1:
            land_value = st.number_input(
                "Transaction / Property Value (₦)",
                min_value=0.0, value=5_000_000.0, step=100_000.0,
                format="%.2f", key="land_val_inp",
            )
            st.caption(f"Entered: **{fmt_ngn(land_value)}**")
        with lf2:
            include_vat = st.checkbox("Add 7.5% VAT on fees", value=True, key="land_vat_chk")
            show_breakdown = st.checkbox("Show band-by-band breakdown", value=True, key="land_bband")

        if st.button("🔢 Calculate Fees", type="primary", key="land_calc_btn", use_container_width=True):
            st.session_state["lf_value"] = land_value
            st.session_state["lf_vat"] = include_vat

        lf_value = st.session_state.get("lf_value", 0.0)
        if lf_value > 0:
            base_fee, breakdown = compute_land_fee(lf_value)
            vat = base_fee * 0.075 if include_vat else 0.0
            total = base_fee + vat

            st.markdown("---")
            # Result cards
            r1, r2, r3 = st.columns(3)
            with r1:
                st.markdown(f"""<div class="stat-card">
                    <div class="stat-value">{fmt_ngn(base_fee)}</div>
                    <div class="stat-label">Base Solicitor's Fee</div>
                </div>""", unsafe_allow_html=True)
            with r2:
                st.markdown(f"""<div class="stat-card">
                    <div class="stat-value">{fmt_ngn(vat)}</div>
                    <div class="stat-label">VAT (7.5%)</div>
                </div>""", unsafe_allow_html=True)
            with r3:
                st.markdown(f"""<div class="stat-card">
                    <div class="stat-value">{fmt_ngn(total)}</div>
                    <div class="stat-label">Total Chargeable</div>
                </div>""", unsafe_allow_html=True)

            effective_rate = (base_fee / lf_value * 100) if lf_value > 0 else 0
            st.info(f"💡 Effective rate: **{effective_rate:.3f}%** on {fmt_ngn(lf_value)}")

            if show_breakdown:
                st.markdown("##### 📊 Band-by-Band Breakdown")
                import pandas as pd
                df = pd.DataFrame([
                    {
                        "Band": row["band"],
                        "Taxable Amount": fmt_ngn(row["taxable"]),
                        "Rate": row["rate"],
                        "Fee": fmt_ngn(row["fee"]),
                    }
                    for row in breakdown
                ])
                if include_vat:
                    df.loc[len(df)] = {"Band": "VAT (7.5%)", "Taxable Amount": "", "Rate": "7.5%", "Fee": fmt_ngn(vat)}
                df.loc[len(df)] = {"Band": "TOTAL", "Taxable Amount": "", "Rate": "", "Fee": fmt_ngn(total)}
                st.dataframe(df, use_container_width=True, hide_index=True)

            # Store for fee note tab
            st.session_state["fn_land_fee"] = base_fee
            st.session_state["fn_land_vat"] = vat
            st.session_state["fn_land_total"] = total
            st.session_state["fn_land_value"] = lf_value

        st.markdown("""<div class="disclaimer">
            <strong>⚖️ Note:</strong> Scale fees under the Land Matters Remuneration Order represent
            the minimum chargeable by a legal practitioner. Fees may be higher by agreement.
            Minimum fee: ₦10,000. Always issue a formal Fee Agreement Letter.
        </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════
    # TAB 2 — STAMP DUTY
    # ═══════════════════════════════════════
    with tab_stamp:
        st.markdown("#### 📄 Stamp Duty Calculator")
        st.caption(
            "Stamp Duties Act Cap S8 LFN 2004, as amended by the Finance Acts 2019–2023. "
            "Stamp duty is payable before or within 30 days of execution of the instrument."
        )

        sd1, sd2 = st.columns([2, 1])
        with sd1:
            instrument_key = st.selectbox(
                "Instrument Type",
                list(STAMP_DUTY_INSTRUMENTS.keys()),
                format_func=lambda k: STAMP_DUTY_INSTRUMENTS[k]["label"],
                key="sd_instrument_sel",
            )
        with sd2:
            st.markdown("<br>", unsafe_allow_html=True)
            inst = STAMP_DUTY_INSTRUMENTS[instrument_key]
            st.info(f"💡 **Rate:** {inst['note']}")

        basis = inst["basis"]
        sd_value = 0.0
        sd_years = 1.0
        sd_annual = 0.0

        if basis == "flat":
            st.metric("Stamp Duty Payable", fmt_ngn(inst.get("flat", 0)))
            st.session_state["fn_stamp_duty"] = float(inst.get("flat", 0))
        else:
            v1, v2 = st.columns(2)
            with v1:
                if basis in ("property_value", "consideration", "contract_value", "secured_amount"):
                    sd_value = st.number_input("Transaction / Property Value (₦)",
                        min_value=0.0, value=10_000_000.0, step=500_000.0,
                        format="%.2f", key="sd_value_inp")
                elif basis == "loan_amount":
                    sd_value = st.number_input("Loan / Secured Amount (₦)",
                        min_value=0.0, value=5_000_000.0, step=250_000.0,
                        format="%.2f", key="sd_loan_inp")
                elif basis == "guaranteed_sum":
                    sd_value = st.number_input("Guaranteed / Indemnified Sum (₦)",
                        min_value=0.0, value=5_000_000.0, step=250_000.0,
                        format="%.2f", key="sd_guar_inp")
                elif "annual_rent" in basis:
                    sd_annual = st.number_input("Annual Rent (₦)",
                        min_value=0.0, value=1_200_000.0, step=100_000.0,
                        format="%.2f", key="sd_rent_inp")
            with v2:
                if basis == "annual_rent_x_years":
                    sd_years = st.number_input("Number of Years",
                        min_value=0.5, max_value=6.9, value=2.0, step=0.5, key="sd_years_inp")
                    st.caption(f"Annual rent: {fmt_ngn(sd_annual)} × {sd_years} years")

            duty = compute_stamp_duty(
                instrument_key,
                value=sd_value if sd_value > 0 else sd_annual,
                years=sd_years,
                annual_rent=sd_annual,
            )

            if st.button("🔢 Calculate Stamp Duty", type="primary",
                         key="sd_calc_btn", use_container_width=True):
                st.session_state["sd_result"] = duty

            sd_result = st.session_state.get("sd_result", None)
            if sd_result is not None:
                st.markdown("---")
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    st.metric("Stamp Duty", fmt_ngn(sd_result))
                with sc2:
                    effective = (sd_result / (sd_value or sd_annual * sd_years or 1)) * 100
                    st.metric("Effective Rate", f"{effective:.3f}%")
                with sc3:
                    st.metric("Penalty (if late > 30 days)", fmt_ngn(sd_result * 0.1 + 50))
                st.markdown(f"""
<div style="background:#fffbeb;border-left:3px solid #f59e0b;padding:0.8rem 1rem;
border-radius:0.4rem;margin-top:0.5rem;font-size:0.9rem;">
  ⚠️ <strong>Reminder:</strong> Stamp duty must be paid within 30 days of execution.
  Late stamping attracts a 10% penalty plus ₦50 administrative charge.
  Unstamped instruments are inadmissible in evidence (Stamp Duties Act, s.22).
</div>""", unsafe_allow_html=True)
                st.session_state["fn_stamp_duty"] = sd_result

        st.markdown("""<div class="disclaimer">
            <strong>⚖️ Note:</strong> Rates reflect the Stamp Duties Act and Finance Act amendments.
            Stamp duty on electronic transactions and receipts (₦50 on transactions above ₦10,000)
            may apply separately. Confirm with FIRS or relevant State tax authority.
        </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════
    # TAB 3 — COURT FILING FEES
    # ═══════════════════════════════════════
    with tab_court:
        st.markdown("#### 🏛️ Court Filing Fee Estimator")
        st.markdown(
            '<div style="background:var(--la-bg2);border:1px solid #f59e0b;border-radius:8px;'
            'padding:0.6rem 1rem;font-size:0.82rem;color:var(--la-text);margin-bottom:0.5rem;">'
            '<strong>⚠️ Estimate Only — Verify Before Filing:</strong> These fees are '
            'indicative and based on the applicable Rules of Court. Registry fees change '
            'without notice. <strong>Always confirm the exact fee schedule at the relevant '
            'court registry before filing or advising any client on litigation costs.</strong>'
            '</div>',
            unsafe_allow_html=True,
        )

        cf1, cf2 = st.columns(2)
        with cf1:
            court_key = st.selectbox(
                "Select Court",
                list(COURT_FILING_FEES.keys()),
                format_func=lambda k: (
                    f"{COURT_FILING_FEES[k]['label']} "
                    f"(verified: {COURT_FILING_FEES[k].get('last_verified', '—')})"
                ),
                key="cf_court_sel",
            )
        with cf2:
            claim_val = st.number_input(
                "Claim Value (₦)",
                min_value=0.0, value=10_000_000.0, step=500_000.0,
                format="%.2f", key="cf_claim_inp",
            )
            st.caption(f"Claim: **{fmt_ngn(claim_val)}**")

        if st.button("🔢 Get Filing Fees", type="primary", key="cf_calc_btn", use_container_width=True):
            st.session_state["cf_result"] = (court_key, claim_val)

        cf_result = st.session_state.get("cf_result", None)
        if cf_result:
            ck, cv = cf_result
            court = COURT_FILING_FEES[ck]
            filing_fee, court_note = get_court_filing_fee(ck, cv)
            appeal_fee = court.get("appeal_fee", 0)

            st.markdown("---")
            ff1, ff2, ff3 = st.columns(3)
            with ff1:
                st.metric("Originating Process Fee", fmt_ngn(filing_fee))
            with ff2:
                st.metric("Estimated Appeal Fee", fmt_ngn(appeal_fee))
            with ff3:
                st.metric("Filing + Service (est.)",
                          fmt_currency(filing_fee + filing_fee * 0.3))

            verified_on = court.get("last_verified", "—")
            st.info(f"ℹ️ **{court['label']}:** {court_note}")
            st.markdown(
                f'<div style="background:var(--la-bg2);border:1px solid #f59e0b;border-radius:6px;'
                f'padding:0.55rem 0.9rem;margin:0.4rem 0 0.8rem 0;font-size:0.82rem;color:var(--la-text);">'
                f'⚠️ <strong>Registry fees change without notice.</strong> '
                f'These figures are estimates based on court rules verified in '
                f'<strong>{esc(verified_on)}</strong>. '
                f'This calculator is an <em>estimate only</em> — '
                f'<strong>confirm the exact fee schedule at the {esc(court["label"])} registry '
                f'before filing or quoting costs to any client.</strong>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # All bands table
            st.markdown("##### 📊 Full Fee Schedule — " + court["label"])
            band_rows = []
            for band in court["bands"]:
                cap = band["claim_max"]
                band_rows.append({
                    "Claim Range": band["label"],
                    "Filing Fee": fmt_currency(band["fee"]),
                })
            import pandas as pd
            st.dataframe(pd.DataFrame(band_rows), use_container_width=True, hide_index=True)

            # Other cost estimates
            st.markdown("##### 💰 Estimated Total Costs to File")
            items = [
                ("Court filing fee", filing_fee),
                ("Sheriff / Process server fee (est.)", filing_fee * 0.2),
                ("Certified true copies (est.)", 2_000),
                ("Solicitor's filing charges (est.)", 5_000),
            ]
            total_costs = sum(v for _, v in items)
            for label, val in items:
                st.markdown(f"- {label}: **{fmt_currency(val)}**")
            st.markdown(f"**Estimated total to file: {fmt_currency(total_costs)}**")
            st.session_state["fn_court_fee"] = filing_fee

        st.markdown("""<div class="disclaimer">
            <strong>⚖️ Disclaimer:</strong> All filing fees shown are indicative estimates based 
            on the Rules of Court in force at the date of last verification. Court registries 
            revise fees periodically and without public notice. These figures must not be 
            quoted to clients as confirmed costs. <strong>Always obtain the current official 
            fee schedule directly from the relevant court registry before filing any process 
            or advising any client on the cost of litigation.</strong>
        </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════
    # TAB 4 — GENERATE PROFESSIONAL FEE NOTE
    # ═══════════════════════════════════════
    with tab_feenote:
        st.markdown("#### 🧾 Professional Fee Note Generator")
        st.caption(
            "Generate a formal, professionally formatted Fee Note / Bill of Costs "
            "ready to issue to your client. Uses values computed in the other tabs."
        )
        fn1, fn2 = st.columns(2)
        with fn1:
            fn_client = st.text_input("Client Name *", key="fn_client_inp",
                                      placeholder="Chief Emeka Obi / ABC Ltd")
            fn_matter = st.text_input("Matter Description *", key="fn_matter_inp",
                                      placeholder="Purchase of property at No. 5 Bourdillon, Ikoyi")
            fn_ref = st.text_input("Our Reference", key="fn_ref_inp",
                                   placeholder="EO/2025/001")
            fn_date = st.text_input("Date", value=datetime.now().strftime("%d %B %Y"),
                                    key="fn_date_inp")
        with fn2:
            fn_land = st.number_input("Professional Fees (₦)", min_value=0.0,
                value=float(st.session_state.get("fn_land_fee", 0) or 0),
                step=1_000.0, format="%.2f", key="fn_land_inp")
            fn_stamp = st.number_input("Stamp Duty Paid (₦)", min_value=0.0,
                value=float(st.session_state.get("fn_stamp_duty", 0) or 0),
                step=500.0, format="%.2f", key="fn_stamp_inp")
            fn_court_fee_val = st.number_input("Court / Registry Fees (₦)", min_value=0.0,
                value=float(st.session_state.get("fn_court_fee", 0) or 0),
                step=500.0, format="%.2f", key="fn_court_inp")
            fn_disbursements = st.number_input("Other Disbursements (₦)", min_value=0.0,
                value=0.0, step=500.0, format="%.2f", key="fn_disb_inp")
            fn_vat = st.checkbox("Add 7.5% VAT on professional fees", value=True, key="fn_vat_chk")

        fn_notes = st.text_area("Additional Notes / Description of Services",
                                height=80, key="fn_notes_inp",
                                placeholder="E.g. Includes perfection of title, CAC searches, preparation of Deed of Assignment, and obtaining Governor's Consent.")

        gen_btn = st.button("🧾 Generate Fee Note", type="primary",
                            key="fn_gen_btn", use_container_width=True,
                            disabled=not (fn_client.strip() and fn_matter.strip()))

        if gen_btn:
            vat_amount = fn_land * 0.075 if fn_vat else 0.0
            subtotal = fn_land + fn_stamp + fn_court_fee_val + fn_disbursements
            total_due = subtotal + vat_amount
            firm = get_firm_name()
            lawyer = st.session_state.profile.get("lawyer_name", "")
            firm_address = st.session_state.profile.get("address", "")
            firm_email = st.session_state.profile.get("email", "")
            firm_phone = st.session_state.profile.get("phone", "")

            fee_note_text = f"""
{'='*65}
{firm.upper() if firm and firm != 'LexiAssist' else 'LAW FIRM'}
{'SOLICITORS & ADVOCATES' if firm and firm != 'LexiAssist' else ''}
{firm_address}
Tel: {firm_phone}  |  Email: {firm_email}
{'='*65}

PROFESSIONAL FEE NOTE / BILL OF COSTS

Date:         {fn_date}
Our Ref:      {fn_ref or '[REF]'}
To:           {fn_client}

RE: {fn_matter}

{'─'*65}

DESCRIPTION OF SERVICES:
{fn_notes or 'Professional legal services rendered in connection with the above matter.'}

{'─'*65}

FEES AND DISBURSEMENTS:
{'─'*65}"""

            items = []
            if fn_land > 0:
                items.append(("Professional / Solicitor's Fees", fn_land))
            if fn_stamp > 0:
                items.append(("Stamp Duty on Instrument", fn_stamp))
            if fn_court_fee_val > 0:
                items.append(("Court / Registry Filing Fees", fn_court_fee_val))
            if fn_disbursements > 0:
                items.append(("Other Disbursements", fn_disbursements))

            for desc, val in items:
                fee_note_text += f"\n  {desc:<45} {fmt_currency(val):>15}"

            fee_note_text += f"""
{'─'*65}
  Sub-Total                                          {fmt_currency(subtotal):>15}"""
            if vat_amount > 0:
                fee_note_text += f"""
  VAT @ 7.5% (on professional fees)                 {fmt_currency(vat_amount):>15}"""
            fee_note_text += f"""
{'─'*65}
  TOTAL AMOUNT DUE                                   {fmt_currency(total_due):>15}
{'='*65}

PAYMENT:
Kindly remit the sum of {fmt_currency(total_due)} to:
  Bank:           [BANK NAME]
  Account Name:   {firm or '[FIRM NAME]'}
  Account No:     [ACCOUNT NUMBER]

Payment is due within 14 days of this fee note.
Kindly quote our reference {fn_ref or '[REF]'} on all payments.

{'─'*65}
{lawyer or '[AUTHORISED SIGNATORY]'}
For: {firm or '[FIRM NAME]'}

⚠️ All fees are subject to the Rules of Professional Conduct for
Legal Practitioners 2007 and are subject to review if the matter
becomes more complex than currently anticipated.
{'='*65}
"""
            st.session_state["fn_generated"] = fee_note_text
            st.session_state["fn_total_due"] = total_due

        fn_generated = st.session_state.get("fn_generated", "")
        if fn_generated:
            st.markdown("---")
            st.markdown(f'<div class="response-box" style="font-family:monospace;font-size:0.88rem;">'
                        f'{esc(fn_generated)}</div>', unsafe_allow_html=True)

            total_due = st.session_state.get("fn_total_due", 0)
            st.success(f"✅ Total Due: **{fmt_currency(total_due)}**")

            fn_fname = f"FeeNote_{fn_client.replace(' ','_')}_{datetime.now():%Y%m%d}"
            fne1, fne2, fne3, fne4 = st.columns(4)
            with fne1:
                st.download_button("📥 TXT", export_txt(fn_generated, "Professional Fee Note"),
                    f"{fn_fname}.txt", "text/plain", key="fn_dl_txt", use_container_width=True)
            with fne2:
                st.download_button("📥 HTML", export_html(fn_generated, "Professional Fee Note"),
                    f"{fn_fname}.html", "text/html", key="fn_dl_html", use_container_width=True)
            with fne3:
                safe_pdf_download(fn_generated, "Professional Fee Note", fn_fname, "fn_dl_pdf")
            with fne4:
                safe_docx_download(fn_generated, "Professional Fee Note", fn_fname, "fn_dl_docx", doc_type="fee_note")

