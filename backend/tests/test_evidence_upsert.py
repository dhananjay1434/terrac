"""Regression — one-to-one evidence corrections are upserted, not dropped.

telemetry / yield / application each have BOTH `<x>_uuid` and `batch_uuid`
UNIQUE. A resubmission for the same batch under a NEW `<x>_uuid` is a correction;
pre-fix it collided on `batch_uuid` and was silently returned as `duplicate`,
so the batch kept the first (stale/attacker) value and the real one was lost.
Now the existing row is updated in place and the credit re-derives.

A retry under the SAME `<x>_uuid` is still a genuine idempotent no-op.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import Batch, EndUseApplication, PyrolysisTelemetry, YieldMetrics
from tests.remediation.crypto_utils import sign_request

pytestmark = pytest.mark.asyncio

OWNER = "test-device-reg"


async def _post(client, path, op, payload):
    return await client.post(
        path,
        content=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Idempotency-Key": op,
            "X-Device-Id": OWNER,
            "X-Signature": sign_request(OWNER, "", "POST", path, op, payload),
        },
    )


async def _create_batch(client, bu):
    payload = {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
    }
    r = await _post(client, "/api/v1/batches", "b-" + bu[:8], payload)
    assert r.status_code == 201, r.text


async def _row_count(session_factory, model, bu):
    async with session_factory() as s:
        rows = (
            (await s.execute(select(model).where(model.batch_uuid == bu)))
            .scalars()
            .all()
        )
        return rows


async def test_same_uuid_retry_is_duplicate(client, registered_device):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)
    tuid = str(uuid.uuid4())
    p = {"telemetry_uuid": tuid, "batch_uuid": bu, "max_temp": 500.0}
    r1 = await _post(client, "/api/v1/telemetry", "t1", p)
    assert r1.status_code == 201 and r1.json()["duplicate"] is False
    # Identical record again -> genuine idempotent no-op.
    r2 = await _post(client, "/api/v1/telemetry", "t2", p)
    assert r2.status_code == 201, r2.text
    assert r2.json().get("duplicate") is True
    assert r2.json().get("updated") is None


async def test_correction_upserts_and_does_not_duplicate_rows(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)

    # First application record for this batch.
    p1 = {"application_uuid": str(uuid.uuid4()), "batch_uuid": bu, "latitude": 1.0}
    assert (await _post(client, "/api/v1/application", "a1", p1)).status_code == 201

    # Correction under a NEW application_uuid, same batch.
    p2 = {"application_uuid": str(uuid.uuid4()), "batch_uuid": bu, "latitude": 2.0}
    r = await _post(client, "/api/v1/application", "a2", p2)
    assert r.status_code == 201, r.text
    assert r.json().get("updated") is True  # not silently dropped

    # Exactly ONE row survives, carrying the corrected value.
    rows = await _row_count(session_factory, EndUseApplication, bu)
    assert len(rows) == 1
    assert json.loads(rows[0].payload_json)["latitude"] == 2.0
    assert rows[0].application_uuid == p2["application_uuid"]


async def test_yield_correction_re_derives_the_credit(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)

    async def _wet_yield():
        async with session_factory() as s:
            b = (
                await s.execute(select(Batch).where(Batch.batch_uuid == uuid.UUID(bu)))
            ).scalar_one()
            return b.wet_yield_kg

    # Initial (understated) yield.
    p1 = {
        "yield_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "wet_yield_weight_kg": 100.0,
    }
    assert (await _post(client, "/api/v1/yield", "y1", p1)).status_code == 201
    assert await _wet_yield() == 100.0

    # Corrected yield under a new yield_uuid — must overwrite, not be dropped.
    p2 = {
        "yield_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "wet_yield_weight_kg": 250.0,
    }
    r = await _post(client, "/api/v1/yield", "y2", p2)
    assert r.status_code == 201 and r.json().get("updated") is True
    # The corroborated credit input now reflects the correction (pre-fix: still 100).
    assert await _wet_yield() == 250.0

    rows = await _row_count(session_factory, YieldMetrics, bu)
    assert len(rows) == 1
    assert rows[0].yield_uuid == p2["yield_uuid"]


async def test_telemetry_correction_upserts(client, registered_device, session_factory):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)
    p1 = {"telemetry_uuid": str(uuid.uuid4()), "batch_uuid": bu, "max_temp": 400.0}
    assert (await _post(client, "/api/v1/telemetry", "t1", p1)).status_code == 201
    p2 = {"telemetry_uuid": str(uuid.uuid4()), "batch_uuid": bu, "max_temp": 650.0}
    r = await _post(client, "/api/v1/telemetry", "t2", p2)
    assert r.status_code == 201 and r.json().get("updated") is True
    rows = await _row_count(session_factory, PyrolysisTelemetry, bu)
    assert len(rows) == 1
    assert json.loads(rows[0].payload_json)["max_temp"] == 650.0
