"""Versioned transport-emissions factors for dispatch journeys (M4.2).

Factors are VERSIONED exactly like the LCA constants: a journey stores the
`factor_version` it was computed under, so a later factor revision never
silently rewrites a historical credit. `estimate_emissions` is pure.

⚠ [VERIFY] the factor values with the founders / methodology before production
use. The numbers below are defensible placeholders (typical Indian road-freight
diesel intensities), NOT registry-signed constants. Until verified, journeys_v2
credit effects must remain flag-gated (see DMRV_EVOLUTION_AGENT_PLAN M4.3).
"""
from __future__ import annotations

# kg CO2e per km, per vehicle class (well-to-wheel, laden single trip).
FACTORS_V1: dict[str, float] = {
    "diesel_truck_5t": 0.82,
    "diesel_truck_10t": 1.05,
    "tractor_diesel": 0.75,
    "ev_truck": 0.28,
    "bullock_cart": 0.0,  # animal traction — no fuel-cycle emissions
}

FACTOR_VERSION = "emf-v1"

# Map the wire `fuel_type` enum to a default vehicle class when the caller does
# not give an explicit class. Conservative: unknown → heaviest diesel factor.
_FUEL_DEFAULT_CLASS: dict[str, str] = {
    "diesel": "diesel_truck_5t",
    "petrol": "diesel_truck_5t",  # no separate petrol-freight factor yet; use diesel
    "ev": "ev_truck",
    "bullock": "bullock_cart",
    "none": "bullock_cart",
}


def estimate_emissions(
    distance_km: float,
    fuel_type: str,
    *,
    vehicle_class: str | None = None,
) -> tuple[float, str]:
    """Return (emissions_kg, factor_version).

    Raises ValueError on negative distance or an unknown fuel_type/vehicle_class
    — never guesses silently, so a bad input surfaces instead of producing a
    plausible-but-wrong credit deduction.
    """
    if distance_km < 0:
        raise ValueError("distance_km must be >= 0")
    cls = vehicle_class or _FUEL_DEFAULT_CLASS.get(fuel_type)
    if cls is None:
        raise ValueError(f"unknown fuel_type: {fuel_type!r}")
    if cls not in FACTORS_V1:
        raise ValueError(f"unknown vehicle_class: {cls!r}")
    return round(distance_km * FACTORS_V1[cls], 3), FACTOR_VERSION
