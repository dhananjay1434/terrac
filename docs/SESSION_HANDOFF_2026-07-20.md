# Session Handoff — TerraCipher dMRV (2026-07-20)

Paste this into a new session to restore full context of what's built and what's
in flight. Written to be self-contained.

## 1. What this project is
**TerraCipher dMRV** — a biochar **carbon-credit MRV** (Monitoring/Reporting/
Verification) system. Three components in one repo
(`github.com/dhananjay1434/terrac`, branch `main`):
- **Flutter app** (`lib/`) — offline-first field-data capture for artisanal
  biochar burns (farmers/operators on cheap Android phones).
- **FastAPI backend** (`backend/`) — SQLAlchemy async + **Postgres** (Render,
  service `dmrv-api`, DB `dmrv-db`). Computes credits, runs compliance gates.
- **React/TS verifier portal** (`portal/`) — auditors review batches, run
  compliance, issue credits, export registry reports. vitest + jest-axe.

Positioning: an **integrity-first** MRV pipeline (cryptographically-signed
evidence, sensor-grounded burn data, transparent credit engine, verifier portal)
— vs breadth-first competitors.

## 2. Environment specifics (Windows dev box)
- OS Windows; shell is Git Bash (POSIX) + PowerShell. Repo path has a space:
  `c:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`.
- Flutter/dart not on PATH in bash → use full path
  `/c/Users/bit/development/flutter/bin/flutter`. adb at
  `/c/Users/bit/AppData/Local/Android/sdk/platform-tools/adb.exe`.
- **Windows Developer Mode reverts between sessions** → `flutter pub get`/builds
  fail with "enable Developer Mode" until toggled on again (manual; needs
  elevation — open `ms-settings:developers`).
- **Disk is tight** (~3–6 GB free); `flutter clean` frees ~5 GB. Full Android
  build ~6 min cold; full flutter test ~4 min; full backend pytest ~4.5 min —
  run these in background.
- Test device: **Micromax E7533**, id `BS7533M4KN022100592`, Android 11.
- Live backend URL: `https://dmrv-api.onrender.com` (Render free tier — **sleeps**
  after inactivity, first request after idle can time out).
- App id: `io.dmrv.dmrv_app`. Drift schema **v25**. Backend has fail-loud env
  (DATABASE_URL required), argon2id portal auth, rate-limit middleware.

## 3. Architecture rails (reused everywhere)
- **App evidence write**: `insertWithOutbox` / `insert*WithOutbox`
  (`lib/data/local/app_database.dart`) → `SyncOutbox` two-phase sync
  (`sync_queue_manager.dart`, `json_synced_at`/`media_synced_at`, atomic CAS
  row-claim, backoff, `retryNow`) → route via `kEndpointByTable` +
  `kCaptureTypeByTable`.
- **Crypto**: `crypto_signer.dart` (device Ed25519, `signRequestV2` w/ replay
  `signed_at`, `signMediaUpload`). Backend verifies in `security.py`.
- **Capture**: `secure_capture_service.dart` — sandboxed photo, q70 <500 kB,
  **EXIF GPS + SHA-256 + azimuth/pitch/roll + isMocked** (PHOTO ONLY, no video).
- **Sensors**: `ble_temperature_service.dart` (ESP32 thermocouple 0x1809 +
  ATECC608B attestation), `ble_weight_scale_service.dart` (crane scale, stab lock).
- **RASP**: `device_integrity_service.dart` (freerasp, fail-closed).
- **Backend**: models `backend/models.py` (Batch, Kiln, EndUseApplication,
  MoistureReading, CompositePileSample, TransportEvent, AnnualVerification,
  MediaFile, PortalUser, EnrollmentToken); evidence endpoints `routers/evidence.py`
  (`_assert_batch_ownership`); portal `portal/routes.py` (`require_role`,
  VALID_ROLES = admin/lab/verifier); `corroboration.py` (derive_* gates),
  `credit_engine.py`, `lca_engine.py` (CSI-3.2, 8-step), `geo.py` (GPS
  corroboration + quarantine), `attestation.py`, `settings.py`, `middleware.py`.
- `batch.status` consumed loosely (only `ISSUED` special-cased) → new
  `QUARANTINE_*`/state strings are safe.
- Env-gated compliance flags pattern: `COMPLIANCE_ENFORCED`,
  `DMRV_REQUIRE_EXIF_GPS`, `TRANSPORT_EVENTS_ENFORCED`, `DMRV_ATTESTATION_ENFORCED`.

## 4. What we DID this session (all committed + pushed unless noted)

### 4a. Portal UI polish V2–V6 (fintech-grade design pass) — DONE, pushed
Token retune (Stripe/Mercury palette, AA-verified), "Verified & Sealed" batch-
detail hero (real data only), evidence gallery fade-in + designed fallback,
compliance-checklist row hierarchy, subtraction pass, registry sentence-case,
scanner-frame fix, and **cursor Prev/Next pagination** for the Batches table
(replaced infinite "Load more"; fixed a row-clipping bug). Commits `2790512`…
`bd4fe5c`, `65470c8`, `c485229`, `0701c70`.

### 4b. capture_type bug + fix — DONE, pushed
Root problem: batch-anchor + farmer end-use photos synced with `capture_type=null`
→ portal showed them as "Other / Uncategorized". Fixed by **stamping capture_type
at source** (`lib/data/capture_types.dart`), rendering `end_use`/`batch_photo` as
named portal sections, and a backend backfill. BUT the first fix put
`capture_type` into the **signed JSON body** → strict endpoints returned **422
extra_forbidden** → rows went FAILED_PERMANENTLY. Corrected (`0b80df8`): derive
capture_type from the target table (`kCaptureTypeByTable`), send only as the
media `X-Capture-Type` header, never in the JSON body. Commits `1ac5a91`,
`f8605ce`, `6d6fc04`, `0b80df8`. (The poisoned rows were cleared by wiping +
reinstalling the app on the phone.)

### 4c. Enrollment paste-to-autofill (V6) — DONE, pushed
The portal mints `dmrv-enroll:v1:{"url":..,"token":..}`. App now recognizes that
pasted string in the token field and auto-splits URL + token (pure parser
`lib/data/enrollment_qr.dart` + wiring). Camera scan deferred (no scanner dep
yet). Commits `8f9615f`, `13d224e` (+ plan `c8fe9f7`).

### 4d. V7 Production Hardening (plan `e220d49`, `docs/PRODUCTION_HARDENING_V7.md`)
Fixes for real audit findings (CI intentionally excluded — user removed CI due to
GitHub limits). Status:
- **P1 DONE** (`73c3282`): RASP no longer hard-locks sideloaded installs
  (`onUnofficialStore` → log-only) + aligned freerasp package id to
  `io.dmrv.dmrv_app` (was `com.kontiki.dmrv` mismatch → would self-brick).
- **P2 DONE** (`ae82bdf`): operator **force-retry** for backoff-stuck sync rows
  (`retryNow`) + clearer "attempt N, waiting" status in Sync Health.
- **P3 DONE** (`8c1df0c`): no-EXIF-GPS photo no longer silently corroborates a
  batch → `QUARANTINE_GPS_MISSING` (env-gated `DMRV_REQUIRE_EXIF_GPS`, default on).
- **P4 = option (b) DONE** (`ea80634`, doc only): device attestation mechanism is
  built + tested but **OFF by design** — real enforcement needs Google Play
  Integrity credentials the user doesn't have. Runbook = how to flip it on later.
- **P5 DEFERRED** (`b23eb4c`, doc only): portal token in `localStorage` → httpOnly
  cookie migration deferred post-demo (cross-origin cookie is demo-fragile).
All app/backend suites green after each phase (flutter ~253 tests, backend ~455).

### 4e. APK rebuild + install on device — DONE
Rebuilt debug APK with the fixes, `adb install`ed to the Micromax. (Hit Developer
Mode reverts + a corrupted-APK-from-interrupted-build snag; resolved.)

### 4f. Varaha competitive analysis — DONE (analysis only, docs uncommitted)
Deep teardown of competitor **Varaha "Kalki"** (`com.varaha.biochar` v1.6.2,
decompiled at `C:\Users\bit\Downloads\com.varaha.biochar_1.6.2\`). Verified
against **primary binary artifacts** (decompiled `classes*.dex`, the base64
`strings.commonMain.cvr` catalog, manifest, native libs) — NOT the bundled RE
`.md` summaries (user explicitly said don't trust those). Used **multiple
parallel agents** across domains (farmer, capture, logistics, platform) and veins
(anti-fraud, sync, field-UX, methodology).

Key findings (condensed):
- Varaha = **Kotlin Multiplatform + Compose**, shipping v1.6.2 in India/
  Bangladesh/Kenya. It's a **full supply-chain ops platform**: farmer KYC +
  payments (UPI/bank/M-Pesa) + **FPIC legal consent**, site/farm **boundary
  mapping** (source parcel, overlap-rejected = anti-double-count), excavation,
  **dispatch/logistics** (trucks, dual weighing, Draft→In-Transit→Received),
  facility admin, dual roles, multi-org/multi-program (biochar/ARR/regen via
  `registry_config_id`), ML Kit doc-scanner/barcode, bulk-density volume→mass,
  dung-mix end-use video, Firebase remote config + in-app updates.
- **Where WE lead (verified):** SQLCipher **encryption at rest** (their DB incl.
  signatures/Aadhaar/bank is **plaintext**); **Ed25519-signed** evidence (theirs
  is hashed but **unsigned**); **sensor-grounded** burn/yield (BLE temp+weight +
  hardware attestation vs their photos); transparent credit engine + verifier
  portal; i18n en+hi (theirs English-only); two-phase hash-verified sync.
- **Where WE lag:** farmer KYC/payments/FPIC (we have a `// TODO` stub), logistics/
  dispatch/facility (we have ~1.5 of their ~8 sub-domains), **boundary mapping is
  a FAKE STUB** (persists a boolean — a false attestation to fix), ML vision,
  media compression + upload progress, remote control plane/kill-switch, in-app
  updates, video capture, observability breadth, iOS shipping.
- Varaha's shipped security holes (contrast points): plaintext PII, **Inspektify
  network inspector shipped in prod**, bundled Google API key. (Two RE claims —
  cleartext-traffic + measure.sh test endpoint — I could NOT confirm in the
  binary, so don't assert them.)
- Brutal verdict: **as a product today, Varaha wins (shipping, complete). We're
  pre-production but better-positioned for the credit-integrity layer the market
  is moving toward — IF we ship.** Don't out-breadth them; win on *verifiable*
  integrity + just-enough breadth.

### 4g. Boundary design + Product Blueprint + audit — DONE (docs uncommitted)
- Decided: **boundary = biomass source parcel**, registered **once in the portal**
  at project setup; field GPS (already captured) checked **point-in-polygon**
  against it; **overlap rejection** = anti-double-count. Optional Phase-2:
  Ed25519-signed **capability link** → App Link → authorized field-walk.
- Deep specs written: geometry math (shapely + pyproj geodesic area; project-to-
  meters overlap with a **sliver floor** so adjacent parcels aren't falsely
  rejected; point-in-polygon in raw degrees with a projected meter buffer) and
  the App-Link/Ed25519 signed-link mechanics (offline verify gates UX, server
  verify gates data; single-use `jti`; deferred-link fallback reuses V6 paste).
- Wrote the **master `PRODUCT_BLUEPRINT.md`** — every Varaha gap mapped to exact
  insertion points in our stack (model/migration/endpoint/sync-route/screen/test),
  14 feature blueprints (A–O) + roadmap.
- **Independently re-audited the blueprint against code** and corrected 2 real
  errors: (1) **no `Project` entity exists** (`project_id` is a bare string) —
  added Blueprint 0 as a P0 prerequisite that A/B/C/D/G hang off, with backfill;
  (2) **video capture was omitted** (SecureCapture is photo-only) — added
  Blueprint O. Also rewrote §5 into a realistic critical path (was unrealistically
  parallel) and logged consciously-deferred items (per-day rollup; OTP-login N/A
  by design).

## 5. Git state
- Branch `main`, **up to date with origin/main** (everything through `b23eb4c` is
  pushed).
- **5 uncommitted docs** (analysis/planning — deliberately not committed yet;
  three name the competitor):
  - `docs/PRODUCT_BLUEPRINT.md` (our build plan — corrected)
  - `docs/BOUNDARY_DESIGN.md` (our boundary spec + math + link mechanics)
  - `docs/COMPETITIVE_ANALYSIS_VARAHA.md`
  - `docs/PM_ROADMAP_VS_VARAHA.md`
  - `docs/VARAHA_TEARDOWN_SMART_THINGS.md`

## 6. Committed planning/runbook docs (already in repo)
`docs/PORTAL_MASTER_V2.md`, `PORTAL_POLISH_V3.md`, `PORTAL_PAGINATION_V4.md`,
`EVIDENCE_CLASSIFICATION_V5.md`, `ENROLLMENT_QR_PASTE_V6.md`,
`PRODUCTION_HARDENING_V7.md`, `ATTESTATION_ENABLEMENT.md`,
`ANDROID_REBUILD_PROMPT.md`.

## 7. Locked decisions / constraints (carry forward)
- **Protect the moat** in every feature: SQLCipher encryption, Ed25519 signing +
  replay, sensor-grounded measurement + attestation, transparent credit engine,
  verifier portal. New features must preserve signed-canonical + encrypted-at-rest.
- **Logic-freeze discipline** on UI passes: UI/markup/copy only; never change
  api.ts/auth.ts/compliance/qr/lab shapes or network payloads.
- **Never fabricate data** (killed the LCA "not exposed" apology copy; must kill
  the boundary boolean stub). Missing data shows as missing.
- **Every new compliance/anti-fraud gate is ENV-GATED, default on.**
- **CI is intentionally OFF** (GitHub limits) — do NOT re-add; gate releases via
  the per-phase test runs.
- **Distribution = private B2B APK** (not Play Store) — hence RASP `onUnofficialStore`
  is log-only; app is signed-release + obfuscated + freerasp.
- **Attestation stays OFF** until the user provides Google Play Integrity creds
  (mechanism ready; do NOT fake it).
- **Boundary = source parcel, portal-registered, overlap-checked, point-in-polygon
  corroborated** using the GPS we already capture.
- **Don't copy Varaha's mistakes** (plaintext PII, unsigned evidence, shipped
  network inspector, secrets in bundle).
- Test-gate every phase; one phase per commit; do NOT push unless asked.

## 8. Current phase & immediate next options
We are at the **end of analysis + planning**. Nothing from `PRODUCT_BLUEPRINT.md`
is built yet. Open choices for the user:
- **(a)** Commit the 5 planning docs (all, or keep competitor-named ones out of git).
- **(b)** Execute **Step 0** of the blueprint: kill the boundary fake stub (S) +
  build the **Project entity** prerequisite (S) + remote control plane (I, M).
- **(c)** Turn **Blueprint A** (source-parcel boundary + overlap) into an
  executable phase-by-phase, test-gated build prompt and start it.
- **(d)** Rebuild/reinstall the APK if more app changes land (Developer Mode will
  need re-toggling).
Recommended: (b) then (c) — Step 0 unblocks the P0 core; A is the credibility fix.

## 9. How to re-verify state in a fresh session
`git -C "<repo>" log --oneline -25` · `git status --short` (shows the 5
uncommitted docs) · read `docs/PRODUCT_BLUEPRINT.md` (§3 gap inventory, §5
critical path) and `docs/BOUNDARY_DESIGN.md`. Competitor teardown source:
`C:\Users\bit\Downloads\com.varaha.biochar_1.6.2\`.
