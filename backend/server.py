"""Kon-Tiki Biochar dMRV — FastAPI microservice with PostgreSQL.

Endpoints:
  POST /api/v1/batches  - Receive dMRV payload with idempotency
  POST /api/v1/media    - Upload media with SHA-256 verification
  GET  /api/health      - Health check
"""
from __future__ import annotations

import hmac
import hashlib
import logging
import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Literal
from contextlib import asynccontextmanager
from pydantic import ConfigDict
from uuid import UUID

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile, status, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session, init_db
from models import Batch, MediaFile, DeviceKey, PyrolysisTelemetry, YieldMetrics, EndUseApplication, SystemMetadata
from lca_engine import calculate_carbon_credit, sign_lca_audit

_HMAC_SECRET = os.environ.get("DMRV_HMAC_SECRET")
if not _HMAC_SECRET:
    raise RuntimeError("DMRV_HMAC_SECRET env var is required.")

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
    allow_headers=["Authorization", "Content-Type", "X-Device-Id", "X-Idempotency-Key", "X-Payload-Sha256", "X-Hmac-Signature"],
)

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

    # --- LCA inputs (Prompt 8) ---
    wet_yield_kg: float = Field(100.0, gt=0.0, description="BLE crane scale reading")
    min_recorded_temp_c: float = Field(0.0, ge=-50.0, le=1500.0, description="Min temp from BLE thermocouple array")
    transport_distance_km: float = Field(0.0, ge=0.0, le=20000.0, description="GPS Haversine distance to application field")

    @field_validator("feedstock_species")
    @classmethod
    def validate_feedstock(cls, v: str) -> str:
        from lca_engine import CORG_TABLE
        if v not in CORG_TABLE:
            raise ValueError(f"feedstock_species must be one of {list(CORG_TABLE.keys())}")
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

    @model_validator(mode="after")
    def _validate_burn_compliance(self) -> "BatchPayload":
        # If a burn temp is being asserted (>0), enforce a defensible floor
        # and require the moisture invariant the LCA assumes.
        if self.min_recorded_temp_c > 0.0:
            if self.min_recorded_temp_c < 100.0:
                # No real Kon-Tiki burn ever measures below 100 C anywhere
                # near the thermocouple. A 1-sample fake is the dominant cause.
                raise ValueError(
                    "min_recorded_temp_c < 100 C; provide the full "
                    "temperature_readings log (>= 60 samples) instead."
                )
        return self

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    lab_h_corg: Optional[float] = Field(None, description="Lab-measured H:Corg ratio")


class BatchResponse(BaseModel):
    batch_uuid: str
    operation_id: str
    status: str
    duplicate: bool
    received_at: datetime
    net_credit_t_co2e: Optional[float] = None


class MediaUploadResponse(BaseModel):
    server_sha256: str
    stored: bool
    file_path: str


class RegistrationRequest(BaseModel):
    device_id: str = Field(..., min_length=1)
    hmac_key: str = Field(..., min_length=40, max_length=64)

class RegistrationResponse(BaseModel):
    status: str
    device_id: str

# ==================== Endpoints ====================\n
@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "dmrv-api",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


async def verify_hmac(
    request: Request,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    x_hmac_signature: Optional[str] = Header(None, alias="X-HMAC-Signature"),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> str:

    if not x_hmac_signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_signature")

    raw_body = await request.body()

    if not x_device_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="unknown_device")

    stmt = select(DeviceKey).where(DeviceKey.device_id == x_device_id)
    result = await session.execute(stmt)
    device = result.scalar_one_or_none()
    if not device:
        log.error(f"HMAC Error: unknown_device '{x_device_id}'")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="unknown_device")

    import base64
    try:
        padding = '=' * (4 - (len(device.hmac_key) % 4))
        secret = base64.urlsafe_b64decode(device.hmac_key + padding)    # Standardize on base64url-encoded 32-byte raw keys
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="invalid_key_format")

    method = request.method.upper()
    path = request.url.path
    op_id = x_idempotency_key or ""
    body_hash = hashlib.sha256(raw_body).hexdigest()
    dev_id = x_device_id or ""
    canonical = "\n".join([method, path, op_id, body_hash, dev_id]).encode('utf-8')

    calculated = hmac.new(secret, canonical, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated.lower(), x_hmac_signature.lower()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="hmac_mismatch")
    
    return x_device_id

from models import EnrollmentToken

@app.post("/api/v1/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    payload: RegistrationRequest,
    x_enrollment_token: Optional[str] = Header(None, alias="X-Enrollment-Token"),
    session: AsyncSession = Depends(get_session)
):
    if not x_enrollment_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="enrollment_token_required")

    token_stmt = select(EnrollmentToken).where(EnrollmentToken.token == x_enrollment_token)
    token_res = await session.execute(token_stmt)
    db_token = token_res.scalar_one_or_none()

    if not db_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_enrollment_token")
    if db_token.used_at:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="enrollment_token_used")
    if db_token.expires_at:
        expires = db_token.expires_at.replace(tzinfo=timezone.utc) if db_token.expires_at.tzinfo is None else db_token.expires_at
        if expires < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="enrollment_token_expired")

    stmt = select(DeviceKey).where(DeviceKey.device_id == payload.device_id)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="device_already_registered")
    
    new_key = DeviceKey(device_id=payload.device_id, hmac_key=payload.hmac_key)
    session.add(new_key)
    
    if db_token.token != "dev-token":
        db_token.used_at = datetime.now(timezone.utc)
    
    await session.commit()
    log.info(f"[register] Device {payload.device_id} registered successfully with token.")
    return RegistrationResponse(status="registered", device_id=payload.device_id)

class MintTokenRequest(BaseModel):
    token: str
    expires_in_days: int = 7

@app.post("/api/v1/admin/mint-token", status_code=status.HTTP_201_CREATED)
async def mint_enrollment_token(
    payload: MintTokenRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session)
):
    import hmac
    if not hmac.compare_digest(x_admin_secret, _HMAC_SECRET):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
        
    from datetime import timedelta
    expires = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
    new_token = EnrollmentToken(token=payload.token, expires_at=expires)
    session.add(new_token)
    
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="token_already_exists")
        
    return {"status": "minted", "token": payload.token, "expires_at": expires.isoformat()}


@app.post(
    "/api/v1/batches",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_batch(
    payload: BatchPayload,
    response: Response,
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
    device_id: str = Depends(verify_hmac),
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
            detail="X-Idempotency-Key header is required and non-empty"
        )

    # Check for existing batch with same operation_id (idempotency)
    stmt = select(Batch).where(Batch.operation_id == x_idempotency_key)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        if (existing.sha256_hash.lower() != payload.sha256_hash.lower()
            or str(existing.batch_uuid) != str(payload.batch_uuid)):
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
        )

    import json
    
    # 1. Fetch Telemetry
    stmt_tel = select(PyrolysisTelemetry).where(PyrolysisTelemetry.batch_uuid == str(payload.batch_uuid))
    telemetry = (await session.execute(stmt_tel)).scalar_one_or_none()
    
    min_temp = 0.0
    if telemetry:
        tel_data = json.loads(telemetry.payload_json)
        readings = tel_data.get("temperatureReadingsJson", [])
        if len(readings) >= 60:
            min_temp = min(readings)
        else:
            if payload.min_recorded_temp_c > 0.0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="missing_qualifying_telemetry_log"
                )
            
        attestation = tel_data.get("hwAttestationJson")
        if attestation:
            # Here we would verify Play Integrity / DeviceCheck
            # For now, we reject if it's explicitly marked as invalid
            if isinstance(attestation, dict) and attestation.get("status") == "INVALID":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid_platform_attestation")
    else:
        if payload.min_recorded_temp_c > 0.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="missing_qualifying_telemetry_log"
            )

    # 2. Teleport Check & Plausibility
    if payload.latitude is not None and payload.longitude is not None:
        from sqlalchemy import desc
        stmt_prev = (select(Batch)
                     .where(Batch.device_id == device_id)
                     .order_by(desc(Batch.harvest_timestamp))
                     .limit(1))
        prev = (await session.execute(stmt_prev)).scalar_one_or_none()
        
        if prev and prev.latitude is not None and prev.longitude is not None:
            from math import radians, cos, sin, asin, sqrt
            def haversine(lon1, lat1, lon2, lat2):
                lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a))
                return 6371 * c
                
            dist_km = haversine(payload.longitude, payload.latitude, prev.longitude, prev.latitude)
            time_diff_hours = abs((payload.harvest_timestamp.replace(tzinfo=None) - prev.harvest_timestamp.replace(tzinfo=None)).total_seconds()) / 3600.0
            
            if time_diff_hours > 0:
                speed_kmh = dist_km / time_diff_hours
                if speed_kmh > 150.0:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="implausible_movement")

    # Calculate LCA carbon credit (8-step CSI pipeline)
    # Task 3.4 Cross-check transport distance
    stmt_app = select(EndUseApplication).where(EndUseApplication.batch_uuid == str(payload.batch_uuid))
    app_row = (await session.execute(stmt_app)).scalar_one_or_none()
    if app_row and payload.latitude is not None and payload.longitude is not None:
        app_payload = json.loads(app_row.payload_json)
        app_lat = app_payload.get("latitude")
        app_lon = app_payload.get("longitude")
        if app_lat is not None and app_lon is not None:
            min_dist = haversine(app_lon, app_lat, payload.longitude, payload.latitude)
            # Apply a 10% tolerance for GPS inaccuracy/rounding
            if payload.transport_distance_km < min_dist * 0.9:
                payload.transport_distance_km = min_dist
                
    kwargs = {}
    if payload.lab_h_corg is not None:
        kwargs["h_corg_ratio"] = payload.lab_h_corg

    lca = calculate_carbon_credit(
        wet_yield_kg=payload.wet_yield_kg,
        moisture_percent=payload.moisture_percent,
        min_recorded_temp_c=min_temp,
        transport_distance_km=payload.transport_distance_km,
        feedstock_species=payload.feedstock_species,
        **kwargs
    )
    
    # Sign provenance trail
    lca_sig = sign_lca_audit(lca, _HMAC_SECRET)
    import json
    lca_json = json.dumps({k: v for k, v in lca.__dict__.items()})
    net_credit = lca.net_credit_t_co2e

    # Create new batch
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
        wet_yield_kg=payload.wet_yield_kg,
        min_recorded_temp_c=min_temp,
        transport_distance_km=payload.transport_distance_km,
        device_id=device_id,
        net_credit_t_co2e=net_credit,
        lca_methodology_version=lca.methodology_version,
        lca_audit_json=lca_json,
        lca_signature=lca_sig,
        status="RECEIVED",
    )

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
        
        if (batch_sha != payload_sha or batch.operation_id != x_idempotency_key):
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
        )

    if payload.sha256_hash:
        stmt = select(MediaFile).where(MediaFile.batch_uuid == batch.batch_uuid)
        media = (await session.execute(stmt)).scalars().first()
        if not media:
            batch.status = "UNVERIFIED"
            await session.commit()

    log.info(f"[batches] STORED batch_uuid={batch.batch_uuid} operation_id={x_idempotency_key}")
    return BatchResponse(
        batch_uuid=str(batch.batch_uuid),
        operation_id=batch.operation_id,
        status=batch.status,
        duplicate=False,
        received_at=batch.received_at,
        net_credit_t_co2e=batch.net_credit_t_co2e,
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
    session: AsyncSession = Depends(get_session),
) -> MediaUploadResponse:
    """
    Upload media file with SHA-256 verification.
    """
    if request.headers.get("x-mock-location", "").lower() == "true":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="mock_location_not_allowed")
        
    import re
    if not x_idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Idempotency-Key header is required"
        )
        
    if x_device_id and not re.match(r'^[\w\-]+$', x_device_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_device_id")

    if not x_declared_sha256.strip() or len(x_declared_sha256) != 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Declared-SHA256 header must be 64-character hex string"
        )

    stmt = select(MediaFile).where(MediaFile.operation_id == x_idempotency_key)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        if existing.sha256_hash.lower() != x_declared_sha256.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="operation_id_in_use_with_different_payload"
            )
        log.info(f"[media] DUPLICATE operation_id={x_idempotency_key}")
        import pathlib
        response.status_code = status.HTTP_200_OK
        return MediaUploadResponse(
            server_sha256=existing.sha256_hash,
            stored=True,
            file_path=pathlib.Path(existing.file_path).name,
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
        log.warning(f"[media] SHA256 MISMATCH declared={x_declared_sha256[:8]} calculated={calculated_hash[:8]}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sha256_mismatch"
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

    media = MediaFile(
        operation_id=x_idempotency_key,
        file_path=str(file_path),
        sha256_hash=calculated_hash,
        filename=file.filename,
    )

    session.add(media)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        stmt = select(MediaFile).where(MediaFile.operation_id == x_idempotency_key)
        result = await session.execute(stmt)
        media = result.scalar_one()

    import uuid
    media.batch_uuid = uuid.UUID(x_batch_uuid)
    
    # Anchor photo to batch if batch was already created (P0-25)
    stmt = select(Batch).where(Batch.batch_uuid == uuid.UUID(x_batch_uuid))
    batch_result = await session.execute(stmt)
    batch = batch_result.scalar_one_or_none()
    if batch:
        if batch.status == "UNVERIFIED":
            batch.status = "RECEIVED"
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

@app.post("/api/v1/telemetry", status_code=status.HTTP_201_CREATED)
async def create_telemetry(payload: dict, is_verified: bool = Depends(verify_hmac), session: AsyncSession = Depends(get_session)):
    bu = payload.get("batch_uuid")
    if bu is None or not isinstance(bu, str):
        raise HTTPException(status_code=422, detail="batch_uuid required")
    tu = payload.get("telemetry_uuid")
    if tu is None or not isinstance(tu, str):
        raise HTTPException(status_code=422, detail="telemetry_uuid required")
        
    import json
    row = PyrolysisTelemetry(telemetry_uuid=tu, batch_uuid=bu, payload_json=json.dumps(payload))
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return {"status": "success", "duplicate": True}
    return {"status": "success", "duplicate": False}

@app.post("/api/v1/yield", status_code=status.HTTP_201_CREATED)
async def create_yield(payload: dict, is_verified: bool = Depends(verify_hmac), session: AsyncSession = Depends(get_session)):
    bu = payload.get("batch_uuid")
    if bu is None or not isinstance(bu, str):
        raise HTTPException(status_code=422, detail="batch_uuid required")
    yu = payload.get("yield_uuid")
    if yu is None or not isinstance(yu, str):
        raise HTTPException(status_code=422, detail="yield_uuid required")
        
    import json
    row = YieldMetrics(yield_uuid=yu, batch_uuid=bu, payload_json=json.dumps(payload))
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return {"status": "success", "duplicate": True}
    return {"status": "success", "duplicate": False}

@app.post("/api/v1/metadata", status_code=status.HTTP_201_CREATED)
async def create_metadata(payload: dict, is_verified: bool = Depends(verify_hmac), session: AsyncSession = Depends(get_session)):
    bu = payload.get("batch_uuid")
    if bu is None or not isinstance(bu, str):
        raise HTTPException(status_code=422, detail="batch_uuid required")
        
    import json
    row = SystemMetadata(batch_uuid=bu, payload_json=json.dumps(payload))
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return {"status": "success", "duplicate": True}
    return {"status": "success", "duplicate": False}

@app.post("/api/v1/application", status_code=status.HTTP_201_CREATED)
async def create_application(payload: dict, is_verified: bool = Depends(verify_hmac), session: AsyncSession = Depends(get_session)):
    bu = payload.get("batch_uuid")
    if bu is None or not isinstance(bu, str):
        raise HTTPException(status_code=422, detail="batch_uuid required")
    au = payload.get("application_uuid")
    if au is None or not isinstance(au, str):
        raise HTTPException(status_code=422, detail="application_uuid required")
        
    import json
    row = EndUseApplication(application_uuid=au, batch_uuid=bu, payload_json=json.dumps(payload))
    session.add(row)
    
    # Task 3.4 Cross-check transport distance if batch already exists
    app_lat = payload.get("latitude")
    app_lon = payload.get("longitude")
    if app_lat is not None and app_lon is not None:
        import uuid
        stmt = select(Batch).where(Batch.batch_uuid == uuid.UUID(bu))
        batch = (await session.execute(stmt)).scalar_one_or_none()
        if batch and batch.latitude is not None and batch.longitude is not None:
            from math import radians, cos, sin, asin, sqrt
            def haversine(lon1, lat1, lon2, lat2):
                lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a))
                return 6371 * c
                
            min_dist = haversine(app_lon, app_lat, batch.longitude, batch.latitude)
            if batch.transport_distance_km < min_dist * 0.9:
                batch.transport_distance_km = min_dist
                from lca_engine import calculate_carbon_credit
                lca = calculate_carbon_credit(
                    wet_yield_kg=batch.wet_yield_kg,
                    moisture_percent=batch.moisture_percent,
                    min_recorded_temp_c=batch.min_recorded_temp_c,
                    transport_distance_km=batch.transport_distance_km,
                    feedstock_species=batch.feedstock_species,
                )
                batch.net_credit_t_co2e = lca.net_credit_t_co2e
                session.add(batch)
                
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return {"status": "success", "duplicate": True}
    return {"status": "success", "duplicate": False}
