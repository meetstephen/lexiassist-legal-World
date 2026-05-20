"""LexiAssist billing + AI cost-tracker page."""
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
# PAGE: BILLING (WITH AI COST TRACKER)
# ═══════════════════════════════════════════════════════
def render_billing():
    st.markdown("""<div class="page-header">
        <h2>💰 Billing & Cost Tracker</h2>
        <p>Time entries, invoicing, financial reports, and AI usage costs</p>
    </div>""", unsafe_allow_html=True)

    tab_time, tab_inv, tab_report, tab_costs = st.tabs(
        ["⏱️ Time Entries", "📄 Invoices", "📊 Reports", "🤖 AI Costs"]
    )

    # ── Time Entries ──
    with tab_time:
        with st.form("add_time_form", clear_on_submit=True):
            st.markdown("#### ➕ New Time Entry")
            bt1, bt2 = st.columns(2)
            with bt1:
                cl_names = [c.get("name", "?") for c in st.session_state.clients]
                if not cl_names:
                    st.warning("Add a client first.")
                    cl_sel_b = None
                else:
                    cl_sel_b = st.selectbox("Client *", cl_names, key="bill_cl_inp")
                desc = st.text_input("Description *", key="bill_desc_inp")
            with bt2:
                hours = st.number_input("Hours *", min_value=0.0, step=0.25, key="bill_hrs_inp")
                rate = st.number_input(f"Rate ({get_currency_symbol()}/hr) *", min_value=0.0, step=1000.0, value=50000.0, key="bill_rate_inp")
                entry_date = st.date_input("Date", key="bill_date_inp")

            if st.form_submit_button("➕ Add Entry", type="primary"):
                if cl_sel_b and desc.strip() and hours > 0:
                    cidx = cl_names.index(cl_sel_b)
                    add_time_entry({
                        "client_id": st.session_state.clients[cidx]["id"],
                        "client_name": cl_sel_b,
                        "description": desc.strip(),
                        "hours": hours, "rate": rate,
                        "date": str(entry_date),
                    })
                    st.success(f"✅ {hours}h @ {fmt_currency(rate)}/hr added!")
                    st.rerun()
                else:
                    st.error("❌ Fill all required fields.")

        entries = st.session_state.time_entries
        if entries:
            st.markdown("#### 📋 Recent Entries")
            for te in reversed(entries[-20:]):
                st.markdown(f"""<div class="custom-card">
                    <strong>{esc(te.get('description', ''))}</strong><br>
                    {esc(te.get('client_name', ''))} ·
                    {te.get('hours', 0)}h @ {esc(fmt_currency(te.get('rate', 0)))}/hr ·
                    <strong>{esc(fmt_currency(te.get('amount', 0)))}</strong> ·
                    {esc(fmt_date(te.get('date', '')))}
                </div>""", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_te_{te['id']}", help="Delete entry"):
                    delete_time_entry(te["id"])
                    st.rerun()

    # ── Invoices ──
    with tab_inv:
        st.markdown("#### 📄 Generate Invoice")
        if st.session_state.clients:
            cl_names_inv = [c.get("name", "?") for c in st.session_state.clients]
            inv_client = st.selectbox("Client", cl_names_inv, key="inv_cl_sel")
            if st.button("📄 Generate Invoice", type="primary", key="gen_inv_btn", use_container_width=True):
                cidx = cl_names_inv.index(inv_client)
                cid = st.session_state.clients[cidx]["id"]
                inv = make_invoice(cid)
                if inv:
                    st.success(f"✅ Invoice {inv['invoice_no']} — {fmt_currency(inv['total'])}")
                    st.rerun()
                else:
                    st.warning("No billable entries for this client.")
        else:
            st.info("Add clients first.")

        if st.session_state.invoices:
            st.markdown("#### 📋 All Invoices")
            for inv in reversed(st.session_state.invoices):
                firm = get_firm_name()
                inv_text = (
                    f"{firm}\n\n"
                    f"INVOICE: {inv['invoice_no']}\n"
                    f"Date: {fmt_date(inv['date'])}\n"
                    f"Client: {inv['client_name']}\n"
                    f"Status: {inv['status']}\n\n"
                    f"{'='*40}\n"
                )
                for e in inv.get("entries", []):
                    inv_text += f"{e.get('description', '')} | {e.get('hours', 0)}h | {fmt_currency(e.get('amount', 0))}\n"
                inv_text += f"{'='*40}\nTOTAL: {fmt_currency(inv['total'])}\n"

                st.markdown(f"""<div class="custom-card">
                    <h4>{esc(inv['invoice_no'])}</h4>
                    {esc(inv['client_name'])} · {esc(fmt_date(inv['date']))} ·
                    <strong>{esc(fmt_currency(inv['total']))}</strong> ·
                    <span class="badge badge-info">{esc(inv['status'])}</span>
                </div>""", unsafe_allow_html=True)

                ic1, ic2, ic3 = st.columns(3)
                with ic1:
                    st.download_button("📥 TXT", export_txt(inv_text, f"Invoice {inv['invoice_no']}"),
                                       f"Invoice_{inv['invoice_no']}.txt", "text/plain",
                                       key=f"inv_txt_{inv['id']}", use_container_width=True)
                with ic2:
                    safe_pdf_download(inv_text, f"Invoice {inv['invoice_no']}",
                                      f"Invoice_{inv['invoice_no']}", f"inv_pdf_{inv['id']}")
                with ic3:
                    safe_docx_download(inv_text, f"Invoice {inv['invoice_no']}",
                                       f"Invoice_{inv['invoice_no']}", f"inv_docx_{inv['id']}",
                                       doc_type="invoice",
                                       meta={"invoice_no": inv.get("invoice_no",""), "client": inv.get("client_name",""), "matter": inv.get("matter",""), "amount": fmt_currency(inv.get('amount',0))})

    # ── Billing Reports ──
    with tab_report:
        st.markdown("#### 📊 Billing Summary")
        entries = st.session_state.time_entries
        if entries:
            th = total_hours()
            tb = total_billable()
            avg = tb / th if th else 0

            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                st.metric("Total Hours", f"{th:.1f}")
            with rc2:
                st.metric("Total Billable", fmt_currency(tb))
            with rc3:
                st.metric("Avg Rate/hr", fmt_currency(avg))

            if HAS_PLOTLY:
                df = pd.DataFrame(entries)
                if "client_name" in df.columns and "amount" in df.columns:
                    chart_df = df.groupby("client_name")["amount"].sum().reset_index()
                    chart_df.columns = ["Client", "Amount"]
                    fig = px.bar(chart_df, x="Client", y="Amount",
                                 title="Billable Amount by Client",
                                 color_discrete_sequence=["#059669"])
                    st.plotly_chart(fig, use_container_width=True)

                if "date" in df.columns and "hours" in df.columns:
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")
                    time_df = df.dropna(subset=["date"]).groupby("date")["hours"].sum().reset_index()
                    if not time_df.empty:
                        fig2 = px.line(time_df, x="date", y="hours",
                                       title="Hours Over Time",
                                       color_discrete_sequence=["#059669"])
                        st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No time entries to report.")

        # ── Nigerian Tax Compliance Reminders ──
        st.markdown("---")
        st.markdown("#### 🧾 Nigerian Tax Obligations for Law Firms")
        t1, t2, t3 = st.columns(3)
        with t1:
            st.markdown("""<div class="custom-card">
                <h4>💼 WHT on Legal Fees</h4>
                <p>Corporate clients deduct <strong>5% Withholding Tax</strong> from legal fees
                paid to law firms per CITA and PITA. You are entitled to a WHT credit note.
                Ensure clients issue WHT credit certificates — use these to offset your CIT
                liability at year-end.</p>
                <small><em>CITA s. 81; FIRS WHT Regulations</em></small>
            </div>""", unsafe_allow_html=True)
        with t2:
            st.markdown("""<div class="custom-card">
                <h4>🧮 VAT on Legal Services</h4>
                <p>Legal services attract <strong>7.5% VAT</strong> (Finance Act 2019).
                If your firm's annual turnover exceeds <strong>₦25 million</strong>,
                you must register for VAT, charge it on invoices, and remit to FIRS
                by the <strong>21st of the following month</strong>.</p>
                <small><em>VATA Cap V1 LFN (as amended); Finance Act 2019 s. 38</em></small>
            </div>""", unsafe_allow_html=True)
        with t3:
            st.markdown("""<div class="custom-card">
                <h4>👔 PAYE for Staff</h4>
                <p>Deduct and remit <strong>PAYE tax</strong> to the relevant State IRS
                (based on employee's residence) by the <strong>10th of each month</strong>.
                File annual returns with LIRS/FIRS by <strong>31 January</strong>.
                Failure: ₦50,000/month penalty + 10% p.a. interest.</p>
                <small><em>PITA Cap P8 LFN 2004 (as amended); Finance Acts</em></small>
            </div>""", unsafe_allow_html=True)

    # ── AI Cost Tracker ──
    with tab_costs:
        st.markdown("#### 🤖 AI Usage & Cost Tracker")
        db = get_db()
        summary = db.get_cost_summary()

        kc1, kc2, kc3 = st.columns(3)
        with kc1:
            st.metric("Today", f"${summary['daily_cost']:.4f}", f"{summary['daily_calls']} calls")
        with kc2:
            st.metric("This Month", f"${summary['monthly_cost']:.4f}", f"{summary['monthly_calls']} calls")
        with kc3:
            st.metric("All Time", f"${summary['total_cost']:.4f}", f"{summary['total_calls']} calls")

        st.markdown("---")

        logs = db.get_cost_logs(100)
        if logs:
            st.markdown("#### 📋 Recent API Calls")

            if HAS_PLOTLY and len(logs) > 1:
                log_df = pd.DataFrame(logs)
                log_df["timestamp"] = pd.to_datetime(log_df["timestamp"], errors="coerce")
                log_df["date"] = log_df["timestamp"].dt.date

                # Daily cost chart
                daily_df = log_df.groupby("date")["estimated_cost"].sum().reset_index()
                daily_df.columns = ["Date", "Cost ($)"]
                if len(daily_df) > 1:
                    fig_cost = px.bar(daily_df, x="Date", y="Cost ($)",
                                      title="Daily AI Cost",
                                      color_discrete_sequence=["#3b82f6"])
                    st.plotly_chart(fig_cost, use_container_width=True)

                # Calls by task
                if "task" in log_df.columns:
                    task_df = log_df.groupby("task").agg(
                        calls=("id", "count"),
                        total_cost=("estimated_cost", "sum")
                    ).reset_index()
                    task_df.columns = ["Task", "Calls", "Cost ($)"]
                    fig_task = px.pie(task_df, values="Calls", names="Task",
                                     title="API Calls by Task Type")
                    st.plotly_chart(fig_task, use_container_width=True)

                # Calls by model
                if "model" in log_df.columns:
                    model_df = log_df.groupby("model").agg(
                        calls=("id", "count"),
                        total_cost=("estimated_cost", "sum")
                    ).reset_index()
                    model_df.columns = ["Model", "Calls", "Cost ($)"]
                    st.dataframe(model_df, use_container_width=True, hide_index=True)

            # Log table — collapsed by default to keep page compact
            with st.expander(f"📜 Call Log ({min(len(logs), 50)} most recent entries)", expanded=False):
                for log in logs[:50]:
                    task_lbl = TASK_TYPES.get(log.get("task", ""), {}).get("label", log.get("task", ""))
                    mode_lbl = RESPONSE_MODES.get(log.get("mode", ""), {}).get("label", log.get("mode", ""))
                    st.markdown(f"""<div class="history-item">
                        <small>{esc(fmt_date(log.get('timestamp', '')))} ·
                        {esc(log.get('model', ''))} ·
                        {esc(task_lbl)} · {esc(mode_lbl)} ·
                        In: {log.get('input_chars', 0):,}c · Out: {log.get('output_chars', 0):,}c ·
                        <strong>${log.get('estimated_cost', 0):.5f}</strong></small><br>
                        <small>{esc(log.get('query_preview', '')[:100])}</small>
                    </div>""", unsafe_allow_html=True)

            # Export cost logs
            if st.button("📥 Export Cost Logs (CSV)", key="export_cost_csv", use_container_width=True):
                cost_df = pd.DataFrame(logs)
                csv_data = cost_df.to_csv(index=False)
                st.download_button(
                    "⬇️ Download CSV", csv_data,
                    f"lexiassist_cost_logs_{datetime.now():%Y%m%d}.csv",
                    "text/csv", key="dl_cost_csv", use_container_width=True,
                )
        else:
            st.info("No API calls logged yet. Use the AI Assistant to generate your first analysis.")

        st.caption(f"💡 Costs estimated at ${COST_PER_1M_INPUT}/1M input tokens + ${COST_PER_1M_OUTPUT}/1M output tokens (approx Gemini 2.5 Flash pricing).")

