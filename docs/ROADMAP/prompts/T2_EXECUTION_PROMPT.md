# T2 EXECUTION PROMPT — Adversary-Ready Security (attestation, rate limits, replay, hardened APK)

> **Hand this file to the implementing engineer/agent verbatim.** Self-contained: every edit has an exact file, line anchor, and code block; every phase has a test plan and a red/green gate. Written 2026-07-08 against branch `remediation/phase-by-phase` **after T1 is committed** (HEAD = `1dbea19`, the T1 journal commit). Line anchors below assume T1 is applied — if it is not, do T1 first.
>
> **Companion doc:** [../03_TIER2_SECURITY.md](../03_TIER2_SECURITY.md) is the tier overview (the "why"). This is the "how".

---

## 0. MISSION

Close the four security gaps that let a hostile actor move a carbon credit:

1. **Attestation is theatre** — `_ATTESTATION_ENFORCED = False` (server.py:199); `attestation_verified = False  # TODO(security)` (server.py:768). A rooted phone's forged `hw_attestation` blob passes with a log warning.
2. **No rate limiting** anywhere — `/register`, `/admin/*`, evidence, media are all unthrottled.
3. **Replayable signatures** — the canonical string (server.py:427-435) has no timestamp/nonce; a captured request is valid forever.
4. **Debug-key-signed, unobfuscated Android release** — build.gradle.kts:32-37 signs release with the debug keystore; no R8/ProGuard.

Plus two smaller hardening closers: a truthful health check + secret-entropy floor (T2.6) and an EXIF-trust honesty pass (T2.7).

**Ordering & independence.** T2.2 (rate limit), T2.6 (health/secret), T2.7 (EXIF) are pure backend and independent — do them first, they're cheap and unblock nothing. T2.3 (replay) touches both client and server behind a version flag. T2.1 (attestation) and T2.4/T2.5 (APK hardening) have an **external dependency** (Play/Apple credentials, a real release keystore) — build the code + fixtures now, flip the enforcement switch later. **T2.4/T2.5 depend on T0.6** (real release keystore) — if T0.6 isn't done, do the ProGuard/FLAG_SECURE code but expect to re-verify signing after T0.6.

---

## 1. ENVIRONMENT & GATES

- Repo root `flutter_dmrv/`. Backend `backend/` (FastAPI). Client `lib/` (Flutter).
- **Backend gate** (from `backend/`): `python -m pytest -q` → current baseline **285 passed, 1 skipped, 0 failed**. "Green" = ≥285 passed + your new tests, 0 failed.
- **Client gates** (repo root): `flutter analyze` → **25 issues, 0 errors** (do not add errors); `flutter test` → **152 passed, 2 skipped**.
- Test env is self-contained (conftest.py:27-34: in-memory SQLite, `DMRV_HMAC_SECRET=test-secret`, `DMRV_ADMIN_SECRET=test-admin-secret`, `DMRV_SKIP_MIGRATIONS=1`). Several tests assert the exact secret literals (`test_admin_secret.py:22,35`) — if you change the secret floor (T2.6) you MUST update these literals **and** the CI env in `.github/workflows/backend-ci.yml` in the same commit.
- New backend deps go in `requirements.txt` (current contents: fastapi/uvicorn/sqlalchemy/asyncpg/aiosqlite/pydantic/python-multipart/httpx/pytest/pytest-asyncio/psycopg2-binary/alembic/piexif). **Note:** `cryptography` and `python-dotenv` are imported but NOT yet declared — if T0.5 hasn't added them, add them when you touch requirements here.
- **One phase = one commit = one green gate = one REMEDIATION_LOG.md entry.** Follow the existing log format (tail of the file).
- Alembic: current head `f1a2b3c4d5e6`. Any new migration sets `down_revision="f1a2b3c4d5e6"` (and update this note if a prior T2 phase already added one — the head moves).

## 2. NON-NEGOTIABLE RULES

1. **Additive & backward-compatible.** Deployed field devices sign with the FROZEN canonical (server.py:427-435 ↔ crypto_signer.dart:100-116) and the FROZEN media canonical (server.py:479-488 ↔ crypto_signer.dart:118-137). You may NOT change these for existing clients. Replay protection (T2.3) is introduced as an **opt-in v2 canonical** negotiated by header, with v1 still accepted until a flag flips.
2. **Compliance stays in the provisional model.** Attestation enforcement (T2.1) flows through `assemble(attestation_ok=...)` (already wired, server.py:959) → `attestation_unverified` reason. It must NEVER reject an upload. Fail-closed = provisional, not HTTP error.
3. **Secrets from env only**, resolved through `_require_secret` (server.py:175-185). No secret literals in code.
4. **Rate limiting returns 429**, never silently drops. Auth failures stay 401/403.
5. Keep `flutter analyze` at 0 errors; keep the release-mode guards (`kReleaseMode`) intact — never weaken a fail-closed path (cert pinning at sync_queue_manager.dart:135-162, RASP compromise flag at crypto_signer.dart:108,128,141).

---

## 3. VERIFIED CURRENT-STATE ANCHORS (edit against these)

- **Attestation:** policy switch `_ATTESTATION_ENFORCED = False` (server.py:199); consumption in `recompute_batch_credit` at server.py:763-775 (`attestation_blob = tel_payload.get("hw_attestation")`; `attestation_verified = False`; `attestation_ok = True if not _ATTESTATION_ENFORCED else attestation_verified`); fed to `assemble(attestation_ok=attestation_ok)` at server.py:959; reason `attestation_unverified` in the C10 catalog (server.py:2084) and provenance resolver (server.py:2124, added in T1.10). Client ships the blob as telemetry `hw_attestation` (a list, `TelemetryPayload.hw_attestation` at server.py:1499).
- **CORS / app setup:** `app = FastAPI(...)` at server.py:212-218; `app.add_middleware(CORSMiddleware, ...)` at server.py:222-239; body-size middleware note at server.py:241+.
- **Health:** `@app.get("/api/health")` / `async def health()` at server.py:387-393 (returns static dict, no DB probe).
- **Secret floor:** `_require_secret` at server.py:175-185 (comment already says "P2.a extends this with an entropy/length floor" — finish it here).
- **verify_signature:** server.py:400-442; canonical built at 427-435 = `METHOD\npath\nidempotency_key\nbody_sha256\ndevice_id`. **verify_media_signature:** server.py:445-495; canonical at 479-488.
- **register_device:** server.py:503-556 (enrollment-token check; `EnrollmentToken` model at models.py:419-428 has `token`(PK)/`used_at`/`expires_at`/`created_at`).
- **EXIF/GPS:** `_gps_mismatch_km(..., threshold_km=1.0)` at server.py:149-154; `_evaluate_anchor` at server.py:157-172; teleport check `speed_kmh > 150.0` at server.py:1210.
- **Client signing:** `CryptoSigner.signRequest` (crypto_signer.dart:100-116) and `signMediaUpload` (crypto_signer.dart:122-137); request headers set at sync_queue_manager.dart:328-342 (`X-Idempotency-Key`, `X-Device-Id`, `X-Signature`), media headers at 504-512.
- **Cert pinning:** `_createSecureClient` at sync_queue_manager.dart:135-162 (release requires `DMRV_PINNED_CERT_PEM`, else `StateError`).
- **Android build:** `android/app/build.gradle.kts` — release block at 32-37 (`signingConfig = signingConfigs.getByName("debug")`, with the literal `// TODO: Add your own signing config`), `applicationId = "io.dmrv.dmrv_app"` at 22, no `signingConfigs {}`, no `minifyEnabled`. `MainActivity` = `android/app/src/main/kotlin/io/dmrv/dmrv_app/MainActivity.kt` (bare `FlutterActivity`).
- **Test fixtures:** conftest.py `client` (auto-signs as `test-device-reg`, conftest.py:101-138), `registered_device`, `session_factory`. Admin secret literal `test-admin-secret`.

---

## 4. PHASE 1 — T2.2 rate limiting (start here: cheap, independent, high value)

### 4.1 Dependency
Add to `backend/requirements.txt`: `slowapi==0.1.9` (pin to current). (SlowAPI wraps `limits`; in-process storage by default — fine for a single pilot node; swap to Redis storage at T3 when multi-node.)

### 4.2 server.py wiring
After the imports and before `app = FastAPI(...)` (server.py:212), add:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def _rate_key(request: Request) -> str:
    # Prefer the authenticated device; fall back to client IP. Admin routes have
    # no device header, so they key on IP (the brute-force surface we care about).
    return request.headers.get("X-Device-Id") or get_remote_address(request)


# Limits are env-tunable so the pilot can loosen/tighten without a redeploy.
_RL_DEFAULT = os.environ.get("DMRV_RATELIMIT_DEFAULT", "120/minute")
_RL_REGISTER = os.environ.get("DMRV_RATELIMIT_REGISTER", "5/minute")
_RL_ADMIN = os.environ.get("DMRV_RATELIMIT_ADMIN", "30/minute")
_RL_MEDIA = os.environ.get("DMRV_RATELIMIT_MEDIA", "20/minute")
_RL_ENABLED = os.environ.get("DMRV_RATELIMIT_ENABLED", "1") == "1"

limiter = Limiter(
    key_func=_rate_key,
    default_limits=[_RL_DEFAULT] if _RL_ENABLED else [],
    enabled=_RL_ENABLED,
)
```

After `app = FastAPI(...)` (server.py:218), register it:

```python
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

Then decorate the sensitive routes (SlowAPI needs the `request: Request` param present — `verify_signature` already receives `Request`; for routes without it, add `request: Request` as the first param). Apply:
- `@limiter.limit(_RL_REGISTER)` on `register_device` (server.py:503) — add `request: Request` param.
- `@limiter.limit(_RL_ADMIN)` on every `/api/v1/admin/*` handler and on `batch_compliance` (the mint-token, lab, lab-hcorg, kiln, operator-training, supervisor-visit, scale-calibration, annual-verification, compliance handlers).
- `@limiter.limit(_RL_MEDIA)` on `upload_media`.
- The global `_RL_DEFAULT` covers the evidence endpoints automatically.

**Test-env note:** conftest sets no rate-limit env, so `DMRV_RATELIMIT_ENABLED` defaults to `"1"` — existing tests that fire many requests in one function could trip limits. **Set `DMRV_RATELIMIT_ENABLED=0` in conftest.py** (add `os.environ.setdefault("DMRV_RATELIMIT_ENABLED", "0")` near conftest.py:30) so the whole legacy suite is unaffected, and write the T2.2 tests to explicitly re-enable via a dedicated app/client with env override.

### 4.3 Tests — new `backend/tests/test_rate_limit.py`
Because the limiter reads env at import, the cleanest test builds a limiter with `enabled=True` and asserts behavior at the SlowAPI layer, OR uses a monkeypatched app. Minimum viable assertions:
- 6th `POST /api/v1/register` within the window → 429 (spin up the app with `DMRV_RATELIMIT_ENABLED=1`, `DMRV_RATELIMIT_REGISTER=5/minute`).
- A legitimate single evidence flow still returns 2xx.
- 429 body carries a `Retry-After` header.

If per-test env override is awkward with the module-level limiter, document it: add a `reset`/`enabled` toggle helper and note that full rate-limit behavior is also covered by a staging smoke test.

**Gate → commit:** `python -m pytest -q` green. `chore(security): per-route rate limiting (register/admin/media) with env tuning (T2.2)`. Journal.

---

## 5. PHASE 2 — T2.6 truthful health check + secret-entropy floor

### 5.1 Health with DB probe (server.py:387-393)
Replace the static handler:

```python
@app.get("/api/health")
async def health(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    db_ok = True
    try:
        await session.execute(select(1))
    except Exception:  # noqa: BLE001 — health must never raise
        db_ok = False
    body = {
        "status": "ok" if db_ok else "degraded",
        "service": "dmrv-api",
        "db": "ok" if db_ok else "down",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(body, status_code=200 if db_ok else 503)
```

(`JSONResponse` is already imported — server.py imports it; if not, add `from fastapi.responses import JSONResponse`.)

### 5.2 Secret-entropy floor (server.py:175-185)
Extend `_require_secret`:

```python
_MIN_SECRET_LEN = 32
_MIN_SECRET_UNIQUE = 10


def _require_secret(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} env var is required.")
    # P2.a: reject obviously weak secrets so a placeholder can't reach production.
    if os.environ.get("DMRV_ALLOW_WEAK_SECRETS") != "1":
        if len(value) < _MIN_SECRET_LEN or len(set(value)) < _MIN_SECRET_UNIQUE:
            raise RuntimeError(
                f"{name} is too weak (needs >= {_MIN_SECRET_LEN} chars and "
                f">= {_MIN_SECRET_UNIQUE} distinct chars)."
            )
    return value
```

**CRITICAL — you WILL break the suite if you skip this:** the test secrets `test-secret` (11 chars) and `test-admin-secret` (17 chars) fail the floor. Two options, pick the honest one:
- **(a)** Update conftest.py:31-33 and `.github/workflows/backend-ci.yml` to 32+ char high-entropy test secrets (e.g. `"t3st-secret-000000000000000000000000"` won't pass the unique-char check — use a base64-ish string like `"Zm9vYmFyLXRlc3Qtc2VjcmV0LTMyLWJ5dGVzIQ"`), AND update the literals asserted in `test_admin_secret.py:22,35` and anywhere else that posts `X-Admin-Secret: test-admin-secret` (grep: `grep -rn "test-admin-secret\|test-secret" backend/tests`). This is a wide change — many tests hardcode `test-admin-secret`.
- **(b, RECOMMENDED)** set `os.environ.setdefault("DMRV_ALLOW_WEAK_SECRETS", "1")` in conftest.py (near line 30) so the test literals stay, and set `DMRV_ALLOW_WEAK_SECRETS=1` in the CI env too. Then add a dedicated `test_secret_floor.py` that imports the check in isolation and asserts a short secret raises. This keeps the blast radius to one file.

Go with **(b)**. It preserves ~30 tests' hardcoded literals and still proves the floor.

### 5.3 Tests
- `test_p1_25_lifespan.py`-style: DB-down health → 503 (override `get_session` to raise; assert 503 + `db: "down"`).
- `test_secret_floor.py`: with `DMRV_ALLOW_WEAK_SECRETS` unset, `_require_secret` on a monkeypatched short env var raises `RuntimeError`; on a 32+/10-unique value returns it.

**Gate → commit:** green. `feat(security): DB-probing health check + secret entropy floor (T2.6)`. Journal.

---

## 6. PHASE 3 — T2.7 EXIF-trust honesty pass (small, backend-only)

The client WRITES the EXIF it later "corroborates" against (secure_capture_service.dart injects GPS), so server EXIF checks corroborate the client against itself. Keep the check (catches sloppy fraud + honest error) but (a) name the constant + state the trust model, (b) surface the plausibility signals into the audit JSON for a verifier.

### 6.1 Name the threshold (server.py:149)
```python
# Client-authored EXIF is WEAK corroboration: the app injects the GPS it later
# "matches" against, so this catches careless fraud and honest error, not a
# determined attacker. The strong device control is attestation (T2.1). Keep the
# threshold generous to avoid false quarantines on legitimate GPS drift.
GPS_ANCHOR_MISMATCH_KM = 1.0


def _gps_mismatch_km(lat1, lon1, lat2, lon2, threshold_km: float = GPS_ANCHOR_MISMATCH_KM) -> bool:
```

### 6.2 Surface plausibility signals into the audit
In `recompute_batch_credit`, where the audit dict `audit["transport_events"]` is assembled (near server.py:965 in the current tree — grep `audit["transport_events"]`), add a sibling block:

```python
    audit["integrity_signals"] = {
        "mock_location_enabled": bool(batch.mock_location_enabled),
        "gps_anchor_status": batch.status,  # e.g. QUARANTINE_GPS_MISMATCH
        "exif_trust": "client_authored_weak",  # documents the trust level in-band
    }
```

### 6.3 Test
Extend an existing audit test (e.g. in `test_transport_events_flow.py` or a new `test_integrity_signals.py`): a batch with `mock_location_enabled=True` shows `integrity_signals.mock_location_enabled == True` in `lca_audit_json`; a normal batch shows `False`.

**Gate → commit:** green. `feat(security): name GPS-anchor threshold + surface integrity signals in audit (T2.7)`. Journal.

---

## 7. PHASE 4 — T2.3 replay protection (signed timestamp freshness, versioned)

**The canonical is FROZEN for the deployed fleet — this MUST be a backward-compatible, negotiated upgrade.**

### 7.1 Server: accept a v2 canonical when the client opts in (verify_signature, server.py:400-442)
Add two headers and branch on a canonical-version header:

```python
async def verify_signature(
    request: Request,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    x_canonical_version: Optional[str] = Header(None, alias="X-Canonical-Version"),
    x_signed_at: Optional[str] = Header(None, alias="X-Signed-At"),
    session: AsyncSession = Depends(get_session),
) -> str:
    ...  # existing missing-signature / unknown-device checks unchanged
    body_hash = hashlib.sha256(await request.body()).hexdigest()
    fields = [request.method.upper(), request.url.path, x_idempotency_key or "", body_hash, x_device_id]
    if x_canonical_version == "2":
        # v2 binds a client timestamp; reject stale/skewed requests (replay window).
        if not x_signed_at:
            raise HTTPException(status_code=401, detail="missing_signed_at")
        try:
            signed_at = int(x_signed_at)
        except ValueError:
            raise HTTPException(status_code=401, detail="bad_signed_at")
        skew = abs(int(datetime.now(timezone.utc).timestamp()) - signed_at)
        if skew > _CANONICAL_SKEW_SECONDS:
            raise HTTPException(status_code=401, detail="stale_signature")
        fields.append(str(signed_at))
    elif _REQUIRE_CANONICAL_V2:
        # After fleet upgrade, refuse legacy unsigned-timestamp requests.
        raise HTTPException(status_code=401, detail="canonical_v2_required")
    canonical = "\n".join(fields).encode("utf-8")
    ...  # existing verify + InvalidSignature handling unchanged
```

Add near the attestation switch (server.py:199):
```python
# T2.3 replay protection. Rural devices drift, so the skew window is generous and
# env-tunable. _REQUIRE_CANONICAL_V2 stays False until the fleet ships v2 signing;
# flip to True (env DMRV_REQUIRE_CANONICAL_V2=1) to refuse replayable v1 requests.
_CANONICAL_SKEW_SECONDS = int(os.environ.get("DMRV_CANONICAL_SKEW_SECONDS", "300"))
_REQUIRE_CANONICAL_V2 = os.environ.get("DMRV_REQUIRE_CANONICAL_V2", "0") == "1"
```

### 7.2 Client: emit v2 (crypto_signer.dart:100-116 + call site sync_queue_manager.dart:328-342)
Add a v2 signer (keep the v1 method for rollback safety, or make v1 delegate):

```dart
/// v2 canonical: method\npath\nidempotencyKey\nsha256(body)\ndeviceId\nsignedAt
static Future<(String sig, String signedAt)> signRequestV2({
  required String method,
  required String path,
  required String idempotencyKey,
  required String deviceId,
  required String jsonBody,
}) async {
  if (isDeviceCompromisedGlobally) throw StateError('device_compromised');
  final signedAt =
      (DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000).toString();
  final bodySha = sha256.convert(utf8.encode(jsonBody)).toString();
  final canonical = '$method\n$path\n$idempotencyKey\n$bodySha\n$deviceId\n$signedAt';
  final sig = await _algo.sign(utf8.encode(canonical), keyPair: await _keyPair());
  return (base64Url.encode(sig.bytes).replaceAll('=', ''), signedAt);
}
```

At the request call site (sync_queue_manager.dart:328-342) switch to v2 and add the two headers:
```dart
final (signature, signedAt) = await CryptoSigner.signRequestV2(...);
// headers:
'X-Canonical-Version': '2',
'X-Signed-At': signedAt,
'X-Signature': signature,
```
(Media path can follow in a later pass — do request-signing first; the media canonical is a separate frozen string.)

### 7.3 Tests
- Backend `test_replay.py`: build a v2-signed request with `signed_at = now` → 200; with `signed_at = now - 3600` → 401 `stale_signature`; a v1 request (no version header) still → 200 while `_REQUIRE_CANONICAL_V2` is False; with `DMRV_REQUIRE_CANONICAL_V2=1` a v1 request → 401. (You'll need to sign with the conftest test key — reuse `_ed25519_sign` / the SignedAsyncClient's canonical builder, extended with the timestamp field.)
- Update `test_client_contract.py` / `test_signature.py` with v2 vectors; keep v1 vectors until the refuse-flag flips.
- Flutter: unit-test `signRequestV2` produces a stable canonical and a parseable `signedAt`.

**Gate → commit:** backend + flutter green. `feat(security): opt-in v2 signed-timestamp canonical for replay protection (T2.3)`. Journal. **Roll-out note in the journal:** flip `DMRV_REQUIRE_CANONICAL_V2=1` only after the field fleet ships a v2 build.

---

## 8. PHASE 5 — T2.1 device attestation verification (code + fixtures now, enforce later)

**External dependency:** Play Integrity / DeviceCheck require Google Play Console + Apple Developer credentials and a real signing cert (T0.6). Build the verifier + tests against fixtures now; wiring the live provider call and flipping `_ATTESTATION_ENFORCED` happens when credentials land.

### 8.1 New module `backend/attestation.py`
```python
"""Platform attestation verification (Play Integrity / DeviceCheck).

Verdict verification is behind an interface so the enforcement wiring in
recompute_batch_credit is testable with fixtures before real Google/Apple
credentials exist. verify_attestation returns a structured verdict; the caller
decides policy (provisional vs issuable) — it never raises to reject an upload.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class AttestationVerdict:
    verified: bool
    reason: Optional[str] = None  # why not verified, for the audit trail


def verify_play_integrity(token: str, *, expected_nonce: str) -> AttestationVerdict:
    # TODO(creds): call playintegrity.googleapis.com decodeIntegrityToken (or
    # local JWE decrypt), assert appRecognitionVerdict == PLAY_RECOGNIZED,
    # deviceIntegrity contains MEETS_DEVICE_INTEGRITY, packageName matches, and
    # requestDetails.nonce == expected_nonce. Until creds exist, treat any token
    # as unverified unless a test double is injected.
    return AttestationVerdict(verified=False, reason="verifier_not_configured")


def verify_attestation(blob, *, expected_nonce: str) -> AttestationVerdict:
    """Dispatch by platform; blob shape is the client's hw_attestation list."""
    if not blob:
        return AttestationVerdict(verified=False, reason="no_attestation")
    # Real dispatch (android vs ios) goes here once the payload shape is fixed.
    return AttestationVerdict(verified=False, reason="verifier_not_configured")
```

### 8.2 Nonce binding via enrollment (additive migration)
A verdict must be bound to something the server issued, or it's replayable. Add a nonce to enrollment:
- **models.py** `EnrollmentToken` (models.py:419-428): add `nonce: Mapped[str] = mapped_column(String(64), nullable=True)`.
- **Migration** `<hash>_enrollment_nonce.py`, `down_revision="f1a2b3c4d5e6"` (or the latest T2 head), one nullable `add_column`.
- **mint_enrollment_token** (server.py:564+): generate a random nonce (`secrets.token_urlsafe(32)`) and return it so the device stores it and feeds it into the Play Integrity request.

(If binding to enrollment is too coarse for your provider, bind per-request instead via the T2.3 `signed_at`+device — document the choice. Enrollment-nonce is the simpler first cut.)

### 8.3 Consume the verdict (server.py:763-775)
Replace the stub:
```python
    attestation_blob = tel_payload.get("hw_attestation") if tel_payload else None
    from attestation import verify_attestation  # local import keeps module optional
    _verdict = verify_attestation(attestation_blob, expected_nonce=_resolve_nonce(batch))
    attestation_verified = _verdict.verified
    if attestation_blob and not attestation_verified:
        log.warning("batch %s attestation unverified: %s", batch.batch_uuid, _verdict.reason)
    attestation_ok = True if not _ATTESTATION_ENFORCED else attestation_verified
```
(`_resolve_nonce(batch)` looks up the device's enrollment nonce; stub it to return `""` until 8.2's wiring is complete — with the verifier returning `verified=False` regardless, behavior is unchanged while `_ATTESTATION_ENFORCED=False`.)

### 8.4 Tests — `backend/tests/test_attestation.py`
Inject a test-double verifier (monkeypatch `attestation.verify_attestation`):
- verdict `verified=True` + `_ATTESTATION_ENFORCED=True` → batch NOT provisional for the attestation reason.
- verdict `verified=False` + `_ATTESTATION_ENFORCED=True` → `attestation_unverified` in reasons, batch provisional.
- `_ATTESTATION_ENFORCED=False` (default) → reason absent regardless (today's behavior preserved).
- `verify_play_integrity` unit: wrong nonce → `verified=False`.

**Gate → commit:** green (default behavior unchanged; enforcement covered by fixtures). `feat(security): attestation verifier interface + nonce binding + verdict wiring (T2.1, enforcement flag off)`. Journal. **Backlog note:** flip `_ATTESTATION_ENFORCED=True` after the live Play Integrity/DeviceCheck call is implemented and the fleet is verified-capable.

---

## 9. PHASE 6 — T2.4 + T2.5 Android hardening (depends on T0.6 release keystore)

### 9.1 T2.5 FLAG_SECURE (screenshot/recents protection)
`MainActivity.kt` is currently a bare `FlutterActivity`. Replace with:
```kotlin
package io.dmrv.dmrv_app

import android.os.Bundle
import android.view.WindowManager
import io.flutter.embedding.android.FlutterActivity

class MainActivity : FlutterActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        // T2.5: block screenshots + hide the app from the recents thumbnail.
        // BuildConfig.DEBUG gate keeps screenshots working for development.
        if (!BuildConfig.DEBUG) {
            window.setFlags(
                WindowManager.LayoutParams.FLAG_SECURE,
                WindowManager.LayoutParams.FLAG_SECURE,
            )
        }
        super.onCreate(savedInstanceState)
    }
}
```
(If `BuildConfig` isn't resolvable in the flavor setup, gate on a `--dart-define`-driven MethodChannel instead; simplest is the BuildConfig.DEBUG check.)

### 9.2 T2.4 R8/ProGuard (build.gradle.kts release block, lines 32-37)
```kotlin
    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release") // from T0.6; NOT debug
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }
```
New `android/app/proguard-rules.pro` with `-keep` rules for: Flutter embedding (`io.flutter.**`), drift/sqlite3 (`-keep class org.sqlite.** { *; }` + the sqlite3 NDK loader), flutter_secure_storage, sentry (`-keep class io.sentry.** { *; }`), freeRASP/Talsec (their published keep rules), flutter_reactive_ble, workmanager, sensors_plus. Start from the Flutter default and add as R8 strips break things.

Build with `flutter build apk --release --obfuscate --split-debug-info=build/symbols`; archive `build/symbols/` per release (Sentry needs it to symbolicate).

### 9.3 Gate
- `flutter build apk --release` succeeds; run the full capture→sync flow on a physical device (or `flutter run --release`).
- `apksigner verify --print-certs build/app/outputs/flutter-apk/app-release.apk` shows the T0.6 release cert, NOT `Android Debug`.
- Screenshot attempt in a release build fails; recents view masked.
- `jadx` on the APK shows obfuscated app classes.
- (These are manual/device gates — `flutter test` can't cover them. Document the manual run in the journal.)

**Commit:** `build(android): R8+ProGuard obfuscation and FLAG_SECURE on release (T2.4/T2.5)`. Journal (note the dependency on T0.6's keystore and the manual verification performed).

---

## 10. PHASE 7 — T2.8 secret rotation note (doc-only unless deploying)

No code. In `DEPLOYMENT.md` (and the T3 secrets section) document: at first real deploy, generate fresh 32-byte `DMRV_HMAC_SECRET`/`DMRV_ADMIN_SECRET` (base64url), store in the platform secret manager, never a file. Note: rotating `DMRV_HMAC_SECRET` invalidates verification of already-issued `lca_signature` values — archive the old key for historical verification, or re-sign historical audits in a migration. Commit as part of the T3 deployment-doc rewrite; here just leave a `TODO(deploy)` breadcrumb in `_require_secret`'s docstring if you want it tracked in-code.

---

## 11. DEFINITION OF DONE (T2 exit benchmark)

Record in REMEDIATION_LOG.md:
1. `python -m pytest -q` → 0 failed, ≥ ~300 passed (285 + new). `flutter analyze` 0 errors; `flutter test` 0 failed.
2. **Rate limit:** a scripted 6× `/register` in a minute → 429 with `Retry-After` (test or staging-smoke).
3. **Replay:** a byte-identical replay of a captured **v2** request older than the skew window → 401 `stale_signature`; v1 still works while `_REQUIRE_CANONICAL_V2=0`.
4. **Attestation:** with the fixture verifier + `_ATTESTATION_ENFORCED=True`, a `verified=False` batch is provisional with `attestation_unverified`; default (flag off) behavior unchanged.
5. **Health:** `/api/health` returns 503 when the DB is unreachable.
6. **Secret floor:** server refuses a <32-char / low-entropy secret (unless `DMRV_ALLOW_WEAK_SECRETS=1`).
7. **APK (manual):** `apksigner` shows a non-debug cert; `jadx` output obfuscated; screenshots blocked on release.
8. Alembic single head after any migration you added; round-trip clean.
9. Each phase = one commit + journal entry.

**Standing claim after T2:** *a rooted phone, a replayed request, a brute-forced admin header, or a decompiled APK no longer moves a credit; every evidence signal's trust level is stated in-band. The only enforcement switches still OFF are `_ATTESTATION_ENFORCED` and `DMRV_REQUIRE_CANONICAL_V2`, both awaiting the field-fleet upgrade / provider credentials — code and tests are in place to flip them.*

## 12. TRAPS

- **The secret floor will red-gate ~30 tests** if you take option (a). Take option (b) (`DMRV_ALLOW_WEAK_SECRETS=1` in conftest + CI). Verify with a full suite run, not a subset.
- **SlowAPI + the test suite:** if you don't disable rate limiting in conftest, existing flow tests that fire 3-4 signed requests per function may randomly 429. Disable by default in tests; enable only in `test_rate_limit.py`.
- **Do NOT change the v1 canonical.** Deployed devices sign it. v2 is additive and negotiated by `X-Canonical-Version`. Keep v1 accepted until the refuse-flag flips.
- **`request: Request` param:** SlowAPI's `@limiter.limit` needs the handler to have a `Request` param (named `request`). Admin handlers currently take only `payload` + header — add `request: Request` or they'll error at decoration.
- **Attestation must never reject.** Fail-closed = provisional via `assemble`, not an HTTP error. Do not add a 403 for unattested devices.
- **`FLAG_SECURE` + camera:** the secure-camera screen still works under FLAG_SECURE (it blocks external screenshots, not the app's own camera). Verify on device.
- **T0.6 dependency:** if the release keystore doesn't exist yet, the `signingConfigs.getByName("release")` line fails the build — do T0.6 first or the ProGuard commit won't build.
- Keep the `1 skipped` baseline; don't chase it.
