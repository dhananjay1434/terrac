"""P2.1 — portal auth: login/session lifecycle, role matrix, disabled users,
and server-side enrollment-token minting entropy.

These tests are HERMETIC: they build their own SQLite engine (schema via
Base.metadata.create_all) and override the exact `db.get_session` the portal
routes depend on. This keeps them independent of the shared-harness
`app.dependency_overrides` state (which other suites mutate) — the portal is the
first endpoint group whose tables the request path actually queries, so it must
not rely on a globally-clean override.
"""

import os
import tempfile

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from db import get_session
from models import Base, PortalUser
from portal.auth import hash_password
from server import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def portal_client():
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


async def _seed_user(Session, email, password, role, disabled=False):
    async with Session() as s:
        s.add(
            PortalUser(
                email=email,
                password_hash=hash_password(password),
                role=role,
                disabled=disabled,
            )
        )
        await s.commit()


async def _login(ac, email, password):
    return await ac.post(
        "/api/v1/portal/login", json={"email": email, "password": password}
    )


async def test_login_success_issues_a_working_session(portal_client):
    ac, Session = portal_client
    await _seed_user(Session, "admin@x.org", "correct-horse-1", "admin")

    r = await _login(ac, "admin@x.org", "correct-horse-1")
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "admin"
    token = body["token"]
    assert len(token) >= 20

    r2 = await ac.post(
        "/api/v1/portal/tokens",
        json={"expires_in_days": 7, "base_url": "https://api.example"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 201


async def test_wrong_password_is_401(portal_client):
    ac, Session = portal_client
    await _seed_user(Session, "admin@x.org", "correct-horse-1", "admin")
    r = await _login(ac, "admin@x.org", "wrong")
    assert r.status_code == 401


async def test_disabled_user_is_401(portal_client):
    ac, Session = portal_client
    await _seed_user(Session, "off@x.org", "correct-horse-1", "admin", disabled=True)
    r = await _login(ac, "off@x.org", "correct-horse-1")
    assert r.status_code == 401


async def test_lab_hitting_admin_route_is_403(portal_client):
    ac, Session = portal_client
    await _seed_user(Session, "lab@x.org", "correct-horse-1", "lab")
    token = (await _login(ac, "lab@x.org", "correct-horse-1")).json()["token"]

    r = await ac.post(
        "/api/v1/portal/tokens",
        json={"expires_in_days": 7},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_no_token_on_admin_route_is_401(portal_client):
    ac, _ = portal_client
    r = await ac.post("/api/v1/portal/tokens", json={"expires_in_days": 7})
    assert r.status_code == 401


async def test_mint_token_entropy_and_qr(portal_client):
    ac, Session = portal_client
    await _seed_user(Session, "admin@x.org", "correct-horse-1", "admin")
    token = (await _login(ac, "admin@x.org", "correct-horse-1")).json()["token"]

    r = await ac.post(
        "/api/v1/portal/tokens",
        json={"expires_in_days": 30, "base_url": "https://api.example"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    body = r.json()
    # 32 random bytes → base64url ≈ 43 chars ≫ the 128-bit (22 char) floor.
    assert len(body["token"]) >= 43
    assert body["qr_payload"].startswith("dmrv-enroll:v1:")
    assert "https://api.example" in body["qr_payload"]
    assert body["token"] in body["qr_payload"]


async def test_logout_revokes_the_session(portal_client):
    ac, Session = portal_client
    await _seed_user(Session, "admin@x.org", "correct-horse-1", "admin")
    token = (await _login(ac, "admin@x.org", "correct-horse-1")).json()["token"]
    auth = {"Authorization": f"Bearer {token}"}

    assert (
        await ac.post(
            "/api/v1/portal/tokens", json={"expires_in_days": 7}, headers=auth
        )
    ).status_code == 201

    assert (await ac.post("/api/v1/portal/logout", headers=auth)).status_code == 200

    r = await ac.post(
        "/api/v1/portal/tokens", json={"expires_in_days": 7}, headers=auth
    )
    assert r.status_code == 401
