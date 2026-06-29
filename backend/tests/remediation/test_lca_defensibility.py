
import pytest
import json
import uuid
from sqlalchemy import select
from models import Batch, DeviceKey
import hmac
import hashlib

@pytest.mark.asyncio
async def test_lca_defensibility(client, session_factory):
    batch_uuid = str(uuid.uuid4())
    payload = {
        "batch_uuid": batch_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": "2026-06-06T12:00:00Z",
        "moisture_percent": 15.0,
        "sha256_hash": "a" * 64,
        "wet_yield_kg": 100.0,
        "min_recorded_temp_c": 650.0,
        "transport_distance_km": 10.0,
        "harvest_uptime_seconds": 3600
    }
    
    raw_body = json.dumps(payload).encode("utf-8")
    
    response = await client.post(
        "/api/v1/batches",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": "req_lca"
        }
    )
    assert response.status_code == 201
    
    async with session_factory() as db_session:
        batch_row = (await db_session.execute(select(Batch).where(Batch.batch_uuid == uuid.UUID(batch_uuid)))).scalar_one()
        assert batch_row.lca_methodology_version == "CSI-3.2"
        assert batch_row.lca_signature is not None
        assert batch_row.lca_audit_json is not None
        
        audit_dict = json.loads(batch_row.lca_audit_json)
        assert audit_dict["methodology_version"] == "CSI-3.2"
        assert audit_dict["ch4_compliant"] is False


