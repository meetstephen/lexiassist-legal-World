"""LexiAssist global-search page."""
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
# PHASE 3 — GLOBAL SEARCH
# ═══════════════════════════════════════════════════════

def render_global_search():
    st.markdown("""<div class="page-header">
        <h2>🔎 Global Search</h2>
        <p>Search across all cases, clients, analyses, and history in one query</p>
    </div>""", unsafe_allow_html=True)

    query = st.text_input(
        "Search everything",
        placeholder="e.g. Lagos State Government · breach of contract · Adeyemi",
        key="global_search_q",
    )

    if not query.strip():
        st.info("Type a name, keyword, or phrase above to search across your entire LexiAssist workspace.")
        return

    q = query.strip().lower()
    results: dict[str, list] = {"Cases": [], "Clients": [], "Analyses": [], "AI History": []}

    # Cases
    for c in st.session_state.get("cases", []):
        target = f"{c.get('title','')} {c.get('suit_no','')} {c.get('court','')} {c.get('notes','')}".lower()
        if q in target:
            results["Cases"].append(c)

    # Clients
    for cl in st.session_state.get("clients", []):
        target = f"{cl.get('name','')} {cl.get('email','')} {cl.get('notes','')}".lower()
        if q in target:
            results["Clients"].append(cl)

    # Saved case analyses (DB)
    try:
        db = get_db()
        for c in st.session_state.get("cases", []):
            for sa in db.get_case_analyses(c["id"]):
                target = f"{sa.get('query','')} {sa.get('response','')}".lower()
                if q in target:
                    results["Analyses"].append({**sa, "_case_title": c.get("title","")})
    except Exception:
        pass

    # AI Session history
    for entry in st.session_state.get("chat_history", []):
        target = f"{entry.get('query','')} {entry.get('response','')}".lower()
        if q in target:
            results["AI History"].append(entry)

    total = sum(len(v) for v in results.values())
    if total == 0:
        st.warning(f"No results found for **{esc(query)}**. Try different keywords.")
        return

    st.success(f"Found **{total}** result(s) matching **{esc(query)}**")

    def _highlight(text: str, term: str) -> str:
        """Bold the matched term in a snippet."""
        idx = text.lower().find(term.lower())
        if idx == -1:
            return esc(text[:200])
        start = max(0, idx - 60)
        end = min(len(text), idx + len(term) + 60)
        snippet = text[start:end]
        return esc(snippet).replace(
            esc(text[idx:idx+len(term)]),
            f'<strong style="background:var(--la-bg2);">{esc(text[idx:idx+len(term)])}</strong>',
            1,
        )

    # Cases
    if results["Cases"]:
        st.markdown(f"#### 📁 Cases ({len(results['Cases'])})")
        for c in results["Cases"]:
            cname = get_client_name(c.get("client_id",""))
            st.markdown(
                f'<div class="history-item"><strong>{esc(c.get("title",""))}</strong>'
                f' · Suit: {esc(c.get("suit_no","—"))} · Court: {esc(c.get("court","—"))}'
                f' · Client: {esc(cname)}'
                f'<br><small style="color:var(--la-text-secondary);">{_highlight(c.get("notes",""),q)}</small></div>',
                unsafe_allow_html=True,
            )

    # Clients
    if results["Clients"]:
        st.markdown(f"#### 👥 Clients ({len(results['Clients'])})")
        for cl in results["Clients"]:
            st.markdown(
                f'<div class="history-item"><strong>{esc(cl.get("name",""))}</strong>'
                f' · {esc(cl.get("type",""))} · {esc(cl.get("email",""))}'
                f'<br><small style="color:var(--la-text-secondary);">{_highlight(cl.get("notes",""),q)}</small></div>',
                unsafe_allow_html=True,
            )

    # Saved analyses
    if results["Analyses"]:
        st.markdown(f"#### 📎 Saved Case Analyses ({len(results['Analyses'])})")
        for sa in results["Analyses"][:10]:
            st.markdown(
                f'<div class="history-item"><strong>{esc(sa.get("_case_title",""))}</strong>'
                f' · {esc(fmt_date(sa.get("timestamp","")))} · {esc(sa.get("task",""))}'
                f'<br><small><em>Query:</em> {_highlight(sa.get("query",""),q)}</small>'
                f'<br><small>{_highlight(sa.get("response",""),q)}</small></div>',
                unsafe_allow_html=True,
            )

    # AI History
    if results["AI History"]:
        st.markdown(f"#### 🧠 AI Session History ({len(results['AI History'])})")
        for entry in results["AI History"][:10]:
            st.markdown(
                f'<div class="history-item"><strong>{_highlight(entry.get("query",""),q)}</strong>'
                f' · {esc(entry.get("timestamp",""))} · {esc(entry.get("task",""))}'
                f'<br><small>{_highlight(entry.get("response",""),q)}</small></div>',
                unsafe_allow_html=True,
            )
