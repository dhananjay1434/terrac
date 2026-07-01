"""P0-22 regression: race-condition winner must not silently accept loser's payload."""

import asyncio
import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from server import app

VALID_HASH_A = "a" * 64
VALID_HASH_B = "b" * 64


@pytest.mark.asyncio
async def test_concurrent_same_uuid_different_hash_yields_409(client):
    """Two concurrent POSTs share batch_uuid but carry different sha256_hash.
    The loser must receive 409, not a 200 'duplicate' that hides data loss.
    """
    batch_uuid = str(uuid.uuid4())

    async def post(hash_hex: str, op_id: str):
        return await client.post(
            "/api/v1/batches",
            json={
                "batch_uuid": batch_uuid,
                "feedstock_species": "Lantana_camara",
                "harvest_timestamp": "2026-01-01T00:00:00Z",
                "moisture_percent": 10.0,
                "sha256_hash": hash_hex,
                "wet_yield_kg": 100.0,
                "min_recorded_temp_c": 650.0,
                "transport_distance_km": 0.0,
                "harvest_uptime_seconds": 3600,
            },
            headers={"X-Idempotency-Key": op_id},
        )

    r1, r2 = await asyncio.gather(
        post(VALID_HASH_A, "op-A"),
        post(VALID_HASH_B, "op-B"),
    )

    # Exactly one of the two must be 409, never both 2xx.
    statuses = sorted([r1.status_code, r2.status_code])
    assert 409 in statuses, f"At least one request must 409; got {statuses}"
    loser = r1 if r1.status_code == 409 else r2
    assert loser.json()["detail"] == "race_resolved_with_different_payload"
