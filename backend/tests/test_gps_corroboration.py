"""Phase 9 — server-side GPS corroboration; drop the client mock-GPS header.

The client-supplied ``X-Mock-Location`` header is no longer an access control.
Instead the server parses the uploaded photo's EXIF GPS and quarantines a batch
when the photo location and the batch's claimed coordinates disagree by >1 km.
"""

import hashlib
import io
import json
import uuid
from types import SimpleNamespace

import piexif
import pytest
from PIL import Image
from sqlalchemy import select

from models import Batch
from tests.remediation.crypto_utils import sign_request, sign_media


def _dms(value: float):
    """Decimal degree -> EXIF (deg, min, sec) rationals (abs value)."""
    value = abs(value)
    deg = int(value)
    minutes = int((value - deg) * 60)
    seconds = round((value - deg - minutes / 60) * 3600 * 100)
    return ((deg, 1), (minutes, 1), (seconds, 100))


def _jpeg_with_gps(lat: float, lon: float) -> bytes:
    """A tiny JPEG carrying EXIF GPS at (lat, lon)."""
    gps = {
        piexif.GPSIFD.GPSLatitudeRef: b"N" if lat >= 0 else b"S",
        piexif.GPSIFD.GPSLatitude: _dms(lat),
        piexif.GPSIFD.GPSLongitudeRef: b"E" if lon >= 0 else b"W",
        piexif.GPSIFD.GPSLongitude: _dms(lon),
    }
    exif_bytes = piexif.dump({"GPS": gps})
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (120, 200, 120)).save(buf, "jpeg", exif=exif_bytes)
    return buf.getvalue()


async def _post_batch(client, batch_uuid, sha, lat, lon, op, parcel_uuid=None):
    payload = {
        "batch_uuid": batch_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": "2026-01-01T00:00:00Z",
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
        "min_recorded_temp_c": 0.0,
        "wet_yield_kg": 100.0,
        "transport_distance_km": 0.0,
        "sha256_hash": sha,
        "latitude": lat,
        "longitude": lon,
    }
    # Only include parcel_uuid when set, so existing callers' signed payloads
    # (and signatures) are byte-identical to before.
    if parcel_uuid is not None:
        payload["parcel_uuid"] = parcel_uuid
    body = json.dumps(payload).encode("utf-8")
    return await client.post(
        "/api/v1/batches",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": op,
            "X-Device-Id": "test-device-reg",
            "X-Signature": sign_request(
                "test-device-reg", "", "POST", "/api/v1/batches", op, payload
            ),
        },
    )


async def _post_media(client, batch_uuid, content, op):
    sha = hashlib.sha256(content).hexdigest()
    return await client.post(
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


@pytest.mark.asyncio
async def test_matching_gps_anchors_to_received(client, session_factory):
    bu = str(uuid.uuid4())
    photo = _jpeg_with_gps(28.6139, 77.2090)
    sha = hashlib.sha256(photo).hexdigest()

    # Batch claims the same location as the photo EXIF.
    r1 = await _post_batch(client, bu, sha, 28.6139, 77.2090, "op-gps-ok")
    assert r1.status_code == 201, r1.text
    assert r1.json()["status"] == "UNVERIFIED"

    r2 = await _post_media(client, bu, photo, "op-gps-ok-media")
    assert r2.status_code == 200, r2.text

    async with session_factory() as session:
        b = (
            await session.execute(select(Batch).where(Batch.batch_uuid == bu))
        ).scalar_one()
        assert b.status == "RECEIVED"


async def _seed_parcel(session_factory, parcel_uuid, *, min_lon, min_lat, size=0.02):
    """Insert an approved SourceParcel covering [min_lon..min_lon+size] x
    [min_lat..min_lat+size]. Used to drive the geofence end-to-end (not by
    calling _evaluate_anchor directly)."""
    from models import SourceParcel

    poly = {
        "type": "Polygon",
        "coordinates": [
            [
                [min_lon, min_lat],
                [min_lon + size, min_lat],
                [min_lon + size, min_lat + size],
                [min_lon, min_lat + size],
                [min_lon, min_lat],
            ]
        ],
    }
    async with session_factory() as session:
        session.add(
            SourceParcel(
                parcel_uuid=parcel_uuid,
                project_id="proj-geofence",
                name="Geofence Parcel",
                boundary_geojson=json.dumps(poly),
                area_m2=1.0,
                declared_area_acres=None,
                bbox_min_lat=min_lat,
                bbox_min_lon=min_lon,
                bbox_max_lat=min_lat + size,
                bbox_max_lon=min_lon + size,
                boundary_method="portal_drawn",
                boundary_status="approved",
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_batch_inside_parcel_anchors_to_received(client, session_factory):
    """End-to-end (Part 1 H1 wiring): a batch that carries a real parcel_uuid
    and whose GPS is INSIDE the approved parcel anchors normally. Drives the
    full ingest→media→_evaluate_anchor path, NOT _evaluate_anchor directly."""
    parcel_uuid = str(uuid.uuid4())
    await _seed_parcel(session_factory, parcel_uuid, min_lon=77.20, min_lat=28.60)

    bu = str(uuid.uuid4())
    photo = _jpeg_with_gps(28.6139, 77.2090)  # inside the parcel
    sha = hashlib.sha256(photo).hexdigest()

    r1 = await _post_batch(
        client, bu, sha, 28.6139, 77.2090, "op-inside", parcel_uuid=parcel_uuid
    )
    assert r1.status_code == 201, r1.text
    r2 = await _post_media(client, bu, photo, "op-inside-media")
    assert r2.status_code == 200, r2.text

    async with session_factory() as session:
        b = (
            await session.execute(select(Batch).where(Batch.batch_uuid == bu))
        ).scalar_one()
        assert b.parcel_uuid == parcel_uuid  # H1: the linkage is actually stored
        assert b.status == "RECEIVED"


@pytest.mark.asyncio
async def test_batch_outside_parcel_is_quarantined(client, session_factory):
    """End-to-end: a batch whose GPS is OUTSIDE its approved parcel is
    quarantined. This is the geofence the review found was dead code (nothing
    ever set batch.parcel_uuid); it now fires through the real ingest path."""
    parcel_uuid = str(uuid.uuid4())
    await _seed_parcel(session_factory, parcel_uuid, min_lon=77.20, min_lat=28.60)

    bu = str(uuid.uuid4())
    photo = _jpeg_with_gps(28.7000, 77.3000)  # well outside the parcel
    sha = hashlib.sha256(photo).hexdigest()

    r1 = await _post_batch(
        client, bu, sha, 28.7000, 77.3000, "op-outside", parcel_uuid=parcel_uuid
    )
    assert r1.status_code == 201, r1.text
    r2 = await _post_media(client, bu, photo, "op-outside-media")
    assert r2.status_code == 200, r2.text

    async with session_factory() as session:
        b = (
            await session.execute(select(Batch).where(Batch.batch_uuid == bu))
        ).scalar_one()
        assert b.status == "QUARANTINE_GPS_OUTSIDE_PARCEL"


@pytest.mark.asyncio
async def test_mismatching_gps_quarantines_batch(client, session_factory):
    bu = str(uuid.uuid4())
    # Photo is at Delhi (28.6139, 77.2090).
    photo = _jpeg_with_gps(28.6139, 77.2090)
    sha = hashlib.sha256(photo).hexdigest()

    # Batch claims Mumbai (19.0760, 72.8777) — >1000 km away.
    r1 = await _post_batch(client, bu, sha, 19.0760, 72.8777, "op-gps-bad")
    assert r1.status_code == 201, r1.text

    r2 = await _post_media(client, bu, photo, "op-gps-bad-media")
    assert r2.status_code == 200, r2.text

    async with session_factory() as session:
        b = (
            await session.execute(select(Batch).where(Batch.batch_uuid == bu))
        ).scalar_one()
        assert b.status == "QUARANTINE_GPS_MISMATCH"


def test_evaluate_anchor_missing_exif_units():
    from geo import _evaluate_anchor

    def _batch(**kw):
        base = dict(
            batch_uuid="b1",
            sha256_hash="a" * 64,
            latitude=28.6139,
            longitude=77.2090,
            status="UNVERIFIED",
        )
        base.update(kw)
        return SimpleNamespace(**base)

    # Batch claims coords, photo sha matches, no EXIF GPS → quarantined (default).
    b = _batch()
    _evaluate_anchor(b, "A" * 64, None, None)
    assert b.status == "QUARANTINE_GPS_MISSING"

    # A batch with NO claimed coords has nothing to corroborate → still upgrades.
    b2 = _batch(latitude=None, longitude=None)
    _evaluate_anchor(b2, "A" * 64, None, None)
    assert b2.status == "RECEIVED"

    # Matching EXIF GPS still upgrades cleanly.
    b3 = _batch()
    _evaluate_anchor(b3, "A" * 64, 28.6139, 77.2090)
    assert b3.status == "RECEIVED"


def test_evaluate_anchor_source_parcel_geofencing():
    from geo import _evaluate_anchor

    parcel_geojson = json.dumps({
        "type": "Polygon",
        "coordinates": [
            [
                [77.2000, 28.6100],
                [77.2200, 28.6100],
                [77.2200, 28.6200],
                [77.2000, 28.6200],
                [77.2000, 28.6100],
            ]
        ]
    })

    def _batch(**kw):
        base = dict(
            batch_uuid="b1",
            sha256_hash="a" * 64,
            latitude=28.6139,
            longitude=77.2090,
            status="UNVERIFIED",
        )
        base.update(kw)
        return SimpleNamespace(**base)

    # 1. Batch inside source parcel -> RECEIVED
    b_inside = _batch()
    _evaluate_anchor(b_inside, "A" * 64, 28.6139, 77.2090, parcel_geojson=parcel_geojson)
    assert b_inside.status == "RECEIVED"

    # 2. Batch outside source parcel -> QUARANTINE_GPS_OUTSIDE_PARCEL
    b_outside = _batch(latitude=28.7000, longitude=77.3000)
    _evaluate_anchor(b_outside, "A" * 64, 28.7000, 77.3000, parcel_geojson=parcel_geojson)
    assert b_outside.status == "QUARANTINE_GPS_OUTSIDE_PARCEL"

    # 3. Batch at parcel buffer edge (slightly outside polygon boundary) -> RECEIVED
    b_edge = _batch(latitude=28.60995, longitude=77.2090) # ~5m outside min_lat 28.6100
    _evaluate_anchor(b_edge, "A" * 64, 28.60995, 77.2090, parcel_geojson=parcel_geojson)
    assert b_edge.status == "RECEIVED"

    # 4. Null parcel_geojson -> grandfathered, RECEIVED
    b_null = _batch()
    _evaluate_anchor(b_null, "A" * 64, 28.6139, 77.2090, parcel_geojson=None)
    assert b_null.status == "RECEIVED"


@pytest.mark.asyncio
async def test_mock_location_header_has_no_effect_on_media(client):
    bu = str(uuid.uuid4())
    content = b"plain-bytes-no-exif"
    sha = hashlib.sha256(content).hexdigest()
    r = await client.post(
        "/api/v1/media",
        files={"file": ("p.jpg", io.BytesIO(content), "image/jpeg")},
        headers={
            "X-Idempotency-Key": "op-mock-noeffect",
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": bu,
            "X-Device-Id": "test-device-reg",
            "X-Mock-Location": "true",
            "X-Signature": sign_media("test-device-reg", "op-mock-noeffect", sha, bu),
        },
    )
    assert r.status_code == 200, r.text
