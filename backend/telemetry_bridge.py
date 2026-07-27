"""M2.5 credit bridge (ADR-001 A2/A3) — turn streamed thermocouple points into
the legacy compliance temperature array, CONSERVATIVELY.

- Compliance uses only T1-T3 (A2: T4 is the base probe and legitimately cools to
  150-450 C below the pyrolysis front — including it would fail good burns).
- The array is the BURN WINDOW only (A3): between the first and last time
  max(T1,T2,T3) crosses 350 C. Ramp-up and cool-down are excluded from
  compliance (but retained in storage/charts) — otherwise a monitored cool-down
  drags a legitimate burn under the sustain fraction (Global Rule 10 violation).
- 10 s buckets, bucket value = MAX across probes+samples (audit A4). Gaps are
  excluded, never interpolated → a gap can only SHORTEN the window, never extend
  eligibility. Fewer than MIN_TEMPERATURE_SAMPLES in-window buckets → None (no
  claim), exactly like a short legacy log.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import TelemetryPoint

try:  # single source of truth for the thresholds (ADR-001 A5)
    from corroboration import (  # type: ignore
        MIN_TEMPERATURE_SAMPLES as _MIN_BUCKETS,
        PYROLYSIS_MIN_C as _FLOOR,
    )
except Exception:  # pragma: no cover - defensive if the import shape changes
    _FLOOR = 350.0
    _MIN_BUCKETS = 60

COMPLIANCE_CHANNELS: tuple[str, ...] = ("T1", "T2", "T3")  # ADR-001 A2 — T4 context only
BURN_WINDOW_FLOOR_C: float = _FLOOR                          # ADR-001 A3 (mirrors PYROLYSIS_MIN_C)
_BUCKET_S = 10


async def temperature_array_for(
    session: AsyncSession, batch_uuid: str
) -> list[float] | None:
    rows = (
        await session.execute(
            select(TelemetryPoint.ts, TelemetryPoint.value)
            .where(TelemetryPoint.batch_uuid == batch_uuid)
            .where(TelemetryPoint.channel.in_(COMPLIANCE_CHANNELS))
            .order_by(TelemetryPoint.ts)
        )
    ).all()
    if not rows:
        return None

    # 10 s buckets keyed relative to the first sample (tz-agnostic — only spacing
    # matters). Bucket value = max across all probes+samples in the bucket.
    t0 = rows[0][0]
    buckets: dict[int, float] = {}
    for ts, value in rows:
        key = int((ts - t0).total_seconds() // _BUCKET_S)
        if key not in buckets or value > buckets[key]:
            buckets[key] = value

    ordered = sorted(buckets.items())
    hot = [k for k, v in ordered if v >= BURN_WINDOW_FLOOR_C]
    if not hot:
        return None
    start, end = hot[0], hot[-1]
    # in-window buckets that actually exist — gaps (missing keys) are excluded,
    # never zero-filled or interpolated.
    array = [v for k, v in ordered if start <= k <= end]
    if len(array) < _MIN_BUCKETS:
        return None
    return array
