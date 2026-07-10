"""P1-B4 — evidence batch_uuid is canonicalized so it can never orphan.

Evidence tables store batch_uuid as a String(36) joined against the batches
row's canonical UUID. A non-canonical case (uppercase from a future client)
would silently orphan the evidence. The _BatchScopedPayload validator now
canonicalizes to str(UUID(...)) at parse time and 422s a malformed value.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import MoistureReading

pytestmark = pytest.mark.asyncio


async def _create_batch(client, bu):
    return await client.post(
        "/api/v1/batches",
        content=json.dumps(
            {
                "batch_uuid": bu,
                "feedstock_species": "Lantana_camara",
                "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
                "moisture_percent": 12.0,
                "harvest_uptime_seconds": 100,
                "biomass_input_kg": 500.0,
                "biomass_measurement_method": "direct_weigh",
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + bu[:8]},
    )


async def _post_moisture(client, bu, op):
    return await client.post(
        "/api/v1/moisture",
        content=json.dumps(
            {
                "reading_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "moisture_percent": 12.0,
                "sequence": 1,
                "sha256_hash": "a" * 64,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": op},
    )


async def test_uppercase_batch_uuid_is_canonicalized_and_matches_batch(
    client, registered_device, session_factory
):
    bu_lower = str(uuid.uuid4())
    await _create_batch(client, bu_lower)  # batch created under canonical (lower) uuid

    # Post a reading with the UPPERCASE uuid — accepted, and stored under the
    # canonical lowercase key so it joins to the batch (not orphaned).
    r = await _post_moisture(client, bu_lower.upper(), "m-canon-1")
    assert r.status_code == 201, r.text

    async with session_factory() as s:
        rows = (
            await s.execute(
                select(MoistureReading).where(MoistureReading.batch_uuid == bu_lower)
            )
        ).scalars().all()
    assert len(rows) == 1, "reading must be stored under the canonical lowercase uuid"


async def test_malformed_batch_uuid_rejected_422(client, registered_device):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)
    r = await _post_moisture(client, "not-a-real-uuid", "m-bad-1")
    assert r.status_code == 422, r.text
