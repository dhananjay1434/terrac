"""Defensive JSON parsing + UTC datetime normalization (extracted from server.py, R1).

Pure leaf utilities: no app/db/model dependencies. Both `server.py` and the credit
engine parse stored payload JSON through these so one corrupt row degrades to "empty"
instead of bricking a recompute (P1-B1), and every datetime comparison is aware-UTC
(P1-B3).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

log = logging.getLogger("dmrv")


def _safe_json(raw, *, context: str):
    """Parse stored payload JSON defensively (P1-B1).

    A corrupt stored payload — a bad write, a manual DB edit, a partial
    migration — must degrade to "this row contributes nothing" plus a log line,
    never a JSONDecodeError that aborts the whole recompute and permanently
    bricks a batch's credit path (or 500s the compliance read). Returns the
    parsed object, or None when raw is empty/unparseable.
    """
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        log.error("corrupt payload_json (%s) — treating as empty", context)
        return None


# P3.7/H3: telemetry payloads can be ~100k floats. Parsing that on the event loop
# stalls every other request, so offload the big ones to a thread. Small payloads
# (yield/application) stay inline — a thread hop would cost more than it saves.
_BIG_JSON_BYTES = 512_000


async def _safe_json_async(raw, *, context: str):
    if raw and len(raw) > _BIG_JSON_BYTES:
        return await asyncio.to_thread(_safe_json, raw, context=context)
    return _safe_json(raw, context=context)


def _as_utc(dt: datetime) -> datetime:
    """Normalize any datetime to aware-UTC (P1-B3).

    Naive datetimes are treated as UTC (the client always sends UTC ISO); aware
    ones are converted. Every cross-datetime comparison/subtraction goes through
    this so a mixed naive/aware pair can never silently skew by the tz offset
    (which previously let the teleport check strip tzinfo and mis-time by hours).
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
