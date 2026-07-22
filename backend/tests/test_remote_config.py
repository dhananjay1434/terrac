"""V8 Part 0.4 — remote control plane: signed feature flags, kill-switch,
min-version.

Covers: the public config document is signed once a server signing key is
configured (Part 0.1); admin writes persist and are role-gated; schema
stability (extra='forbid'); and the dormant-by-default posture (no signing
key configured => signing_configured: false, not a crash).
"""

from __future__ import annotations

import base64
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

import observability
import server_signing
from routers.config import _canonical_payload

pytestmark = pytest.mark.asyncio


def test_canonical_payload_is_ascii_free_and_recursively_sorted():
    """Pins the cross-language signing contract (the app's Dart verifier must
    reproduce these exact bytes). Locks two things that silently break
    verification if regressed: ensure_ascii=False (raw UTF-8, not \\uXXXX) and
    RECURSIVE key sorting (the nested `flags` map is sorted too). A non-ASCII
    kill-switch message + two out-of-order flags exercise both."""
    doc = {
        "flags": {"b_flag": True, "a_flag": False},  # deliberately b before a
        "kill_switch": True,
        "message": "चेतावनी",  # Hindi — would be \\uXXXX-escaped if ensure_ascii=True
        "min_version": "1.2.0",
        "signed_at": "2026-07-22T00:00:00+00:00",
    }
    expected = (
        '{"flags":{"a_flag":false,"b_flag":true},"kill_switch":true,'
        '"message":"चेतावनी","min_version":"1.2.0",'
        '"signed_at":"2026-07-22T00:00:00+00:00"}'
    ).encode("utf-8")
    assert _canonical_payload(doc) == expected


async def test_config_get_emits_no_gate_rejection_metrics(
    client, session_factory, monkeypatch
):
    """Regression: GET /api/v1/config is a READ endpoint that rejects nothing.
    It must NOT emit gate-rejection metrics — doing so polluted the counter on
    every device boot-poll (min_version is set in steady state) and would bury
    real fraud signals during a kill-switch emergency."""
    calls: list = []
    monkeypatch.setattr(
        observability,
        "record_gate_rejection",
        lambda **kw: calls.append(kw),
    )

    headers = await _login_admin(client, session_factory)
    # Configure BOTH a kill-switch and a min_version — the exact state the old
    # buggy code fired two rejections for on every request.
    await client.post(
        "/api/v1/portal/config",
        json={"kill_switch": True, "min_version": "9.9.9"},
        headers=headers,
    )

    for _ in range(3):
        resp = await client.get("/api/v1/config")
        assert resp.status_code == 200

    assert calls == [], f"GET /config must not record gate rejections, got {calls}"


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64u_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _new_keypair() -> tuple[str, str]:
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
    for name in (
        "DMRV_SERVER_SIGNING_SK",
        "DMRV_SERVER_SIGNING_KID",
        "DMRV_SERVER_SIGNING_PUBKEYS",
    ):
        monkeypatch.delenv(name, raising=False)
    yield


async def _login_admin(client, session_factory):
    from portal.auth import hash_password
    from models import PortalUser

    async with session_factory() as session:
        session.add(
            PortalUser(
                email="admin-config@test.local",
                password_hash=hash_password("correct-horse-battery-staple"),
                role="admin",
                disabled=False,
            )
        )
        await session.commit()

    resp = await client.post(
        "/api/v1/portal/login",
        json={
            "email": "admin-config@test.local",
            "password": "correct-horse-battery-staple",
        },
    )
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


async def test_config_dormant_by_default(client):
    """No row, no signing key: safe inert defaults, not a 500."""
    resp = await client.get("/api/v1/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["signing_configured"] is False
    assert body["kill_switch"] is False
    assert body["min_version"] is None
    assert body["flags"] == {}


async def test_config_write_requires_admin_role(client):
    resp = await client.post(
        "/api/v1/portal/config", json={"kill_switch": True}
    )
    assert resp.status_code == 401


async def test_admin_write_persists_and_is_readable(client, session_factory):
    headers = await _login_admin(client, session_factory)

    write_resp = await client.post(
        "/api/v1/portal/config",
        json={
            "flags": {"boundary_v2": True},
            "min_version": "1.4.0",
            "kill_switch": False,
            "message": "Routine update.",
        },
        headers=headers,
    )
    assert write_resp.status_code == 200
    assert write_resp.json()["flags"] == {"boundary_v2": True}

    read_resp = await client.get("/api/v1/config")
    body = read_resp.json()
    assert body["flags"] == {"boundary_v2": True}
    assert body["min_version"] == "1.4.0"
    assert body["kill_switch"] is False
    assert body["message"] == "Routine update."


async def test_partial_update_only_touches_given_fields(client, session_factory):
    headers = await _login_admin(client, session_factory)

    await client.post(
        "/api/v1/portal/config",
        json={"flags": {"a": 1}, "min_version": "1.0.0"},
        headers=headers,
    )
    # Only flip the kill switch — min_version and flags must survive untouched.
    resp = await client.post(
        "/api/v1/portal/config",
        json={"kill_switch": True},
        headers=headers,
    )
    body = resp.json()
    assert body["kill_switch"] is True
    assert body["min_version"] == "1.0.0"
    assert body["flags"] == {"a": 1}


async def test_extra_field_rejected(client, session_factory):
    headers = await _login_admin(client, session_factory)
    resp = await client.post(
        "/api/v1/portal/config",
        json={"kill_switch": True, "not_a_real_field": 1},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_config_is_signed_once_key_configured(client, session_factory, monkeypatch):
    seed_b64, pub_b64 = _new_keypair()
    monkeypatch.setenv("DMRV_SERVER_SIGNING_SK", seed_b64)
    monkeypatch.setenv("DMRV_SERVER_SIGNING_KID", "sk1")
    monkeypatch.setenv("DMRV_SERVER_SIGNING_PUBKEYS", json.dumps({"sk1": pub_b64}))

    headers = await _login_admin(client, session_factory)
    await client.post(
        "/api/v1/portal/config",
        json={"kill_switch": True, "min_version": "2.0.0"},
        headers=headers,
    )

    resp = await client.get("/api/v1/config")
    body = resp.json()
    assert body["signing_configured"] is True
    assert body["kid"] == "sk1"

    # The signature must verify against the EXACT canonical payload the app
    # will reconstruct client-side — this is the contract test for that byte
    # format (routers.config._canonical_payload).
    signed_fields = {
        "flags": body["flags"],
        "min_version": body["min_version"],
        "kill_switch": body["kill_switch"],
        "message": body["message"],
        "signed_at": body["signed_at"],
    }
    pub = Ed25519PublicKey.from_public_bytes(_b64u_decode(pub_b64))
    pub.verify(
        _b64u_decode(body["signature"]),
        _canonical_payload(signed_fields),
    )  # raises InvalidSignature if this ever drifts


async def test_tampered_config_document_fails_verification(client, session_factory, monkeypatch):
    """Regression guard for the app-side contract: if any byte of the signed
    fields changes, the signature must NOT verify — proving the app's
    reject-on-tamper path has something real to reject."""
    from cryptography.exceptions import InvalidSignature

    seed_b64, pub_b64 = _new_keypair()
    monkeypatch.setenv("DMRV_SERVER_SIGNING_SK", seed_b64)
    monkeypatch.setenv("DMRV_SERVER_SIGNING_KID", "sk1")
    monkeypatch.setenv("DMRV_SERVER_SIGNING_PUBKEYS", json.dumps({"sk1": pub_b64}))

    headers = await _login_admin(client, session_factory)
    await client.post(
        "/api/v1/portal/config", json={"kill_switch": False}, headers=headers
    )
    resp = await client.get("/api/v1/config")
    body = resp.json()

    tampered_fields = {
        "flags": body["flags"],
        "min_version": body["min_version"],
        "kill_switch": True,  # flipped after signing
        "message": body["message"],
        "signed_at": body["signed_at"],
    }
    pub = Ed25519PublicKey.from_public_bytes(_b64u_decode(pub_b64))
    with pytest.raises(InvalidSignature):
        pub.verify(
            _b64u_decode(body["signature"]),
            _canonical_payload(tampered_fields),
        )
