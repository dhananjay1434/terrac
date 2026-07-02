"""End-to-end corroboration flow (Phase 7-R).

Proves the real lifecycle: a batch is created PROVISIONAL with no credit inputs,
then telemetry / yield / application evidence arrives and the server derives the
credit-bearing inputs and converges the credit. Runs with the global telemetry
mock disabled so it exercises real stored rows.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import Batch

pytestmark = pytest.mark.asyncio


def _batch_payload(batch_uuid: str) -> dict:
    """Exact fields the client sends (no credit inputs)."""
    return {
        "sourcing_uuid": str(uuid.uuid4()),
        "batch_uuid": batch_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 14.5,
        "moisture_compliant": True,
        "photo_path": "/sandbox/x.jpg",
        "sha256_hash": "a" * 64,
        "latitude": 12.9716,
        "longitude": 77.5946,
        "mock_location_enabled": False,
        "harvest_uptime_seconds": 3600,
        "azimuth": 1.0,
        "pitch": 2.0,
        "roll": 3.0,
    }


async def _fetch(session_factory, batch_uuid: str) -> Batch:
    async with session_factory() as s:
        row = (
            await s.execute(
                select(Batch).where(Batch.batch_uuid == uuid.UUID(batch_uuid))
            )
        ).scalar_one()
        return row


async def test_credit_converges_as_evidence_arrives(
    client, registered_device, session_factory, monkeypatch
):
    monkeypatch.setenv("DISABLE_TELEMETRY_MOCK", "1")
    bu = str(uuid.uuid4())

    # 1. Batch lands first — no evidence yet -> provisional, uncorroborated inputs.
    resp = await client.post(
        "/api/v1/batches",
        content=json.dumps(_batch_payload(bu)).encode("utf-8"),
        headers={"X-Idempotency-Key": "flow-batch"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["provisional"] is True

    batch = await _fetch(session_factory, bu)
    assert batch.wet_yield_kg == 0.0
    assert batch.min_recorded_temp_c == 0.0
    assert batch.transport_distance_km == 0.0
    reasons = json.loads(batch.provisional_reasons)
    assert "wet_yield_uncorroborated" in reasons
    assert "min_temp_uncorroborated" in reasons
    assert "transport_uncorroborated" in reasons

    # 2. Telemetry arrives (canonical snake key) -> min temp corroborated.
    tel = {
        "telemetry_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "temperature_readings": [650.0] * 65,
    }
    r = await client.post(
        "/api/v1/telemetry",
        content=json.dumps(tel).encode("utf-8"),
        headers={"X-Idempotency-Key": "flow-tel"},
    )
    assert r.status_code == 201, r.text
    batch = await _fetch(session_factory, bu)
    assert batch.min_recorded_temp_c == 650.0
    assert "min_temp_uncorroborated" not in json.loads(batch.provisional_reasons)

    # 3. Yield arrives -> wet yield corroborated.
    yld = {
        "yield_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "wet_yield_weight_kg": 120.0,
    }
    r = await client.post(
        "/api/v1/yield",
        content=json.dumps(yld).encode("utf-8"),
        headers={"X-Idempotency-Key": "flow-yield"},
    )
    assert r.status_code == 201, r.text
    batch = await _fetch(session_factory, bu)
    assert batch.wet_yield_kg == 120.0

    # 3.5 Moisture readings arrive (Rainbow C2) -> moisture compliance satisfied.
    # No biomass_input_kg on this payload, so the floor of 10 photographed
    # readings applies; supply exactly 10 so the only remaining reason is the
    # assumed H:Corg.
    for i in range(1, 11):
        rm = await client.post(
            "/api/v1/moisture",
            content=json.dumps(
                {
                    "reading_uuid": str(uuid.uuid4()),
                    "batch_uuid": bu,
                    "moisture_percent": 12.0,
                    "sequence": i,
                    "sha256_hash": "a" * 64,
                }
            ).encode("utf-8"),
            headers={"X-Idempotency-Key": f"flow-moist-{i}"},
        )
        assert rm.status_code == 201, rm.text

    # 4. Application arrives with distinct GPS -> transport corroborated.
    app = {
        "application_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "latitude": 13.9716,  # ~111 km north of the batch
        "longitude": 77.5946,
    }
    r = await client.post(
        "/api/v1/application",
        content=json.dumps(app).encode("utf-8"),
        headers={"X-Idempotency-Key": "flow-app"},
    )
    assert r.status_code == 201, r.text

    batch = await _fetch(session_factory, bu)
    # All physical inputs now corroborated from real evidence.
    assert batch.wet_yield_kg == 120.0
    assert batch.min_recorded_temp_c == 650.0
    assert batch.transport_distance_km > 100.0
    assert batch.net_credit_t_co2e != 0.0
    # Still provisional ONLY because the lab permanence inputs are unsupplied:
    # H:Corg (Phase 8-R) and organic Corg (C7 — previously a species constant).
    assert json.loads(batch.provisional_reasons) == ["assumed_h_corg", "assumed_corg"]
    assert batch.provisional is True
