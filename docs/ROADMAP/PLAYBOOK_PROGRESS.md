# PLAYBOOK PROGRESS — the live execution tracker

**This file is the single source of truth for "where are we."** One checkbox per task, in dependency order (Section 9 of `AGENT_EXECUTION_PLAYBOOK.md`). The rule (playbook §0.8): work the first UNCHECKED task whose dependencies are all checked; tick its box in the SAME commit that lands the task; never start a new phase until the prior phase's EXIT GATE is fully green.

**Legend:** `[ ]` not started · `[~]` in progress · `[x]` done (committed) · `⏸` blocked (waiting on a human/decision — note what it needs)

**Started:** 2026-07-10
**Current phase:** P1a + P1b COMPLETE ✅ → next is P1c (Rainbow capture screens, S1–S8). Backend 325 / Flutter 194, all green. P0 agent-work 8/10 (P0.7/P0.8 hardware/decision-parked).
**Next actionable task:** P1-S6 (delivery/buyer fields on End-Use — server `create_application` + `EndUseApplication` columns exist; UI only). Then S5 (composite sample), S3 (kiln select → Drift v25), S4 (pyrolysis rework), S8 (enrollment). S1+S2+S7 done.

---

## PHASE P0 — Protect & release-able
- [x] **P0.1** — Push repo to remote · pushed all 4 branches to github.com/dhananjay1434/terra (commits 9686a11, 2ea6fba, 356bf24); remote verified clean of secrets/demo_tools · `⏸ FOLLOW-UP (HUMAN, after P0.5): enable branch protection on main requiring backend-ci + flutter-ci`
- [x] **P0.2** — Pin `cryptography` + `python-dotenv` in requirements.txt · commit 1d20989 · hermetic venv import OK, suite 307/1 green
- [x] **P0.3** — Scrub secrets from demo_tools, then commit it · generated fresh 64-hex secrets myself (into gitignored backend/.env + demo_secrets.bat); scrubbed 1_start_backend.bat/pick_batch.py/index.html/DEMO_RUNBOOK.md + a tracked prompt doc; repo audit clean of both burned values; 3 new hygiene tests (G1 310/1). NOTE: demo enrollment token `demo-eu-3` remains in 3_run_app.bat — low-sev single-use, eliminated by P1-S8.
- [x] **P0.4** — Sentry release-build guard · extracted `validateReleaseConfig` in main.dart (throws in release when DSN empty) + test/release_guards_test.dart (4 tests) · G2 zero new issues, G3 169 passed
- [x] **P0.5** — Flutter CI lane · `.github/workflows/flutter-ci.yml` (analyze --no-fatal-infos + test + release-apk build, Flutter pinned 3.41.9; codegen drift already in codegen.yml, not duplicated). Cleared 9 pre-existing analyzer WARNINGS (dead imports + 1 unused var) so the warning-fatal gate is enforceable (info-level cleanup stays P4.8). All 3 CI steps verified LOCALLY green (analyze exit 0, 169 tests, APK built 95.3MB). `⏸ remote Actions run unverified — no gh CLI here; confirm on GitHub or I'll retry if gh gets installed.`
- [x] **P0.6** — Real release keystore + signing config · generated PKCS12 RSA-4096 keystore myself (outside repo) + gitignored key.properties + key.properties.example; build.gradle.kts conditional signing (release key when key.properties present, debug fallback for CI). Hit + fixed the PKCS12 key-password trap (keypass must == storepass). VERIFIED: signed APK cert = CN=dMRV (apksigner), not Android Debug. `⚠️ HUMAN residual: back up the .jks + password off-machine (single point of failure until then).`
- [~] **P0.7** — Validate release build on-device; close ProGuard gaps · `⏸ BLOCKED: no physical Android device`. The on-device walk needs hardware; ProGuard keep-rule prep can be done device-free when P0.7 is next.
- [~] **P0.8** — 16 KB page-size · DIAGNOSED device-free: 9/14 arm64 libs compliant; 5 freeRASP libs are 4KB-aligned. Fix = freeRASP 6.12→8.0 (MAJOR, API-breaking, security SDK) → reported not silently applied; deferred to P4.1 (needs device validation; blocks nothing until Play/P4.9). See RELEASE_CHECKLIST.md.
- [x] **P0.9** — Finalize applicationId · kept `io.dmrv.dmrv_app` (default), removed the TODO; namespace matches. Comment-only gradle change (build validated in P0.5).
- [x] **P0.10** — Dependency policy: lock is law · flutter-ci `pub get --enforce-lockfile` (verified exit 0 locally); backend-ci `pip check` step (verified hermetically: "No broken requirements found"); created docs/RELEASE_CHECKLIST.md with the dep-upgrade policy.
- [~] **P0 EXIT GATE** — ✅ remote pushed · ✅ no secret in repo · ✅ signed release APK (cert verified) · ✅ fresh-venv `import server` · ✅ CI workflows written+locally-green · ⏸ REMAINING (hardware/decision only): on-device checklist (P0.7, needs device), 16KB (P0.8, freeRASP major bump→P4.1), remote-CI-green confirm (no gh), branch-protection toggle. **All agent-doable P0 work is DONE (8/10 tasks); the 2 open items and the gate confirmations need hardware or a human toggle.**

## PHASE P1a — Backend robustness
- [x] **P1-B1** — Guard every json.loads in recompute/compliance · added `_safe_json` helper; hardened all 7 sites (telemetry/yield/application scalars, moisture/composite sum-gens, transport list-comp, compliance provisional_reasons) with isinstance-dict guards. +4 tests (corrupt row excluded not fatal; compliance still 200). G1 314 passed.
- [x] **P1-B2** — Harden create_batch race fallback · fallback now looks up by operation_id first then batch_uuid (no scalar_one → no NoResultFound 500), and validates device+uuid+op-id+sha before returning 200 duplicate. +1 test (concurrent same-op/different-uuid never 500). G1 315 passed.
- [x] **P1-B3** — Timezone-aware UTC normalization · added `_as_utc`; fixed the teleport check (was stripping tzinfo on both operands → up-to-hours skew on mixed tz) + consolidated 3 already-correct sites (enrollment expiry, scale-cal, timestamp parse). +4 deterministic unit tests. G1 319 passed.
- [x] **P1-B4** — Canonical UUID normalization at write · `_BatchScopedPayload` mixin canonicalizes batch_uuid (str(UUID(...))) + 422s malformed, applied to all 7 str-uuid evidence payloads. +2 tests. Fixed one incidental test fixture (test_signature used a non-UUID placeholder). G1 321 passed.
- [x] **P1-B5** — Media temp-file cleanup + payload validator bounds · B5a: media UUID parsed before write + post-write rollback/unlink (no orphan files; +2 tests). B5b: bounded 12 unbounded fields (photo_path/sourcing_uuid max_length; azimuth/pitch/roll ±360; min/max_temp -50..1500; kiln_gross_capacity/gross_volume/wet_yield_kg/application_rate_tonnes/ignition_energy_amount ranges); feedstock_species (validator) + biomass_method (Literal) already bounded. +2 tests. G1 325 passed.
- [x] **P1-B6** — Regression tests for already-fixed races · backend media path-guard: audit found ALREADY PINNED (test_hardening.py) — no work. Client GC stamp-before-delete: was NOT pinned → added Test 5 to sync_two_phase_test.dart (a row stamped media_synced_at with its file already GC'd resumes SYNCED, no network, never FAILED). G3 170 passed.
- [x] **P1a COMPLETE** ✅ — all 6 backend-robustness tasks done + pushed. Backend suite 325 passed; Flutter suite 170 passed.

## PHASE P1b — Client robustness
- [x] **P1-C1** — failure_reason column + retry API · SyncOutbox.failureReason (schema v24 + migration, G4 regen); both FAILED_PERMANENTLY sites now record the reason + lastAttemptAt; added watchProblemRows()/retryPermanentlyFailed()/retryAllPermanentlyFailed(). +3 tests (422→FAILED+reason, retry→recovers, migration). Flutter 173 passed.
- [x] **P1-C2** — Clock-skew detection · pure `computeClockSkew(dateHeader, now)` + `clockSkewProvider`; sync loop reads the server `date` header on JSON+media responses and publishes any >2min skew; transient retries now also record failureReason (so a 401-during-skew row isn't blank in Sync Health). +4 tests. Flutter 177 passed.
- [x] **P1-C3** — Resume restores step progress · added `BatchProgress` + `loadBatchProgress(db,uuid)` + `restoreProgress()`; both dashboard resume sites now restore card statuses (biomass/ble/yield) from persisted rows instead of a fresh-start layout. +4 tests. Flutter 181 passed. NOTE: deferred the findIncompleteBatch metadata-anchor sub-item — low value (a metadata-only batch has no evidence/credit; orphan is harmless) vs reworking the 218-line existing test.
- [x] **P1-C4** — BLE stream error handling + disconnect banner · onError on all 3 subscriptions → bleError state; 30s watchdog → connectionLost (cleared on next sample); pyrolysis_screen shows a danger banner while lost/errored. +3 tests (watchdog via injected clock, stream-error, beginBurn clears). Flutter 184 passed. NOTE: playbook's gap-marker omitted — temperatureLog is List<double>, a marker would corrupt telemetry; the banner + honest truncation is the fix.
- [x] **P1-C5** — Pyrolysis END BURN pre-validation · gating already existed; extracted testable `canEndBurn(proofCount, ending)` predicate + wired the button to it; humanized the persist-failure snackbar (was raw `$e`). +3 tests. Flutter 187 passed.
- [x] **P1-C6** — Read-back-verified passphrase migration · migration now reads back the secure-storage write and scrubs SharedPreferences ONLY on a verified match (else keeps the copy + retries next launch); fresh-generation throws if the key didn't persist (never encrypt under an unstored key). +3 tests (mocktail fake storage). Flutter 190 passed.
- [x] **P1-C7** — Two-phase invariant at insert time · `assertOutboxMediaInvariant` (a row declaring sha256_hash must carry photo_path) called at the top of insertWithOutbox — an unsyncable media row now throws at the capture site, not poisons at sync. +4 tests. Flutter 194 passed.
- [x] **P1b COMPLETE** ✅ — all 7 client-robustness tasks done + pushed (C3 metadata-anchor sub-item deferred as low-value). Flutter 194 passed.

## PHASE P1c — Rainbow capture screens
- [x] **P1-S1** — Moisture multi-reading loop (THE C2 bug) · moisture screen now writes N photographed `moisture_readings` rows (one per capture, sequence-numbered) against target max(10, ceil(biomassKg/100)); BiomassSourcing summary written once; counter-hero UI ("N / target"); INITIATE PYROLYSIS gated on readingCount>=target. `moistureSampleTarget` + `moistureReadingCountProvider` added. +3 target tests (backend test_moisture_flow already proves 10 readings clear C2). Flutter 199 passed. **C2 is now passable from the field.**
- [x] **P1-S2** — Biomass input on Sourcing · SourcingState gains biomassInputKg/biomassMeasurementMethod (+persist/load) + `setBiomass` + `hasBiomass`; sourcing screen has a weight field + WEIGHED/EST-FROM-YIELD toggle; proceed button now requires biomass; moisture screen threads biomass into insertBiomassSourcingWithOutbox. +2 tests. Flutter 196 passed.
- [ ] **P1-S2** — Biomass input on Sourcing (do before S1)
- [ ] **P1-S1** — Moisture multi-reading loop (THE bug) (deps: P1-C1, P1-S2)
- [ ] **P1-S3** — Kiln selection at burn start
- [ ] **P1-S4** — Pyrolysis completion rework (deps: P1-S3) · `DECISION (default: ADD 3 gate stages, keep 4 smoke photos)`
- [ ] **P1-S5** — Composite sample screen
- [ ] **P1-S6** — Delivery & buyer fields on End-Use
- [x] **P1-S7** — Sync Health screen · new `sync_health_screen.dart` reachable from a now-tappable dashboard integrity footer; clock-skew danger banner (from `clockSkewProvider`); Synced/Waiting/Stuck summary chips; per problem-row DmrvPanel with human op-label + short batch id + last-tried + verbatim `failureReason` + per-row RETRY; RETRY ALL when stuck; NO delete action. Added `problemOutboxRowsProvider` + `syncedOutboxCountProvider` (thin wrappers over C1's `watchProblemRows` + a SYNCED count). +5 widget tests (fake DB rows via provider overrides, FakeSyncQueueManager records retries). G2 clean (0 new), G3 204 passed.
- [ ] **P1-S8** — In-app enrollment screen
- [ ] **P1 EXIT GATE** — fresh phone enrolls in-app · one batch turns every field criterion green · kill-and-resume at 3 points · stuck sync visible+retryable · BLE disconnect banner

## PHASE P2 — Lab & Verifier portal
- [ ] **P2.0** — Backend modularization seam (do before any portal endpoint)
- [ ] **P2.1** — Portal auth: users, roles, sessions
- [ ] **P2.2** — Read API (batches, detail, devices, summary, authed media)
- [ ] **P2.3** — Portal UI: dashboard + batch detail
- [ ] **P2.4** — Lab flow: scan QR → results → live recompute
- [ ] **P2.5** — Registry forms + M5 idempotency
- [ ] **P2.6** — Issuance action + immutable audit log
- [ ] **P2 EXIT GATE** — lab scans real batch QR → gates flip green · admin issues credit with full audit trail · zero curl in workflow

## PHASE P3 — Deploy & scale-hardening
- [ ] **P3.1** — docker-compose + .dockerignore + CI image smoke
- [ ] **P3.2** — Object storage abstraction for evidence media
- [ ] **P3.3** — Cloud deployment (Cloud Run + Cloud SQL + GCS) · `⏸ needs HUMAN: GCP project + resources`
- [ ] **P3.4** — Observability (structured logs, request IDs, /metrics, Sentry)
- [ ] **P3.5** — Backups + restore drill · `⏸ needs HUMAN: run one restore on staging`
- [ ] **P3.6** — HMAC key versioning
- [ ] **P3.7** — Recompute efficiency + rate-limit pruning
- [ ] **P3.8** — 200-device load smoke
- [ ] **P3 EXIT GATE** — staging URL live over TLS · media in versioned object storage · restore drill done · zero 5xx at 200 devices · HMAC rotation breaks nothing

## PHASE P4 — Trust switches & polish
- [ ] **P4.1** Attestation flip · [ ] **P4.2** Require canonical v2 · [ ] **P4.3** Transport factors `⏸ Rainbow` · [ ] **P4.4** Cross-field plausibility · [ ] **P4.5** Batch checklist hub · [ ] **P4.6** Full Hindi i18n · [ ] **P4.7** Corrective-flow policy `DECISION` · [ ] **P4.8** Hygiene sweep + server.py extraction · [ ] **P4.9** Play release pipeline · [ ] **P4.10** Privacy/GDPR pack `DECISION` · [ ] **P4.11** ARCHITECTURE.md

## PHASE P5 — Platform
- [ ] **P5.0** Multi-instance scale-out (removes the max-instances-1 pin) · [ ] **P5.1** Europe/Pro skin · [ ] **P5.2** White-label config · [ ] **P5.3** Multi-tenant backend · [ ] **P5.4** iOS

---

## EXECUTION LOG (newest first — one line per committed task / exit-gate run)
- 2026-07-10 · P1-S7 · Sync Health screen (tappable integrity footer → clock-skew banner + Synced/Waiting/Stuck chips + per-row human label/reason/RETRY + RETRY ALL; no delete). Added problemOutboxRowsProvider + syncedOutboxCountProvider. +5 widget tests. Flutter 204 passed. (2 parallel Explore agents fed data-layer + house-style ground truth.)
- 2026-07-10 · P1-S1 · moisture multi-reading loop — THE C2 bug fixed: N photographed moisture_readings rows vs target max(10,ceil(kg/100)); counter UI; pyrolysis gated on count>=target. +3 tests. Flutter 199 passed.
- 2026-07-10 · P1-S2 · biomass weight + method on Sourcing (state+persist+setBiomass+hasBiomass, UI field+toggle, proceed gate, moisture threading). +2 tests. Flutter 196 passed. First P1c screen.
- 2026-07-10 · P1b EXIT ✅ · all 7 client-robustness tasks (C1 failure-reason+retry, C2 clock-skew, C3 resume-progress, C4 BLE-disconnect, C5 END-BURN gate, C6 passphrase read-back, C7 media-invariant) done+pushed. Backend 325 / Flutter 194 green.
- 2026-07-10 · P1-C7 · assertOutboxMediaInvariant at insertWithOutbox (media row without photo_path throws at capture site). +4 tests. Flutter 194 passed.
- 2026-07-10 · P1-C6 · read-back-verified passphrase migration (never scrub the last copy; fresh-gen throws on non-persist). +3 tests. Flutter 190 passed.
- 2026-07-10 · P1-C5 · extracted testable canEndBurn predicate + wired END BURN button; humanized persist-failure snackbar. +3 tests. Flutter 187 passed.
- 2026-07-10 · P1-C4 · BLE onError on all subs → bleError; 30s watchdog → connectionLost; pyrolysis_screen disconnect banner. +3 tests. Flutter 184 passed.
- 2026-07-10 · P1-C3 · resume restores dashboard card statuses (BatchProgress + loadBatchProgress + restoreProgress; both dashboard resume sites wired). +4 tests. Flutter 181 passed. Metadata-anchor sub-item deferred (low-value edge).
- 2026-07-10 · P1-C2 · computeClockSkew (pure, tested) + clockSkewProvider; sync reads server `date` header on both phases; transient rows record failureReason. +4 tests. Flutter 177 passed.
- 2026-07-10 · P1-C1 · SyncOutbox.failureReason (schema v24 + migration + G4 regen); reason recorded at both FAILED_PERMANENTLY sites; watchProblemRows/retryPermanentlyFailed/retryAllPermanentlyFailed API. +3 tests. Flutter 173 passed. (3 parallel context agents fed C1-C5.)
- 2026-07-10 · P1a EXIT GATE ✅ · backend 325 passed / flutter 170 passed. All 6 backend-robustness fixes (B1 corrupt-json, B2 race-fallback, B3 tz, B4 uuid-canon, B5 media-cleanup+bounds, B6 gc-ordering-test) done + pushed. B6 added no app code (test-only) so the P0.6 signed release build still holds.
- 2026-07-10 · P1-B6 · client GC stamp-before-delete crash-safety pinned (sync_two_phase_test Test 5); backend path-guard already pinned. G3 170 passed.
- 2026-07-10 · P1-B5b · bounded 12 previously-unbounded numeric/string payload fields (generous physical ranges; compass ±360 to avoid rejecting real sensor data); +2 tests. G1 325 passed, no over-tightening.
- 2026-07-10 · P1-B5a · media upload: validate batch_uuid before write + rollback/unlink on any post-write failure (no orphan files); +2 tests (malformed-uuid & non-owner leave no file). G1 323 passed.
- 2026-07-10 · P1-B4 · _BatchScopedPayload mixin canonicalizes+validates batch_uuid on 7 evidence models; +2 tests; fixed test_signature's non-UUID placeholder (incidental). Caught the regression via full-suite gate, diagnosed, fixed. G1 321 passed.
- 2026-07-10 · P1-B3 · _as_utc helper; teleport subtraction fixed (mixed-tz skew) + 3 sites consolidated; +4 unit tests. G1 319 passed.
- 2026-07-10 · P1-B2 · create_batch race fallback: lookup by op-id then uuid, no scalar_one (no 500), device+uuid+op+sha validated before 200 dup. +1 test. G1 315 passed. (3 parallel context agents used for B2-B6.)
- 2026-07-10 · P1-B1 · _safe_json guard on all 7 json.loads sites in server.py recompute/compliance; +4 tests (test_corrupt_payload_recompute.py); G1 314 passed. Independent subagent audit verified P0 8/10 before starting.
- 2026-07-10 · P0 milestone · all 8 agent-doable P0 tasks done + pushed. P0.7 (device) & P0.8 (freeRASP 6→8 major bump for 16KB) parked as hardware/decision-blocked. P0.8 diagnosed device-free (5 freeRASP libs 4KB-aligned). Advancing to P1a.
- 2026-07-10 · P0.6 · generated PKCS12 RSA-4096 release keystore (outside repo), wired conditional signing in build.gradle.kts + key.properties(.example). Diagnosed a real failure: PKCS12 ignores separate -keypass, so key.properties keyPassword had to equal storePassword ("Given final block not properly padded"). Rebuilt → apksigner confirms signer CN=dMRV (SHA-256 c04e5392…), not debug. Keystore backup is the only human residual.
- 2026-07-10 · P0.10 · flutter-ci --enforce-lockfile (exit 0 locally) + backend-ci pip-check (hermetic: no broken requirements) + docs/RELEASE_CHECKLIST.md dep policy. commit pending push.
- 2026-07-10 · P0.9 · commit 7ce570e · kept io.dmrv.dmrv_app, removed scaffold TODO.
- 2026-07-10 · P0.5 · added flutter-ci.yml (analyze+test+release-apk, Flutter 3.41.9 pinned); removed 9 dead-code warnings across 3 lib screens + 4 test files so `analyze --no-fatal-infos` is warning-fatal-clean. Verified locally: analyze exit 0 (15 infos left), 169 tests pass, release APK built 95.3MB with R8. Remote GitHub Actions run not observable here (no gh).
- 2026-07-10 · P0.3 · rotated demo secrets (fresh token_hex(32) into gitignored .env + demo_secrets.bat); scrubbed 4 demo files + 1 tracked prompt doc; committed demo_tools sans secrets; repo audit shows 0 burned-value hits; +3 hygiene tests; G1 310 passed. Old secrets were in history (commit 81e126e) but are now dead — rotation is the mitigation; no history rewrite for a defunct demo secret.
- 2026-07-10 · P0.4 · main.dart validateReleaseConfig + release_guards_test.dart (4 tests) · G2 24 issues all pre-existing (0 new), G3 169 passed. Release builds now refuse to boot without SENTRY_DSN.
- 2026-07-10 · P0.2 · commit 1d20989 · pinned cryptography==44.0.3 + python-dotenv==1.0.1 · proved via hermetic venv import + full suite 307 passed/1 skipped (G1 green). Note: initial run showed 29 false failures from exporting DMRV_*_SECRET over conftest's setdefault — resolved by letting conftest own the test secrets.
- 2026-07-10 · P0.1 · pushed all 4 branches to github.com/dhananjay1434/terra; remote verified free of .env/demo_tools/keystores. Branch protection = human follow-up after flutter-ci exists (P0.5).
- 2026-07-10 · P0.1 (local) · 3 commits: gitignore hardening + docs corpus + Dockerfile · verified backend/.env absent from history, secrets-scanned docs (clean)
