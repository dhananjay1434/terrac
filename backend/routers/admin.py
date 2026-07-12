from __future__ import annotations
from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from schemas import KilnRequest, OperatorTrainingRequest, SupervisorVisitRequest, ScaleCalibrationRequest, AnnualVerificationRequest
from security import _require_admin
from services.registry import upsert_kiln, upsert_operator_training, upsert_supervisor_visit, upsert_scale_calibration, upsert_annual_verification

router = APIRouter()

@router.post("/api/v1/admin/kiln", status_code=status.HTTP_200_OK)
async def register_kiln(
    payload: KilnRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    """Register/update a project kiln (C8). Upsert by kiln_id — the methodology
    says kiln data is captured once and updated when kilns change."""
    _require_admin(x_admin_secret)
    return await upsert_kiln(session, payload)
@router.post("/api/v1/admin/operator-training", status_code=status.HTTP_201_CREATED)
async def register_operator_training(
    payload: OperatorTrainingRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(x_admin_secret)
    return await upsert_operator_training(session, payload)
@router.post("/api/v1/admin/supervisor-visit", status_code=status.HTTP_201_CREATED)
async def register_supervisor_visit(
    payload: SupervisorVisitRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(x_admin_secret)
    return await upsert_supervisor_visit(session, payload)
@router.post("/api/v1/admin/scale-calibration", status_code=status.HTTP_201_CREATED)
async def register_scale_calibration(
    payload: ScaleCalibrationRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(x_admin_secret)
    return await upsert_scale_calibration(session, payload)
@router.post("/api/v1/admin/annual-verification", status_code=status.HTTP_200_OK)
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
