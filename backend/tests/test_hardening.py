"""
Hardening verification suite — one (or two) test(s) per issue in
`/app/detailed.md`.

Run from <REPO_ROOT>:
    python -m pytest /app/tests/backend/test_hardening.py -q

Each test name encodes the issue id (e.g. test_p0_12_*). If a test fails:
    1. Re-read the matching section of /app/detailed.md.
    2. Re-apply the fix exactly as written there.
    3. Re-run only that test:  pytest -q -k p0_12
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import importlib
import io
import os
import re
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio


# =============================================================================
# Test helpers
# =============================================================================


def _valid_payload(**overrides) -> dict:
    p = {
        "batch_uuid": str(uuid4()),
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": "2026-01-01T00:00:00+00:00",
        "moisture_percent": 12.0,
        "photo_path": "/tmp/x.jpg",
        "sha256_hash": "a" * 64,
        "latitude": 28.6139,
        "longitude": 77.2090,
        "harvest_uptime_seconds": 100,
        "wet_yield_kg": 1000.0,
        "min_recorded_temp_c": 0.0,
        "transport_distance_km": 0.0,
    }
    p.update(overrides)
    return p


# =============================================================================
# P0-12 — extra fields rejected, species validated
# =============================================================================


@pytest.mark.asyncio
async def test_p0_12_extra_field_rejected(client):
    """Extra fields must be rejected — model_config = extra='forbid'."""
    body = _valid_payload(some_unknown_field="oops")
    r = await client.post(
        "/api/v1/batches",
        json=body,
        headers={"X-Idempotency-Key": str(uuid4())},
    )
    assert r.status_code == 422, (
        f"Expected 422 for extra field, got {r.status_code}. "
        "Did you set model_config extra='forbid' on BatchPayload?"
    )


@pytest.mark.asyncio
async def test_p0_12_invalid_species_rejected(client):
    body = _valid_payload(feedstock_species="Unicorn_horn")
    r = await client.post(
        "/api/v1/batches",
        json=body,
        headers={"X-Idempotency-Key": str(uuid4())},
    )
    assert r.status_code == 422


# =============================================================================
# P0-13 — duplicate idempotency-key with different payload returns 409
# =============================================================================


@pytest.mark.asyncio
async def test_p0_13_batch_dup_op_id_same_payload_returns_200(client):
    op_id = str(uuid4())
    body = _valid_payload()
    r1 = await client.post(
        "/api/v1/batches", json=body, headers={"X-Idempotency-Key": op_id}
    )
    assert r1.status_code == 201, r1.text
    r2 = await client.post(
        "/api/v1/batches", json=body, headers={"X-Idempotency-Key": op_id}
    )
    assert r2.status_code == 200, (
        f"Same payload + same op-id should be idempotent 200, got {r2.status_code}"
    )
    assert r2.json()["duplicate"] is True


@pytest.mark.asyncio
async def test_p0_13_batch_dup_op_id_different_sha_returns_409(client):
    op_id = str(uuid4())
    body1 = _valid_payload(sha256_hash="a" * 64)
    body2 = _valid_payload(batch_uuid=body1["batch_uuid"], sha256_hash="b" * 64)
    r1 = await client.post(
        "/api/v1/batches", json=body1, headers={"X-Idempotency-Key": op_id}
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/v1/batches", json=body2, headers={"X-Idempotency-Key": op_id}
    )
    assert r2.status_code == 409, (
        f"Different sha256_hash for same op-id MUST be 409, got {r2.status_code}. "
        "See /app/detailed.md#P0-13."
    )


@pytest.mark.asyncio
async def test_p0_13_media_dup_op_id_different_hash_returns_409(client):
    op_id = str(uuid4())
    content_a = b"photo-A-bytes"
    content_b = b"photo-B-bytes"
    sha_a = hashlib.sha256(content_a).hexdigest()
    sha_b = hashlib.sha256(content_b).hexdigest()

    r1 = await client.post(
        "/api/v1/media",
        files={"file": ("a.jpg", io.BytesIO(content_a), "image/jpeg")},
        headers={
            "X-Idempotency-Key": op_id,
            "X-Declared-SHA256": sha_a,
            "X-Device-Id": "device-123",
            "X-Batch-UUID": str(uuid4()),
        },
    )
    assert r1.status_code == 200, r1.text
    r2 = await client.post(
        "/api/v1/media",
        files={"file": ("b.jpg", io.BytesIO(content_b), "image/jpeg")},
        headers={
            "X-Idempotency-Key": op_id,
            "X-Declared-SHA256": sha_b,
            "X-Device-Id": "device-123",
            "X-Batch-UUID": str(uuid4()),
        },
    )
    assert r2.status_code == 409


# =============================================================================
# P0-14 — UNIQUE(batch_uuid) on child tables
# =============================================================================


@pytest.mark.asyncio
async def test_p0_14_pyrolysis_unique_batch_uuid(test_engine):
    """The new server-side PyrolysisTelemetry model must declare UNIQUE(batch_uuid)."""
    try:
        import models
    except Exception as e:
        pytest.fail(f"could not import backend.models: {e}")

    assert hasattr(models, "PyrolysisTelemetry"), (
        "models.PyrolysisTelemetry not defined — add it per /app/detailed.md#P0-14"
    )
    col = models.PyrolysisTelemetry.__table__.c.batch_uuid
    assert col.unique is True, "batch_uuid must be unique=True on PyrolysisTelemetry"


@pytest.mark.asyncio
async def test_p0_14_yield_unique_batch_uuid(test_engine):
    import models

    assert hasattr(models, "YieldMetrics")
    assert models.YieldMetrics.__table__.c.batch_uuid.unique is True


@pytest.mark.asyncio
async def test_p0_14_end_use_unique_batch_uuid(test_engine):
    import models

    assert hasattr(models, "EndUseApplication")
    assert models.EndUseApplication.__table__.c.batch_uuid.unique is True


# =============================================================================
# P0-15 — stub endpoints require batch_uuid in payload
# =============================================================================


@pytest.mark.parametrize(
    "path",
    ["/api/v1/telemetry", "/api/v1/yield", "/api/v1/metadata", "/api/v1/application"],
)
@pytest.mark.asyncio
async def test_p0_15_stub_missing_batch_uuid_422(client, path):
    r = await client.post(path, json={"unrelated": 1})
    assert r.status_code == 422, (
        f"{path} accepted payload without batch_uuid (got {r.status_code}). "
        "See /app/detailed.md#P0-15."
    )


# =============================================================================
# P0-16 — reject too-short temperature logs (low single-sample fake reading)
# =============================================================================


@pytest.mark.asyncio
async def test_p0_16_single_high_temp_rejected(client):
    """Phase 7-R: a client-ASSERTED min_recorded_temp_c is ignored — temperature is
    corroborated from the /telemetry log, not trusted from the payload. A suspicious
    asserted value therefore cannot earn a compliant-temperature credit: the batch is
    accepted but PROVISIONAL with min_temp uncorroborated."""
    body = _valid_payload(min_recorded_temp_c=50.0)
    r = await client.post(
        "/api/v1/batches", json=body, headers={"X-Idempotency-Key": str(uuid4())}
    )
    assert r.status_code == 201, r.text
    assert r.json()["provisional"] is True


@pytest.mark.asyncio
async def test_p0_16_zero_temp_allowed_for_unmeasured(client):
    """min_recorded_temp_c == 0.0 means "no thermocouple data" — must still be accepted."""
    body = _valid_payload(min_recorded_temp_c=0.0)
    r = await client.post(
        "/api/v1/batches", json=body, headers={"X-Idempotency-Key": str(uuid4())}
    )
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_p0_16_real_burn_temp_accepted(client):
    body = _valid_payload(min_recorded_temp_c=350.0, moisture_percent=8.0)
    r = await client.post(
        "/api/v1/batches", json=body, headers={"X-Idempotency-Key": str(uuid4())}
    )
    assert r.status_code == 201


# =============================================================================
# P0-17 — DATABASE_URL must not have a hardcoded default
# =============================================================================


def test_p0_17_no_hardcoded_db_default():
    db_py = (
        Path(__file__).resolve().parents[2]
        / "uploaded"
        / "New folder"
        / "backend"
        / "db.py"
    ).read_text(encoding="utf-8")
    assert "postgres:postgres@localhost" not in db_py, (
        "Hardcoded postgres:postgres default still present in db.py. See /app/detailed.md#P0-17."
    )
    assert (
        'os.environ.get("DATABASE_URL",' not in db_py
        and "os.environ.get('DATABASE_URL'," not in db_py
    ), (
        "db.py still uses os.environ.get(...) with a default value. "
        "Use RuntimeError on missing DATABASE_URL."
    )


def test_p0_17_missing_db_url_raises(monkeypatch):
    """Re-importing db with DATABASE_URL unset must raise."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import sys

    sys.modules.pop("db", None)
    with pytest.raises((RuntimeError, KeyError)):
        importlib.import_module("db")


# =============================================================================
# P0-18 — Alembic in place
# =============================================================================


def test_p0_18_alembic_dir_exists():
    backend = Path(__file__).resolve().parents[1]
    assert (backend / "alembic.ini").exists(), (
        "backend/alembic.ini missing. See /app/detailed.md#P0-18."
    )
    assert (backend / "alembic" / "env.py").exists()
    versions = backend / "alembic" / "versions"
    assert versions.exists() and any(versions.glob("*.py")), (
        "No Alembic revisions generated yet."
    )


def test_p0_18_init_db_respects_skip_env():
    """When DMRV_SKIP_MIGRATIONS=1, init_db() must early-return."""
    import sys

    sys.modules.pop("db", None)
    db = importlib.import_module("db")
    src = Path(db.__file__).read_text(encoding="utf-8")
    assert "DMRV_SKIP_MIGRATIONS" in src, (
        "init_db() must honour DMRV_SKIP_MIGRATIONS=1 escape hatch for the test suite."
    )


# =============================================================================
# P1-18 — X-Mock-Location header is NOT an access control (Phase 9)
# =============================================================================


@pytest.mark.asyncio
async def test_p1_18_mock_location_header_has_no_effect(client):
    # Phase 9: the honor-system X-Mock-Location header was dropped as a control.
    # A well-formed media upload must NOT be rejected because of it; mock-location
    # is corroborated server-side (EXIF GPS / teleport), not via a client header.
    content = b"x"
    sha = hashlib.sha256(content).hexdigest()
    r = await client.post(
        "/api/v1/media",
        files={"file": ("a.jpg", io.BytesIO(content), "image/jpeg")},
        headers={
            "X-Idempotency-Key": str(uuid4()),
            "X-Declared-SHA256": sha,
            "X-Mock-Location": "true",
            "X-Device-Id": "device-abc",
            "X-Batch-UUID": str(uuid4()),
        },
    )
    assert r.status_code == 200, (
        f"X-Mock-Location:true must have no effect (got {r.status_code}). "
        "Phase 9 dropped it as an access control."
    )


# =============================================================================
# P1-19 — HMAC covers METHOD|PATH|IDEMPOTENCY|body-sha|device
# =============================================================================


def _sign(
    method: str,
    path: str,
    op_id: str,
    body: bytes,
    device: str,
    secret: bytes = b"test-secret",
) -> str:
    # Phase 5: requests are signed with the device's Ed25519 private key.
    # `secret` is retained for call-site compatibility but ignored; signing
    # uses the fixed test private key whose public half every test device
    # enrolls (crypto_utils.TEST_PUBLIC_KEY_B64).
    from tests.remediation.crypto_utils import sign_canonical

    canonical = "\n".join(
        [method, path, op_id, hashlib.sha256(body).hexdigest(), device]
    ).encode()
    return sign_canonical(canonical)


@pytest.mark.asyncio
async def test_p1_19_hmac_canonical_string_accepted(client):
    import json as _json

    body = _valid_payload()
    raw = _json.dumps(body).encode()
    op_id = str(uuid4())
    sig = _sign("POST", "/api/v1/batches", op_id, raw, "dev-1")
    r = await client.post(
        "/api/v1/batches",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": op_id,
            "X-Signature": sig,
            "X-Device-Id": "dev-1",
        },
    )
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_p1_19_hmac_replay_to_different_endpoint_rejected(client):
    """A signature minted for /batches must NOT verify against /telemetry."""
    import json as _json

    body = _valid_payload()
    raw = _json.dumps(body).encode()
    op_id = str(uuid4())
    # Sign as /api/v1/batches but POST to /api/v1/telemetry
    sig = _sign("POST", "/api/v1/batches", op_id, raw, "dev-1")
    r = await client.post(
        "/api/v1/telemetry",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": op_id,
            "X-Signature": sig,
            "X-Device-Id": "dev-1",
        },
    )
    assert r.status_code in (403,), (
        f"Cross-endpoint HMAC replay was not rejected (got {r.status_code}). "
        "See /app/detailed.md#P1-19."
    )


# =============================================================================
# P1-20 — path traversal + device-id sanitisation
# =============================================================================


@pytest.mark.asyncio
async def test_p1_20_invalid_device_id_400(client):
    content = b"x"
    sha = hashlib.sha256(content).hexdigest()
    r = await client.post(
        "/api/v1/media",
        files={"file": ("a.jpg", io.BytesIO(content), "image/jpeg")},
        headers={
            "X-Idempotency-Key": str(uuid4()),
            "X-Declared-SHA256": sha,
            "X-Device-Id": "../../etc",
            "X-Batch-UUID": str(uuid4()),
        },
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_p1_20_path_traversal_filename_blocked(client):
    """Even with a hostile filename, the file must land under UPLOAD_DIR/device/."""
    content = b"hello"
    sha = hashlib.sha256(content).hexdigest()
    op_id = "op-" + uuid4().hex
    r = await client.post(
        "/api/v1/media",
        files={"file": ("../../etc/passwd_pwn.jpg", io.BytesIO(content), "image/jpeg")},
        headers={
            "X-Idempotency-Key": op_id,
            "X-Declared-SHA256": sha,
            "X-Device-Id": "device-1",
            "X-Batch-UUID": str(uuid4()),
        },
    )
    assert r.status_code == 200, r.text
    file_path = r.json()["file_path"]
    assert ".." not in file_path
    assert "passwd_pwn" not in file_path
    # Path must end with op_id-based filename, NOT the user-supplied one
    assert op_id in file_path


def test_p1_20_uploads_in_gitignore():
    root = Path(__file__).resolve().parents[2] / "uploaded" / "New folder"
    gi = root / ".gitignore"
    assert gi.exists(), ".gitignore missing at repo root"
    text = gi.read_text(encoding="utf-8")
    assert "backend/uploads" in text or "uploads/" in text, (
        "backend/uploads/ not in .gitignore. See /app/detailed.md#P1-20."
    )


# =============================================================================
# P1-21 — schemas.py either deleted, or uses @model_validator
# =============================================================================


def test_p1_21_schemas_py_deleted_or_uses_model_validator():
    schemas_py = (
        Path(__file__).resolve().parents[2]
        / "uploaded"
        / "New folder"
        / "backend"
        / "schemas.py"
    )
    if not schemas_py.exists():
        return  # deleted per P0-12 — accepted
    text = schemas_py.read_text(encoding="utf-8")
    # If kept, it MUST use @model_validator on BatchPayload
    assert "model_validator" in text, (
        "schemas.py is still present but does not use @model_validator. "
        "Either delete the file (P0-12) or migrate to @model_validator (P1-21)."
    )
    assert (
        re.search(r"@field_validator\(\s*[\"']biomass_sourcing[\"']", text) is None
    ), "Stale order-sensitive @field_validator('biomass_sourcing') still in schemas.py."


# =============================================================================
# Existing-suite regression sentinels
# =============================================================================


@pytest.mark.asyncio
async def test_regression_health_endpoint(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_regression_valid_batch_still_works(client):
    body = _valid_payload()
    r = await client.post(
        "/api/v1/batches", json=body, headers={"X-Idempotency-Key": str(uuid4())}
    )
    assert r.status_code == 201
    data = r.json()
    assert data["duplicate"] is False
    assert data["net_credit_t_co2e"] is not None
