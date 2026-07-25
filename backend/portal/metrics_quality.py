"""Part 1F.1 -- org-scoped, read-only pyrolysis + permanence quality metrics.

Pure analytics, never credit-affecting. Tenancy scoping reuses
`tenancy.scope_batches_by_org` exactly as `list_batches` does (routes.py), so
a caller never sees a batch outside their org. Batches missing telemetry or
lab H:Corg (or with an unparseable/incomplete LCA audit) are EXCLUDED from
the relevant metric and counted in an `excluded` field -- never defaulted to
a fabricated value.

NOTE: do not import from routes.py here -- routes.py imports this module to
wire the route, so an import back would be circular.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import tenancy
from models import Batch, PortalUser, PyrolysisTelemetry

# Informational pyrolysis-range indicator, adjustable, NOT a credit gate.
PYROLYSIS_THRESHOLD_C = 450.0

# Buckets sized to the ACHIEVABLE permanence range of the CSI 100-year decay
# model, not a generic 0-100% ramp. The model yields ~82.6% for the top
# stability tier (H:Corg < 0.4) and 70% for the lower tier — nothing above
# ~83% is reachable, so the old 90-95%/95-100% buckets were structurally
# dead-on-arrival. These boundaries keep every bucket in the real range and
# separate the two tiers ("80%+" = top-tier durable, "70-75%" = lower tier).
_DISTRIBUTION_LABELS = ["<70%", "70-75%", "75-80%", "80%+"]


def _parse_audit(json_str: "str | None") -> "dict | None":
    if not json_str:
        return None
    try:
        parsed = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    if "cremain_t" not in parsed or "gross_c_sink_t_co2e" not in parsed:
        return None
    try:
        return {
            "cremain_t": float(parsed["cremain_t"]),
            "gross_c_sink_t_co2e": float(parsed["gross_c_sink_t_co2e"]),
        }
    except (TypeError, ValueError):
        return None


def parse_telemetry(payload_json: "str | None") -> "dict | None":
    """Allow-lists ONLY temperature_readings, min_temp, max_temp."""
    if not payload_json:
        return None
    try:
        parsed = json.loads(payload_json)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    readings = parsed.get("temperature_readings")
    if not isinstance(readings, list) or len(readings) == 0:
        return None
    try:
        readings = [float(r) for r in readings]
    except (TypeError, ValueError):
        return None
    result = {"temperature_readings": readings}
    if "min_temp" in parsed:
        result["min_temp"] = parsed["min_temp"]
    if "max_temp" in parsed:
        result["max_temp"] = parsed["max_temp"]
    return result


def _stats(values: list[float]) -> "dict | None":
    if not values:
        return None
    return {
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values),
    }


def _bucket_label(pct: float) -> str:
    if pct < 70.0:
        return "<70%"
    if pct < 75.0:
        return "70-75%"
    if pct < 80.0:
        return "75-80%"
    return "80%+"


async def _compute_permanence(session: AsyncSession, user: PortalUser) -> dict:
    stmt = tenancy.scope_batches_by_org(
        select(Batch.batch_uuid, Batch.lab_h_corg, Batch.lca_audit_json), user
    )
    rows = (await session.execute(stmt)).all()

    h_corg_values: list[float] = []
    permanence_values: list[float] = []
    excluded = 0
    dist_counts = {label: 0 for label in _DISTRIBUTION_LABELS}

    for row in rows:
        if row.lab_h_corg is None:
            excluded += 1
            continue
        audit = _parse_audit(row.lca_audit_json)
        if audit is None or audit["gross_c_sink_t_co2e"] <= 0:
            excluded += 1
            continue
        permanence_pct = (
            (audit["cremain_t"] * 44 / 12) / audit["gross_c_sink_t_co2e"] * 100
        )
        if permanence_pct < 0:
            excluded += 1
            continue
        h_corg_values.append(row.lab_h_corg)
        permanence_values.append(permanence_pct)
        dist_counts[_bucket_label(permanence_pct)] += 1

    return {
        "n": len(permanence_values),
        "excluded": excluded,
        "h_corg": _stats(h_corg_values),
        "permanence_pct": _stats(permanence_values),
        "distribution": [
            {"label": label, "count": dist_counts[label]}
            for label in _DISTRIBUTION_LABELS
        ],
    }


async def _compute_pyrolysis(session: AsyncSession, user: PortalUser) -> dict:
    uuid_stmt = tenancy.scope_batches_by_org(select(Batch.batch_uuid), user)
    batch_uuids = [r[0] for r in (await session.execute(uuid_stmt)).all()]

    if not batch_uuids:
        return {
            "n": 0,
            "excluded": 0,
            "threshold_c": PYROLYSIS_THRESHOLD_C,
            "peak_temp_c": None,
            "pct_above_threshold": None,
        }

    t_stmt = (
        select(
            PyrolysisTelemetry.batch_uuid,
            PyrolysisTelemetry.payload_json,
            PyrolysisTelemetry.received_at,
        )
        .where(PyrolysisTelemetry.batch_uuid.in_(batch_uuids))
        .order_by(PyrolysisTelemetry.received_at.desc())
    )
    t_rows = (await session.execute(t_stmt)).all()

    latest_by_batch: dict[str, str] = {}
    for row in t_rows:
        if row.batch_uuid not in latest_by_batch:
            latest_by_batch[row.batch_uuid] = row.payload_json

    peak_values: list[float] = []
    pct_above_values: list[float] = []
    excluded = 0

    for bu in batch_uuids:
        payload_json = latest_by_batch.get(bu)
        telemetry = parse_telemetry(payload_json) if payload_json is not None else None
        if telemetry is None:
            excluded += 1
            continue
        readings = telemetry["temperature_readings"]
        peak = telemetry.get("max_temp")
        if peak is None:
            peak = max(readings)
        pct_above = 100.0 * sum(
            1 for r in readings if r >= PYROLYSIS_THRESHOLD_C
        ) / len(readings)
        peak_values.append(float(peak))
        pct_above_values.append(pct_above)

    return {
        "n": len(peak_values),
        "excluded": excluded,
        "threshold_c": PYROLYSIS_THRESHOLD_C,
        "peak_temp_c": _stats(peak_values),
        "pct_above_threshold": _stats(pct_above_values),
    }


async def quality_metrics(session: AsyncSession, user: PortalUser) -> dict:
    pyrolysis = await _compute_pyrolysis(session, user)
    permanence = await _compute_permanence(session, user)
    return {"pyrolysis": pyrolysis, "permanence": permanence}
