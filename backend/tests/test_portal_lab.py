import uuid as _uuid
"""P2.4 — portal lab flow. The session-authed portal lab-results endpoint must
trigger the SAME recompute as the legacy X-Admin-Secret channel (identical batch
state), and be gated to the lab/admin roles (verifier -> 403)."""

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
from models import Base, Batch, PortalUser
from portal.auth import hash_password
from server import app

pytestmark = pytest.mark.asyncio

_ADMIN = os.environ.get("DMRV_ADMIN_SECRET", "test-admin-secret")
_LAB = {
    "lab_h_corg": 0.5,
    "organic_carbon_pct": 0.6,
    "biochar_moisture_samples": [8.0, 9.0, 10.0],
    "dry_bulk_density": 400.0,
}


def _mk_batch():
    return Batch(
        batch_uuid=str(_uuid.uuid4()),
        operation_id=f"op-{_uuid.uuid4().hex[:8]}",
        feedstock_species="Lantana_camara",
        harvest_timestamp=datetime(2026, 7, 1, tzinfo=timezone.utc),
        moisture_percent=12.0,
        harvest_uptime_seconds=100,
    )


@pytest_asyncio.fixture
async def lab_env():
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
        for email, role in [("lab@x.org", "lab"), ("ver@x.org", "verifier")]:
            s.add(
                PortalUser(
                    email=email, password_hash=hash_password("pw-12345"), role=role
                )
            )
        await s.commit()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac, Session
    finally:
        app.dependency_overrides.pop(get_session, None)
        await engine.dispose()
        try:
            os.remove(path)
        except OSError:
            pass


async def _token(ac, email):
    return (
        await ac.post(
            "/api/v1/portal/login", json={"email": email, "password": "pw-12345"}
        )
    ).json()["token"]


async def _state(Session, buid):
    from sqlalchemy import select

    async with Session() as s:
        b = (
            await s.execute(select(Batch).where(Batch.batch_uuid == buid))
        ).scalar_one()
        return (
            b.provisional,
            json.loads(b.provisional_reasons or "[]"),
            round(b.net_credit_t_co2e, 6),
        )


async def test_portal_lab_matches_legacy_channel(lab_env):
    ac, Session = lab_env
    bp, ba = _mk_batch(), _mk_batch()
    async with Session() as s:
        s.add(bp)
        s.add(ba)
        await s.commit()
        bp_uuid, ba_uuid = bp.batch_uuid, ba.batch_uuid

    lab_token = await _token(ac, "lab@x.org")

    # Portal channel.
    rp = await ac.post(
        f"/api/v1/portal/batches/{bp_uuid}/lab-results",
        json=_LAB,
        headers={"Authorization": f"Bearer {lab_token}"},
    )
    assert rp.status_code == 200

    # Legacy admin channel, same values.
    ra = await ac.post(
        "/api/v1/admin/lab",
        json={"batch_uuid": str(ba_uuid), **_LAB},
        headers={"X-Admin-Secret": _ADMIN},
    )
    assert ra.status_code == 200

    sp = await _state(Session, bp_uuid)
    sa = await _state(Session, ba_uuid)
    assert sp == sa  # identical provisional / reasons / credit
    # assumed_* reasons flipped away now that lab data is present.
    assert "assumed_h_corg" not in sp[1]
    assert "assumed_corg" not in sp[1]


async def test_lab_role_can_verifier_cannot(lab_env):
    ac, Session = lab_env
    b = _mk_batch()
    async with Session() as s:
        s.add(b)
        await s.commit()
        buid = b.batch_uuid

    ver = await _token(ac, "ver@x.org")
    r = await ac.post(
        f"/api/v1/portal/batches/{buid}/lab-results",
        json=_LAB,
        headers={"Authorization": f"Bearer {ver}"},
    )
    assert r.status_code == 403

    lab = await _token(ac, "lab@x.org")
    r2 = await ac.post(
        f"/api/v1/portal/batches/{buid}/lab-results",
        json=_LAB,
        headers={"Authorization": f"Bearer {lab}"},
    )
    assert r2.status_code == 200
