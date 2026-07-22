"""V8 Part 0.1 — server Ed25519 signing + kid rotation.

Opposite direction from device auth (security.py): the SERVER signs, a
future app-side verifier checks. Tests cover: round-trip, tamper rejection,
unknown-kid handling, rotation (old kid still verifies after a new kid
becomes the signer), and the dormant-by-default posture (no env => no crash).
"""

from __future__ import annotations

import base64
import json
import os

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import server_signing


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _new_keypair() -> tuple[str, str]:
    """Returns (seed_b64url, pubkey_b64url) for a fresh Ed25519 keypair."""
    priv = Ed25519PrivateKey.generate()
    seed = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return _b64u(seed), _b64u(pub)


@pytest.fixture(autouse=True)
def _clean_signing_env(monkeypatch):
    """Every test starts with signing env fully unset; each test opts in."""
    for name in (
        "DMRV_SERVER_SIGNING_SK",
        "DMRV_SERVER_SIGNING_KID",
        "DMRV_SERVER_SIGNING_PUBKEYS",
    ):
        monkeypatch.delenv(name, raising=False)
    yield


def test_dormant_by_default_no_crash():
    """No env configured => RuntimeError on use, not an import-time crash."""
    with pytest.raises(RuntimeError):
        server_signing.sign(b"payload")
    with pytest.raises(RuntimeError):
        server_signing.public_keys()
    # verify() must degrade to 'unverifiable', never raise, even with no config.
    assert server_signing.verify(b"payload", "sig", "sk1") == "unverifiable"


def test_sign_verify_round_trip(monkeypatch):
    seed_b64, pub_b64 = _new_keypair()
    monkeypatch.setenv("DMRV_SERVER_SIGNING_SK", seed_b64)
    monkeypatch.setenv("DMRV_SERVER_SIGNING_KID", "sk1")
    monkeypatch.setenv("DMRV_SERVER_SIGNING_PUBKEYS", json.dumps({"sk1": pub_b64}))

    server_signing.validate_consistency()  # must not raise on a correct config

    payload = b"config-document-v1"
    kid, sig = server_signing.sign(payload)
    assert kid == "sk1"
    assert server_signing.verify(payload, sig, kid) == "valid"


def test_tampered_payload_rejected(monkeypatch):
    seed_b64, pub_b64 = _new_keypair()
    monkeypatch.setenv("DMRV_SERVER_SIGNING_SK", seed_b64)
    monkeypatch.setenv("DMRV_SERVER_SIGNING_KID", "sk1")
    monkeypatch.setenv("DMRV_SERVER_SIGNING_PUBKEYS", json.dumps({"sk1": pub_b64}))

    kid, sig = server_signing.sign(b"original")
    assert server_signing.verify(b"tampered", sig, kid) == "invalid"


def test_wrong_key_fails(monkeypatch):
    """A signature made under one keypair must not verify under another's pubkey."""
    seed_a, _pub_a = _new_keypair()
    _seed_b, pub_b = _new_keypair()
    monkeypatch.setenv("DMRV_SERVER_SIGNING_SK", seed_a)
    monkeypatch.setenv("DMRV_SERVER_SIGNING_KID", "sk1")
    # Verify set declares sk1 as pub_b (WRONG on purpose) to prove mismatch is caught.
    monkeypatch.setenv("DMRV_SERVER_SIGNING_PUBKEYS", json.dumps({"sk1": pub_b}))

    with pytest.raises(RuntimeError):
        server_signing.validate_consistency()

    kid, sig = server_signing.sign(b"payload")
    assert server_signing.verify(b"payload", sig, kid) == "invalid"


def test_unknown_kid_is_unverifiable(monkeypatch):
    seed_b64, pub_b64 = _new_keypair()
    monkeypatch.setenv("DMRV_SERVER_SIGNING_SK", seed_b64)
    monkeypatch.setenv("DMRV_SERVER_SIGNING_KID", "sk1")
    monkeypatch.setenv("DMRV_SERVER_SIGNING_PUBKEYS", json.dumps({"sk1": pub_b64}))

    kid, sig = server_signing.sign(b"payload")
    assert server_signing.verify(b"payload", sig, "sk-nonexistent") == "unverifiable"


def test_rotation_old_kid_still_verifies_new_kid_signs(monkeypatch):
    """Rotation: sk1 (old) stays in the verify set; sk2 (new) becomes the signer.
    A signature made under sk1 before rotation must still verify after."""
    seed_1, pub_1 = _new_keypair()
    seed_2, pub_2 = _new_keypair()

    # Before rotation: sk1 signs.
    monkeypatch.setenv("DMRV_SERVER_SIGNING_SK", seed_1)
    monkeypatch.setenv("DMRV_SERVER_SIGNING_KID", "sk1")
    monkeypatch.setenv("DMRV_SERVER_SIGNING_PUBKEYS", json.dumps({"sk1": pub_1}))
    kid_old, sig_old = server_signing.sign(b"pre-rotation-payload")
    assert kid_old == "sk1"

    # Rotation step 1 (runbook): add sk2's pubkey to the verify set BEFORE it signs.
    monkeypatch.setenv(
        "DMRV_SERVER_SIGNING_PUBKEYS", json.dumps({"sk1": pub_1, "sk2": pub_2})
    )
    assert server_signing.verify(b"pre-rotation-payload", sig_old, "sk1") == "valid"

    # Rotation step 2: sk2 becomes the signer.
    monkeypatch.setenv("DMRV_SERVER_SIGNING_SK", seed_2)
    monkeypatch.setenv("DMRV_SERVER_SIGNING_KID", "sk2")
    server_signing.validate_consistency()

    kid_new, sig_new = server_signing.sign(b"post-rotation-payload")
    assert kid_new == "sk2"
    assert server_signing.verify(b"post-rotation-payload", sig_new, "sk2") == "valid"
    # The old key's signature (issued before rotation) STILL verifies — this is
    # the whole point of keeping sk1 in the verify set.
    assert server_signing.verify(b"pre-rotation-payload", sig_old, "sk1") == "valid"


def test_malformed_env_reports_config_error_not_crash(monkeypatch):
    monkeypatch.setenv("DMRV_SERVER_SIGNING_SK", "not-valid-base64!!!")
    monkeypatch.setenv("DMRV_SERVER_SIGNING_KID", "sk1")
    monkeypatch.setenv("DMRV_SERVER_SIGNING_PUBKEYS", json.dumps({"sk1": "x"}))
    with pytest.raises(RuntimeError):
        server_signing.sign(b"payload")


@pytest.mark.asyncio
async def test_pubkeys_endpoint_reports_dormant_when_unconfigured(client):
    resp = await client.get("/api/v1/pubkeys")
    assert resp.status_code == 200
    body = resp.json()
    assert body["signing_configured"] is False
    assert body["keys"] == {}


@pytest.mark.asyncio
async def test_pubkeys_endpoint_reports_configured(client, monkeypatch):
    seed_b64, pub_b64 = _new_keypair()
    monkeypatch.setenv("DMRV_SERVER_SIGNING_SK", seed_b64)
    monkeypatch.setenv("DMRV_SERVER_SIGNING_KID", "sk1")
    monkeypatch.setenv("DMRV_SERVER_SIGNING_PUBKEYS", json.dumps({"sk1": pub_b64}))

    resp = await client.get("/api/v1/pubkeys")
    assert resp.status_code == 200
    body = resp.json()
    assert body["signing_configured"] is True
    assert body["current_kid"] == "sk1"
    assert body["keys"] == {"sk1": pub_b64}
