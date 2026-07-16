"""Audit fix 2: retrying a photo-less batch (sha256_hash=None) with the same
idempotency key must return 200 duplicate, not 500 (None.lower() crash)."""

import json
import uuid
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.asyncio


def _payload(bu):
    # No sha256_hash / photo_path — a legitimate photo-less batch.
    return {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
    }


async def test_photoless_batch_retry_is_200_duplicate(client, registered_device):
    bu = str(uuid.uuid4())
    body = json.dumps(_payload(bu)).encode("utf-8")
    op = "op-nophoto-" + bu[:8]

    r1 = await client.post(
        "/api/v1/batches", content=body, headers={"X-Idempotency-Key": op}
    )
    assert r1.status_code == 201, r1.text

    # Byte-identical retry with the same idempotency key.
    r2 = await client.post(
        "/api/v1/batches", content=body, headers={"X-Idempotency-Key": op}
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["duplicate"] is True


async def test_photoless_op_reuse_with_photo_is_409(client, registered_device):
    bu = str(uuid.uuid4())
    op = "op-conflict-" + bu[:8]
    r1 = await client.post(
        "/api/v1/batches",
        content=json.dumps(_payload(bu)).encode("utf-8"),
        headers={"X-Idempotency-Key": op},
    )
    assert r1.status_code == 201, r1.text

    # Same op-id, same uuid, but NOW claims a photo hash -> different payload -> 409.
    p2 = _payload(bu)
    p2["sha256_hash"] = "a" * 64
    r2 = await client.post(
        "/api/v1/batches",
        content=json.dumps(p2).encode("utf-8"),
        headers={"X-Idempotency-Key": op},
    )
    assert r2.status_code == 409, r2.text
