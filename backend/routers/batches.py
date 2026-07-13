from __future__ import annotations
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Response, Depends, Header, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from models import Batch, MediaFile
from geo import haversine_km, _evaluate_anchor
from schemas import BatchPayload, BatchResponse
from security import verify_signature
from credit_engine import recompute_batch_credit
from storage import get_storage
from settings import log
from jsonsafe import _as_utc

router = APIRouter()

@router.post(
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
