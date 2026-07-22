"""V8 Part 1.3 — source parcel boundary registration and list API tests.

Covers:
- Admin role enforcement on POST /api/v1/portal/parcels
- Successful parcel creation, bounding box computation, and list filtering by project_id
- Invalid GeoJSON rejection (422 boundary_invalid)
- Declared area mismatch rejection (422 area_mismatch)
- Overlapping parcel rejection (409 boundary_overlaps_existing_parcel)
- Overlap env-gate override (DMRV_PARCEL_OVERLAP_ENFORCED=0 allows overlap)
- Idempotency / duplicate parcel_uuid rejection (409 parcel_already_exists)
"""

from __future__ import annotations

import json
import pytest
from sqlalchemy import select

from models import SourceParcel, Project

pytestmark = pytest.mark.asyncio


async def _login_admin(client, session_factory):
    from portal.auth import hash_password
    from models import PortalUser

    async with session_factory() as session:
        session.add(
            PortalUser(
                email="admin-parcels@test.local",
                password_hash=hash_password("correct-horse-battery-staple"),
                role="admin",
                disabled=False,
            )
        )
        # Create a test project
        session.add(Project(project_id="proj-parcels-1", name="Parcel Test Project"))
        await session.commit()

    resp = await client.post(
        "/api/v1/portal/login",
        json={"email": "admin-parcels@test.local", "password": "correct-horse-battery-staple"},
    )
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _make_geojson(min_lon=0.0, min_lat=0.0, size_deg=0.001):
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_lon, min_lat],
                [min_lon + size_deg, min_lat],
                [min_lon + size_deg, min_lat + size_deg],
                [min_lon, min_lat + size_deg],
                [min_lon, min_lat],
            ]
        ],
    }


async def test_create_parcel_requires_admin_role(client):
    resp = await client.post(
        "/api/v1/portal/parcels",
        json={
            "project_id": "proj-parcels-1",
            "name": "North Field",
            "boundary_geojson": _make_geojson(),
        },
    )
    assert resp.status_code == 401


async def test_create_and_list_parcel(client, session_factory):
    headers = await _login_admin(client, session_factory)

    resp = await client.post(
        "/api/v1/portal/parcels",
        json={
            "project_id": "proj-parcels-1",
            "name": "North Field",
            "boundary_geojson": _make_geojson(0.0, 0.0, 0.001),
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "North Field"
    assert body["project_id"] == "proj-parcels-1"
    assert body["area_m2"] > 0
    assert body["boundary_status"] == "approved"

    # List parcels
    list_resp = await client.get("/api/v1/portal/parcels?project_id=proj-parcels-1", headers=headers)
    assert list_resp.status_code == 200
    parcels = list_resp.json()["parcels"]
    assert len(parcels) == 1
    assert parcels[0]["parcel_uuid"] == body["parcel_uuid"]


async def test_invalid_boundary_geojson_rejected(client, session_factory):
    headers = await _login_admin(client, session_factory)
    resp = await client.post(
        "/api/v1/portal/parcels",
        json={
            "project_id": "proj-parcels-1",
            "name": "Invalid Parcel",
            "boundary_geojson": {"type": "Polygon", "coordinates": []},
        },
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "boundary_invalid"


async def test_declared_area_mismatch_rejected(client, session_factory):
    headers = await _login_admin(client, session_factory)
    # Area of 0.001 deg square is ~12,300 m2 = ~3.04 acres.
    # Claiming 100 acres will trigger area mismatch (>15%)
    resp = await client.post(
        "/api/v1/portal/parcels",
        json={
            "project_id": "proj-parcels-1",
            "name": "Mismatch Parcel",
            "boundary_geojson": _make_geojson(1.0, 1.0, 0.001),
            "declared_area_acres": 100.0,
        },
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "area_mismatch"


async def test_overlapping_parcel_rejected(client, session_factory):
    headers = await _login_admin(client, session_factory)

    # 1. Register Parcel 1
    p1 = await client.post(
        "/api/v1/portal/parcels",
        json={
            "project_id": "proj-parcels-1",
            "name": "Parcel 1",
            "boundary_geojson": _make_geojson(2.0, 2.0, 0.01),
        },
        headers=headers,
    )
    assert p1.status_code == 201

    # 2. Register Parcel 2 (50% overlapping Parcel 1)
    p2 = await client.post(
        "/api/v1/portal/parcels",
        json={
            "project_id": "proj-parcels-1",
            "name": "Parcel 2 (Overlapping)",
            "boundary_geojson": _make_geojson(2.005, 2.0, 0.01),
        },
        headers=headers,
    )
    assert p2.status_code == 409
    assert p2.json()["detail"]["code"] == "boundary_overlaps_existing_parcel"


async def test_overlapping_parcel_rejected_ACROSS_projects(client, session_factory):
    """The anti-double-count core: two DIFFERENT projects must not both be able
    to register the same land. This is the exact fraud the overlap check exists
    to stop, and the case the same-project test above does NOT cover — before
    the fix the scan was scoped to payload.project_id, so a second project could
    claim identical land undetected."""
    headers = await _login_admin(client, session_factory)

    # A second, distinct project.
    async with session_factory() as session:
        session.add(Project(project_id="proj-parcels-2", name="Second Project"))
        await session.commit()

    p1 = await client.post(
        "/api/v1/portal/parcels",
        json={
            "project_id": "proj-parcels-1",
            "name": "Project 1 Parcel",
            "boundary_geojson": _make_geojson(7.0, 7.0, 0.01),
        },
        headers=headers,
    )
    assert p1.status_code == 201

    # Same land, DIFFERENT project → must be rejected as a double-count.
    p2 = await client.post(
        "/api/v1/portal/parcels",
        json={
            "project_id": "proj-parcels-2",
            "name": "Project 2 Land Grab",
            "boundary_geojson": _make_geojson(7.0, 7.0, 0.01),
        },
        headers=headers,
    )
    assert p2.status_code == 409
    assert p2.json()["detail"]["code"] == "boundary_overlaps_existing_parcel"
    # The conflict names the parcel in the OTHER project.
    assert p2.json()["detail"]["conflicting_parcel_name"] == "Project 1 Parcel"


async def test_device_parcels_list_returns_approved_only(client, session_factory, registered_device):
    """V8 Part 1.6: the device-facing GET /api/v1/parcels lets the field app
    fetch selectable parcels. Device-signed (the `client` fixture auto-signs),
    returns approved parcels for the project with only uuid+name (no geometry)."""
    # Seed an approved and a non-approved parcel via the DB.
    from models import SourceParcel

    async with session_factory() as session:
        session.add(Project(project_id="proj-dev", name="Device Project"))
        session.add(
            SourceParcel(
                parcel_uuid="dev-approved-uuid",
                project_id="proj-dev",
                name="Approved Field",
                boundary_geojson=json.dumps(_make_geojson(9.0, 9.0, 0.01)),
                area_m2=1.0,
                bbox_min_lat=9.0,
                bbox_min_lon=9.0,
                bbox_max_lat=9.01,
                bbox_max_lon=9.01,
                boundary_method="portal_drawn",
                boundary_status="approved",
            )
        )
        session.add(
            SourceParcel(
                parcel_uuid="dev-pending-uuid",
                project_id="proj-dev",
                name="Pending Field",
                boundary_geojson=json.dumps(_make_geojson(9.1, 9.1, 0.01)),
                area_m2=1.0,
                bbox_min_lat=9.1,
                bbox_min_lon=9.1,
                bbox_max_lat=9.11,
                bbox_max_lon=9.11,
                boundary_method="portal_drawn",
                boundary_status="pending_review",
            )
        )
        await session.commit()

    resp = await client.get("/api/v1/parcels?project_id=proj-dev")
    assert resp.status_code == 200, resp.text
    parcels = resp.json()["parcels"]
    assert len(parcels) == 1  # only the approved one
    assert parcels[0]["parcel_uuid"] == "dev-approved-uuid"
    assert parcels[0]["name"] == "Approved Field"
    # No geometry leaked to the device list.
    assert "boundary_geojson" not in parcels[0]


async def test_device_parcels_list_requires_signature(client, session_factory):
    """Unsigned request → rejected (device Ed25519 auth, same as batch ingest).
    The `client` fixture only auto-signs when neither X-Device-Id nor
    X-Signature is present; sending a bogus device id with no signature must
    fail."""
    resp = await client.get(
        "/api/v1/parcels?project_id=proj-dev",
        headers={"X-Device-Id": "unknown-unsigned-device"},
    )
    assert resp.status_code in (401, 403)


async def test_overlap_env_gate_override(client, session_factory, monkeypatch):
    monkeypatch.setenv("DMRV_PARCEL_OVERLAP_ENFORCED", "0")
    headers = await _login_admin(client, session_factory)

    p1 = await client.post(
        "/api/v1/portal/parcels",
        json={
            "project_id": "proj-parcels-1",
            "name": "Parcel Gate Base",
            "boundary_geojson": _make_geojson(3.0, 3.0, 0.01),
        },
        headers=headers,
    )
    assert p1.status_code == 201

    p2 = await client.post(
        "/api/v1/portal/parcels",
        json={
            "project_id": "proj-parcels-1",
            "name": "Parcel Gate Overlap",
            "boundary_geojson": _make_geojson(3.005, 3.0, 0.01),
        },
        headers=headers,
    )
    assert p2.status_code == 201


async def test_duplicate_parcel_uuid_rejected(client, session_factory):
    headers = await _login_admin(client, session_factory)
    fixed_uuid = "11111111-2222-3333-4444-555555555555"

    p1 = await client.post(
        "/api/v1/portal/parcels",
        json={
            "parcel_uuid": fixed_uuid,
            "project_id": "proj-parcels-1",
            "name": "Parcel Fixed ID",
            "boundary_geojson": _make_geojson(4.0, 4.0, 0.01),
        },
        headers=headers,
    )
    assert p1.status_code == 201

    p2 = await client.post(
        "/api/v1/portal/parcels",
        json={
            "parcel_uuid": fixed_uuid,
            "project_id": "proj-parcels-1",
            "name": "Parcel Duplicate ID",
            "boundary_geojson": _make_geojson(5.0, 5.0, 0.01),
        },
        headers=headers,
    )
    assert p2.status_code == 409
