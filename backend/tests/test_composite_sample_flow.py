"""Rainbow compliance C4 — site composite pile sub-sample.

The deriver is inert by default (enforced at the C10 unified gate), so posting a
sub-sample must NOT add `missing_composite_sample` to a batch's reasons today,
and the endpoint must persist + dedupe like the other evidence channels. The
enforced counting logic is unit-tested directly.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import Batch, CompositePileSample
from corroboration import derive_composite_sample_compliance

pytestmark = pytest.mark.asyncio


def test_deriver_inert_by_default():
    # Zero samples, not enforced -> compliant, no reason.
    assert derive_composite_sample_compliance(0) == (True, None)


def test_deriver_enforced_requires_a_photographed_sample():
    assert derive_composite_sample_compliance(0, enforced=True) == (
        False,
        "missing_composite_sample",
    )
    assert derive_composite_sample_compliance(1, enforced=True) == (True, None)


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
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + bu[:8]},
    )


async def _post_sample(client, bu, op):
    return await client.post(
        "/api/v1/composite-sample",
        content=json.dumps(
            {
                "sample_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "sampled_at": datetime.now(timezone.utc).isoformat(),
                "latitude": 12.9,
                "longitude": 77.6,
                "kiln_qr": "KILN-42",
                "batch_qr": "BATCH-99",
                "sha256_hash": "b" * 64,  # photographed
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": op},
    )


async def test_composite_sample_persists_and_is_inert(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)
    assert (await _post_sample(client, bu, f"cs-{bu[:6]}-1")).status_code == 201

    async with session_factory() as s:
        rows = (
            (
                await s.execute(
                    select(CompositePileSample).where(
                        CompositePileSample.batch_uuid == bu
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert json.loads(rows[0].payload_json)["kiln_qr"] == "KILN-42"

        batch = (
            await s.execute(select(Batch).where(Batch.batch_uuid == uuid.UUID(bu)))
        ).scalar_one()
        reasons = json.loads(batch.provisional_reasons or "[]")
        # Inert by default — must NOT gate issuance yet.
        assert "missing_composite_sample" not in reasons


async def test_composite_sample_is_idempotent(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)
    op = f"cs-{bu[:6]}-dup"
    # Same sample_uuid via the same op key would 409-dedupe at the outbox; here we
    # re-post the identical idempotency key to exercise the server-side dedupe.
    r1 = await _post_sample(client, bu, op)
    assert r1.status_code == 201
    # A second identical sample_uuid triggers the IntegrityError dedupe path.
    dup = await client.post(
        "/api/v1/composite-sample",
        content=json.dumps(
            {
                "sample_uuid": json.loads(r1.request.content)["sample_uuid"],
                "batch_uuid": bu,
                "sha256_hash": "b" * 64,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": op + "-2"},
    )
    assert dup.status_code == 201
    assert dup.json()["duplicate"] is True
