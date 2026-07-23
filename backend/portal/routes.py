"""Portal API router.

Mounted once from `server.py` via `app.include_router(router)`. Every new portal
endpoint hangs off THIS router — `server.py` only ever gains the single mount
line. Rate limiting for `/api/v1/portal/*` maps to the "admin" bucket in
`server._rl_bucket`.
"""

import hashlib
import json
import secrets
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select, cast, String, text
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import (
    AuditEvent,
    Batch,
    BulkDensityTest,
    CompositePileSample,
    DeviceKey,
    Dispatch,
    EndUseApplication,
    Facility,
    FieldWalkTrack,
    Kiln,
    MediaFile,
    MoistureReading,
    AppConfig,
    PortalUser,
    Project,
    PyrolysisTelemetry,
    RegistryConfig,
    SourceParcel,
    TransportEvent,
    YieldMetrics,
    EnrollmentToken,
)
import geometry
import observability
import server_signing
import settings
import tenancy
# P2.5: reuse the admin registry request models + upsert helpers directly from
# schemas + services.registry (P4.8/R7 — repointed off server to break the cycle).
from schemas import (
    AnnualVerificationRequest,
    KilnRequest,
    OperatorTrainingRequest,
    ScaleCalibrationRequest,
    SupervisorVisitRequest,
)
from services.registry import (
    upsert_annual_verification,
    upsert_kiln,
    upsert_operator_training,
    upsert_scale_calibration,
    upsert_supervisor_visit,
)
from routers.devices import _hash_enroll_token
from .auth import (
    create_session,
    require_role,
    revoke_session,
    verify_login,
)
from .schemas import (
    AppConfigUpdate,
    BulkDensityTestCreate,
    BulkDensityTestOut,
    FacilityCreate,
    FacilityOut,
    LabResultsInput,
    LoginRequest,
    LoginResponse,
    MediaVerifyInput,
    MintTokenRequest,
    MintTokenResponse,
    ParcelCreate,
    ParcelOut,
    ProjectCreate,
    ProjectOut,
    RegistryConfigCreate,
    RegistryConfigOut,
)

router = APIRouter(prefix="/api/v1/portal", tags=["portal"])


async def write_audit(
    session: AsyncSession,
    *,
    event_type: str,
    actor_user_id: Optional[int],
    batch_uuid: Optional[str] = None,
    payload: Optional[dict] = None,
) -> None:
    """Append one row to the immutable audit trail (P2.6). The caller commits."""
    session.add(
        AuditEvent(
            event_type=event_type,
            batch_uuid=batch_uuid,
            actor_user_id=actor_user_id,
            payload_json=json.dumps(payload or {}),
        )
    )

# Enrollment tokens are minted server-side with 256 bits of entropy — far above
# the ≥128-bit floor (M3). token_urlsafe(n) draws n random bytes.
_ENROLL_TOKEN_BYTES = 32

# V8 Part 1 (A): fixed key for the transaction-scoped Postgres advisory lock that
# serializes ALL source-parcel registrations (see create_parcel). Arbitrary but
# stable 32-bit int — the value only has to be unique among advisory-lock keys
# this app uses (currently the only one).
_PARCEL_REGISTRATION_LOCK_KEY = 0x70617263  # "parc"


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    user = (
        await session.execute(
            select(PortalUser).where(PortalUser.email == payload.email)
        )
    ).scalar_one_or_none()

    # A disabled user must never authenticate; feed None so the check still
    # burns one argon2 verify (constant-ish timing) and fails.
    stored = user.password_hash if (user is not None and not user.disabled) else None
    if not verify_login(stored, payload.password):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "invalid_credentials"},
        )

    token, expires = await create_session(session, user.id)
    return LoginResponse(
        token=token, expires_at=expires.isoformat(), role=user.role
    )


@router.post("/logout")
async def logout(
    authorization: str | None = Header(None, alias="Authorization"),
    session: AsyncSession = Depends(get_session),
):
    if authorization and authorization.lower().startswith("bearer "):
        await revoke_session(session, authorization[7:].strip())
    return {"status": "logged_out"}


@router.post(
    "/tokens",
    response_model=MintTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def mint_enrollment_token(
    payload: MintTokenRequest,
    admin: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    """Admin-only: mint a single-use device enrollment token (256-bit) and
    return it plus a scannable QR payload `dmrv-enroll:v1:{...}`."""
    token = secrets.token_urlsafe(_ENROLL_TOKEN_BYTES)
    expires = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
    # Audit fix 6: store only the SHA-256 hash; the raw token is returned once
    # below (QR + response) and never persisted.
    session.add(EnrollmentToken(token=_hash_enroll_token(token), expires_at=expires))
    await write_audit(
        session,
        event_type="token_minted",
        actor_user_id=admin.id,
        payload={"expires_at": expires.isoformat()},
    )
    await session.commit()

    qr_payload = "dmrv-enroll:v1:" + json.dumps(
        {"url": payload.base_url or "", "token": token},
        separators=(",", ":"),
    )
    return MintTokenResponse(
        token=token, expires_at=expires.isoformat(), qr_payload=qr_payload
    )


# ---------------------------------------------------------------------------
# V8 Part 0.2 — Project entity (admin create + authenticated list). project_id
# is the primary key (see models.Project docstring) — the unique constraint
# on that PK is what makes create() concurrency-safe: two simultaneous
# `POST /projects` with the same id cannot both succeed (the second commit
# raises IntegrityError, caught below), no explicit lock needed.
# ---------------------------------------------------------------------------


def _project_row(p: Project) -> dict:
    return {
        "project_id": p.project_id,
        "name": p.name,
        "registry_config_id": p.registry_config_id,
        "org_id": p.org_id,
        "status": p.status,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    project = Project(
        project_id=payload.project_id,
        name=payload.name,
        registry_config_id=payload.registry_config_id,
        org_id=payload.org_id,
    )
    session.add(project)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="project_already_exists")
    await write_audit(
        session,
        event_type="project_created",
        actor_user_id=user.id,
        payload={"project_id": project.project_id},
    )
    await session.commit()
    return _project_row(project)


@router.get("/projects")
async def list_projects(
    user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
    before: Optional[str] = Query(None, description="cursor: created_at ISO"),
    limit: int = Query(50, ge=1, le=100),
):
    stmt = tenancy.scope_by_org(select(Project), Project.org_id, user)
    if before:
        stmt = stmt.where(Project.created_at < _parse_dt(before))
    stmt = stmt.order_by(Project.created_at.desc(), Project.project_id.desc()).limit(
        limit + 1
    )
    rows = list((await session.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        rows[-1].created_at.isoformat() if has_more and rows and rows[-1].created_at
        else None
    )
    return {"projects": [_project_row(p) for p in rows], "next_cursor": next_cursor}


# ---------------------------------------------------------------------------
# V8 Part 3.1/3.3 — Facility admin (create/list) + Dispatch read (portal).
# Facilities are portal-registered infrastructure (mirrors Project/
# SourceParcel); dispatches are device-created (mirrors Batch) — the portal
# only READS them here, tabbed by status.
# ---------------------------------------------------------------------------


def _facility_row(f: Facility) -> dict:
    return {
        "facility_uuid": f.facility_uuid,
        "name": f.name,
        "facility_type": f.facility_type,
        "state": f.state,
        "district": f.district,
        "latitude": f.latitude,
        "longitude": f.longitude,
        "status": f.status,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


@router.post(
    "/facilities", response_model=FacilityOut, status_code=status.HTTP_201_CREATED
)
async def create_facility(
    payload: FacilityCreate,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    facility = Facility(
        facility_uuid=payload.facility_uuid,
        org_id=payload.org_id,
        name=payload.name,
        facility_type=payload.facility_type,
        state=payload.state,
        district=payload.district,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    session.add(facility)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="facility_already_exists")
    await write_audit(
        session,
        event_type="facility_created",
        actor_user_id=user.id,
        payload={"facility_uuid": facility.facility_uuid},
    )
    await session.commit()
    return _facility_row(facility)


@router.get("/facilities")
async def list_facilities(
    user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
    before: Optional[str] = Query(None, description="cursor: created_at ISO"),
    limit: int = Query(50, ge=1, le=100),
):
    stmt = tenancy.scope_by_org(select(Facility), Facility.org_id, user)
    if before:
        stmt = stmt.where(Facility.created_at < _parse_dt(before))
    stmt = stmt.order_by(Facility.created_at.desc(), Facility.facility_uuid.desc()).limit(
        limit + 1
    )
    rows = list((await session.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        rows[-1].created_at.isoformat() if has_more and rows and rows[-1].created_at
        else None
    )
    return {"facilities": [_facility_row(f) for f in rows], "next_cursor": next_cursor}


def _dispatch_row(d: Dispatch) -> dict:
    return {
        "dispatch_uuid": d.dispatch_uuid,
        "kind": d.kind,
        "source_ref": d.source_ref,
        "dest_facility_uuid": d.dest_facility_uuid,
        "status": d.status,
        "weight_source_kg": d.weight_source_kg,
        "weight_facility_kg": d.weight_facility_kg,
        "weight_delta_pct": d.weight_delta_pct,
        "weight_flagged": d.weight_flagged,
        "driver_name": d.driver_name,
        "truck_number": d.truck_number,
        "device_id": d.device_id,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "received_at": d.received_at.isoformat() if d.received_at else None,
    }


@router.get("/dispatch")
async def list_dispatch(
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
    status_eq: Optional[str] = Query(None, alias="status"),
    before: Optional[str] = Query(None, description="cursor: created_at ISO"),
    limit: int = Query(50, ge=1, le=100),
):
    stmt = select(Dispatch)
    if status_eq is not None:
        stmt = stmt.where(Dispatch.status == status_eq)
    if before:
        stmt = stmt.where(Dispatch.created_at < _parse_dt(before))
    stmt = stmt.order_by(Dispatch.created_at.desc(), Dispatch.dispatch_uuid.desc()).limit(
        limit + 1
    )
    rows = list((await session.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        rows[-1].created_at.isoformat() if has_more and rows and rows[-1].created_at
        else None
    )
    return {"dispatches": [_dispatch_row(d) for d in rows], "next_cursor": next_cursor}


# ---------------------------------------------------------------------------
# V8 Part 4 (G) — Registry config admin (create/list). A project opts into a
# config via Project.registry_config_id (already reserved, Part 0.2); a
# project with none set keeps today's CSI-3.2 default exactly.
# ---------------------------------------------------------------------------


def _registry_config_row(c: RegistryConfig) -> dict:
    try:
        params = json.loads(c.params_json) if c.params_json else {}
    except (ValueError, TypeError):
        params = {}
    return {
        "config_id": c.config_id,
        "registry_name": c.registry_name,
        "methodology_version": c.methodology_version,
        "params": params,
        "fpic_template_set_id": c.fpic_template_set_id,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.post(
    "/registry-configs",
    response_model=RegistryConfigOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_registry_config(
    payload: RegistryConfigCreate,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    config = RegistryConfig(
        config_id=payload.config_id,
        registry_name=payload.registry_name,
        methodology_version=payload.methodology_version,
        params_json=json.dumps(payload.params),
        fpic_template_set_id=payload.fpic_template_set_id,
    )
    session.add(config)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="registry_config_already_exists")
    await write_audit(
        session,
        event_type="registry_config_created",
        actor_user_id=user.id,
        payload={"config_id": config.config_id},
    )
    await session.commit()
    return _registry_config_row(config)


@router.get("/registry-configs")
async def list_registry_configs(
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(RegistryConfig).order_by(RegistryConfig.created_at.desc())
        )
    ).scalars().all()
    return {"registry_configs": [_registry_config_row(c) for c in rows]}


# ---------------------------------------------------------------------------
# V8 Part 4 (F) — Bulk-density calibration admin (create/list). Project-
# scoped (see models.BulkDensityTest docstring); drives both the volumetric
# yield fallback and the production_requires_valid_density C10 gate.
# ---------------------------------------------------------------------------


def _bulk_density_row(t: BulkDensityTest) -> dict:
    return {
        "test_uuid": t.test_uuid,
        "project_id": t.project_id,
        "density_kg_per_l": t.density_kg_per_l,
        "performed_at": t.performed_at.isoformat() if t.performed_at else None,
        "mass_kg": t.mass_kg,
        "volume_l": t.volume_l,
        "valid_until": t.valid_until.isoformat() if t.valid_until else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@router.post(
    "/bulk-density-tests",
    response_model=BulkDensityTestOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_bulk_density_test(
    payload: BulkDensityTestCreate,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    existing = (
        await session.execute(
            select(BulkDensityTest).where(BulkDensityTest.test_uuid == payload.test_uuid)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="bulk_density_test_already_exists")

    test = BulkDensityTest(
        test_uuid=payload.test_uuid,
        project_id=payload.project_id,
        density_kg_per_l=payload.density_kg_per_l,
        performed_at=_parse_dt(payload.performed_at) if payload.performed_at else None,
        mass_kg=payload.mass_kg,
        volume_l=payload.volume_l,
        valid_until=_parse_dt(payload.valid_until) if payload.valid_until else None,
    )
    session.add(test)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="bulk_density_test_already_exists")
    await write_audit(
        session,
        event_type="bulk_density_test_created",
        actor_user_id=user.id,
        payload={"test_uuid": test.test_uuid, "project_id": test.project_id},
    )
    await session.commit()
    return _bulk_density_row(test)


@router.get("/bulk-density-tests")
async def list_bulk_density_tests(
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
    project_id: Optional[str] = Query(None),
):
    stmt = select(BulkDensityTest)
    if project_id:
        stmt = stmt.where(BulkDensityTest.project_id == project_id)
    stmt = stmt.order_by(BulkDensityTest.created_at.desc())
    rows = (await session.execute(stmt)).scalars().all()
    return {"bulk_density_tests": [_bulk_density_row(t) for t in rows]}


# ---------------------------------------------------------------------------
# V8 Part 1.3 — Source Parcel Boundary Registration + List API.
# Role-gated ("admin" for create, any authed user for list).
# Concurrency safety: project row is locked FOR UPDATE during overlap check.
# Overlap defense: SQL bbox prefilter + exact shapely overlap ratio check.
# Idempotency: client-supplied parcel_uuid or server UUID, flush 409 guard.
# ---------------------------------------------------------------------------


def _parcel_row(p: SourceParcel) -> dict:
    return {
        "parcel_uuid": p.parcel_uuid,
        "project_id": p.project_id,
        "name": p.name,
        "boundary_geojson": p.boundary_geojson,
        "area_m2": p.area_m2,
        "declared_area_acres": p.declared_area_acres,
        "bbox_min_lat": p.bbox_min_lat,
        "bbox_min_lon": p.bbox_min_lon,
        "bbox_max_lat": p.bbox_max_lat,
        "bbox_max_lon": p.bbox_max_lon,
        "boundary_method": p.boundary_method,
        "boundary_status": p.boundary_status,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.post("/parcels", response_model=ParcelOut, status_code=status.HTTP_201_CREATED)
async def create_parcel(
    payload: ParcelCreate,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    geojson_input = payload.boundary_geojson
    try:
        poly = geometry.parse_geojson(geojson_input)
        valid_poly = geometry.validate_polygon(poly)
    except ValueError as exc:
        observability.record_gate_rejection(
            gate="parcel_registration",
            reason="boundary_invalid",
            extra={"project_id": payload.project_id, "error": str(exc)},
        )
        raise HTTPException(
            status_code=422,
            detail={"code": "boundary_invalid", "message": str(exc)},
        )

    area_m2 = geometry.geodesic_area_m2(valid_poly)
    min_lat, min_lon, max_lat, max_lon = geometry.bbox_of(valid_poly)

    if payload.declared_area_acres is not None and payload.declared_area_acres > 0:
        declared_area_m2 = payload.declared_area_acres * 4046.8564224
        diff_pct = abs(area_m2 - declared_area_m2) / declared_area_m2 * 100.0
        max_mismatch_pct = settings.parcel_area_mismatch_pct()
        if diff_pct > max_mismatch_pct:
            observability.record_gate_rejection(
                gate="parcel_registration",
                reason="area_mismatch",
                extra={
                    "project_id": payload.project_id,
                    "area_m2": area_m2,
                    "declared_area_m2": declared_area_m2,
                    "diff_pct": diff_pct,
                },
            )
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "area_mismatch",
                    "message": (
                        f"Calculated area ({area_m2:.1f} m²) differs from declared area "
                        f"({declared_area_m2:.1f} m²) by {diff_pct:.1f}% (max allowed is {max_mismatch_pct}%)."
                    ),
                    "area_m2": area_m2,
                    "declared_area_m2": declared_area_m2,
                    "diff_pct": diff_pct,
                },
            )

    proj = (
        await session.execute(
            select(Project).where(Project.project_id == payload.project_id)
        )
    ).scalar_one_or_none()
    if proj is None:
        raise HTTPException(status_code=404, detail="project_not_found")

    # Serialize parcel registration GLOBALLY so the check-then-insert below is
    # atomic across concurrent requests. Critically, the overlap scan is
    # CROSS-PROJECT (see below): the fraud it defends against — two DIFFERENT
    # projects claiming the same land (double-counting) — is inherently
    # cross-project, so a per-project row lock could not serialize it (two
    # registrations in different projects lock different rows and race). A
    # transaction-scoped advisory lock on one fixed key serializes ALL parcel
    # registrations fleet-wide. Postgres-only; SQLite (tests) has no advisory
    # locks and runs registrations sequentially, so it's a safe no-op there.
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:k)"),
            {"k": _PARCEL_REGISTRATION_LOCK_KEY},
        )

    if settings.parcel_overlap_enforced():
        # NO project_id filter: overlap must be detected across ALL projects,
        # because double-counting is two different projects claiming the same
        # parcel. Scoping this to payload.project_id would let a colluding or
        # duplicate project register byte-identical land undetected.
        candidates_stmt = select(SourceParcel).where(
            SourceParcel.boundary_status == "approved",
            SourceParcel.bbox_max_lat >= min_lat,
            SourceParcel.bbox_min_lat <= max_lat,
            SourceParcel.bbox_max_lon >= min_lon,
            SourceParcel.bbox_min_lon <= max_lon,
        )
        candidates = list((await session.execute(candidates_stmt)).scalars().all())

        tolerance = settings.parcel_overlap_ratio()
        for candidate in candidates:
            try:
                # Trusted parse: stored geometry is canonical + already validated
                # at creation, so we skip the untrusted-input DoS guard (which,
                # if DMRV_PARCEL_MAX_VERTICES were later lowered, would 500 every
                # scan touching an over-limit approved parcel — a self-DoS).
                cand_poly = geometry.parse_trusted_geojson(candidate.boundary_geojson)
            except Exception as exc:  # noqa: BLE001
                # A stored, previously-approved parcel that no longer parses is a
                # data-integrity failure in an anti-fraud scan. Silently skipping
                # it (the old `continue`) is fail-OPEN: the new parcel could
                # overlap this candidate and be approved anyway. Fail closed —
                # broad except because an invalid stored geometry raises GEOS
                # errors (not just ValueError).
                observability.record_gate_rejection(
                    gate="parcel_registration",
                    reason="corrupt_stored_geometry",
                    extra={"conflicting_parcel_uuid": candidate.parcel_uuid},
                )
                raise HTTPException(
                    status_code=500,
                    detail="corrupt_stored_parcel_geometry",
                ) from exc
            ratio = geometry.overlap_ratio(cand_poly, valid_poly)
            if ratio > tolerance:
                observability.record_gate_rejection(
                    gate="parcel_registration",
                    reason="overlap_reject",
                    extra={
                        "project_id": payload.project_id,
                        "conflicting_parcel_uuid": candidate.parcel_uuid,
                        "conflicting_parcel_project_id": candidate.project_id,
                        "overlap_ratio": ratio,
                    },
                )
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "boundary_overlaps_existing_parcel",
                        "message": (
                            f"Boundary overlaps with existing approved parcel "
                            f"'{candidate.name}' ({candidate.parcel_uuid}) by {ratio * 100:.1f}% "
                            f"(tolerance limit is {tolerance * 100:.1f}%)."
                        ),
                        "conflicting_parcel_uuid": candidate.parcel_uuid,
                        "conflicting_parcel_name": candidate.name,
                        "overlap_ratio": ratio,
                    },
                )

    parcel_uuid = payload.parcel_uuid or str(_uuid.uuid4())
    # Persist the CANONICAL, validated/repaired geometry (not the raw client
    # input): keeps stored boundary consistent with the computed area/bbox and
    # guarantees it always re-parses to a valid polygon on later overlap scans.
    geojson_str = geometry.to_geojson_str(valid_poly)

    parcel = SourceParcel(
        parcel_uuid=parcel_uuid,
        project_id=payload.project_id,
        name=payload.name,
        boundary_geojson=geojson_str,
        area_m2=area_m2,
        declared_area_acres=payload.declared_area_acres,
        bbox_min_lat=min_lat,
        bbox_min_lon=min_lon,
        bbox_max_lat=max_lat,
        bbox_max_lon=max_lon,
        boundary_method=payload.boundary_method or "portal_drawn",
        boundary_status="approved",
        created_by_user_id=user.id,
    )
    session.add(parcel)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="parcel_already_exists")

    await write_audit(
        session,
        event_type="source_parcel_created",
        actor_user_id=user.id,
        payload={"parcel_uuid": parcel.parcel_uuid, "project_id": parcel.project_id},
    )
    await session.commit()
    return _parcel_row(parcel)


@router.get("/parcels")
async def list_parcels(
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
    project_id: Optional[str] = Query(None, description="filter by project_id"),
    before: Optional[str] = Query(None, description="cursor: created_at ISO"),
    limit: int = Query(50, ge=1, le=100),
):
    stmt = select(SourceParcel)
    if project_id:
        stmt = stmt.where(SourceParcel.project_id == project_id)
    if before:
        stmt = stmt.where(SourceParcel.created_at < _parse_dt(before))
    stmt = stmt.order_by(SourceParcel.created_at.desc(), SourceParcel.parcel_uuid.desc()).limit(
        limit + 1
    )
    rows = list((await session.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        rows[-1].created_at.isoformat() if has_more and rows and rows[-1].created_at
        else None
    )
    return {"parcels": [_parcel_row(p) for p in rows], "next_cursor": next_cursor}


# ---------------------------------------------------------------------------
# V8 Part 5 (A phase-2) — signed field-walk link mint + ground-truthing read.
# The link is a server-signed {parcel_uuid, nonce, issued_at, expires_at}
# document (Ed25519, the SAME key `server_signing.py` uses for the
# remote-config document) — a device presents it back at
# POST /api/v1/field-walk (routers/field_walk.py) to authorize exactly one
# boundary walk. Single-use is enforced there via a UNIQUE(link_nonce).
# ---------------------------------------------------------------------------

_FIELD_WALK_LINK_TTL = timedelta(hours=24)


@router.post("/parcels/{parcel_uuid}/field-walk-link")
async def mint_field_walk_link(
    parcel_uuid: str,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    parcel = await session.get(SourceParcel, parcel_uuid)
    if parcel is None:
        raise HTTPException(status_code=404, detail="parcel_not_found")

    now = datetime.now(timezone.utc)
    link_payload = json.dumps(
        {
            "parcel_uuid": parcel_uuid,
            "nonce": secrets.token_urlsafe(16),
            "issued_at": now.isoformat(),
            "expires_at": (now + _FIELD_WALK_LINK_TTL).isoformat(),
        }
    )
    kid, signature = server_signing.sign(link_payload.encode("utf-8"))

    await write_audit(
        session,
        event_type="field_walk_link_minted",
        actor_user_id=user.id,
        payload={"parcel_uuid": parcel_uuid},
    )
    await session.commit()

    return {"payload": link_payload, "kid": kid, "signature": signature}


def _field_walk_row(t: FieldWalkTrack) -> dict:
    return {
        "id": t.id,
        "parcel_uuid": t.parcel_uuid,
        "device_id": t.device_id,
        "computed_area_m2": t.computed_area_m2,
        "overlap_ratio_vs_declared": t.overlap_ratio_vs_declared,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@router.get("/parcels/{parcel_uuid}/field-walks")
async def list_field_walks(
    parcel_uuid: str,
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        (
            await session.execute(
                select(FieldWalkTrack)
                .where(FieldWalkTrack.parcel_uuid == parcel_uuid)
                .order_by(FieldWalkTrack.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return {"field_walks": [_field_walk_row(t) for t in rows]}


# ---------------------------------------------------------------------------
# V8 Part 0.4 — Remote control plane admin write. Public read lives at
# GET /api/v1/config (routers/config.py) — feature flags/min-version/kill-
# switch are not secrets, so any device can fetch them; only the WRITE is
# admin-gated here. Single logical row (config_id='default'); this is a
# benign admin panel, not an invariant-enforcing write (unlike parcel
# overlap or project-id uniqueness), so a plain read-then-write is
# sufficient — worst case under a race is last-admin-write-wins, not a
# security-invariant violation.
# ---------------------------------------------------------------------------


@router.post("/config")
async def update_app_config(
    payload: AppConfigUpdate,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    row = await session.get(AppConfig, "default")
    if row is None:
        row = AppConfig(config_id="default")
        session.add(row)

    if payload.flags is not None:
        row.flags_json = json.dumps(payload.flags)
    if payload.min_version is not None:
        row.min_version = payload.min_version
    if payload.kill_switch is not None:
        row.kill_switch = payload.kill_switch
    if payload.message is not None:
        row.message = payload.message

    await write_audit(
        session,
        event_type="app_config_updated",
        actor_user_id=user.id,
        payload={
            "kill_switch": row.kill_switch,
            "min_version": row.min_version,
        },
    )
    await session.commit()
    return {
        "flags": json.loads(row.flags_json) if row.flags_json else {},
        "min_version": row.min_version,
        "kill_switch": row.kill_switch,
        "message": row.message,
    }


# ---------------------------------------------------------------------------
# P2.2 — Read API (any authenticated portal user). Verifiers read; nobody
# writes here. Media bytes stream through an authed route — no static path
# ever leaves the server.
# ---------------------------------------------------------------------------

_PAGE_MAX = 100


def _batch_row(b: Batch) -> dict:
    reasons = b.provisional_reasons
    try:
        reason_count = len(json.loads(reasons)) if reasons else 0
    except (ValueError, TypeError):
        reason_count = 0
    return {
        "batch_uuid": str(b.batch_uuid),
        "device_id": b.device_id,
        "project_id": b.project_id,
        "status": b.status,
        "provisional": b.provisional,
        "reason_count": reason_count,
        "net_credit_t_co2e": b.net_credit_t_co2e,
        "wet_yield_kg": b.wet_yield_kg,
        "received_at": b.received_at.isoformat() if b.received_at else None,
    }


@router.get("/batches")
async def list_batches(
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
    status_eq: Optional[str] = Query(None, alias="status"),
    provisional: Optional[bool] = None,
    device_id: Optional[str] = None,
    project_id: Optional[str] = None,
    received_from: Optional[str] = None,
    received_to: Optional[str] = None,
    before: Optional[str] = Query(None, description="cursor: received_at ISO"),
    limit: int = Query(50, ge=1, le=_PAGE_MAX),
):
    stmt = tenancy.scope_batches_by_org(select(Batch), _user)
    if status_eq is not None:
        stmt = stmt.where(Batch.status == status_eq)
    if provisional is not None:
        stmt = stmt.where(Batch.provisional == provisional)
    if device_id is not None:
        stmt = stmt.where(Batch.device_id == device_id)
    if project_id is not None:
        stmt = stmt.where(Batch.project_id == project_id)
    if received_from:
        stmt = stmt.where(Batch.received_at >= _parse_dt(received_from))
    if received_to:
        stmt = stmt.where(Batch.received_at <= _parse_dt(received_to))
    if before:
        stmt = stmt.where(Batch.received_at < _parse_dt(before))
    stmt = stmt.order_by(Batch.received_at.desc(), Batch.id.desc()).limit(limit + 1)

    rows = list((await session.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        rows[-1].received_at.isoformat() if has_more and rows and rows[-1].received_at
        else None
    )
    return {"batches": [_batch_row(b) for b in rows], "next_cursor": next_cursor}


def _parse_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="invalid_datetime")


@router.get("/batches/{batch_uuid}")
async def batch_detail(
    batch_uuid: str,
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    import uuid as _uuid

    from services.compliance import compliance_view  # reuse the ONE grading view (P2.0 coupling)

    try:
        buid = str(_uuid.UUID(batch_uuid))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="invalid_batch_uuid")
    batch = (
        await session.execute(select(Batch).where(Batch.batch_uuid == buid))
    ).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=404, detail="unknown_batch")

    key = str(buid)

    async def _count(model, col) -> int:
        return int(
            (await session.execute(select(func.count()).where(col == key))).scalar() or 0
        )

    evidence = {
        "moisture_readings": await _count(MoistureReading, MoistureReading.batch_uuid),
        "composite_pile_samples": await _count(
            CompositePileSample, CompositePileSample.batch_uuid
        ),
        "transport_events": await _count(TransportEvent, TransportEvent.batch_uuid),
        "pyrolysis_telemetry": await _count(
            PyrolysisTelemetry, PyrolysisTelemetry.batch_uuid
        ),
        "yield_metrics": await _count(YieldMetrics, YieldMetrics.batch_uuid),
        "end_use_application": await _count(
            EndUseApplication, EndUseApplication.batch_uuid
        ),
    }

    media_rows = (
        await session.execute(
            select(MediaFile)
            .where(MediaFile.batch_uuid == buid)
            .order_by(MediaFile.uploaded_at.asc())
        )
    ).scalars().all()
    media = [
        {
            "operation_id": m.operation_id,
            "filename": m.filename,
            "sha256_hash": m.sha256_hash,
            "capture_type": m.capture_type,
            "capture_type_verified": bool(m.capture_type_verified),
            "exif_lat": m.exif_lat,
            "exif_lon": m.exif_lon,
            "uploaded_at": m.uploaded_at.isoformat() if m.uploaded_at else None,
            "verification_status": m.verification_status,
            "verification_remarks": m.verification_remarks,
        }
        for m in media_rows
    ]

    return {
        "batch": _batch_row(batch),
        "compliance": compliance_view(batch),
        "evidence_counts": evidence,
        "media": media,
    }


@router.get("/devices")
async def list_devices(
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(DeviceKey).order_by(DeviceKey.registered_at.desc())
        )
    ).scalars().all()
    return {
        "devices": [
            {
                "device_id": d.device_id,
                "registered_at": d.registered_at.isoformat()
                if d.registered_at
                else None,
            }
            for d in rows
        ]
    }


@router.get("/summary")
async def summary(
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    status_rows = (
        await session.execute(
            select(Batch.status, func.count()).group_by(Batch.status)
        )
    ).all()
    provisional_count = int(
        (
            await session.execute(
                select(func.count()).where(Batch.provisional.is_(True))
            )
        ).scalar()
        or 0
    )

    # Reasons histogram across all provisional batches.
    reason_rows = (
        await session.execute(
            select(Batch.provisional_reasons).where(Batch.provisional.is_(True))
        )
    ).scalars().all()
    histogram: dict[str, int] = {}
    for raw in reason_rows:
        try:
            for code in json.loads(raw) if raw else []:
                histogram[code] = histogram.get(code, 0) + 1
        except (ValueError, TypeError):
            continue

    return {
        "by_status": {s: int(c) for s, c in status_rows},
        "provisional": provisional_count,
        "reasons_histogram": histogram,
    }


@router.get("/media/{operation_id}")
async def get_media(
    operation_id: str,
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    from security import _SAFE  # shared identity guard
    from storage import get_storage

    if not _SAFE.match(operation_id or ""):
        raise HTTPException(status_code=400, detail="invalid_operation_id")
    row = (
        await session.execute(
            select(MediaFile).where(MediaFile.operation_id == operation_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown_media")

    # P3.2: read back through the storage abstraction (local FS or S3/MinIO).
    # file_path holds an abstract key for new rows and a legacy absolute path
    # for old ones; the local backend resolves both and guards traversal.
    storage = get_storage()
    try:
        stream = storage.open_stream(row.file_path)
    except ValueError:
        raise HTTPException(status_code=400, detail="path_traversal")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="media_missing")
    filename = row.filename or f"{operation_id}.bin"
    return StreamingResponse(
        stream,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/media/{operation_id}/verify")
async def verify_media(
    operation_id: str,
    payload: MediaVerifyInput,
    user: PortalUser = Depends(require_role("verifier", "admin")),
    session: AsyncSession = Depends(get_session),
):
    """V8 Part 4 (K) — reviewer verdict on ONE piece of evidence (targeted
    recapture) rather than the all-or-nothing batch-level compliance gate."""
    from security import _SAFE

    if not _SAFE.match(operation_id or ""):
        raise HTTPException(status_code=400, detail="invalid_operation_id")
    row = (
        await session.execute(
            select(MediaFile).where(MediaFile.operation_id == operation_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown_media")

    row.verification_status = payload.status
    row.verification_remarks = payload.remarks
    await write_audit(
        session,
        event_type="media_verified",
        actor_user_id=user.id,
        batch_uuid=row.batch_uuid,
        payload={
            "operation_id": operation_id,
            "status": payload.status,
            "remarks": payload.remarks,
        },
    )
    await session.commit()
    return {
        "operation_id": operation_id,
        "verification_status": row.verification_status,
        "verification_remarks": row.verification_remarks,
    }


# ---------------------------------------------------------------------------
# P2.4 — Lab flow. A lab tech (or admin) submits results for a batch; the SAME
# recompute the legacy X-Admin-Secret channel runs fires, so the assumed_*
# provisional reasons flip identically. The certificate PDF is stored via the
# media mechanism under a labcert-<uuid> operation id.
# ---------------------------------------------------------------------------


async def _load_batch(session: AsyncSession, batch_uuid: str) -> Batch:
    if len(batch_uuid) < 32:
        # Short prefix lookup (e.g. 8 chars)
        batch = (
            await session.execute(select(Batch).where(cast(Batch.batch_uuid, String).like(f"{batch_uuid.lower()}%")))
        ).scalar_one_or_none()
    else:
        try:
            buid = str(_uuid.UUID(batch_uuid))
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="invalid_batch_uuid")
        batch = (
            await session.execute(select(Batch).where(Batch.batch_uuid == buid))
        ).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=404, detail="unknown_batch")
    return batch


@router.post("/batches/{batch_uuid}/lab-results")
async def submit_lab_results(
    batch_uuid: str,
    payload: LabResultsInput,
    user: PortalUser = Depends(require_role("lab", "admin")),
    session: AsyncSession = Depends(get_session),
):
    from services.lab import apply_lab_results  # the ONE lab-ingestion path (P2.4)

    batch = await _load_batch(session, batch_uuid)
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
    await write_audit(
        session,
        event_type="lab_results",
        actor_user_id=user.id,
        batch_uuid=str(batch.batch_uuid),
        payload={"provisional": batch.provisional},
    )
    await session.commit()
    reasons = batch.provisional_reasons
    try:
        parsed = json.loads(reasons) if reasons else []
    except (ValueError, TypeError):
        parsed = []
    return {
        "status": "ok",
        "batch_uuid": str(batch.batch_uuid),
        "provisional": batch.provisional,
        "reasons": parsed,
    }


@router.post("/batches/{batch_uuid}/lab-certificate", status_code=status.HTTP_201_CREATED)
async def upload_lab_certificate(
    batch_uuid: str,
    file: UploadFile = File(...),
    _user: PortalUser = Depends(require_role("lab", "admin")),
    session: AsyncSession = Depends(get_session),
):
    from storage import get_storage

    batch = await _load_batch(session, batch_uuid)
    op = f"labcert-{batch.batch_uuid}"
    data = await file.read()
    sha = hashlib.sha256(data).hexdigest()
    # P3.2: store the certificate under the "labcerts" prefix via the abstraction.
    stored_key = get_storage().write(op, "labcerts", data)

    row = MediaFile(
        operation_id=op,
        file_path=stored_key,
        sha256_hash=sha,
        filename=file.filename,
        batch_uuid=batch.batch_uuid,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        # A re-submitted certificate overwrites the prior one (same op id).
        await session.rollback()
        existing = (
            await session.execute(
                select(MediaFile).where(MediaFile.operation_id == op)
            )
        ).scalar_one()
        existing.file_path = stored_key
        existing.sha256_hash = sha
        existing.filename = file.filename
        existing.batch_uuid = batch.batch_uuid
        await session.commit()
    return {"operation_id": op, "sha256_hash": sha}


# ---------------------------------------------------------------------------
# P2.5 — Registry admin forms. Thin portal (admin-role) wrappers over the SAME
# upsert helpers the legacy X-Admin-Secret routes use. Operator-training and
# supervisor-visit are idempotent on their natural key (M5).
# ---------------------------------------------------------------------------


@router.post("/registry/kilns")
async def portal_register_kiln(
    payload: KilnRequest,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await upsert_kiln(session, payload)
    await write_audit(
        session,
        event_type="kiln_registered",
        actor_user_id=user.id,
        payload={"kiln_id": payload.kiln_id},
    )
    await session.commit()
    return result


@router.get("/registry/kilns")
async def portal_list_kilns(
    _user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(select(Kiln).order_by(Kiln.registered_at.desc()))
    ).scalars().all()
    return {
        "kilns": [
            {
                "kiln_id": k.kiln_id,
                "kiln_type": k.kiln_type,
                "material": k.material,
                "weight_kg": k.weight_kg,
                "lifetime_years": k.lifetime_years,
            }
            for k in rows
        ]
    }


@router.post("/registry/operator-training")
async def portal_operator_training(
    payload: OperatorTrainingRequest,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await upsert_operator_training(session, payload)
    await write_audit(
        session,
        event_type="operator_training",
        actor_user_id=user.id,
        payload={"operator_id": payload.operator_id},
    )
    await session.commit()
    return result


@router.post("/registry/supervisor-visit")
async def portal_supervisor_visit(
    payload: SupervisorVisitRequest,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await upsert_supervisor_visit(session, payload)
    await write_audit(
        session,
        event_type="supervisor_visit",
        actor_user_id=user.id,
        payload={"kiln_id": payload.kiln_id},
    )
    await session.commit()
    return result


@router.post("/registry/scale-calibration")
async def portal_scale_calibration(
    payload: ScaleCalibrationRequest,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await upsert_scale_calibration(session, payload)
    await write_audit(
        session,
        event_type="scale_calibration",
        actor_user_id=user.id,
        payload={"scale_id": payload.scale_id},
    )
    await session.commit()
    return result


@router.post("/registry/annual-verification")
async def portal_annual_verification(
    payload: AnnualVerificationRequest,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await upsert_annual_verification(session, payload)
    await write_audit(
        session,
        event_type="annual_verification",
        actor_user_id=user.id,
        payload={"project_id": payload.project_id, "year": payload.year},
    )
    await session.commit()
    return result


# ---------------------------------------------------------------------------
# P2.6 — Deliberate credit issuance. Admin-only, re-verified server-side, and
# recorded in the append-only audit trail.
# ---------------------------------------------------------------------------


@router.post("/batches/{batch_uuid}/issue")
async def issue_credit(
    # PR-1: this flat, no-serial/no-lifecycle path predates the
    # CreditIssuance ledger (portal/issuance_routes.py's
    # `/batches/{batch_uuid}/issuance/issue`) and lacks its serial number,
    # vintage, and enforced independent-verification precondition. Left
    # working as-is (existing callers/tests depend on it) but the ledger
    # path is the authoritative one going forward; this endpoint is a
    # deprecation candidate once callers migrate.
    batch_uuid: str,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    batch = await _load_batch(session, batch_uuid)
    if batch.status == "ISSUED":
        raise HTTPException(status_code=409, detail="already_issued")
    # Never trust the UI: the server's own provisional flag (recomputed from all
    # gates) is the authority — a provisional batch can never be issued.
    if batch.provisional:
        raise HTTPException(status_code=409, detail="batch_provisional")

    batch.status = "ISSUED"
    await write_audit(
        session,
        event_type="credit_issued",
        actor_user_id=user.id,
        batch_uuid=str(batch.batch_uuid),
        payload={
            "net_credit_t_co2e": batch.net_credit_t_co2e,
            "lca_signature": batch.lca_signature,
        },
    )
    await session.commit()
    return {
        "status": "ISSUED",
        "batch_uuid": batch_uuid,
        "net_credit_t_co2e": batch.net_credit_t_co2e,
    }


@router.get("/batches/{batch_uuid}/export/{fmt}")
async def export_batch(
    batch_uuid: str,
    fmt: str,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    """Portal-native registry export (Bearer + admin role).

    Reuses the SAME CSIExportService/RainbowExportService as the admin-secret
    ops endpoints (routers/exports.py), so the browser never needs the admin
    secret. Provisional batches are rejected — a batch that cannot be issued
    cannot be exported.
    """
    from services.export import CSIExportService, RainbowExportService
    from services.methodology import CSI, DEFAULT, RAINBOW, resolve_methodology

    if fmt not in ("csi", "rainbow"):
        raise HTTPException(status_code=400, detail="unknown_export_format")

    batch = await _load_batch(session, batch_uuid)

    # PR-4.2: the requested format must match the batch's project's resolved
    # methodology — UNLESS that project is DEFAULT (no registry_config, or
    # one naming neither known methodology), which is every existing
    # project's actual state today and must keep today's free-choice
    # behavior (the regression guarantee).
    methodology_version = None
    if batch.project_id:
        project = (
            await session.execute(
                select(Project).where(Project.project_id == batch.project_id)
            )
        ).scalar_one_or_none()
        if project is not None and project.registry_config_id:
            cfg = (
                await session.execute(
                    select(RegistryConfig).where(
                        RegistryConfig.config_id == project.registry_config_id
                    )
                )
            ).scalar_one_or_none()
            if cfg is not None:
                methodology_version = cfg.methodology_version
    methodology = resolve_methodology(methodology_version)
    _expected_fmt = {CSI: "csi", RAINBOW: "rainbow"}.get(methodology)
    if _expected_fmt is not None and fmt != _expected_fmt:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "format_does_not_match_project_methodology",
                "expected_format": _expected_fmt,
            },
        )

    if batch.provisional:
        reasons = batch.provisional_reasons
        try:
            parsed = json.loads(reasons) if reasons else []
        except (ValueError, TypeError):
            parsed = []
        raise HTTPException(
            status_code=409,
            detail={"error": "batch_provisional", "reasons": parsed},
        )

    try:
        if fmt == "csi":
            report = await CSIExportService.export_batch_as_csi(batch, session)
        else:
            report = await RainbowExportService.export_batch_as_rainbow(batch, session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await write_audit(
        session,
        event_type="batch_exported",
        actor_user_id=user.id,
        batch_uuid=str(batch.batch_uuid),
        payload={"format": fmt},
    )
    await session.commit()
    return report


@router.get("/batches/{batch_uuid}/audit")
async def batch_audit(
    batch_uuid: str,
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    batch = await _load_batch(session, batch_uuid)
    rows = (
        await session.execute(
            select(AuditEvent)
            .where(AuditEvent.batch_uuid == str(batch.batch_uuid))
            .order_by(AuditEvent.created_at.asc())
        )
    ).scalars().all()
    return {
        "events": [
            {
                "event_type": e.event_type,
                "actor_user_id": e.actor_user_id,
                "payload": json.loads(e.payload_json or "{}"),
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in rows
        ]
    }


# ---------------------------------------------------------------------------
# Farmer API — Portal access
# ---------------------------------------------------------------------------

from models import Farmer, FarmerDocument, FarmerPayment, FarmerConsent
from .schemas import FarmerListResponse, FarmerOut, FarmerDocumentOut, FarmerPaymentOut, FarmerConsentOut

def _farmer_row(f: Farmer) -> dict:
    return {
        "farmer_uuid": f.farmer_uuid,
        "project_id": f.project_id,
        "first_name": f.first_name,
        "last_name": f.last_name,
        "gender": f.gender,
        "guardian_name": f.guardian_name,
        "dob": f.dob.isoformat() if f.dob else None,
        "mobile_number": f.mobile_number,
        "education": f.education,
        "family_size": f.family_size,
        "reported_area": f.reported_area,
        "village": f.village,
        "kyc_status": f.kyc_status,
        "consent_status": f.consent_status,
        "signature_media_id": f.signature_media_id,
        "created_at": f.created_at.isoformat() if f.created_at else None,
        "sync_status": f.sync_status,
        "documents": [],
        "payments": [],
        "consents": []
    }


@router.get("/farmers", response_model=FarmerListResponse)
async def list_farmers(
    _user: PortalUser = Depends(require_role("admin", "verifier")),
    session: AsyncSession = Depends(get_session),
    project_id: Optional[str] = Query(None, description="filter by project_id"),
    search: Optional[str] = Query(None, description="search by name or mobile"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
):
    stmt = select(Farmer)
    if project_id:
        stmt = stmt.where(Farmer.project_id == project_id)
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            (Farmer.first_name.ilike(search_pattern)) |
            (Farmer.last_name.ilike(search_pattern)) |
            (Farmer.mobile_number.ilike(search_pattern))
        )
        
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    
    stmt = stmt.order_by(Farmer.created_at.desc()).offset((page - 1) * size).limit(size)
    rows = (await session.execute(stmt)).scalars().all()
    
    items = []
    for r in rows:
        items.append(_farmer_row(r))
        
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/farmers/{farmer_uuid}", response_model=FarmerOut)
async def get_farmer_detail(
    farmer_uuid: str,
    _user: PortalUser = Depends(require_role("admin", "verifier")),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Farmer).where(Farmer.farmer_uuid == farmer_uuid)
    farmer = (await session.execute(stmt)).scalar_one_or_none()
    
    if not farmer:
        raise HTTPException(status_code=404, detail="farmer_not_found")
        
    res = _farmer_row(farmer)
    
    docs = (await session.execute(select(FarmerDocument).where(FarmerDocument.farmer_uuid == farmer_uuid))).scalars().all()
    pays = (await session.execute(select(FarmerPayment).where(FarmerPayment.farmer_uuid == farmer_uuid))).scalars().all()
    cons = (await session.execute(select(FarmerConsent).where(FarmerConsent.farmer_uuid == farmer_uuid))).scalars().all()
    
    res["documents"] = [{"id": d.id, "doc_type": d.doc_type, "last4": d.last4, "media_id": d.media_id} for d in docs]
    res["payments"] = [{
        "id": p.id, "rail": p.rail, "account_holder": p.account_holder,
        "masked_account": p.masked_account, "ifsc_code": p.ifsc_code,
        "masked_upi_id": p.masked_upi_id, "masked_mfs_id": p.masked_mfs_id
    } for p in pays]
    res["consents"] = [{
        "id": c.id, "fpic_template_id": c.fpic_template_id,
        "signed_pdf_media_id": c.signed_pdf_media_id,
        "holding_photo_media_id": c.holding_photo_media_id,
        "signed_at": c.signed_at.isoformat() if c.signed_at else None,
        "exclusivity_ack": c.exclusivity_ack
    } for c in cons]
    
    return res
