"""M2.5 (ADR-001 A2/A3) — credit bridge: burn window excludes ramp/cool-down,
T4 is context-only, gaps only shorten, <60 buckets → None, and parity with an
equivalent legacy array."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from models import TelemetryPoint
from telemetry_bridge import BURN_WINDOW_FLOOR_C, temperature_array_for

_T0 = datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc)


async def _add(session, batch_uuid, channel, values, *, base=0, period=10):
    for i, v in enumerate(values):
        session.add(TelemetryPoint(
            batch_uuid=batch_uuid,
            channel=channel,
            ts=_T0 + timedelta(seconds=period * (base + i)),
            value=float(v),
        ))
    await session.flush()


@pytest.mark.asyncio
async def test_burn_window_excludes_ramp_and_cooldown(session_factory):
    async with session_factory() as s:
        await _add(s, "b1", "T1", [100, 200, 300] + [500.0] * 70 + [300, 200, 100])
        await s.commit()
    async with session_factory() as s:
        arr = await temperature_array_for(s, "b1")
    assert arr is not None
    assert len(arr) == 70  # only the hot window; ramp + cool-down excluded
    assert min(arr) >= BURN_WINDOW_FLOOR_C
    assert all(v == 500.0 for v in arr)


@pytest.mark.asyncio
async def test_returns_none_below_min_buckets(session_factory):
    async with session_factory() as s:
        await _add(s, "b2", "T1", [500.0] * 30)  # only 30 in-window buckets < 60
        await s.commit()
    async with session_factory() as s:
        assert await temperature_array_for(s, "b2") is None


@pytest.mark.asyncio
async def test_t4_is_ignored_for_compliance(session_factory):
    async with session_factory() as s:
        await _add(s, "b3", "T1", [500.0] * 70)
        await _add(s, "b3", "T4", [50.0] * 70)  # cool base probe must NOT lower the array
        await s.commit()
    async with session_factory() as s:
        arr = await temperature_array_for(s, "b3")
    assert arr is not None and all(v == 500.0 for v in arr)


@pytest.mark.asyncio
async def test_gap_only_shortens_never_extends(session_factory):
    async with session_factory() as s:
        await _add(s, "gapless", "T1", [500.0] * 70)
        await _add(s, "gapped", "T1", [500.0] * 35, base=0)        # buckets 0..34
        await _add(s, "gapped", "T1", [500.0] * 35, base=55)       # buckets 55..89 (20-bucket hole)
        await s.commit()
    async with session_factory() as s:
        gapless = await temperature_array_for(s, "gapless")
        gapped = await temperature_array_for(s, "gapped")
    assert len(gapless) == 70
    assert len(gapped) == 70          # the 20-bucket hole is excluded, NOT filled to 90
    assert len(gapped) <= len(gapless)  # a gap can only shorten, never extend


@pytest.mark.asyncio
async def test_parity_with_equivalent_legacy_array(session_factory):
    from corroboration import derive_plausibility_reasons

    hot = [500.0] * 70
    async with session_factory() as s:
        await _add(s, "instr", "T1", hot)
        await s.commit()
    async with session_factory() as s:
        bridge = await temperature_array_for(s, "instr")

    common = dict(biomass_input_kg=1000.0, wet_yield_kg=250.0, moisture_values=[10.0, 11.0, 12.0])
    r_bridge = derive_plausibility_reasons(min_temp=min(bridge), temperature_readings=bridge, **common)
    r_legacy = derive_plausibility_reasons(min_temp=min(hot), temperature_readings=hot, **common)
    assert r_bridge == r_legacy  # instrumented verdict identical to legacy
