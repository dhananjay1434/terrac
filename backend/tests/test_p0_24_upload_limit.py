"""P0-24 regression: upload must reject >10MB before exhausting memory."""

import hashlib
import io

import pytest
from httpx import AsyncClient, ASGITransport

from server import app
from tests.remediation.crypto_utils import sign_media


@pytest.mark.asyncio
async def test_upload_rejects_oversize_file(client):
    # 11 MB of zero bytes — over the 10 MB endpoint cap (under the 12 MB middleware
    # cap, so it reaches the streaming size check). Signed so auth passes first.
    payload = b"\0" * (11 * 1024 * 1024)
    sha = hashlib.sha256(payload).hexdigest()
    batch_uuid = "123e4567-e89b-12d3-a456-426614174000"
    op = "op-oversize"
    r = await client.post(
        "/api/v1/media",
        files={"file": ("big.bin", io.BytesIO(payload), "application/octet-stream")},
        headers={
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Device-Id": "test-device-1",
            "X-Batch-UUID": batch_uuid,
            "X-Signature": sign_media("test-device-1", op, sha, batch_uuid),
        },
    )
    assert r.status_code == 413
    assert r.json()["detail"] == "file_too_large"


@pytest.mark.asyncio
async def test_upload_accepts_small_file(client):
    payload = b"hello world"
    sha = hashlib.sha256(payload).hexdigest()
    batch_uuid = "123e4567-e89b-12d3-a456-426614174001"
    op = "op-small"
    r = await client.post(
        "/api/v1/media",
        files={"file": ("hello.txt", io.BytesIO(payload), "text/plain")},
        headers={
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Device-Id": "test-device-1",
            "X-Batch-UUID": batch_uuid,
            "X-Signature": sign_media("test-device-1", op, sha, batch_uuid),
        },
    )
    assert r.status_code in (200, 201)
    assert r.json()["server_sha256"] == sha
