import pytest
from unittest.mock import patch
import observability

def test_record_gate_rejection_increments_prometheus_and_logs(caplog):
    caplog.clear()
    with patch("observability._PROM", True):
        initial_val = observability.GATE_REJECTIONS.labels(
            gate="boundary_geofence", reason="QUARANTINE_GPS_OUTSIDE_PARCEL"
        )._value.get()

        observability.record_gate_rejection(
            gate="boundary_geofence",
            reason="QUARANTINE_GPS_OUTSIDE_PARCEL",
            extra={"batch_uuid": "batch-123", "lat": 12.3},
        )

        new_val = observability.GATE_REJECTIONS.labels(
            gate="boundary_geofence", reason="QUARANTINE_GPS_OUTSIDE_PARCEL"
        )._value.get()

        assert new_val == initial_val + 1
        assert "gate_rejection: boundary_geofence (QUARANTINE_GPS_OUTSIDE_PARCEL)" in caplog.text


def test_parcel_registration_gate_rejections(caplog):
    caplog.clear()
    with patch("observability._PROM", True):
        initial_val = observability.GATE_REJECTIONS.labels(
            gate="parcel_registration", reason="overlap_reject"
        )._value.get()

        observability.record_gate_rejection(
            gate="parcel_registration",
            reason="overlap_reject",
            extra={"project_id": "proj-1", "conflicting_parcel_uuid": "parcel-1"},
        )

        new_val = observability.GATE_REJECTIONS.labels(
            gate="parcel_registration", reason="overlap_reject"
        )._value.get()

        assert new_val == initial_val + 1
        assert "gate_rejection: parcel_registration (overlap_reject)" in caplog.text
