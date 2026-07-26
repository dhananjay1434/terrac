"""Per-org feature flags on top of AppConfig — additive, default OFF.

Key format: "ff.<flag>.<org_id>" or global "ff.<flag>".  Values "on"/"off".
Never cache across requests — flags must be flippable live.

ADAPTATION (plan M0.2 caveat, the ONE permitted deviation): the real AppConfig
is a SINGLE-ROW table (config_id="default") carrying a `flags_json` TEXT blob,
not key/value columns. Flags therefore live as keys inside that JSON dict. All
plan semantics are preserved: the FLAGS tuple is unchanged, an org-specific key
beats the global key, a missing row/key/blob means OFF, and nothing is cached
(the row is re-read on every call so flags flip live).
"""
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import AppConfig

FLAGS = ("telemetry_v2", "hierarchy_v2", "timeline_v2", "journeys_v2", "ledgers_v2")


async def flag_enabled(
    session: AsyncSession, flag: str, org_id: str | None = None
) -> bool:
    if flag not in FLAGS:
        raise ValueError(f"unknown feature flag: {flag}")
    row = (
        await session.execute(
            select(AppConfig).where(AppConfig.config_id == "default")
        )
    ).scalar_one_or_none()
    if row is None:
        return False
    try:
        flags = json.loads(row.flags_json or "{}")
    except (ValueError, TypeError):
        return False
    if not isinstance(flags, dict):
        return False
    keys = [f"ff.{flag}"] + ([f"ff.{flag}.{org_id}"] if org_id else [])
    for key in reversed(keys):  # org-specific beats global
        if key in flags:
            return str(flags[key]).strip().lower() == "on"
    return False
