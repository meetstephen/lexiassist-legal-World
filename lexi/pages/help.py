"""LexiAssist Help & Quick Start guide.

A scannable in-app guide for lawyers in their first 5 minutes. Lives under
the 👤 Account group in the navigation. Designed to be read top-to-bottom
once and then referenced by tab on demand.
"""
from __future__ import annotations

# Barrel import: mirrors the global namespace of the original single-file
# app.py exactly. The original code below is unchanged.
from ..runtime import *      # noqa: F401, F403
from ..runtime import __version__  # noqa: F401
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


def render_help() -> None:
    """Render the Help & Quick Start page.

    Five tabs:
      1. 🚀 Quick Start    — 5-minute orientation
      2. 🧠 Using the AI   — how to get strong, citable output
      3. 🛠️ Tour of Tools  — what each module does, when to use it
      4. ❓ FAQ            — common questions
      5. ⚖️ Trust & Safety — confidentiality, accuracy, what AI can/can't do
    """
    st.markdown("""<div class="page-header">
        <h2>❓ Help &amp; Quick Start</h2>
        <p>Get the most out of LexiAssist in 5 minutes</p>
    </div>""", unsafe_allow_html=True)

    h_quick, h_ai, h_tools, h_faq, h_trust = st.tabs([
        "🚀 Quick Start",
        "🧠 Using the AI",
        "🛠️ Tour of Tools",
        "❓ FAQ",
        "⚖️ Trust & Safety",
    ])

    # ───────────────────────────── 1. Quick Start ─────────────────────────────
    with h_quick:
        st.markdown(
            f"""
### Welcome to LexiAssist — v{__version__}

LexiAssist is an AI-powered workspace for Nigerian legal practice. It is
designed to be a **drafting and analysis aid** that respects how you actually
work: position-taking, citation-grounded, and case-aware.

**The 5-minute orientation:**

1. **Set up your firm.** Open **👤 Profile → 🏢 Firm Details**. Add your firm
   name and your name as registered with the Supreme Court. Every export will
   carry these on the letterhead.

2. **Add your first client.** **👥 Clients → ➕ Add Client.** Every case,
   billing entry, and conflict check links back to a client.

3. **Create your first case.** **📁 Cases → ➕ Add Case.** Suit number, court,
   parties. The case becomes the spine of everything else.

4. **Run your first AI query.** **🧠 AI Assistant.** Pick *Standard* mode,
   click an example query (or type your own), hit *Generate*. Watch it stream
   a position-taking analysis with verified Nigerian authorities.

5. **Save it back to the case.** Below the AI response, use **💾 Save to Case**
   so the analysis becomes part of the matter file.

That's the whole loop. Everything else is optional power tools.
"""
        )

        st.markdown("---")
        st.markdown("#### 📲 Working from your phone")
        st.markdown(
            """
LexiAssist is fully mobile-friendly — the layout stacks single-column on
phones, the AI query box uses a 16px font (no iOS auto-zoom), and the
sidebar opens on a single tap. Tabs scroll horizontally; long tables
scroll horizontally.

**Tip:** Add the page to your home screen (Safari → Share → *Add to Home
Screen*; Chrome → ⋮ → *Install app*) for a one-tap launch.
"""
        )

        st.markdown("---")
        st.markdown("#### 💬 Tell us what you think")
        st.info(
            "There's a **💬 Send Beta Feedback** form in the sidebar on every "
            "page. Bug, feature request, or compliment — three clicks and you're "
            "done. Your firm admin sees every submission in their inbox."
        )

    # ─────────────────────────── 2. Using the AI ──────────────────────────────
    with h_ai:
        st.markdown(
            """
### How to get the strongest output

LexiAssist is tuned to take a **firm position** rather than hedge. To get
the best out of it, give it the same context you'd give a junior in chambers.

#### ✅ A great prompt usually has

- **Facts.** Names, dates, amounts, the contract clause, the notice served.
- **Jurisdiction.** Which State, which court, federal vs state.
- **What you actually want.** *"Draft a Statement of Defence"* is different
  from *"Tell me my client's exposure"* is different from *"What's the
  limitation period?"*.
- **Posture.** *"Acting for the claimant"* or *"acting for the defendant"*
  changes the strategy. Say so.

#### 🎯 Three modes — pick the right one

| Mode | When to use | Token budget |
|---|---|---|
| **Brief** | Quick fact-check, citation lookup, one-line answer | ~2k tokens |
| **Standard** | Most analysis, advice memos, drafting | ~16k tokens |
| **Comprehensive** | Long-form opinions, complex matters, trial briefs | ~32k tokens |

#### 🧪 Example queries to try right now

These are pre-loaded as one-click chips above the AI query box:

- **Limitation:** *Compute the limitation period — my client was injured in
  a road accident on 15 March 2022. The driver works for the Federal
  Ministry of Health.* (Tests POPA / public-officer rules.)
- **Pre-action:** *Client wants to sue Lagos State Government for breach
  of contract worth ₦50M. Walk me through the pre-action requirements.*
- **Drafting:** *Draft a Memorandum of Understanding between two Nigerian
  companies for a joint venture in Lagos.*
- **Contract review:** *Review for risks: "The Service Provider may
  terminate at any time, with or without cause, without liability."*

#### 🔬 Confidence + Citation Audit

Every response gets two automatic checks:

1. **AI Confidence Score** — 4 axes (statutory grounding, case law support,
   procedural certainty, position-taking) rolled into a 0-10 score. Below
   6 means you should double-check.
2. **Citation Audit** — every case name extracted and cross-checked against
   the verified Nigerian case database (200+ landmark decisions from NWLR /
   LPELR). Unverified cases are flagged in red — verify before filing.

#### 🎯 Strategy Simulator

After any analysis, scroll down to the *Case Strength Meter* expander to
ask **"What if we do X?"** — file a preliminary objection, make a
without-prejudice offer, apply for an injunction. The AI returns a
probability of success, opponent counter-strategy, and your counter-counter.
"""
        )

    # ─────────────────────────── 3. Tour of Tools ─────────────────────────────
    with h_tools:
        st.markdown("### What's in the toolbox")
        st.caption(
            "Every tool below is one click away from the navigation. "
            "Use this section as a reference — don't try to read it all at once."
        )

        tools = [
            ("🧠 AI Assistant",
             "Position-taking analysis, contract review, drafting, "
             "follow-ups, history compare. The workhorse."),
            ("📚 Research",
             "Legal research with retrieval-augmented grounding against "
             "verified Nigerian statutes and the case database."),
            ("🔍 Authority Verification",
             "Paste any AI text or draft argument. We extract every "
             "case/statute/rule and check each against the verified "
             "database. Catches hallucinations, repealed laws, and "
             "foreign-only authorities."),
            ("🔗 Source-Backed Research",
             "Same research engine, but every claim is anchored to a "
             "specific source citation."),
            ("📁 Cases",
             "Case manager with status, parties, hearings, and saved "
             "AI analyses on the matter file."),
            ("✅ Tasks",
             "Deadline + assignment tracker with overdue auto-flag, "
             "priority sort, and case linkage."),
            ("📜 Smart Pleadings",
             "18 court document types drafted in full Nigerian format "
             "from your case file."),
            ("📅 Calendar",
             "Hearing calendar with vacation-period notices for the "
             "Long, Christmas, and Easter recesses."),
            ("🔍 Conflict Check",
             "RPC-2007 compliant conflict scan across every existing "
             "client and case before you take a new matter. Includes "
             "fuzzy name-matching to catch alias / spelling variants."),
            ("👥 Clients",
             "Client database — every case and conflict "
             "check links here."),
            ("⚖️ Fee Calculator",
             "Land scale fees · stamp duty · court filing fees for FHC, "
             "Lagos, FCT, Rivers, TAT, IST. Generates professional fee "
             "notes ready to issue."),
            ("🎯 Witness Prep",
             "Examination-in-chief questions, cross-exam risk matrix, "
             "coaching notes, multi-witness contradiction check."),
            ("🤝 Settlement Advisor",
             "Without-prejudice settlement strategy — opening, BATNA, "
             "concession map, draft offer letter."),
            ("🔎 Due Diligence",
             "Structured DD reports for transactional matters."),
            ("📋 Templates",
             "Reusable prompts and document templates — system + custom."),
            ("📰 Practice Updates",
             "AI-assisted Nigerian legal practice update generator with "
             "case relevance scan against your current matter."),
            ("📝 Notes → Brief",
             "Convert raw client interview notes into a structured legal "
             "brief."),
            ("🔧 Tools",
             "Limitation periods, deadline calculator, court hierarchy, "
             "legal maxims, AML/SCUML compliance, court process "
             "checklist, authority verification mode — all in one tab."),
            ("🔎 Global Search",
             "Search across every client, case, analysis, and template "
             "you've created."),
        ]
        for icon_title, desc in tools:
            st.markdown(
                f'<div class="custom-card">'
                f'<h4>{esc(icon_title)}</h4>'
                f'<p>{esc(desc)}</p></div>',
                unsafe_allow_html=True,
            )

    # ─────────────────────────────── 4. FAQ ───────────────────────────────────
    with h_faq:
        with st.expander("Is my client data sent to Google?", expanded=True):
            st.markdown(
                """
The text of every AI query is sent to **Google Gemini** for processing
under Google's Gemini API terms. Google states that, for paid API
traffic, prompts and responses are **not used to train models**.

What we recommend, regardless of provider terms:

- **Don't paste raw client identifiers** unless the analysis needs them.
  Use placeholders ("Mr A", "the claimant") for sensitive data.
- For highly confidential matters, anonymise the facts before submitting.
- Treat AI output the way you'd treat a junior's draft — review before use.

We log nothing about your prompts beyond an 80-character preview for the
AI cost tracker (so you know what each ₦ was spent on).
"""
            )

        with st.expander("How accurate are the citations?"):
            st.markdown(
                """
Two layers protect you:

1. **Verified Nigerian case database** — 200+ landmark Supreme Court and
   Court of Appeal decisions with full NWLR/SC citations. Every case the
   AI mentions is matched against this database. Unverified ones are
   **flagged in red** in the Citation Audit panel below every response.

2. **Repealed-law detector** — citations to repealed Acts (CAMA 1990,
   Electoral Act 2010, Arbitration Act 1988, etc.) are flagged with the
   correct replacement.

**Always** verify any unflagged citation against NWLR / LPELR / LawPavilion
before filing. The database is curated, not exhaustive.
"""
            )

        with st.expander("What about repealed laws and recent amendments?"):
            st.markdown(
                """
Your firm admin can add new cases, repealed laws, and amendments via
**🛡️ Admin → 📚 Law Updates**. Entries there are injected into every AI
prompt as a **currency note** — so the AI is reminded of changes it might
not know.

If you spot something the AI cited that's been overruled or amended,
let your admin know via the **💬 Send Beta Feedback** widget.
"""
            )

        with st.expander("Why does it sometimes refuse to answer?"):
            st.markdown(
                """
Three reasons it might come back empty or with an error:

1. **Rate limit.** You've made 30 AI calls in the last 60 seconds. Wait
   one minute and try again.
2. **Monthly budget.** Your firm has set a monthly AI spend cap and
   you've hit it. Ask your admin.
3. **Safety filter.** Gemini's content policies sometimes refuse on
   facts that mention violence, illegal acts, or sensitive identifiers
   in a way it interprets as harmful. Rephrase the facts neutrally and
   re-submit — the model handles legal scenarios fine when framed as
   *"the claimant alleges …"* rather than first-person.
"""
            )

        with st.expander("Can I export my data?"):
            st.markdown(
                """
Yes. Open the sidebar and click **📥 Export All Data (JSON)**. You get
every case, client, time entry, invoice, AI session, custom template,
and limitation override in one file. It's a clean backup or migration
artefact.

You can re-import it on a fresh deployment via the same sidebar
(*Upload* → drop the JSON).
"""
            )

        with st.expander("How do I share an AI analysis with a colleague?"):
            st.markdown(
                """
Below every AI response there are four export buttons:

- **TXT** — plain text for email
- **HTML** — print-ready, branded with your firm
- **PDF** — confidential watermark, your firm letterhead
- **DOCX** — fully formatted Word doc, ready for further editing

All four embed your firm name, the lawyer's name + SCN enrolment number
(if set), and the standard "AI-generated drafting aid" disclaimer.
"""
            )

        with st.expander("My session timed out — did I lose my draft?"):
            st.markdown(
                """
LexiAssist auto-locks after 30 minutes of idle. Your session token is
preserved and a single password re-entry brings you straight back to
where you were — case data, history, exports all intact.

The exception is the **AI query box**: text typed into the live text
area is browser-side and isn't auto-saved. If you're drafting a long
prompt, hit *Generate* before stepping away — the response (and your
prompt) are persisted to your session history immediately.
"""
            )

        with st.expander("Where do I report a bug or request a feature?"):
            st.markdown(
                """
Open the sidebar — at the bottom there's a **💬 Send Beta Feedback**
expander. Pick a category (Bug / Feature / Praise / Comment), set the
severity, write what happened. Your firm admin sees every submission in
their inbox tab and can mark it *In Progress* / *Resolved* /
*Dismissed*.
"""
            )

    # ───────────────────────── 5. Trust & Safety ─────────────────────────────
    with h_trust:
        st.markdown("### What this is — and what it isn't")
        st.markdown(
            """
LexiAssist is a **drafting and analysis aid for qualified legal
practitioners**. It is not legal advice, it does not replace counsel, and
its outputs must be independently verified before any client filing or
court process.

#### ✅ What we're good at

- Surfacing relevant Nigerian statute and case authority for a problem
- Drafting first cuts of pleadings, contracts, advice memos, fee notes
- Computing limitation periods and pre-action notice requirements
- Risk-ranking contract clauses and flagging unfair terms
- Witness preparation: examination-in-chief, cross-exam, coaching
- Generating matter workflows and tracking deadlines
- Catching hallucinated case citations and repealed-law references

#### ⚠️ What we won't do (and why)

- **We won't tell you the current filing fee at a specific registry.**
  Registries change fees without notice. The Fee Calculator gives an
  estimate flagged with the verification date, but the registry desk
  is the authoritative source.
- **We won't guarantee a citation is current good law.** Every citation
  audit is best-effort against a curated database; case law moves and
  the database is not exhaustive.
- **We won't make a final call on jurisdiction-sensitive limitation
  questions.** State Limitation Laws differ; public-officer rules cut
  across; continuing-injury and concealment doctrines apply variably.
  We surface the analysis, you make the call.
- **We won't draft anything we mark with `[PLACEHOLDER]`.** Those are
  facts only you have.

#### 🔐 Confidentiality

- Data lives in PostgreSQL, encrypted at rest by the database provider.
- API keys are encrypted with the firm's `ENCRYPTION_KEY` before storage.
- All AI calls go through Google Gemini under their API terms (paid
  traffic is not used for training).
- Login uses PBKDF2 password hashing; session tokens are SHA-256 hashed
  in the DB.
- Idle sessions auto-lock at 30 minutes; failed-login lockout at 5 tries.
- Every significant action (login, AI call, case-add, role-change,
  user-deletion) writes to a hash-chained, immutable audit log
  visible to admins.

#### 📜 Always-on disclaimer

Every AI response, every export, every page-footer carries:

> **Authorities are cited and verifiable · finalised under the supervising practitioner's judgment**

You'll see it. Your client (if you share a PDF) will see it. The court
(if it ends up in a filing) will not — because you'll have reviewed it
first. That's the contract.

#### 🆘 If something goes wrong

- **App is down / not responding** — try a hard refresh first; if it
  persists, contact your firm admin who can check the keep-alive
  workflow status.
- **Wrong answer / hallucinated citation** — flag via the in-app
  feedback widget; we treat citation hallucinations as P0.
- **Lost data** — admin has a backup; you also have your own JSON
  export from the sidebar.
"""
        )
