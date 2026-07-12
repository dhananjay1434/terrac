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
