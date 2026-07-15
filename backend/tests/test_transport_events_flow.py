"""Rainbow compliance C6 — per transport-event channel.

Transport events (biomass/biochar legs: distance/weight/vehicle/fuel) are a new
one-to-many channel. While emission_factors.TRANSPORT_EVENTS_ENFORCED is False
the fuel emissions + GPS-vs-reported cross-check are AUDIT-ONLY: computed and
stored in lca_audit_json, but they do NOT change the issued credit (the existing
GPS-haversine transport penalty stays authoritative). This locks that contract in
so a later "enforce" flip is a deliberate, tested change — not an accident.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import Batch, TransportEvent
from emission_factors import (
    TRANSPORT_EVENTS_ENFORCED,
    fuel_emissions_kg_co2e,
)
from tests.remediation.crypto_utils import sign_request

# NB: no module-level asyncio mark — the fuel-emission and enforcement-flag tests
# below are synchronous unit tests. The async DB-flow tests are marked
# individually so pytest-asyncio doesn't warn on the sync ones.

OWNER = "test-device-reg"


def test_fuel_emissions_zero_when_amount_missing():
    assert fuel_emissions_kg_co2e("diesel", None) == 0.0
    assert fuel_emissions_kg_co2e("diesel", 0.0) == 0.0
    assert fuel_emissions_kg_co2e(None, 10.0) > 0.0  # unknown fuel still charged


def test_fuel_emissions_scale_with_litres_and_unknown_is_conservative():
    ten = fuel_emissions_kg_co2e("diesel", 10.0)
    twenty = fuel_emissions_kg_co2e("diesel", 20.0)
    assert twenty == pytest.approx(2 * ten)
    # Unknown fuel uses the most conservative (highest) known factor -> >= a known one.
    assert fuel_emissions_kg_co2e("rocket-fuel", 10.0) >= fuel_emissions_kg_co2e(
        "cng", 10.0
    )


def test_transport_is_not_enforced_yet():
    # Guard: the credit-affecting path must stay OFF until real factors are cited.
    assert TRANSPORT_EVENTS_ENFORCED is False


async def _post(client, path, op, payload):
    return await client.post(
        path,
        content=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Idempotency-Key": op,
            "X-Device-Id": OWNER,
            "X-Signature": sign_request(OWNER, "", "POST", path, op, payload),
        },
    )


async def _create_batch(client, bu):
    payload = {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
        "latitude": 12.0,
        "longitude": 77.0,
    }
    r = await _post(client, "/api/v1/batches", "b-" + bu[:8], payload)
    assert r.status_code == 201, r.text


async def _batch(session_factory, bu):
    async with session_factory() as s:
        return (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(uuid.UUID(bu))))
        ).scalar_one()


@pytest.mark.asyncio
async def test_transport_events_persist_and_are_many_per_batch(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)

    for i, material in enumerate(["biomass", "biochar"]):
        p = {
            "event_uuid": str(uuid.uuid4()),
            "batch_uuid": bu,
            "material": material,
            "distance_km": 30.0,
            "weight_kg": 500.0,
            "vehicle_type": "tractor",
            "fuel_type": "diesel",
            "fuel_amount_litres": 12.0,
        }
        assert (
            await _post(client, "/api/v1/transport", f"te-{bu[:6]}-{i}", p)
        ).status_code == 201

    async with session_factory() as s:
        rows = (
            (
                await s.execute(
                    select(TransportEvent).where(TransportEvent.batch_uuid == bu)
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 2  # many-per-batch

    # Audit block is populated, but the credit is NOT altered by transport events.
    b = await _batch(session_factory, bu)
    audit = json.loads(b.lca_audit_json)
    te = audit["transport_events"]
    assert te["enforced"] is False
    assert te["event_count"] == 2
    assert te["fuel_co2e_kg"] > 0.0  # 2 legs * 12 L diesel


@pytest.mark.asyncio
async def test_transport_events_do_not_change_the_credit(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)
    # Establish a yield so there is a non-zero credit to compare.
    y = {
        "yield_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "wet_yield_weight_kg": 200.0,
    }
    assert (await _post(client, "/api/v1/yield", "y-" + bu[:6], y)).status_code == 201
    credit_before = (await _batch(session_factory, bu)).net_credit_t_co2e

    p = {
        "event_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "material": "biochar",
        "distance_km": 40.0,
        "fuel_type": "diesel",
        "fuel_amount_litres": 100.0,  # large burn — must NOT dent the credit yet
    }
    assert (
        await _post(client, "/api/v1/transport", "te-" + bu[:6], p)
    ).status_code == 201

    credit_after = (await _batch(session_factory, bu)).net_credit_t_co2e
    assert credit_after == credit_before  # audit-only while unenforced


@pytest.mark.asyncio
async def test_underreported_transport_is_flagged_not_gated(
    client, registered_device, session_factory
):
    # Batch at (12,77); application far away -> large GPS transport. A single tiny
    # reported leg (<50% of GPS) should raise the audit flag but NOT gate issuance.
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)
    app = {
        "application_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "latitude": 13.0,  # ~111 km north
        "longitude": 77.0,
    }
    assert (
        await _post(client, "/api/v1/application", "app-" + bu[:6], app)
    ).status_code == 201

    p = {
        "event_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "material": "biochar",
        "distance_km": 1.0,  # grossly under the ~111 km GPS distance
    }
    assert (
        await _post(client, "/api/v1/transport", "te-" + bu[:6], p)
    ).status_code == 201

    b = await _batch(session_factory, bu)
    audit = json.loads(b.lca_audit_json)
    assert audit["transport_events"]["underreported_flag"] is True
    # Flag is audit-only — it must NOT appear in the provisional reasons.
    reasons = json.loads(b.provisional_reasons or "[]")
    assert not any("transport" in r and "under" in r for r in reasons)
