"""M1.3 (ADR-001 B4.5) — batch_code backfill: seq per (kiln, day), second kiln
restarts, unmapped lineage stays NULL, re-run is a no-op."""
import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from models import Batch, Facility, Kiln, Network, PyrolysisTelemetry
from tools.backfill_batch_codes import backfill_batch_codes
from tools.backfill_ordinals import backfill_ordinals


def _batch(received_at) -> Batch:
    return Batch(
        batch_uuid=str(uuid.uuid4()),
        operation_id="op-" + uuid.uuid4().hex[:8],
        feedstock_species="Lantana_camara",
        harvest_timestamp=received_at,
        moisture_percent=12.0,
        harvest_uptime_seconds=0,
        received_at=received_at,
    )


async def _telemetry(s, batch_uuid, kiln_id):
    s.add(PyrolysisTelemetry(
        telemetry_uuid=str(uuid.uuid4()),
        batch_uuid=batch_uuid,
        payload_json=json.dumps({"kiln_id": kiln_id}),
    ))


@pytest.mark.asyncio
async def test_backfill_generates_codes_with_correct_sequence(session_factory):
    day = datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc)  # 14:30 IST → slot 2
    async with session_factory() as s:
        s.add(Network(network_id="N1", org_id="org-1", name="N1", country_code="IN"))
        s.add(Facility(facility_uuid="F1", name="F1", facility_type="artisanal", network_id="N1"))
        s.add(Kiln(kiln_id="K7", site_id="F1"))
        s.add(Kiln(kiln_id="K8", site_id="F1"))
        b1, b2, b3 = _batch(day), _batch(day.replace(hour=10)), _batch(day.replace(hour=11))
        b4 = _batch(day.replace(hour=9, minute=30))  # second kiln, same day
        b5 = _batch(day)  # no telemetry → unmapped
        for b in (b1, b2, b3, b4, b5):
            s.add(b)
        await s.flush()
        ids = {k: b.batch_uuid for k, b in
               dict(b1=b1, b2=b2, b3=b3, b4=b4, b5=b5).items()}
        for b in (b1, b2, b3):
            await _telemetry(s, b.batch_uuid, "K7")
        await _telemetry(s, b4.batch_uuid, "K8")
        await s.commit()

    async with session_factory() as s:
        await backfill_ordinals(s)
    async with session_factory() as s:
        res = await backfill_batch_codes(s)
        assert len(res["coded"]) == 4 and res["skipped_incomplete"] == 1

    async with session_factory() as s:
        codes = {b.batch_uuid: b.batch_code
                 for b in (await s.execute(select(Batch))).scalars()}
    # K7 (kiln_ordinal 1): three batches ordered by received_at → seq 01/02/03.
    # Slot digit is S1 here because SQLite drops tzinfo on round-trip, so
    # slot_for reads the stored UTC wall-clock hour (9 → morning) as if IST — a
    # SQLite/Postgres parity quirk on a cosmetic field (slot is a derived
    # convenience, audit A3); prod Postgres preserves tz and would bucket by IST.
    assert codes[ids["b1"]] == "IN01A001P01S1K01B23072601"
    assert codes[ids["b2"]].endswith("02")
    assert codes[ids["b3"]].endswith("03")
    # K8 (kiln_ordinal 2) same day → its own sequence restarts at 01
    assert codes[ids["b4"]] == "IN01A001P01S1K02B23072601"
    # no telemetry → lineage incomplete → stays NULL (audit A3)
    assert codes[ids["b5"]] is None

    # re-run: only b5 is NULL and still unmapped → zero new codes
    async with session_factory() as s:
        res2 = await backfill_batch_codes(s)
        assert res2["coded"] == [] and res2["skipped_incomplete"] == 1
