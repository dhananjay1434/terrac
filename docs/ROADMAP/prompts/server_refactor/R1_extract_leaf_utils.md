# R1 — Extract leaf utilities: `jsonsafe.py` + `geo.py`

> **Read `00_SERVER_REFACTOR_SOP.md` first.** This is step 1 of 10. Pure relocation — no behavior change.
> Baseline gate: **416 passed, 2 skipped**. Do ONE commit. Do not start R2 until this is committed & green.

**Why these two first:** they are pure leaves — they import only stdlib + `piexif`, and nothing else in
`server.py` that we haven't-yet-moved depends *back* on them in a way that creates a cycle. Perfect warm-up
that proves the facade mechanism end-to-end.

---

## STEP 1 — Create `backend/jsonsafe.py`

Create a new file `backend/jsonsafe.py` with EXACTLY this content. The three functions + one constant are
copied verbatim from `server.py` (`_safe_json`, `_BIG_JSON_BYTES`, `_safe_json_async`, `_as_utc`).

> Note: `_safe_json` logs via a logger named `"dmrv"`. `logging.getLogger("dmrv")` returns the SAME logger
> object no matter which module calls it, so defining it here is identical to sharing `server.log`. This
> keeps R1 independent of R2 (settings, where `log` officially lives).

```python
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
```

---

## STEP 2 — Create `backend/geo.py`

Create `backend/geo.py`. Copy `haversine_km`, `_exif_to_decimal`, `_parse_exif_gps`,
`GPS_ANCHOR_MISMATCH_KM`, `_gps_mismatch_km`, `_evaluate_anchor` **verbatim from server.py** (they are at
approx lines 116–194). The content is exactly:

```python
"""Geospatial + EXIF-GPS helpers (extracted from server.py, R1).

Pure leaf: imports only stdlib math + piexif. `_evaluate_anchor` mutates a Batch's
status in place (photo-anchored GPS corroboration, T2.7) but takes the batch as an
argument — no model import needed here.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Optional

import piexif


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    lon1, lat1, lon2, lat2 = map(radians, (lon1, lat1, lon2, lat2))
    a = (
        sin((lat2 - lat1) / 2) ** 2
        + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    )
    return 6371.0 * 2 * asin(sqrt(a))


def _exif_to_decimal(dms, ref) -> Optional[float]:
    """Convert an EXIF GPS (degrees, minutes, seconds) rational triple + ref
    ('N'/'S'/'E'/'W') to a signed decimal degree. Returns None if absent."""
    if not dms or ref is None:
        return None
    try:

        def _r(x):
            return x[0] / x[1]

        deg = _r(dms[0]) + _r(dms[1]) / 60.0 + _r(dms[2]) / 3600.0
    except (TypeError, IndexError, ZeroDivisionError):
        return None
    if isinstance(ref, bytes):
        ref = ref.decode("ascii", "ignore")
    if ref in ("S", "W"):
        deg = -deg
    return deg


def _parse_exif_gps(content: bytes) -> tuple[Optional[float], Optional[float]]:
    """Best-effort GPS extraction from a photo's EXIF. Non-JPEG / no-EXIF /
    no-GPS uploads return (None, None) rather than raising."""
    try:
        gps = piexif.load(content).get("GPS") or {}
    except Exception:
        return (None, None)
    lat = _exif_to_decimal(
        gps.get(piexif.GPSIFD.GPSLatitude), gps.get(piexif.GPSIFD.GPSLatitudeRef)
    )
    lon = _exif_to_decimal(
        gps.get(piexif.GPSIFD.GPSLongitude), gps.get(piexif.GPSIFD.GPSLongitudeRef)
    )
    return (lat, lon)


# T2.7: client-authored EXIF is WEAK corroboration — the app injects the GPS it
# later "matches" against, so this catches careless fraud and honest error, not a
# determined attacker. The strong device control is attestation (T2.1). The
# threshold is deliberately generous to avoid false quarantines on GPS drift.
GPS_ANCHOR_MISMATCH_KM = 1.0


def _gps_mismatch_km(
    lat1, lon1, lat2, lon2, threshold_km: float = GPS_ANCHOR_MISMATCH_KM
) -> bool:
    """True only when all four coordinates are present AND the photo EXIF and
    the claimed location disagree by more than `threshold_km`."""
    if None in (lat1, lon1, lat2, lon2):
        return False
    return haversine_km(lon1, lat1, lon2, lat2) > threshold_km


def _evaluate_anchor(batch, photo_sha: Optional[str], exif_lat, exif_lon) -> None:
    """Decide a batch's status when a photo is anchored to it.

    Phase 9 + media integrity: only a photo whose SHA-256 matches the batch's
    declared `sha256_hash` may verify it (a mismatching upload never upgrades
    the batch). When the photo's EXIF GPS disagrees with the batch's claimed
    coordinates by >1 km the batch is quarantined for review.
    """
    if not batch.sha256_hash or not photo_sha:
        return
    if photo_sha.lower() != batch.sha256_hash.lower():
        return  # wrong photo — do not upgrade
    if _gps_mismatch_km(batch.latitude, batch.longitude, exif_lat, exif_lon):
        batch.status = "QUARANTINE_GPS_MISMATCH"
    elif batch.status == "UNVERIFIED":
        batch.status = "RECEIVED"
```

> **Verify before deleting from server.py:** confirm `_evaluate_anchor` in server.py has no other local
> dependency beyond the four symbols above. (It calls only `_gps_mismatch_km` + reads batch attributes.)

---

## STEP 3 — Edit `backend/server.py` (delete originals, add re-export imports)

1. **Delete** these definitions from `server.py` (locate by name):
   - `haversine_km`, `_exif_to_decimal`, `_parse_exif_gps`, `GPS_ANCHOR_MISMATCH_KM`, `_gps_mismatch_km`,
     `_evaluate_anchor` (the ~116–194 block)
   - `_safe_json`, `_BIG_JSON_BYTES`, `_safe_json_async`, `_as_utc` (the ~271–317 block)
   - Leave `_SAFE` (line 304) IN PLACE — it moves in R3, not now.

2. **Add re-export imports.** In server.py's local-import block (the region around lines 50–96, right
   after `import observability`), add these two lines:

   ```python
   from jsonsafe import _as_utc, _safe_json, _safe_json_async, _BIG_JSON_BYTES  # noqa: F401  (R1 facade)
   from geo import (  # noqa: F401  (R1 facade)
       GPS_ANCHOR_MISMATCH_KM,
       _evaluate_anchor,
       _gps_mismatch_km,
       _parse_exif_gps,
       haversine_km,
   )
   ```
   (`_exif_to_decimal` is only used by `_parse_exif_gps`, which now lives in geo.py, so it does not need
   re-exporting — but adding it costs nothing if you prefer symmetry.)

3. **Check the now-unused stdlib imports in server.py.** After the delete, server.py may no longer use
   `from math import asin, cos, radians, sin, sqrt` directly. **Only remove a stdlib import from server.py
   if `grep` confirms zero remaining uses in the file** — e.g.:
   ```
   grep -nE "\b(asin|cos|radians|sin|sqrt)\b" backend/server.py
   ```
   If any remain (they may not), leave the import. Do NOT remove `piexif`, `json`, `asyncio`, `datetime`,
   `timezone` from server.py without grepping — they are used elsewhere. When unsure, leave the import;
   an unused import is harmless and never worth risking a break.

---

## STEP 4 — Gates

Run in order from `backend/`:

1. **G3 import sanity:** `DMRV_DISABLE_DOTENV=1 python -c "import server; from server import app, _as_utc, haversine_km, _evaluate_anchor, _parse_exif_gps, _safe_json_async; print('ok')"` → prints `ok`.
2. **G1 full suite:** `DMRV_DISABLE_DOTENV=1 python -m pytest -q` → **416 passed, 2 skipped, 0 failed**.
   - Sanity: `tests/test_timezone_normalization.py` (imports `_as_utc` from server) and any EXIF/anchor
     tests must pass via the re-export.

If red: re-read SOP §5 "If the suite goes red" — it's a missing re-export or a missing import in the new
module, never the test.

---

## STEP 5 — Commit + tick tracker

- In `docs/ROADMAP/PLAYBOOK_PROGRESS.md`, under the P4.8 line, add/tick the sub-tracker (create it if this
  is the first R-step to land):
  ```
  - [x] **P4.8/R1** — extracted jsonsafe.py + geo.py (leaf utils); server.py 2762→~2600; suite 416/2 green
  ```
- Commit (SOP §7 format):
  ```
  refactor(backend): extract jsonsafe.py + geo.py leaf utils — server.py 2762→~2600 LOC (P4.8/R1)

  Pure relocation, no behavior change. Suite green (416 passed, 2 skipped).
  Facade re-exports preserve `from server import ...` for tests + portal.

  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```

**Report:** what moved, server.py LOC before/after, gate result. Then STOP — R2 is a separate session.
