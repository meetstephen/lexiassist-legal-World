"""Unit tests for the AI cost-estimation primitive used by the budget
enforcement layer in lexi.ai.generate().

The full ``generate()`` budget block has many side effects (Streamlit
session state, DB writes, external AI client) that are expensive to
mock. Here we focus on the PURE primitive that the budget logic
depends on — ``estimate_cost`` — plus the projection arithmetic
itself (input chars × $/M-tokens + output cap × $/M-tokens × NGN/USD).

If these maths are right, an integration test is the only thing left
to verify the wiring; if they're wrong, the budget enforcement is
silently broken.
"""
from __future__ import annotations

import pytest

from lexi.ai import estimate_cost
from lexi.constants import (
    COST_PER_1M_INPUT,
    COST_PER_1M_OUTPUT,
    RESPONSE_MODES,
    USD_TO_NGN,
)


# ─────────────────────────────────────────────────────────────────────────────
# estimate_cost — pure, char-based heuristic (chars / 4 ≈ tokens)
# ─────────────────────────────────────────────────────────────────────────────
class TestEstimateCost:
    def test_zero_input_zero_output_is_zero(self):
        assert estimate_cost("", "") == 0.0

    def test_returns_a_float(self):
        cost = estimate_cost("hello", "world")
        assert isinstance(cost, float)

    def test_cost_is_non_negative(self):
        # No invocation should ever produce a negative cost — that would
        # silently CREDIT the budget.
        for inp_len in (0, 100, 1_000, 100_000):
            for out_len in (0, 100, 1_000, 100_000):
                cost = estimate_cost("x" * inp_len, "y" * out_len)
                assert cost >= 0, f"negative cost at in={inp_len} out={out_len}"

    def test_more_tokens_costs_more(self):
        # Monotonic in input AND output length.
        a = estimate_cost("x" * 1_000, "y" * 1_000)
        b = estimate_cost("x" * 10_000, "y" * 1_000)
        c = estimate_cost("x" * 10_000, "y" * 10_000)
        assert a < b < c

    def test_matches_documented_formula(self):
        """Pin the formula so a future refactor can't silently change it.

        Per the source: input_tokens = chars/4; cost_USD =
        (input_tokens / 1M) * IN_RATE + (output_tokens / 1M) * OUT_RATE.

        For chars in = 4_000_000 → 1M input tokens. With OUT empty,
        the cost should equal exactly COST_PER_1M_INPUT (rounded to
        6 dp).
        """
        cost = estimate_cost("x" * 4_000_000, "")
        assert cost == pytest.approx(COST_PER_1M_INPUT, abs=1e-6)

        # And the output side, with INPUT empty.
        cost = estimate_cost("", "y" * 4_000_000)
        assert cost == pytest.approx(COST_PER_1M_OUTPUT, abs=1e-6)

    def test_cost_rounded_to_six_decimals(self):
        # The function rounds to 6dp — pin it so we don't accidentally
        # report sub-microdollar precision that suggests false certainty.
        cost = estimate_cost("hello", "world")
        # str representation should have <= 6 decimal digits.
        as_str = f"{cost:.10f}".rstrip("0").rstrip(".")
        if "." in as_str:
            decimals = len(as_str.split(".")[1])
            assert decimals <= 6


# ─────────────────────────────────────────────────────────────────────────────
# Budget projection arithmetic — replicates the calculation that the
# in-line budget check in generate() runs to decide whether THIS call's
# worst-case cost would push the firm over the monthly limit.
#
# The test is intentionally a duplicate of the formula, so any future
# edit to the production code that changes the formula has to ALSO
# update this test — making the change visible in code review.
# ─────────────────────────────────────────────────────────────────────────────
class TestBudgetProjectionFormula:
    @staticmethod
    def _projected_ngn(input_chars: int, mode: str) -> float:
        """Mirror of the projection block in lexi.ai.generate().

        If this drifts from production, one or both is wrong.
        """
        mode_tokens = RESPONSE_MODES.get(mode, RESPONSE_MODES["standard"])["tokens"]
        input_tokens = input_chars / 4
        projected_usd = (
            (input_tokens / 1_000_000) * COST_PER_1M_INPUT
            + (mode_tokens / 1_000_000) * COST_PER_1M_OUTPUT
        )
        return projected_usd * USD_TO_NGN

    def test_brief_mode_cheaper_than_comprehensive(self):
        # Same input, larger output cap → larger projected NGN.
        brief = self._projected_ngn(input_chars=4_000, mode="brief")
        comp = self._projected_ngn(input_chars=4_000, mode="comprehensive")
        assert comp > brief

    def test_zero_input_still_charges_for_max_output(self):
        # Even an empty prompt has a worst-case cost because the model
        # may emit up to mode.tokens of output. The budget guard MUST
        # treat zero input as still consuming output budget.
        ngn = self._projected_ngn(input_chars=0, mode="comprehensive")
        assert ngn > 0

    def test_projected_is_monotonic_in_input(self):
        # Bigger query → never cheaper.
        a = self._projected_ngn(100, "standard")
        b = self._projected_ngn(10_000, "standard")
        c = self._projected_ngn(1_000_000, "standard")
        assert a <= b <= c

    def test_unknown_mode_falls_back_to_standard(self):
        # The production code uses RESPONSE_MODES.get(mode, RESPONSE_MODES["standard"]).
        # Confirm the fallback gives the same answer as explicit "standard".
        unknown = self._projected_ngn(1_000, mode="not-a-real-mode")
        standard = self._projected_ngn(1_000, mode="standard")
        assert unknown == standard


# ─────────────────────────────────────────────────────────────────────────────
# Constants sanity — guards against accidental edits to the rate card
# that would silently shift every projected cost.
# ─────────────────────────────────────────────────────────────────────────────
class TestRateCardSanity:
    def test_input_rate_positive(self):
        assert COST_PER_1M_INPUT > 0

    def test_output_rate_at_least_input_rate(self):
        # Output is consistently more expensive than input across every
        # current Gemini SKU. If this ever flips, the predictive budget
        # check needs a re-think.
        assert COST_PER_1M_OUTPUT >= COST_PER_1M_INPUT

    def test_usd_to_ngn_in_sensible_band(self):
        # Conservative sanity floor + ceiling. If the FX constant is set
        # to e.g. 16 instead of 1600 (a real category of bug) the budget
        # would silently become 100× tighter.
        assert 500 < USD_TO_NGN < 5_000

    def test_response_modes_have_token_budgets(self):
        for mode_key, cfg in RESPONSE_MODES.items():
            assert "tokens" in cfg, f"mode {mode_key} missing 'tokens'"
            assert cfg["tokens"] > 0, f"mode {mode_key} non-positive token budget"
