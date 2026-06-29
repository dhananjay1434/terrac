# TerraCipher dMRV — Detailed Remediation & Refactor Runbook (copy‑paste grade)

**Read this first.** This document is written so that an agent with **no prior knowledge** of the codebase can fix it completely by following instructions top to bottom. Every phase gives you: the exact files, the exact lines that are wrong, the **full replacement code** (not snippets), the exact commands to run, and the exact pass/fail criteria. Do not improvise. Do not skip gates. Do not reorder.

**Repository layout you will be working in**

```
<repo>/
├── lib/                         # Flutter client (Dart)
│   ├── main.dart
│   ├── services/
│   │   ├── crypto_signer.dart
│   │   ├── device_integrity_service.dart
│   │   ├── sync_queue_manager.dart
│   │   └── secure_capture_service.dart
│   └── data/local/
│       ├── app_database.dart
│       ├── tables.dart
│       └── proof_queries.dart
├── test/                        # Dart tests (49 files)
├── backend/
│   ├── server.py
│   ├── models.py
│   ├── lca_engine.py
│   ├── db.py
│   ├── alembic/versions/
│   └── tests/                   # pytest suite
└── pubspec.yaml
```

---

## 0. Global rules (binding for every phase)

1. **One phase, one commit.** Use the commit message printed in the phase. Never combine phases.
2. **Scope is a fence.** Touch only the files listed under "Files in scope." If a fix seems to need an out‑of‑scope file, **stop** (see §Stop conditions) — do not widen the blast radius silently.
3. **Run the formatter at the end of every phase.** Dart: `dart format lib test`. Python: `ruff format backend`. This makes diffs deterministic.
4. **`[FIX]` vs `[REFACTOR]`.** `[REFACTOR]` must not change behavior — the existing tests must pass unchanged. `[FIX]` changes behavior — you must add/adjust tests in the same phase.
5. **A gate is a command list.** It passes only when every command exits `0` and every assertion is literally true. Paste the output into `REMEDIATION_LOG.md`.
6. **Secrets only from env. Never a default for a secret.** No hardcoded keys, tokens, URLs.
7. **The canonical signing string is sacred.** Once defined (Phase 4/5) it must be byte‑identical on client and server forever. Never reformat it.

Create these two tracking files now (Phase 0 writes into them):

- `REMEDIATION_LOG.md` — your running record of gate output.
- `FINDINGS_BACKLOG.md` — anything you notice but must NOT fix now.

---

## Phase 0 — Baseline & safety net `[REFACTOR]`

**Goal:** know the exact starting state so "no new failures" is meaningful later.

**Commands**
```bash
git checkout -b remediation/phase-by-phase

# Backend
cd backend
pip install -r requirements.txt
pytest -q | tee ../.baseline_backend.txt
cd ..

# Client
flutter pub get
dart run build_runner build --delete-conflicting-outputs
flutter analyze | tee .baseline_analyze.txt
flutter test | tee .baseline_client.txt
```

**Write to `REMEDIATION_LOG.md`:**
```
## Baseline (<date>)
Backend pytest: <N passed, M failed, K skipped>
Client flutter test: <N passed, M failed, K skipped>
flutter analyze: <X issues>
Known pre-existing failures (excluded from later gates):
- <test name> — <reason>
```

**Gate:** both suites run to completion; baseline counts recorded; pre‑existing failures listed explicitly.

**Commit:** `chore: capture test baseline before remediation`

---

## Phase 1 — Backend import & structure hygiene `[REFACTOR]`

**Files in scope:** `backend/server.py`

**What's wrong (confirm each with grep before editing):**
- In‑function imports scattered through `create_batch`, `upload_media`, `create_application` (`import json`, `import base64`, `import re`, `import uuid`, `from math import ...`). `import json` appears **twice** inside `create_batch`.
- `from models import EnrollmentToken` sits mid‑file (~line 211) instead of at the top.
- `haversine` is defined **inline twice** (inside `create_batch` and inside `create_application`).

**Exact fix**

1. At the very top of `server.py`, immediately after the module docstring, make the import block read **exactly**:
```python
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Optional, Literal

from dotenv import load_dotenv
from fastapi import (
    Depends, FastAPI, File, Header, HTTPException, Request, Response,
    UploadFile, status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session, init_db
from lca_engine import calculate_carbon_credit, sign_lca_audit, CORG_TABLE
from models import (
    Batch, MediaFile, DeviceKey, EnrollmentToken,
    PyrolysisTelemetry, YieldMetrics, EndUseApplication, SystemMetadata,
)

load_dotenv()
```

2. Delete every `import ...` / `from ... import ...` line that now lives **inside** a function body. Delete the mid‑file `from models import EnrollmentToken`.

3. Add **one** module‑level haversine, placed just after the import block:
```python
def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in kilometres."""
    lon1, lat1, lon2, lat2 = map(radians, (lon1, lat1, lon2, lat2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(a))
```
Replace both inline `def haversine(...)` blocks and rewrite their call sites to `haversine_km(...)`. **Preserve the original argument order** at each call site (the original called `haversine(lon, lat, lon, lat)`).

4. `ruff format backend/server.py`

**Gate**
```bash
python -m py_compile backend/server.py        # exit 0
grep -n "^import json" backend/server.py       # exactly one line, near top
grep -nc "    import " backend/server.py        # 0  (no indented imports)
grep -nc "def haversine(" backend/server.py     # 0
grep -nc "def haversine_km(" backend/server.py  # 1
cd backend && pytest -q ; cd ..                 # no new failures vs baseline
```

**Commit:** `refactor(backend): hoist imports and extract single haversine_km`

---

## Phase 2 — Dedicated admin secret `[FIX]`

**Files in scope:** `backend/server.py`, `backend/.env.example`, `backend/tests/test_admin_secret.py` (new)

**What's wrong:** `mint_enrollment_token` authenticates admins with `hmac.compare_digest(x_admin_secret, _HMAC_SECRET)` — the HMAC pepper doubles as the admin password.

**Exact fix**

1. Below the existing `_HMAC_SECRET` block, add:
```python
_ADMIN_SECRET = os.environ.get("DMRV_ADMIN_SECRET")
if not _ADMIN_SECRET:
    raise RuntimeError("DMRV_ADMIN_SECRET env var is required.")
```

2. In `mint_enrollment_token`, change the comparison to:
```python
if not hmac.compare_digest(x_admin_secret, _ADMIN_SECRET):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
```

3. Add to `backend/.env.example` (empty placeholder, no value):
```
DMRV_ADMIN_SECRET=
```

4. Create `backend/tests/test_admin_secret.py`:
```python
import os
import pytest
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_mint_requires_admin_secret(monkeypatch):
    monkeypatch.setenv("DMRV_HMAC_SECRET", "pepper-value")
    monkeypatch.setenv("DMRV_ADMIN_SECRET", "admin-value")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    import importlib, server
    importlib.reload(server)
    transport = ASGITransport(app=server.app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        # HMAC pepper must NOT work as admin auth
        r = await c.post("/api/v1/admin/mint-token",
                         headers={"X-Admin-Secret": "pepper-value"},
                         json={"token": "tok1", "expires_in_days": 7})
        assert r.status_code == 401
        # Correct admin secret works
        r = await c.post("/api/v1/admin/mint-token",
                         headers={"X-Admin-Secret": "admin-value"},
                         json={"token": "tok2", "expires_in_days": 7})
        assert r.status_code == 201
```
(If the suite already has fixtures/conftest for the app + in‑memory DB, reuse them instead of the reload trick — match the existing test style.)

**Gate**
```bash
cd backend
DMRV_HMAC_SECRET=x DMRV_ADMIN_SECRET=y python -c "import server"   # imports OK
pytest -q tests/test_admin_secret.py                               # passes
pytest -q                                                          # no new failures
cd ..
```

**Commit:** `fix(backend): use a dedicated DMRV_ADMIN_SECRET for admin auth`

---

## Phase 3 — Remove the `dev-token` backdoor `[FIX]`

**Files in scope:** `backend/server.py` (`register_device`), `lib/services/crypto_signer.dart` (registration only), `backend/tests/test_enrollment.py` (new)

**What's wrong:**
- Server: `if db_token.token != "dev-token": db_token.used_at = ...` — `dev-token` is never consumed and never expires.
- Client: `ENROLLMENT_TOKEN` defaults to `'dev-token'`.

**Exact fix**

1. In `register_device`, replace the special‑case with an unconditional consume:
```python
    db_token.used_at = datetime.now(timezone.utc)
    await session.commit()
```

2. In `crypto_signer.dart` `registerDevice()`, replace the token line:
```dart
const enrollmentToken = String.fromEnvironment('ENROLLMENT_TOKEN');
if (enrollmentToken.isEmpty) {
  throw StateError('ENROLLMENT_TOKEN is required; pass via --dart-define-from-file=secrets.json.');
}
```

3. Create `backend/tests/test_enrollment.py` covering: a freshly minted token enrolls a device once (`201`), and reusing the same token returns `401` (`enrollment_token_used`). Use the existing conftest app/DB fixtures.

**Gate**
```bash
grep -c '"dev-token"' backend/server.py        # 0
grep -c "dev-token" lib/services/crypto_signer.dart   # 0
cd backend && pytest -q tests/test_enrollment.py && pytest -q ; cd ..   # passes, no new failures
flutter test                                    # no new failures
```

**Commit:** `fix: remove dev-token enrollment backdoor; require minted single-use tokens`

---

## Phase 4 — Client Ed25519 device identity `[FIX]`

**Files in scope:** `pubspec.yaml`, `lib/services/crypto_signer.dart`, callers in `lib/services/sync_queue_manager.dart` and `lib/data/local/app_database.dart`, `test/services/crypto_signer_test.dart` (rewrite)

**What's wrong:** the client generates a 32‑byte symmetric secret and uploads it to the server. Shared secret ⇒ server can forge signatures ⇒ zero non‑repudiation.

**Exact fix**

1. `flutter pub add cryptography` then `flutter pub get`.

2. Replace the body of `lib/services/crypto_signer.dart` with the following. Keep the class name `CryptoSigner` so existing imports keep working, but switch the internals to Ed25519. The canonical string format is frozen here and reused verbatim by the server in Phase 5.

```dart
import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:cryptography/cryptography.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:uuid/uuid.dart';
import 'package:http/http.dart' as http;
import 'device_integrity_service.dart';

/// Ed25519 device identity. The PRIVATE seed never leaves the device;
/// only the PUBLIC key is enrolled with the server. This restores true
/// non-repudiation — the server cannot forge a client signature.
class CryptoSigner {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );
  static const _seedKey = 'ed25519_seed';
  static const _deviceIdKey = 'device_id_key';
  static final _algo = Ed25519();

  static SimpleKeyPair? _pair;
  static String? _deviceId;

  static Future<SimpleKeyPair> _keyPair() async {
    if (_pair != null) return _pair!;
    final stored = await _storage.read(key: _seedKey);
    if (stored != null) {
      _pair = await _algo.newKeyPairFromSeed(base64Url.decode(_pad(stored)));
      return _pair!;
    }
    final pair = await _algo.newKeyPair();
    final seed = await pair.extractPrivateKeyBytes();
    await _storage.write(key: _seedKey, value: base64Url.encode(seed).replaceAll('=', ''));
    _pair = pair;
    return pair;
  }

  static String _pad(String s) {
    while (s.length % 4 != 0) { s += '='; }
    return s;
  }

  static Future<String> getDeviceId() async {
    if (_deviceId != null) return _deviceId!;
    final existing = await _storage.read(key: _deviceIdKey);
    if (existing != null) { _deviceId = existing; return existing; }
    final id = const Uuid().v4();
    await _storage.write(key: _deviceIdKey, value: id);
    _deviceId = id;
    return id;
  }

  static Future<String> publicKeyB64() async {
    final pub = await (await _keyPair()).extractPublicKey();
    return base64Url.encode(pub.bytes).replaceAll('=', '');
  }

  static Future<void> warmUp() async {
    await _keyPair();
    await getDeviceId();
    await registerDevice();
  }

  static Future<void> registerDevice() async {
    final deviceId = await getDeviceId();
    final publicKey = await publicKeyB64();
    const enrollmentToken = String.fromEnvironment('ENROLLMENT_TOKEN');
    if (enrollmentToken.isEmpty) {
      throw StateError('ENROLLMENT_TOKEN is required; pass via --dart-define-from-file=secrets.json.');
    }
    const apiBaseUrl = String.fromEnvironment('DMRV_API_BASE_URL');
    if (apiBaseUrl.isEmpty) {
      throw StateError('DMRV_API_BASE_URL is required.');
    }
    final response = await http.post(
      Uri.parse('$apiBaseUrl/api/v1/register'),
      headers: {'Content-Type': 'application/json', 'X-Enrollment-Token': enrollmentToken},
      body: jsonEncode({'device_id': deviceId, 'public_key': publicKey}),
    );
    if (response.statusCode != 201 && response.statusCode != 409) {
      throw StateError('Device registration failed: ${response.statusCode} ${response.body}');
    }
  }

  /// CANONICAL STRING (frozen): method\npath\nidempotencyKey\nsha256(jsonBody)\ndeviceId
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
    return base64Url.encode(sig.bytes).replaceAll('=', '');
  }

  /// Local-only tamper-evidence for the outbox row. NOT sent to the server as proof.
  static Future<String> signPayload(String jsonPayload) async {
    if (isDeviceCompromisedGlobally) throw StateError('device_compromised');
    final sig = await _algo.sign(utf8.encode(jsonPayload), keyPair: await _keyPair());
    return base64Url.encode(sig.bytes).replaceAll('=', '');
  }

  static Future<void> clear() async {
    _pair = null; _deviceId = null;
    await _storage.delete(key: _seedKey);
    await _storage.delete(key: _deviceIdKey);
  }

  @visibleForTesting
  static void resetForTest() { _pair = null; _deviceId = null; }
  static Future<void> resetKeyForTesting() => clear();
}
```

3. Update callers if any referenced removed members (`_resolveKey`, `hmac_key`). The public API used by `sync_queue_manager.dart` (`getDeviceId`, `signRequest`) and `app_database.dart` (`signPayload`) is preserved, so changes should be minimal.

4. Rewrite `test/services/crypto_signer_test.dart` to assert: signing is deterministic for a fixed seed; signature changes when any canonical component changes; a public‑key `verify` of a tampered body fails. (The previous test asserted a 64‑char hex HMAC — that assertion is now wrong and must be replaced.)

**Gate**
```bash
grep -rc "hmac_key" lib/services/crypto_signer.dart   # 0
flutter analyze                                         # clean
flutter test test/services/crypto_signer_test.dart      # passes
flutter test                                            # no new failures
```

**Commit:** `fix(client): replace symmetric HMAC identity with Ed25519 device signatures`

---

## Phase 5 — Server Ed25519 verification + column migration `[FIX]`

**Files in scope:** `backend/models.py`, `backend/server.py`, `backend/alembic/versions/<new>.py`, `backend/tests/test_signature.py` (new)

**What's wrong:** server stores and verifies a shared symmetric key.

**Exact fix**

1. `models.py` — rename the column on `DeviceKey`:
```python
class DeviceKey(Base):
    __tablename__ = "device_keys"
    device_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    public_key: Mapped[str] = mapped_column(String(64), nullable=False)  # base64url Ed25519
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
```

2. New Alembic migration (`alembic revision -m "device_keys hmac_key to public_key"`), body:
```python
def upgrade():
    op.alter_column("device_keys", "hmac_key", new_column_name="public_key")

def downgrade():
    op.alter_column("device_keys", "public_key", new_column_name="hmac_key")
```

3. `server.py` — add a base64url helper and the new verifier; delete the old `verify_hmac`:
```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

async def verify_signature(
    request: Request,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> str:
    if not x_signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_signature")
    if not x_device_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="unknown_device")
    device = (await session.execute(
        select(DeviceKey).where(DeviceKey.device_id == x_device_id))).scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="unknown_device")
    pub = Ed25519PublicKey.from_public_bytes(_b64url_decode(device.public_key))
    body_hash = hashlib.sha256(await request.body()).hexdigest()
    canonical = "\n".join([
        request.method.upper(), request.url.path,
        x_idempotency_key or "", body_hash, x_device_id,
    ]).encode("utf-8")
    try:
        pub.verify(_b64url_decode(x_signature), canonical)
    except InvalidSignature:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="signature_mismatch")
    return x_device_id
```

4. Update the client header name in Phase 4's `signRequest` usage (sync_queue_manager) to send `X-Signature` (not `X-HMAC-Signature`). The canonical string is already identical — confirm byte‑for‑byte.

5. `register_device`: `RegistrationRequest.hmac_key` → `public_key` (40–64 chars), store `DeviceKey(device_id=..., public_key=payload.public_key)`.

6. Replace every `Depends(verify_hmac)` with `Depends(verify_signature)`.

7. `backend/tests/test_signature.py`: generate an Ed25519 private key, register its public key, sign a request, assert `200/201`; sign with a different key, assert `403 signature_mismatch`. Assert no server code path can produce a valid signature from only `public_key`.

**Gate (cross‑stack proof)**
```bash
grep -nc "verify_hmac" backend/server.py         # 0
grep -nc "hmac_key" backend/server.py backend/models.py   # 0
cd backend
alembic upgrade head && alembic downgrade -1 && alembic upgrade head   # clean up/down
pytest -q tests/test_signature.py && pytest -q   # passes, no new failures
cd ..
```

**Commit:** `fix(backend): verify Ed25519 device signatures; migrate device_keys to public_key`

---

## Phase 6 — Fail closed on integrity & registration `[FIX]`

**Files in scope:** `lib/services/device_integrity_service.dart`, `test/device_integrity_test.dart` (extend)

**What's wrong:** integrity is bypassed whenever `kDebugMode || DMRV_DEMO_MODE` with no release guard; cert config defaults to `''`; Talsec start failure is swallowed.

**Exact fix** — replace `initialize()` with:
```dart
Future<void> initialize() async {
  if (kIsWeb) return;
  final demo = const bool.fromEnvironment('DMRV_DEMO_MODE');
  if (demo && kReleaseMode) {
    throw StateError('DMRV_DEMO_MODE is forbidden in release builds.');
  }
  if (demo || kDebugMode) {
    debugPrint('[DeviceIntegrity] demo/debug build — integrity checks skipped.');
    return;
  }
  const certHash = String.fromEnvironment('TALSEC_SIGNING_CERT_HASH');
  const iosTeam = String.fromEnvironment('TALSEC_IOS_TEAM_ID');
  if (certHash.isEmpty || iosTeam.isEmpty) {
    _compromised('Integrity configuration missing');
    return;
  }
  final config = TalsecConfig(
    androidConfig: AndroidConfig(packageName: 'com.kontiki.dmrv', signingCertHashes: [certHash]),
    iosConfig: IOSConfig(bundleIds: ['com.kontiki.dmrv'], teamId: iosTeam),
    watcherMail: 'security@kontiki.test',
    isProd: true,
  );
  // attach the existing ThreatCallback here (unchanged) ...
  Talsec.instance.attachListener(callback);
  try {
    await Talsec.instance.start(config);
  } catch (e) {
    _compromised('Talsec failed to start: $e');
  }
}
```

**Gate**
```bash
grep -n "forbidden in release builds" lib/services/device_integrity_service.dart   # present
flutter analyze && flutter test test/device_integrity_test.dart && flutter test    # green, no new failures
```

**Commit:** `fix(client): fail closed on integrity bypass, missing config, and registration errors`

---

## Phase 7 — Require credit‑bearing inputs `[FIX]`

**Files in scope:** `backend/server.py` (`BatchPayload`), affected fixtures in `backend/tests/`

**What's wrong:** `wet_yield_kg=100.0`, `min_recorded_temp_c=0.0`, `transport_distance_km=0.0` defaults fabricate credits when omitted.

**Exact fix**
```python
wet_yield_kg: float = Field(..., gt=0.0, description="BLE crane scale reading")
min_recorded_temp_c: float = Field(..., ge=-50.0, le=1500.0)
transport_distance_km: float = Field(..., ge=0.0, le=20000.0)
```
Add a test: payload missing `wet_yield_kg` → `422`. Update any fixtures that relied on defaults and list them in `REMEDIATION_LOG.md`.

**Gate**
```bash
grep -n "wet_yield_kg: float = Field(\.\.\." backend/server.py   # present (required)
cd backend && pytest -q ; cd ..   # no new failures beyond intentionally updated fixtures
```

**Commit:** `fix(backend): make wet_yield_kg, min_temp, transport_distance required`

---

## Phase 8 — LCA: measured permanence or PROVISIONAL `[FIX]`

**Files in scope:** `backend/lca_engine.py`, `backend/server.py` (`create_batch`), `backend/models.py` (+ migration), `backend/tests/test_lca_provisional.py` (new)

**What's wrong:** `h_corg_ratio` defaults to 0.35, `lab_h_corg` usually absent ⇒ credits computed on an assumption. `gross_c_sink_t_co2e` is dead.

**Exact fix**
1. `step3_cremain(dry_mass_t, corg_pct, *, h_corg_ratio, t=100)` — required keyword; raise `ValueError("h_corg_ratio is required")` if `None`.
2. `calculate_carbon_credit(..., h_corg_ratio: float | None = None)`:
   - `provisional = h_corg_ratio is None`
   - use `0.35` when provisional (conservative), real value otherwise
   - set `audit.provisional = provisional`
3. Add `provisional: bool = True` to `LCAAudit`; label `gross_c_sink_t_co2e` docstring "informational only — not used in issuance."
4. `create_batch`: if `audit.provisional`, set `status="PROVISIONAL"` and do not present `net_credit_t_co2e` as final/issuable.
5. Migration: add `provisional` handling if a column is needed; otherwise derive from `status`.
6. Test: no `lab_h_corg` → `status=="PROVISIONAL"`; with `lab_h_corg` → not provisional; `step3_cremain` without ratio raises; identical inputs → byte‑identical `lca_audit_json` (`json.dumps(..., sort_keys=True)`).

**Gate**
```bash
cd backend && pytest -q tests/test_lca_provisional.py && pytest -q ; cd ..
```

**Commit:** `fix(lca): require measured H:Corg or mark batch PROVISIONAL; never issue on assumptions`

---

## Phase 9 — Server‑side GPS corroboration (drop client mock header) `[FIX]`

**Files in scope:** `backend/server.py` (`upload_media`, `create_batch`), `backend/models.py` (+ migration), `backend/requirements.txt`, `backend/tests/test_gps_corroboration.py` (new)

**What's wrong:** `if request.headers.get("x-mock-location") == "true": 403` is an honor‑system control.

**Exact fix**
1. Remove the `X-Mock-Location` rejection from `upload_media`.
2. `pip install piexif` and freeze (`pip freeze > backend/requirements.txt`). Parse EXIF GPS from the uploaded bytes; store `exif_lat`, `exif_lon` (nullable Float) on `MediaFile` (+ migration).
3. In `create_batch`, after the media is anchored: if payload GPS and media EXIF GPS both exist and `haversine_km(...) > 1.0`, set `status="QUARANTINE_GPS_MISMATCH"`.
4. Keep `mock_location_enabled` only as a stored review signal. Keep the teleport check.
5. Test: EXIF vs payload disagree >1 km → quarantine; agree → pass; `X-Mock-Location` header has no effect.

**Gate**
```bash
grep -c "x-mock-location" backend/server.py   # 0
cd backend && pytest -q tests/test_gps_corroboration.py && pytest -q ; cd ..
```

**Commit:** `fix(backend): drop client mock-GPS header; corroborate GPS against media EXIF`

---

## Phase 10 — Background sync awaits real completion `[FIX]`

**Files in scope:** `lib/services/sync_queue_manager.dart`, `test/background_sync_test.dart` (extend)

**What's wrong:** `callbackDispatcher` fires `kickSync()` un‑awaited, sleeps 10 s, returns `true`; `ProviderContainer` leaks.

**Exact fix**
```dart
Future<void> kickSync() => _triggerSync();   // _triggerSync is Future<void>

@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    final container = ProviderContainer();
    try {
      await container.read(syncQueueManagerProvider).kickSync();
      return true;
    } catch (e) {
      debugPrint('Background sync failed: $e');
      return false;
    } finally {
      container.dispose();
    }
  });
}
```
Remove the `Future.delayed(const Duration(seconds: 10))`.

**Gate**
```bash
grep -c "Future.delayed(const Duration(seconds: 10))" lib/services/sync_queue_manager.dart   # 0
flutter test test/background_sync_test.dart && flutter test   # green
```

**Commit:** `fix(client): await sync completion in WorkManager task; dispose container`

---

## Phase 11 — Strict schemas on loose endpoints `[FIX]`

**Files in scope:** `backend/server.py` (`/telemetry`, `/yield`, `/metadata`, `/application`), `backend/tests/test_endpoint_schemas.py` (new)

**What's wrong:** these accept raw `payload: dict`, no schema, no size limit; `is_verified: bool = Depends(verify_signature)` is mistyped.

**Exact fix**
1. Define `TelemetryPayload`, `YieldPayload`, `MetadataPayload`, `ApplicationPayload` (`model_config = ConfigDict(extra="forbid")`) with the exact persisted fields. Bound arrays with `Field(..., max_length=100_000)`.
2. Replace `payload: dict` with the typed models; `json.dumps(payload.model_dump())` when persisting.
3. Change the dependency param to `device_id: str = Depends(verify_signature)`.
4. Test: unknown extra field → `422`; oversized array → `422`; valid payload persists.

**Gate**
```bash
grep -c "payload: dict" backend/server.py   # 0
cd backend && pytest -q tests/test_endpoint_schemas.py && pytest -q ; cd ..
```

**Commit:** `fix(backend): add strict schemas and size bounds to telemetry/yield/metadata/application`

---

## Phase 12 — Remove unsafe test code from prod surface `[REFACTOR]`

**Files in scope:** `lib/data/local/app_database.dart`, callers in `test/`

**Exact fix:** annotate `getBatchTelemetryUnsafe` with `@visibleForTesting` and rename to `getBatchTelemetryRaw`; update test callers.

**Gate**
```bash
grep -c "getBatchTelemetryUnsafe" lib/   # 0
flutter analyze && flutter test          # green
```

**Commit:** `refactor(client): gate raw telemetry query behind @visibleForTesting`

---

## Phase 13 — Correct claims & residual doc rot `[REFACTOR]`

**Files in scope:** `lib/main.dart`, `lib/services/secure_capture_service.dart`, `lib/data/local/tables.dart` (header), `lib/data/local/proof_queries.dart`

**Exact fix**
1. `main.dart`: reword "Truth Machine … can never cause double‑counted carbon credits" → "Append‑only outbox with idempotency keys minimizes double‑counting under intermittent connectivity."
2. `secure_capture_service.dart`: reword "indelible digital fingerprint" → "SHA‑256 anchors the on‑disk file bytes for transit tamper‑evidence; scene authenticity is corroborated server‑side via EXIF GPS (see backend Phase 9)."
3. `tables.dart` header: change "v4" to the real `schemaVersion` and list columns added since v4.
4. `proof_queries.dart:89`: replace `catch (_) {}` with a logged handler or a one‑line comment justifying the ignore.

**Gate**
```bash
grep -rc "indelible" lib/                                  # reworded
grep -n "catch (_) {}" lib/data/local/proof_queries.dart   # no empty body
flutter analyze && flutter test                            # green
```

**Commit:** `docs(client): correct integrity-vs-authenticity claims and schema header`

---

## Phase 14 — Full regression & sign‑off `[REFACTOR]`

**Commands**
```bash
ruff format --check backend && (cd backend && pytest -q | tee ../.final_backend.txt)
dart format --output=none --set-exit-if-changed lib test
flutter analyze
flutter test | tee .final_client.txt
cd backend && alembic upgrade head && alembic downgrade base && alembic upgrade head ; cd ..
```

**Write `## Final` to `REMEDIATION_LOG.md`** comparing baseline vs final counts.

**Release sign‑off (all must hold):**
- Ed25519 only; no `hmac_key` in identity/request code; no server path forges signatures.
- No `dev-token`, no `payload: dict`, no `x-mock-location` control, no `Future.delayed(10s)` sync, no fabricating defaults on credit fields.
- Integrity & registration fail closed.
- Both suites green vs baseline; formatters report no diffs; Alembic up/down clean.

**Commit:** `chore: full regression green; remediation complete`

---

## Appendix A — Dependency graph (no cycles)
```
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14
                  └ 4 & 5 land back-to-back; cross-stack gate is in 5
```

## Appendix B — Determinism rules
- Format at the end of every phase.
- Signed/audited JSON uses `sort_keys=True` (Py) / fixed key order (Dart).
- The canonical signing string is defined once (Phase 4) and reused byte‑identically server‑side (Phase 5).
- Deterministic functions get exact‑value assertions, never ranges.
- Migrations are explicit and reversible; never rely on `create_all`.

## Appendix C — Stop conditions (halt and report)
- A gate cannot go green without editing out‑of‑scope files.
- A required secret/credential is absent from the environment.
- An Alembic migration will not downgrade cleanly.
- The Phase‑5 cross‑stack signature test fails (canonical strings disagree) — align both sides; never patch only one side.

## Appendix D — Env vars you must provide
| Var | Where | Required | Notes |
|---|---|---|---|
| `DMRV_HMAC_SECRET` | backend | yes | LCA audit signing pepper |
| `DMRV_ADMIN_SECRET` | backend | yes (Phase 2) | admin auth, distinct from pepper |
| `DATABASE_URL` | backend | yes | async SQLAlchemy URL |
| `DMRV_ALLOWED_ORIGIN` | backend | optional | CORS origin |
| `ENROLLMENT_TOKEN` | client `--dart-define` | yes (Phase 3/4) | single‑use minted token, no default |
| `DMRV_API_BASE_URL` | client `--dart-define` | yes | no default |
| `DMRV_PINNED_CERT_PEM` | client `--dart-define` | release only | cert pinning |
| `TALSEC_SIGNING_CERT_HASH` | client `--dart-define` | release only (Phase 6) | integrity config |
| `TALSEC_IOS_TEAM_ID` | client `--dart-define` | release only (Phase 6) | integrity config |
