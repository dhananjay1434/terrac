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


import math


def derive_moisture_compliance(
    photographed_reading_count: int, biomass_input_kg: Optional[float]
) -> tuple[bool, Optional[str]]:
    """Rainbow C2 moisture rule: at least 1 photographed reading per 100 kg of
    biomass, with a floor of 10 readings per run. `photographed_reading_count` is
    the number of moisture readings that carry a photo hash. Returns
    (compliant, reason_if_not)."""
    required = 10
    if biomass_input_kg and biomass_input_kg > 0:
        required = max(required, math.ceil(biomass_input_kg / 100.0))
    if photographed_reading_count < required:
        return False, "insufficient_moisture_samples"
    return True, None


# Rainbow C3: open-kiln pyrolysis photo evidence the methodology requires.
REQUIRED_OPEN_KILN_STAGES = frozenset({"flame_curtain", "quenching", "flame_height"})
MAX_OPEN_KILN_FLAME_HEIGHT_M = 0.5


def derive_pyrolysis_photo_compliance(
    kiln_type: Optional[str],
    smoke_evidence: Optional[list],
    flame_height_m: Optional[float],
) -> tuple[bool, bool]:
    """Rainbow C3 (open-kiln only): returns (photos_ok, flame_height_ok).

    Only enforced when kiln_type == 'open'. For any other/unknown kiln type the
    checks are inert (both True) so existing/closed-kiln flows are unaffected.
    """
    if kiln_type != "open":
        return True, True
    stages = {
        e.get("stage")
        for e in (smoke_evidence or [])
        if isinstance(e, dict) and e.get("sha256")
    }
    photos_ok = REQUIRED_OPEN_KILN_STAGES.issubset(stages)
    flame_ok = (
        flame_height_m is not None
        and 0.0 <= flame_height_m < MAX_OPEN_KILN_FLAME_HEIGHT_M
    )
    return photos_ok, flame_ok


def derive_ignition_compliance(
    kiln_type: Optional[str], ignition_energy_type: Optional[str]
) -> bool:
    """Rainbow C3b (closed-kiln only): closed kilns must declare ignition energy.
    Inert for non-closed kiln types."""
    if kiln_type != "closed":
        return True
    return bool(ignition_energy_type)


def derive_composite_sample_compliance(
    photographed_sample_count: int, *, enforced: bool = False
) -> tuple[bool, Optional[str]]:
    """Rainbow C4: a site composite pile sub-sample (photographed) must be set
    aside per run. `photographed_sample_count` is the number of composite-sample
    rows carrying a photo hash. Returns (compliant, reason_if_not).

    Inert by default (`enforced=False`) so existing flows are untouched until the
    unified issuance gate (C10) turns it on — mirrors how C1's biomass reason is
    deferred. When enforced, requires at least one photographed sub-sample.
    """
    if not enforced:
        return True, None
    if photographed_sample_count < 1:
        return False, "missing_composite_sample"
    return True, None


def derive_delivery_compliance(
    app_payload: Optional[dict], *, enforced: bool = False
) -> tuple[bool, bool]:
    """Rainbow C5: delivery record + buyer/end-user identity on the /application.

    Returns (delivery_ok, buyer_ok):
      * delivery_ok  — a delivery record is present (a delivery date OR a
        delivered amount was captured for this batch).
      * buyer_ok     — the buyer/end-user is identified (a name is present).

    Inert by default (`enforced=False`, deferred to the C10 unified gate,
    mirroring C4/C1) so existing flows are untouched. When enforced, a missing
    delivery record or buyer identity flips the batch provisional via
    `missing_delivery_record` / `missing_buyer_identity`.
    """
    if not enforced:
        return True, True
    p = app_payload or {}
    delivery_ok = bool(p.get("delivery_date") or p.get("delivered_amount_kg"))
    buyer_ok = bool((p.get("buyer_name") or "").strip())
    return delivery_ok, buyer_ok


def assemble(
    wet_yield: Optional[float],
    min_temp: Optional[float],
    transport: Optional[float],
    *,
    has_lab_hcorg: bool,
    has_lab_corg: bool = True,
    attestation_ok: bool = True,
    moisture_ok: bool = True,
    pyrolysis_photos_ok: bool = True,
    flame_height_ok: bool = True,
    ignition_ok: bool = True,
    composite_sample_ok: bool = True,
    delivery_ok: bool = True,
    buyer_ok: bool = True,
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
    if not has_lab_corg:
        reasons.append("assumed_corg")
    if not attestation_ok:
        reasons.append("attestation_unverified")
    if not moisture_ok:
        reasons.append("insufficient_moisture_samples")
    if not pyrolysis_photos_ok:
        reasons.append("missing_pyrolysis_photos")
    if not flame_height_ok:
        reasons.append("flame_height_out_of_range")
    if not ignition_ok:
        reasons.append("missing_ignition_energy")
    if not composite_sample_ok:
        reasons.append("missing_composite_sample")
    if not delivery_ok:
        reasons.append("missing_delivery_record")
    if not buyer_ok:
        reasons.append("missing_buyer_identity")
    return Corroboration(
        wet_yield_kg=wet_yield,
        min_recorded_temp_c=min_temp,
        transport_distance_km=transport,
        provisional=bool(reasons),
        reasons=reasons,
    )
