"""Rainbow compliance C1 — biomass input amount + measurement method.

The methodology requires the biomass AMOUNT (direct-weighed or via yield
conversion). These are additive/optional on the batch; they persist on the Batch
row for downstream compliance evaluation (C10).
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import Batch

pytestmark = pytest.mark.asyncio


def _payload(bu, **over):
    p = {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
    }
    p.update(over)
    return p


async def test_biomass_input_persists(client, registered_device, session_factory):
    bu = str(uuid.uuid4())
    r = await client.post(
        "/api/v1/batches",
        content=json.dumps(
            _payload(
                bu, biomass_input_kg=250.0, biomass_measurement_method="direct_weigh"
            )
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "bm-" + bu[:8]},
    )
    assert r.status_code == 201, r.text
    async with session_factory() as s:
        batch = (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(uuid.UUID(bu))))
        ).scalar_one()
    assert batch.biomass_input_kg == 250.0
    assert batch.biomass_measurement_method == "direct_weigh"


async def test_biomass_method_enum_validated(client, registered_device):
    bu = str(uuid.uuid4())
    r = await client.post(
        "/api/v1/batches",
        content=json.dumps(
            _payload(bu, biomass_measurement_method="eyeballed_it")
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "bm-bad-" + bu[:8]},
    )
    assert r.status_code == 422, r.text


async def test_biomass_input_optional(client, registered_device):
    # Backward-compatible: omitting biomass fields is still accepted.
    bu = str(uuid.uuid4())
    r = await client.post(
        "/api/v1/batches",
        content=json.dumps(_payload(bu)).encode("utf-8"),
        headers={"X-Idempotency-Key": "bm-none-" + bu[:8]},
    )
    assert r.status_code == 201, r.text
