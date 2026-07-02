"""Kon-Tiki Biochar dMRV — FastAPI microservice with PostgreSQL.

Endpoints:
  POST /api/v1/batches  - Receive dMRV payload with idempotency
  POST /api/v1/media    - Upload media with SHA-256 verification
  GET  /api/health      - Health check
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Optional, Literal
from uuid import UUID

from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
import piexif

from db import get_session, init_db
from models import (
    AnnualVerification,
    Batch,
    CompositePileSample,
    DeviceKey,
    EndUseApplication,
    EnrollmentToken,
    Kiln,
    MediaFile,
    MoistureReading,
    OperatorTraining,
    PyrolysisTelemetry,
    ScaleCalibration,
    SupervisorVisit,
    SystemMetadata,
    TransportEvent,
    YieldMetrics,
)
from emission_factors import TRANSPORT_EVENTS_ENFORCED, fuel_emissions_kg_co2e
from lca_engine import CORG_TABLE, calculate_carbon_credit, sign_lca_audit
from corroboration import (
    assemble,
    derive_composite_sample_compliance,
    derive_delivery_compliance,
    derive_ignition_compliance,
    derive_min_temp,
    derive_moisture_compliance,
    derive_pyrolysis_photo_compliance,
    derive_transport_km,
    derive_wet_yield,
)

load_dotenv()


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


def _gps_mismatch_km(lat1, lon1, lat2, lon2, threshold_km: float = 1.0) -> bool:
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
    """
    if not batch.sha256_hash or not photo_sha:
        return
    if photo_sha.lower() != batch.sha256_hash.lower():
        return  # wrong photo — do not upgrade
    if _gps_mismatch_km(batch.latitude, batch.longitude, exif_lat, exif_lon):
        batch.status = "QUARANTINE_GPS_MISMATCH"
    elif batch.status == "UNVERIFIED":
        batch.status = "RECEIVED"


_HMAC_SECRET = os.environ.get("DMRV_HMAC_SECRET")
if not _HMAC_SECRET:
    raise RuntimeError("DMRV_HMAC_SECRET env var is required.")

_ADMIN_SECRET = os.environ.get("DMRV_ADMIN_SECRET")
if not _ADMIN_SECRET:
    raise RuntimeError("DMRV_ADMIN_SECRET env var is required.")

# Phase 9-R: platform attestation (Play Integrity / DeviceCheck) is NOT yet
# cryptographically verified — a rooted device's forged blob would pass. We refuse
# to pretend a blob's mere presence proves integrity. Policy switch:
#   False (default, "Option B") — non-blocking: log a loud warning, do not gate.
#   True  ("Option A")          — fail closed: an unverified attestation keeps the
#                                  batch PROVISIONAL. Flip to True once a real
#                                  verifier exists (or to halt final issuance until
#                                  then). See FINDINGS_BACKLOG.
_ATTESTATION_ENFORCED = False

log = logging.getLogger("dmrv")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    log.info("Database initialized")
    yield


app = FastAPI(
    title="Kon-Tiki dMRV API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

_ALLOWED_ORIGIN = os.environ.get("DMRV_ALLOWED_ORIGIN", "")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_ALLOWED_ORIGIN] if _ALLOWED_ORIGIN else [],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Device-Id",
        "X-Idempotency-Key",
        "X-Payload-Sha256",
        # Phase 13: advertise the live Ed25519 signature + auth headers actually
        # used; the dead legacy HMAC signature header (removed in Phase 5) is gone.
        "X-Signature",
        "X-Enrollment-Token",
        "X-Admin-Secret",
    ],
)

# Phase 11-R: reject oversized bodies via Content-Length before parsing. JSON
# endpoints are capped at 2 MB (a max 100k-float telemetry log is well under that);
# /api/v1/media gets headroom for its multipart 10 MB file (its handler enforces the
# real 10 MB cap while streaming).
_MAX_JSON_BODY_BYTES = 2 * 1024 * 1024
_MAX_MEDIA_BODY_BYTES = 12 * 1024 * 1024


@app.middleware("http")
async def _limit_body_size(request: Request, call_next):
    cl = request.headers.get("content-length")
    if cl is not None and cl.isdigit():
        cap = (
            _MAX_MEDIA_BODY_BYTES
            if request.url.path == "/api/v1/media"
            else _MAX_JSON_BODY_BYTES
        )
        if int(cl) > cap:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "payload_too_large"},
            )
    return await call_next(request)


# Media upload directory — relative to this file, works on Windows + Linux + Docker.
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ==================== Pydantic Models ====================


class BatchPayload(BaseModel):
    """Strict Pydantic V2 model for batch payload."""

    batch_uuid: UUID
    feedstock_species: str
    harvest_timestamp: datetime
    moisture_percent: float = Field(..., ge=0.0, le=100.0)
    photo_path: Optional[str] = None
    sha256_hash: Optional[str] = Field(None, min_length=64, max_length=64)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    harvest_uptime_seconds: Optional[int] = Field(0, ge=0)

    sourcing_uuid: Optional[str] = None
    moisture_compliant: Optional[bool] = None
    mock_location_enabled: Optional[bool] = False
    azimuth: Optional[float] = None
    pitch: Optional[float] = None
    roll: Optional[float] = None

    # Rainbow compliance C1: biomass input amount + how it was measured.
    biomass_input_kg: Optional[float] = Field(None, ge=0.0, le=1_000_000.0)
    biomass_measurement_method: Optional[
        Literal["direct_weigh", "yield_conversion"]
    ] = None

    # --- LCA inputs (Prompt 8) ---
    # Phase 7-R: these are NOT client-supplied. They are corroborated server-side
    # from the /telemetry (min temp), /yield (wet yield) and /application (transport
    # GPS) streams, which arrive AFTER the batch. They are optional on the payload;
    # an uncorroborated input keeps the batch PROVISIONAL (never issued as final).
    wet_yield_kg: Optional[float] = Field(
        None, gt=0.0, description="Corroborated server-side from /yield"
    )
    min_recorded_temp_c: Optional[float] = Field(
        None,
        ge=-50.0,
        le=1500.0,
        description="Corroborated server-side from /telemetry",
    )
    transport_distance_km: Optional[float] = Field(
        None,
        ge=0.0,
        le=20000.0,
        description="Corroborated server-side from /application GPS",
    )

    @field_validator("feedstock_species")
    @classmethod
    def validate_feedstock(cls, v: str) -> str:
        if v not in CORG_TABLE:
            raise ValueError(
                f"feedstock_species must be one of {list(CORG_TABLE.keys())}"
            )
        return v

    @field_validator("sha256_hash")
    @classmethod
    def validate_hex(cls, v: Optional[str]) -> Optional[str]:
        """Ensure SHA-256 hash is valid hexadecimal."""
        if v is None:
            return v
        try:
            int(v, 16)
        except ValueError:
            raise ValueError("sha256_hash must be valid hexadecimal")
        return v.lower()

    # Phase 7-R: the payload-temp validator was removed. min_recorded_temp_c is
    # no longer client-asserted; the <100 C / >=60-sample burn-compliance rule now
    # lives in corroboration.derive_min_temp against the real /telemetry log.

    # Phase 8-R: lab_h_corg is NOT accepted from the device. A lab-measured
    # permanence ratio is authoritative and must arrive on the admin-authenticated
    # /api/v1/admin/lab-hcorg channel (range-checked). extra="forbid" now 422s any
    # client that tries to self-assert it.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BatchResponse(BaseModel):
    batch_uuid: str
    operation_id: str
    status: str
    duplicate: bool
    received_at: datetime
    net_credit_t_co2e: Optional[float] = None
    # Phase 8: True when net_credit_t_co2e was computed on an ASSUMED H:Corg
    # (no lab value). Such a credit is NOT issuable as final.
    provisional: Optional[bool] = None


class MediaUploadResponse(BaseModel):
    server_sha256: str
    stored: bool
    file_path: str


class RegistrationRequest(BaseModel):
    device_id: str = Field(..., min_length=1)
    public_key: str = Field(..., min_length=40, max_length=64)  # base64url Ed25519


class RegistrationResponse(BaseModel):
    status: str
    device_id: str


# ==================== Endpoints ====================\n
@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "dmrv-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


async def verify_signature(
    request: Request,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> str:
    if not x_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_signature"
        )
    if not x_device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="unknown_device"
        )
    device = (
        await session.execute(
            select(DeviceKey).where(DeviceKey.device_id == x_device_id)
        )
    ).scalar_one_or_none()
    if not device:
        log.error(f"Signature Error: unknown_device '{x_device_id}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="unknown_device"
        )
    pub = Ed25519PublicKey.from_public_bytes(_b64url_decode(device.public_key))
    body_hash = hashlib.sha256(await request.body()).hexdigest()
    canonical = "\n".join(
        [
            request.method.upper(),
            request.url.path,
            x_idempotency_key or "",
            body_hash,
            x_device_id,
        ]
    ).encode("utf-8")
    try:
        pub.verify(_b64url_decode(x_signature), canonical)
    except InvalidSignature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="signature_mismatch"
        )
    return x_device_id


async def verify_media_signature(
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    x_declared_sha256: Optional[str] = Header(None, alias="X-Declared-SHA256"),
    x_batch_uuid: Optional[str] = Header(None, alias="X-Batch-UUID"),
    session: AsyncSession = Depends(get_session),
) -> str:
    """Phase 15-A: Ed25519 auth for the media evidence channel.

    FROZEN media canonical — MUST byte-match the client's CryptoSigner.signMediaUpload:
        POST\\n/api/v1/media\\n{idempotency_key}\\n{declared_sha256_lower}\\n{batch_uuid}\\n{device_id}
    We sign the DECLARED file hash rather than sha256(multipart body) — the client
    cannot reproduce the exact multipart bytes. upload_media separately enforces
    calculated_hash == declared, so signing the declared hash binds the real bytes.
    """
    if not x_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_signature"
        )
    if not x_device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="unknown_device"
        )
    device = (
        await session.execute(
            select(DeviceKey).where(DeviceKey.device_id == x_device_id)
        )
    ).scalar_one_or_none()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="unknown_device"
        )
    pub = Ed25519PublicKey.from_public_bytes(_b64url_decode(device.public_key))
    canonical = "\n".join(
        [
            "POST",
            "/api/v1/media",
            x_idempotency_key or "",
            (x_declared_sha256 or "").lower(),
            x_batch_uuid or "",
            x_device_id,
        ]
    ).encode("utf-8")
    try:
        pub.verify(_b64url_decode(x_signature), canonical)
    except InvalidSignature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="signature_mismatch"
        )
    return x_device_id


@app.post(
    "/api/v1/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_device(
    payload: RegistrationRequest,
    x_enrollment_token: Optional[str] = Header(None, alias="X-Enrollment-Token"),
    session: AsyncSession = Depends(get_session),
):
    if not x_enrollment_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="enrollment_token_required"
        )

    token_stmt = select(EnrollmentToken).where(
        EnrollmentToken.token == x_enrollment_token
    )
    token_res = await session.execute(token_stmt)
    db_token = token_res.scalar_one_or_none()

    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_enrollment_token"
        )
    if db_token.used_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="enrollment_token_used"
        )
    if db_token.expires_at:
        expires = (
            db_token.expires_at.replace(tzinfo=timezone.utc)
            if db_token.expires_at.tzinfo is None
            else db_token.expires_at
        )
        if expires < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="enrollment_token_expired",
            )

    stmt = select(DeviceKey).where(DeviceKey.device_id == payload.device_id)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="device_already_registered"
        )

    new_key = DeviceKey(device_id=payload.device_id, public_key=payload.public_key)
    session.add(new_key)

    db_token.used_at = datetime.now(timezone.utc)
    await session.commit()
    log.info(
        f"[register] Device {payload.device_id} registered successfully with token."
    )
    return RegistrationResponse(status="registered", device_id=payload.device_id)


class MintTokenRequest(BaseModel):
    token: str
    expires_in_days: int = 7


@app.post("/api/v1/admin/mint-token", status_code=status.HTTP_201_CREATED)
async def mint_enrollment_token(
    payload: MintTokenRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    if not hmac.compare_digest(x_admin_secret, _ADMIN_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )

    expires = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
    new_token = EnrollmentToken(token=payload.token, expires_at=expires)
    session.add(new_token)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="token_already_exists")

    return {
        "status": "minted",
        "token": payload.token,
        "expires_at": expires.isoformat(),
    }


class LabHCorgRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_uuid: UUID
    # Physically plausible H:Corg molar ratio for biochar (~0.1–0.7 typical; Lantana
    # ~0.3–0.35). Bounds reject forged/absurd values that would inflate permanence.
    lab_h_corg: float = Field(..., ge=0.1, le=1.5)


class LabResultsRequest(BaseModel):
    """C7 full per-batch lab-results channel (admin-authenticated, range-checked).

    All fields optional so a lab can report incrementally. `organic_carbon_pct` is
    the credit-affecting one (replaces the species CORG_TABLE constant); `lab_h_corg`
    is accepted here too so a single lab report can supply both permanence inputs.
    The rest are captured for verification / the 1000-year pathway (gated to C8).
    """

    model_config = ConfigDict(extra="forbid")
    batch_uuid: UUID
    lab_h_corg: Optional[float] = Field(None, ge=0.1, le=1.5)
    # Organic carbon as a FRACTION in (0, 1] (e.g. Lantana ~0.60), matching CORG_TABLE.
    organic_carbon_pct: Optional[float] = Field(None, gt=0.0, le=1.0)
    # Biochar moisture: the methodology requires >= 3 samples when measured by mass.
    biochar_moisture_samples: Optional[list[float]] = Field(
        None, min_length=3, max_length=100
    )
    dry_bulk_density: Optional[float] = Field(None, gt=0.0, le=2000.0)
    # 1000-year pathway inputs (data capture only in C7; pathway gated to C8).
    inertinite_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    residual_corg_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    ro_measurements_count: Optional[int] = Field(None, ge=0)

    @field_validator("biochar_moisture_samples")
    @classmethod
    def _validate_moisture_samples(
        cls, v: Optional[list[float]]
    ) -> Optional[list[float]]:
        if v is not None and any((m < 0.0 or m > 100.0) for m in v):
            raise ValueError("biochar_moisture_samples must be percentages in [0, 100]")
        return v


@app.post("/api/v1/admin/lab-hcorg", status_code=status.HTTP_200_OK)
async def ingest_lab_hcorg(
    payload: LabHCorgRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    """Authenticated lab channel for the permanence ratio (Phase 8-R).

    A lab-measured H:Corg is authoritative and must NOT be self-asserted by the
    device — it arrives here, admin-authenticated and range-checked, then triggers
    a recompute that can clear the batch's PROVISIONAL status.
    """
    if not hmac.compare_digest(x_admin_secret, _ADMIN_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )
    batch = (
        await session.execute(
            select(Batch).where(Batch.batch_uuid == payload.batch_uuid)
        )
    ).scalar_one_or_none()
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="unknown_batch"
        )
    await recompute_batch_credit(session, batch, lab_h_corg=payload.lab_h_corg)
    await session.commit()
    return {
        "status": "ok",
        "batch_uuid": str(payload.batch_uuid),
        "provisional": batch.provisional,
    }


@app.post("/api/v1/admin/lab", status_code=status.HTTP_200_OK)
async def ingest_lab_results(
    payload: LabResultsRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    """C7 full lab-results channel (admin-authenticated).

    Widens the Phase-8-R /admin/lab-hcorg endpoint to the full per-batch lab set.
    `organic_carbon_pct` is authoritative and REPLACES the species CORG_TABLE
    constant in the credit (its absence keeps the batch provisional via
    `assumed_corg`, mirroring `assumed_h_corg`). The remaining fields are captured
    for verification / the 1000-year pathway (gated to C8). Lab data must NEVER be
    device-asserted — same admin-secret + range-check discipline as lab-hcorg.
    """
    if not hmac.compare_digest(x_admin_secret, _ADMIN_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )
    batch = (
        await session.execute(
            select(Batch).where(Batch.batch_uuid == payload.batch_uuid)
        )
    ).scalar_one_or_none()
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="unknown_batch"
        )

    # Persist the non-credit verification fields directly (recompute reads the
    # credit-affecting organic_carbon_pct via the lab_corg kwarg below).
    if payload.biochar_moisture_samples is not None:
        batch.biochar_moisture_samples_json = json.dumps(
            payload.biochar_moisture_samples
        )
    if payload.dry_bulk_density is not None:
        batch.dry_bulk_density = payload.dry_bulk_density
    if payload.inertinite_pct is not None:
        batch.inertinite_pct = payload.inertinite_pct
    if payload.residual_corg_pct is not None:
        batch.residual_corg_pct = payload.residual_corg_pct
    if payload.ro_measurements_count is not None:
        batch.ro_measurements_count = payload.ro_measurements_count

    await recompute_batch_credit(
        session,
        batch,
        lab_h_corg=payload.lab_h_corg,
        lab_corg=payload.organic_carbon_pct,
    )
    await session.commit()
    return {
        "status": "ok",
        "batch_uuid": str(payload.batch_uuid),
        "provisional": batch.provisional,
    }


async def recompute_batch_credit(
    session: AsyncSession,
    batch: Batch,
    *,
    lab_h_corg: Optional[float] = None,
    lab_corg: Optional[float] = None,
) -> None:
    """Corroborate a batch's credit inputs from the telemetry/yield/application
    streams, recompute the LCA credit, and update the batch row in place.

    Pure derivation lives in corroboration.py; this is the thin DB glue. The
    caller commits. Idempotent — safe to call from create_batch and from every
    evidence endpoint so the credit converges as evidence arrives. A batch stays
    PROVISIONAL (never issued) until every input is corroborated.
    """
    buid = str(batch.batch_uuid)

    tel = (
        await session.execute(
            select(PyrolysisTelemetry).where(PyrolysisTelemetry.batch_uuid == buid)
        )
    ).scalar_one_or_none()
    yld = (
        await session.execute(
            select(YieldMetrics).where(YieldMetrics.batch_uuid == buid)
        )
    ).scalar_one_or_none()
    app_row = (
        await session.execute(
            select(EndUseApplication).where(EndUseApplication.batch_uuid == buid)
        )
    ).scalar_one_or_none()

    tel_payload = json.loads(tel.payload_json) if tel else None
    yld_payload = json.loads(yld.payload_json) if yld else None
    app_payload = json.loads(app_row.payload_json) if app_row else None

    # Phase 9-R: platform attestation. There is NO real Play Integrity / DeviceCheck
    # verifier yet, so a blob's presence proves nothing — we do not treat it as a
    # control (the old isinstance(dict) check was dead: the client sends a list).
    # SECURITY TODO: verify the attestation signature; until then it is unverified.
    attestation_blob = tel_payload.get("hw_attestation") if tel_payload else None
    attestation_verified = False  # TODO(security): real Play Integrity/DeviceCheck
    if attestation_blob and not attestation_verified:
        log.warning(
            "batch %s carries hw_attestation but it is NOT cryptographically "
            "verified (Play Integrity/DeviceCheck integration is a SECURITY TODO)",
            buid,
        )
    attestation_ok = True if not _ATTESTATION_ENFORCED else attestation_verified

    min_temp, _ = derive_min_temp(tel_payload)
    wet_yield, _ = derive_wet_yield(yld_payload)
    transport, _ = derive_transport_km(
        batch.latitude, batch.longitude, app_payload, haversine=haversine_km
    )

    # Rainbow C2: count photographed moisture readings and evaluate the ≥1/100 kg,
    # min-10 rule against the batch's biomass input.
    m_rows = (
        (
            await session.execute(
                select(MoistureReading).where(MoistureReading.batch_uuid == buid)
            )
        )
        .scalars()
        .all()
    )
    photographed = sum(
        1 for r in m_rows if json.loads(r.payload_json).get("sha256_hash")
    )
    moisture_ok, _ = derive_moisture_compliance(photographed, batch.biomass_input_kg)

    # Rainbow C4: count photographed composite pile sub-samples. Inert by default
    # (enforced at the C10 unified gate) so existing flows are unaffected.
    cs_rows = (
        (
            await session.execute(
                select(CompositePileSample).where(
                    CompositePileSample.batch_uuid == buid
                )
            )
        )
        .scalars()
        .all()
    )
    photographed_samples = sum(
        1 for r in cs_rows if json.loads(r.payload_json).get("sha256_hash")
    )
    composite_sample_ok, _ = derive_composite_sample_compliance(photographed_samples)

    # Rainbow C3/C3b: kiln-type-conditional pyrolysis-photo, flame-height and
    # ignition-energy compliance, read from the telemetry payload. Inert unless
    # kiln_type is explicitly 'open'/'closed'.
    kiln_type = tel_payload.get("kiln_type") if tel_payload else None
    photos_ok, flame_ok = derive_pyrolysis_photo_compliance(
        kiln_type,
        tel_payload.get("smoke_evidence") if tel_payload else None,
        tel_payload.get("flame_height_m") if tel_payload else None,
    )
    ignition_ok = derive_ignition_compliance(
        kiln_type,
        tel_payload.get("ignition_energy_type") if tel_payload else None,
    )

    # Rainbow C5: delivery record + buyer identity, read from the /application
    # payload. Inert by default (enforced at the C10 unified gate).
    delivery_ok, buyer_ok = derive_delivery_compliance(app_payload)

    # Rainbow C6: transport events. AUDIT-ONLY while TRANSPORT_EVENTS_ENFORCED is
    # False — we sum the per-leg fuel emissions and run a GPS-vs-reported
    # under-reporting cross-check, but neither touches the issued credit (the
    # GPS-haversine transport penalty in the LCA stays authoritative until the
    # methodology's real fuel emission factors are cited; see emission_factors.py).
    te_rows = (
        (
            await session.execute(
                select(TransportEvent).where(TransportEvent.batch_uuid == buid)
            )
        )
        .scalars()
        .all()
    )
    te_payloads = [json.loads(r.payload_json) for r in te_rows]
    transport_fuel_co2e_kg = sum(
        fuel_emissions_kg_co2e(p.get("fuel_type"), p.get("fuel_amount_litres"))
        for p in te_payloads
    )
    reported_transport_km = sum((p.get("distance_km") or 0.0) for p in te_payloads)
    # Cross-check: the GPS-derived transport (production→application haversine) is
    # a lower bound on real hauling; if the operator's REPORTED legs sum to far
    # less than the GPS distance, the fuel/transport burden is being under-stated.
    # Flag for review (audit-only) — never gates issuance here.
    gps_km = transport if transport is not None else 0.0
    transport_underreported = bool(
        te_payloads and gps_km > 0.0 and reported_transport_km < 0.5 * gps_km
    )

    effective_lab = lab_h_corg if lab_h_corg is not None else batch.lab_h_corg
    # C7: prefer a lab-measured organic-carbon fraction over the species constant.
    effective_corg = lab_corg if lab_corg is not None else batch.organic_carbon_pct
    corr = assemble(
        wet_yield,
        min_temp,
        transport,
        has_lab_hcorg=effective_lab is not None,
        has_lab_corg=effective_corg is not None,
        attestation_ok=attestation_ok,
        moisture_ok=moisture_ok,
        pyrolysis_photos_ok=photos_ok,
        flame_height_ok=flame_ok,
        ignition_ok=ignition_ok,
        composite_sample_ok=composite_sample_ok,
        delivery_ok=delivery_ok,
        buyer_ok=buyer_ok,
    )

    kwargs = {}
    if effective_lab is not None:
        kwargs["h_corg_ratio"] = effective_lab
    if effective_corg is not None:
        kwargs["corg_override"] = effective_corg

    lca = calculate_carbon_credit(
        wet_yield_kg=corr.wet_yield_kg if corr.wet_yield_kg is not None else 0.0,
        moisture_percent=batch.moisture_percent,
        min_recorded_temp_c=(
            corr.min_recorded_temp_c if corr.min_recorded_temp_c is not None else 0.0
        ),
        transport_distance_km=(
            corr.transport_distance_km
            if corr.transport_distance_km is not None
            else 0.0
        ),
        feedstock_species=batch.feedstock_species,
        **kwargs,
    )

    # Persist derived inputs (0.0 where uncorroborated; columns are NOT NULL).
    batch.wet_yield_kg = corr.wet_yield_kg if corr.wet_yield_kg is not None else 0.0
    batch.min_recorded_temp_c = (
        corr.min_recorded_temp_c if corr.min_recorded_temp_c is not None else 0.0
    )
    batch.transport_distance_km = (
        corr.transport_distance_km if corr.transport_distance_km is not None else 0.0
    )
    if lab_h_corg is not None:
        batch.lab_h_corg = lab_h_corg
    if lab_corg is not None:
        batch.organic_carbon_pct = lab_corg
    # Provisional if any input is uncorroborated OR H:Corg / Corg was assumed.
    batch.provisional = corr.provisional or lca.provisional or lca.corg_assumed
    batch.provisional_reasons = json.dumps(corr.reasons)
    batch.net_credit_t_co2e = lca.net_credit_t_co2e
    batch.lca_methodology_version = lca.methodology_version
    # Rainbow C6 audit trail (audit-only; not part of the signed credit while
    # transport events are unenforced — see emission_factors.TRANSPORT_EVENTS_ENFORCED).
    audit = {k: v for k, v in lca.__dict__.items()}
    audit["transport_events"] = {
        "enforced": TRANSPORT_EVENTS_ENFORCED,
        "event_count": len(te_payloads),
        "fuel_co2e_kg": transport_fuel_co2e_kg,
        "reported_transport_km": reported_transport_km,
        "gps_transport_km": gps_km,
        "underreported_flag": transport_underreported,
    }
    batch.lca_audit_json = json.dumps(audit)
    # Phase 8-R: only a fully-corroborated, non-provisional batch carries an
    # issuance signature. A provisional audit must never look issuable downstream.
    batch.lca_signature = (
        None
        if batch.provisional
        else sign_lca_audit(lca, _HMAC_SECRET, batch_uuid=str(batch.batch_uuid))
    )


async def _assert_batch_ownership(
    session: AsyncSession, batch_uuid_str: str, device_id: str
) -> None:
    """Reject evidence targeting a batch owned by a DIFFERENT device.

    Security (batch-ownership hardening): the evidence endpoints authenticate the
    caller but historically never checked that the caller owns the batch the
    evidence is anchored to. Because the credit is corroborated server-side from
    these streams (recompute_batch_credit), any enrolled device could otherwise
    inject telemetry/yield/application/moisture/composite rows into a victim's
    batch and move its credit. This mirrors the media handler's `not_your_batch`
    rule (upload_media).

    Policy:
      * batch exists AND is owned by another device  -> 403 not_your_batch
      * batch exists AND owned by this device         -> OK
      * batch owned by nobody yet (device_id NULL)    -> OK (legacy/unowned)
      * batch does NOT exist yet                      -> OK (evidence-first is a
        legitimate flow; create_batch establishes ownership from its own signed
        payload when it arrives, and drives the authoritative recompute then)

    A malformed batch_uuid is left for the endpoint's own persistence/validation
    to handle; it cannot match an existing owned batch, so it is not a bypass.
    """
    try:
        buid = uuid.UUID(batch_uuid_str)
    except (ValueError, AttributeError, TypeError):
        return
    batch = (
        await session.execute(select(Batch).where(Batch.batch_uuid == buid))
    ).scalar_one_or_none()
    if (
        batch is not None
        and batch.device_id is not None
        and batch.device_id != device_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not_your_batch"
        )


async def _upsert_one_to_one_evidence(
    session: AsyncSession,
    model,
    *,
    uuid_attr: str,
    uuid_value: str,
    batch_uuid: str,
    payload_json: str,
) -> dict:
    """Recover from an IntegrityError on a one-to-one evidence table
    (telemetry / yield / application: both `<x>_uuid` AND `batch_uuid` are UNIQUE).

    The commit can collide on either unique key, and the two cases mean different
    things:
      * same `<x>_uuid` again  -> a genuine idempotent retry of the SAME record.
        No-op; report duplicate. (Overwriting would be pointless and would reset
        received_at semantics.)
      * different `<x>_uuid`, same `batch_uuid` -> a CORRECTION / resubmission for
        the batch. Pre-fix this was silently dropped as `duplicate` — the batch
        kept the first (possibly attacker- or stale-) value and the real one was
        lost. Now we UPDATE the existing row in place so the corrected evidence
        wins and the credit re-derives from it.
      * `<x>_uuid` collides against a row on a DIFFERENT batch (pathological UUID
        reuse) -> there is no batch row to upsert; report duplicate rather than
        clobber another batch's record.

    The caller must have already rolled back the failed insert. Returns the JSON
    response body; caller commits + recomputes on the `updated` path.
    """
    await session.rollback()
    existing = (
        await session.execute(select(model).where(model.batch_uuid == batch_uuid))
    ).scalar_one_or_none()
    if existing is None or getattr(existing, uuid_attr) == uuid_value:
        # Same-record retry, or a cross-batch <x>_uuid clash we must not clobber.
        return {"status": "success", "duplicate": True}
    # Correction for this batch: overwrite the natural key + payload in place.
    setattr(existing, uuid_attr, uuid_value)
    existing.payload_json = payload_json
    await session.commit()
    await _recompute_if_batch_exists(session, batch_uuid)
    return {"status": "success", "updated": True}


async def _recompute_if_batch_exists(
    session: AsyncSession, batch_uuid_str: str
) -> None:
    """Recompute a batch's corroborated credit if the batch already exists.

    Called by the evidence endpoints so a batch's credit converges the moment its
    telemetry/yield/application lands. No-op if the batch hasn't arrived yet
    (create_batch will recompute when it does)."""
    try:
        buid = uuid.UUID(batch_uuid_str)
    except (ValueError, AttributeError, TypeError):
        return
    batch = (
        await session.execute(select(Batch).where(Batch.batch_uuid == buid))
    ).scalar_one_or_none()
    if batch is not None:
        await recompute_batch_credit(session, batch)
        await session.commit()


@app.post(
    "/api/v1/batches",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_batch(
    payload: BatchPayload,
    response: Response,
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
) -> BatchResponse:
    """
    Accept dMRV batch payload with idempotency.

    Returns 201 on first insert, 200 on duplicate (idempotent).
    Returns 422 if payload is malformed.
    """
    if not x_idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Idempotency-Key header is required and non-empty",
        )

    # Check for existing batch with same operation_id (idempotency)
    stmt = select(Batch).where(Batch.operation_id == x_idempotency_key)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        if existing.sha256_hash.lower() != payload.sha256_hash.lower() or str(
            existing.batch_uuid
        ) != str(payload.batch_uuid):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="operation_id_in_use_with_different_payload",
            )
        log.info(f"[batches] DUPLICATE operation_id={x_idempotency_key}")
        response.status_code = status.HTTP_200_OK
        return BatchResponse(
            batch_uuid=str(existing.batch_uuid),
            operation_id=existing.operation_id,
            status=existing.status,
            duplicate=True,
            received_at=existing.received_at,
            net_credit_t_co2e=existing.net_credit_t_co2e,
            provisional=existing.provisional,
        )

    # Plausibility: teleport / implausible-movement check against the device's
    # previous batch. (Credit inputs are corroborated separately, below.)
    if payload.latitude is not None and payload.longitude is not None:
        stmt_prev = (
            select(Batch)
            .where(Batch.device_id == device_id)
            .order_by(desc(Batch.harvest_timestamp))
            .limit(1)
        )
        prev = (await session.execute(stmt_prev)).scalar_one_or_none()

        if prev and prev.latitude is not None and prev.longitude is not None:
            dist_km = haversine_km(
                payload.longitude, payload.latitude, prev.longitude, prev.latitude
            )
            time_diff_hours = (
                abs(
                    (
                        payload.harvest_timestamp.replace(tzinfo=None)
                        - prev.harvest_timestamp.replace(tzinfo=None)
                    ).total_seconds()
                )
                / 3600.0
            )

            if time_diff_hours > 0:
                speed_kmh = dist_km / time_diff_hours
                if speed_kmh > 150.0:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="implausible_movement",
                    )

    # Build the batch from client-supplied fields only. The credit-bearing inputs
    # (wet_yield_kg, min_recorded_temp_c, transport_distance_km) and the net credit
    # are corroborated server-side by recompute_batch_credit; the batch stays
    # PROVISIONAL until every input is corroborated.
    batch = Batch(
        batch_uuid=payload.batch_uuid,
        operation_id=x_idempotency_key,
        feedstock_species=payload.feedstock_species,
        harvest_timestamp=payload.harvest_timestamp,
        moisture_percent=payload.moisture_percent,
        photo_path=payload.photo_path,
        sha256_hash=payload.sha256_hash,
        latitude=payload.latitude,
        longitude=payload.longitude,
        harvest_uptime_seconds=payload.harvest_uptime_seconds or 0,
        sourcing_uuid=payload.sourcing_uuid,
        moisture_compliant=payload.moisture_compliant,
        mock_location_enabled=payload.mock_location_enabled,
        azimuth=payload.azimuth,
        pitch=payload.pitch,
        roll=payload.roll,
        biomass_input_kg=payload.biomass_input_kg,
        biomass_measurement_method=payload.biomass_measurement_method,
        device_id=device_id,
        status="RECEIVED",
    )

    # Credit inputs (incl. lab H:Corg) are corroborated server-side; a fresh batch
    # has no lab value, so it stays PROVISIONAL until /admin/lab-hcorg supplies one.
    await recompute_batch_credit(session, batch)

    session.add(batch)
    try:
        await session.commit()
        await session.refresh(batch)
    except IntegrityError:
        # Race condition: another request beat us
        await session.rollback()
        stmt = select(Batch).where(Batch.batch_uuid == payload.batch_uuid)
        result = await session.execute(stmt)
        batch = result.scalar_one()

        batch_sha = batch.sha256_hash.lower() if batch.sha256_hash else None
        payload_sha = payload.sha256_hash.lower() if payload.sha256_hash else None

        if batch_sha != payload_sha or batch.operation_id != x_idempotency_key:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="race_resolved_with_different_payload",
            )
        log.info(f"[batches] RACE-RESOLVED batch_uuid={payload.batch_uuid}")
        response.status_code = status.HTTP_200_OK
        return BatchResponse(
            batch_uuid=str(batch.batch_uuid),
            operation_id=batch.operation_id,
            status=batch.status,
            duplicate=True,
            received_at=batch.received_at,
            net_credit_t_co2e=batch.net_credit_t_co2e,
            provisional=batch.provisional,
        )

    if payload.sha256_hash:
        # A batch asserting a photo is UNVERIFIED until a photo whose hash
        # matches (and whose EXIF GPS corroborates) is anchored. If the photo
        # already arrived (media-first), evaluate it now.
        stmt = select(MediaFile).where(MediaFile.batch_uuid == batch.batch_uuid)
        media = (await session.execute(stmt)).scalars().first()
        batch.status = "UNVERIFIED"
        if media:
            _evaluate_anchor(batch, media.sha256_hash, media.exif_lat, media.exif_lon)
        await session.commit()

    log.info(
        f"[batches] STORED batch_uuid={batch.batch_uuid} operation_id={x_idempotency_key}"
    )
    return BatchResponse(
        batch_uuid=str(batch.batch_uuid),
        operation_id=batch.operation_id,
        status=batch.status,
        duplicate=False,
        received_at=batch.received_at,
        net_credit_t_co2e=batch.net_credit_t_co2e,
        provisional=batch.provisional,
    )


@app.post(
    "/api/v1/media",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_media(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
    x_declared_sha256: str = Header(..., alias="X-Declared-SHA256"),
    x_batch_uuid: str = Header(..., alias="X-Batch-UUID"),
    x_device_id: str = Header(..., alias="X-Device-Id"),
    device_id: str = Depends(verify_media_signature),
    session: AsyncSession = Depends(get_session),
) -> MediaUploadResponse:
    """
    Upload media file with SHA-256 verification.

    Phase 9: the client-supplied ``X-Mock-Location`` header is no longer an
    access control (it was honor-system). Mock-location is recorded as a review
    signal (``mock_location_enabled`` on the batch) and corroborated server-side
    via photo EXIF GPS and the teleport check.
    """
    if not x_idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Idempotency-Key header is required",
        )

    if x_device_id and not re.match(r"^[\w\-]+$", x_device_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_device_id"
        )

    if not x_declared_sha256.strip() or len(x_declared_sha256) != 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Declared-SHA256 header must be 64-character hex string",
        )

    stmt = select(MediaFile).where(MediaFile.operation_id == x_idempotency_key)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        if existing.sha256_hash.lower() != x_declared_sha256.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="operation_id_in_use_with_different_payload",
            )
        log.info(f"[media] DUPLICATE operation_id={x_idempotency_key}")
        response.status_code = status.HTTP_200_OK
        return MediaUploadResponse(
            server_sha256=existing.sha256_hash,
            stored=True,
            file_path=Path(existing.file_path).name,
        )

    MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
    CHUNK = 64 * 1024
    hasher = hashlib.sha256()
    buf = bytearray()
    total = 0
    while True:
        chunk = await file.read(CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="file_too_large")
        hasher.update(chunk)
        buf.extend(chunk)
    content = bytes(buf)
    calculated_hash = hasher.hexdigest()

    if calculated_hash.lower() != x_declared_sha256.lower():
        log.warning(
            f"[media] SHA256 MISMATCH declared={x_declared_sha256[:8]} calculated={calculated_hash[:8]}"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="sha256_mismatch"
        )

    _SAFE = re.compile(r"^[A-Za-z0-9_\-]{1,128}$")

    def _safe_device(s: str) -> str:
        if not _SAFE.match(s or ""):
            raise HTTPException(status_code=400, detail="invalid_device_id")
        return s

    def _safe_op(s: str) -> str:
        if not _SAFE.match(s or ""):
            raise HTTPException(status_code=400, detail="invalid_operation_id")
        return s

    device = _safe_device(x_device_id)
    op = _safe_op(x_idempotency_key)
    target_dir = UPLOAD_DIR / device
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / f"{op}.bin"

    if not file_path.resolve().is_relative_to(UPLOAD_DIR.resolve()):
        raise HTTPException(status_code=400, detail="path_traversal")

    with open(file_path, "wb") as f:
        f.write(content)

    # Phase 9: extract GPS from the photo's EXIF for server-side corroboration.
    exif_lat, exif_lon = _parse_exif_gps(content)

    media = MediaFile(
        operation_id=x_idempotency_key,
        file_path=str(file_path),
        sha256_hash=calculated_hash,
        filename=file.filename,
        exif_lat=exif_lat,
        exif_lon=exif_lon,
    )

    session.add(media)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        stmt = select(MediaFile).where(MediaFile.operation_id == x_idempotency_key)
        result = await session.execute(stmt)
        media = result.scalar_one()

    # Phase 15-A: parse the batch UUID safely (malformed → 400, not a 500) and
    # bind ownership — only the device that owns the batch may anchor evidence to it.
    try:
        batch_uuid = uuid.UUID(x_batch_uuid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="invalid_batch_uuid")
    media.batch_uuid = batch_uuid

    # Anchor photo to batch if batch was already created (P0-25). The photo only
    # verifies the batch if its hash matches the batch's declared sha256_hash,
    # and the EXIF GPS corroborates the claimed coordinates (Phase 9).
    stmt = select(Batch).where(Batch.batch_uuid == batch_uuid)
    batch_result = await session.execute(stmt)
    batch = batch_result.scalar_one_or_none()
    if batch:
        if batch.device_id is not None and batch.device_id != device_id:
            raise HTTPException(status_code=403, detail="not_your_batch")
        _evaluate_anchor(batch, calculated_hash, exif_lat, exif_lon)
        session.add(batch)

    session.add(media)
    await session.commit()

    log.info(f"[media] STORED file={file.filename} sha256={calculated_hash}")
    response.status_code = status.HTTP_200_OK
    return MediaUploadResponse(
        server_sha256=calculated_hash,
        stored=True,
        file_path=file_path.name,
    )


def _assert_same_uuid(*, expected: str, **kwargs: str) -> None:
    """Raise 422 if any value in kwargs differs from expected."""
    for name, value in kwargs.items():
        if value != expected:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"batch_uuid mismatch: {name}={value} expected={expected}",
            )


# ==================== Evidence-endpoint schemas (Phase 11) ====================
# Strict schemas + size bounds for the previously-`dict` side-endpoints. Identity
# fields are required; the rest are optional (accepts the real client and minimal
# test payloads). `extra="forbid"` rejects unknown keys; lists are bounded. The
# canonical field names MUST match the Dart writers and what corroboration.py reads
# (temperature_readings / wet_yield_weight_kg / latitude / longitude) — changing
# them silently breaks credit corroboration.


# Phase 11-R: free-text string fields are length-bounded so a single huge string
# cannot slip past the array bounds. Identifiers/short text -> 128, paths -> 512,
# timestamps -> 64, hex hashes -> 64.
class TelemetryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    telemetry_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    kiln_gross_capacity: Optional[float] = None
    burn_start_timestamp: Optional[str] = Field(None, max_length=64)
    burn_end_timestamp: Optional[str] = Field(None, max_length=64)
    min_temp: Optional[float] = None
    max_temp: Optional[float] = None
    temperature_readings: Optional[list[float]] = Field(None, max_length=100_000)
    smoke_evidence: Optional[list[dict]] = Field(None, max_length=1_000)
    hw_attestation: Optional[list] = Field(None, max_length=1_000)
    # Rainbow compliance C0: kiln type/id (persisted in payload_json).
    kiln_type: Optional[Literal["open", "closed"]] = None
    kiln_id: Optional[str] = Field(None, max_length=128)
    # Rainbow compliance C3 (open-kiln) / C3b (closed-kiln); read from payload_json
    # by recompute_batch_credit for kiln-type-conditional compliance.
    flame_height_m: Optional[float] = Field(None, ge=0.0, le=5.0)
    ignition_energy_type: Optional[str] = Field(None, max_length=128)
    ignition_energy_amount: Optional[float] = Field(None, ge=0.0)

    @field_validator("temperature_readings")
    @classmethod
    def _validate_temp_range(cls, v: Optional[list[float]]) -> Optional[list[float]]:
        # Phase 15-C: every reading must be physically plausible so a fabricated
        # constant array can't inflate the burn-quality (CH4) gate with absurd values.
        if v is not None and any((t < -50.0 or t > 1500.0) for t in v):
            raise ValueError("temperature_readings values must be in [-50, 1500] C")
        return v


class YieldPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yield_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    quench_methodology: Optional[str] = Field(None, max_length=128)
    gross_volume: Optional[float] = None
    # Phase 15-C: hard upper bound so a single self-asserted field can't linearly
    # inflate the credit to arbitrary size (100 t/batch ceiling — confirm vs real
    # kiln throughput). A kiln-capacity cross-check remains a documented follow-up.
    wet_yield_weight_kg: Optional[float] = Field(None, gt=0.0, le=100_000.0)
    dry_yield_weight_kg: Optional[float] = Field(None, ge=0.0, le=100_000.0)


class MetadataPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_uuid: str = Field(..., max_length=64)
    artisan_id: Optional[str] = Field(None, max_length=128)
    device_hardware_mac: Optional[str] = Field(None, max_length=128)
    app_build_version: Optional[str] = Field(None, max_length=128)
    sync_status: Optional[str] = Field(None, max_length=64)
    created_at: Optional[str] = Field(None, max_length=64)


class ApplicationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    application_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    application_methodology: Optional[str] = Field(None, max_length=128)
    application_rate_tonnes: Optional[float] = None
    transport_distance_km: Optional[float] = Field(None, ge=0.0, le=20000.0)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    farmer_photo_path: Optional[str] = Field(None, max_length=512)
    farmer_photo_sha256: Optional[str] = Field(None, max_length=64)
    # Rainbow compliance C5: delivery record + buyer/end-user identity.
    # Persisted in payload_json (no server column); read by
    # derive_delivery_compliance in recompute_batch_credit.
    delivery_date: Optional[str] = Field(None, max_length=64)
    delivered_amount_kg: Optional[float] = Field(None, ge=0.0, le=100_000.0)
    buyer_name: Optional[str] = Field(None, max_length=256)
    buyer_contact: Optional[str] = Field(None, max_length=256)


class MoisturePayload(BaseModel):
    # Rainbow compliance C2: one moisture-meter reading (many per batch).
    model_config = ConfigDict(extra="forbid")
    reading_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    moisture_percent: float = Field(..., ge=0.0, le=100.0)
    sequence: int = Field(..., ge=1)
    photo_path: Optional[str] = Field(None, max_length=512)
    sha256_hash: Optional[str] = Field(None, min_length=64, max_length=64)


class CompositeSamplePayload(BaseModel):
    # Rainbow compliance C4: one site composite pile sub-sample (many per batch).
    model_config = ConfigDict(extra="forbid")
    sample_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    sampled_at: Optional[str] = Field(None, max_length=64)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    kiln_qr: Optional[str] = Field(None, max_length=128)
    batch_qr: Optional[str] = Field(None, max_length=128)
    photo_path: Optional[str] = Field(None, max_length=512)
    sha256_hash: Optional[str] = Field(None, min_length=64, max_length=64)


class TransportEventPayload(BaseModel):
    # Rainbow compliance C6: one transport leg (many per batch).
    model_config = ConfigDict(extra="forbid")
    event_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    material: Literal["biomass", "biochar"]
    distance_km: Optional[float] = Field(None, ge=0.0, le=20000.0)
    weight_kg: Optional[float] = Field(None, ge=0.0, le=1_000_000.0)
    vehicle_type: Optional[str] = Field(None, max_length=128)
    fuel_type: Optional[str] = Field(None, max_length=64)
    fuel_amount_litres: Optional[float] = Field(None, ge=0.0, le=100_000.0)
    occurred_at: Optional[str] = Field(None, max_length=64)


@app.post("/api/v1/moisture", status_code=status.HTTP_201_CREATED)
async def create_moisture(
    payload: MoisturePayload,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
):
    await _assert_batch_ownership(session, payload.batch_uuid, device_id)
    row = MoistureReading(
        reading_uuid=payload.reading_uuid,
        batch_uuid=payload.batch_uuid,
        payload_json=json.dumps(payload.model_dump(mode="json")),
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return {"status": "success", "duplicate": True}
    # New reading may satisfy the moisture-sample-count compliance rule.
    await _recompute_if_batch_exists(session, payload.batch_uuid)
    return {"status": "success", "duplicate": False}


@app.post("/api/v1/composite-sample", status_code=status.HTTP_201_CREATED)
async def create_composite_sample(
    payload: CompositeSamplePayload,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
):
    await _assert_batch_ownership(session, payload.batch_uuid, device_id)
    row = CompositePileSample(
        sample_uuid=payload.sample_uuid,
        batch_uuid=payload.batch_uuid,
        payload_json=json.dumps(payload.model_dump(mode="json")),
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return {"status": "success", "duplicate": True}
    # New sub-sample may satisfy the C4 composite-sample compliance rule.
    await _recompute_if_batch_exists(session, payload.batch_uuid)
    return {"status": "success", "duplicate": False}


@app.post("/api/v1/transport", status_code=status.HTTP_201_CREATED)
async def create_transport_event(
    payload: TransportEventPayload,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
):
    await _assert_batch_ownership(session, payload.batch_uuid, device_id)
    row = TransportEvent(
        event_uuid=payload.event_uuid,
        batch_uuid=payload.batch_uuid,
        payload_json=json.dumps(payload.model_dump(mode="json")),
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return {"status": "success", "duplicate": True}
    # Recompute so the (audit-only until enforced) transport emissions + the
    # GPS-vs-reported cross-check refresh as legs arrive.
    await _recompute_if_batch_exists(session, payload.batch_uuid)
    return {"status": "success", "duplicate": False}


@app.post("/api/v1/telemetry", status_code=status.HTTP_201_CREATED)
async def create_telemetry(
    payload: TelemetryPayload,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
):
    await _assert_batch_ownership(session, payload.batch_uuid, device_id)
    payload_json = json.dumps(payload.model_dump(mode="json"))
    row = PyrolysisTelemetry(
        telemetry_uuid=payload.telemetry_uuid,
        batch_uuid=payload.batch_uuid,
        payload_json=payload_json,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        return await _upsert_one_to_one_evidence(
            session,
            PyrolysisTelemetry,
            uuid_attr="telemetry_uuid",
            uuid_value=payload.telemetry_uuid,
            batch_uuid=payload.batch_uuid,
            payload_json=payload_json,
        )
    await _recompute_if_batch_exists(session, payload.batch_uuid)
    return {"status": "success", "duplicate": False}


@app.post("/api/v1/yield", status_code=status.HTTP_201_CREATED)
async def create_yield(
    payload: YieldPayload,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
):
    await _assert_batch_ownership(session, payload.batch_uuid, device_id)
    payload_json = json.dumps(payload.model_dump(mode="json"))
    row = YieldMetrics(
        yield_uuid=payload.yield_uuid,
        batch_uuid=payload.batch_uuid,
        payload_json=payload_json,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        return await _upsert_one_to_one_evidence(
            session,
            YieldMetrics,
            uuid_attr="yield_uuid",
            uuid_value=payload.yield_uuid,
            batch_uuid=payload.batch_uuid,
            payload_json=payload_json,
        )
    await _recompute_if_batch_exists(session, payload.batch_uuid)
    return {"status": "success", "duplicate": False}


@app.post("/api/v1/metadata", status_code=status.HTTP_201_CREATED)
async def create_metadata(
    payload: MetadataPayload,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
):
    await _assert_batch_ownership(session, payload.batch_uuid, device_id)
    payload_json = json.dumps(payload.model_dump(mode="json"))
    row = SystemMetadata(batch_uuid=payload.batch_uuid, payload_json=payload_json)
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        # 16D: metadata is keyed by batch_uuid; a repeat POST is a status UPDATE
        # (e.g. closeBatch → CLOSED_PENDING_UPLOAD), not a no-op. Upsert the latest
        # signed payload so batch-close events actually propagate to the server.
        await session.rollback()
        existing = (
            await session.execute(
                select(SystemMetadata).where(
                    SystemMetadata.batch_uuid == payload.batch_uuid
                )
            )
        ).scalar_one()
        existing.payload_json = payload_json
        await session.commit()
        return {"status": "success", "updated": True}
    return {"status": "success", "duplicate": False}


@app.post("/api/v1/application", status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationPayload,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
):
    await _assert_batch_ownership(session, payload.batch_uuid, device_id)
    payload_json = json.dumps(payload.model_dump(mode="json"))
    row = EndUseApplication(
        application_uuid=payload.application_uuid,
        batch_uuid=payload.batch_uuid,
        payload_json=payload_json,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        return await _upsert_one_to_one_evidence(
            session,
            EndUseApplication,
            uuid_attr="application_uuid",
            uuid_value=payload.application_uuid,
            batch_uuid=payload.batch_uuid,
            payload_json=payload_json,
        )
    # Transport distance is derived from this application's GPS inside
    # recompute_batch_credit (see corroboration.derive_transport_km).
    await _recompute_if_batch_exists(session, payload.batch_uuid)
    return {"status": "success", "duplicate": False}


# ==================== C8: project registry (admin) ====================
# Project-setup data (once / updated on change): kilns, operator training,
# supervisor visits, scale calibrations. Admin-authenticated (project console,
# NOT the per-run field app). The compliance reasons these enable
# (unregistered_kiln / scale_calibration_expired) are DEFERRED to the C10 unified
# gate — C8 lands the registry only, so no batch's issuance changes here.


def _require_admin(x_admin_secret: str) -> None:
    if not hmac.compare_digest(x_admin_secret, _ADMIN_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp to an aware UTC datetime, or 400 on garbage."""
    if s is None:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="invalid_timestamp")
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class KilnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kiln_id: str = Field(..., min_length=1, max_length=128)
    material: Optional[str] = Field(None, max_length=128)
    weight_kg: Optional[float] = Field(None, ge=0.0, le=1_000_000.0)
    lifetime_years: Optional[float] = Field(None, ge=0.0, le=200.0)
    kiln_type: Optional[Literal["open", "closed"]] = None


class OperatorTrainingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_uuid: str = Field(..., max_length=64)
    operator_id: Optional[str] = Field(None, max_length=128)
    training_type: Optional[str] = Field(None, max_length=128)
    completed_at: Optional[str] = Field(None, max_length=64)
    report_sha256: Optional[str] = Field(None, min_length=64, max_length=64)


class SupervisorVisitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visit_uuid: str = Field(..., max_length=64)
    kiln_id: Optional[str] = Field(None, max_length=128)
    visited_at: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = Field(None, max_length=2000)
    report_sha256: Optional[str] = Field(None, min_length=64, max_length=64)


class ScaleCalibrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    calibration_uuid: str = Field(..., max_length=64)
    scale_id: Optional[str] = Field(None, max_length=128)
    calibrated_at: Optional[str] = Field(None, max_length=64)
    valid_until: Optional[str] = Field(None, max_length=64)
    report_sha256: Optional[str] = Field(None, min_length=64, max_length=64)


@app.post("/api/v1/admin/kiln", status_code=status.HTTP_200_OK)
async def register_kiln(
    payload: KilnRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    """Register/update a project kiln (C8). Upsert by kiln_id — the methodology
    says kiln data is captured once and updated when kilns change."""
    _require_admin(x_admin_secret)
    existing = (
        await session.execute(select(Kiln).where(Kiln.kiln_id == payload.kiln_id))
    ).scalar_one_or_none()
    extra = payload.model_dump(mode="json")
    if existing is None:
        session.add(
            Kiln(
                kiln_id=payload.kiln_id,
                material=payload.material,
                weight_kg=payload.weight_kg,
                lifetime_years=payload.lifetime_years,
                kiln_type=payload.kiln_type,
                payload_json=json.dumps(extra),
            )
        )
        await session.commit()
        return {"status": "ok", "kiln_id": payload.kiln_id, "updated": False}
    existing.material = payload.material
    existing.weight_kg = payload.weight_kg
    existing.lifetime_years = payload.lifetime_years
    existing.kiln_type = payload.kiln_type
    existing.payload_json = json.dumps(extra)
    await session.commit()
    return {"status": "ok", "kiln_id": payload.kiln_id, "updated": True}


@app.post("/api/v1/admin/operator-training", status_code=status.HTTP_201_CREATED)
async def register_operator_training(
    payload: OperatorTrainingRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(x_admin_secret)
    session.add(
        OperatorTraining(
            record_uuid=payload.record_uuid,
            operator_id=payload.operator_id,
            payload_json=json.dumps(payload.model_dump(mode="json")),
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return {"status": "ok", "duplicate": True}
    return {"status": "ok", "duplicate": False}


@app.post("/api/v1/admin/supervisor-visit", status_code=status.HTTP_201_CREATED)
async def register_supervisor_visit(
    payload: SupervisorVisitRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(x_admin_secret)
    session.add(
        SupervisorVisit(
            visit_uuid=payload.visit_uuid,
            kiln_id=payload.kiln_id,
            report_sha256=payload.report_sha256,
            payload_json=json.dumps(payload.model_dump(mode="json")),
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return {"status": "ok", "duplicate": True}
    return {"status": "ok", "duplicate": False}


@app.post("/api/v1/admin/scale-calibration", status_code=status.HTTP_201_CREATED)
async def register_scale_calibration(
    payload: ScaleCalibrationRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(x_admin_secret)
    # Parse the validity window so the C10 gate can check in-date calibration.
    calibrated_at = _parse_dt(payload.calibrated_at)
    valid_until = _parse_dt(payload.valid_until)
    session.add(
        ScaleCalibration(
            calibration_uuid=payload.calibration_uuid,
            scale_id=payload.scale_id,
            calibrated_at=calibrated_at,
            valid_until=valid_until,
            report_sha256=payload.report_sha256,
            payload_json=json.dumps(payload.model_dump(mode="json")),
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return {"status": "ok", "duplicate": True}
    return {"status": "ok", "duplicate": False}


# ==================== C9: annual verification (admin) ====================
# Annual / per-verification project inputs, keyed by (project_id, year). Admin-
# authenticated. DATA CAPTURE only: the credit-affecting fields (methane rate →
# CH4 penalty; conversion_factor → C1 yield_conversion) are NOT wired into the
# credit here — that needs methodology sign-off and its own gated phase (same
# discipline as C6 transport). Compliance reasons (missing_annual_methane /
# missing_pah) are deferred to the C10 unified gate.


class AnnualVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(..., min_length=1, max_length=128)
    year: int = Field(..., ge=2000, le=2100)
    # Methane emission rate over >= 3 representative runs (independent provider).
    methane_rate_g_per_kg: Optional[float] = Field(None, ge=0.0, le=100_000.0)
    methane_run_count: Optional[int] = Field(None, ge=0)
    # Biomass->biochar conversion factor (if not directly weighing biomass).
    conversion_factor: Optional[float] = Field(None, gt=0.0, le=100.0)
    pah_measured: Optional[bool] = None
    heavy_metals_measured: Optional[bool] = None
    leakage_assessment_done: Optional[bool] = None
    dry_bulk_density: Optional[float] = Field(None, gt=0.0, le=2000.0)
    quality_oversight_sha256: Optional[str] = Field(None, min_length=64, max_length=64)
    report_sha256: Optional[str] = Field(None, min_length=64, max_length=64)


@app.post("/api/v1/admin/annual-verification", status_code=status.HTTP_200_OK)
async def register_annual_verification(
    payload: AnnualVerificationRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    """Register/update the annual verification record for a (project_id, year).
    Upsert — the methodology captures these annually / when feedstock changes, so
    a re-POST for the same project-year updates the existing record."""
    _require_admin(x_admin_secret)
    existing = (
        await session.execute(
            select(AnnualVerification).where(
                AnnualVerification.project_id == payload.project_id,
                AnnualVerification.year == payload.year,
            )
        )
    ).scalar_one_or_none()
    fields = dict(
        methane_rate_g_per_kg=payload.methane_rate_g_per_kg,
        methane_run_count=payload.methane_run_count,
        conversion_factor=payload.conversion_factor,
        pah_measured=payload.pah_measured,
        heavy_metals_measured=payload.heavy_metals_measured,
        leakage_assessment_done=payload.leakage_assessment_done,
        dry_bulk_density=payload.dry_bulk_density,
        quality_oversight_sha256=payload.quality_oversight_sha256,
        report_sha256=payload.report_sha256,
    )
    payload_json = json.dumps(payload.model_dump(mode="json"))
    if existing is None:
        session.add(
            AnnualVerification(
                project_id=payload.project_id,
                year=payload.year,
                payload_json=payload_json,
                **fields,
            )
        )
        await session.commit()
        return {
            "status": "ok",
            "project_id": payload.project_id,
            "year": payload.year,
            "updated": False,
        }
    for k, v in fields.items():
        setattr(existing, k, v)
    existing.payload_json = payload_json
    await session.commit()
    return {
        "status": "ok",
        "project_id": payload.project_id,
        "year": payload.year,
        "updated": True,
    }
