import pytest
import pytest_asyncio
import json
import hmac
import hashlib
from uuid import uuid4
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.future import select
from models import DeviceKey, PyrolysisTelemetry, YieldMetrics, EndUseApplication, SystemMetadata

from tests.remediation.crypto_utils import sign_request

@pytest_asyncio.fixture
async def registered_device(client: AsyncClient, session_factory):
    from models import EnrollmentToken
    import base64
    async with session_factory() as session:
        t = EnrollmentToken(token="test-credit")
        session.add(t)
        await session.commit()
    b64_key = base64.urlsafe_b64encode(b"12345678901234567890123456789012").decode('utf-8')
    dev_id = "test-device"
    payload = {"device_id": dev_id, "hmac_key": b64_key}
    headers = {"X-Enrollment-Token": "test-credit"}
    await client.post("/api/v1/register", content=json.dumps(payload).encode("utf-8"), headers=headers)
    return {"device_id": dev_id, "b64_key": b64_key}

@pytest.mark.asyncio
async def test_telemetry_persistence(client: AsyncClient, registered_device, session_factory, monkeypatch):
    monkeypatch.setenv("DISABLE_TELEMETRY_MOCK", "1")
    batch_uuid = str(uuid4())
    telemetry_uuid = str(uuid4())
    payload = {
        "telemetry_uuid": telemetry_uuid,
        "batch_uuid": batch_uuid,
        "some_data": 123
    }
    raw_body = json.dumps(payload).encode('utf-8')
    op_id = "op-tel-1"
    device_id = registered_device["device_id"]
    
    headers = {
        "X-Idempotency-Key": op_id,
        "X-Device-Id": device_id,
        "X-HMAC-Signature": sign_request(device_id, registered_device["b64_key"], "POST", "/api/v1/telemetry", op_id, payload),
        "Content-Type": "application/json"
    }
    
    resp = await client.post("/api/v1/telemetry", content=raw_body, headers=headers)
    assert resp.status_code == 201
    
    async with session_factory() as s:
        result = await s.execute(select(PyrolysisTelemetry).where(PyrolysisTelemetry.telemetry_uuid == telemetry_uuid))
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.batch_uuid == batch_uuid
        assert json.loads(row.payload_json) == payload

@pytest.mark.asyncio
async def test_yield_persistence(client: AsyncClient, registered_device, session_factory):
    batch_uuid = str(uuid4())
    yield_uuid = str(uuid4())
    payload = {
        "yield_uuid": yield_uuid,
        "batch_uuid": batch_uuid,
        "yield_kg": 500
    }
    raw_body = json.dumps(payload).encode('utf-8')
    op_id = "op-yld-1"
    device_id = registered_device["device_id"]
    
    headers = {
        "X-Idempotency-Key": op_id,
        "X-Device-Id": device_id,
        "X-HMAC-Signature": sign_request(device_id, registered_device["b64_key"], "POST", "/api/v1/yield", op_id, payload),
        "Content-Type": "application/json"
    }
    
    resp = await client.post("/api/v1/yield", content=raw_body, headers=headers)
    assert resp.status_code == 201
    
    async with session_factory() as s:
        result = await s.execute(select(YieldMetrics).where(YieldMetrics.yield_uuid == yield_uuid))
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.batch_uuid == batch_uuid

@pytest.mark.asyncio
async def test_application_persistence(client: AsyncClient, registered_device, session_factory):
    batch_uuid = str(uuid4())
    app_uuid = str(uuid4())
    payload = {
        "application_uuid": app_uuid,
        "batch_uuid": batch_uuid,
        "field_id": "field_1"
    }
    raw_body = json.dumps(payload).encode('utf-8')
    op_id = "op-app-1"
    device_id = registered_device["device_id"]
    
    headers = {
        "X-Idempotency-Key": op_id,
        "X-Device-Id": device_id,
        "X-HMAC-Signature": sign_request(device_id, registered_device["b64_key"], "POST", "/api/v1/application", op_id, payload),
        "Content-Type": "application/json"
    }
    
    resp = await client.post("/api/v1/application", content=raw_body, headers=headers)
    assert resp.status_code == 201
    
    async with session_factory() as s:
        result = await s.execute(select(EndUseApplication).where(EndUseApplication.application_uuid == app_uuid))
        row = result.scalar_one_or_none()
        assert row is not None

@pytest.mark.asyncio
async def test_metadata_persistence(client: AsyncClient, registered_device, session_factory):
    batch_uuid = str(uuid4())
    payload = {
        "batch_uuid": batch_uuid,
        "artisan_id": "art_123",
        "device_hardware_mac": "00:11:22",
        "app_build_version": "1.0",
        "sync_status": "SYNCED",
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    raw_body = json.dumps(payload).encode('utf-8')
    op_id = "op-meta-1"
    device_id = registered_device["device_id"]
    
    headers = {
        "X-Idempotency-Key": op_id,
        "X-Device-Id": device_id,
        "X-HMAC-Signature": sign_request(device_id, registered_device["b64_key"], "POST", "/api/v1/metadata", op_id, payload),
        "Content-Type": "application/json"
    }
    
    resp = await client.post("/api/v1/metadata", content=raw_body, headers=headers)
    assert resp.status_code == 201
    
    async with session_factory() as s:
        result = await s.execute(select(SystemMetadata).where(SystemMetadata.batch_uuid == batch_uuid))
        row = result.scalar_one_or_none()
        assert row is not None
