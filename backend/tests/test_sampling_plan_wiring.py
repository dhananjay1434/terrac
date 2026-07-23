"""PR-3.3 — credit_engine wiring test for the sampling-plan gate (PR-3.1).

Mirrors test_compliance_gate_c10.py's fixture style: build a batch that
clears every OTHER C10 item, so only the sampling gate's reason can appear.
Project-scoped and config-driven — inert unless the project's RegistryConfig
sets sampling_kg_per_lab_result (no invented cadence number).
"""

import json
import uuid
from datetime import datetime, timezone

import pytest

from models import Batch, Project, RegistryConfig

pytestmark = pytest.mark.asyncio

_ADMIN = {"X-Admin-Secret": "test-admin-secret"}
_SHA = "a" * 64
_KILN = "KILN-SAMPLING"


async def _post(client, path, op, payload):
    return await client.post(
        path,
        content=json.dumps(payload).encode("utf-8"),
        headers={"X-Idempotency-Key": op},
    )


async def _admin(client, path, payload):
    return await client.post(
        path, content=json.dumps(payload).encode("utf-8"), headers=_ADMIN
    )


async def _fully_compliant_batch_with_project(client, bu, *, project_id=None):
    """Same evidence set as test_compliance_gate_c10.py's helper (clears every
    other C10 item), with an optional project_id on the batch."""
    await _admin(
        client, "/api/v1/admin/kiln", {"kiln_id": _KILN, "kiln_type": "open"}
    )
    await _post(
        client,
        "/api/v1/telemetry",
        "tel-" + bu[:8],
        {
            "telemetry_uuid": str(uuid.uuid4()),
            "batch_uuid": bu,
            "kiln_type": "open",
            "kiln_id": _KILN,
            "temperature_readings": [650.0] * 60,
            "flame_height_m": 0.3,
            "smoke_evidence": [
                {"stage": "flame_curtain", "sha256": _SHA},
                {"stage": "quenching", "sha256": _SHA},
                {"stage": "flame_height", "sha256": _SHA},
            ],
        },
    )
    await _post(
        client,
        "/api/v1/yield",
        "yld-" + bu[:8],
        {
            "yield_uuid": str(uuid.uuid4()),
            "batch_uuid": bu,
            "wet_yield_weight_kg": 100.0,
        },
    )
    app = {
        "application_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "latitude": 13.9716,
        "longitude": 77.5946,
        "delivery_date": "2026-07-03T00:00:00Z",
        "delivered_amount_kg": 50.0,
        "buyer_name": "Asha Co-op",
    }
    await _post(client, "/api/v1/application", "app-" + bu[:8], app)
    for i in range(1, 11):
        await _post(
            client,
            "/api/v1/moisture",
            f"m-{bu[:6]}-{i}",
            {
                "reading_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "moisture_percent": 12.0,
                "sequence": i,
                "sha256_hash": _SHA,
            },
        )
    await _post(
        client,
        "/api/v1/composite-sample",
        "cs-" + bu[:8],
        {"sample_uuid": str(uuid.uuid4()), "batch_uuid": bu, "sha256_hash": _SHA},
    )
    batch = {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
        "latitude": 12.9716,
        "longitude": 77.5946,
        "biomass_input_kg": 500.0,
        "biomass_measurement_method": "direct_weigh",
    }
    if project_id is not None:
        batch["project_id"] = project_id
    await _post(client, "/api/v1/batches", "b-" + bu[:8], batch)
    await _admin(
        client,
        "/api/v1/admin/lab",
        {"batch_uuid": bu, "lab_h_corg": 0.3, "organic_carbon_pct": 0.60},
    )


async def _reasons(session_factory, bu):
    from sqlalchemy import select

    async with session_factory() as s:
        b = (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(uuid.UUID(bu))))
        ).scalar_one()
        return b.provisional, json.loads(b.provisional_reasons or "[]")


async def _seed_project_with_cadence(session_factory, project_id, config_id, cadence):
    async with session_factory() as s:
        s.add(
            RegistryConfig(
                config_id=config_id,
                registry_name="Sampling Test Registry",
                methodology_version="v1",
                params_json=json.dumps({"sampling_kg_per_lab_result": cadence}),
            )
        )
        s.add(
            Project(
                project_id=project_id, name="Sampling Test Project",
                registry_config_id=config_id,
            )
        )
        await s.commit()


async def test_inert_when_project_has_no_registry_config(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    async with session_factory() as s:
        s.add(Project(project_id="samp-proj-noconfig", name="No Config"))
        await s.commit()
    await _fully_compliant_batch_with_project(
        client, bu, project_id="samp-proj-noconfig"
    )
    # Other project-scoped gates (density/methane calibration) are expected
    # to fire too — this helper doesn't satisfy those. Only the sampling
    # gate's own behavior is under test here: inert with no registry config.
    _, reasons = await _reasons(session_factory, bu)
    assert "insufficient_lab_sampling" not in reasons


async def test_undersampled_batch_is_provisional_with_reason(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    # 100 kg wet yield / 10 kg-per-sample cadence -> 10 samples required;
    # only this batch's own 1 lab result is on file.
    await _seed_project_with_cadence(
        session_factory, "samp-proj-strict", "samp-cfg-strict", 10.0
    )
    await _fully_compliant_batch_with_project(
        client, bu, project_id="samp-proj-strict"
    )
    provisional, reasons = await _reasons(session_factory, bu)
    assert provisional is True
    assert "insufficient_lab_sampling" in reasons


async def test_generously_sampled_batch_is_not_gated(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    # 100 kg wet yield / 1,000 kg-per-sample cadence -> only 1 sample
    # required; this batch's own lab result satisfies it.
    await _seed_project_with_cadence(
        session_factory, "samp-proj-loose", "samp-cfg-loose", 1_000.0
    )
    await _fully_compliant_batch_with_project(
        client, bu, project_id="samp-proj-loose"
    )
    provisional, reasons = await _reasons(session_factory, bu)
    assert "insufficient_lab_sampling" not in reasons
