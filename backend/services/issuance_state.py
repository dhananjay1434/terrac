"""PR-1 — credit issuance lifecycle state machine.

A registry credit is a serialized, issue-exactly-once unit traceable to one
physical batch — today `net_credit_t_co2e` is just a number on a `Batch` row
with no lifecycle. This module is the pure lifecycle for `CreditIssuance`
(PR-1.2): pending -> verified -> issued -> retired, with cancellation from
either of the first two states. Immutable once `issued`.

Pure functions only (no DB/HTTP), mirroring services/dispatch_state.py's
shape — the portal router (PR-1.4) is the thin DB edge that calls these and
persists the result.
"""

from __future__ import annotations

VALID_STATUSES = ("pending", "verified", "issued", "retired", "cancelled")

# Legal forward-only transitions. 'retired' and 'cancelled' are terminal.
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"verified", "cancelled"},
    "verified": {"issued", "cancelled"},
    "issued": {"retired"},
    "retired": set(),
    "cancelled": set(),
}


class IllegalIssuanceTransition(ValueError):
    """Raised for any transition that violates the issuance state machine."""


class IssuanceNotReady(ValueError):
    """Raised when a batch does not yet meet the preconditions to issue."""


def validate_transition(current_status: str, target_status: str) -> None:
    """Raise IllegalIssuanceTransition unless target_status is a legal next
    step from current_status. Pure — the caller applies + persists the
    change."""
    if current_status not in VALID_STATUSES:
        raise IllegalIssuanceTransition(f"unknown current status '{current_status}'")
    if target_status not in VALID_STATUSES:
        raise IllegalIssuanceTransition(f"unknown target status '{target_status}'")
    if target_status not in _ALLOWED_TRANSITIONS[current_status]:
        raise IllegalIssuanceTransition(
            f"illegal transition '{current_status}' -> '{target_status}'"
        )


def assert_issuable(
    *,
    batch_is_provisional: bool,
    batch_is_signed: bool,
    independently_verified: bool,
) -> None:
    """Raise IssuanceNotReady unless the batch meets ALL preconditions to
    enter 'issued': not provisional, signed (lca_signature present), and
    independently verified (PR-2 — a distinct verifier/admin human channel
    signed off, not the producing device/operator). Collects every failing
    reason into one message rather than stopping at the first."""
    reasons = []
    if batch_is_provisional:
        reasons.append("batch is still provisional")
    if not batch_is_signed:
        reasons.append("batch credit is not signed")
    if not independently_verified:
        reasons.append("batch has not passed independent verification")
    if reasons:
        raise IssuanceNotReady("; ".join(reasons))


def is_mutable(status: str) -> bool:
    """False once a CreditIssuance has left the pending/verified states —
    'issued', 'retired', and 'cancelled' records are immutable."""
    return status in ("pending", "verified")


def make_serial(project_id: str, vintage: int, sequence: int) -> str:
    """Deterministic, human-legible, collision-resistant serial:
    '{project_id}-{vintage}-{zero-padded sequence}'. Uniqueness across a
    project's issuances comes from `sequence` being a per-project monotonic
    counter (assigned by the caller under the DB's unique constraint on
    `serial`), not from anything computed here."""
    return f"{project_id}-{vintage}-{sequence:06d}"
