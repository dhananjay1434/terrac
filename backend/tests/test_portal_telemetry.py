"""M2.3 read API + M2.4 SSE shell — portal telemetry routes.

Read API: epoch-ms points per channel, min/max, gap detection, 1m rollup,
channel filter, tier-aware empty response. SSE endpoints: smoke tests only
(audit A8 — the pub/sub + ticket logic is fully unit-tested in
test_telemetry_bus.py; here we prove mint→200 and no-ticket→401)."""
import os
import tempfile
import uuid as _uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from db import get_session
from models import Base, Batch, PortalUser, TelemetryPoint
from portal.auth import hash_password
from server import app

pytestmark = pytest.mark.asyncio

_T0 = datetime(2026, 7, 22, 13, 0, 0, tzinfo=timezone.utc)


def _batch() -> Batch:
    return Batch(
        batch_uuid=str(_uuid.uuid4()),
        operation_id=f"op-{_uuid.uuid4().hex[:8]}",
        feedstock_species="Lantana_camara",
        harvest_timestamp=_T0,
        moisture_percent=12.0,
        harvest_uptime_seconds=100,
        device_id="edge-1",
        received_at=_T0,
    )


def _points(batch_uuid: str, channel: str, n: int, *, start=_T0, period_s=10, base=400.0):
    return [
        TelemetryPoint(
            batch_uuid=batch_uuid,
            channel=channel,
            ts=start + timedelta(seconds=period_s * i),
            value=base + i,
        )
        for i in range(n)
    ]


@pytest_asyncio.fixture
async def tclient():
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
        s.add(PortalUser(email="v@x.org", password_hash=hash_password("pw-verifier-1"), role="verifier"))
        await s.commit()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            token = (
                await ac.post("/api/v1/portal/login", json={"email": "v@x.org", "password": "pw-verifier-1"})
            ).json()["token"]
            yield ac, Session, {"Authorization": f"Bearer {token}"}
    finally:
        app.dependency_overrides.pop(get_session, None)
        await engine.dispose()
        try:
            os.remove(path)
        except OSError:
            pass


async def _seed(Session, *, channels=("T1", "T2"), n=12) -> str:
    async with Session() as s:
        b = _batch()
        s.add(b)
        for c in channels:
            for p in _points(b.batch_uuid, c, n):
                s.add(p)
        await s.commit()
        return b.batch_uuid


async def test_read_returns_epoch_ms_points_min_max(tclient):
    ac, Session, hdrs = tclient
    uuid = await _seed(Session, channels=("T1",), n=6)
    r = await ac.get(f"/api/v1/portal/batches/{uuid}/telemetry2", headers=hdrs)
    assert r.status_code == 200
    body = r.json()
    t1 = body["channels"]["T1"]
    assert len(t1["points"]) == 6
    ts0, v0 = t1["points"][0]
    assert ts0 == int(_T0.timestamp() * 1000)  # epoch ms
    assert v0 == 400.0
    assert t1["max"] == 405.0 and t1["min"] == 400.0
    assert body["burn"]["t_start"] == ts0
    assert body["burn"]["gaps"] == []


async def test_channel_filter_and_unknown_channel_422(tclient):
    ac, Session, hdrs = tclient
    uuid = await _seed(Session, channels=("T1", "LOAD"))
    r = await ac.get(f"/api/v1/portal/batches/{uuid}/telemetry2?channels=LOAD", headers=hdrs)
    assert set(r.json()["channels"].keys()) == {"LOAD"}
    r = await ac.get(f"/api/v1/portal/batches/{uuid}/telemetry2?channels=T9", headers=hdrs)
    assert r.status_code == 422


async def test_gap_detected_never_interpolated(tclient):
    ac, Session, hdrs = tclient
    async with Session() as s:
        b = _batch()
        s.add(b)
        for p in _points(b.batch_uuid, "T1", 3):
            s.add(p)
        # resume 10 minutes later — a hole far beyond the 60 s threshold
        for p in _points(b.batch_uuid, "T1", 3, start=_T0 + timedelta(minutes=10)):
            s.add(p)
        await s.commit()
        uuid = b.batch_uuid
    body = (await ac.get(f"/api/v1/portal/batches/{uuid}/telemetry2", headers=hdrs)).json()
    assert len(body["channels"]["T1"]["points"]) == 6  # no synthetic fill
    assert len(body["burn"]["gaps"]) == 1


async def test_minute_rollup_means(tclient):
    ac, Session, hdrs = tclient
    uuid = await _seed(Session, channels=("T1",), n=12)  # 2 minutes @10s
    body = (
        await ac.get(f"/api/v1/portal/batches/{uuid}/telemetry2?res=1m", headers=hdrs)
    ).json()
    pts = body["channels"]["T1"]["points"]
    assert len(pts) == 2
    assert pts[0][1] == pytest.approx(402.5)  # mean of 400..405
    assert pts[1][1] == pytest.approx(408.5)  # mean of 406..411


async def test_tier0_batch_empty_channels(tclient):
    ac, Session, hdrs = tclient
    async with Session() as s:
        b = _batch()
        s.add(b)
        await s.commit()
        uuid = b.batch_uuid
    body = (await ac.get(f"/api/v1/portal/batches/{uuid}/telemetry2", headers=hdrs)).json()
    assert body["channels"] == {}  # graceful: no channels, no error


async def test_read_requires_auth_and_known_batch(tclient):
    ac, Session, hdrs = tclient
    uuid = await _seed(Session)
    assert (await ac.get(f"/api/v1/portal/batches/{uuid}/telemetry2")).status_code in (401, 403)
    assert (
        await ac.get(f"/api/v1/portal/batches/{_uuid.uuid4()}/telemetry2", headers=hdrs)
    ).status_code == 404


# ── M2.4 smoke (bus logic fully covered in test_telemetry_bus.py) ───────────
async def test_ticket_mint_and_stream_auth(tclient):
    ac, Session, hdrs = tclient
    uuid = await _seed(Session)
    r = await ac.post(f"/api/v1/portal/streams/burn/{uuid}/ticket", headers=hdrs)
    assert r.status_code == 200
    body = r.json()
    assert body["expires_in"] == 60 and len(body["ticket"]) > 20
    # stream without a ticket → 422 (missing param) / with a bogus ticket → 401
    r = await ac.get(f"/api/v1/portal/streams/burn/{uuid}?ticket=bogus")
    assert r.status_code == 401
    # ticket mint requires auth
    assert (await ac.post(f"/api/v1/portal/streams/burn/{uuid}/ticket")).status_code in (401, 403)
