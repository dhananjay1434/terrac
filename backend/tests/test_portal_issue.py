"""P2.6 — deliberate credit issuance + immutable audit trail. Issue requires a
non-provisional batch (server re-verified), is admin-only, records an audit
event, is single-shot (double-issue -> 409), and audit rows cannot be updated."""

import os
import tempfile
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from db import get_session
from models import AuditEvent, Base, Batch, PortalUser
from portal.auth import hash_password
from server import app

pytestmark = pytest.mark.asyncio


def _mk_batch(*, provisional: bool):
    return Batch(
        batch_uuid=uuid.uuid4(),
        operation_id=f"op-{uuid.uuid4().hex[:8]}",
        feedstock_species="Lantana_camara",
        harvest_timestamp=datetime(2026, 7, 1, tzinfo=timezone.utc),
        moisture_percent=12.0,
        harvest_uptime_seconds=100,
        provisional=provisional,
        status="RECEIVED",
        net_credit_t_co2e=1.5,
        lca_signature=None if provisional else "sig-abc",
    )


@pytest_asyncio.fixture
async def issue_client():
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
        for email, role in [
            ("admin@x.org", "admin"),
            ("ver@x.org", "verifier"),
            ("lab@x.org", "lab"),
        ]:
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


async def _auth(ac, email):
    tok = (
        await ac.post(
            "/api/v1/portal/login", json={"email": email, "password": "pw-12345"}
        )
    ).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


async def _seed(Session, batch):
    async with Session() as s:
        s.add(batch)
        await s.commit()
        return str(batch.batch_uuid)


async def test_issue_provisional_batch_is_409(issue_client):
    ac, Session = issue_client
    bu = await _seed(Session, _mk_batch(provisional=True))
    admin = await _auth(ac, "admin@x.org")
    r = await ac.post(f"/api/v1/portal/batches/{bu}/issue", headers=admin)
    assert r.status_code == 409


async def test_issue_success_writes_audit_and_double_issue_409(issue_client):
    ac, Session = issue_client
    bu = await _seed(Session, _mk_batch(provisional=False))
    admin = await _auth(ac, "admin@x.org")

    r = await ac.post(f"/api/v1/portal/batches/{bu}/issue", headers=admin)
    assert r.status_code == 200
    assert r.json()["status"] == "ISSUED"

    # Audit row recorded.
    async with Session() as s:
        n = int(
            (
                await s.execute(
                    select(func.count()).where(
                        AuditEvent.event_type == "credit_issued",
                        AuditEvent.batch_uuid == bu,
                    )
                )
            ).scalar()
        )
        assert n == 1

    # Second attempt is refused.
    r2 = await ac.post(f"/api/v1/portal/batches/{bu}/issue", headers=admin)
    assert r2.status_code == 409

    # And it shows up on the audit read route.
    audit = (await ac.get(f"/api/v1/portal/batches/{bu}/audit", headers=admin)).json()
    assert any(e["event_type"] == "credit_issued" for e in audit["events"])


async def test_issue_is_admin_only(issue_client):
    ac, Session = issue_client
    bu = await _seed(Session, _mk_batch(provisional=False))
    for email in ("ver@x.org", "lab@x.org"):
        r = await ac.post(
            f"/api/v1/portal/batches/{bu}/issue", headers=await _auth(ac, email)
        )
        assert r.status_code == 403


async def test_audit_events_are_immutable(issue_client):
    ac, Session = issue_client
    bu = await _seed(Session, _mk_batch(provisional=False))
    await ac.post(
        f"/api/v1/portal/batches/{bu}/issue", headers=await _auth(ac, "admin@x.org")
    )
    async with Session() as s:
        ev = (await s.execute(select(AuditEvent).limit(1))).scalar_one()
        ev.event_type = "tampered"
        with pytest.raises(Exception):
            await s.flush()
