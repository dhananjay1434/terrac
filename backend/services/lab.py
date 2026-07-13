import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from models import Batch
from credit_engine import recompute_batch_credit

async def apply_lab_results(
    session: AsyncSession,
    batch: Batch,
    *,
    lab_h_corg: Optional[float] = None,
    organic_carbon_pct: Optional[float] = None,
    biochar_moisture_samples: Optional[list] = None,
    dry_bulk_density: Optional[float] = None,
    inertinite_pct: Optional[float] = None,
    residual_corg_pct: Optional[float] = None,
    ro_measurements_count: Optional[int] = None,
) -> None:
    """Persist the non-credit lab verification fields, then recompute the batch
    credit. THE single lab-ingestion path — reused by the admin `/lab` route and
    the portal `POST /batches/{uuid}/lab-results` (P2.4) so gate flips are
    identical across channels. The caller commits.
    """
    if biochar_moisture_samples is not None:
        batch.biochar_moisture_samples_json = json.dumps(biochar_moisture_samples)
    if dry_bulk_density is not None:
        batch.dry_bulk_density = dry_bulk_density
    if inertinite_pct is not None:
        batch.inertinite_pct = inertinite_pct
    if residual_corg_pct is not None:
        batch.residual_corg_pct = residual_corg_pct
    if ro_measurements_count is not None:
        batch.ro_measurements_count = ro_measurements_count
    await recompute_batch_credit(
        session, batch, lab_h_corg=lab_h_corg, lab_corg=organic_carbon_pct
    )

