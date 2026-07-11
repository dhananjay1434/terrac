"""P4.4 (H15) — cross-field plausibility. Advisory checks add a provisional
reason (never reject). Bounds are generous; only clearly-implausible values flag.
"""

from corroboration import derive_plausibility_reasons


def _r(**kw):
    base = dict(
        biomass_input_kg=None,
        wet_yield_kg=None,
        min_temp=None,
        temperature_readings=None,
        moisture_values=None,
    )
    base.update(kw)
    return derive_plausibility_reasons(**base)


# --- yield vs biomass ratio ---
def test_plausible_yield_ratio_is_clean():
    assert _r(biomass_input_kg=500.0, wet_yield_kg=100.0) == []  # 0.20


def test_yield_ratio_too_high_flags():
    assert "implausible_yield_biomass_ratio" in _r(
        biomass_input_kg=100.0, wet_yield_kg=90.0  # 0.90
    )


def test_yield_ratio_too_low_flags():
    assert "implausible_yield_biomass_ratio" in _r(
        biomass_input_kg=1000.0, wet_yield_kg=10.0  # 0.01
    )


def test_ratio_skipped_when_biomass_absent():
    assert _r(biomass_input_kg=None, wet_yield_kg=100.0) == []


# --- temp sustain coverage ---
def test_sustained_high_burn_is_clean():
    assert _r(min_temp=650.0, temperature_readings=[650.0] * 60) == []


def test_poor_temp_sustain_flags():
    # Only 20% of samples in the pyrolysis range.
    readings = [650.0] * 12 + [100.0] * 48
    assert "insufficient_temp_sustain" in _r(min_temp=100.0, temperature_readings=readings)


def test_temp_check_skipped_without_min_temp():
    assert _r(min_temp=None, temperature_readings=[100.0] * 60) == []


# --- moisture spread ---
def test_constant_moisture_is_clean():
    # Uniform readings are legitimate — must NOT flag.
    assert _r(moisture_values=[12.0] * 10) == []


def test_small_moisture_spread_is_clean():
    assert _r(moisture_values=[11.0, 12.0, 13.0, 12.5, 11.5]) == []


def test_huge_moisture_spread_flags():
    assert "implausible_moisture_spread" in _r(
        moisture_values=[5.0, 8.0, 10.0, 55.0, 12.0]  # spread 50 > 40
    )


def test_spread_needs_minimum_readings():
    # Below the reading floor, even a wide spread is not flagged.
    assert _r(moisture_values=[5.0, 55.0]) == []


def test_multiple_reasons_accumulate():
    reasons = _r(
        biomass_input_kg=100.0,
        wet_yield_kg=90.0,
        moisture_values=[5.0, 8.0, 10.0, 55.0, 12.0],
    )
    assert "implausible_yield_biomass_ratio" in reasons
    assert "implausible_moisture_spread" in reasons
