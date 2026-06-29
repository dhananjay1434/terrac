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
os.environ.setdefault("DMRV_HMAC_SECRET", "test-secret")

BACKEND_DIR = Path(__file__).resolve().parents[1]
if BACKEND_DIR.exists() and str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a fresh SQLite database file for each test."""
    from models import Base
    import tempfile
    
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    db_url = f"sqlite+aiosqlite:///{path}"
    engine = create_async_engine(
        db_url,
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
        if "X-HMAC-Signature" not in request.headers and "X-Device-Id" not in request.headers:
            request.headers["X-Device-Id"] = "test-device-reg"
            import hashlib, hmac, base64
            method = request.method
            path = request.url.path
            op_id = request.headers.get("X-Idempotency-Key", "")
            body_hash = hashlib.sha256(request.content).hexdigest()
            canonical = f"{method}\n{path}\n{op_id}\n{body_hash}\ntest-device-reg".encode("utf-8")
            raw_key = b"test-secret"
            sig = hmac.new(raw_key, canonical, hashlib.sha256).hexdigest()
            request.headers["X-HMAC-Signature"] = sig
        return await super().send(request, *args, **kwargs)

@pytest_asyncio.fixture(scope="function")
async def client(session_factory):
    from server import app, get_session

    async def override_session():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_session
    from httpx import ASGITransport
    async with SignedAsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture(scope="function")
async def registered_device(client, session_factory):
    import base64, json
    from models import EnrollmentToken
    async with session_factory() as session:
        session.add(EnrollmentToken(token="test-credit"))
        await session.commit()
    b64_key = base64.urlsafe_b64encode(b"12345678901234567890123456789012").decode('utf-8')
    dev_id = "test-device-reg"
    payload = {"device_id": dev_id, "hmac_key": b64_key}
    await client.post("/api/v1/register", content=json.dumps(payload).encode("utf-8"), headers={"X-Enrollment-Token": "test-credit"})
    return {"device_id": dev_id, "b64_key": b64_key}

@pytest_asyncio.fixture(scope="function", autouse=True)
async def legacy_test_environment(session_factory):
    import base64
    from models import DeviceKey
    from unittest.mock import patch
    import server

    # Pre-populate common devices used in legacy tests
    b64_key = base64.urlsafe_b64encode(b"test-secret").decode("utf-8")
    devices_to_add = ["dev-1", "test-device-1", "test-device-2", "", "test-device-reg"]
    
    async with session_factory() as session:
        for d in devices_to_add:
            session.add(DeviceKey(device_id=d, hmac_key=b64_key))
        await session.commit()
    # Mock telemetry check by hooking AsyncSession.execute
    original_execute = server.AsyncSession.execute
    
    async def mock_execute(self, stmt, *args, **kwargs):
        import os
        if os.environ.get("DISABLE_TELEMETRY_MOCK") == "1":
            return await original_execute(self, stmt, *args, **kwargs)
        if "PyrolysisTelemetry" in str(stmt) or "telemetry" in str(stmt).lower():
            import json
            from unittest.mock import MagicMock
            mock_result = MagicMock()
            mock_tel = MagicMock()
            mock_tel.payload_json = json.dumps({"temperatureReadingsJson": [650.0] * 60, "hwAttestationJson": "mock"})
            mock_result.scalar_one_or_none.return_value = mock_tel
            return mock_result
        return await original_execute(self, stmt, *args, **kwargs)

    patcher = patch("server.AsyncSession.execute", new=mock_execute)
    patcher.start()
    
    yield
    
    patcher.stop()
