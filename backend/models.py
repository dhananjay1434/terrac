"""SQLAlchemy 2.0 models for dMRV batches and media files."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SystemMetadata(Base):
    __tablename__ = "system_metadata"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class PyrolysisTelemetry(Base):
    __tablename__ = "pyrolysis_telemetry"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telemetry_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    batch_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class YieldMetrics(Base):
    __tablename__ = "yield_metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    yield_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    batch_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class EndUseApplication(Base):
    __tablename__ = "end_use_application"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    batch_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class MoistureReading(Base):
    """Rainbow compliance C2: one moisture-meter reading per row (many per batch).

    Unlike the other side tables, batch_uuid is NOT unique — the methodology
    requires many readings per run (≥1 per 100 kg, min 10).
    """

    __tablename__ = "moisture_readings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reading_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    batch_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CompositePileSample(Base):
    """Rainbow compliance C4: a site composite pile sub-sample (many per batch).

    Like moisture_readings, batch_uuid is indexed but NOT unique — the
    methodology sets aside sub-samples per run, each tagged with GPS + kiln/batch
    QR + a photo.
    """

    __tablename__ = "composite_pile_samples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sample_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    batch_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class TransportEvent(Base):
    """Rainbow compliance C6: one transport event (many per batch).

    The methodology requires distance, weight, vehicle type and fuel consumed for
    each transport leg, separately for biomass and biochar. `event_uuid` is
    unique; `batch_uuid` is indexed but NOT unique (many legs per batch).
    """

    __tablename__ = "transport_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    batch_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Kiln(Base):
    """Rainbow compliance C8: project kiln registry (once / updated on change).

    Admin-authenticated project-setup data — kiln material, weight, item lifetime.
    A batch's telemetry `kiln_id` (C0) references a row here; the C10 gate will
    require a batch's kiln to be registered (reason `unregistered_kiln`).
    """

    __tablename__ = "kilns"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kiln_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    material: Mapped[str] = mapped_column(String(128), nullable=True)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=True)
    lifetime_years: Mapped[float] = mapped_column(Float, nullable=True)
    kiln_type: Mapped[str] = mapped_column(String(16), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class OperatorTraining(Base):
    """Rainbow compliance C8: kiln-operator training records (many per project)."""

    __tablename__ = "operator_training"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_uuid: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    operator_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SupervisorVisit(Base):
    """Rainbow compliance C8: kiln-supervisor site-visit reports (many per project)."""

    __tablename__ = "supervisor_visits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visit_uuid: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    kiln_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    # SHA-256 of a signed report artifact uploaded via the existing /media channel.
    report_sha256: Mapped[str] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ScaleCalibration(Base):
    """Rainbow compliance C8: scale calibration proof (many per project/scale).

    `valid_until` drives the C10 `scale_calibration_expired` gate — a batch whose
    weighing scale has no in-date calibration is not issuable.
    """

    __tablename__ = "scale_calibrations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    calibration_uuid: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    scale_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    calibrated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    report_sha256: Mapped[str] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AnnualVerification(Base):
    """Rainbow compliance C9: annual / per-verification project inputs.

    Keyed by (project_id, year) — the methodology captures these "annually or when
    feedstock changes": methane emission rate (3 runs), PAH / heavy metals (PAH
    mandatory for closed kilns), biomass leakage assessment, biomass→biochar
    conversion factor, dry bulk density per site, plus the per-verification
    quality-oversight report. Admin-authenticated; upsert on (project_id, year).

    All fields are DATA CAPTURE only in C9. The credit-affecting ones (methane
    rate → CH4 penalty; conversion_factor → C1 yield_conversion) are NOT wired into
    the credit here — that needs methodology sign-off and its own gated phase (same
    discipline as C6 transport). The compliance reasons (missing_annual_methane /
    missing_pah) are deferred to the C10 unified gate.
    """

    __tablename__ = "annual_verifications"
    __table_args__ = (
        UniqueConstraint("project_id", "year", name="uq_annual_verif_project_year"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # Credit-relevant (captured, not yet wired): methane rate + conversion factor.
    methane_rate_g_per_kg: Mapped[float] = mapped_column(Float, nullable=True)
    methane_run_count: Mapped[int] = mapped_column(Integer, nullable=True)
    conversion_factor: Mapped[float] = mapped_column(Float, nullable=True)
    # PAH / heavy-metals composite sample (closed-kiln PAH is mandatory).
    pah_measured: Mapped[bool] = mapped_column(nullable=True)
    heavy_metals_measured: Mapped[bool] = mapped_column(nullable=True)
    # Leakage assessment + dry bulk density per site.
    leakage_assessment_done: Mapped[bool] = mapped_column(nullable=True)
    dry_bulk_density: Mapped[float] = mapped_column(Float, nullable=True)
    # Per-verification quality-oversight report (artifact via signed /media).
    quality_oversight_sha256: Mapped[str] = mapped_column(String(64), nullable=True)
    report_sha256: Mapped[str] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Batch(Base):
    __tablename__ = "batches"

    # Phase 15-D: the permanence ratio invariant lives at the DB layer, not just in
    # the LabHCorgRequest API model — any write path must respect [0.1, 1.5].
    __table_args__ = (
        CheckConstraint(
            "lab_h_corg IS NULL OR (lab_h_corg >= 0.1 AND lab_h_corg <= 1.5)",
            name="ck_batches_lab_h_corg_range",
        ),
        # C7: organic carbon is a fraction in (0, 1]. The DB enforces the invariant
        # regardless of write path (mirrors the lab_h_corg guard).
        CheckConstraint(
            "organic_carbon_pct IS NULL "
            "OR (organic_carbon_pct > 0.0 AND organic_carbon_pct <= 1.0)",
            name="ck_batches_organic_carbon_pct_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_uuid: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), unique=True, nullable=False, index=True
    )
    operation_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    # Payload fields
    feedstock_species: Mapped[str] = mapped_column(String(255), nullable=False)
    harvest_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    moisture_percent: Mapped[float] = mapped_column(Float, nullable=False)
    photo_path: Mapped[str] = mapped_column(Text, nullable=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    harvest_uptime_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    device_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)

    # Rainbow T1.1: batch->project/scale linkage. Resolves the project-scoped
    # gates (C8 scale calibration, C9 annual methane/PAH). Nullable — legacy
    # batches predate the linkage and those gates stay inert for them.
    project_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    scale_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)

    sourcing_uuid: Mapped[str] = mapped_column(String(36), nullable=True)
    moisture_compliant: Mapped[bool] = mapped_column(nullable=True)
    mock_location_enabled: Mapped[bool] = mapped_column(nullable=True, default=False)
    azimuth: Mapped[float] = mapped_column(Float, nullable=True)
    pitch: Mapped[float] = mapped_column(Float, nullable=True)
    roll: Mapped[float] = mapped_column(Float, nullable=True)

    # Phase 7-R: these are corroborated server-side from the telemetry/yield/
    # application streams (see corroboration.py + recompute_batch_credit). They
    # stay 0.0 until corroborated; the `provisional` flag + `provisional_reasons`
    # record whether the credit is issuable.
    wet_yield_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    min_recorded_temp_c: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    transport_distance_km: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    # Lab-measured H:Corg permanence ratio, when available (else credit uses the
    # conservative 0.35 assumption and is PROVISIONAL). Persisted so recompute
    # from a later evidence stream does not lose a previously-ingested lab value.
    lab_h_corg: Mapped[float] = mapped_column(Float, nullable=True)

    # Rainbow compliance C7: per-batch lab results (admin-authenticated channel).
    # organic_carbon_pct is CREDIT-AFFECTING — when present it replaces the species
    # CORG_TABLE constant in the LCA; its absence keeps the batch provisional
    # (assumed_corg). The rest are captured for verification / the 1000-yr pathway.
    organic_carbon_pct: Mapped[float] = mapped_column(Float, nullable=True)
    biochar_moisture_samples_json: Mapped[str] = mapped_column(Text, nullable=True)
    dry_bulk_density: Mapped[float] = mapped_column(Float, nullable=True)
    inertinite_pct: Mapped[float] = mapped_column(Float, nullable=True)
    residual_corg_pct: Mapped[float] = mapped_column(Float, nullable=True)
    ro_measurements_count: Mapped[int] = mapped_column(Integer, nullable=True)

    # Rainbow compliance C1: biomass input amount + measurement method.
    biomass_input_kg: Mapped[float] = mapped_column(Float, nullable=True)
    biomass_measurement_method: Mapped[str] = mapped_column(String(32), nullable=True)

    # Metadata
    status: Mapped[str] = mapped_column(String(32), default="RECEIVED", nullable=False)
    net_credit_t_co2e: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Phase 8: True when the credit was computed on an ASSUMED H:Corg (no lab
    # value). Orthogonal to `status` (which tracks photo-evidence anchoring) —
    # a provisional credit must never be issued as final.
    provisional: Mapped[bool] = mapped_column(nullable=False, default=True)
    # Phase 7-R: JSON list of reasons the batch is provisional / not issuable
    # (e.g. ["wet_yield_uncorroborated", "assumed_h_corg"]). Audit trail.
    provisional_reasons: Mapped[str] = mapped_column(Text, nullable=True)
    lca_methodology_version: Mapped[str] = mapped_column(String(255), nullable=True)
    lca_audit_json: Mapped[str] = mapped_column(Text, nullable=True)
    lca_signature: Mapped[str] = mapped_column(String(64), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_uuid: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("batches.batch_uuid"), nullable=True
    )
    operation_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=True)
    # Phase 9: GPS parsed from the uploaded photo's EXIF, for server-side
    # corroboration against the batch's claimed coordinates. NULL when the
    # upload carries no EXIF GPS.
    exif_lat: Mapped[float] = mapped_column(Float, nullable=True)
    exif_lon: Mapped[float] = mapped_column(Float, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class EnrollmentToken(Base):
    __tablename__ = "enrollment_tokens"
    token: Mapped[str] = mapped_column(String(255), primary_key=True)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class DeviceKey(Base):
    __tablename__ = "device_keys"

    device_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    public_key: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # base64url Ed25519
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
