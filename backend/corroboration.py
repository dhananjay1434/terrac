"""Server-side corroboration of credit-bearing batch inputs (Phase 7-R).

The Flutter client writes the batch at harvest, then emits telemetry (burn),
yield (post-burn) and application (field) records later. The credit-bearing
inputs therefore do NOT exist at batch-creation time — they must be derived
server-side from those corroborating streams as they arrive, never trusted from
the batch payload.

Every function here is PURE (no DB, no FastAPI, no I/O) so it is trivially
unit-testable. The thin DB glue that loads the evidence rows and persists the
result lives in server.recompute_batch_credit.

Canonical wire field names (must match what the Dart writers send — see
lib/data/local/pyrolysis_writer.dart and yield_end_use_writers.dart):
  * telemetry:    temperature_readings (List[float])
  * yield:        wet_yield_weight_kg (float)
  * application:  latitude, longitude (float)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

# CSI rule (preserved from the original create_batch): a telemetry log must carry
# at least this many samples to count as a qualifying burn record.
MIN_TEMPERATURE_SAMPLES = 60


@dataclass
class Corroboration:
    """Outcome of corroborating a batch's credit inputs against evidence.

    A ``None`` field means "not corroborated yet". ``provisional`` is True whenever
    ANY required input is missing OR the H:Corg permanence factor is assumed rather
    than lab-measured; ``reasons`` records exactly why, for the audit trail.
    """

    wet_yield_kg: Optional[float]
    min_recorded_temp_c: Optional[float]
    transport_distance_km: Optional[float]
    provisional: bool
    reasons: list[str] = field(default_factory=list)


def derive_min_temp(
    telemetry_payload: Optional[dict],
) -> tuple[Optional[float], Optional[str]]:
    """Minimum burn temperature from the /telemetry log.

    Returns (min_temp, reason_if_missing). Reads the canonical
    ``temperature_readings`` key and requires >= MIN_TEMPERATURE_SAMPLES samples,
    replacing the old client-asserted min_recorded_temp_c + <100 C validator.
    """
    if not telemetry_payload:
        return None, "no_telemetry"
    readings = telemetry_payload.get("temperature_readings") or []
    if not isinstance(readings, list) or len(readings) < MIN_TEMPERATURE_SAMPLES:
        return None, "insufficient_temperature_samples"
    try:
        return float(min(readings)), None
    except (TypeError, ValueError):
        return None, "invalid_temperature_samples"


def derive_wet_yield(
    yield_payload: Optional[dict],
) -> tuple[Optional[float], Optional[str]]:
    """Wet biochar yield (kg) from the /yield record's canonical
    ``wet_yield_weight_kg`` field."""
    if not yield_payload:
        return None, "no_yield_record"
    v = yield_payload.get("wet_yield_weight_kg")
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None, "invalid_wet_yield"
    if v <= 0.0:
        return None, "invalid_wet_yield"
    return v, None


def derive_transport_km(
    batch_lat: Optional[float],
    batch_lon: Optional[float],
    app_payload: Optional[dict],
    *,
    haversine: Callable[[float, float, float, float], float],
) -> tuple[Optional[float], Optional[str]]:
    """Transport distance (km) as the Haversine between the batch's production
    GPS and the /application field GPS.

    ``haversine`` is injected (server.haversine_km) so this module stays free of
    server imports. Note the server's fixed arg order: haversine(lon, lat, lon, lat).
    """
    if app_payload is None or batch_lat is None or batch_lon is None:
        return None, "no_application_record"
    a_lat = app_payload.get("latitude")
    a_lon = app_payload.get("longitude")
    if a_lat is None or a_lon is None:
        return None, "application_missing_gps"
    try:
        return float(haversine(a_lon, a_lat, batch_lon, batch_lat)), None
    except (TypeError, ValueError):
        return None, "invalid_application_gps"


def assemble(
    wet_yield: Optional[float],
    min_temp: Optional[float],
    transport: Optional[float],
    *,
    has_lab_hcorg: bool,
    attestation_ok: bool = True,
) -> Corroboration:
    """Combine the derived inputs into a Corroboration, computing provisional
    status and the ordered list of reasons a batch is not yet issuable.

    `attestation_ok` is the platform-integrity signal. Phase 9-R: real Play
    Integrity / DeviceCheck verification is not built yet, so the caller decides
    the policy — when enforcement is on and attestation is unverified, this adds
    `attestation_unverified` (fail closed). Defaults True so the check is inert
    until a verifier and the enforcement flag are enabled.
    """
    reasons: list[str] = []
    if wet_yield is None:
        reasons.append("wet_yield_uncorroborated")
    if min_temp is None:
        reasons.append("min_temp_uncorroborated")
    if transport is None:
        reasons.append("transport_uncorroborated")
    if not has_lab_hcorg:
        reasons.append("assumed_h_corg")
    if not attestation_ok:
        reasons.append("attestation_unverified")
    return Corroboration(
        wet_yield_kg=wet_yield,
        min_recorded_temp_c=min_temp,
        transport_distance_km=transport,
        provisional=bool(reasons),
        reasons=reasons,
    )
