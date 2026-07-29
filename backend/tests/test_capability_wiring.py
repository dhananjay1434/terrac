"""H4 - opt-out toggles actually hide timeline and ledgers; default stays visible."""
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from db import get_session
from models import Base, Batch, PortalUser, AppConfig
from portal.auth import hash_password
from server import app

pytestmark = pytest.mark.asyncio
BUID = "bbbb2222-3333-4444-5555-666677778888"


async def _mk(flags):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}",
        connect_args={"check_same_thread": False}, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        s.add(PortalUser(email="a@x.org", password_hash=hash_password("pw-123456789"), role="admin"))
        s.add(Batch(batch_uuid=BUID, operation_id="op-" + uuid.uuid4().hex[:8],
            feedstock_species="Lantana_camara", harvest_timestamp=datetime.now(timezone.utc),
            moisture_percent=12.0, harvest_uptime_seconds=0, biomass_input_kg=100.0))
        if flags is not None:
            s.add(AppConfig(config_id="default", flags_json=json.dumps(flags)))
        await s.commit()
    return engine, Session, path


@pytest_asyncio.fixture
async def make_client():
    created = []

    async def _factory(flags):
        engine, Session, path = await _mk(flags)

        async def _ov():
            async with Session() as s:
                yield s
        app.dependency_overrides[get_session] = _ov
        ac = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        await ac.__aenter__()
        tok = (await ac.post("/api/v1/portal/login",
            json={"email": "a@x.org", "password": "pw-123456789"})).json()["token"]
        created.append((ac, engine, path))
        return ac, {"Authorization": f"Bearer {tok}"}

    yield _factory
    app.dependency_overrides.pop(get_session, None)
    for ac, engine, path in created:
        await ac.__aexit__(None, None, None)
        await engine.dispose()
        try:
            os.remove(path)
        except OSError:
            pass


async def test_timeline_visible_by_default(make_client):
    ac, auth = await make_client(None)
    r = await ac.get(f"/api/v1/portal/batches/{BUID}/timeline", headers=auth)
    assert r.status_code == 200 and len(r.json()) > 0   # opt-out default ON


async def test_timeline_hidden_when_off(make_client):
    ac, auth = await make_client({"ff.timeline_v2": "off"})
    r = await ac.get(f"/api/v1/portal/batches/{BUID}/timeline", headers=auth)
    assert r.status_code == 200 and r.json() == []      # client turned it off


async def test_ledger_visible_by_default(make_client):
    ac, auth = await make_client(None)
    r = await ac.get("/api/v1/portal/ledgers/biomass?bucket=month", headers=auth)
    assert r.status_code == 200 and r.json()["totals"]["total_kg"] == 100.0


async def test_ledger_hidden_when_off(make_client):
    ac, auth = await make_client({"ff.ledgers_v2": "off"})
    r = await ac.get("/api/v1/portal/ledgers/biomass?bucket=month", headers=auth)
    assert r.status_code == 200 and r.json()["totals"]["total_kg"] == 0.0
