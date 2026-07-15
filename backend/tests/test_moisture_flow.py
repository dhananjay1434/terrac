"""Rainbow compliance C2 — multi-sample moisture end-to-end.

Posting fewer than the required photographed moisture readings keeps the batch
PROVISIONAL with `insufficient_moisture_samples`; posting enough clears that
specific reason.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import Batch

pytestmark = pytest.mark.asyncio


async def _post_moisture(client, bu, seq):
    return await client.post(
        "/api/v1/moisture",
        content=json.dumps(
            {
                "reading_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "moisture_percent": 12.0,
                "sequence": seq,
                "sha256_hash": "a" * 64,  # photographed
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": f"m-{bu[:6]}-{seq}"},
    )


async def _create_batch(client, bu, biomass_kg):
    return await client.post(
        "/api/v1/batches",
        content=json.dumps(
            {
                "batch_uuid": bu,
                "feedstock_species": "Lantana_camara",
                "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
                "moisture_percent": 12.0,
                "harvest_uptime_seconds": 100,
                "biomass_input_kg": biomass_kg,
                "biomass_measurement_method": "direct_weigh",
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + bu[:8]},
    )


async def _reasons(session_factory, bu):
    async with session_factory() as s:
        batch = (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(uuid.UUID(bu))))
        ).scalar_one()
        return json.loads(batch.provisional_reasons or "[]")


async def test_insufficient_moisture_keeps_provisional(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu, 500.0)  # needs 10
    for seq in range(1, 10):  # only 9
        assert (await _post_moisture(client, bu, seq)).status_code == 201
    assert "insufficient_moisture_samples" in await _reasons(session_factory, bu)


async def test_enough_moisture_clears_the_reason(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu, 500.0)  # floor of 10
    for seq in range(1, 11):  # 10 photographed readings
        assert (await _post_moisture(client, bu, seq)).status_code == 201
    assert "insufficient_moisture_samples" not in await _reasons(session_factory, bu)
