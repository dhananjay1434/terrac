from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from models import Farmer, FarmerDocument, FarmerPayment, FarmerConsent
from schemas import FarmerCreate
from security import verify_signature

router = APIRouter()


@router.post(
    "/api/v1/farmers",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_farmer(
    payload: FarmerCreate,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
):
    """Device endpoint for farmer registration (upsert by farmer_uuid).

    Requires an Ed25519 signature from an enrolled device.

    ATOMICITY: the farmer row and ALL its children (documents / payments /
    consents) are written in a SINGLE transaction with ONE commit. The prior
    version committed the farmer first, then swallowed any non-mobile
    IntegrityError with a bare `pass`, and STILL returned {"status":"success"}
    — so a failed farmer write reported success, the device dropped its outbox
    row, and the registration was silently lost while orphaned child rows were
    committed anyway. A failed commit now returns a real 4xx/5xx and never a
    false success; a retry reconciles idempotently (delete-then-reinsert
    children, upsert-by-uuid) so the offline outbox can safely replay.
    """
    # Mobile uniqueness is DB-enforced (uq_farmer_project_mobile); this explicit
    # pre-check just turns the race-free common case into a friendly 409 instead
    # of a generic conflict. The DB constraint remains the real guard.
    dup = (
        await session.execute(
            select(Farmer).where(
                Farmer.project_id == payload.project_id,
                Farmer.mobile_number == payload.mobile_number,
                Farmer.farmer_uuid != payload.farmer_uuid,
            )
        )
    ).scalar_one_or_none()
    if dup is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="check-farmer-mobile: Mobile number already registered in this project",
        )

    existing = (
        await session.execute(
            select(Farmer).where(Farmer.farmer_uuid == payload.farmer_uuid)
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.project_id = payload.project_id
        existing.first_name = payload.first_name
        existing.last_name = payload.last_name
        existing.gender = payload.gender
        existing.guardian_name = payload.guardian_name
        existing.dob = payload.dob
        existing.mobile_number = payload.mobile_number
        existing.education = payload.education
        existing.family_size = payload.family_size
        existing.reported_area = payload.reported_area
        existing.village = payload.village
        existing.kyc_status = payload.kyc_status
        existing.consent_status = payload.consent_status
        existing.signature_media_id = payload.signature_media_id
        existing.sync_status = payload.sync_status
        status_code = status.HTTP_200_OK
    else:
        session.add(
            Farmer(
                farmer_uuid=payload.farmer_uuid,
                project_id=payload.project_id,
                first_name=payload.first_name,
                last_name=payload.last_name,
                gender=payload.gender,
                guardian_name=payload.guardian_name,
                dob=payload.dob,
                mobile_number=payload.mobile_number,
                education=payload.education,
                family_size=payload.family_size,
                reported_area=payload.reported_area,
                village=payload.village,
                kyc_status=payload.kyc_status,
                consent_status=payload.consent_status,
                signature_media_id=payload.signature_media_id,
                sync_status=payload.sync_status,
            )
        )
        status_code = status.HTTP_201_CREATED

    # Children: delete + re-insert so an outbox retry is idempotent (no dupes).
    # All of this is part of the SAME transaction as the farmer upsert above.
    await session.execute(
        delete(FarmerDocument).where(FarmerDocument.farmer_uuid == payload.farmer_uuid)
    )
    await session.execute(
        delete(FarmerPayment).where(FarmerPayment.farmer_uuid == payload.farmer_uuid)
    )
    await session.execute(
        delete(FarmerConsent).where(FarmerConsent.farmer_uuid == payload.farmer_uuid)
    )

    for doc in payload.documents:
        session.add(
            FarmerDocument(
                farmer_uuid=payload.farmer_uuid,
                doc_type=doc.doc_type,
                last4=doc.last4,
                media_id=doc.media_id,
            )
        )
    for pay in payload.payments:
        session.add(
            FarmerPayment(
                farmer_uuid=payload.farmer_uuid,
                rail=pay.rail,
                account_holder=pay.account_holder,
                masked_account=pay.masked_account,
                ifsc_code=pay.ifsc_code,
                masked_upi_id=pay.masked_upi_id,
                masked_mfs_id=pay.masked_mfs_id,
            )
        )
    for cons in payload.consents:
        session.add(
            FarmerConsent(
                farmer_uuid=payload.farmer_uuid,
                fpic_template_id=cons.fpic_template_id,
                signed_pdf_media_id=cons.signed_pdf_media_id,
                holding_photo_media_id=cons.holding_photo_media_id,
                signed_at=cons.signed_at,
                exclusivity_ack=cons.exclusivity_ack,
            )
        )

    try:
        await session.commit()
    except IntegrityError:
        # A concurrent request won the race (same mobile, or same farmer_uuid).
        # NEVER return success on a failed write — surface a real conflict so the
        # device retries/reconciles rather than dropping the registration.
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="farmer_registration_conflict",
        )

    return JSONResponse(
        status_code=status_code,
        content={"status": "success", "farmer_uuid": payload.farmer_uuid},
    )
