"""Rainbow compliance C10 — unified issuance gate + compliance report.

C10 flips the previously-inert methodology checks (C1 biomass, C4 composite, C5
delivery/buyer, C8 kiln registration) to ENFORCED. A batch is issuable
(non-provisional) only when every resolvable methodology item is satisfied; each
missing datum surfaces its specific reason. GET /batches/{uuid}/compliance
returns the ordered reasons + a human checklist.

Scale-calibration and annual-methane gating need a batch→project/scale linkage
that does not exist yet, so they stay dormant (documented C10 follow-up) and are
NOT asserted as gating here.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import Batch

pytestmark = pytest.mark.asyncio

_ADMIN = {"X-Admin-Secret": "test-admin-secret"}
_SHA = "a" * 64
_KILN = "KILN-C10"


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


async def _fully_compliant_batch(
    client, bu, *, biomass=True, composite=True, delivery=True, register_kiln=True
):
    """Build a batch that satisfies every C10-enforced item, toggling one off to
    test its reason. Physical corroboration (yield/temp/transport) + moisture (10)
    + lab (H:Corg + Corg) are always supplied so only the toggled item can fail."""
    if register_kiln:
        await _admin(
            client, "/api/v1/admin/kiln", {"kiln_id": _KILN, "kiln_type": "open"}
        )

    # Telemetry: 60 temps + registered kiln id + full open-kiln C3 evidence
    # (3 photographed stages + flame height < 0.5 m) so C3 does not gate.
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
    # Yield.
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
    # Application with transport GPS + delivery + buyer.
    app = {
        "application_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "latitude": 13.9716,
        "longitude": 77.5946,  # ~111 km from batch below
    }
    if delivery:
        app.update(
            {
                "delivery_date": "2026-07-03T00:00:00Z",
                "delivered_amount_kg": 50.0,
                "buyer_name": "Asha Co-op",
            }
        )
    await _post(client, "/api/v1/application", "app-" + bu[:8], app)
    # 10 photographed moisture readings (C2).
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
    # Composite pile sub-sample (C4).
    if composite:
        await _post(
            client,
            "/api/v1/composite-sample",
            "cs-" + bu[:8],
            {
                "sample_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "sha256_hash": _SHA,
            },
        )
    # Batch itself (biomass input toggled).
    batch = {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
        "latitude": 12.9716,
        "longitude": 77.5946,
    }
    if biomass:
        batch.update(
            {"biomass_input_kg": 500.0, "biomass_measurement_method": "direct_weigh"}
        )
    await _post(client, "/api/v1/batches", "b-" + bu[:8], batch)
    # Full lab (H:Corg + Corg) via the admin channel.
    await _admin(
        client,
        "/api/v1/admin/lab",
        {"batch_uuid": bu, "lab_h_corg": 0.3, "organic_carbon_pct": 0.60},
    )


async def _reasons(session_factory, bu):
    async with session_factory() as s:
        b = (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(uuid.UUID(bu))))
        ).scalar_one()
        return b.provisional, json.loads(b.provisional_reasons or "[]")


async def test_fully_compliant_batch_is_issuable(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _fully_compliant_batch(client, bu)
    provisional, reasons = await _reasons(session_factory, bu)
    assert provisional is False, f"expected issuable, reasons={reasons}"
    assert reasons == []


@pytest.mark.parametrize(
    "toggle,reason",
    [
        ("biomass", "missing_biomass_input"),
        ("composite", "missing_composite_sample"),
        ("delivery", "missing_delivery_record"),
        ("register_kiln", "unregistered_kiln"),
    ],
)
async def test_each_missing_datum_surfaces_its_reason(
    client, registered_device, session_factory, toggle, reason
):
    bu = str(uuid.uuid4())
    await _fully_compliant_batch(client, bu, **{toggle: False})
    provisional, reasons = await _reasons(session_factory, bu)
    assert provisional is True
    assert reason in reasons, f"{toggle} off → expected {reason}, got {reasons}"


async def test_compliance_endpoint_reports_checklist(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _fully_compliant_batch(client, bu, composite=False)
    r = await client.get(f"/api/v1/batches/{bu}/compliance", headers=_ADMIN)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["issuable"] is False
    assert "missing_composite_sample" in body["reasons"]
    # The checklist marks that item not-ok and a satisfied one ok.
    by_code = {c["code"]: c for c in body["checklist"]}
    assert by_code["missing_composite_sample"]["ok"] is False
    assert by_code["missing_biomass_input"]["ok"] is True


async def test_compliance_endpoint_requires_admin(client, registered_device):
    bu = str(uuid.uuid4())
    r = await client.get(
        f"/api/v1/batches/{bu}/compliance", headers={"X-Admin-Secret": "wrong"}
    )
    assert r.status_code == 401, r.text


async def test_compliance_endpoint_unknown_batch_404(client, registered_device):
    r = await client.get(f"/api/v1/batches/{str(uuid.uuid4())}/compliance", headers=_ADMIN)
    assert r.status_code == 404, r.text


# ---- T1.10: per-item enforcement provenance ----------------------------


async def _simple_batch(client, bu, *, project_id=None, scale_id=None):
    payload = {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
    }
    if project_id is not None:
        payload["project_id"] = project_id
    if scale_id is not None:
        payload["scale_id"] = scale_id
    await client.post(
        "/api/v1/batches",
        content=json.dumps(payload).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + bu[:8]},
    )


def _by_code(checklist):
    return {item["code"]: item for item in checklist}


async def test_provenance_enforced_for_linked_batch(client, registered_device):
    bu = str(uuid.uuid4())
    await _simple_batch(client, bu, project_id="P-PROV-1", scale_id="S-PROV-1")
    r = await client.get(f"/api/v1/batches/{bu}/compliance", headers=_ADMIN)
    assert r.status_code == 200, r.text
    items = _by_code(r.json()["checklist"])
    assert items["scale_calibration_expired"]["enforcement"] == "enforced"
    assert items["missing_annual_methane"]["enforcement"] == "enforced"
    assert items["missing_pah"]["enforcement"] == "enforced"


async def test_provenance_inert_for_unlinked_batch(client, registered_device):
    bu = str(uuid.uuid4())
    await _simple_batch(client, bu)  # no linkage
    r = await client.get(f"/api/v1/batches/{bu}/compliance", headers=_ADMIN)
    assert r.status_code == 200, r.text
    items = _by_code(r.json()["checklist"])
    assert items["scale_calibration_expired"]["enforcement"] == "inert_no_linkage"
    assert items["missing_annual_methane"]["enforcement"] == "inert_no_linkage"
    assert items["missing_pah"]["enforcement"] == "inert_no_linkage"
    # Back-compat: the original checklist keys are still present.
    assert set(["code", "section", "label", "ok"]).issubset(
        r.json()["checklist"][0].keys()
    )
