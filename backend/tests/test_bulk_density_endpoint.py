"""V8 Part 4 (F) — bulk-density end-to-end: portal admin CRUD + the
credit_engine wiring (volumetric yield fallback + production_requires_valid_
density C10 gate + wet_yield_density_derived transparency flag).

Mirrors the scale-calibration end-to-end pattern in test_project_registry_c8.py
(evidence-first: telemetry posted before the batch itself, recompute runs at
batch creation and sees the already-committed evidence).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from models import Batch, Project

pytestmark = pytest.mark.asyncio


async def _login_admin(client, session_factory):
    from portal.auth import hash_password
    from models import PortalUser

    async with session_factory() as session:
        session.add(
            PortalUser(
                email="admin-density@test.local",
                password_hash=hash_password("correct-horse-battery-staple"),
                role="admin",
                disabled=False,
            )
        )
        await session.commit()
    resp = await client.post(
        "/api/v1/portal/login",
        json={"email": "admin-density@test.local", "password": "correct-horse-battery-staple"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['token']}"}


async def _post(client, path, op, payload):
    return await client.post(
        path,
        content=json.dumps(payload).encode("utf-8"),
        headers={"X-Idempotency-Key": op},
    )


async def _post_telemetry(client, bu, *, kiln_gross_capacity, temps=None):
    return await _post(
        client,
        "/api/v1/telemetry",
        "tel-" + bu[:8],
        {
            "telemetry_uuid": str(uuid.uuid4()),
            "batch_uuid": bu,
            "kiln_gross_capacity": kiln_gross_capacity,
            "temperature_readings": temps or [650.0] * 60,
        },
    )


async def _post_yield(client, bu, wet_yield_weight_kg):
    return await _post(
        client,
        "/api/v1/yield",
        "yld-" + bu[:8],
        {
            "yield_uuid": str(uuid.uuid4()),
            "batch_uuid": bu,
            "wet_yield_weight_kg": wet_yield_weight_kg,
        },
    )


async def _post_batch(client, bu, project_id):
    return await client.post(
        "/api/v1/batches",
        content=json.dumps(
            {
                "batch_uuid": bu,
                "feedstock_species": "Lantana_camara",
                "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
                "moisture_percent": 12.0,
                "harvest_uptime_seconds": 100,
                "project_id": project_id,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + bu[:8]},
    )


async def _fetch_batch(session_factory, bu):
    async with session_factory() as s:
        return (
            await s.execute(select(Batch).where(Batch.batch_uuid == bu))
        ).scalar_one()


async def _seed_project(session_factory, project_id):
    async with session_factory() as s:
        s.add(Project(project_id=project_id, name=project_id))
        await s.commit()


# ---------------------------------------------------------------------------
# Portal admin CRUD
# ---------------------------------------------------------------------------


async def test_create_bulk_density_test_requires_admin(client):
    resp = await client.post(
        "/api/v1/portal/bulk-density-tests",
        json={"test_uuid": "t1", "project_id": "p1", "density_kg_per_l": 0.25},
    )
    assert resp.status_code == 401


async def test_create_and_list_bulk_density_test(client, session_factory):
    headers = await _login_admin(client, session_factory)
    resp = await client.post(
        "/api/v1/portal/bulk-density-tests",
        json={
            "test_uuid": "t-create-1",
            "project_id": "proj-density-list",
            "density_kg_per_l": 0.25,
            "valid_until": "2030-01-01T00:00:00Z",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["density_kg_per_l"] == 0.25

    list_resp = await client.get(
        "/api/v1/portal/bulk-density-tests?project_id=proj-density-list",
        headers=headers,
    )
    assert list_resp.status_code == 200
    ids = [t["test_uuid"] for t in list_resp.json()["bulk_density_tests"]]
    assert "t-create-1" in ids


async def test_duplicate_bulk_density_test_rejected(client, session_factory):
    headers = await _login_admin(client, session_factory)
    body = {"test_uuid": "t-dup-1", "project_id": "p1", "density_kg_per_l": 0.25}
    r1 = await client.post("/api/v1/portal/bulk-density-tests", json=body, headers=headers)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/portal/bulk-density-tests", json=body, headers=headers)
    assert r2.status_code == 409


# ---------------------------------------------------------------------------
# credit_engine wiring: gate + volumetric fallback
# ---------------------------------------------------------------------------


async def test_no_project_is_inert(client, session_factory):
    """A batch with no project_id is never gated by density, and never
    attempts the volumetric fallback (mirrors test_no_scale_linkage_is_inert)."""
    bu = str(uuid.uuid4())
    await _post_telemetry(client, bu, kiln_gross_capacity=200.0)
    resp = await _post_batch(client, bu, project_id=None)
    assert resp.status_code in (200, 201)

    b = await _fetch_batch(session_factory, bu)
    reasons = json.loads(b.provisional_reasons or "[]")
    assert "production_requires_valid_density" not in reasons
    assert "wet_yield_density_derived" not in reasons


async def test_project_without_density_test_gates(client, session_factory):
    project_id = "proj-density-nogate-" + str(uuid.uuid4())[:8]
    await _seed_project(session_factory, project_id)
    bu = str(uuid.uuid4())
    await _post_telemetry(client, bu, kiln_gross_capacity=200.0)
    await _post_batch(client, bu, project_id=project_id)

    b = await _fetch_batch(session_factory, bu)
    reasons = json.loads(b.provisional_reasons or "[]")
    assert "production_requires_valid_density" in reasons


async def test_expired_density_test_gates(client, session_factory):
    headers = await _login_admin(client, session_factory)
    project_id = "proj-density-expired-" + str(uuid.uuid4())[:8]
    await _seed_project(session_factory, project_id)
    await client.post(
        "/api/v1/portal/bulk-density-tests",
        json={
            "test_uuid": str(uuid.uuid4()),
            "project_id": project_id,
            "density_kg_per_l": 0.25,
            "valid_until": "2020-01-01T00:00:00Z",
        },
        headers=headers,
    )
    bu = str(uuid.uuid4())
    await _post_telemetry(client, bu, kiln_gross_capacity=200.0)
    await _post_batch(client, bu, project_id=project_id)

    b = await _fetch_batch(session_factory, bu)
    reasons = json.loads(b.provisional_reasons or "[]")
    assert "production_requires_valid_density" in reasons


async def test_in_date_density_clears_gate_and_derives_yield(client, session_factory):
    """The core F feature: an in-date density test + telemetry-declared kiln
    volume, with NO direct crane-scale weight, derives wet_yield_kg = volume
    × density, clears the gate, and flags the derivation transparently."""
    headers = await _login_admin(client, session_factory)
    project_id = "proj-density-ok-" + str(uuid.uuid4())[:8]
    await _seed_project(session_factory, project_id)
    await client.post(
        "/api/v1/portal/bulk-density-tests",
        json={
            "test_uuid": str(uuid.uuid4()),
            "project_id": project_id,
            "density_kg_per_l": 0.25,
            "valid_until": "2030-01-01T00:00:00Z",
        },
        headers=headers,
    )
    bu = str(uuid.uuid4())
    await _post_telemetry(client, bu, kiln_gross_capacity=200.0)
    # Deliberately NO /api/v1/yield post — this batch has no direct weight.
    await _post_batch(client, bu, project_id=project_id)

    b = await _fetch_batch(session_factory, bu)
    reasons = json.loads(b.provisional_reasons or "[]")
    assert "production_requires_valid_density" not in reasons
    assert "wet_yield_density_derived" in reasons
    assert "wet_yield_uncorroborated" not in reasons
    assert b.wet_yield_kg == pytest.approx(200.0 * 0.25)  # 50.0 kg
    assert b.net_credit_t_co2e != 0.0


async def test_direct_yield_takes_precedence_over_density_fallback(client, session_factory):
    """A batch WITH a direct crane-scale weight must never be overridden by
    the volumetric fallback, even when an in-date density test exists."""
    headers = await _login_admin(client, session_factory)
    project_id = "proj-density-direct-" + str(uuid.uuid4())[:8]
    await _seed_project(session_factory, project_id)
    await client.post(
        "/api/v1/portal/bulk-density-tests",
        json={
            "test_uuid": str(uuid.uuid4()),
            "project_id": project_id,
            "density_kg_per_l": 0.25,
            "valid_until": "2030-01-01T00:00:00Z",
        },
        headers=headers,
    )
    bu = str(uuid.uuid4())
    await _post_telemetry(client, bu, kiln_gross_capacity=200.0)
    await _post_yield(client, bu, 999.0)  # direct weight, deliberately != volume*density
    await _post_batch(client, bu, project_id=project_id)

    b = await _fetch_batch(session_factory, bu)
    reasons = json.loads(b.provisional_reasons or "[]")
    assert "wet_yield_density_derived" not in reasons
    assert b.wet_yield_kg == pytest.approx(999.0)
