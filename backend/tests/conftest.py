"""
Shared fixtures for the hardening verification suite.

Two engines are exposed:
  * `test_engine`   — fresh in-memory SQLite, schema built via Base.metadata
  * `client`        — httpx.AsyncClient wired to the FastAPI app with the
                      session dependency overridden to use the test engine.

These fixtures are intentionally minimal duplicates of `tests/test_api.py`
so the hardening tests can run even if the original fixtures change.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from uuid import uuid4

# ---- env shims so the backend imports cleanly under test ------------------
os.environ.setdefault(
    "DATABASE_URL", "sqlite+aiosqlite:///:memory:"
)  # neutralises P0-17 RuntimeError under test
os.environ.setdefault("DMRV_SKIP_MIGRATIONS", "1")  # P0-18 escape hatch
# T2.2: rate limiting off by default under test so multi-request flow tests don't
# trip 429; test_rate_limit.py re-enables it via monkeypatch on the server module.
os.environ.setdefault("DMRV_RATELIMIT_ENABLED", "0")
# T2.6: the suite uses short fixed secret literals (asserted verbatim in many
# tests); allow them past the production entropy floor. NEVER set in production.
os.environ.setdefault("DMRV_ALLOW_WEAK_SECRETS", "1")
os.environ.setdefault("DMRV_HMAC_SECRET", "test-secret")
os.environ.setdefault(
    "DMRV_ADMIN_SECRET", "test-admin-secret"
)  # Phase 2: admin auth distinct from HMAC pepper

BACKEND_DIR = Path(__file__).resolve().parents[1]
if BACKEND_DIR.exists() and str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ---- Phase 5: fixed Ed25519 test identity ---------------------------------
# Every seeded test device enrolls TEST_PUBLIC_KEY_B64; the SignedAsyncClient
# (and tests/remediation/crypto_utils) sign with the matching private key,
# derived from the same 32-byte seed so the public keys are identical.
import base64 as _base64  # noqa: E402
from cryptography.hazmat.primitives import serialization as _ser  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: E402
    Ed25519PrivateKey as _Ed25519PrivateKey,
)

_TEST_PRIV = _Ed25519PrivateKey.from_private_bytes(bytes(range(32)))


def _b64u(b: bytes) -> str:
    return _base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


TEST_PUBLIC_KEY_B64 = _b64u(
    _TEST_PRIV.public_key().public_bytes(
        encoding=_ser.Encoding.Raw, format=_ser.PublicFormat.Raw
    )
)


def _ed25519_sign(canonical: bytes) -> str:
    return _b64u(_TEST_PRIV.sign(canonical))


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Per-test database engine.

    T3.1: when DATABASE_URL points at Postgres, run the suite against that
    server so app queries genuinely exercise the production dialect (JSON,
    timezone, CheckConstraint, UUID divergences the audit called out). Isolation
    is per-test via drop_all+create_all — slower than SQLite but correct on a
    shared server. Otherwise keep the fast default: a fresh SQLite tempfile per
    test (local dev + the neutral CI lane). SQLite in-memory can't be shared
    across connections, so the tempfile path is retained for that case.
    """
    from models import Base

    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("postgresql"):
        engine = create_async_engine(db_url, poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        try:
            yield engine
        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
        return

    import tempfile

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{path}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()

    try:
        os.remove(path)
    except OSError:
        pass


@pytest_asyncio.fixture(scope="function")
async def session_factory(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False)


class SignedAsyncClient(AsyncClient):
    async def send(self, request, *args, **kwargs):
        if (
            "X-Signature" not in request.headers
            and "X-Device-Id" not in request.headers
        ):
            request.headers["X-Device-Id"] = "test-device-reg"
            import hashlib

            method = request.method
            path = request.url.path
            op_id = request.headers.get("X-Idempotency-Key", "")
            body_hash = hashlib.sha256(request.content).hexdigest()
            canonical = (
                f"{method}\n{path}\n{op_id}\n{body_hash}\ntest-device-reg".encode(
                    "utf-8"
                )
            )
            request.headers["X-Signature"] = _ed25519_sign(canonical)
        return await super().send(request, *args, **kwargs)


@pytest_asyncio.fixture(scope="function")
async def client(session_factory):
    from server import app, get_session

    async def override_session():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_session

    from httpx import ASGITransport

    async with SignedAsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def registered_device(client, session_factory):
    import base64, json
    from models import EnrollmentToken

    async with session_factory() as session:
        session.add(EnrollmentToken(token="test-credit"))
        await session.commit()
    dev_id = "test-device-reg"
    payload = {"device_id": dev_id, "public_key": TEST_PUBLIC_KEY_B64}
    await client.post(
        "/api/v1/register",
        content=json.dumps(payload).encode("utf-8"),
        headers={"X-Enrollment-Token": "test-credit"},
    )
    return {
        "device_id": dev_id,
        "public_key": TEST_PUBLIC_KEY_B64,
        "b64_key": TEST_PUBLIC_KEY_B64,  # back-compat alias for legacy call sites
    }


@pytest_asyncio.fixture(scope="function", autouse=True)
async def legacy_test_environment(session_factory):
    """Seed the device identities the legacy tests assume.

    Phase 7-R: the previous global monkeypatch of AsyncSession.execute (which
    faked every telemetry query as {"temperatureReadingsJson": [650]*60}) was
    removed. It hid the client↔server telemetry-key mismatch for nine phases and
    meant large parts of the suite verified the mock, not the code. Tests that
    need telemetry now insert a real PyrolysisTelemetry row with the canonical
    `temperature_readings` key. The DISABLE_TELEMETRY_MOCK env flag is obsolete
    (no-op) but harmless where still set.
    """
    from models import DeviceKey

    # Pre-populate common devices used in legacy tests. All enroll the fixed
    # Ed25519 test public key; requests are signed with the matching private key.
    devices_to_add = ["dev-1", "test-device-1", "test-device-2", "", "test-device-reg"]

    async with session_factory() as session:
        for d in devices_to_add:
            session.add(DeviceKey(device_id=d, public_key=TEST_PUBLIC_KEY_B64))
        await session.commit()

    yield
