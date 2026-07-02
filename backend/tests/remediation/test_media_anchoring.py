from tests.remediation.crypto_utils import TEST_PUBLIC_KEY_B64, sign_media
import json
import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
import pytest_asyncio
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def registered_device(client: AsyncClient, session_factory):
    from models import EnrollmentToken
    import base64

    async with session_factory() as session:
        t = EnrollmentToken(token="test-credit-media")
        session.add(t)
        await session.commit()

    b64_key = TEST_PUBLIC_KEY_B64
    dev_id = "test-device-media"
    payload = {"device_id": dev_id, "public_key": b64_key}
    headers = {"X-Enrollment-Token": "test-credit-media"}
    await client.post(
        "/api/v1/register", content=json.dumps(payload).encode("utf-8"), headers=headers
    )

    return {"device_id": dev_id, "b64_key": b64_key}


async def test_media_anchors_by_explicit_batch_uuid(
    client: AsyncClient, registered_device, session_factory
):
    from tests.remediation.crypto_utils import sign_request
    from models import Batch, MediaFile

    b1_uuid = str(uuid.uuid4())
    dev_id = registered_device["device_id"]
    b64_key = registered_device["b64_key"]

    import hashlib

    # Phase 9 media-integrity: the batch's declared photo hash must match the
    # uploaded photo, otherwise the upload cannot verify the batch.
    photo_hash = hashlib.sha256(b"fake photo data").hexdigest()
    # 1. Create batch with sha256_hash but no photo yet -> should be UNVERIFIED
    payload = {
        "batch_uuid": b1_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 14.5,
        "harvest_uptime_seconds": 3600,
        "min_recorded_temp_c": 0.0,
        "wet_yield_kg": 100.0,
        "transport_distance_km": 0.0,
        "sha256_hash": photo_hash,
    }

    headers = {
        "X-Device-Id": dev_id,
        "X-Idempotency-Key": "op-batch-media",
        "X-Signature": sign_request(
            dev_id, b64_key, "POST", "/api/v1/batches", "op-batch-media", payload
        ),
    }
    resp1 = await client.post(
        "/api/v1/batches", content=json.dumps(payload).encode("utf-8"), headers=headers
    )
    assert resp1.status_code == 201
    assert resp1.json()["status"] == "UNVERIFIED"

    # 2. Upload media with explicit batch_uuid
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"fake photo data")
        tmp_name = tmp.name

    import hashlib

    actual_hash = hashlib.sha256(b"fake photo data").hexdigest()

    with open(tmp_name, "rb") as f:
        resp2 = await client.post(
            "/api/v1/media",
            files={"file": ("photo.jpg", f, "image/jpeg")},
            headers={
                "X-Idempotency-Key": "op-media-anch",
                "X-Declared-SHA256": actual_hash,
                "X-Batch-UUID": b1_uuid,
                "X-Device-Id": dev_id,
                "X-Signature": sign_media(
                    dev_id, "op-media-anch", actual_hash, b1_uuid
                ),
            },
        )
    assert resp2.status_code == 200

    # Check if batch status upgraded
    async with session_factory() as session:
        batch = (
            await session.execute(
                select(Batch).where(Batch.batch_uuid == uuid.UUID(b1_uuid))
            )
        ).scalar_one()
        assert batch.status == "RECEIVED"

        media = (
            await session.execute(
                select(MediaFile).where(MediaFile.operation_id == "op-media-anch")
            )
        ).scalar_one()
        assert media.batch_uuid == uuid.UUID(b1_uuid)


async def test_duplicate_photo_hash_does_not_500(
    client: AsyncClient, registered_device
):
    from tests.remediation.crypto_utils import sign_request

    b1_uuid = str(uuid.uuid4())
    b2_uuid = str(uuid.uuid4())
    dev_id = registered_device["device_id"]
    b64_key = registered_device["b64_key"]

    import hashlib

    actual_hash = hashlib.sha256(b"same photo data").hexdigest()

    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"same photo data")
        tmp_name = tmp.name

    # Upload first time for batch 1
    with open(tmp_name, "rb") as f:
        resp1 = await client.post(
            "/api/v1/media",
            files={"file": ("photo.jpg", f, "image/jpeg")},
            headers={
                "X-Idempotency-Key": "op-media-dup1",
                "X-Declared-SHA256": actual_hash,
                "X-Batch-UUID": b1_uuid,
                "X-Device-Id": dev_id,
                "X-Signature": sign_media(
                    dev_id, "op-media-dup1", actual_hash, b1_uuid
                ),
            },
        )
    assert resp1.status_code == 200

    # Upload second time for batch 2 (same photo bytes -> same hash)
    with open(tmp_name, "rb") as f:
        resp2 = await client.post(
            "/api/v1/media",
            files={"file": ("photo2.jpg", f, "image/jpeg")},
            headers={
                "X-Idempotency-Key": "op-media-dup2",
                "X-Declared-SHA256": actual_hash,
                "X-Batch-UUID": b2_uuid,
                "X-Device-Id": dev_id,
                "X-Signature": sign_media(
                    dev_id, "op-media-dup2", actual_hash, b2_uuid
                ),
            },
        )
    assert resp2.status_code == 200

    # Neither should 500


async def test_reused_photo_anchors_to_correct_batch(
    client: AsyncClient, registered_device, session_factory
):
    # Already implicitly tested by duplicate_photo_hash test, but let's verify DB
    from models import MediaFile

    b1_uuid = str(uuid.uuid4())
    b2_uuid = str(uuid.uuid4())
    dev_id = registered_device["device_id"]

    import hashlib

    actual_hash = hashlib.sha256(b"another photo").hexdigest()

    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"another photo")
        tmp_name = tmp.name

    # batch 1 media
    with open(tmp_name, "rb") as f:
        await client.post(
            "/api/v1/media",
            files={"file": ("photo.jpg", f, "image/jpeg")},
            headers={
                "X-Idempotency-Key": "op-media-ru1",
                "X-Declared-SHA256": actual_hash,
                "X-Batch-UUID": b1_uuid,
                "X-Device-Id": dev_id,
                "X-Signature": sign_media(dev_id, "op-media-ru1", actual_hash, b1_uuid),
            },
        )

    # batch 2 media
    with open(tmp_name, "rb") as f:
        await client.post(
            "/api/v1/media",
            files={"file": ("photo.jpg", f, "image/jpeg")},
            headers={
                "X-Idempotency-Key": "op-media-ru2",
                "X-Declared-SHA256": actual_hash,
                "X-Batch-UUID": b2_uuid,
                "X-Device-Id": dev_id,
                "X-Signature": sign_media(dev_id, "op-media-ru2", actual_hash, b2_uuid),
            },
        )

    async with session_factory() as session:
        m1 = (
            await session.execute(
                select(MediaFile).where(MediaFile.operation_id == "op-media-ru1")
            )
        ).scalar_one()
        assert m1.batch_uuid == uuid.UUID(b1_uuid)

        m2 = (
            await session.execute(
                select(MediaFile).where(MediaFile.operation_id == "op-media-ru2")
            )
        ).scalar_one()
        assert m2.batch_uuid == uuid.UUID(b2_uuid)


async def test_missing_device_id_on_media_rejected(client: AsyncClient):
    import tempfile
    import hashlib

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"missing device id")
        tmp_name = tmp.name

    actual_hash = hashlib.sha256(b"missing device id").hexdigest()

    with open(tmp_name, "rb") as f:
        resp = await client.post(
            "/api/v1/media",
            files={"file": ("photo.jpg", f, "image/jpeg")},
            headers={
                "X-Idempotency-Key": "op-media-nodev",
                "X-Declared-SHA256": actual_hash,
                "X-Batch-UUID": str(uuid.uuid4()),
                "X-Signature": "dummy",
                # Intentionally missing X-Device-Id
            },
        )
    # Phase 15-A: media now requires auth; a missing device id is rejected
    # (422 from the required header, or 403 unknown_device) — either way, not stored.
    assert resp.status_code in (401, 403, 422)
