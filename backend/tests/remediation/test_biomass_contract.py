from tests.remediation.crypto_utils import TEST_PUBLIC_KEY_B64
import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4
import hmac
import hashlib
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.remediation.crypto_utils import sign_request

@pytest_asyncio.fixture
async def registered_device(client: AsyncClient, session_factory):
    from models import EnrollmentToken
    import base64
    async with session_factory() as session:
        t = EnrollmentToken(token="test-credit")
        session.add(t)
        await session.commit()
    b64_key = TEST_PUBLIC_KEY_B64
    dev_id = "test-device"
    payload = {"device_id": dev_id, "public_key": b64_key}
    headers = {"X-Enrollment-Token": "test-credit"}
    await client.post("/api/v1/register", content=json.dumps(payload).encode("utf-8"), headers=headers)
    return {"device_id": dev_id, "b64_key": b64_key}

@pytest.mark.asyncio
async def test_real_client_biomass_payload_accepted(client: AsyncClient, registered_device):
    batch_uuid = str(uuid4())
    sourcing_uuid = str(uuid4())
    payload = {
        "batch_uuid": batch_uuid,
        "sourcing_uuid": sourcing_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.utcnow().isoformat() + "Z",
        "moisture_percent": 14.5,
        "moisture_compliant": True,
        "photo_path": "/local/path.jpg",
        "sha256_hash": "a" * 64,
        "latitude": 45.0,
        "longitude": 90.0,
        "mock_location_enabled": False,
        "azimuth": 1.2,
        "pitch": 0.5,
        "roll": 0.1,
        "harvest_uptime_seconds": 120,
        "wet_yield_kg": 150.0,
        "min_recorded_temp_c": 0.0,
        "transport_distance_km": 10.0
    }
    raw_body = json.dumps(payload).encode('utf-8')
    
    device_id = registered_device["device_id"]
    op_id = "test-op-id"
    sig = sign_request(device_id, registered_device["b64_key"], "POST", "/api/v1/batches", op_id, payload)
    
    headers = {
        "X-Idempotency-Key": op_id,
        "X-Device-Id": device_id,
        "X-Signature": sig,
        "Content-Type": "application/json"
    }
    
    response = await client.post("/api/v1/batches", content=raw_body, headers=headers)
    assert response.status_code in [200, 201], f"Failed with {response.status_code}: {response.text}"

@pytest.mark.asyncio
async def test_photoless_biomass_accepted_null_sha(client: AsyncClient, registered_device):
    batch_uuid = str(uuid4())
    payload = {
        "batch_uuid": batch_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.utcnow().isoformat() + "Z",
        "moisture_percent": 14.5,
        "sha256_hash": None,
        "harvest_uptime_seconds": 120,
        "wet_yield_kg": 150.0,
        "min_recorded_temp_c": 0.0,
        "transport_distance_km": 10.0
    }
    raw_body = json.dumps(payload).encode('utf-8')
    device_id = registered_device["device_id"]
    op_id = "test-op-id2"
    sig = sign_request(device_id, registered_device["b64_key"], "POST", "/api/v1/batches", op_id, payload)
    
    headers = {
        "X-Idempotency-Key": op_id,
        "X-Device-Id": device_id,
        "X-Signature": sig,
        "Content-Type": "application/json"
    }
    response = await client.post("/api/v1/batches", content=raw_body, headers=headers)
    assert response.status_code in [200, 201], f"Failed with {response.status_code}: {response.text}"

@pytest.mark.asyncio
async def test_unknown_extra_field_still_rejected(client: AsyncClient, registered_device):
    batch_uuid = str(uuid4())
    payload = {
        "batch_uuid": batch_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.utcnow().isoformat() + "Z",
        "moisture_percent": 14.5,
        "sha256_hash": None,
        "harvest_uptime_seconds": 120,
        "wet_yield_kg": 150.0,
        "min_recorded_temp_c": 0.0,
        "transport_distance_km": 10.0,
        "some_random_field": "unwanted"
    }
    raw_body = json.dumps(payload).encode('utf-8')
    device_id = registered_device["device_id"]
    op_id = "test-op-id3"
    sig = sign_request(device_id, registered_device["b64_key"], "POST", "/api/v1/batches", op_id, payload)
    headers = {
        "X-Idempotency-Key": op_id,
        "X-Device-Id": device_id,
        "X-Signature": sig,
        "Content-Type": "application/json"
    }
    response = await client.post("/api/v1/batches", content=raw_body, headers=headers)
    assert response.status_code == 422
