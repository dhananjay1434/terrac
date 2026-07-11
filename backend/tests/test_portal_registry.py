"""P2.5 — portal registry forms + M5 idempotency. Operator-training and
supervisor-visit are now idempotent on their NATURAL key (operator+date /
kiln+date), so a double-submit with a fresh record uuid yields one row. Role is
admin-only."""

import os
import tempfile
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from db import get_session
from models import Base, OperatorTraining, PortalUser, SupervisorVisit
from portal.auth import hash_password
from server import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def reg_client():
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
        for email, role in [("admin@x.org", "admin"), ("ver@x.org", "verifier")]:
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


async def _count(Session, model):
    async with Session() as s:
        return int((await s.execute(select(func.count()).select_from(model))).scalar())


async def test_m5_training_idempotent_on_operator_date(reg_client):
    ac, Session = reg_client
    auth = {"Authorization": f"Bearer {await _token(ac, 'admin@x.org')}"}
    base = {"operator_id": "OP-7", "completed_at": "2026-07-01", "training_type": "safety"}

    # Two submits, same operator+date, DIFFERENT record_uuid.
    r1 = await ac.post(
        "/api/v1/portal/registry/operator-training",
        json={"record_uuid": str(uuid.uuid4()), **base},
        headers=auth,
    )
    r2 = await ac.post(
        "/api/v1/portal/registry/operator-training",
        json={"record_uuid": str(uuid.uuid4()), **base},
        headers=auth,
    )
    assert r1.json()["duplicate"] is False
    assert r2.json()["duplicate"] is True
    assert await _count(Session, OperatorTraining) == 1


async def test_m5_visit_idempotent_on_kiln_date(reg_client):
    ac, Session = reg_client
    auth = {"Authorization": f"Bearer {await _token(ac, 'admin@x.org')}"}
    base = {"kiln_id": "KILN-1", "visited_at": "2026-07-02", "notes": "ok"}

    await ac.post(
        "/api/v1/portal/registry/supervisor-visit",
        json={"visit_uuid": str(uuid.uuid4()), **base},
        headers=auth,
    )
    await ac.post(
        "/api/v1/portal/registry/supervisor-visit",
        json={"visit_uuid": str(uuid.uuid4()), **base},
        headers=auth,
    )
    assert await _count(Session, SupervisorVisit) == 1


async def test_kiln_upsert_and_list(reg_client):
    ac, Session = reg_client
    auth = {"Authorization": f"Bearer {await _token(ac, 'admin@x.org')}"}
    body = {"kiln_id": "KILN-42", "kiln_type": "open", "material": "steel"}
    assert (
        await ac.post("/api/v1/portal/registry/kilns", json=body, headers=auth)
    ).json()["updated"] is False
    assert (
        await ac.post("/api/v1/portal/registry/kilns", json=body, headers=auth)
    ).json()["updated"] is True

    listed = (await ac.get("/api/v1/portal/registry/kilns", headers=auth)).json()
    assert len(listed["kilns"]) == 1
    assert listed["kilns"][0]["kiln_type"] == "open"


async def test_registry_is_admin_only(reg_client):
    ac, _ = reg_client
    ver = {"Authorization": f"Bearer {await _token(ac, 'ver@x.org')}"}
    r = await ac.post(
        "/api/v1/portal/registry/kilns",
        json={"kiln_id": "K1", "kiln_type": "open"},
        headers=ver,
    )
    assert r.status_code == 403
