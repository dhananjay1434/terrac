"""SQLAlchemy 2.0 models for dMRV batches and media files."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass

class SystemMetadata(Base):
    __tablename__ = "system_metadata"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class PyrolysisTelemetry(Base):
    __tablename__ = "pyrolysis_telemetry"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telemetry_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    batch_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class YieldMetrics(Base):
    __tablename__ = "yield_metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    yield_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    batch_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class EndUseApplication(Base):
    __tablename__ = "end_use_application"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    batch_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_uuid: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), unique=True, nullable=False, index=True)
    operation_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    # Payload fields
    feedstock_species: Mapped[str] = mapped_column(String(255), nullable=False)
    harvest_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    moisture_percent: Mapped[float] = mapped_column(Float, nullable=False)
    photo_path: Mapped[str] = mapped_column(Text, nullable=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    harvest_uptime_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    
    device_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)

    sourcing_uuid: Mapped[str] = mapped_column(String(36), nullable=True)
    moisture_compliant: Mapped[bool] = mapped_column(nullable=True)
    mock_location_enabled: Mapped[bool] = mapped_column(nullable=True, default=False)
    azimuth: Mapped[float] = mapped_column(Float, nullable=True)
    pitch: Mapped[float] = mapped_column(Float, nullable=True)
    roll: Mapped[float] = mapped_column(Float, nullable=True)

    wet_yield_kg: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    min_recorded_temp_c: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    transport_distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Metadata
    status: Mapped[str] = mapped_column(String(32), default="RECEIVED", nullable=False)
    net_credit_t_co2e: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
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
    batch_uuid: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("batches.batch_uuid"), nullable=True)
    operation_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=True)
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
    hmac_key: Mapped[str] = mapped_column(String(64), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

