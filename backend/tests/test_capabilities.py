"""H3 - capability resolver invariants (the safety guarantee behind one-click toggles)."""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from models import Batch, PyrolysisTelemetry, TelemetryPoint
from capabilities import resolve_batch_capabilities

pytestmark = pytest.mark.asyncio


def _batch(**over):
    base = dict(
        batch_uuid=str(uuid.uuid4()), operation_id="op-" + uuid.uuid4().hex[:8],
        feedstock_species="Lantana_camara", harvest_timestamp=datetime.now(timezone.utc),
        moisture_percent=12.0, harvest_uptime_seconds=0,
    )
    base.update(over)
    return Batch(**base)


async def _resolve(session_factory, batch):
    async with session_factory() as s:
        b = (await s.execute(select(Batch).where(Batch.batch_uuid == batch.batch_uuid))).scalar_one()
        return await resolve_batch_capabilities(s, b)


async def test_no_data_no_flags(session_factory):
    b = _batch()
    async with session_factory() as s:
        s.add(b); await s.commit()
    caps = await _resolve(session_factory, b)
    assert caps["telemetry"] == "none" and caps["tier"] == "none" and caps["load"] is False
    assert caps["timeline"] is True and caps["ledgers"] is True   # opt-out default ON
    assert caps["provenance_code"] is False


async def test_legacy_resolves_legacy(session_factory):
    b = _batch()
    async with session_factory() as s:
        s.add(b)
        s.add(PyrolysisTelemetry(telemetry_uuid=str(uuid.uuid4()), batch_uuid=b.batch_uuid,
            payload_json='{"temperature_readings":[400.0,450.0]}'))
        await s.commit()
    caps = await _resolve(session_factory, b)
    assert caps["telemetry"] == "legacy"


async def test_v2_points_do_not_claim_v2_while_flag_off(session_factory):
    """Data present but telemetry_v2 OFF -> never claim v2 (opt-in invariant)."""
    b = _batch()
    async with session_factory() as s:
        s.add(b)
        s.add(TelemetryPoint(batch_uuid=b.batch_uuid, channel="T1",
            ts=datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc), value=400.0))
        await s.commit()
    caps = await _resolve(session_factory, b)
    assert caps["telemetry"] != "v2", "telemetry_v2 is opt-in; must not claim v2 while flag off"
    assert caps["tier"] == "none"
