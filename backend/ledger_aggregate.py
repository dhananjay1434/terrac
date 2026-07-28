"""Pure biomass-ledger aggregation (M5.1 core).

The M5.1 endpoint (`GET /portal/ledgers/biomass`, coordinator's lane — router +
registration) adapts ORM rows into plain dicts and calls `build_biomass_ledger`
for the grouping/aggregation. Kept pure + ORM-free (dict/attr-agnostic via
`_get`) so it unit-tests standalone and the DB coupling stays in the endpoint —
same seam as `stage_projection` and `emissions_factors`.

Never fabricates: a row with no mass contributes 0; an empty range yields empty
buckets + zeroed totals, not invented figures.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Iterable, Optional


def _get(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _as_datetime(v: Any) -> Optional[datetime]:
    if isinstance(v, datetime):
        dt = v
    elif isinstance(v, date):
        dt = datetime(v.year, v.month, v.day)
    else:
        return None
    # Normalise to tz-aware UTC so naive DB timestamps (SQLite round-trips naive)
    # compare cleanly against the endpoint's aware from/to bounds. A naive value is
    # assumed already-UTC - never a fabricated time, just an explicit zone.
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def bucket_key(dt: datetime, bucket: str) -> str:
    """Period label: 'YYYY-MM' for month, 'YYYY-MM-DD' for day."""
    if bucket == "day":
        return dt.strftime("%Y-%m-%d")
    if bucket == "month":
        return dt.strftime("%Y-%m")
    raise ValueError(f"unsupported bucket: {bucket!r} (use 'day' or 'month')")


def build_biomass_ledger(
    rows: Iterable[Any],
    *,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    bucket: str = "month",
) -> dict:
    """Aggregate biomass-intake rows into period buckets + species totals.

    Each row exposes: date (datetime|date), species (str|None), kg (number|None),
    batch_code (str|None). Rows outside [date_from, date_to] (inclusive) are
    dropped. Returns:
      {
        "bucket": "month"|"day",
        "buckets": [{"period","total_kg","by_species":{...},"batch_codes":[...],"row_count"}],
        "totals": {"total_kg","by_species":{...},"row_count"},
      }
    Buckets are chronologically ordered; species maps are ordered by kg desc.
    """
    if bucket not in ("day", "month"):
        raise ValueError(f"unsupported bucket: {bucket!r}")

    # Route the caller's bounds through the same normaliser so a naive from/to can
    # never mismatch a normalised row datetime.
    date_from = _as_datetime(date_from)
    date_to = _as_datetime(date_to)

    per_bucket: dict[str, dict] = {}
    grand_kg = 0.0
    grand_species: dict[str, float] = {}
    grand_rows = 0

    for r in rows:
        dt = _as_datetime(_get(r, "date"))
        if dt is None:
            continue  # undated row cannot be placed — skip, never guess a date
        if date_from is not None and dt < date_from:
            continue
        if date_to is not None and dt > date_to:
            continue

        kg_raw = _get(r, "kg")
        try:
            kg = float(kg_raw) if kg_raw is not None else 0.0
        except (TypeError, ValueError):
            kg = 0.0
        species = _get(r, "species") or "unknown"
        code = _get(r, "batch_code")

        key = bucket_key(dt, bucket)
        b = per_bucket.setdefault(
            key,
            {"period": key, "total_kg": 0.0, "by_species": {}, "batch_codes": [], "row_count": 0},
        )
        b["total_kg"] += kg
        b["by_species"][species] = b["by_species"].get(species, 0.0) + kg
        b["row_count"] += 1
        if code:
            b["batch_codes"].append(code)

        grand_kg += kg
        grand_species[species] = grand_species.get(species, 0.0) + kg
        grand_rows += 1

    def _round_species(m: dict[str, float]) -> dict[str, float]:
        # ordered by kg desc for a stable, meaningful display
        return {k: round(v, 3) for k, v in sorted(m.items(), key=lambda kv: -kv[1])}

    buckets = []
    for key in sorted(per_bucket):
        b = per_bucket[key]
        buckets.append(
            {
                "period": b["period"],
                "total_kg": round(b["total_kg"], 3),
                "by_species": _round_species(b["by_species"]),
                "batch_codes": b["batch_codes"],
                "row_count": b["row_count"],
            }
        )

    return {
        "bucket": bucket,
        "buckets": buckets,
        "totals": {
            "total_kg": round(grand_kg, 3),
            "by_species": _round_species(grand_species),
            "row_count": grand_rows,
        },
    }
