"""Portal Ledgers API (M5.1)."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import Batch
from portal.auth import require_role
from ledger_aggregate import build_biomass_ledger

router = APIRouter(prefix="/api/v1/portal/ledgers", tags=["portal", "ledgers"])

@router.get("/biomass")
async def get_biomass_ledger(
    _user=Depends(require_role()),
    session: AsyncSession = Depends(get_session),
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    bucket: str = Query("month", pattern="^(day|month)$"),
    site_id: Optional[str] = None,
    network_id: Optional[str] = None,
):
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
    
    ledger = build_biomass_ledger(
        adapted_rows,
        date_from=from_date,
        date_to=to_date,
        bucket=bucket,
    )
    
    return ledger
