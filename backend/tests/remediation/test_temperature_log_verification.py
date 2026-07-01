from tests.remediation.crypto_utils import TEST_PUBLIC_KEY_B64
import json
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from tests.remediation.crypto_utils import sign_request
import pytest_asyncio

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture(scope="function", autouse=True)
async def disable_legacy_telemetry_mock():
    # The autouse fixture legacy_test_environment in conftest.py mocks AsyncSession.execute.
    # We want real DB behavior here. We can just stop the patch if it's active.
    from unittest.mock import patch
    patch.stopall()
    yield

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

async def test_single_sample_temp_rejected(client: AsyncClient, registered_device):
    """
    If min_recorded_temp_c is asserted but telemetry is missing or lacks 60 samples, reject or override to 0.
    In our implementation, if asserted > 0 and telemetry missing, it rejects.
    If telemetry exists but < 60 samples, min_temp is 0, so LCA penalty might be 30.0 instead of 0.005.
    Wait, the implementation in create_batch raises missing_qualifying_telemetry_log if asserted > 0 and NO telemetry.
    If telemetry has < 60 samples, it sets min_temp to 0.0. The validator in BatchPayload then complains if asserted > 0!
    Wait, the validator in BatchPayload runs *before* create_batch.
    Wait, if the validator runs before, it's checking the *client's* payload!
    Let's check the behavior of the server.
    """
    from crypto_utils import sign_request
    b1_uuid = str(uuid.uuid4())
    payload = {
        "batch_uuid": b1_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 14.5,
        "harvest_uptime_seconds": 3600,
        "min_recorded_temp_c": 200.0,
        "wet_yield_kg": 100.0,
        "transport_distance_km": 0.0,
    }
    dev_id = registered_device["device_id"]
    b64_key = registered_device["b64_key"]
    
    headers = {
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-single",
        "X-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/batches", "op-single", payload)
    }
    response = await client.post("/api/v1/batches", content=json.dumps(payload).encode("utf-8"), headers=headers)
    # Phase 7-R: min temp is corroborated from the /telemetry log, not asserted on
    # the payload. With no qualifying telemetry, the batch is accepted but PROVISIONAL
    # (min_temp uncorroborated) — a client cannot assert its way to a compliant credit.
    assert response.status_code == 201, response.text
    assert response.json()["provisional"] is True

async def test_full_log_required_for_compliant_penalty(client: AsyncClient, registered_device):
    from crypto_utils import sign_request
    b1_uuid = str(uuid.uuid4())
    
    # 1. Send telemetry with >= 60 samples
    dev_id = registered_device["device_id"]
    b64_key = registered_device["b64_key"]
    
    tel = {
        "telemetry_uuid": str(uuid.uuid4()),
        "batch_uuid": b1_uuid,
        "temperature_readings": [210.0] * 65,
    }
    await client.post("/api/v1/telemetry", content=json.dumps(tel).encode("utf-8"), headers={
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-tel-full",
        "X-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/telemetry", "op-tel-full", tel)
    })
    yld = {"yield_uuid": str(uuid.uuid4()), "batch_uuid": b1_uuid, "wet_yield_weight_kg": 100.0}
    await client.post("/api/v1/yield", content=json.dumps(yld).encode("utf-8"), headers={
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-yld-full",
        "X-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/yield", "op-yld-full", yld)
    })

    payload = {
        "batch_uuid": b1_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 14.5,
        "harvest_uptime_seconds": 3600,
        "min_recorded_temp_c": 210.0,
        "wet_yield_kg": 100.0,
        "transport_distance_km": 0.0,
    }
    headers = {
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-batch-full",
        "X-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/batches", "op-batch-full", payload)
    }
    response = await client.post("/api/v1/batches", content=json.dumps(payload).encode("utf-8"), headers=headers)
    assert response.status_code == 201
    
    # Check net_credit to see if penalty is small
    data = response.json()
    assert data["net_credit_t_co2e"] > 0.0  # Means penalty was 0.005 not 30.0 (if yield is 100, 30 penalty would make it negative or 0)

async def test_min_temp_derived_from_array_not_scalar(client: AsyncClient, registered_device):
    from crypto_utils import sign_request
    b1_uuid = str(uuid.uuid4())
    
    dev_id = registered_device["device_id"]
    b64_key = registered_device["b64_key"]
    
    tel = {
        "telemetry_uuid": str(uuid.uuid4()),
        "batch_uuid": b1_uuid,
        "temperature_readings": [180.0] * 60, # Min is 180, which is < 190
    }
    await client.post("/api/v1/telemetry", content=json.dumps(tel).encode("utf-8"), headers={
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-tel-deriv",
        "X-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/telemetry", "op-tel-deriv", tel)
    })
    yld = {"yield_uuid": str(uuid.uuid4()), "batch_uuid": b1_uuid, "wet_yield_weight_kg": 100.0}
    await client.post("/api/v1/yield", content=json.dumps(yld).encode("utf-8"), headers={
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-yld-deriv",
        "X-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/yield", "op-yld-deriv", yld)
    })

    payload = {
        "batch_uuid": b1_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 14.5,
        "harvest_uptime_seconds": 3600,
        "min_recorded_temp_c": 210.0, # Client lies and says 210
        "wet_yield_kg": 100.0,
        "transport_distance_km": 0.0,
    }
    headers = {
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-batch-deriv",
        "X-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/batches", "op-batch-deriv", payload)
    }
    response = await client.post("/api/v1/batches", content=json.dumps(payload).encode("utf-8"), headers=headers)
    assert response.status_code == 201
    
    data = response.json()
    assert data["net_credit_t_co2e"] < 0.185

async def test_under_reported_transport_flagged(client: AsyncClient, registered_device, session_factory):
    from crypto_utils import sign_request
    from models import Batch
    from sqlalchemy import select
    b1_uuid = str(uuid.uuid4())
    dev_id = registered_device["device_id"]
    b64_key = registered_device["b64_key"]
    
    tel = {
        "telemetry_uuid": str(uuid.uuid4()),
        "batch_uuid": b1_uuid,
        "temperature_readings": [210.0] * 60,
    }
    await client.post("/api/v1/telemetry", content=json.dumps(tel).encode("utf-8"), headers={
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-tel-transp",
        "X-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/telemetry", "op-tel-transp", tel)
    })
    
    payload = {
        "batch_uuid": b1_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 14.5,
        "harvest_uptime_seconds": 3600,
        "min_recorded_temp_c": 210.0,
        "wet_yield_kg": 100.0,
        "transport_distance_km": 1.0, 
        "latitude": 0.0,
        "longitude": 0.0,
    }
    headers = {
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-batch-transp",
        "X-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/batches", "op-batch-transp", payload)
    }
    await client.post("/api/v1/batches", content=json.dumps(payload).encode("utf-8"), headers=headers)
    
    app_payload = {
        "application_uuid": str(uuid.uuid4()),
        "batch_uuid": b1_uuid,
        "latitude": 1.0, 
        "longitude": 0.0,
    }
    app_headers = {
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-app-transp",
        "X-Signature": sign_request(dev_id, b64_key, "POST", "/api/v1/application", "op-app-transp", app_payload)
    }
    resp = await client.post("/api/v1/application", content=json.dumps(app_payload).encode("utf-8"), headers=app_headers)
    assert resp.status_code == 201
    
    async with session_factory() as session:
        stmt = select(Batch).where(Batch.batch_uuid == uuid.UUID(b1_uuid))
        result = await session.execute(stmt)
        batch = result.scalar_one()
        assert batch.transport_distance_km > 100.0
