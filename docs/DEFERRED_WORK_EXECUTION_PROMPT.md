# TerraCipher dMRV — Deferred-Work EXECUTION PROMPT (step-by-step, agent-runnable)

> **You are an execution agent.** This file tells you EXACTLY what to do, in order, to
> finish the deferred backlog. Follow it literally. Do not improvise architecture. When a
> step says "mirror file X", open file X and copy its shape. When a step gives you code,
> adapt names to match surrounding code but keep the structure. This is the companion to
> `docs/DEFERRED_WORK_EXECUTION_PLAN.md` (the *what/why*); this file is the *how, step by
> step*.

---

## 0. OPERATING RULES (read once, obey always)

1. **One Part per session/PR.** Do Part R1 completely (green + committed) before R2/R5.
   R3, R4, R6, R7 are independent — but still one at a time unless you are explicitly
   running the parallel worktree flow in the PLAN `§1.1`.
2. **Never commit red.** After every code change, run the relevant suite. If it is red,
   fix it before moving to the next step. Do not proceed past a red checkpoint.
3. **Never fake data.** If a feature can't capture something, render it as "missing/not
   captured", never as a placeholder that implies data exists.
4. **Additive only.** New DB columns are nullable. New API fields are optional. Old app +
   new backend must still work. Every migration has a real `downgrade()`.
5. **Reuse, don't reinvent.** Each Part names an existing "rail" to reuse. If you find
   yourself writing a second copy of something that exists, STOP — you're doing it wrong.
6. **Test-first for pure logic.** Math/decisions (density formula, resume-phase, geofence)
   → write the unit test before the implementation.
7. **Stay in your lane per layer.** Screens never call Drift/`http` directly — go through
   services/providers. Backend routers call services/domain modules, not inline logic.
8. **When unsure of a fact, VERIFY IT** with a `grep`/read — do not guess file contents.
9. **Do not push. Do not open PRs.** Commit locally only. The human pushes.
10. **NEVER paste a literal placeholder.** Anything in `<angle brackets>` is a value YOU
    must resolve from the live repo, not text to copy. Resolve them like this:
    - `<HEAD>` (alembic parent revision) → run `cd backend && python -m alembic heads`
      and use that exact string.
    - A new alembic revision id → **do not invent one.** Run
      `cd backend && python -m alembic revision -m "short_slug"`. Alembic generates a
      valid, unique revision id AND the file skeleton (with `revision`, `down_revision`
      already filled to the current head). You then paste the `upgrade()`/`downgrade()`
      bodies this prompt gives you into that generated file. Never hand-write the
      revision id.
    - `<N>` / next Drift `schemaVersion` → run
      `grep -n "int get schemaVersion" lib/data/local/app_database.dart`, use that number,
      and bump to that number + 1.
    If you ever find a literal `<...>` string in a file you wrote, you made a mistake —
    go back and resolve it.
11. **After ANY Drift table/column/schemaVersion change**, you MUST regenerate the
    generated code: `dart run build_runner build --delete-conflicting-outputs`. The app
    will not compile until you do. Then run `flutter test`.

### Commands you will use constantly
```bash
# from repo root: c:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv
# --- backend ---
cd backend && python -m pytest -q                 # full backend suite
cd backend && python -m pytest tests/<file> -v    # one backend test file
cd backend && python -m alembic heads             # current migration head
cd backend && python -m alembic upgrade head      # apply migrations (throwaway/local db)
# --- app ---
flutter test                                       # full flutter suite
flutter test test/<file>                           # one flutter test file
flutter analyze lib/<file> test/<file>             # lint specific files (fast)
# --- portal ---
cd portal && npm test -- --run                     # full portal suite
cd portal && npx tsc --noEmit                      # type check
cd portal && npm run build                          # build
```

### GLOBAL PREFLIGHT — run before ANY Part, confirm all green
```bash
cd backend && python -m alembic heads            # note the value; expect c8d9e0f1a2b3 (or later)
grep -n "int get schemaVersion" lib/data/local/app_database.dart   # note the number; expect 26 (or later)
cd backend && python -m pytest -q                # must be all-pass before you touch anything
flutter test                                     # must be all-pass
cd portal && npm test -- --run                   # must be all-pass
```
If any suite is RED before you start, STOP and report — do not build on red.

---

# PART R1 — Entity-scoped evidence media (farmer + dispatch)

**Rail you MUST reuse:** the existing media pipeline — `SecureCaptureService` (capture) →
an `insert*WithOutbox` writer → `POST /api/v1/media` (`backend/routers/media.py`) →
`_uploadMedia` two-phase commit (`lib/services/sync_queue_manager.dart`). You are making
it *subject-agnostic*, not building a new one.

### R1 PREFLIGHT
```bash
cd backend && python -m alembic heads    # record as <HEAD>; your new migration chains from it
grep -n "class MediaFile" backend/models.py         # confirm line ~512
grep -n "X-Batch-UUID" backend/routers/media.py     # confirm the required header exists
grep -n "static const" lib/data/capture_types.dart  # confirm current capture types
grep -n "int get schemaVersion" lib/data/local/app_database.dart   # record as <N> (Drift)
grep -n "class SyncOutbox\|class MediaCaptures\|batchUuid" lib/data/local/tables.dart | head
```
**KNOWN FACTS you must design around (verified — do not fight them):**
- `SyncOutbox.batchUuid` is `text()()` → **NON-nullable**.
- `MediaCaptures.batchUuid` is `text().references(SystemMetadata, ...)()` → **non-nullable,
  has a foreign key to batches, and is part of the primary key `{batchUuid, captureType}`.**
- Therefore farmer/dispatch media (which has NO batch) **cannot** be written into
  `MediaCaptures` or enqueued with a non-null `batchUuid` as-is. **R1 REQUIRES a Drift
  schema change** (Steps R1-6b + R1-7 below). This is the single most important thing to
  get right; the batch media path must stay byte-for-byte unchanged.

### STEP R1-1 — Backend model: add subject columns (nullable)
1. Open `backend/models.py`, find `class MediaFile` (~line 512).
2. Directly after the `batch_uuid` column block, add:
```python
    # V8 deferred R1 — entity-scoped media. NULL subject_type = legacy row
    # (implicitly a batch, still referenced by batch_uuid above). When set,
    # media belongs to a farmer/dispatch instead of a batch.
    subject_type: Mapped[str] = mapped_column(String(16), nullable=True)   # 'batch'|'farmer'|'dispatch'
    subject_uuid: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
```
3. Save. Do NOT touch `batch_uuid` — legacy rows keep using it.

### STEP R1-2 — Backend migration
1. **Generate the migration file the safe way (do NOT hand-write a revision id):**
   ```bash
   cd backend && python -m alembic revision -m "media_add_subject_scope"
   ```
   This creates a new file under `backend/alembic/versions/` with a valid, unique
   `revision` id and `down_revision` already set to the current head. Open that new file.
2. Replace its empty `upgrade()`/`downgrade()` with these bodies (mirrors the
   `op.batch_alter_table` style used in `b7c1d2e3f4a5_portal_users_org_scoping.py`):
```python
def upgrade() -> None:
    with op.batch_alter_table("media_files") as batch_op:
        batch_op.add_column(sa.Column("subject_type", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("subject_uuid", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_media_files_subject_uuid", ["subject_uuid"])


def downgrade() -> None:
    with op.batch_alter_table("media_files") as batch_op:
        batch_op.drop_index("ix_media_files_subject_uuid")
        batch_op.drop_column("subject_uuid")
        batch_op.drop_column("subject_type")
```
   Ensure `import sqlalchemy as sa` and `from alembic import op` are present at the top
   (alembic's template usually includes them; add if missing).
3. Run `cd backend && python -m alembic heads` — it must show exactly ONE head (your new
   file's revision id). If it shows two heads, your `down_revision` is wrong — fix it to
   the value from the R1 PREFLIGHT.
4. **CHECKPOINT:** `cd backend && python -m alembic upgrade head` on a throwaway/local db
   must succeed with no error.

### STEP R1-3 — Backend ownership helpers
1. Open `backend/services/evidence.py`. Find `_assert_batch_ownership` — read how it
   works (looks up the entity, compares its device/project to the caller, raises 403).
2. Add two siblings in the same file, same shape:
```python
async def _assert_farmer_ownership(session, farmer_uuid: str, device_id: str) -> None:
    # mirror _assert_batch_ownership: load the Farmer, confirm it belongs to the
    # device's project; raise HTTPException(403, "not_your_farmer") otherwise.
    ...

async def _assert_dispatch_ownership(session, dispatch_uuid: str, device_id: str) -> None:
    # load the Dispatch; confirm dispatch.device_id == device_id;
    # raise HTTPException(403, "not_your_dispatch") otherwise.
    ...
```
   Use the exact imports/patterns already in `evidence.py` and how `routers/dispatch.py`
   checks `dispatch.device_id == device_id`. VERIFY those two rules by reading those files
   first.

### STEP R1-4 — Backend endpoint: accept subject scope
1. Open `backend/routers/media.py`, `upload_media` (~line 31).
2. Change `x_batch_uuid` from required to optional, and add two optional headers:
```python
    x_batch_uuid: Optional[str] = Header(None, alias="X-Batch-UUID"),
    x_subject_type: Optional[str] = Header(None, alias="X-Subject-Type"),
    x_subject_uuid: Optional[str] = Header(None, alias="X-Subject-UUID"),
    x_media_canonical: Optional[str] = Header(None, alias="X-Media-Canonical"),
```
3. Near the top of the body (after the existing header validations), add scope
   resolution:
```python
    # Deferred R1 — resolve exactly one media scope.
    has_batch = bool(x_batch_uuid and x_batch_uuid.strip())
    has_subject = bool(x_subject_type and x_subject_uuid)
    if has_batch and has_subject:
        raise HTTPException(status_code=400, detail="ambiguous_media_scope")
    if not has_batch and not has_subject:
        raise HTTPException(status_code=400, detail="missing_media_scope")
    if has_subject and x_subject_type not in ("farmer", "dispatch"):
        raise HTTPException(status_code=400, detail="invalid_subject_type")
```
4. Where the code currently does `_assert_batch_ownership(...)` and `_evaluate_anchor(...)`:
   - if `has_batch`: keep the EXACT existing path (ownership + EXIF anchor) unchanged.
   - if `has_subject` and `farmer`: call `_assert_farmer_ownership`, and SKIP
     `_evaluate_anchor` (no batch GPS to corroborate).
   - if `has_subject` and `dispatch`: call `_assert_dispatch_ownership`, SKIP anchor.
5. When persisting the `MediaFile`, set `subject_type`/`subject_uuid` for the subject
   case (leave `batch_uuid` NULL then); for the batch case set `batch_uuid` and leave
   subject columns NULL (unchanged).
6. **Signature (CRITICAL — byte-exact, do NOT paraphrase).** The media canonical is a
   6-line `\n`-joined string, defined in TWO places that MUST match byte-for-byte:
   `backend/security.py::verify_media_signature` and
   `lib/services/crypto_signer.dart::signMediaUpload`. The EXISTING v1 canonical is
   exactly (leave it UNCHANGED for old apps):
   ```
   POST\n/api/v1/media\n{idempotency_key}\n{declared_sha256_lower}\n{batch_uuid}\n{device_id}
   ```
   Add a **v2** canonical, selected when the request has header `X-Media-Canonical: 2`.
   v2 is identical EXCEPT line 5 (the batch slot) becomes `{subject_type}:{subject_uuid}`
   (a literal colon between them). Exactly:
   ```
   POST\n/api/v1/media\n{idempotency_key}\n{declared_sha256_lower}\n{subject_type}:{subject_uuid}\n{device_id}
   ```
   In `security.py`, branch inside `verify_media_signature`: if the v2 header is present,
   build line 5 as `f"{x_subject_type}:{x_subject_uuid}"`; else use `x_batch_uuid or ""`
   exactly as today. (You'll need to add `x_subject_type`/`x_subject_uuid`/
   `x_media_canonical` as `Header(None, ...)` params to `verify_media_signature` too.)
   The Dart side is Step R1-7.4. Both sides get pinned by the cross-language test in
   Step R1-5 (`test_v2_canonical_verifies_and_tamper_rejected`) — that test is what
   proves you got the bytes identical.

### STEP R1-5 — Backend tests (write these, then make them pass)
1. Create `backend/tests/test_media_entity_scope.py`. Mirror the helper style in
   `backend/tests/test_field_walk.py` (device-signed requests via
   `tests/remediation/crypto_utils.py`, admin login helper, seed helpers).
2. Write these test cases (names are self-describing):
   - `test_farmer_media_upload_happy_path`
   - `test_dispatch_media_upload_happy_path`
   - `test_batch_media_backcompat_unchanged` (batch-only headers behave as today)
   - `test_both_scopes_rejected_400`
   - `test_no_scope_rejected_400`
   - `test_foreign_device_farmer_upload_403`
   - `test_foreign_device_dispatch_upload_403`
   - `test_v2_canonical_verifies_and_tamper_rejected`
   - `test_duplicate_idempotency_key_is_noop`
3. Create `backend/tests/test_media_subject_scope_migration.py` — mirror
   `backend/tests/test_org_scoping_migration.py` (drives alembic upgrade/downgrade on a
   throwaway sqlite file; asserts legacy rows survive with NULL subject_type).
4. **CHECKPOINT:** `cd backend && python -m pytest tests/test_media_entity_scope.py
   tests/test_media_subject_scope_migration.py -v` → all green. Then full
   `python -m pytest -q` → all green (no regressions).

### STEP R1-6 — App: capture types
1. Open `lib/data/capture_types.dart`. Add inside `class CaptureType`:
```dart
  // Deferred R1 — farmer + dispatch media (entity-scoped, via /api/v1/media).
  static const farmerSignature = 'farmer_signature';
  static const farmerIdDocument = 'farmer_id_document';
  static const fpicConsentPdf = 'fpic_consent_pdf';
  static const fpicHoldingPhoto = 'fpic_holding_photo';
  static const dispatchTruckPhoto = 'dispatch_truck_photo';
  static const dispatchInvoicePhoto = 'dispatch_invoice_photo';
  static const dispatchWeighTicket = 'dispatch_weigh_ticket';
```
2. `flutter analyze lib/data/capture_types.dart` → no issues.

### STEP R1-7a — App: Drift schema change (REQUIRED — the non-null batchUuid problem)
Entity media has no batch, but `SyncOutbox.batchUuid` and `MediaCaptures.batchUuid` are
non-nullable (and `MediaCaptures` PK includes batchUuid + has an FK to batches). You will
therefore, in `lib/data/local/tables.dart`:
1. Make `SyncOutbox.batchUuid` nullable: change `TextColumn get batchUuid => text()();`
   → `TextColumn get batchUuid => text().nullable()();`. (This is additive/back-compat:
   existing rows always have a value; only new entity-media ops will be null.)
2. Add a NEW table for the local record of entity media (do NOT touch `MediaCaptures` —
   changing its PK/FK is risky and would disturb the batch path):
   ```dart
   class EntityMediaCaptures extends Table {
     TextColumn get subjectType => text()();      // 'farmer' | 'dispatch'
     TextColumn get subjectUuid => text()();
     TextColumn get captureType => text()();
     TextColumn get sandboxPath => text()();
     TextColumn get sha256Hash => text()();
     BoolColumn get isMockLocation => boolean().withDefault(const Constant(false))();
     TextColumn get createdAt => text()();
     @override
     Set<Column> get primaryKey => {subjectUuid, captureType};
   }
   ```
3. Register `EntityMediaCaptures` in the `@DriftDatabase(tables: [...])` list in
   `lib/data/local/app_database.dart` (find the existing `tables:` list, add it).
4. Bump `schemaVersion` from `<N>` (R1 PREFLIGHT) to `<N>+1`, and in the
   `MigrationStrategy.onUpgrade` add a numbered step that (a) `createTable(entityMediaCaptures)`
   and (b) is a no-op for the SyncOutbox nullability change on SQLite (SQLite treats the
   column as-is; the generated schema just stops enforcing NOT NULL for new rows — confirm
   by reading how prior `from <= N` steps are written and mirror one).
5. Regenerate: `dart run build_runner build --delete-conflicting-outputs`.
6. Add a migration test `test/migration_v<N+1>_entity_media_test.dart` mirroring an
   existing `test/migration_vNN_*_test.dart`: assert the new table exists after upgrade
   and that an entity-media row inserts with a null-batchUuid outbox op.
7. **CHECKPOINT:** `flutter test test/migration_v<N+1>_entity_media_test.dart` green.

### STEP R1-7b — App: subject-aware media writer
1. Open `lib/data/local/pyrolysis_writer.dart`, read `insertMediaCaptureAndEnqueue`
   (it writes a `mediaCaptures` row + a `media` outbox op with a signed JSON payload,
   `batchUuid` set on both).
2. Add a sibling `insertEntityMediaWithOutbox({required String subjectType, required
   String subjectUuid, required String captureType, required String sandboxPath,
   required String sha256Hash, required bool isMockLocation})` that:
   - writes an `EntityMediaCaptures` row (NOT `mediaCaptures`);
   - builds the JSON payload with `subject_type`/`subject_uuid` (and the same
     `photo_path`/`sha256_hash`/`capture_type`/`isMockLocation` keys) but **NO**
     `batch_uuid` key;
   - enqueues a `SyncOutbox` row with `batchUuid: const Value(null)`,
     `targetTable: 'media'`, that same `payloadJson`, and the `signPayload` signature.
   Keep the signing call; do not fork the sync flow.

### STEP R1-7c — App: sync manager handles the null-batch / subject case
1. Open `lib/services/sync_queue_manager.dart`, find `_uploadMedia` and the media branch.
2. First, `grep -n "\.batchUuid" lib/services/sync_queue_manager.dart` and guard every
   place that assumes a non-null `entry.batchUuid` for a media op — entity-media ops now
   have null batchUuid. Do not crash on null.
3. In `_uploadMedia`: read `subject_type`/`subject_uuid` from the decoded payload. If
   present (entity media), send headers `X-Subject-Type`, `X-Subject-UUID`, and
   `X-Media-Canonical: 2`, and sign with `signMediaUploadV2` (Step R1-7d). Do NOT send
   `X-Batch-UUID`. Otherwise (batch media, payload has `batch_uuid`) keep the existing
   path 100% unchanged.

### STEP R1-7d — App: v2 signing
1. Open `lib/services/crypto_signer.dart`, find `signMediaUpload` (~line 210). Add
   `signMediaUploadV2({required String idempotencyKey, required String declaredSha256,
   required String subjectType, required String subjectUuid, required String deviceId})`
   that builds the EXACT v2 canonical from Step R1-4.6:
   ```dart
   final canonical =
       'POST\n/api/v1/media\n$idempotencyKey\n'
       '${declaredSha256.toLowerCase()}\n$subjectType:$subjectUuid\n$deviceId';
   ```
   and signs it exactly like `signMediaUpload` does (same `_algo.sign` + base64Url).

### STEP R1-7e — App test
1. Create `test/entity_media_outbox_test.dart` — mirror `test/farmer_outbox_test.dart`.
   Assert: farmer/dispatch media enqueues a `media` op with `subject_type` set,
   `batchUuid` null, correct capture_type, no PII in payload; an `EntityMediaCaptures`
   row is written; `signMediaUploadV2` produces a signature over the exact v2 canonical.
2. **CHECKPOINT:** `flutter test test/entity_media_outbox_test.dart` → green, then full
   `flutter test` → green (the Drift bump didn't regress anything).

### STEP R1-8 — App: farmer KYC capture UI
1. Open `lib/ui/screens/farmer_kyc_screen.dart`. Find where the form is submitted
   (`insertFarmerWithOutbox` call). Read how the screen is structured (it has the draft
   persistence + lookup rows already from Part J).
2. Add four capture rows (each opens `SecureCameraScreen` via
   `Navigator.push<SecureCaptureResult>` — mirror how `pyrolysis_screen.dart::_captureStage`
   does it), each producing media via `insertEntityMediaWithOutbox(subjectType: 'farmer',
   subjectUuid: <the farmer uuid>, captureType: <one of the four farmer types>, ...)`:
   - signature photo → `CaptureType.farmerSignature`
   - ID document photo → `CaptureType.farmerIdDocument`
   - FPIC signed-PDF (file pick OR photo) → `CaptureType.fpicConsentPdf`
   - FPIC holding photo → `CaptureType.fpicHoldingPhoto`
3. Each row shows "not captured" until captured. NONE blocks saving the farmer.
4. **VERIFY the record/media ordering:** read `backend/routers/farmers.py` — confirm it
   stores `signature_media_id` etc. as a plain string (it does per audit). The farmer
   record can reference a media UUID that hasn't uploaded yet; the portal shows "pending".
5. Create `test/farmer_kyc_media_test.dart`: tapping a capture row + returning a
   `SecureCaptureResult` enqueues a farmer-scoped media op; farmer still saves with zero
   media.
6. **CHECKPOINT:** `flutter analyze lib/ui/screens/farmer_kyc_screen.dart` clean;
   `flutter test test/farmer_kyc_media_test.dart` green.

### STEP R1-9 — App: dispatch capture UI
1. Open `lib/ui/screens/dispatch/dispatch_screen.dart`. Add capture rows for truck photo,
   invoice photo, weigh-ticket (photo/PDF) via `insertEntityMediaWithOutbox(subjectType:
   'dispatch', subjectUuid: <dispatch uuid>, ...)`. Same optional-but-tracked pattern.
2. Create `test/dispatch_media_test.dart`: capturing a truck photo enqueues a
   dispatch-scoped media op; dispatch still submittable with no media.
3. **CHECKPOINT:** analyze clean; `flutter test test/dispatch_media_test.dart` green.

### STEP R1-10 — Portal: render entity media
1. Open `portal/src/api.ts`. Extend the media type with `subject_type`/`subject_uuid`;
   add fetchers for farmer media + dispatch media (mirror existing media fetchers).
2. On the farmer detail + dispatch detail pages, render attached media using the existing
   `EvidenceGallery` component, with an honest empty state.
3. Any new/changed page: add to `portal/src/__tests__/a11y.test.tsx` (zero violations),
   use cursor pagination if a list can grow.
4. Extend the relevant portal tests.
5. **CHECKPOINT:** `cd portal && npm test -- --run && npx tsc --noEmit && npm run build`
   → all green.

### R1 FINAL CHECK + COMMIT
```bash
cd backend && python -m pytest -q       # all green
flutter test                            # all green
cd portal && npm test -- --run && npx tsc --noEmit && npm run build   # all green
```
Then: `git add -A && git commit -m "feat: entity-scoped evidence media (farmer + dispatch) via one media rail"`
(one commit; do NOT push).

**R1 DONE when:** all three suites green, one media rail serves all subjects, v1 signature
still valid (old app + new backend), farmer + dispatch media capture/sync/render,
foreign-device uploads 403, the Drift bump (nullable SyncOutbox.batchUuid +
EntityMediaCaptures table) has a passing migration test, and the batch media path is
byte-for-byte unchanged (back-compat tests prove it).

---

# PART R2 — Dispatch flow durability (do AFTER R1)

**Rail to reuse:** the SharedPreferences draft pattern already used by the farmer KYC
draft (Part J) — read `lib/ui/screens/farmer_kyc_screen.dart` for the `_saveDraft` /
`_loadDraft` / restored-banner pattern.

### STEP R2-1 — Pure resume logic (test-first)
1. Create `test/dispatch_wizard_resume_test.dart` FIRST. Test a pure function
   `resolveResumePhase(persistedPhase, serverStatus)`:
   - persisted behind server → resume to server's phase (trust server)
   - persisted ahead of server → resume to server's phase
   - equal → resume to that phase
   - no persisted → fresh (no banner)
2. Implement `resolveResumePhase` as a pure top-level function in
   `lib/services/dispatch_service.dart` (or a small new `dispatch_resume.dart`).
3. **CHECKPOINT:** `flutter test test/dispatch_wizard_resume_test.dart` green.

### STEP R2-2 — Persist + restore
1. In `lib/services/dispatch_service.dart` add `saveInFlightPhase(uuid, phase)`,
   `loadInFlightPhase(uuid)`, `clearInFlightPhase(uuid)` (SharedPreferences, key
   `dmrv.dispatch_wizard.<uuid>`). Add a code comment: only a uuid + phase enum are
   stored here (non-PII), which is why SharedPreferences is acceptable.
2. In `dispatch_screen.dart`: on init, if a persisted phase exists for the active
   dispatch, call `resolveResumePhase` against server status and restore, showing a
   dismissible "resumed your in-progress dispatch" banner. Save on each transition; clear
   on `received` / abandon.
3. Add screen test: persisted phase restored on reopen; cleared on received; fresh
   dispatch shows no banner.
4. **CHECKPOINT:** `flutter test` (full) green.

### R2 COMMIT
`git commit -m "feat(app): restart-resilient dispatch wizard (resume in-flight phase)"`

---

# PART R3 — Density calibration capture (independent)

**Rail to reuse (app BLE):** `lib/services/ble_weight_scale_service.dart` +
`lib/providers/yield_scale_notifier.dart` (the yield-weighing BLE stack). Inject the
same; do NOT write new BLE code.

**⚠️ VERIFIED REALITY — the backend has NO device endpoint for this.** The only
density-create route is **`POST /portal/bulk-density-tests`** with
**`require_role("admin")`** (`backend/portal/routes.py:489`) — it is portal/admin-only, a
human logs in with a password. A field DEVICE (Ed25519-signed, no admin password) CANNOT
call it. Also, its schema (`BulkDensityTestCreate`, `backend/portal/schemas.py:150`)
takes `density_kg_per_l` as a REQUIRED client value — i.e. the server currently trusts the
client's density. So "reuse F's endpoint / server is source of truth" is NOT achievable
as-is. You must resolve the fork in R3-0 FIRST.

### STEP R3-0 — Design fork (decide + record before any code)
Pick ONE and write it into `docs/DEFERRED_WORK_EXECUTION_PLAN.md` R3 slot:
- **(A, RECOMMENDED) Add a new device-signed endpoint** `POST /api/v1/density-tests` in a
  new `backend/routers/density.py`, mirroring `backend/routers/dispatch.py` (device auth
  via `verify_signature`, client-generated `test_uuid` PK, upsert-on-conflict, project
  resolved from the device). It accepts `mass_kg` + `volume_l` and **computes
  `density_kg_per_l = mass_kg / volume_l` SERVER-SIDE** (this is what makes the server the
  source of truth, satisfying `§0.1.4`). Register it in `backend/app_factory.py` like the
  other routers. Then the app calls THIS endpoint, not the admin one.
- **(B) Keep density admin/portal-only** — then this item is NOT an app feature; it's a
  portal form. If you pick B, the "app-side" deferred item is reclassified as "portal
  density entry" and there is no Flutter screen. Only pick B if the human explicitly says
  density is a lab/admin task, not a field task.

Default to **(A)** unless told otherwise. The rest of R3 assumes (A).

### STEP R3-1 — Backend: new device-signed density endpoint (option A)
1. Create `backend/routers/density.py` mirroring `backend/routers/dispatch.py`'s
   device-auth + idempotent-upsert shape. `POST /api/v1/density-tests`:
   device-signed; body `{test_uuid, volume_l, mass_kg, performed_at?}`; compute
   `density_kg_per_l = mass_kg / volume_l` server-side (reuse
   `backend/services/bulk_density.py`'s pure helper if one exists — grep it); persist a
   `BulkDensityTest`; upsert on `test_uuid` (duplicate = no-op, `§0.7.2`); resolve
   `project_id` from the device's enrollment.
2. Add explicit Pydantic request/response schemas in `backend/schemas.py`.
3. Register the router in `backend/app_factory.py` (add `from routers.density import
   router as density_router` + `application.include_router(density_router)`).
4. Create `backend/tests/test_density_endpoint.py` mirroring
   `backend/tests/test_dispatch_endpoint.py`: happy path (server computes density from
   mass/volume); duplicate test_uuid is idempotent; volume<=0 rejected; foreign device /
   unenrolled rejected.
5. **CHECKPOINT:** `cd backend && python -m pytest tests/test_density_endpoint.py -v`
   then full `-q` → green.

### STEP R3-2 — App: pure display-density math (test-first)
1. Create `test/density_calibration_test.dart`. Test a pure helper
   `displayDensityKgPerL(massKg, volumeL)` = `massKg / volumeL` (guard volume<=0 → null).
   Pin it equal to the server formula on a shared fixture (server: `mass_kg / volume_l`).
   This is DISPLAY ONLY — the server recomputes and stores the authoritative value.
2. Implement the helper in a new `lib/services/density_service.dart`.

### STEP R3-3 — App: service + screen
1. `lib/services/density_service.dart`: `submitDensityTest({...})` — client-generated
   `test_uuid`; direct signed call to `POST /api/v1/density-tests` (mirror
   `lib/services/dispatch_service.dart`'s `signRequestV2` + headers pattern); submit
   `mass_kg` + `volume_l` (+ optional BLE mass). Returns the server's stored density.
2. `lib/ui/screens/density_calibration_screen.dart` (NEW): operator enters/reads mass +
   volume, sees the display density, submits, shows the server's confirmed value. Reuse
   the BLE weight-scale widget/notifier.
3. Add an always-accessible tile in `lib/ui/screens/dashboard_screen.dart` (mirror the
   Dispatch / Field-Walk tiles — read how those were added).
4. i18n: add all new strings to `lib/l10n/app_en.arb` + `lib/l10n/app_hi.arb`.
5. Extend `test/density_calibration_test.dart`: submit sends correct payload; BLE mass
   populates the field; i18n keys resolve.
6. **CHECKPOINT:** `flutter analyze` on the new files clean; full `flutter test` green.

### R3 COMMIT
`git commit -m "feat: device-signed density calibration capture (server-computed) feeding the F fallback"`

---

# PART R4 — On-device parcel geometry + geofence gate (independent; MEDIUM)

**Reality check first:** the app has NO parcel geometry on-device today. The device
endpoint `GET /api/v1/parcels` (`backend/routers/batches.py`) returns only
`{parcel_uuid, name}` by design. `lib/services/geofence_check.dart` is built but unused.
This Part is backend + local-schema + wiring — not just wiring.

### STEP R4-0 — Record the design decision
1. Add a new env flag `DMRV_DEVICE_PARCEL_GEOMETRY` (default **off**) in the backend
   settings module (mirror an existing flag in `backend/settings.py`).
2. Write 3 sentences in `docs/DEFERRED_WORK_EXECUTION_PLAN.md` R4 runbook slot: geometry
   exposure is off by default, rolled out deliberately; off = today's behavior exactly.

### STEP R4-1 — Backend: flag-gated geometry in the parcels response
1. `backend/routers/batches.py`, `GET /api/v1/parcels`: when the flag is on, include
   `boundary_geojson` (+ bbox) per parcel, scoped to the device's project. When off,
   unchanged. Explicit Pydantic response model.
2. `backend/tests/test_device_parcel_geometry.py` (NEW): flag-off → no geometry
   (back-compat); flag-on → geometry present + project-scoped; foreign project excluded.
3. **CHECKPOINT:** `cd backend && python -m pytest tests/test_device_parcel_geometry.py -v`
   then full `-q` → green.

### STEP R4-2 — App: cache geometry (Drift bump)
1. Re-read `grep -n "int get schemaVersion" lib/data/local/app_database.dart` — note N.
2. `lib/data/local/tables.dart`: add a `parcel_geometry` table (`parcel_uuid` TEXT PK,
   `boundary_geojson` TEXT). `app_database.dart`: bump `schemaVersion` N → N+1, add a
   numbered `MigrationStrategy` step. (If another parallel Part also bumped it, take the
   next free integer — re-verify.)
3. Regenerate Drift: `dart run build_runner build --delete-conflicting-outputs`.
4. `lib/services/parcel_service.dart`: cache geometry when present; add
   `boundaryRingFor(parcelUuid)` returning `List<List<double>>?` (null when absent).
5. `test/parcel_geometry_cache_test.dart` (NEW): geometry cached + retrieved; absent →
   null; Drift migration test (mirror an existing migration_vNN test).
6. **CHECKPOINT:** `flutter test test/parcel_geometry_cache_test.dart` green.

### STEP R4-3 — Wire the gate into capture
1. Find the batch-evidence capture call sites (`grep -rn "\.capture(" lib/ui` and
   `lib/services/secure_capture_service.dart`). At each, pass
   `parcelBoundaryRing: <parcelService>.boundaryRingFor(<batch's parcelUuid>)`.
2. The gate behavior already exists in `secure_capture_service.dart` — you are only
   feeding it data. Absent geometry → null ring → capture proceeds ungated (grandfather).
3. `test/geofence_capture_wiring_test.dart` (NEW): in-bounds passes; out-of-bounds trips
   the existing gate; no geometry → ungated.
4. Observability: confirm a geofence trip emits a metric/log (add if missing, mirror an
   existing gate).
5. **CHECKPOINT:** full `flutter test` + `cd backend && python -m pytest -q` green.

### R4 COMMIT
`git commit -m "feat: flag-gated on-device parcel geometry + live geofence capture gate"`

---

# PART R5 — i18n retrofit of farmer_kyc_screen (do AFTER R1)

**Rail to reuse:** `lib/l10n/app_en.arb` + `lib/l10n/app_hi.arb` + `AppLocalizations`.
Read another already-localized screen (e.g. `dashboard_screen.dart`) to copy the usage
pattern.

### STEP R5-1 — Extract + wire
1. `grep -n "'" lib/ui/screens/farmer_kyc_screen.dart` — find every hardcoded
   user-facing English string (INCLUDING R1's new capture labels).
2. Add each to `app_en.arb` + `app_hi.arb` with descriptive keys (follow the existing key
   naming convention in those files). Provide real Hindi translations in `app_hi.arb`.
3. Replace each literal with `AppLocalizations.of(context)!.<key>`.
4. Extend `test/l10n_test.dart`: the existing "English loads all strings" / "no hardcoded
   Hindi strings remain" tests must still pass and now cover the new keys.
5. **CHECKPOINT:** `flutter analyze lib/ui/screens/farmer_kyc_screen.dart` clean;
   `flutter test` green.

### R5 COMMIT
`git commit -m "feat(app): localize farmer KYC screen (en + hi)"`

---

# PART R6 — Day-start audit lock (OPTIONAL — build only if elected)

If NOT building it: add one line to the PLAN's `§7-DELTA` — "R6 elected-out (optional per
blueprint)" — and skip. Do not silently drop it.

If building it:
### STEP R6-1 — Spec it in writing first
Write the exact rule in the PLAN R6 slot: what the operator attests (device time correct,
correct project, calibration in date), when the lock triggers (before the day's first
capture), and that it grandfathers existing devices + is env-flagged default-off.

### STEP R6-2 — Pure gate + thin UI
1. Test-first: `test/daystart_lock_test.dart` — pure `isDayStartValid(lastAttestation,
   now, config)` (fresh / stale / same-day); gate-off → always valid (grandfather).
2. Implement the pure gate; add a thin acknowledgement screen; persist attestation
   (SharedPreferences — an attestation is not PII; comment why). Env flag
   `DMRV_DAYSTART_LOCK` default off.
3. i18n en+hi for the new screen.
4. **CHECKPOINT:** three suites green.

### R6 COMMIT
`git commit -m "feat(app): optional day-start audit lock (env-gated, default off)"`

---

# PART R7 — iOS build validation (docs only — THIS HOST CANNOT BUILD iOS)

**Do NOT fake a pass.** You are on Windows; you cannot run `pod install`/Xcode.

### STEP R7-1 — Write the runbook
Create `docs/IOS_BUILD_RUNBOOK.md` with the EXACT macOS steps: Flutter + CocoaPods
versions, `flutter precache --ios`, `cd ios && pod install`, open `Runner.xcworkspace`,
set signing team, `flutter build ios --release`, and a per-plugin iOS smoke-test list
(camera, geolocator, mobile_scanner, freerasp, flutter_secure_storage, BLE). Note that
`ios/Runner/Info.plist` ALREADY has the needed permission strings (camera, location,
bluetooth, photo library) — do not re-add. Record known unknowns: no `Podfile` yet
(first `pod install` creates it), mobile_scanner iOS min 12.0 vs project target 13.0
(compatible).

### STEP R7-2 — Keep the gate honest
In the PLAN `§7-DELTA`, leave the iOS line as "iOS build UNVERIFIED — needs a macOS
runner". It is NOT done until a Mac confirms the runbook produces a launchable build.

### R7 COMMIT
`git commit -m "docs: iOS build runbook (macOS-gated; build unverified on this host)"`

---

## FINAL: after all elected Parts land
Run the full three-suite regression ONE more time on the merged tree (not just per-Part):
```bash
cd backend && python -m pytest -q
flutter test
cd portal && npm test -- --run && npx tsc --noEmit && npm run build
```
All green = the deferred backlog is closed (except iOS, which stays macOS-pending, and any
optional Part explicitly elected-out). Update `docs/DEFERRED_WORK_EXECUTION_PLAN.md`
`§7-DELTA` checkboxes and the migration/Drift ledger. Do NOT push — the human does that.
