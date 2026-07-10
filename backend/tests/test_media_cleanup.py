"""P1-B5 — a rejected/failed media upload must leave no orphaned file on disk.

Before the fix, the batch-UUID parse (400) and the ownership check (403) both
ran AFTER the bytes were written, stranding a file. Now the UUID is validated
before the write, and everything after the write is wrapped so any failure rolls
back the DB and unlinks the file.
"""

import hashlib
import io
import json
import uuid
from datetime import datetime, timezone

import pytest

from server import UPLOAD_DIR
from tests.remediation.crypto_utils import sign_media, sign_request

pytestmark = pytest.mark.asyncio

DEVICE = "test-device-reg"  # seeded + enrolled by conftest


def _file(content: bytes):
    return {"file": ("p.jpg", io.BytesIO(content), "image/jpeg")}


async def _make_batch(client, bu, sha):
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


async def test_malformed_uuid_writes_no_file(client, registered_device):
    content = b"z-bytes"
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
    assert r.status_code == 400, r.text
    assert not (UPLOAD_DIR / DEVICE / f"{op}.bin").exists()


async def test_non_owner_leaves_no_orphan_file(client, registered_device):
    bu = str(uuid.uuid4())
    content = b"owned-photo-bytes"
    sha = hashlib.sha256(content).hexdigest()
    await _make_batch(client, bu, sha)

    other = "test-device-1"  # also enrolled by conftest
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
    assert not (UPLOAD_DIR / other / f"{op}.bin").exists()
