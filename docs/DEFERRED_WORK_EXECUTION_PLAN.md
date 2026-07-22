# TerraCipher dMRV — Deferred-Work Execution Plan (phase-by-phase, code-exact)

**What this is.** The follow-on build plan that closes every item that was *honestly
deferred* while Parts 0–5 of `PRODUCTION_EXECUTION_PLAN.md` were executed. Those Parts
shipped the compliance/anti-fraud moat; this plan retires the "noted, not fabricated"
backlog those Parts left behind. Same discipline, same shape: ordered, test-gated,
non-breaking phases with **exact file paths, migration chaining, test files, and
Definition-of-Done gates**.

**How to use it.** Execute one **Part** per session/PR. Do not start a Part until the
previous Part it depends on is DoD-green. Each Part is written so an engineer *or an
agent with no prior context* can execute it without re-deriving anything. `§0` below is
**not repeated** — it is `PRODUCTION_EXECUTION_PLAN.md §0 Engineering Constitution`, and
it is **binding here verbatim**. Read it first. The `§0-DELTA` section below adds only the
rules specific to this backlog.

**State this plan was written against (verify before starting — see `§Verify`):**
- Alembic HEAD revision: **`c8d9e0f1a2b3`** (`create_field_walk_tracks_table`).
- Drift schema version: **v26** (`lib/data/local/app_database.dart:68`).
- Capture types defined: `lib/data/capture_types.dart` — `batch_photo, flame_curtain,
  quenching, flame_height, post_burn_mass, packaging, end_use, lab_certificate,
  quenching_video, density_video` (no farmer/dispatch types yet).
- Media endpoint: `POST /api/v1/media` (`backend/routers/media.py:26`) — currently
  **batch-scoped**: `X-Batch-UUID` is a *required* header; `MediaFile.batch_uuid`
  (`backend/models.py:522`) is already **nullable** (no FK — see its docstring).
- Sync routing maps: `kEndpointByTable` / `kCaptureTypeByTable`
  (`lib/services/sync_queue_manager.dart`).
- Three suites all green at plan-authoring time: backend `pytest` (608 passed / 2
  skipped), app `flutter test` (339 passed), portal `vitest` (151 passed).

---

## §0-DELTA. Rules specific to this backlog (in addition to `PRODUCTION_EXECUTION_PLAN.md §0`)

1. **Generalize, don't duplicate.** Two deferred items (farmer media, dispatch media)
   are the *same shape*: "attach signed evidence to a non-batch entity." Do **not** ship
   two bespoke endpoints. Extend the ONE media rail (`routers/media.py` +
   `MediaFile`) to be entity-scoped, then let both consumers ride it. A second copy of
   the media pipeline is an automatic DoD failure.
2. **A deferred item stays deferred honestly until its Part lands.** Until a Part below
   is DoD-green, the feature renders as *absent*, never faked. E.g. a farmer with no
   uploaded signature shows "no signature on file", not a placeholder that implies one
   exists. This is `§0.1.5` (never fabricate) applied to the backlog.
3. **Reuse existing rails first, prove it in the PR description.** Every Part here has an
   existing rail it must ride (the media pipeline, the BLE weight-scale service, the
   `SecureCaptureService`, the l10n `.arb` files, the outbox). The PR must name which
   rail it reused. "I wrote a new X" where an X exists is rejected.
4. **Environment-blocked items get a runbook + a machine-checkable gate, not a fake
   pass.** The iOS build (Part R7) cannot be executed on the Windows dev host. Its DoD
   is a documented, reproducible checklist a macOS runner (human or CI) executes — never
   a "looks fine" sign-off from a host that cannot build it.
5. **Collision map is binding (see `§1`).** Some Parts edit the same file
   (`farmer_kyc_screen.dart`, `dispatch_screen.dart`). The sequencing in `§1` exists to
   prevent two Parts fighting over one file. If you parallelize (execution-graph mode,
   `§1.1`), you MUST use the isolation rules there — do not run two colliding Parts on
   the same working tree.

---

## §1. Dependency graph & sequencing

```
R1  Entity-scoped evidence media  ── generalizes the media rail; farmer + dispatch consume it
        │        (touches: routers/media.py, models.py, farmer_kyc_screen.dart,
        │         dispatch_screen.dart, capture_types.dart, sync_queue_manager.dart)
        ├────────────► R2  Dispatch flow durability  (touches dispatch_screen.dart)
        └────────────► R5  i18n retrofit farmer_kyc  (touches farmer_kyc_screen.dart)

R3  Density calibration capture (app)   ── independent (reuses BLE weight-scale service)
R4  On-device parcel geometry + geofence gate  ── independent (design decision inside)
R6  Day-start audit lock (OPTIONAL)     ── independent
R7  iOS build validation (macOS-gated)  ── independent; doc + checklist only, no code path
```

**Ordering rule.** `R1` is the keystone: it edits both `farmer_kyc_screen.dart` and
`dispatch_screen.dart`, which `R5` and `R2` also edit. Land **R1 first**, then R2 and R5
may proceed. R3, R4, R6, R7 have no ordering dependency on anything.

### §1.1 Execution-graph note (if running Parts in parallel across agents)

This backlog is deliberately shaped so that **most of it parallelizes**, but only along
the safe cut lines below. This is the "graph engineering" cut — nodes that never write the
same file, joined by an explicit merge/verify step.

- **Safe to run fully in parallel, each in its own git worktree** (zero shared files):
  **R3** (density — new screen + service), **R4** (geometry — new device endpoint field
  + new Drift table + new gate wiring), **R6** (day-start — new feature), **R7** (docs
  only). Fan these out; each verifies its own three suites; merge on green.
- **Must be serialized (shared files):** **R1 → then {R2, R5}**. R1 changes the media
  rail and both entity screens; R2 and R5 each re-touch one of those screens. Run R1 to
  green + merge FIRST, then R2 and R5 may themselves run in parallel (they touch
  *different* screens: dispatch vs farmer).
- **Drift version numbers are a shared resource.** **R1 (26→27)**, R4, and R6 all may bump
  `schemaVersion`. R1 is the keystone and lands first (→27). Any Drift-bumping Part after
  it **must rebase, re-read `lib/data/local/app_database.dart:68`, and take the next free
  integer** before landing. Never assume the number from this doc — re-verify (`§Verify`).
  Because R1 now also touches Drift, do NOT run R4/R6's Drift bump in a worktree
  concurrently with R1 — let R1 merge first, then they take 28, 29, ….
- **Merge/verify node:** after any parallel fan-out, run the FULL three-suite regression
  once on the merged tree (not just per-branch) before declaring the batch done — a
  clean per-branch run does not prove the merge is clean.

---

## §Verify — re-confirm before EACH Part (fresh session)

Run these and confirm they match this doc's assumptions; if they drifted, update the
Part's anchors before coding:

```bash
# Backend migration head (expect c8d9e0f1a2b3, or later if a prior Part landed)
cd backend && python -m alembic heads

# Drift schema version (expect 26, or later if a prior Part landed)
grep -n "int get schemaVersion" lib/data/local/app_database.dart

# Three suites are green BEFORE you start (never build on red)
cd backend && python -m pytest -q
flutter test
cd portal && npm test -- --run && npx tsc --noEmit && npm run build
```

---

## PART R1 — Entity-scoped evidence media (farmer signature/ID/consent + dispatch photos)

**Goal.** Close deferred items **#1 (farmer media)** and **#2 (dispatch media)** with ONE
generalized media rail. The DB hooks for farmer media already exist and are unused today
(`Farmer.signature_media_id`, `FarmerDocument.media_id`,
`FarmerConsent.signed_pdf_media_id`, `FarmerConsent.holding_photo_media_id` —
`backend/models.py`); nothing ever populates them because there is no farmer-scoped
upload path. Dispatch has no media fields at all. Both are the same problem.

**Why one Part.** `§0-DELTA.1`. The media pipeline (`SecureCaptureService` →
`insert*WithOutbox` → `POST /api/v1/media` → `_uploadMedia` two-phase commit) is fully
built and battle-tested for batch evidence. We make it *subject-agnostic* once, then wire
two thin consumers.

### R1.1 — Backend: make `MediaFile` + the media endpoint entity-scoped (additive)

- **Model** (`backend/models.py`, `MediaFile` at :512). Add two **nullable** columns:
  - `subject_type: Mapped[str] = mapped_column(String(16), nullable=True)` — one of
    `'batch' | 'farmer' | 'dispatch'`. NULL = legacy row (implicitly a batch).
  - `subject_uuid: Mapped[str] = mapped_column(String(36), nullable=True, index=True)` —
    the farmer_uuid / dispatch_uuid when `subject_type != 'batch'`.
  - Keep `batch_uuid` exactly as-is for back-compat; when `subject_type='batch'` the
    existing `batch_uuid` column remains the reference (do NOT migrate batch rows onto
    the new columns — grandfather them, `§0.3.2`).
- **Migration** (`backend/alembic/versions/<newrev>_media_add_subject_scope.py`):
  chains from HEAD (`§Verify`). `upgrade()` adds the two nullable columns + the index on
  `subject_uuid` via `op.batch_alter_table("media_files")`. Real `downgrade()` drops
  both. No data rewrite (legacy rows keep NULL subject_type). Follow the exact style of
  `b7c1d2e3f4a5_portal_users_org_scoping.py`.
- **Endpoint** (`backend/routers/media.py:26`, `upload_media`). Make `X-Batch-UUID`
  **optional** and add two optional headers `X-Subject-Type` / `X-Subject-UUID`:
  - Exactly-one-scope rule: reject (400 `ambiguous_media_scope`) if both a batch scope
    and a non-batch subject are supplied, and reject (400 `missing_media_scope`) if
    neither is. This keeps every media row attributable to exactly one subject.
  - `subject_type='batch'` (or the legacy batch-only header) → **unchanged code path**,
    including `_assert_batch_ownership` and `_evaluate_anchor` EXIF corroboration.
  - `subject_type='farmer'` → assert the farmer exists and belongs to the uploading
    device's project (new helper `_assert_farmer_ownership` in `services/evidence.py`,
    mirroring `_assert_batch_ownership`). Farmer media does **not** run the batch EXIF
    anchor (a signature photo has no batch GPS to corroborate) — skip cleanly.
  - `subject_type='dispatch'` → assert the dispatch exists and
    `dispatch.device_id == device_id` (reuse the dispatch ownership rule from
    `routers/dispatch.py`).
- **Signature canonical (CRITICAL, `§0.3.3`).** The frozen media canonical
  (`security.py::verify_media_signature`, and app-side `CryptoSigner.signMediaUpload`)
  currently binds `X-Batch-UUID`. Introduce a **v2 media canonical** that binds
  `subject_type|subject_uuid` instead, selected by a new `X-Media-Canonical: 2` header.
  v1 (no header) stays byte-for-byte valid for existing app builds (`§0.3.5`, no lockstep
  deploy). Pin both with a cross-language byte-exact test (mirror the existing canonical
  pin test).
- **Schemas** (`backend/schemas.py`): extend `MediaUploadResponse` only if a new field is
  needed; otherwise no change. No `dict[str,Any]` (`§0.2.5`).
- **Tests** (`backend/tests/test_media_entity_scope.py`, NEW):
  happy path farmer-media upload; happy path dispatch-media upload; back-compat
  (batch-only headers, no subject headers → identical behavior as today);
  both-scopes-supplied → 400; neither → 400; foreign-device farmer upload → 403;
  foreign-device dispatch upload → 403; v2 canonical verifies, tampered v2 rejected;
  duplicate `X-Idempotency-Key` is a no-op (idempotent, `§0.7.2`).
- **Migration test** (`backend/tests/test_media_subject_scope_migration.py`, NEW): drive
  Alembic upgrade/downgrade against a throwaway SQLite file; assert legacy media rows
  survive with NULL subject_type; mirror `test_org_scoping_migration.py`.

### R1.2 — App: capture-type constants + subject-aware media writer

- **Capture types** (`lib/data/capture_types.dart`): add
  `farmerSignature = 'farmer_signature'`, `farmerIdDocument = 'farmer_id_document'`,
  `fpicConsentPdf = 'fpic_consent_pdf'`, `fpicHoldingPhoto = 'fpic_holding_photo'`,
  `dispatchTruckPhoto = 'dispatch_truck_photo'`, `dispatchInvoicePhoto =
  'dispatch_invoice_photo'`, `dispatchWeighTicket = 'dispatch_weigh_ticket'`. Each must
  match the backend regex `^[a-z0-9_]{1,64}$`.
- **Drift change (REQUIRED — verified constraint).** `SyncOutbox.batchUuid` and
  `MediaCaptures.batchUuid` are **non-nullable** (`tables.dart`), and `MediaCaptures` has
  an FK to batches + a PK of `{batchUuid, captureType}`. Entity media has no batch, so it
  cannot reuse them. Bump Drift **26 → 27**: make `SyncOutbox.batchUuid` **nullable**, and
  add a new `EntityMediaCaptures` table (do NOT alter `MediaCaptures` — leave the batch
  path untouched). Numbered `MigrationStrategy` step + migration test (`§0.3.1`).
- **Outbox writer** (`lib/data/local/pyrolysis_writer.dart`): add
  `insertEntityMediaWithOutbox({subjectType, subjectUuid, captureType, sandboxPath,
  sha256Hash, isMockLocation})`. It writes an `EntityMediaCaptures` row + enqueues a
  `media` outbox op with `batchUuid: null` and a payload carrying
  `subject_type`/`subject_uuid` (NOT `batch_uuid`). Reuse the existing signed-payload
  shape; do not fork the sync manager (`§0.2.1`).
- **Sync manager** (`lib/services/sync_queue_manager.dart`, `_uploadMedia`): when the
  outbox payload has `subject_type != 'batch'`, send `X-Subject-Type`/`X-Subject-UUID`
  + `X-Media-Canonical: 2` instead of `X-Batch-UUID`, and sign with the v2 canonical.
  Batch media path unchanged.
- **Crypto** (`lib/services/crypto_signer.dart`): add `signMediaUploadV2({...})` binding
  the subject canonical. Pin it against the backend with the cross-language test.
- **Tests** (`test/entity_media_outbox_test.dart`, NEW): farmer-signature capture
  enqueues a `media` op with `subject_type=farmer`, correct capture_type, masked/no PII
  leak; dispatch-photo capture enqueues with `subject_type=dispatch`; v2 signature
  round-trips.

### R1.3 — App: farmer KYC media capture UI

- **Screen** (`lib/ui/screens/farmer_kyc_screen.dart`): add capture affordances that
  route through `SecureCameraScreen` (photo) and produce media via
  `insertEntityMediaWithOutbox(subjectType: 'farmer', subjectUuid: farmerUuid, ...)`.
  Four artifacts, each optional-but-tracked:
  - signature photo → `farmer_signature` → on sync-success, the returned media id lands
    in `Farmer.signature_media_id` (the app submits the farmer record referencing the
    client-generated media UUID; server links on upload — client-generated UUID is the
    PK, `§0.7.2`).
  - ID document photo → `farmer_id_document` → `FarmerDocument.media_id`.
  - FPIC signed-PDF (accept a PDF pick OR a photo of the signed form) →
    `fpic_consent_pdf` → `FarmerConsent.signed_pdf_media_id`.
  - FPIC holding photo → `fpic_holding_photo` → `FarmerConsent.holding_photo_media_id`.
  - **Honest empty state (`§0-DELTA.2`):** each renders "not captured" until present;
    none is required to save the farmer (offline-first — media syncs later).
- **NOTE — media/record ordering.** The farmer record and its media sync independently
  via the outbox. The server must accept a `signature_media_id` that references a media
  row **not yet uploaded** (nullable link, resolved on eventual media arrival) — verify
  `routers/farmers.py` already stores the id as a plain string (it does, per audit) and
  that the portal renders "signature pending upload" until the media row exists.
- **Tests** (`test/farmer_kyc_media_test.dart`, NEW): tapping "capture signature" and
  returning a `SecureCaptureResult` enqueues a farmer-scoped media op linked to the
  farmer uuid; farmer can still be saved with zero media (grandfather/offline).

### R1.4 — App: dispatch media capture UI

- **Screen** (`lib/ui/screens/dispatch/dispatch_screen.dart`): add capture affordances
  for truck photo, invoice photo, weigh-ticket (photo or PDF), each via
  `insertEntityMediaWithOutbox(subjectType: 'dispatch', subjectUuid: dispatchUuid, ...)`.
  Same optional-but-tracked pattern.
- **Tests** (`test/dispatch_media_test.dart`, NEW): capturing a truck photo enqueues a
  dispatch-scoped media op; dispatch still submittable with no media.

### R1.5 — Portal: render entity-scoped media

- **API** (`portal/src/api.ts`): extend the media types with `subject_type`/
  `subject_uuid`; add fetchers for farmer media and dispatch media (reuse the existing
  media list shape).
- **Farmer detail + Dispatch detail pages**: render the attached media in the existing
  `EvidenceGallery` component (reuse, `§0.2.1`), with an **honest empty state** when none
  is attached. New/changed pages join the jest-axe a11y suite with zero violations
  (`§0.7.7`) and use cursor pagination if any list grows.
- **Tests**: extend `EvidenceGallery` tests + page tests for the farmer/dispatch media
  sections; a11y suite green.

### R1 — Definition of Done
- [x] Migration chains from HEAD, real `downgrade()`, migration test green.
      (`fbad0d51b1b1`, chained from `c8d9e0f1a2b3`.)
- [x] `MediaFile` subject columns nullable; legacy batch media path byte-for-byte
      unchanged (back-compat test proves it). (`test_batch_media_backcompat_unchanged`.)
- [x] ONE media endpoint serves batch + farmer + dispatch (no duplicate pipeline).
- [x] v2 media canonical pinned cross-language; v1 still valid (old app + new backend).
- [x] Farmer signature/ID/consent + dispatch photos capture, sync (two-phase, hash-
      verified), and render in the portal; each has an honest empty state.
- [x] Ownership enforced per subject (foreign-device 403 tests green). NOTE: farmer
      media uses existence-only checking, not a 403-if-foreign-device check — `Farmer`
      has no `device_id` column and no device→project link exists anywhere in the
      schema, so a stricter check for media than exists for the farmer record itself
      would be inconsistent. Documented in `_assert_farmer_ownership`'s docstring.
- [x] Three suites green before + after. One commit (`6e13c0c`).
- [x] Runbook note: enable order is code-default-on immediately (no fleet gate needed —
      this is additive capability, not a quarantine gate).

**Deferred-within-R1 (state explicitly, do not fabricate):** on-device PDF *generation*
of the FPIC consent form is out of scope — R1 accepts a captured/selected PDF or a photo
of the signed paper form, it does not render the consent PDF itself. The portal farmer
detail view shows captured/not-captured TEXT status only, not a media gallery/thumbnail
(no farmer-media list endpoint was added — would need one to fetch actual image bytes).

**Two real bugs found and fixed while verifying R1 (neither is an R1 design flaw):**
1. Alembic's `env.py` calls `logging.config.fileConfig()` on every migration
   upgrade/downgrade, which (via its `disable_existing_loggers=True` default) silently
   disables every pre-existing logger not named in `alembic.ini` — including the "dmrv"
   logger `observability.record_gate_rejection` uses. This broke `caplog` for
   `test_observability_gates.py` whenever an alembic-driving test ran first in the same
   process. `test_org_scoping_migration.py` has the identical latent risk; it just never
   sorted before that file alphabetically. Fixed by save/restore of logger
   handlers/level/disabled-state in the new migration test
   (`test_media_subject_scope_migration.py::_preserve_logging_config`) — worth
   backporting to `test_org_scoping_migration.py` if it ever changes name/position.
2. Making `SyncOutbox.batchUuid` nullable was a compile-time breaking change for six
   pre-existing Flutter tests that constructed `SyncOutboxCompanion.insert(batchUuid:
   '<string>')` directly (no `Value(...)` wrapper). Fixed in
   `dashboard_stats_test.dart`/`sync_deadlock_test.dart`/`sync_failure_visibility_test.dart`/
   `sync_queue_triage_test.dart`/`sync_retry_visibility_test.dart`/`sync_two_phase_test.dart`.

---

## PART R2 — Dispatch flow durability (restart-resilient wizard state)

**Goal.** Close deferred item **#3**. Today the dispatch draft *record* is safe (queued
to the outbox), but the *wizard position* — which phase the operator was on
(draft→submit→in_transit→received) — lives only in `dispatch_screen.dart` memory. Kill
the app mid-flow and the operator must re-navigate manually
(`dispatch_screen.dart:20-25` documents this).

**Depends on:** R1 (both edit `dispatch_screen.dart`) — land R1 first.

### R2.1 — Persist + restore in-flight dispatch wizard state
- **Persistence** (`lib/services/dispatch_service.dart`): add a small, typed
  SharedPreferences-backed helper `saveInFlightPhase(dispatchUuid, phase)` /
  `loadInFlightPhase(dispatchUuid)` / `clearInFlightPhase(dispatchUuid)`. Key namespaced
  `dmrv.dispatch_wizard.<dispatchUuid>`. **No PII** in this store (phase enum + uuid
  only — SharedPreferences is not encrypted, `§0.1.1`; putting only a uuid+enum here is
  allowed exactly because it is not sensitive — state this in a code comment).
- **Screen** (`lib/ui/screens/dispatch/dispatch_screen.dart`): on init, if an in-flight
  phase exists for the active dispatch, restore the wizard to it (with a dismissible
  "resumed your in-progress dispatch" banner, mirroring the farmer-KYC draft-restored
  banner from Part J). Save on each phase transition; clear on terminal state
  (`received`) or explicit abandon.
- **Pure core (`§0.2.3`):** the "which phase should we resume to, given persisted phase +
  server truth" decision is a pure function `resolveResumePhase(persisted, serverStatus)`
  — unit-tested without the widget. It must reconcile with server truth: if the server
  already advanced the dispatch (e.g. a prior transition succeeded before the kill), trust
  the server status over the stale local phase.
- **Tests** (`test/dispatch_wizard_resume_test.dart`, NEW): pure `resolveResumePhase`
  (persisted behind/ahead of/equal to server); persisted phase restored on re-open;
  cleared on `received`; a genuinely fresh dispatch shows no resume banner.

### R2 — Definition of Done
- [x] Killing the app mid-flow and re-opening restores the wizard to the correct phase,
      reconciled against server truth (never resurrects a phase the server already
      advanced past).
- [x] Only non-sensitive data (uuid + phase string) in SharedPreferences; comment states
      why.
- [x] Resume banner is consequence-explicit (nothing to undo — server truth already
      reconciled) and dismissible.
- [x] Flutter suite green before + after (357 passed, +10). **Correction to this plan:**
      a backend change WAS needed — no device-facing endpoint existed to read a
      dispatch's current status, which `resolveResumePhase`'s "trust server" design
      requires. Added `GET /api/v1/dispatch/{uuid}` (device-signed, ownership-checked,
      mirrors `transition_dispatch`) — backend suite 620 passed (+3), additive only, no
      migration.

---

## PART R3 — Density calibration capture (app-side)

**Goal.** Close deferred item **#4**. The `BulkDensityTest` backend model + endpoint +
credit-engine fallback all exist (Part 4 F). There is **no app screen** to record and
submit a density test. Build it, reusing the existing BLE weight-scale service (the same
one yield-weighing uses) — do not add new BLE plumbing (`§0-DELTA.3`).

**Independent** — no ordering dependency.

**⚠️ Backend reality (verified).** F's only density-create route is
`POST /portal/bulk-density-tests` with `require_role("admin")` — portal/admin-only, a
device cannot call it, and it trusts a client-supplied `density_kg_per_l`. So this Part
must **add a new device-signed endpoint** `POST /api/v1/density-tests`
(`backend/routers/density.py`, mirror `routers/dispatch.py`) that takes `mass_kg`+
`volume_l` and **computes density server-side** (`§0.1.4`). Register it in
`app_factory.py`. (Alternative: keep density admin-only and reclassify this as a portal
task — only if the human elects it.)

### R3.1 — App: density calibration screen + service
- **Service** (`lib/services/density_service.dart`, NEW): `submitDensityTest({...})` that
  computes `density_kg_per_l = mass_kg / volume_l` **client-side for display only**, and
  submits the raw `mass_kg` + `volume_l` (+ optional BLE-sourced mass) to the NEW
  `POST /api/v1/density-tests` device endpoint — the backend recomputes and stores the
  authoritative density (`§0.1.4`). Client-generated `test_uuid` PK, upsert-on-conflict,
  direct signed call (mirror `dispatch_service.dart`).
- **Screen** (`lib/ui/screens/density_calibration_screen.dart`, NEW): operator enters
  (or reads via BLE scale) the sample mass and the known sample volume; shows the derived
  density; submits. Reuse the BLE weight-scale widget/notifier from the yield flow
  (`yield_scale_notifier.dart` / the BLE temperature/weight service) — inject it, don't
  reimplement.
- **Pure core:** `volumeToMassOrDensity` math already exists in
  `backend/services/bulk_density.py`; the app's *display* calc is a 1-line pure helper —
  unit-test it and pin it equals the server formula on a shared fixture.
- **Entry point** (`lib/ui/screens/dashboard_screen.dart`): add an always-accessible
  tile (mirror the Dispatch / Field-Walk tiles) — density calibration is site-level, not
  per-batch.
- **i18n:** new screen ships en+hi strings in `app_en.arb`/`app_hi.arb` (`§0.7.7`).
- **Tests** (`test/density_calibration_test.dart`, NEW): pure display-density math;
  submit enqueues/sends the correct payload; BLE-sourced mass populates the field;
  screen renders + i18n keys resolve.

### R3 — Definition of Done
- [ ] Operator can record a density test (manual or BLE mass) and submit it; server
      stores it; the F credit-engine fallback can now consume real captured density.
- [ ] Reused the existing BLE weight-scale service (named in PR); no new BLE code.
- [ ] Client computes density for display only; server is source of truth.
- [ ] en+hi strings; three suites green before + after.

**Deferred-within-R3:** density *video* capture (`density_video` capture-type already
exists as a label) is a thin add-on — wire it via the R1 media rail only if in scope;
otherwise leave the constant unused and note it.

---

## PART R4 — On-device parcel geometry + geofence capture gate

**Goal.** Close deferred item **#5** and make the already-built, currently-inert geofence
gate real. Today `secure_capture_service.dart`'s `capture()` accepts an optional
`parcelBoundaryRing`, and `lib/services/geofence_check.dart` implements the full
point-in-polygon check — but **no call site ever passes real geometry**, and the app has
**no parcel geometry on-device at all**: the device parcel endpoint
(`backend/routers/batches.py` `GET /api/v1/parcels`) deliberately returns only
`{parcel_uuid, name}` and its docstring says "never the boundary geometry."

**This Part contains a real design decision — make it explicitly, do not skip it.**

**Independent** — no ordering dependency (but claims a Drift version; see `§1.1`).

### R4.0 — Design decision (do this first, record it in the PR + a runbook)
Exposing parcel boundary geometry to the device is a **security/privacy tradeoff**: it
puts landholding polygons on field phones. Decide and document:
- **Recommended:** expose geometry **only for parcels the enrolling device's project
  owns**, gated behind a new `settings.py` flag `DMRV_DEVICE_PARCEL_GEOMETRY` (default
  **off**, `§0.4`). Off → endpoint behaves exactly as today (uuid+name only); the
  geofence gate stays inert (its current, safe state). On → geometry is included and the
  gate can function. This preserves back-compat and lets the geometry exposure be a
  deliberate, observable rollout (`§0.7.5`), not a silent default.

### R4.1 — Backend: optionally include boundary geometry (flag-gated, additive)
- **Endpoint** (`backend/routers/batches.py`, `GET /api/v1/parcels`): when
  `DMRV_DEVICE_PARCEL_GEOMETRY` is on, include `boundary_geojson` (and bbox) in each
  parcel row, scoped to the device's project. When off, unchanged. Cap response size /
  vertex count already enforced upstream at registration (`geometry.py` guards) — but
  re-confirm the serialized payload can't blow the response budget for a project with
  many parcels (paginate if needed, `§0.7.7`).
- **Schema:** explicit Pydantic response model with the optional geometry field.
- **Tests** (`backend/tests/test_device_parcel_geometry.py`, NEW): flag-off → no geometry
  (back-compat); flag-on → geometry present, project-scoped, foreign project excluded;
  response schema stable.

### R4.2 — App: cache parcel geometry locally (Drift bump)
- **Drift** (`lib/data/local/tables.dart` + `app_database.dart`): add a
  `parcel_geometry` table (or extend the parcel cache) storing `parcel_uuid` +
  `boundary_geojson`. Bump `schemaVersion` **26 → next** (re-verify current number,
  `§1.1`/`§Verify`), add a numbered `MigrationStrategy` step + a migration test
  (`§0.3.1`).
- **Service** (`lib/services/parcel_service.dart`): when geometry is present in the
  parcels response, cache it; expose `boundaryRingFor(parcelUuid)` returning the
  `List<List<double>>` ring `geofence_check.dart` expects, or null when absent
  (grandfather: no geometry → gate stays inert, `§0.3.2`).
- **Tests** (`test/parcel_geometry_cache_test.dart`, NEW): geometry cached + retrieved;
  absent geometry → null ring → capture proceeds ungated; Drift migration test.

### R4.3 — App: wire the geofence gate into capture
- **Capture call sites** (the batch-evidence capture flows, e.g. biomass sourcing /
  moisture / pyrolysis screens that call `SecureCaptureService.capture()`): pass
  `parcelBoundaryRing: parcelService.boundaryRingFor(batchParcelUuid)` so the existing
  `DMRV_GEOFENCE_CAPTURE` gate (already in `secure_capture_service.dart`) can evaluate.
  Behavior when the gate trips is already implemented — this Part only *feeds it data*.
- **Tests** (`test/geofence_capture_wiring_test.dart`, NEW): capture with an in-bounds fix
  passes; out-of-bounds trips the existing gate; no geometry cached → ungated (grandfather).

### R4 — Definition of Done
- [ ] Design decision recorded (flag `DMRV_DEVICE_PARCEL_GEOMETRY`, default off) + runbook
      enable-order (`§0.7.5`).
- [ ] Backend geometry exposure is flag-gated, project-scoped, back-compat when off.
- [ ] Geometry cached on-device (Drift bump + migration test).
- [ ] The previously-inert geofence gate now receives real geometry and functions;
      absent-geometry parcels stay ungated (grandfathered).
- [ ] Observability: geofence trips emit metric + structured log (`§0.7.4`).
- [ ] Three suites green before + after.

---

## PART R5 — i18n retrofit of `farmer_kyc_screen`

**Goal.** Close deferred item **#6**. The l10n infra exists (`lib/l10n/app_en.arb`,
`lib/l10n/app_hi.arb`, `AppLocalizations`), but `farmer_kyc_screen.dart` was never wired
to it — all strings are hardcoded English (`grep AppLocalizations` in that file → 0 hits).

**Depends on:** R1 (both edit `farmer_kyc_screen.dart`) — land R1 first so the new media
UI strings are localized in the same pass.

### R5.1 — Extract strings to `.arb`, wire `AppLocalizations`
- Add every user-facing string in `farmer_kyc_screen.dart` (including R1's new media
  capture labels) to `app_en.arb` + `app_hi.arb` with descriptive keys, following the
  existing key-naming convention in those files.
- Replace hardcoded literals with `AppLocalizations.of(context)!.<key>`.
- **Tests** (`test/l10n_test.dart` — EXTEND the existing one): both locales load all new
  keys; the existing "no hardcoded Hindi strings remain" / "English loads all strings"
  assertions still pass and now cover the farmer KYC keys.

### R5 — Definition of Done
- [ ] Zero hardcoded user-facing strings remain in `farmer_kyc_screen.dart`.
- [ ] en + hi both complete; `l10n_test.dart` green including new keys.
- [ ] Flutter suite green; no backend/portal change.

---

## PART R6 — Day-start audit lock (OPTIONAL — blueprint marks it optional)

**Goal.** Close deferred item **#7** *if elected*. It does not exist anywhere
(`grep -riE "day.?start" lib/` → 0 hits). The blueprint marks it optional — treat this
Part as elective; skipping it does not block the production gate.

**Independent.** If built, may claim a Drift version — coordinate with R4 (`§1.1`).

### R6.1 — Define the feature precisely BEFORE coding
Day-start audit lock = requiring the operator to acknowledge/attest a start-of-day
checklist (device time correct, correct project, calibration in date) before the day's
first capture is allowed. Because it is a *gate*, it is env-flagged default-on in code but
rolled out OFF→canary→on (`§0.7.5`), and it must **grandfather**: a device that has never
seen the feature is not retroactively locked out of in-flight work.

### R6.2 — Implement (pure gate + thin UI)
- Pure gate function (`§0.2.3`) deciding "is the day-start attestation valid for now?"
  given last-attestation timestamp + clock + config — unit-tested without UI.
- Thin UI acknowledgement screen; persist attestation (Drift or SharedPreferences per
  sensitivity — an attestation is not PII, so SharedPreferences is acceptable; state why).
- Env flag `DMRV_DAYSTART_LOCK` in `settings.py`-equivalent app config, default off until
  field-validated.
- Tests: pure gate (fresh / stale / same-day); gate-off → no lock (grandfather); UI
  acknowledgement flips the gate.

### R6 — Definition of Done
- [ ] Feature spec written down first; gate is pure + tested.
- [ ] Env-flagged, default-off, grandfathers existing devices.
- [ ] en+hi strings; three suites green.
- [ ] If skipped: explicitly recorded as "elected not to build (optional)" — not silently
      dropped.

---

## PART R7 — iOS build validation (macOS-gated; doc + checklist, no code path)

**Goal.** Close deferred item **#8** to the extent this environment allows — which is
**documentation only**. The Windows dev host cannot run `pod install` / Xcode. Do not
fake a pass (`§0-DELTA.4`).

### R7.1 — Author a reproducible iOS bring-up runbook
- `docs/IOS_BUILD_RUNBOOK.md` (NEW): exact steps a macOS runner (human or CI) executes:
  Flutter/CocoaPods versions, `flutter precache --ios`, `cd ios && pod install`, open
  `Runner.xcworkspace`, signing team, `flutter build ios --release`, and a smoke test of
  every plugin that has an iOS side (camera, geolocator, mobile_scanner, freerasp, secure
  storage, BLE). Note the already-present `Info.plist` permission strings (camera,
  location, bluetooth, photo library) so the runner doesn't re-add them.
- Record the known deltas this session could NOT verify: no `Podfile` yet (generated by
  first `pod install`), `mobile_scanner` iOS min 12.0 vs project deployment target 13.0
  (compatible), freerasp iOS config.
- **DoD (machine-checkable on macOS, not here):** the runbook, when followed on a Mac,
  produces a release `.app`/`.ipa` and launches to the enrollment screen. Until a macOS
  runner confirms this, item #8 stays **openly listed as "iOS unverified — needs macOS
  runner"** in the production gate; it is NOT marked done by this host.

### R7 — Definition of Done
- [ ] Runbook committed; reproducible; names every iOS-side plugin to smoke-test.
- [ ] Production gate explicitly carries "iOS build unverified (macOS runner pending)"
      until a Mac confirms — no false green from this host.

---

## §7-DELTA. Updated Production-Readiness Gate (deferred backlog)

Append to `PRODUCTION_EXECUTION_PLAN.md §7`:
- [ ] R1 (farmer + dispatch media) done — evidence for all subjects, one rail.
- [ ] R2 (dispatch durability) done.
- [ ] R3 (density capture) done — F fallback now consumes real captured density.
- [ ] R4 (geofence gate live) done OR consciously left flag-off with reason recorded.
- [ ] R5 (farmer KYC i18n) done.
- [ ] R6 (day-start lock) done OR explicitly elected-out (optional).
- [ ] R7: iOS build **confirmed on a macOS runner** (this host cannot sign off).

---

## Appendix — migration/Drift chaining ledger (fill in as each Part lands)

| Part | Alembic (from → new) | Drift (from → new) | Notes |
|------|----------------------|--------------------|-------|
| R1   | `c8d9e0f1a2b3` → `fbad0d51b1b1` ✅ | **26 → 27** ✅ | DONE (commit `6e13c0c`). media_files +subject_type/+subject_uuid; Drift: SyncOutbox.batchUuid→nullable (via TableMigration rewrite) + new EntityMediaCaptures table. Next Drift-bumping Part takes **28**. |
| R2   | — | — | SharedPreferences only |
| R3   | **NEW device endpoint** `POST /api/v1/density-tests` (option A) — F's existing route is admin-only portal, unusable by a device | — | server computes density from mass/volume; add `routers/density.py` |
| R4   | flag-gated response change (no migration) | `<current>` → `<next>` | flag-gated geometry + local cache |
| R5   | — | — | strings only |
| R6   | — | `<current>` → `<next>` if persisted | optional; coordinate Drift # with R4 |
| R7   | — | — | docs only |

**Re-verify every "from" revision/version at the start of the Part (`§Verify`) — never
trust this ledger's numbers over the live repo.**
