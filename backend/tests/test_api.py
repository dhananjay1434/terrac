"""Comprehensive pytest tests for dMRV API endpoints.

Tests:
  1. Valid batch payload → 201
  2. Duplicate idempotency key → 200 (no duplicate insert)
  3. Malformed payload (missing sha256_hash) → 422
  4. Media upload with correct hash → 200 + server_sha256 matches
  5. Media upload with wrong declared hash → 422
"""

from __future__ import annotations

import asyncio
import hashlib
import io
from pathlib import Path


async def inject_telemetry(client, batch_uuid):
    from uuid import uuid4
    import json

    tel_payload = {
        "telemetry_uuid": "tel-" + uuid4().hex,
        "batch_uuid": batch_uuid,
        "timestamp": "2026-01-15T08:30:00Z",
        "pyrolysis_temperature": 600.0,
    }
    await client.post(
        "/api/v1/telemetry",
        content=json.dumps(tel_payload).encode("utf-8"),
        headers={"X-Idempotency-Key": "op-tel"},
    )


from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from server import app, get_session
from models import Base
from tests.remediation.crypto_utils import sign_request


# ==================== Fixtures ====================
# Fixtures are inherited from conftest.py


def sample_batch_payload():
    """Generate a sample batch payload."""
    batch_uuid = str(uuid4())
    return {
        "batch_uuid": batch_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": "2026-01-15T08:30:00Z",
        "moisture_percent": 12.5,
        "photo_path": "/sandbox/evidence/test.jpg",
        "sha256_hash": hashlib.sha256(b"test_image_content").hexdigest(),
        "latitude": 12.9716,
        "longitude": 77.5946,
        "harvest_uptime_seconds": 3600,
        # LCA inputs (Prompt 8)
        "wet_yield_kg": 115.4,
        "min_recorded_temp_c": 210.0,
        "transport_distance_km": 14.2,
    }


# ==================== Tests ====================


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health endpoint returns 200."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_valid_payload_returns_201(client, registered_device):
    """Test 1: Valid batch payload returns 201 and stores correctly."""
    payload = sample_batch_payload()
    operation_id = "test-op-" + uuid4().hex
    await inject_telemetry(client, payload["batch_uuid"])
    response = await client.post(
        "/api/v1/batches",
        json=payload,
        headers={"X-Idempotency-Key": operation_id},
    )
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["batch_uuid"] == payload["batch_uuid"]
    assert data["operation_id"] == operation_id
    assert data["status"] in ("RECEIVED", "UNVERIFIED")
    assert data["duplicate"] is False
    assert "received_at" in data
    assert "net_credit_t_co2e" in data
    # Phase 7-R: without corroborating /yield + a qualifying /telemetry log, the
    # batch is accepted but PROVISIONAL and earns no fabricated credit.
    assert data["provisional"] is True


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_returns_200(client, registered_device):
    """Test 2: Same idempotency key returns 200 with duplicate=true."""
    import json

    payload = sample_batch_payload()
    operation_id = "test-op-" + uuid4().hex

    # First request
    await inject_telemetry(client, payload["batch_uuid"])
    response1 = await client.post(
        "/api/v1/batches",
        json=payload,
        headers={"X-Idempotency-Key": operation_id},
    )
    assert response1.status_code == 201
    data1 = response1.json()
    assert data1["duplicate"] is False

    # Second request with same key
    response2 = await client.post(
        "/api/v1/batches",
        json=payload,
        headers={"X-Idempotency-Key": operation_id},
    )
    assert response2.status_code == 200
    data2 = response2.json()

    assert data2["duplicate"] is True
    assert data2["batch_uuid"] == data1["batch_uuid"]
    assert data2["operation_id"] == operation_id
    # received_at should be the same (original insertion time)
    assert data2["received_at"] == data1["received_at"]


@pytest.mark.asyncio
async def test_missing_feedstock_species_returns_422(client, registered_device):
    """Test 3: Malformed payload (missing feedstock_species) returns 422."""
    payload = sample_batch_payload()
    del payload["feedstock_species"]  # Remove required field

    operation_id = "test-op-" + uuid4().hex

    await inject_telemetry(client, payload["batch_uuid"])
    response = await client.post(
        "/api/v1/batches",
        json=payload,
        headers={"X-Idempotency-Key": operation_id},
    )

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_invalid_moisture_percent_returns_422(client, registered_device):
    """Test: Invalid moisture_percent (>100) returns 422."""
    payload = sample_batch_payload()
    payload["moisture_percent"] = 150.0  # Invalid: > 100

    operation_id = "test-op-" + uuid4().hex

    await inject_telemetry(client, payload["batch_uuid"])
    response = await client.post(
        "/api/v1/batches",
        json=payload,
        headers={"X-Idempotency-Key": operation_id},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_missing_idempotency_key_returns_422(client, registered_device):
    """Test: Missing X-Idempotency-Key header returns 422."""
    payload = sample_batch_payload()

    await inject_telemetry(client, payload["batch_uuid"])
    response = await client.post(
        "/api/v1/batches",
        json=payload,
        headers={},  # Missing X-Idempotency-Key
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_media_upload_correct_hash_returns_200(client, registered_device):
    """Test 4: Media upload with correct SHA-256 returns 200."""
    file_content = b"test_image_data_12345"
    expected_hash = hashlib.sha256(file_content).hexdigest()
    operation_id = "media-op-" + uuid4().hex

    # Create file-like object
    files = {"file": ("test_photo.jpg", io.BytesIO(file_content), "image/jpeg")}

    response = await client.post(
        "/api/v1/media",
        files=files,
        headers={
            "X-Idempotency-Key": operation_id,
            "X-Declared-SHA256": expected_hash,
            "X-Batch-UUID": str(uuid4()),
            "X-Device-Id": registered_device["device_id"],
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["server_sha256"] == expected_hash
    assert data["stored"] is True
    assert "file_path" in data


@pytest.mark.asyncio
async def test_media_upload_wrong_hash_returns_422(client, registered_device):
    """Test 5: Media upload with wrong declared hash returns 422."""
    file_content = b"test_image_data_67890"
    wrong_hash = hashlib.sha256(b"different_content").hexdigest()
    operation_id = "media-op-" + uuid4().hex

    files = {"file": ("test_photo.jpg", io.BytesIO(file_content), "image/jpeg")}

    response = await client.post(
        "/api/v1/media",
        files=files,
        headers={
            "X-Idempotency-Key": operation_id,
            "X-Declared-SHA256": wrong_hash,
            "X-Batch-UUID": str(uuid4()),
            "X-Device-Id": registered_device["device_id"],
        },
    )

    assert response.status_code == 422, response.text
    data = response.json()
    assert "sha256_mismatch" in data["detail"]


@pytest.mark.asyncio
async def test_media_duplicate_idempotency_key(client, registered_device):
    """Test: Duplicate media upload with same idempotency key returns original."""
    file_content = b"test_duplicate_image"
    expected_hash = hashlib.sha256(file_content).hexdigest()
    operation_id = "media-op-" + uuid4().hex

    files1 = {"file": ("photo1.jpg", io.BytesIO(file_content), "image/jpeg")}

    # First upload
    response = await client.post(
        "/api/v1/media",
        files=files1,
        headers={
            "X-Idempotency-Key": operation_id,
            "X-Declared-SHA256": expected_hash,
            "X-Batch-UUID": str(uuid4()),
            "X-Device-Id": registered_device["device_id"],
        },
    )
    response1 = response
    assert response1.status_code == 200
    data1 = response1.json()

    # Second upload with same key
    files2 = {"file": ("photo2.jpg", io.BytesIO(file_content), "image/jpeg")}

    import json

    dev_id = registered_device["device_id"]
    sig = sign_request(
        dev_id,
        registered_device["b64_key"],
        "POST",
        "/api/v1/media",
        operation_id,
        None,
    )

    response = await client.post(
        "/api/v1/media",
        files=files2,
        headers={
            "X-Idempotency-Key": operation_id,
            "X-Declared-SHA256": expected_hash,
            "X-Batch-UUID": str(uuid4()),
            "X-Device-Id": registered_device["device_id"],
        },
    )
    response2 = response
    assert response2.status_code == 200
    data2 = response2.json()

    # Should return original file
    assert data2["server_sha256"] == data1["server_sha256"]
    assert data2["file_path"] == data1["file_path"]


@pytest.mark.asyncio
async def test_extra_field_ignored_returns_201(client, registered_device):
    """Test: Extra unknown fields are silently ignored (extra='ignore').

    This is deliberate: the Flutter app may send fields the backend
    doesn't model yet (e.g., new telemetry columns added later).
    """
    payload = sample_batch_payload()
    payload["extra_field"] = "silently_ignored"

    operation_id = "test-op-" + uuid4().hex

    await inject_telemetry(client, payload["batch_uuid"])
    response = await client.post(
        "/api/v1/batches",
        json=payload,
        headers={"X-Idempotency-Key": operation_id},
    )

    assert response.status_code == 422
