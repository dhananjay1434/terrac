"""Rainbow compliance C8 — project registry (admin console).

Project-setup data: kilns, operator training, supervisor visits, scale
calibrations. Admin-authenticated (never the field app). C8 lands the registry
ONLY — the compliance reasons it enables (unregistered_kiln /
scale_calibration_expired) are deferred to the C10 unified gate, so no batch's
issuance changes here.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import Batch, Kiln, OperatorTraining, ScaleCalibration, SupervisorVisit

pytestmark = pytest.mark.asyncio

_ADMIN = {"X-Admin-Secret": "test-admin-secret"}
_SHA = "a" * 64


async def _post(client, path, payload, headers=_ADMIN):
    return await client.post(
        path, content=json.dumps(payload).encode("utf-8"), headers=headers
    )


# ---- auth ----------------------------------------------------------------


@pytest.mark.parametrize(
    "path,body",
    [
        ("/api/v1/admin/kiln", {"kiln_id": "K1"}),
        ("/api/v1/admin/operator-training", {"record_uuid": "r1"}),
        ("/api/v1/admin/supervisor-visit", {"visit_uuid": "v1"}),
        ("/api/v1/admin/scale-calibration", {"calibration_uuid": "c1"}),
    ],
)
async def test_registry_requires_admin(client, path, body):
    r = await _post(client, path, body, headers={"X-Admin-Secret": "wrong"})
    assert r.status_code == 401, r.text


# ---- kiln upsert ---------------------------------------------------------


async def test_kiln_register_then_update(client, session_factory):
    r1 = await _post(
        client,
        "/api/v1/admin/kiln",
        {
            "kiln_id": "KILN-1",
            "material": "steel",
            "weight_kg": 300.0,
            "lifetime_years": 10.0,
            "kiln_type": "open",
        },
    )
    assert r1.status_code == 200 and r1.json()["updated"] is False

    # Same kiln_id again = update on change (methodology: updated when kilns change).
    r2 = await _post(
        client,
        "/api/v1/admin/kiln",
        {"kiln_id": "KILN-1", "material": "stainless", "weight_kg": 320.0},
    )
    assert r2.status_code == 200 and r2.json()["updated"] is True

    async with session_factory() as s:
        rows = (
            (await s.execute(select(Kiln).where(Kiln.kiln_id == "KILN-1")))
            .scalars()
            .all()
        )
        assert len(rows) == 1  # upsert, not duplicate
        assert rows[0].material == "stainless"
        assert rows[0].weight_kg == 320.0


# ---- one-to-many records + dedupe ---------------------------------------


async def test_operator_training_persists_and_dedupes(client, session_factory):
    rid = str(uuid.uuid4())
    body = {"record_uuid": rid, "operator_id": "OP-7", "training_type": "safety"}
    assert (await _post(client, "/api/v1/admin/operator-training", body)).json()[
        "duplicate"
    ] is False
    # same record_uuid -> dedupe
    assert (await _post(client, "/api/v1/admin/operator-training", body)).json()[
        "duplicate"
    ] is True
    async with session_factory() as s:
        rows = (
            (
                await s.execute(
                    select(OperatorTraining).where(OperatorTraining.record_uuid == rid)
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1


async def test_supervisor_visit_persists(client, session_factory):
    vid = str(uuid.uuid4())
    r = await _post(
        client,
        "/api/v1/admin/supervisor-visit",
        {"visit_uuid": vid, "kiln_id": "KILN-1", "notes": "ok", "report_sha256": _SHA},
    )
    assert r.status_code == 201, r.text
    async with session_factory() as s:
        row = (
            await s.execute(
                select(SupervisorVisit).where(SupervisorVisit.visit_uuid == vid)
            )
        ).scalar_one()
        assert row.report_sha256 == _SHA


async def test_scale_calibration_parses_validity(client, session_factory):
    cid = str(uuid.uuid4())
    r = await _post(
        client,
        "/api/v1/admin/scale-calibration",
        {
            "calibration_uuid": cid,
            "scale_id": "SCALE-3",
            "calibrated_at": "2026-01-01T00:00:00Z",
            "valid_until": "2027-01-01T00:00:00Z",
            "report_sha256": _SHA,
        },
    )
    assert r.status_code == 201, r.text
    async with session_factory() as s:
        row = (
            await s.execute(
                select(ScaleCalibration).where(ScaleCalibration.calibration_uuid == cid)
            )
        ).scalar_one()
        assert row.valid_until.year == 2027


async def test_scale_calibration_bad_timestamp_is_400(client):
    r = await _post(
        client,
        "/api/v1/admin/scale-calibration",
        {"calibration_uuid": str(uuid.uuid4()), "valid_until": "not-a-date"},
    )
    assert r.status_code == 400, r.text


# ---- registry does NOT gate issuance yet --------------------------------


async def test_registry_does_not_change_batch_provisional(
    client, registered_device, session_factory
):
    # A batch with a kiln_id that is NOT registered must be unaffected by C8
    # (unregistered_kiln is deferred to C10).
    bu = str(uuid.uuid4())
    await client.post(
        "/api/v1/telemetry",
        content=json.dumps(
            {
                "telemetry_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "kiln_type": "open",
                "kiln_id": "UNREGISTERED-KILN",
                "temperature_readings": [650.0] * 60,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "tel-" + bu[:8]},
    )
    await client.post(
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
    async with session_factory() as s:
        b = (
            await s.execute(select(Batch).where(Batch.batch_uuid == uuid.UUID(bu)))
        ).scalar_one()
    reasons = json.loads(b.provisional_reasons or "[]")
    assert "unregistered_kiln" not in reasons
    assert "scale_calibration_expired" not in reasons
