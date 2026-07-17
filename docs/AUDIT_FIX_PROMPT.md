# AUDIT FIX PROMPT — dMRV backend (9 findings, fix ONE AT A TIME)

> Copy everything below the line into the agent. It assumes the repo is checked
> out at `c:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`, Python 3.11
> + backend requirements installed, and `git` works. The agent must do the tasks
> IN ORDER, ONE AT A TIME, and STOP when a CHECK fails.

---

You are fixing 9 audited findings in a FastAPI biochar dMRV backend. They come
from a line-by-line code audit at commit `7d6c611` (source of truth = the code,
not any .md). Follow every rule exactly.

## GLOBAL RULES — apply to every task

1. **One task at a time.** Finish task N (code + test + full suite green +
   commit) before you even READ task N+1.
2. **Never claim a test passed without running it and seeing the output.**
   Paste the tail of pytest output for every CHECK.
3. Backend commands run from:
   `cd "c:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv/backend"`
4. Full-suite gate after every task:
   ```bash
   python -m pytest -q
   ```
   Baseline: **428 passed, 2 skipped** (~4–5 min). After each task: at least
   that many passed, **0 failed**. If a test you did not write fails, STOP and
   report — do not modify unrelated tests to force green.
5. Commit after EVERY task with the exact message given. One task = one commit.
   ```bash
   cd "c:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv"
   git add <only files named in the task>
   git commit -m "<message from the task>"
   ```
6. **No refactoring, renaming, reformatting, or extra "improvements".** Match
   surrounding style. Touch only the files each task names.
7. Line numbers are as of `7d6c611` and may drift slightly — if an exact match
   fails, read the file around that line and locate the verbatim code shown.
8. Test-suite conventions you MUST reuse (verified in `backend/tests/conftest.py`):
   - `client` fixture = SignedAsyncClient (auto-signs device requests) over
     in-memory SQLite; `session_factory` = async_sessionmaker. There is **no**
     bare `session` fixture.
   - Admin header in tests: `{"X-Admin-Secret": "test-admin-secret"}`.
   - `pytestmark = pytest.mark.asyncio` at module top; POST JSON bodies are sent
     as `content=json.dumps(payload).encode("utf-8")` (NOT `json=`).
   - Portal tests build their own app/db fixture — copy the fixture pattern
     from `tests/test_portal_export.py` verbatim if you need a portal client.

---

# TASK 1 — HIGH (deploy blocker): rate limiter blind behind Render's proxy

**Files:** `backend/Dockerfile`, `backend/middleware.py`, new test
`backend/tests/test_rate_limit_proxy.py`

**Problem.** `backend/middleware.py` keys the brute-force rate-limit buckets by
`request.client.host` (lines ~96–102):

```python
    if bucket in ("register", "admin"):
        # brute-force surfaces: key by client IP so rotating device ids can't evade.
        key = request.client.host if request.client else "ip-unknown"
```

Uvicorn is started WITHOUT `--proxy-headers` (`backend/Dockerfile` last line):

```dockerfile
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8001}"]
```

Behind Render's TLS-terminating proxy, every request's `client.host` is the
proxy's internal IP. Consequences: (a) ALL users worldwide share ONE bucket —
`register` cap is 5/min TOTAL and `admin` (which also covers every
`/api/v1/portal/*` request, see `_rl_bucket` lines ~76–87) is 30/min TOTAL, so
a handful of portal users 429 each other; (b) per-IP brute-force protection is
nullified (every attacker shares the victim pool's identity).

**Fix (two parts, both required).**

Part A — `backend/Dockerfile`: make uvicorn trust the platform proxy's
`X-Forwarded-For` so `request.client.host` becomes the real client IP. Replace
the CMD line:

```dockerfile
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8001}"]
```

with:

```dockerfile
# --proxy-headers: Render terminates TLS and injects X-Forwarded-For; without
# this, request.client.host is the proxy IP and the per-IP rate limiter
# collapses to one global bucket. --forwarded-allow-ips='*' is safe here
# because the container is only reachable through Render's proxy.
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8001} --proxy-headers --forwarded-allow-ips='*'"]
```

Part B — `backend/middleware.py`: defense-in-depth for any deployment that
misses Part A (e.g. someone runs the app without the flag). In `_rate_limit`,
replace the two-line ip-key block shown above with:

```python
    if bucket in ("register", "admin"):
        # brute-force surfaces: key by client IP so rotating device ids can't evade.
        # Behind a TLS-terminating proxy the socket peer is the proxy, so prefer
        # the first X-Forwarded-For hop when present (uvicorn --proxy-headers
        # already rewrites request.client; this is belt-and-braces for runs
        # without that flag). First hop = client as seen by OUR proxy.
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            key = fwd.split(",")[0].strip() or "ip-unknown"
        else:
            key = request.client.host if request.client else "ip-unknown"
```

Do NOT change the `else:` branch below it (device-keyed buckets) in this task.

**New test — create `backend/tests/test_rate_limit_proxy.py`:**

```python
"""Audit fix 1: per-IP rate-limit buckets must honor X-Forwarded-For so two
clients behind one proxy do not share (or jointly exhaust) a bucket."""

import json
import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def _register(client, xff, n):
    # /api/v1/register is the "register" bucket (cap 5/min, IP-keyed).
    return await client.post(
        "/api/v1/register",
        content=json.dumps(
            {"device_id": f"rl-{n}-{uuid.uuid4().hex[:6]}", "public_key": "A" * 43}
        ).encode("utf-8"),
        headers={"X-Forwarded-For": xff, "X-Enrollment-Token": "nope"},
    )


async def test_xff_clients_get_separate_buckets(client, monkeypatch):
    monkeypatch.setenv("DMRV_RATELIMIT_ENABLED", "1")
    monkeypatch.setenv("DMRV_RATELIMIT_REGISTER", "3")
    # Exhaust the bucket for IP 10.0.0.1 (3 requests hit the cap; 4th is 429).
    for i in range(3):
        r = await _register(client, "10.0.0.1", i)
        assert r.status_code != 429, r.text
    r = await _register(client, "10.0.0.1", 99)
    assert r.status_code == 429
    # A DIFFERENT client behind the same proxy is NOT rate-limited.
    r2 = await _register(client, "10.0.0.2", 100)
    assert r2.status_code != 429, r2.text


async def test_first_xff_hop_wins(client, monkeypatch):
    monkeypatch.setenv("DMRV_RATELIMIT_ENABLED", "1")
    monkeypatch.setenv("DMRV_RATELIMIT_REGISTER", "1")
    r = await _register(client, "10.9.9.9, 172.16.0.1", 0)
    assert r.status_code != 429
    # Same first hop, different second hop -> SAME bucket -> limited.
    r = await _register(client, "10.9.9.9, 172.16.0.2", 1)
    assert r.status_code == 429
```

Note: the 401s these requests get (bad enrollment token) are fine — the rate
limiter runs BEFORE auth; the test only asserts 429 vs non-429.

**CHECKS (in order):**
```bash
python -m pytest tests/test_rate_limit_proxy.py tests/test_rate_limit.py -q   # all pass
python -m pytest -q                                                            # >= 428 passed, 0 failed
```

**Commit message:**
`fix(security): honor X-Forwarded-For in per-IP rate limits + uvicorn proxy-headers`

# TASK 2 — MEDIUM: create_batch idempotency 500s on photo-less batches

**Files:** `backend/routers/batches.py`, new test
`backend/tests/test_batch_retry_no_photo.py`

**Problem.** `backend/routers/batches.py` lines ~49–52, the duplicate fast-path:

```python
    if existing:
        if existing.sha256_hash.lower() != payload.sha256_hash.lower() or str(
            existing.batch_uuid
        ) != str(payload.batch_uuid):
```

`sha256_hash` is Optional on BOTH sides (`schemas.py` BatchPayload ~line 16:
`sha256_hash: Optional[str]`; `models.py` Batch ~line 322: `nullable=True`).
A batch legitimately created WITHOUT a photo (sha256_hash omitted) that is
retried with the same `X-Idempotency-Key` hits `None.lower()` →
`AttributeError` → HTTP 500 instead of the intended 200 duplicate. Offline
field clients retry aggressively, so this fires in production. Note the
IntegrityError race path lower in the same file (~lines 163–164) already
handles None correctly:

```python
        existing_sha = existing.sha256_hash.lower() if existing.sha256_hash else None
        payload_sha = payload.sha256_hash.lower() if payload.sha256_hash else None
```

Use the SAME None-safe pattern in the fast path.

**Fix.** Replace the fast-path comparison with:

```python
    if existing:
        # None-safe: photo-less batches (sha256_hash NULL) must retry as clean
        # duplicates too — mirrors the None handling in the race path below.
        existing_sha = existing.sha256_hash.lower() if existing.sha256_hash else None
        payload_sha = payload.sha256_hash.lower() if payload.sha256_hash else None
        if existing_sha != payload_sha or str(
            existing.batch_uuid
        ) != str(payload.batch_uuid):
```

Nothing else in the function changes.

**New test — create `backend/tests/test_batch_retry_no_photo.py`:**

```python
"""Audit fix 2: retrying a photo-less batch (sha256_hash=None) with the same
idempotency key must return 200 duplicate, not 500 (None.lower() crash)."""

import json
import uuid
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.asyncio


def _payload(bu):
    # No sha256_hash / photo_path — a legitimate photo-less batch.
    return {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
    }


async def test_photoless_batch_retry_is_200_duplicate(client, registered_device):
    bu = str(uuid.uuid4())
    body = json.dumps(_payload(bu)).encode("utf-8")
    op = "op-nophoto-" + bu[:8]

    r1 = await client.post(
        "/api/v1/batches", content=body, headers={"X-Idempotency-Key": op}
    )
    assert r1.status_code == 201, r1.text

    # Byte-identical retry with the same idempotency key.
    r2 = await client.post(
        "/api/v1/batches", content=body, headers={"X-Idempotency-Key": op}
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["duplicate"] is True


async def test_photoless_op_reuse_with_photo_is_409(client, registered_device):
    bu = str(uuid.uuid4())
    op = "op-conflict-" + bu[:8]
    r1 = await client.post(
        "/api/v1/batches",
        content=json.dumps(_payload(bu)).encode("utf-8"),
        headers={"X-Idempotency-Key": op},
    )
    assert r1.status_code == 201, r1.text

    # Same op-id, same uuid, but NOW claims a photo hash -> different payload -> 409.
    p2 = _payload(bu)
    p2["sha256_hash"] = "a" * 64
    r2 = await client.post(
        "/api/v1/batches",
        content=json.dumps(p2).encode("utf-8"),
        headers={"X-Idempotency-Key": op},
    )
    assert r2.status_code == 409, r2.text
```

**CHECKS (in order):**
```bash
python -m pytest tests/test_batch_retry_no_photo.py tests/test_api.py tests/test_client_contract.py -q
python -m pytest -q      # >= 428 passed, 0 failed
```

**Commit message:**
`fix(batches): None-safe sha256 compare on idempotent retry of photo-less batch`

# TASK 3 — MEDIUM: media upload can strand a poisoned row (bytes deleted, row says stored)

**Files:** `backend/routers/media.py`, new test
`backend/tests/test_media_poisoned_row.py`

**Problem.** In `backend/routers/media.py` `upload_media` (~lines 139–181) the
order of operations is:

1. `storage.write(...)` — bytes stored
2. `session.add(media)`; `await session.commit()` — **media row COMMITTED** (~line 153)
3. `media.batch_uuid = batch_uuid`
4. batch ownership check — `raise HTTPException(403, "not_your_batch")` (~line 172)
5. `except Exception:` → `await session.rollback()` + `storage.delete(stored_key)`

The rollback in step 5 CANNOT undo the commit in step 2. After a 403 (or any
failure after step 2): the `media_files` row survives with that
`operation_id`, while the BYTES are deleted. A later legitimate retry with the
same op-id hits the duplicate fast-path (~line 69: `if existing:` → returns
`stored=True`) — **the API forever claims evidence is stored that no longer
exists**.

**Fix — check ownership BEFORE any persistence.** The handler already loads
nothing batch-related before writing; move the batch load + ownership check to
BEFORE `storage.write(...)`. Concretely, in `upload_media`, immediately AFTER
the `batch_uuid = str(uuid.UUID(x_batch_uuid))` validation block (~lines
124–127) and BEFORE `storage = get_storage()`, insert:

```python
    # Audit fix 3: resolve the batch and enforce ownership BEFORE any bytes or
    # rows are persisted. Previously the ownership 403 fired AFTER the media row
    # was committed; the except-path rollback could not undo that commit, so a
    # rejected upload stranded a row whose bytes were deleted — and the
    # duplicate fast-path then reported stored=True for evidence that no longer
    # existed. Loading the batch first makes rejection side-effect-free.
    stmt = select(Batch).where(Batch.batch_uuid == batch_uuid)
    batch = (await session.execute(stmt)).scalar_one_or_none()
    if batch is not None and batch.device_id is not None and batch.device_id != device_id:
        raise HTTPException(status_code=403, detail="not_your_batch")
```

Then, INSIDE the existing `try:` block, DELETE the now-redundant re-load and
ownership check (~lines 166–172):

```python
        stmt = select(Batch).where(Batch.batch_uuid == batch_uuid)
        batch_result = await session.execute(stmt)
        batch = batch_result.scalar_one_or_none()
        if batch:
            if batch.device_id is not None and batch.device_id != device_id:
                raise HTTPException(status_code=403, detail="not_your_batch")
            _evaluate_anchor(batch, calculated_hash, exif_lat, exif_lon)
            session.add(batch)
```

becomes:

```python
        if batch:
            _evaluate_anchor(batch, calculated_hash, exif_lat, exif_lon)
            session.add(batch)
```

(the `batch` variable now comes from the pre-persistence load). Keep the
`try/except` + `storage.delete` wrapper — it still protects against DB errors
on the second commit.

**New test — create `backend/tests/test_media_poisoned_row.py`:**

```python
"""Audit fix 3: a media upload rejected for ownership (403) must leave NO
media_files row behind — otherwise a later legitimate retry hits the duplicate
fast-path and reports stored=True for bytes that were deleted."""

import io
import json
import uuid
from datetime import datetime, timezone
import hashlib

import pytest
from sqlalchemy import select

from models import Batch, MediaFile

pytestmark = pytest.mark.asyncio

_JPEG = b"\xff\xd8\xff\xe0" + b"x" * 64  # minimal fake JPEG bytes


async def _seed_foreign_batch(session_factory, bu):
    """A batch owned by a DIFFERENT device than the test client's."""
    async with session_factory() as s:
        s.add(
            Batch(
                batch_uuid=bu,
                operation_id="op-foreign-" + bu[:8],
                feedstock_species="Lantana_camara",
                harvest_timestamp=datetime.now(timezone.utc),
                moisture_percent=12.0,
                harvest_uptime_seconds=0,
                device_id="someone-elses-device",
                status="RECEIVED",
            )
        )
        await s.commit()


async def test_403_upload_leaves_no_row(client, registered_device, session_factory):
    bu = str(uuid.uuid4())
    await _seed_foreign_batch(session_factory, bu)
    sha = hashlib.sha256(_JPEG).hexdigest()
    op = "op-media-poison-" + bu[:8]

    r = await client.post(
        "/api/v1/media",
        files={"file": ("p.jpg", io.BytesIO(_JPEG), "image/jpeg")},
        headers={
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": bu,
        },
    )
    assert r.status_code == 403, r.text

    # THE core assertion: no stranded media_files row under that op-id.
    async with session_factory() as s:
        row = (
            await s.execute(select(MediaFile).where(MediaFile.operation_id == op))
        ).scalar_one_or_none()
    assert row is None, "403 upload must not leave a media row behind"

    # And a retry does NOT lie 'stored=True' via the duplicate fast-path — it
    # is judged on its own merits (still 403, still foreign batch).
    r2 = await client.post(
        "/api/v1/media",
        files={"file": ("p.jpg", io.BytesIO(_JPEG), "image/jpeg")},
        headers={
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": bu,
        },
    )
    assert r2.status_code == 403, r2.text
```

IMPORTANT test-harness note: the `client` fixture auto-signs media uploads via
the frozen media canonical, and `registered_device` enrolls the signing device
— include BOTH fixtures exactly as shown. If the fixture signature differs,
copy the header/signing usage from `backend/tests/test_media_auth.py` instead
of inventing your own.

**CHECKS (in order):**
```bash
python -m pytest tests/test_media_poisoned_row.py tests/test_media_auth.py tests/remediation/test_media_path_leak.py tests/test_batch_ownership.py -q
python -m pytest -q      # >= 428 passed, 0 failed
```

**Commit message:**
`fix(media): enforce batch ownership before persisting upload (no poisoned rows)`

# TASK 4 — LOW: ops-export 400 body leaks the raw provisional_reasons string

**Files:** `backend/routers/exports.py`, edit test
`backend/tests/test_export_endpoints.py`

**Problem.** In `backend/routers/exports.py`, `_load_exportable_batch` builds
the 400 detail with the UNPARSED text column:

```python
        raise HTTPException(
            status_code=400,
            detail={
                "error": "batch_is_provisional",
                "reasons": batch.provisional_reasons or [],
```

`provisional_reasons` is a JSON-encoded TEXT column, so clients receive
`"reasons": "[\"assumed_h_corg\"]"` (a string) instead of a list. The portal
route (`backend/portal/routes.py` `export_batch`) already parses it correctly
— copy that pattern.

**Fix.** In `_load_exportable_batch`, replace the provisional block with:

```python
    if batch.provisional:
        # Parse the JSON TEXT column so clients get a list, not a raw string
        # (mirrors the portal export route).
        reasons = batch.provisional_reasons
        try:
            parsed = json.loads(reasons) if reasons else []
        except (ValueError, TypeError):
            parsed = []
        raise HTTPException(
            status_code=400,
            detail={
                "error": "batch_is_provisional",
                "reasons": parsed,
                "message": "Batch cannot be exported until all compliance gaps are resolved.",
            },
        )
```

Add `import json` to the imports at the top of `exports.py` (keep import order:
stdlib first).

**Test change — in `backend/tests/test_export_endpoints.py`**, extend the
existing `test_csi_export_provisional_400` to assert the parsed shape. Replace
its body with:

```python
async def test_csi_export_provisional_400(client, session_factory):
    bu = await _seed(session_factory, provisional=True, reasons=["assumed_h_corg"])
    r = await client.get(f"/api/v1/batches/{bu}/export/csi", headers=ADMIN)
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["error"] == "batch_is_provisional"
    assert detail["reasons"] == ["assumed_h_corg"]      # a LIST, not a raw string
```

(The `_seed` helper in that file already accepts `provisional=`/`reasons=`.)

**CHECKS (in order):**
```bash
python -m pytest tests/test_export_endpoints.py tests/test_portal_export.py -q
python -m pytest -q      # >= 428 passed, 0 failed
```

**Commit message:**
`fix(export): parse provisional_reasons JSON in ops-export 400 body`

---

# TASK 5 — LOW: lca_signature does not cover the full audit JSON

**Files:** `backend/credit_engine.py`, new test
`backend/tests/test_lca_audit_extras_signed.py`

**Problem.** In `_recompute_batch_credit_impl`
(`backend/credit_engine.py` ~lines 456–487), the signature is computed over the
`LCAAudit` dataclass, but `transport_events` and `integrity_signals` are
appended to `lca_audit_json` AFTER that dataclass snapshot:

```python
    audit = {k: v for k, v in lca.__dict__.items()}
    audit["transport_events"] = { ... }
    audit["integrity_signals"] = { ... }
    batch.lca_audit_json = json.dumps(audit)
```

`sign_lca_audit(lca, ...)` (lca_engine.py) signs `lca.__dict__` only — so a
direct DB tamper of the `transport_events`/`integrity_signals` sections of
`lca_audit_json` is undetectable by `verify_lca_signature`.

**Fix — bind the extras into the signed payload WITHOUT changing the wire
format for existing rows.** Changing `_lca_sign_payload` would invalidate
every already-issued signature — DO NOT do that. Instead, add a SECOND
integrity field: a plain SHA-256 of the exact persisted JSON, stored inside
the audit itself is impossible (self-reference), so store it on the module
boundary as an hmac over the FULL json using the same active key, persisted in
a new audit key. Concretely, in `_recompute_batch_credit_impl`, replace:

```python
    batch.lca_audit_json = json.dumps(audit)
```

with:

```python
    # Audit fix 5: the HMAC lca_signature covers only the LCAAudit dataclass;
    # transport_events/integrity_signals are appended after that snapshot, so a
    # DB tamper of those sections was undetectable. Bind the FULL audit JSON
    # with its own HMAC under the active key (recorded key id makes it
    # rotation-safe). Existing rows lack the field and verify as before.
    _audit_body = json.dumps(audit, sort_keys=True)
    _fk_id, _fk_secret = hmac_keys.active_key()
    audit["full_audit_hmac"] = {
        "key_id": _fk_id,
        "hmac_sha256": hmac.new(
            _fk_secret.encode(), _audit_body.encode(), hashlib.sha256
        ).hexdigest(),
    }
    batch.lca_audit_json = json.dumps(audit)
```

Add the needed imports at the top of `credit_engine.py` (it already imports
`hmac_keys`; add `import hmac` and `import hashlib` if not present).

Verification helper — append to `credit_engine.py` after
`verify_lca_signature`:

```python
def verify_full_audit_hmac(lca_audit_json: str) -> str:
    """Audit fix 5: verify the whole-audit HMAC. Returns 'unsigned' (rows
    predating the field), 'unverifiable' (key rotated out), 'valid' or
    'invalid'. Never raises."""
    try:
        audit = json.loads(lca_audit_json or "null")
    except (ValueError, TypeError):
        return "invalid"
    if not isinstance(audit, dict) or "full_audit_hmac" not in audit:
        return "unsigned"
    seal = audit.pop("full_audit_hmac")
    body = json.dumps(audit, sort_keys=True)
    secret = hmac_keys.key_for((seal or {}).get("key_id"))
    if secret is None:
        return "unverifiable"
    expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    import hmac as _hmac_mod
    return "valid" if _hmac_mod.compare_digest(expected, (seal or {}).get("hmac_sha256", "")) else "invalid"
```

(If `import hmac` is already top-level, drop the local `_hmac_mod` line and use
`hmac.compare_digest` directly — prefer that.)

**New test — create `backend/tests/test_lca_audit_extras_signed.py`:**

```python
"""Audit fix 5: tampering the post-signature audit sections
(transport_events / integrity_signals) must be detectable."""

import json
import uuid
from datetime import datetime, timezone

import pytest

from credit_engine import verify_full_audit_hmac

pytestmark = pytest.mark.asyncio


async def _make_batch(client, bu):
    return await client.post(
        "/api/v1/batches",
        content=json.dumps(
            {
                "batch_uuid": bu,
                "feedstock_species": "Lantana_camara",
                "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
                "moisture_percent": 12.0,
                "harvest_uptime_seconds": 100,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "op-seal-" + bu[:8]},
    )


async def test_full_audit_hmac_valid_and_tamper_detected(
    client, registered_device, session_factory
):
    from sqlalchemy import select
    from models import Batch

    bu = str(uuid.uuid4())
    r = await _make_batch(client, bu)
    assert r.status_code == 201, r.text

    async with session_factory() as s:
        b = (await s.execute(select(Batch).where(Batch.batch_uuid == bu))).scalar_one()
        assert verify_full_audit_hmac(b.lca_audit_json) == "valid"

        # Tamper an extras section that the dataclass signature does NOT cover.
        audit = json.loads(b.lca_audit_json)
        audit["integrity_signals"]["mock_location_enabled"] = True
        tampered = json.dumps(audit)

    assert verify_full_audit_hmac(tampered) == "invalid"


def test_rows_without_seal_are_unsigned():
    legacy = json.dumps({"methodology_version": "CSI-3.2"})
    assert verify_full_audit_hmac(legacy) == "unsigned"
```

**CHECKS (in order):**
```bash
python -m pytest tests/test_lca_audit_extras_signed.py tests/test_lca_engine.py tests/test_hmac_keys.py tests/remediation/test_lca_defensibility.py -q
python -m pytest -q      # >= 428 passed, 0 failed
```

**Commit message:**
`fix(credit): HMAC-seal the full lca_audit_json (extras were unsigned)`

---

# TASK 6 — LOW: enrollment tokens stored raw in the DB

**Files:** `backend/routers/devices.py`, `backend/portal/routes.py` (token mint
route), new test `backend/tests/test_enrollment_token_hashing.py`.
NO alembic migration — the SHA-256 hex digest fits the existing String(255)
column and legacy raw rows keep working via the dual lookup below.

**Problem.** `models.py` `EnrollmentToken` — the PRIMARY KEY IS the raw token
(`token: Mapped[str] = mapped_column(String(255), primary_key=True)`). A DB
read (backup leak, SQLi, misconfigured replica) exposes every UNUSED
enrollment token → attacker can enroll a rogue device. Portal sessions already
store only SHA-256 (`portal/auth.py _hash_token`) — tokens must match that
discipline.

**Fix — store SHA-256 of the token, compare on hash.** No schema change needed
(the hex digest fits String(255)); old raw-token rows keep working via a
dual-lookup during the transition.

Step 6a — add a helper in `backend/routers/devices.py` (top of file, after
imports):

```python
def _hash_enroll_token(raw: str) -> str:
    # Audit fix 6: enrollment tokens are stored only as SHA-256 (same
    # discipline as portal sessions) so a DB leak cannot mint devices.
    import hashlib
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
```

Step 6b — in `register_device`, replace the single-token lookup:

```python
    token_stmt = select(EnrollmentToken).where(
        EnrollmentToken.token == x_enrollment_token
    )
    token_res = await session.execute(token_stmt)
    db_token = token_res.scalar_one_or_none()
```

with a hash-first, legacy-raw-fallback lookup:

```python
    # Hash-first lookup; fall back to the raw value so tokens minted before
    # the hashing change keep working until they expire.
    token_res = await session.execute(
        select(EnrollmentToken).where(
            EnrollmentToken.token == _hash_enroll_token(x_enrollment_token)
        )
    )
    db_token = token_res.scalar_one_or_none()
    if db_token is None:
        token_res = await session.execute(
            select(EnrollmentToken).where(EnrollmentToken.token == x_enrollment_token)
        )
        db_token = token_res.scalar_one_or_none()
```

Step 6c — in `mint_enrollment_token` (same file), store the hash:

```python
    new_token = EnrollmentToken(token=payload.token, expires_at=expires)
```

becomes:

```python
    new_token = EnrollmentToken(
        token=_hash_enroll_token(payload.token), expires_at=expires
    )
```

The RESPONSE still returns the raw `payload.token` (shown once) — do not
change the response body.

Step 6d — the PORTAL also mints tokens. Search `backend/portal/routes.py` for
`EnrollmentToken(` (the `/tokens` mint route, ~line 139–160 region). Apply the
same change there: hash before store, return raw once. Import the helper:
`from routers.devices import _hash_enroll_token`.

Step 6e — check the test seam: `backend/tests/conftest.py` `registered_device`
seeds an EnrollmentToken directly. Open it; if it inserts a raw token row that
`/api/v1/register` must accept, the legacy-raw fallback in 6b keeps it green —
LEAVE conftest untouched (it also proves backward compat).

**New test — create `backend/tests/test_enrollment_token_hashing.py`:**

```python
"""Audit fix 6: enrollment tokens are stored hashed; raw legacy rows still work."""

import hashlib
import json
import uuid

import pytest
from sqlalchemy import select

from models import EnrollmentToken

pytestmark = pytest.mark.asyncio

ADMIN = {"X-Admin-Secret": "test-admin-secret"}


async def test_minted_token_stored_hashed_and_usable(client, session_factory):
    raw = "tok-" + uuid.uuid4().hex
    r = await client.post(
        "/api/v1/admin/mint-token",
        content=json.dumps({"token": raw, "expires_in_days": 1}).encode("utf-8"),
        headers=ADMIN,
    )
    assert r.status_code == 201, r.text
    assert r.json()["token"] == raw          # raw returned once to the operator

    # DB stores ONLY the hash.
    h = hashlib.sha256(raw.encode()).hexdigest()
    async with session_factory() as s:
        assert (
            await s.execute(select(EnrollmentToken).where(EnrollmentToken.token == h))
        ).scalar_one_or_none() is not None
        assert (
            await s.execute(select(EnrollmentToken).where(EnrollmentToken.token == raw))
        ).scalar_one_or_none() is None

    # And the raw token still enrolls a device (server hashes on lookup).
    r2 = await client.post(
        "/api/v1/register",
        content=json.dumps(
            {"device_id": "dev-" + uuid.uuid4().hex[:8], "public_key": "A" * 43}
        ).encode("utf-8"),
        headers={"X-Enrollment-Token": raw},
    )
    assert r2.status_code == 201, r2.text
```

Note: if `public_key: "A" * 43` fails the base64url/Ed25519 decode inside
registration, copy a working public_key literal from
`tests/test_enrollment.py` instead — do NOT weaken the endpoint.

**CHECKS (in order):**
```bash
python -m pytest tests/test_enrollment_token_hashing.py tests/test_enrollment.py tests/remediation/test_enrollment_auth.py tests/test_no_dev_token_seed.py -q
python -m pytest -q      # >= 428 passed, 0 failed
```

**Commit message:**
`fix(security): store enrollment tokens as SHA-256 (raw legacy fallback kept)`

# TASK 7 — LOW: default rate-limit bucket keyed by spoofable X-Device-Id

**Files:** `backend/middleware.py`, extend test
`backend/tests/test_rate_limit_proxy.py`

**Problem.** In `_rate_limit`, the non-brute-force buckets key by a
client-controlled header:

```python
    else:
        key = request.headers.get("X-Device-Id") or (
            request.client.host if request.client else "unknown"
        )
```

Rotating `X-Device-Id` values yields a fresh bucket per request → the 120/min
default and 20/min media caps are evadable by anyone (the header is not
authenticated at middleware time).

**Fix — compose the key from IP AND device id** so a single IP rotating device
ids still exhausts ONE ip-scoped budget, while two legit devices behind one
NAT keep separate buckets:

```python
    else:
        # Key by (client-ip, device-id): the device id alone is spoofable at
        # middleware time (auth happens later), so rotating ids must not mint
        # fresh buckets. Prefer the first X-Forwarded-For hop (Task 1).
        fwd = request.headers.get("x-forwarded-for")
        ip = (
            fwd.split(",")[0].strip()
            if fwd
            else (request.client.host if request.client else "unknown")
        )
        key = f"{ip}|{request.headers.get('X-Device-Id') or '-'}"
```

**Extend `backend/tests/test_rate_limit_proxy.py`** — append:

```python
async def test_rotating_device_ids_share_ip_budget(client, monkeypatch):
    """Audit fix 7: X-Device-Id rotation must not evade the default bucket."""
    import json as _json
    from datetime import datetime, timezone
    import uuid as _uuid

    monkeypatch.setenv("DMRV_RATELIMIT_ENABLED", "1")
    monkeypatch.setenv("DMRV_RATELIMIT_DEFAULT", "3")

    async def _post(devid):
        # Any /api/v1/* JSON endpoint in the 'default' bucket works; use batches.
        return await client.post(
            "/api/v1/batches",
            content=_json.dumps(
                {
                    "batch_uuid": str(_uuid.uuid4()),
                    "feedstock_species": "Lantana_camara",
                    "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
                    "moisture_percent": 12.0,
                    "harvest_uptime_seconds": 1,
                }
            ).encode("utf-8"),
            headers={
                "X-Idempotency-Key": "op-" + _uuid.uuid4().hex[:10],
                "X-Forwarded-For": "10.7.7.7",
                "X-Device-Id": devid,       # rotated every request
            },
        )

    statuses = []
    for i in range(5):
        r = await _post(f"rotator-{i}")
        statuses.append(r.status_code)
    assert 429 in statuses, f"rotating device ids evaded the cap: {statuses}"
```

CAUTION: the auto-signing `client` fixture may overwrite `X-Device-Id` — read
`backend/tests/conftest.py` first. If the fixture forces its own device header,
send the requests through a plain `httpx.AsyncClient(transport=ASGITransport
(app=server.app))` instead (copy the wiring from `tests/test_portal_export.py`'s
fixture, minus the portal users) so YOUR headers reach the middleware
untouched. The 401/403 the unsigned requests earn is irrelevant — only the 429
matters and the limiter runs before auth.

**CHECKS (in order):**
```bash
python -m pytest tests/test_rate_limit_proxy.py tests/test_rate_limit.py -q
python -m pytest -q      # >= 428 passed, 0 failed
```

**Commit message:**
`fix(security): key default rate-limit bucket by (ip, device-id) not spoofable header`

---

# TASK 8 — LOW: exports don't re-verify lca_signature before emitting

**Files:** `backend/services/export.py`, extend tests
`backend/tests/test_export_endpoints.py`

**Problem.** `export_batch_common` (backend/services/export.py) checks only
`batch.provisional` before projecting the batch into a registry report. It
never re-verifies `lca_signature` — so a DB row whose credit fields were
tampered after signing exports cleanly. `credit_engine.verify_lca_signature`
already exists but needs the recomputed LCAAudit; the CHEAP invariant we can
enforce at export time without recomputing is: a non-provisional batch MUST
carry a signature + key id (recompute nulls both on provisional rows —
credit_engine.py ~lines 479–487).

**Fix.** In `export_batch_common`, immediately after the existing provisional
guard, add:

```python
    # Audit fix 8: a non-provisional batch always carries an issuance signature
    # (recompute nulls it on provisional rows). Its absence at export time means
    # the row was tampered or corrupted — refuse to emit a registry report.
    if not batch.lca_signature:
        raise ValueError("unsigned_batch")
```

The routers already convert `ValueError` → HTTP 400, both in
`routers/exports.py` and `portal/routes.py` `export_batch` — verify that by
reading both call sites, but you should not need to change them.

**Extend `backend/tests/test_export_endpoints.py`** — append:

```python
async def test_export_refuses_unsigned_nonprovisional_batch(client, session_factory):
    """Audit fix 8: non-provisional + NULL lca_signature = tampered row -> 400."""
    bu = await _seed(session_factory)
    from sqlalchemy import update
    from models import Batch

    async with session_factory() as s:
        await s.execute(
            update(Batch).where(Batch.batch_uuid == bu).values(lca_signature=None)
        )
        await s.commit()

    r = await client.get(f"/api/v1/batches/{bu}/export/csi", headers=ADMIN)
    assert r.status_code == 400
    assert "unsigned_batch" in r.text
```

NOTE: the existing `_seed` helper in that file sets `lca_signature=None`
already? READ it. As of `7d6c611` it does NOT set `lca_signature` at all
(defaults to NULL) — so the EXISTING tests `test_csi_export_ok` /
`test_rainbow_export_ok` will start failing once this guard lands. FIX THE
SEED, not the guard: add `lca_signature="sig-test", lca_signature_key_id="k0",`
to the `Batch(...)` constructor inside `_seed`. Also check
`backend/tests/test_portal_export.py::_mk_batch` — it already sets
`lca_signature="sig-abc"` for the non-provisional case (verified), so it
stays untouched.

**CHECKS (in order):**
```bash
python -m pytest tests/test_export_endpoints.py tests/test_portal_export.py -q
python -m pytest -q      # >= 428 passed, 0 failed
```

**Commit message:**
`fix(export): refuse to export a non-provisional batch missing its lca_signature`

---

# TASK 9 — LOW (documentation-only): EXIF-strip bypasses GPS quarantine

**Files:** `backend/geo.py` (comment only), `FINDINGS_BACKLOG.md` (append)

**Problem (accepted risk, document it).** `_evaluate_anchor`
(backend/geo.py ~lines 78–93): a photo carrying NO EXIF GPS can never trigger
`_gps_mismatch_km` (it returns False when any coordinate is None), so the
batch upgrades `UNVERIFIED → RECEIVED`. The quarantine therefore only catches
attackers who INCLUDE mismatching GPS, not ones who strip EXIF. The code
already brands EXIF as weak (`exif_trust: client_authored_weak` in
credit_engine.py) and the strong control is attestation (T2.1) — so the fix is
a POLICY decision (should EXIF-less photos anchor at a lower trust status?)
that belongs to the methodology owner, not this task.

**Do exactly two things:**

9a — extend the comment on `_evaluate_anchor` in `backend/geo.py`. After the
existing docstring line about quarantine, add:

```python
    NOTE (audit): a photo with NO EXIF GPS bypasses the mismatch check entirely
    (None coordinates short-circuit _gps_mismatch_km) and still upgrades the
    batch. Deliberate for now — EXIF is client-authored/weak and attestation is
    the strong control — but flagged for methodology-owner review: an EXIF-less
    anchor could set a distinct status (e.g. RECEIVED_NO_GPS) instead.
```

9b — append to `FINDINGS_BACKLOG.md` (create it at repo root if absent):

```markdown
## AUDIT-9: EXIF-strip bypasses GPS quarantine (accepted, needs policy)
- Where: backend/geo.py `_evaluate_anchor` / `_gps_mismatch_km`
- A photo with no EXIF GPS can never mismatch -> batch anchors to RECEIVED.
- Catches only attackers who INCLUDE wrong GPS; stripping EXIF evades review.
- Options: (a) status RECEIVED_NO_GPS + portal badge, (b) require capture-time
  GPS envelope (RequestMetadata pattern) once mobile ships it, (c) accept until
  Play Integrity attestation is enforced (DMRV_ATTESTATION_ENFORCED=1).
- Decision owner: methodology owner. No code gate changed by the audit.
```

**No new test** (no behavior change). CHECK:
```bash
python -m pytest tests/test_corroboration.py -q   # untouched behavior still green
python -m pytest -q                                # >= 428 passed, 0 failed
```

**Commit message:**
`docs(audit): record EXIF-strip anchor bypass as accepted risk pending policy`

---

# FINAL WRAP-UP (after ALL 9 tasks are committed)

1. Run the full suite ONE more time and paste the tail:
   ```bash
   python -m pytest -q
   ```
   Expected: baseline 428 + the ~10 new tests from tasks 1–8, 0 failed.
2. Show the commit list:
   ```bash
   git log --oneline -12
   ```
   Expected: 9 new commits in task order on top of `7d6c611`.
3. Report, per task: files touched, tests added, pass counts. Flag anything you
   had to adapt (drifted line numbers, fixture differences) explicitly.
4. Do NOT push. The human reviews and pushes.




