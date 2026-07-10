"""P1-B5b — previously-unbounded numeric fields now reject absurd values.

The global body-size middleware already caps total payload size; these bounds
add semantic range validation so an out-of-physical-range float (which could
skew downstream math or just be nonsense) is a clean 422 rather than stored.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.asyncio


async def test_out_of_range_telemetry_min_temp_rejected(client, registered_device):
    r = await client.post(
        "/api/v1/telemetry",
        content=json.dumps(
            {
                "telemetry_uuid": str(uuid.uuid4()),
                "batch_uuid": str(uuid.uuid4()),
                "min_temp": 1e9,  # far beyond the -50..1500 C bound
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "t-bound-" + uuid.uuid4().hex[:6]},
    )
    assert r.status_code == 422, r.text


async def test_absurd_batch_azimuth_rejected(client, registered_device):
    r = await client.post(
        "/api/v1/batches",
        content=json.dumps(
            {
                "batch_uuid": str(uuid.uuid4()),
                "feedstock_species": "Lantana_camara",
                "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
                "moisture_percent": 12.0,
                "harvest_uptime_seconds": 100,
                "azimuth": 1e9,  # far beyond the +/-360 bound
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-bound-" + uuid.uuid4().hex[:6]},
    )
    assert r.status_code == 422, r.text
