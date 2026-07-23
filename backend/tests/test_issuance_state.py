"""PR-1.1 — pure credit-issuance lifecycle state machine.

Mirrors services/dispatch_state.py's shape: pure functions only, no DB/HTTP,
unit-testable in isolation. The portal router (PR-1.4) is the thin DB edge
that calls these and persists the result.
"""

import pytest

from services.issuance_state import (
    IllegalIssuanceTransition,
    IssuanceNotReady,
    VALID_STATUSES,
    assert_issuable,
    is_mutable,
    validate_transition,
)


class TestValidateTransition:
    def test_pending_to_verified_is_legal(self):
        validate_transition("pending", "verified")  # no raise

    def test_verified_to_issued_is_legal(self):
        validate_transition("verified", "issued")

    def test_issued_to_retired_is_legal(self):
        validate_transition("issued", "retired")

    def test_pending_to_cancelled_is_legal(self):
        validate_transition("pending", "cancelled")

    def test_verified_to_cancelled_is_legal(self):
        validate_transition("verified", "cancelled")

    def test_pending_to_issued_skips_verification_illegal(self):
        with pytest.raises(IllegalIssuanceTransition):
            validate_transition("pending", "issued")

    def test_issued_to_verified_backward_illegal(self):
        with pytest.raises(IllegalIssuanceTransition):
            validate_transition("issued", "verified")

    def test_issued_to_cancelled_illegal_once_issued(self):
        with pytest.raises(IllegalIssuanceTransition):
            validate_transition("issued", "cancelled")

    def test_retired_is_terminal(self):
        with pytest.raises(IllegalIssuanceTransition):
            validate_transition("retired", "issued")
        with pytest.raises(IllegalIssuanceTransition):
            validate_transition("retired", "cancelled")

    def test_cancelled_is_terminal(self):
        with pytest.raises(IllegalIssuanceTransition):
            validate_transition("cancelled", "pending")

    def test_unknown_current_status_illegal(self):
        with pytest.raises(IllegalIssuanceTransition):
            validate_transition("bogus", "verified")

    def test_unknown_target_status_illegal(self):
        with pytest.raises(IllegalIssuanceTransition):
            validate_transition("pending", "bogus")

    def test_all_valid_statuses_present(self):
        assert VALID_STATUSES == (
            "pending",
            "verified",
            "issued",
            "retired",
            "cancelled",
        )


class TestAssertIssuable:
    def test_issuable_when_final_signed_and_verified(self):
        assert_issuable(
            batch_is_provisional=False,
            batch_is_signed=True,
            independently_verified=True,
        )  # no raise

    def test_not_issuable_when_provisional(self):
        with pytest.raises(IssuanceNotReady, match="provisional"):
            assert_issuable(
                batch_is_provisional=True,
                batch_is_signed=True,
                independently_verified=True,
            )

    def test_not_issuable_when_unsigned(self):
        with pytest.raises(IssuanceNotReady, match="signed"):
            assert_issuable(
                batch_is_provisional=False,
                batch_is_signed=False,
                independently_verified=True,
            )

    def test_not_issuable_without_independent_verification(self):
        with pytest.raises(IssuanceNotReady, match="independent"):
            assert_issuable(
                batch_is_provisional=False,
                batch_is_signed=True,
                independently_verified=False,
            )

    def test_reports_all_failing_reasons_together(self):
        with pytest.raises(IssuanceNotReady) as exc_info:
            assert_issuable(
                batch_is_provisional=True,
                batch_is_signed=False,
                independently_verified=False,
            )
        message = str(exc_info.value)
        assert "provisional" in message
        assert "signed" in message
        assert "independent" in message


class TestIsMutable:
    def test_pending_is_mutable(self):
        assert is_mutable("pending") is True

    def test_verified_is_mutable(self):
        assert is_mutable("verified") is True

    def test_issued_is_immutable(self):
        assert is_mutable("issued") is False

    def test_retired_is_immutable(self):
        assert is_mutable("retired") is False

    def test_cancelled_is_immutable(self):
        assert is_mutable("cancelled") is False
