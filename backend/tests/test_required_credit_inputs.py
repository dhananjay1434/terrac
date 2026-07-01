"""Phase 7-R — credit-bearing inputs are corroborated server-side, never trusted
from the batch payload.

Phase 7 originally made ``wet_yield_kg`` / ``min_recorded_temp_c`` /
``transport_distance_km`` REQUIRED on the batch and rejected omissions with 422.
That was both temporally impossible (the client writes the batch at harvest,
before those values exist) and weaker than deriving them from the /telemetry,
/yield and /application evidence streams. Phase 7-R reverses it: omitting them is
accepted, but the batch is PROVISIONAL and earns no fabricated credit — the same
"never credit unmeasured data" guarantee, enforced by corroboration instead of a
required field. See corroboration.py + recompute_batch_credit.
"""

import json
from uuid import uuid4

import pytest


def _client_batch_payload() -> dict:
    """The batch fields the real device sends — no credit inputs."""
    return {
        "batch_uuid": str(uuid4()),
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": "2026-01-01T00:00:00Z",
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
    }


@pytest.mark.parametrize(
    "reason",
    ["wet_yield_uncorroborated", "min_temp_uncorroborated", "transport_uncorroborated"],
)
@pytest.mark.asyncio
async def test_uncorroborated_input_is_provisional_not_fabricated(
    client, registered_device, session_factory, reason
):
    """A batch with no corroborating evidence is accepted (201) but PROVISIONAL,
    and records exactly why — never a silently-fabricated credit."""
    from uuid import UUID
    from sqlalchemy.future import select
    from models import Batch

    payload = _client_batch_payload()
    r = await client.post(
        "/api/v1/batches",
        content=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Idempotency-Key": str(uuid4())},
    )
    assert r.status_code == 201, r.text
    assert r.json()["provisional"] is True

    async with session_factory() as s:
        batch = (
            await s.execute(
                select(Batch).where(Batch.batch_uuid == UUID(payload["batch_uuid"]))
            )
        ).scalar_one()
    reasons = json.loads(batch.provisional_reasons)
    assert reason in reasons
    # No evidence => no fabricated physical inputs.
    assert batch.wet_yield_kg == 0.0
    assert batch.min_recorded_temp_c == 0.0
    assert batch.transport_distance_km == 0.0
