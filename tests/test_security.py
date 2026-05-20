"""Unit tests for password security primitives in lexi.auth.

These functions are the front line of multi-user auth — every login
goes through them. A regression here (timing leak, salt re-use, hash
collision, legacy-format breakage) is a security incident.

The tests are pure: no DB, no streamlit, no network. They run in
milliseconds and exercise each branch of the password module.
"""
from __future__ import annotations

import hashlib

import pytest

from lexi.auth import hash_password, hash_session_token, verify_password


# ─────────────────────────────────────────────────────────────────────────────
# hash_password — format and uniqueness contract
# ─────────────────────────────────────────────────────────────────────────────
class TestHashPassword:
    def test_returns_pbkdf2_format(self):
        h = hash_password("hunter2")
        parts = h.split("$")
        assert parts[0] == "pbkdf2"
        assert len(parts) == 3, "expected 'pbkdf2$<salt>$<hash>'"

    def test_salt_is_32_hex_chars(self):
        # secrets.token_hex(16) → 32 hex chars
        _, salt, _ = hash_password("anything").split("$")
        assert len(salt) == 32
        int(salt, 16)  # must be valid hex

    def test_derived_key_is_64_hex_chars(self):
        # SHA-256 → 32 bytes → 64 hex chars
        _, _, dk = hash_password("anything").split("$")
        assert len(dk) == 64
        int(dk, 16)

    def test_two_calls_produce_different_hashes(self):
        """Random salt: same password must NEVER produce the same stored hash.

        If this ever fails, the salt is no longer random — that means an
        attacker who steals one record can rainbow-table every other
        account that shares the password.
        """
        a = hash_password("identical")
        b = hash_password("identical")
        assert a != b, "salt is not random — critical security regression"
        # And the salts themselves must differ:
        _, salt_a, _ = a.split("$")
        _, salt_b, _ = b.split("$")
        assert salt_a != salt_b

    def test_handles_unicode_password(self):
        # Lawyers using non-Latin characters / Naira sign in passwords.
        h = hash_password("p₦$$w0rd-é-中")
        assert h.startswith("pbkdf2$")
        assert verify_password("p₦$$w0rd-é-中", h)

    def test_handles_empty_password(self):
        # Empty passwords should still hash deterministically (the policy
        # layer above is responsible for refusing them; this primitive
        # must not crash).
        h = hash_password("")
        assert h.startswith("pbkdf2$")
        assert verify_password("", h)

    def test_long_password(self):
        long_pw = "x" * 4096
        h = hash_password(long_pw)
        assert verify_password(long_pw, h)


# ─────────────────────────────────────────────────────────────────────────────
# verify_password — happy path, rejection, legacy fallback, malformed input
# ─────────────────────────────────────────────────────────────────────────────
class TestVerifyPassword:
    def test_correct_password_passes(self):
        h = hash_password("correct horse battery staple")
        assert verify_password("correct horse battery staple", h) is True

    def test_wrong_password_fails(self):
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_case_sensitive(self):
        h = hash_password("Hunter2")
        assert verify_password("hunter2", h) is False
        assert verify_password("HUNTER2", h) is False
        assert verify_password("Hunter2", h) is True

    def test_legacy_sha256_format_still_verifies(self):
        """Pre-PBKDF2 accounts stored a bare SHA-256 hex digest. The new
        verify_password must still accept those so legacy users can log in
        and have their hash auto-upgraded by the auth layer.
        """
        legacy_hash = hashlib.sha256("oldpass".encode()).hexdigest()
        assert verify_password("oldpass", legacy_hash) is True
        assert verify_password("notoldpass", legacy_hash) is False

    def test_malformed_pbkdf2_returns_false(self):
        # Not enough segments
        assert verify_password("anything", "pbkdf2$only-two-parts") is False
        # Wrong segment count
        assert verify_password("anything", "pbkdf2$a$b$c$d") is False
        # Empty stored
        assert verify_password("anything", "") is False
        # Garbage that LOOKS pbkdf2 but isn't valid hex
        assert (
            verify_password("anything", "pbkdf2$NOT-HEX-SALT$ALSO-NOT-HEX")
            is False
        )

    def test_does_not_crash_on_weird_input_types(self):
        """If the DB ever returns something unexpected we must fail
        closed (return False), not raise.
        """
        # Random-string stored value — falls into the legacy path,
        # candidate sha256 won't match, returns False.
        assert verify_password("anything", "definitely-not-a-real-hash") is False

    def test_two_independent_hashes_of_same_password_both_verify(self):
        """The whole point of per-record salt: two records with the same
        password verify against THEIR OWN stored hash, but not against
        each other's."""
        h1 = hash_password("shared")
        h2 = hash_password("shared")
        assert h1 != h2
        assert verify_password("shared", h1)
        assert verify_password("shared", h2)


# ─────────────────────────────────────────────────────────────────────────────
# hash_session_token — used to anonymise tokens before DB storage
# ─────────────────────────────────────────────────────────────────────────────
class TestHashSessionToken:
    def test_deterministic(self):
        # Session tokens are looked up by hash on every request — must
        # be deterministic for the same input.
        a = hash_session_token("abc123")
        b = hash_session_token("abc123")
        assert a == b

    def test_different_tokens_hash_differently(self):
        a = hash_session_token("token-A")
        b = hash_session_token("token-B")
        assert a != b

    def test_returns_64_hex_chars(self):
        # SHA-256 hex digest
        h = hash_session_token("anything")
        assert len(h) == 64
        int(h, 16)

    def test_handles_long_token(self):
        # No truncation, no crash.
        h = hash_session_token("x" * 10_000)
        assert len(h) == 64
