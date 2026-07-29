"""H5 - the capability descriptor endpoint returns the resolver's verdict."""
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
from models import Base, Batch, PortalUser
from portal.auth import hash_password
from server import app

pytestmark = pytest.mark.asyncio
BUID = "cccc3333-4444-5555-6666-777788889999"


@pytest_asyncio.fixture
async def tclient():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}",
        connect_args={"check_same_thread": False}, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def _ov():
        async with Session() as s:
            yield s
    app.dependency_overrides[get_session] = _ov
    async with Session() as s:
        s.add(PortalUser(email="a@x.org", password_hash=hash_password("pw-123456789"), role="admin"))
        s.add(Batch(batch_uuid=BUID, operation_id="op-" + uuid.uuid4().hex[:8],
            feedstock_species="Lantana_camara", harvest_timestamp=datetime.now(timezone.utc),
            moisture_percent=12.0, harvest_uptime_seconds=0))
        await s.commit()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            tok = (await ac.post("/api/v1/portal/login",
                json={"email": "a@x.org", "password": "pw-123456789"})).json()["token"]
            yield ac, {"Authorization": f"Bearer {tok}"}
    finally:
        app.dependency_overrides.pop(get_session, None)
        await engine.dispose()
        try: os.remove(path)
        except OSError: pass


async def test_descriptor_shape_for_bare_batch(tclient):
    ac, auth = tclient
    r = await ac.get(f"/api/v1/portal/batches/{BUID}/capabilities", headers=auth)
    assert r.status_code == 200, r.text
    caps = r.json()
    for key in ("telemetry", "thermal", "load", "timeline", "ledgers", "provenance_code", "tier"):
        assert key in caps
    assert caps["telemetry"] == "none" and caps["tier"] == "none"
    assert caps["timeline"] is True   # opt-out default ON


async def test_descriptor_unknown_batch_404(tclient):
    ac, auth = tclient
    r = await ac.get(f"/api/v1/portal/batches/{uuid.uuid4()}/capabilities", headers=auth)
    assert r.status_code == 404
