"""Phase 9 — server-side GPS corroboration; drop the client mock-GPS header.

The client-supplied ``X-Mock-Location`` header is no longer an access control.
Instead the server parses the uploaded photo's EXIF GPS and quarantines a batch
when the photo location and the batch's claimed coordinates disagree by >1 km.
"""

import hashlib
import io
import json
import uuid

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


async def _post_batch(client, batch_uuid, sha, lat, lon, op):
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

    async with session_factory() as s:
        batch = (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(uuid.UUID(bu))))
        ).scalar_one()
        assert batch.status == "RECEIVED"


@pytest.mark.asyncio
async def test_mismatched_gps_is_quarantined(client, session_factory):
    bu = str(uuid.uuid4())
    photo = _jpeg_with_gps(28.6139, 77.2090)  # Delhi
    sha = hashlib.sha256(photo).hexdigest()

    # Batch claims London — >1 km from the photo's Delhi EXIF.
    r1 = await _post_batch(client, bu, sha, 51.5074, -0.1278, "op-gps-bad")
    assert r1.status_code == 201, r1.text

    r2 = await _post_media(client, bu, photo, "op-gps-bad-media")
    assert r2.status_code == 200, r2.text

    async with session_factory() as s:
        batch = (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(uuid.UUID(bu))))
        ).scalar_one()
        assert batch.status == "QUARANTINE_GPS_MISMATCH"


def _jpeg_no_gps() -> bytes:
    """A tiny JPEG with NO EXIF GPS (simulates a stripped / non-app photo)."""
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (120, 200, 120)).save(buf, "jpeg")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_no_exif_gps_is_quarantined_by_default(client, session_factory):
    """V7 P3: a batch that CLAIMS coordinates but is anchored by a photo with no
    EXIF GPS no longer silently reaches RECEIVED — it is quarantined for review."""
    bu = str(uuid.uuid4())
    photo = _jpeg_no_gps()
    sha = hashlib.sha256(photo).hexdigest()

    r1 = await _post_batch(client, bu, sha, 28.6139, 77.2090, "op-gps-missing")
    assert r1.status_code == 201, r1.text
    assert r1.json()["status"] == "UNVERIFIED"

    r2 = await _post_media(client, bu, photo, "op-gps-missing-media")
    assert r2.status_code == 200, r2.text

    async with session_factory() as s:
        batch = (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(uuid.UUID(bu))))
        ).scalar_one()
        assert batch.status == "QUARANTINE_GPS_MISSING"


@pytest.mark.asyncio
async def test_no_exif_gps_upgrades_when_requirement_relaxed(
    client, session_factory, monkeypatch
):
    """With DMRV_REQUIRE_EXIF_GPS=0 the legacy pass-through is restored (for a
    device family that can't write EXIF) — the batch upgrades but the event is
    logged as not-independently-corroborated."""
    monkeypatch.setenv("DMRV_REQUIRE_EXIF_GPS", "0")
    bu = str(uuid.uuid4())
    photo = _jpeg_no_gps()
    sha = hashlib.sha256(photo).hexdigest()

    r1 = await _post_batch(client, bu, sha, 28.6139, 77.2090, "op-gps-relaxed")
    assert r1.status_code == 201, r1.text

    r2 = await _post_media(client, bu, photo, "op-gps-relaxed-media")
    assert r2.status_code == 200, r2.text

    async with session_factory() as s:
        batch = (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(uuid.UUID(bu))))
        ).scalar_one()
        assert batch.status == "RECEIVED"


def test_evaluate_anchor_missing_exif_units():
    """Pure-unit lock on the P3 policy without the HTTP stack."""
    from types import SimpleNamespace
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
