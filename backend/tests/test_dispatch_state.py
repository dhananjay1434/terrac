"""V8 Part 3.2 — dispatch custody state machine (pure, no DB/HTTP).

Written test-first per the production execution plan: draft->in_transit->received
transitions, illegal-transition rejection, weight-lock (weight_source immutable
once a dispatch leaves 'draft'), and dual-weigh reconciliation (delta beyond
tolerance is FLAGGED for review, not rejected — a real-world discrepancy must
still be recorded).
"""

from __future__ import annotations

import pytest

import services.dispatch_state as ds


def test_legal_forward_transitions():
    ds.validate_transition("draft", "in_transit")
    ds.validate_transition("in_transit", "received")


def test_illegal_skip_transition_rejected():
    with pytest.raises(ds.IllegalTransitionError):
        ds.validate_transition("draft", "received")


def test_illegal_backward_transition_rejected():
    with pytest.raises(ds.IllegalTransitionError):
        ds.validate_transition("in_transit", "draft")
    with pytest.raises(ds.IllegalTransitionError):
        ds.validate_transition("received", "in_transit")


def test_received_is_terminal():
    with pytest.raises(ds.IllegalTransitionError):
        ds.validate_transition("received", "received")


def test_unknown_status_rejected():
    with pytest.raises(ds.IllegalTransitionError):
        ds.validate_transition("draft", "bogus")
    with pytest.raises(ds.IllegalTransitionError):
        ds.validate_transition("bogus", "draft")


def test_weight_lock_allows_edit_only_in_draft():
    ds.assert_weight_source_not_locked("draft")  # no raise
    with pytest.raises(ds.IllegalTransitionError):
        ds.assert_weight_source_not_locked("in_transit")
    with pytest.raises(ds.IllegalTransitionError):
        ds.assert_weight_source_not_locked("received")


def test_dual_weigh_within_tolerance_not_flagged():
    r = ds.reconcile_dual_weight(
        weight_source_kg=100.0, weight_facility_kg=103.0, tolerance_pct=5.0
    )
    assert r.flagged is False
    assert r.reason is None
    assert r.delta_kg == pytest.approx(3.0)
    assert r.delta_pct == pytest.approx(3.0)


def test_dual_weigh_beyond_tolerance_flagged():
    r = ds.reconcile_dual_weight(
        weight_source_kg=100.0, weight_facility_kg=120.0, tolerance_pct=5.0
    )
    assert r.flagged is True
    assert r.reason == "weight_discrepancy"
    assert r.delta_pct == pytest.approx(20.0)


def test_dual_weigh_exact_tolerance_boundary_not_flagged():
    r = ds.reconcile_dual_weight(
        weight_source_kg=100.0, weight_facility_kg=105.0, tolerance_pct=5.0
    )
    assert r.flagged is False  # exactly at tolerance, not beyond it


def test_dual_weigh_negative_delta_flagged_by_magnitude():
    """A facility weight LOWER than source (spillage/loss) must flag on the
    same absolute-delta basis, not just when the facility weight is higher."""
    r = ds.reconcile_dual_weight(
        weight_source_kg=100.0, weight_facility_kg=80.0, tolerance_pct=5.0
    )
    assert r.flagged is True
    assert r.delta_kg == pytest.approx(-20.0)
    assert r.delta_pct == pytest.approx(20.0)


def test_dual_weigh_invalid_source_weight_flagged():
    r = ds.reconcile_dual_weight(
        weight_source_kg=0.0, weight_facility_kg=50.0, tolerance_pct=5.0
    )
    assert r.flagged is True
    assert r.reason == "invalid_source_weight"
