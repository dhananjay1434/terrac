"""T2.3 — v2 signed-timestamp canonical for replay protection.

v2 appends a client unix timestamp to the canonical and the server rejects
requests outside the skew window. v1 (no X-Canonical-Version header) is still
accepted unless DMRV_REQUIRE_CANONICAL_V2=1. Tests sign with the shared fixed
test key via crypto_utils.sign_canonical.
"""

import hashlib
import json
import time
import uuid

import pytest
from sqlalchemy.future import select

from models import DeviceKey
from tests.remediation.crypto_utils import TEST_PUBLIC_KEY_B64, sign_canonical

pytestmark = pytest.mark.asyncio

DEVICE = "replay-dev"


async def _enroll(session_factory):
    async with session_factory() as s:
        exists = (
            await s.execute(select(DeviceKey).where(DeviceKey.device_id == DEVICE))
        ).scalar_one_or_none()
        if not exists:
            s.add(DeviceKey(device_id=DEVICE, public_key=TEST_PUBLIC_KEY_B64))
            await s.commit()


def _body(bu):
    return json.dumps({"telemetry_uuid": str(uuid.uuid4()), "batch_uuid": bu}).encode(
        "utf-8"
    )


def _v2_headers(path, op, body, signed_at):
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = "\n".join(
        ["POST", path, op, body_hash, DEVICE, str(signed_at)]
    ).encode("utf-8")
    return {
        "X-Device-Id": DEVICE,
        "X-Idempotency-Key": op,
        "X-Signature": sign_canonical(canonical),
        "X-Canonical-Version": "2",
        "X-Signed-At": str(signed_at),
    }


async def _post(client, path, op, body, headers):
    # Bypass the SignedAsyncClient auto-signer by supplying X-Signature ourselves.
    return await client.post(path, content=body, headers=headers)


async def test_v2_fresh_timestamp_accepted(client, session_factory):
    await _enroll(session_factory)
    bu = str(uuid.uuid4())
    body = _body(bu)
    op = "op-fresh-" + bu[:6]
    r = await _post(
        client, "/api/v1/telemetry", op, body, _v2_headers("/api/v1/telemetry", op, body, int(time.time()))
    )
    assert r.status_code == 201, r.text


async def test_v2_stale_timestamp_rejected(client, session_factory):
    await _enroll(session_factory)
    bu = str(uuid.uuid4())
    body = _body(bu)
    op = "op-stale-" + bu[:6]
    stale = int(time.time()) - 3600  # an hour old, well outside the 300s window
    r = await _post(
        client, "/api/v1/telemetry", op, body, _v2_headers("/api/v1/telemetry", op, body, stale)
    )
    assert r.status_code == 401, r.text
    assert r.json()["detail"] == "stale_signature"


async def test_v2_missing_signed_at_rejected(client, session_factory):
    await _enroll(session_factory)
    bu = str(uuid.uuid4())
    body = _body(bu)
    op = "op-nosat-" + bu[:6]
    headers = _v2_headers("/api/v1/telemetry", op, body, int(time.time()))
    del headers["X-Signed-At"]
    r = await _post(client, "/api/v1/telemetry", op, body, headers)
    assert r.status_code == 401, r.text
    assert r.json()["detail"] == "missing_signed_at"


async def test_v1_still_accepted_by_default(client, session_factory):
    # No X-Canonical-Version header -> legacy v1 path, still valid.
    await _enroll(session_factory)
    bu = str(uuid.uuid4())
    body = _body(bu)
    op = "op-v1-" + bu[:6]
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = "\n".join(
        ["POST", "/api/v1/telemetry", op, body_hash, DEVICE]
    ).encode("utf-8")
    headers = {
        "X-Device-Id": DEVICE,
        "X-Idempotency-Key": op,
        "X-Signature": sign_canonical(canonical),
    }
    r = await _post(client, "/api/v1/telemetry", op, body, headers)
    assert r.status_code == 201, r.text


async def test_v1_refused_when_v2_required(client, session_factory, monkeypatch):
    monkeypatch.setenv("DMRV_REQUIRE_CANONICAL_V2", "1")
    await _enroll(session_factory)
    bu = str(uuid.uuid4())
    body = _body(bu)
    op = "op-v1req-" + bu[:6]
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = "\n".join(
        ["POST", "/api/v1/telemetry", op, body_hash, DEVICE]
    ).encode("utf-8")
    headers = {
        "X-Device-Id": DEVICE,
        "X-Idempotency-Key": op,
        "X-Signature": sign_canonical(canonical),
    }
    r = await _post(client, "/api/v1/telemetry", op, body, headers)
    assert r.status_code == 401, r.text
    assert r.json()["detail"] == "canonical_v2_required"
