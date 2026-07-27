"""M3.2 — timeline endpoint tests."""
import json
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
from models import Base, Batch, BatchStageEvent, MediaFile, PyrolysisTelemetry, PortalUser
from portal.auth import hash_password
from server import app
from stage_projection import STAGE_ORDER

pytestmark = pytest.mark.asyncio

_T0 = datetime(2026, 7, 22, 13, 0, 0, tzinfo=timezone.utc)

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


@pytest_asyncio.fixture
async def seeded_batch(tclient) -> str:
    _, Session, _ = tclient
    async with Session() as session:
        b = Batch(
            batch_uuid=str(_uuid.uuid4()),
            operation_id="op-123",
            feedstock_species="Lantana_camara",
            harvest_timestamp=_T0,
            harvest_uptime_seconds=3600,
            moisture_percent=12.0,
            received_at=_T0 + timedelta(hours=4),
            provisional=True,
            provisional_reasons=json.dumps(["min_temp_uncorroborated"]),
            # Fix NOT NULL constraints for other missing fields:
            # Actually, `operation_id` was the only NOT NULL in sqlite error, but let's provide safe defaults if needed.
        )
        session.add(b)
        
        session.add(BatchStageEvent(
            batch_uuid=b.batch_uuid,
            stage="sourcing",
            started_at=_T0,
            ended_at=_T0 + timedelta(hours=1),
            source="projected",
        ))
        
        session.add(BatchStageEvent(
            batch_uuid=b.batch_uuid,
            stage="firing",
            started_at=_T0 + timedelta(hours=1),
            ended_at=None,
            source="device",
        ))
        
        session.add(MediaFile(
            batch_uuid=b.batch_uuid,
            operation_id="op-123",
            filename="pic1.jpg",
            file_path="foo/pic1.jpg",
            sha256_hash="fakehash1",
            capture_type="batch_photo",
            uploaded_at=_T0,
        ))
        session.add(MediaFile(
            batch_uuid=b.batch_uuid,
            operation_id="op-456",
            filename="smoke.jpg",
            file_path="foo/smoke.jpg",
            sha256_hash="fakehash2",
            capture_type="smoke_50",
            uploaded_at=_T0 + timedelta(hours=1, minutes=10),
        ))
        
        session.add(PyrolysisTelemetry(
            batch_uuid=b.batch_uuid,
            telemetry_uuid=str(_uuid.uuid4()),
            payload_json=json.dumps({
                "temperatureReadingsJson": [{"temperature": 350}, {"temperature": 455}]
            }),
            received_at=_T0 + timedelta(hours=1),
        ))
        
        await session.commit()
        return b.batch_uuid

async def test_timeline_endpoint_ordered_and_populated(tclient, seeded_batch):
    """M3.2: Endpoint returns STAGE_ORDER, properly setting state, media, and blocking."""
    client, Session, auth = tclient
    
    resp = await client.get(
        f"/api/v1/portal/batches/{seeded_batch}/timeline",
        headers=auth
    )
    assert resp.status_code == 200
    timeline = resp.json()
    
    assert len(timeline) == len(STAGE_ORDER)
    assert [n["stage"] for n in timeline] == list(STAGE_ORDER)
    
    # Sourcing: done (started/ended), has 1 media (batch_photo)
    sourcing = timeline[0]
    assert sourcing["stage"] == "sourcing"
    assert sourcing["state"] == "done"
    assert sourcing["started_at"] is not None
    assert sourcing["ended_at"] is not None
    assert len(sourcing["media"]) == 1
    assert sourcing["media"][0]["capture_type"] == "batch_photo"
    
    # Firing: active (started, no end), has telemetry_summary, is blocking since min_temp_uncorroborated
    firing = next(n for n in timeline if n["stage"] == "firing")
    assert firing["state"] == "active"
    assert firing["started_at"] is not None
    assert firing["ended_at"] is None
    assert len(firing["media"]) == 1
    assert firing["media"][0]["capture_type"] == "smoke_50"
    
    assert "telemetry_summary" in firing
    assert firing["telemetry_summary"]["max_temp"] == 455
    assert firing["telemetry_summary"]["duration_min"] == 60
    
    # Yield: empty, but since we didn't add missing_post_burn_mass it shouldn't be blocking
    yld = next(n for n in timeline if n["stage"] == "yield")
    assert yld["state"] == "empty"
    assert "blocking" not in yld

async def test_timeline_blocking_reason(tclient):
    """M3.2: An empty stage matches provisional_reasons -> blocking=True."""
    client, Session, auth = tclient
    
    async with Session() as session:
        b = Batch(
            batch_uuid=str(_uuid.uuid4()),
            operation_id="op-empty",
            feedstock_species="Lantana_camara",
            harvest_timestamp=_T0,
            harvest_uptime_seconds=3600,
            moisture_percent=12.0,
            provisional_reasons=json.dumps(["missing_post_burn_mass", "missing_end_use"])
        )
        session.add(b)
        await session.commit()
        buid = b.batch_uuid
        
    resp = await client.get(
        f"/api/v1/portal/batches/{buid}/timeline",
        headers=auth
    )
    assert resp.status_code == 200
    timeline = resp.json()
    
    yld = next(n for n in timeline if n["stage"] == "yield")
    app = next(n for n in timeline if n["stage"] == "application")
    
    assert yld["state"] == "empty"
    assert yld.get("blocking") is True
    
    assert app["state"] == "empty"
    assert app.get("blocking") is True
    
    # Unrelated empty stage should not be blocking
    quench = next(n for n in timeline if n["stage"] == "quenching")
    assert quench["state"] == "empty"
    assert "blocking" not in quench

async def test_timeline_404(tclient):
    client, Session, auth = tclient
    
    resp = await client.get(
        f"/api/v1/portal/batches/{_uuid.uuid4()}/timeline",
        headers=auth
    )
    assert resp.status_code == 404
