"""S5 / STITCHING Phase H — list burn sessions that still need a batch bound."""
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio

from models import PortalUser, BurnSession, TelemetryChunk
from portal.auth import hash_password

pytestmark = pytest.mark.asyncio

T0 = datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def auth(client, session_factory):
    async with session_factory() as s:
        s.add(PortalUser(
            email="unbound@x.org", password_hash=hash_password("pw-123456789"), role="admin",
        ))
        await s.commit()
    token = (await client.post(
        "/api/v1/portal/login",
        json={"email": "unbound@x.org", "password": "pw-123456789"},
    )).json()["token"]
    return {"Authorization": f"Bearer {token}"}


async def test_lists_only_unbound_oldest_first(client, session_factory, auth):
    async with session_factory() as s:
        s.add(BurnSession(session_uuid="s-late", device_id="d1", started_at=T0 + timedelta(hours=2)))
        s.add(BurnSession(session_uuid="s-early", device_id="d1", started_at=T0))
        s.add(BurnSession(
            session_uuid="s-bound", device_id="d1", started_at=T0 + timedelta(hours=1),
            batch_uuid="already-bound",
        ))
        await s.commit()
    r = await client.get("/api/v2/telemetry/unbound-sessions", headers=auth)
    assert r.status_code == 200, r.text
    ids = [x["session_uuid"] for x in r.json()["unbound_sessions"]]
    assert ids == ["s-early", "s-late"]          # oldest first, bound one excluded


async def test_chunk_count_reported(client, session_factory, auth):
    async with session_factory() as s:
        s.add(BurnSession(session_uuid="s-cc", device_id="d1", started_at=T0))
        for _ in range(3):
            s.add(TelemetryChunk(
                batch_uuid=None, device_id="d1", channel="T1", t_start=T0, t_end=T0,
                sample_period_s=10.0, session_uuid="s-cc", seq=None, prev_hash=None,
                payload_json='{"values":[1.0]}', signature="sig-" + uuid.uuid4().hex[:8],
            ))
        await s.commit()
    r = await client.get("/api/v2/telemetry/unbound-sessions", headers=auth)
    row = [x for x in r.json()["unbound_sessions"] if x["session_uuid"] == "s-cc"][0]
    assert row["chunk_count"] == 3


async def test_empty_when_nothing_unbound(client, auth):
    r = await client.get("/api/v2/telemetry/unbound-sessions", headers=auth)
    assert r.status_code == 200
    assert r.json() == {"unbound_sessions": []}
