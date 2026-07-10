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
