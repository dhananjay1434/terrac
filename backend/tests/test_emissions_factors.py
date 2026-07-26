"""M4.2 — transport emissions factors (pure, versioned)."""
import pytest

from emissions_factors import FACTOR_VERSION, estimate_emissions


def test_diesel_truck_golden():
    kg, ver = estimate_emissions(100.0, "diesel")
    assert kg == 82.0
    assert ver == FACTOR_VERSION


def test_tractor_explicit_class():
    kg, _ = estimate_emissions(9.2, "diesel", vehicle_class="tractor_diesel")
    assert kg == round(9.2 * 0.75, 3)


def test_ev_lower_than_diesel():
    ev, _ = estimate_emissions(100.0, "ev")
    dsl, _ = estimate_emissions(100.0, "diesel")
    assert ev < dsl


def test_bullock_is_zero():
    kg, _ = estimate_emissions(50.0, "bullock")
    assert kg == 0.0


def test_zero_distance():
    assert estimate_emissions(0.0, "diesel")[0] == 0.0


def test_negative_distance_raises():
    with pytest.raises(ValueError):
        estimate_emissions(-1.0, "diesel")


def test_unknown_fuel_raises():
    with pytest.raises(ValueError):
        estimate_emissions(10.0, "plutonium")


def test_unknown_vehicle_class_raises():
    with pytest.raises(ValueError):
        estimate_emissions(10.0, "diesel", vehicle_class="rocket")
