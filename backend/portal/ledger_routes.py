"""Portal Ledgers API (M5.1)."""

from datetime import date, datetime, time, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import Batch
from portal.auth import require_role
from feature_flags import flag_active
from ledger_aggregate import build_biomass_ledger

router = APIRouter(prefix="/api/v1/portal/ledgers", tags=["portal", "ledgers"])

@router.get("/biomass")
async def get_biomass_ledger(
    user=Depends(require_role()),
    session: AsyncSession = Depends(get_session),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    bucket: str = Query("month", pattern="^(day|month)$"),
    site_id: Optional[str] = None,
    network_id: Optional[str] = None,
):
    # R4: ledgers is an opt-out display feature (default ON). If a client turned it
    # off, return an empty-but-valid ledger of the same shape.
    if not await flag_active(session, "ledgers_v2", getattr(user, "org_id", None)):
        return build_biomass_ledger([], bucket=bucket)

    # Base query for batches
    stmt = select(Batch)
    
    if site_id:
        stmt = stmt.where(Batch.site_id == site_id)
    if network_id:
        stmt = stmt.where(Batch.network_id == network_id)
        
    # We load all matching batches into memory since aggregation requires full visibility.
    # In a production environment with millions of rows, this should be done in SQL,
    # but the blueprint specifies using the pure python `build_biomass_ledger` aggregator.
    batches = (await session.execute(stmt)).scalars().all()
    
    # Map Batch fields to the expected attribute names for build_biomass_ledger
    # The aggregator expects: date, species, kg, batch_code
    class RowAdapter:
        def __init__(self, b: Batch):
            self.date = b.harvest_timestamp
            self.species = b.feedstock_species
            self.kg = b.biomass_input_kg
            self.batch_code = b.batch_code

    adapted_rows = [RowAdapter(b) for b in batches]
    
    aware_from = None
    if from_date:
        aware_from = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
        
    aware_to = None
    if to_date:
        aware_to = datetime.combine(to_date, time.max, tzinfo=timezone.utc)

    ledger = build_biomass_ledger(
        adapted_rows,
        date_from=aware_from,
        date_to=aware_to,
        bucket=bucket,
    )
    
    return ledger
