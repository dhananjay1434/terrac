"""V8 Part 3.3 — dispatch endpoint tests (create/transition, ownership,
weight-lock, dual-weigh reconciliation) + portal facility admin + dispatch list.

Ownership pattern mirrors test_batch_ownership.py: OWNER/OTHER are both
pre-enrolled by conftest's autouse fixture with the same test Ed25519 key.
"""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import select

from models import Dispatch
from tests.remediation.crypto_utils import sign_request

pytestmark = pytest.mark.asyncio

OWNER = "test-device-reg"
OTHER = "test-device-1"


def _signed_headers(device_id: str, path: str, op: str, payload: dict) -> dict:
    return {
        "X-Idempotency-Key": op,
        "X-Device-Id": device_id,
        "X-Signature": sign_request(device_id, "", "POST", path, op, payload),
    }


async def _post(client, device_id, path, op, payload):
    return await client.post(
        path,
        content=json.dumps(payload).encode("utf-8"),
        headers=_signed_headers(device_id, path, op, payload),
    )


def _create_payload(dispatch_uuid, **over):
    p = {
        "dispatch_uuid": dispatch_uuid,
        "kind": "biomass",
        "weight_source_kg": 100.0,
        "weight_source_method": "platform_scale",
    }
    p.update(over)
    return p


async def _login_admin(client, session_factory):
    from portal.auth import hash_password
    from models import PortalUser

    async with session_factory() as session:
        session.add(
            PortalUser(
                email="admin-dispatch@test.local",
                password_hash=hash_password("correct-horse-battery-staple"),
                role="admin",
                disabled=False,
            )
        )
        await session.commit()
    resp = await client.post(
        "/api/v1/portal/login",
        json={
            "email": "admin-dispatch@test.local",
            "password": "correct-horse-battery-staple",
        },
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['token']}"}


# ---------------------------------------------------------------------------
# Device-facing facility list (destination picker)
# ---------------------------------------------------------------------------


async def test_device_facility_list_returns_active_only(client, session_factory):
    from models import Facility

    async with session_factory() as session:
        session.add(
            Facility(
                facility_uuid=str(uuid.uuid4()),
                name="Active Facility",
                facility_type="industrial",
                status="active",
            )
        )
        session.add(
            Facility(
                facility_uuid=str(uuid.uuid4()),
                name="Inactive Facility",
                facility_type="industrial",
                status="inactive",
            )
        )
        await session.commit()

    resp = await client.get("/api/v1/facilities")
    assert resp.status_code == 200
    names = [f["name"] for f in resp.json()["facilities"]]
    assert "Active Facility" in names
    assert "Inactive Facility" not in names


# ---------------------------------------------------------------------------
# Create + idempotency + weight-lock (re-post after leaving draft)
# ---------------------------------------------------------------------------


async def test_create_dispatch(client):
    du = str(uuid.uuid4())
    resp = await _post(client, OWNER, "/api/v1/dispatch", "d-1", _create_payload(du))
    assert resp.status_code == 201, resp.text
    assert resp.json()["dispatch_status"] == "draft"


async def test_idempotent_repost_while_draft_updates(client):
    du = str(uuid.uuid4())
    r1 = await _post(
        client, OWNER, "/api/v1/dispatch", "d-2a", _create_payload(du, weight_source_kg=100.0)
    )
    assert r1.status_code == 201
    r2 = await _post(
        client, OWNER, "/api/v1/dispatch", "d-2b", _create_payload(du, weight_source_kg=150.0)
    )
    assert r2.status_code == 200  # update, not a new row


async def test_foreign_device_cannot_create_over_existing(client):
    du = str(uuid.uuid4())
    r1 = await _post(client, OWNER, "/api/v1/dispatch", "d-3a", _create_payload(du))
    assert r1.status_code == 201
    r2 = await _post(client, OTHER, "/api/v1/dispatch", "d-3b", _create_payload(du))
    assert r2.status_code == 403


async def test_repost_after_leaving_draft_is_locked(client):
    du = str(uuid.uuid4())
    await _post(client, OWNER, "/api/v1/dispatch", "d-4a", _create_payload(du))
    t1 = await _post(
        client,
        OWNER,
        f"/api/v1/dispatch/{du}/transition",
        "d-4t",
        {"target_status": "in_transit"},
    )
    assert t1.status_code == 200, t1.text

    # Weight-lock: re-posting the create payload (which would edit
    # weight_source_kg) must be rejected now that the dispatch has left draft.
    r2 = await _post(
        client, OWNER, "/api/v1/dispatch", "d-4b", _create_payload(du, weight_source_kg=999.0)
    )
    assert r2.status_code == 409
    assert r2.json()["detail"] == "dispatch_locked"


# ---------------------------------------------------------------------------
# Transitions: legal path, illegal skip, ownership, missing weight
# ---------------------------------------------------------------------------


async def test_full_lifecycle_draft_to_received(client, session_factory):
    du = str(uuid.uuid4())
    await _post(client, OWNER, "/api/v1/dispatch", "d-5a", _create_payload(du, weight_source_kg=100.0))

    t1 = await _post(
        client, OWNER, f"/api/v1/dispatch/{du}/transition", "d-5b",
        {"target_status": "in_transit"},
    )
    assert t1.status_code == 200
    assert t1.json()["dispatch_status"] == "in_transit"

    t2 = await _post(
        client, OWNER, f"/api/v1/dispatch/{du}/transition", "d-5c",
        {"target_status": "received", "weight_facility_kg": 98.0},
    )
    assert t2.status_code == 200
    body = t2.json()
    assert body["dispatch_status"] == "received"
    assert body["weight_flagged"] is False  # 2% delta, within default 5% tolerance

    async with session_factory() as session:
        d = (
            await session.execute(
                select(Dispatch).where(Dispatch.dispatch_uuid == du)
            )
        ).scalar_one()
        assert d.weight_facility_kg == 98.0
        assert d.received_at is not None


async def test_skip_transition_rejected(client):
    du = str(uuid.uuid4())
    await _post(client, OWNER, "/api/v1/dispatch", "d-6a", _create_payload(du))
    r = await _post(
        client, OWNER, f"/api/v1/dispatch/{du}/transition", "d-6b",
        {"target_status": "received", "weight_facility_kg": 50.0},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "illegal_transition"


async def test_foreign_device_cannot_transition(client):
    du = str(uuid.uuid4())
    await _post(client, OWNER, "/api/v1/dispatch", "d-7a", _create_payload(du))
    r = await _post(
        client, OTHER, f"/api/v1/dispatch/{du}/transition", "d-7b",
        {"target_status": "in_transit"},
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Deferred R2 — GET /api/v1/dispatch/{uuid} (device status read, for wizard resume)
# ---------------------------------------------------------------------------


def _get_signed_headers(device_id: str, path: str, op: str) -> dict:
    """A real GET sends no body at all, so the canonical's body-hash slot must
    be sha256(b"") — NOT sha256(json.dumps({})) — matching how
    `security.py::verify_signature` hashes `await request.body()`."""
    import hashlib

    from tests.remediation.crypto_utils import sign_canonical

    body_hash = hashlib.sha256(b"").hexdigest()
    canonical = "\n".join(["GET", path, op, body_hash, device_id]).encode("utf-8")
    return {
        "X-Idempotency-Key": op,
        "X-Device-Id": device_id,
        "X-Signature": sign_canonical(canonical),
    }


async def test_get_dispatch_status_owner_sees_current_status(client):
    du = str(uuid.uuid4())
    await _post(client, OWNER, "/api/v1/dispatch", "d-8a", _create_payload(du))
    path = f"/api/v1/dispatch/{du}"
    r = await client.get(path, headers=_get_signed_headers(OWNER, path, "d-8b"))
    assert r.status_code == 200
    body = r.json()
    assert body["dispatch_uuid"] == du
    assert body["status"] == "draft"

    await _post(
        client, OWNER, f"/api/v1/dispatch/{du}/transition", "d-8c",
        {"target_status": "in_transit"},
    )
    r2 = await client.get(path, headers=_get_signed_headers(OWNER, path, "d-8d"))
    assert r2.json()["status"] == "in_transit"


async def test_get_dispatch_status_unknown_uuid_404(client):
    path = f"/api/v1/dispatch/{uuid.uuid4()}"
    r = await client.get(path, headers=_get_signed_headers(OWNER, path, "d-9a"))
    assert r.status_code == 404
    assert r.json()["detail"] == "dispatch_not_found"


async def test_get_dispatch_status_foreign_device_403(client):
    du = str(uuid.uuid4())
    await _post(client, OWNER, "/api/v1/dispatch", "d-10a", _create_payload(du))
    path = f"/api/v1/dispatch/{du}"
    r = await client.get(path, headers=_get_signed_headers(OTHER, path, "d-10b"))
    assert r.status_code == 403


async def test_transition_without_weight_source_rejected(client):
    du = str(uuid.uuid4())
    payload = _create_payload(du)
    del payload["weight_source_kg"]
    await _post(client, OWNER, "/api/v1/dispatch", "d-8a", payload)
    r = await _post(
        client, OWNER, f"/api/v1/dispatch/{du}/transition", "d-8b",
        {"target_status": "in_transit"},
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "missing_weight_source"


async def test_receive_without_facility_weight_rejected(client):
    du = str(uuid.uuid4())
    await _post(client, OWNER, "/api/v1/dispatch", "d-9a", _create_payload(du))
    await _post(
        client, OWNER, f"/api/v1/dispatch/{du}/transition", "d-9b",
        {"target_status": "in_transit"},
    )
    r = await _post(
        client, OWNER, f"/api/v1/dispatch/{du}/transition", "d-9c",
        {"target_status": "received"},
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "missing_weight_facility"


async def test_dual_weigh_beyond_tolerance_flagged_and_recorded(client, monkeypatch):
    """Weight discrepancy beyond tolerance FLAGS (doesn't block) and emits a
    gate-rejection metric for verifier review."""
    import observability

    calls = []
    monkeypatch.setattr(
        observability, "record_gate_rejection", lambda **kw: calls.append(kw)
    )

    du = str(uuid.uuid4())
    await _post(client, OWNER, "/api/v1/dispatch", "d-10a", _create_payload(du, weight_source_kg=100.0))
    await _post(
        client, OWNER, f"/api/v1/dispatch/{du}/transition", "d-10b",
        {"target_status": "in_transit"},
    )
    r = await _post(
        client, OWNER, f"/api/v1/dispatch/{du}/transition", "d-10c",
        {"target_status": "received", "weight_facility_kg": 70.0},  # 30% delta
    )
    assert r.status_code == 200
    body = r.json()
    assert body["weight_flagged"] is True
    assert body["weight_delta_pct"] == pytest.approx(30.0)
    assert len(calls) == 1
    assert calls[0]["gate"] == "dispatch_reconciliation"


# ---------------------------------------------------------------------------
# Portal: facility admin + dispatch list
# ---------------------------------------------------------------------------


async def test_create_facility_requires_admin(client):
    resp = await client.post(
        "/api/v1/portal/facilities",
        json={
            "facility_uuid": str(uuid.uuid4()),
            "name": "North Facility",
            "facility_type": "industrial",
        },
    )
    assert resp.status_code == 401


async def test_create_and_list_facility(client, session_factory):
    headers = await _login_admin(client, session_factory)
    fu = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/portal/facilities",
        json={"facility_uuid": fu, "name": "North Facility", "facility_type": "industrial"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    list_resp = await client.get("/api/v1/portal/facilities", headers=headers)
    assert list_resp.status_code == 200
    ids = [f["facility_uuid"] for f in list_resp.json()["facilities"]]
    assert fu in ids


async def test_duplicate_facility_rejected(client, session_factory):
    headers = await _login_admin(client, session_factory)
    fu = str(uuid.uuid4())
    body = {"facility_uuid": fu, "name": "Dup", "facility_type": "artisanal"}
    r1 = await client.post("/api/v1/portal/facilities", json=body, headers=headers)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/portal/facilities", json=body, headers=headers)
    assert r2.status_code == 409


async def test_invalid_facility_type_rejected(client, session_factory):
    headers = await _login_admin(client, session_factory)
    resp = await client.post(
        "/api/v1/portal/facilities",
        json={"facility_uuid": str(uuid.uuid4()), "name": "X", "facility_type": "bogus"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_dispatch_list_requires_auth(client):
    resp = await client.get("/api/v1/portal/dispatch")
    assert resp.status_code == 401


async def test_dispatch_list_filters_by_status(client, session_factory):
    headers = await _login_admin(client, session_factory)
    du = str(uuid.uuid4())
    await _post(client, OWNER, "/api/v1/dispatch", "d-11a", _create_payload(du))

    resp = await client.get("/api/v1/portal/dispatch?status=draft", headers=headers)
    assert resp.status_code == 200
    ids = [d["dispatch_uuid"] for d in resp.json()["dispatches"]]
    assert du in ids

    resp2 = await client.get("/api/v1/portal/dispatch?status=received", headers=headers)
    ids2 = [d["dispatch_uuid"] for d in resp2.json()["dispatches"]]
    assert du not in ids2
