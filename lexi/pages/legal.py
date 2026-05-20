"""LexiAssist Privacy Notice and Terms of Service pages.

These two pages give the firm a NDPA-2023-compliant Privacy Notice and a
Terms of Service that puts the AI-disclaimer in writing — both critical
for a tool that processes client data and emits AI-generated drafts a
lawyer will rely on.

Content lives in editable markdown files under ``lexi/legal_text/``:
    - privacy_notice.md
    - terms_of_service.md

Placeholders (``{firm_name}``, ``{firm_email}``, ``{dpo_email}``, etc.)
are filled at render time from ``st.session_state.profile`` so the
output is the firm's own document, not generic boilerplate. Where a
profile field is empty we substitute an obvious bracketed placeholder
(e.g. ``[YOUR FIRM NAME]``) so the firm admin notices what still needs
to be set up.

To customise the wording, edit the .md file directly — the rendered
page picks up changes on the next reload.
"""
from __future__ import annotations

# Barrel import so the page module mirrors the global namespace used by
# the rest of the app (st, esc, datetime, …).
from ..runtime import *      # noqa: F401, F403
from ..helpers import *      # noqa: F401, F403

from datetime import date as _date
from pathlib import Path

_LEGAL_DIR = Path(__file__).resolve().parent.parent / "legal_text"


def _build_placeholder_map() -> dict[str, str]:
    """Pull placeholder values from the firm profile.

    Empty profile fields fall back to obvious bracketed placeholders so
    the firm admin can see at a glance what they still need to set up
    in Profile → Firm Details. The DPO defaults to the lead lawyer if
    no separate DPO has been designated.
    """
    profile = st.session_state.get("profile", {}) or {}

    def _or_placeholder(value: str, label: str) -> str:
        v = (value or "").strip()
        return v if v else f"[{label}]"

    firm_name = _or_placeholder(profile.get("firm_name"), "YOUR FIRM NAME")
    firm_address = _or_placeholder(profile.get("firm_address"), "YOUR FIRM ADDRESS")
    firm_email = _or_placeholder(profile.get("firm_email"), "YOUR FIRM EMAIL")
    firm_phone = _or_placeholder(profile.get("firm_phone"), "YOUR FIRM PHONE")
    lawyer_name = _or_placeholder(profile.get("lawyer_name"), "YOUR LEAD COUNSEL NAME")

    # DPO: separate fields if provided, otherwise fall back to lead counsel
    dpo_name = (profile.get("dpo_name") or profile.get("lawyer_name") or "").strip()
    dpo_name = dpo_name if dpo_name else "[YOUR DESIGNATED DPO NAME]"
    dpo_email = (profile.get("dpo_email") or profile.get("firm_email") or "").strip()
    dpo_email = dpo_email if dpo_email else "[YOUR DPO EMAIL]"

    governing_state = (profile.get("governing_state") or "Lagos").strip() or "Lagos"

    return {
        "firm_name": firm_name,
        "firm_address": firm_address,
        "firm_email": firm_email,
        "firm_phone": firm_phone,
        "lawyer_name": lawyer_name,
        "dpo_name": dpo_name,
        "dpo_email": dpo_email,
        "governing_state": governing_state,
        "effective_date": _date.today().strftime("%d %B %Y"),
    }


def _load_legal_markdown(filename: str) -> str:
    """Read a markdown file from lexi/legal_text and substitute
    placeholders against the firm profile.
    """
    path = _LEGAL_DIR / filename
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return (
            f"### Document not found\n\n"
            f"The legal text file `{filename}` could not be loaded. "
            f"Please contact the firm admin."
        )
    placeholders = _build_placeholder_map()
    # Use str.format_map so an unexpected {placeholder} in the markdown
    # doesn't blow up the page — a missing key just renders verbatim.
    try:
        return text.format_map(_DefaultDict(placeholders))
    except Exception:
        return text


class _DefaultDict(dict):
    """Dict that returns a literal "{key}" string for any missing key,
    so str.format_map never raises KeyError on an unexpected placeholder.
    """
    def __missing__(self, key):  # type: ignore[override]
        return "{" + key + "}"


def _render_unfilled_placeholder_warning() -> None:
    """If the firm profile still has empty fields the legal documents
    rely on, show an admin-only warning at the top of the page so the
    firm knows the document is not yet customised."""
    if st.session_state.get("current_user_role") != "admin":
        return
    profile = st.session_state.get("profile", {}) or {}
    required = {
        "firm_name": "Firm Name",
        "firm_address": "Firm Address",
        "firm_email": "Firm Email",
        "firm_phone": "Firm Phone",
        "lawyer_name": "Lead Counsel Name",
    }
    missing = [label for k, label in required.items() if not (profile.get(k) or "").strip()]
    if missing:
        st.warning(
            "**⚠️ Admin notice:** The following Firm Profile fields are still "
            f"empty and will display as `[YOUR …]` placeholders in this "
            f"document: **{', '.join(missing)}**.  "
            "Set them in 👤 Profile → 🏢 Firm Details so the published "
            "Privacy Notice and Terms of Service show the firm's real "
            "details. Non-admin users do not see this notice."
        )


def render_privacy_policy() -> None:
    """Render the firm's NDPA-2023-compliant Privacy Notice."""
    st.markdown(
        """<div class="page-header">
        <h2>📜 Privacy Notice</h2>
        <p>Nigeria Data Protection Act 2023 · Nigeria Data Protection Regulation 2019</p>
    </div>""",
        unsafe_allow_html=True,
    )
    _render_unfilled_placeholder_warning()
    st.markdown(_load_legal_markdown("privacy_notice.md"))


def render_terms_of_service() -> None:
    """Render the firm's Terms of Service (incorporates the AI-output
    disclaimer that protects both the firm and the user)."""
    st.markdown(
        """<div class="page-header">
        <h2>📋 Terms of Service</h2>
        <p>Conditions of use · AI-output disclaimer · Limitation of liability</p>
    </div>""",
        unsafe_allow_html=True,
    )
    _render_unfilled_placeholder_warning()
    st.markdown(_load_legal_markdown("terms_of_service.md"))
