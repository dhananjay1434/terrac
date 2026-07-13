from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from models import MoistureReading, CompositePileSample, TransportEvent, PyrolysisTelemetry, YieldMetrics, SystemMetadata, EndUseApplication
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from schemas import _BatchScopedPayload
from schemas import (
    ApplicationPayload,
    CompositeSamplePayload,
    MetadataPayload,
    MoisturePayload,
    TelemetryPayload,
    TransportEventPayload,
    YieldPayload,
)

from security import verify_signature
from services.evidence import _assert_batch_ownership, _upsert_one_to_one_evidence, _recompute_if_batch_exists, _assert_same_uuid

router = APIRouter()

@router.post("/api/v1/moisture", status_code=status.HTTP_201_CREATED)
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
@router.post("/api/v1/composite-sample", status_code=status.HTTP_201_CREATED)
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
@router.post("/api/v1/transport", status_code=status.HTTP_201_CREATED)
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
@router.post("/api/v1/telemetry", status_code=status.HTTP_201_CREATED)
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
@router.post("/api/v1/yield", status_code=status.HTTP_201_CREATED)
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
@router.post("/api/v1/metadata", status_code=status.HTTP_201_CREATED)
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
@router.post("/api/v1/application", status_code=status.HTTP_201_CREATED)
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
