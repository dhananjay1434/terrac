"""P1-B3 — all datetime comparisons normalize to aware-UTC.

Before the fix, the teleport check stripped tzinfo from both operands
(`.replace(tzinfo=None)`) before subtracting. A payload sent with a +05:30
offset vs a stored UTC value then mis-timed by 5.5 hours — spuriously 403ing
honest evidence or missing a real teleport. `_as_utc` normalizes every operand
so the subtraction is representation-invariant. These test that contract
directly (deterministic; no SQLite tz-storage flakiness).
"""

from datetime import datetime, timedelta, timezone

from server import _as_utc

_IST = timezone(timedelta(hours=5, minutes=30))


def test_naive_is_treated_as_utc():
    r = _as_utc(datetime(2026, 1, 1, 12, 0, 0))
    assert r.tzinfo == timezone.utc
    assert (r.hour, r.minute) == (12, 0)


def test_offset_aware_is_converted_to_utc():
    # 17:30 +05:30 is 12:00 UTC.
    r = _as_utc(datetime(2026, 1, 1, 17, 30, 0, tzinfo=_IST))
    assert r.tzinfo == timezone.utc
    assert (r.hour, r.minute) == (12, 0)


def test_same_instant_different_representations_are_equal():
    utc = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ist = datetime(2026, 1, 1, 17, 30, 0, tzinfo=_IST)  # identical instant
    assert _as_utc(utc) == _as_utc(ist)
    assert (_as_utc(utc) - _as_utc(ist)).total_seconds() == 0.0


def test_mixed_naive_aware_subtraction_has_no_skew():
    naive_noon = datetime(2026, 1, 1, 12, 0, 0)
    aware_noon = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert (_as_utc(naive_noon) - _as_utc(aware_noon)).total_seconds() == 0.0
