"""Kon-Tiki Biochar dMRV — FastAPI microservice with PostgreSQL.

Endpoints:
  POST /api/v1/batches  - Receive dMRV payload with idempotency
  POST /api/v1/media    - Upload media with SHA-256 verification
  GET  /api/health      - Health check
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Literal
from uuid import UUID

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
from schemas import (
    BatchPayload,
    BatchResponse,
    MediaUploadResponse,
    RegistrationRequest,
    RegistrationResponse,
    MintTokenRequest,
    LabHCorgRequest,
    LabResultsRequest,
    _BatchScopedPayload,
    KilnRequest,
    OperatorTrainingRequest,
    SupervisorVisitRequest,
    ScaleCalibrationRequest,
    AnnualVerificationRequest
)
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
import piexif

import attestation
import observability
from db import get_session, init_db
from storage import get_storage
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
import hmac_keys
from credit_engine import (
    _recompute_slot,
    recompute_batch_credit,
    _recompute_batch_credit_impl,
    verify_lca_signature,
    _recompute_lock,
    _recompute_state,
    _RECOMPUTE_STATE_CAP,
    _recompute_run_count,
)
from lca_engine import (
    CORG_TABLE,
    calculate_carbon_credit,
    lca_sign_payload_bytes,
    sign_lca_audit,
)
from corroboration import (
    assemble,
    derive_annual_methane_compliance,
    derive_biomass_compliance,
    derive_composite_sample_compliance,
    derive_delivery_compliance,
    derive_ignition_compliance,
    derive_kiln_registration_compliance,
    derive_min_temp,
    derive_moisture_compliance,
    derive_pah_compliance,
    derive_plausibility_reasons,
    derive_pyrolysis_photo_compliance,
    derive_scale_calibration_compliance,
    derive_transport_km,
    derive_wet_yield,
)
from jsonsafe import _as_utc, _safe_json, _safe_json_async, _BIG_JSON_BYTES  # noqa: F401  (R1 facade)
from geo import (  # noqa: F401  (R1 facade)
    GPS_ANCHOR_MISMATCH_KM,
    _evaluate_anchor,
    _gps_mismatch_km,
    _parse_exif_gps,
    haversine_km,
)
# R2: when server.py is reloaded (test_p0_21 does sys.modules.pop("server") +
# reimport), settings must also re-initialize so the startup validation
# (hmac_keys.validate_startup, _require_secret) fires again with the test's
# monkeypatched env. This is a no-op on first import (settings runs normally).
import importlib as _importlib
import settings as _settings_mod
_importlib.reload(_settings_mod)
from settings import (  # noqa: F401  (R2 facade)
    _ADMIN_SECRET,
    _HMAC_SECRET,
    _MIN_SECRET_LEN,
    _MIN_SECRET_UNIQUE,
    _attestation_enforced,
    _canonical_skew_seconds,
    _load_env,
    _require_canonical_v2,
    _require_secret,
    _rl_int,
    env_int,
    log,
)
from security import (  # noqa: F401  (R3 facade)
    _SAFE,
    _b64url_decode,
    _require_admin,
    verify_media_signature,
    verify_signature,
)



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


# ==================== T2.2: per-route rate limiting ====================
# Fixed-window counter keyed by (bucket, device-or-ip). In-process — correct for
# a single-node pilot; swap to a shared store (Redis) when horizontally scaled
# (tracked in the T3 roadmap). Register/admin are IP-keyed brute-force surfaces;
# media/default are device-keyed throughput limits.
#
# Config is read LIVE from os.environ on every request (not captured at import),
# so it survives importlib.reload(server) — a test elsewhere reloads this module,
# which would otherwise desync module-level constants from the running middleware.
# It also makes every limit + the window genuinely runtime-tunable. Disabled by
# default under test (conftest sets DMRV_RATELIMIT_ENABLED=0); test_rate_limit.py
# re-enables it via monkeypatch.setenv.
_RL_DEFAULT_CAPS = {"register": 5, "admin": 30, "media": 20, "default": 120}
_RL_CAP_ENV = {
    "register": "DMRV_RATELIMIT_REGISTER",
    "admin": "DMRV_RATELIMIT_ADMIN",
    "media": "DMRV_RATELIMIT_MEDIA",
    "default": "DMRV_RATELIMIT_DEFAULT",
}

# {(bucket, key, window_index): count} — bounded by pruning when it grows large.
_rl_counters: dict = {}
_RL_MAX_COUNTERS = 4096


def _rl_prune(current_window: int) -> None:
    """P3.7/M1: bound memory WITHOUT wiping live windows.

    The previous ``_rl_counters.clear()`` at the cap was an attack surface: a
    flooder could push the dict past the cap and reset EVERYONE's current-window
    counters to zero, defeating the limiter. Instead, drop only dead windows
    (older than the current one); if still over cap, evict the oldest windows
    first. Current-window counts always survive.
    """
    stale = [k for k in _rl_counters if k[2] < current_window]
    for k in stale:
        del _rl_counters[k]
    if len(_rl_counters) > _RL_MAX_COUNTERS:
        # Still over cap with only live/future windows — evict oldest-window
        # entries first (lowest window index) until back under the cap.
        for k in sorted(_rl_counters, key=lambda kk: kk[2])[
            : len(_rl_counters) - _RL_MAX_COUNTERS
        ]:
            del _rl_counters[k]





def _rl_enabled() -> bool:
    return os.environ.get("DMRV_RATELIMIT_ENABLED", "1") == "1"


def _rl_window_seconds() -> int:
    return max(1, _rl_int("DMRV_RATELIMIT_WINDOW_SECONDS", 60))


def _rl_now() -> int:
    """Current epoch seconds — isolated so it can be stubbed if ever needed."""
    return int(time.time())


def _rl_bucket(path: str) -> str:
    if path == "/api/v1/register":
        return "register"
    # P2.1: portal auth/admin surfaces are brute-force targets — rate-limit them
    # under the stricter "admin" bucket (keyed by client IP).
    if path.startswith("/api/v1/admin/") or path.startswith(
        "/api/v1/portal/"
    ) or path.endswith("/compliance"):
        return "admin"
    if path == "/api/v1/media":
        return "media"
    return "default"


@app.middleware("http")
async def _rate_limit(request: Request, call_next):
    if not _rl_enabled() or request.method == "OPTIONS":
        return await call_next(request)
    path = request.url.path
    if not path.startswith("/api/") or path == "/api/health":
        return await call_next(request)
    bucket = _rl_bucket(path)
    cap = _rl_int(_RL_CAP_ENV[bucket], _RL_DEFAULT_CAPS[bucket])
    if bucket in ("register", "admin"):
        # brute-force surfaces: key by client IP so rotating device ids can't evade.
        key = request.client.host if request.client else "ip-unknown"
    else:
        key = request.headers.get("X-Device-Id") or (
            request.client.host if request.client else "unknown"
        )
    window_seconds = _rl_window_seconds()
    now = _rl_now()
    window = now // window_seconds
    ckey = (bucket, key, window)
    if len(_rl_counters) > 4096:
        _rl_prune(window)
    count = _rl_counters.get(ckey, 0) + 1
    _rl_counters[ckey] = count
    if count > cap:
        retry = window_seconds - (now % window_seconds)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "rate_limited"},
            headers={"Retry-After": str(max(1, retry))},
        )
    return await call_next(request)


# P3.4: registered LAST so it is the OUTERMOST middleware — it assigns the
# request id and records latency/status metrics around everything else, so even
# a 429 from the rate-limiter above still echoes X-Request-Id.
observability.install_middleware(app)


# Media upload directory — relative to this file, works on Windows + Linux + Docker.
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ==================== Pydantic Models ====================












# ==================== Endpoints ====================\n
@app.get("/api/health")
async def health(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    # T2.6: probe the DB so a monitor gets a truthful signal (was a static "ok").
    db_ok = True
    try:
        await session.execute(select(1))
    except Exception:  # noqa: BLE001 — health must report, never raise
        db_ok = False
    body = {
        "status": "ok" if db_ok else "degraded",
        "service": "dmrv-api",
        "db": "ok" if db_ok else "down",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(
        body,
        status_code=status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@app.get("/metrics")
async def metrics(
    x_metrics_token: Optional[str] = Header(None, alias="X-Metrics-Token"),
    session: AsyncSession = Depends(get_session),
):
    """Prometheus exposition. P3.4: guarded by DMRV_METRICS_TOKEN (a public
    scrape leaks operational intel). The provisional-ratio gauge is refreshed at
    scrape time from a cheap COUNT so it never drifts."""
    observability.require_metrics_token(x_metrics_token)  # 401 if missing/wrong
    if observability.metrics_enabled():
        total = (
            await session.execute(select(func.count()).select_from(Batch))
        ).scalar() or 0
        prov = (
            await session.execute(
                select(func.count()).select_from(Batch).where(Batch.provisional.is_(True))
            )
        ).scalar() or 0
        observability.set_provisional_ratio((prov / total) if total else 0.0)
    return observability.metrics_payload()





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
        expires = _as_utc(db_token.expires_at)
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

    # P2.4: the portal lab flow (session-authed) is now the primary channel;
    # this X-Admin-Secret endpoint stays for compatibility.
    log.warning(
        "[deprecated] /api/v1/admin/lab — prefer the portal "
        "POST /api/v1/portal/batches/{uuid}/lab-results (P2.4)"
    )
    await apply_lab_results(
        session,
        batch,
        lab_h_corg=payload.lab_h_corg,
        organic_carbon_pct=payload.organic_carbon_pct,
        biochar_moisture_samples=payload.biochar_moisture_samples,
        dry_bulk_density=payload.dry_bulk_density,
        inertinite_pct=payload.inertinite_pct,
        residual_corg_pct=payload.residual_corg_pct,
        ro_measurements_count=payload.ro_measurements_count,
    )
    await session.commit()
    return {
        "status": "ok",
        "batch_uuid": str(payload.batch_uuid),
        "provisional": batch.provisional,
    }


# P3.7/H2: per-batch recompute coalescing. recompute reads the FULL committed
# evidence set for a batch and is idempotent, so under a burst of evidence posts
# a single run reflects all of them. State: buid -> {lock, dirty}. `dirty` means
# "committed evidence has landed that a recompute must still observe".






# Test/metrics observability: total impl runs (monkeypatch-free counter).


async def _device_registered_at(session: AsyncSession, device_id):
    """The DeviceKey.registered_at for a device, or None if unknown. Used only by
    the attestation grace check (P4.1)."""
    if not device_id:
        return None
    return (
        await session.execute(
            select(DeviceKey.registered_at).where(DeviceKey.device_id == device_id)
        )
    ).scalar_one_or_none()


@observability.timed_recompute




async def apply_lab_results(
    session: AsyncSession,
    batch: Batch,
    *,
    lab_h_corg: Optional[float] = None,
    organic_carbon_pct: Optional[float] = None,
    biochar_moisture_samples: Optional[list] = None,
    dry_bulk_density: Optional[float] = None,
    inertinite_pct: Optional[float] = None,
    residual_corg_pct: Optional[float] = None,
    ro_measurements_count: Optional[int] = None,
) -> None:
    """Persist the non-credit lab verification fields, then recompute the batch
    credit. THE single lab-ingestion path — reused by the admin `/lab` route and
    the portal `POST /batches/{uuid}/lab-results` (P2.4) so gate flips are
    identical across channels. The caller commits.
    """
    if biochar_moisture_samples is not None:
        batch.biochar_moisture_samples_json = json.dumps(biochar_moisture_samples)
    if dry_bulk_density is not None:
        batch.dry_bulk_density = dry_bulk_density
    if inertinite_pct is not None:
        batch.inertinite_pct = inertinite_pct
    if residual_corg_pct is not None:
        batch.residual_corg_pct = residual_corg_pct
    if ro_measurements_count is not None:
        batch.ro_measurements_count = ro_measurements_count
    await recompute_batch_credit(
        session, batch, lab_h_corg=lab_h_corg, lab_corg=organic_carbon_pct
    )


# ---------------------------------------------------------------------------
# Registry upserts (C8/C9). Single definitions reused by the admin X-Admin-Secret
# routes AND the portal admin forms (P2.5). Kiln + annual upsert by their natural
# keys; scale keeps uuid dedup; operator-training + supervisor-visit are made
# idempotent on the real natural key (M5) with a graceful uuid fallback.
# ---------------------------------------------------------------------------


async def upsert_kiln(session: AsyncSession, payload) -> dict:
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


async def _find_by_payload_key(session, model, indexed_col, indexed_val, key, val):
    """Return the row whose indexed column matches AND whose payload_json[key]
    equals val — the natural-key lookup for the M5 idempotency fix."""
    if not indexed_val or val is None:
        return None
    rows = (
        await session.execute(select(model).where(indexed_col == indexed_val))
    ).scalars().all()
    for r in rows:
        parsed = _safe_json(r.payload_json, context=f"{model.__tablename__} nat-key")
        if isinstance(parsed, dict) and parsed.get(key) == val:
            return r
    return None


async def upsert_operator_training(session: AsyncSession, payload) -> dict:
    payload_json = json.dumps(payload.model_dump(mode="json"))
    existing = await _find_by_payload_key(
        session,
        OperatorTraining,
        OperatorTraining.operator_id,
        payload.operator_id,
        "completed_at",
        payload.completed_at,
    )
    if existing is not None:
        existing.record_uuid = payload.record_uuid
        existing.payload_json = payload_json
        await session.commit()
        return {"status": "ok", "duplicate": True}
    session.add(
        OperatorTraining(
            record_uuid=payload.record_uuid,
            operator_id=payload.operator_id,
            payload_json=payload_json,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return {"status": "ok", "duplicate": True}
    return {"status": "ok", "duplicate": False}


async def upsert_supervisor_visit(session: AsyncSession, payload) -> dict:
    payload_json = json.dumps(payload.model_dump(mode="json"))
    existing = await _find_by_payload_key(
        session,
        SupervisorVisit,
        SupervisorVisit.kiln_id,
        payload.kiln_id,
        "visited_at",
        payload.visited_at,
    )
    if existing is not None:
        existing.visit_uuid = payload.visit_uuid
        existing.report_sha256 = payload.report_sha256
        existing.payload_json = payload_json
        await session.commit()
        return {"status": "ok", "duplicate": True}
    session.add(
        SupervisorVisit(
            visit_uuid=payload.visit_uuid,
            kiln_id=payload.kiln_id,
            report_sha256=payload.report_sha256,
            payload_json=payload_json,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return {"status": "ok", "duplicate": True}
    return {"status": "ok", "duplicate": False}


async def upsert_scale_calibration(session: AsyncSession, payload) -> dict:
    session.add(
        ScaleCalibration(
            calibration_uuid=payload.calibration_uuid,
            scale_id=payload.scale_id,
            calibrated_at=_parse_dt(payload.calibrated_at),
            valid_until=_parse_dt(payload.valid_until),
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


async def upsert_annual_verification(session: AsyncSession, payload) -> dict:
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
        # Evidence is already committed here (caller commits before this), so a
        # coalesced recompute is safe: a concurrent run observes our committed
        # rows. This collapses redundant recomputes under a burst of posts.
        await recompute_batch_credit(session, batch, coalesce=True)
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
                        _as_utc(payload.harvest_timestamp)
                        - _as_utc(prev.harvest_timestamp)
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
        project_id=payload.project_id,
        scale_id=payload.scale_id,
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
        # Race: another request committed first (P1-B2). The unique collision may
        # be on operation_id OR on batch_uuid, so look up by BOTH — operation_id
        # first — and NEVER scalar_one(): an op-id collision whose batch_uuid
        # differs from ours would raise NoResultFound and 500. Only a
        # byte-identical replay from the SAME device is a safe 200 duplicate;
        # anything else (different device, uuid, op-id, or hash) is a genuine 409.
        await session.rollback()
        existing = (
            await session.execute(
                select(Batch).where(Batch.operation_id == x_idempotency_key)
            )
        ).scalar_one_or_none()
        if existing is None:
            existing = (
                await session.execute(
                    select(Batch).where(Batch.batch_uuid == payload.batch_uuid)
                )
            ).scalar_one_or_none()
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="race_unresolvable"
            )

        existing_sha = existing.sha256_hash.lower() if existing.sha256_hash else None
        payload_sha = payload.sha256_hash.lower() if payload.sha256_hash else None
        if not (
            existing.device_id == device_id
            and str(existing.batch_uuid) == str(payload.batch_uuid)
            and existing.operation_id == x_idempotency_key
            and existing_sha == payload_sha
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="race_resolved_with_different_payload",
            )
        log.info(f"[batches] RACE-RESOLVED batch_uuid={payload.batch_uuid}")
        batch = existing
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

    # _SAFE is now module-level (shared with the portal media route, P2.2).
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

    # P1-B5: validate the batch UUID BEFORE writing any bytes, so a malformed
    # value (400) can never leave an orphaned object.
    try:
        batch_uuid = uuid.UUID(x_batch_uuid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="invalid_batch_uuid")

    # P3.2: persist through the storage abstraction (local FS or S3/MinIO). The
    # returned key — not an OS path — is what lands in media_files.file_path;
    # traversal is guarded inside the backend.
    storage = get_storage()
    stored_key = storage.write(op, device, content)

    # P1-B5: the object now exists in storage. ANY subsequent failure (ownership
    # 403, DB error, etc.) must roll back the session AND remove the just-written
    # object so a rejected/failed upload never strands an orphan.
    try:
        # Phase 9: extract GPS from the photo's EXIF for server-side corroboration.
        exif_lat, exif_lon = _parse_exif_gps(content)

        media = MediaFile(
            operation_id=x_idempotency_key,
            file_path=stored_key,
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
            stmt = select(MediaFile).where(
                MediaFile.operation_id == x_idempotency_key
            )
            result = await session.execute(stmt)
            media = result.scalar_one()

        media.batch_uuid = batch_uuid

        # Anchor photo to batch if batch was already created (P0-25). The photo
        # only verifies the batch if its hash matches the batch's declared
        # sha256_hash, and the EXIF GPS corroborates the claimed coords (Phase 9).
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
    except Exception:
        await session.rollback()
        storage.delete(stored_key)
        raise

    log.info(f"[media] STORED file={file.filename} sha256={calculated_hash}")
    response.status_code = status.HTTP_200_OK
    return MediaUploadResponse(
        server_sha256=calculated_hash,
        stored=True,
        file_path=Path(stored_key).name,
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


class TelemetryPayload(_BatchScopedPayload):
    model_config = ConfigDict(extra="forbid")
    telemetry_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    kiln_gross_capacity: Optional[float] = Field(None, ge=0.0, le=100_000.0)
    burn_start_timestamp: Optional[str] = Field(None, max_length=64)
    burn_end_timestamp: Optional[str] = Field(None, max_length=64)
    min_temp: Optional[float] = Field(None, ge=-50.0, le=1500.0)
    max_temp: Optional[float] = Field(None, ge=-50.0, le=1500.0)
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
    ignition_energy_amount: Optional[float] = Field(None, ge=0.0, le=1_000_000.0)

    @field_validator("temperature_readings")
    @classmethod
    def _validate_temp_range(cls, v: Optional[list[float]]) -> Optional[list[float]]:
        # Phase 15-C: every reading must be physically plausible so a fabricated
        # constant array can't inflate the burn-quality (CH4) gate with absurd values.
        if v is not None and any((t < -50.0 or t > 1500.0) for t in v):
            raise ValueError("temperature_readings values must be in [-50, 1500] C")
        return v


class YieldPayload(_BatchScopedPayload):
    model_config = ConfigDict(extra="forbid")
    yield_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    quench_methodology: Optional[str] = Field(None, max_length=128)
    gross_volume: Optional[float] = Field(None, ge=0.0, le=100_000.0)
    # Phase 15-C: hard upper bound so a single self-asserted field can't linearly
    # inflate the credit to arbitrary size (100 t/batch ceiling — confirm vs real
    # kiln throughput). A kiln-capacity cross-check remains a documented follow-up.
    wet_yield_weight_kg: Optional[float] = Field(None, gt=0.0, le=100_000.0)
    dry_yield_weight_kg: Optional[float] = Field(None, ge=0.0, le=100_000.0)


class MetadataPayload(_BatchScopedPayload):
    model_config = ConfigDict(extra="forbid")
    batch_uuid: str = Field(..., max_length=64)
    artisan_id: Optional[str] = Field(None, max_length=128)
    device_hardware_mac: Optional[str] = Field(None, max_length=128)
    app_build_version: Optional[str] = Field(None, max_length=128)
    sync_status: Optional[str] = Field(None, max_length=64)
    created_at: Optional[str] = Field(None, max_length=64)


class ApplicationPayload(_BatchScopedPayload):
    model_config = ConfigDict(extra="forbid")
    application_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    application_methodology: Optional[str] = Field(None, max_length=128)
    application_rate_tonnes: Optional[float] = Field(None, ge=0.0, le=1_000_000.0)
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


class MoisturePayload(_BatchScopedPayload):
    # Rainbow compliance C2: one moisture-meter reading (many per batch).
    model_config = ConfigDict(extra="forbid")
    reading_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    moisture_percent: float = Field(..., ge=0.0, le=100.0)
    sequence: int = Field(..., ge=1)
    photo_path: Optional[str] = Field(None, max_length=512)
    sha256_hash: Optional[str] = Field(None, min_length=64, max_length=64)


class CompositeSamplePayload(_BatchScopedPayload):
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


class TransportEventPayload(_BatchScopedPayload):
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





def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp to an aware UTC datetime, or 400 on garbage."""
    if s is None:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="invalid_timestamp")
    return _as_utc(dt)










@app.post("/api/v1/admin/kiln", status_code=status.HTTP_200_OK)
async def register_kiln(
    payload: KilnRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    """Register/update a project kiln (C8). Upsert by kiln_id — the methodology
    says kiln data is captured once and updated when kilns change."""
    _require_admin(x_admin_secret)
    return await upsert_kiln(session, payload)


@app.post("/api/v1/admin/operator-training", status_code=status.HTTP_201_CREATED)
async def register_operator_training(
    payload: OperatorTrainingRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(x_admin_secret)
    return await upsert_operator_training(session, payload)


@app.post("/api/v1/admin/supervisor-visit", status_code=status.HTTP_201_CREATED)
async def register_supervisor_visit(
    payload: SupervisorVisitRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(x_admin_secret)
    return await upsert_supervisor_visit(session, payload)


@app.post("/api/v1/admin/scale-calibration", status_code=status.HTTP_201_CREATED)
async def register_scale_calibration(
    payload: ScaleCalibrationRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(x_admin_secret)
    return await upsert_scale_calibration(session, payload)


# ==================== C9: annual verification (admin) ====================
# Annual / per-verification project inputs, keyed by (project_id, year). Admin-
# authenticated. DATA CAPTURE only: the credit-affecting fields (methane rate →
# CH4 penalty; conversion_factor → C1 yield_conversion) are NOT wired into the
# credit here — that needs methodology sign-off and its own gated phase (same
# discipline as C6 transport). Compliance reasons (missing_annual_methane /
# missing_pah) are deferred to the C10 unified gate.




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
    return await upsert_annual_verification(session, payload)


# ==================== C10: unified compliance gate + report ====================
# Every provisional reason `assemble` can emit, mapped to its methodology section
# and a human-readable label. Ordered so the checklist reads project → per-run →
# per-batch → lab. This is the single source of truth for the compliance report.
_COMPLIANCE_CATALOG: list[tuple[str, str, str]] = [
    # (reason_code, methodology_section, human_label)
    ("missing_biomass_input", "per-run (C1)", "Biomass input amount not recorded"),
    (
        "missing_conversion_factor",
        "per-run (C1)",
        "Biomass yield-conversion factor missing",
    ),
    ("wet_yield_uncorroborated", "per-run", "Wet biochar yield not corroborated"),
    ("min_temp_uncorroborated", "per-run", "Minimum burn temperature not corroborated"),
    (
        "insufficient_moisture_samples",
        "per-run (C2)",
        "Too few photographed moisture readings",
    ),
    ("missing_pyrolysis_photos", "per-run (C3)", "Open-kiln pyrolysis photos missing"),
    (
        "flame_height_out_of_range",
        "per-run (C3)",
        "Open-kiln flame height out of range",
    ),
    ("missing_ignition_energy", "per-run (C3b)", "Closed-kiln ignition energy missing"),
    (
        "missing_composite_sample",
        "per-run (C4)",
        "Site composite pile sub-sample missing",
    ),
    ("transport_uncorroborated", "per-event", "Transport distance not corroborated"),
    ("missing_delivery_record", "per-batch (C5)", "Delivery record missing"),
    ("missing_buyer_identity", "per-batch (C5)", "Buyer/end-user identity missing"),
    ("unregistered_kiln", "project (C8)", "Kiln not in the project registry"),
    ("scale_calibration_expired", "project (C8)", "Scale calibration missing/expired"),
    ("missing_annual_methane", "annual (C9)", "Current methane measurement missing"),
    ("missing_pah", "annual (C9)", "Closed-kiln PAH measurement missing"),
    ("assumed_h_corg", "lab (C7)", "H:Corg permanence ratio not lab-measured"),
    ("assumed_corg", "lab (C7)", "Organic carbon not lab-measured"),
    ("attestation_unverified", "security", "Device attestation unverified"),
]


def compliance_view(batch) -> dict:
    """Build the C10 compliance report (ordered provisional reasons + a human
    per-item checklist) for a batch. THE single grading view — reused by the
    admin `/compliance` route and the portal read API (P2.2); never forked.
    """
    reasons = _safe_json(
        batch.provisional_reasons, context=f"provisional_reasons {batch.batch_uuid}"
    )
    if not isinstance(reasons, list):
        reasons = []
    reason_set = set(reasons)

    # T1.10: per-item enforcement provenance so a verifier can tell "checked and
    # passed" from "not applicable to this batch". 'enforced' = the gate can fire
    # for this batch; 'inert_no_linkage' = needs project/scale linkage this batch
    # lacks; 'awaiting_methodology' = code path exists but is flag-gated pending
    # Rainbow sign-off (device attestation).
    def _enforcement(code: str) -> str:
        if code == "scale_calibration_expired" and not batch.scale_id:
            return "inert_no_linkage"
        if code in ("missing_annual_methane", "missing_pah") and not batch.project_id:
            return "inert_no_linkage"
        if code == "attestation_unverified" and not _attestation_enforced():
            return "awaiting_methodology"
        return "enforced"

    checklist = [
        {
            "code": code,
            "section": section,
            "label": label,
            "ok": code not in reason_set,
            "enforcement": _enforcement(code),
        }
        for code, section, label in _COMPLIANCE_CATALOG
    ]
    return {
        "batch_uuid": str(batch.batch_uuid),
        "provisional": batch.provisional,
        "issuable": not batch.provisional,
        "reasons": reasons,
        "checklist": checklist,
    }


@app.get("/api/v1/batches/{batch_uuid}/compliance")
async def batch_compliance(
    batch_uuid: str,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    """C10 unified compliance report for a batch (admin).

    Returns the ordered provisional reasons plus a human checklist mapping every
    methodology item to pass/fail, so a Project Developer sees exactly what is
    missing before issuance. `issuable` mirrors `not provisional`.
    """
    _require_admin(x_admin_secret)
    try:
        buid = uuid.UUID(batch_uuid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="invalid_batch_uuid")
    batch = (
        await session.execute(select(Batch).where(Batch.batch_uuid == buid))
    ).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=404, detail="unknown_batch")

    return compliance_view(batch)


# ---------------------------------------------------------------------------
# P2.0 — Lab & Verifier portal seam. New portal code lives in the `portal`
# package; server.py only ever gains this single mount line (see AGENT
# playbook §0.3: new backend code goes in modules, server.py only shrinks).
# Imported at the end so the portal package may freely import server helpers
# in later phases without an import-order cycle.
# ---------------------------------------------------------------------------
from portal.routes import router as portal_router  # noqa: E402

app.include_router(portal_router)
