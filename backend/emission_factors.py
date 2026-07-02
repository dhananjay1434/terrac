"""Transport fuel emission factors — Rainbow BiCRS (Rainbow C6).

SINGLE audited source of the fuel→CO2e factors used by the transport-event LCA
contribution. Isolated here (not inlined in lca_engine) so the numbers are
reviewable in one place and every value carries its citation.

STATUS: the Rainbow methodology annexes have NOT yet been supplied with numeric
fuel emission factors (the `docs/dMRV Criteria Distributed Biochar.md` section
lists only the REQUIRED per-event data: distance, weight, vehicle type, fuel
consumed — no kg-CO2e-per-unit constants). Per the C6 build rule we DO NOT invent
factors. The values below are placeholders and MUST be replaced with cited
methodology/annex values before the transport-event contribution is allowed to
affect any issued credit.

Because of that, `TRANSPORT_EVENTS_ENFORCED` is False: the per-event fuel
emissions are computed and PERSISTED for audit, but they do NOT replace or add to
the credit (the existing GPS-haversine transport penalty in lca_engine remains
authoritative). Flip to True only once every factor below is cited and the
methodology owner has signed off — at which point wire the summed emissions into
recompute_batch_credit's LCA call.
"""

from __future__ import annotations

# Master switch. While False, transport-event emissions are audit-only (computed
# + stored, never fed into the issued credit). See module docstring.
TRANSPORT_EVENTS_ENFORCED = False

# Fuel emission factors, kg CO2e per LITRE of fuel burned.
# TODO(cite): replace every value with the Rainbow methodology / annex figure and
# record the source doc + table + version next to it. These are NON-BINDING
# placeholders (order-of-magnitude only) and are inert while ENFORCED is False.
_FUEL_FACTORS_KG_CO2E_PER_L: dict[str, float] = {
    # "diesel": <annex value>,  TODO(cite)
    # "petrol": <annex value>,  TODO(cite)
    # "cng":    <annex value>,  TODO(cite)
    "diesel": 2.68,  # TODO(cite): placeholder, ~DEFRA-order; NOT methodology-sourced
    "petrol": 2.31,  # TODO(cite): placeholder
    "cng": 2.02,  # TODO(cite): placeholder (per kg; unit needs confirming)
}

# Fallback when the fuel type is unknown/unmapped: use the highest known factor so
# an unrecognized fuel is penalised conservatively rather than under-counted.
_UNKNOWN_FUEL_FACTOR = max(_FUEL_FACTORS_KG_CO2E_PER_L.values())


def fuel_emissions_kg_co2e(
    fuel_type: str | None, fuel_amount_litres: float | None
) -> float:
    """kg CO2e for one transport leg from its fuel burn.

    Returns 0.0 when the amount is missing/non-positive. An unknown fuel type is
    charged at the most conservative (highest) known factor. This is the pure
    per-leg math; it is NOT gated here — the caller decides whether the result
    affects the credit (see TRANSPORT_EVENTS_ENFORCED).
    """
    if fuel_amount_litres is None or fuel_amount_litres <= 0.0:
        return 0.0
    factor = _FUEL_FACTORS_KG_CO2E_PER_L.get(
        (fuel_type or "").strip().lower(), _UNKNOWN_FUEL_FACTOR
    )
    return fuel_amount_litres * factor
