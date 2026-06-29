import pytest
import pytest_asyncio
import json
import hmac
import hashlib
import base64
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.future import select
from models import DeviceKey, EnrollmentToken

_HMAC_SECRET = "test-secret"
_RAW_KEY = b"12345678901234567890123456789012"
_B64_KEY = base64.urlsafe_b64encode(_RAW_KEY).decode('utf-8')

@pytest_asyncio.fixture
async def admin_mint_token(client: AsyncClient, session_factory):
    token = "test-token-123"
    headers = {"X-Admin-Secret": _HMAC_SECRET}
    payload = {"token": token, "expires_in_days": 7}
    resp = await client.post("/api/v1/admin/mint-token", json=payload, headers=headers)
    assert resp.status_code == 201
    return token

@pytest.mark.asyncio
async def test_register_without_token_rejected_401(client: AsyncClient):
    payload = {"device_id": "device-no-token", "hmac_key": _B64_KEY}
    resp = await client.post("/api/v1/register", json=payload)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "enrollment_token_required"

@pytest.mark.asyncio
async def test_register_with_valid_token_succeeds(client: AsyncClient, admin_mint_token):
    payload = {"device_id": "device-valid", "hmac_key": _B64_KEY}
    headers = {"X-Enrollment-Token": admin_mint_token}
    resp = await client.post("/api/v1/register", json=payload, headers=headers)
    assert resp.status_code == 201

@pytest.mark.asyncio
async def test_enrollment_token_is_single_use(client: AsyncClient, admin_mint_token):
    # First use
    payload1 = {"device_id": "device-use-1", "hmac_key": _B64_KEY}
    headers = {"X-Enrollment-Token": admin_mint_token}
    resp1 = await client.post("/api/v1/register", json=payload1, headers=headers)
    assert resp1.status_code == 201
    
    # Second use
    payload2 = {"device_id": "device-use-2", "hmac_key": _B64_KEY}
    resp2 = await client.post("/api/v1/register", json=payload2, headers=headers)
    assert resp2.status_code == 401
    assert resp2.json()["detail"] == "enrollment_token_used"

@pytest.mark.asyncio
async def test_existing_device_key_not_overwritable(client: AsyncClient, session_factory):
    # Mint 2 tokens manually
    async with session_factory() as session:
        t1 = EnrollmentToken(token="token-a")
        t2 = EnrollmentToken(token="token-b")
        session.add(t1)
        session.add(t2)
        await session.commit()
        
    payload1 = {"device_id": "device-dup", "hmac_key": _B64_KEY}
    resp1 = await client.post("/api/v1/register", json=payload1, headers={"X-Enrollment-Token": "token-a"})
    assert resp1.status_code == 201
    
    payload2 = {"device_id": "device-dup", "hmac_key": _B64_KEY}
    resp2 = await client.post("/api/v1/register", json=payload2, headers={"X-Enrollment-Token": "token-b"})
    assert resp2.status_code == 409
    assert resp2.json()["detail"] == "device_already_registered"

@pytest.mark.asyncio
async def test_missing_device_id_rejected(client: AsyncClient):
    resp = await client.post("/api/v1/telemetry", json={}, headers={"X-HMAC-Signature": "dummy"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "unknown_device"

@pytest.mark.asyncio
async def test_unknown_device_id_rejected_403(client: AsyncClient):
    resp = await client.post("/api/v1/telemetry", json={}, headers={"X-Device-Id": "unknown", "X-HMAC-Signature": "dummy"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "unknown_device"

@pytest.mark.asyncio
async def test_registered_device_valid_signature_accepted(client: AsyncClient, admin_mint_token):
    # Register device
    dev_id = "device-sig-test"
    payload = {"device_id": dev_id, "hmac_key": _B64_KEY}
    headers = {"X-Enrollment-Token": admin_mint_token}
    resp = await client.post("/api/v1/register", json=payload, headers=headers)
    assert resp.status_code == 201

    # Call telemetry
    req_body = {"batch_uuid": str(uuid4()), "telemetry_uuid": str(uuid4())}
    raw_body = json.dumps(req_body).encode("utf-8")
    
    method = "POST"
    path = "/api/v1/telemetry"
    op_id = "op-1"
    body_hash = hashlib.sha256(raw_body).hexdigest()
    canonical = "\n".join([method, path, op_id, body_hash, dev_id]).encode("utf-8")
    sig = hmac.new(_RAW_KEY, canonical, hashlib.sha256).hexdigest()
    
    headers = {
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": op_id,
        "X-HMAC-Signature": sig
    }
    
    resp_telemetry = await client.post(path, content=raw_body, headers=headers)
    assert resp_telemetry.status_code == 201
