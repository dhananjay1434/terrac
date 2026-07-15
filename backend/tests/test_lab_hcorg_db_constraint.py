"""Phase 15-D — lab_h_corg range is enforced at the DB layer, not only the API.

A DB CHECK constraint rejects an out-of-range permanence ratio even if some future
write path bypasses the LabHCorgRequest Pydantic bound. Also pins the H:Corg 0.4
tier boundary behavior (methodology decision — documented, not silently changed).
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from models import Batch
from lca_engine import step3_cremain


def _batch(lab_h_corg):
    return Batch(
        batch_uuid=str(uuid.uuid4()),
        operation_id="ck-" + uuid.uuid4().hex[:8],
        feedstock_species="Lantana_camara",
        harvest_timestamp=datetime.now(timezone.utc),
        moisture_percent=12.0,
        harvest_uptime_seconds=0,
        lab_h_corg=lab_h_corg,
    )


@pytest.mark.asyncio
async def test_db_rejects_out_of_range_lab_h_corg(session_factory):
    async with session_factory() as s:
        s.add(_batch(0.01))  # below the 0.1 floor — the forged-permanence attack value
        with pytest.raises(IntegrityError):
            await s.commit()


@pytest.mark.asyncio
async def test_db_accepts_in_range_and_null_lab_h_corg(session_factory):
    async with session_factory() as s:
        s.add(_batch(0.3))
        s.add(_batch(None))
        await s.commit()  # both valid — no raise


def test_hcorg_tier_boundary_is_pinned():
    # Methodology decision (documented, not silently changed): 0.4 is the CSI tier
    # boundary. Pin the current behavior so any future change is deliberate.
    just_below = step3_cremain(1.0, 1.0, h_corg_ratio=0.399)
    at_or_above = step3_cremain(1.0, 1.0, h_corg_ratio=0.400)
    assert just_below > at_or_above  # top-tier permanence earns more
    assert abs(at_or_above - 0.70) < 1e-9  # >=0.4 branch → flat 0.70 retention
