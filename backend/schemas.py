from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID
import uuid
from lca_engine import CORG_TABLE

class BatchPayload(BaseModel):
    """Strict Pydantic V2 model for batch payload."""

    batch_uuid: UUID
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
    batch_uuid: UUID
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
    batch_uuid: UUID
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


