"""R4 - single source of truth for a batch's active capabilities.

Combines org feature flags (with their opt-in/opt-out defaults) and runtime data
presence into one plain dict. Consumers ask here; nobody reads a raw flag or guesses
from a failed fetch. Adding/removing a capability is a data/flag change, never code.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from feature_flags import flag_active, flag_enabled
from models import Batch, Project, PyrolysisTelemetry, TelemetryPoint

_THERMAL = ("T1", "T2", "T3", "T4")


async def _org_for_batch(session: AsyncSession, batch: Batch) -> str | None:
    if not batch.project_id:
        return None
    proj = (
        await session.execute(select(Project).where(Project.project_id == batch.project_id))
    ).scalar_one_or_none()
    return proj.org_id if proj else None


async def resolve_batch_capabilities(session: AsyncSession, batch: Batch) -> dict:
    buid = str(batch.batch_uuid)
    org = await _org_for_batch(session, batch)

    channels = set(
        (
            await session.execute(
                select(TelemetryPoint.channel)
                .where(TelemetryPoint.batch_uuid == buid)
                .distinct()
            )
        ).scalars().all()
    )
    has_thermal_pts = any(c in _THERMAL for c in channels)
    has_load_pts = "LOAD" in channels
    has_legacy_tel = (
        await session.execute(
            select(PyrolysisTelemetry.id).where(PyrolysisTelemetry.batch_uuid == buid).limit(1)
        )
    ).scalar_one_or_none() is not None

    # telemetry_v2 is OPT-IN (default off); display flags are OPT-OUT (default on).
    telemetry_v2 = await flag_enabled(session, "telemetry_v2", org)

    if telemetry_v2 and (has_thermal_pts or has_load_pts):
        telemetry = "v2"
    elif has_legacy_tel:
        telemetry = "legacy"
    else:
        telemetry = "none"

    if telemetry_v2 and has_thermal_pts and has_load_pts:
        tier = "full"
    elif telemetry_v2 and has_thermal_pts:
        tier = "thermal"
    elif telemetry_v2 and has_load_pts:
        tier = "load"
    else:
        tier = "none"

    return {
        "telemetry": telemetry,                                  # "v2" | "legacy" | "none"
        "thermal": (telemetry_v2 and has_thermal_pts) or has_legacy_tel,
        "load": telemetry_v2 and has_load_pts,
        "timeline": await flag_active(session, "timeline_v2", org),
        "journeys": await flag_active(session, "journeys_v2", org),
        "ledgers": await flag_active(session, "ledgers_v2", org),
        "provenance_code": batch.batch_code is not None,
        "tier": tier,                                            # none | load | thermal | full
    }
