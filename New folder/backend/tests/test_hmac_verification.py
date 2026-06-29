import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
import server
from server import app, get_session
from unittest.mock import AsyncMock, MagicMock

from datetime import datetime

server.init_db = AsyncMock()

@pytest.fixture(autouse=True)
def override_dependencies():
    async def override_get_session():
        mock_session = AsyncMock()
        mock_result = MagicMock()
        import base64
        mock_device = MagicMock()
        mock_device.hmac_key = base64.urlsafe_b64encode(b"test_secret").decode('utf-8')
        def mock_execute_impl(stmt):
            mock_res = MagicMock()
            if 'device_keys' in str(stmt).lower():
                mock_res.scalar_one_or_none.return_value = mock_device
            else:
                mock_res.scalar_one_or_none.return_value = None
            return mock_res
            
        mock_session.execute.side_effect = mock_execute_impl
        
        async def mock_refresh(obj):
            obj.received_at = datetime.utcnow()
        mock_session.refresh.side_effect = mock_refresh
        
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session
    yield
    app.dependency_overrides.clear()

client = TestClient(app)

def test_hmac_verification_success(monkeypatch):
    monkeypatch.setattr(server, "_HMAC_SECRET", "test_secret")
    
    payload = {
        "batch_uuid": "123e4567-e89b-12d3-a456-426614174000",
        "feedstock_species": "Lantana_camara",
            "harvest_uptime_seconds": 1000,
        "harvest_timestamp": "2026-06-06T12:00:00Z",
        "moisture_percent": 15.0,
        "sha256_hash": "a" * 64,
        "wet_yield_kg": 100.0,
        "min_recorded_temp_c": 650.0,
        "transport_distance_km": 10.0
    }
    
    raw_body = json.dumps(payload).encode("utf-8")
    secret = b"test_secret"
    method = "POST"
    path = "/api/v1/batches"
    op_id = "req_1"
    body_hash = hashlib.sha256(raw_body).hexdigest()
    dev_id = "dev-1"
    canonical = "\n".join([method, path, op_id, body_hash, dev_id]).encode('utf-8')
    signature = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
    
    response = client.post(
        "/api/v1/batches",
        data=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": "req_1",
            "X-Device-Id": "dev-1",
            "X-HMAC-Signature": signature
        }
    )
    
    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "missing_qualifying_telemetry_log"

def test_hmac_verification_failure(monkeypatch):
    monkeypatch.setattr(server, "_HMAC_SECRET", "test_secret")
    
    payload = {
        "batch_uuid": "123e4567-e89b-12d3-a456-426614174001",
        "feedstock_species": "Lantana_camara",
            "harvest_uptime_seconds": 1000,
        "harvest_timestamp": "2026-06-06T12:00:00Z",
        "moisture_percent": 15.0,
        "sha256_hash": "b" * 64
    }
    
    raw_body = json.dumps(payload).encode("utf-8")
    
    response = client.post(
        "/api/v1/batches",
        data=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": "req_2",
            "X-Device-Id": "dev-1",
            "X-HMAC-Signature": "invalid_signature"
        }
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "hmac_mismatch"

def test_hmac_verification_missing_header_fallback(monkeypatch):
    monkeypatch.setattr(server, "_HMAC_SECRET", "test_secret")
    
    payload = {
        "batch_uuid": "123e4567-e89b-12d3-a456-426614174002",
        "feedstock_species": "Lantana_camara",
            "harvest_uptime_seconds": 1000,
        "harvest_timestamp": "2026-06-06T12:00:00Z",
        "moisture_percent": 15.0,
        "sha256_hash": "c" * 64
    }
    
    raw_body = json.dumps(payload).encode("utf-8")
    
    response = client.post(
        "/api/v1/batches",
        data=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": "req_3",
            "X-Device-Id": "dev-1"
            # Missing X-HMAC-Signature
        }
    )
    
    assert response.status_code == 401
