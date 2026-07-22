"""V8 deferred R1 — entity-scoped evidence media (farmer + dispatch).

Covers the generalized `/api/v1/media` endpoint: exactly-one-scope enforcement
(batch XOR subject), ownership per subject type (dispatch has real
device-ownership; farmer is existence-only — see
`services/evidence.py::_assert_farmer_ownership` docstring for why), the v2
signature canonical, and that the pre-existing batch-media path is completely
unaffected (back-compat).
"""

from __future__ import annotations

import io
import json
import uuid

import pytest

pytestmark = pytest.mark.asyncio

DEVICE = "test-device-reg"
OTHER_DEVICE = "test-device-1"


def _sha256_hex(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _media_headers_v2(*, device_id, op_id, declared_sha256, subject_type, subject_uuid):
    """V2 canonical: POST\\n/api/v1/media\\n{op}\\n{sha}\\n{subject_type}:{subject_uuid}\\n{device_id}."""
    import base64
    import hashlib as _hashlib
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    seed = bytes(range(32))  # matches crypto_utils._SEED / TEST_PUBLIC_KEY_B64
    priv = Ed25519PrivateKey.from_private_bytes(seed)
    canonical = "\n".join(
        [
            "POST",
            "/api/v1/media",
            op_id,
            declared_sha256.lower(),
            f"{subject_type}:{subject_uuid}",
            device_id,
        ]
    ).encode("utf-8")
    sig = base64.urlsafe_b64encode(priv.sign(canonical)).decode("utf-8").rstrip("=")
    return {
        "X-Idempotency-Key": op_id,
        "X-Declared-SHA256": declared_sha256,
        "X-Subject-Type": subject_type,
        "X-Subject-UUID": subject_uuid,
        "X-Media-Canonical": "2",
        "X-Device-Id": device_id,
        "X-Signature": sig,
    }


async def _create_farmer(client, farmer_uuid: str, project_id: str = "proj-r1"):
    payload = {
        "farmer_uuid": farmer_uuid,
        "project_id": project_id,
        "first_name": "Asha",
        "mobile_number": f"9{farmer_uuid[:9].replace('-', '')}",
    }
    from tests.remediation.crypto_utils import sign_request

    op_id = f"farmer-create-{farmer_uuid}"
    resp = await client.post(
        "/api/v1/farmers",
        content=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Idempotency-Key": op_id,
            "X-Device-Id": DEVICE,
            "X-Signature": sign_request(DEVICE, "", "POST", "/api/v1/farmers", op_id, payload),
        },
    )
    assert resp.status_code == 201, resp.text


async def _create_dispatch(client, dispatch_uuid: str, device_id: str = DEVICE):
    from tests.remediation.crypto_utils import sign_request

    payload = {"dispatch_uuid": dispatch_uuid, "kind": "biomass"}
    op_id = f"dispatch-create-{dispatch_uuid}"
    resp = await client.post(
        "/api/v1/dispatch",
        content=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Idempotency-Key": op_id,
            "X-Device-Id": device_id,
            "X-Signature": sign_request(device_id, "", "POST", "/api/v1/dispatch", op_id, payload),
        },
    )
    assert resp.status_code == 201, resp.text


async def test_farmer_media_upload_happy_path(client):
    farmer_uuid = str(uuid.uuid4())
    await _create_farmer(client, farmer_uuid)
    content = b"farmer-signature-bytes"
    sha = _sha256_hex(content)
    headers = _media_headers_v2(
        device_id=DEVICE,
        op_id="fm-op-1",
        declared_sha256=sha,
        subject_type="farmer",
        subject_uuid=farmer_uuid,
    )
    files = {"file": ("sig.jpg", io.BytesIO(content), "image/jpeg")}
    resp = await client.post("/api/v1/media", files=files, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["server_sha256"] == sha


async def test_dispatch_media_upload_happy_path(client):
    dispatch_uuid = str(uuid.uuid4())
    await _create_dispatch(client, dispatch_uuid)
    content = b"truck-photo-bytes"
    sha = _sha256_hex(content)
    headers = _media_headers_v2(
        device_id=DEVICE,
        op_id="dm-op-1",
        declared_sha256=sha,
        subject_type="dispatch",
        subject_uuid=dispatch_uuid,
    )
    files = {"file": ("truck.jpg", io.BytesIO(content), "image/jpeg")}
    resp = await client.post("/api/v1/media", files=files, headers=headers)
    assert resp.status_code == 200, resp.text


async def test_batch_media_backcompat_unchanged(client):
    """The pre-existing v1 batch-only path must behave exactly as before —
    no scope headers beyond X-Batch-UUID, no X-Media-Canonical."""
    from tests.remediation.crypto_utils import sign_media

    content = b"batch-photo-bytes"
    sha = _sha256_hex(content)
    batch_uuid = str(uuid.uuid4())
    op_id = "batch-op-1"
    headers = {
        "X-Idempotency-Key": op_id,
        "X-Declared-SHA256": sha,
        "X-Batch-UUID": batch_uuid,
        "X-Device-Id": DEVICE,
        "X-Signature": sign_media(DEVICE, op_id, sha, batch_uuid),
    }
    files = {"file": ("batch.jpg", io.BytesIO(content), "image/jpeg")}
    resp = await client.post("/api/v1/media", files=files, headers=headers)
    assert resp.status_code == 200, resp.text


async def test_both_scopes_rejected_400(client):
    dispatch_uuid = str(uuid.uuid4())
    content = b"ambiguous"
    sha = _sha256_hex(content)
    headers = _media_headers_v2(
        device_id=DEVICE,
        op_id="ambig-op-1",
        declared_sha256=sha,
        subject_type="dispatch",
        subject_uuid=dispatch_uuid,
    )
    headers["X-Batch-UUID"] = str(uuid.uuid4())
    files = {"file": ("x.jpg", io.BytesIO(content), "image/jpeg")}
    resp = await client.post("/api/v1/media", files=files, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "ambiguous_media_scope"


async def test_no_scope_rejected_400(client):
    from tests.remediation.crypto_utils import sign_media

    content = b"no-scope"
    sha = _sha256_hex(content)
    op_id = "noscope-op-1"
    headers = {
        "X-Idempotency-Key": op_id,
        "X-Declared-SHA256": sha,
        "X-Device-Id": DEVICE,
        "X-Signature": sign_media(DEVICE, op_id, sha, ""),
    }
    files = {"file": ("x.jpg", io.BytesIO(content), "image/jpeg")}
    resp = await client.post("/api/v1/media", files=files, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "missing_media_scope"


async def test_foreign_device_dispatch_upload_403(client):
    dispatch_uuid = str(uuid.uuid4())
    await _create_dispatch(client, dispatch_uuid, device_id=DEVICE)
    content = b"someone-elses-truck"
    sha = _sha256_hex(content)
    headers = _media_headers_v2(
        device_id=OTHER_DEVICE,
        op_id="foreign-dispatch-op-1",
        declared_sha256=sha,
        subject_type="dispatch",
        subject_uuid=dispatch_uuid,
    )
    files = {"file": ("x.jpg", io.BytesIO(content), "image/jpeg")}
    resp = await client.post("/api/v1/media", files=files, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "not_your_dispatch"


async def test_v2_canonical_tamper_rejected(client):
    farmer_uuid = str(uuid.uuid4())
    await _create_farmer(client, farmer_uuid)
    content = b"tampered-test"
    sha = _sha256_hex(content)
    headers = _media_headers_v2(
        device_id=DEVICE,
        op_id="tamper-op-1",
        declared_sha256=sha,
        subject_type="farmer",
        subject_uuid=farmer_uuid,
    )
    headers["X-Subject-UUID"] = str(uuid.uuid4())  # swap subject after signing
    files = {"file": ("x.jpg", io.BytesIO(content), "image/jpeg")}
    resp = await client.post("/api/v1/media", files=files, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "signature_mismatch"


async def test_duplicate_idempotency_key_is_noop(client):
    farmer_uuid = str(uuid.uuid4())
    await _create_farmer(client, farmer_uuid)
    content = b"dup-test"
    sha = _sha256_hex(content)
    headers = _media_headers_v2(
        device_id=DEVICE,
        op_id="dup-op-1",
        declared_sha256=sha,
        subject_type="farmer",
        subject_uuid=farmer_uuid,
    )
    files1 = {"file": ("x.jpg", io.BytesIO(content), "image/jpeg")}
    resp1 = await client.post("/api/v1/media", files=files1, headers=headers)
    assert resp1.status_code == 200

    files2 = {"file": ("x.jpg", io.BytesIO(content), "image/jpeg")}
    resp2 = await client.post("/api/v1/media", files=files2, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["server_sha256"] == resp1.json()["server_sha256"]
