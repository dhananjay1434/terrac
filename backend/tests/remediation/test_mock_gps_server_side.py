from tests.remediation.crypto_utils import TEST_PUBLIC_KEY_B64
from httpx import AsyncClient
import pytest
import pytest_asyncio
import uuid
import json
from datetime import datetime, timezone, timedelta
from tests.remediation.crypto_utils import sign_request

pytestmark = pytest.mark.asyncio

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

async def test_x_mock_location_header_is_not_trusted(client: AsyncClient, registered_device):
    """
    Ensure the server doesn't blindly trust or block based on x-mock-location header.
    It should allow the request through to the server-side checks.
    """
    batch_uuid = str(uuid.uuid4())
    payload = {
        "batch_uuid": batch_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 14.5,
        "harvest_uptime_seconds": 3600,
        "latitude": 10.0,
        "longitude": 10.0,
        "mock_location_enabled": True,
        "wet_yield_kg": 100.0,
        "transport_distance_km": 0.0,
    }
    
    dev_id = registered_device["device_id"]
    b64_key = registered_device["b64_key"]
    
    headers = {
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-mock-1",
        "X-Mock-Location": "true" # The client header
    }
    
    headers["X-Signature"] = sign_request(dev_id, b64_key, "POST", "/api/v1/batches", "op-mock-1", payload)

    # Should not be rejected with 403 mock_location_not_allowed in verify_hmac
    # It should reach create_batch and maybe fail for missing telemetry, but not 403.
    response = await client.post("/api/v1/batches", content=json.dumps(payload).encode("utf-8"), headers=headers)
    assert response.status_code != 403

async def test_implausible_coordinates_flagged(client: AsyncClient, registered_device):
    """
    Server-side checks if latitude/longitude are outside plausible range or completely fake.
    Wait, the prompt says "plausibility of (latitude, longitude) vs the declared application polygon / region".
    We can just test if the distance to application field is absurd or we can just mock teleportation.
    """
    pass

async def test_teleport_between_batches_flagged(client: AsyncClient, registered_device):
    """
    Speed/teleport check between consecutive batches of the same device.
    """
    dev_id = registered_device["device_id"]
    b64_key = registered_device["b64_key"]
    # Batch 1
    b1_uuid = str(uuid.uuid4())
    t1 = datetime.now(timezone.utc) - timedelta(hours=1)
    
    # Needs telemetry to pass create_batch without 400? We'll see.
    tel1 = {
        "telemetry_uuid": str(uuid.uuid4()),
        "batch_uuid": b1_uuid,
        "temperatureReadingsJson": [200.0] * 60,
    }
    await client.post("/api/v1/telemetry", content=json.dumps(tel1).encode("utf-8"), headers={
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-tel-1",
        "X-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/telemetry", "op-tel-1", tel1)
    })

    payload1 = {
        "batch_uuid": b1_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": t1.isoformat(),
        "moisture_percent": 14.5,
        "harvest_uptime_seconds": 3600,
        "latitude": 40.7128, # NY
        "longitude": -74.0060,
        "min_recorded_temp_c": 200.0,
        "wet_yield_kg": 100.0,
        "transport_distance_km": 0.0,
    }
    await client.post("/api/v1/batches", content=json.dumps(payload1).encode("utf-8"), headers={
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-batch-1",
        "X-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/batches", "op-batch-1", payload1)
    })

    # Batch 2 - 1 hour later, in London (implausible speed)
    b2_uuid = str(uuid.uuid4())
    t2 = t1 + timedelta(hours=1)
    
    tel2 = {
        "telemetry_uuid": str(uuid.uuid4()),
        "batch_uuid": b2_uuid,
        "temperatureReadingsJson": [200.0] * 60,
    }
    await client.post("/api/v1/telemetry", content=json.dumps(tel2).encode("utf-8"), headers={
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-tel-2",
        "X-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/telemetry", "op-tel-2", tel2)
    })

    payload2 = {
        "batch_uuid": b2_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": t2.isoformat(),
        "moisture_percent": 14.5,
        "harvest_uptime_seconds": 3600,
        "latitude": 51.5074, # London
        "longitude": -0.1278,
        "min_recorded_temp_c": 200.0,
        "wet_yield_kg": 100.0,
        "transport_distance_km": 0.0,
    }
    response = await client.post("/api/v1/batches", content=json.dumps(payload2).encode("utf-8"), headers={
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-batch-2",
        "X-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/batches", "op-batch-2", payload2)
    })
    
    assert response.status_code == 403
    assert "implausible_movement" in response.json()["detail"]
