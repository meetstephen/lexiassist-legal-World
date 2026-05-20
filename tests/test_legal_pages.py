"""Unit tests for lexi.pages.legal — the Privacy Notice and Terms of
Service renderers.

These pages publish the firm's legal commitments to its users and the
NDPC. A regression that drops a placeholder, mis-substitutes a value,
or silently fails to load the markdown file is a real exposure.

The tests check the pure helpers (placeholder map, markdown loader,
substitution semantics) without invoking Streamlit.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from lexi.pages import legal as legal_module


# ─────────────────────────────────────────────────────────────────────────────
# Markdown source files exist and contain every placeholder we promise
# to substitute. If anyone deletes a placeholder from the markdown by
# mistake, the tests catch it.
# ─────────────────────────────────────────────────────────────────────────────
class TestMarkdownSourceFiles:
    REQUIRED_PLACEHOLDERS = {
        "{firm_name}",
        "{firm_address}",
        "{firm_email}",
        "{firm_phone}",
        "{effective_date}",
    }
    PRIVACY_EXTRA = {"{dpo_name}", "{dpo_email}"}
    TERMS_EXTRA = {"{governing_state}"}

    def test_privacy_notice_file_exists(self):
        path = legal_module._LEGAL_DIR / "privacy_notice.md"
        assert path.exists(), f"missing legal text file: {path}"
        assert path.stat().st_size > 1000, "privacy_notice.md looks suspiciously short"

    def test_terms_of_service_file_exists(self):
        path = legal_module._LEGAL_DIR / "terms_of_service.md"
        assert path.exists(), f"missing legal text file: {path}"
        assert path.stat().st_size > 1000, "terms_of_service.md looks suspiciously short"

    def test_privacy_notice_contains_required_placeholders(self):
        text = (legal_module._LEGAL_DIR / "privacy_notice.md").read_text(
            encoding="utf-8"
        )
        for ph in self.REQUIRED_PLACEHOLDERS | self.PRIVACY_EXTRA:
            assert ph in text, f"privacy_notice.md missing placeholder {ph!r}"

    def test_terms_of_service_contains_required_placeholders(self):
        text = (legal_module._LEGAL_DIR / "terms_of_service.md").read_text(
            encoding="utf-8"
        )
        for ph in self.REQUIRED_PLACEHOLDERS | self.TERMS_EXTRA:
            assert ph in text, f"terms_of_service.md missing placeholder {ph!r}"

    def test_privacy_mentions_ndpa_and_ndpc(self):
        # The Privacy Notice MUST cite the governing Nigerian regime.
        # If anyone replaces it with a generic GDPR boilerplate, this fires.
        text = (legal_module._LEGAL_DIR / "privacy_notice.md").read_text(
            encoding="utf-8"
        )
        for marker in [
            "Nigeria Data Protection Act 2023",
            "Nigeria Data Protection Commission",
            "NDPC",
            "section 25",
            "72 hours",
        ]:
            assert marker in text, f"privacy_notice.md missing required marker {marker!r}"

    def test_terms_includes_critical_ai_disclaimer(self):
        # The whole point of the ToS is to put the AI-output disclaimer
        # in writing. Pin the most important clauses.
        text = (legal_module._LEGAL_DIR / "terms_of_service.md").read_text(
            encoding="utf-8"
        )
        for marker in [
            "AI-generated output",
            "Every AI output is provisional",
            "You must independently verify",
            "Citations must be cross-checked",
            "RPC",
            "Limitation of liability",
        ]:
            assert marker in text, f"terms_of_service.md missing required marker {marker!r}"


# ─────────────────────────────────────────────────────────────────────────────
# Placeholder map — pulls from session profile, falls back loudly
# ─────────────────────────────────────────────────────────────────────────────
class TestPlaceholderMap:
    def test_full_profile_produces_no_brackets(self):
        profile = {
            "firm_name":        "Adékúnlé & Partners",
            "firm_address":     "12 Awolowo Road, Ikoyi, Lagos",
            "firm_email":       "info@adekunle-partners.ng",
            "firm_phone":       "+234 1 555 0123",
            "lawyer_name":      "Olúwáṣẹ́gun Adékúnlé Esq.",
            "dpo_name":         "Funke Bello Esq.",
            "dpo_email":        "dpo@adekunle-partners.ng",
            "governing_state":  "Lagos",
        }
        with patch.object(
            legal_module.st, "session_state", {"profile": profile}, create=True,
        ):
            placeholders = legal_module._build_placeholder_map()

        for value in placeholders.values():
            # No "[YOUR …]" placeholders should leak through when the
            # profile is fully populated.
            assert not (value.startswith("[") and value.endswith("]")), (
                f"unexpected bracket placeholder in fully populated profile: {value!r}"
            )
        assert placeholders["firm_name"] == "Adékúnlé & Partners"
        assert placeholders["dpo_email"] == "dpo@adekunle-partners.ng"

    def test_empty_profile_uses_obvious_bracket_placeholders(self):
        with patch.object(
            legal_module.st, "session_state", {"profile": {}}, create=True,
        ):
            placeholders = legal_module._build_placeholder_map()

        # Every required-but-unset value renders as a "[YOUR …]" string
        # so the firm admin sees what's missing.
        assert placeholders["firm_name"].startswith("[")
        assert placeholders["firm_address"].startswith("[")
        assert placeholders["firm_email"].startswith("[")
        assert placeholders["firm_phone"].startswith("[")
        # DPO defaults: when both dpo_* and lawyer_name/firm_email are
        # empty, the bracket placeholder shows.
        assert placeholders["dpo_name"].startswith("[")
        assert placeholders["dpo_email"].startswith("[")

    def test_dpo_falls_back_to_lead_counsel_when_dpo_unset(self):
        profile = {
            "lawyer_name": "Funke Bello Esq.",
            "firm_email":  "info@firm.ng",
            # no dpo_name, no dpo_email
        }
        with patch.object(
            legal_module.st, "session_state", {"profile": profile}, create=True,
        ):
            placeholders = legal_module._build_placeholder_map()
        assert placeholders["dpo_name"] == "Funke Bello Esq."
        assert placeholders["dpo_email"] == "info@firm.ng"

    def test_governing_state_defaults_to_lagos(self):
        with patch.object(
            legal_module.st, "session_state", {"profile": {}}, create=True,
        ):
            placeholders = legal_module._build_placeholder_map()
        assert placeholders["governing_state"] == "Lagos"

    def test_governing_state_respects_override(self):
        profile = {"governing_state": "Abuja"}
        with patch.object(
            legal_module.st, "session_state", {"profile": profile}, create=True,
        ):
            placeholders = legal_module._build_placeholder_map()
        assert placeholders["governing_state"] == "Abuja"

    def test_effective_date_is_dd_month_yyyy(self):
        with patch.object(
            legal_module.st, "session_state", {"profile": {}}, create=True,
        ):
            placeholders = legal_module._build_placeholder_map()
        # "20 May 2026" format — three space-separated parts.
        parts = placeholders["effective_date"].split(" ")
        assert len(parts) == 3
        assert parts[0].isdigit()
        assert parts[2].isdigit() and len(parts[2]) == 4


# ─────────────────────────────────────────────────────────────────────────────
# Markdown loader — substitutes correctly, never crashes on missing keys
# ─────────────────────────────────────────────────────────────────────────────
class TestLoadLegalMarkdown:
    def test_load_privacy_substitutes_firm_name(self):
        profile = {"firm_name": "Test Firm Ltd"}
        with patch.object(
            legal_module.st, "session_state", {"profile": profile}, create=True,
        ):
            text = legal_module._load_legal_markdown("privacy_notice.md")
        assert "Test Firm Ltd" in text
        # The placeholder itself must NOT survive substitution.
        assert "{firm_name}" not in text

    def test_load_terms_substitutes_governing_state(self):
        profile = {"governing_state": "Abuja"}
        with patch.object(
            legal_module.st, "session_state", {"profile": profile}, create=True,
        ):
            text = legal_module._load_legal_markdown("terms_of_service.md")
        assert "Abuja" in text
        assert "{governing_state}" not in text

    def test_missing_file_does_not_crash(self):
        # If a future edit deletes the file, we render a friendly error
        # rather than 500.
        with patch.object(
            legal_module.st, "session_state", {"profile": {}}, create=True,
        ):
            out = legal_module._load_legal_markdown("does_not_exist.md")
        assert "could not be loaded" in out.lower()

    def test_unexpected_placeholder_does_not_raise(self):
        """If a markdown edit introduces an unexpected ``{placeholder}``
        we want it to render verbatim, not blow up the page.
        """
        # Use the DefaultDict directly to verify behaviour.
        d = legal_module._DefaultDict({"firm_name": "X"})
        out = "Hello {firm_name}, see {totally_new_placeholder}".format_map(d)
        assert "Hello X" in out
        # The unknown placeholder is preserved literally so an admin
        # editing the markdown can see it didn't get substituted.
        assert "{totally_new_placeholder}" in out
