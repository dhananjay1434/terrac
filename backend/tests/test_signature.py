"""Phase 5 — the server verifies Ed25519 request signatures.

A device enrolls a PUBLIC key; only the holder of the matching PRIVATE key can
produce a signature that verifies. The server stores no secret capable of
forging a signature.
"""

import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from models import DeviceKey


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def _pub_b64(priv: Ed25519PrivateKey) -> str:
    return _b64u(
        priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )


def _sign(priv, method, path, op_id, device_id, body: bytes) -> str:
    canonical = "\n".join(
        [method, path, op_id, hashlib.sha256(body).hexdigest(), device_id]
    ).encode("utf-8")
    return _b64u(priv.sign(canonical))


async def _enroll(session_factory, device_id, pub_b64):
    async with session_factory() as s:
        s.add(DeviceKey(device_id=device_id, public_key=pub_b64))
        await s.commit()


@pytest.mark.asyncio
async def test_valid_ed25519_signature_accepted(client, session_factory):
    priv = Ed25519PrivateKey.generate()
    dev = "sig-dev-ok"
    await _enroll(session_factory, dev, _pub_b64(priv))

    body = json.dumps({"batch_uuid": "b-sig-1", "telemetry_uuid": "t-1"}).encode(
        "utf-8"
    )
    op = "op-sig-1"
    sig = _sign(priv, "POST", "/api/v1/telemetry", op, dev, body)

    r = await client.post(
        "/api/v1/telemetry",
        content=body,
        headers={"X-Device-Id": dev, "X-Idempotency-Key": op, "X-Signature": sig},
    )
    assert r.status_code == 201


@pytest.mark.asyncio
async def test_signature_from_different_key_rejected(client, session_factory):
    enrolled = Ed25519PrivateKey.generate()
    attacker = Ed25519PrivateKey.generate()
    dev = "sig-dev-bad"
    await _enroll(session_factory, dev, _pub_b64(enrolled))

    body = json.dumps({"batch_uuid": "b-sig-2", "telemetry_uuid": "t-2"}).encode(
        "utf-8"
    )
    op = "op-sig-2"
    # Signed with a key that is NOT the enrolled one.
    sig = _sign(attacker, "POST", "/api/v1/telemetry", op, dev, body)

    r = await client.post(
        "/api/v1/telemetry",
        content=body,
        headers={"X-Device-Id": dev, "X-Idempotency-Key": op, "X-Signature": sig},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "signature_mismatch"


@pytest.mark.asyncio
async def test_public_key_alone_cannot_forge(client, session_factory):
    # The server holds only the public key. Anyone lacking the private half
    # (here, a freshly generated key) cannot forge a verifying signature.
    enrolled = Ed25519PrivateKey.generate()
    dev = "sig-dev-forge"
    await _enroll(session_factory, dev, _pub_b64(enrolled))

    body = json.dumps({"batch_uuid": "b-sig-3", "telemetry_uuid": "t-3"}).encode(
        "utf-8"
    )
    op = "op-sig-3"
    forged = _sign(
        Ed25519PrivateKey.generate(), "POST", "/api/v1/telemetry", op, dev, body
    )

    r = await client.post(
        "/api/v1/telemetry",
        content=body,
        headers={"X-Device-Id": dev, "X-Idempotency-Key": op, "X-Signature": forged},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_missing_signature_rejected(client, session_factory):
    priv = Ed25519PrivateKey.generate()
    dev = "sig-dev-missing"
    await _enroll(session_factory, dev, _pub_b64(priv))

    body = json.dumps({"batch_uuid": "b-sig-4", "telemetry_uuid": "t-4"}).encode(
        "utf-8"
    )
    # No X-Signature header at all.
    r = await client.post(
        "/api/v1/telemetry",
        content=body,
        headers={"X-Device-Id": dev, "X-Idempotency-Key": "op-sig-4"},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_signature"
