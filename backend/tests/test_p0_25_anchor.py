"""P0-25 regression: every photo must anchor to its batch by FK; orphan rows forbidden."""

import hashlib
import io
import uuid
import hmac
import json

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from server import app
from models import Batch, MediaFile


@pytest.mark.asyncio
async def test_photo_then_batch_anchors_correctly(client, session_factory):
    payload = b"image-bytes-here"
    sha = hashlib.sha256(payload).hexdigest()
    batch_uuid = str(uuid.uuid4())

    from tests.remediation.crypto_utils import sign_media

    # 1. Photo lands first (signed by test-device-1, which will own the batch)
    r1 = await client.post(
        "/api/v1/media",
        files={"file": ("x.jpg", io.BytesIO(payload), "image/jpeg")},
        headers={
            "X-Idempotency-Key": "op-photo-1",
            "X-Declared-SHA256": sha,
            "X-Device-Id": "test-device-1",
            "X-Batch-UUID": batch_uuid,
            "X-Signature": sign_media("test-device-1", "op-photo-1", sha, batch_uuid),
        },
    )
    assert r1.status_code in (200, 201)

    # 2. Batch lands second
    batch_dict = {
        "batch_uuid": batch_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": "2026-01-01T00:00:00Z",
        "moisture_percent": 10.0,
        "sha256_hash": sha,
        "wet_yield_kg": 100.0,
        "min_recorded_temp_c": 650.0,
        "harvest_uptime_seconds": 3600,
        "transport_distance_km": 0.0,
    }
    raw_body = json.dumps(batch_dict).encode("utf-8")

    canonical = "\n".join(
        [
            "POST",
            "/api/v1/batches",
            "op-batch-1",
            hashlib.sha256(raw_body).hexdigest(),
            "test-device-1",
        ]
    ).encode("utf-8")
    # Phase 5: sign with the enrolled device's Ed25519 private key.
    from tests.remediation.crypto_utils import sign_canonical

    sig = sign_canonical(canonical)

    r2 = await client.post(
        "/api/v1/batches",
        content=raw_body,
        headers={
            "X-Idempotency-Key": "op-batch-1",
            "X-Signature": sig,
            "X-Device-Id": "test-device-1",
            "Content-Type": "application/json",
        },
    )
    assert r2.status_code == 201
    assert r2.json()["status"] == "RECEIVED"

    # FK must be populated.
    async with session_factory() as db_session:
        media_row = (
            await db_session.execute(
                select(MediaFile).where(MediaFile.sha256_hash == sha)
            )
        ).scalar_one()
        assert str(media_row.batch_uuid) == batch_uuid


@pytest.mark.asyncio
async def test_batch_without_photo_is_unverified(client):
    batch_uuid = str(uuid.uuid4())
    sha = hashlib.sha256(b"will-arrive-later").hexdigest()

    r = await client.post(
        "/api/v1/batches",
        json={
            "batch_uuid": batch_uuid,
            "feedstock_species": "Lantana_camara",
            "harvest_timestamp": "2026-01-01T00:00:00Z",
            "moisture_percent": 10.0,
            "sha256_hash": sha,
            "wet_yield_kg": 100.0,
            "min_recorded_temp_c": 650.0,
            "transport_distance_km": 0.0,
            "harvest_uptime_seconds": 3600,
        },
        headers={"X-Idempotency-Key": "op-orphan"},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "UNVERIFIED"


@pytest.mark.asyncio
async def test_late_photo_upgrades_batch_to_received(client, session_factory):
    batch_uuid = str(uuid.uuid4())
    payload = b"late-photo"
    sha = hashlib.sha256(payload).hexdigest()

    # Batch first -> UNVERIFIED
    await client.post(
        "/api/v1/batches",
        json={
            "batch_uuid": batch_uuid,
            "feedstock_species": "Lantana_camara",
            "harvest_timestamp": "2026-01-01T00:00:00Z",
            "moisture_percent": 10.0,
            "sha256_hash": sha,
            "wet_yield_kg": 100.0,
            "min_recorded_temp_c": 650.0,
            "harvest_uptime_seconds": 3600,
            "transport_distance_km": 0.0,
        },
        headers={"X-Idempotency-Key": "op-late-1"},
    )

    # Photo arrives second -> should flip RECEIVED. The batch above was auto-signed
    # by the conftest client as "test-device-reg", so the owner uploads the photo.
    from tests.remediation.crypto_utils import sign_media

    await client.post(
        "/api/v1/media",
        files={"file": ("late.jpg", io.BytesIO(payload), "image/jpeg")},
        headers={
            "X-Idempotency-Key": "op-late-2",
            "X-Declared-SHA256": sha,
            "X-Device-Id": "test-device-reg",
            "X-Batch-UUID": batch_uuid,
            "X-Signature": sign_media("test-device-reg", "op-late-2", sha, batch_uuid),
        },
    )

    async with session_factory() as db_session:
        batch_row = (
            await db_session.execute(
                select(Batch).where(Batch.batch_uuid == str(uuid.UUID(batch_uuid)))
            )
        ).scalar_one()
        assert batch_row.status == "RECEIVED"
