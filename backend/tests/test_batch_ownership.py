"""Security regression — evidence endpoints enforce batch ownership.

The evidence channels (telemetry / yield / moisture / application / metadata /
composite-sample) authenticate the caller but historically never checked that
the caller OWNS the batch the evidence is anchored to. Since the carbon credit
is corroborated server-side from these streams, any enrolled device could
inject rows into a victim's batch and move its credit. This locks in the fix:

  * a DIFFERENT enrolled device anchoring to a batch owned by someone else -> 403
  * the OWNER posting to its own batch                                     -> 201
  * evidence for a batch that does not exist yet (evidence-first)          -> 201
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import (
    CompositePileSample,
    EndUseApplication,
    MoistureReading,
    PyrolysisTelemetry,
    SystemMetadata,
    YieldMetrics,
)
from tests.remediation.crypto_utils import sign_request

pytestmark = pytest.mark.asyncio

OWNER = "test-device-reg"  # seeded + enrolled by conftest; the default signer
OTHER = "test-device-1"  # also enrolled with the same test key by conftest


def _signed_headers(device_id: str, path: str, op: str, payload: dict) -> dict:
    return {
        "X-Idempotency-Key": op,
        "X-Device-Id": device_id,
        "X-Signature": sign_request(device_id, "", "POST", path, op, payload),
    }


async def _post(client, device_id, path, op, payload):
    # Body MUST be the exact bytes whose hash was signed.
    return await client.post(
        path,
        content=json.dumps(payload).encode("utf-8"),
        headers=_signed_headers(device_id, path, op, payload),
    )


async def _create_owned_batch(client, bu):
    payload = {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
    }
    op = "batch-" + bu[:8]
    r = await _post(client, OWNER, "/api/v1/batches", op, payload)
    assert r.status_code == 201, r.text


# (endpoint path, payload builder keyed on batch_uuid, ORM model, batch_uuid col)
def _cases(bu):
    return [
        (
            "/api/v1/telemetry",
            {"telemetry_uuid": str(uuid.uuid4()), "batch_uuid": bu},
            PyrolysisTelemetry,
        ),
        (
            "/api/v1/yield",
            {"yield_uuid": str(uuid.uuid4()), "batch_uuid": bu},
            YieldMetrics,
        ),
        (
            "/api/v1/moisture",
            {
                "reading_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "moisture_percent": 12.0,
                "sequence": 1,
            },
            MoistureReading,
        ),
        (
            "/api/v1/application",
            {"application_uuid": str(uuid.uuid4()), "batch_uuid": bu},
            EndUseApplication,
        ),
        (
            "/api/v1/metadata",
            {"batch_uuid": bu},
            SystemMetadata,
        ),
        (
            "/api/v1/composite-sample",
            {"sample_uuid": str(uuid.uuid4()), "batch_uuid": bu},
            CompositePileSample,
        ),
    ]


async def test_foreign_device_cannot_inject_evidence(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _create_owned_batch(client, bu)

    for i, (path, payload, model) in enumerate(_cases(bu)):
        op = f"atk-{bu[:6]}-{i}"
        r = await _post(client, OTHER, path, op, payload)
        assert r.status_code == 403, (
            f"{path} should be 403, got {r.status_code} {r.text}"
        )
        assert r.json()["detail"] == "not_your_batch", path

        # And the row must NOT have been persisted.
        async with session_factory() as s:
            rows = (
                (await s.execute(select(model).where(model.batch_uuid == bu)))
                .scalars()
                .all()
            )
            assert rows == [], f"{path} persisted a foreign-device row"


async def test_owner_can_post_its_own_evidence(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _create_owned_batch(client, bu)
    for i, (path, payload, _model) in enumerate(_cases(bu)):
        op = f"own-{bu[:6]}-{i}"
        r = await _post(client, OWNER, path, op, payload)
        assert r.status_code == 201, f"{path} owner post: {r.status_code} {r.text}"


async def test_evidence_first_for_absent_batch_is_allowed(client, registered_device):
    # No batch created — a legitimate evidence-first upload must still be accepted;
    # create_batch establishes ownership from its own signature when it arrives.
    bu = str(uuid.uuid4())
    for i, (path, payload, _model) in enumerate(_cases(bu)):
        op = f"ef-{bu[:6]}-{i}"
        r = await _post(client, OTHER, path, op, payload)
        assert r.status_code == 201, f"{path} evidence-first: {r.status_code} {r.text}"
