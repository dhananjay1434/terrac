"""M1.1 — hierarchy_v2 schema: round-trip, sensor_profile whitelist/default,
batch_code uniqueness. Schema is built from Base.metadata by the fixtures."""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models import Batch, Facility, Kiln, Network


def _batch(**over) -> Batch:
    base = dict(
        batch_uuid=str(uuid.uuid4()),
        operation_id="hv2-" + uuid.uuid4().hex[:8],
        feedstock_species="Lantana_camara",
        harvest_timestamp=datetime.now(timezone.utc),
        moisture_percent=12.0,
        harvest_uptime_seconds=0,
    )
    base.update(over)
    return Batch(**base)


@pytest.mark.asyncio
async def test_hierarchy_roundtrip(session_factory):
    async with session_factory() as s:
        s.add(Network(network_id="NET-1", org_id="org-1", name="North Net", country_code="IN"))
        s.add(Facility(
            facility_uuid="FAC-1", name="Site A", facility_type="artisanal",
            network_id="NET-1", site_code="P01",
        ))
        s.add(Kiln(kiln_id="KILN-1", site_id="FAC-1", kiln_code="K01", sensor_profile="full"))
        s.add(_batch(batch_code="IN01A001P03S2K07B23072601", network_id="NET-1", site_id="FAC-1"))
        await s.commit()
    async with session_factory() as s:
        net = (await s.execute(select(Network).where(Network.network_id == "NET-1"))).scalar_one()
        assert (net.name, net.country_code, net.org_id) == ("North Net", "IN", "org-1")
        fac = (await s.execute(select(Facility).where(Facility.facility_uuid == "FAC-1"))).scalar_one()
        assert (fac.network_id, fac.site_code) == ("NET-1", "P01")
        kiln = (await s.execute(select(Kiln).where(Kiln.kiln_id == "KILN-1"))).scalar_one()
        assert (kiln.site_id, kiln.kiln_code, kiln.sensor_profile) == ("FAC-1", "K01", "full")
        b = (await s.execute(
            select(Batch).where(Batch.batch_code == "IN01A001P03S2K07B23072601")
        )).scalar_one()
        assert (b.network_id, b.site_id) == ("NET-1", "FAC-1")


@pytest.mark.asyncio
async def test_kiln_sensor_profile_default_none(session_factory):
    async with session_factory() as s:
        s.add(Kiln(kiln_id="KILN-DEF"))
        await s.commit()
    async with session_factory() as s:
        kiln = (await s.execute(select(Kiln).where(Kiln.kiln_id == "KILN-DEF"))).scalar_one()
        assert kiln.sensor_profile == "none"


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", ["none", "load_only", "thermal_only", "full"])
async def test_kiln_sensor_profile_accepts_whitelist(session_factory, profile):
    async with session_factory() as s:
        s.add(Kiln(kiln_id=f"KILN-{profile}", sensor_profile=profile))
        await s.commit()


@pytest.mark.asyncio
async def test_kiln_sensor_profile_rejects_invalid(session_factory):
    async with session_factory() as s:
        s.add(Kiln(kiln_id="KILN-BAD", sensor_profile="bogus"))
        with pytest.raises(IntegrityError):
            await s.commit()


@pytest.mark.asyncio
async def test_batch_code_is_unique(session_factory):
    async with session_factory() as s:
        s.add(_batch(batch_code="DUP-CODE-01"))
        await s.commit()
    async with session_factory() as s:
        s.add(_batch(batch_code="DUP-CODE-01"))
        with pytest.raises(IntegrityError):
            await s.commit()
