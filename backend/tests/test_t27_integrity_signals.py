"""T2.7 — device-integrity plausibility signals surfaced in the LCA audit.

The GPS anchor is client-authored (the app injects the EXIF it later matches),
so it is weak corroboration; the audit records that trust level plus the
mock-location flag so a verifier sees it per batch.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import Batch

pytestmark = pytest.mark.asyncio


async def _make_batch(client, bu, *, mock_location):
    await client.post(
        "/api/v1/batches",
        content=json.dumps(
            {
                "batch_uuid": bu,
                "feedstock_species": "Lantana_camara",
                "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
                "moisture_percent": 12.0,
                "harvest_uptime_seconds": 100,
                "latitude": 12.97,
                "longitude": 77.59,
                "mock_location_enabled": mock_location,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + bu[:8]},
    )


async def _signals(session_factory, bu):
    async with session_factory() as s:
        b = (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(uuid.UUID(bu))))
        ).scalar_one()
    return json.loads(b.lca_audit_json)["integrity_signals"]


async def test_mock_location_true_is_flagged(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _make_batch(client, bu, mock_location=True)
    sig = await _signals(session_factory, bu)
    assert sig["mock_location_enabled"] is True
    assert sig["exif_trust"] == "client_authored_weak"
    assert sig["gps_anchor_mismatch_km"] == 1.0


async def test_mock_location_false_default(client, registered_device, session_factory):
    bu = str(uuid.uuid4())
    await _make_batch(client, bu, mock_location=False)
    sig = await _signals(session_factory, bu)
    assert sig["mock_location_enabled"] is False
    assert "gps_anchor_status" in sig
