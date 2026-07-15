"""Rainbow T1.1: batch->project/scale linkage — additive & backward compatible.

The linkage columns (project_id, scale_id) are optional on the batch payload.
When supplied they persist and enable the project-scoped C8/C9 gates; when
omitted (the deployed-client shape) the batch behaves exactly as before and none
of the project-scoped reasons appear.
"""

import json
import uuid as _uuid

import pytest
from sqlalchemy.future import select

from models import Batch

pytestmark = pytest.mark.asyncio


def _batch_payload(**over):
    p = {
        "batch_uuid": str(_uuid.uuid4()),
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": "2026-07-01T10:00:00+05:30",
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
    }
    p.update(over)
    return p


async def _post_batch(client, payload):
    return await client.post(
        "/api/v1/batches",
        content=json.dumps(payload).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + payload["batch_uuid"][:8]},
    )


async def _load(session_factory, bu):
    async with session_factory() as s:
        return (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(_uuid.UUID(bu))))
        ).scalar_one()


async def test_batch_accepts_and_persists_linkage(
    client, registered_device, session_factory
):
    payload = _batch_payload(project_id="proj-khp-01", scale_id="scale-7")
    r = await _post_batch(client, payload)
    assert r.status_code == 201, r.text
    row = await _load(session_factory, payload["batch_uuid"])
    assert row.project_id == "proj-khp-01"
    assert row.scale_id == "scale-7"


async def test_legacy_payload_without_linkage_unchanged(
    client, registered_device, session_factory
):
    payload = _batch_payload()  # no project_id/scale_id — the deployed-client shape
    r = await _post_batch(client, payload)
    assert r.status_code == 201, r.text
    row = await _load(session_factory, payload["batch_uuid"])
    assert row.project_id is None and row.scale_id is None
    # Crucially: no project-scoped reasons appear for an unlinked batch.
    reasons = json.loads(row.provisional_reasons or "[]")
    assert "scale_calibration_expired" not in reasons
    assert "missing_annual_methane" not in reasons
    assert "missing_pah" not in reasons


async def test_empty_string_linkage_is_rejected(client, registered_device):
    # min_length=1 guards against empty-string project ids sneaking through.
    r = await _post_batch(client, _batch_payload(project_id=""))
    assert r.status_code == 422, r.text
