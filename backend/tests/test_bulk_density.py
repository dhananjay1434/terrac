"""V8 Part 4 (F) — bulk-density volume→mass. Pure-function tests, test-first.

Covers services/bulk_density.volume_to_mass_kg and the two corroboration.py
derivers (derive_wet_yield_from_density, derive_density_calibration_compliance).
The credit_engine wiring (project-scoped in-date lookup + C10 gate +
"wet_yield_density_derived" transparency flag) is covered end-to-end in
test_credit_engine_density_wiring.py.
"""

from __future__ import annotations

import pytest

from services.bulk_density import volume_to_mass_kg
from corroboration import (
    derive_density_calibration_compliance,
    derive_wet_yield_from_density,
)


def test_volume_to_mass_basic():
    assert volume_to_mass_kg(200.0, 0.25) == 50.0


def test_volume_to_mass_zero_volume_rejected():
    with pytest.raises(ValueError):
        volume_to_mass_kg(0.0, 0.25)


def test_volume_to_mass_negative_density_rejected():
    with pytest.raises(ValueError):
        volume_to_mass_kg(200.0, -0.1)


def test_derive_wet_yield_from_density_success():
    mass, reason = derive_wet_yield_from_density({"kiln_gross_capacity": 200.0}, 0.25)
    assert mass == 50.0
    assert reason is None


def test_derive_wet_yield_from_density_no_telemetry():
    mass, reason = derive_wet_yield_from_density(None, 0.25)
    assert mass is None
    assert reason == "no_telemetry_for_density_fallback"


def test_derive_wet_yield_from_density_missing_volume():
    # A non-empty telemetry payload that simply lacks kiln_gross_capacity
    # (an empty dict is falsy and hits the "no telemetry" branch instead —
    # see the adjacent no_telemetry test).
    mass, reason = derive_wet_yield_from_density({"kiln_id": "k1"}, 0.25)
    assert mass is None
    assert reason == "missing_volume_or_density"


def test_derive_wet_yield_from_density_missing_density():
    mass, reason = derive_wet_yield_from_density({"kiln_gross_capacity": 200.0}, None)
    assert mass is None
    assert reason == "missing_volume_or_density"


def test_derive_wet_yield_from_density_invalid_volume_type():
    mass, reason = derive_wet_yield_from_density(
        {"kiln_gross_capacity": "not-a-number"}, 0.25
    )
    assert mass is None
    assert reason == "invalid_volume_or_density"


def test_derive_density_calibration_compliance_enforced_and_missing():
    ok, reason = derive_density_calibration_compliance(False, enforced=True)
    assert ok is False
    assert reason == "production_requires_valid_density"


def test_derive_density_calibration_compliance_enforced_and_present():
    ok, reason = derive_density_calibration_compliance(True, enforced=True)
    assert ok is True
    assert reason is None


def test_derive_density_calibration_compliance_unenforced_is_inert():
    ok, reason = derive_density_calibration_compliance(False, enforced=False)
    assert ok is True
    assert reason is None
