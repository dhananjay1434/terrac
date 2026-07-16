"""Phase 2 — verify capture_type against signed telemetry."""
import hashlib
import io
import json
import uuid

import pytest
from sqlalchemy import select

from models import MediaFile
from tests.remediation.crypto_utils import sign_media, sign_request

pytestmark = pytest.mark.asyncio

DEVICE = "test-device-reg"


def _file(content: bytes):
    return {"file": ("p.jpg", io.BytesIO(content), "image/jpeg")}


async def test_telemetry_then_media_labels_media(client, registered_device, session_factory):
    bu = str(uuid.uuid4())
    content = b"my-flame-curtain-photo"
    sha = hashlib.sha256(content).hexdigest()
    
    # POST telemetry first
    payload = {
        "telemetry_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "smoke_evidence": [{"stage": "flame_curtain", "sha256": sha}],
    }
    tel_op = "op-" + uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/telemetry",
        content=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Idempotency-Key": tel_op,
            "X-Signature": sign_request(DEVICE, "", "POST", "/api/v1/telemetry", tel_op, payload), 
            "X-Device-Id": DEVICE
        }
    )
    assert r.status_code == 201
    
    # Upload media without header
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
    assert r.status_code == 200

    async with session_factory() as s:
        m = (await s.execute(select(MediaFile).where(MediaFile.operation_id == op))).scalar_one()
        assert m.capture_type == "flame_curtain"
        assert m.capture_type_verified is True


async def test_media_then_telemetry_updates_label(client, registered_device, session_factory):
    bu = str(uuid.uuid4())
    content = b"my-quenching-photo"
    sha = hashlib.sha256(content).hexdigest()
    
    # Upload media without header
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
    assert r.status_code == 200

    async with session_factory() as s:
        m = (await s.execute(select(MediaFile).where(MediaFile.operation_id == op))).scalar_one()
        assert m.capture_type is None
        assert m.capture_type_verified is False
        
    # POST telemetry
    payload = {
        "telemetry_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "smoke_evidence": [{"stage": "quenching", "sha256": sha}],
    }
    tel_op = "op-" + uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/telemetry",
        content=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Idempotency-Key": tel_op,
            "X-Signature": sign_request(DEVICE, "", "POST", "/api/v1/telemetry", tel_op, payload), 
            "X-Device-Id": DEVICE
        }
    )
    assert r.status_code == 201

    async with session_factory() as s:
        m = (await s.execute(select(MediaFile).where(MediaFile.operation_id == op))).scalar_one()
        assert m.capture_type == "quenching"
        assert m.capture_type_verified is True


async def test_telemetry_overrides_lying_client_hint(client, registered_device, session_factory):
    bu = str(uuid.uuid4())
    content = b"lying-client-photo"
    sha = hashlib.sha256(content).hexdigest()
    
    # Upload media WITH lying header
    op = "m-" + uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/media",
        files=_file(content),
        headers={
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": bu,
            "X-Device-Id": DEVICE,
            "X-Capture-Type": "quenching", # Lyin'
            "X-Signature": sign_media(DEVICE, op, sha, bu),
        },
    )
    assert r.status_code == 200

    async with session_factory() as s:
        m = (await s.execute(select(MediaFile).where(MediaFile.operation_id == op))).scalar_one()
        assert m.capture_type == "quenching"
        assert m.capture_type_verified is False
        
    # POST telemetry truth
    payload = {
        "telemetry_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "smoke_evidence": [{"stage": "flame_curtain", "sha256": sha}],
    }
    tel_op = "op-" + uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/telemetry",
        content=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Idempotency-Key": tel_op,
            "X-Signature": sign_request(DEVICE, "", "POST", "/api/v1/telemetry", tel_op, payload), 
            "X-Device-Id": DEVICE
        }
    )
    assert r.status_code == 201

    async with session_factory() as s:
        m = (await s.execute(select(MediaFile).where(MediaFile.operation_id == op))).scalar_one()
        assert m.capture_type == "flame_curtain"
        assert m.capture_type_verified is True
