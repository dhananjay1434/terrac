from __future__ import annotations
import hashlib
import re
from pathlib import Path
import uuid
from typing import Optional
from fastapi import APIRouter, Request, Response, Depends, File, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from models import Batch, MediaFile, PyrolysisTelemetry, SourceParcel
import json
from services.evidence import (
    label_media_from_telemetry,
    _assert_batch_ownership,
    _assert_farmer_ownership,
    _assert_dispatch_ownership,
    _assert_day_start_ownership,
    _assert_density_test_ownership,
)
from pydantic import BaseModel, Field
from schemas import MediaUploadResponse

from security import verify_media_signature, verify_signature, _SAFE
from geo import _evaluate_anchor, _parse_exif_gps
from storage import get_storage
from settings import log
from app_factory import UPLOAD_DIR

router = APIRouter()

@router.post(
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
    x_batch_uuid: Optional[str] = Header(None, alias="X-Batch-UUID"),
    x_device_id: str = Header(..., alias="X-Device-Id"),
    x_capture_type: Optional[str] = Header(None, alias="X-Capture-Type"),
    # V8 deferred R1 — entity-scoped media (farmer/dispatch, not a batch).
    x_subject_type: Optional[str] = Header(None, alias="X-Subject-Type"),
    x_subject_uuid: Optional[str] = Header(None, alias="X-Subject-UUID"),
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

    # V8 deferred R1 — resolve exactly one media scope: batch (legacy) XOR
    # subject (farmer/dispatch). Never both, never neither.
    has_batch = bool(x_batch_uuid and x_batch_uuid.strip())
    has_subject = bool(x_subject_type and x_subject_uuid)
    if has_batch and has_subject:
        raise HTTPException(status_code=400, detail="ambiguous_media_scope")
    if not has_batch and not has_subject:
        raise HTTPException(status_code=400, detail="missing_media_scope")
    if has_subject and x_subject_type not in (
        "farmer",
        "dispatch",
        "day_start_audit",
        "density_test",
    ):
        raise HTTPException(status_code=400, detail="invalid_subject_type")

    if x_capture_type is not None and not re.match(
        r"^[a-z0-9_]{1,64}$", x_capture_type
    ):
        raise HTTPException(status_code=400, detail="invalid_capture_type")

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

    # P1-B5: validate the scope identifier BEFORE writing any bytes, so a
    # malformed value (400) can never leave an orphaned object.
    batch_uuid = None
    batch = None
    if has_batch:
        try:
            batch_uuid = str(uuid.UUID(x_batch_uuid))
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="invalid_batch_uuid")

        # Audit fix 3: resolve the batch and enforce ownership BEFORE any bytes or
        # rows are persisted. Previously the ownership 403 fired AFTER the media row
        # was committed; the except-path rollback could not undo that commit, so a
        # rejected upload stranded a row whose bytes were deleted — and the
        # duplicate fast-path then reported stored=True for evidence that no longer
        # existed. Loading the batch first makes rejection side-effect-free.
        stmt = select(Batch).where(Batch.batch_uuid == batch_uuid)
        batch = (await session.execute(stmt)).scalar_one_or_none()
        if batch is not None and batch.device_id is not None and batch.device_id != device_id:
            raise HTTPException(status_code=403, detail="not_your_batch")
    else:
        # V8 deferred R1 (+PR-5.1b: day_start_audit) — entity-scoped media.
        # Validate the subject uuid shape, then enforce the appropriate
        # ownership rule BEFORE any bytes are written (same side-effect-free
        # ordering as the batch path above).
        try:
            subject_uuid = str(uuid.UUID(x_subject_uuid))
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="invalid_subject_uuid")
        if x_subject_type == "farmer":
            await _assert_farmer_ownership(session, subject_uuid, device_id)
        elif x_subject_type == "dispatch":
            await _assert_dispatch_ownership(session, subject_uuid, device_id)
        elif x_subject_type == "day_start_audit":
            await _assert_day_start_ownership(session, subject_uuid, device_id)
        else:  # "density_test" — the only remaining value invalid_subject_type allows through
            await _assert_density_test_ownership(session, subject_uuid, device_id)

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
            capture_type=x_capture_type,
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

        if has_batch:
            media.batch_uuid = batch_uuid

            # Anchor photo to batch if batch was already created (P0-25). The photo
            # only verifies the batch if its hash matches the batch's declared
            # sha256_hash, and the EXIF GPS corroborates the claimed coords (Phase 9).
            if batch:
                parcel_geojson = None
                if getattr(batch, "parcel_uuid", None):
                    sp = (await session.execute(select(SourceParcel).where(SourceParcel.parcel_uuid == batch.parcel_uuid))).scalar_one_or_none()
                    if sp:
                        parcel_geojson = sp.boundary_geojson
                _evaluate_anchor(batch, calculated_hash, exif_lat, exif_lon, parcel_geojson=parcel_geojson)
                session.add(batch)

            session.add(media)

            # Look up telemetry to retroactively label media arriving after telemetry
            telemetry = (
                await session.execute(
                    select(PyrolysisTelemetry).where(PyrolysisTelemetry.batch_uuid == batch_uuid)
                )
            ).scalar_one_or_none()
            if telemetry and telemetry.payload_json:
                try:
                    parsed = json.loads(telemetry.payload_json)
                    await label_media_from_telemetry(session, batch_uuid, parsed.get("smoke_evidence"))
                except (ValueError, TypeError):
                    pass
        else:
            # V8 deferred R1 — entity-scoped media has no batch to anchor/label
            # against; no EXIF-GPS corroboration applies (a signature photo has
            # no batch GPS to corroborate).
            media.subject_type = x_subject_type
            media.subject_uuid = subject_uuid
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


@router.get("/api/v1/batches/{batch_uuid}/media-verdicts")
async def get_media_verdicts(
    batch_uuid: str,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """V8 Part 4 (K) — device-facing read of reviewer verdicts on this batch's
    media, so the app can surface "rejected: <reason>" and prompt a targeted
    recapture instead of the operator learning only when the whole batch is
    provisional. Same ownership rule as the evidence-write endpoints
    (_assert_batch_ownership): a different device's batch is 403; a batch that
    doesn't exist yet (or is unowned) returns an empty list, not an error.
    """
    await _assert_batch_ownership(session, batch_uuid, device_id)
    rows = (
        await session.execute(
            select(MediaFile).where(MediaFile.batch_uuid == batch_uuid)
        )
    ).scalars().all()
    return {
        "media": [
            {
                "operation_id": m.operation_id,
                "capture_type": m.capture_type,
                "verification_status": m.verification_status,
                "verification_remarks": m.verification_remarks,
            }
            for m in rows
            if m.verification_status is not None
        ]
    }
