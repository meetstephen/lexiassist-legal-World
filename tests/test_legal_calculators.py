"""Unit tests for Nigerian fee calculators in lexi.legal_data.

These calculators drive the Fee Calculator page that lawyers quote
to clients. A bug here = wrong fee on an engagement letter = a real
problem.

All tests are pure math — no DB, no AI. They pin both the happy path
and the edge cases (zero value, minimum-fee floor, the boundary
between bands of the sliding scale, unknown instrument keys).
"""
from __future__ import annotations

import pytest

from lexi.legal_data import (
    LAND_MATTERS_MIN_FEE,
    LAND_MATTERS_SCALE,
    STAMP_DUTY_INSTRUMENTS,
    compute_land_fee,
    compute_stamp_duty,
    get_court_filing_fee,
)


# ─────────────────────────────────────────────────────────────────────────────
# compute_land_fee — Nigerian Legal Practitioners (Remuneration for Land
# Matters) Order — sliding scale
# ─────────────────────────────────────────────────────────────────────────────
class TestComputeLandFee:
    def test_zero_value_returns_minimum_fee(self):
        fee, breakdown = compute_land_fee(0)
        assert fee == LAND_MATTERS_MIN_FEE
        # No bands taxed when nothing remains.
        assert breakdown == []

    def test_value_below_minimum_threshold_returns_minimum(self):
        # Even on a tiny ₦1,000 land matter, the floor is ₦10,000.
        fee, _ = compute_land_fee(1_000)
        assert fee == LAND_MATTERS_MIN_FEE

    def test_first_band_only(self):
        # First ₦5,000 band @ 10% → ₦500. But min-fee floor lifts it.
        fee, breakdown = compute_land_fee(5_000)
        assert fee == LAND_MATTERS_MIN_FEE  # floor active
        assert breakdown[0]["band"] == "First ₦5,000"
        assert breakdown[0]["fee"] == 500.0

    def test_one_million_naira_matches_manual_calculation(self):
        # Manual sliding-scale calculation for ₦1,000,000 land matter:
        #   ₦5,000   @ 10.00%  =     ₦500
        #   ₦10,000  @  7.50%  =     ₦750  (5k → 15k)
        #   ₦15,000  @  5.00%  =     ₦750  (15k → 30k)
        #   ₦70,000  @  3.50%  =   ₦2,450  (30k → 100k)
        #   ₦400,000 @  2.50%  =  ₦10,000  (100k → 500k)
        #   ₦500,000 @  1.50%  =   ₦7,500  (500k → 1m)
        #   ────────────────────────────
        #   Total              =  ₦21,950
        fee, breakdown = compute_land_fee(1_000_000)
        assert fee == pytest.approx(21_950, abs=0.01)
        # Breakdown should hit all six bands at this value.
        assert len(breakdown) == 6

    def test_fee_is_monotonic_increasing(self):
        # Fee must never DECREASE as the underlying value grows.
        values = [10_000, 100_000, 500_000, 1_000_000, 10_000_000, 100_000_000]
        fees = [compute_land_fee(v)[0] for v in values]
        for a, b in zip(fees, fees[1:]):
            assert b >= a, f"non-monotonic: {a} → {b}"

    def test_large_value_uses_remainder_band(self):
        # For ₦10m, the remainder above ₦500k is ₦9,500,000 @ 1.5% = ₦142,500
        # plus all the fixed lower-band contributions (= ₦14,450 from above)
        # → ~₦156,950 total.
        fee, breakdown = compute_land_fee(10_000_000)
        last_band = breakdown[-1]
        assert "Remainder" in last_band["band"]
        assert last_band["taxable"] == pytest.approx(9_500_000)
        assert last_band["fee"] == pytest.approx(9_500_000 * 0.015)

    def test_breakdown_taxable_amounts_sum_to_input(self):
        # Sanity: across all bands, the taxable portions must sum to the input.
        for value in [50_000, 250_000, 1_500_000, 50_000_000]:
            _, breakdown = compute_land_fee(value)
            total_taxed = sum(b["taxable"] for b in breakdown)
            assert total_taxed == pytest.approx(value)


# ─────────────────────────────────────────────────────────────────────────────
# compute_stamp_duty — covers all 5 basis types in STAMP_DUTY_INSTRUMENTS
# ─────────────────────────────────────────────────────────────────────────────
class TestComputeStampDuty:
    # ── basis: flat ─────────────────────────────────────────────────────
    def test_flat_affidavit(self):
        # Affidavit is a flat ₦200 — value/years/rent are ignored.
        assert compute_stamp_duty("affidavit") == 200
        assert compute_stamp_duty("affidavit", value=999_999) == 200
        assert compute_stamp_duty("affidavit", value=0, years=99) == 200

    def test_flat_general_power_of_attorney(self):
        assert compute_stamp_duty("power_of_attorney_gen") == 1_000

    def test_flat_special_power_of_attorney(self):
        assert compute_stamp_duty("power_of_attorney_spec") == 500

    # ── basis: property_value ───────────────────────────────────────────
    def test_deed_of_assignment_fifteen_pct_of_value(self):
        # 1.5% of ₦10,000,000 = ₦150,000
        assert compute_stamp_duty("deed_of_assignment", value=10_000_000) == 150_000
        # Zero value → zero duty
        assert compute_stamp_duty("deed_of_assignment", value=0) == 0

    def test_settlement_agreement_fifteen_pct(self):
        assert compute_stamp_duty("settlement_agreement", value=2_000_000) == 30_000

    # ── basis: annual_rent_x_years ──────────────────────────────────────
    def test_tenancy_lt7_years_uses_years_factor(self):
        # 0.78% * ₦1,000,000 annual * 5 years = ₦39,000
        duty = compute_stamp_duty("tenancy_lt7", annual_rent=1_000_000, years=5)
        assert duty == pytest.approx(39_000)

    def test_tenancy_lt7_with_value_param_as_fallback(self):
        # If annual_rent is omitted, the value param is used as the rent.
        duty = compute_stamp_duty("tenancy_lt7", value=1_000_000, years=5)
        assert duty == pytest.approx(39_000)

    # ── basis: annual_rent ──────────────────────────────────────────────
    def test_tenancy_7to21_three_pct_of_annual_rent(self):
        # 3% of ₦5,000,000 annual rent = ₦150,000 (no year multiplier)
        duty = compute_stamp_duty("tenancy_7to21", annual_rent=5_000_000)
        assert duty == 150_000

    def test_tenancy_over21_six_pct_of_annual_rent(self):
        duty = compute_stamp_duty("tenancy_over21", annual_rent=5_000_000)
        assert duty == 300_000

    # ── basis: loan_amount, consideration, guaranteed_sum, etc. ─────────
    def test_mortgage_uses_value(self):
        # 0.375% of ₦100m loan = ₦375,000
        duty = compute_stamp_duty("mortgage", value=100_000_000)
        assert duty == pytest.approx(375_000)

    def test_share_transfer_uses_consideration(self):
        # 1.5% of ₦5m consideration = ₦75,000
        duty = compute_stamp_duty("share_transfer", value=5_000_000)
        assert duty == 75_000

    def test_guarantee_uses_guaranteed_sum(self):
        # 0.75% of ₦20m = ₦150,000
        duty = compute_stamp_duty("guarantee", value=20_000_000)
        assert duty == 150_000

    def test_loan_agreement(self):
        # 0.375% of ₦50m
        duty = compute_stamp_duty("loan_agreement", value=50_000_000)
        assert duty == pytest.approx(187_500)

    # ── error / unknown paths ───────────────────────────────────────────
    def test_unknown_instrument_returns_zero(self):
        # Caller-side guard: if the UI ever passes an unknown key the
        # function must return 0 rather than crash.
        assert compute_stamp_duty("nonexistent_instrument", value=1_000_000) == 0

    def test_zero_inputs_yield_zero(self):
        assert compute_stamp_duty("deed_of_assignment", value=0) == 0
        assert compute_stamp_duty("tenancy_lt7", annual_rent=0, years=0) == 0

    def test_every_instrument_produces_a_number(self):
        # No instrument key should raise — the dispatcher handles every
        # basis listed in STAMP_DUTY_INSTRUMENTS.
        for key in STAMP_DUTY_INSTRUMENTS:
            duty = compute_stamp_duty(
                key, value=1_000_000, years=3, annual_rent=500_000,
            )
            assert isinstance(duty, (int, float))
            assert duty >= 0


# ─────────────────────────────────────────────────────────────────────────────
# get_court_filing_fee — band lookup
# ─────────────────────────────────────────────────────────────────────────────
class TestGetCourtFilingFee:
    def test_lagos_magistrate_first_band(self):
        # Claim ≤ ₦100,000 → ₦2,000
        fee, note = get_court_filing_fee("magistrate_lagos", 50_000)
        assert fee == 2_000
        assert "Lagos Magistrate" in note

    def test_lagos_magistrate_jumps_to_next_band(self):
        # Claim ₦200,000 (in the ₦100k–₦300k band) → ₦5,000
        fee, _ = get_court_filing_fee("magistrate_lagos", 200_000)
        assert fee == 5_000

    def test_state_high_court_largest_band(self):
        # Claim ₦500m hits the "above ₦100m" band.
        fee, _ = get_court_filing_fee("high_court_state", 500_000_000)
        assert fee == 120_000

    def test_unknown_court_returns_zero(self):
        fee, note = get_court_filing_fee("imaginary_court", 1_000_000)
        assert fee == 0
        assert note == ""

    def test_band_boundary_inclusive(self):
        # Exactly at the upper bound of the first band — should still
        # use that band (claim_max is inclusive in the source).
        fee, _ = get_court_filing_fee("magistrate_lagos", 100_000)
        assert fee == 2_000
