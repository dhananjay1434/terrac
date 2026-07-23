"""Pydantic request/response models for the portal API."""

from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(..., max_length=255)
    password: str = Field(..., max_length=1024)


class LoginResponse(BaseModel):
    token: str
    expires_at: str
    role: str


class MintTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expires_in_days: int = Field(7, ge=1, le=365)
    # The enrollment URL baked into the QR payload the operator scans.
    base_url: Optional[str] = Field(None, max_length=512)


class MintTokenResponse(BaseModel):
    token: str
    expires_at: str
    qr_payload: str


class ProjectCreate(BaseModel):
    """V8 Part 0.2. `project_id` is caller-supplied (not server-generated) so
    it can match/continue an existing natural key already used by batches —
    or be a fresh id for a brand-new project. Create is idempotent: creating
    with an id that already exists returns 409, never a duplicate row."""

    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    registry_config_id: Optional[str] = Field(None, max_length=128)
    org_id: Optional[str] = Field(None, max_length=128)
    # FM-1: validated at create time against the resolved registry config's
    # corg_table (or the module default when no config is set) — see
    # create_project. Empty list is allowed (a project may be registered
    # before its feedstock is decided).
    allowed_feedstocks: list[str] = Field(default_factory=list)
    client_target: Optional[int] = Field(None, ge=0)


class ProjectOut(BaseModel):
    project_id: str
    name: str
    registry_config_id: Optional[str] = None
    org_id: Optional[str] = None
    allowed_feedstocks: list[str] = Field(default_factory=list)
    client_target: Optional[int] = None
    status: str
    created_at: str


class FacilityCreate(BaseModel):
    """V8 Part 3.1. Facilities are portal-registered infrastructure (like
    projects/parcels), not device-created — `facility_uuid` is caller-supplied
    so the portal (or a pre-generated QR/label) can mint it up front."""

    model_config = ConfigDict(extra="forbid")
    facility_uuid: str = Field(..., min_length=36, max_length=36)
    name: str = Field(..., min_length=1, max_length=255)
    facility_type: str = Field(..., pattern="^(artisanal|industrial)$")
    state: Optional[str] = Field(None, max_length=128)
    district: Optional[str] = Field(None, max_length=128)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    org_id: Optional[str] = Field(None, max_length=128)


class FacilityOut(BaseModel):
    facility_uuid: str
    name: str
    facility_type: str
    state: Optional[str] = None
    district: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: str
    created_at: str


class AppConfigUpdate(BaseModel):
    """V8 Part 0.4. All fields optional — an admin can update just the
    kill-switch, or just min_version, without re-sending the whole document.
    `flags` replaces the entire flags map (not a merge) so removing a flag
    is possible; omit it to leave flags untouched."""

    model_config = ConfigDict(extra="forbid")
    flags: Optional[dict] = None
    min_version: Optional[str] = Field(None, max_length=32)
    kill_switch: Optional[bool] = None
    message: Optional[str] = Field(None, max_length=2000)


class ParcelCreate(BaseModel):
    """V8 Part 1.3 — source parcel registration request body."""

    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    boundary_geojson: Union[Dict[str, Any], str] = Field(...)
    declared_area_acres: Optional[float] = Field(None, gt=0.0, le=100000.0)
    parcel_uuid: Optional[str] = Field(None, min_length=36, max_length=36)
    boundary_method: Optional[str] = Field("portal_drawn", max_length=64)


class ParcelOut(BaseModel):
    """V8 Part 1.3 — source parcel output response schema."""

    parcel_uuid: str
    project_id: str
    name: str
    boundary_geojson: str
    area_m2: float
    declared_area_acres: Optional[float] = None
    bbox_min_lat: float
    bbox_min_lon: float
    bbox_max_lat: float
    bbox_max_lon: float
    boundary_method: str
    boundary_status: str
    created_at: str


class RegistryConfigCreate(BaseModel):
    """V8 Part 4 (G). `params_json` is a JSON object matching lca_engine's
    LcaParams fields (corg_table, safety_deduction_kg_per_t,
    transport_factor_kg_per_t_km, transport_threshold_km,
    ch4_compliant_kg_per_t, ch4_non_compliant_kg_per_t) — any field omitted
    falls back to the CSI-3.2 default for that field, never crashes."""

    model_config = ConfigDict(extra="forbid")
    config_id: str = Field(..., min_length=1, max_length=128)
    registry_name: str = Field(..., min_length=1, max_length=255)
    methodology_version: str = Field(..., min_length=1, max_length=64)
    params: dict = Field(default_factory=dict)
    fpic_template_set_id: Optional[str] = Field(None, max_length=128)


class RegistryConfigOut(BaseModel):
    config_id: str
    registry_name: str
    methodology_version: str
    params: dict
    fpic_template_set_id: Optional[str] = None
    created_at: str


class BulkDensityTestCreate(BaseModel):
    """V8 Part 4 (F). `test_uuid` is caller-supplied (idempotent create, like
    Project/Facility). `valid_until` drives the production_requires_valid_
    density C10 gate — omit it (or set it in the past) to register a test
    that does NOT clear the gate."""

    model_config = ConfigDict(extra="forbid")
    test_uuid: str = Field(..., min_length=1, max_length=36)
    project_id: str = Field(..., min_length=1, max_length=128)
    density_kg_per_l: float = Field(..., gt=0.0, le=1000.0)
    performed_at: Optional[str] = Field(None, max_length=64)
    mass_kg: Optional[float] = Field(None, gt=0.0)
    volume_l: Optional[float] = Field(None, gt=0.0)
    valid_until: Optional[str] = Field(None, max_length=64)


class BulkDensityTestOut(BaseModel):
    test_uuid: str
    project_id: str
    density_kg_per_l: float
    performed_at: Optional[str] = None
    mass_kg: Optional[float] = None
    volume_l: Optional[float] = None
    valid_until: Optional[str] = None
    created_at: str


class MediaVerifyInput(BaseModel):
    """V8 Part 4 (K). status is required; remarks is free text (e.g. a
    rejection reason for targeted recapture)."""

    model_config = ConfigDict(extra="forbid")
    status: str = Field(..., pattern="^(approved|rejected)$")
    remarks: Optional[str] = Field(None, max_length=2000)


class LabResultsInput(BaseModel):
    """P2.4 lab-results body (batch_uuid comes from the path). Mirrors the admin
    LabResultsRequest bounds; all fields optional so a lab reports incrementally.
    """

    model_config = ConfigDict(extra="forbid")
    lab_h_corg: Optional[float] = Field(None, ge=0.1, le=1.5)
    organic_carbon_pct: Optional[float] = Field(None, gt=0.0, le=1.0)
    biochar_moisture_samples: Optional[list[float]] = Field(
        None, min_length=3, max_length=100
    )
    dry_bulk_density: Optional[float] = Field(None, gt=0.0, le=2000.0)
    inertinite_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    residual_corg_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    ro_measurements_count: Optional[int] = Field(None, ge=0)


class FarmerDocumentOut(BaseModel):
    id: int
    doc_type: str
    last4: str
    media_id: str


class FarmerPaymentOut(BaseModel):
    id: int
    rail: str
    account_holder: Optional[str] = None
    masked_account: Optional[str] = None
    ifsc_code: Optional[str] = None
    masked_upi_id: Optional[str] = None
    masked_mfs_id: Optional[str] = None


class FarmerConsentOut(BaseModel):
    id: int
    fpic_template_id: Optional[str] = None
    signed_pdf_media_id: Optional[str] = None
    holding_photo_media_id: Optional[str] = None
    signed_at: Optional[str] = None
    exclusivity_ack: bool


class FarmerOut(BaseModel):
    farmer_uuid: str
    project_id: str
    first_name: str
    last_name: Optional[str] = None
    gender: Optional[str] = None
    guardian_name: Optional[str] = None
    dob: Optional[str] = None
    mobile_number: str
    education: Optional[str] = None
    family_size: Optional[int] = None
    reported_area: Optional[float] = None
    village: Optional[str] = None
    kyc_status: Optional[str] = None
    consent_status: Optional[str] = None
    signature_media_id: Optional[str] = None
    created_at: str
    sync_status: Optional[str] = None

    documents: list[FarmerDocumentOut] = Field(default_factory=list)
    payments: list[FarmerPaymentOut] = Field(default_factory=list)
    consents: list[FarmerConsentOut] = Field(default_factory=list)


class FarmerListResponse(BaseModel):
    items: list[FarmerOut]
    total: int
    page: int
    size: int


class IssuanceRetireInput(BaseModel):
    """PR-1 — optional registry-submission reference recorded at retire."""

    model_config = ConfigDict(extra="forbid")
    registry_submission_ref: Optional[str] = Field(None, max_length=255)


class IssuanceOut(BaseModel):
    issuance_uuid: str
    batch_uuid: str
    serial: Optional[str] = None
    vintage: Optional[int] = None
    t_co2e_frozen: Optional[float] = None
    methodology_version: Optional[str] = None
    status: str
    verified_by_user_id: Optional[int] = None
    issued_at: Optional[str] = None
    registry_submission_ref: Optional[str] = None
    created_at: str


class IssuanceListResponse(BaseModel):
    issuances: list[IssuanceOut]
    next_cursor: Optional[str] = None
