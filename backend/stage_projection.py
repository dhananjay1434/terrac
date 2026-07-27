"""Pure stage-timeline projection (M3.1).

Derives a batch's custody-chain stages from whatever evidence exists — media
capture types, the burn's telemetry/timestamps, dispatch rows, application rows.
The absence of evidence for a stage produces NO stage row (Global Rule 10 /
audit: absence is evidence, never fabricated).

This module is DELIBERATELY pure and ORM-free: it accepts normalized plain
inputs (dicts OR any object exposing the same attributes — `_get` handles both),
so it unit-tests in isolation and the M3.1 backfill tool (coordinator-owned,
which reads the real ORM rows and persists `batch_stage_events`) is the only
place that touches the database. That keeps the seam clean.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, NamedTuple, Optional

# Ordered custody chain (superset of Circonomy's C-Sink timeline). Output is
# always sorted by this order so the UI renders a stable spine.
STAGE_ORDER: tuple[str, ...] = (
    "sourcing",
    "moisture",
    "loading",
    "firing",
    "biochar_addition",
    "pre_quenching",
    "quenching",
    "yield",
    "mixing",
    "packaging",
    "dispatch",
    "application",
    "lab",
)
_ORDER_INDEX = {s: i for i, s in enumerate(STAGE_ORDER)}

# capture_type → stage. Smoke-opacity captures (smoke_*, "0".."100") map to
# firing via the prefix/whitelist check in `_stage_for_capture`.
_CAPTURE_STAGE: dict[str, str] = {
    "batch_photo": "sourcing",
    "moisture": "moisture",
    "flame_curtain": "firing",
    "flame_height": "firing",
    "quenching": "quenching",
    "pre_quenching": "pre_quenching",
    "post_burn_mass": "yield",
    "mixing": "mixing",
    "packaging": "packaging",
    "end_use": "application",
    "lab_certificate": "lab",
}
_SMOKE_TOKENS = {"smoke_0", "smoke_50", "smoke_90", "smoke_100", "0", "50", "90", "100"}


class StageEvent(NamedTuple):
    stage: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    source: str  # "projected" here; the forward path may write device/edge/admin


def _get(obj: Any, key: str) -> Any:
    """Attribute-or-dict accessor so callers may pass ORM rows OR plain dicts."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _stage_for_capture(capture_type: Optional[str]) -> Optional[str]:
    if not capture_type:
        return None
    if capture_type in _SMOKE_TOKENS or capture_type.startswith("smoke_"):
        return "firing"
    return _CAPTURE_STAGE.get(capture_type)


def _span(timestamps: list[datetime]) -> tuple[datetime, Optional[datetime]]:
    """(min, max-or-None). A single timestamp has no meaningful end."""
    ts = sorted(t for t in timestamps if t is not None)
    if not ts:
        raise ValueError("empty timestamps")
    return ts[0], (ts[-1] if len(ts) > 1 else None)


def project_stages(
    *,
    batch: Any,
    media: Iterable[Any] = (),
    telemetry: Any = None,
    dispatches: Iterable[Any] = (),
    applications: Iterable[Any] = (),
) -> list[StageEvent]:
    """Derive stage events from available evidence. Emits a stage ONLY when it
    has at least one real timestamp; never invents a stage to fill the chain.

    Inputs (dicts or objects):
      batch: harvest_timestamp, received_at
      media[]: capture_type, uploaded_at
      telemetry: t_start, t_end (from the telemetry plane OR legacy burn ts)
      dispatches[]: created_at, received_at
      applications[]: delivery_date
    """
    buckets: dict[str, list[datetime]] = {}

    def add(stage: str, ts: Optional[datetime]) -> None:
        if stage and ts is not None:
            buckets.setdefault(stage, []).append(ts)

    # 1. sourcing anchored on harvest (fallback: batch received_at)
    add("sourcing", _get(batch, "harvest_timestamp"))

    # 2. media capture types
    for m in media:
        stage = _stage_for_capture(_get(m, "capture_type"))
        add(stage, _get(m, "uploaded_at"))

    # 3. firing preferentially from telemetry window (more precise than photos)
    if telemetry is not None:
        add("firing", _get(telemetry, "t_start"))
        add("firing", _get(telemetry, "t_end"))

    # 4. dispatch + application from their own rows
    for d in dispatches:
        add("dispatch", _get(d, "created_at"))
        add("dispatch", _get(d, "received_at"))
    for a in applications:
        add("application", _get(a, "delivery_date"))

    events: list[StageEvent] = []
    for stage, tss in buckets.items():
        start, end = _span(tss)
        events.append(StageEvent(stage=stage, started_at=start, ended_at=end, source="projected"))

    events.sort(key=lambda e: _ORDER_INDEX.get(e.stage, len(STAGE_ORDER)))
    return events
