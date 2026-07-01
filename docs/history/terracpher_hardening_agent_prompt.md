# TerraCipher Phase 2 Hardening — AI Coding Agent Prompt

## PRIME DIRECTIVE

You are implementing the TerraCipher Phase 2 Hardening plan across a Flutter/Dart mobile app and a FastAPI Python backend. This document is your single source of truth.

**You must follow these rules unconditionally:**

1. **One task at a time.** Complete a task fully, then run its specified tests. Do not start the next task until every test in the gate passes.
2. **Never hallucinate file contents.** Before modifying any file, read its current contents from disk. Every code snippet marked `CURRENT CODE` in this prompt is the exact content you will find. If the file on disk does not match, stop and report the discrepancy — do not proceed on assumptions.
3. **Never skip a test gate.** Each task ends with a test gate. The gate is not optional. Paste the test output before declaring a task done.
4. **No creative deviation.** Implement exactly what is specified. If you believe an approach is wrong, flag it as a question — do not silently substitute your own approach.
5. **Regression tests run after every phase.** After completing all tasks in a phase, run the full regression suite. A new failure in an existing test means you broke something. Fix it before moving on.

---

## CODEBASE ORIENTATION

- Flutter app root: `flutter_dmrv/`
- Backend root: `flutter_dmrv/backend/`
- Key Flutter files you will touch:
  - `lib/services/crypto_signer.dart` (new)
  - `lib/data/local/tables.dart`
  - `lib/data/local/app_database.dart`
  - `lib/data/local/pyrolysis_writer.dart`
  - `lib/services/sync_queue_manager.dart`
  - `lib/providers/dashboard_provider.dart`
  - `lib/providers/moisture_gate_notifier.dart`
  - `lib/providers/dashboard_stats_provider.dart` (new)
- Key backend files you will touch:
  - `backend/server.py`
  - `backend/models.py`
  - `backend/auth.py` (new)
  - `backend/alembic/versions/001_initial_schema.py` (new)
- Existing reference files (read-only, do not modify):
  - `lib/data/local/passphrase_resolver.dart` — HMAC key generation pattern
  - `lib/services/ble_service.dart` — existing SHA-256 usage pattern
  - `lib/providers/sync_providers.dart` — existing Drift `selectOnly` + `count()` pattern
  - `backend/schemas.py` — Pydantic schema source of truth
  - `backend/db.py` — database connection setup

---

## PHASE 1: Critical Security — HMAC Payload Signing

**Why this matters:** Without HMAC signing, an attacker with Frida/runtime hooking can tamper with outbox payloads after they are written to SQLite but before they sync to the server. This phase seals every outbox entry with a cryptographic signature at write time.

**Do not begin Phase 2 until every one of the 16 Phase 1 tests passes.**

---

### TASK 1.1 — Create `CryptoSigner` Service

**File to create:** `lib/services/crypto_signer.dart`

**Exact specification:**

- A stateless Dart utility class named `CryptoSigner`.
- Contains one public static async method: `Future<String> signPayload(String jsonPayload)`.
- The HMAC key is a 256-bit random key, base64url-encoded, stored in `flutter_secure_storage` under the key `hmac_signing_key`.
- Key generation: if `hmac_signing_key` does not exist in secure storage, generate it with `dart:math`'s `Random.secure()`, base64url-encode it, and store it. On all subsequent calls, read and return the stored key.
- This key generation/retrieval pattern is **identical** to the pattern already used in `lib/data/local/passphrase_resolver.dart`. Read that file first and follow the same structure.
- The signing algorithm is HMAC-SHA256 using `package:crypto/crypto.dart` — specifically `Hmac(sha256, keyBytes)`. This package is already a dependency (confirmed in `lib/services/ble_service.dart` lines 33–35 which already use `sha256` from the same package).
- `signPayload` returns the hex digest string (64 characters).
- Do **not** hardcode any key string. The intelligence report's suggested `_deviceSecret = "tc_secure_enclave_key_v1"` is insecure and must not be used.

**Before writing:** Read `lib/data/local/passphrase_resolver.dart` in full. Read `lib/services/ble_service.dart` lines 33–35. Model your implementation on those patterns.

**After writing:** Run Task 1.1 test gate.

#### Task 1.1 Test Gate

Run: `flutter test test/crypto_signer_test.dart`

All 3 tests must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `signPayload returns consistent 64-char hex` | Same key + same payload always produces the same 64-character hex HMAC digest |
| 2 | `signPayload changes when payload changes` | Altering even one character of the JSON input produces a completely different digest |
| 3 | `signPayload changes when key changes` | A different HMAC key produces a different digest for the same payload |

**Do not proceed to Task 1.2 until all 3 pass.**

---

### TASK 1.2 — Add `hmacSignature` Column to Drift Schema

**File to modify:** `lib/data/local/tables.dart`

**Before writing:** Read `lib/data/local/tables.dart` in full.

**Current code you will find at lines 115–134:**

```dart
class SyncOutbox extends Table {
  TextColumn get operationId => text()();
  TextColumn get batchUuid => text()();
  TextColumn get targetTable => text()();
  TextColumn get operationType => text()();
  TextColumn get payloadJson => text()();
  TextColumn get status => text().withDefault(const Constant('PENDING'))();
  IntColumn get retryCount => integer().withDefault(const Constant(0))();
  TextColumn get createdAt => text()();
  TextColumn get lastAttemptAt => text().nullable()();

  // ---------- v4 two-phase sync commit ----------
  TextColumn get jsonSyncedAt => text().nullable()();
  TextColumn get mediaSyncedAt => text().nullable()();

  @override
  Set<Column> get primaryKey => {operationId};
}
```

**Change:** Insert the following block after the `mediaSyncedAt` line and before the `@override` line:

```dart
  // ---------- v8 HMAC payload signing ----------
  /// HMAC-SHA256 of payloadJson, calculated at the exact moment of insertion.
  /// If a hacker tampers with payloadJson after insertion, this column will
  /// no longer match and the server will reject the upload.
  TextColumn get hmacSignature => text().nullable()();
```

**Why nullable:** Rows inserted before schema v8 will have no signature. The nullable column ensures those legacy rows can still be read and synced — the sync manager handles null gracefully (see Task 1.5).

**After writing:** Run Task 1.2 test gate.

#### Task 1.2 Test Gate

Run: `flutter test test/drift_schema_test.dart`

The following test must pass (it will be extended in Task 1.3, but the column declaration must exist now):

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `SyncOutbox table has hmacSignature column` | The Drift table definition includes `hmacSignature` as a nullable TextColumn |

**Do not proceed to Task 1.3 until it passes.**

---

### TASK 1.3 — Increment Schema Version & Add Migration

**File to modify:** `lib/data/local/app_database.dart`

**Before writing:** Read `lib/data/local/app_database.dart` in full.

**Change 1 — Schema version.** Find this exact line:

```dart
  @override
  int get schemaVersion => 7;
```

Change it to:

```dart
  @override
  int get schemaVersion => 8;
```

**Change 2 — Migration block.** Find the last migration block, which currently ends with:

```dart
          if (from < 7) {
            await m.createTable(mediaCaptures);
          }
```

Append directly after it:

```dart
          if (from < 8) {
            await m.addColumn(syncOutbox, syncOutbox.hmacSignature);
          }
```

**After making both changes**, run the build runner to regenerate `app_database.g.dart`:

```
dart run build_runner build --delete-conflicting-outputs
```

Confirm the build runner completes without errors before running the test gate.

**After building:** Run Task 1.3 test gate.

#### Task 1.3 Test Gate

Run: `flutter test test/drift_schema_test.dart`

All tests in this file must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `schema v8 migration adds hmacSignature column` | Open a v7 database, run migration to v8, verify the `hmac_signature` column exists and is nullable |

**Do not proceed to Task 1.4 until it passes.**

---

### TASK 1.4 — Sign Payloads at Creation Time

**Files to modify:**
- `lib/data/local/app_database.dart`
- `lib/data/local/pyrolysis_writer.dart`

**Before writing:** Read both files in full.

#### Change A — `insertWithOutbox()` in `app_database.dart`

**Current code (lines 124–143):**

```dart
  Future<void> insertWithOutbox({
    required String batchUuid,
    required String targetTable,
    required Map<String, dynamic> payload,
    required Future<void> Function() insertRow,
  }) async {
    await transaction(() async {
      await insertRow();
      await into(syncOutbox).insert(
        SyncOutboxCompanion.insert(
          operationId: _uuid.v4(),
          batchUuid: batchUuid,
          targetTable: targetTable,
          operationType: 'INSERT',
          payloadJson: jsonEncode(payload),
          createdAt: DateTime.now().toUtc().toIso8601String(),
        ),
      );
    });
  }
```

**Change to:**

```dart
  Future<void> insertWithOutbox({
    required String batchUuid,
    required String targetTable,
    required Map<String, dynamic> payload,
    required Future<void> Function() insertRow,
  }) async {
    final jsonString = jsonEncode(payload);
    final signature = await CryptoSigner.signPayload(jsonString);
    await transaction(() async {
      await insertRow();
      await into(syncOutbox).insert(
        SyncOutboxCompanion.insert(
          operationId: _uuid.v4(),
          batchUuid: batchUuid,
          targetTable: targetTable,
          operationType: 'INSERT',
          payloadJson: jsonString,
          createdAt: DateTime.now().toUtc().toIso8601String(),
          hmacSignature: Value(signature),
        ),
      );
    });
  }
```

**Important:** `CryptoSigner.signPayload` must be called **outside** the transaction lambda. Async calls inside Drift transactions can cause deadlocks.

#### Change B — `insertSystemMetadataWithOutbox()` in `app_database.dart`

Find the `into(syncOutbox).insert(...)` call inside `insertSystemMetadataWithOutbox()` (lines 94–121). It currently builds its own `SyncOutboxCompanion.insert` directly. Apply the same pattern:

1. Encode the payload JSON into a string first.
2. Call `CryptoSigner.signPayload(jsonString)` before entering the transaction.
3. Pass `hmacSignature: Value(signature)` into the companion.

**Current inner insert block to find:**

```dart
      await into(syncOutbox).insert(
        SyncOutboxCompanion.insert(
          operationId: _uuid.v4(),
          batchUuid: meta.batchUuid.value,
          targetTable: 'system_metadata',
          operationType: 'INSERT',
          payloadJson: jsonEncode(payload),
          createdAt: DateTime.now().toUtc().toIso8601String(),
        ),
      );
```

Apply the same encode-then-sign pattern as Change A.

#### Change C — `insertMediaCaptureAndEnqueue()` in `pyrolysis_writer.dart`

**Current code (lines 50–58):**

```dart
      await into(syncOutbox).insert(
        SyncOutboxCompanion.insert(
          operationId: _uuid.v4(),
          batchUuid: batchUuid,
          targetTable: 'media',
          operationType: 'INSERT',
          payloadJson: jsonEncode(payload),
          createdAt: now,
        ),
      );
```

This method does a direct `SyncOutboxCompanion.insert` call — it bypasses `insertWithOutbox`. Apply the same encode-then-sign pattern. The signature calculation must happen before the surrounding `transaction()` call.

**After all three changes:** Run Task 1.4 test gate.

#### Task 1.4 Test Gate

Run: `flutter test test/hmac_outbox_test.dart`

All 7 tests must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `insertWithOutbox stores non-null hmacSignature` | Create an outbox entry via `insertWithOutbox`, read back the row, assert `hmacSignature` is non-null |
| 2 | `hmacSignature matches CryptoSigner output` | The stored signature equals `CryptoSigner.signPayload(row.payloadJson)` |
| 3 | `insertSystemMetadataWithOutbox stores hmacSignature` | The manual outbox path in `insertSystemMetadataWithOutbox` also generates a valid HMAC |
| 4 | `insertMediaCaptureAndEnqueue stores hmacSignature` | The pyrolysis writer's direct outbox insert also generates a valid HMAC |
| 5 | `tampered payloadJson fails verification` | Manually alter `payloadJson` in the DB after insertion, re-read, assert `hmacSignature` no longer matches |
| 6 | `legacy rows with null hmacSignature do not crash` | Create a row without `hmacSignature`, verify the sync manager can read it without throwing |
| 7 | `signature is frozen at write time` | Verify the stored signature was calculated from the original payload, not recalculated on read |

**Do not proceed to Task 1.5 until all 7 pass.**

---

### TASK 1.5 — Attach HMAC Header in Sync Manager

**File to modify:** `lib/services/sync_queue_manager.dart`

**Before writing:** Read `lib/services/sync_queue_manager.dart` in full.

**Current code (lines 122–130):**

```dart
        if (entry.jsonSyncedAt == null) {
          final jsonResponse = await _client.post(
            Uri.parse('$_apiBase/api/v1/$endpoint'),
            headers: {
              'Content-Type': 'application/json',
              'X-Idempotency-Key': entry.operationId,
            },
            body: entry.payloadJson,
          );
```

**Change to:**

```dart
        if (entry.jsonSyncedAt == null) {
          final jsonResponse = await _client.post(
            Uri.parse('$_apiBase/api/v1/$endpoint'),
            headers: {
              'Content-Type': 'application/json',
              'X-Idempotency-Key': entry.operationId,
              if (entry.hmacSignature != null)
                'X-HMAC-Signature': entry.hmacSignature!,
            },
            body: entry.payloadJson,
          );
```

**Critical rule:** The sync manager reads the signature that was frozen at insertion time. It does **not** recalculate it. If `hmacSignature` is null (pre-v8 legacy rows), no header is added and the server will accept but mark the batch as `UNVERIFIED`.

**After writing:** Run Task 1.5 test gate.

#### Task 1.5 Test Gate

Run: `flutter test test/hmac_outbox_test.dart`

These additional tests (added to the same file) must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `sync manager sends X-HMAC-Signature header when present` | Mock HTTP client captures the request; assert header equals the stored signature |
| 2 | `sync manager omits X-HMAC-Signature when null` | Legacy row with null signature; assert the header is absent from the request |

**Do not proceed to Task 1.6 until both pass.**

---

### TASK 1.6 — Server-Side HMAC Verification

**File to modify:** `backend/server.py`

**Before writing:** Read `backend/server.py` in full. Read `backend/schemas.py` in full.

**Current code (lines 122–126) — `/batches` endpoint signature:**

```python
async def create_batch(
    payload: BatchPayload,
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> BatchResponse:
```

**Change:** Add a FastAPI dependency function (not inline logic) that performs HMAC verification. The dependency must:

1. Accept the raw `Request` object to read raw bytes via `await request.body()`.
2. Read the `X-HMAC-Signature` header (treat it as optional — `None` if absent).
3. Read the shared secret from the environment variable `DMRV_HMAC_SECRET`. If the env var is not set, log a warning and skip verification.
4. Compute `hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()`.
5. **If the header is present AND the signatures do not match:** raise `HTTPException(status_code=403, detail="hmac_mismatch")`.
6. **If the header is present as an empty string:** raise `HTTPException(status_code=403, detail="hmac_mismatch")`.
7. **If the header is absent:** accept the request, log a warning, and mark the batch status as `UNVERIFIED` (add a `verified: bool` field to the batch record in the database).

Apply this dependency to **all** data-writing endpoints: `/batches`, `/telemetry`, `/yield`, `/metadata`, `/application`.

**Environment variable:** `DMRV_HMAC_SECRET` — a single shared secret for the MVP. Each device uses the same secret, configured server-side via environment. Per-device unique keys are deferred to post-pilot.

**After writing:** Run the full Phase 1 test gate.

---

### PHASE 1 FULL TEST GATE — ALL 16 MUST PASS

Run Flutter tests: `flutter test`
Run backend tests: `pytest backend/tests/ -v`

| # | Test File | Test Name |
|---|-----------|-----------|
| 1 | `test/crypto_signer_test.dart` | `signPayload returns consistent 64-char hex` |
| 2 | `test/crypto_signer_test.dart` | `signPayload changes when payload changes` |
| 3 | `test/crypto_signer_test.dart` | `signPayload changes when key changes` |
| 4 | `test/hmac_outbox_test.dart` | `insertWithOutbox stores non-null hmacSignature` |
| 5 | `test/hmac_outbox_test.dart` | `hmacSignature matches CryptoSigner output` |
| 6 | `test/hmac_outbox_test.dart` | `insertSystemMetadataWithOutbox stores hmacSignature` |
| 7 | `test/hmac_outbox_test.dart` | `insertMediaCaptureAndEnqueue stores hmacSignature` |
| 8 | `test/hmac_outbox_test.dart` | `tampered payloadJson fails verification` |
| 9 | `test/hmac_outbox_test.dart` | `legacy rows with null hmacSignature do not crash` |
| 10 | `test/drift_schema_test.dart` | `schema v8 migration adds hmacSignature column` |
| 11 | `backend/tests/test_hmac_verification.py` | `valid HMAC → 201 Created` |
| 12 | `backend/tests/test_hmac_verification.py` | `tampered HMAC → 403 Forbidden` |
| 13 | `backend/tests/test_hmac_verification.py` | `missing HMAC → 201 with UNVERIFIED flag` |
| 14 | `backend/tests/test_hmac_verification.py` | `empty HMAC → 403 Forbidden` |
| 15 | **Regression** | All existing 11 Flutter test files pass (`flutter test`) |
| 16 | **Regression** | All existing 27 backend tests pass (`pytest tests/ -v`) |

**Do not begin Phase 2 until all 16 pass.**

---

## PHASE 2: Performance — OOM Fix & Dashboard Statistics Cache

**Why this matters:** The `findIncompleteBatch()` method in `dashboard_provider.dart` loads every row from two tables into Dart memory. On a device with 500+ batches, this will OOM-crash a low-RAM Android phone. This phase eliminates all full-table loads and replaces them with SQL-level aggregation.

**Do not begin Phase 3 until every one of the 13 Phase 2 tests passes.**

---

### TASK 2.1 — Rewrite `findIncompleteBatch()` with Drift SQL

**File to modify:** `lib/providers/dashboard_provider.dart`

**Before writing:** Read `lib/providers/dashboard_provider.dart` in full.

**Current code (lines 82–91):**

```dart
  Future<String?> findIncompleteBatch(AppDatabase db) async {
    final allSourcing = await db.select(db.biomassSourcing).get();
    final allEndUse = await db.select(db.endUseApplication).get();
    final completedIds = allEndUse.map((e) => e.batchUuid).toSet();
    final incomplete = allSourcing
        .where((s) => !completedIds.contains(s.batchUuid))
        .toList();
    if (incomplete.isEmpty) return null;
    return incomplete.last.batchUuid;
  }
```

**Change to:**

```dart
  Future<String?> findIncompleteBatch(AppDatabase db) async {
    final result = await db.customSelect(
      'SELECT bs.batch_uuid FROM biomass_sourcing bs '
      'WHERE bs.batch_uuid NOT IN '
      '(SELECT eu.batch_uuid FROM end_use_application eu) '
      'ORDER BY bs.harvest_timestamp DESC '
      'LIMIT 1',
    ).getSingleOrNull();
    return result?.read<String>('batch_uuid');
  }
```

This query returns exactly one string or null. Memory consumption is constant regardless of table size.

**After writing:** Run Task 2.1 test gate.

#### Task 2.1 Test Gate

Run: `flutter test test/find_incomplete_batch_test.dart`

All 5 tests must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `returns null when no batches exist` | Empty database → null |
| 2 | `returns batchUuid when sourcing exists but no end-use` | A batch with only BiomassSourcing is found |
| 3 | `returns null when all batches have end-use records` | All completed batches are excluded |
| 4 | `returns most recent incomplete batch` | With 3 incomplete batches, the one with the latest `harvest_timestamp` is returned |
| 5 | `handles 500+ batches without OOM` | Insert 500 sourcing + 499 end-use rows, call method, assert it returns the 1 remaining batch with no memory spike |

**Do not proceed to Task 2.2 until all 5 pass.**

---

### TASK 2.2 — Fix `moistureEvidenceProvider` Full-Table Watch

**File to modify:** `lib/providers/moisture_gate_notifier.dart`

**Before writing:** Read `lib/providers/moisture_gate_notifier.dart` in full.

**Current code (lines 91–104):**

```dart
final moistureEvidenceProvider = StreamProvider<bool>((ref) {
  final batchUuid = ref.watch(requiredBatchUuidProvider);
  final db = ref.watch(appDatabaseProvider).value;

  if (db == null) {
    return Stream.value(false);
  }

  return db
      .select(db.biomassSourcing)
      .watch()
      .map((rows) => rows.any((r) =>
          r.batchUuid == batchUuid && r.photoPath != null && r.photoPath!.isNotEmpty));
});
```

**Change to:**

```dart
final moistureEvidenceProvider = StreamProvider<bool>((ref) {
  final batchUuid = ref.watch(requiredBatchUuidProvider);
  final db = ref.watch(appDatabaseProvider).value;

  if (db == null) {
    return Stream.value(false);
  }

  final query = db.select(db.biomassSourcing)
    ..where((t) => t.batchUuid.equals(batchUuid))
    ..where((t) => t.photoPath.isNotNull());
  return query.watch().map((rows) => rows.isNotEmpty);
});
```

The WHERE clause is now evaluated by SQLite, not by Dart. Only matching rows are returned across the stream.

**After writing:** Run Task 2.2 test gate.

#### Task 2.2 Test Gate

Run: `flutter test test/moisture_evidence_test.dart`

All 3 tests must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `returns false when no photo exists` | Batch with null `photoPath` → false |
| 2 | `returns true when photo exists for matching batch` | Batch with non-null `photoPath` → true |
| 3 | `does not match photos from other batches` | Photo exists for batch-A, query is for batch-B → false |

**Do not proceed to Task 2.3 until all 3 pass.**

---

### TASK 2.3 — Add Dashboard Statistics Provider

**File to create:** `lib/providers/dashboard_stats_provider.dart`

**Before writing:** Read `lib/providers/sync_providers.dart` lines 13–24. Your implementation must follow the exact same `selectOnly` + `count()` + `watchSingle()` pattern shown there.

**Specification:**

Create a data class:

```dart
class DashboardStats {
  final int totalBatches;
  final int completedBatches;
  final int pendingSync;
  final double totalYieldKg;
}
```

Create a `StreamProvider<DashboardStats>` that computes all four fields using separate Drift `selectOnly` queries — do not load any rows into memory. Use reactive Drift streams so the provider updates automatically when the database changes.

- `totalBatches`: count of rows in `SystemMetadata`.
- `completedBatches`: count of rows in `EndUseApplication`.
- `pendingSync`: count of rows in `SyncOutbox` where `status == 'PENDING'`. This must match the output of the existing `pendingOutboxCountProvider`.
- `totalYieldKg`: sum of `wetYieldWeightKg` from the yield metrics table.

**Reference pattern from `sync_providers.dart` lines 13–24:**

```dart
final pendingOutboxCountProvider = StreamProvider<int>((ref) async* {
  final db = await ref.watch(appDatabaseProvider.future);
  final outbox = db.syncOutbox;

  final query = db.selectOnly(outbox)
    ..addColumns([outbox.operationId.count()])
    ..where(outbox.status.equals('PENDING'));

  yield* query
      .map((row) => row.read(outbox.operationId.count()) ?? 0)
      .watchSingle();
});
```

Follow this pattern for each stat. Combine into a single `DashboardStats` object.

**After writing:** Run Task 2.3 test gate.

#### Task 2.3 Test Gate

Run: `flutter test test/dashboard_stats_test.dart`

All 4 tests must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `totalBatches counts SystemMetadata rows` | Insert 3 metadata rows → `totalBatches == 3` |
| 2 | `completedBatches counts batches with EndUseApplication` | 3 batches, 2 with end-use → `completedBatches == 2` |
| 3 | `pendingSync matches SyncOutbox PENDING count` | Matches the output of the existing `pendingOutboxCountProvider` for the same database state |
| 4 | `totalYieldKg sums wetYieldWeightKg` | Insert rows of 10 kg, 20 kg, 30 kg → `totalYieldKg == 60.0` |

**Do not run the Phase 2 gate until all 4 pass.**

---

### PHASE 2 FULL TEST GATE — ALL 13 MUST PASS

Run: `flutter test`

| # | Test File | Test Name |
|---|-----------|-----------|
| 1 | `test/find_incomplete_batch_test.dart` | `returns null when no batches exist` |
| 2 | `test/find_incomplete_batch_test.dart` | `returns batchUuid when sourcing exists but no end-use` |
| 3 | `test/find_incomplete_batch_test.dart` | `returns null when all batches have end-use records` |
| 4 | `test/find_incomplete_batch_test.dart` | `returns most recent incomplete batch` |
| 5 | `test/find_incomplete_batch_test.dart` | `handles 500+ batches without OOM` |
| 6 | `test/moisture_evidence_test.dart` | `returns false when no photo exists` |
| 7 | `test/moisture_evidence_test.dart` | `returns true when photo exists for matching batch` |
| 8 | `test/moisture_evidence_test.dart` | `does not match photos from other batches` |
| 9 | `test/dashboard_stats_test.dart` | `totalBatches counts SystemMetadata rows` |
| 10 | `test/dashboard_stats_test.dart` | `completedBatches counts batches with EndUseApplication` |
| 11 | `test/dashboard_stats_test.dart` | `pendingSync matches SyncOutbox PENDING count` |
| 12 | `test/dashboard_stats_test.dart` | `totalYieldKg sums wetYieldWeightKg` |
| 13 | **Regression** | All Phase 1 tests + all original 11 Flutter tests pass |

**Do not begin Phase 3 until all 13 pass.**

---

## PHASE 3: Backend Hardening — Stub Endpoints, Auth & Migrations

**Why this matters:** Four backend endpoints (`/telemetry`, `/yield`, `/metadata`, `/application`) accept any dict with zero validation and silently discard the data. The Flutter app sends real field data to them. There is also no authentication — any HTTP client can write to the API.

**Do not begin Phase 4 until every one of the 20 Phase 3 tests passes.**

---

### TASK 3.1 — Add Missing SQLAlchemy Models

**File to modify:** `backend/models.py`

**Before writing:** Read `backend/models.py` in full. Read `backend/schemas.py` in full to understand the field structure of each new model.

**Current models.py** has exactly 2 models:
- `Batch` — maps to the `batches` table
- `MediaFile` — maps to the `media_files` table

**Add 4 new SQLAlchemy models** (using the same base class and column style already in the file):

1. `SystemMetadataRow` — mirrors `schemas.SystemMetadata`. Table name: `system_metadata`.
2. `PyrolysisTelemetryRow` — mirrors `schemas.PyrolysisTelemetry`. Table name: `pyrolysis_telemetry`.
3. `YieldMetricsRow` — mirrors `schemas.YieldMetrics`. Table name: `yield_metrics`.
4. `EndUseApplicationRow` — mirrors `schemas.EndUseApplication`. Table name: `end_use_application`.

**Every new model must include:**
- `operation_id`: String, unique, indexed (used for idempotency).
- `received_at`: DateTime, set server-side at insertion time (not from the client payload).
- All domain fields from the corresponding Pydantic schema in `schemas.py`.

**After writing:** Run Task 3.1 test gate.

#### Task 3.1 Test Gate

Run: `pytest backend/tests/test_models.py -v`

All 5 tests must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `SystemMetadataRow creates in DB` | Insert a row, read it back, all fields match |
| 2 | `PyrolysisTelemetryRow creates in DB` | Insert a row, read it back, all fields match |
| 3 | `YieldMetricsRow creates in DB` | Insert a row, read it back, all fields match |
| 4 | `EndUseApplicationRow creates in DB` | Insert a row, read it back, all fields match |
| 5 | `operation_id unique constraint enforced` | Insert two rows with the same `operation_id` → `IntegrityError` |

**Do not proceed to Task 3.2 until all 5 pass.**

---

### TASK 3.2 — Wire Stub Endpoints to Pydantic Schemas

**File to modify:** `backend/server.py`

**Before writing:** Read `backend/server.py` in full. Note how the existing `/batches` endpoint handles idempotency via `X-Idempotency-Key` and database persistence — replicate that pattern exactly.

**Current code (lines 211–225) — the 4 stub endpoints:**

```python
@app.post("/api/v1/telemetry", status_code=status.HTTP_201_CREATED)
async def create_telemetry(payload: dict):
    return {"status": "success", "duplicate": False}

@app.post("/api/v1/yield", status_code=status.HTTP_201_CREATED)
async def create_yield(payload: dict):
    return {"status": "success", "duplicate": False}

@app.post("/api/v1/metadata", status_code=status.HTTP_201_CREATED)
async def create_metadata(payload: dict):
    return {"status": "success", "duplicate": False}

@app.post("/api/v1/application", status_code=status.HTTP_201_CREATED)
async def create_application(payload: dict):
    return {"status": "success", "duplicate": False}
```

**Change each endpoint to:**

1. Replace `payload: dict` with the correct Pydantic model from `schemas.py` (e.g. `payload: PyrolysisTelemetry` for `/telemetry`).
2. Add `x_idempotency_key: str = Header(..., alias="X-Idempotency-Key")`.
3. Add `session: AsyncSession = Depends(get_session)`.
4. Persist the payload to the corresponding SQLAlchemy model created in Task 3.1.
5. Check for duplicate `operation_id` (the idempotency key) by catching `IntegrityError`. If duplicate, return `{"status": "success", "duplicate": True}` with HTTP 200.
6. On success, return `{"status": "success", "duplicate": False}` with HTTP 201.

**After writing:** Run Task 3.2 test gate.

#### Task 3.2 Test Gate

Run: `pytest backend/tests/test_endpoints.py -v`

All 8 endpoint tests must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `POST /telemetry valid → 201` | Valid `PyrolysisTelemetry` JSON → 201 Created |
| 2 | `POST /telemetry malformed → 422` | Missing required field → 422 Unprocessable Entity |
| 3 | `POST /telemetry duplicate → 200` | Same idempotency key as a previous request → 200 with `duplicate: True` |
| 4 | `POST /yield valid → 201` | Valid `YieldMetrics` JSON → 201 Created |
| 5 | `POST /yield malformed → 422` | Missing required field → 422 Unprocessable Entity |
| 6 | `POST /metadata valid → 201` | Valid `SystemMetadata` JSON → 201 Created |
| 7 | `POST /application valid → 201` | Valid `EndUseApplication` JSON → 201 Created |
| 8 | `POST /application invalid methodology → 422` | `methodology` value not in the allowed enum set → 422 |

**Do not proceed to Task 3.3 until all 8 pass.**

---

### TASK 3.3 — Fix `BatchPayload` Strictness Mismatch

**File to modify:** `backend/server.py`

**Before writing:** Read `backend/server.py` and `backend/schemas.py` in full.

**The problem:** There are two models both named `BatchPayload` with incompatible structures:

- `server.py` (lines 60–88): Flat model with `extra="ignore"` (permissive). This is what the running server currently uses.
- `schemas.py` (lines 144–149): Nested model with `extra="forbid"` (strict), using sub-models for each data domain.

**Decision:** Keep the flat `server.py` `BatchPayload` for backwards compatibility with the existing `/batches` endpoint. Rename the `schemas.py` version to `BatchSyncPayload` and reserve it for the future `/batches/sync` endpoint. Add a comment in both files marking the distinction clearly.

**Changes:**
1. In `schemas.py`: rename `BatchPayload` to `BatchSyncPayload`. Add a comment: `# Reserved for future /batches/sync endpoint. Do not use for /batches.`
2. In `server.py`: add a comment above the existing `BatchPayload` class: `# Backwards-compatible flat schema for /batches. See schemas.BatchSyncPayload for the strict nested version.`
3. Update any imports in `server.py` that reference `schemas.BatchPayload` to `schemas.BatchSyncPayload`.

**After writing:** Run Task 3.3 test gate.

#### Task 3.3 Test Gate

Run: `pytest backend/tests/test_endpoints.py -v`

The following test must pass (in addition to all 8 from Task 3.2 which must still pass):

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `POST /batches still accepts existing flat payload` | The `/batches` endpoint remains functional with the existing flat `BatchPayload` format |

**Do not proceed to Task 3.4 until all 9 endpoint tests pass.**

---

### TASK 3.4 — Create Alembic Initial Migration

**Context:** `backend/alembic.ini` exists. `backend/alembic/versions/` is empty. No migration has ever been captured. The tables currently exist in the database because SQLAlchemy creates them directly — this will break in production.

**Steps:**

1. Confirm all 6 SQLAlchemy models (`Batch`, `MediaFile`, and the 4 new ones from Task 3.1) are imported in `backend/alembic/env.py`'s `target_metadata`.
2. Run: `alembic revision --autogenerate -m "initial schema"`
3. Inspect the generated file in `backend/alembic/versions/`. Verify it includes `CREATE TABLE` statements for all 6 models.
4. Run: `alembic upgrade head` against a fresh database. Verify it completes cleanly.

**After running:** Run Task 3.4 test gate.

#### Task 3.4 Test Gate

Run: `pytest backend/tests/test_alembic.py -v`

Both tests must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `alembic upgrade head succeeds` | Migration applies cleanly to a fresh database with no existing tables |
| 2 | `alembic downgrade base succeeds` | Migration is fully reversible — downgrading drops all tables cleanly |

**Do not proceed to Task 3.5 until both pass.**

---

### TASK 3.5 — Add API Key Authentication

**File to create:** `backend/auth.py`

**Specification:**

Create a FastAPI dependency function `verify_api_key(request: Request)` that:

1. Reads the `Authorization` header. Expected format: `Bearer <device_api_key>`.
2. Reads the environment variable `DMRV_API_KEYS` — a comma-separated list of valid API keys.
3. If the header is missing or malformed: raise `HTTPException(status_code=401, detail="missing_authorization")`.
4. If the extracted key is not in the list: raise `HTTPException(status_code=401, detail="invalid_api_key")`.
5. If valid: return the key string (for logging purposes).

**Apply to endpoints:**

Add `api_key: str = Depends(verify_api_key)` to all data-writing endpoints: `/batches`, `/telemetry`, `/yield`, `/metadata`, `/application`, `/media`.

**Exclude from auth:** The `/api/health` endpoint must remain public. Do not add the dependency there.

**After writing:** Run Task 3.5 test gate.

#### Task 3.5 Test Gate

Run: `pytest backend/tests/test_auth.py -v`

All 4 tests must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `no Authorization header → 401` | Request with no auth header → 401 with `missing_authorization` |
| 2 | `invalid API key → 401` | Wrong key → 401 with `invalid_api_key` |
| 3 | `valid API key → request proceeds` | Correct key → 201 on a valid payload |
| 4 | `health endpoint skips auth` | `GET /api/health` with no auth header → 200 |

**Do not run the Phase 3 gate until all 4 pass.**

---

### PHASE 3 FULL TEST GATE — ALL 20 MUST PASS

Run: `pytest backend/tests/ -v`

| # | Test File | Test Name |
|---|-----------|-----------|
| 1 | `test_models.py` | `SystemMetadataRow creates in DB` |
| 2 | `test_models.py` | `PyrolysisTelemetryRow creates in DB` |
| 3 | `test_models.py` | `YieldMetricsRow creates in DB` |
| 4 | `test_models.py` | `EndUseApplicationRow creates in DB` |
| 5 | `test_models.py` | `operation_id unique constraint enforced` |
| 6 | `test_endpoints.py` | `POST /telemetry valid → 201` |
| 7 | `test_endpoints.py` | `POST /telemetry malformed → 422` |
| 8 | `test_endpoints.py` | `POST /telemetry duplicate → 200` |
| 9 | `test_endpoints.py` | `POST /yield valid → 201` |
| 10 | `test_endpoints.py` | `POST /yield malformed → 422` |
| 11 | `test_endpoints.py` | `POST /metadata valid → 201` |
| 12 | `test_endpoints.py` | `POST /application valid → 201` |
| 13 | `test_endpoints.py` | `POST /application invalid methodology → 422` |
| 14 | `test_alembic.py` | `alembic upgrade head succeeds` |
| 15 | `test_alembic.py` | `alembic downgrade base succeeds` |
| 16 | `test_auth.py` | `no Authorization header → 401` |
| 17 | `test_auth.py` | `invalid API key → 401` |
| 18 | `test_auth.py` | `valid API key → request proceeds` |
| 19 | `test_auth.py` | `health endpoint skips auth` |
| 20 | **Regression** | All existing 27 backend tests + all Phase 1 backend tests pass |

**Do not begin Phase 4 until all 20 pass.**

---

## PHASE 4: Infrastructure — Docker, CI/CD & Object Storage

**Do not begin Phase 5 until every one of the 8 Phase 4 tests passes.**

---

### TASK 4.1 — Dockerfile & docker-compose

**Files to create:**
- `backend/Dockerfile`
- `docker-compose.yml` (at the project root)

**Dockerfile specification:**

- Base image: `python:3.11-slim`
- Multi-stage build: first stage installs dependencies, second stage copies source and runs the server.
- Copy `backend/requirements.txt`, run `pip install --no-cache-dir -r requirements.txt`.
- Copy `backend/` source.
- Expose port `8001`.
- Entrypoint: `uvicorn server:app --host 0.0.0.0 --port 8001`.

**docker-compose.yml specification:**

Two services:
- `api`: built from `backend/Dockerfile`. Environment variables: `DATABASE_URL`, `DMRV_HMAC_SECRET`, `DMRV_API_KEYS`. Depends on `postgres`. Exposes `8001:8001`.
- `postgres`: image `postgres:15`. Persisted volume. Environment: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.

**Note:** `backend/db.py` lines 16–19 already read `DATABASE_URL` from environment:

```python
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/dmrv"
)
```

No change needed to `db.py`. Docker simply sets the env var.

**After writing:** Run Task 4.1 test gate.

#### Task 4.1 Test Gate

Run: `docker-compose up -d` then run `pytest backend/tests/test_docker.py -v`

Both tests must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `docker-compose up health check` | `curl localhost:8001/api/health` returns `{"status": "ok"}` after `docker-compose up` |
| 2 | `pytest runs inside container` | `docker-compose exec api pytest tests/ -v` exits with code 0 |

**Do not proceed to Task 4.2 until both pass.**

---

### TASK 4.2 — GitHub Actions CI Pipeline

**File to create:** `.github/workflows/ci.yml`

**Specification — three jobs:**

**Job 1: `flutter`**
- Runs on: `ubuntu-latest`
- Steps: checkout → setup Flutter → `flutter pub get` → `dart run build_runner build --delete-conflicting-outputs` → `flutter test`

**Job 2: `backend`**
- Runs on: `ubuntu-latest`
- Services: `postgres:15` (with health check)
- Steps: checkout → setup Python 3.11 → `pip install -r backend/requirements.txt` → `pytest backend/tests/ -v`
- Environment: `DATABASE_URL` pointed at the service container

**Job 3: `lint`**
- Runs on: `ubuntu-latest`
- Steps: `flutter analyze` (Flutter job) and `ruff check backend/` (backend job) — can be combined or separate

**Trigger:** `on: [push, pull_request]` targeting `main`.

**After writing:** Run Task 4.2 test gate.

#### Task 4.2 Test Gate

Push the `.github/workflows/ci.yml` file to the repository on a feature branch. Verify on GitHub Actions:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `CI Flutter job passes` | Flutter job completes green in GitHub Actions |
| 2 | `CI Backend job passes` | Backend job completes green in GitHub Actions |

**Do not proceed to Task 4.3 until both jobs are green.**

---

### TASK 4.3 — Migrate Media Uploads to S3-Compatible Object Storage

**File to modify:** `backend/server.py`

**Before writing:** Read `backend/server.py` in full, specifically the file upload handler.

**Current code (lines 47–49):**

```python
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
```

**Current code (lines 283–285) — local file write:**

```python
    file_path = UPLOAD_DIR / f"{x_idempotency_key}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(content)
```

**Change:**

1. Add a dependency on `boto3` (add to `requirements.txt`).
2. Read environment variables: `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (optional, default `us-east-1`), `S3_ENDPOINT_URL` (optional, for S3-compatible stores like MinIO).
3. If `S3_BUCKET` is set: upload the file bytes to S3 using `boto3.client('s3').put_object(...)`. Store the resulting S3 object key (not the full URL) in `MediaFile.file_path`.
4. If `S3_BUCKET` is **not** set: fall back to writing to the local `UPLOAD_DIR`. Log a warning: `"S3_BUCKET not configured — falling back to local storage"`. The server must not crash in this case.

**After writing:** Run Task 4.3 test gate.

#### Task 4.3 Test Gate

Run: `pytest backend/tests/test_s3_upload.py -v`

All 3 tests must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `media upload writes to S3` | Upload a file → verify the object exists in the configured S3 bucket (use moto mock in tests) |
| 2 | `media upload SHA-256 verified` | Server-side hash of the file matches the hash declared in the upload request, after S3 round-trip |
| 3 | `fallback to local when S3 unavailable` | `S3_BUCKET` env var not set → server writes to local uploads dir and returns 201, no crash |

**Do not run the Phase 4 gate until all 3 pass.**

---

### PHASE 4 FULL TEST GATE — ALL 8 MUST PASS

| # | Test File / Location | Test Name |
|---|-----------|-----------|
| 1 | `backend/tests/test_docker.py` | `docker-compose up health check` |
| 2 | `backend/tests/test_docker.py` | `pytest runs inside container` |
| 3 | GitHub Actions | `CI Flutter job passes` |
| 4 | GitHub Actions | `CI Backend job passes` |
| 5 | `backend/tests/test_s3_upload.py` | `media upload writes to S3` |
| 6 | `backend/tests/test_s3_upload.py` | `media upload SHA-256 verified` |
| 7 | `backend/tests/test_s3_upload.py` | `fallback to local when S3 unavailable` |
| 8 | **Regression** | All Phase 1–3 tests pass (`pytest backend/tests/ -v` and `flutter test`) |

**Do not begin Phase 5 until all 8 pass.**

---

## PHASE 5: Phase 2+ Features — Background Sync, Fonts & i18n

**Do not declare the project complete until every one of the 12 Phase 5 tests passes.**

---

### TASK 5.1 — True Background Sync (Android WorkManager)

**Files to create/modify:**
- `android/app/src/main/kotlin/.../SyncWorker.kt` (new)
- `lib/services/sync_queue_manager.dart` (modify)

**Before writing:** Read `lib/services/sync_queue_manager.dart` lines 53–69.

**Current code (lines 53–69) — foreground-only listener:**

```dart
  void _initConnectivityListener() {
    _connectivity.checkConnectivity().then((results) {
      if (results.any((r) => r != ConnectivityResult.none)) {
        debugPrint('[SyncQueue] Network detected on startup. Triggering loop.');
        _triggerSync();
      }
    });

    _subscription = _connectivity.onConnectivityChanged.listen((results) {
      if (results.any((r) => r != ConnectivityResult.none)) {
        debugPrint('[SyncQueue] Network change detected. Triggering loop.');
        _triggerSync();
      }
    });
  }
```

This only runs when the app is in the foreground.

**Change:**

1. Add the `workmanager` Flutter plugin to `pubspec.yaml`.
2. Create `SyncWorker.kt` as a Kotlin `Worker` subclass that calls back into a Dart isolate via `FlutterEngine`.
3. In `sync_queue_manager.dart`, after `_initConnectivityListener()`, register a periodic `workmanager` task (minimum interval: 15 minutes, as enforced by Android WorkManager). The task must call the same `_triggerSync()` logic.
4. Preserve the existing foreground `_isSyncing` guard — the background task must respect it to prevent concurrent sync runs.

**After writing:** Run Task 5.1 test gate.

#### Task 5.1 Test Gate

Run: `flutter test test/background_sync_test.dart`

All 3 tests must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `WorkManager callback invokes _triggerSync` | Mock WorkManager fires the callback → `_triggerSync` is called |
| 2 | `background sync skips when already syncing` | `_isSyncing` is true when the callback fires → `_triggerSync` is not called a second time |
| 3 | `background sync handles no-network gracefully` | No connectivity → sync exits cleanly without any exception or crash |

**Do not proceed to Task 5.2 until all 3 pass.**

---

### TASK 5.2 — Commit Font Assets & Fix `pubspec.yaml`

**Files to create:**
- `assets/fonts/SpaceGrotesk-Regular.ttf`
- `assets/fonts/SpaceGrotesk-Medium.ttf`
- `assets/fonts/SpaceGrotesk-Bold.ttf`
- `assets/fonts/SpaceMono-Regular.ttf`
- `assets/fonts/SpaceMono-Bold.ttf`
- `assets/fonts/NotoSansDevanagari-Regular.ttf`
- `assets/fonts/NotoSansDevanagari-Bold.ttf`

**File to modify:** `pubspec.yaml`

**Before writing:** Read `pubspec.yaml` in full. Note lines 53–54 — the `flutter:` section currently has no `fonts:` key.

**Current code (lines 53–54):**

```yaml
flutter:
  uses-material-design: true
```

**Add** a `fonts:` section under `flutter:` declaring all three font families with the correct weight mappings. Download the `.ttf` files from Google Fonts. The exact `pubspec.yaml` font declaration format must match Flutter's specification.

**After writing:** Run Task 5.2 test gate.

#### Task 5.2 Test Gate

Run: `flutter test test/font_assets_test.dart`

Both tests must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `SpaceGrotesk font family resolves` | `TextStyle(fontFamily: 'SpaceGrotesk')` resolves to the bundled font, not the system fallback |
| 2 | `NotoSansDevanagari renders Hindi glyphs` | Hindi text renders with the correct font metrics (not Roboto) |

**Do not proceed to Task 5.3 until both pass.**

---

### TASK 5.3 — Internationalization (Hindi `.arb` Files)

**Files to create:**
- `lib/l10n/app_en.arb`
- `lib/l10n/app_hi.arb`

**File to modify:** `pubspec.yaml`

**Before writing:** Search the entire `lib/` directory for Devanagari Unicode characters (Unicode range U+0900–U+097F). Every string found is a hardcoded Hindi string that must be extracted.

**Known hardcoded instance to extract** (from `lib/ui/screens/dashboard_screen.dart` line 480):

```dart
            subtitleHindi: 'बायोमास स्कैन करें',
```

**Steps:**

1. Add `flutter_localizations` and `intl` to `pubspec.yaml` dependencies.
2. Add `generate: true` under the `flutter:` key in `pubspec.yaml`.
3. Add a `flutter_gen` or `l10n.yaml` config pointing to `lib/l10n/`.
4. Create `app_en.arb` with English strings for every key.
5. Create `app_hi.arb` with Hindi strings for every key.
6. Replace all hardcoded Devanagari literals in `lib/` with `AppLocalizations.of(context).keyName` references.

**After writing:** Run Task 5.3 test gate.

#### Task 5.3 Test Gate

Run: `flutter test test/l10n_test.dart`

All 3 tests must pass:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `English locale loads all strings` | All keys in `app_en.arb` resolve without a `MissingLocalizationError` |
| 2 | `Hindi locale loads all strings` | All keys in `app_hi.arb` resolve without a `MissingLocalizationError` |
| 3 | `no hardcoded Hindi strings remain` | Grep `lib/` for Devanagari code points → zero matches outside `.arb` files |

**Do not run the Phase 5 gate until all 3 pass.**

---

### PHASE 5 FULL TEST GATE — ALL 12 MUST PASS

Run: `flutter test` and `pytest backend/tests/ -v`

| # | Test File | Test Name |
|---|-----------|-----------|
| 1 | `test/background_sync_test.dart` | `WorkManager callback invokes _triggerSync` |
| 2 | `test/background_sync_test.dart` | `background sync skips when already syncing` |
| 3 | `test/background_sync_test.dart` | `background sync handles no-network gracefully` |
| 4 | `test/font_assets_test.dart` | `SpaceGrotesk font family resolves` |
| 5 | `test/font_assets_test.dart` | `NotoSansDevanagari renders Hindi glyphs` |
| 6 | `test/l10n_test.dart` | `English locale loads all strings` |
| 7 | `test/l10n_test.dart` | `Hindi locale loads all strings` |
| 8 | `test/l10n_test.dart` | `no hardcoded Hindi strings remain` |
| 9 | **Manual** | Background sync on a real device: kill app → turn airplane mode off → verify sync runs within 15 minutes |
| 10 | **Manual** | Hindi font rendering: switch locale to Hindi → verify all screens render correctly with no tofu boxes |
| 11 | **Regression** | All Phase 1–4 Flutter tests pass (`flutter test`) |
| 12 | **Regression** | All Phase 1–4 backend tests pass (`pytest backend/tests/ -v`) |

---

## OPEN QUESTIONS — DO NOT RESOLVE ON YOUR OWN

Before beginning Phase 1, flag these to the human and wait for answers:

1. **HMAC Key Provisioning (Phase 1, Task 1.6):** Should each pilot device receive a unique HMAC key during enrollment, or is a single shared `DMRV_HMAC_SECRET` environment variable acceptable for the MVP? A per-device unique key provides stronger fraud attribution but requires a device registration flow that is not currently implemented.

2. **BatchPayload Canonical Schema (Phase 3, Task 3.3):** After renaming `schemas.BatchPayload` to `schemas.BatchSyncPayload`, which callers need to be updated? Confirm no existing Flutter code references the Python schema names directly.

3. **Background Sync Battery Policy (Phase 5, Task 5.1):** Should `workmanager` be configured as `periodic` (minimum 15-minute interval, Android enforced) or as a `oneOff` triggered by a connectivity broadcast receiver? `periodic` is simpler; `oneOff` is more responsive to connectivity changes but requires a separate `BroadcastReceiver` registration.

---

## COMPLETION CRITERIA

The project is complete when:

- All 16 Phase 1 tests pass.
- All 13 Phase 2 tests pass.
- All 20 Phase 3 tests pass.
- All 8 Phase 4 tests pass.
- All 12 Phase 5 tests pass (including both manual tests).
- `flutter test` passes with zero failures on all test files.
- `pytest backend/tests/ -v` passes with zero failures on all test files.
- The two manual device tests have been executed and confirmed.
