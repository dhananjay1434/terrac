"""M2.2 - signed /api/v2/telemetry/ingest: happy path, idempotent duplicate,
validation (channel/oversize/future), unsigned rejection."""
import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from models import Batch, TelemetryPoint

pytestmark = pytest.mark.asyncio

BUID = "aaaa1111-2222-3333-4444-555566667777"


def _body(**over) -> bytes:
    from tests.conftest import _ed25519_sign
    b = {
        "device_id": "test-device-reg",
        "session_uuid": str(uuid.uuid4()),
        "batch_uuid": BUID,
        "channel": "T1",
        "t_start": "2026-07-23T09:00:00Z",
        "sample_period_s": 10.0,
        "values": [400.0, 410.0, 420.0],
        "seq": 0,
        "prev_hash": None,
    }
    b.update(over)
    if "producer_signature" not in b:
        canonical = json.dumps(b, separators=(",", ":"), sort_keys=True).encode("utf-8")
        b["producer_signature"] = _ed25519_sign(canonical)
    return json.dumps(b).encode("utf-8")


async def _seed_batch(session_factory):
    async with session_factory() as s:
        s.add(Batch(
            batch_uuid=BUID,
            operation_id="op-" + uuid.uuid4().hex[:8],
            feedstock_species="Lantana_camara",
            harvest_timestamp=datetime.now(timezone.utc),
            moisture_percent=12.0,
            harvest_uptime_seconds=0,
        ))
        await s.commit()


async def test_signed_ingest_happy_path(client, registered_device, session_factory):
    await _seed_batch(session_factory)
    r = await client.post("/api/v2/telemetry/ingest", content=_body())
    assert r.status_code == 200, r.text
    assert r.json() == {"status": "ok", "points": 3}


async def test_duplicate_chunk_not_doubled(client, registered_device, session_factory):
    await _seed_batch(session_factory)
    body = _body()
    assert (await client.post("/api/v2/telemetry/ingest", content=body)).json()["points"] == 3
    r2 = await client.post("/api/v2/telemetry/ingest", content=body)
    assert r2.json() == {"status": "duplicate"}
    async with session_factory() as s:
        n = (await s.execute(select(func.count()).select_from(TelemetryPoint))).scalar_one()
    assert n == 3  # not doubled


async def test_bad_channel_422(client, registered_device, session_factory):
    await _seed_batch(session_factory)
    r = await client.post("/api/v2/telemetry/ingest", content=_body(channel="XX"))
    assert r.status_code == 422


async def test_oversize_values_422(client, registered_device, session_factory):
    await _seed_batch(session_factory)
    r = await client.post("/api/v2/telemetry/ingest", content=_body(values=[1.0] * 721))
    assert r.status_code == 422


async def test_future_t_start_422(client, registered_device, session_factory):
    await _seed_batch(session_factory)
    r = await client.post("/api/v2/telemetry/ingest", content=_body(t_start="2099-01-01T00:00:00Z"))
    assert r.status_code == 422


async def test_unsigned_rejected(client, session_factory):
    await _seed_batch(session_factory)
    # both headers present -> SignedAsyncClient does NOT auto-sign; bad sig -> reject
    r = await client.post(
        "/api/v2/telemetry/ingest",
        content=_body(),
        headers={"X-Device-Id": "nope", "X-Signature": "bad"},
    )
    assert r.status_code in (401, 403)



async def test_unbound_duplicate_chunk_is_idempotent(client, registered_device, session_factory):
    """F2 — an UNBOUND chunk (batch_uuid=None) must still be deduplicated.

    Before the fix the UNIQUE included the nullable batch_uuid, and NULL != NULL
    meant retries inserted duplicate rows forever.
    """
    from sqlalchemy import func, select
    from models import TelemetryChunk

    body = _body(batch_uuid=None)
    first = await client.post("/api/v2/telemetry/ingest", content=body)
    assert first.status_code == 200, first.text

    second = await client.post("/api/v2/telemetry/ingest", content=body)
    assert second.json() == {"status": "duplicate"}

    async with session_factory() as s:
        n = (await s.execute(select(func.count()).select_from(TelemetryChunk))).scalar_one()
    assert n == 1, f"expected 1 chunk after a retried upload, found {n}"
