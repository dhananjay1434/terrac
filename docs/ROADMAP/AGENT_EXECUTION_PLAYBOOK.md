# AGENT EXECUTION PLAYBOOK — dMRV demo → production

**Date:** 2026-07-09 · **Derived from:** `PRODUCTION_READINESS_PLAN.md` (v2) + line-level ground-truth verification of the actual code on branch `feature/t5-india`.
**Audience:** an AI coding agent (or junior engineer) executing ONE task at a time. Every task below is self-contained: what to read, what to change, what tests to write, what gates must pass, what to commit, and what is forbidden.

---

# SECTION 0 — GLOBAL OPERATING RULES (read before EVERY task, no exceptions)

## 0.1 The repo

- Root: `flutter_dmrv/` — Flutter app in `lib/`, `android/`, `test/`; FastAPI backend in `backend/`.
- Working branch: create `feature/<task-id>` off the current branch per task, or commit directly on the phase branch if instructed — but **one task = one commit**, always.
- `backend/server.py` is a single 2322-line file. `lib/services/sync_queue_manager.dart` is 613 lines. Line numbers cited in tasks are accurate as of this writing but WILL drift as tasks land — always re-locate by the quoted code snippet, never blindly by line number.

## 0.2 The gates — run ALL of these before every commit

| Gate | Command (from repo root) | Pass condition |
|---|---|---|
| G1 Backend tests | `cd backend` then `python -m pytest -q` | 0 failures. Test count must never DECREASE. |
| G2 Flutter analyze | `flutter analyze` | Baseline is ~25 info-level issues in legacy files. Your change must add ZERO new issues of any level. |
| G3 Flutter tests | `flutter test` | 0 failures. |
| G4 Drift codegen (only if you touched `lib/data/local/tables.dart` or `app_database.dart`) | `dart run build_runner build --delete-conflicting-outputs` | Completes; commit regenerated `*.g.dart`. |
| G5 Alembic (only if you touched `backend/models.py`) | new revision file + `alembic upgrade head` runs on a scratch DB; CI's `alembic check` passes | Migration chain stays linear (current head: `a2b3c4d5e6f7`). |

If a gate fails, FIX IT before committing. Never commit red. Never weaken/delete an existing test to get green — if an existing test genuinely conflicts with a required behavior change, the task text will say so explicitly; otherwise treat existing tests as the specification.

## 0.3 Hard fences — things NO task ever permits

1. **Never edit generated files** (`lib/data/local/app_database.g.dart`, any `*.g.dart`) — regenerate them with G4.
2. **Never edit an existing alembic migration file.** New behavior = new revision. The chain (in order) is: `8fd65cb412f6 → d7e8f9a0b1c2 → a1b2c3d4e5f6 → b2c3d4e5f6a7 → c3d4e5f6a7b8 → d4e5f6a7b8c9 → e5f6a7b8c9d0 → f6a7b8c9d0e1 → a7b8c9d0e1f2 → b8c9d0e1f2a3 → c9d0e1f2a3b4 → d0e1f2a3b4c5 → e1f2a3b4c5d6 → f1a2b3c4d5e6 → a2b3c4d5e6f7`.
3. **Never change credit math** (`compute_lca`, decay curves, H:Corg thresholds, emission factors) unless the task explicitly says "methodology change, flag-gated". Compliance behavior changes ONLY via the provisional/reasons model — a batch missing evidence gets `provisional=true` + a reason string; it is NEVER rejected and a credit is NEVER auto-issued.
4. **API/schema changes are additive-only.** Never rename or remove a JSON field, column, or endpoint the shipped client uses. Old clients must keep syncing.
5. **Never put a secret in the repo.** No secrets in `.bat`, `.md`, `.dart`, `.py`, `.yml`, URLs, or test fixtures. Secrets live in env vars / CI secrets / `backend/.env` (gitignored). `demo_tools/` currently violates this — that is task P0.3, not license to add more.
6. **Never touch the Ed25519 signing scheme** (`crypto_signer.dart` canonical string `$method\n$path\n$idempotencyKey\n$bodySha\n$deviceId\n$signedAt` and its server verifier) — it is a device↔server contract; changing either side bricks the fleet.
7. **Never mark a sync outbox row FAILED_PERMANENTLY for a 401/403** — those are transient by decision 16C (`sync_queue_manager.dart` ~line 355). Only 422/other-4xx are permanent.
8. **`demo_tools/` never ships** — nothing in `lib/` or `backend/` may import from or depend on it.
9. **Windows environment**: shell commands in CI files use bash; local verification commands must work in PowerShell. Python is `python` (conda). Flutter is on PATH.
10. **Never run `git push --force`, never amend published commits, never skip hooks.**

## 0.4 Commit format

```
<type>(<scope>): <what changed> (<TASK-ID>)
```
Types: `feat`, `fix`, `refactor`, `test`, `ci`, `build`, `docs`, `chore`. Example:
`fix(backend): guard recompute json.loads against corrupt payloads (P1-B1)`

## 0.5 Task template legend

- **Type: AGENT** — fully executable by an agent with no human input.
- **Type: AGENT+HUMAN** — agent does the code; steps marked `[HUMAN]` need the owner (creating cloud accounts, generating a keystore, rotating a real secret, plugging in a phone).
- **Type: DECISION** — blocked on a product/methodology decision; the task states the exact question and the default to take if no answer.
- **Depends on** — do not start until those task IDs are committed.

## 0.6 Definition of done (applies to every task)

All gates green → new tests written and passing → commit made with the task ID → a 3-line report: what changed, what proves it works, anything discovered that the playbook got wrong (report drift — do not silently improvise).

## 0.7 Anti-hallucination protocol (MANDATORY first step of every task)

Every task's **Context** paragraph cites code that was verified against the real files on 2026-07-10. Before writing a single line:

1. **Re-read every file the task cites**, at the cited location. Confirm the quoted snippet/symbol EXISTS. Line numbers drift — re-locate by the quoted content, not the number.
2. **If a cited mechanism is missing or different**: STOP. Search for it under 2–3 alternative names (`grep` the symbol, the string literal, the table name). If still absent, report the mismatch and wait — do NOT build a parallel version of something that might exist under another name. Duplicated plumbing is the #1 failure mode this protocol exists to prevent.
3. **Never invent a field name, enum value, endpoint path, or JSON key.** Every cross-boundary name must be COPIED from its source of truth: server request models in `server.py` (pydantic classes), gate functions in `backend/corroboration.py`, client tables in `lib/data/local/tables.dart`, endpoint routing in `sync_queue_manager.dart`'s `kEndpointByTable`. If the source of truth doesn't contain the name you need, that's a finding to report, not a name to make up.
4. **Before creating any new function/writer/screen/test file**, grep for an existing one (`*WithOutbox`, `*_screen.dart`, `test_*` patterns). This codebase is FURTHER ALONG than most plans assume — verified examples: the moisture/composite/transport writers, endpoints, tables, and sync routing ALL already exist (see Section 4 preamble).
5. **When your change spans the device↔server contract**, write the contract test FIRST (client payload keys == server model fields — `test_client_contract.py` is the pattern) and only then the implementation.
6. In your task report, list every playbook claim you re-verified and flag any that were stale. The playbook gets corrected in the same commit (it's a living document).

## 0.8 The run loop — how execution proceeds when the owner says "go"

You are the tech lead of a virtual 10-team org; the playbook is your backlog. On "go" (or "continue"):

1. Open `docs/ROADMAP/PLAYBOOK_PROGRESS.md` (create on first run: a checkbox per task ID from Section 9, in order). Find the first unchecked task whose **Depends on** items are all checked.
2. If it's marked `[HUMAN]`-blocking or an unanswered **DECISION** with no stated default: post the exact question/request to the owner, mark it `⏸ blocked`, and move to the next unblocked task. Never idle while blocked; never fake a human step.
3. Execute the task: 0.7 protocol → implement in the smallest reviewable increments → write the specified tests → run ALL gates (not just the ones you think you affected).
4. Commit with the task-ID format, tick the checkbox in PLAYBOOK_PROGRESS.md (same commit), and report the 3-liner.
5. **Phase-boundary QA (non-negotiable):** when the last task of a phase is ticked, do NOT start the next phase in the same session-breath. Run the phase's EXIT GATE checklist item by item; run the FULL backend suite, full flutter suite, `flutter build apk --release` locally, and re-run the on-device checklist if the phase touched the client. Only a fully green exit gate unlocks the next phase. Record the exit-gate run (date + results) in PLAYBOOK_PROGRESS.md.
6. One task per commit, one phase at a time, no parallel half-done tasks on the same branch. If a task turns out to be >1 day of work, split it into lettered sub-commits (P1-S1a, P1-S1b…) each independently green.

---

# SECTION 1 — PHASE P0: PROTECT & RELEASE-ABLE (~3–4 days)

Goal: the company no longer fits on one laptop; a real, signed, obfuscated release APK exists; CI guards both codebases; no secret lives in the repo.

---

## TASK P0.1 — Push the repository to a remote + branch protection
**Type: AGENT+HUMAN** · **Depends on: nothing** · **Fixes: C1 (the single biggest existential risk)**

**Context:** `git remote -v` returns nothing. Branch `feature/t5-india` holds all work. There are ~18 untracked files/dirs (see `git status`): `docs/*.md` strategy documents, `demo_tools/`, `backend/Dockerfile`, `SESSION_HANDOFF.md`, `detailed.md`, `android/hs_err_pid12464.log`.

**Steps:**
1. Add to `.gitignore`: `android/hs_err_pid*.log`, `*.log`, `backend/.env`, `backend/dmrv.db`, `backend/uploads/`, `**/key.properties`, `**/*.jks`, `**/*.keystore`. Verify `backend/.env` was NEVER committed: `git log --all --full-history -- backend/.env` must be empty (if not, STOP and report — history scrub needed).
2. `git add` and commit the untracked docs (`docs/**/*.md`, `SESSION_HANDOFF.md`, `detailed.md`) as `docs(repo): commit strategy and planning documents (P0.1)`.
3. Commit `backend/Dockerfile` as `build(backend): commit Dockerfile (P0.1)`.
4. **Do NOT commit `demo_tools/` yet** — it contains secrets. That is P0.3's job; it gets committed there, after scrubbing.
5. `[HUMAN]` Create a private GitHub repo, provide the URL.
6. `git remote add origin <url>`, push `main` and `feature/t5-india`.
7. `[HUMAN]` Enable branch protection on `main`: require PR + require the two CI workflows (`backend-ci`, plus `flutter-ci` once P0.5 lands).

**Gates:** G1–G3 (nothing should change, but run them). **DO NOT:** commit `demo_tools/`, `backend/.env`, any `*.db`, `uploads/`.

---

## TASK P0.2 — Pin the two undeclared backend dependencies
**Type: AGENT** · **Depends on: nothing** · **Fixes: H10**

**Context:** `backend/requirements.txt` (13 lines, all `==`-pinned) is missing two packages that `server.py` imports: `cryptography` (Ed25519 verification) and `python-dotenv` (the `DMRV_DISABLE_DOTENV` path at server.py:98). Today they work only because the conda env happens to have them — a fresh `pip install -r requirements.txt` produces a server that crashes on import.

**Steps:**
1. In the backend Python env run `python -c "import cryptography, dotenv; print(cryptography.__version__); import importlib.metadata as m; print(m.version('python-dotenv'))"` to get the exact working versions.
2. Append both to `backend/requirements.txt` with `==<that version>`.
3. Prove it: create a scratch venv (`python -m venv .scratch-venv` in the scratchpad, NOT the repo), `pip install -r backend/requirements.txt`, then `python -c "import server"` from `backend/` with `DATABASE_URL=sqlite+aiosqlite:///:memory:` and `DMRV_HMAC_SECRET`/`DMRV_ADMIN_SECRET` set to 64-char dummy values. Import must succeed. Delete the venv after.

**Tests:** none new (this is an environment fix; the CI postgres job in `backend-ci.yml` installs from requirements.txt and will regress-guard it forever).
**Gates:** G1. **Commit:** `build(backend): pin cryptography and python-dotenv in requirements.txt (P0.2)`

---

## TASK P0.3 — Scrub secrets from demo_tools, then commit it
**Type: AGENT+HUMAN** · **Depends on: P0.1** · **Fixes: C8 (rotation half)**

**Context:** `demo_tools/*.bat` contain literal `DMRV_ADMIN_SECRET` / `DMRV_HMAC_SECRET` values and the verifier URL pattern passes the admin secret as a URL query parameter. These exact secret VALUES must be treated as burned.

**Steps:**
1. Edit every `demo_tools/*.bat`: replace each literal secret with a read from a local, gitignored file — at the top of each bat: `if exist "%~dp0demo_secrets.bat" call "%~dp0demo_secrets.bat"` and after it, a guard: `if "%DMRV_ADMIN_SECRET%"=="" echo demo_secrets.bat missing - copy demo_secrets.example.bat && exit /b 1`.
2. Create `demo_tools/demo_secrets.example.bat` containing `set DMRV_ADMIN_SECRET=CHANGE_ME` etc. (placeholders only). Add `demo_tools/demo_secrets.bat` to `.gitignore`.
3. `demo_tools/verifier_view/index.html` + `demo_tools/pick_batch.py`: the admin secret must NOT appear in a URL. Change the page to read the secret from a browser `prompt()` stored in `sessionStorage` (demo-grade is fine — the real fix is the P2 portal), and `pick_batch.py` to print the URL WITHOUT the secret param.
4. Grep-audit the whole repo for the burned secret values and for `X-Admin-Secret` literals: `git grep -I` for each value. Zero hits outside `.gitignore`d files.
5. `[HUMAN]` Generate new 64-hex-char values for `DMRV_ADMIN_SECRET` and `DMRV_HMAC_SECRET` (e.g. `python -c "import secrets;print(secrets.token_hex(32))"`), put them in `backend/.env` and `demo_tools/demo_secrets.bat` (both gitignored). NOTE: rotating `DMRV_HMAC_SECRET` invalidates historical `lca_signature` values — acceptable NOW because all data is demo data. After P3.6 (key versioning) rotation becomes safe forever; until then, never rotate again.
6. Commit the scrubbed `demo_tools/` tree.

**Tests:** extend `backend/tests/remediation/test_repo_hygiene.py` with a test that walks `demo_tools/` (if present) and asserts no line matches `set DMRV_(ADMIN|HMAC)_SECRET=[0-9a-f]{16,}` (a literal hex secret).
**Gates:** G1. **Commit:** `fix(security): remove literal secrets from demo_tools; secrets load from gitignored file (P0.3)`
**DO NOT:** print old or new secret values in any committed file, test, or report.

---

## TASK P0.4 — Sentry release-build guard
**Type: AGENT** · **Depends on: nothing** · **Fixes: H9**

**Context:** `lib/main.dart` (~line 34) reads `SENTRY_DSN` with `defaultValue: ''`. `SentryFlutter.init` with an empty DSN silently disables reporting — a release fleet whose crashes vanish.

**Steps:**
1. In `main()` before `SentryFlutter.init`, add:
   ```dart
   const sentryDsn = String.fromEnvironment('SENTRY_DSN', defaultValue: '');
   assert(() { if (sentryDsn.isEmpty) debugPrint('[Sentry] DSN empty — crash reporting OFF (debug ok)'); return true; }());
   if (kReleaseMode && sentryDsn.isEmpty) {
     // Fail loudly at startup rather than ship a black-box fleet.
     throw StateError('Release build without SENTRY_DSN. Pass --dart-define=SENTRY_DSN=...');
   }
   ```
   Use `sentryDsn` in `options.dsn`.
2. Mirror the existing pattern used by `DMRV_PINNED_CERT_PEM` (see `sync_queue_manager.dart` ~line 138) — this codebase already has the "required in release, optional in debug" idiom; match it.

**Tests:** `test/release_guards_test.dart` — a unit test that documents the guard (can't flip kReleaseMode in a test; instead test a small extracted function `validateReleaseConfig({required bool isRelease, required String dsn})` that throws when `isRelease && dsn.isEmpty`. Extract the check into that function in `main.dart` so it's testable).
**Gates:** G2, G3. **Commit:** `fix(client): refuse release builds without SENTRY_DSN (P0.4)`

---

## TASK P0.5 — Flutter CI lane
**Type: AGENT** · **Depends on: P0.1** · **Fixes: H11**

**Context:** `.github/workflows/` has `backend-ci.yml` (lint + sqlite tests + postgres tests + alembic check) and `codegen.yml`. Nothing builds or tests the Flutter app.

**Steps:**
1. Create `.github/workflows/flutter-ci.yml`:
   - Trigger: `push` + `pull_request` on paths `lib/**, test/**, android/**, pubspec.*, .github/workflows/flutter-ci.yml`.
   - Job `analyze-test` on `ubuntu-latest`: checkout → `subosito/flutter-action@v2` with a PINNED Flutter version (run `flutter --version` locally and pin that exact version — record it in the yml comment) and `cache: true` → `flutter pub get` → `flutter analyze --no-fatal-infos` (fatal on warning+) → `flutter test --coverage`.
   - Job `build-release-apk`: needs `analyze-test`. `flutter build apk --release --dart-define=SENTRY_DSN=https://ci-placeholder@sentry.invalid/1 --dart-define=DMRV_API_BASE_URL=https://ci.invalid --dart-define=DMRV_PINNED_CERT_PEM="$CI_DUMMY_PEM"` — supply every dart-define that release code requires (full list: `SENTRY_DSN`, `DMRV_API_BASE_URL`, `DMRV_PINNED_CERT_PEM`, `TALSEC_SIGNING_CERT_HASH`, `TALSEC_IOS_TEAM_ID`, `ENROLLMENT_TOKEN` can be empty, `DMRV_PROJECT_ID` can be empty). Use obviously-fake placeholder values; upload the APK as a build artifact (retention 7 days).
   - The point of the build job is catching R8/ProGuard/manifest breakage on every PR, not producing a shippable artifact.
2. `dart run build_runner build --delete-conflicting-outputs` must NOT be needed in CI (generated files are committed) — add a CI step that runs codegen and fails if `git diff --exit-code` shows drift (guards stale `.g.dart`). **Check `.github/workflows/codegen.yml` first** — it may already do exactly this; if so, don't duplicate it, just reference it.

**Gates:** the workflow itself must go green on the pushed branch. G2/G3 locally first.
**Commit:** `ci(flutter): add analyze + test + release-apk build lane (P0.5)`

---

## TASK P0.6 — Real release keystore + signing config
**Type: AGENT+HUMAN** · **Depends on: P0.1** · **Fixes: C2 (build.gradle.kts:44)**

**Context:** `android/app/build.gradle.kts` `buildTypes.release` currently has `signingConfig = signingConfigs.getByName("debug")` with a comment admitting it (T0.6). A debug-signed APK is package-replaceable by anyone — unshippable.

**Steps:**
1. `[HUMAN]` Generate the keystore (ONE time, then back it up in a password manager + one offline copy — losing it means losing the Play identity forever):
   `keytool -genkey -v -keystore dmrv-release.jks -keyalg RSA -keysize 4096 -validity 10000 -alias dmrv` — store OUTSIDE the repo.
2. Agent: add to `android/app/build.gradle.kts` the standard `key.properties` pattern:
   ```kotlin
   val keystoreProperties = java.util.Properties()
   val keystorePropertiesFile = rootProject.file("key.properties")
   if (keystorePropertiesFile.exists()) {
       keystoreProperties.load(java.io.FileInputStream(keystorePropertiesFile))
   }
   // inside android { }
   signingConfigs {
       create("release") {
           keyAlias = keystoreProperties["keyAlias"] as String?
           keyPassword = keystoreProperties["keyPassword"] as String?
           storeFile = keystoreProperties["storeFile"]?.let { file(it) }
           storePassword = keystoreProperties["storePassword"] as String?
       }
   }
   buildTypes {
       release {
           signingConfig = if (keystorePropertiesFile.exists())
               signingConfigs.getByName("release") else signingConfigs.getByName("debug")
           // debug fallback ONLY so CI (no keystore) can smoke-build; the
           // publish pipeline MUST provide key.properties.
           ...existing minify/proguard lines unchanged...
       }
   }
   ```
3. Create `android/key.properties.example` with placeholder keys (`storeFile=../dmrv-release.jks` etc.). Confirm `key.properties` + `*.jks` are gitignored (P0.1 added them).
4. `[HUMAN]` Create `android/key.properties` locally; run `flutter build apk --release` with real dart-defines; verify signature: `apksigner verify --print-certs build/app/outputs/flutter-apk/app-release.apk` shows the new cert, not `Android Debug`.
5. Delete the now-stale T0.6 comment block.

**Tests:** none automatable; step 4 is the proof. **Gates:** G2, G3, P0.5 workflow still green (CI path uses the debug fallback).
**Commit:** `build(android): real release signing via key.properties with CI debug fallback (P0.6)`

---

## TASK P0.7 — Validate the release build on-device; close ProGuard gaps
**Type: AGENT+HUMAN** · **Depends on: P0.6** · **Fixes: H12, M15(FLAG_SECURE part), H13**

**Context:** `isMinifyEnabled = true` + `proguard-rules.pro` exist but NO R8 release build has ever been exercised on a device. `proguard-rules.pro` covers flutter/sqlite/secure_storage/sentry/talsec/BLE/workmanager — it does NOT cover CameraX (`camera` plugin), `androidx.exifinterface` (used by `native_exif`), or geolocator's play-services location internals.

**Steps:**
1. Add to `android/app/proguard-rules.pro`:
   ```
   # camera (CameraX) — reflection-heavy; plugin channel breaks silently if stripped.
   -keep class androidx.camera.** { *; }
   -dontwarn androidx.camera.**
   # native_exif reads EXIF via androidx.
   -keep class androidx.exifinterface.** { *; }
   # geolocator play-services location.
   -keep class com.google.android.gms.location.** { *; }
   -dontwarn com.google.android.gms.**
   ```
2. `[HUMAN + agent driving]` Build `flutter build apk --release --obfuscate --split-debug-info=build/symbols` with real dart-defines, install on the physical Android device, and walk this scripted checklist end-to-end. For each item record PASS/FAIL:
   a. App launches (no instant R8 crash) · b. FLAG_SECURE: screenshot attempt is blocked · c. Secure camera opens, captures, EXIF GPS written · d. BLE scan finds the scale/thermocouple (or virtual if demo defines on) · e. A full batch syncs (metadata → media 201s) · f. Kill app mid-batch, relaunch, no crash · g. Airplane mode capture → reconnect → sync · h. Background sync fires with app backgrounded 15+ min (workmanager) · i. Note EVERY permission dialog that appears; note if background sync silently never runs.
3. If (h) fails on Android 13+: add `<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>` to the manifest and a runtime request at first launch, then retest. Do NOT add permissions preemptively without the failing test — the manifest currently declares camera/location/internet/BLE only, and every added permission is Play-review surface.
4. Archive `build/symbols/` — from now on every release build must keep symbols for Sentry symbolication (note this in `docs/RELEASE_CHECKLIST.md`, which you create with the step-2 checklist as its content).
5. Check the build log/device for the 16 KB page-size warning; if present, that's P0.8 — record it there, don't fix here.

**Tests:** `docs/RELEASE_CHECKLIST.md` IS the test (repeatable, scripted). **Gates:** G2, G3.
**Commit:** `build(android): CameraX/exif/location keep rules + on-device release validation checklist (P0.7)`

---

## TASK P0.8 — 16 KB page-size compliance
**Type: AGENT+HUMAN** · **Depends on: P0.7** · **Fixes: H12 (page-size half)**

**Context:** A 16 KB page-size warning was observed on-device during demo prep. Google Play requires 16 KB-compatible native libraries for new releases (hard requirement for target API 35+). Native libs here come from Flutter engine, `sqlcipher_flutter_libs`, `flutter_reactive_ble`, `freerasp`, `sentry_flutter`.

**Steps:**
1. Diagnose: `python -c` or use `unzip -l` on the built APK to list `lib/arm64-v8a/*.so`, then check alignment with the `check_elf_alignment` approach: for each `.so`, `objdump -p <lib> | findstr LOAD` — every LOAD segment's `align` must be `2**14` (16384) or higher. Simpler: `flutter build apk --release` with AGP ≥ 8.5.1 + latest Flutter prints per-lib compliance; or use Play Console's pre-launch report after upload.
2. Fix path (in order of preference): (a) upgrade Flutter stable (`flutter upgrade`) — recent Flutter engines are 16 KB-aligned; (b) bump `sqlcipher_flutter_libs`, `freerasp`, `flutter_reactive_ble`, `sentry_flutter` to their latest compatible versions in `pubspec.yaml`; (c) if AGP is old, bump `android/settings.gradle.kts` AGP to ≥ 8.5.1.
3. After each bump: `flutter pub get`, G2, G3, rebuild, re-check alignment. A Flutter upgrade may change analyzer baselines — if new deprecation infos appear in YOUR baseline count, fix them (do not suppress).
4. `[HUMAN]` Re-run the P0.7 on-device checklist after the upgrade (engine bumps can break plugins).

**Gates:** G2, G3, alignment check clean, P0.7 checklist re-passed. **Commit:** `build(android): 16KB page-size compliance via engine/plugin upgrades (P0.8)`
**DO NOT:** upgrade any package's MAJOR version silently — if a major bump is unavoidable, report it and its changelog first.

---

## TASK P0.9 — Finalize applicationId
**Type: DECISION → AGENT** · **Depends on: nothing (but must land before first Play upload)** · **Fixes: M15**

**Context:** `applicationId = "io.dmrv.dmrv_app"` with a TODO comment (build.gradle.kts:24). The applicationId is PERMANENT once on Play.

**The question for the owner:** keep `io.dmrv.dmrv_app` or move to a company domain id (e.g. `com.rodicconsultants.dmrv`)? **Default if no answer: keep `io.dmrv.dmrv_app`** (only change it if the io.dmrv domain isn't controlled).
**Steps if changed:** update `applicationId` AND `namespace` in build.gradle.kts, move `MainActivity.kt` package dir, update any `io.dmrv` references (`git grep io.dmrv`), delete the TODO comment. NOTE: changing applicationId orphans installed dev builds and their local DBs — coordinate with any enrolled field devices (re-enrollment needed).
**Gates:** G2, G3, release build installs. **Commit:** `build(android): finalize applicationId (P0.9)`

---

## TASK P0.10 — Dependency policy: lock is law
**Type: AGENT** · **Depends on: P0.5** · **Fixes: M10**

**Steps:**
1. Confirm `pubspec.lock` is committed (it should be). In `flutter-ci.yml`, ensure `flutter pub get` runs with `--enforce-lockfile` so CI can never silently resolve newer versions.
2. Add to `docs/RELEASE_CHECKLIST.md`: "before a release branch: `flutter pub outdated` reviewed; any upgrade is its own commit with G1–G4 green."
3. Backend equivalent already holds (requirements.txt fully `==`-pinned after P0.2) — add a one-line CI check in `backend-ci.yml`: `python -m pip check` after install.

**Gates:** both CI workflows green. **Commit:** `ci(deps): enforce lockfile in flutter CI + pip check in backend CI (P0.10)`

---

## P0 EXIT GATE (verify before declaring P0 done)
- [ ] `git remote -v` shows origin; `main` + feature branch pushed; branch protection on.
- [ ] Both CI workflows exist and are green on the remote.
- [ ] `git grep` for the burned secret values → zero hits; `demo_tools/` committed scrubbed.
- [ ] A release APK signed by the REAL keystore passed the full on-device checklist, 16 KB-clean.
- [ ] `pip install -r backend/requirements.txt` in a fresh venv can `import server`.

---

# SECTION 2 — PHASE P1a: BACKEND ROBUSTNESS FIXES (~4 days)

These are small, surgical, individually committable. Do them in ID order.

---

## TASK P1-B1 — Guard every `json.loads` in the recompute/compliance path
**Type: AGENT** · **Depends on: nothing** · **Fixes: C6**

**Context:** `backend/server.py` recompute (~lines 905–1080) parses stored `payload_json` with bare `json.loads` at these sites: line 927–929 (`tel`/`yld`/`app_row` payloads), 964 (per moisture row), 982 (per composite-sample row), 1018 (per transport row); plus line 2289 (`batch.provisional_reasons`) in `batch_compliance`. One corrupted row (bad write, manual DB edit, partial migration) raises `JSONDecodeError`, which aborts the whole recompute → the batch's credit path is permanently bricked, and on line 2289 the compliance READ endpoint 500s.

**Steps:**
1. Add near the top of server.py (after existing helpers):
   ```python
   def _safe_json(raw: str | None, *, context: str) -> dict | list | None:
       """Parse stored payload JSON defensively. Corrupt evidence must degrade
       to 'this row contributes nothing' + a log line — never a 500 that
       bricks the batch's recompute path."""
       if not raw:
           return None
       try:
           return json.loads(raw)
       except (ValueError, TypeError):
           log.error(f"[recompute] corrupt payload_json ({context}) — row skipped")
           return None
   ```
2. Replace each cited site. Semantics per site:
   - 927–929: `tel_payload = _safe_json(tel.payload_json, context=f"telemetry {buid}") if tel else None` (same for yld/app). Downstream code already handles `None` payloads (verify by reading the consumers; if a consumer assumes non-None when the row exists, treat corrupt the same as row-absent).
   - 964/982: inside the `sum(...)` generators, a corrupt row simply doesn't count as photographed: `payload = _safe_json(r.payload_json, context=...); 1 if payload and payload.get("sha256_hash") else 0` — restructure the genexp into a small loop for readability.
   - 1018: `te_payloads = [p for r in te_rows if (p := _safe_json(r.payload_json, context=...)) is not None]`.
   - 2289: `reasons = _safe_json(batch.provisional_reasons, context=...) or []` and guard that it's a list: `if not isinstance(reasons, list): reasons = []`.
3. Search for any OTHER bare `json.loads(` in server.py operating on DB-stored text (grep `json.loads`) and apply the same treatment — the audit's line list may be incomplete. Do NOT touch `json.loads` on request bodies (those are pydantic-validated upstream or intentionally fail-fast).

**Tests:** new file `backend/tests/test_corrupt_payload_recompute.py`:
- Insert a batch + a moisture row with `payload_json="{not json"` directly via the session, POST a valid evidence item to trigger recompute → 201 (not 500), batch stays provisional, corrupt row counted as not-photographed.
- Corrupt `provisional_reasons` on a batch, GET `/api/v1/batches/{uuid}/compliance` → 200 with empty/valid reasons list.
- One test per corrupted table type (telemetry, yield, application, composite, transport) asserting recompute completes.

**Gates:** G1. **Commit:** `fix(backend): corrupt payload_json degrades gracefully instead of bricking recompute (P1-B1)`

---

## TASK P1-B2 — Harden the create_batch race fallback
**Type: AGENT** · **Depends on: nothing** · **Fixes: C7**

**Context:** `server.py` 1428–1447. On `IntegrityError` the fallback does `select(Batch).where(Batch.batch_uuid == payload.batch_uuid)` then `scalar_one()`. Two failure modes: (1) if the unique collision was on `operation_id` (idempotency key) with a DIFFERENT `batch_uuid`, `scalar_one()` raises `NoResultFound` → unhandled 500; (2) the fallback never verifies the existing row belongs to the SAME device — a colliding key from another device gets that device's batch replayed back as its own 200.

**Steps:**
1. Rewrite the except block:
   ```python
   except IntegrityError:
       await session.rollback()
       existing = (await session.execute(
           select(Batch).where(Batch.operation_id == x_idempotency_key)
       )).scalar_one_or_none()
       if existing is None:
           # Collision was on batch_uuid with a different operation_id.
           existing = (await session.execute(
               select(Batch).where(Batch.batch_uuid == payload.batch_uuid)
           )).scalar_one_or_none()
       if existing is None:
           raise HTTPException(status_code=409, detail="race_unresolvable")
       same_device = existing.device_id == x_device_id
       same_uuid = str(existing.batch_uuid) == str(payload.batch_uuid)
       existing_sha = existing.sha256_hash.lower() if existing.sha256_hash else None
       payload_sha = payload.sha256_hash.lower() if payload.sha256_hash else None
       if not (same_device and same_uuid
               and existing_sha == payload_sha
               and existing.operation_id == x_idempotency_key):
           raise HTTPException(status_code=409,
                               detail="race_resolved_with_different_payload")
       batch = existing
   ```
2. Preserve the response shape of the success path exactly (idempotent replay must look identical to first-write).

**Tests:** extend `backend/tests/test_p0_22_race_payload.py` (currently 1 test): (a) same op-id, different batch_uuid → 409 not 500; (b) same op-id + same payload from a DIFFERENT device_id → 409; (c) true idempotent replay (same device, same everything) → 201/200 with identical body.
**Gates:** G1 — pay attention to `test_sync.py` (7 tests) and `test_evidence_upsert.py`, which exercise replay semantics; they must stay green unmodified.
**Commit:** `fix(backend): create_batch race fallback validates device + uuid + handles op-id collisions (P1-B2)`

---

## TASK P1-B3 — Normalize all datetime comparisons to aware-UTC
**Type: AGENT** · **Depends on: nothing** · **Fixes: H1**

**Context:** `server.py` 1376–1384: the teleport check strips tzinfo (`payload.harvest_timestamp.replace(tzinfo=None) - prev.harvest_timestamp.replace(tzinfo=None)`). If one timestamp arrived as `+05:30` and the other as `Z`, stripping tzinfo silently produces a 5.5-hour error → false "implausible_movement" 403s (blocking honest evidence) or missed teleports.

**Steps:**
1. Add helper:
   ```python
   def _as_utc(dt: datetime) -> datetime:
       """Naive datetimes are treated as UTC (the client always sends UTC ISO);
       aware ones are converted. All comparisons happen in aware-UTC."""
       if dt.tzinfo is None:
           return dt.replace(tzinfo=timezone.utc)
       return dt.astimezone(timezone.utc)
   ```
2. Teleport check becomes `abs((_as_utc(payload.harvest_timestamp) - _as_utc(prev.harvest_timestamp)).total_seconds())`.
3. Grep server.py for every OTHER `.replace(tzinfo=None)` and every naive `datetime.utcnow()` (should be none; the codebase uses `datetime.now(timezone.utc)`) and every subtraction between a column datetime and a payload datetime — normalize each through `_as_utc`. List every site you changed in your report.

**Tests:** new `backend/tests/test_timezone_normalization.py`: two batches from the same device, second harvest_timestamp sent with `+05:30` offset representing the SAME instant + a nearby location → must NOT 403; same instant/location with mixed naive/aware → identical verdict as all-UTC.
**Gates:** G1 (`test_gps_corroboration.py`'s 3 tests are the regression floor). **Commit:** `fix(backend): timezone-aware UTC normalization for all datetime comparisons (P1-B3)`

---

## TASK P1-B4 — Canonical UUID normalization at write
**Type: AGENT** · **Depends on: nothing** · **Fixes: H4**

**Context:** `batches.batch_uuid` is `PG_UUID(as_uuid=True)`; all six evidence tables store `batch_uuid` as `String(36)`. Joins/lookups rely on the string form being lowercase-canonical. An uppercase UUID from a future client would silently orphan evidence on Postgres (string `!=` UUID text form).

**Steps:**
1. In every evidence-ingest endpoint (`create_moisture` 1780, `create_composite_sample` 1803, `create_transport_event` 1826, `create_telemetry` 1850, `create_yield` 1879, `create_metadata` 1908, `create_application` 1938) normalize at the top: `buid = str(UUID(payload.batch_uuid)).lower()` — pydantic may already coerce; verify each request model's `batch_uuid` field type. If it's `str`, add a pydantic `field_validator` on the shared base (or each model) doing `return str(UUID(v))` — this rejects malformed UUIDs with 422 AND canonicalizes case. Prefer the validator approach: one definition, all models.
2. Ensure `_evaluate_anchor` / recompute lookups compare like-for-like (`str(batch.batch_uuid)` vs stored string).

**Tests:** new `backend/tests/test_uuid_canonicalization.py`: POST moisture evidence with an UPPERCASE batch_uuid → 201, then recompute finds it (compliance endpoint shows the reading counted); malformed uuid → 422.
**Gates:** G1. **Commit:** `fix(backend): canonicalize batch_uuid case at ingest so evidence can never orphan (P1-B4)`

---

## TASK P1-B5 — Media upload: cleanup on failure + payload validator bounds
**Type: AGENT** · **Depends on: nothing** · **Fixes: M2 (residual), M4**

**Context (ground-truth corrected):** the path-traversal guard at server.py:1585 ALREADY runs before `open()` at 1588, and `_SAFE` regex sanitizes device/op — the original audit line about "guard after write" is stale. What remains: (a) if hash-verify or DB insert fails AFTER `f.write(content)`, the orphan file stays on disk forever; (b) several pydantic request models lack `max_length` on free-text fields (`feedstock_species`, buyer fields, `fuel_type`, etc.) — a 10 MB string in a JSON field sails through into `payload_json`.

**Steps:**
1. In `upload_media` (1483): wrap everything after the file write in `try/except`; on any failure `file_path.unlink(missing_ok=True)` then re-raise. Also write to a temp name first (`f"{op}.part"`) and `os.replace` to final name only after the hash check passes — a crashed request never leaves a plausible-looking `.bin`.
2. Audit every pydantic request model in server.py: every `str` field gets `max_length` (256 for names/ids/species/methods, 64 for hashes, 2048 for anything free-text), every float that is physically bounded gets `ge`/`le` (`moisture_percent: ge=0, le=100`; `latitude ge=-90 le=90`; `longitude ge=-180 le=180`; kg/litres `ge=0, le=1_000_000`). List every field you bounded in the report. The global body-size middleware (server.py:296) is the outer wall; these are the inner walls.

**Tests:** extend `backend/tests/test_endpoint_schemas.py`: oversized string → 422; out-of-range moisture/lat → 422; media upload where the DB insert is forced to fail (monkeypatch session.commit) leaves NO file in uploads dir.
**Gates:** G1 — `test_p0_24_upload_limit.py` and `test_media_auth.py` are the regression floor. **Commit:** `fix(backend): media temp-file write with cleanup + bounded payload validators (P1-B5)`

---

## TASK P1-B6 — Regression tests for already-fixed races (no code change expected)
**Type: AGENT** · **Depends on: nothing** · **Closes: H7 verification, M2 verification**

**Context:** ground truth shows two audit findings were already fixed in code but may lack pinning tests: (a) GC ordering — `sync_queue_manager.dart` 565-575 stamps `media_synced_at` BEFORE deleting the file (comment 16B); (b) media path guard order (see P1-B5 context).

**Steps:** verify `test/sync_two_phase_test.dart` and `backend/tests/remediation/test_media_anchoring.py` actually pin these behaviors. If yes, report "already pinned" and close with a docs-only commit noting it. If no: add (client) a test that simulates crash-between-stamp-and-delete → retry treats row as synced, file re-delete is safe; (backend) covered by P1-B5's tests.
**Gates:** G1, G3. **Commit:** `test(sync): pin GC stamp-before-delete ordering (P1-B6)` (or docs-only note).

---

# SECTION 3 — PHASE P1b: CLIENT ROBUSTNESS (~1 week)

---

## TASK P1-C1 — Failure visibility: `failure_reason` column + retry API in SyncQueueManager
**Type: AGENT** · **Depends on: nothing** · **Fixes: C3 (data layer half — the screen is P1-S7)**

**Context:** `sync_queue_manager.dart` marks rows `FAILED_PERMANENTLY` in two places (retry-exhaustion ~line 260; `PermanentSyncException` ~line 465) writing ONLY the status — the reason (`jsonResponse.body`, exception text) is debugPrinted and lost. Nothing in the app can list or retry these rows.

**Steps:**
1. `lib/data/local/tables.dart` → `SyncOutbox` table (line ~222): add ONLY `TextColumn get failureReason => text().nullable()();` — **`lastAttemptAt` ALREADY EXISTS at tables.dart:231; do not re-add it** (verify it's being populated by the sync loop; if not, populate it in step 2). Bump `schemaVersion` in `app_database.dart` (find the current number, +1) and add the drift `onUpgrade` migration step (`m.addColumn(syncOutbox, syncOutbox.failureReason)`) following the exact pattern of the existing v21/v22/v23 migration steps. Run G4.
2. In both FAILED_PERMANENTLY write sites and in the retry-increment path, also write `failureReason: Value(_truncate(reasonText, 500))` and stamp the existing `lastAttemptAt` column.
3. Add public API to `SyncQueueManager`:
   ```dart
   /// All rows an operator needs to see: PENDING with retries, FAILED_PERMANENTLY.
   Stream<List<SyncOutboxData>> watchProblemRows();
   /// Reset a permanently-failed row for another attempt (operator-initiated).
   Future<void> retryPermanentlyFailed(String operationId); // status→PENDING, retryCount→0, failureReason kept until next terminal state
   Future<void> retryAllPermanentlyFailed();
   ```
   then `kickSync()`.
4. Migration test: extend `test/data/local/migration_test.dart` with the new version following the existing per-version test pattern (`migration_v21_c5_delivery_test.dart` is the template).

**Tests:** `test/sync_failure_visibility_test.dart`: force a 422 (mock http client, pattern exists in `sync_queue_triage_test.dart`) → row FAILED_PERMANENTLY with failureReason containing the server body; `retryPermanentlyFailed` resets it; a subsequent 201 clears it to SYNCED.
**Gates:** G2, G3, G4. **Commit:** `feat(sync): persist failure reasons + operator retry API for stranded rows (P1-C1)`
**DO NOT:** change the 16C rule (401/403 stay transient).

---

## TASK P1-C2 — Clock-skew detection and surfacing
**Type: AGENT** · **Depends on: P1-C1** · **Fixes: H6**

**Context:** v2 signing embeds `signedAt` (crypto_signer.dart ~150); the server enforces `DMRV_CANONICAL_SKEW_SECONDS`. A device with a wrong clock gets 401 on every upload → infinite transient retries (correct per 16C, but invisible and unexplained).

**Steps:**
1. In `sync_queue_manager.dart`, on ANY http response, read the standard `date` response header; compute `skew = serverDate.difference(DateTime.now().toUtc())`. If `skew.abs() > Duration(minutes: 2)`, store it in a new `clockSkewProvider` (`StateProvider<Duration?>` in `lib/providers/sync_providers.dart`).
2. On 401 responses specifically, if skew is over threshold, write `failureReason: 'clock_skew: device clock is off by ${skew.inMinutes} min — fix date/time settings'` on the row (still transient, still retried).
3. The sync health screen (P1-S7) renders the banner; nothing UI here.

**Tests:** `test/clock_skew_detection_test.dart`: mock client returns `date` header 30 min ahead + 401 → provider holds the skew, row stays PENDING with the clock_skew reason; skew < 2 min → provider null.
**Gates:** G2, G3. **Commit:** `feat(sync): detect server-vs-device clock skew and label auth failures with it (P1-C2)`

---

## TASK P1-C3 — Resume covers every partial-batch state
**Type: AGENT** · **Depends on: nothing** · **Fixes: C5**

**Context:** `dashboard_provider.dart` 86–97 `findIncompleteBatch` = "has biomass_sourcing row, lacks end_use_application row", read from `biomass_sourcing`. Misses: batch with only `system_metadata` (created, killed before moisture persisted), and resume doesn't restore which steps were already done (card statuses) or the batch session.

**Steps:**
1. Rewrite `findIncompleteBatch` to anchor on `system_metadata` (the row written at batch creation — verify with `lib/data/local/tables.dart` SystemMetadata and its writer): most recent `system_metadata.batch_uuid` having no `end_use_application` row. Keep it one SQL statement.
2. Add `Future<BatchProgress> loadBatchProgress(AppDatabase db, String batchUuid)` returning which stages have rows: `hasSourcing` (biomass_sourcing), `hasMoisture` (count of moisture_readings), `hasTelemetry` (pyrolysis_telemetry), `hasYield` (yield_metrics), `hasEndUse`. Pure query object — unit-testable without widgets.
3. On resume (wherever `findIncompleteBatch`'s result is consumed — trace it from `dashboard_screen.dart`): restore `batchSessionProvider` to that uuid AND set each dashboard `CardStatus` from `BatchProgress` (`verified` for done stages, `pending` for the first undone, `locked` after). Today's behavior on fresh-launch-mid-batch is the bug — reproduce it first with the existing `find_incomplete_batch_test.dart` harness, then fix.

**Tests:** extend `test/find_incomplete_batch_test.dart`: batch with metadata only → found; with sourcing+telemetry but no yield → found + progress shows exactly {sourcing, telemetry}; completed batch → not found. Widget test in `test/ui/screens/dashboard_screen_test.dart`: resumed batch renders correct card states.
**Gates:** G2, G3. **Commit:** `fix(client): resume finds every partial-batch state and restores step progress (P1-C3)`

---

## TASK P1-C4 — BLE stream error handling + disconnect surfacing during burn
**Type: AGENT** · **Depends on: nothing** · **Fixes: H5**

**Context:** `lib/providers/pyrolysis_ble_notifier.dart` ~99–101: `_connSub/_tempSub/_attestSub = _source.<stream>.listen(...)` with NO `onError`. A BLE stack error kills the subscription silently: burn continues, telemetry silently truncates, operator learns nothing.

**Steps:**
1. Add `onError` to all three subscriptions → route into a new state field `bleError: String?` on the notifier state (copyWith pattern already there) + `debugPrint`. On temperature-stream error, also record a gap marker: append `{'t': _clock().toIso8601String(), 'gap': true}` to the telemetry log so the server-side ≥60-sample check sees an honest hole rather than a smooth-looking truncation.
2. Watchdog: `_lastSampleAt` already exists — add a periodic 15 s timer during an active burn; if `now - _lastSampleAt > 30 s` and burn is running, set `state = state.copyWith(connectionLost: true)`. Clear on next sample.
3. `pyrolysis_screen.dart`: when `connectionLost || bleError != null`, show a persistent `t.danger` banner: "Thermocouple connection lost — move closer to the kiln. Recording resumes automatically." (match existing token usage; `t.dangerSurface` background).
4. On reconnect (next sample arrives), banner clears; log continues in the same telemetry session (no restart).

**Tests:** the fake-source pattern exists (`virtual_ble_adapter_test.dart`, `ble_temperature_service_test.dart`): emit values → error → assert `bleError` set, gap marker appended, subscription of connection stream still alive; watchdog test with `fake_async` advancing 45 s without samples → `connectionLost` true, sample arrives → false.
**Gates:** G2, G3. **Commit:** `fix(ble): surface disconnects and stream errors during burn with honest telemetry gaps (P1-C4)`

---

## TASK P1-C5 — Pyrolysis END BURN pre-validation
**Type: AGENT** · **Depends on: nothing** · **Fixes: H8**

**Context:** `pyrolysis_writer.dart` line 159 throws `StateError('Saved telemetry. Cannot finalise burn: need 4 smoke captures, found N')` AFTER persisting telemetry — the screen shows a raw error and the operator is stranded mid-state. Smoke stages are `smoke_0/50/90/100` (`pyrolysis_screen.dart` 106-109, `smoke_evidence_provider.dart` 20-23).

**Steps:**
1. `pyrolysis_screen.dart`: the END BURN `DmrvButton` becomes disabled (`onPressed: null`) until `smokeEvidenceProvider` reports all 4 stages captured. Under the disabled button render which stages are missing as chips: "Photos needed: 50% · 90%" using `PremiumStatusChip`/tokens.
2. Keep the writer's throw as the last-line defense (unchanged), but the screen path can now only reach it via a race — catch it and show a human message with a "RETAKE PHOTOS" action instead of `e.toString()`.
3. `smoke_evidence_provider.dart`: expose `Set<String> capturedStages` if not already queryable.

**Tests:** widget test `test/ui/screens/pyrolysis_end_burn_gate_test.dart`: 3 of 4 stages → button disabled + missing chip shown; 4 of 4 → enabled. Existing `pyrolysis_writer_retake_test.dart` stays green untouched.
**Gates:** G2, G3. **Commit:** `fix(pyrolysis): END BURN disabled until all 4 smoke stages captured (P1-C5)`

---

## TASK P1-C6 — Passphrase safety: migration edge + recovery groundwork
**Type: AGENT** · **Depends on: nothing** · **Fixes: M12 + C4 (first slice — full recovery UX is P2-scoped with the portal)**

**Context:** `lib/data/local/passphrase_resolver.dart`: migration path writes to secure storage (line 27) then removes from SharedPreferences (28). A crash BETWEEN them is safe (next run finds secure copy first — verify!), but a crash where secure-storage write reports success yet doesn't persist (known flutter_secure_storage behavior on some OEMs) then prefs removed = passphrase gone = SQLCipher DB unreadable = every unsynced capture lost.

**Steps:**
1. Make the migration read-back-verified: after `secureStorage.write`, `final check = await secureStorage.read(key: kDbPassphraseKey); if (check != legacy) { /* leave prefs copy in place, log, return legacy */ }` — only remove from prefs after a successful read-back. Same read-back for the fresh-generation path (line 43): verify before first DB open; on mismatch throw a clear `StateError('secure storage write not persisted')` rather than proceeding to encrypt data under a key that isn't stored.
2. Priority-of-truth comment: secure storage wins; a stale prefs copy is scrubbed on the NEXT successful run.
3. C4 groundwork (data-loss blast-radius reduction, no UX yet): in `SyncQueueManager`, we already sync aggressively; add a startup metric — count of unsynced rows — logged to Sentry as a breadcrumb (`outbox_backlog: N`) so fleet-wide "data at risk on device" is observable. The full recovery-code UX is deferred; do NOT build UI here.

**Tests:** `test/secure_storage_test.dart` exists — extend: mock secure storage whose `write` succeeds but `read` returns null → prefs copy retained, passphrase still resolves; normal path → prefs scrubbed exactly once.
**Gates:** G2, G3. **Commit:** `fix(client): read-back-verified passphrase migration; never scrub the last copy (P1-C6)`
**DO NOT:** change the passphrase key name, rotate passphrases, or touch SQLCipher params — any of those bricks existing installs.

---

## TASK P1-C7 — Two-phase invariant at insert time
**Type: AGENT** · **Depends on: nothing** · **Fixes: M7**

**Context:** a media-phase outbox row whose payload lacks `photoPath` is only detected at sync time (row poisons then). The invariant belongs at write time.

**Steps:** locate the outbox-insert helper(s) (`insertBiomassSourcingWithOutbox` in `app_database.dart` / `yield_end_use_writers.dart` / `pyrolysis_writer.dart` — grep `WithOutbox`). In the shared insert path, if the entry type implies media, `assert + throw ArgumentError` when `photoPath`/`sha256Hash` are null/empty. This converts a silent field-data-loss bug class into an immediate, attributable crash at the capture site.
**Tests:** unit test on the writer: media-type outbox insert without photoPath → throws; with → row written.
**Gates:** G2, G3. **Commit:** `fix(sync): enforce media payload invariant at insert time, not sync time (P1-C7)`

---

# SECTION 4 — PHASE P1c: THE RAINBOW CAPTURE SCREENS (~2 weeks)

**Ground truth (verified 2026-07-10) that makes these tasks smaller than the plan feared — the ENTIRE data layer already exists; these tasks are UI-only:**
- Client Drift tables: `MoistureReadings` tables.dart:269, `CompositePileSamples` :294, `TransportEvents` :324.
- Client writers, ALL implemented in `lib/data/local/app_database.dart`: `insertMoistureReadingWithOutbox` (:398, signature `{batchUuid, moisturePercent, sequence, photoPath, sha256Hash}` → returns readingUuid), `insertCompositePileSampleWithOutbox` (:436), `insertTransportEventWithOutbox` (:482).
- Sync routing, ALL wired: `kEndpointByTable` map + `endpointForTable()` in `sync_queue_manager.dart` (~:58–69) route by the outbox row's `targetTable` (`moisture_readings`→`/api/v1/moisture` etc.; unknown table throws StateError — loud by design).
- **Two-phase is ONE outbox row, not two**: the writer inserts a single row whose payload carries `photo_path`/`sha256_hash`; the sync loop does Phase 1 (JSON POST to the routed endpoint) then Phase 2 (media multipart to `/api/v1/media`) from that same row. Do NOT create separate media outbox rows for these flows.
- Server endpoints: `POST /api/v1/moisture` server.py:1780, `/composite-sample` :1803, `/transport` :1826, models in models.py.
- Gate rules (source of truth `backend/corroboration.py`): moisture `required = max(10, ceil(biomass_kg/100))`, counts rows whose payload has `sha256_hash`, reason `insufficient_moisture_samples` (:125–137). Composite: **≥ 1** photographed sample, reason `missing_composite_sample` (:180–195). Pyrolysis open-kiln: payload `smoke_evidence` list of `{stage, sha256}` dicts must cover `{flame_curtain, quenching, flame_height}` + `flame_height_m` with `0 ≤ h < 0.5` (:141–167). Closed-kiln: `ignition_energy_type` required (:170–177). Kiln-type vocabulary is lowercase `"open"` / `"closed"`. Biomass method vocabulary includes `yield_conversion` (reasons `missing_biomass_input`, `missing_conversion_factor`, :198+).

**Every screen task still starts with the 0.7 protocol — re-verify these locations before coding.**

**Every new screen follows the house style:** `ConsumerStatefulWidget`, tokens via `context.tokens` (never raw colors — the 36 DmrvTokens fields are the only palette), `DmrvButton`/`DmrvPanel`/`PremiumScreenHeader`/`PremiumStatusChip` components, human error strings (never `e.toString()` — the pattern to copy is end_use's "GPS fix failed. Move to open sky and retry."), photos via `SecureCaptureService` (returns `SecureCaptureResult` with sandboxPath/sha256Hash/GPS/mock-flag), all persistence through a `*WithOutbox` writer inside one DB transaction, Hindi-ready strings in `lib/l10n/` (add keys to both `app_localizations_en.dart` and `_hi.dart` — English text in the Hindi file with a `// TODO(i18n)` is acceptable until P4).

---

## TASK P1-S1 — Moisture multi-reading loop (THE bug)
**Type: AGENT** · **Depends on: P1-C1 (uses failure surfacing), P1-S2 recommended first (target count needs biomass kg)** · **Fixes: the C2 shape mismatch — the single genuine compliance bug**

**Context:** `moisture_verification_screen.dart` persists ONE `moisture_percent` into `BiomassSourcing` via `insertBiomassSourcingWithOutbox` (lines 78–131). The server C2 gate counts `moisture_readings` ROWS: `derive_moisture_compliance(photographed, batch.biomass_input_kg)` where photographed = rows whose payload has `sha256_hash` (server.py:954–966). Required count = `max(10, ceil(biomass_kg / 100))`. Today that count is always 0 → C2 can never pass from the field.

**Steps:**
1. Read first: `moisture_verification_screen.dart` (all), `moisture_gate_notifier.dart`, `MoistureReadings` table (tables.dart:269 — has `readingUuid`, `batchUuid`, `moisturePercent`, `sequence` unique per batch, `sandboxPath`, `sha256Hash`, `createdAt`), server `create_moisture` (1780) for the exact JSON contract, `test/moisture_evidence_test.dart`, `test/remediation/sync_routing_test.dart`.
2. **The writer ALREADY EXISTS**: `insertMoistureReadingWithOutbox` at `app_database.dart:398` — signature `{required String batchUuid, required double moisturePercent, required int sequence, String? photoPath, String? sha256Hash}`, returns readingUuid, writes ONE outbox row (`targetTable: 'moisture_readings'`) whose payload carries the photo refs for the automatic two-phase upload. Routing to `/api/v1/moisture` already exists in `kEndpointByTable`. **Do NOT write a new writer or routing.** Only verify retake semantics: the table's unique `{batchUuid, sequence}` key means a retake of the same sequence needs insert-or-replace — check whether the writer handles conflict; if plain `insert` throws on retake, add `mode: InsertMode.insertOrReplace` + a fresh outbox row (server side is idempotent per reading_uuid — confirm against `create_moisture`'s upsert behavior in server.py:1780 before choosing).
3. Screen rework — the counter-hero loop (THIS is the actual task):
   - Header shows target: "Reading 3 of 12" where target = `max(10, (biomassKg / 100).ceil())`, biomassKg from the sourcing state (P1-S2). If biomass not yet entered, target shows 10 and a hint chip.
   - Each iteration: enter % → photograph the meter (SecureCaptureService) → auto-persist that single reading via the new writer → counter advances, list of completed readings below (sequence, %, ✓).
   - Big progress state: readings done vs target as the hero numeric (`t.numericHero`), CONTINUE button (`DmrvButtonVariant.success`) enabled only at `count >= target`.
   - The EXISTING single-value flow (`insertBiomassSourcingWithOutbox` writing summary `moisturePercent` + `moistureCompliant`) stays — write the summary as the MEAN of the readings when the loop completes. Both the summary and rows ship; the server gate reads the rows.
4. Routing already exists (Section 4 preamble) — just add a widget-level assertion that each loop iteration produced exactly one outbox row with `targetTable == 'moisture_readings'`.

**Tests:** unit — writer already covered by `moisture_evidence_test.dart` (extend for retake-same-sequence semantics per step 2's finding); widget — `test/ui/screens/moisture_loop_test.dart`: target math (250 kg → 10, 1600 kg → 16 — mirror `derive_moisture_compliance` corroboration.py:125), button gating, counter renders, N iterations → N outbox rows. Backend already has `test_moisture_flow.py`; add one test there: 10 photographed readings on a 900 kg batch → compliance shows moisture gate green.
**Gates:** G1, G2, G3, G4 if schema touched (it shouldn't be — table exists). **Commit:** `feat(moisture): multi-reading capture loop writing moisture_readings rows — C2 now passable from the field (P1-S1)`
**DO NOT:** change `derive_moisture_compliance` thresholds; remove the summary write (old server versions read it).

---

## TASK P1-S2 — Biomass input on Sourcing
**Type: AGENT** · **Depends on: nothing** · **Fixes: C1 gate inputs + C2 dynamic threshold**

**Context:** `BiomassSourcing` already has `biomassInputKg` + `biomassMeasurementMethod` columns (tables.dart, v17) and `insertBiomassSourcingWithOutbox` likely already accepts them (verify — `backend/tests/test_biomass_input.py` exists, so the server contract is live). The screen never collects them.

**Steps:** on `lantana_sourcing_screen.dart` add a "Biomass weight" section: numeric field (kg, `PremiumInputField`, bounded 1–100 000) + method selector of exactly two `DmrvButton`-style toggle chips: "WEIGHED" (`direct_weigh`) / "ESTIMATED FROM YIELD" (`yield_conversion`) — confirm the exact enum strings the server validates (grep `biomass_measurement_method` in server.py; use ITS vocabulary). Thread both into the sourcing state notifier → writer call in moisture screen's `_persistEvidence` (it calls `insertBiomassSourcingWithOutbox` — add the two args). Gate the sourcing CONTINUE on a valid weight.
**Tests:** notifier unit test (state carries values), widget test (invalid weight blocks continue), assert the writer receives them (existing harvest_lock/lantana notifier test patterns).
**Gates:** G2, G3. **Commit:** `feat(sourcing): biomass input weight + measurement method capture (P1-S2)`

---

## TASK P1-S3 — Kiln selection at burn start
**Type: AGENT** · **Depends on: nothing** · **Fixes: the hardcoded 200 L / WATER_QUENCH / null kiln_id — activates C0/C3/C3b/C9-PAH**

**Context (verified):** kilns are registered server-side (`POST /api/v1/admin/kiln`, `Kiln` model: kiln_id, material, weight_kg, lifetime_years, kiln_type). The client data layer is ALREADY kiln-aware: `PyrolysisTelemetry` has `kiln_type`/`kiln_id` columns (schema v16) and `flame_height_m`/`ignition_energy_type`/`ignition_energy_amount` (v19), and `pyrolysis_writer.dart:143-147` already puts all of them in the payload. What's missing is purely that NO UI ever sets them. The exact hardcode sites: `pyrolysis_screen.dart:63` passes `kilnGrossCapacity: 200.0` (comment: "default kiln gross volume (L)"), and `yield_scale_screen.dart:71-72` passes `quenchMethodology: 'WATER_QUENCH'` + `grossVolume: 200.0`. Server kiln-type vocabulary is lowercase `"open"`/`"closed"` (corroboration.py:141-177) — the UI must emit exactly those strings.

**Steps:**
1. New table `Kilns` in client `tables.dart` (kilnId unique, kilnType, capacityLitres nullable, label, addedAt) + schemaVersion bump + migration + G4. Kilns reach the device by QR: the P2 portal will render a kiln QR containing `dmrv-kiln:v1:{"kiln_id":...,"kiln_type":...,"capacity_l":...}`; until the portal exists, also provide a manual-entry form (kiln id + type picker: `OPEN` / `CLOSED` — match server vocabulary, grep `kiln_type` validation in server.py).
2. New screen `lib/ui/screens/kiln_select_screen.dart`, pushed at burn start (before `pyrolysis_screen`): list of locally known kilns as `DmrvPanel` rows (radio select) + "ADD KILN" → QR scan (reuse the QR-scan capability if present in secure camera; else manual form only, QR in P2) → selection stored in a `selectedKilnProvider`.
3. Wire the selection into the EXISTING writer params (no writer change needed): `pyrolysis_screen.dart:63` passes the selected kiln's real capacity instead of `200.0` and passes `kilnId`/`kilnType` (check `insertPyrolysisTelemetryWithOutbox`'s signature at pyrolysis_writer.dart:70 — the params exist since v16/v19); `yield_scale_screen.dart:71-72` gets the quench methodology from a picker (confirm allowed values against `quench_methodology` validation in server.py — it's `max_length=128` free text at :1701, so define the app-side vocabulary: `WATER_QUENCH` stays the default option) and the real gross volume from the selected kiln. If no kiln selected, BLOCK starting the burn (the selection screen is mandatory).
4. Route: `dashboard → kiln_select → pyrolysis`.

**Tests:** migration test (new version); widget test (no kilns → add form; selection enables START BURN); writer-call test (screen passes the selected kiln's id/type/capacity — assert no literal `200.0`/unconditional `WATER_QUENCH` remains: grep-style source assertion is acceptable). Backend `test_compliance_gate_c10.py` covers `unregistered_kiln`; add a client-contract note.
**Gates:** G1–G4. **Commit:** `feat(pyrolysis): mandatory kiln selection; kiln_id/type/capacity in telemetry — kills 200L+WATER_QUENCH hardcodes (P1-S3)`

---

## TASK P1-S4 — Pyrolysis completion rework: flame height / ignition energy + stage-name alignment
**Type: DECISION → AGENT** · **Depends on: P1-S3** · **Fixes: C3 evidence set + the stage-name mismatch**

**Ground truth (verified — corroboration.py:141-177):** the gate `derive_pyrolysis_photo_compliance(kiln_type, smoke_evidence, flame_height_m)` runs ONLY when `kiln_type == "open"`. It reads the telemetry payload's `smoke_evidence` — a list of `{"stage": <str>, "sha256": <str>}` dicts — and requires the stage set to cover `{"flame_curtain", "quenching", "flame_height"}`, plus `flame_height_m` with `0.0 ≤ h < 0.5`. Closed kilns instead need `ignition_energy_type` (`derive_ignition_compliance`). The app today captures 4 photos labeled `smoke_0/50/90/100` — first VERIFY how `pyrolysis_writer.dart` builds `smoke_evidence` from the mediaCaptures rows (it selects `captureType.like('smoke_%')` at :89-95): whatever stage strings land in the payload are what the gate sees, so today the gate finds `smoke_*` stages and fails the subset check.
**The decision (ask methodology owner, DEFAULT stated):** do the 3 required stages REPLACE the 4 smoke-opacity stages, or come IN ADDITION (7 photos)? **Default if no answer: ADD the 3 required stages as captures during the burn flow (flame_curtain mid-burn, flame_height with the numeric entry, quenching at end) and keep the 4 smoke photos** — additive, satisfies the gate, loses nothing. Do NOT invent a mapping like smoke_50→flame_curtain; the photos document different things.
**Steps:** (1) add the 3 stage captures to the pyrolysis flow with captureType exactly `flame_curtain`/`quenching`/`flame_height` (copy the smoke-stage capture pattern in `pyrolysis_screen.dart:106-109` / `smoke_evidence_provider.dart:20-23`); verify the writer's `smoke_evidence` builder picks them up (if it filters `smoke_%` only, widen the filter to include the three new types — client-side change, payload shape unchanged); (2) for `kiln_type == "open"`: flame-height numeric entry (m, `PremiumInputField`, record verbatim — the SERVER grades the <0.5 rule, don't pre-block); wire it to the existing `flame_height_m` writer param (v19, already in payload at pyrolysis_writer.dart:146 area); for `"closed"`: ignition-energy type picker + amount wired to the existing `ignition_energy_type/amount` params; (3) completion summary panel lists all captured evidence before END BURN (composes with P1-C5's gating — update the required-photo count there: 4 smoke + 3 stage photos for open kilns).
**Tests:** widget (open vs closed kiln shows the right extra steps; END BURN gating counts the right set), writer payload test (smoke_evidence contains all 7 stage entries with sha256), backend: extend the corroboration tests with a payload carrying exactly the app's produced stage list → photos_ok True.
**Gates:** G1–G3. **Commit:** `feat(pyrolysis): flame-height/ignition evidence + stage-name alignment with server gate (P1-S4)`

---

## TASK P1-S5 — Composite sample screen
**Type: AGENT** · **Depends on: nothing (P1-S3 improves it: kiln QR in frame)** · **Fixes: C4 capture + the physical↔digital chain-of-custody key for the P2 lab flow**

**Context (verified):** client table `CompositePileSamples` (tables.dart:294), writer `insertCompositePileSampleWithOutbox` (app_database.dart:436 — ALREADY EXISTS, one outbox row, routing wired), server `POST /api/v1/composite-sample` (1803), and the gate `derive_composite_sample_compliance` (corroboration.py:180-195) all exist. The gate requires **at least ONE photographed sample** (reason `missing_composite_sample`) — NOT a computed-N loop. No screen exists; that's the whole task.

**Steps:**
1. New screen `composite_sample_screen.dart`, entered from the yield step (after biochar is weighed): instructions panel ("Place the sample bag with the batch QR card in frame"), then capture flow: photo (SecureCaptureService; GPS on) per sub-sample — minimum 1 to CONTINUE, "ADD ANOTHER SAMPLE" optional repeat (methodology says one per run; extras don't hurt).
2. **The batch QR**: add a `batch_qr_card` widget — renders the batch UUID as a QR (add `qr_flutter` to pubspec — a pure-Dart, no-native-lib package; pin exact version) shown full-screen so the operator can photograph the PHYSICAL printed card *or* screen alongside the sample. This QR value (`dmrv-batch:v1:<uuid>`) is what the lab scans in P2 — keep the format versioned.
3. Persist via the EXISTING `insertCompositePileSampleWithOutbox` (app_database.dart:436 — read its full signature first; it takes sampledAt and more).
4. Dashboard card for the step (`CardStatus` wiring like the others).

**Tests:** widget test (capture → CONTINUE enabled at 1 sample; outbox row with `targetTable == 'composite_pile_samples'` — confirm the exact table string from the writer, don't guess); backend `test_composite_sample_flow.py` exists — extend with "1 photographed sample → gate green".
**Gates:** G1–G4 (G4 only if table tweaks needed — shouldn't be). **Commit:** `feat(composite): sub-sample capture loop with batch-QR chain-of-custody card (P1-S5)`

---

## TASK P1-S6 — Delivery & buyer fields on End-Use
**Type: AGENT** · **Depends on: nothing** · **Fixes: C5 capture gap**

**Context (verified):** client columns exist on `EndUseApplication` (tables.dart:203-211): `deliveryDate` (ISO-8601 UTC text), `deliveredAmountKg` (real), `buyerName`, `buyerContact` (all nullable; buyer fields are PII — SQLCipher-only, scrubbed by secureWipe, so NEVER log them). `backend/tests/test_delivery_buyer_flow.py` proves the server contract. The screen (`end_use_application_screen.dart`) collects method/tonnage/transport/GPS/photo only. Check whether `insertEndUseWithOutbox` (yield_end_use_writers.dart:76) already accepts the four params before extending its signature — the v21 migration suggests it might.

**Steps:** add a "Delivery" `DmrvPanel` to the end-use form: delivery date (date picker, default today, no future dates), delivered amount kg (numeric, ≤ yield), buyer name (text, required), buyer contact (text, optional). Thread through `insertEndUseWithOutbox` (extend signature — check what the server's `create_application` model expects for field names; use exactly those). `_canCommit` requires buyer name + delivered amount.
**Tests:** widget (commit blocked without buyer), writer payload assertion; backend flow test already exists.
**Gates:** G1–G3. **Commit:** `feat(end-use): delivery date/amount/buyer capture completing C5 (P1-S6)`

---

## TASK P1-S7 — Sync Health screen
**Type: AGENT** · **Depends on: P1-C1, P1-C2** · **Fixes: C3 (visibility half)**

**Steps:**
1. New screen `sync_health_screen.dart`, entered from the dashboard's integrity footer (make the footer tappable — it already shows the live dot + hash).
2. Content, in tokens/house style: (a) clock-skew banner if `clockSkewProvider` non-null — `t.danger` panel: "This phone's clock is off by N minutes. Fix Date & Time settings or evidence uploads will be rejected."; (b) summary chips: Synced / Waiting / Stuck counts (from `watchProblemRows` + a synced count query); (c) list of problem rows as `DmrvPanel`s: human operation label (map op types → "Moisture reading photo", "Burn telemetry"…), batch short-id, `failureReason` (verbatim, it's already humanized where we control it), lastAttemptAt, and per-row RETRY button (`DmrvButtonVariant.primary`) → `retryPermanentlyFailed`; (d) RETRY ALL button when any stuck.
3. NO delete/dismiss action — evidence rows are never operator-deletable (audit integrity).

**Tests:** widget test with a fake DB: one FAILED_PERMANENTLY row renders reason + retry calls the manager (mocktail); skew banner renders when provider set.
**Gates:** G2, G3. **Commit:** `feat(sync): operator-facing sync health screen with per-row retry (P1-S7)`

---

## TASK P1-S8 — In-app enrollment screen
**Type: AGENT** · **Depends on: nothing** · **Fixes: compile-time `ENROLLMENT_TOKEN` (unscalable + a burned-token trap)**

**Context:** `crypto_signer.dart` line 87 reads `ENROLLMENT_TOKEN` from dart-define; `warmUp()` (lines 67–82) auto-registers once, guarded by the `_enrolledKey` flag. Tokens are single-use, minted via `POST /api/v1/admin/mint-token`.

**Steps:**
1. New screen `enrollment_screen.dart` shown as the app's home iff not enrolled (read the `_enrolledKey` secure-storage flag via a new `enrollmentStateProvider`; main.dart routes: enrolled → dashboard, else → enrollment). Fields: backend URL (prefilled from `DMRV_API_BASE_URL` define if set, editable), enrollment token (text entry now; QR scan lands with the portal in P2 — leave a `// P2: QR` marker). ENROLL button → `CryptoSigner.registerDevice(token, baseUrl)` — refactor `registerDevice` to take explicit params, keeping the old dart-define path as fallback so existing enrolled devices and demo builds don't break (additive).
2. Success → set `_enrolledKey`, persist the base URL (secure storage, new key `dmrv.api.base_url.v1`), navigate to dashboard. Failure → human messages by cause: 401/409 "Token invalid or already used — ask your project admin for a new one", timeout "Can't reach the server — check the URL and your connection."
3. `sync_queue_manager.dart` + `crypto_signer.dart`: base-URL resolution becomes: secure-storage value → dart-define fallback. One shared resolver function, used by both.
4. `warmUp()` keeps its offline-first contract (never blocks splash); it no longer auto-registers when no dart-define token exists — enrollment is now explicit UI.

**Tests:** unit — URL resolver precedence; enrollment provider state machine (unenrolled → enrolling → enrolled/failed); widget — error message mapping; regression — `crypto_signer_test.dart` + `test/services/crypto_signer_test.dart` stay green (signature scheme untouched).
**Gates:** G2, G3. **Commit:** `feat(enrollment): first-launch in-app enrollment replacing compile-time tokens (P1-S8)`
**DO NOT:** break already-enrolled devices — the `_enrolledKey` check must short-circuit before any UI/network.

---

## P1 EXIT GATE
- [ ] Fresh phone (or wiped install): enrolls IN-APP with a minted token against the backend.
- [ ] One full batch captured on that phone where moisture (≥10 readings), biomass, kiln, pyrolysis (+flame/ignition evidence), yield, composite samples, delivery/buyer, end-use ALL sync green — `GET /api/v1/batches/{uuid}/compliance` shows every field-capturable criterion `true`, remaining reasons ONLY lab/annual/registry ones.
- [ ] Kill the app at 3 different mid-batch points → relaunch resumes with correct step states each time.
- [ ] Force a 422 → row visible in Sync Health with reason → RETRY works. Set the phone clock +30 min → skew banner appears.
- [ ] BLE power-off mid-burn → banner within 30 s; power-on → telemetry resumes with a gap marker.

---

# SECTION 5 — PHASE P2: LAB & VERIFIER PORTAL (~2–3 weeks)

Architecture (fixed): ONE static web app in `portal/` (plain HTML/JS/CSS or Vite+React — **default: Vite + React + TypeScript**, built to static files served by FastAPI `StaticFiles` at `/portal`), talking ONLY to new authenticated JSON endpoints under `/api/v1/portal/*`. Three roles enforced SERVER-side: `admin`, `lab`, `verifier`. The device API (HMAC/Ed25519) is untouched.

## TASK P2.0 — Backend modularization seam (do BEFORE any portal endpoint)
**Type: AGENT** · **Depends on: P1 exit** · **Fixes: the 2322-line server.py monolith growing unboundedly**

**Context:** `server.py` is one file. P2 adds ~15 endpoints, 3+ models, and auth machinery — landing all of it in server.py makes the monolith permanently unrefactorable. The fix is a seam, NOT a big-bang refactor (moving existing routes now would churn every open line-number reference and risk import-order bugs for zero user value).

**Steps:**
1. Create package `backend/portal/` with `__init__.py`, `auth.py` (P2.1's users/sessions/`require_role`), `routes.py` (an `APIRouter(prefix="/api/v1/portal")`), `schemas.py` (pydantic models). `server.py` gains exactly ONE new line pattern: `from portal.routes import router as portal_router` + `app.include_router(portal_router)`.
2. Shared helpers the portal needs from server.py (`get_session`, `_safe_json`, the compliance/grading function, `_SAFE`): move them to a new `backend/core.py` ONLY IF importable without side effects; otherwise import from server module directly and record the coupling as a P4.8 cleanup item. NEVER copy-paste a helper — one definition, period.
3. Rule from here on (add to Section 0.3 mentally, enforced by review): **new backend code goes in modules; server.py only shrinks.** Migration of EXISTING route groups out of server.py is P4.8 scope, one group per commit, tests green after each.

**Tests:** app boots with the router included (health test passes); an empty `/api/v1/portal/ping` (auth-free, temporary, removed in P2.1) returns 200 — proves the seam.
**Gates:** G1. **Commit:** `refactor(backend): portal package seam via APIRouter — server.py stops growing (P2.0)`

## TASK P2.1 — Portal auth: users, roles, sessions
**Type: AGENT** · **Fixes: H14, M3**
1. New models + alembic revision (additive): `portal_users` (id, email unique, password_hash — argon2 via `argon2-cffi` pinned, role enum admin/lab/verifier, created_at, disabled) and `portal_sessions` (token_hash indexed, user_id, expires_at, created_at) or JWT — **default: opaque session tokens, 24 h, stored hashed** (no JWT lib surface).
2. Endpoints: `POST /api/v1/portal/login` (rate-limited via existing `_rate_limit` bucket "admin"), `POST /api/v1/portal/logout`. Dependency `require_role(*roles)` reading `Authorization: Bearer`.
3. Bootstrap: CLI-ish endpoint is a backdoor — instead a script `backend/create_portal_user.py` run server-side with env DB access.
4. Token minting moves portal-side: `POST /api/v1/portal/tokens` (admin) wraps the existing mint logic and RETURNS the token + a QR payload string `dmrv-enroll:v1:{"url":...,"token":...}`; enforce ≥ 128-bit entropy in the mint function (M3) — verify current entropy at server.py:733's mint implementation first.
**Tests:** login/session lifecycle, role denial matrix (lab hitting admin route → 403), disabled user → 401, mint entropy length.
**Gate G1.** Commit per sub-step allowed; final: `feat(portal): role-based auth foundation (P2.1)`

## TASK P2.2 — Read API (T3.4)
**Type: AGENT**
`GET /api/v1/portal/batches` (cursor pagination on received_at desc; filters: status, provisional, device_id, project_id, date range) · `GET /api/v1/portal/batches/{uuid}` (batch + per-criterion compliance verdict — reuse the exact logic behind the existing compliance endpoint, do NOT fork the grading — + evidence counts per table + media list) · `GET /api/v1/portal/devices` · `GET /api/v1/portal/summary` (counts by status, provisional reasons histogram). All `require_role(any)`. Media bytes: `GET /api/v1/portal/media/{operation_id}` streams the file with auth (NO static file paths leak — the demo page's pattern dies here).
**Tests:** pagination stability, filter matrix, verifier can read, media route 403 unauthenticated, path traversal attempt on operation_id → 400 (reuse `_SAFE`).
Commit: `feat(portal): read API — batches, detail, devices, summary, authed media (P2.2)`

## TASK P2.3 — Portal UI: dashboard + batch detail
**Type: AGENT**
Scaffold `portal/` (Vite React TS). Pages: Login · Batches (table: short uuid, device, date, credit, provisional badge, reasons count; filters; the premium aesthetic already prototyped in `demo_tools/verifier_view/index.html` — port its visual language: hero credit number, compliance ring, grouped criteria) · Batch detail (criteria checklist grouped field/lab/annual with green/amber, evidence timeline with photos via the authed media route, audit JSON viewer). Build output committed OR built in CI — **default: CI builds it (`portal-ci.yml`: npm ci, tsc, vite build, artifact) and the backend Dockerfile copies `portal/dist`**.
**Tests:** vitest for the criteria-grouping component + API client; a Playwright smoke (login → see batch list) if quick, else defer to P3 staging.
Commit: `feat(portal): dashboard + batch detail UI (P2.3)`

## TASK P2.4 — Lab flow: scan QR → enter results → live recompute
**Type: AGENT** · **The chain-of-custody gem**
1. Route `/lab/scan`: camera QR scan (browser `BarcodeDetector` with jsQR fallback, both local — no CDN) of the `dmrv-batch:v1:<uuid>` card photographed with the composite sample (P1-S5) → lands on the batch's lab entry form.
2. Form (role lab or admin): H:Corg, Corg %, biochar moisture samples, dry bulk density (+ optional inertinite/Ro for 1000-yr) + certificate PDF upload. Submits to a new `POST /api/v1/portal/batches/{uuid}/lab-results` which WRAPS the existing `ingest_lab_results`/`ingest_lab_hcorg` logic (server.py:837/803) — same validation, same recompute trigger; the old X-Admin-Secret endpoints remain for compatibility but log a deprecation line.
3. After submit the detail page re-fetches: the `assumed_*` provisional reasons visibly flip. Certificate stored via the media-file mechanism (own operation_id namespace `labcert-<uuid>`).
**Tests:** backend — portal lab submit triggers recompute identically to the legacy channel (assert same batch state both paths); lab role can, verifier cannot (403). UI — form validation vitest.
Commit: `feat(portal): lab QR-scan entry with live recompute (P2.4)`

## TASK P2.5 — Registry forms + M5 idempotency
**Type: AGENT**
Admin pages for kilns, scale calibrations, operator training, supervisor visits, annual verification — thin forms over portal-wrapped versions of the existing admin endpoints (server.py:2031–2165). While wrapping, fix M5: make training/visit inserts idempotent on a natural key (operator+date / site+date) via upsert, matching kiln/annual behavior. Kiln page renders each kiln's QR (`dmrv-kiln:v1:...` — the P1-S3 format). Token page renders enrollment QRs (`dmrv-enroll:v1:...` — the P1-S8 format).
**Tests:** double-submit of training/visit → one row; QR payload format snapshot tests (these strings are cross-system contracts — pin them).
Commit: `feat(portal): registry forms, idempotent admin upserts, kiln/enrollment QRs (P2.5)`

## TASK P2.6 — Issuance action + immutable audit log
**Type: AGENT**
1. New model + migration: `audit_events` (id, event_type, batch_uuid nullable, actor_user_id, payload_json, created_at) — INSERT-only (no update/delete route anywhere; add a SQLAlchemy event listener raising on update as a belt-and-braces).
2. `POST /api/v1/portal/batches/{uuid}/issue` (admin only): allowed IFF `provisional == false` and every gate green (re-verify server-side at call time — never trust the UI) → sets `status = 'ISSUED'` (check the existing status vocabulary in the Batch model first; extend additively), writes an `audit_event(credit_issued, actor, credit_value, lca_signature)`.
3. Every portal mutation (lab results, registry writes, token mint, issuance) writes an audit event from here on.
4. UI: "Issue credit" button on batch detail — enabled only when server says eligible; confirmation dialog restating the credit tonnage; after: an ISSUED seal (use the seal-blue `certified` semantics matching the app).
**Tests:** issue on provisional batch → 409; issue writes audit row; double-issue → 409; verifier/lab → 403; audit rows survive and cannot be updated.
Commit: `feat(portal): deliberate credit issuance with immutable audit trail (P2.6)`

## P2 EXIT GATE
- [ ] A lab tech logs in on a phone browser, scans the printed QR from a real P1 batch's composite card, enters results, watches gates flip green.
- [ ] Admin issues that batch's credit; `audit_events` has the full story (mint→lab→issue) with actor identities.
- [ ] Zero curl in the operational workflow; the X-Admin-Secret demo page retired from use (file may remain in demo_tools).

---

# SECTION 6 — PHASE P3: DEPLOY & SCALE-HARDENING (~1–2 weeks, overlaps P2)

## TASK P3.1 — docker-compose + .dockerignore + CI image smoke
**Type: AGENT** · **Fixes: M6**
1. `backend/.dockerignore`: `__pycache__`, `*.pyc`, `.pytest_cache`, `dmrv.db*`, `uploads/`, `.env*`, `tests/`.
2. Root `docker-compose.yml`: `api` (build backend/, env from `.env.compose.example` placeholders, port 8000), `db` (postgres:16, healthcheck, volume), `minio` (for P3.3, profile-gated so it's opt-in until then). Healthcheck `start_period: 60s` (first-boot migrations are slow — the current tight value was flagged).
3. CI (`backend-ci.yml` new job): `docker build` + boot container with sqlite env + curl `/api/health` until 200 (max 90 s) → fail otherwise.
**Tests:** the CI job IS the test. **Commit:** `build(deploy): docker-compose + dockerignore + CI image-boot smoke (P3.1)`

## TASK P3.2 — Object storage abstraction for evidence media
**Type: AGENT** · **Fixes: evidence-survives-host-death (T3.3)**
1. `backend/storage.py`: `MediaStorage` protocol — `write(op_id, device, content) -> stored_path`, `open_stream(stored_path)`, `exists`. Implementations: `LocalMediaStorage` (current behavior, default) and `S3MediaStorage` (boto3 pinned; bucket/endpoint/creds from env `DMRV_MEDIA_BUCKET`, `DMRV_S3_ENDPOINT` — endpoint param makes MinIO and GCS-interop both work). Selection by env `DMRV_MEDIA_BACKEND=local|s3`.
2. `upload_media` + the portal media route go through the abstraction. `media_files.file_path` stores the abstract key, not an OS path (additive: old rows keep working via the local backend's path handling).
3. Bucket policy documented in `docs/DEPLOYMENT.md` (created here): versioning ON, object-lock/retention where supported — evidence is append-only by policy.
**Tests:** unit tests against LocalMediaStorage; S3 path tested against MinIO in a CI job (service container) — upload → hash verify → stream back.
**Commit:** `feat(backend): pluggable media storage with S3/MinIO backend (P3.2)`

## TASK P3.3 — Cloud deployment (Cloud Run + Cloud SQL + GCS)
**Type: AGENT+HUMAN** · **Fixes: SQLite-on-laptop backend**
`[HUMAN]`: GCP project, billing, Cloud SQL Postgres instance, GCS bucket (versioning+retention), Artifact Registry, a deploy service account; provide values.
Agent: `docs/DEPLOYMENT.md` runbook with exact gcloud commands; `deploy/cloudrun.yaml` (or a `gcloud run deploy` script) wiring env vars (DATABASE_URL via Cloud SQL connector, secrets from Secret Manager — NEVER env-in-yaml), min-instances 0→1 decision (default 1 — cold starts + migrations don't mix), `DMRV_SKIP_MIGRATIONS=1` on the service + a separate migration job (`gcloud run jobs`) so deploys don't race migrations across instances. **The single-process rate-limiter (`_rl_counters` dict) is per-instance — set max-instances 1 until P3.6 or accept per-instance limits (default: max-instances 1 for the pilot; note it in the runbook).**
TLS/pinning: Cloud Run terminates TLS with Google-rotated certs — SPKI pinning against leaf certs will break. Decide pin strategy: pin the intermediate/root or ship `DMRV_PINNED_CERT_PEM` empty-with-system-trust for Cloud Run and document it (**default: system trust on Cloud Run; keep the pinning code for self-hosted deployments**). Update `docs/RELEASE_CHECKLIST.md` accordingly.
Exit: a real phone enrolls + syncs a batch against the staging URL over TLS.
**Commit:** `docs(deploy): Cloud Run runbook + migration job + pinning policy (P3.3)`

## TASK P3.4 — Observability
**Type: AGENT** · **Fixes: T3.5, H9 (backend side)**
1. JSON structured logging (stdlib logging + a formatter; no new heavy deps) with request-id middleware (uuid per request, echoed in responses as `X-Request-Id`, bound into every log line).
2. `GET /metrics` (prometheus_client pinned): request counts/latencies by route, sync 5xx counter, provisional-ratio gauge, recompute duration histogram. Guard behind `DMRV_METRICS_TOKEN` header check (public /metrics leaks operational intel).
3. Sentry backend: `sentry-sdk[fastapi]` pinned, DSN from env, tracesSampleRate 0.05, PII scrubbing: strip lat/lon/device_id from breadcrumbs (mirror the client's `beforeBreadcrumb` policy).
4. Alert definitions documented in DEPLOYMENT.md: 5xx rate, p95 latency, health-check fail, provisional-ratio spike (>20% day-over-day), disk/DB connections.
**Tests:** request-id echoed; /metrics 401 without token, 200 with; log lines are valid JSON.
**Commit:** `feat(backend): structured logs, request IDs, guarded /metrics, Sentry (P3.4)`

## TASK P3.5 — Backups + restore drill
**Type: AGENT+HUMAN** · **Fixes: T3.6**
Agent: `docs/DR_RUNBOOK.md` — Cloud SQL automated backups (7 daily + PITR), GCS versioning as media backup, restore procedure step-by-step, RPO 24 h / RTO 2 h stated. A verification script `backend/scripts/verify_restore.py`: connects to a restored instance, counts batches/evidence/media rows, spot-verifies N media hashes against storage.
`[HUMAN]`: actually run one restore drill on staging; initial+date the runbook.
**Commit:** `docs(ops): DR runbook + restore verification script (P3.5)`

## TASK P3.6 — HMAC key versioning (unlocks safe rotation forever)
**Type: AGENT** · **Fixes: C8b**
1. Env becomes `DMRV_HMAC_KEYS` = JSON `{"k2":"<hex>","k1":"<hex>"}` + `DMRV_HMAC_ACTIVE_KEY=k2`. Back-compat: if only legacy `DMRV_HMAC_SECRET` set, treat as `{"k0":...}` active k0 (additive, zero-config-change deploys keep working).
2. New column via migration: `batches.lca_signature_key_id` (String(16), nullable — old rows null ⇒ k0/legacy). Signing writes the active key id; verification looks up by the row's key id.
3. Grep every HMAC use of `_HMAC_SECRET` (lca_signature signing + any verification) and route through a `_hmac_key(key_id)` resolver. The DEVICE-auth path (Ed25519) is untouched — this is only the server's own lca_signature HMAC.
**Tests:** sign under k1 → rotate active to k2 → old batch still verifies, new batch signed k2; missing key id in env → verification returns "unverifiable", not a crash.
**Commit:** `feat(backend): versioned HMAC keys for lca_signature — rotation-safe (P3.6)`

## TASK P3.7 — Recompute efficiency + rate-limit pruning
**Type: AGENT** · **Fixes: H2, H3, M1**
1. H2: in the recompute (~905–1080), collapse the 8+ sequential per-table `SELECT`s into fewer round-trips (e.g., run them with `asyncio.gather` on separate... NO — same session, so instead: one pass, and cache parsed payloads; the meaningful win is (2)).
2. Debounce: recompute currently fires per evidence POST. Add a cheap short-circuit: skip recompute if a recompute for the same batch ran < 2 s ago AND no gate could change (simplest correct version: per-batch `asyncio.Lock` + coalescing flag — last writer wins, concurrent duplicates coalesce). Keep it in-process (single instance per P3.3).
3. H3: telemetry payloads can be 100k floats — parse via `await asyncio.to_thread(json.loads, raw)` when `len(raw) > 512_000`. Apply in `_safe_json` (P1-B1) as a size-gated branch.
4. M1: replace `_rl_counters.clear()` at 4096 (server.py:386 — wipes ALL live windows, letting a flooder reset everyone's counters) with pruning: drop only entries whose `window < current_window`, and if still over cap, drop oldest windows first.
**Tests:** rate-limit: fill with stale windows → current-window counts SURVIVE pruning (this is the attack the clear-all enabled); recompute coalescing: N concurrent evidence posts → batch state correct, recompute ran < N times (counter via monkeypatch).
**Commit:** `perf(backend): recompute coalescing, threaded big-payload parse, rate-limit pruning (P3.7)`

## TASK P3.8 — 200-device load smoke
**Type: AGENT** · **Fixes: T3.8**
`backend/scripts/load_smoke.py` (httpx, no locust dep): simulates 200 devices × full batch (register skipped — pre-mint keys directly in DB via a setup helper; then metadata→moisture×10→telemetry(large)→yield→media×N→application), concurrency 20, against a target URL. Reports p50/p95/p99 per endpoint + error count. Run against staging (P3.3). Pass: zero 5xx, p95 < 2 s for JSON, < 10 s for media. Wire a reduced version (20 devices) as a manual-dispatch CI workflow against a compose stack.
**Commit:** `test(load): 200-device batch simulation script + CI smoke variant (P3.8)`

## P3 EXIT GATE
- [ ] Staging URL live: phone syncs over TLS; portal served from the same origin.
- [ ] Media in object storage with versioning; restore drill performed and dated.
- [ ] Load smoke: zero 5xx at 200 devices; rotation test: HMAC key rotated on staging without breaking a single historical signature.

---

# SECTION 7 — PHASE P4: TRUST SWITCHES & POLISH (ongoing)

Shorter specs — by this point the codebase conventions are locked and the agent has P0–P3 patterns to mirror.

- **P4.1 Attestation flip** (AGENT+HUMAN): wire Play Integrity credentials (`[HUMAN]` obtains) into the existing stub verification interface (grep `attestation` in server.py; `test_attestation.py` shows the seam). Flag `DMRV_ATTESTATION_ENFORCED` already exists — turn on in staging first; add per-device grace period for already-enrolled devices.
- **P4.2 Require canonical v2** (AGENT): flip `DMRV_REQUIRE_CANONICAL_V2` default after fleet confirms v2-only traffic (add a metrics counter for v1 requests in P3.4's /metrics first; flip when zero for 14 days).
- **P4.3 Transport factors** (DECISION+AGENT): blocked on Rainbow supplying fuel emission factors; when they arrive, update `fuel_emissions_kg_co2e` (server.py ~1020 consumer) via flag-gated methodology change WITH sign-off; then build the client transport-legs screen against the existing `/api/v1/transport` endpoint + `TransportEvents` client table (mirror P1-S5's loop pattern).
- **P4.4 Cross-field plausibility (H15)** (AGENT): server-side advisory checks — temp-log coverage vs claimed min temp, yield vs biomass ratio bounds (0.15–0.45 typical), moisture readings variance sanity. Each failure = a NEW provisional reason (additive), never a rejection. Methodology owner reviews the bounds before merge.
- **P4.5 Batch checklist hub** (AGENT): the UX spine — a per-batch screen mirroring the server's criteria list (reuse P1-C3's `BatchProgress` + the compliance endpoint when online), each row → jumps to its capture screen; makes the flow non-linear and resume obvious. This SUPERSEDES the dashboard's linear card row; keep both until field feedback picks.
- **P4.6 Full Hindi i18n** (AGENT+HUMAN): sweep every user-facing string into l10n keys (grep for raw string literals in `lib/ui/`), `[HUMAN/translator]` fills `app_localizations_hi.dart`; pseudo-locale test asserts no hardcoded strings remain in screens.
- **P4.7 Re-burn/corrective policy (M8)** (DECISION): unique-per-batch constraints forbid re-submitting corrected evidence. Question for methodology owner: supersede-with-tombstone vs new-batch-reference. Default: NEW batch with `supersedes_batch_uuid` column (additive), old batch status `SUPERSEDED`, credit only on the new one.
- **P4.8 Hygiene sweep** (AGENT): M11 ruff clean-to-blocking on backend (fix ~100 legacy issues file-by-file, one commit each area); analyzer infos in legacy Dart files to zero; M13 document BLE-whitelist threat model in `docs/SECURITY_MODEL.md` (hash entries if trivially cheap); M14 cap cleanup-manifest retries at 20 with a log line; **extract existing server.py route groups into modules** (the P2.0 seam made this safe — one group per commit: device-ingest, admin-legacy, compliance; server.py ends as app-assembly + middleware only).
- **P4.9 Play release pipeline + staged rollout** (AGENT+HUMAN): tag-driven `flutter-release.yml` — on `v*` tag: `flutter build appbundle --release --obfuscate --split-debug-info` with keystore + dart-defines from CI secrets, upload symbols to Sentry, upload `.aab` to Play **internal** track (gradle-play-publisher or fastlane; `[HUMAN]` creates the Play service account). Promotion internal→closed→production is ALWAYS a human action. `versionCode` auto-derives from the tag; `CHANGELOG.md` entry required by the workflow (fails without it). This replaces "someone builds an APK on a laptop" forever.
- **P4.10 Privacy & data-protection pack** (DECISION+AGENT — REQUIRED before any EU customer): (a) data inventory doc (`docs/PRIVACY.md`): what personal data exists (buyer name/contact, operator GPS traces, device ids), where, retention; (b) **the erasure problem**: buyer PII currently rides INSIDE the HMAC-signed `payload_json` — erasing it later breaks signature verification. DECISION for owner, default: server-side, store buyer fields ALSO in dedicated nullable columns at ingest; an erasure request nulls the columns + redacts payload_json + writes an `audit_event(pii_redacted)` recording the pre-redaction payload hash so the evidence chain stays explainable to an auditor; (c) Play data-safety form answers + a hosted privacy policy (`[HUMAN]` publishes); (d) verify Sentry scrubbing covers buyer fields (extend the `beforeBreadcrumb` filter + server-side scrubber from P3.4).
- **P4.11 Architecture record** (AGENT): `docs/ARCHITECTURE.md` — one authoritative diagram+prose doc: device (capture→outbox→two-phase sync→signing), server (ingest→anchor→recompute→provisional→issuance), portal roles, trust boundaries, key material inventory (Ed25519 device keys, HMAC key ring, keystore, SQLCipher passphrase), and the invariants from Section 0.3. New-engineer onboarding reads THIS, not 45 scattered docs. Keep it under 400 lines; link out for detail.

---

# SECTION 8 — PHASE P5: PLATFORM (later — do not start before P4.5 ships)

- **P5.0 Multi-instance scale-out** (AGENT — the task that removes P3.3's deliberate `max-instances 1` pin): the two in-process states are the rate-limit counters (`_rl_counters`) and the per-batch recompute coalescing lock (P3.7). Move both to Postgres — rate limits as an UPSERT-counter table keyed `(bucket, key, window)` with per-request increment + periodic window purge; recompute serialization via `pg_advisory_xact_lock(hash(batch_uuid))` (no new infra, no Redis until measured need). Portal sessions are already DB-backed (P2.1) and media is object storage (P3.2), so after this task the API is fully stateless → lift max-instances, re-run the P3.8 load smoke at 2+ instances, and verify rate limits hold fleet-wide, not per-instance. THIS is the gate between "pilot scale" and "any scale".
- **P5.1 Europe/Pro skin**: second `DmrvTokens` instance (all 36 fields — the `required` constructor makes partial skins impossible by design); goldens for both skins; skin picked by config/tenant, not build flavor.
- **P5.2 White-label config**: `BrandConfig` (logo asset, app name, token set, backend URL) resolved at first-launch/enrollment; QR-enrollment payload (P1-S8/P2.5 format) gains optional brand field — version the QR string to `v2`, parsers accept both.
- **P5.3 Multi-tenant backend**: `tenant_id` on projects/devices/portal_users (additive migration), row-level scoping in every portal query via the session's user; device API scoped through project linkage. Big — needs its own plan doc when reached.
- **P5.4 iOS (M9)**: pods audit, deployment target, Secure Enclave keychain flags verification, TestFlight lane. Blocked on an actual customer need; do not speculatively build.

---

# SECTION 9 — MASTER EXECUTION ORDER & TRACKING

Strict order within a column; columns can interleave where Depends-on allows.

| # | Task | Type | Blocks |
|---|---|---|---|
| 1 | P0.1 remote+push | A+H | everything (do FIRST) |
| 2 | P0.2 pin deps | A | P3.1 |
| 3 | P0.3 secrets scrub | A+H | P0 exit |
| 4 | P0.4 sentry guard | A | — |
| 5 | P0.5 flutter CI | A | P0.10 |
| 6 | P0.6 keystore | A+H | P0.7 |
| 7 | P0.7 release validation | A+H | P0.8 |
| 8 | P0.8 16KB | A+H | Play upload |
| 9 | P0.9 applicationId | D→A | Play upload |
| 10 | P0.10 lock policy | A | — |
| 11–16 | P1-B1…B6 backend fixes | A | P1 exit |
| 17 | P1-C1 failure column+retry | A | P1-C2, P1-S7 |
| 18–23 | P1-C2…C7 | A | P1 exit |
| 24 | P1-S2 biomass input | A | P1-S1 |
| 25 | P1-S1 moisture loop | A | P1 exit (THE bug) |
| 26 | P1-S3 kiln select | A | P1-S4 |
| 27–30 | P1-S4…S6, S8 | D/A | P1 exit |
| 31 | P1-S7 sync health | A | P1 exit |
| 32 | P2.0 modularization seam | A | all P2 endpoints |
| 33–38 | P2.1…P2.6 portal | A | P2 exit |
| 39–46 | P3.1…P3.8 deploy | A/A+H | P3 exit |
| 47+ | P4.1…P4.11 trust/polish/release-pipeline/privacy | mixed | GA |
| last | P5.0 scale-out, then P5.1…P5.4 platform | mixed | any-scale / multi-tenant |

**Standing decisions already made (do not re-litigate in any task):** India tokens are the only client skin until P5 · provisional model is the only compliance mechanism · Ed25519 scheme frozen · demo_tools never ships · additive-only schema · new backend code goes in modules, server.py only shrinks (P2.0) · Vite+React for portal · Cloud Run/Cloud SQL/GCS for hosting · opaque session tokens over JWT · system-trust TLS on Cloud Run · Postgres-first for shared state, Redis only on measured need (P5.0).

**Open decisions this playbook needs answered (each has a stated default):** P0.9 applicationId (default keep) · P1-S4 smoke-stage evidence: replace or add (default ADD the 3 gate stages, keep the 4 smoke photos) · P4.3 transport factors (blocked on Rainbow) · P4.7 corrective-flow policy (default supersede-by-new-batch) · P4.10 buyer-PII erasure design (default redactable columns + payload redaction with audit event).

*End of playbook. If reality contradicts a task's quoted code, trust reality, fix the playbook line in the same commit, and say so in the report.*
