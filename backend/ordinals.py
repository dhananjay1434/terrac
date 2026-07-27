"""ADR-001 B3 — ordinal allocation for batch-code identity.

`allocate_ordinal(session, kind, parent_id)` returns the next integer for that
parent = max(existing) + 1 (starting at 1). Ordinals are **never reused** — a
decommissioned kiln keeps its number forever so historical codes stay
resolvable. The per-parent UNIQUE constraint (migration b8e2d4f6a1c3) is the
real guard; callers retry once on conflict.

`network_code_for(org_ordinal)` derives the display network code
("A" + zero-padded ordinal); the leading letter is reserved for a future
partition dimension ("A" for all current networks).
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Facility, Kiln, Network

# kind → (ordinal column, parent column)
_SPEC = {
    "network": (Network.org_ordinal, Network.org_id),
    "site": (Facility.site_ordinal, Facility.network_id),
    "kiln": (Kiln.kiln_ordinal, Kiln.site_id),
}


async def allocate_ordinal(
    session: AsyncSession, kind: str, parent_id: str
) -> int:
    if kind not in _SPEC:
        raise ValueError(f"unknown ordinal kind: {kind!r}")
    ord_col, parent_col = _SPEC[kind]
    current_max = (
        await session.execute(
            select(func.max(ord_col)).where(parent_col == parent_id)
        )
    ).scalar_one_or_none()
    return int(current_max or 0) + 1


def network_code_for(org_ordinal: int) -> str:
    if not (0 <= org_ordinal <= 999):
        raise ValueError("org_ordinal out of range 0..999")
    return f"A{org_ordinal:03d}"
