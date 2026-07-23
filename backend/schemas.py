from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID
import uuid
from lca_engine import CORG_TABLE

class BatchPayload(BaseModel):
    """Strict Pydantic V2 model for batch payload."""

    batch_uuid: str = Field(..., max_length=36)
    feedstock_species: str
    harvest_timestamp: datetime
    moisture_percent: float = Field(..., ge=0.0, le=100.0)
    photo_path: Optional[str] = Field(None, max_length=512)
    sha256_hash: Optional[str] = Field(None, min_length=64, max_length=64)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    harvest_uptime_seconds: Optional[int] = Field(0, ge=0)

    sourcing_uuid: Optional[str] = Field(None, max_length=64)
    moisture_compliant: Optional[bool] = None
    mock_location_enabled: Optional[bool] = False
    # Compass telemetry (advisory). Generous ±360 bounds accept any sensor
    # convention while blocking absurd floats (P1-B5b).
    azimuth: Optional[float] = Field(None, ge=-360.0, le=360.0)
    pitch: Optional[float] = Field(None, ge=-360.0, le=360.0)
    roll: Optional[float] = Field(None, ge=-360.0, le=360.0)

    # Rainbow compliance C1: biomass input amount + how it was measured.
    biomass_input_kg: Optional[float] = Field(None, ge=0.0, le=1_000_000.0)
    biomass_measurement_method: Optional[
        Literal["direct_weigh", "yield_conversion"]
    ] = None

    # Rainbow T1.1: optional batch->project/scale linkage. Configured on the
    # device (dart-define) — enables the project-scoped C8/C9 gates. Old clients
    # omit these; the gates stay inert for their batches.
    project_id: Optional[str] = Field(None, min_length=1, max_length=128)
    scale_id: Optional[str] = Field(None, min_length=1, max_length=128)

    # V8 Part 1 (A): optional source-parcel linkage. When present, the batch's
    # claimed GPS coordinate is checked point-in-polygon against the approved,
    # non-overlapping parcel (geo.py → QUARANTINE_GPS_OUTSIDE_PARCEL); the photo
    # EXIF must independently agree with the claim within the mismatch threshold,
    # so the geofence rides on top of the existing GPS corroboration. OPTIONAL
    # and additive: old app builds omit it (the geofence stays inert for their
    # batches — grandfathered), so no signed-body 422 regression.
    parcel_uuid: Optional[str] = Field(None, min_length=1, max_length=36)

    # --- LCA inputs (Prompt 8) ---
    # Phase 7-R: these are NOT client-supplied. They are corroborated server-side
    # from the /telemetry (min temp), /yield (wet yield) and /application (transport
    # GPS) streams, which arrive AFTER the batch. They are optional on the payload;
    # an uncorroborated input keeps the batch PROVISIONAL (never issued as final).
    wet_yield_kg: Optional[float] = Field(
        None, gt=0.0, le=100_000.0, description="Corroborated server-side from /yield"
    )
    min_recorded_temp_c: Optional[float] = Field(
        None,
        ge=-50.0,
        le=1500.0,
        description="Corroborated server-side from /telemetry",
    )
    transport_distance_km: Optional[float] = Field(
        None,
        ge=0.0,
        le=20000.0,
        description="Corroborated server-side from /application GPS",
    )

    @field_validator("feedstock_species")
    @classmethod
    def validate_feedstock(cls, v: str) -> str:
        if v not in CORG_TABLE:
            raise ValueError(
                f"feedstock_species must be one of {list(CORG_TABLE.keys())}"
            )
        return v

    @field_validator("sha256_hash")
    @classmethod
    def validate_hex(cls, v: Optional[str]) -> Optional[str]:
        """Ensure SHA-256 hash is valid hexadecimal."""
        if v is None:
            return v
        try:
            int(v, 16)
        except ValueError:
            raise ValueError("sha256_hash must be valid hexadecimal")
        return v.lower()

    # Phase 7-R: the payload-temp validator was removed. min_recorded_temp_c is
    # no longer client-asserted; the <100 C / >=60-sample burn-compliance rule now
    # lives in corroboration.derive_min_temp against the real /telemetry log.

    # Phase 8-R: lab_h_corg is NOT accepted from the device. A lab-measured
    # permanence ratio is authoritative and must arrive on the admin-authenticated
    # /api/v1/admin/lab-hcorg channel (range-checked). extra="forbid" now 422s any
    # client that tries to self-assert it.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BatchResponse(BaseModel):
    batch_uuid: str
    operation_id: str
    status: str
    duplicate: bool
    received_at: datetime
    net_credit_t_co2e: Optional[float] = None
    # Phase 8: True when net_credit_t_co2e was computed on an ASSUMED H:Corg
    # (no lab value). Such a credit is NOT issuable as final.
    provisional: Optional[bool] = None


class MediaUploadResponse(BaseModel):
    server_sha256: str
    stored: bool
    file_path: str


class RegistrationRequest(BaseModel):
    device_id: str = Field(..., min_length=1)
    public_key: str = Field(..., min_length=40, max_length=64)  # base64url Ed25519


class RegistrationResponse(BaseModel):
    status: str
    device_id: str


class MintTokenRequest(BaseModel):
    token: str
    expires_in_days: int = 7


class LabHCorgRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_uuid: str = Field(..., max_length=36)
    # Physically plausible H:Corg molar ratio for biochar (~0.1–0.7 typical; Lantana
    # ~0.3–0.35). Bounds reject forged/absurd values that would inflate permanence.
    lab_h_corg: float = Field(..., ge=0.1, le=1.5)


class LabResultsRequest(BaseModel):
    """C7 full per-batch lab-results channel (admin-authenticated, range-checked).

    All fields optional so a lab can report incrementally. `organic_carbon_pct` is
    the credit-affecting one (replaces the species CORG_TABLE constant); `lab_h_corg`
    is accepted here too so a single lab report can supply both permanence inputs.
    The rest are captured for verification / the 1000-year pathway (gated to C8).
    """

    model_config = ConfigDict(extra="forbid")
    batch_uuid: str = Field(..., max_length=36)
    lab_h_corg: Optional[float] = Field(None, ge=0.1, le=1.5)
    # Organic carbon as a FRACTION in (0, 1] (e.g. Lantana ~0.60), matching CORG_TABLE.
    organic_carbon_pct: Optional[float] = Field(None, gt=0.0, le=1.0)
    # Biochar moisture: the methodology requires >= 3 samples when measured by mass.
    biochar_moisture_samples: Optional[list[float]] = Field(
        None, min_length=3, max_length=100
    )
    dry_bulk_density: Optional[float] = Field(None, gt=0.0, le=2000.0)
    # 1000-year pathway inputs (data capture only in C7; pathway gated to C8).
    inertinite_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    residual_corg_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    ro_measurements_count: Optional[int] = Field(None, ge=0)

    @field_validator("biochar_moisture_samples")
    @classmethod
    def _validate_moisture_samples(
        cls, v: Optional[list[float]]
    ) -> Optional[list[float]]:
        if v is not None and any((m < 0.0 or m > 100.0) for m in v):
            raise ValueError("biochar_moisture_samples must be percentages in [0, 100]")
        return v


class _BatchScopedPayload(BaseModel):
    """Base for evidence payloads that reference a batch by UUID string (P1-B4).

    Evidence tables store batch_uuid as String(36) and are joined against the
    batches row's canonical UUID. A non-canonical case (e.g. an uppercase UUID
    from a future client) would silently orphan the evidence on a case-sensitive
    engine, so canonicalize to the lowercase str(UUID(...)) form here and reject
    a malformed value with 422 rather than storing an unmatchable key.
    """

    model_config = ConfigDict(extra="forbid")

    @field_validator("batch_uuid", check_fields=False)
    @classmethod
    def _canonicalize_batch_uuid(cls, v: str) -> str:
        try:
            return str(uuid.UUID(str(v)))
        except (ValueError, AttributeError, TypeError):
            raise ValueError("batch_uuid must be a valid UUID")


class KilnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kiln_id: str = Field(..., min_length=1, max_length=128)
    material: Optional[str] = Field(None, max_length=128)
    weight_kg: Optional[float] = Field(None, ge=0.0, le=1_000_000.0)
    lifetime_years: Optional[float] = Field(None, ge=0.0, le=200.0)
    kiln_type: Optional[Literal["open", "closed"]] = None

    @field_validator("kiln_type", mode="before")
    @classmethod
    def lower_kiln_type(cls, v):
        return v.lower() if isinstance(v, str) else v


class OperatorTrainingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_uuid: str = Field(..., max_length=64)
    operator_id: Optional[str] = Field(None, max_length=128)
    training_type: Optional[str] = Field(None, max_length=128)
    completed_at: Optional[str] = Field(None, max_length=64)
    report_sha256: Optional[str] = Field(None, min_length=64, max_length=64)


class SupervisorVisitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visit_uuid: str = Field(..., max_length=64)
    kiln_id: Optional[str] = Field(None, max_length=128)
    visited_at: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = Field(None, max_length=2000)
    report_sha256: Optional[str] = Field(None, min_length=64, max_length=64)


class ScaleCalibrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    calibration_uuid: str = Field(..., max_length=64)
    scale_id: Optional[str] = Field(None, max_length=128)
    calibrated_at: Optional[str] = Field(None, max_length=64)
    valid_until: Optional[str] = Field(None, max_length=64)
    report_sha256: Optional[str] = Field(None, min_length=64, max_length=64)


class AnnualVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(..., min_length=1, max_length=128)
    year: int = Field(..., ge=2000, le=2100)
    # Methane emission rate over >= 3 representative runs (independent provider).
    methane_rate_g_per_kg: Optional[float] = Field(None, ge=0.0, le=100_000.0)
    methane_run_count: Optional[int] = Field(None, ge=0)
    # Biomass->biochar conversion factor (if not directly weighing biomass).
    conversion_factor: Optional[float] = Field(None, gt=0.0, le=100.0)
    pah_measured: Optional[bool] = None
    heavy_metals_measured: Optional[bool] = None
    leakage_assessment_done: Optional[bool] = None
    dry_bulk_density: Optional[float] = Field(None, gt=0.0, le=2000.0)
    quality_oversight_sha256: Optional[str] = Field(None, min_length=64, max_length=64)
    report_sha256: Optional[str] = Field(None, min_length=64, max_length=64)

class TelemetryPayload(_BatchScopedPayload):
    model_config = ConfigDict(extra="forbid")
    telemetry_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    kiln_gross_capacity: Optional[float] = Field(None, ge=0.0, le=100_000.0)
    burn_start_timestamp: Optional[str] = Field(None, max_length=64)
    burn_end_timestamp: Optional[str] = Field(None, max_length=64)
    min_temp: Optional[float] = Field(None, ge=-50.0, le=1500.0)
    max_temp: Optional[float] = Field(None, ge=-50.0, le=1500.0)
    temperature_readings: Optional[list[float]] = Field(None, max_length=100_000)
    smoke_evidence: Optional[list[dict]] = Field(None, max_length=1_000)
    hw_attestation: Optional[list] = Field(None, max_length=1_000)
    # Rainbow compliance C0: kiln type/id (persisted in payload_json).
    kiln_type: Optional[Literal["open", "closed"]] = None
    kiln_id: Optional[str] = Field(None, max_length=128)
    # Rainbow compliance C3 (open-kiln) / C3b (closed-kiln); read from payload_json
    # by recompute_batch_credit for kiln-type-conditional compliance.
    flame_height_m: Optional[float] = Field(None, ge=0.0, le=5.0)
    ignition_energy_type: Optional[str] = Field(None, max_length=128)
    ignition_energy_amount: Optional[float] = Field(None, ge=0.0, le=1_000_000.0)

    @field_validator("temperature_readings")
    @classmethod
    def _validate_temp_range(cls, v: Optional[list[float]]) -> Optional[list[float]]:
        # Phase 15-C: every reading must be physically plausible so a fabricated
        # constant array can't inflate the burn-quality (CH4) gate with absurd values.
        if v is not None and any((t < -50.0 or t > 1500.0) for t in v):
            raise ValueError("temperature_readings values must be in [-50, 1500] C")
        return v
class YieldPayload(_BatchScopedPayload):
    model_config = ConfigDict(extra="forbid")
    yield_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    quench_methodology: Optional[str] = Field(None, max_length=128)
    gross_volume: Optional[float] = Field(None, ge=0.0, le=100_000.0)
    # Phase 15-C: hard upper bound so a single self-asserted field can't linearly
    # inflate the credit to arbitrary size (100 t/batch ceiling — confirm vs real
    # kiln throughput). A kiln-capacity cross-check remains a documented follow-up.
    wet_yield_weight_kg: Optional[float] = Field(None, gt=0.0, le=100_000.0)
    dry_yield_weight_kg: Optional[float] = Field(None, ge=0.0, le=100_000.0)
class MetadataPayload(_BatchScopedPayload):
    model_config = ConfigDict(extra="forbid")
    batch_uuid: str = Field(..., max_length=64)
    artisan_id: Optional[str] = Field(None, max_length=128)
    device_hardware_mac: Optional[str] = Field(None, max_length=128)
    app_build_version: Optional[str] = Field(None, max_length=128)
    sync_status: Optional[str] = Field(None, max_length=64)
    created_at: Optional[str] = Field(None, max_length=64)
class ApplicationPayload(_BatchScopedPayload):
    model_config = ConfigDict(extra="forbid")
    application_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    application_methodology: Optional[str] = Field(None, max_length=128)
    application_rate_tonnes: Optional[float] = Field(None, ge=0.0, le=1_000_000.0)
    transport_distance_km: Optional[float] = Field(None, ge=0.0, le=20000.0)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    farmer_photo_path: Optional[str] = Field(None, max_length=512)
    farmer_photo_sha256: Optional[str] = Field(None, max_length=64)
    # Rainbow compliance C5: delivery record + buyer/end-user identity.
    # Persisted in payload_json (no server column); read by
    # derive_delivery_compliance in recompute_batch_credit.
    delivery_date: Optional[str] = Field(None, max_length=64)
    delivered_amount_kg: Optional[float] = Field(None, ge=0.0, le=100_000.0)
    buyer_name: Optional[str] = Field(None, max_length=256)
    buyer_contact: Optional[str] = Field(None, max_length=256)
class MoisturePayload(_BatchScopedPayload):
    # Rainbow compliance C2: one moisture-meter reading (many per batch).
    model_config = ConfigDict(extra="forbid")
    reading_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    moisture_percent: float = Field(..., ge=0.0, le=100.0)
    sequence: int = Field(..., ge=1)
    photo_path: Optional[str] = Field(None, max_length=512)
    sha256_hash: Optional[str] = Field(None, min_length=64, max_length=64)
class CompositeSamplePayload(_BatchScopedPayload):
    # Rainbow compliance C4: one site composite pile sub-sample (many per batch).
    model_config = ConfigDict(extra="forbid")
    sample_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    sampled_at: Optional[str] = Field(None, max_length=64)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    kiln_qr: Optional[str] = Field(None, max_length=128)
    batch_qr: Optional[str] = Field(None, max_length=128)
    photo_path: Optional[str] = Field(None, max_length=512)
    sha256_hash: Optional[str] = Field(None, min_length=64, max_length=64)
class TransportEventPayload(_BatchScopedPayload):
    # Rainbow compliance C6: one transport leg (many per batch).
    model_config = ConfigDict(extra="forbid")
    event_uuid: str = Field(..., max_length=64)
    batch_uuid: str = Field(..., max_length=64)
    material: Literal["biomass", "biochar"]
    distance_km: Optional[float] = Field(None, ge=0.0, le=20000.0)
    weight_kg: Optional[float] = Field(None, ge=0.0, le=1_000_000.0)
    vehicle_type: Optional[str] = Field(None, max_length=128)
    fuel_type: Optional[str] = Field(None, max_length=64)
    fuel_amount_litres: Optional[float] = Field(None, ge=0.0, le=100_000.0)
    occurred_at: Optional[str] = Field(None, max_length=64)


class FarmerDocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doc_type: Literal["aadhaar", "pan", "passport", "nid"]
    last4: str = Field(..., min_length=4, max_length=4)
    media_id: str = Field(..., max_length=64)


_MASK_CHARS = frozenset("*xX•#")


class FarmerPaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rail: Literal["bank", "upi", "mfs"]
    account_holder: Optional[str] = Field(None, max_length=255)
    masked_account: Optional[str] = Field(None, max_length=255)
    ifsc_code: Optional[str] = Field(None, max_length=32)
    masked_upi_id: Optional[str] = Field(None, max_length=255)
    masked_mfs_id: Optional[str] = Field(None, max_length=255)

    @field_validator("masked_account", "masked_upi_id", "masked_mfs_id")
    @classmethod
    def _enforce_masking(cls, v: Optional[str]) -> Optional[str]:
        """Server-side guard so a FULL account/card/phone number can never be
        stored in a field named 'masked_*'. The masking used to be a naming
        convention only — a device could put a full number here and it would
        land in plaintext Postgres. Reject any value with a long run of digits
        (≥7) that carries no masking character."""
        if v is None:
            return v
        digit_count = sum(c.isdigit() for c in v)
        if digit_count >= 7 and not any(c in _MASK_CHARS for c in v):
            raise ValueError(
                "payment identifier appears unmasked; store a masked value "
                "(e.g. 'XXXXXX3210'), never the full number"
            )
        return v


class FarmerConsentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fpic_template_id: Optional[str] = Field(None, max_length=128)
    signed_pdf_media_id: Optional[str] = Field(None, max_length=64)
    holding_photo_media_id: Optional[str] = Field(None, max_length=64)
    signed_at: Optional[datetime] = None
    exclusivity_ack: bool


class FarmerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    farmer_uuid: str = Field(..., min_length=36, max_length=36)
    project_id: str = Field(..., min_length=1, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    gender: Optional[str] = Field(None, max_length=32)
    guardian_name: Optional[str] = Field(None, max_length=255)
    dob: Optional[datetime] = None
    mobile_number: str = Field(..., min_length=1, max_length=32)
    education: Optional[str] = Field(None, max_length=128)
    family_size: Optional[int] = Field(None, ge=0)
    reported_area: Optional[float] = Field(None, ge=0.0)
    village: Optional[str] = Field(None, max_length=255)
    kyc_status: Optional[str] = Field(None, max_length=32)
    consent_status: Optional[str] = Field(None, max_length=32)
    signature_media_id: Optional[str] = Field(None, max_length=64)
    sync_status: Optional[str] = Field(None, max_length=32)
    
    documents: list[FarmerDocumentCreate] = Field(default_factory=list)
    payments: list[FarmerPaymentCreate] = Field(default_factory=list)
    consents: list[FarmerConsentCreate] = Field(default_factory=list)


class DispatchSiteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parcel_uuid: Optional[str] = Field(None, max_length=36)
    moisture_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    truck_percentage_filled: Optional[float] = Field(None, ge=0.0, le=100.0)


class DispatchCreate(BaseModel):
    """V8 Part 3.3 — device-signed dispatch creation (draft). Re-POSTing the
    same dispatch_uuid while still 'draft' is an idempotent upsert (lets the
    operator edit fields before Submit); once the dispatch has left 'draft'
    this endpoint 409s (weight-lock / sequential-stage gating)."""

    model_config = ConfigDict(extra="forbid")
    dispatch_uuid: str = Field(..., min_length=36, max_length=36)
    kind: Literal["biomass", "biochar"]
    source_ref: Optional[str] = Field(None, max_length=128)
    dest_facility_uuid: Optional[str] = Field(None, max_length=36)
    weight_source_kg: Optional[float] = Field(None, gt=0.0, le=1_000_000.0)
    weight_source_method: Optional[str] = Field(None, max_length=64)
    driver_name: Optional[str] = Field(None, max_length=255)
    driver_phone: Optional[str] = Field(None, max_length=32)
    truck_number: Optional[str] = Field(None, max_length=32)
    sites: list[DispatchSiteInput] = Field(default_factory=list)


class DayStartAuditCreate(BaseModel):
    """PR-5.1a — device-signed day-start audit creation. Client-generated
    audit_uuid + idempotent upsert on (facility_uuid, audit_date), mirroring
    DispatchCreate's create pattern."""

    model_config = ConfigDict(extra="forbid")
    audit_uuid: str = Field(..., min_length=36, max_length=36)
    facility_uuid: str = Field(..., min_length=1, max_length=36)
    audit_date: str = Field(..., min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")


class DispatchTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_status: Literal["in_transit", "received"]
    # Required only when target_status == "received" (the facility's witnessed
    # re-weigh); validated in the router against dispatch_state's rules.
    weight_facility_kg: Optional[float] = Field(None, gt=0.0, le=1_000_000.0)


class FieldWalkSubmit(BaseModel):
    """V8 Part 5 (A phase-2) — device submission of a GPS boundary walk.

    `link_payload`/`link_kid`/`link_signature` are the server-signed
    field-walk link exactly as minted by
    `POST /portal/parcels/{uuid}/field-walk-link` (see server_signing.py) —
    the router re-verifies this signature, expiry, and single-use nonce
    before trusting `points` at all. `points` are [lon, lat] pairs in walk
    order; the router closes the ring and validates it via
    `geometry.polygon_from_track_points`.
    """

    model_config = ConfigDict(extra="forbid")
    link_payload: str = Field(..., max_length=2000)
    link_kid: str = Field(..., max_length=32)
    link_signature: str = Field(..., max_length=512)
    points: list[list[float]] = Field(..., min_length=3, max_length=5000)

    @field_validator("points")
    @classmethod
    def _points_are_lon_lat_pairs(cls, v: list[list[float]]) -> list[list[float]]:
        for pt in v:
            if len(pt) != 2:
                raise ValueError("each point must be a [lon, lat] pair")
        return v


class DensityTestSubmit(BaseModel):
    """Deferred R3 — device-signed bulk-density calibration submission.

    `project_id` is client-supplied (same pattern as `Batch.project_id` — a
    device has no server-side project link to resolve it from). The SERVER
    computes `density_kg_per_l = mass_kg / volume_l` from the submitted
    mass/volume (`services/bulk_density.mass_and_volume_to_density_kg_per_l`)
    — the device's own display-only calculation is never trusted as the
    stored value. `test_uuid` is caller-supplied (idempotent create, like
    Project/Facility/Dispatch)."""

    model_config = ConfigDict(extra="forbid")
    test_uuid: str = Field(..., min_length=1, max_length=36)
    project_id: str = Field(..., min_length=1, max_length=128)
    mass_kg: float = Field(..., gt=0.0, le=1_000_000.0)
    volume_l: float = Field(..., gt=0.0, le=1_000_000.0)
    performed_at: Optional[str] = Field(None, max_length=64)


