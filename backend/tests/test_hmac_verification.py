"""Request-signature verification on /api/v1/batches.

Phase 5 migrated device identity from a symmetric HMAC key to an Ed25519
public key, so this file no longer tests HMAC despite its (now historical)
name. It exercises the Ed25519 verifier: a signature from the enrolled key is
accepted, a bad/forged signature is rejected with ``signature_mismatch``, and a
missing signature is rejected with ``missing_signature``.

NOTE: the filename is retained only because the harness forbids deleting a
pre-existing test; consider renaming to test_signature_verification.py.
"""

import hashlib
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

import server
from server import app, get_session
from tests.remediation.crypto_utils import TEST_PUBLIC_KEY_B64, sign_canonical

server.init_db = AsyncMock()


@pytest.fixture(autouse=True)
def override_dependencies():
    async def override_get_session():
        mock_session = AsyncMock()
        mock_device = MagicMock()
        # Phase 5: the server reads device.public_key (Ed25519), not hmac_key.
        mock_device.public_key = TEST_PUBLIC_KEY_B64

        def mock_execute_impl(stmt):
            mock_res = MagicMock()
            if "device_keys" in str(stmt).lower():
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


def _canonical(method, path, op_id, raw_body, dev_id):
    body_hash = hashlib.sha256(raw_body).hexdigest()
    return "\n".join([method, path, op_id, body_hash, dev_id]).encode("utf-8")


def test_hmac_verification_success():
    """A valid Ed25519 signature authenticates; the batch is then accepted as
    PROVISIONAL (no corroborating telemetry yet), proving auth was accepted.
    Phase 7-R: a missing telemetry log no longer hard-rejects (400) — the batch
    is created provisional and earns no credit until evidence corroborates it."""
    payload = {
        "batch_uuid": "123e4567-e89b-12d3-a456-426614174000",
        "feedstock_species": "Lantana_camara",
        "harvest_uptime_seconds": 1000,
        "harvest_timestamp": "2026-06-06T12:00:00Z",
        "moisture_percent": 15.0,
        "sha256_hash": "a" * 64,
        "wet_yield_kg": 100.0,
        "min_recorded_temp_c": 650.0,
        "transport_distance_km": 10.0,
    }
    raw_body = json.dumps(payload).encode("utf-8")
    op_id = "req_1"
    dev_id = "dev-1"
    sig = sign_canonical(_canonical("POST", "/api/v1/batches", op_id, raw_body, dev_id))

    response = client.post(
        "/api/v1/batches",
        data=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": op_id,
            "X-Device-Id": dev_id,
            "X-Signature": sig,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["provisional"] is True  # auth accepted; credit not yet issuable


def test_hmac_verification_failure():
    payload = {
        "batch_uuid": "123e4567-e89b-12d3-a456-426614174001",
        "feedstock_species": "Lantana_camara",
        "harvest_uptime_seconds": 1000,
        "harvest_timestamp": "2026-06-06T12:00:00Z",
        "moisture_percent": 15.0,
        "sha256_hash": "b" * 64,
    }
    raw_body = json.dumps(payload).encode("utf-8")

    response = client.post(
        "/api/v1/batches",
        data=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": "req_2",
            "X-Device-Id": "dev-1",
            "X-Signature": "aW52YWxpZF9zaWduYXR1cmU",  # not a valid signature
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "signature_mismatch"


def test_hmac_verification_missing_header_fallback():
    payload = {
        "batch_uuid": "123e4567-e89b-12d3-a456-426614174002",
        "feedstock_species": "Lantana_camara",
        "harvest_uptime_seconds": 1000,
        "harvest_timestamp": "2026-06-06T12:00:00Z",
        "moisture_percent": 15.0,
        "sha256_hash": "c" * 64,
    }
    raw_body = json.dumps(payload).encode("utf-8")

    response = client.post(
        "/api/v1/batches",
        data=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": "req_3",
            "X-Device-Id": "dev-1",
            # Missing X-Signature
        },
    )

    assert response.status_code == 401
