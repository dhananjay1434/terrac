"""PR-4.3 — credit_engine wiring + regression pin for the methodology switch.

DEFAULT (no project, or a project whose RegistryConfig.methodology_version
names neither known methodology) must reproduce EXACTLY today's behavior:
the full Rainbow C10-extras gate set applies. Only a project an admin has
deliberately pointed at a CSI-labeled RegistryConfig excludes those
Rainbow-labeled extras — and even then, the CORE corroboration checks
(composite sample, delivery/buyer, moisture, etc. — always-on `assemble()`
params, not C10 extras) still gate every methodology equally.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest

from models import Batch, Project, RegistryConfig

pytestmark = pytest.mark.asyncio

_ADMIN = {"X-Admin-Secret": "test-admin-secret"}
_SHA = "a" * 64


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


async def _batch_missing_kiln_registration_and_composite(
    client, bu, *, project_id=None, register_kiln=True, composite=True
):
    """A batch that clears every OTHER item; kiln-registration (a c10_reasons
    Rainbow extra) and composite-sample (a core assemble() param) are
    independently toggleable so each can be isolated."""
    kiln_id = "KILN-" + bu[:8]
    if register_kiln:
        await _admin(
            client, "/api/v1/admin/kiln", {"kiln_id": kiln_id, "kiln_type": "open"}
        )
    await _post(
        client,
        "/api/v1/telemetry",
        "tel-" + bu[:8],
        {
            "telemetry_uuid": str(uuid.uuid4()),
            "batch_uuid": bu,
            "kiln_type": "open",
            "kiln_id": kiln_id,
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
        {"yield_uuid": str(uuid.uuid4()), "batch_uuid": bu, "wet_yield_weight_kg": 100.0},
    )
    await _post(
        client,
        "/api/v1/application",
        "app-" + bu[:8],
        {
            "application_uuid": str(uuid.uuid4()),
            "batch_uuid": bu,
            "latitude": 13.9716,
            "longitude": 77.5946,
            "delivery_date": "2026-07-03T00:00:00Z",
            "delivered_amount_kg": 50.0,
            "buyer_name": "Asha Co-op",
        },
    )
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
    if composite:
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


async def _seed_project(session_factory, project_id, *, methodology_version=None):
    async with session_factory() as s:
        if methodology_version is not None:
            config_id = f"cfg-{project_id}"
            s.add(
                RegistryConfig(
                    config_id=config_id,
                    registry_name="Methodology Wiring Test Registry",
                    methodology_version=methodology_version,
                    params_json="{}",
                )
            )
            s.add(
                Project(
                    project_id=project_id, name=project_id,
                    registry_config_id=config_id,
                )
            )
        else:
            s.add(Project(project_id=project_id, name=project_id))
        await s.commit()


async def test_default_methodology_regression_pin_gates_on_kiln_registration(
    client, registered_device, session_factory
):
    """Regression pin: a project with NO registry_config (today's actual
    state for every existing project) must still gate on the Rainbow
    'unregistered_kiln' extra exactly as before this Part."""
    bu = str(uuid.uuid4())
    await _seed_project(session_factory, "meth-proj-default")
    await _batch_missing_kiln_registration_and_composite(
        client, bu, project_id="meth-proj-default", register_kiln=False
    )
    provisional, reasons = await _reasons(session_factory, bu)
    assert provisional is True
    assert "unregistered_kiln" in reasons


async def test_rainbow_methodology_gates_same_as_default(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _seed_project(
        session_factory, "meth-proj-rainbow", methodology_version="Rainbow"
    )
    await _batch_missing_kiln_registration_and_composite(
        client, bu, project_id="meth-proj-rainbow", register_kiln=False
    )
    provisional, reasons = await _reasons(session_factory, bu)
    assert provisional is True
    assert "unregistered_kiln" in reasons


async def test_csi_methodology_excludes_kiln_registration_extra(
    client, registered_device, session_factory
):
    """A project deliberately wired to a CSI-labeled RegistryConfig excludes
    the Rainbow-labeled c10_reasons — 'unregistered_kiln' is one of them."""
    bu = str(uuid.uuid4())
    await _seed_project(
        session_factory, "meth-proj-csi", methodology_version="CSI-3.2"
    )
    await _batch_missing_kiln_registration_and_composite(
        client, bu, project_id="meth-proj-csi", register_kiln=False
    )
    _, reasons = await _reasons(session_factory, bu)
    assert "unregistered_kiln" not in reasons


async def test_csi_methodology_still_gates_on_core_composite_sample(
    client, registered_device, session_factory
):
    """CSI excludes Rainbow's C10 extras but NOT the core `assemble()`
    corroboration checks — missing_composite_sample still gates."""
    bu = str(uuid.uuid4())
    await _seed_project(
        session_factory, "meth-proj-csi-core", methodology_version="CSI-3.2"
    )
    await _batch_missing_kiln_registration_and_composite(
        client, bu, project_id="meth-proj-csi-core", composite=False
    )
    provisional, reasons = await _reasons(session_factory, bu)
    assert provisional is True
    assert "missing_composite_sample" in reasons
