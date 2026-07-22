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

from services.bulk_density import volume_to_mass_kg

# CSI rule (preserved from the original create_batch): a telemetry log must carry
# at least this many samples to count as a qualifying burn record.
MIN_TEMPERATURE_SAMPLES = 60

# Rainbow C10 — unified issuance gate. When True, the previously-inert methodology
# checks (C1 biomass, C4 composite sample, C5 delivery/buyer, C8 kiln registration +
# scale calibration, C9 annual methane + closed-kiln PAH) are ENFORCED: a batch
# missing any of them stays provisional and is not issuable. Flipped on at C10;
# each deriver takes an `enforced` override so a caller/test can opt out.
#
# NOTE: this gate is about methodology COMPLETENESS, not the credit-math flips that
# still need methodology sign-off (C6 transport-emission factors, C9 methane→CH4
# penalty, C9 conversion_factor→C1 yield_conversion, C7 1000-yr inertinite pathway).
COMPLIANCE_ENFORCED = True

# C9: minimum representative kiln runs for the annual methane measurement.
MIN_METHANE_RUNS = 3


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


def derive_wet_yield_from_density(
    telemetry_payload: Optional[dict],
    density_kg_per_l: Optional[float],
) -> tuple[Optional[float], Optional[str]]:
    """V8 Part 4 (F) — volumetric fallback yield: mass = kiln_gross_capacity
    (telemetry, litres) × an in-date bulk-density calibration. Used ONLY when
    the caller has no direct crane-scale weight (derive_wet_yield returned
    None) — artisanal biochar can't go on a truck scale mid-process.

    Requires BOTH a telemetry-declared kiln_gross_capacity AND a density
    value; returns (None, reason) on either being absent or invalid — never
    fabricates a mass from a partial input.
    """
    if not telemetry_payload:
        return None, "no_telemetry_for_density_fallback"
    volume_l = telemetry_payload.get("kiln_gross_capacity")
    if volume_l is None or density_kg_per_l is None:
        return None, "missing_volume_or_density"
    try:
        mass_kg = volume_to_mass_kg(float(volume_l), float(density_kg_per_l))
    except (TypeError, ValueError):
        return None, "invalid_volume_or_density"
    return mass_kg, None


def derive_density_calibration_compliance(
    has_in_date_density: bool, *, enforced: bool = COMPLIANCE_ENFORCED
) -> tuple[bool, Optional[str]]:
    """Rainbow C10 (V8 Part 4 F): production at a project must have an in-date
    bulk-density calibration on file — mirrors derive_scale_calibration_
    compliance exactly (same shape, same enforcement gate). Applies whenever
    the batch has a project_id, regardless of whether THIS batch's yield used
    the volumetric fallback (an equipment-calibration QA gate, not conditioned
    on which yield path was taken — same convention as scale_calibration_
    expired). Returns (compliant, `production_requires_valid_density`)."""
    if not enforced:
        return True, None
    if not has_in_date_density:
        return False, "production_requires_valid_density"
    return True, None


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
    photographed_sample_count: int, *, enforced: bool = COMPLIANCE_ENFORCED
) -> tuple[bool, Optional[str]]:
    """Rainbow C4: a site composite pile sub-sample (photographed) must be set
    aside per run. `photographed_sample_count` is the number of composite-sample
    rows carrying a photo hash. Returns (compliant, reason_if_not).

    Enforced at the C10 unified gate (`COMPLIANCE_ENFORCED`); a caller/test can
    pass `enforced=False` to opt out. When enforced, requires at least one
    photographed sub-sample.
    """
    if not enforced:
        return True, None
    if photographed_sample_count < 1:
        return False, "missing_composite_sample"
    return True, None


def derive_biomass_compliance(
    biomass_input_kg: Optional[float],
    biomass_measurement_method: Optional[str],
    *,
    enforced: bool = COMPLIANCE_ENFORCED,
) -> tuple[bool, Optional[str]]:
    """Rainbow C1: the biomass input amount + how it was measured must be recorded.

    Deferred from C1 (data-capture) to the C10 gate. Returns (compliant,
    reason_if_not): `missing_biomass_input` when no positive amount is recorded;
    `missing_conversion_factor` when the method is 'yield_conversion' but no amount
    was derived (a yield-converted amount still needs the amount present).
    """
    if not enforced:
        return True, None
    if not biomass_input_kg or biomass_input_kg <= 0:
        # A yield_conversion method with no amount specifically flags the missing
        # conversion; otherwise the raw input amount is missing.
        if biomass_measurement_method == "yield_conversion":
            return False, "missing_conversion_factor"
        return False, "missing_biomass_input"
    return True, None


def derive_delivery_compliance(
    app_payload: Optional[dict], *, enforced: bool = COMPLIANCE_ENFORCED
) -> tuple[bool, bool]:
    """Rainbow C5: delivery record + buyer/end-user identity on the /application.

    Returns (delivery_ok, buyer_ok):
      * delivery_ok  — a delivery record is present (a delivery date OR a
        delivered amount was captured for this batch).
      * buyer_ok     — the buyer/end-user is identified (a name is present).

    Enforced at the C10 unified gate (`COMPLIANCE_ENFORCED`; deferred there,
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


def derive_kiln_registration_compliance(
    kiln_id: Optional[str],
    kiln_is_registered: bool,
    *,
    enforced: bool = COMPLIANCE_ENFORCED,
) -> tuple[bool, Optional[str]]:
    """Rainbow C8: the batch's kiln (telemetry `kiln_id`, C0) must be registered
    in the project kiln registry. `kiln_is_registered` is resolved by the caller
    (DB lookup). Inert when no kiln_id is declared (older flows) or unenforced.
    Returns (compliant, `unregistered_kiln`)."""
    if not enforced or not kiln_id:
        return True, None
    if not kiln_is_registered:
        return False, "unregistered_kiln"
    return True, None


def derive_scale_calibration_compliance(
    has_in_date_calibration: bool, *, enforced: bool = COMPLIANCE_ENFORCED
) -> tuple[bool, Optional[str]]:
    """Rainbow C8: the weighing scale must have an in-date calibration on file.
    `has_in_date_calibration` is resolved by the caller (a scale_calibrations row
    whose valid_until is in the future). Returns (compliant,
    `scale_calibration_expired`)."""
    if not enforced:
        return True, None
    if not has_in_date_calibration:
        return False, "scale_calibration_expired"
    return True, None


def derive_annual_methane_compliance(
    methane_run_count: Optional[int], *, enforced: bool = COMPLIANCE_ENFORCED
) -> tuple[bool, Optional[str]]:
    """Rainbow C9: the batch's project/period must have a current methane
    measurement over >= MIN_METHANE_RUNS representative runs. `methane_run_count`
    is resolved by the caller from the annual verification record. Returns
    (compliant, `missing_annual_methane`)."""
    if not enforced:
        return True, None
    if not methane_run_count or methane_run_count < MIN_METHANE_RUNS:
        return False, "missing_annual_methane"
    return True, None


def derive_pah_compliance(
    kiln_type: Optional[str],
    pah_measured: bool,
    *,
    enforced: bool = COMPLIANCE_ENFORCED,
) -> tuple[bool, Optional[str]]:
    """Rainbow C9: PAH measurement is MANDATORY for closed kilns. Inert for
    open/unknown kiln types (open-kiln PAH is not required). Returns (compliant,
    `missing_pah`)."""
    if not enforced or kiln_type != "closed":
        return True, None
    if not pah_measured:
        return False, "missing_pah"
    return True, None


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
    extra_reasons: Optional[list[str]] = None,
) -> Corroboration:
    """Combine the derived inputs into a Corroboration, computing provisional
    status and the ordered list of reasons a batch is not yet issuable.

    `attestation_ok` is the platform-integrity signal. Phase 9-R: real Play
    Integrity / DeviceCheck verification is not built yet, so the caller decides
    the policy — when enforcement is on and attestation is unverified, this adds
    `attestation_unverified` (fail closed). Defaults True so the check is inert
    until a verifier and the enforcement flag are enabled.

    `extra_reasons` (C10): additional issuance-gate reasons the caller derives
    from DB state (C1 biomass, C8 kiln registration + scale calibration, C9 annual
    methane + PAH), appended in caller order and de-duplicated.
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
    # C10: caller-supplied gate reasons (C1 biomass, C8 kiln/calibration, C9
    # methane/PAH) — already ordered by the caller; de-duplicated defensively.
    for r in extra_reasons or []:
        if r not in reasons:
            reasons.append(r)
    return Corroboration(
        wet_yield_kg=wet_yield,
        min_recorded_temp_c=min_temp,
        transport_distance_km=transport,
        provisional=bool(reasons),
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# P4.4 (H15) — cross-field plausibility. ADVISORY: each failing check adds a
# provisional reason (the batch stays PROVISIONAL for human review, never
# rejected). Bounds are deliberately generous and PENDING METHODOLOGY-OWNER
# REVIEW — they should flag only clearly-implausible values, not narrow the
# accepted operating envelope.
# ---------------------------------------------------------------------------
# Biochar mass yield from biomass is typically 0.15–0.45; flag only well outside.
YIELD_BIOMASS_RATIO_MIN = 0.05
YIELD_BIOMASS_RATIO_MAX = 0.60
# Biochar pyrolysis needs sustained heat; below this °C the "biochar" claim is
# physically implausible.
PYROLYSIS_MIN_C = 350.0
# At least this fraction of temperature samples should be in the pyrolysis range
# to substantiate a sustained-burn (min-temp) claim.
TEMP_SUSTAIN_MIN_FRACTION = 0.5
# Moisture variance sanity: a single biomass batch shouldn't span a huge moisture
# range. We flag implausibly HIGH spread (not zero variance — uniform biomass
# legitimately reads identically), so constant readings are never penalized.
MOISTURE_VARIANCE_MIN_READINGS = 5
MOISTURE_SPREAD_MAX_PCT = 40.0


def derive_plausibility_reasons(
    *,
    biomass_input_kg: Optional[float],
    wet_yield_kg: Optional[float],
    min_temp: Optional[float],
    temperature_readings: Optional[list],
    moisture_values: Optional[list],
) -> list[str]:
    """Pure cross-field plausibility checks (H15). Returns advisory provisional
    reasons; an empty list means nothing looked implausible."""
    reasons: list[str] = []

    # 1. Yield vs biomass ratio (yield stream cross-checked against batch biomass).
    if (
        biomass_input_kg
        and biomass_input_kg > 0
        and wet_yield_kg
        and wet_yield_kg > 0
    ):
        ratio = wet_yield_kg / biomass_input_kg
        if ratio < YIELD_BIOMASS_RATIO_MIN or ratio > YIELD_BIOMASS_RATIO_MAX:
            reasons.append("implausible_yield_biomass_ratio")

    # 2. Temp-log coverage vs the claimed min temp: a sustained burn should keep
    #    most samples in the pyrolysis range. Only checked once a min-temp claim
    #    exists (i.e. a qualifying, >= MIN_TEMPERATURE_SAMPLES log).
    temps = [t for t in (temperature_readings or []) if isinstance(t, (int, float))]
    if min_temp is not None and temps:
        in_range = sum(1 for t in temps if t >= PYROLYSIS_MIN_C)
        if in_range / len(temps) < TEMP_SUSTAIN_MIN_FRACTION:
            reasons.append("insufficient_temp_sustain")

    # 3. Moisture-reading variance sanity: an implausibly wide spread across one
    #    batch's readings suggests they aren't all from the same biomass. Uniform
    #    (identical) readings are legitimate, so only high spread is flagged.
    vals = [v for v in (moisture_values or []) if isinstance(v, (int, float))]
    if (
        len(vals) >= MOISTURE_VARIANCE_MIN_READINGS
        and (max(vals) - min(vals)) > MOISTURE_SPREAD_MAX_PCT
    ):
        reasons.append("implausible_moisture_spread")

    return reasons
