"""M3.1 batch_stage_events — schema round-trip, projection, backfill idempotency.

Tests the ORM model (BatchStageEvent), the stage_projection pure function,
and the schema constraints (stage whitelist, unique batch+stage).
Uses the shared conftest fixtures (test_engine, session_factory).
"""
import uuid as _uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models import Batch, BatchStageEvent
from stage_projection import STAGE_ORDER, StageEvent, project_stages

pytestmark = pytest.mark.asyncio

_T0 = datetime(2026, 7, 22, 13, 0, 0, tzinfo=timezone.utc)


def _batch(uuid: str | None = None) -> Batch:
    return Batch(
        batch_uuid=uuid or str(_uuid.uuid4()),
        operation_id=f"op-{_uuid.uuid4().hex[:8]}",
        feedstock_species="Lantana_camara",
        harvest_timestamp=_T0,
        moisture_percent=12.0,
        harvest_uptime_seconds=100,
        device_id="edge-1",
        received_at=_T0 + timedelta(hours=4),
    )


# ── Schema tests (use conftest session_factory) ──────────────────────────────

async def test_stage_event_round_trip(session_factory):
    """Insert a stage event and read it back."""
    async with session_factory() as session:
        b = _batch()
        session.add(b)
        session.add(
            BatchStageEvent(
                batch_uuid=b.batch_uuid,
                stage="firing",
                started_at=_T0,
                ended_at=_T0 + timedelta(hours=2),
                source="projected",
            )
        )
        await session.commit()

        row = (
            await session.execute(
                select(BatchStageEvent).where(
                    BatchStageEvent.batch_uuid == b.batch_uuid
                )
            )
        ).scalar_one()
        assert row.stage == "firing"
        assert row.source == "projected"
        assert row.started_at is not None
        assert row.ended_at is not None


async def test_unique_batch_stage_constraint(session_factory):
    """Same (batch_uuid, stage) pair rejects duplicate."""
    async with session_factory() as session:
        b = _batch()
        session.add(b)
        session.add(
            BatchStageEvent(
                batch_uuid=b.batch_uuid, stage="sourcing",
                started_at=_T0, source="projected",
            )
        )
        await session.commit()

    async with session_factory() as session:
        session.add(
            BatchStageEvent(
                batch_uuid=b.batch_uuid, stage="sourcing",
                started_at=_T0, source="admin",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_multiple_stages_per_batch(session_factory):
    """One batch can have many different stages."""
    async with session_factory() as session:
        b = _batch()
        session.add(b)
        for stage in ("sourcing", "firing", "quenching", "yield", "application"):
            session.add(
                BatchStageEvent(
                    batch_uuid=b.batch_uuid, stage=stage,
                    started_at=_T0, source="projected",
                )
            )
        await session.commit()

        rows = (
            await session.execute(
                select(BatchStageEvent).where(
                    BatchStageEvent.batch_uuid == b.batch_uuid
                )
            )
        ).scalars().all()
        assert len(rows) == 5


# ── Projection tests (pure, no DB) ──────────────────────────────────────────

def test_rich_batch_projects_expected_stages():
    """A batch with full evidence produces the expected stages."""
    batch = {"harvest_timestamp": _T0, "received_at": _T0 + timedelta(hours=4)}
    media = [
        {"capture_type": "moisture", "uploaded_at": _T0 + timedelta(minutes=10)},
        {"capture_type": "flame_curtain", "uploaded_at": _T0 + timedelta(minutes=30)},
        {"capture_type": "quenching", "uploaded_at": _T0 + timedelta(hours=2)},
        {"capture_type": "post_burn_mass", "uploaded_at": _T0 + timedelta(hours=3)},
    ]
    telemetry = {"t_start": _T0 + timedelta(minutes=20), "t_end": _T0 + timedelta(hours=2)}
    dispatches = [{"created_at": _T0 + timedelta(hours=5), "received_at": _T0 + timedelta(hours=8)}]
    applications = [{"delivery_date": _T0 + timedelta(days=3)}]

    stages = project_stages(
        batch=batch, media=media, telemetry=telemetry,
        dispatches=dispatches, applications=applications,
    )
    stage_names = [s.stage for s in stages]
    assert "sourcing" in stage_names
    assert "moisture" in stage_names
    assert "firing" in stage_names
    assert "quenching" in stage_names
    assert "yield" in stage_names
    assert "dispatch" in stage_names
    assert "application" in stage_names


def test_sparse_batch_produces_sparse_stages():
    """A batch with minimal evidence only produces stages it has evidence for."""
    batch = {"harvest_timestamp": _T0, "received_at": _T0 + timedelta(hours=1)}
    stages = project_stages(batch=batch, media=[], telemetry=None)
    stage_names = [s.stage for s in stages]
    assert stage_names == ["sourcing"]


def test_never_fabricates_stages():
    """A batch with no evidence produces no stages at all."""
    batch = {"harvest_timestamp": None, "received_at": None}
    stages = project_stages(batch=batch, media=[])
    assert stages == []


def test_stages_sorted_by_custody_order():
    """Stages are always sorted by STAGE_ORDER regardless of input order."""
    batch = {"harvest_timestamp": None, "received_at": None}
    media = [
        {"capture_type": "end_use", "uploaded_at": _T0},
        {"capture_type": "moisture", "uploaded_at": _T0},
        {"capture_type": "flame_curtain", "uploaded_at": _T0},
    ]
    stages = project_stages(batch=batch, media=media)
    stage_names = [s.stage for s in stages]
    assert stage_names == ["moisture", "firing", "application"]
    indices = [STAGE_ORDER.index(s) for s in stage_names]
    assert indices == sorted(indices)


def test_smoke_captures_map_to_firing():
    """Smoke opacity captures map to firing stage."""
    batch = {"harvest_timestamp": None, "received_at": None}
    media = [
        {"capture_type": "smoke_50", "uploaded_at": _T0},
        {"capture_type": "100", "uploaded_at": _T0 + timedelta(minutes=5)},
    ]
    stages = project_stages(batch=batch, media=media)
    assert len(stages) == 1
    assert stages[0].stage == "firing"


# ── Backfill idempotency ─────────────────────────────────────────────────────

async def test_backfill_idempotency(session_factory):
    """Re-inserting projected stages for a batch that already has them fails."""
    async with session_factory() as session:
        b = _batch()
        session.add(b)
        session.add(
            BatchStageEvent(
                batch_uuid=b.batch_uuid, stage="sourcing",
                started_at=_T0, source="projected",
            )
        )
        await session.commit()
        uuid = b.batch_uuid

    async with session_factory() as session:
        session.add(
            BatchStageEvent(
                batch_uuid=uuid, stage="sourcing",
                started_at=_T0, source="projected",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
