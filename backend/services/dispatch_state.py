"""V8 Part 3.2 — dispatch custody state machine.

Represents biomass/biochar moving between custodians:
    draft --(Submit)--> in_transit --(Mark Received)--> received

Pure functions only (no DB/HTTP) so the transition and weight-lock rules are
unit-testable in isolation; the router (routers/dispatch.py) is the thin DB
edge that calls these and persists the result.

Two integrity rules live here:
  1. **Weight-lock.** `weight_source_kg` (the source-side witnessed weight) is
     set once, at Submit (still in 'draft'), and becomes IMMUTABLE the moment
     the dispatch leaves 'draft' — a shipment cannot be re-weighed after the
     fact to hide shrinkage/theft. `weight_facility_kg` is set exactly once,
     at the in_transit -> received transition (the facility's witnessed
     re-weigh) — the router enforces "exactly once" by only accepting it on
     that specific transition.
  2. **Dual-weigh reconciliation.** Comparing the two witnessed weights is a
     REVIEW SIGNAL, not a block: a delta beyond tolerance is FLAGGED (mirrors
     corroboration.py's derive_* "value + reason" pattern) so a verifier sees
     it, but the transition still succeeds — spillage, moisture loss, or theft
     are real-world events that must be recorded, not hidden by a rejected
     request.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

VALID_STATUSES = ("draft", "in_transit", "received")

# Legal forward-only transitions. No skipping (draft -> received forbidden),
# no backward transitions, 'received' is terminal.
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"in_transit"},
    "in_transit": {"received"},
    "received": set(),
}

DEFAULT_WEIGHT_TOLERANCE_PCT = 5.0


class IllegalTransitionError(ValueError):
    """Raised for any transition that violates the dispatch state machine."""


def validate_transition(current_status: str, target_status: str) -> None:
    """Raise IllegalTransitionError unless target_status is a legal next step
    from current_status. Pure — the caller applies + persists the change."""
    if current_status not in VALID_STATUSES:
        raise IllegalTransitionError(f"unknown current status '{current_status}'")
    if target_status not in VALID_STATUSES:
        raise IllegalTransitionError(f"unknown target status '{target_status}'")
    if target_status not in _ALLOWED_TRANSITIONS[current_status]:
        raise IllegalTransitionError(
            f"illegal transition '{current_status}' -> '{target_status}'"
        )


def assert_weight_source_not_locked(current_status: str) -> None:
    """weight_source_kg may only be written while status is still 'draft'.
    Raise once the dispatch has left draft (weight-lock)."""
    if current_status != "draft":
        raise IllegalTransitionError(
            "weight_source_kg is locked once a dispatch leaves 'draft'"
        )


@dataclass
class ReconciliationResult:
    delta_kg: float
    delta_pct: float
    flagged: bool
    reason: Optional[str]


def reconcile_dual_weight(
    weight_source_kg: float,
    weight_facility_kg: float,
    tolerance_pct: float = DEFAULT_WEIGHT_TOLERANCE_PCT,
) -> ReconciliationResult:
    """Compare the source-witnessed and facility-witnessed weights.

    `delta_pct` is measured on the ABSOLUTE delta, so a facility weight that is
    LOWER than the source weight (spillage/loss) flags on the same basis as
    one that is higher (double-loading fraud) — magnitude of discrepancy is
    what matters for review, not direction.
    """
    if weight_source_kg <= 0:
        return ReconciliationResult(0.0, 0.0, True, "invalid_source_weight")
    delta_kg = weight_facility_kg - weight_source_kg
    delta_pct = abs(delta_kg) / weight_source_kg * 100.0
    flagged = delta_pct > tolerance_pct
    return ReconciliationResult(
        delta_kg=delta_kg,
        delta_pct=delta_pct,
        flagged=flagged,
        reason="weight_discrepancy" if flagged else None,
    )
