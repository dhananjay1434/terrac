"""P3.4 — observability: request IDs echoed, guarded /metrics, JSON logs.

Hermetic (own SQLite engine + get_session override) like the portal tests, so
the /metrics provisional-ratio COUNT has real tables to read.
"""

import json
import logging
import os
import tempfile

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import observability
from db import get_session
from models import Base
from server import app


@pytest_asyncio.fixture
async def client():
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
            yield ac
    finally:
        app.dependency_overrides.pop(get_session, None)
        await engine.dispose()
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.mark.asyncio
async def test_request_id_is_generated_and_echoed(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.headers.get("X-Request-Id")  # a uuid was minted


@pytest.mark.asyncio
async def test_request_id_preserved_when_client_supplies_one(client):
    rid = "trace-abc-123"
    r = await client.get("/api/health", headers={"X-Request-Id": rid})
    assert r.headers.get("X-Request-Id") == rid


@pytest.mark.asyncio
async def test_metrics_401_without_token_200_with(client, monkeypatch):
    monkeypatch.setenv("DMRV_METRICS_TOKEN", "sekret-token")
    r = await client.get("/metrics")
    assert r.status_code == 401

    ok = await client.get("/metrics", headers={"X-Metrics-Token": "sekret-token"})
    assert ok.status_code == 200
    # Exposition includes our custom metrics.
    assert b"dmrv_provisional_ratio" in ok.content


@pytest.mark.asyncio
async def test_metrics_closed_when_token_unconfigured(client, monkeypatch):
    monkeypatch.delenv("DMRV_METRICS_TOKEN", raising=False)
    r = await client.get("/metrics", headers={"X-Metrics-Token": "anything"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_metrics_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setenv("DMRV_METRICS_TOKEN", "right")
    r = await client.get("/metrics", headers={"X-Metrics-Token": "wrong"})
    assert r.status_code == 401


def test_json_log_line_is_valid_json_with_request_id():
    fmt = observability.JsonLogFormatter()
    rec = logging.LogRecord(
        "dmrv", logging.INFO, __file__, 1, "hello %s", ("world",), None
    )
    parsed = json.loads(fmt.format(rec))
    assert parsed["msg"] == "hello world"
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "dmrv"
    assert "request_id" in parsed


def test_json_log_scrubs_pii_extra_fields():
    fmt = observability.JsonLogFormatter()
    rec = logging.LogRecord("dmrv", logging.INFO, __file__, 1, "m", (), None)
    rec.extra_fields = {"device_id": "SECRET", "lat": 12.3, "safe": "ok"}
    parsed = json.loads(fmt.format(rec))
    assert "device_id" not in parsed
    assert "lat" not in parsed
    assert parsed["safe"] == "ok"


def test_sentry_noop_without_dsn(monkeypatch):
    monkeypatch.delenv("DMRV_SENTRY_DSN", raising=False)
    assert observability.init_sentry() is False
