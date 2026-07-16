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


async def test_rotating_device_ids_share_ip_budget(client, monkeypatch):
    """Audit fix 7: X-Device-Id rotation must not evade the default bucket."""
    import json as _json
    from datetime import datetime, timezone
    import uuid as _uuid

    monkeypatch.setenv("DMRV_RATELIMIT_ENABLED", "1")
    monkeypatch.setenv("DMRV_RATELIMIT_DEFAULT", "3")

    async def _post(devid):
        # Any /api/v1/* JSON endpoint in the 'default' bucket works; use batches.
        return await client.post(
            "/api/v1/batches",
            content=_json.dumps(
                {
                    "batch_uuid": str(_uuid.uuid4()),
                    "feedstock_species": "Lantana_camara",
                    "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
                    "moisture_percent": 12.0,
                    "harvest_uptime_seconds": 1,
                }
            ).encode("utf-8"),
            headers={
                "X-Idempotency-Key": "op-" + _uuid.uuid4().hex[:10],
                "X-Forwarded-For": "10.7.7.7",
                "X-Device-Id": devid,       # rotated every request
            },
        )

    statuses = []
    for i in range(5):
        r = await _post(f"rotator-{i}")
        statuses.append(r.status_code)
    assert 429 in statuses, f"rotating device ids evaded the cap: {statuses}"
