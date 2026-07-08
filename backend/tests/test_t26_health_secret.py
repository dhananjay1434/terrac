"""T2.6 — DB-probing health check + secret entropy floor."""

import pytest
from httpx import AsyncClient, ASGITransport

import server


# ---- health check --------------------------------------------------------


@pytest.mark.asyncio
async def test_health_ok_reports_db(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["db"] == "ok"


@pytest.mark.asyncio
async def test_health_503_when_db_unreachable():
    from server import app, get_session

    class _BrokenSession:
        async def execute(self, *a, **k):
            raise RuntimeError("db down")

    async def _broken():
        yield _BrokenSession()

    app.dependency_overrides[get_session] = _broken
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/api/health")
        assert r.status_code == 503
        assert r.json()["db"] == "down"
    finally:
        app.dependency_overrides.pop(get_session, None)


# ---- secret entropy floor ------------------------------------------------

_VAR = "DMRV_T26_TEST_SECRET"


def test_weak_short_secret_rejected(monkeypatch):
    monkeypatch.delenv("DMRV_ALLOW_WEAK_SECRETS", raising=False)
    monkeypatch.setenv(_VAR, "short")
    with pytest.raises(RuntimeError):
        server._require_secret(_VAR)


def test_low_entropy_secret_rejected(monkeypatch):
    monkeypatch.delenv("DMRV_ALLOW_WEAK_SECRETS", raising=False)
    monkeypatch.setenv(_VAR, "a" * 40)  # long enough, but only one distinct char
    with pytest.raises(RuntimeError):
        server._require_secret(_VAR)


def test_missing_secret_rejected(monkeypatch):
    monkeypatch.delenv("DMRV_ALLOW_WEAK_SECRETS", raising=False)
    monkeypatch.delenv(_VAR, raising=False)
    with pytest.raises(RuntimeError):
        server._require_secret(_VAR)


def test_strong_secret_accepted(monkeypatch):
    monkeypatch.delenv("DMRV_ALLOW_WEAK_SECRETS", raising=False)
    strong = "Zm9vYmFyLXRlc3Qtc2VjcmV0LTMyLWJ5dGVzIQ"  # 38 chars, many distinct
    monkeypatch.setenv(_VAR, strong)
    assert server._require_secret(_VAR) == strong


def test_escape_hatch_allows_weak_secret(monkeypatch):
    monkeypatch.setenv("DMRV_ALLOW_WEAK_SECRETS", "1")
    monkeypatch.setenv(_VAR, "short")
    assert server._require_secret(_VAR) == "short"
