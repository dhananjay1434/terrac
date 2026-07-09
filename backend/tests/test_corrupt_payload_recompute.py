"""P1-B1 — a corrupt stored payload must never brick a batch.

Before the fix, a single unparseable `payload_json` (bad write, manual DB edit,
partial migration) raised JSONDecodeError inside recompute_batch_credit, which
aborted the whole recompute (500 on every subsequent evidence POST) and 500'd
the compliance read. After the fix (_safe_json), a corrupt row degrades to
"contributes nothing" + a log line, and recompute/compliance keep working.

These cover the three distinct constructs the fix touched: the moisture/composite
`sum(...)` generator, the scalar telemetry/yield/application `.get()` payloads,
and the transport list-comp — plus the compliance endpoint's provisional_reasons.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import Batch, MoistureReading, PyrolysisTelemetry, YieldMetrics

pytestmark = pytest.mark.asyncio

_CORRUPT = "{ this is not valid json"


async def _create_batch(client, bu, biomass_kg=500.0):
    return await client.post(
        "/api/v1/batches",
        content=json.dumps(
            {
                "batch_uuid": bu,
                "feedstock_species": "Lantana_camara",
                "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
                "moisture_percent": 12.0,
                "harvest_uptime_seconds": 100,
                "biomass_input_kg": biomass_kg,
                "biomass_measurement_method": "direct_weigh",
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + bu[:8]},
    )


async def _post_moisture(client, bu, seq):
    return await client.post(
        "/api/v1/moisture",
        content=json.dumps(
            {
                "reading_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "moisture_percent": 12.0,
                "sequence": seq,
                "sha256_hash": "a" * 64,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": f"m-{bu[:6]}-{seq}"},
    )


async def _post_yield(client, bu):
    return await client.post(
        "/api/v1/yield",
        content=json.dumps(
            {
                "yield_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "wet_yield_weight_kg": 100.0,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": f"y-{bu[:6]}-{uuid.uuid4().hex[:5]}"},
    )


async def _post_telemetry(client, bu):
    return await client.post(
        "/api/v1/telemetry",
        content=json.dumps(
            {
                "telemetry_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "temperature_readings": [650.0] * 60,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": f"t-{bu[:6]}"},
    )


async def _corrupt_first(session_factory, model, bu):
    async with session_factory() as s:
        row = (
            await s.execute(select(model).where(model.batch_uuid == bu))
        ).scalars().first()
        assert row is not None, f"no {model.__name__} row to corrupt"
        row.payload_json = _CORRUPT
        await s.commit()


async def _reasons(session_factory, bu):
    async with session_factory() as s:
        batch = (
            await s.execute(select(Batch).where(Batch.batch_uuid == uuid.UUID(bu)))
        ).scalar_one()
        return json.loads(batch.provisional_reasons or "[]")


async def test_corrupt_moisture_row_is_excluded_not_fatal(
    client, registered_device, session_factory
):
    """A corrupt moisture row must not crash recompute AND must not count as a
    photographed reading."""
    bu = str(uuid.uuid4())
    await _create_batch(client, bu, 500.0)  # needs 10
    for seq in range(1, 11):
        assert (await _post_moisture(client, bu, seq)).status_code == 201
    assert "insufficient_moisture_samples" not in await _reasons(session_factory, bu)

    await _corrupt_first(session_factory, MoistureReading, bu)

    # Re-trigger recompute via a valid yield post — must NOT 500.
    r = await _post_yield(client, bu)
    assert r.status_code == 201, r.text
    # Corrupt row excluded → only 9 valid photographed → the reason returns.
    assert "insufficient_moisture_samples" in await _reasons(session_factory, bu)


async def test_corrupt_telemetry_payload_not_fatal(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)
    assert (await _post_telemetry(client, bu)).status_code == 201
    await _corrupt_first(session_factory, PyrolysisTelemetry, bu)
    # Recompute reads the corrupt telemetry (scalar .get path) — must survive.
    r = await _post_yield(client, bu)
    assert r.status_code == 201, r.text


async def test_corrupt_yield_payload_not_fatal(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)
    assert (await _post_yield(client, bu)).status_code == 201
    await _corrupt_first(session_factory, YieldMetrics, bu)
    # Trigger recompute via moisture — must survive the corrupt yield payload.
    r = await _post_moisture(client, bu, 1)
    assert r.status_code == 201, r.text


async def test_corrupt_provisional_reasons_compliance_still_200(
    client, registered_device, session_factory
):
    """A corrupt provisional_reasons column must not 500 the compliance read."""
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)
    async with session_factory() as s:
        batch = (
            await s.execute(select(Batch).where(Batch.batch_uuid == uuid.UUID(bu)))
        ).scalar_one()
        batch.provisional_reasons = "{ not a list, not valid"
        await s.commit()
    r = await client.get(
        f"/api/v1/batches/{bu}/compliance",
        headers={"X-Admin-Secret": "test-admin-secret"},
    )
    assert r.status_code == 200, r.text
