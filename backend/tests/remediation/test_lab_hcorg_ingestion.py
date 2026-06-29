import json
import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
import pytest_asyncio

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def registered_device(client: AsyncClient, session_factory):
    from models import EnrollmentToken
    import base64
    async with session_factory() as session:
        t = EnrollmentToken(token="test-credit-hcorg")
        session.add(t)
        await session.commit()
    
    b64_key = base64.urlsafe_b64encode(b"12345678901234567890123456789012").decode('utf-8')
    dev_id = "test-device-hcorg"
    payload = {"device_id": dev_id, "hmac_key": b64_key}
    headers = {"X-Enrollment-Token": "test-credit-hcorg"}
    await client.post("/api/v1/register", content=json.dumps(payload).encode("utf-8"), headers=headers)
    
    return {"device_id": dev_id, "b64_key": b64_key}

async def test_lab_hcorg_passed_to_lca_engine(client: AsyncClient, registered_device):
    from tests.remediation.crypto_utils import sign_request
    b1_uuid = str(uuid.uuid4())
    dev_id = registered_device["device_id"]
    b64_key = registered_device["b64_key"]
    
    # 1. Telemetry for compliant burn
    tel = {
        "telemetry_uuid": str(uuid.uuid4()),
        "batch_uuid": b1_uuid,
        "temperatureReadingsJson": [650.0] * 60,
    }
    await client.post("/api/v1/telemetry", content=json.dumps(tel).encode("utf-8"), headers={
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-tel-hcorg",
        "X-HMAC-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/telemetry", "op-tel-hcorg", tel)
    })
    
    # 2. Submit batch with low H:Corg (e.g., 0.1) -> means high stability, high credit
    payload_low = {
        "batch_uuid": b1_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 14.5,
        "harvest_uptime_seconds": 3600,
        "min_recorded_temp_c": 650.0,
        "wet_yield_kg": 1000.0,
        "transport_distance_km": 0.0,
        "lab_h_corg": 0.1
    }
    headers_low = {
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-batch-hcorg-low",
        "X-HMAC-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/batches", "op-batch-hcorg-low", payload_low)
    }
    resp1 = await client.post("/api/v1/batches", content=json.dumps(payload_low).encode("utf-8"), headers=headers_low)
    assert resp1.status_code == 201
    credit_low = resp1.json()["net_credit_t_co2e"]
    
    # 3. Submit batch with high H:Corg (e.g., 0.6) -> means lower stability, lower credit
    b2_uuid = str(uuid.uuid4())
    tel2 = {
        "telemetry_uuid": str(uuid.uuid4()),
        "batch_uuid": b2_uuid,
        "temperatureReadingsJson": [650.0] * 60,
    }
    await client.post("/api/v1/telemetry", content=json.dumps(tel2).encode("utf-8"), headers={
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-tel-hcorg2",
        "X-HMAC-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/telemetry", "op-tel-hcorg2", tel2)
    })
    
    payload_high = payload_low.copy()
    payload_high["batch_uuid"] = b2_uuid
    payload_high["lab_h_corg"] = 0.6
    headers_high = {
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-batch-hcorg-high",
        "X-HMAC-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/batches", "op-batch-hcorg-high", payload_high)
    }
    resp2 = await client.post("/api/v1/batches", content=json.dumps(payload_high).encode("utf-8"), headers=headers_high)
    assert resp2.status_code == 201
    credit_high = resp2.json()["net_credit_t_co2e"]
    
    assert credit_low > credit_high, f"Credit low {credit_low} should be > credit high {credit_high}"
