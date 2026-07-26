"""M1.5 — /api/v1/portal/hierarchy: flag-gated, empty→empty, seeded→nested."""
import json
import os
import tempfile

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from db import get_session
from models import AppConfig, Base, Facility, Kiln, Network, PortalUser
from portal.auth import hash_password
from server import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def hclient():
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
        s.add(PortalUser(
            email="v@x.org", password_hash=hash_password("pw-verifier-1"), role="verifier",
        ))
        await s.commit()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            token = (await ac.post(
                "/api/v1/portal/login",
                json={"email": "v@x.org", "password": "pw-verifier-1"},
            )).json()["token"]
            yield ac, Session, {"Authorization": f"Bearer {token}"}
    finally:
        app.dependency_overrides.pop(get_session, None)
        await engine.dispose()
        try:
            os.remove(path)
        except OSError:
            pass


async def _enable_flag(Session):
    async with Session() as s:
        s.add(AppConfig(config_id="default", flags_json=json.dumps({"ff.hierarchy_v2": "on"})))
        await s.commit()


async def _seed(Session):
    async with Session() as s:
        s.add(Network(network_id="NET-1", name="North Net", country_code="IN"))
        s.add(Facility(
            facility_uuid="FAC-1", name="Site A", facility_type="artisanal",
            network_id="NET-1", site_code="P01",
        ))
        s.add(Kiln(kiln_id="KILN-1", site_id="FAC-1", kiln_code="K01", sensor_profile="full"))
        await s.commit()


async def test_hierarchy_empty_when_flag_off(hclient):
    ac, Session, auth = hclient
    await _seed(Session)  # data exists, but the flag is off → dormant
    body = (await ac.get("/api/v1/portal/hierarchy", headers=auth)).json()
    assert body == {"networks": []}


async def test_hierarchy_empty_when_no_data(hclient):
    ac, Session, auth = hclient
    await _enable_flag(Session)
    body = (await ac.get("/api/v1/portal/hierarchy", headers=auth)).json()
    assert body == {"networks": []}


async def test_hierarchy_nested_when_seeded_and_on(hclient):
    ac, Session, auth = hclient
    await _enable_flag(Session)
    await _seed(Session)
    body = (await ac.get("/api/v1/portal/hierarchy", headers=auth)).json()
    assert len(body["networks"]) == 1
    net = body["networks"][0]
    assert (net["network_id"], net["name"]) == ("NET-1", "North Net")
    assert len(net["sites"]) == 1
    site = net["sites"][0]
    assert (site["site_id"], site["name"]) == ("FAC-1", "Site A")
    assert site["kilns"] == [
        {"kiln_id": "KILN-1", "kiln_code": "K01", "sensor_profile": "full"}
    ]


async def test_hierarchy_requires_auth(hclient):
    ac, _Session, _auth = hclient
    resp = await ac.get("/api/v1/portal/hierarchy")
    assert resp.status_code in (401, 403)
