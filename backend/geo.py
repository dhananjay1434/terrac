"""Geospatial + EXIF-GPS helpers (extracted from server.py, R1).

Pure leaf: imports only stdlib math + piexif. `_evaluate_anchor` mutates a Batch's
status in place (photo-anchored GPS corroboration, T2.7) but takes the batch as an
argument — no model import needed here.
"""

from __future__ import annotations

import logging
import os
from math import asin, cos, radians, sin, sqrt
from typing import Optional

import piexif

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


def _evaluate_anchor(batch, photo_sha: Optional[str], exif_lat, exif_lon) -> None:
    """Decide a batch's status when a photo is anchored to it.

    Phase 9 + media integrity: only a photo whose SHA-256 matches the batch's
    declared `sha256_hash` may verify it (a mismatching upload never upgrades
    the batch). When the photo's EXIF GPS disagrees with the batch's claimed
    coordinates by >1 km the batch is quarantined for review.

    T2.7b (V7 P3): a photo with NO EXIF GPS anchoring a batch that DOES claim
    coordinates no longer silently earns the clean RECEIVED upgrade. The field
    app embeds EXIF GPS on every capture, so a missing one is anomalous — under
    the default `DMRV_REQUIRE_EXIF_GPS` policy it is quarantined for review
    (QUARANTINE_GPS_MISSING) rather than passing unseen. Set the flag to 0 to
    restore the legacy pass-through (a device family that can't write EXIF), in
    which case the upgrade still happens but is logged. A batch that claims no
    coordinates has nothing to corroborate, so the requirement does not apply.
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

    if batch.status == "UNVERIFIED":
        batch.status = "RECEIVED"
