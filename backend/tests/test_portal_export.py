import uuid as _uuid
"""Portal-native export routes (Bearer + admin role). Reuses the same export
services as the ops endpoints; the browser never holds the admin secret."""

import os
import tempfile
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
        batch_uuid=str(_uuid.uuid4()),
        operation_id=f"op-{_uuid.uuid4().hex[:8]}",
        feedstock_species="Lantana_camara",
        harvest_timestamp=datetime(2026, 7, 1, tzinfo=timezone.utc),
        moisture_percent=12.0,
        harvest_uptime_seconds=100,
        provisional=provisional,
        status="RECEIVED",
        net_credit_t_co2e=1.5,
        lab_h_corg=None if provisional else 0.42,
        organic_carbon_pct=0.8,
        lca_signature=None if provisional else "sig-abc",
    )


@pytest_asyncio.fixture
async def export_client():
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


async def test_csi_export_ok_and_writes_audit(export_client):
    ac, Session = export_client
    bu = await _seed(Session, _mk_batch(provisional=False))
    admin = await _auth(ac, "admin@x.org")

    r = await ac.get(f"/api/v1/portal/batches/{bu}/export/csi", headers=admin)
    assert r.status_code == 200
    body = r.json()
    assert body["batch_uuid"] == bu
    assert body["standard"] == "CSI GlobalCSinkVerificationReport v1"

    async with Session() as s:
        n = int(
            (
                await s.execute(
                    select(func.count()).where(
                        AuditEvent.event_type == "batch_exported",
                        AuditEvent.batch_uuid == bu,
                    )
                )
            ).scalar()
        )
        assert n == 1


async def test_rainbow_export_ok(export_client):
    ac, Session = export_client
    bu = await _seed(Session, _mk_batch(provisional=False))
    admin = await _auth(ac, "admin@x.org")
    r = await ac.get(f"/api/v1/portal/batches/{bu}/export/rainbow", headers=admin)
    assert r.status_code == 200
    assert r.json()["h_corg_ratio"] == 0.42


async def test_export_provisional_is_409(export_client):
    ac, Session = export_client
    bu = await _seed(Session, _mk_batch(provisional=True))
    admin = await _auth(ac, "admin@x.org")
    r = await ac.get(f"/api/v1/portal/batches/{bu}/export/csi", headers=admin)
    assert r.status_code == 409


async def test_export_unknown_format_is_400(export_client):
    ac, Session = export_client
    bu = await _seed(Session, _mk_batch(provisional=False))
    admin = await _auth(ac, "admin@x.org")
    r = await ac.get(f"/api/v1/portal/batches/{bu}/export/puro", headers=admin)
    assert r.status_code == 400


async def _seed_with_project(Session, batch, *, project_id, methodology_version=None):
    from models import Project, RegistryConfig

    batch.project_id = project_id
    async with Session() as s:
        if methodology_version is not None:
            config_id = f"cfg-{project_id}"
            s.add(
                RegistryConfig(
                    config_id=config_id,
                    registry_name="Export Routing Test Registry",
                    methodology_version=methodology_version,
                    params_json="{}",
                )
            )
            s.add(
                Project(
                    project_id=project_id, name=project_id,
                    registry_config_id=config_id,
                )
            )
        else:
            s.add(Project(project_id=project_id, name=project_id))
        s.add(batch)
        await s.commit()
        return str(batch.batch_uuid)


async def test_default_project_export_still_allows_either_format(export_client):
    """Regression pin: a project with no registry_config (every existing
    project's actual state) keeps today's free choice of export format."""
    ac, Session = export_client
    bu = await _seed_with_project(
        Session, _mk_batch(provisional=False), project_id="exp-proj-default"
    )
    admin = await _auth(ac, "admin@x.org")
    r1 = await ac.get(f"/api/v1/portal/batches/{bu}/export/csi", headers=admin)
    assert r1.status_code == 200
    r2 = await ac.get(f"/api/v1/portal/batches/{bu}/export/rainbow", headers=admin)
    assert r2.status_code == 200


async def test_csi_project_rejects_rainbow_format(export_client):
    ac, Session = export_client
    bu = await _seed_with_project(
        Session,
        _mk_batch(provisional=False),
        project_id="exp-proj-csi",
        methodology_version="CSI-3.2",
    )
    admin = await _auth(ac, "admin@x.org")
    r_ok = await ac.get(f"/api/v1/portal/batches/{bu}/export/csi", headers=admin)
    assert r_ok.status_code == 200

    r_bad = await ac.get(f"/api/v1/portal/batches/{bu}/export/rainbow", headers=admin)
    assert r_bad.status_code == 400
    assert r_bad.json()["detail"]["expected_format"] == "csi"


async def test_rainbow_project_rejects_csi_format(export_client):
    ac, Session = export_client
    bu = await _seed_with_project(
        Session,
        _mk_batch(provisional=False),
        project_id="exp-proj-rainbow",
        methodology_version="Rainbow",
    )
    admin = await _auth(ac, "admin@x.org")
    r_ok = await ac.get(f"/api/v1/portal/batches/{bu}/export/rainbow", headers=admin)
    assert r_ok.status_code == 200

    r_bad = await ac.get(f"/api/v1/portal/batches/{bu}/export/csi", headers=admin)
    assert r_bad.status_code == 400
    assert r_bad.json()["detail"]["expected_format"] == "rainbow"


async def test_export_is_admin_only(export_client):
    ac, Session = export_client
    bu = await _seed(Session, _mk_batch(provisional=False))
    for email in ("ver@x.org", "lab@x.org"):
        r = await ac.get(
            f"/api/v1/portal/batches/{bu}/export/csi", headers=await _auth(ac, email)
        )
        assert r.status_code == 403


async def test_export_unauthenticated_is_401(export_client):
    ac, Session = export_client
    bu = await _seed(Session, _mk_batch(provisional=False))
    r = await ac.get(f"/api/v1/portal/batches/{bu}/export/csi")
    assert r.status_code == 401
