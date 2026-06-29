# TerraCipher / Kon‑Tiki Biochar dMRV — Full Code Review & Refactoring Report

**Reviewed artifact:** `New folder.zip`
**Stack:** Flutter/Dart client (~9,433 hand‑written LOC + 7,845 generated) · FastAPI + SQLAlchemy backend · CSI LCA engine · 49 Dart test files (~4,846 LOC) + Python test suite
**Review style:** Brutally honest (as requested)
**Date:** June 2026
**Document contents:** (1) Executive verdict · (2) Detailed findings with code · (3) File‑by‑file refactoring guide with before/after · (4) Prioritized remediation plan · (5) Skill assessment

---

# PART 1 — EXECUTIVE VERDICT

This is **ambitious, well‑above‑average software** with a real architectural backbone: transactional outbox, two‑phase sync with server‑hash verification, SQLCipher encryption at rest, idempotency, a maintained 15‑version migration history, and ~49 test files. The *design vision* is senior‑level.

But it is **not the "Truth Machine" it advertises.** The core premise — cryptographic, non‑repudiable proof of carbon credits — is undermined by:

- a **symmetric‑key** trust model wrongly described as non‑repudiation,
- a **hardcoded `dev-token` backdoor** in shipped code,
- security controls that **fail open** instead of closed,
- **client‑asserted** fraud flags (mock GPS),
- credit math driven by **assumed constants and dangerous defaults**.

There is also a clear fingerprint of **LLM/agent‑generated code** (prompt files, codegen CI, "Phase 6 Fix 4/Fix 5" comment style). Orchestrating that is a real skill — but the tell is consistent: excellent *patterns*, weak *threat modeling*.

| | |
|---|---|
| **Overall grade** | **B / B+** |
| **Skill level** | Mid‑level engineer with senior architectural reach, heavy AI assistance |
| **Production‑ready to mint real credits?** | **No** — fix the 🔴 items first |

---

# PART 2 — DETAILED FINDINGS

Severity legend: 🔴 Critical (blocks trust/money) · 🟠 High · 🟡 Medium · ⚪ Minor

---

## 🔴 FINDING 1 — "Non‑repudiable" crypto is symmetric HMAC

**Files:** `lib/services/crypto_signer.dart:70‑125`, `backend/server.py:167‑209`, `backend/models.py:132‑141`

`CryptoSigner` signs payloads with **HMAC‑SHA256**, and the client **generates its own key and uploads it to the server**:

```dart
// crypto_signer.dart — the client mints the secret and ships it to the server
final keyBytes = List<int>.generate(32, (_) => random.nextInt(256));
final b64Key = base64Url.encode(keyBytes).replaceAll('=', '');
await _storage.write(key: _keyName, value: b64Key);
// ...later, registerDevice():
body: jsonEncode({'device_id': deviceId, 'hmac_key': hmacKey}),  // <-- secret leaves the device
```

The server stores it (`device_keys.hmac_key`) and verifies with the **same** key. **Both parties hold the secret → the server can forge any client signature → there is no non‑repudiation.** A symmetric MAC gives you integrity + channel auth, nothing more. Yet `main.dart` brands this a "Truth Machine" and comments call the result "indelible."

You already do this correctly for the ESP32 sensor (ECDSA `hwAttestationJson`). The phone — which signs the *financially material* payloads — must do the same. **See Refactor R1.**

---

## 🔴 FINDING 2 — Hardcoded backdoor enrollment token

**Files:** `lib/services/crypto_signer.dart:76`, `backend/server.py:245`

```dart
// client: default token baked into the binary
final enrollmentToken = const String.fromEnvironment('ENROLLMENT_TOKEN', defaultValue: 'dev-token');
```
```python
# server: dev-token is never consumed and never expires
if db_token.token != "dev-token":
    db_token.used_at = datetime.now(timezone.utc)
```

If a `dev-token` row exists, **anyone with the APK can register unlimited arbitrary devices** with a token shipped in the binary. This is the single most dangerous primitive in the repo for a system that mints money. **See Refactor R2.**

---

## 🔴 FINDING 3 — Security controls fail OPEN

**Files:** `crypto_signer.dart:91‑96`, `device_integrity_service.dart:11‑58`

```dart
// registerDevice — failure is swallowed, device proceeds unregistered
if (response.statusCode != 201) {
  debugPrint('Failed to register device: ${response.statusCode}');
}
// ...
} catch (e) {
  debugPrint('Error registering device: $e');
}
```
```dart
// device_integrity_service — three separate fail-open paths
if (kDebugMode || const bool.fromEnvironment('DMRV_DEMO_MODE')) {
  return;                       // (a) integrity entirely bypassed
}
signingCertHashes: [const String.fromEnvironment('TALSEC_SIGNING_CERT_HASH')], // (b) defaults to ['']
// ...
} catch (e, st) {
  debugPrint('Talsec initialization failed ...'); // (c) failure swallowed
}
```

For an anti‑fraud product these must **fail closed** (hard‑lock). Ship one release with `--dart-define=DMRV_DEMO_MODE=true` and *all* root/emulator/hook detection is silently off. **See Refactor R3.**

---

## 🔴 FINDING 4 — Mock‑GPS "server‑side" detection is the honor system

**File:** `backend/server.py:514`

```python
if request.headers.get("x-mock-location", "").lower() == "true":
    raise HTTPException(status_code=403, detail="mock_location_not_allowed")
```

The "control" trusts a **client‑sent boolean**. A fraudster sends `false`. You moved the *check* server‑side but not the *source of truth*. The compass telemetry + teleport/`implausible_movement` speed check are real signals; the mock flag is theatre. **See Refactor R4.**

---

## 🟠 FINDING 5 — Financial defaults that silently fabricate credits

**File:** `backend/server.py:91‑93`

```python
wet_yield_kg: float = Field(100.0, gt=0.0, ...)        # <-- defaults to a fictional 100kg
min_recorded_temp_c: float = Field(0.0, ge=-50.0, ...)
transport_distance_km: float = Field(0.0, ge=0.0, ...)
```

If the client omits `wet_yield_kg`, the LCA engine issues a credit for a **made‑up 100kg batch.** Inputs that feed money must be **required**, never defaulted. **See Refactor R5.**

---

## 🟠 FINDING 6 — LCA engine issues credits from an assumed permanence constant

**File:** `backend/lca_engine.py:116‑134, 181‑200`

`step3_cremain` defaults `h_corg_ratio=0.35`; `lab_h_corg` is optional and rarely sent. Since 0.35 < 0.4 always, the permanence factor collapses to a near‑constant (~0.96). The scientific basis for issuance is therefore **an assumption, not a measurement,** on the common path.

Also `gross_c_sink_t_co2e` (Step 2) is computed, stored in the audit, and **never used** in `step8_net_credit` — dead provenance.

```python
def step3_cremain(dry_mass_t, corg_pct, t=100, h_corg_ratio=0.35):  # silent default
    if h_corg_ratio >= 0.4:
        return dry_mass_t * corg_pct * 0.70
    decay_term = 0.1787*math.exp(-0.5337*t) + 0.8237*math.exp(-0.00997*t)
    return dry_mass_t * corg_pct * (0.75 + 0.25*decay_term)
```

**See Refactor R6.**

---

## 🟠 FINDING 7 — Background sync worker is a self‑admitted hack

**File:** `lib/services/sync_queue_manager.dart:25‑42`

```dart
Workmanager().executeTask((task, inputData) async {
  final syncQueue = container.read(syncQueueManagerProvider);
  syncQueue.kickSync(); // not awaited
  // "Actually we should wait for sync to complete ... but kickSync doesn't
  //  return a Future. We can just sleep for 10 seconds..."
  await Future.delayed(const Duration(seconds: 10));
  return Future.value(true); // WorkManager success signal is meaningless
});
```

WorkManager's retry/backoff machinery is defeated; completion is a coin flip. `kickSync`/`_triggerSync` must return a `Future` the worker awaits. **See Refactor R7.**

---

## 🟠 FINDING 8 — Backend hygiene contradicts the architecture

**File:** `backend/server.py` (throughout)

- Imports **inside functions**: `import json`, `import base64`, `import re`, `import uuid`, `from math import ...`. `import json` appears **twice** inside `create_batch` (`:327`, `:415`). `from models import EnrollmentToken` sits at line 211.
- `haversine` is **defined inline twice** (`:370`, `:725`). DRY violation.
- `is_verified: bool = Depends(verify_hmac)` — `verify_hmac` returns a **device_id string**, not a bool. Misleading.
- `/telemetry`, `/yield`, `/metadata`, `/application` take raw `payload: dict` with **no schema and no size limit**, while `/batches` is strict (`extra="forbid"`). Rigor evaporates where it's least observed.

**See Refactor R8.**

---

## 🟡 FINDING 9 — Secret reuse (admin password == HMAC pepper)

**File:** `backend/server.py:263`

```python
if not hmac.compare_digest(x_admin_secret, _HMAC_SECRET):  # admin auth reuses the HMAC pepper
```

Two distinct secrets collapsed into one. Rotate one → break the other; leak one → leak both. **See Refactor R9.**

---

## 🟡 FINDING 10 — Test/"unsafe" code on the production surface

**File:** `lib/data/local/app_database.dart:303‑309`

```dart
// Test-only: fetch unencrypted raw query result
Future<List<QueryRow>> getBatchTelemetryUnsafe(String batchUuid) async { ... }
```

A public method named `...Unsafe` lives in the production `AppDatabase`. Gate behind `@visibleForTesting` or remove. **See Refactor R10.**

---

## 🟡 FINDING 11 — File integrity ≠ scene authenticity (conceptual)

**File:** `lib/services/secure_capture_service.dart:19‑24, 236‑239`

The pipeline re‑encodes the JPEG at q=70 in an isolate, then SHA‑256‑hashes the **recompressed derivative**, branding it an "indelible digital fingerprint." It proves bytes didn't change in transit — it does **not** prove the photo shows a real burn. The product conflates *integrity* with *authenticity*. No code fix; fix the **claims** and add server‑side corroboration (GPS↔EXIF cross‑check, time‑of‑day vs sun angle, device attestation). **See Refactor R11 (docs/claims).**

---

## ⚪ MINOR

- **Global mutable state:** `isDeviceCompromisedGlobally` (process‑global, never re‑evaluated) + all‑static `CryptoSigner` with cached futures → fragile isolation tests, ordering hazards.
- **Doc rot:** `schemaVersion = 15` but `tables.dart` header says "v4"; `onUpgrade` skips explicit v5/v13/v14 blocks (cumulative `if (from < N)` is fine, but comments mislead).
- **Comment‑to‑signal ratio:** large self‑narrating blocks ("Phase 7 — Sybil Asset Defense") read like a changelog welded onto source. Let tests document behavior.
- **`empty catch`:** `proof_queries.dart:89 } catch (_) {}` swallows errors silently.

---

# PART 3 — FILE‑BY‑FILE REFACTORING GUIDE

Each refactor shows **why**, **before**, and **after**. Backend refactors are Python (compile‑checkable); Dart refactors are reviewed‑but‑uncompiled (no Flutter SDK in this environment) — treat them as drop‑in patches to validate locally with `flutter analyze` + `flutter test`.

---

## R1 — Replace symmetric HMAC with asymmetric device signatures

**Goal:** real non‑repudiation. Private key never leaves the device; server stores only the public key.

**Dart — `crypto_signer.dart` (use Ed25519 via `cryptography` package):**

`pubspec.yaml`: add `cryptography: ^2.7.0`.

```dart
import 'package:cryptography/cryptography.dart';

class DeviceSigner {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );
  static const _privKeyName = 'ed25519_private_seed';
  static final _algo = Ed25519();
  static SimpleKeyPair? _cachedPair;

  static Future<SimpleKeyPair> _keyPair() async {
    if (_cachedPair != null) return _cachedPair!;
    final stored = await _storage.read(key: _privKeyName);
    if (stored != null) {
      final seed = base64Url.decode(stored);
      _cachedPair = await _algo.newKeyPairFromSeed(seed);
      return _cachedPair!;
    }
    final pair = await _algo.newKeyPair();
    final seed = await pair.extractPrivateKeyBytes();
    await _storage.write(key: _privKeyName, value: base64Url.encode(seed));
    _cachedPair = pair;
    return pair;
  }

  /// Only the PUBLIC key is ever transmitted.
  static Future<String> publicKeyB64() async {
    final pub = await (await _keyPair()).extractPublicKey();
    return base64Url.encode(pub.bytes);
  }

  static Future<String> signRequest({
    required String method,
    required String path,
    required String idempotencyKey,
    required String deviceId,
    required String jsonBody,
  }) async {
    if (isDeviceCompromisedGlobally) throw StateError('device_compromised');
    final bodySha = sha256.convert(utf8.encode(jsonBody)).toString();
    final canonical = '$method\n$path\n$idempotencyKey\n$bodySha\n$deviceId';
    final sig = await _algo.sign(utf8.encode(canonical), keyPair: await _keyPair());
    return base64Url.encode(sig.bytes); // signature only; pubkey already enrolled
  }
}
```

**Python — `server.py` verification (replace `verify_hmac` body crypto):**

`requirements`: add `cryptography`.

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
import base64

async def verify_signature(request, x_device_id, x_signature, x_idempotency_key, session):
    if not x_signature:
        raise HTTPException(401, "missing_signature")
    if not x_device_id:
        raise HTTPException(403, "unknown_device")
    device = (await session.execute(
        select(DeviceKey).where(DeviceKey.device_id == x_device_id))).scalar_one_or_none()
    if not device:
        raise HTTPException(403, "unknown_device")

    pub = Ed25519PublicKey.from_public_bytes(base64.urlsafe_b64decode(_pad(device.public_key)))
    raw_body = await request.body()
    body_hash = hashlib.sha256(raw_body).hexdigest()
    canonical = "\n".join([request.method.upper(), request.url.path,
                           x_idempotency_key or "", body_hash, x_device_id]).encode()
    try:
        pub.verify(base64.urlsafe_b64decode(_pad(x_signature)), canonical)
    except InvalidSignature:
        raise HTTPException(403, "signature_mismatch")
    return x_device_id
```

Rename `DeviceKey.hmac_key` → `public_key` (migration), and `register` now accepts `public_key` instead of `hmac_key`. The server **never holds anything that can forge a client signature.**

---

## R2 — Remove the `dev-token` backdoor

**`crypto_signer.dart` (registration):** remove the default; fail closed if missing.

```dart
const enrollmentToken = String.fromEnvironment('ENROLLMENT_TOKEN');
if (enrollmentToken.isEmpty) {
  throw StateError('ENROLLMENT_TOKEN is required; pass via --dart-define-from-file.');
}
```

**`server.py` (register_device):** delete the special case — every token is single‑use + expiring.

```python
# BEFORE
if db_token.token != "dev-token":
    db_token.used_at = datetime.now(timezone.utc)

# AFTER
db_token.used_at = datetime.now(timezone.utc)   # all tokens are consumed, no exceptions
```

Seed dev environments with a real minted token via `/api/v1/admin/mint-token`, never a magic string.

---

## R3 — Make security controls fail CLOSED

**`device_integrity_service.dart`:**

```dart
Future<void> initialize() async {
  if (kIsWeb) return;

  // Demo mode must be a SEPARATE build flavor, never silently disable integrity
  // in a release binary. Refuse to run a release build with demo bypass.
  final demo = const bool.fromEnvironment('DMRV_DEMO_MODE');
  if (demo && kReleaseMode) {
    throw StateError('DMRV_DEMO_MODE is forbidden in release builds.');
  }
  if (demo || kDebugMode) {
    debugPrint('[DeviceIntegrity] demo/debug — integrity skipped (non-release only).');
    return;
  }

  const certHash = String.fromEnvironment('TALSEC_SIGNING_CERT_HASH');
  const iosTeam  = String.fromEnvironment('TALSEC_IOS_TEAM_ID');
  if (certHash.isEmpty || iosTeam.isEmpty) {
    _compromised('Integrity config missing'); // FAIL CLOSED, not ['']
    return;
  }
  // ...attach listener...
  try {
    await Talsec.instance.start(config);
  } catch (e) {
    _compromised('Talsec failed to start: $e'); // FAIL CLOSED
  }
}
```

**`crypto_signer.dart` registration:** surface failure to the caller instead of swallowing.

```dart
if (response.statusCode != 201 && response.statusCode != 409) {
  throw StateError('Device registration failed: ${response.statusCode} ${response.body}');
}
```

---

## R4 — Stop trusting the client mock‑GPS header

Delete the honor‑system header check; rely on (a) compass telemetry plausibility and (b) the teleport speed check you already have, and add server‑side EXIF‑vs‑payload GPS cross‑check.

**`server.py`:**

```python
# REMOVE this from upload_media:
# if request.headers.get("x-mock-location") == "true": raise 403

# In create_batch, after the existing teleport check, add EXIF corroboration:
if media and media.exif_lat is not None:           # parse EXIF server-side on upload
    drift_km = haversine(payload.longitude, payload.latitude, media.exif_lon, media.exif_lat)
    if drift_km > 1.0:                              # photo GPS vs claimed GPS disagree
        batch.status = "QUARANTINE_GPS_MISMATCH"
```

Treat `mock_location_enabled` as a **stored signal for review**, not an access control.

---

## R5 — Make credit inputs required, not defaulted

**`server.py` `BatchPayload`:**

```python
# BEFORE
wet_yield_kg: float = Field(100.0, gt=0.0)
min_recorded_temp_c: float = Field(0.0, ge=-50.0, le=1500.0)
transport_distance_km: float = Field(0.0, ge=0.0, le=20000.0)

# AFTER — no silent fabrication of money
wet_yield_kg: float = Field(..., gt=0.0)
min_recorded_temp_c: float = Field(..., ge=-50.0, le=1500.0)
transport_distance_km: float = Field(..., ge=0.0, le=20000.0)
```

A missing field now yields `422`, not a fictional credit.

---

## R6 — Make LCA permanence measured, not assumed; drop dead value

**`lca_engine.py`:**

```python
# step3: require an explicit ratio — no silent default
def step3_cremain(dry_mass_t, corg_pct, *, h_corg_ratio, t=100):
    if h_corg_ratio is None:
        raise ValueError("h_corg_ratio is required (lab-measured H:Corg).")
    ...

# calculate_carbon_credit: require lab_h_corg OR mark provisional
def calculate_carbon_credit(*, wet_yield_kg, moisture_percent, min_recorded_temp_c,
                            transport_distance_km, feedstock_species, h_corg_ratio=None):
    provisional = h_corg_ratio is None
    ratio = h_corg_ratio if h_corg_ratio is not None else 0.35
    ...
    audit.provisional = provisional   # never issue final credits on provisional
    return audit
```

**`server.py`:** if `lab_h_corg is None`, store the batch as `status="PROVISIONAL"` and **do not** treat `net_credit_t_co2e` as issuable until a lab value arrives. Also remove `gross_c_sink_t_co2e` from issuance logic (keep in audit only, clearly labelled "informational").

---

## R7 — Make background sync await real completion

**`sync_queue_manager.dart`:**

```dart
// _triggerSync already returns Future<void>; expose it and return its result.
Future<void> kickSync() => _triggerSync();

@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    final container = ProviderContainer();
    try {
      await container.read(syncQueueManagerProvider).kickSync(); // AWAIT real work
      return true;            // success only if sync completed
    } catch (e) {
      debugPrint('Background sync failed: $e');
      return false;           // let WorkManager retry with its own backoff
    } finally {
      container.dispose();    // also fixes a container leak in the original
    }
  });
}
```

(Original also leaked the `ProviderContainer` — `dispose()` fixes it.)

---

## R8 — Backend hygiene pass

**`server.py` top of file (hoist all imports):**

```python
import base64, hashlib, hmac, json, logging, os, re, uuid
from datetime import datetime, timezone, timedelta
from math import radians, cos, sin, asin, sqrt
from models import (Batch, MediaFile, DeviceKey, EnrollmentToken,
                    PyrolysisTelemetry, YieldMetrics, EndUseApplication, SystemMetadata)
```

**Extract `haversine` once (module level):**

```python
def haversine_km(lon1, lat1, lon2, lat2) -> float:
    lon1, lat1, lon2, lat2 = map(radians, (lon1, lat1, lon2, lat2))
    a = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 6371.0 * 2 * asin(sqrt(a))
```

**Fix the misleading dependency name/type:**

```python
async def create_telemetry(payload: TelemetryPayload,
                           device_id: str = Depends(verify_signature),  # not "is_verified: bool"
                           session: AsyncSession = Depends(get_session)):
```

**Add schemas + size guard to the four `dict` endpoints** (example for telemetry):

```python
class TelemetryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_uuid: str
    telemetry_uuid: str
    temperature_readings_json: list[float] = Field(..., max_length=100_000)
    # ...explicit fields instead of raw dict...
```

Apply the same to `/yield`, `/metadata`, `/application`. This restores the rigor `/batches` already has.

---

## R9 — Separate the admin secret from the HMAC pepper

**`.env`:** add `DMRV_ADMIN_SECRET` distinct from `DMRV_HMAC_SECRET`.

**`server.py`:**

```python
_ADMIN_SECRET = os.environ.get("DMRV_ADMIN_SECRET")
if not _ADMIN_SECRET:
    raise RuntimeError("DMRV_ADMIN_SECRET env var is required.")

# mint_enrollment_token:
if not hmac.compare_digest(x_admin_secret, _ADMIN_SECRET):  # no longer reuses _HMAC_SECRET
    raise HTTPException(401, "unauthorized")
```

---

## R10 — Remove test code from the production surface

**`app_database.dart`:**

```dart
@visibleForTesting
Future<List<QueryRow>> getBatchTelemetryRaw(String batchUuid) =>  // renamed, gated
    customSelect('SELECT * FROM pyrolysis_telemetry WHERE batch_uuid = ?',
        variables: [Variable.withString(batchUuid)]).get();
```

Move it to a test helper extension if it's only used by tests.

---

## R11 — Fix the claims (not just the code)

Replace marketing language in comments/UX that conflates integrity with authenticity:

- `main.dart`: "Truth Machine … can never cause double‑counted carbon credits" → *"Append‑only outbox with idempotency keys minimizes double‑counting under intermittent connectivity."*
- `secure_capture_service.dart`: "indelible digital fingerprint" → *"SHA‑256 anchors the on‑disk file bytes for tamper‑evidence in transit; it does not attest scene authenticity."*

Then add the real corroboration controls (R4) so the product earns the trust it claims.

---

# PART 4 — PRIORITIZED REMEDIATION PLAN

### Phase 0 — Stop minting fraud (do first, ~1 week)
1. **R2** Remove `dev-token` backdoor.
2. **R3** Fail closed on integrity + registration.
3. **R5** Make credit inputs required.
4. **R7** Await real sync completion + fix container leak.

### Phase 1 — Restore real trust (~2 weeks)
5. **R1** Asymmetric (Ed25519) device signatures; server stores public keys only.
6. **R4** Drop client mock‑GPS header; add EXIF↔payload GPS cross‑check.
7. **R6** Require lab H:Corg or mark batches `PROVISIONAL`; never issue on assumptions.

### Phase 2 — Hygiene & maintainability (~1 week)
8. **R8** Hoist imports, extract `haversine`, schema‑validate the four `dict` endpoints, fix `is_verified` type.
9. **R9** Separate admin secret from HMAC pepper.
10. **R10** Gate `...Unsafe` test methods.
11. **R11** Correct the trust claims; fix schema‑version doc rot; remove empty `catch (_) {}`.

### Phase 3 — Hardening backlog
- Re‑evaluate `isDeviceCompromisedGlobally` periodically (it's set once and never rechecked).
- Convert `CryptoSigner`/`DeviceSigner` static singletons to injectable services for testability.
- Add server‑side rate limiting on `/register` and `/admin/mint-token`.
- Add Alembic‑driven migrations (backend currently relies on `create_all`, which silently drifts from the client's disciplined 15‑version migrations).

---

# PART 5 — SKILL ASSESSMENT (honest)

| Dimension | Rating | Evidence |
|---|---|---|
| Architecture & system design | **Senior** | Outbox, two‑phase sync, offline‑first, 15‑version migrations |
| Test discipline | **Senior** | 49 files; migration/deadlock/release‑guard coverage |
| Flutter/Dart idiom | **Mid‑Senior** | Clean Riverpod; but global statics + static singletons |
| Backend craftsmanship | **Mid** | Capable, but in‑function imports, dup `haversine`, inconsistent validation |
| Security threat modeling | **Junior‑Mid** | Symmetric "non‑repudiation", dev‑token, fail‑open, client‑trust flags |
| Domain/methodology integrity | **Mid** | Credits on assumed constants + dangerous defaults |

### Verdict
> **Mid‑level engineer with senior‑level architectural reach, working with heavy AI assistance.** Capable of designing systems most seniors would respect — and of shipping security primitives a security senior would block in review. The gap between the *ambition* of the design and the *rigor* of the trust model is the defining characteristic of this codebase.

- If a human wrote all of this unaided: **strong senior, B+.**
- Given the agent‑generated fingerprint and the fail‑open/symmetric‑key gaps: **B**, and **not yet safe to mint real carbon credits.**

You can clearly build sophisticated software. The next level is building software that's still safe when an attacker — not a happy‑path demo — is holding it.

---

*Generated from a full read of `lib/`, `backend/`, `lca_engine.py`, `tables.dart`, and the test suite. Backend snippets are syntax‑oriented and compile‑checkable; Dart snippets are reviewed but uncompiled (no Flutter SDK in the review environment) — validate locally with `flutter analyze` and `flutter test`.*
