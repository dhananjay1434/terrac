import json
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from jsonsafe import _safe_json, _as_utc
from models import Kiln, OperatorTraining, SupervisorVisit, ScaleCalibration, AnnualVerification

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

def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp to an aware UTC datetime, or 400 on garbage."""
    if s is None:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="invalid_timestamp")
    return _as_utc(dt)

