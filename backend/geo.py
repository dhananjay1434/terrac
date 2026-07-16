"""Geospatial + EXIF-GPS helpers (extracted from server.py, R1).

Pure leaf: imports only stdlib math + piexif. `_evaluate_anchor` mutates a Batch's
status in place (photo-anchored GPS corroboration, T2.7) but takes the batch as an
argument — no model import needed here.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Optional

import piexif


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


def _evaluate_anchor(batch, photo_sha: Optional[str], exif_lat, exif_lon) -> None:
    """Decide a batch's status when a photo is anchored to it.

    Phase 9 + media integrity: only a photo whose SHA-256 matches the batch's
    declared `sha256_hash` may verify it (a mismatching upload never upgrades
    the batch). When the photo's EXIF GPS disagrees with the batch's claimed
    coordinates by >1 km the batch is quarantined for review.

    NOTE (audit): a photo with NO EXIF GPS bypasses the mismatch check entirely
    (None coordinates short-circuit _gps_mismatch_km) and still upgrades the
    batch. Deliberate for now — EXIF is client-authored/weak and attestation is
    the strong control — but flagged for methodology-owner review: an EXIF-less
    anchor could set a distinct status (e.g. RECEIVED_NO_GPS) instead.
    """
    if not batch.sha256_hash or not photo_sha:
        return
    if photo_sha.lower() != batch.sha256_hash.lower():
        return  # wrong photo — do not upgrade
    if _gps_mismatch_km(batch.latitude, batch.longitude, exif_lat, exif_lon):
        batch.status = "QUARANTINE_GPS_MISMATCH"
    elif batch.status == "UNVERIFIED":
        batch.status = "RECEIVED"
