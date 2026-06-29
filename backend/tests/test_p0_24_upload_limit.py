"""P0-24 regression: upload must reject >10MB before exhausting memory."""
import hashlib
import io

import pytest
from httpx import AsyncClient, ASGITransport

from server import app


@pytest.mark.asyncio
async def test_upload_rejects_oversize_file(client):
    # 11 MB of zero bytes — over the 10 MB cap.
    payload = b"\0" * (11 * 1024 * 1024)
    sha = hashlib.sha256(payload).hexdigest()
    batch_uuid = "123e4567-e89b-12d3-a456-426614174000"
    r = await client.post(
        "/api/v1/media",
        files={"file": ("big.bin", io.BytesIO(payload), "application/octet-stream")},
        headers={
            "X-Idempotency-Key": "op-oversize",
            "X-Declared-SHA256": sha,
            "X-Device-Id": "test-device-1",
            "X-Batch-UUID": batch_uuid
        },
    )
    assert r.status_code == 413
    assert r.json()["detail"] == "file_too_large"


@pytest.mark.asyncio
async def test_upload_accepts_small_file(client):
    payload = b"hello world"
    sha = hashlib.sha256(payload).hexdigest()
    batch_uuid = "123e4567-e89b-12d3-a456-426614174001"
    r = await client.post(
        "/api/v1/media",
        files={"file": ("hello.txt", io.BytesIO(payload), "text/plain")},
        headers={
            "X-Idempotency-Key": "op-small",
            "X-Declared-SHA256": sha,
            "X-Device-Id": "test-device-1",
            "X-Batch-UUID": batch_uuid
        },
    )
    assert r.status_code in (200, 201)
    assert r.json()["server_sha256"] == sha
