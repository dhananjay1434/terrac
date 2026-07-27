"""ADR-001 B4.1-4 — ordinal backfill: per-parent sequences, country default,
idempotency, dry-run."""
import pytest
from sqlalchemy import select

from models import Facility, Kiln, Network
from tools.backfill_ordinals import backfill_ordinals


@pytest.mark.asyncio
async def test_assigns_per_parent_ordinals_and_codes(session_factory):
    async with session_factory() as s:
        s.add(Network(network_id="N1", org_id="org-1", name="N1"))
        s.add(Network(network_id="N2", org_id="org-1", name="N2"))
        s.add(Network(network_id="N3", org_id="org-2", name="N3"))
        s.add(Facility(facility_uuid="F1", name="F1", facility_type="artisanal", network_id="N1"))
        s.add(Facility(facility_uuid="F2", name="F2", facility_type="artisanal", network_id="N1"))
        s.add(Kiln(kiln_id="K1", site_id="F1"))
        s.add(Kiln(kiln_id="K2", site_id="F1"))
        await s.commit()

    async with session_factory() as s:
        await backfill_ordinals(s)

    async with session_factory() as s:
        nets = {n.network_id: n for n in (await s.execute(select(Network))).scalars()}
        # org-1's networks sequence 1,2 → A001,A002; org-2 restarts at 1
        assert (nets["N1"].org_ordinal, nets["N1"].network_code) == (1, "A001")
        assert (nets["N2"].org_ordinal, nets["N2"].network_code) == (2, "A002")
        assert (nets["N3"].org_ordinal, nets["N3"].network_code) == (1, "A001")
        assert nets["N1"].country_code == "IN"  # default applied
        facs = {f.facility_uuid: f for f in (await s.execute(select(Facility))).scalars()}
        assert (facs["F1"].site_ordinal, facs["F2"].site_ordinal) == (1, 2)  # per network N1
        kilns = {k.kiln_id: k for k in (await s.execute(select(Kiln))).scalars()}
        assert (kilns["K1"].kiln_ordinal, kilns["K2"].kiln_ordinal) == (1, 2)  # per site F1


@pytest.mark.asyncio
async def test_dry_run_persists_nothing_and_rerun_is_noop(session_factory):
    async with session_factory() as s:
        s.add(Network(network_id="N1", org_id="org-1", name="N1"))
        await s.commit()

    async with session_factory() as s:
        plan = await backfill_ordinals(s, dry_run=True)
        assert len(plan["networks"]) == 1
    async with session_factory() as s:
        assert (await s.execute(select(Network))).scalar_one().org_ordinal is None

    async with session_factory() as s:
        await backfill_ordinals(s)
    async with session_factory() as s:
        plan2 = await backfill_ordinals(s)
        assert plan2["networks"] == []  # nothing left to assign
