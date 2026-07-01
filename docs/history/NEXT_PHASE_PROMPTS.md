# TerraCipher dMRV — Next-Phase AI Prompts (Phase 2 → Phase 4)
_Same prompt-engineering style as the original AI-Guided Flutter dMRV PDF.  
Each prompt is self-contained. Use one prompt per AI session. Do not combine prompts.  
Each prompt has: **Objective → Instructions (numbered steps) → Test & Verification → Acceptance Gate**._

---

## PART A — VERIFIED DONE (with file:line evidence)

### Phase 1 — Project Initialization & Database (PDF Prompt 1) ✅
| Requirement | File | Evidence |
|---|---|---|
| `drift` + `sqlcipher_flutter_libs` + `flutter_riverpod ^2.5.1` + `uuid ^4.3.3` | `pubspec.yaml:13-22` | Pinned versions match Master P13 |
| Relational schema (UUID PKs) | `lib/data/local/tables.dart` | `SystemMetadata`, `BiomassSourcing`, `PyrolysisTelemetry`, `YieldMetrics`, `EndUseApplication`, `CryptographicSignatures`, `SyncOutbox` |
| Drift generated code | `lib/data/local/app_database.g.dart` | schema v4 |
| Global Riverpod DB provider | `lib/data/local/database_provider.dart` | `final databaseProvider = Provider<AppDatabase>(...)` |
| **Transactional Outbox Pattern** | `app_database.dart` → `insertBiomassSourcingWithOutbox()`, `yield_end_use_writers.dart` → `insertYieldMetricsWithOutbox()` + `insertEndUseWithOutbox()`, `pyrolysis_writer.dart` | Atomic `transaction { insert row + insert SyncOutbox(PENDING) }` |
| AES-256 at rest | `app_database.dart` (SQLCipher) + `passphrase_resolver.dart` | 256-bit passphrase via `flutter_secure_storage` (Android Keystore / iOS Keychain) |
| Schema unit test | `test/drift_schema_test.dart` | `NativeDatabase.memory()` round-trip |

### Phase 2 — Core UI & Anti-Fraud Camera (PDF Prompts 2, 3) ✅
| Requirement | File | Evidence |
|---|---|---|
| `LantanaSourcingScreen` (immutable species dropdown) | `lib/ui/screens/lantana_sourcing_screen.dart` | `Lantana_camara` pre-pinned |
| 72-hour temporal lock | `lib/providers/lantana_sourcing_notifier.dart` | Local-clock delta gate |
| `MoistureVerificationScreen` | `lib/ui/screens/moisture_verification_screen.dart` | Numeric text field + photo capture |
| Compliance gate ≤15.0% | `lib/providers/moisture_gate_notifier.dart` | `compliant && photoCaptured && persisted` |
| Sandboxed camera capture | `lib/services/secure_capture_service.dart` | `getApplicationSupportDirectory()/evidence/<uuid>.jpg` |
| EXIF stamping | `secure_capture_service.dart` via `native_exif` | `GPSLatitude`, `GPSLongitude`, `DateTimeOriginal` |
| SHA-256 of final on-disk bytes | `secure_capture_service.dart` | `sha256.convert(file.readAsBytesSync())` |
| Camera debug screen | `lib/ui/screens/camera_debug_view.dart` | prints path / EXIF / SHA-256 |
| GPS recovery UX (v5.1) | `secure_camera_screen.dart` | `CaptureErrorKind` switch |
| Widget tests | `test/moisture_gate_notifier_test.dart`, `test/harvest_lock_test.dart`, `test/lantana_sourcing_notifier_test.dart`, `test/secure_capture_cleanup_test.dart` | All passing |

### Phase 3 — BLE Hardware (PDF Prompts 4, 5) ✅
| Requirement | File | Evidence |
|---|---|---|
| ESP32 Thermocouple Service `0x1809` | `lib/services/ble_temperature_service.dart` | `flutter_reactive_ble`, MTU 247, char `0x2A1C` |
| 60s buffer | `lib/providers/pyrolysis_ble_notifier.dart` | `Timer.periodic(60s)` |
| Crane Scale Service `0x181D` | `lib/services/ble_weight_scale_service.dart` | char `0x2A9D`, SIG flag + uint16 × 0.005 |
| 5-reading variance <0.05 kg lock | `lib/providers/yield_scale_notifier.dart` | circular buffer |
| BLE permissions gate | `lib/services/ble_permission_gate.dart` | Android 12+ runtime grants |
| Tests | `test/ble_temperature_buffer_test.dart`, `test/scale_stabilization_test.dart` | 60s buffering + variance lock |

### Phase 4 — Offline-First Sync (PDF Prompt 6) 🟡
| Requirement | File | Status |
|---|---|---|
| `SyncQueueManager` outbox drain | `lib/services/sync_queue_manager.dart` | ✅ Foreground stream |
| `connectivity_plus` gate | `sync_queue_manager.dart` | ✅ |
| `X-Idempotency-Key` injection | `sync_queue_manager.dart` | ✅ From outbox `operation_id` |
| Payload triage (JSON → media) | `sync_queue_manager.dart` | ✅ verified in `sync_two_phase_test.dart` |
| **`background_fetch` isolate** | — | ❌ **MISSING** — see Prompt 16 |
| `--dart-define=DMRV_API_BASE_URL` | `sync_queue_manager.dart` | ✅ |
| Deadlock + triage tests | `test/sync_deadlock_test.dart`, `sync_queue_triage_test.dart`, `sync_two_phase_test.dart` | ✅ |

### Phase 5 — FastAPI Backend + LCA (PDF Prompts 7, 8) ✅
| Requirement | File | Evidence |
|---|---|---|
| FastAPI + async SQLAlchemy + asyncpg | `backend/server.py`, `backend/db.py` | `create_async_engine` |
| Pydantic V2 strict (`extra="forbid"`) | `backend/schemas.py` | nested `BatchPayload` |
| `POST /api/v1/batches` (idempotent 201/200) | `backend/server.py` | `X-Idempotency-Key` |
| `POST /api/v1/media` SHA-256 verify | `backend/server.py` | 422 on mismatch |
| 8-step CSI LCA | `backend/lca_engine.py` | dry_mass → gross_csink → H:Corg decay → MOS → transport → CH4 → net |
| pytest 27/27 passing | `backend/tests/test_api.py` (10), `backend/tests/test_lca_engine.py` (17) | green |

### Master Prompts P1–P15 (UI layer) ✅
| Master Prompt | File | Notes |
|---|---|---|
| P2 Color palette | `lib/ui/design/app_theme.dart:4-10` | 7 named tokens |
| P3 ThemeData + typography | `app_theme.dart:12-50` | `bodyMedium.color = armorSlate` (contrast fix this session) |
| P4 Font registration | `pubspec.yaml` | 🟡 declared but `assets/fonts/` is empty |
| P5–P7 `PremiumActionCard` | `lib/ui/widgets/premium_action_card.dart` | 96-px touch target, haptic heavy-impact, locked→null onTap |
| P8 `IntegrityFooter` | `lib/ui/widgets/integrity_footer.dart` | now takes `final String lastHash` |
| P9–P10 Dashboard build | `lib/ui/screens/dashboard_screen.dart` | pulse animation + `_buildConnector` |
| P11 `BleService` | `lib/services/ble_service.dart` | UUID v4 + sorted canonical JSON + SHA-256 |
| P12 Riverpod state | `lib/providers/dashboard_provider.dart` | `NotifierProvider<DashboardNotifier, DashboardState>` |
| P13 `main.dart` ProviderScope | `lib/main.dart` | wraps `TerraCipherApp` |
| P14 ConsumerWidget refactor | `dashboard_screen.dart` | `ref.watch(dashboardProvider)` drives all 3 card statuses |
| P15 QA audit | `STATUS.md` | 9/10 PASS + 1 intentional Riverpod deviation |

### Verified gone (zero `package:provider` references)
```bash
$ grep -rn "package:provider" lib/   # 0 hits
```

---

## PART B — NEXT-PHASE PROMPTS (Prompts 16 → 25)

### PROMPT 16 — Background Isolate Sync (closes PDF Prompt 6 gap)

**Objective:** Migrate `SyncQueueManager` from a foreground stream to a true background isolate so the outbox drains even when the app is killed/backgrounded.

**Instructions:**
1. Add `background_fetch: ^1.3.7` to `pubspec.yaml` dependencies.
2. Create `lib/services/background_sync_dispatcher.dart`. Implement a top-level function `Future<void> backgroundFetchHeadlessTask(HeadlessTask task)` registered via `BackgroundFetch.registerHeadlessTask()` in `main.dart` **before** `runApp`.
3. The headless task must:
   - a) Open a *new* `AppDatabase` instance (Drift is safe across isolates because SQLCipher uses file locks; pass the same passphrase via `PassphraseResolver.resolve()`).
   - b) Check `Connectivity().checkConnectivity()`. Abort if `ConnectivityResult.none`.
   - c) Query `SyncOutbox` rows where `status='PENDING'` ORDER BY `enqueuedAt ASC` LIMIT 25.
   - d) For each row, POST to `String.fromEnvironment('DMRV_API_BASE_URL')` with `X-Idempotency-Key: <operation_id>`. Use `Dio` with 30s timeout. On HTTP 2xx → mark `SYNCED`. On 4xx → mark `DEAD` + `deadReason`. On network error / 5xx → leave `PENDING` + increment `retryCount`.
   - e) Call `BackgroundFetch.finish(task.taskId)` in a `finally` block.
4. Configure `BackgroundFetch.configure(BackgroundFetchConfig(minimumFetchInterval: 15, stopOnTerminate: false, enableHeadless: true, requiredNetworkType: NetworkType.ANY), ...)`.
5. Android: declare `RECEIVE_BOOT_COMPLETED` permission. iOS: add `fetch` to `UIBackgroundModes` in `Info.plist`.
6. Keep the existing foreground `sync_queue_manager.dart` for *immediate* drains while the user is in-app — they share the same DB rows, so no duplication risk (idempotency key + DB row state machine guarantee at-most-once).

**Test & Verification:**
- New file `test/background_sync_dispatcher_test.dart` using `fake_async` + an in-memory Drift DB + `MockClient` from `http/testing.dart`.
- Seed 3 `SyncOutbox(status: PENDING)` rows. Mock connectivity=`mobile`. Trigger the headless function directly.
- Assert: HTTP called 3 times, each with the row's `operation_id` as the `X-Idempotency-Key` header, rows transition to `SYNCED`, `BackgroundFetch.finish` invoked.
- Negative test: mock connectivity=`none` → assert HTTP never called and rows remain `PENDING`.

**Acceptance Gate:** All existing sync tests (`sync_two_phase_test.dart`, `sync_queue_triage_test.dart`, `sync_deadlock_test.dart`) must still pass. Manual smoke test on a physical Android: kill the app, toggle airplane mode off → log shows headless drain within 60 seconds.

---

### PROMPT 17 — Asset Font Pipeline

**Objective:** Commit and register the three typefaces the design system depends on, so Devanagari `matras` and SpaceMono hashes render correctly in production.

**Instructions:**
1. Create directory `assets/fonts/`. Place these files (download from Google Fonts):
   - `SpaceGrotesk-Regular.ttf` (400), `SpaceGrotesk-SemiBold.ttf` (600), `SpaceGrotesk-Bold.ttf` (700)
   - `SpaceMono-Regular.ttf` (400), `SpaceMono-Bold.ttf` (700)
   - `NotoSansDevanagari-Regular.ttf` (400), `NotoSansDevanagari-Medium.ttf` (500), `NotoSansDevanagari-Bold.ttf` (700)
2. In `pubspec.yaml`, under the existing `flutter:` block, add:
   ```yaml
   fonts:
     - family: SpaceGrotesk
       fonts:
         - asset: assets/fonts/SpaceGrotesk-Regular.ttf
         - asset: assets/fonts/SpaceGrotesk-SemiBold.ttf
           weight: 600
         - asset: assets/fonts/SpaceGrotesk-Bold.ttf
           weight: 700
     - family: SpaceMono
       fonts:
         - asset: assets/fonts/SpaceMono-Regular.ttf
         - asset: assets/fonts/SpaceMono-Bold.ttf
           weight: 700
     - family: NotoSansDevanagari
       fonts:
         - asset: assets/fonts/NotoSansDevanagari-Regular.ttf
         - asset: assets/fonts/NotoSansDevanagari-Medium.ttf
           weight: 500
         - asset: assets/fonts/NotoSansDevanagari-Bold.ttf
           weight: 700
   ```
3. Do not change any `TextStyle.fontFamily` strings — they already match these family names.

**Test & Verification:**
- `flutter pub get && flutter run` on a device. Render `DashboardScreen` and capture a screenshot.
- Pixel-diff the Hindi subtitle "बायोमास स्कैन करें" — kerning must show unmodulated, even-thickness strokes (no system Roboto fallback).
- Add a golden test `test/typography_golden_test.dart` rendering each of the four `TextStyle` variants on a 200×80 canvas.

**Acceptance Gate:** Zero `Could not find a set of Noto fonts` warnings in `flutter run --verbose`. Golden test passes on Linux + macOS.

---

### PROMPT 18 — Backend Auth (JWT + Device Attestation)

**Objective:** Lock down the FastAPI surface. Pilot blocker until done.

**Instructions:**
1. Add `python-jose[cryptography]==3.3.0`, `passlib[bcrypt]==1.7.4`, `python-multipart==0.0.20` to `backend/requirements.txt`.
2. New file `backend/auth.py`:
   - `class TokenPayload(BaseModel): sub: str; device_id: str; exp: int`
   - Function `create_access_token(device_id: str) -> str` — JWT signed with `HS256`, key from `JWT_SECRET` env var, 7-day TTL.
   - `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/device")`
   - `async def require_device(token: str = Depends(oauth2_scheme)) -> TokenPayload` — decodes JWT, raises 401 on failure.
3. New table `devices` (`device_id` PK uuid, `display_name`, `secret_hash` bcrypt, `created_at`, `revoked_at` nullable).
4. New endpoint `POST /api/v1/auth/device` — accepts `{device_id, secret}` form-data, returns `{access_token, token_type:"bearer"}`. Uses `passlib.context.CryptContext(["bcrypt"])` to verify against `devices.secret_hash`.
5. Apply `Depends(require_device)` to **every** existing endpoint (`/api/v1/batches`, `/api/v1/media`, future `/api/v1/batches/sync`).
6. Flutter side: store the access token in `flutter_secure_storage` under key `dmrv_jwt`. `SyncQueueManager` reads it and adds `Authorization: Bearer <token>` to every POST.
7. `.env` additions: `JWT_SECRET=<openssl rand -hex 32>` — never commit. `.env.example` should ship a placeholder.

**Test & Verification:**
- New file `backend/tests/test_auth.py`:
  - `test_unauthenticated_returns_401` — POST `/api/v1/batches` with no `Authorization` header → 401.
  - `test_login_returns_token` — POST `/api/v1/auth/device` with valid creds → 200 + `access_token` field present.
  - `test_invalid_secret_returns_401`.
  - `test_revoked_device_returns_403` — set `revoked_at`, retry → 403.
  - `test_authenticated_batch_post_returns_201` — full happy path.

**Acceptance Gate:** Existing 27 pytest assertions plus 5 new auth tests = **32/32 passing**. Update `STATUS.md` with the new auth flow diagram.

---

### PROMPT 19 — Alembic Migrations + Dockerfile + GitHub Actions CI

**Objective:** Make the backend deployable and reproducible. Currently ops-only docs exist; this prompt produces the actual infra files.

**Instructions:**
1. Initialize Alembic: `cd backend && alembic init alembic` (already partially done — confirm `alembic.ini` + `alembic/env.py`).
2. Edit `alembic/env.py` to read `DATABASE_URL` from env, import `Base.metadata` from `backend.models`, set `target_metadata = Base.metadata`.
3. Run `alembic revision --autogenerate -m "initial schema"` — commit the generated `alembic/versions/<rev>_initial_schema.py`.
4. Add to `backend/server.py` startup: `await run_migrations_async()` that shells `alembic upgrade head` (or programmatic equivalent via `alembic.command.upgrade`).
5. Create `backend/Dockerfile`:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   RUN mkdir -p /app/uploads
   EXPOSE 8001
   CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
   ```
6. Create `docker-compose.yml` at repo root with `postgres:15-alpine` + `api` service (mirror `DEPLOYMENT.md`).
7. Create `.github/workflows/backend-ci.yml`:
   - Triggers on `push` and `pull_request`.
   - Jobs: `lint` (`ruff check backend/`), `test` (matrix on Py 3.11 + Postgres service), `docker-build` (only on `main`).
8. Create `.github/workflows/flutter-ci.yml` — `flutter analyze`, `flutter test`, build artifact APK on tag.

**Test & Verification:**
- Locally: `docker-compose up --build` → curl `http://localhost:8001/api/health` → 200.
- Apply migration to a fresh Postgres: `alembic upgrade head` → confirm all tables present via `\dt`.
- Push to a branch → GitHub Actions run, both jobs green.

**Acceptance Gate:** `docker-compose up` boots cleanly. CI badge in `PROJECT_README.md` shows green on `main`.

---

### PROMPT 20 — Auditor Web Portal (React + Vite + the existing FastAPI)

**Objective:** Build the secondary-persona surface. Auditors / registries log in, browse signed batches, replay the SHA-256 chain, download evidence.

**Instructions:**
1. Create `auditor_portal/` at repo root. Scaffold with `npm create vite@latest -- --template react-ts auditor_portal`.
2. Backend: add `GET /api/v1/audit/batches` (paginated list of all batches with `net_credit_t_co2e`, `lastHash`, `signed_at`), `GET /api/v1/audit/batches/{batch_uuid}` (full payload + linked media), `GET /api/v1/audit/batches/{batch_uuid}/proof` (returns the full chain: original payload JSON, canonical-sorted form, computed SHA-256, stored SHA-256, ✓/✗ match).
3. Auditor role: extend `devices` table with `role` column (`field_worker` | `auditor`). Auditor endpoints require `role == 'auditor'`.
4. Frontend pages:
   - `/login` — JWT login form.
   - `/batches` — table: batch_uuid, feedstock, net credit, signed_at, status pill (verified ✓ / mismatch ✗).
   - `/batches/:id` — full evidence view: GPS pin (Leaflet), media gallery, LCA breakdown (8-step table), **Proof Replay** button → calls `/proof` endpoint and renders a side-by-side diff of stored vs recomputed SHA-256.
5. Visual system: reuse TerraCipher palette via CSS variables (`--tactical-titanium`, `--cobalt-shield`, `--yield-gold`, `--midnight-cyber`, `--telemetry-cyan`). Mono font for all hashes.
6. Deploy target: same Docker network. Add `auditor` service to `docker-compose.yml` running `nginx` serving the Vite `dist/`.

**Test & Verification:**
- Backend: `backend/tests/test_audit.py` — list, detail, proof endpoints; assert proof recomputation succeeds for a known fixture batch.
- Frontend: `auditor_portal/src/__tests__/proof_replay.test.tsx` — Vitest + Testing Library. Mock `/proof` response with a *deliberately mismatched* SHA-256 → assert UI renders red "INTEGRITY FAIL" banner.
- E2E: Playwright script logs in as auditor, opens a batch, clicks Proof Replay → screenshot saved to `auditor_portal/e2e/screenshots/`.

**Acceptance Gate:** Auditor can log in, view a batch, hit "Replay Proof" and see ✓. Field-worker JWT must get 403 on auditor endpoints.

---

### PROMPT 21 — Localization (intl)

**Objective:** Move every Hindi string out of hard-coded literals into ARB files; add an in-app language toggle.

**Instructions:**
1. Add `flutter_localizations: sdk: flutter` and `intl: any` to `pubspec.yaml`.
2. Create `lib/l10n/app_en.arb` and `lib/l10n/app_hi.arb`. Migrate every Hindi/English literal from screens into these files. Each ARB entry includes `description` and `placeholders` blocks.
3. Add `l10n.yaml` at repo root pointing to `lib/l10n/`.
4. In `main.dart`, expose `MaterialApp(locale, localizationsDelegates, supportedLocales)`. Locale comes from a new `localeProvider` (Riverpod `StateProvider<Locale>`).
5. Refactor `dashboard_screen.dart`, `lantana_sourcing_screen.dart`, etc. to call `AppLocalizations.of(context)!.bayomassScan` instead of literals.
6. Add a long-press easter-egg on the TerraCipher logo → bottom sheet with EN / हिंदी toggle, persisted via `shared_preferences`.

**Test & Verification:**
- `flutter gen-l10n` regenerates `lib/l10n/app_localizations.dart` cleanly.
- New widget test `test/locale_switch_test.dart` — pumps with `Locale('en')`, asserts "Scan Biomass Input" visible; rebuilds with `Locale('hi')`, asserts "बायोमास स्कैन करें" visible.

**Acceptance Gate:** Zero hard-coded Devanagari literals remain in `lib/ui/`. Verified by `grep -rP "[\u0900-\u097F]" lib/ui/ | wc -l` → 0.

---

### PROMPT 22 — Observability (Sentry + Structured Logs)

**Objective:** Add crash reporting and request tracing so we can debug field issues we can't reproduce.

**Instructions:**
1. Flutter: add `sentry_flutter: ^8.10.1`. In `main.dart` wrap `runApp` with `SentryFlutter.init((options) { options.dsn = String.fromEnvironment('SENTRY_DSN'); options.tracesSampleRate = 0.2; }, appRunner: () => runApp(...))`.
2. Backend: add `sentry-sdk[fastapi]==2.18.0`. In `server.py`: `sentry_sdk.init(dsn=os.environ['SENTRY_DSN'], traces_sample_rate=0.2, integrations=[FastApiIntegration()])`.
3. Replace `print()` and `debugPrint()` in services with `Logger` from `package:logging`. Attach a `Logger.root.onRecord` listener that forwards `Level.WARNING+` to Sentry breadcrumbs.
4. Backend: replace `print()` with `structlog` (add to requirements). Configure JSON renderer. Every request gets a `request_id` middleware that attaches to all log lines for that request.
5. Add a global Riverpod `Provider<Logger>` so widgets/notifiers can inject the logger without imports.

**Test & Verification:**
- `backend/tests/test_logging.py` — assert log lines emitted during `/api/v1/batches` POST contain `request_id`, `idempotency_key`, `batch_uuid`.
- Flutter: trigger an uncaught exception in a debug build with `SENTRY_DSN` set to a local mock; assert breadcrumb POST hit.

**Acceptance Gate:** Sentry dashboard receives at least one test event from each environment. Log volume <1 KB / request average.

---

### PROMPT 23 — S3 / Cloud Media Storage

**Objective:** Stop writing media to the backend pod's local disk. Move to S3-compatible storage with presigned upload URLs.

**Instructions:**
1. Backend: add `boto3==1.35.0`. Add env vars `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`.
2. New endpoint `POST /api/v1/media/presign` → accepts `{filename, sha256, content_type}`, returns `{upload_url, object_key, headers}`. The presigned URL is bound to the declared SHA-256 via `x-amz-checksum-sha256` so AWS rejects mismatched uploads at the edge.
3. Existing `POST /api/v1/media` is kept for backwards-compat but marked `Deprecated` in OpenAPI.
4. Flutter `SyncQueueManager` flow becomes:
   a) POST JSON to `/batches/sync` → 200 OK.
   b) For each media row in outbox → POST `/media/presign` → PUT to `upload_url` with the file bytes → mark `SYNCED`.
5. Auditor portal `/batches/:id` fetches signed GET URLs from `/api/v1/audit/media/{key}/signed-url` (expires in 5 min).

**Test & Verification:**
- `backend/tests/test_media_presign.py` using `moto` (S3 mock).
- E2E: upload a 2 MB JPEG via the new flow → confirm object exists in mock S3 with correct SHA-256 metadata.

**Acceptance Gate:** Zero new uploads land in `backend/uploads/` after this prompt. `/api/v1/media` returns `410 Gone` after a one-week deprecation window.

---

### PROMPT 24 — End-to-End Field Smoke Test (CI-enforceable)

**Objective:** Codify the whole 8-step field flow as a single integration test that runs on every push.

**Instructions:**
1. New file `test/integration/full_field_flow_test.dart` (annotated `@Tags(['integration'])`).
2. Test uses `IntegrationTestWidgetsFlutterBinding`. Mocks BLE via `MockBleTemperatureService` and `MockBleWeightScaleService` (already in test dir). Mocks camera via a fixture image bundled at `test/fixtures/sample_biomass.jpg`.
3. Script:
   - START NEW BATCH → assert batch UUID minted.
   - Sourcing → tap `-73h TEST` → PROCEED TO MOISTURE.
   - Moisture → enter `12.5` → CAPTURE METER PHOTO → assert outbox row inserted.
   - INITIATE PYROLYSIS → emit 10 mock temperature readings → END BURN.
   - Yield → emit 5 stable readings (variance=0.04kg) → LOCK YIELD → SAVE YIELD.
   - End-Use → fill all fields → COMMIT END-USE.
   - Assert: 5 outbox rows exist (`system_metadata`, `biomass_sourcing`, `pyrolysis_telemetry`, `yield_metrics`, `end_use_application`).
   - Trigger sync against a `MockClient` → assert all 5 rows transition `PENDING → SYNCED`.
4. Wire into `.github/workflows/flutter-ci.yml` as a separate job `integration` (Android emulator on macOS runner).

**Test & Verification:** This *is* the test.

**Acceptance Gate:** GitHub Actions `integration` job green on `main`. Test runtime <90 seconds.

---

### PROMPT 25 — Documentation Pass + ADR-001

**Objective:** Write the *one* document a new engineer can read in 30 minutes to understand the whole system.

**Instructions:**
1. Create `docs/ADR-001-truth-machine-architecture.md`. Sections: Context, Decision, Consequences, Alternatives Considered. Pull from this file + STATUS.md + the two source PDFs.
2. Create `docs/sequence-diagrams/` with Mermaid diagrams for:
   - `01-batch-capture-flow.mmd` (Dashboard → Sourcing → Moisture → Pyrolysis → Yield → End-Use → Outbox)
   - `02-sync-flow.mmd` (Outbox PENDING → Headless task → POST → SYNCED)
   - `03-auditor-proof-replay.mmd` (Auditor Portal → /proof endpoint → SHA-256 recompute)
3. Update `PROJECT_README.md` to link to ADR-001 and the sequence diagrams.
4. Generate OpenAPI client SDK for Dart: `npx @openapitools/openapi-generator-cli generate -i http://localhost:8001/api/openapi.json -g dart-dio -o packages/dmrv_api_client`. Wire `SyncQueueManager` to use the generated client instead of hand-rolled `http` calls.

**Test & Verification:**
- Render Mermaid diagrams in GitHub preview — must compile.
- `dart pub publish --dry-run` in `packages/dmrv_api_client` → no errors.

**Acceptance Gate:** A new engineer can clone the repo, run `docker-compose up`, open `docs/ADR-001-...md`, and submit a meaningful PR within their first 4 hours.

---

## PART C — PRIORITY ORDER & EFFORT ESTIMATE

| Order | Prompt | Effort | Why first |
|---|---|---|---|
| 1 | **P18** Auth | 1.5 days | Pilot blocker — backend is wide open |
| 2 | **P19** Alembic + Docker + CI | 1 day | You can't reproduce a deploy today |
| 3 | **P17** Fonts | 2 hours | Cheapest win — fixes Hindi rendering |
| 4 | **P16** Background sync | 1 day | Closes the only Phase-1 gap |
| 5 | **P20** Auditor portal | 3–5 days | Unlocks the second persona = revenue |
| 6 | **P23** S3 media | 1 day | Required before any real pilot scale |
| 7 | **P24** Integration test | 1 day | Stops regressions while you build P20 |
| 8 | **P22** Sentry / logs | 0.5 day | Field debug without it = guessing |
| 9 | **P21** Localization | 1.5 days | Required for non-Hindi-speaking pilots |
| 10 | **P25** Docs + ADR | 0.5 day | Onboarding-velocity multiplier |

**Total: ~12 engineer-days for a production-ready Phase-2 release.**

---

## PART D — PROMPT TEMPLATE (use for any future prompt)

```
## PROMPT N — <One-Line Title>

**Objective:** <One sentence: what problem this solves and why now.>

**Instructions:**
1. <Concrete step. Mention exact file paths, exact dependency names + pinned versions, exact env var names.>
2. ...
N. <Last step is always integration / wiring into existing flow.>

**Test & Verification:**
- <Unit test file path + 2-3 assertions.>
- <Integration / widget / E2E test if applicable.>
- <Manual verification step on physical hardware if BLE / Camera / GPS involved.>

**Acceptance Gate:** <Single measurable criterion. CI green, file count = 0, latency budget, etc.>
```

**Rules of thumb (learned from the original PDF):**
- Always name a real file (`lib/services/foo.dart`), never "a service file".
- Always pin dependency versions.
- Always include a negative test (the wrong input → the right error).
- Always end with a "do not proceed until X passes" gate so the AI doesn't bleed into the next prompt's scope.
- Never combine prompts. One prompt, one AI session, one PR.
