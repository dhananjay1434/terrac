"""Rainbow compliance C7 — per-batch lab results via the admin channel.

The integrity fix: organic Corg was a hardcoded species CONSTANT (CORG_TABLE) —
the same class of self-asserted assumption the H:Corg channel already closed. C7
accepts a lab-measured organic_carbon_pct on the admin-authenticated /admin/lab
channel and PREFERS it in the credit; its absence keeps the batch provisional
(assumed_corg). Lab data is never device-asserted.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import Batch
from lca_engine import calculate_carbon_credit, get_corg

pytestmark = pytest.mark.asyncio

_ADMIN = {"X-Admin-Secret": "test-admin-secret"}


# ---- pure LCA: lab Corg replaces the species constant ---------------------


def test_corg_override_replaces_species_constant():
    species = calculate_carbon_credit(
        wet_yield_kg=100.0,
        moisture_percent=12.0,
        min_recorded_temp_c=210.0,
        h_corg_ratio=0.3,
        feedstock_species="Lantana_camara",
    )
    assert species.corg_assumed is True
    assert species.corg_pct == get_corg("Lantana_camara")

    lab = calculate_carbon_credit(
        wet_yield_kg=100.0,
        moisture_percent=12.0,
        min_recorded_temp_c=210.0,
        h_corg_ratio=0.3,
        feedstock_species="Lantana_camara",
        corg_override=0.45,
    )
    assert lab.corg_assumed is False
    assert lab.corg_pct == 0.45
    # A different Corg must change the credit (proves it actually feeds the math).
    assert lab.net_credit_t_co2e != species.net_credit_t_co2e


# ---- admin channel --------------------------------------------------------


async def _post(client, path, op, payload):
    return await client.post(
        path,
        content=json.dumps(payload).encode("utf-8"),
        headers={"X-Idempotency-Key": op},
    )


async def _corroborated_batch(client, bu):
    # min temp
    await _post(
        client,
        "/api/v1/telemetry",
        "tel-" + bu[:8],
        {
            "telemetry_uuid": str(uuid.uuid4()),
            "batch_uuid": bu,
            "temperature_readings": [650.0] * 60,
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
    await _post(
        client,
        "/api/v1/application",
        "app-" + bu[:8],
        {
            "application_uuid": str(uuid.uuid4()),
            "batch_uuid": bu,
            "latitude": 12.98,
            "longitude": 77.60,
        },
    )
    await _post(
        client,
        "/api/v1/batches",
        "b-" + bu[:8],
        {
            "batch_uuid": bu,
            "feedstock_species": "Lantana_camara",
            "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
            "moisture_percent": 12.0,
            "harvest_uptime_seconds": 100,
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )


async def _batch(session_factory, bu):
    async with session_factory() as s:
        return (
            await s.execute(select(Batch).where(Batch.batch_uuid == uuid.UUID(bu)))
        ).scalar_one()


async def test_lab_corg_is_preferred_and_clears_assumed_corg(
    client, registered_device, session_factory
):
    # Focus: the C7 organic-Corg reason clears and the lab value feeds the credit.
    # (Full non-provisional additionally needs C2 moisture evidence, which this
    # helper deliberately omits — see test_full_lab_channel_clears_provisional in
    # test_lab_hcorg_channel.py for the end-to-end issuable case.)
    bu = str(uuid.uuid4())
    await _corroborated_batch(client, bu)
    before = await _batch(session_factory, bu)
    assert "assumed_corg" in json.loads(before.provisional_reasons)

    r = await client.post(
        "/api/v1/admin/lab",
        content=json.dumps(
            {"batch_uuid": bu, "lab_h_corg": 0.3, "organic_carbon_pct": 0.62}
        ).encode("utf-8"),
        headers=_ADMIN,
    )
    assert r.status_code == 200, r.text

    after = await _batch(session_factory, bu)
    assert after.organic_carbon_pct == 0.62
    reasons = json.loads(after.provisional_reasons or "[]")
    # Both lab permanence assumptions cleared by the full lab channel.
    assert "assumed_corg" not in reasons
    assert "assumed_h_corg" not in reasons
    # Credit recomputed against the lab Corg (0.62 != species 0.60) → changed.
    assert after.net_credit_t_co2e != before.net_credit_t_co2e


async def test_lab_channel_persists_verification_fields(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _corroborated_batch(client, bu)
    r = await client.post(
        "/api/v1/admin/lab",
        content=json.dumps(
            {
                "batch_uuid": bu,
                "organic_carbon_pct": 0.60,
                "biochar_moisture_samples": [2.1, 2.4, 2.0],
                "dry_bulk_density": 420.0,
                "inertinite_pct": 55.0,
                "residual_corg_pct": 78.0,
                "ro_measurements_count": 512,
            }
        ).encode("utf-8"),
        headers=_ADMIN,
    )
    assert r.status_code == 200, r.text
    b = await _batch(session_factory, bu)
    assert json.loads(b.biochar_moisture_samples_json) == [2.1, 2.4, 2.0]
    assert b.dry_bulk_density == 420.0
    assert b.inertinite_pct == 55.0
    assert b.ro_measurements_count == 512


async def test_lab_channel_requires_admin(client, registered_device):
    bu = str(uuid.uuid4())
    r = await client.post(
        "/api/v1/admin/lab",
        content=json.dumps({"batch_uuid": bu, "organic_carbon_pct": 0.6}).encode(
            "utf-8"
        ),
        headers={"X-Admin-Secret": "wrong"},
    )
    assert r.status_code == 401, r.text


async def test_lab_channel_range_checks(client, registered_device):
    bu = str(uuid.uuid4())
    # Corg > 1.0 is impossible for a fraction.
    r = await client.post(
        "/api/v1/admin/lab",
        content=json.dumps({"batch_uuid": bu, "organic_carbon_pct": 1.5}).encode(
            "utf-8"
        ),
        headers=_ADMIN,
    )
    assert r.status_code == 422, r.text
    # Fewer than 3 moisture samples violates the methodology minimum.
    r2 = await client.post(
        "/api/v1/admin/lab",
        content=json.dumps(
            {"batch_uuid": bu, "biochar_moisture_samples": [2.0, 2.1]}
        ).encode("utf-8"),
        headers=_ADMIN,
    )
    assert r2.status_code == 422, r2.text


async def test_lab_channel_unknown_batch_404(client, registered_device):
    r = await client.post(
        "/api/v1/admin/lab",
        content=json.dumps(
            {"batch_uuid": str(uuid.uuid4()), "organic_carbon_pct": 0.6}
        ).encode("utf-8"),
        headers=_ADMIN,
    )
    assert r.status_code == 404, r.text


# ---- T1.9: lab biochar-moisture requires >= 3 samples -------------------


async def test_lab_moisture_fewer_than_three_samples_rejected(
    client, registered_device
):
    bu = str(uuid.uuid4())
    r = await client.post(
        "/api/v1/admin/lab",
        content=json.dumps(
            {"batch_uuid": bu, "biochar_moisture_samples": [11.0, 12.0]}
        ).encode("utf-8"),
        headers=_ADMIN,
    )
    assert r.status_code == 422, r.text


async def test_lab_moisture_three_samples_accepted(client, registered_device):
    bu = str(uuid.uuid4())
    await _corroborated_batch(client, bu)
    r = await client.post(
        "/api/v1/admin/lab",
        content=json.dumps(
            {"batch_uuid": bu, "biochar_moisture_samples": [11.0, 12.0, 13.0]}
        ).encode("utf-8"),
        headers=_ADMIN,
    )
    assert r.status_code == 200, r.text


async def test_lab_moisture_omitted_is_ok(client, registered_device):
    bu = str(uuid.uuid4())
    await _corroborated_batch(client, bu)
    r = await client.post(
        "/api/v1/admin/lab",
        content=json.dumps({"batch_uuid": bu, "organic_carbon_pct": 0.6}).encode(
            "utf-8"
        ),
        headers=_ADMIN,
    )
    assert r.status_code == 200, r.text
