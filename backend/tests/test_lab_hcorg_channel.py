"""Phase 8-R — lab H:Corg is authenticated + range-checked, never client-asserted.

The permanence ratio determines issuance, so it must not be self-asserted by the
device: it arrives only on the admin-authenticated /api/v1/admin/lab-hcorg channel,
is range-checked, and only then can clear a batch's PROVISIONAL status.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import Batch

pytestmark = pytest.mark.asyncio

_ADMIN = {"X-Admin-Secret": "test-admin-secret"}  # from conftest env shim


def _batch_payload(bu, lat=12.9716, lon=77.5946):
    return {
        "sourcing_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 14.5,
        "moisture_compliant": True,
        "photo_path": "/x.jpg",
        "sha256_hash": "a" * 64,
        "latitude": lat,
        "longitude": lon,
        "harvest_uptime_seconds": 3600,
        # C1 (enforced at C10): biomass input amount + method.
        "biomass_input_kg": 500.0,
        "biomass_measurement_method": "direct_weigh",
    }


async def _corroborate(client, bu, lat=12.9716, lon=77.5946):
    await client.post(
        "/api/v1/telemetry",
        content=json.dumps(
            {
                "telemetry_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "temperature_readings": [650.0] * 60,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "tel-" + bu[:8]},
    )
    await client.post(
        "/api/v1/yield",
        content=json.dumps(
            {
                "yield_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "wet_yield_weight_kg": 100.0,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "yld-" + bu[:8]},
    )
    await client.post(
        "/api/v1/application",
        content=json.dumps(
            {
                "application_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "latitude": lat + 1.0,
                "longitude": lon,
                # C5 (enforced at C10): delivery record + buyer identity.
                "delivery_date": "2026-07-03T00:00:00Z",
                "delivered_amount_kg": 50.0,
                "buyer_name": "Asha Co-op",
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "app-" + bu[:8]},
    )
    # C4 (enforced at C10): a photographed site composite pile sub-sample.
    await client.post(
        "/api/v1/composite-sample",
        content=json.dumps(
            {
                "sample_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "sha256_hash": "a" * 64,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "cs-" + bu[:8]},
    )
    # Rainbow C2: supply the floor of 10 photographed moisture readings so the
    # only remaining provisional reason is the assumed H:Corg (cleared by the lab).
    for i in range(1, 11):
        await client.post(
            "/api/v1/moisture",
            content=json.dumps(
                {
                    "reading_uuid": str(uuid.uuid4()),
                    "batch_uuid": bu,
                    "moisture_percent": 12.0,
                    "sequence": i,
                    "sha256_hash": "a" * 64,
                }
            ).encode("utf-8"),
            headers={"X-Idempotency-Key": f"moist-{bu[:6]}-{i}"},
        )


async def _create_batch(client, bu):
    r = await client.post(
        "/api/v1/batches",
        content=json.dumps(_batch_payload(bu)).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + bu[:8]},
    )
    assert r.status_code == 201, r.text
    return r


async def test_lab_hcorg_on_batch_payload_is_forbidden(client, registered_device):
    bu = str(uuid.uuid4())
    payload = _batch_payload(bu)
    payload["lab_h_corg"] = 0.05  # device tries to self-assert a forged permanence
    r = await client.post(
        "/api/v1/batches",
        content=json.dumps(payload).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + bu[:8]},
    )
    assert r.status_code == 422, r.text  # extra="forbid"


async def test_lab_endpoint_requires_admin_secret(client, registered_device):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)
    body = json.dumps({"batch_uuid": bu, "lab_h_corg": 0.3}).encode("utf-8")
    r_missing = await client.post("/api/v1/admin/lab-hcorg", content=body)
    assert r_missing.status_code in (401, 422)  # missing header
    r_wrong = await client.post(
        "/api/v1/admin/lab-hcorg", content=body, headers={"X-Admin-Secret": "nope"}
    )
    assert r_wrong.status_code == 401, r_wrong.text


@pytest.mark.parametrize("bad", [0.01, -0.2, 9.0])
async def test_lab_endpoint_rejects_out_of_range(client, registered_device, bad):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)
    r = await client.post(
        "/api/v1/admin/lab-hcorg",
        content=json.dumps({"batch_uuid": bu, "lab_h_corg": bad}).encode("utf-8"),
        headers=_ADMIN,
    )
    assert r.status_code == 422, r.text


async def test_lab_endpoint_unknown_batch_404(client, registered_device):
    r = await client.post(
        "/api/v1/admin/lab-hcorg",
        content=json.dumps({"batch_uuid": str(uuid.uuid4()), "lab_h_corg": 0.3}).encode(
            "utf-8"
        ),
        headers=_ADMIN,
    )
    assert r.status_code == 404, r.text


async def test_lab_hcorg_alone_leaves_only_assumed_corg(
    client, registered_device, session_factory
):
    # C7 strengthened the invariant: lab H:Corg alone no longer clears provisional
    # because organic Corg is still the species-CONSTANT assumption. The only
    # remaining reason must be exactly 'assumed_corg'.
    bu = str(uuid.uuid4())
    await _corroborate(client, bu)
    await _create_batch(client, bu)  # provisional: assumed_h_corg + assumed_corg

    r = await client.post(
        "/api/v1/admin/lab-hcorg",
        content=json.dumps({"batch_uuid": bu, "lab_h_corg": 0.3}).encode("utf-8"),
        headers=_ADMIN,
    )
    assert r.status_code == 200, r.text
    assert r.json()["provisional"] is True  # C7: Corg still assumed

    async with session_factory() as s:
        batch = (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(uuid.UUID(bu))))
        ).scalar_one()
    assert batch.provisional is True
    assert batch.lab_h_corg == 0.3
    assert json.loads(batch.provisional_reasons) == ["assumed_corg"]


async def test_full_lab_channel_clears_provisional(
    client, registered_device, session_factory
):
    # C7: a fully-corroborated batch with BOTH lab H:Corg and lab Corg is issuable.
    bu = str(uuid.uuid4())
    await _corroborate(client, bu)
    await _create_batch(client, bu)

    r = await client.post(
        "/api/v1/admin/lab",
        content=json.dumps(
            {"batch_uuid": bu, "lab_h_corg": 0.3, "organic_carbon_pct": 0.60}
        ).encode("utf-8"),
        headers=_ADMIN,
    )
    assert r.status_code == 200, r.text
    assert r.json()["provisional"] is False

    async with session_factory() as s:
        batch = (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(uuid.UUID(bu))))
        ).scalar_one()
    assert batch.provisional is False
    assert batch.lab_h_corg == 0.3
    assert batch.organic_carbon_pct == 0.60
    assert batch.net_credit_t_co2e != 0.0
    # Phase 8-R: a non-provisional batch now carries an issuance signature.
    assert batch.lca_signature is not None and batch.lca_signature != ""


async def test_provisional_batch_has_no_issuance_signature(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)  # no evidence → provisional
    async with session_factory() as s:
        batch = (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(uuid.UUID(bu))))
        ).scalar_one()
    assert batch.provisional is True
    assert batch.lca_signature is None  # must not look issuable
