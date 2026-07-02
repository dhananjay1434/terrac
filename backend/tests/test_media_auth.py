"""Phase 15-A — the media evidence channel is Ed25519-authenticated.

/api/v1/media used to be the only state-changing endpoint with no signature — an
anonymous checksum, not proof. It now requires a valid Ed25519 signature over the
frozen media canonical, binds the uploading device to the batch owner, and returns
400 (not 500) on a malformed batch UUID.
"""

import hashlib
import io
import uuid

import pytest

from tests.remediation.crypto_utils import sign_media

pytestmark = pytest.mark.asyncio

DEVICE = "test-device-reg"  # seeded + enrolled by conftest


def _file(content: bytes):
    return {"file": ("p.jpg", io.BytesIO(content), "image/jpeg")}


async def _make_batch(client, registered_device, bu, sha):
    """Create a batch owned by DEVICE that declares photo hash `sha`."""
    import json
    from datetime import datetime, timezone
    from tests.remediation.crypto_utils import sign_request

    payload = {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
        "sha256_hash": sha,
    }
    op = "batch-" + bu[:8]
    r = await client.post(
        "/api/v1/batches",
        content=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Idempotency-Key": op,
            "X-Device-Id": DEVICE,
            "X-Signature": sign_request(
                DEVICE, "", "POST", "/api/v1/batches", op, payload
            ),
        },
    )
    assert r.status_code == 201, r.text


async def test_unsigned_media_rejected(client, registered_device):
    content = b"photo-bytes"
    sha = hashlib.sha256(content).hexdigest()
    r = await client.post(
        "/api/v1/media",
        files=_file(content),
        headers={
            "X-Idempotency-Key": "m-" + uuid.uuid4().hex[:8],
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": str(uuid.uuid4()),
            "X-Device-Id": DEVICE,
        },
    )
    assert r.status_code == 401, r.text  # missing_signature


async def test_signed_media_accepted_and_anchors(client, registered_device):
    bu = str(uuid.uuid4())
    content = b"real-photo-bytes"
    sha = hashlib.sha256(content).hexdigest()
    await _make_batch(client, registered_device, bu, sha)
    op = "m-" + uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/media",
        files=_file(content),
        headers={
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": bu,
            "X-Device-Id": DEVICE,
            "X-Signature": sign_media(DEVICE, op, sha, bu),
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["server_sha256"] == sha


async def test_signature_over_wrong_hash_rejected(client, registered_device):
    # Signature computed over a DIFFERENT declared hash than the header sends.
    bu = str(uuid.uuid4())
    content = b"x"
    sha = hashlib.sha256(content).hexdigest()
    op = "m-" + uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/media",
        files=_file(content),
        headers={
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": bu,
            "X-Device-Id": DEVICE,
            "X-Signature": sign_media(DEVICE, op, "b" * 64, bu),  # signed wrong hash
        },
    )
    assert r.status_code == 403, r.text  # signature_mismatch


async def test_malformed_batch_uuid_is_400(client, registered_device):
    content = b"y"
    sha = hashlib.sha256(content).hexdigest()
    op = "m-" + uuid.uuid4().hex[:8]
    bad = "not-a-uuid"
    r = await client.post(
        "/api/v1/media",
        files=_file(content),
        headers={
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": bad,
            "X-Device-Id": DEVICE,
            "X-Signature": sign_media(DEVICE, op, sha, bad),
        },
    )
    assert r.status_code == 400, r.text  # invalid_batch_uuid, not 500


async def test_non_owner_cannot_anchor(client, registered_device, session_factory):
    # Batch owned by DEVICE; a different enrolled device tries to anchor evidence.
    bu = str(uuid.uuid4())
    content = b"owned-photo"
    sha = hashlib.sha256(content).hexdigest()
    await _make_batch(client, registered_device, bu, sha)

    other = "test-device-1"  # also enrolled with the same test key by conftest
    op = "m-" + uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/media",
        files=_file(content),
        headers={
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": bu,
            "X-Device-Id": other,
            "X-Signature": sign_media(other, op, sha, bu),
        },
    )
    assert r.status_code == 403, r.text  # not_your_batch
