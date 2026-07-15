import uuid as _uuid
"""P2.2 — portal read API: batches list (cursor pagination + filters), detail
(reused compliance view + evidence counts + media list), devices, summary, and
authed media streaming (path-traversal guarded). Hermetic, like the auth tests."""

import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import server
from db import get_session
from models import Base, Batch, DeviceKey, MediaFile, PortalUser
from portal.auth import hash_password
from server import app

pytestmark = pytest.mark.asyncio

_T0 = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)


def _mk_batch(i: int, *, status="RECEIVED", provisional=True, device="dev-A", project=None):
    return Batch(
        batch_uuid=str(_uuid.uuid4()),
        operation_id=f"op-{i}-{_uuid.uuid4().hex[:8]}",
        feedstock_species="Lantana_camara",
        harvest_timestamp=_T0,
        moisture_percent=12.0,
        harvest_uptime_seconds=100,
        status=status,
        provisional=provisional,
        provisional_reasons='["assumed_h_corg"]' if provisional else "[]",
        device_id=device,
        project_id=project,
        received_at=_T0 + timedelta(minutes=i),
    )


@pytest_asyncio.fixture
async def read_client():
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

    # Seed a verifier + log in for a bearer token.
    async with Session() as s:
        s.add(
            PortalUser(
                email="v@x.org",
                password_hash=hash_password("pw-verifier-1"),
                role="verifier",
            )
        )
        await s.commit()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            token = (
                await ac.post(
                    "/api/v1/portal/login",
                    json={"email": "v@x.org", "password": "pw-verifier-1"},
                )
            ).json()["token"]
            yield ac, Session, {"Authorization": f"Bearer {token}"}
    finally:
        app.dependency_overrides.pop(get_session, None)
        await engine.dispose()
        try:
            os.remove(path)
        except OSError:
            pass


async def test_pagination_is_stable_and_ordered(read_client):
    ac, Session, auth = read_client
    async with Session() as s:
        for i in range(5):
            s.add(_mk_batch(i))
        await s.commit()

    seen = []
    cursor = None
    for _ in range(10):  # generous ceiling
        params = {"limit": 2}
        if cursor:
            params["before"] = cursor
        body = (await ac.get("/api/v1/portal/batches", params=params, headers=auth)).json()
        seen.extend(b["batch_uuid"] for b in body["batches"])
        cursor = body["next_cursor"]
        if not cursor:
            break

    assert len(seen) == 5
    assert len(set(seen)) == 5  # no duplicates / skips across pages


async def test_filter_matrix(read_client):
    ac, Session, auth = read_client
    async with Session() as s:
        s.add(_mk_batch(1, status="RECEIVED", provisional=True, device="dev-A"))
        s.add(_mk_batch(2, status="ISSUED", provisional=False, device="dev-B"))
        s.add(_mk_batch(3, status="RECEIVED", provisional=False, device="dev-A"))
        await s.commit()

    async def n(params):
        return len((await ac.get("/api/v1/portal/batches", params=params, headers=auth)).json()["batches"])

    assert await n({"status": "RECEIVED"}) == 2
    assert await n({"provisional": "false"}) == 2
    assert await n({"device_id": "dev-B"}) == 1
    assert await n({"status": "RECEIVED", "provisional": "false"}) == 1


async def test_verifier_can_read_all_read_routes(read_client):
    ac, Session, auth = read_client
    b = _mk_batch(1)
    async with Session() as s:
        s.add(b)
        s.add(DeviceKey(device_id="dev-A", public_key="k" * 40))
        await s.commit()
        bu = str(b.batch_uuid)

    assert (await ac.get("/api/v1/portal/batches", headers=auth)).status_code == 200
    assert (await ac.get("/api/v1/portal/devices", headers=auth)).status_code == 200
    assert (await ac.get("/api/v1/portal/summary", headers=auth)).status_code == 200
    detail = await ac.get(f"/api/v1/portal/batches/{bu}", headers=auth)
    assert detail.status_code == 200
    body = detail.json()
    assert "compliance" in body and "checklist" in body["compliance"]
    assert set(body["evidence_counts"]) >= {"moisture_readings", "pyrolysis_telemetry"}
    # media list must never leak the on-disk path
    assert all("file_path" not in m for m in body["media"])


async def test_media_requires_auth(read_client):
    ac, _, _auth = read_client
    r = await ac.get("/api/v1/portal/media/some-op")  # no Authorization header
    assert r.status_code == 401


async def test_media_operation_id_traversal_is_400(read_client):
    ac, _, auth = read_client
    # A single-segment id that reaches the handler but fails the _SAFE guard
    # (a dot is not in [A-Za-z0-9_-]); this is the injection/traversal defence.
    r = await ac.get("/api/v1/portal/media/bad.id", headers=auth)
    assert r.status_code == 400


async def test_media_streams_bytes_with_auth(read_client):
    ac, Session, auth = read_client
    op = "op-media-1"
    upload_root = server.UPLOAD_DIR / "dev-A"
    upload_root.mkdir(parents=True, exist_ok=True)
    fpath = upload_root / f"{op}.bin"
    fpath.write_bytes(b"PROOFBYTES")
    bu = str(_uuid.uuid4())
    try:
        async with Session() as s:
            s.add(
                MediaFile(
                    batch_uuid=bu,
                    operation_id=op,
                    file_path=str(fpath),
                    sha256_hash="a" * 64,
                    filename="proof.jpg",
                )
            )
            await s.commit()

        r = await ac.get(f"/api/v1/portal/media/{op}", headers=auth)
        assert r.status_code == 200
        assert r.content == b"PROOFBYTES"
    finally:
        try:
            fpath.unlink()
        except OSError:
            pass
