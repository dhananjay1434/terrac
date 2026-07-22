"""V8 Part 5 (A phase-2) — device-signed field-walk submission.

A field-walk link is minted by the portal (`POST
/portal/parcels/{uuid}/field-walk-link`, admin-only) and server-signed with
the Part 0.1 Ed25519 key (`server_signing.py` — the same key that signs the
remote-config document). The device receives that link (e.g. scanned as a
QR code — see `qr_scan_screen.dart`), walks the parcel boundary recording
GPS points, then POSTs both the link and the track here. This endpoint:

  1. Authenticates the DEVICE request itself (`verify_signature` — same
     device-auth layer as dispatch/media).
  2. Verifies the LINK's server signature, expiry, and that its nonce has
     never been consumed (single-use — a captured link can't submit a second,
     different track).
  3. Builds a polygon from the walked points and computes its overlap ratio
     against the parcel's portal-drawn boundary — corroborating evidence, not
     a silent replacement (see FieldWalkTrack model docstring).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import geometry
import server_signing
from db import get_session
from models import FieldWalkTrack, SourceParcel
from schemas import FieldWalkSubmit
from security import verify_signature

router = APIRouter()


@router.post("/api/v1/field-walk", status_code=status.HTTP_201_CREATED)
async def submit_field_walk(
    payload: FieldWalkSubmit,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
) -> dict:
    # 1) Verify the LINK's server signature over its own canonical payload
    #    string (not the device's request body — the link was signed by the
    #    server at mint time, independent of this device's own signature).
    verdict = server_signing.verify(
        payload.link_payload.encode("utf-8"), payload.link_signature, payload.link_kid
    )
    if verdict != "valid":
        raise HTTPException(status_code=403, detail="invalid_field_walk_link")

    try:
        link = json.loads(payload.link_payload)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="malformed_link_payload")

    parcel_uuid = link.get("parcel_uuid")
    nonce = link.get("nonce")
    expires_at_str = link.get("expires_at")
    if not parcel_uuid or not nonce or not expires_at_str:
        raise HTTPException(status_code=400, detail="incomplete_link_payload")

    try:
        expires_at = datetime.fromisoformat(expires_at_str)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="malformed_link_expiry")

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="field_walk_link_expired")

    parcel = (
        await session.execute(
            select(SourceParcel).where(SourceParcel.parcel_uuid == parcel_uuid)
        )
    ).scalar_one_or_none()
    if parcel is None:
        raise HTTPException(status_code=404, detail="parcel_not_found")

    # 2) Build + validate the walked polygon BEFORE touching the DB, so a
    #    malformed track never gets as far as an insert attempt.
    try:
        walked_poly = geometry.polygon_from_track_points(
            [(pt[0], pt[1]) for pt in payload.points]
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid_track: {exc}")

    overlap_ratio = None
    try:
        declared_poly = geometry.parse_trusted_geojson(parcel.boundary_geojson)
        overlap_ratio = geometry.overlap_ratio(walked_poly, declared_poly)
    except Exception:
        # Corroboration is best-effort — a parcel with unparsable stored
        # geometry (shouldn't happen; defense in depth) still lets the walk
        # itself be recorded, just without a computed overlap.
        overlap_ratio = None

    track = FieldWalkTrack(
        parcel_uuid=parcel_uuid,
        device_id=device_id,
        link_nonce=nonce,
        points_json=json.dumps(payload.points),
        computed_boundary_geojson=geometry.to_geojson_str(walked_poly),
        computed_area_m2=geometry.geodesic_area_m2(walked_poly),
        overlap_ratio_vs_declared=overlap_ratio,
    )
    session.add(track)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        # UNIQUE(link_nonce) tripped — this link was already used.
        raise HTTPException(status_code=409, detail="field_walk_link_already_used")

    return {
        "parcel_uuid": parcel_uuid,
        "computed_area_m2": track.computed_area_m2,
        "overlap_ratio_vs_declared": track.overlap_ratio_vs_declared,
    }
