"""Kon-Tiki Biochar dMRV — FastAPI microservice with PostgreSQL.

Endpoints:
  POST /api/v1/batches  - Receive dMRV payload with idempotency
  POST /api/v1/media    - Upload media with SHA-256 verification
  GET  /api/health      - Health check
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Literal
from uuid import UUID

from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from schemas import (
    BatchPayload,
    BatchResponse,
    MediaUploadResponse,
    RegistrationRequest,
    RegistrationResponse,
    MintTokenRequest,
    LabHCorgRequest,
    LabResultsRequest,
    _BatchScopedPayload,
    KilnRequest,
    OperatorTrainingRequest,
    SupervisorVisitRequest,
    ScaleCalibrationRequest,
    AnnualVerificationRequest
)
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
import piexif

import attestation
import observability
from db import get_session, init_db
from storage import get_storage
from models import (
    AnnualVerification,
    Batch,
    CompositePileSample,
    DeviceKey,
    EndUseApplication,
    EnrollmentToken,
    Kiln,
    MediaFile,
    MoistureReading,
    OperatorTraining,
    PyrolysisTelemetry,
    ScaleCalibration,
    SupervisorVisit,
    SystemMetadata,
    TransportEvent,
    YieldMetrics,
)
from emission_factors import TRANSPORT_EVENTS_ENFORCED, fuel_emissions_kg_co2e
import hmac_keys
from credit_engine import (
    _recompute_slot,
    recompute_batch_credit,
    _recompute_batch_credit_impl,
    verify_lca_signature,
    _recompute_lock,
    _recompute_state,
    _RECOMPUTE_STATE_CAP,
    _recompute_run_count,
)

from services.registry import (  # noqa: F401  (R6 facade)
    _find_by_payload_key,
    _parse_dt,
    upsert_annual_verification,
    upsert_kiln,
    upsert_operator_training,
    upsert_scale_calibration,
    upsert_supervisor_visit,
)
from services.lab import apply_lab_results  # noqa: F401  (R6 facade)
from services.compliance import (  # noqa: F401  (R6 facade)
    _COMPLIANCE_CATALOG,
    compliance_view,
)
from services.evidence import (  # noqa: F401  (R6 facade)
    _assert_batch_ownership,
    _assert_same_uuid,
    _recompute_if_batch_exists,
    _upsert_one_to_one_evidence,
)

from lca_engine import (
    CORG_TABLE,
    calculate_carbon_credit,
    lca_sign_payload_bytes,
    sign_lca_audit,
)
from corroboration import (
    assemble,
    derive_annual_methane_compliance,
    derive_biomass_compliance,
    derive_composite_sample_compliance,
    derive_delivery_compliance,
    derive_ignition_compliance,
    derive_kiln_registration_compliance,
    derive_min_temp,
    derive_moisture_compliance,
    derive_pah_compliance,
    derive_plausibility_reasons,
    derive_pyrolysis_photo_compliance,
    derive_scale_calibration_compliance,
    derive_transport_km,
    derive_wet_yield,
)
from jsonsafe import _as_utc, _safe_json, _safe_json_async, _BIG_JSON_BYTES  # noqa: F401  (R1 facade)
from geo import (  # noqa: F401  (R1 facade)
    GPS_ANCHOR_MISMATCH_KM,
    _evaluate_anchor,
    _gps_mismatch_km,
    _parse_exif_gps,
    haversine_km,
)
# R2: when server.py is reloaded (test_p0_21 does sys.modules.pop("server") +
# reimport), settings must also re-initialize so the startup validation
# (hmac_keys.validate_startup, _require_secret) fires again with the test's
# monkeypatched env. This is a no-op on first import (settings runs normally).
import importlib as _importlib
import settings as _settings_mod
_importlib.reload(_settings_mod)
from settings import (  # noqa: F401  (R2 facade)
    _ADMIN_SECRET,
    _HMAC_SECRET,
    _MIN_SECRET_LEN,
    _MIN_SECRET_UNIQUE,
    _attestation_enforced,
    _canonical_skew_seconds,
    _load_env,
    _require_canonical_v2,
    _require_secret,
    _rl_int,
    env_int,
    log,
)
from security import (  # noqa: F401  (R3 facade)
    _SAFE,
    _b64url_decode,
    _require_admin,
    verify_media_signature,
    verify_signature,
)



import app_factory as _app_factory
_importlib.reload(_app_factory)
from app_factory import app, create_app, lifespan, UPLOAD_DIR  # noqa: F401  (R9 facade)
_ALLOWED_ORIGIN = os.environ.get("DMRV_ALLOWED_ORIGIN", "")

# ==================== Pydantic Models ====================

































# P3.7/H2: per-batch recompute coalescing. recompute reads the FULL committed
# evidence set for a batch and is idempotent, so under a burst of evidence posts
# a single run reflects all of them. State: buid -> {lock, dirty}. `dirty` means
# "committed evidence has landed that a recompute must still observe".











# ---------------------------------------------------------------------------
# Registry upserts (C8/C9). Single definitions reused by the admin X-Admin-Secret
# routes AND the portal admin forms (P2.5). Kiln + annual upsert by their natural
# keys; scale keeps uuid dedup; operator-training + supervisor-visit are made
# idempotent on the real natural key (M5) with a graceful uuid fallback.
# ---------------------------------------------------------------------------


























# ==================== Evidence-endpoint schemas (Phase 11) ====================
# Strict schemas + size bounds for the previously-`dict` side-endpoints. Identity
# fields are required; the rest are optional (accepts the real client and minimal
# test payloads). `extra="forbid"` rejects unknown keys; lists are bounded. The
# canonical field names MUST match the Dart writers and what corroboration.py reads
# (temperature_readings / wet_yield_weight_kg / latitude / longitude) — changing
# them silently breaks credit corroboration.


# Phase 11-R: free-text string fields are length-bounded so a single huge string
# cannot slip past the array bounds. Identifiers/short text -> 128, paths -> 512,
# timestamps -> 64, hex hashes -> 64.






























# ==================== C8: project registry (admin) ====================
# Project-setup data (once / updated on change): kilns, operator training,
# supervisor visits, scale calibrations. Admin-authenticated (project console,
# NOT the per-run field app). The compliance reasons these enable
# (unregistered_kiln / scale_calibration_expired) are DEFERRED to the C10 unified
# gate — C8 lands the registry only, so no batch's issuance changes here.























# ==================== C9: annual verification (admin) ====================
# Annual / per-verification project inputs, keyed by (project_id, year). Admin-
# authenticated. DATA CAPTURE only: the credit-affecting fields (methane rate →
# CH4 penalty; conversion_factor → C1 yield_conversion) are NOT wired into the
# credit here — that needs methodology sign-off and its own gated phase (same
# discipline as C6 transport). Compliance reasons (missing_annual_methane /
# missing_pah) are deferred to the C10 unified gate.












