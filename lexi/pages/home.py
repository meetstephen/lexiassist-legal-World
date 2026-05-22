"""LexiAssist home + tasks pages."""
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

def render_tasks():
    st.markdown("""<div class="page-header">
        <h2>✅ Task Manager</h2>
        <p>Track deadlines, assignments and matter actions — never miss a filing date</p>
    </div>""", unsafe_allow_html=True)

    PRIORITY_COLOURS = {"High": "#dc2626", "Medium": "#d97706", "Low": "#16a34a"}
    STATUS_COLOURS   = {"Pending": "#6366f1", "In Progress": "#d97706", "Done": "#16a34a", "Overdue": "#dc2626"}

    tasks = st.session_state.get("tasks", [])

    # ── Overdue auto-flag ──
    today_str = date.today().isoformat()
    for t in tasks:
        if t.get("due_date") and t.get("status") not in ("Done",) and t["due_date"] < today_str:
            t["status"] = "Overdue"

    tab_list, tab_add = st.tabs(["📋 All Tasks", "➕ Add Task"])

    # ══════════════════════════
    # TAB: ADD TASK
    # ══════════════════════════
    with tab_add:
        st.markdown("#### ➕ Create New Task")
        ta1, ta2 = st.columns(2)
        with ta1:
            t_title = st.text_input("Task Title *", key="t_title", placeholder="E.g. File Statement of Defence")
            t_due   = st.date_input("Due Date *", key="t_due", min_value=date.today())
            t_prio  = st.selectbox("Priority", ["High", "Medium", "Low"], key="t_prio")
            t_status = st.selectbox("Status", ["Pending", "In Progress"], key="t_status_new")
        with ta2:
            case_options = {c["id"]: c.get("title", "Untitled") for c in st.session_state.get("cases", [])}
            case_options[""] = "— None —"
            t_case = st.selectbox(
                "Linked Case",
                options=[""] + list({c["id"]: c for c in st.session_state.get("cases", [])}.keys()),
                format_func=lambda k: case_options.get(k, k),
                key="t_case_sel",
            )
            t_assigned = st.text_input("Assigned To", key="t_assigned", placeholder="Barr. Chidi or leave blank")
            t_notes = st.text_area("Notes", key="t_notes", height=100, placeholder="Optional — additional context or instructions")

        if st.button("✅ Save Task", type="primary", key="t_save_btn", use_container_width=True):
            if not t_title.strip():
                st.error("❌ Task title is required.")
            else:
                new_task = {
                    "id": new_id(),
                    "title": t_title.strip(),
                    "due_date": t_due.isoformat(),
                    "priority": t_prio,
                    "status": t_status,
                    "linked_case_id": t_case,
                    "assigned_to": t_assigned.strip(),
                    "notes": t_notes.strip(),
                    "created_at": datetime.now().isoformat(),
                }
                st.session_state.tasks.append(new_task)
                persist("tasks")
                get_db().append_audit("TASK_CREATED", f"title={t_title.strip()[:80]} due={t_due.isoformat()} priority={t_prio}")
                st.success(f"✅ Task '{t_title.strip()}' saved.")
                st.rerun()

    # ══════════════════════════
    # TAB: ALL TASKS
    # ══════════════════════════
    with tab_list:
        if not tasks:
            st.markdown(
                '<div style="text-align:center;padding:2.5rem 1rem;border:2px dashed '
                'var(--la-border);border-radius:12px;margin-top:1rem;">'
                '<div style="font-size:3rem;margin-bottom:0.6rem;">✅</div>'
                '<h3 style="margin:0 0 0.4rem 0;">No Tasks Yet</h3>'
                '<p style="color:var(--la-text2);margin:0 0 1rem 0;max-width:360px;'
                'margin-left:auto;margin-right:auto;">Stay on top of every deadline, '
                'filing and assignment in one place.</p>'
                '<p style="font-size:0.82rem;color:var(--la-text2);">'
                '<strong>Example:</strong> <em>File Statement of Defence · Due: 14 May 2026 · '
                'High Priority · ABC Ltd v XYZ Ltd</em></p>'
                '<p style="font-size:0.82rem;color:var(--la-text2);">'
                '👆 Click <strong>➕ Add Task</strong> above to get started.'
                '</p></div>',
                unsafe_allow_html=True,
            )
            return

        # ── Summary badges ──
        n_over  = sum(1 for t in tasks if t.get("status") == "Overdue")
        n_high  = sum(1 for t in tasks if t.get("priority") == "High" and t.get("status") != "Done")
        n_today = sum(1 for t in tasks if t.get("due_date") == today_str and t.get("status") != "Done")
        n_done  = sum(1 for t in tasks if t.get("status") == "Done")

        sm1, sm2, sm3, sm4 = st.columns(4)
        for col, label, val, colour in [
            (sm1, "Overdue",    n_over,  "#dc2626"),
            (sm2, "Due Today",  n_today, "#d97706"),
            (sm3, "High Prio",  n_high,  "#7c3aed"),
            (sm4, "Completed",  n_done,  "#16a34a"),
        ]:
            with col:
                col.markdown(
                    f'<div style="background:var(--la-card);border:1px solid var(--la-border);'
                    f'border-radius:8px;padding:0.7rem 0.9rem;text-align:center;">'
                    f'<div style="font-size:1.6rem;font-weight:800;color:{colour};">{val}</div>'
                    f'<div style="font-size:0.75rem;color:var(--la-text2);">{label}</div></div>',
                    unsafe_allow_html=True,
                )

        st.markdown("")

        # ── Filters ──
        fl1, fl2, fl3 = st.columns(3)
        with fl1:
            f_status = st.multiselect("Filter by Status", ["Pending","In Progress","Overdue","Done"], default=["Pending","In Progress","Overdue"], key="t_f_status")
        with fl2:
            f_prio = st.multiselect("Filter by Priority", ["High","Medium","Low"], default=["High","Medium","Low"], key="t_f_prio")
        with fl3:
            case_names = {c["id"]: c.get("title","Untitled") for c in st.session_state.get("cases",[])}
            f_case = st.selectbox("Filter by Case", ["All"] + list(case_names.values()), key="t_f_case")

        filtered = [
            t for t in tasks
            if (not f_status or t.get("status","Pending") in f_status)
            and (not f_prio   or t.get("priority","Medium") in f_prio)
            and (f_case == "All" or case_names.get(t.get("linked_case_id",""),"") == f_case)
        ]

        # ── Sort: overdue first, then by due_date, then priority weight ──
        prio_w = {"High": 0, "Medium": 1, "Low": 2}
        filtered.sort(key=lambda t: (
            0 if t.get("status") == "Overdue" else 1,
            t.get("due_date", "9999"),
            prio_w.get(t.get("priority", "Medium"), 1),
        ))

        st.markdown(f"**{len(filtered)} task(s) shown**")
        st.markdown("")

        for task in filtered:
            tid      = task["id"]
            pcolour  = PRIORITY_COLOURS.get(task.get("priority","Medium"), "#64748b")
            scolour  = STATUS_COLOURS.get(task.get("status","Pending"), "#64748b")
            due_str  = task.get("due_date","—")
            is_overdue = task.get("status") == "Overdue"
            border_c = "#dc2626" if is_overdue else "var(--la-border)"
            linked_case_title = case_names.get(task.get("linked_case_id",""), "")

            with st.container():
                overdue_html = '<br><small style="color:#dc2626;font-weight:600;">⚠️ OVERDUE</small>' if is_overdue else ''
                case_html = f'<br><small style="color:var(--la-text2);">📁 {esc(linked_case_title)}</small>' if linked_case_title else ''
                assigned_html = f'<br><small style="color:var(--la-text2);">👤 {esc(task.get("assigned_to",""))}</small>' if task.get("assigned_to") else ''
                notes_html = f'<div style="margin-top:0.4rem;font-size:0.82rem;color:var(--la-text2);">{esc(task.get("notes",""))}</div>' if task.get("notes") else ''
                st.markdown(
                    f'<div style="background:var(--la-card);border:1px solid {border_c};'
                    f'border-left:4px solid {pcolour};border-radius:8px;'
                    f'padding:0.75rem 1rem;margin-bottom:0.5rem;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.4rem;">'
                    f'<div>'
                    f'<strong style="font-size:0.95rem;">{esc(task.get("title",""))}</strong>'
                    f'{overdue_html}'
                    f'{case_html}'
                    f'{assigned_html}'
                    f'</div>'
                    f'<div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.25rem;">'
                    f'<span style="background:{scolour}22;color:{scolour};border:1px solid {scolour}44;'
                    f'border-radius:999px;padding:0.15rem 0.6rem;font-size:0.72rem;font-weight:600;">'
                    f'{esc(task.get("status","Pending"))}</span>'
                    f'<span style="background:{pcolour}22;color:{pcolour};border:1px solid {pcolour}44;'
                    f'border-radius:999px;padding:0.15rem 0.6rem;font-size:0.72rem;font-weight:600;">'
                    f'{esc(task.get("priority","Medium"))}</span>'
                    f'<span style="font-size:0.78rem;color:var(--la-text2);">📅 {esc(due_str)}</span>'
                    f'</div></div>'
                    f'{notes_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # Action row
                ac1, ac2, ac3, ac4 = st.columns([2, 2, 2, 1])
                with ac1:
                    new_status = st.selectbox(
                        "Status",
                        ["Pending", "In Progress", "Done", "Overdue"],
                        index=["Pending","In Progress","Done","Overdue"].index(task.get("status","Pending")),
                        key=f"t_st_{tid}",
                        label_visibility="collapsed",
                    )
                with ac2:
                    new_prio = st.selectbox(
                        "Priority",
                        ["High","Medium","Low"],
                        index=["High","Medium","Low"].index(task.get("priority","Medium")),
                        key=f"t_pr_{tid}",
                        label_visibility="collapsed",
                    )
                with ac3:
                    if st.button("💾 Update", key=f"t_upd_{tid}", use_container_width=True):
                        task["status"]   = new_status
                        task["priority"] = new_prio
                        persist("tasks")
                        get_db().append_audit("TASK_UPDATED", f"title={task['title'][:60]} status={new_status}")
                        st.rerun()
                with ac4:
                    if st.button("🗑️", key=f"t_del_{tid}", use_container_width=True, help="Delete task"):
                        st.session_state.tasks = [t for t in st.session_state.tasks if t["id"] != tid]
                        persist("tasks")
                        get_db().append_audit("TASK_DELETED", f"title={task['title'][:60]}")
                        st.rerun()


def render_home():
    # The "Private Beta" verification banner and the admin "needs attention"
    # health expander used to live here. Both were removed because they
    # shouted at the user on every home-screen visit, which is unprofessional
    # for a tool lawyers screen-share with clients.
    #
    # The same disclaimer text still lives in the global footer
    # ("AI-Generated Drafting Aid · Not Legal Advice · Verify all
    # authorities") and admin metrics (AI spend, failed logins, backup
    # status) still surface in the dedicated Admin tab and Tools page.
    #
    # Do NOT re-add a banner here without an explicit product decision.

    firm = get_firm_name()

    subtitle = f"{esc(firm)} · " if firm and firm != "LexiAssist" else ""
    st.markdown(f"""
    <style>
   .lexi-hero {{
        position: relative;
        overflow: hidden;
        background: linear-gradient(135deg, #1e3a5f 0%, #0f2440 60%, #162d4a 100%);
        border-radius: 16px;
        padding: 2.6rem 2.8rem 2.3rem;
        margin-bottom: 1.8rem;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 8px 32px rgba(0,0,0,0.25);
    }}
    .lexi-hero-watermark {{
        position: absolute;
        right: 2rem;
        top: 50%;
        transform: translateY(-50%);
        font-size: 13rem;
        line-height: 1;
        opacity: 0.07;
        color: #ffffff;
        pointer-events: none;
        user-select: none;
        filter: blur(1px);
        font-family: serif;
    }}
    .lexi-hero h1 {{
        font-size: 3.4rem !important;
        font-weight: 900 !important;
        letter-spacing: -0.04em !important;
        color: #ffffff !important;
        margin: 0 0 0.4rem 0 !important;
        line-height: 1 !important;
        position: relative;
        z-index: 1;
    }}
    .lexi-hero p {{
        font-size: 1rem !important;
        color: rgba(255,255,255,0.82) !important;
        margin: 0 !important;
        position: relative;
        z-index: 1;
        line-height: 1.6;
    }}
    /* Mobile sizing for the hero is handled centrally in lexi.themes
       so all 10 themes pick up the same responsive rules. We do not
       override here — that would defeat the global cascade. */
    </style>
    <div class="lexi-hero">
        <div class="lexi-hero-watermark">&#9878;</div>
        <h1>⚖️ LexiAssist</h1>
        <p>{subtitle}Elite AI Legal Engine for Nigerian Lawyers<br>
        Position-taking &middot; Strategy-driven &middot; Risk-ranked &middot; Litigator-minded</p>
    </div>
    """, unsafe_allow_html=True)

    # Stats row
    cost_summary = get_db().get_cost_summary()
    _today = date.today().isoformat()
    _tasks_all = st.session_state.get("tasks", [])
    _overdue_n = sum(1 for t in _tasks_all if t.get("due_date","") < _today and t.get("status") != "Done")
    _pending_n = sum(1 for t in _tasks_all if t.get("status") in ("Pending","In Progress"))
    c1, c2, c3, c4, c5, c6 = st.columns([1,1,1,1,1,1], gap="small")
    with c1:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{len(st.session_state.cases)}</div><div class="stat-label">Total Cases</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{len(get_active_cases())}</div><div class="stat-label">Active Cases</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{len(st.session_state.clients)}</div><div class="stat-label">Clients</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{total_hours():.1f}h</div><div class="stat-label">Billable Hours</div></div>', unsafe_allow_html=True)
    with c5:
        _ov_colour = "#dc2626" if _overdue_n else "inherit"
        st.markdown(f'<div class="stat-card"><div class="stat-value" style="color:{_ov_colour};">{_overdue_n}</div><div class="stat-label">Overdue Tasks</div></div>', unsafe_allow_html=True)
    with c6:
        st.markdown(f'<div class="stat-card"><div class="stat-value">{_pending_n}</div><div class="stat-label">Open Tasks</div></div>', unsafe_allow_html=True)

    st.markdown("")

    # ── Upcoming Tasks & Hearings panel ──────────────────────────────────────
    from datetime import timedelta
    _lookahead = (date.today() + timedelta(days=7)).isoformat()
    _upcoming_tasks = [
        t for t in _tasks_all
        if t.get("due_date","") and _today <= t.get("due_date","") <= _lookahead
        and t.get("status") not in ("Done",)
    ]
    _upcoming_tasks.sort(key=lambda t: t.get("due_date","9999"))

    _upcoming_hearings = [
        c for c in st.session_state.get("cases",[])
        if c.get("next_hearing") and _today <= c.get("next_hearing","") <= _lookahead
    ]
    _upcoming_hearings.sort(key=lambda c: c.get("next_hearing","9999"))

    if _upcoming_tasks or _upcoming_hearings or _overdue_n:
        st.markdown("### 📅 Next 7 Days")
        up1, up2 = st.columns(2)

        with up1:
            st.markdown("##### ✅ Upcoming Tasks")
            if _overdue_n:
                st.markdown(
                    f'<div style="background:var(--la-card);border:1px solid var(--la-border);border-left:4px solid #dc2626;'
                    f'border-radius:8px;padding:0.5rem 0.9rem;margin-bottom:0.4rem;">'
                    f'<strong style="color:#dc2626;">⚠️ {_overdue_n} overdue task(s)</strong>'
                    f' — go to ✅ Tasks to review.</div>',
                    unsafe_allow_html=True,
                )
            if _upcoming_tasks:
                for _t in _upcoming_tasks[:5]:
                    _days_left = (date.fromisoformat(_t["due_date"]) - date.today()).days
                    _days_label = "Today" if _days_left == 0 else f"in {_days_left}d"
                    _pc = {"High":"#dc2626","Medium":"#d97706","Low":"#16a34a"}.get(_t.get("priority","Medium"),"#64748b")
                    st.markdown(
                        f'<div style="background:var(--la-card);border:1px solid var(--la-border);'
                        f'border-left:3px solid {_pc};border-radius:6px;'
                        f'padding:0.45rem 0.8rem;margin-bottom:0.3rem;font-size:0.85rem;">'
                        f'<strong>{esc(_t.get("title",""))}</strong>'
                        f'<span style="float:right;font-size:0.75rem;color:var(--la-text2);">📅 {esc(_days_label)}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                if len(_upcoming_tasks) > 5:
                    st.caption(f"+ {len(_upcoming_tasks)-5} more — see ✅ Tasks tab")
            elif not _overdue_n:
                st.caption("No tasks due in the next 7 days. ✅")

        with up2:
            st.markdown("##### 🏛️ Upcoming Hearings")
            if _upcoming_hearings:
                for _h in _upcoming_hearings[:5]:
                    _hdays = (date.fromisoformat(_h["next_hearing"]) - date.today()).days
                    _hlabel = "Today" if _hdays == 0 else f"in {_hdays}d"
                    st.markdown(
                        f'<div style="background:var(--la-card);border:1px solid var(--la-border);'
                        f'border-left:3px solid #6366f1;border-radius:6px;'
                        f'padding:0.45rem 0.8rem;margin-bottom:0.3rem;font-size:0.85rem;">'
                        f'🏛️ <strong>{esc(_h.get("title","Untitled"))}</strong>'
                        f'<span style="float:right;font-size:0.75rem;color:var(--la-text2);">📅 {esc(_hlabel)}</span>'
                        f'<br><small style="color:var(--la-text2);">{esc(_h.get("court",""))}</small>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No hearings scheduled in the next 7 days.")

        st.markdown("")

   # ── Onboarding Wizard — shown until all 4 steps complete ────────────
    is_new_user = (
        len(st.session_state.cases) == 0
        and len(st.session_state.chat_history) == 0
        and len(st.session_state.clients) == 0
    )

    _WIZ_KEY = "onboarding_dismissed"
    _WIZ_STEP_KEY = "onboarding_step"

    # Mark steps complete automatically based on actual data
    steps_done = {
        1: bool(st.session_state.get("profile", {}).get("firm_name", "")),
        2: len(st.session_state.clients) > 0,
        3: len(st.session_state.cases) > 0,
        4: len(st.session_state.chat_history) > 0,
    }
    all_done = all(steps_done.values())

    show_wizard = (
        not st.session_state.get(_WIZ_KEY, False)
        and not all_done
    )

    if show_wizard:
        current_step = st.session_state.get(_WIZ_STEP_KEY, 1)
        # Auto-advance to first incomplete step
        for s in [1, 2, 3, 4]:
            if not steps_done[s]:
                current_step = s
                break

        st.session_state[_WIZ_STEP_KEY] = current_step

        completed = sum(steps_done.values())
        progress_pct = int((completed / 4) * 100)

        # Progress bar
        st.markdown(
            f'<div style="background:var(--la-card);border:1px solid var(--la-border);'
            f'border-radius:10px;padding:1rem 1.2rem;margin-bottom:1rem;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;margin-bottom:0.5rem;">'
            f'<strong>🚀 Getting Started — {completed}/4 steps complete</strong>'
            f'<span style="font-size:0.8rem;color:var(--la-text-secondary);">'
            f'{progress_pct}%</span></div>'
            f'<div style="background:rgba(128,128,128,0.25);border-radius:999px;height:8px;">'
            f'<div style="width:{progress_pct}%;background:#059669;'
            f'height:8px;border-radius:999px;transition:width 0.4s;"></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # Step cards
        STEPS = [
            {
                "num": 1, "icon": "🏢",
                "title": "Set up your firm",
                "desc": "Add your firm name and lawyer name so LexiAssist can personalise all your documents, letterheads and exports.",
                "action": "Go to 👤 Profile → 🏢 Firm Details and save your name.",
                "done_msg": "Firm profile saved ✓",
            },
            {
                "num": 2, "icon": "👤",
                "title": "Add your first client",
                "desc": "Create a client record — every case, billing entry and conflict check links back to a client.",
                "action": "Go to 👥 Clients → ➕ Add Client.",
                "done_msg": "First client added ✓",
            },
            {
                "num": 3, "icon": "📁",
                "title": "Create your first case",
                "desc": "A case ties your client, hearings, pleadings, analyses and billing together in one place.",
                "action": "Go to 📁 Cases → ➕ Add Case.",
                "done_msg": "First case created ✓",
            },
            {
                "num": 4, "icon": "🧠",
                "title": "Run your first AI query",
                "desc": "Ask LexiAssist a legal question — any area of Nigerian law, any complexity. See it take a firm position.",
                "action": "Go to 🧠 AI Assistant, type a query, pick Standard mode, hit Generate.",
                "done_msg": "First AI session complete ✓",
            },
        ]

        wiz_cols = st.columns(4)
        for col, step in zip(wiz_cols, STEPS):
            done = steps_done[step["num"]]
            is_current = step["num"] == current_step and not done
            border = "#059669" if done else ("#6366f1" if is_current else "var(--la-border)")
            # Use theme-aware card background throughout — no hardcoded light colours
            bg = "var(--la-card)"
            left_strip = "#059669" if done else ("#6366f1" if is_current else "transparent")
            with col:
                st.markdown(
                    f'<div style="border:2px solid {border};background:{bg};'
                    f'border-radius:10px;padding:0.9rem;min-height:170px;'
                    f'border-left:4px solid {left_strip};">'
                    f'<div style="font-size:1.5rem;">{step["icon"]}</div>'
                    f'<div style="font-weight:700;font-size:0.88rem;margin:.35rem 0 .3rem;'
                    f'color:var(--la-text);">'
                    f'Step {step["num"]}: {esc(step["title"])}</div>'
                    f'<div style="font-size:0.78rem;color:var(--la-text2);'
                    f'margin-bottom:0.5rem;">{esc(step["desc"])}</div>'
                    + (
                        f'<div style="color:#4ade80;font-size:0.78rem;font-weight:600;">'
                        f'✅ {esc(step["done_msg"])}</div>'
                        if done else
                        f'<div style="color:#818cf8;font-size:0.76rem;">'
                        f'👉 {esc(step["action"])}</div>'
                    )
                    + '</div>',
                    unsafe_allow_html=True,
                )

        # Dismiss button
        st.markdown("")
        wz1, wz2 = st.columns([1, 5])
        with wz1:
            if st.button(
                "✖ Dismiss wizard", key="dismiss_wizard",
                use_container_width=True,
            ):
                st.session_state[_WIZ_KEY] = True
                st.rerun()
        with wz2:
            st.caption(
                "The wizard disappears automatically when all 4 steps are complete. "
                "You can also dismiss it manually above."
            )

        st.markdown("---")

    elif all_done and not st.session_state.get(_WIZ_KEY, False):
        # First time all steps complete — show a one-time congratulations
        st.success(
            "🎉 **Setup complete!** You have finished all 4 getting-started steps. "
            "LexiAssist is fully configured for your practice."
        )
        st.session_state[_WIZ_KEY] = True

    col_left, col_right = st.columns([3, 2])
    with col_left:
        st.markdown("### 📅 Upcoming Hearings")
        hearings = get_hearings()
        if hearings:
            for h in hearings[:8]:
                d = days_until(h["date"])
                badge = "badge-err" if d <= 3 else ("badge-warn" if d <= 7 else "badge-ok")
                st.markdown(f"""<div class="custom-card">
                    <h4>{esc(h['title'])}</h4>
                    Suit: {esc(h['suit'])} · Court: {esc(h['court'])}<br>
                    📅 {esc(fmt_date(h['date']))}
                    <span class="badge {badge}">{esc(relative_date(h['date']))}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No upcoming hearings. Add cases with hearing dates.")

    with col_right:
        history = st.session_state.chat_history
        session_count = len(history)
        with st.expander(f"🧠 Recent AI Sessions ({session_count})", expanded=False):
            if history:
                for entry in reversed(history[-6:]):
                    mode_lbl = RESPONSE_MODES.get(entry.get("mode", ""), {}).get("label", "")
                    st.markdown(f"""<div class="history-item">
                        <strong>{esc(entry.get('query', '')[:80])}{'…' if len(entry.get('query', '')) > 80 else ''}</strong><br>
                        <small>{esc(entry.get('timestamp', ''))} · {esc(mode_lbl)} · {entry.get('word_count', 0)} words</small>
                    </div>""", unsafe_allow_html=True)
                if session_count > 6:
                    st.caption(f"Showing latest 6 of {session_count} sessions. Full history in 🧠 AI Assistant.")
            else:
                st.info("No AI sessions yet. Go to AI Assistant to start.")


        # Cost summary on home
        if cost_summary["total_calls"] > 0:
            st.markdown("### 💰 AI Costs")
            kc1, kc2 = st.columns(2)
            with kc1:
                st.metric("Today", f"${cost_summary['daily_cost']:.4f}")
            with kc2:
                st.metric("This Month", f"${cost_summary['monthly_cost']:.4f}")

    st.markdown("---")
    st.markdown("### 🏆 What LexiAssist Does")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        st.markdown("""<div class="custom-card">
            <h4>🎯 Position-Taking AI</h4>
            <p>No more "may be liable" — firm conclusions backed by Nigerian statute and case authority</p>
        </div>""", unsafe_allow_html=True)
    with f2:
        st.markdown("""<div class="custom-card">
            <h4>📑 Contract Review</h4>
            <p>Clause-by-clause risk matrix, red flag grading, and redline recommendations</p>
        </div>""", unsafe_allow_html=True)
    with f3:
        st.markdown("""<div class="custom-card">
            <h4>📜 Smart Pleadings</h4>
            <p>18 court document types drafted in full Nigerian court format from your case file</p>
        </div>""", unsafe_allow_html=True)
    with f4:
        st.markdown("""<div class="custom-card">
            <h4>🛡️ AML / SCUML</h4>
            <p>AI-assisted anti-money laundering checks, red flag detection, and SCUML compliance</p>
        </div>""", unsafe_allow_html=True)

    f5, f6, f7, f8 = st.columns(4)
    with f5:
        st.markdown("""<div class="custom-card">
            <h4>⏳ Limitation Checker</h4>
            <p>AI computes all applicable deadlines from your facts — 32 causes of action covered</p>
        </div>""", unsafe_allow_html=True)
    with f6:
        st.markdown("""<div class="custom-card">
            <h4>⚖️ Fee Calculator</h4>
            <p>Land solicitor's fees, stamp duty, court filing fees — Lagos, FCT, Rivers, FHC, TAT</p>
        </div>""", unsafe_allow_html=True)
    with f7:
        st.markdown("""<div class="custom-card">
            <h4>🎯 Witness Prep</h4>
            <p>Examination-in-chief questions, cross-examination risks, and coaching notes</p>
        </div>""", unsafe_allow_html=True)
    with f8:
        st.markdown("""<div class="custom-card">
            <h4>💾 Multi-User Cloud</h4>
            <p>PostgreSQL-backed — all data persists across sessions; admin + user roles</p>
        </div>""", unsafe_allow_html=True)

    # ── Nigerian Court Calendar Notice ──
    st.markdown("---")
    _today = date.today()
    _month = _today.month
    _day   = _today.day
    vacation_notices = []
    # Long vacation: August–September
    if _month == 8 or (_month == 9 and _day < 25):
        vacation_notices.append("☀️ **Long Vacation** (August–September) — Most Superior Courts are on recess. Urgent matters by leave only.")
    # Christmas vacation: mid-December to mid-January
    if _month == 12 and _day >= 15:
        vacation_notices.append("🎄 **Christmas Vacation** — Courts rising. Last sittings typically 3rd week of December.")
    if _month == 1 and _day < 15:
        vacation_notices.append("🎄 **Christmas Vacation** — Courts resuming mid-January. Verify exact resumption dates with each registry.")
    # Easter: computed properly for the current year
    def _easter_date(year: int) -> date:
        a = year % 19; b = year // 100; c = year % 100
        d = b // 4;   e = b % 4;       f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19*a + b - d - g + 15) % 30
        i = c // 4;   k = c % 4
        l = (32 + 2*e + 2*i - h - k) % 7
        m = (a + 11*h + 22*l) // 451
        month = (h + l - 7*m + 114) // 31
        day   = ((h + l - 7*m + 114) % 31) + 1
        return date(year, month, day)
    from datetime import timedelta as _td
    _easter      = _easter_date(_today.year)
    _good_friday = _easter - _td(days=2)
    _easter_mon  = _easter + _td(days=1)
    if _good_friday <= _today <= _easter_mon:
        vacation_notices.append("✝️ **Easter Vacation Period** — Courts typically on recess Good Friday through Easter Monday.")
    if vacation_notices:
        for vn in vacation_notices:
            st.warning(vn)

