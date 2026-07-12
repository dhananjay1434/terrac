"""T2.2 — per-route rate limiting.

Rate limiting is disabled by default under test (conftest sets
DMRV_RATELIMIT_ENABLED=0). These tests re-enable it via monkeypatch.setenv —
config is read live from os.environ by the middleware, so this is robust to the
importlib.reload(server) that other test files perform (a module-constant
approach would desync from the running middleware). A large window keeps every
request in one bucket so the counter never straddles a boundary. Register/admin
buckets are IP-keyed; under the ASGI test transport all requests share one key.
"""

import json

import pytest

import server
import middleware

pytestmark = pytest.mark.asyncio


def _enable(monkeypatch, **caps):
    monkeypatch.setenv("DMRV_RATELIMIT_ENABLED", "1")
    monkeypatch.setenv("DMRV_RATELIMIT_WINDOW_SECONDS", "3600")
    for bucket, value in caps.items():
        monkeypatch.setenv(f"DMRV_RATELIMIT_{bucket.upper()}", str(value))
    middleware._rl_counters.clear()


async def _register(client, i):
    return await client.post(
        "/api/v1/register",
        content=json.dumps({"device_id": f"rl-dev-{i}", "public_key": "x"}).encode(
            "utf-8"
        ),
        headers={"X-Enrollment-Token": "definitely-invalid"},
    )


async def test_register_is_rate_limited(client, monkeypatch):
    _enable(monkeypatch, register=3)
    codes = [(await _register(client, i)).status_code for i in range(5)]
    # First 3 reach the app (not throttled); the 4th and 5th are rate-limited.
    assert all(c != 429 for c in codes[:3]), codes
    assert codes[3] == 429 and codes[4] == 429, codes


async def test_rate_limited_response_carries_retry_after(client, monkeypatch):
    _enable(monkeypatch, register=1)
    await _register(client, 0)
    r = await _register(client, 1)
    assert r.status_code == 429
    assert "retry-after" in {k.lower() for k in r.headers.keys()}
    assert r.json()["detail"] == "rate_limited"


async def test_admin_bucket_is_rate_limited(client, monkeypatch):
    _enable(monkeypatch, admin=2)

    async def _mint():
        return await client.post(
            "/api/v1/admin/mint-token",
            content=json.dumps({"token": "t", "expires_in_days": 1}).encode("utf-8"),
            headers={"X-Admin-Secret": "wrong-secret"},
        )

    codes = [(await _mint()).status_code for _ in range(4)]
    # First 2 reach the app (401 unauthorized); 3rd/4th throttled.
    assert all(c != 429 for c in codes[:2]), codes
    assert codes[2] == 429 and codes[3] == 429, codes


async def test_disabled_limiter_does_not_throttle(client, monkeypatch):
    # Default test posture: disabled. Many requests, never a 429.
    monkeypatch.setenv("DMRV_RATELIMIT_ENABLED", "0")
    middleware._rl_counters.clear()
    codes = [(await _register(client, i)).status_code for i in range(8)]
    assert 429 not in codes, codes
