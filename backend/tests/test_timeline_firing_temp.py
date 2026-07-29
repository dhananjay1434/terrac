"""H1 - timeline firing max-temp reads the real temperature_readings key."""
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
from models import Base, Batch, PyrolysisTelemetry, PortalUser
from portal.auth import hash_password
from server import app

pytestmark = pytest.mark.asyncio
BUID = "aaaa1111-2222-3333-4444-555566667777"


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
        s.add(Batch(batch_uuid=BUID, operation_id="op-"+uuid.uuid4().hex[:8],
            feedstock_species="Lantana_camara", harvest_timestamp=datetime.now(timezone.utc),
            moisture_percent=12.0, harvest_uptime_seconds=3600))
        s.add(PyrolysisTelemetry(telemetry_uuid=str(uuid.uuid4()), batch_uuid=BUID,
            payload_json=json.dumps({"temperature_readings": [420.0, 690.5, 510.0]})))
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


async def test_firing_node_has_real_max_temp(tclient):
    ac, auth = tclient
    r = await ac.get(f"/api/v1/portal/batches/{BUID}/timeline", headers=auth)
    assert r.status_code == 200, r.text
    firing = [n for n in r.json() if n["stage"] == "firing"]
    assert firing, "timeline must include a firing stage"
    summary = firing[0].get("telemetry_summary")
    assert summary is not None, "firing node must carry a telemetry summary when telemetry exists"
    assert summary["max_temp"] == 690.5, "max_temp must come from temperature_readings, not be null"
