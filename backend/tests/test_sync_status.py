"""S4 / STITCHING D3b — sync-status returns the max stored seq per (session, channel)."""
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from models import PortalUser, TelemetryChunk
from portal.auth import hash_password

pytestmark = pytest.mark.asyncio

DEVICE = "edge-sync-1"


@pytest_asyncio.fixture
async def auth(client, session_factory):
    async with session_factory() as s:
        s.add(PortalUser(
            email="sync@x.org", password_hash=hash_password("pw-123456789"), role="admin",
        ))
        await s.commit()
    token = (await client.post(
        "/api/v1/portal/login",
        json={"email": "sync@x.org", "password": "pw-123456789"},
    )).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _chunk(seq, channel="T1", session="sess-1"):
    return TelemetryChunk(
        batch_uuid=None,
        device_id=DEVICE,
        channel=channel,
        t_start=datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc),
        t_end=datetime(2026, 7, 23, 9, 10, tzinfo=timezone.utc),
        sample_period_s=10.0,
        session_uuid=session,
        seq=seq,
        prev_hash=None,
        payload_json='{"values":[400.0]}',
        signature="sig-" + uuid.uuid4().hex[:8],
    )


async def test_watermark_is_max_seq_per_channel(client, session_factory, auth):
    async with session_factory() as s:
        s.add(_chunk(0)); s.add(_chunk(1)); s.add(_chunk(2))
        s.add(_chunk(0, channel="T2"))
        await s.commit()
    r = await client.get(f"/api/v2/telemetry/sync-status/{DEVICE}", headers=auth)
    assert r.status_code == 200, r.text
    marks = {(w["session_uuid"], w["channel"]): w["max_seq"] for w in r.json()["watermarks"]}
    assert marks[("sess-1", "T1")] == 2
    assert marks[("sess-1", "T2")] == 0


async def test_unknown_device_is_empty_not_error(client, auth):
    r = await client.get("/api/v2/telemetry/sync-status/does-not-exist", headers=auth)
    assert r.status_code == 200
    assert r.json() == {"device_id": "does-not-exist", "watermarks": []}


async def test_seqless_chunks_ignored(client, session_factory, auth):
    async with session_factory() as s:
        s.add(_chunk(None, session="sess-legacy"))
        await s.commit()
    r = await client.get(f"/api/v2/telemetry/sync-status/{DEVICE}", headers=auth)
    assert all(w["session_uuid"] != "sess-legacy" for w in r.json()["watermarks"])
