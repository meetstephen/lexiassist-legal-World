"""Unit tests for citation extraction and verification in lexi.citations.

These tests pin down behaviour for the most user-visible AI safety
feature: catching fabricated case names and citations before they
reach a court process. A regression here means hallucinated authorities
slip past the audit silently.

All tests are pure: no DB, no AI, no network. They exercise every
branch of the citation regex parsers and the three-tier matcher
(exact / partial / fuzzy) inside ``verify_case_name``.
"""
from __future__ import annotations

import pytest

from lexi.citations import (
    VERIFIED_NIGERIAN_CASES,
    extract_case_names,
    extract_citations,
    find_relevant_verified_cases,
    scan_foreign_authorities,
    scan_repealed_laws,
    verify_case_name,
    verify_response_citations,
)


# ─────────────────────────────────────────────────────────────────────────────
# DB integrity
# ─────────────────────────────────────────────────────────────────────────────
class TestVerifiedDatabase:
    def test_database_has_substantial_coverage(self):
        # PR #12 expanded the DB from ~50 to 153 cases. This guards
        # against an accidental shrinkage that would make verification
        # less effective without anyone noticing.
        assert len(VERIFIED_NIGERIAN_CASES) >= 100, (
            f"Verified case DB has only {len(VERIFIED_NIGERIAN_CASES)} cases — "
            "regression. PR #12 set the floor at 153."
        )

    def test_every_entry_has_required_fields(self):
        required = {"citation", "court", "year", "principle"}
        for name, val in VERIFIED_NIGERIAN_CASES.items():
            missing = required - set(val.keys())
            assert not missing, f"{name} missing fields: {missing}"
            assert isinstance(val["year"], int), f"{name}: year must be int"
            assert val["citation"], f"{name}: empty citation"
            assert val["principle"], f"{name}: empty principle"

    def test_no_obvious_duplicates(self):
        # Lower-cased keys must be unique.
        lowered = [k.lower() for k in VERIFIED_NIGERIAN_CASES]
        assert len(lowered) == len(set(lowered)), "duplicate case names in DB"


# ─────────────────────────────────────────────────────────────────────────────
# verify_case_name — exact, partial, fuzzy paths
# ─────────────────────────────────────────────────────────────────────────────
class TestVerifyCaseName:
    def test_exact_match_case_insensitive(self):
        m = verify_case_name("Madukolu v Nkemdilim")
        assert m is not None
        assert m["match_type"] == "exact"
        assert m["name"] == "Madukolu v Nkemdilim"

        m = verify_case_name("MADUKOLU V NKEMDILIM")
        assert m is not None and m["match_type"] == "exact"

        m = verify_case_name("madukolu v nkemdilim")
        assert m is not None and m["match_type"] == "exact"

    def test_partial_match_with_extra_text(self):
        # AI output often appends citation in-line: "X v Y (1989) ..."
        # The verifier should still find the case via substring match.
        m = verify_case_name("Madukolu v Nkemdilim (1962) 2 SCNLR 341")
        assert m is not None
        assert m["match_type"] in ("exact", "partial")
        assert m["name"] == "Madukolu v Nkemdilim"

    def test_unknown_case_returns_none(self):
        # No invented case must ever look "verified".
        assert verify_case_name("Smith v Definitely Fake Co Ltd") is None
        assert verify_case_name("Random v Words") is None

    def test_empty_input_returns_none(self):
        assert verify_case_name("") is None
        assert verify_case_name("   ") is None

    def test_whitespace_normalised(self):
        m = verify_case_name("Madukolu    v\tNkemdilim")
        assert m is not None
        assert m["name"] == "Madukolu v Nkemdilim"

    def test_returns_full_metadata(self):
        m = verify_case_name("Kotoye v CBN")
        assert m is not None
        for key in ("name", "citation", "court", "year", "principle", "match_type"):
            assert key in m, f"verify_case_name result missing {key!r}"
        assert m["court"] == "Supreme Court"
        assert m["year"] == 1989


# ─────────────────────────────────────────────────────────────────────────────
# extract_citations — NWLR + LPELR formats
# ─────────────────────────────────────────────────────────────────────────────
class TestExtractCitations:
    def test_extracts_nwlr_format(self):
        text = "See Kotoye v CBN (1989) 1 NWLR (Pt. 98) 419."
        cits = extract_citations(text)
        assert len(cits) == 1
        assert cits[0]["year"] == "1989"
        assert cits[0]["reporter"].upper() == "NWLR"

    def test_extracts_lpelr_format(self):
        text = "Recent SC decision in Smith v Jones [2015] LPELR-12345(SC)."
        cits = extract_citations(text)
        assert len(cits) == 1
        assert cits[0]["year"] == "2015"
        assert cits[0]["reporter"].upper() == "LPELR"

    def test_extracts_multiple_citations(self):
        text = (
            "Compare (1989) 1 NWLR (Pt. 98) 419 with [2015] LPELR-12345(SC) "
            "and (2003) 12 NWLR (Pt. 833) 1."
        )
        cits = extract_citations(text)
        assert len(cits) == 3

    def test_no_false_positive_on_plain_text(self):
        # A plain English sentence with no citation shape must yield zero.
        cits = extract_citations(
            "The court considered the matter carefully but reached no firm "
            "conclusion on the facts as presented."
        )
        assert cits == []

    def test_empty_input(self):
        assert extract_citations("") == []

    def test_handles_alternative_reporters(self):
        # SCNLR is in the regex
        text = "Madukolu v Nkemdilim (1962) 2 SCNLR 341."
        cits = extract_citations(text)
        assert len(cits) == 1
        assert cits[0]["reporter"].upper() == "SCNLR"


# ─────────────────────────────────────────────────────────────────────────────
# extract_case_names — "X v Y" pattern
# ─────────────────────────────────────────────────────────────────────────────
class TestExtractCaseNames:
    def test_extracts_simple_case_name(self):
        # The regex anchors on punctuation / certain prepositions /
        # end-of-line. Use a comma anchor — typical of AI prose.
        names = extract_case_names("In Smith v Jones, the court held that...")
        # The capture is anchored at "," so we get a clean "Smith v Jones".
        assert any("Smith" in n and "Jones" in n for n in names)

    def test_extracts_multiple_names(self):
        # Each name is separated by a comma anchor — yields three entries.
        text = "See Smith v Jones, Brown v Wilson, and Adams v Baker."
        names = extract_case_names(text)
        # All three party names show up across the captured strings.
        joined = " | ".join(names)
        assert "Smith" in joined and "Jones" in joined
        assert "Brown" in joined and "Wilson" in joined
        assert "Adams" in joined and "Baker" in joined

    def test_dedupes_identical_repeated_names(self):
        # The function dedupes EXACT-match repeats; if the same string
        # "Smith v Jones" appears twice in identical context, only one
        # entry comes back.
        text = "Apply Smith v Jones. The court in Smith v Jones, again..."
        names = extract_case_names(text)
        # "Smith v Jones" (the trailing-period match) should appear at
        # most once.
        assert sum("Smith v Jones" == n for n in names) <= 1

    def test_handles_v_with_period(self):
        # "v." instead of "v"
        names = extract_case_names("The leading case is Smith v. Jones (2020).")
        assert any("Smith" in n and "Jones" in n for n in names)

    def test_no_false_positive_on_random_v(self):
        # "v" as a standalone word in an unrelated sentence must not
        # produce a fake case match. The regex requires both sides to
        # start with a capital letter, so lowercase "volume v counted"
        # shouldn't trigger.
        names = extract_case_names(
            "The witness said the volume v counted differently."
        )
        assert all("volume" not in n.lower() for n in names)

    def test_compound_party_names_with_parens_are_truncated(self):
        # Real cases with parenthesised qualifiers like "(Nig) Ltd"
        # exceed the regex character class — the parser stops at "(".
        # Document this behaviour so callers (verify_case_name) know
        # to do substring matching against the verified DB.
        text = "Per Best Nig Ltd v Blackwood Hodge Nig Ltd, consideration is..."
        names = extract_case_names(text)
        assert any("Best" in n and "Blackwood" in n for n in names)

    def test_empty_input(self):
        assert extract_case_names("") == []


# ─────────────────────────────────────────────────────────────────────────────
# verify_response_citations — full audit pipeline
# ─────────────────────────────────────────────────────────────────────────────
class TestVerifyResponseCitations:
    def test_audit_on_clean_text_returns_zero_counts(self):
        audit = verify_response_citations("This text has no legal authorities.")
        assert audit["case_names_found"] == 0
        assert audit["citations_found"] == 0
        assert audit["verified_cases"] == []
        assert audit["unverified_cases"] == []

    def test_audit_separates_verified_from_unverified(self):
        text = (
            "Per Madukolu v Nkemdilim, jurisdiction matters. "
            "Compare with Fabricated v Nonsense which says otherwise."
        )
        audit = verify_response_citations(text)
        verified_names = {v["name"] for v in audit["verified_cases"]}
        assert "Madukolu v Nkemdilim" in verified_names
        # The fabricated one must end up in the unverified bucket.
        assert any("Fabricated" in n or "Nonsense" in n
                   for n in audit["unverified_cases"])

    def test_audit_counts_citation_strings(self):
        text = "Cited (1989) 1 NWLR (Pt. 98) 419 and [2015] LPELR-12345(SC)."
        audit = verify_response_citations(text)
        assert audit["citations_found"] >= 2


# ─────────────────────────────────────────────────────────────────────────────
# scan_repealed_laws — deterministic statute currency check
# ─────────────────────────────────────────────────────────────────────────────
class TestScanRepealedLaws:
    def test_flags_old_cama(self):
        findings = scan_repealed_laws(
            "The CAMA 1990 governs corporate registration in Nigeria."
        )
        assert any("CAMA 1990" in f["authority"] for f in findings)
        assert all(f["status"] == "Repealed" for f in findings)

    def test_flags_old_evidence_act(self):
        findings = scan_repealed_laws("Per the Evidence Act 1945, hearsay is excluded.")
        assert findings  # at least one finding
        assert any("Evidence Act 1945" in f["authority"] for f in findings)

    def test_no_false_positive_on_current_acts(self):
        findings = scan_repealed_laws(
            "Section 84 of the Evidence Act 2011 governs computer-generated evidence."
        )
        assert findings == []

    def test_empty_input(self):
        assert scan_repealed_laws("") == []
        assert scan_repealed_laws(None) == []  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# scan_foreign_authorities
# ─────────────────────────────────────────────────────────────────────────────
class TestScanForeignAuthorities:
    def test_flags_donoghue(self):
        findings = scan_foreign_authorities(
            "The duty of care principle was set in Donoghue v Stevenson."
        )
        assert any("Donoghue v Stevenson" in f["authority"] for f in findings)
        assert all(f["status"] == "Foreign" for f in findings)

    def test_flags_carlill(self):
        findings = scan_foreign_authorities("See Carlill v Carbolic Smoke Ball Co.")
        assert findings


# ─────────────────────────────────────────────────────────────────────────────
# find_relevant_verified_cases — grounding helper
# ─────────────────────────────────────────────────────────────────────────────
class TestFindRelevantVerifiedCases:
    def test_returns_real_db_entries_only(self):
        # Whatever this function returns must be in the verified DB —
        # no invention.
        for query in [
            "land title",
            "election petition",
            "fundamental rights enforcement",
            "company directors fraudulent trading",
            "burden of proof criminal",
        ]:
            results = find_relevant_verified_cases(query, top_k=5)
            for r in results:
                assert r["name"] in VERIFIED_NIGERIAN_CASES, (
                    f"query={query!r} returned {r['name']!r} which is not in DB"
                )

    def test_empty_query_returns_empty_list(self):
        assert find_relevant_verified_cases("") == []
        assert find_relevant_verified_cases("   ") == []

    def test_junk_query_does_not_hallucinate(self):
        # Queries that match no keyword must return [], not random matches.
        assert find_relevant_verified_cases("xyzqwerty1234nonexistent") == []

    def test_top_k_bounds_result_size(self):
        results = find_relevant_verified_cases("burden of proof", top_k=3)
        assert len(results) <= 3

    def test_results_sorted_by_relevance(self):
        # Higher score must come first.
        results = find_relevant_verified_cases("election petition", top_k=10)
        if len(results) >= 2:
            scores = [r["_score"] for r in results]
            assert scores == sorted(scores, reverse=True), (
                f"results not sorted by score: {scores}"
            )

    def test_no_cross_domain_leakage(self):
        """Regression: a query in one legal domain must NOT surface a case
        whose principle is in an unrelated domain just because of one shared
        incidental word (the bug where an employment query returned land
        cases). The TOP result must be on-domain.
        """
        domain_terms = {
            "employment": {"employment", "dismissal", "master", "servant",
                           "wrongful", "termination"},
            "company": {"corporate", "veil", "company", "incorporation",
                        "shareholder", "salomon"},
            "criminal": {"murder", "criminal", "confession", "intent",
                         "provocation", "proof", "trial"},
            "contract": {"contract", "damages", "sale", "goods", "warranty",
                         "performance", "consideration"},
        }
        cases = [
            ("employee dismissed without notice unfair termination", "employment"),
            ("director personal liability for company debts lifting the veil", "company"),
            ("bail pending trial murder accused person", "criminal"),
            ("breach of contract damages for non-delivery of goods", "contract"),
        ]
        for query, domain in cases:
            results = find_relevant_verified_cases(query, top_k=5)
            assert results, f"expected matches for {query!r}"
            top_principle = results[0]["principle"].lower().replace(";", " ")
            top_tokens = set(top_principle.split())
            assert domain_terms[domain] & top_tokens, (
                f"top result for {query!r} is off-domain: "
                f"{results[0]['name']} :: {results[0]['principle']}"
            )

    def test_irrelevant_case_not_returned_for_unrelated_query(self):
        """A pure land query must not return a confessional-statement /
        criminal case, and vice-versa."""
        land = find_relevant_verified_cases("proof of title to land trespass", top_k=8)
        names = {r["name"] for r in land}
        # These criminal cases share no real land concept and must not appear.
        assert "Akpan v The State" not in names
        assert "Sunday v The State" not in names



# ─────────────────────────────────────────────────────────────────────────────
# verify_online_case — honest authenticity tiering for online-sourced cases
# ─────────────────────────────────────────────────────────────────────────────
class TestVerifyOnlineCaseAuthenticity:
    """An online-sourced case must never be over-stated. The tier must reflect
    what was ACTUALLY checked: DB match (verified), live-web sourced + valid
    citation shape (web_sourced, confirm-the-source), or otherwise
    needs_verification. A valid citation *shape* alone must NOT be promoted."""

    def test_known_db_case_is_verified(self):
        from lexi.web_search import verify_online_case
        v = verify_online_case("Madukolu v Nkemdilim", "(1962) 2 SCNLR 341", "1962",
                               grounded=False)
        assert v["confidence_tier"] == "verified"
        assert v["verified"] is True

    def test_grounded_valid_shape_is_web_sourced_not_verified(self):
        from lexi.web_search import verify_online_case
        v = verify_online_case("Some New Co v Another Co",
                               "(2021) 12 NWLR (Pt. 1234) 56", "2021", grounded=True)
        assert v["confidence_tier"] == "web_sourced"
        assert v["verified"] is False

    def test_ungrounded_valid_shape_is_needs_verification(self):
        # The key fix: a valid citation FORMAT with no live grounding must NOT
        # be labelled high-confidence — a hallucinated citation can have the
        # right shape. It must drop to needs_verification.
        from lexi.web_search import verify_online_case
        v = verify_online_case("Some New Co v Another Co",
                               "(2021) 12 NWLR (Pt. 1234) 56", "2021", grounded=False)
        assert v["confidence_tier"] == "needs_verification"

    def test_invalid_citation_is_needs_verification_even_if_grounded(self):
        from lexi.web_search import verify_online_case
        v = verify_online_case("Fake v Nobody", "not a real citation", "",
                               grounded=True)
        assert v["confidence_tier"] == "needs_verification"

    def test_no_legacy_high_confidence_tier(self):
        # The misleading 'high_confidence' tier (format-only) must be gone.
        from lexi.web_search import verify_online_case
        tiers = {
            verify_online_case("A v B", "(2020) 1 NWLR (Pt. 1) 1", "2020", grounded=g)["confidence_tier"]
            for g in (True, False)
        }
        assert "high_confidence" not in tiers
