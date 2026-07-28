"""G2 — session binding uses portal RBAC and records the real actor."""
import os
import tempfile
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from db import get_session
from models import Base, Batch, BurnSession, PortalUser
from portal.auth import hash_password
from server import app

pytestmark = pytest.mark.asyncio

BUID = "cccc1111-2222-3333-4444-555566667777"
SUID = "session-abc-123"


@pytest_asyncio.fixture
async def bind_client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{path}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def _override():
        async with Session() as s:
            yield s

    app.dependency_overrides[get_session] = _override
    async with Session() as s:
        s.add(PortalUser(
            email="boss@x.org", password_hash=hash_password("pw-admin-12345"), role="admin",
        ))
        s.add(Batch(
            batch_uuid=BUID,
            operation_id="op-" + uuid.uuid4().hex[:8],
            feedstock_species="Lantana_camara",
            harvest_timestamp=datetime.now(timezone.utc),
            moisture_percent=12.0,
            harvest_uptime_seconds=0,
        ))
        s.add(BurnSession(
            session_uuid=SUID,
            device_id="dev-1",
            started_at=datetime.now(timezone.utc),
        ))
        await s.commit()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            token = (await ac.post(
                "/api/v1/portal/login",
                json={"email": "boss@x.org", "password": "pw-admin-12345"},
            )).json()["token"]
            yield ac, Session, {"Authorization": f"Bearer {token}"}
    finally:
        app.dependency_overrides.pop(get_session, None)
        await engine.dispose()
        try:
            os.remove(path)
        except OSError:
            pass


async def test_bind_requires_auth(bind_client):
    ac, _S, _auth = bind_client
    r = await ac.post(f"/api/v2/telemetry/sessions/{SUID}/bind", json={"batch_uuid": BUID})
    assert r.status_code in (401, 403)


async def test_bind_records_real_user_email(bind_client):
    ac, Session, auth = bind_client
    r = await ac.post(
        f"/api/v2/telemetry/sessions/{SUID}/bind",
        json={"batch_uuid": BUID},
        headers=auth,
    )
    assert r.status_code == 200, r.text
    async with Session() as s:
        bs = (await s.execute(
            select(BurnSession).where(BurnSession.session_uuid == SUID)
        )).scalar_one()
    assert bs.batch_uuid == BUID
    assert bs.bound_by == "boss@x.org", "must record the real actor, not 'admin'"
    assert bs.binding_source == "admin"


async def test_bind_skips_corrupt_chunk_and_still_binds(bind_client):
    """G3 - one unparseable chunk must not abort the whole bind."""
    import json as _json
    from datetime import datetime as _dt, timezone as _tz
    from models import TelemetryChunk

    ac, Session, auth = bind_client
    t0 = _dt(2026, 7, 23, 9, 0, tzinfo=_tz.utc)
    async with Session() as s:
        s.add(TelemetryChunk(
            session_uuid=SUID, batch_uuid=None, device_id="dev-1", channel="T1",
            t_start=t0, t_end=t0, sample_period_s=10.0,
            payload_json=_json.dumps({"values": [400.0, 410.0]}), signature="sig-good",
        ))
        s.add(TelemetryChunk(
            session_uuid=SUID, batch_uuid=None, device_id="dev-1", channel="T2",
            t_start=t0, t_end=t0, sample_period_s=10.0,
            payload_json="{not valid json", signature="sig-bad",
        ))
        await s.commit()

    r = await ac.post(
        f"/api/v2/telemetry/sessions/{SUID}/bind",
        json={"batch_uuid": BUID},
        headers=auth,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["points_inserted"] == 2, "good chunk must still replay"
    assert body["skipped_chunks"] == 1, "corrupt chunk must be counted, not fatal"
