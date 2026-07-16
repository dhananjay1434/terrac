"""Audit fix 1: per-IP rate-limit buckets must honor X-Forwarded-For so two
clients behind one proxy do not share (or jointly exhaust) a bucket."""

import json
import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def _register(client, xff, n):
    # /api/v1/register is the "register" bucket (cap 5/min, IP-keyed).
    return await client.post(
        "/api/v1/register",
        content=json.dumps(
            {"device_id": f"rl-{n}-{uuid.uuid4().hex[:6]}", "public_key": "A" * 43}
        ).encode("utf-8"),
        headers={"X-Forwarded-For": xff, "X-Enrollment-Token": "nope"},
    )


async def test_xff_clients_get_separate_buckets(client, monkeypatch):
    monkeypatch.setenv("DMRV_RATELIMIT_ENABLED", "1")
    monkeypatch.setenv("DMRV_RATELIMIT_REGISTER", "3")
    # Exhaust the bucket for IP 10.0.0.1 (3 requests hit the cap; 4th is 429).
    for i in range(3):
        r = await _register(client, "10.0.0.1", i)
        assert r.status_code != 429, r.text
    r = await _register(client, "10.0.0.1", 99)
    assert r.status_code == 429
    # A DIFFERENT client behind the same proxy is NOT rate-limited.
    r2 = await _register(client, "10.0.0.2", 100)
    assert r2.status_code != 429, r2.text


async def test_first_xff_hop_wins(client, monkeypatch):
    monkeypatch.setenv("DMRV_RATELIMIT_ENABLED", "1")
    monkeypatch.setenv("DMRV_RATELIMIT_REGISTER", "1")
    r = await _register(client, "10.9.9.9, 172.16.0.1", 0)
    assert r.status_code != 429
    # Same first hop, different second hop -> SAME bucket -> limited.
    r = await _register(client, "10.9.9.9, 172.16.0.2", 1)
    assert r.status_code == 429
