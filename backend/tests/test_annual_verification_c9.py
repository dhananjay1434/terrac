"""Rainbow compliance C9 — annual / per-verification project inputs.

Keyed by (project_id, year): methane rate (3 runs), PAH/heavy metals, biomass
leakage, conversion factor, dry bulk density, quality-oversight report. Admin-
authenticated. DATA CAPTURE only — the credit-affecting fields (methane rate,
conversion factor) are NOT wired into the credit here, and the compliance
reasons are deferred to C10, so no batch's issuance changes.
"""

import json
import uuid

import pytest
from sqlalchemy.future import select

from models import AnnualVerification, Batch

pytestmark = pytest.mark.asyncio

_ADMIN = {"X-Admin-Secret": "test-admin-secret"}
_SHA = "a" * 64


async def _post(client, payload, headers=_ADMIN):
    return await client.post(
        "/api/v1/admin/annual-verification",
        content=json.dumps(payload).encode("utf-8"),
        headers=headers,
    )


async def test_requires_admin(client):
    r = await _post(
        client, {"project_id": "P1", "year": 2026}, headers={"X-Admin-Secret": "wrong"}
    )
    assert r.status_code == 401, r.text


async def test_register_then_update_is_upsert(client, session_factory):
    r1 = await _post(
        client,
        {
            "project_id": "P1",
            "year": 2026,
            "methane_rate_g_per_kg": 3.2,
            "methane_run_count": 3,
            "pah_measured": True,
            "conversion_factor": 0.25,
            "report_sha256": _SHA,
        },
    )
    assert r1.status_code == 200 and r1.json()["updated"] is False

    # Same (project, year) again -> update, not a second row.
    r2 = await _post(
        client,
        {
            "project_id": "P1",
            "year": 2026,
            "methane_rate_g_per_kg": 2.9,
            "methane_run_count": 4,
        },
    )
    assert r2.status_code == 200 and r2.json()["updated"] is True

    async with session_factory() as s:
        rows = (
            (
                await s.execute(
                    select(AnnualVerification).where(
                        AnnualVerification.project_id == "P1",
                        AnnualVerification.year == 2026,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].methane_rate_g_per_kg == 2.9
        assert rows[0].methane_run_count == 4


async def test_distinct_years_are_separate_rows(client, session_factory):
    await _post(
        client, {"project_id": "P2", "year": 2025, "methane_rate_g_per_kg": 1.0}
    )
    await _post(
        client, {"project_id": "P2", "year": 2026, "methane_rate_g_per_kg": 2.0}
    )
    async with session_factory() as s:
        rows = (
            (
                await s.execute(
                    select(AnnualVerification).where(
                        AnnualVerification.project_id == "P2"
                    )
                )
            )
            .scalars()
            .all()
        )
        assert {r.year for r in rows} == {2025, 2026}


async def test_range_checks(client):
    # conversion_factor must be > 0.
    r = await _post(
        client, {"project_id": "P3", "year": 2026, "conversion_factor": 0.0}
    )
    assert r.status_code == 422, r.text
    # year out of range.
    r2 = await _post(client, {"project_id": "P3", "year": 1999})
    assert r2.status_code == 422, r2.text


async def test_annual_verification_does_not_change_batch_provisional(
    client, registered_device, session_factory
):
    # C9 is data-capture only: recording annual verification must not gate any
    # batch (missing_annual_methane / missing_pah are deferred to C10).
    bu = str(uuid.uuid4())
    await client.post(
        "/api/v1/batches",
        content=json.dumps(
            {
                "batch_uuid": bu,
                "feedstock_species": "Lantana_camara",
                "harvest_timestamp": "2026-07-03T00:00:00Z",
                "moisture_percent": 12.0,
                "harvest_uptime_seconds": 100,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + bu[:8]},
    )
    await _post(
        client, {"project_id": "P4", "year": 2026, "methane_rate_g_per_kg": 3.0}
    )
    async with session_factory() as s:
        b = (
            await s.execute(select(Batch).where(Batch.batch_uuid == uuid.UUID(bu)))
        ).scalar_one()
    reasons = json.loads(b.provisional_reasons or "[]")
    assert "missing_annual_methane" not in reasons
    assert "missing_pah" not in reasons
