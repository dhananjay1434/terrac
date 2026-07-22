"""V8 Part 4 (K) — per-media reviewer verdict loop.

Covers: PATCH /api/v1/portal/media/{operation_id}/verify (role-gated,
persists status+remarks, audited); the batch-detail media list surfaces the
verdict; and the device-facing GET /api/v1/batches/{uuid}/media-verdicts read
(ownership-checked, only verified rows returned).
"""

from __future__ import annotations

import hashlib
import io
import json
import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def _login_admin(client, session_factory, role="admin"):
    from portal.auth import hash_password
    from models import PortalUser

    async with session_factory() as session:
        session.add(
            PortalUser(
                email=f"{role}-verdict@test.local",
                password_hash=hash_password("correct-horse-battery-staple"),
                role=role,
                disabled=False,
            )
        )
        await session.commit()
    resp = await client.post(
        "/api/v1/portal/login",
        json={"email": f"{role}-verdict@test.local", "password": "correct-horse-battery-staple"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['token']}"}


async def _upload_media(client, batch_uuid, op):
    content = b"fake-image-bytes-for-verdict-test"
    sha = hashlib.sha256(content).hexdigest()
    from tests.remediation.crypto_utils import sign_media

    resp = await client.post(
        "/api/v1/media",
        files={"file": ("photo.jpg", io.BytesIO(content), "image/jpeg")},
        headers={
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": batch_uuid,
            "X-Device-Id": "test-device-reg",
            "X-Signature": sign_media("test-device-reg", op, sha, batch_uuid),
        },
    )
    assert resp.status_code == 200, resp.text
    return op  # operation_id == the idempotency key used at upload


async def test_verify_requires_verifier_or_admin_role(client):
    resp = await client.patch(
        "/api/v1/portal/media/op-1/verify", json={"status": "rejected"}
    )
    assert resp.status_code == 401


async def test_verify_persists_status_and_remarks(client, session_factory):
    bu = str(uuid.uuid4())
    op = await _upload_media(client, bu, "op-verdict-1")
    headers = await _login_admin(client, session_factory)

    resp = await client.patch(
        f"/api/v1/portal/media/{op}/verify",
        json={"status": "rejected", "remarks": "kiln ID not visible"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["verification_status"] == "rejected"
    assert body["verification_remarks"] == "kiln ID not visible"


async def test_verify_unknown_operation_id_404(client, session_factory):
    headers = await _login_admin(client, session_factory)
    resp = await client.patch(
        "/api/v1/portal/media/does-not-exist/verify",
        json={"status": "approved"},
        headers=headers,
    )
    assert resp.status_code == 404


async def test_verify_invalid_status_rejected(client, session_factory):
    bu = str(uuid.uuid4())
    op = await _upload_media(client, bu, "op-verdict-2")
    headers = await _login_admin(client, session_factory)
    resp = await client.patch(
        f"/api/v1/portal/media/{op}/verify",
        json={"status": "bogus"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_batch_detail_media_list_includes_verdict(client, session_factory):
    from tests.remediation.crypto_utils import sign_request

    bu = str(uuid.uuid4())
    op = await _upload_media(client, bu, "op-verdict-3")
    batch_payload = {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": "2026-01-01T00:00:00Z",
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
    }
    await client.post(
        "/api/v1/batches",
        content=json.dumps(batch_payload).encode("utf-8"),
        headers={
            "X-Idempotency-Key": "op-verdict-3-batch",
            "X-Device-Id": "test-device-reg",
            "X-Signature": sign_request(
                "test-device-reg", "", "POST", "/api/v1/batches", "op-verdict-3-batch", batch_payload
            ),
        },
    )
    headers = await _login_admin(client, session_factory)
    await client.patch(
        f"/api/v1/portal/media/{op}/verify",
        json={"status": "approved"},
        headers=headers,
    )

    detail = await client.get(f"/api/v1/portal/batches/{bu}", headers=headers)
    assert detail.status_code == 200
    media = detail.json()["media"]
    assert any(m["verification_status"] == "approved" for m in media)


async def test_device_media_verdicts_returns_only_reviewed(client, session_factory):
    bu = str(uuid.uuid4())
    op1 = await _upload_media(client, bu, "op-verdict-4a")
    await _upload_media(client, bu, "op-verdict-4b")  # never reviewed
    headers = await _login_admin(client, session_factory)
    await client.patch(
        f"/api/v1/portal/media/{op1}/verify",
        json={"status": "rejected", "remarks": "blurry"},
        headers=headers,
    )

    resp = await client.get(f"/api/v1/batches/{bu}/media-verdicts")
    assert resp.status_code == 200
    media = resp.json()["media"]
    assert len(media) == 1  # only the reviewed one
    assert media[0]["operation_id"] == op1
    assert media[0]["verification_remarks"] == "blurry"


async def test_device_media_verdicts_foreign_device_forbidden(client, session_factory):
    """A different device must not read another device's batch verdicts."""
    import hashlib as _hashlib

    from tests.remediation.crypto_utils import sign_canonical, sign_request

    bu = str(uuid.uuid4())
    await _upload_media(client, bu, "op-verdict-5")
    # Establish batch ownership by posting a batch as test-device-reg.
    payload = {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": "2026-01-01T00:00:00Z",
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
    }
    await client.post(
        "/api/v1/batches",
        content=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Idempotency-Key": "op-verdict-5-batch",
            "X-Device-Id": "test-device-reg",
            "X-Signature": sign_request(
                "test-device-reg", "", "POST", "/api/v1/batches", "op-verdict-5-batch", payload
            ),
        },
    )

    # GET has no body: the signed canonical must hash the EMPTY body (not
    # json.dumps({})), or the request 403s on signature_mismatch instead of on
    # the ownership check this test is actually verifying.
    path = f"/api/v1/batches/{bu}/media-verdicts"
    empty_body_hash = _hashlib.sha256(b"").hexdigest()
    canonical = "\n".join(
        ["GET", path, "", empty_body_hash, "test-device-1"]
    ).encode("utf-8")
    resp = await client.get(
        path,
        headers={
            "X-Device-Id": "test-device-1",
            "X-Signature": sign_canonical(canonical),
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "not_your_batch"
