"""V8 Part 5 (A phase-2) — signed field-walk link + device submission.

Covers: link minting (admin-only, server-signed), the device endpoint's
layered verification (device signature via `verify_signature`, THEN the
link's own server signature/expiry/single-use nonce), overlap computation
against the parcel's declared boundary, and the portal ground-truthing read.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from models import Project, SourceParcel
from tests.remediation.crypto_utils import sign_request

import server_signing

pytestmark = pytest.mark.asyncio

DEVICE = "test-device-reg"


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _new_keypair():
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
def _signing_env(monkeypatch):
    seed_b64, pub_b64 = _new_keypair()
    monkeypatch.setenv("DMRV_SERVER_SIGNING_SK", seed_b64)
    monkeypatch.setenv("DMRV_SERVER_SIGNING_KID", "sk1")
    monkeypatch.setenv("DMRV_SERVER_SIGNING_PUBKEYS", json.dumps({"sk1": pub_b64}))
    yield


async def _login_admin(client, session_factory):
    from portal.auth import hash_password
    from models import PortalUser

    async with session_factory() as session:
        session.add(
            PortalUser(
                email="admin-fw@test.local",
                password_hash=hash_password("correct-horse-battery-staple"),
                role="admin",
                disabled=False,
            )
        )
        await session.commit()
    resp = await client.post(
        "/api/v1/portal/login",
        json={"email": "admin-fw@test.local", "password": "correct-horse-battery-staple"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['token']}"}


def _square_geojson(lon0, lat0, side):
    ring = [
        [lon0, lat0],
        [lon0 + side, lat0],
        [lon0 + side, lat0 + side],
        [lon0, lat0 + side],
        [lon0, lat0],
    ]
    return json.dumps({"type": "Polygon", "coordinates": [ring]})


async def _seed_parcel(session_factory, parcel_uuid, *, lon0=10.0, lat0=10.0, side=0.01):
    async with session_factory() as session:
        session.add(Project(project_id="proj-fw", name="FW Project"))
        session.add(
            SourceParcel(
                parcel_uuid=parcel_uuid,
                project_id="proj-fw",
                name="FW Parcel",
                boundary_geojson=_square_geojson(lon0, lat0, side),
                area_m2=1_000_000.0,
                bbox_min_lat=lat0,
                bbox_min_lon=lon0,
                bbox_max_lat=lat0 + side,
                bbox_max_lon=lon0 + side,
            )
        )
        await session.commit()


def _device_post(device_id, path, op, payload):
    return {
        "content": json.dumps(payload).encode("utf-8"),
        "headers": {
            "X-Idempotency-Key": op,
            "X-Device-Id": device_id,
            "X-Signature": sign_request(device_id, "", "POST", path, op, payload),
        },
    }


async def _mint_link(client, headers, parcel_uuid):
    resp = await client.post(
        f"/api/v1/portal/parcels/{parcel_uuid}/field-walk-link", headers=headers
    )
    assert resp.status_code == 200
    return resp.json()


def _walk_points(lon0=10.0, lat0=10.0, side=0.01):
    return [
        [lon0 + 0.0005, lat0 + 0.0005],
        [lon0 + side - 0.0005, lat0 + 0.0005],
        [lon0 + side - 0.0005, lat0 + side - 0.0005],
        [lon0 + 0.0005, lat0 + side - 0.0005],
    ]


async def test_mint_link_requires_admin(client, session_factory):
    parcel_uuid = str(uuid.uuid4())
    await _seed_parcel(session_factory, parcel_uuid)
    resp = await client.post(f"/api/v1/portal/parcels/{parcel_uuid}/field-walk-link")
    assert resp.status_code == 401


async def test_mint_link_404_for_unknown_parcel(client, session_factory):
    headers = await _login_admin(client, session_factory)
    resp = await client.post(
        f"/api/v1/portal/parcels/{uuid.uuid4()}/field-walk-link", headers=headers
    )
    assert resp.status_code == 404


async def test_submit_field_walk_end_to_end_computes_high_overlap(
    client, session_factory
):
    parcel_uuid = str(uuid.uuid4())
    await _seed_parcel(session_factory, parcel_uuid)
    headers = await _login_admin(client, session_factory)
    link = await _mint_link(client, headers, parcel_uuid)

    payload = {
        "link_payload": link["payload"],
        "link_kid": link["kid"],
        "link_signature": link["signature"],
        "points": _walk_points(),
    }
    resp = await client.post(
        "/api/v1/field-walk", **_device_post(DEVICE, "/api/v1/field-walk", "fw-op-1", payload)
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["parcel_uuid"] == parcel_uuid
    assert body["computed_area_m2"] > 0
    # The walk track is a slightly-inset version of the declared square, so
    # overlap should be high but not necessarily exactly 1.0.
    assert body["overlap_ratio_vs_declared"] > 0.8


async def test_submit_field_walk_rejects_tampered_link_signature(
    client, session_factory
):
    parcel_uuid = str(uuid.uuid4())
    await _seed_parcel(session_factory, parcel_uuid)
    headers = await _login_admin(client, session_factory)
    link = await _mint_link(client, headers, parcel_uuid)

    payload = {
        "link_payload": link["payload"],
        "link_kid": link["kid"],
        "link_signature": "tampered-" + link["signature"],
        "points": _walk_points(),
    }
    resp = await client.post(
        "/api/v1/field-walk", **_device_post(DEVICE, "/api/v1/field-walk", "fw-op-2", payload)
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "invalid_field_walk_link"


async def test_submit_field_walk_rejects_expired_link(client, session_factory):
    parcel_uuid = str(uuid.uuid4())
    await _seed_parcel(session_factory, parcel_uuid)

    expired_payload = json.dumps(
        {
            "parcel_uuid": parcel_uuid,
            "nonce": "nonce-expired",
            "issued_at": (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(),
            "expires_at": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(),
        }
    )
    kid, signature = server_signing.sign(expired_payload.encode("utf-8"))

    payload = {
        "link_payload": expired_payload,
        "link_kid": kid,
        "link_signature": signature,
        "points": _walk_points(),
    }
    resp = await client.post(
        "/api/v1/field-walk", **_device_post(DEVICE, "/api/v1/field-walk", "fw-op-3", payload)
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "field_walk_link_expired"


async def test_submit_field_walk_link_is_single_use(client, session_factory):
    parcel_uuid = str(uuid.uuid4())
    await _seed_parcel(session_factory, parcel_uuid)
    headers = await _login_admin(client, session_factory)
    link = await _mint_link(client, headers, parcel_uuid)

    payload = {
        "link_payload": link["payload"],
        "link_kid": link["kid"],
        "link_signature": link["signature"],
        "points": _walk_points(),
    }
    first = await client.post(
        "/api/v1/field-walk", **_device_post(DEVICE, "/api/v1/field-walk", "fw-op-4a", payload)
    )
    assert first.status_code == 201

    # Re-POSTing the SAME link (even under a different idempotency key) must
    # be rejected — a captured link can't be replayed for a second track.
    second = await client.post(
        "/api/v1/field-walk", **_device_post(DEVICE, "/api/v1/field-walk", "fw-op-4b", payload)
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "field_walk_link_already_used"


async def test_submit_field_walk_rejects_link_for_a_different_parcel_shape(
    client, session_factory
):
    """A well-formed, validly-signed link whose payload names a parcel that
    doesn't exist must 404, not silently accept the walk against nothing."""
    headers = await _login_admin(client, session_factory)
    real_parcel = str(uuid.uuid4())
    await _seed_parcel(session_factory, real_parcel)
    real_link = await _mint_link(client, headers, real_parcel)

    tampered_link_payload = json.dumps(
        {**json.loads(real_link["payload"]), "parcel_uuid": str(uuid.uuid4())}
    )
    # Re-sign under the tampered payload so signature verification itself
    # passes — this isolates the "parcel not found" path specifically.
    kid, signature = server_signing.sign(tampered_link_payload.encode("utf-8"))

    payload = {
        "link_payload": tampered_link_payload,
        "link_kid": kid,
        "link_signature": signature,
        "points": _walk_points(),
    }
    resp = await client.post(
        "/api/v1/field-walk", **_device_post(DEVICE, "/api/v1/field-walk", "fw-op-5", payload)
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "parcel_not_found"


async def test_submit_field_walk_rejects_too_few_points(client, session_factory):
    parcel_uuid = str(uuid.uuid4())
    await _seed_parcel(session_factory, parcel_uuid)
    headers = await _login_admin(client, session_factory)
    link = await _mint_link(client, headers, parcel_uuid)

    payload = {
        "link_payload": link["payload"],
        "link_kid": link["kid"],
        "link_signature": link["signature"],
        "points": [[10.0005, 10.0005], [10.0095, 10.0005]],
    }
    resp = await client.post(
        "/api/v1/field-walk", **_device_post(DEVICE, "/api/v1/field-walk", "fw-op-6", payload)
    )
    assert resp.status_code == 422  # Pydantic min_length=3 on `points`


async def test_portal_list_field_walks_shows_submitted_track(client, session_factory):
    parcel_uuid = str(uuid.uuid4())
    await _seed_parcel(session_factory, parcel_uuid)
    headers = await _login_admin(client, session_factory)
    link = await _mint_link(client, headers, parcel_uuid)

    payload = {
        "link_payload": link["payload"],
        "link_kid": link["kid"],
        "link_signature": link["signature"],
        "points": _walk_points(),
    }
    await client.post(
        "/api/v1/field-walk", **_device_post(DEVICE, "/api/v1/field-walk", "fw-op-7", payload)
    )

    resp = await client.get(
        f"/api/v1/portal/parcels/{parcel_uuid}/field-walks", headers=headers
    )
    assert resp.status_code == 200
    walks = resp.json()["field_walks"]
    assert len(walks) == 1
    assert walks[0]["parcel_uuid"] == parcel_uuid
    assert walks[0]["device_id"] == DEVICE
    assert walks[0]["overlap_ratio_vs_declared"] > 0.8
