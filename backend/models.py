"""SQLAlchemy 2.0 models for dMRV batches and media files."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    event,
)
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


class Project(Base):
    """V8 Part 0.2 — the real Project entity. Until now `Batch.project_id`
    (l.333) and `AnnualVerification.project_id` (l.266) were bare strings with
    no backing table, no metadata, no tenancy anchor. Blueprint A (parcel),
    B (farmer), C (facility), D (org/tenancy), and G (registry-config) all
    scope off "project" as a real entity — this unblocks them.

    `project_id` is kept as the PRIMARY KEY (not a synthetic UUID) because
    every existing Batch/AnnualVerification row already stores this natural
    string value — using it as the PK means the backfill migration needs no
    data rewrite; existing rows resolve their project by a plain value match.

    Deliberately NOT a DB-enforced ForeignKey from Batch/AnnualVerification:
    a device may sync a batch whose project hasn't been portal-registered yet
    (offline-first), and an enforced FK would reject that write. The link is
    by value at the application layer — same looseness the project_id column
    already had, now resolvable against real project metadata when present.
    """

    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Reserved for Blueprint G (config-driven methodology/registry) — nullable
    # until that Part exists.
    registry_config_id: Mapped[str] = mapped_column(String(128), nullable=True)
    # Reserved for Blueprint D (multi-tenancy) — nullable until that Part exists.
    org_id: Mapped[str] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SourceParcel(Base):
    """V8 Part 1.2 — source parcel entity.

    Biomass harvest origin boundary. Registered in the portal at project setup.
    Stores GeoJSON text, server-computed geodesic area, declared area, and
    bounding box coordinates for fast O(1) SQL prefiltering during overlap checks.
    """

    __tablename__ = "source_parcels"

    parcel_uuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("projects.project_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    boundary_geojson: Mapped[str] = mapped_column(Text, nullable=False)
    area_m2: Mapped[float] = mapped_column(Float, nullable=False)
    declared_area_acres: Mapped[float] = mapped_column(Float, nullable=True)
    bbox_min_lat: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    bbox_min_lon: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    bbox_max_lat: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    bbox_max_lon: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    boundary_method: Mapped[str] = mapped_column(
        String(64), nullable=False, default="portal_drawn"
    )
    boundary_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="approved"
    )
    created_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("portal_users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class FieldWalkTrack(Base):
    """V8 Part 5 (A phase-2) — a device-recorded GPS boundary walk, submitted
    against a server-signed "field-walk link" (see `server_signing.py` — the
    same Ed25519 key that signs the remote-config document). The link
    authorizes ONE walk of ONE parcel; `link_nonce` is UNIQUE so a captured
    link can't be replayed to submit a second, different track.

    This is corroborating evidence alongside the portal-drawn
    `SourceParcel.boundary_geojson`, never a silent replacement — an admin
    reviews `overlap_ratio_vs_declared` and decides whether to act on a
    mismatch. `points_json` keeps the raw walked (lon, lat, timestamp) log for
    audit; `computed_boundary_geojson`/`computed_area_m2` are the derived
    polygon so a review doesn't need to reconstruct it.
    """

    __tablename__ = "field_walk_tracks"
    __table_args__ = (
        UniqueConstraint("link_nonce", name="uq_field_walk_tracks_link_nonce"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parcel_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_parcels.parcel_uuid"), nullable=False, index=True
    )
    device_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    link_nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    points_json: Mapped[str] = mapped_column(Text, nullable=False)
    computed_boundary_geojson: Mapped[str] = mapped_column(Text, nullable=False)
    computed_area_m2: Mapped[float] = mapped_column(Float, nullable=False)
    overlap_ratio_vs_declared: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
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
    batch_uuid: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), unique=True, nullable=False, index=True
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
    parcel_uuid: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_parcels.parcel_uuid"), nullable=True, index=True
    )

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
    # P3.6: id of the versioned HMAC key that produced lca_signature. Null on
    # rows written before key versioning ⇒ resolves to the legacy key id k0.
    lca_signature_key_id: Mapped[str] = mapped_column(String(16), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # T3.1: NO ForeignKey to batches. Evidence media can be uploaded BEFORE its
    # batch exists (deferred anchoring via _evaluate_anchor) — a real field
    # flow. A DB-level FK forbids exactly that on any FK-enforcing engine
    # (Postgres rejected it; SQLite silently ignored FKs, hiding the bug). The
    # five sibling evidence tables (moisture/composite/transport/telemetry/
    # yield) already carry batch_uuid as a plain indexed column; media now matches.
    batch_uuid: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), nullable=True
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
    # Evidence-step label. `capture_type` arrives as an OPTIONAL client hint
    # (X-Capture-Type header — NOT in the frozen media canonical, so unsigned);
    # `capture_type_verified` flips True only when the server corroborates the
    # label against the Ed25519-signed telemetry smoke_evidence (stage, sha256)
    # pairs. NULL = legacy row or non-burn media not yet classified.
    capture_type: Mapped[str] = mapped_column(String(64), nullable=True)
    capture_type_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    # V8 Part 4 (K) — per-media reviewer verdict. NULL = not yet reviewed.
    # A verifier can reject ONE photo with a reason (targeted recapture)
    # instead of the all-or-nothing batch-level compliance gate.
    verification_status: Mapped[str] = mapped_column(String(16), nullable=True)
    verification_remarks: Mapped[str] = mapped_column(Text, nullable=True)
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


# ---------------------------------------------------------------------------
# P2.1 — Lab & Verifier portal auth.
# ---------------------------------------------------------------------------
class PortalUser(Base):
    """A human portal operator (admin / lab / verifier / org_admin). Distinct
    from the device fleet — devices sign with Ed25519; humans log in with a
    password (argon2 hash) and carry an opaque session token."""

    __tablename__ = "portal_users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'lab', 'verifier', 'org_admin')",
            name="ck_portal_users_role",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    # V8 Part 5 (D) — multi-tenancy scoping. NULL (every user before this Part,
    # and any global admin) sees all orgs' data, unchanged from pre-tenancy
    # behavior. Set only for a user who should be confined to one org's
    # Projects/Facilities/Batches (see tenancy.py).
    org_id: Mapped[str] = mapped_column(String(128), nullable=True)
    disabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class PortalSession(Base):
    """An opaque 24h session. Only the SHA-256 of the bearer token is stored,
    so a DB leak can't be replayed as a live session."""

    __tablename__ = "portal_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Facility(Base):
    """V8 Part 3.1 — registered facility (artisanal or industrial site) that can
    receive a dispatch. Portal-registered infrastructure (like Project/
    SourceParcel), not device-created — mirrors that admin-registration pattern.

    `org_id` and `registry_config_id` are reserved for later Blueprints (D
    multi-tenancy, G config-driven registry) — nullable until those Parts exist.
    """

    __tablename__ = "facilities"

    facility_uuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(128), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    facility_type: Mapped[str] = mapped_column(String(16), nullable=False)  # artisanal|industrial
    state: Mapped[str] = mapped_column(String(128), nullable=True)
    district: Mapped[str] = mapped_column(String(128), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    registry_config_id: Mapped[str] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Dispatch(Base):
    """V8 Part 3.1/3.2 — a custody-transfer shipment of biomass or biochar.

    Lifecycle (services/dispatch_state.py owns the rules): draft -> in_transit
    (Submit — LOCKS weight_source_kg) -> received (Mark Received — sets
    weight_facility_kg exactly once + runs dual-weigh reconciliation).

    Device-created (mirrors Batch): a field operator's app writes this via the
    signed evidence pattern, not the portal. `dest_facility_uuid` is a soft
    value-link (NOT a DB-enforced FK) for the same offline-first reason
    Project/SourceParcel use one — a device may dispatch to a facility that
    hasn't synced to the portal's view yet.
    """

    __tablename__ = "dispatches"

    dispatch_uuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # biomass|biochar
    source_ref: Mapped[str] = mapped_column(String(128), nullable=True)  # parcel_uuid or farmer_uuid
    dest_facility_uuid: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")

    # Weight-lock pair: weight_source_kg set once in 'draft', immutable after.
    weight_source_kg: Mapped[float] = mapped_column(Float, nullable=True)
    weight_source_method: Mapped[str] = mapped_column(String(64), nullable=True)
    # weight_facility_kg set exactly once, at in_transit -> received.
    weight_facility_kg: Mapped[float] = mapped_column(Float, nullable=True)

    # Dual-weigh reconciliation outcome (computed server-side at receiving).
    weight_delta_kg: Mapped[float] = mapped_column(Float, nullable=True)
    weight_delta_pct: Mapped[float] = mapped_column(Float, nullable=True)
    weight_flagged: Mapped[bool] = mapped_column(nullable=True)

    driver_name: Mapped[str] = mapped_column(String(255), nullable=True)
    driver_phone: Mapped[str] = mapped_column(String(32), nullable=True)
    truck_number: Mapped[str] = mapped_column(String(32), nullable=True)

    device_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    sync_status: Mapped[str] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    transitioned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class DispatchSite(Base):
    """V8 Part 3.1 — child rows aggregating the source site(s) contributing to
    one dispatch (a truck load may combine multiple parcels)."""

    __tablename__ = "dispatch_sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dispatch_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parcel_uuid: Mapped[str] = mapped_column(String(36), nullable=True)
    moisture_pct: Mapped[float] = mapped_column(Float, nullable=True)
    truck_percentage_filled: Mapped[float] = mapped_column(Float, nullable=True)


class RegistryConfig(Base):
    """V8 Part 4 (G) — config-driven methodology/registry. `lca_engine.py`
    hardcoded CSI-3.2 as Python constants; this table lets a second
    program/registry (a different biochar standard, ARR, regen) supply its
    own methodology parameters without touching engine code.

    `params_json` holds the LcaParams fields (see lca_engine.params_from_json)
    — corg_table, safety_deduction_kg_per_t, transport_factor_kg_per_t_km,
    transport_threshold_km, ch4_compliant_kg_per_t, ch4_non_compliant_kg_per_t.
    A row missing any key falls back to the CSI-3.2 default for that key, so
    a partial config can never crash the engine, only under-specify.

    Bound to `Project.registry_config_id` (added in Part 0.2, reserved for
    this) — NOT to Facility: batches carry `project_id` today, not a facility
    reference, so project is the natural, already-wired scoping level.
    """

    __tablename__ = "registry_configs"

    config_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    registry_name: Mapped[str] = mapped_column(String(255), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(64), nullable=False)
    params_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    fpic_template_set_id: Mapped[str] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class BulkDensityTest(Base):
    """V8 Part 4 (F) — bulk-density calibration for the volume→mass yield path.

    Artisanal biochar can't go on a truck scale mid-process; when no direct
    crane-scale weight exists for a batch, wet_yield_kg can instead be derived
    as kiln_gross_capacity (telemetry, litres) × density_kg_per_l from an
    IN-DATE test here (credit_engine._resolve wires this; see
    corroboration.derive_wet_yield_from_density). `valid_until` drives the
    `production_requires_valid_density` C10 gate, mirroring
    ScaleCalibration.valid_until / `scale_calibration_expired` exactly.

    Bound to `project_id` (like RegistryConfig, Part 4 G) rather than a
    facility: Batch carries `project_id`, not a facility reference, so
    project is the real, already-wired scoping level.

    Media (mass photo / calibration video) is deliberately NOT captured here
    yet — same deferred-media policy as farmer documents and dispatch
    photos: claiming a media_id nothing uploads would be a false attestation.
    """

    __tablename__ = "bulk_density_tests"

    test_uuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    density_kg_per_l: Mapped[float] = mapped_column(Float, nullable=False)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    mass_kg: Mapped[float] = mapped_column(Float, nullable=True)
    volume_l: Mapped[float] = mapped_column(Float, nullable=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AppConfig(Base):
    """V8 Part 0.4 — remote control plane: server-signed feature flags,
    kill-switch, and minimum supported app version. A private-APK + CI-off
    fleet has zero remote control otherwise — a bad build or a discovered
    fraud vector can't be flag-gated or force-updated post-deploy.

    Single logical row (config_id='default') — no multi-tenant config yet
    (that's Blueprint D, later), so admin writes are a plain upsert on this
    one key. An EMPTY table (no row at all) is the safe "never configured"
    state: `GET /api/v1/config` serves inert defaults (no kill-switch, no
    min-version floor) rather than erroring, so this feature stays fully
    dormant until an admin explicitly writes a config.
    """

    __tablename__ = "app_config"

    config_id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default="default"
    )
    flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    min_version: Mapped[str] = mapped_column(String(32), nullable=True)
    kill_switch: Mapped[bool] = mapped_column(nullable=False, default=False)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AuditEvent(Base):
    """P2.6 — append-only audit trail for every portal mutation (token mint, lab
    results, registry writes, credit issuance). INSERT-only: there is no update
    or delete route anywhere, and the ORM event below hard-blocks any UPDATE as
    a belt-and-braces guard."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    batch_uuid: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    actor_user_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


@event.listens_for(AuditEvent, "before_update", propagate=True)
def _audit_events_are_immutable(_mapper, _connection, _target):
    raise RuntimeError("audit_events are append-only; UPDATE is forbidden")


class Farmer(Base):
    __tablename__ = "farmers"
    __table_args__ = (
        UniqueConstraint("project_id", "mobile_number", name="uq_farmer_project_mobile"),
    )
    farmer_uuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=True)
    gender: Mapped[str] = mapped_column(String(32), nullable=True)
    guardian_name: Mapped[str] = mapped_column(String(255), nullable=True)
    dob: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    mobile_number: Mapped[str] = mapped_column(String(32), nullable=False)
    education: Mapped[str] = mapped_column(String(128), nullable=True)
    family_size: Mapped[int] = mapped_column(Integer, nullable=True)
    reported_area: Mapped[float] = mapped_column(Float, nullable=True)
    village: Mapped[str] = mapped_column(String(255), nullable=True)
    kyc_status: Mapped[str] = mapped_column(String(32), nullable=True)
    consent_status: Mapped[str] = mapped_column(String(32), nullable=True)
    signature_media_id: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    sync_status: Mapped[str] = mapped_column(String(32), nullable=True)


class FarmerDocument(Base):
    __tablename__ = "farmer_documents"
    __table_args__ = (
        CheckConstraint(
            "doc_type IN ('aadhaar', 'pan', 'passport', 'nid')",
            name="ck_farmer_doc_type",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    farmer_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)
    last4: Mapped[str] = mapped_column(String(4), nullable=False)
    media_id: Mapped[str] = mapped_column(String(64), nullable=False)


class FarmerPayment(Base):
    __tablename__ = "farmer_payments"
    __table_args__ = (
        CheckConstraint(
            "rail IN ('bank', 'upi', 'mfs')",
            name="ck_farmer_payment_rail",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    farmer_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rail: Mapped[str] = mapped_column(String(32), nullable=False)
    account_holder: Mapped[str] = mapped_column(String(255), nullable=True)
    masked_account: Mapped[str] = mapped_column(String(255), nullable=True)
    ifsc_code: Mapped[str] = mapped_column(String(32), nullable=True)
    masked_upi_id: Mapped[str] = mapped_column(String(255), nullable=True)
    masked_mfs_id: Mapped[str] = mapped_column(String(255), nullable=True)


class FarmerConsent(Base):
    __tablename__ = "farmer_consents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    farmer_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    fpic_template_id: Mapped[str] = mapped_column(String(128), nullable=True)
    signed_pdf_media_id: Mapped[str] = mapped_column(String(64), nullable=True)
    holding_photo_media_id: Mapped[str] = mapped_column(String(64), nullable=True)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    exclusivity_ack: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
