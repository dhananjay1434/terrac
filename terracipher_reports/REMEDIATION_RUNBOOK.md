# TerraCipher dMRV — Remediation & Refactor Runbook

**Audience:** an autonomous AI coding agent.
**Codebase:** Flutter/Dart client (`lib/`, `test/`) + FastAPI/SQLAlchemy backend (`backend/`).
**Purpose:** fix the security, correctness, and hygiene defects identified in review, in a fixed order, with a verification gate between every phase.

This is not a wish list. It is a sequenced procedure. Execute phases in order. Do not start a phase until the previous phase's gate is **green**. Do not bundle changes across phases. If a gate fails, stop and resolve the failure inside that phase — never carry a red gate forward.

---

## Working agreement (read once, obey throughout)

1. **One phase = one commit.** Each phase below specifies its exact commit message. Use it verbatim. No phase touches files outside its declared scope.
2. **No opportunistic edits.** If you notice an unrelated defect, record it in `FINDINGS_BACKLOG.md` and keep moving. Do not fix it now.
3. **Deterministic formatting.** After editing, run the formatter for the language you touched (`dart format` for Dart, `ruff format` for Python). This guarantees the same input produces the same diff every time.
4. **Behavior‑preserving vs behavior‑changing.** Each phase is labelled `[REFACTOR]` (no observable behavior change — tests must pass unchanged) or `[FIX]` (behavior changes — tests are added or updated as part of the phase). Treat the labels as contracts.
5. **Gates are commands, not opinions.** A gate passes only when every listed command exits `0` and every listed assertion holds. Paste the command output into the phase's completion note.
6. **No mocks for the thing under test.** When a phase adds a security control, the verification test must exercise the real control path, not a stub.
7. **Secrets come from the environment.** Never hardcode a key, token, or URL. Never add a default value to a secret.

If any instruction here conflicts with code you find, the code is wrong — follow the runbook.

---

## Phase 0 — Establish a green baseline and a safety net

**Label:** `[REFACTOR]` (no source changes)
**Why first:** every later gate is "tests still pass." That assertion is meaningless until you know the current pass/fail state and have captured it.

**Steps**
1. Create a working branch: `git checkout -b remediation/phase-by-phase`.
2. Backend baseline:
   - `cd backend && pip install -r requirements.txt`
   - `pytest -q | tee ../.baseline_backend.txt`
3. Client baseline:
   - `flutter pub get`
   - `dart run build_runner build --delete-conflicting-outputs`
   - `flutter analyze | tee .baseline_analyze.txt`
   - `flutter test | tee .baseline_client.txt`
4. Record the **exact** counts (passed / failed / skipped) for both suites in a new file `REMEDIATION_LOG.md` under a heading `## Baseline`. If a test is already failing on `main`, list it explicitly as a **known pre‑existing failure** — it is excluded from every later "no new failures" gate.

**Gate**
- Both suites run to completion (a non‑zero failure count is acceptable here as long as it is *recorded*).
- `REMEDIATION_LOG.md` contains the baseline counts and the known‑failure list.

**Commit:** `chore: capture test baseline before remediation`

---

## Phase 1 — Backend import & structure hygiene

**Label:** `[REFACTOR]`
**Scope:** `backend/server.py` only.
**Why now:** later phases edit `server.py` logic. Cleaning structure first keeps those diffs small and reviewable. This phase changes **zero** behavior.

**What's wrong (verify each before changing):**
- Imports scattered inside functions: `import json`, `import base64`, `import re`, `import uuid`, `from math import ...`. `import json` appears twice inside `create_batch`. `from models import EnrollmentToken` sits mid‑module (~line 211).
- `haversine` is defined inline twice (inside `create_batch` and inside `create_application`).

**Fix**
1. Hoist every import to the top of the module, grouped stdlib → third‑party → local. Remove all in‑function `import` statements. The consolidated `from models import (...)` must include `EnrollmentToken`.
2. Define one module‑level function:
   ```python
   def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
       lon1, lat1, lon2, lat2 = map(radians, (lon1, lat1, lon2, lat2))
       a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
       return 6371.0 * 2 * asin(sqrt(a))
   ```
   Replace both inline definitions and their call sites with `haversine_km(...)`. Preserve argument order exactly as the originals used them.
3. `ruff format backend/server.py`.

**Gate**
- `python -m py_compile backend/server.py` exits 0.
- `grep -n "import json" backend/server.py` returns exactly one line, at the top.
- `grep -nc "def haversine" backend/server.py` returns `0` (the inline defs are gone) and `grep -n "def haversine_km" backend/server.py` returns exactly one line.
- `pytest -q` shows **no new failures** vs Phase 0 baseline.

**Commit:** `refactor(backend): hoist imports and extract single haversine_km`

---

## Phase 2 — Separate the admin secret from the HMAC pepper

**Label:** `[FIX]`
**Scope:** `backend/server.py`, `backend/.env(.example)`.
**Why now:** isolated, tiny, and unblocks safe enrollment changes in later phases.

**What's wrong:** `mint_enrollment_token` authenticates admins with `hmac.compare_digest(x_admin_secret, _HMAC_SECRET)`. One secret serves two unrelated purposes.

**Fix**
1. Add a required env var read at module load, next to `_HMAC_SECRET`:
   ```python
   _ADMIN_SECRET = os.environ.get("DMRV_ADMIN_SECRET")
   if not _ADMIN_SECRET:
       raise RuntimeError("DMRV_ADMIN_SECRET env var is required.")
   ```
2. In `mint_enrollment_token`, compare against `_ADMIN_SECRET`.
3. Add `DMRV_ADMIN_SECRET=` to `.env.example` (empty placeholder, no value) and document it in `backend/README` if one exists.

**Gate**
- A test (new, in `backend/tests/test_admin_secret.py`) proves: minting with the correct `DMRV_ADMIN_SECRET` succeeds; minting with a value equal to `DMRV_HMAC_SECRET` (but not the admin secret) returns `401`.
- App refuses to start when `DMRV_ADMIN_SECRET` is unset (assert the `RuntimeError`).
- `pytest -q` — no new failures.

**Commit:** `fix(backend): use a dedicated DMRV_ADMIN_SECRET for admin auth`

---

## Phase 3 — Harden enrollment: remove the `dev-token` backdoor

**Label:** `[FIX]`
**Scope:** `backend/server.py` (`register_device`), `lib/services/crypto_signer.dart` (registration only).
**Why now:** independent of key material; closes the highest‑urgency exploit before the larger crypto change.

**What's wrong:**
- Server: `if db_token.token != "dev-token": db_token.used_at = ...` — `dev-token` is never consumed and never expires.
- Client: `ENROLLMENT_TOKEN` defaults to `'dev-token'`, so the backdoor ships in the binary.

**Fix**
1. Server: delete the conditional. Every successful enrollment marks the token used:
   ```python
   db_token.used_at = datetime.now(timezone.utc)
   ```
2. Client: remove the default. Fail closed if the define is absent:
   ```dart
   const enrollmentToken = String.fromEnvironment('ENROLLMENT_TOKEN');
   if (enrollmentToken.isEmpty) {
     throw StateError('ENROLLMENT_TOKEN is required; pass via --dart-define-from-file.');
   }
   ```
3. For local/dev usage, document that developers mint a real single‑use token via `POST /api/v1/admin/mint-token`. Do not reintroduce a magic string anywhere.

**Gate**
- New backend test: enrolling with a token whose `used_at` is already set returns `401`; a fresh token enrolls once and is rejected on reuse. The string `"dev-token"` no longer appears in `backend/server.py` (`grep -c '"dev-token"' backend/server.py` → `0`).
- `grep -c "dev-token" lib/services/crypto_signer.dart` → `0`.
- `flutter test` and `pytest -q` — no new failures.

**Commit:** `fix: remove dev-token enrollment backdoor; require minted single-use tokens`

---

## Phase 4 — Replace symmetric HMAC identity with Ed25519 (client)

**Label:** `[FIX]`
**Scope:** `pubspec.yaml`, `lib/services/crypto_signer.dart` (signing/identity), call sites in `lib/services/sync_queue_manager.dart` and `lib/data/local/app_database.dart`.
**Why now:** this is the trust‑model fix. Do the **client** half here; the server half is Phase 5. Between Phase 4 and 5 the system is intentionally inconsistent — that is why these two phases must land back‑to‑back and the integration gate lives in Phase 5.

**What's wrong:** the client generates a 32‑byte secret and uploads it to the server (`hmac_key`). Both sides holding the secret means the server can forge client signatures — no non‑repudiation.

**Fix**
1. `flutter pub add cryptography` (Ed25519 implementation). Run `flutter pub get`.
2. Rewrite the identity surface as a `DeviceSigner` that:
   - generates an Ed25519 keypair on first launch, persists **only the private seed** in `flutter_secure_storage` (Android Keystore / iOS Keychain), and caches the keypair in memory;
   - exposes `Future<String> publicKeyB64()` (base64url, no padding);
   - exposes `signRequest({method, path, idempotencyKey, deviceId, jsonBody})` returning a base64url Ed25519 signature over the canonical string `method\npath\nidempotencyKey\nsha256(jsonBody)\ndeviceId`;
   - throws if `isDeviceCompromisedGlobally` is true;
   - keeps `@visibleForTesting` reset hooks.
3. `registerDevice()` now sends `public_key` (not `hmac_key`). Keep the canonical‑string format **byte‑identical** to what the server will verify in Phase 5 — this is the contract; write it down as a comment in both languages.
4. Update every caller that referenced the old static `CryptoSigner` signing API.
5. Preserve the `signPayload` outbox‑integrity use (HMAC of the local row is acceptable for *local* tamper‑evidence) **only if** it is not presented to the server as proof. If it is sent to the server, migrate it to Ed25519 too. Document the decision in the file header.

**Gate**
- New unit tests: signing is deterministic for a fixed seed; signature changes when any canonical component changes; a tampered body fails verification using the public key (verify in‑test with the `cryptography` package).
- `grep -c "hmac_key" lib/` → `0` for the request/identity path (local‑only HMAC, if retained, is clearly named and documented).
- `flutter analyze` clean; `flutter test` — no new failures.

**Commit:** `fix(client): replace symmetric HMAC identity with Ed25519 device signatures`

---

## Phase 5 — Verify Ed25519 on the server; migrate the key column

**Label:** `[FIX]`
**Scope:** `backend/models.py`, `backend/alembic/versions/*` (new migration), `backend/server.py` (`verify_hmac` → `verify_signature`, `register_device`, `RegistrationRequest`).
**Why now:** completes the trust model started in Phase 4. The cross‑stack integration test lives here.

**What's wrong:** server stores and verifies with a shared symmetric key.

**Fix**
1. Model: rename `DeviceKey.hmac_key` → `public_key` (`String(64)` → size for base64url Ed25519 public key, 44 chars; use `String(64)` to be safe). Generate an Alembic migration that renames the column (do **not** `create_all`‑drift). `RegistrationRequest.hmac_key` → `public_key`.
2. Rewrite `verify_hmac` as `verify_signature`:
   ```python
   from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
   from cryptography.exceptions import InvalidSignature

   async def verify_signature(request, x_device_id, x_signature, x_idempotency_key, session) -> str:
       if not x_signature:
           raise HTTPException(401, "missing_signature")
       if not x_device_id:
           raise HTTPException(403, "unknown_device")
       device = (await session.execute(
           select(DeviceKey).where(DeviceKey.device_id == x_device_id))).scalar_one_or_none()
       if not device:
           raise HTTPException(403, "unknown_device")
       pub = Ed25519PublicKey.from_public_bytes(_b64url_decode(device.public_key))
       body_hash = hashlib.sha256(await request.body()).hexdigest()
       canonical = "\n".join([request.method.upper(), request.url.path,
                              x_idempotency_key or "", body_hash, x_device_id]).encode()
       try:
           pub.verify(_b64url_decode(x_signature), canonical)
       except InvalidSignature:
           raise HTTPException(403, "signature_mismatch")
       return x_device_id
   ```
   Read the signature header consistently (`X-Signature`); update the client header name in Phase 4's code to match — they must agree. The canonical string must be **byte‑identical** to the client's.
3. Update every `Depends(verify_hmac)` to `Depends(verify_signature)`.

**Gate (cross‑stack — this is the proof the trust model works):**
- New backend test signs a request with a generated Ed25519 private key, registers the matching public key, and asserts `200/201`; a request signed by a *different* key returns `403 signature_mismatch`.
- Negative test: a request where the server attempts to forge a signature using only the stored `public_key` **cannot** (there is no private key server‑side) — assert there is no code path that signs on behalf of a device.
- Alembic upgrade + downgrade run cleanly against a scratch DB.
- `pytest -q` — no new failures.

**Commit:** `fix(backend): verify Ed25519 device signatures; migrate device_keys to public_key`

---

## Phase 6 — Fail closed on device integrity and registration (client)

**Label:** `[FIX]`
**Scope:** `lib/services/device_integrity_service.dart`, `lib/services/crypto_signer.dart`/`DeviceSigner` (registration error path).
**Why now:** the identity is now real; integrity gating must stop failing open.

**What's wrong:**
- `initialize()` returns early (integrity off) whenever `kDebugMode || DMRV_DEMO_MODE`, with no guard against a release build carrying the demo flag.
- `signingCertHashes` / team id default to empty strings.
- Talsec start failure and registration HTTP failure are swallowed via `debugPrint`.

**Fix**
1. Refuse demo bypass in release builds:
   ```dart
   if (demo && kReleaseMode) {
     throw StateError('DMRV_DEMO_MODE is forbidden in release builds.');
   }
   if (demo || kDebugMode) { /* skip integrity, log, return (non-release only) */ return; }
   ```
2. Require integrity config; absence = compromised:
   ```dart
   if (certHash.isEmpty || iosTeamId.isEmpty) { _compromised('Integrity config missing'); return; }
   ```
3. Talsec start failure → `_compromised(...)`, not a benign log.
4. Registration: a non‑`201`/`409` response throws (do not let an unregistered device proceed).

**Gate**
- New tests (use the existing `device_integrity_*` test patterns): demo+release throws; missing cert config sets `deviceCompromisedProvider` true; a registration failure surfaces an error rather than completing silently.
- `grep -n "DMRV_DEMO_MODE" lib/services/device_integrity_service.dart` shows the release guard present.
- `flutter analyze` clean; `flutter test` — no new failures.

**Commit:** `fix(client): fail closed on integrity bypass, missing config, and registration errors`

---

## Phase 7 — Require credit‑bearing inputs (no fabricated batches)

**Label:** `[FIX]`
**Scope:** `backend/server.py` (`BatchPayload`).
**Why now:** independent backend change; precedes the LCA correctness work that consumes these fields.

**What's wrong:** `wet_yield_kg` defaults to `100.0`; `min_recorded_temp_c` and `transport_distance_km` default to `0.0`. A client omitting `wet_yield_kg` causes the engine to issue a credit for a fictional 100 kg batch.

**Fix**
```python
wet_yield_kg: float = Field(..., gt=0.0)
min_recorded_temp_c: float = Field(..., ge=-50.0, le=1500.0)
transport_distance_km: float = Field(..., ge=0.0, le=20000.0)
```
Keep all validators. Confirm the Flutter client already sends these (it does, via the outbox payload); if a field is missing client‑side, add it in this phase's client edit and note it.

**Gate**
- New test: a `BatchPayload` missing `wet_yield_kg` returns `422` (not a 100 kg credit).
- Existing valid‑payload tests still pass (update fixtures that relied on the defaults; record which fixtures changed in `REMEDIATION_LOG.md`).
- `pytest -q` — no new failures beyond intentionally updated fixtures.

**Commit:** `fix(backend): make wet_yield_kg, min_temp, transport_distance required`

---

## Phase 8 — LCA permanence must be measured, not assumed

**Label:** `[FIX]`
**Scope:** `backend/lca_engine.py`, `backend/server.py` (`create_batch` issuance path), `backend/models.py` (add `provisional` / status), Alembic migration.
**Why now:** depends on Phase 7's required inputs; defines what "issuable" means.

**What's wrong:** `step3_cremain` defaults `h_corg_ratio=0.35`; `lab_h_corg` is optional and usually absent, so the permanence factor is effectively a constant. Credits are computed on an assumption. Also `gross_c_sink_t_co2e` is computed and stored but never used in the net calculation.

**Fix**
1. `step3_cremain(..., *, h_corg_ratio)` — make the ratio a required keyword; raise `ValueError` if `None`.
2. `calculate_carbon_credit(..., h_corg_ratio: float | None = None)`:
   - if `None`, compute with the conservative `0.35` **but** set `audit.provisional = True`;
   - if provided, `provisional = False`.
3. Add `provisional: bool` to `LCAAudit`. Label `gross_c_sink_t_co2e` in the dataclass docstring as **informational only — not used in issuance**.
4. In `create_batch`: when the audit is provisional, persist `status="PROVISIONAL"` and treat `net_credit_t_co2e` as **not yet issuable** (do not surface it as a final credit). A later lab `lab_h_corg` recomputes and promotes the batch.

**Gate**
- New tests: provisional batch (no `lab_h_corg`) → `status == "PROVISIONAL"`, `audit.provisional is True`; supplying `lab_h_corg` → `provisional is False`. `step3_cremain` without a ratio raises `ValueError`.
- Determinism test: identical inputs produce a byte‑identical `lca_audit_json` (sorted keys) and identical `net_credit_t_co2e`.
- `pytest -q` — no new failures.

**Commit:** `fix(lca): require measured H:Corg or mark batch PROVISIONAL; never issue on assumptions`

---

## Phase 9 — Replace client‑asserted mock‑GPS with server‑side corroboration

**Label:** `[FIX]`
**Scope:** `backend/server.py` (`upload_media` EXIF parse, `create_batch` cross‑check), `backend/models.py` (store EXIF lat/lon on `MediaFile`), Alembic migration.
**Why now:** depends on the verified identity (Phase 5) and the issuance gating (Phase 8); it strengthens fraud detection without trusting the client.

**What's wrong:** `upload_media` rejects on the client‑sent `X-Mock-Location: true` header — an honor‑system control a fraudster simply sets to `false`.

**Fix**
1. Remove the `X-Mock-Location` rejection. Keep `mock_location_enabled` only as a **stored review signal**, never an access control.
2. On media upload, parse EXIF GPS server‑side (e.g. `piexif`/`exifread`) and persist `exif_lat`, `exif_lon` on `MediaFile`.
3. In `create_batch`, if both payload GPS and the anchored media EXIF GPS exist, compute `haversine_km` between them; if drift > 1.0 km, set `status="QUARANTINE_GPS_MISMATCH"` (do not issue).
4. Keep the existing `implausible_movement` teleport check; it stays.

**Gate**
- New tests: a media file whose EXIF GPS disagrees with the payload GPS by >1 km quarantines the batch; agreement passes; the `X-Mock-Location` header has **no** effect on the response (`grep -c "x-mock-location" backend/server.py` → `0`).
- `pytest -q` — no new failures.

**Commit:** `fix(backend): drop client mock-GPS header; corroborate GPS against media EXIF`

---

## Phase 10 — Make background sync await real completion

**Label:** `[FIX]`
**Scope:** `lib/services/sync_queue_manager.dart`.
**Why now:** client‑only, independent; finishes the reliability story.

**What's wrong:** `callbackDispatcher` calls `kickSync()` (fire‑and‑forget), sleeps 10 s, returns `true`. WorkManager's retry signal is meaningless, and the `ProviderContainer` is never disposed (leak).

**Fix**
```dart
Future<void> kickSync() => _triggerSync(); // _triggerSync is already Future<void>

@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    final container = ProviderContainer();
    try {
      await container.read(syncQueueManagerProvider).kickSync();
      return true;
    } catch (e) {
      debugPrint('Background sync failed: $e');
      return false; // let WorkManager apply its own backoff
    } finally {
      container.dispose();
    }
  });
}
```
Remove the `Future.delayed(10s)`.

**Gate**
- Update/extend `test/background_sync_test.dart`: the task completes only after the sync future resolves; a thrown sync returns `false`. Assert no `Future.delayed` remains (`grep -c "Future.delayed(const Duration(seconds: 10))" lib/services/sync_queue_manager.dart` → `0`).
- `flutter test` — no new failures.

**Commit:** `fix(client): await sync completion in WorkManager task; dispose container`

---

## Phase 11 — Schema‑validate the four loose backend endpoints

**Label:** `[FIX]`
**Scope:** `backend/server.py` (`/telemetry`, `/yield`, `/metadata`, `/application`).
**Why now:** structural change best done after their callers (`verify_signature`) are stable.

**What's wrong:** these endpoints accept raw `payload: dict` with no schema and no size limit, while `/batches` is strict (`extra="forbid"`). Rigor evaporates exactly where it's least observed.

**Fix**
1. Define explicit Pydantic models (`extra="forbid"`) for each endpoint with the fields actually persisted. For array fields (e.g. `temperature_readings_json`) set a `max_length` (e.g. 100_000) to bound payload size.
2. Replace `payload: dict` parameters with the typed models.
3. Fix the misleading dependency: `is_verified: bool = Depends(verify_signature)` → `device_id: str = Depends(verify_signature)`.

**Gate**
- New tests: an unknown extra field returns `422`; an oversized array returns `422`; valid payloads persist unchanged.
- `grep -nc "payload: dict" backend/server.py` → `0`.
- `pytest -q` — no new failures.

**Commit:** `fix(backend): add strict schemas and size bounds to telemetry/yield/metadata/application`

---

## Phase 12 — Remove test/"unsafe" code from the production surface

**Label:** `[REFACTOR]`
**Scope:** `lib/data/local/app_database.dart`, affected tests.
**Why now:** safe cleanup once behavior is settled.

**What's wrong:** public `getBatchTelemetryUnsafe()` (a "test‑only" method) lives in the production `AppDatabase`.

**Fix**
- Annotate with `@visibleForTesting` and rename to `getBatchTelemetryRaw`, or move it into a test‑only extension under `test/`. Update callers (tests only).

**Gate**
- `grep -c "getBatchTelemetryUnsafe" lib/` → `0`.
- `flutter analyze` clean; `flutter test` — no new failures.

**Commit:** `refactor(client): gate raw telemetry query behind @visibleForTesting`

---

## Phase 13 — Correct the trust claims and residual doc rot

**Label:** `[REFACTOR]`
**Scope:** `lib/main.dart`, `lib/services/secure_capture_service.dart`, `lib/data/local/tables.dart` header, `lib/data/local/proof_queries.dart`.
**Why last:** documentation should describe the system as it now is, after Phases 1–12.

**What's wrong:** comments conflate file integrity with scene authenticity ("Truth Machine," "indelible digital fingerprint"); the `tables.dart` header says "v4" while `schemaVersion = 15`; `proof_queries.dart:89` has an empty `catch (_) {}`.

**Fix**
1. Reword the two overselling comments to state precisely what is proven (byte‑level tamper‑evidence in transit) and what is not (scene authenticity), referencing the EXIF corroboration added in Phase 9.
2. Update the `tables.dart` header to reflect the current schema version and the columns added since v4.
3. Replace the empty catch with a logged handler (or a comment explaining why the error is genuinely ignorable, if it is).

**Gate**
- `grep -rc "Truth Machine\|indelible" lib/` reflects the reworded text (no claim of authenticity remains).
- `grep -n "catch (_) {}" lib/data/local/proof_queries.dart` → no empty body.
- `flutter analyze` clean; `flutter test` — no new failures.

**Commit:** `docs(client): correct integrity-vs-authenticity claims and schema header`

---

## Phase 14 — Full regression and sign‑off

**Label:** `[REFACTOR]` (verification only)
**Scope:** none (no source edits).

**Steps**
1. Backend: `ruff format --check backend && pytest -q | tee .final_backend.txt`.
2. Client: `dart format --output=none --set-exit-if-changed lib test && flutter analyze && flutter test | tee .final_client.txt`.
3. Alembic: upgrade a scratch DB head‑to‑head and downgrade to base; both clean.
4. In `REMEDIATION_LOG.md`, add a `## Final` section comparing baseline vs final counts. Assert: zero new failures; every phase's new tests are present and passing; every `grep` gate above holds.

**Gate (release sign‑off — all must hold):**
- No symmetric key leaves the device (`grep` confirms Ed25519 path; no `hmac_key` in identity/request code).
- No `dev-token`, no `payload: dict`, no `X-Mock-Location` control, no `Future.delayed(10s)` sync, no fabricating defaults on credit fields.
- Integrity and registration fail closed.
- Both test suites green (no new failures vs baseline); formatters report no diffs.

**Commit:** `chore: full regression green; remediation complete`

---

## Appendix A — Phase dependency graph (no cycles)

```
0 baseline
└─ 1 backend hygiene
   └─ 2 admin secret
      └─ 3 dev-token removal
         └─ 4 client Ed25519 ──► 5 server Ed25519 + migration   (4 and 5 land together)
            └─ 6 fail-closed integrity
               └─ 7 required credit inputs
                  └─ 8 LCA provisional/measured
                     └─ 9 server-side GPS corroboration
                        └─ 10 sync await
                           └─ 11 strict endpoint schemas
                              └─ 12 remove unsafe surface
                                 └─ 13 claims + doc rot
                                    └─ 14 regression sign-off
```

## Appendix B — Determinism rules

- Always run the language formatter at the end of a phase; never hand‑align code.
- JSON used for signatures or audit must be serialized with `sort_keys=True` (Python) / a fixed key order (Dart). The canonical signing string is defined once (Phase 4/5) and must be byte‑identical on both sides — never reformat it.
- New tests assert exact values, not ranges, for deterministic functions (LCA math, signing, hashing).
- Migrations are explicit and reversible (Alembic up/down). Never rely on `create_all` to "catch up" a renamed column.

## Appendix C — Stop conditions (when to halt and report)

- A gate cannot be made green without editing files outside the phase scope.
- A phase requires a secret/credential that is not in the environment.
- An Alembic migration cannot downgrade cleanly.
- A cross‑stack signing test fails after Phase 5 (the canonical strings disagree) — do not paper over it client‑side; align both sides and re‑run.
