"""FM-0 — credit_engine wiring test for the feedstock positive-list gate.

NOTE: BatchPayload.feedstock_species already has a Pydantic field_validator
(schemas.py) that rejects any species outside the static module CORG_TABLE
at batch-create time — so an "unknown species" batch can never arrive via
the normal signed POST /api/v1/batches path today. That validator is
project-blind (it has no way to see the batch's project_id and therefore
can't validate against a per-project RegistryConfig.corg_table override),
which FM-1 must address. Until then, an unknown-species row can still exist
via direct DB writes (legacy data, admin tooling, migrations) — this test
constructs the Batch directly via the ORM (bypassing the HTTP layer, the
same way test_registry_config.py's _resolve_lca_config tests do) and calls
recompute_batch_credit directly, proving the recompute-level gate holds
regardless of how the row got there.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from credit_engine import recompute_batch_credit
from models import Batch

pytestmark = pytest.mark.asyncio


def _mk_batch(*, feedstock_species: str) -> Batch:
    buid = str(uuid.uuid4())
    return Batch(
        batch_uuid=buid,
        operation_id=f"op-{buid[:8]}",
        feedstock_species=feedstock_species,
        harvest_timestamp=datetime(2026, 7, 1, tzinfo=timezone.utc),
        moisture_percent=12.0,
        harvest_uptime_seconds=100,
    )


async def _reasons(session_factory, buid):
    async with session_factory() as s:
        b = (
            await s.execute(select(Batch).where(Batch.batch_uuid == buid))
        ).scalar_one()
        import json

        return json.loads(b.provisional_reasons or "[]")


async def test_known_species_lantana_is_not_flagged(session_factory):
    """Regression pin: every existing batch's feedstock (Lantana_camara, in
    the default CORG_TABLE) must NOT be flagged by this new gate."""
    batch = _mk_batch(feedstock_species="Lantana_camara")
    async with session_factory() as session:
        session.add(batch)
        await session.commit()
        await recompute_batch_credit(session, batch)
        await session.commit()

    reasons = await _reasons(session_factory, batch.batch_uuid)
    assert "feedstock_not_in_positive_list" not in reasons


async def test_unknown_species_is_flagged_provisional(session_factory):
    batch = _mk_batch(feedstock_species="Made_up_grass")
    async with session_factory() as session:
        session.add(batch)
        await session.commit()
        await recompute_batch_credit(session, batch)
        await session.commit()

    reasons = await _reasons(session_factory, batch.batch_uuid)
    assert "feedstock_not_in_positive_list" in reasons
