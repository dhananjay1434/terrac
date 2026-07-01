"""Unit tests for the 8-step CSI LCA engine.

Test vector from the spec:
  wet_yield  = 115.4 kg
  moisture   = 12.7%
  min_temp   = 210Â°C
  distance   = 14.2 km
"""

from __future__ import annotations

import math

import pytest

from lca_engine import (
    LCAAudit,
    calculate_carbon_credit,
    get_corg,
    step1_dry_mass,
    step2_gross_c_sink,
    step3_cremain,
    step4_safety_deduction,
    step5_6_transport_penalty,
    step7_ch4_penalty,
    step8_net_credit,
    CO2_PER_C,
)


# ==================== Step 1 â€” Dry Mass ====================


def test_step1_dry_mass_spec_vector():
    """Spec: wet=115.4kg, moisture=12.7% â†’ dry â‰ˆ 0.10074 t."""
    dm = step1_dry_mass(115.4, 12.7)
    assert dm == pytest.approx(0.10074, abs=0.0001)


def test_step1_zero_moisture():
    dm = step1_dry_mass(100.0, 0.0)
    assert dm == pytest.approx(0.100, abs=0.001)


def test_step1_full_moisture():
    dm = step1_dry_mass(100.0, 100.0)
    assert dm == 0.0


# ==================== Step 2 â€” Gross C-Sink ====================


def test_step2_gross_c_sink_lantana():
    """Corg=0.60, dry=0.10074t â†’ gross = 0.60 * 0.10074 * (44/12)."""
    dm = step1_dry_mass(115.4, 12.7)
    gross = step2_gross_c_sink(0.60, dm)
    expected = 0.60 * dm * (44.0 / 12.0)
    assert gross == pytest.approx(expected, rel=0.001)


# ==================== Step 3 â€” H:Corg Decay ====================


def test_step3_cremain_top_tier():
    """H:Corg < 0.4 uses exponential decay formula."""
    dm = 0.10074
    corg = 0.60
    cr = step3_cremain(dm, corg, t=100, h_corg_ratio=0.35)
    # Must be between 60% and 100% of (dm * corg) â€” the decay reduces it
    assert cr > dm * corg * 0.60
    assert cr < dm * corg * 1.01


def test_step3_cremain_lower_tier():
    """H:Corg >= 0.4 gives conservative 70% retention."""
    dm = 0.10074
    corg = 0.60
    cr = step3_cremain(dm, corg, t=100, h_corg_ratio=0.45)
    assert cr == pytest.approx(dm * corg * 0.70, rel=0.001)


# ==================== Step 4 â€” Margin of Safety ====================


def test_step4_safety():
    dm = 0.10074
    safety = step4_safety_deduction(dm)
    assert safety == pytest.approx(dm * 20.0, rel=0.001)


# ==================== Steps 5-6 â€” Transport ====================


def test_step5_6_under_threshold():
    """14.2 km < 100 km â†’ penalty = 0."""
    penalty = step5_6_transport_penalty(14.2, 0.10074)
    assert penalty == 0.0


def test_step5_6_over_threshold():
    """150 km > 100 km â†’ penalty = 150 * 0.01194 * dry_mass."""
    dm = 0.10074
    penalty = step5_6_transport_penalty(150.0, dm)
    assert penalty == pytest.approx(150.0 * 0.01194 * dm, rel=0.001)


# ==================== Step 7 â€” CH4 ====================


def test_step7_compliant_burn():
    """min_temp=210Â°C > 190 AND moisture=12.7% < 15 â†’ compliant, * 0.005."""
    dm = 0.10074
    ok, pen = step7_ch4_penalty(dm, 12.7, 210.0)
    assert ok is True
    assert pen == pytest.approx(dm * 0.005, rel=0.001)


def test_step7_non_compliant_low_temp():
    """min_temp=180Â°C â‰¤ 190 â†’ non-compliant, * 30."""
    dm = 0.10074
    ok, pen = step7_ch4_penalty(dm, 12.7, 180.0)
    assert ok is False
    assert pen == pytest.approx(dm * 30.0, rel=0.001)


def test_step7_non_compliant_high_moisture():
    """moisture=16% â‰¥ 15 â†’ non-compliant regardless of temp."""
    dm = 0.10074
    ok, pen = step7_ch4_penalty(dm, 16.0, 300.0)
    assert ok is False
    assert pen == pytest.approx(dm * 30.0, rel=0.001)


# ==================== Step 8 â€” Net Credit ====================


def test_step8_net_credit_basic():
    # cremain is tonnes of elemental C remaining after 100yr decay.
    cremain_t_c = 0.05241  # dry=0.10074 * corg=0.60 * (0.75 + 0.25*decay@100)
    safety = 2.0148
    transport = 0.0
    ch4 = 0.0005037
    net = step8_net_credit(cremain_t_c, safety, transport, ch4)
    expected = (
        (cremain_t_c * (44.0 / 12.0))
        - (safety / 1000)
        - (transport / 1000)
        - (ch4 / 1000)
    )
    assert net == pytest.approx(expected, rel=0.001)


# ==================== Full Pipeline ====================


def test_full_pipeline_spec_vector():
    """Full 8-step with the spec test vector.

    wet=115.4kg, moisture=12.7%, min_temp=210Â°C, distance=14.2km.
    """
    audit = calculate_carbon_credit(
        wet_yield_kg=115.4,
        moisture_percent=12.7,
        min_recorded_temp_c=210.0,
        transport_distance_km=14.2,
        feedstock_species="Lantana_camara",
    )

    # Step 1: dry_mass â‰ˆ 0.10074
    assert audit.dry_mass_t == pytest.approx(0.10074, abs=0.0005)

    # Step 5-6: distance < 100 â†’ transport penalty = 0
    assert audit.transport_penalty_kg == 0.0

    # Step 7: compliant burn (210 > 190 AND 12.7 < 15)
    assert audit.ch4_compliant is True
    assert audit.ch4_penalty_kg == pytest.approx(audit.dry_mass_t * 0.005, rel=0.01)

    # Step 8: net credit is positive
    assert audit.net_credit_t_co2e > 0.0

    # Corg must be 0.60 for Lantana
    assert audit.corg_pct == 0.60

    # Result is an LCAAudit with all fields populated
    assert isinstance(audit, LCAAudit)


def test_full_pipeline_returns_dataclass():
    """Ensure all audit fields are populated and of correct type."""
    audit = calculate_carbon_credit(
        wet_yield_kg=100.0,
        moisture_percent=10.0,
        min_recorded_temp_c=200.0,
        transport_distance_km=50.0,
    )
    assert isinstance(audit.dry_mass_t, float)
    assert isinstance(audit.gross_c_sink_t_co2e, float)
    assert isinstance(audit.cremain_t, float)
    assert isinstance(audit.safety_deduction_kg, float)
    assert isinstance(audit.ch4_compliant, bool)
    assert isinstance(audit.net_credit_t_co2e, float)


def test_full_pipeline_heavy_penalty():
    """Non-compliant burn (low temp) produces drastically lower credit."""
    compliant = calculate_carbon_credit(
        wet_yield_kg=100.0,
        moisture_percent=10.0,
        min_recorded_temp_c=250.0,  # compliant
    )
    non_compliant = calculate_carbon_credit(
        wet_yield_kg=100.0,
        moisture_percent=10.0,
        min_recorded_temp_c=150.0,  # non-compliant
    )
    assert compliant.net_credit_t_co2e > non_compliant.net_credit_t_co2e


def test_get_corg_lantana():
    assert get_corg("Lantana_camara") == 0.60


def test_get_corg_unknown_species_returns_default():
    assert get_corg("Unknown_species") == get_corg("Default")


def test_co2_per_c_constant():
    """44/12 â‰ˆ 3.6667."""
    assert CO2_PER_C == pytest.approx(44.0 / 12.0, rel=0.001)


# ==================== P0-1 Regression — pinned spec answer ====================


def test_full_pipeline_spec_vector_pinned_net_credit():
    """REGRESSION: lock the post-fix net credit for the spec test vector.

    Inputs: wet=115.4kg, moisture=12.7%, min_temp=210°C, distance=14.2km,
            Lantana (Corg=0.60), H:Corg=0.35.
    Expected (computed by hand from CSI Standard 3.2):
      dry_mass    = 0.10074 t
      cremain     = 0.10074 * 0.60 * (0.75 + 0.25*(0.1787*e^-53.37 + 0.8237*e^-0.997))
                  ≈ 0.10074 * 0.60 * (0.75 + 0.25 * 0.30421)
                  ≈ 0.10074 * 0.60 * 0.82605
                  ≈ 0.04994 t elemental C
      gross_co2e  = 0.04994 * (44/12) ≈ 0.18311 t CO2e   ? the legitimate basis
      safety_t    = 0.10074 * 0.020 ≈ 0.002015 t CO2e
      transport   = 0  (14.2 km < 100)
      ch4_t       = 0.10074 * 0.005 / 1000 ≈ 5.037e-7 t CO2e
      net_credit  ≈ 0.18311 - 0.002015 - 0 - 5e-7  ≈ 0.18110 t CO2e

    Before this fix the value would have been ≈ 0.21961 t CO2e (~21% higher).
    """
    audit = calculate_carbon_credit(
        wet_yield_kg=115.4,
        moisture_percent=12.7,
        min_recorded_temp_c=210.0,
        transport_distance_km=14.2,
        feedstock_species="Lantana_camara",
        h_corg_ratio=0.35,
    )
    assert audit.net_credit_t_co2e == pytest.approx(0.18110, abs=0.001), (
        f"Net credit must derive from cremain*44/12, got {audit.net_credit_t_co2e}"
    )
    # Cremain must be ~0.04994 t C, NOT 0.06044 (which would be dry*corg without decay)
    assert audit.cremain_t == pytest.approx(0.04994, abs=0.001)
