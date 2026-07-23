import asyncio
import hashlib
import hmac
import hmac_keys
import json
import logging
import observability
import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import (
    AnnualVerification,
    Batch,
    BulkDensityTest,
    CompositePileSample,
    DeviceKey,
    EndUseApplication,
    EnrollmentToken,
    Kiln,
    MediaFile,
    MoistureReading,
    OperatorTraining,
    Project,
    PyrolysisTelemetry,
    RegistryConfig,
    ScaleCalibration,
    SupervisorVisit,
    SystemMetadata,
    TransportEvent,
    YieldMetrics,
)
from lca_engine import (
    calculate_carbon_credit,
    params_from_json,
    sign_lca_audit,
    lca_sign_payload_bytes,
)
from corroboration import (
    assemble,
    derive_annual_methane_compliance,
    derive_biomass_compliance,
    derive_composite_sample_compliance,
    derive_delivery_compliance,
    derive_density_calibration_compliance,
    derive_ignition_compliance,
    derive_kiln_registration_compliance,
    derive_min_temp,
    derive_moisture_compliance,
    derive_pah_compliance,
    derive_plausibility_reasons,
    derive_pyrolysis_photo_compliance,
    derive_sampling_compliance,
    derive_scale_calibration_compliance,
    derive_transport_km,
    derive_wet_yield,
    derive_wet_yield_from_density,
)
from emission_factors import TRANSPORT_EVENTS_ENFORCED, fuel_emissions_kg_co2e
import attestation
from settings import _attestation_enforced
from geo import haversine_km, GPS_ANCHOR_MISMATCH_KM
from jsonsafe import _safe_json, _safe_json_async, _as_utc
from schemas import *

log = logging.getLogger(__name__)

# P3.7 globals
_recompute_lock = asyncio.Lock()
_recompute_state = {}
_RECOMPUTE_STATE_CAP = 8192
_recompute_run_count = 0


def _recompute_slot(buid: str) -> dict:
    st = _recompute_state.get(buid)
    if st is None:
        if len(_recompute_state) > _RECOMPUTE_STATE_CAP:
            # Drop idle, clean slots (never a locked/dirty one).
            for k in [
                k
                for k, v in _recompute_state.items()
                if not v["dirty"] and not v["lock"].locked()
            ][: len(_recompute_state) // 2]:
                _recompute_state.pop(k, None)
        st = {"lock": asyncio.Lock(), "dirty": False}
        _recompute_state[buid] = st
    return st


async def _resolve_lca_config(session: AsyncSession, project_id: str | None):
    """V8 Part 4 (G) — resolve this batch's methodology config, if any.

    Returns None (⇒ calculate_carbon_credit uses its CSI-3.2 default) unless
    the batch's project both exists AND has a registry_config_id pointing at
    a real RegistryConfig row. This is the explicit regression guarantee:
    every batch with no project_id, an unregistered project_id, or a project
    with no registry_config_id set gets EXACTLY today's behavior — nothing
    changes until an admin deliberately opts a project into a config.
    """
    if not project_id:
        return None
    project = (
        await session.execute(
            select(Project).where(Project.project_id == project_id)
        )
    ).scalar_one_or_none()
    if project is None or not project.registry_config_id:
        return None
    row = (
        await session.execute(
            select(RegistryConfig).where(
                RegistryConfig.config_id == project.registry_config_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    # methodology_version is its own RegistryConfig COLUMN (for querying/
    # display), not part of params_json — params_from_json alone never sees
    # it, so overlay the authoritative column value here.
    from dataclasses import replace

    return replace(
        params_from_json(row.params_json), methodology_version=row.methodology_version
    )


async def _device_registered_at(session: AsyncSession, device_id):
    """The DeviceKey.registered_at for a device, or None if unknown. Used only by
    the attestation grace check (P4.1)."""
    if not device_id:
        return None
    return (
        await session.execute(
            select(DeviceKey.registered_at).where(DeviceKey.device_id == device_id)
        )
    ).scalar_one_or_none()

@observability.timed_recompute
async def recompute_batch_credit(
    session: AsyncSession,
    batch: Batch,
    *,
    lab_h_corg: Optional[float] = None,
    lab_corg: Optional[float] = None,
    coalesce: bool = False,
) -> None:
    """Serialize (and optionally coalesce) recomputes for one batch.

    The lock prevents two concurrent recomputes of the same batch from racing on
    its credit/provisional fields (a lost-update guard). When ``coalesce=True``
    — used ONLY by the post-commit evidence path, where the caller's evidence is
    already committed — a caller returns early if another recompute already ran
    after it marked the batch dirty, since that run observed its committed
    evidence. Pre-commit callers (create_batch, lab) pass coalesce=False so they
    always run against their own session's pending state.
    """
    buid = str(batch.batch_uuid)
    st = _recompute_slot(buid)
    st["dirty"] = True
    async with st["lock"]:
        if coalesce and not st["dirty"]:
            return  # a concurrent recompute already reflected our evidence
        st["dirty"] = False
        await _recompute_batch_credit_impl(
            session, batch, lab_h_corg=lab_h_corg, lab_corg=lab_corg
        )


async def _recompute_batch_credit_impl(
    session: AsyncSession,
    batch: Batch,
    *,
    lab_h_corg: Optional[float] = None,
    lab_corg: Optional[float] = None,
) -> None:
    """Corroborate a batch's credit inputs from the telemetry/yield/application
    streams, recompute the LCA credit, and update the batch row in place.

    Pure derivation lives in corroboration.py; this is the thin DB glue. The
    caller commits. Idempotent — safe to call from create_batch and from every
    evidence endpoint so the credit converges as evidence arrives. A batch stays
    PROVISIONAL (never issued) until every input is corroborated.
    """
    global _recompute_run_count
    _recompute_run_count += 1
    buid = str(batch.batch_uuid)

    tel = (
        await session.execute(
            select(PyrolysisTelemetry).where(PyrolysisTelemetry.batch_uuid == buid)
        )
    ).scalar_one_or_none()
    yld = (
        await session.execute(
            select(YieldMetrics).where(YieldMetrics.batch_uuid == buid)
        )
    ).scalar_one_or_none()
    app_row = (
        await session.execute(
            select(EndUseApplication).where(EndUseApplication.batch_uuid == buid)
        )
    ).scalar_one_or_none()

    # H3: the telemetry payload is the large one (100k floats) — parse off-thread
    # when big. yield/application are small scalars, parsed inline.
    tel_payload = (
        await _safe_json_async(tel.payload_json, context=f"telemetry {buid}")
        if tel
        else None
    )
    yld_payload = _safe_json(yld.payload_json, context=f"yield {buid}") if yld else None
    app_payload = (
        _safe_json(app_row.payload_json, context=f"application {buid}") if app_row else None
    )

    # T2.1: platform attestation runs through the attestation.py verifier
    # interface. Real Play Integrity / DeviceCheck verification awaits provider
    # credentials, so a genuine token still returns unverified today — but the
    # wiring + enforcement switch are in place, and enabling
    # DMRV_ATTESTATION_ENFORCED makes an unverified batch PROVISIONAL. Module-
    # qualified call so tests can inject a verdict double via monkeypatch.
    attestation_blob = tel_payload.get("hw_attestation") if tel_payload else None
    _att_verdict = attestation.verify_attestation(attestation_blob)
    attestation_verified = _att_verdict.verified
    if attestation_blob and not attestation_verified:
        log.warning(
            "batch %s hw_attestation not verified: %s", buid, _att_verdict.reason
        )
    if not _attestation_enforced() or attestation_verified:
        attestation_ok = True
    else:
        # P4.1: enforced + unverified. Honor a grace window for devices that
        # enrolled BEFORE enforcement began, so flipping the flag on doesn't
        # instantly brick the existing fleet. Only queried on this rare path.
        reg_at = await _device_registered_at(session, batch.device_id)
        attestation_ok = attestation.attestation_in_grace(
            reg_at, datetime.now(timezone.utc)
        )
        if attestation_ok:
            log.info("batch %s attestation unverified but device in grace", buid)

    min_temp, _ = derive_min_temp(tel_payload)
    wet_yield, _ = derive_wet_yield(yld_payload)

    # Moved up from just before assemble()/calculate_carbon_credit below so
    # the C10 sampling-plan gate (PR-3.1) can use them; no other change in
    # behavior, since both depend only on the function args + batch fields
    # already available at this point.
    effective_lab = lab_h_corg if lab_h_corg is not None else batch.lab_h_corg
    effective_corg = lab_corg if lab_corg is not None else batch.organic_carbon_pct
    lca_config = await _resolve_lca_config(session, batch.project_id)

    # V8 Part 4 (F): resolve this batch's project-scoped bulk-density
    # calibration ONCE — reused below for both the volumetric yield fallback
    # and the production_requires_valid_density C10 gate. Inert (None) for a
    # batch with no project_id, mirroring every other project-scoped gate.
    density_row = None
    if batch.project_id:
        _now_bd = datetime.now(timezone.utc)
        _density_rows = (
            (
                await session.execute(
                    select(BulkDensityTest).where(
                        BulkDensityTest.project_id == batch.project_id
                    )
                )
            )
            .scalars()
            .all()
        )
        _in_date_density = [
            r for r in _density_rows
            if r.valid_until and _as_utc(r.valid_until) >= _now_bd
        ]
        density_row = _in_date_density[0] if _in_date_density else None

    wet_yield_density_derived = False
    if wet_yield is None and density_row is not None:
        _density_yield, _density_reason = derive_wet_yield_from_density(
            tel_payload, density_row.density_kg_per_l
        )
        if _density_yield is not None:
            wet_yield = _density_yield
            wet_yield_density_derived = True

    transport, _ = derive_transport_km(
        batch.latitude, batch.longitude, app_payload, haversine=haversine_km
    )

    # Rainbow C2: count photographed moisture readings and evaluate the ≥1/100 kg,
    # min-10 rule against the batch's biomass input.
    m_rows = (
        (
            await session.execute(
                select(MoistureReading).where(MoistureReading.batch_uuid == buid)
            )
        )
        .scalars()
        .all()
    )
    photographed = sum(
        1
        for r in m_rows
        if isinstance(_p := _safe_json(r.payload_json, context=f"moisture {buid}"), dict)
        and _p.get("sha256_hash")
    )
    moisture_ok, _ = derive_moisture_compliance(photographed, batch.biomass_input_kg)
    # P4.4: moisture reading values for the variance plausibility check.
    _moisture_values = [
        _mp.get("moisture_percent")
        for r in m_rows
        if isinstance(
            _mp := _safe_json(r.payload_json, context=f"moisture {buid}"), dict
        )
    ]

    # Rainbow C4: count photographed composite pile sub-samples. Inert by default
    # (enforced at the C10 unified gate) so existing flows are unaffected.
    cs_rows = (
        (
            await session.execute(
                select(CompositePileSample).where(
                    CompositePileSample.batch_uuid == buid
                )
            )
        )
        .scalars()
        .all()
    )
    photographed_samples = sum(
        1
        for r in cs_rows
        if isinstance(_p := _safe_json(r.payload_json, context=f"composite {buid}"), dict)
        and _p.get("sha256_hash")
    )
    composite_sample_ok, _ = derive_composite_sample_compliance(photographed_samples)

    # Rainbow C3/C3b: kiln-type-conditional pyrolysis-photo, flame-height and
    # ignition-energy compliance, read from the telemetry payload. Inert unless
    # kiln_type is explicitly 'open'/'closed'.
    kiln_type = tel_payload.get("kiln_type") if tel_payload else None
    photos_ok, flame_ok = derive_pyrolysis_photo_compliance(
        kiln_type,
        tel_payload.get("smoke_evidence") if tel_payload else None,
        tel_payload.get("flame_height_m") if tel_payload else None,
    )
    ignition_ok = derive_ignition_compliance(
        kiln_type,
        tel_payload.get("ignition_energy_type") if tel_payload else None,
    )

    # Rainbow C5: delivery record + buyer identity, read from the /application
    # payload. Inert by default (enforced at the C10 unified gate).
    delivery_ok, buyer_ok = derive_delivery_compliance(app_payload)

    # Rainbow C6: transport events. AUDIT-ONLY while TRANSPORT_EVENTS_ENFORCED is
    # False — we sum the per-leg fuel emissions and run a GPS-vs-reported
    # under-reporting cross-check, but neither touches the issued credit (the
    # GPS-haversine transport penalty in the LCA stays authoritative until the
    # methodology's real fuel emission factors are cited; see emission_factors.py).
    te_rows = (
        (
            await session.execute(
                select(TransportEvent).where(TransportEvent.batch_uuid == buid)
            )
        )
        .scalars()
        .all()
    )
    te_payloads = [
        _p
        for r in te_rows
        if isinstance(_p := _safe_json(r.payload_json, context=f"transport {buid}"), dict)
    ]
    transport_fuel_co2e_kg = sum(
        fuel_emissions_kg_co2e(p.get("fuel_type"), p.get("fuel_amount_litres"))
        for p in te_payloads
    )
    reported_transport_km = sum((p.get("distance_km") or 0.0) for p in te_payloads)
    # Cross-check: the GPS-derived transport (production→application haversine) is
    # a lower bound on real hauling; if the operator's REPORTED legs sum to far
    # less than the GPS distance, the fuel/transport burden is being under-stated.
    # Flag for review (audit-only) — never gates issuance here.
    gps_km = transport if transport is not None else 0.0
    transport_underreported = bool(
        te_payloads and gps_km > 0.0 and reported_transport_km < 0.5 * gps_km
    )

    # ---- Rainbow C10: unified issuance-gate signals -------------------------
    # Fold the methodology checks into the provisional gate. Project/scale-scoped
    # checks (scale calibration, annual methane, PAH) resolve through the batch's
    # project_id/scale_id linkage (T1.1); they stay inert for legacy batches that
    # carry no linkage, so those are never gated spuriously.
    c10_reasons: list[str] = []

    # C1: biomass input amount + method (persisted on the batch).
    _biomass_ok, _biomass_reason = derive_biomass_compliance(
        batch.biomass_input_kg, batch.biomass_measurement_method
    )
    if _biomass_reason:
        c10_reasons.append(_biomass_reason)

    # C8: the batch's kiln (telemetry kiln_id) must be in the project registry.
    kiln_id = tel_payload.get("kiln_id") if tel_payload else None
    kiln_registered = False
    if kiln_id:
        kiln_registered = (
            await session.execute(select(Kiln.id).where(Kiln.kiln_id == kiln_id))
        ).first() is not None
    _kiln_ok, _kiln_reason = derive_kiln_registration_compliance(
        kiln_id, kiln_registered
    )
    if _kiln_reason:
        c10_reasons.append(_kiln_reason)

    # C8 (T1.2): the batch's weighing scale must have an in-date calibration.
    # Inert when the batch has no scale linkage (legacy batches / no scale_id).
    # The validity comparison is done in Python (not SQL) so it is identical on
    # the SQLite test path and Postgres regardless of stored-tz handling.
    if batch.scale_id:
        _now = datetime.now(timezone.utc)
        _cal_valid_untils = (
            (
                await session.execute(
                    select(ScaleCalibration.valid_until).where(
                        ScaleCalibration.scale_id == batch.scale_id,
                        ScaleCalibration.valid_until.is_not(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        _has_in_date_cal = any(_as_utc(vu) >= _now for vu in _cal_valid_untils)
        _sc_ok, _sc_reason = derive_scale_calibration_compliance(_has_in_date_cal)
        if _sc_reason:
            c10_reasons.append(_sc_reason)

    # V8 Part 4 (F): production_requires_valid_density — mirrors the scale
    # gate above exactly. Inert for a batch with no project_id. Applies
    # regardless of whether THIS batch's yield used the volumetric fallback
    # (an equipment-calibration QA gate, same convention as scale_calibration_
    # expired). `density_row` was already resolved above (reused, not re-queried).
    if batch.project_id:
        _dc_ok, _dc_reason = derive_density_calibration_compliance(
            density_row is not None
        )
        if _dc_reason:
            c10_reasons.append(_dc_reason)
    if wet_yield_density_derived:
        # Transparency flag (not a gate): this batch's yield came from
        # volume × density, not a direct crane-scale weight — auditable, but
        # not itself grounds to withhold issuance.
        c10_reasons.append("wet_yield_density_derived")

    # PR-3.1: representative-sampling cadence, config-driven (inert unless a
    # project's RegistryConfig sets sampling_kg_per_lab_result — no invented
    # number). in_scope_lab_result_count is this batch's own C7 lab result
    # (1 if present, else 0) — the batch's already-persisted representative
    # sample, not a cross-batch/facility count (no such linkage exists yet).
    _samp_ok, _samp_reason = derive_sampling_compliance(
        wet_yield,
        1 if effective_lab is not None else 0,
        lca_config.sampling_kg_per_lab_result if lca_config is not None else None,
    )
    if _samp_reason:
        c10_reasons.append(_samp_reason)

    # C9 (T1.3): the batch's project must have a methane verification (>= 3
    # representative runs) for the batch's production year. Inert when the batch
    # has no project linkage. The verification row is reused by the PAH gate
    # below. Year policy: harvest-timestamp year (production vintage) — flagged
    # to the methodology owner in the T1.3 PR.
    annual_verif = None
    if batch.project_id:
        _verif_year = batch.harvest_timestamp.year
        annual_verif = (
            await session.execute(
                select(AnnualVerification).where(
                    AnnualVerification.project_id == batch.project_id,
                    AnnualVerification.year == _verif_year,
                )
            )
        ).scalar_one_or_none()
        _am_ok, _am_reason = derive_annual_methane_compliance(
            annual_verif.methane_run_count if annual_verif else None
        )
        if _am_reason:
            c10_reasons.append(_am_reason)

    # C9 (T1.4): PAH measurement is mandatory for closed kilns, resolved from the
    # project-year verification fetched above. Inert when the batch has no project
    # linkage or kiln_type isn't explicitly 'closed' (the deriver also guards
    # kiln-conditionality). The deriver now runs under the default
    # COMPLIANCE_ENFORCED policy — the previous hardcoded bypass is removed.
    if batch.project_id and kiln_type == "closed":
        _pah_measured = bool(annual_verif and annual_verif.pah_measured)
        _pah_ok, _pah_reason = derive_pah_compliance(kiln_type, _pah_measured)
        if _pah_reason:
            c10_reasons.append(_pah_reason)

    # P4.4 (H15): cross-field plausibility. Advisory — each failing check adds a
    # provisional reason for human review; it never rejects or auto-issues.
    c10_reasons.extend(
        derive_plausibility_reasons(
            biomass_input_kg=batch.biomass_input_kg,
            wet_yield_kg=wet_yield,
            min_temp=min_temp,
            temperature_readings=(
                tel_payload.get("temperature_readings") if tel_payload else None
            ),
            moisture_values=_moisture_values,
        )
    )

    corr = assemble(
        wet_yield,
        min_temp,
        transport,
        has_lab_hcorg=effective_lab is not None,
        has_lab_corg=effective_corg is not None,
        attestation_ok=attestation_ok,
        moisture_ok=moisture_ok,
        pyrolysis_photos_ok=photos_ok,
        flame_height_ok=flame_ok,
        ignition_ok=ignition_ok,
        composite_sample_ok=composite_sample_ok,
        delivery_ok=delivery_ok,
        buyer_ok=buyer_ok,
        extra_reasons=c10_reasons,
    )

    kwargs = {}
    if effective_lab is not None:
        kwargs["h_corg_ratio"] = effective_lab
    if effective_corg is not None:
        kwargs["corg_override"] = effective_corg

    if lca_config is not None:
        kwargs["config"] = lca_config

    lca = calculate_carbon_credit(
        wet_yield_kg=corr.wet_yield_kg if corr.wet_yield_kg is not None else 0.0,
        moisture_percent=batch.moisture_percent,
        min_recorded_temp_c=(
            corr.min_recorded_temp_c if corr.min_recorded_temp_c is not None else 0.0
        ),
        transport_distance_km=(
            corr.transport_distance_km
            if corr.transport_distance_km is not None
            else 0.0
        ),
        feedstock_species=batch.feedstock_species,
        **kwargs,
    )

    # Persist derived inputs (0.0 where uncorroborated; columns are NOT NULL).
    batch.wet_yield_kg = corr.wet_yield_kg if corr.wet_yield_kg is not None else 0.0
    batch.min_recorded_temp_c = (
        corr.min_recorded_temp_c if corr.min_recorded_temp_c is not None else 0.0
    )
    batch.transport_distance_km = (
        corr.transport_distance_km if corr.transport_distance_km is not None else 0.0
    )
    if lab_h_corg is not None:
        batch.lab_h_corg = lab_h_corg
    if lab_corg is not None:
        batch.organic_carbon_pct = lab_corg
    # Provisional if any input is uncorroborated OR H:Corg / Corg was assumed.
    batch.provisional = corr.provisional or lca.provisional or lca.corg_assumed
    batch.provisional_reasons = json.dumps(corr.reasons)
    batch.net_credit_t_co2e = lca.net_credit_t_co2e
    batch.lca_methodology_version = lca.methodology_version
    # Rainbow C6 audit trail (audit-only; not part of the signed credit while
    # transport events are unenforced — see emission_factors.TRANSPORT_EVENTS_ENFORCED).
    audit = {k: v for k, v in lca.__dict__.items()}
    audit["transport_events"] = {
        "enforced": TRANSPORT_EVENTS_ENFORCED,
        "event_count": len(te_payloads),
        "fuel_co2e_kg": transport_fuel_co2e_kg,
        "reported_transport_km": reported_transport_km,
        "gps_transport_km": gps_km,
        "underreported_flag": transport_underreported,
    }
    # T2.7: surface the device-integrity plausibility signals per batch so a
    # verifier sees the trust level in-band. exif_trust documents that the GPS
    # anchor is client-authored (weak) — the strong control is attestation.
    audit["integrity_signals"] = {
        "mock_location_enabled": bool(batch.mock_location_enabled),
        "gps_anchor_status": batch.status,
        "gps_anchor_mismatch_km": GPS_ANCHOR_MISMATCH_KM,
        "exif_trust": "client_authored_weak",
    }
    # Audit fix 5: the HMAC lca_signature covers only the LCAAudit dataclass;
    # transport_events/integrity_signals are appended after that snapshot, so a
    # DB tamper of those sections was undetectable. Bind the FULL audit JSON
    # with its own HMAC under the active key (recorded key id makes it
    # rotation-safe). Existing rows lack the field and verify as before.
    _audit_body = json.dumps(audit, sort_keys=True)
    _fk_id, _fk_secret = hmac_keys.active_key()
    audit["full_audit_hmac"] = {
        "key_id": _fk_id,
        "hmac_sha256": hmac.new(
            _fk_secret.encode(), _audit_body.encode(), hashlib.sha256
        ).hexdigest(),
    }
    batch.lca_audit_json = json.dumps(audit)
    # Phase 8-R: only a fully-corroborated, non-provisional batch carries an
    # issuance signature. A provisional audit must never look issuable downstream.
    # P3.6: sign under the ACTIVE versioned key and record its id, so a later key
    # rotation never invalidates this signature.
    if batch.provisional:
        batch.lca_signature = None
        batch.lca_signature_key_id = None
    else:
        _key_id, _secret = hmac_keys.active_key()
        batch.lca_signature = sign_lca_audit(
            lca, _secret, batch_uuid=str(batch.batch_uuid)
        )
        batch.lca_signature_key_id = _key_id


def verify_lca_signature(batch: Batch, lca) -> str:
    """P3.6: verify a batch's lca_signature under the key it was signed with.

    Returns 'unsigned' (no signature), 'unverifiable' (the signing key id is no
    longer in the environment — rotated out), 'valid', or 'invalid'. Never raises
    on a missing key so a caller can surface the state instead of 500ing.
    """
    if not batch.lca_signature:
        return "unsigned"
    payload = lca_sign_payload_bytes(lca, batch_uuid=str(batch.batch_uuid))
    return hmac_keys.verify(payload, batch.lca_signature, batch.lca_signature_key_id)


def verify_full_audit_hmac(lca_audit_json: str) -> str:
    """Audit fix 5: verify the whole-audit HMAC. Returns 'unsigned' (rows
    predating the field), 'unverifiable' (key rotated out), 'valid' or
    'invalid'. Never raises."""
    try:
        audit = json.loads(lca_audit_json or "null")
    except (ValueError, TypeError):
        return "invalid"
    if not isinstance(audit, dict) or "full_audit_hmac" not in audit:
        return "unsigned"
    seal = audit.pop("full_audit_hmac")
    body = json.dumps(audit, sort_keys=True)
    secret = hmac_keys.key_for((seal or {}).get("key_id"))
    if secret is None:
        return "unverifiable"
    expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return "valid" if hmac.compare_digest(expected, (seal or {}).get("hmac_sha256", "")) else "invalid"


