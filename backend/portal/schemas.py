"""Pydantic request/response models for the portal API."""

from typing import Optional

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
