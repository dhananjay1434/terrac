"""CSI / Rainbow export endpoint tests (EXECUTION_MASTER_PLAN E12)."""

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from models import Batch

pytestmark = pytest.mark.asyncio

ADMIN = {"X-Admin-Secret": "test-admin-secret"}


async def _seed(session_factory, *, provisional=False, reasons=None) -> str:
    from models import MediaFile
    bu = str(uuid4())
    b = Batch(
        batch_uuid=bu,
        operation_id=str(uuid4()),
        feedstock_species="Lantana camara",
        harvest_timestamp=datetime.now(timezone.utc),
        moisture_percent=15.0,
        harvest_uptime_seconds=0,
        latitude=10.5,
        longitude=20.5,
        wet_yield_kg=500.0,
        min_recorded_temp_c=650.0,
        transport_distance_km=12.0,
        lab_h_corg=0.75,
        organic_carbon_pct=0.8,
        biomass_input_kg=500.0,
        biomass_measurement_method="WEIGHED",
        status="RECEIVED",
        net_credit_t_co2e=150.5,
        lca_signature="sig-test",
        lca_signature_key_id="k0",
        provisional=provisional,
        provisional_reasons=json.dumps(reasons) if reasons is not None else None,
    )
    m = MediaFile(
        batch_uuid=bu,
        operation_id="test-media-op",
        file_path="/tmp/fake.jpg",
        sha256_hash="deadbeef",
        capture_type="flame_curtain",
        capture_type_verified=True,
    )
    async with session_factory() as s:
        s.add(b)
        s.add(m)
        await s.commit()
    return bu


async def test_csi_export_ok(client, session_factory):
    bu = await _seed(session_factory)
    r = await client.get(f"/api/v1/batches/{bu}/export/csi", headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["batch_uuid"] == bu
    assert body["standard"] == "CSI GlobalCSinkVerificationReport v1"
    assert body["exported_at"] is not None
    assert body["credit"]["net_credit_t_co2e"] == 150.5
    assert len(body["evidence_media"]) == 1
    assert body["evidence_media"][0]["capture_type"] == "flame_curtain"
    assert body["evidence_media"][0]["capture_type_verified"] is True


async def test_rainbow_export_ok(client, session_factory):
    bu = await _seed(session_factory)
    r = await client.get(f"/api/v1/batches/{bu}/export/rainbow", headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["batch_uuid"] == bu
    assert body["h_corg_ratio"] == 0.75
    assert "Rainbow" in body["standard"]


async def test_csi_export_provisional_400(client, session_factory):
    bu = await _seed(session_factory, provisional=True, reasons=["assumed_h_corg"])
    r = await client.get(f"/api/v1/batches/{bu}/export/csi", headers=ADMIN)
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["error"] == "batch_is_provisional"
    assert detail["reasons"] == ["assumed_h_corg"]      # a LIST, not a raw string


async def test_csi_export_requires_admin(client, session_factory):
    bu = await _seed(session_factory)
    r = await client.get(f"/api/v1/batches/{bu}/export/csi")
    assert r.status_code in (401, 403, 422)


async def test_csi_export_bad_admin_secret(client, session_factory):
    bu = await _seed(session_factory)
    r = await client.get(
        f"/api/v1/batches/{bu}/export/csi", headers={"X-Admin-Secret": "wrong"}
    )
    assert r.status_code in (401, 403)


async def test_csi_export_not_found(client):
    r = await client.get(f"/api/v1/batches/{uuid4()}/export/csi", headers=ADMIN)
    assert r.status_code == 404


async def test_csi_export_invalid_uuid_400(client):
    r = await client.get("/api/v1/batches/not-a-uuid/export/csi", headers=ADMIN)
    assert r.status_code == 400


async def test_export_refuses_unsigned_nonprovisional_batch(client, session_factory):
    """Audit fix 8: non-provisional + NULL lca_signature = tampered row -> 400."""
    bu = await _seed(session_factory)
    from sqlalchemy import update
    from models import Batch

    async with session_factory() as s:
        await s.execute(
            update(Batch).where(Batch.batch_uuid == bu).values(lca_signature=None)
        )
        await s.commit()

    r = await client.get(f"/api/v1/batches/{bu}/export/csi", headers=ADMIN)
    assert r.status_code == 400
    assert "unsigned_batch" in r.text
