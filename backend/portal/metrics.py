"""V8 Part D.1a — org-scoped credit time-series aggregate.

Read-only reporting endpoint support. All aggregation happens in SQL (a real
GROUP BY on a date-truncated period key) — never fetch-all-then-bucket-in-
Python. Tenancy scoping reuses `tenancy.scope_batches_by_org` exactly as
`list_batches` does (routes.py), so a caller never sees a batch outside their
org. "Issued" credit (provisional=false) and "provisional" (pipeline) credit
are kept as two separate, explicitly-labeled sums — never folded together.
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

import tenancy
from models import Batch, PortalUser


def _parse_components(json_str: "str | None") -> "dict | None":
    """Local, minimal allow-list parse of the signed LCA audit JSON — kept
    separate from portal.routes.parse_lca_breakdown to avoid a circular
    import (routes.py imports this module). Extracts only the four numeric
    fields needed for the per-bucket deduction breakdown; never returns
    sensitive sections (audit_signature, transport_events, integrity_signals)
    and never **-splats the parsed dict."""
    if not json_str:
        return None
    try:
        parsed = json.loads(json_str)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    return {
        "cremain_t": parsed.get("cremain_t"),
        "safety_deduction_kg": parsed.get("safety_deduction_kg"),
        "transport_penalty_kg": parsed.get("transport_penalty_kg"),
        "ch4_penalty_kg": parsed.get("ch4_penalty_kg"),
    }


def _month_labels(dt_from: datetime, dt_to: datetime) -> list[str]:
    """Full ordered list of "YYYY-MM" labels spanning [dt_from, dt_to], stepping
    month-by-month via integer year/month arithmetic (timedelta has no
    "months" unit and must not be used here)."""
    labels: list[str] = []
    year, month = dt_from.year, dt_from.month
    end_key = dt_to.year * 12 + (dt_to.month - 1)
    cur_key = year * 12 + (month - 1)
    while cur_key <= end_key:
        y, m = divmod(cur_key, 12)
        labels.append(f"{y:04d}-{m + 1:02d}")
        cur_key += 1
    return labels


async def credit_timeseries(
    session: AsyncSession,
    user: PortalUser,
    dt_from: datetime,
    dt_to: datetime,
) -> dict:
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        # Postgres branch is NOT exercised by the SQLite test suite —
        # sanity-check against a real Postgres instance before deploy.
        period_key = func.to_char(
            func.date_trunc("month", func.timezone("UTC", Batch.received_at)),
            "YYYY-MM",
        )
    else:
        period_key = func.strftime("%Y-%m", Batch.received_at)

    issued_sum = func.coalesce(
        func.sum(case((Batch.provisional.is_(False), Batch.net_credit_t_co2e), else_=0.0)),
        0.0,
    )
    issued_cnt = func.coalesce(
        func.sum(case((Batch.provisional.is_(False), 1), else_=0)), 0
    )
    prov_sum = func.coalesce(
        func.sum(case((Batch.provisional.is_(True), Batch.net_credit_t_co2e), else_=0.0)),
        0.0,
    )
    prov_cnt = func.coalesce(
        func.sum(case((Batch.provisional.is_(True), 1), else_=0)), 0
    )

    stmt = tenancy.scope_batches_by_org(
        select(
            period_key.label("period"), issued_sum, issued_cnt, prov_sum, prov_cnt
        ),
        user,
    ).where(
        Batch.received_at >= dt_from, Batch.received_at <= dt_to
    ).group_by(period_key).order_by(period_key.asc())

    rows = (await session.execute(stmt)).all()
    by_period = {r.period: r for r in rows}

    buckets = []
    for label in _month_labels(dt_from, dt_to):
        row = by_period.get(label)
        if row is None:
            buckets.append(
                {
                    "period": label,
                    "issued_credit_t_co2e": 0.0,
                    "issued_count": 0,
                    "provisional_count": 0,
                }
            )
        else:
            buckets.append(
                {
                    "period": label,
                    "issued_credit_t_co2e": float(row[1]),
                    "issued_count": int(row[2]),
                    "provisional_count": int(row[4]),
                }
            )

    # parse-on-read of lca_audit_json; O(batches in window). Fine at current
    # scale; revisit with a component-column or rollup approach at industrial
    # volume.
    raw_stmt = tenancy.scope_batches_by_org(
        select(Batch.received_at, Batch.provisional, Batch.lca_audit_json), user
    ).where(Batch.received_at >= dt_from, Batch.received_at <= dt_to)
    raw_rows = (await session.execute(raw_stmt)).all()

    components_by_period: dict[str, dict[str, float]] = {}
    for row in raw_rows:
        if row.provisional:
            continue  # INV-3: provisional batches contribute nothing.
        comp = _parse_components(row.lca_audit_json)
        if comp is None:
            continue
        period = row.received_at.strftime("%Y-%m")
        acc = components_by_period.setdefault(
            period,
            {
                "safety_t_co2e": 0.0,
                "transport_t_co2e": 0.0,
                "ch4_t_co2e": 0.0,
                "gross_t_co2e": 0.0,
            },
        )
        acc["safety_t_co2e"] += (comp.get("safety_deduction_kg") or 0) / 1000
        acc["transport_t_co2e"] += (comp.get("transport_penalty_kg") or 0) / 1000
        acc["ch4_t_co2e"] += (comp.get("ch4_penalty_kg") or 0) / 1000
        acc["gross_t_co2e"] += (comp.get("cremain_t") or 0) * 44 / 12

    for bucket in buckets:
        acc = components_by_period.get(
            bucket["period"],
            {
                "safety_t_co2e": 0.0,
                "transport_t_co2e": 0.0,
                "ch4_t_co2e": 0.0,
                "gross_t_co2e": 0.0,
            },
        )
        bucket["components"] = {k: round(v, 6) for k, v in acc.items()}

    totals = {
        "issued_credit_t_co2e": sum(b["issued_credit_t_co2e"] for b in buckets),
        "issued_count": sum(b["issued_count"] for b in buckets),
        "provisional_count": sum(b["provisional_count"] for b in buckets),
        "provisional_credit_t_co2e": sum(float(r[3]) for r in rows),
    }

    return {
        "bucket": "month",
        "from": dt_from.isoformat(),
        "to": dt_to.isoformat(),
        "buckets": buckets,
        "totals": totals,
    }
