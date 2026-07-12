"""Kon-Tiki Biochar dMRV — compatibility facade.

This module re-exports every public and internal name that tests and other modules
historically imported as ``from server import X``. The real implementations live in
the domain modules extracted during the P4.8 server.py refactor (R1–R9).

New code should import from the domain module directly:
    from schemas import BatchPayload
    from security import verify_signature
    from credit_engine import recompute_batch_credit
    from app_factory import app

This facade exists so that existing ``from server import ...`` statements — in
30+ test files and in any external tooling — keep working without a mass rewrite.
"""

from __future__ import annotations
import os

import importlib as _importlib

import settings as _settings_mod
_importlib.reload(_settings_mod)

import app_factory as _app_factory
_importlib.reload(_app_factory)

# ---- R9: app + assembly ----
from app_factory import app, create_app, lifespan, UPLOAD_DIR  # noqa: F401

_ALLOWED_ORIGIN = os.environ.get("DMRV_ALLOWED_ORIGIN", "")

# ---- R1: leaf utils ----
from jsonsafe import _as_utc, _safe_json, _safe_json_async, _BIG_JSON_BYTES  # noqa: F401
from geo import (  # noqa: F401
    GPS_ANCHOR_MISMATCH_KM,
    _evaluate_anchor,
    _exif_to_decimal,
    _gps_mismatch_km,
    _parse_exif_gps,
    haversine_km,
)

# ---- R2: settings ----
from settings import (  # noqa: F401
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

# ---- R3: security ----
from security import (  # noqa: F401
    _SAFE,
    _b64url_decode,
    _require_admin,
    verify_media_signature,
    verify_signature,
)

# ---- R4: schemas ----
from schemas import (  # noqa: F401
    AnnualVerificationRequest,
    BatchPayload,
    BatchResponse,
    KilnRequest,
    LabHCorgRequest,
    LabResultsRequest,
    MediaUploadResponse,
    MintTokenRequest,
    OperatorTrainingRequest,
    RegistrationRequest,
    RegistrationResponse,
    ScaleCalibrationRequest,
    SupervisorVisitRequest,
    _BatchScopedPayload,
)

# ---- R5: credit engine ----
from credit_engine import (  # noqa: F401
    _RECOMPUTE_STATE_CAP,
    _device_registered_at,
    _recompute_batch_credit_impl,
    _recompute_run_count,
    _recompute_slot,
    _recompute_state,
    recompute_batch_credit,
    verify_lca_signature,
)

# ---- R6: services ----
from services.registry import (  # noqa: F401
    _find_by_payload_key,
    _parse_dt,
    upsert_annual_verification,
    upsert_kiln,
    upsert_operator_training,
    upsert_scale_calibration,
    upsert_supervisor_visit,
)
from services.lab import apply_lab_results  # noqa: F401
from services.compliance import (  # noqa: F401
    _COMPLIANCE_CATALOG,
    compliance_view,
)
from services.evidence import (  # noqa: F401
    _assert_batch_ownership,
    _assert_same_uuid,
    _recompute_if_batch_exists,
    _upsert_one_to_one_evidence,
)

# ---- R8: middleware ----
from middleware import (  # noqa: F401
    _MAX_JSON_BODY_BYTES,
    _MAX_MEDIA_BODY_BYTES,
    _RL_CAP_ENV,
    _RL_DEFAULT_CAPS,
    _RL_MAX_COUNTERS,
    _limit_body_size,
    _rate_limit,
    _rl_bucket,
    _rl_counters,
    _rl_enabled,
    _rl_now,
    _rl_prune,
    _rl_window_seconds,
)

# ---- Re-export db/models for legacy imports ----
from db import get_session, init_db  # noqa: F401
