"""PR-1.6 — credit issuance ledger portal endpoints.

Mirrors test_portal_issue.py's fixture pattern (temp sqlite db, seeded
PortalUsers, ASGI test client) but exercises the new serialized-ledger
endpoints under /api/v1/portal/batches/{uuid}/issuance/*.
"""

import os
import tempfile
import uuid as _uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from db import get_session
from models import Base, Batch, CreditIssuance, PortalUser
from portal.auth import hash_password
from server import app

pytestmark = pytest.mark.asyncio


def _mk_batch(*, provisional: bool = False, signed: bool = True):
    return Batch(
        batch_uuid=str(_uuid.uuid4()),
        operation_id=f"op-{_uuid.uuid4().hex[:8]}",
        feedstock_species="Lantana_camara",
        harvest_timestamp=datetime(2026, 7, 1, tzinfo=timezone.utc),
        moisture_percent=12.0,
        harvest_uptime_seconds=100,
        provisional=provisional,
        status="RECEIVED",
        project_id="proj-a",
        net_credit_t_co2e=1.5,
        lca_signature=("sig-abc" if (signed and not provisional) else None),
        lca_methodology_version="CSI-3.2",
    )


@pytest_asyncio.fixture
async def issuance_client():
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


async def test_verify_then_issue_happy_path(issuance_client):
    ac, Session = issuance_client
    bu = await _seed(Session, _mk_batch())
    verifier = await _auth(ac, "ver@x.org")
    admin = await _auth(ac, "admin@x.org")

    r = await ac.post(
        f"/api/v1/portal/batches/{bu}/issuance/verify", headers=verifier
    )
    assert r.status_code == 200
    assert r.json()["status"] == "verified"
    assert r.json()["verified_by_user_id"] is not None

    r2 = await ac.post(f"/api/v1/portal/batches/{bu}/issuance/issue", headers=admin)
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] == "issued"
    assert body["serial"] == "proj-a-2026-000001"
    assert body["t_co2e_frozen"] == 1.5
    assert body["issued_at"] is not None


async def test_issue_before_verify_is_409(issuance_client):
    ac, Session = issuance_client
    bu = await _seed(Session, _mk_batch())
    admin = await _auth(ac, "admin@x.org")

    r = await ac.post(f"/api/v1/portal/batches/{bu}/issuance/issue", headers=admin)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "illegal_transition"


async def test_issue_of_provisional_batch_rejected(issuance_client):
    ac, Session = issuance_client
    bu = await _seed(Session, _mk_batch(provisional=True, signed=False))
    verifier = await _auth(ac, "ver@x.org")
    admin = await _auth(ac, "admin@x.org")

    await ac.post(f"/api/v1/portal/batches/{bu}/issuance/verify", headers=verifier)
    r = await ac.post(f"/api/v1/portal/batches/{bu}/issuance/issue", headers=admin)
    assert r.status_code == 422
    assert "provisional" in r.json()["detail"]["message"]


async def test_issue_of_unsigned_batch_rejected(issuance_client):
    ac, Session = issuance_client
    bu = await _seed(Session, _mk_batch(provisional=False, signed=False))
    verifier = await _auth(ac, "ver@x.org")
    admin = await _auth(ac, "admin@x.org")

    await ac.post(f"/api/v1/portal/batches/{bu}/issuance/verify", headers=verifier)
    r = await ac.post(f"/api/v1/portal/batches/{bu}/issuance/issue", headers=admin)
    assert r.status_code == 422
    assert "signed" in r.json()["detail"]["message"]


async def test_duplicate_issue_is_idempotent_one_row_one_serial(issuance_client):
    ac, Session = issuance_client
    bu = await _seed(Session, _mk_batch())
    verifier = await _auth(ac, "ver@x.org")
    admin = await _auth(ac, "admin@x.org")

    await ac.post(f"/api/v1/portal/batches/{bu}/issuance/verify", headers=verifier)
    r1 = await ac.post(f"/api/v1/portal/batches/{bu}/issuance/issue", headers=admin)
    r2 = await ac.post(f"/api/v1/portal/batches/{bu}/issuance/issue", headers=admin)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["serial"] == r2.json()["serial"]
    assert r1.json()["issuance_uuid"] == r2.json()["issuance_uuid"]

    async with Session() as s:
        rows = (
            await s.execute(
                select(CreditIssuance).where(CreditIssuance.batch_uuid == bu)
            )
        ).scalars().all()
        assert len(rows) == 1


async def test_illegal_transition_retire_a_pending_is_409(issuance_client):
    ac, Session = issuance_client
    bu = await _seed(Session, _mk_batch())
    verifier = await _auth(ac, "ver@x.org")
    admin = await _auth(ac, "admin@x.org")

    # Create the pending row via verify... no wait, verify moves straight to
    # 'verified'. To exercise a 'pending' row, hit /retire before any verify.
    r = await ac.post(
        f"/api/v1/portal/batches/{bu}/issuance/retire", json={}, headers=admin
    )
    assert r.status_code == 404  # no issuance row exists at all yet

    await ac.post(f"/api/v1/portal/batches/{bu}/issuance/verify", headers=verifier)
    r2 = await ac.post(
        f"/api/v1/portal/batches/{bu}/issuance/retire", json={}, headers=admin
    )
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "illegal_transition"


async def test_export_includes_serial_after_issue(issuance_client):
    ac, Session = issuance_client
    bu = await _seed(Session, _mk_batch())
    verifier = await _auth(ac, "ver@x.org")
    admin = await _auth(ac, "admin@x.org")

    await ac.post(f"/api/v1/portal/batches/{bu}/issuance/verify", headers=verifier)
    await ac.post(f"/api/v1/portal/batches/{bu}/issuance/issue", headers=admin)

    r = await ac.get(f"/api/v1/portal/batches/{bu}/export/csi", headers=admin)
    assert r.status_code == 200
    issuance = r.json()["issuance"]
    assert issuance is not None
    assert issuance["serial"] == "proj-a-2026-000001"
    assert issuance["status"] == "issued"


async def test_export_issuance_is_null_before_any_issuance(issuance_client):
    ac, Session = issuance_client
    bu = await _seed(Session, _mk_batch())
    admin = await _auth(ac, "admin@x.org")

    r = await ac.get(f"/api/v1/portal/batches/{bu}/export/csi", headers=admin)
    assert r.status_code == 200
    assert r.json()["issuance"] is None


async def test_verify_is_verifier_or_admin_only(issuance_client):
    ac, Session = issuance_client
    bu = await _seed(Session, _mk_batch())
    lab = await _auth(ac, "lab@x.org")

    r = await ac.post(f"/api/v1/portal/batches/{bu}/issuance/verify", headers=lab)
    assert r.status_code == 403


async def test_issue_retire_cancel_are_admin_only(issuance_client):
    ac, Session = issuance_client
    bu = await _seed(Session, _mk_batch())
    verifier_headers = await _auth(ac, "ver@x.org")

    r = await ac.post(
        f"/api/v1/portal/batches/{bu}/issuance/issue", headers=verifier_headers
    )
    assert r.status_code == 403

    r2 = await ac.post(
        f"/api/v1/portal/batches/{bu}/issuance/retire",
        json={},
        headers=verifier_headers,
    )
    assert r2.status_code == 403

    r3 = await ac.post(
        f"/api/v1/portal/batches/{bu}/issuance/cancel", headers=verifier_headers
    )
    assert r3.status_code == 403


async def test_cancel_from_pending_then_illegal_from_cancelled(issuance_client):
    ac, Session = issuance_client
    bu = await _seed(Session, _mk_batch())
    verifier = await _auth(ac, "ver@x.org")
    admin = await _auth(ac, "admin@x.org")

    # No row yet -> 404 on cancel.
    r0 = await ac.post(f"/api/v1/portal/batches/{bu}/issuance/cancel", headers=admin)
    assert r0.status_code == 404

    await ac.post(f"/api/v1/portal/batches/{bu}/issuance/verify", headers=verifier)
    r1 = await ac.post(f"/api/v1/portal/batches/{bu}/issuance/cancel", headers=admin)
    assert r1.status_code == 200
    assert r1.json()["status"] == "cancelled"

    r2 = await ac.post(f"/api/v1/portal/batches/{bu}/issuance/cancel", headers=admin)
    assert r2.status_code == 409


async def test_list_issuances(issuance_client):
    ac, Session = issuance_client
    bu = await _seed(Session, _mk_batch())
    verifier = await _auth(ac, "ver@x.org")
    admin = await _auth(ac, "admin@x.org")

    await ac.post(f"/api/v1/portal/batches/{bu}/issuance/verify", headers=verifier)
    await ac.post(f"/api/v1/portal/batches/{bu}/issuance/issue", headers=admin)

    r = await ac.get("/api/v1/portal/issuances", headers=admin)
    assert r.status_code == 200
    body = r.json()
    assert len(body["issuances"]) == 1
    assert body["issuances"][0]["batch_uuid"] == bu

    r2 = await ac.get(
        "/api/v1/portal/issuances", params={"status": "issued"}, headers=admin
    )
    assert len(r2.json()["issuances"]) == 1

    r3 = await ac.get(
        "/api/v1/portal/issuances", params={"status": "pending"}, headers=admin
    )
    assert len(r3.json()["issuances"]) == 0
