"""M5.1 — portal ledger API tests."""
import os
import tempfile
import uuid as _uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from db import get_session
from models import Base, Batch, PortalUser
from portal.auth import hash_password
from server import app

pytestmark = pytest.mark.asyncio

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
        s.add(PortalUser(email="admin@x.org", password_hash=hash_password("admin-pw"), role="admin"))
        await s.commit()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            token = (
                await ac.post("/api/v1/portal/login", json={"email": "admin@x.org", "password": "admin-pw"})
            ).json()["token"]
            yield ac, Session, {"Authorization": f"Bearer {token}"}
    finally:
        app.dependency_overrides.pop(get_session, None)
        await engine.dispose()
        try:
            os.remove(path)
        except OSError:
            pass


def _mk_batch(code, site, net, dt, species, kg):
    return Batch(
        batch_uuid=str(_uuid.uuid4()),
        operation_id=f"op-{_uuid.uuid4().hex[:8]}",
        batch_code=code,
        site_id=site,
        network_id=net,
        harvest_timestamp=dt,
        feedstock_species=species,
        biomass_input_kg=kg,
        moisture_percent=12.0,
        harvest_uptime_seconds=100,
        status="RECEIVED",
        provisional=False,
    )

async def test_biomass_ledger_month_bucket(tclient):
    ac, Session, headers = tclient
    
    async with Session() as s:
        b1 = _mk_batch("B1", "site-1", "net-1", datetime(2026, 7, 10, tzinfo=timezone.utc), "Prosopis", 100.0)
        b2 = _mk_batch("B2", "site-1", "net-1", datetime(2026, 7, 15, tzinfo=timezone.utc), "Lantana", 50.0)
        b3 = _mk_batch("B3", "site-2", "net-2", datetime(2026, 8, 5, tzinfo=timezone.utc), "Prosopis", 200.0)
        s.add_all([b1, b2, b3])
        await s.commit()

    res = await ac.get(
        "/api/v1/portal/ledgers/biomass?bucket=month",
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["bucket"] == "month"
    
    assert data["totals"]["total_kg"] == 350.0
    assert data["totals"]["by_species"]["Prosopis"] == 300.0
    assert data["totals"]["by_species"]["Lantana"] == 50.0
    
    buckets = data["buckets"]
    assert len(buckets) == 2
    assert buckets[0]["period"] == "2026-07"
    assert buckets[0]["total_kg"] == 150.0
    
    assert buckets[1]["period"] == "2026-08"
    assert buckets[1]["total_kg"] == 200.0


async def test_biomass_ledger_filters(tclient):
    ac, Session, headers = tclient
    
    async with Session() as s:
        b1 = _mk_batch("B4", "site-1", "net-1", datetime(2026, 7, 10, tzinfo=timezone.utc), "Prosopis", 100.0)
        s.add(b1)
        await s.commit()

    res = await ac.get(
        "/api/v1/portal/ledgers/biomass?site_id=site-99",
        headers=headers
    )
    assert res.status_code == 200
    assert res.json()["totals"]["total_kg"] == 0.0

    res = await ac.get(
        "/api/v1/portal/ledgers/biomass?from=2026-08-01T00:00:00",
        headers=headers
    )
    assert res.status_code == 200
    assert res.json()["totals"]["total_kg"] == 0.0
