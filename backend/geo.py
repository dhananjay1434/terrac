"""Geospatial + EXIF-GPS helpers (extracted from server.py, R1).

Pure leaf: imports only stdlib math + piexif + geometry & settings. `_evaluate_anchor` mutates
a Batch's status in place (photo-anchored GPS corroboration, T2.7 + V8 Part 1.4 source parcel geofencing).
"""

from __future__ import annotations

import logging
import os
from math import asin, cos, radians, sin, sqrt
from typing import Optional

import piexif

import geometry
import observability
import settings

log = logging.getLogger("dmrv.geo")


def _require_exif_gps() -> bool:
    """T2.7b: whether a photo anchoring a batch that CLAIMS coordinates must
    carry EXIF GPS to earn the clean RECEIVED upgrade. Default ON — the field
    app embeds EXIF GPS on every capture (secure_capture_service writes
    GPSLatitude/Longitude), so an EXIF-less anchor is anomalous (stripped /
    tampered / non-app upload). A deployment whose devices can't reliably write
    EXIF can relax this with DMRV_REQUIRE_EXIF_GPS=0."""
    return os.environ.get("DMRV_REQUIRE_EXIF_GPS", "1") == "1"


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    lon1, lat1, lon2, lat2 = map(radians, (lon1, lat1, lon2, lat2))
    a = (
        sin((lat2 - lat1) / 2) ** 2
        + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    )
    return 6371.0 * 2 * asin(sqrt(a))


def _exif_to_decimal(dms, ref) -> Optional[float]:
    """Convert an EXIF GPS (degrees, minutes, seconds) rational triple + ref
    ('N'/'S'/'E'/'W') to a signed decimal degree. Returns None if absent."""
    if not dms or ref is None:
        return None
    try:

        def _r(x):
            return x[0] / x[1]

        deg = _r(dms[0]) + _r(dms[1]) / 60.0 + _r(dms[2]) / 3600.0
    except (TypeError, IndexError, ZeroDivisionError):
        return None
    if isinstance(ref, bytes):
        ref = ref.decode("ascii", "ignore")
    if ref in ("S", "W"):
        deg = -deg
    return deg


def _parse_exif_gps(content: bytes) -> tuple[Optional[float], Optional[float]]:
    """Best-effort GPS extraction from a photo's EXIF. Non-JPEG / no-EXIF /
    no-GPS uploads return (None, None) rather than raising."""
    try:
        gps = piexif.load(content).get("GPS") or {}
    except Exception:
        return (None, None)
    lat = _exif_to_decimal(
        gps.get(piexif.GPSIFD.GPSLatitude), gps.get(piexif.GPSIFD.GPSLatitudeRef)
    )
    lon = _exif_to_decimal(
        gps.get(piexif.GPSIFD.GPSLongitude), gps.get(piexif.GPSIFD.GPSLongitudeRef)
    )
    return (lat, lon)


# T2.7: client-authored EXIF is WEAK corroboration — the app injects the GPS it
# later "matches" against, so this catches careless fraud and honest error, not a
# determined attacker. The strong device control is attestation (T2.1). The
# threshold is deliberately generous to avoid false quarantines on GPS drift.
GPS_ANCHOR_MISMATCH_KM = 1.0


def _gps_mismatch_km(
    lat1, lon1, lat2, lon2, threshold_km: float = GPS_ANCHOR_MISMATCH_KM
) -> bool:
    """True only when all four coordinates are present AND the photo EXIF and
    the claimed location disagree by more than `threshold_km`."""
    if None in (lat1, lon1, lat2, lon2):
        return False
    return haversine_km(lon1, lat1, lon2, lat2) > threshold_km


def _evaluate_anchor(
    batch,
    photo_sha: Optional[str],
    exif_lat,
    exif_lon,
    parcel_geojson: Optional[str] = None,
) -> None:
    """Decide a batch's status when a photo is anchored to it.

    Phase 9 + media integrity: only a photo whose SHA-256 matches the batch's
    declared `sha256_hash` may verify it (a mismatching upload never upgrades
    the batch). When the photo's EXIF GPS disagrees with the batch's claimed
    coordinates by >1 km the batch is quarantined for review.

    V8 Part 1.4: If parcel_geojson is provided (or loaded via batch.parcel_uuid),
    check that the claimed GPS coordinates fall within the parcel polygon
    (with DMRV_PARCEL_GEOFENCE_BUFFER_M tolerance). If outside, status becomes
    QUARANTINE_GPS_OUTSIDE_PARCEL. Null parcel_geojson skips cleanly (grandfathering).
    """
    if not batch.sha256_hash or not photo_sha:
        return
    if photo_sha.lower() != batch.sha256_hash.lower():
        return  # wrong photo — do not upgrade
    if _gps_mismatch_km(batch.latitude, batch.longitude, exif_lat, exif_lon):
        batch.status = "QUARANTINE_GPS_MISMATCH"
        return

    batch_claims_gps = batch.latitude is not None and batch.longitude is not None
    exif_gps_missing = exif_lat is None or exif_lon is None
    if batch_claims_gps and exif_gps_missing:
        if _require_exif_gps():
            log.warning(
                "batch %s anchor photo has no EXIF GPS but batch claims "
                "coordinates — quarantining for review (QUARANTINE_GPS_MISSING)",
                getattr(batch, "batch_uuid", "?"),
            )
            batch.status = "QUARANTINE_GPS_MISSING"
            return
        log.warning(
            "batch %s anchor photo has no EXIF GPS; DMRV_REQUIRE_EXIF_GPS=0 so "
            "upgrading anyway (GPS not independently corroborated)",
            getattr(batch, "batch_uuid", "?"),
        )

    # V8 Part 1.4: Source parcel geofence check
    if parcel_geojson and batch_claims_gps:
        try:
            # Trusted parse of an already-approved stored parcel (skip the
            # untrusted-input DoS guard so a later-lowered vertex cap can't turn
            # corroboration into a self-DoS).
            poly = geometry.parse_trusted_geojson(parcel_geojson)
            buffer_m = settings.parcel_geofence_buffer_m()
            if not geometry.point_in_polygon(poly, batch.longitude, batch.latitude, buffer_m=buffer_m):
                log.warning(
                    "batch %s GPS (%.5f, %.5f) is outside source parcel boundary — quarantining (QUARANTINE_GPS_OUTSIDE_PARCEL)",
                    getattr(batch, "batch_uuid", "?"),
                    batch.latitude,
                    batch.longitude,
                )
                observability.record_gate_rejection(
                    gate="boundary_geofence",
                    reason="QUARANTINE_GPS_OUTSIDE_PARCEL",
                    extra={
                        "batch_uuid": getattr(batch, "batch_uuid", None),
                        "parcel_uuid": getattr(batch, "parcel_uuid", None),
                    },
                )
                batch.status = "QUARANTINE_GPS_OUTSIDE_PARCEL"
                return
        except Exception as exc:
            log.warning("Failed to evaluate source parcel boundary for batch %s: %s", getattr(batch, "batch_uuid", "?"), exc)

    if batch.status == "UNVERIFIED":
        batch.status = "RECEIVED"
