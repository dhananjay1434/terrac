import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from models import Batch, TelemetryPoint, BurnSession, TelemetryChunk, AuditEvent

pytestmark = pytest.mark.asyncio

BUID = "bbbb1111-2222-3333-4444-555566667777"
SESSION_UUID = str(uuid.uuid4())


@pytest.fixture
def admin_headers():
    from settings import _ADMIN_SECRET
    return {"X-Admin-Secret": _ADMIN_SECRET}


def _body(session_id: str, batch_id: str | None = None, **over) -> bytes:
    from tests.conftest import _ed25519_sign
    b = {
        "device_id": "test-device-reg",
        "session_uuid": session_id,
        "batch_uuid": batch_id,
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


async def test_session_binding_flow(client, registered_device, session_factory, admin_headers):
    await _seed_batch(session_factory)
    
    # 1. Ingest telemetry without a batch_uuid (orphaned session)
    r = await client.post("/api/v2/telemetry/ingest", content=_body(SESSION_UUID, batch_id=None))
    assert r.status_code == 200, r.text
    assert r.json() == {"status": "ok", "points": 0}

    # Verify session is created but unbound
    async with session_factory() as s:
        burn = (await s.execute(select(BurnSession).where(BurnSession.session_uuid == SESSION_UUID))).scalar_one()
        assert burn.batch_uuid is None
        assert burn.binding_source is None

        # Verify chunk exists but is unbound
        chunk = (await s.execute(select(TelemetryChunk).where(TelemetryChunk.session_uuid == SESSION_UUID))).scalar_one()
        assert chunk.batch_uuid is None
        
        # Verify NO points were inserted
        n_points = (await s.execute(select(func.count()).select_from(TelemetryPoint))).scalar_one()
        assert n_points == 0

    # 2. Bind session to batch
    bind_r = await client.post(
        f"/api/v2/telemetry/sessions/{SESSION_UUID}/bind",
        json={"batch_uuid": BUID},
        headers=admin_headers
    )
    assert bind_r.status_code == 200, bind_r.text
    assert bind_r.json() == {"status": "ok", "points_inserted": 3}
    
    # Verify DB state
    async with session_factory() as s:
        burn = (await s.execute(select(BurnSession).where(BurnSession.session_uuid == SESSION_UUID))).scalar_one()
        assert burn.batch_uuid == BUID
        assert burn.binding_source == "admin"
        assert burn.bound_by == "admin"
        assert burn.bound_at is not None

        chunk = (await s.execute(select(TelemetryChunk).where(TelemetryChunk.session_uuid == SESSION_UUID))).scalar_one()
        assert chunk.batch_uuid == BUID
        
        n_points = (await s.execute(select(func.count()).select_from(TelemetryPoint))).scalar_one()
        assert n_points == 3
        
        audit = (await s.execute(select(AuditEvent).where(AuditEvent.event_type == "session_bound"))).scalar_one()
        assert audit.batch_uuid == BUID
        assert json.loads(audit.payload_json)["session_uuid"] == SESSION_UUID

    # 3. Idempotency - calling again shouldn't fail
    bind_r2 = await client.post(
        f"/api/v2/telemetry/sessions/{SESSION_UUID}/bind",
        json={"batch_uuid": BUID},
        headers=admin_headers
    )
    assert bind_r2.status_code == 200
    assert bind_r2.json() == {"status": "ok", "points_inserted": 0, "message": "already_bound"}

async def test_session_binding_not_found(client, admin_headers):
    bind_r = await client.post(
        f"/api/v2/telemetry/sessions/{str(uuid.uuid4())}/bind",
        json={"batch_uuid": BUID},
        headers=admin_headers
    )
    assert bind_r.status_code == 404
    assert bind_r.json()["detail"] == "session_not_found"

async def test_session_binding_batch_not_found(client, registered_device, session_factory, admin_headers):
    # create session
    s_uuid = str(uuid.uuid4())
    r = await client.post("/api/v2/telemetry/ingest", content=_body(s_uuid, batch_id=None))
    assert r.status_code == 200

    bind_r = await client.post(
        f"/api/v2/telemetry/sessions/{s_uuid}/bind",
        json={"batch_uuid": str(uuid.uuid4())},
        headers=admin_headers
    )
    assert bind_r.status_code == 404
    assert bind_r.json()["detail"] == "batch_not_found"
