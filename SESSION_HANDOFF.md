# dMRV — Session Handoff (paste this into a new AI session)

**Written:** 2026-07-08 · **Repo root:** `c:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`
**Branch:** `remediation/phase-by-phase` · **HEAD:** `82a6fe0` · **Git remote:** **NONE (local-only — nothing is pushed)**

This file tells the next session exactly what exists, where, what's done, and what's next. Read it top to bottom before touching anything.

---

## 0. TL;DR of where we are

- A full brutal audit was done → written to **`detailed.md`** (repo root).
- A 6-tier remediation roadmap was written → **`docs/ROADMAP/`** (untracked — see §4).
- **Tier 1 (Rainbow methodology completion) = DONE & committed** (7 commits, `732e2cb`→`e30ee10`).
- **Tier 2 (security) = DONE & committed** except the Android release-build validation which the environment couldn't run (8 commits, `dfcc74d`→`82a6fe0`).
- **Nothing is pushed to a remote** and **`docs/ROADMAP/`, `detailed.md`, this file, and several docs are UNTRACKED** (never `git add`ed). That is the single most urgent thing to fix (Tier 0, task T0.1).

**Current verified test state:**
- Backend: `cd backend && python -m pytest -q` → **307 passed, 1 skipped, 0 failed** (~305s).
- Flutter: `flutter analyze` → **25 issues, 0 errors**; `flutter test` → **153 passed, 2 skipped, 0 failed**.
- Alembic single head: **`f1a2b3c4d5e6`**; client Drift `schemaVersion = 23`.

---

## 1. The map — every roadmap/audit file and what it's for

All under repo root unless noted. **⚠️ Everything in `docs/ROADMAP/` and `detailed.md` is UNTRACKED — commit them (T0.3).**

| File | What it is |
|---|---|
| `detailed.md` | The brutal full-codebase audit (backend, client, Rainbow methodology, hygiene). The "what's wrong" source of truth. |
| `docs/ROADMAP/00_OVERVIEW.md` | Roadmap index + the benchmark ladder (T0→T5) + load-bearing rules. **Start here.** |
| `docs/ROADMAP/01_TIER0_FOUNDATION.md` | T0 "survivable MVP": git remote, CI, requirements.txt, release signing. **NOT STARTED (mostly).** |
| `docs/ROADMAP/02_TIER1_RAINBOW.md` | T1 methodology completion. **DONE (T1.1–T1.4, T1.9, T1.10).** T1.5–T1.8 blocked on Rainbow. |
| `docs/ROADMAP/03_TIER2_SECURITY.md` | T2 security. **DONE (T2.1–T2.8)** minus the manual Android build gate. |
| `docs/ROADMAP/04_TIER3_PRODUCTION.md` | T3 ops (Postgres CI, Docker, S3, read API, observability, backups). **NOT STARTED.** |
| `docs/ROADMAP/05_TIER4_POLISH.md` | T4 polish (module refactor, e2e/golden tests, 3rd locale, analytics). **NOT STARTED.** |
| `docs/ROADMAP/06_TIER5_UI_PLATFORM.md` | T5 UI unification → dual skins → white-label → multi-tenant SaaS. **NOT STARTED.** |
| `docs/ROADMAP/UI_CONSISTENCY_AUDIT.md` | Forensic UI audit (findings U1–U12: dark/light theme split, 61 hardcoded colors, etc.). Feeds T5. |
| `docs/ROADMAP/TASKBOARD.md` | One-line checklist of every task ID (T0.x–T5.x) + external-dependency ledger. |
| `docs/ROADMAP/prompts/T1_EXECUTION_PROMPT.md` | The exact step-by-step that built T1. Already executed. |
| `docs/ROADMAP/prompts/T2_EXECUTION_PROMPT.md` | The exact step-by-step that built T2. Already executed. |
| `REMEDIATION_LOG.md` | Per-phase journal (tracked). T1 entry + T2 entry are the last two sections. |

**To continue building:** the next tier to execute is **T3** (production ops) or **T5 Stage A** (UI unification). There is **no T3/T4/T5 execution prompt yet** — the tier `.md` files have the task detail; a new session can either execute directly from those or first write a `docs/ROADMAP/prompts/T3_EXECUTION_PROMPT.md` the same way T1/T2 were written (verify code anchors → dense per-task prompt).

---

## 2. What we did THIS work-stream (T1 + T2), commit by commit

Branch `remediation/phase-by-phase`, on top of pre-existing `7ed32b7` (Rainbow C10). Newest last:

```
732e2cb fix(config): dotenv opt-out + single _require_secret choke point (P0.a)
277a437 feat(dmrv): batch->project/scale linkage — server schema+API (Rainbow T1.1a)
5efce6e feat(dmrv): client capture+sync of project/scale linkage, schema v23 (Rainbow T1.1c)
f69158a feat(dmrv): enforce C8 scale-calibration expiry via batch scale linkage (Rainbow T1.2)
f75632b feat(dmrv): enforce C9 annual-methane + un-bypass closed-kiln PAH gates (Rainbow T1.3/T1.4)
032e943 feat(dmrv): compliance-report enforcement provenance + lab moisture min-3 lock-in (T1.9/T1.10)
1dbea19 chore(tests): drop module asyncio mark from sync transport tests
e30ee10 docs(remediation): journal Rainbow T1 methodology completion
dfcc74d feat(security): per-route rate limiting (register/admin/media) via env-live middleware (T2.2)
b1e66f6 feat(security): DB-probing health check + secret entropy floor (T2.6)
686f4a2 feat(security): name GPS-anchor threshold + surface integrity signals in audit (T2.7)
5717da7 feat(security): opt-in v2 signed-timestamp canonical for replay protection (T2.3)
4fba157 feat(security): attestation verifier interface + verdict wiring, env-live enforce switch (T2.1)
0ee2d73 docs(security): secret-rotation + enforcement-switch + cert-pinning deploy notes (T2.8)
14e84ae build(android): FLAG_SECURE on release + R8/ProGuard obfuscation config (T2.4/T2.5)
82a6fe0 docs(remediation): journal Rainbow T2 security tier
```

### T1 — Rainbow methodology completion (what changed)
The audit found 3 compliance-catalog reasons that could NEVER fire (dead gates). All now wired:
- **`batch.project_id` / `batch.scale_id`** added: `backend/models.py` (Batch class), migration **`backend/alembic/versions/f1a2b3c4d5e6_batches_project_linkage.py`** (down_revision `e1f2a3b4c5d6`), `BatchPayload` in `backend/server.py`, persisted in `create_batch`.
- **Client v23**: `lib/data/local/tables.dart` (`BiomassSourcing.projectId/scaleId`), `lib/data/local/app_database.dart` (`schemaVersion => 23` + `if (from < 23)` block + outbox writer), `lib/ui/screens/moisture_verification_screen.dart` stamps `DMRV_PROJECT_ID` dart-define. Codegen file `lib/data/local/app_database.g.dart` regenerated.
- **Gates wired in `backend/server.py` `recompute_batch_credit`**: `scale_calibration_expired` (T1.2), `missing_annual_methane` (T1.3, `(project_id, harvest-year)` verification, ≥3 runs), `missing_pah` (T1.4 — **removed a hardcoded `enforced=False` bypass**). All INERT for legacy batches with no linkage.
- **`/api/v1/batches/{uuid}/compliance`** checklist gained an `enforcement` field: `enforced` | `inert_no_linkage` | `awaiting_methodology` (T1.10). T1.9 (lab moisture ≥3) was already enforced by `min_length=3` — added lock-in tests.
- New tests: `backend/tests/test_batch_project_linkage.py`, `test_annual_gates_t13_t14.py`, additions to `test_project_registry_c8.py` / `test_compliance_gate_c10.py` / `test_lab_results_c7.py`, and `test/migration_v23_project_linkage_test.dart`.

### T2 — Security (what changed)
- **T2.2 rate limiting**: `_rate_limit` `@app.middleware("http")` in `backend/server.py` (fixed-window, per-route buckets register/admin/media/default, 429+Retry-After). Config **read live from `os.environ`** (`DMRV_RATELIMIT_*`). Test: `backend/tests/test_rate_limit.py`. Disabled in tests via `DMRV_RATELIMIT_ENABLED=0` in `backend/tests/conftest.py`.
- **T2.6 health + secret floor**: `/api/health` runs `SELECT 1` → 503 when DB down; `_require_secret` rejects secrets <32 chars/<10 distinct unless `DMRV_ALLOW_WEAK_SECRETS=1` (set in conftest + `.github/workflows/backend-ci.yml`). Test: `backend/tests/test_t26_health_secret.py`. Also retargeted `backend/tests/test_p1_25_lifespan.py` onto the `client` fixture.
- **T2.7 EXIF honesty**: `GPS_ANCHOR_MISMATCH_KM` constant + `lca_audit_json.integrity_signals`. Test: `backend/tests/test_t27_integrity_signals.py`.
- **T2.3 replay protection**: opt-in **v2 signed-timestamp canonical**. Server `verify_signature` in `backend/server.py` accepts `X-Canonical-Version: 2` + `X-Signed-At`, rejects stale (skew window, default 300s). Client `CryptoSigner.signRequestV2` in `lib/services/crypto_signer.dart`; sync loop sends the headers (`lib/services/sync_queue_manager.dart`). Tests: `backend/tests/test_replay_v2.py`, `test/services/crypto_signer_test.dart`.
- **T2.1 attestation**: new module **`backend/attestation.py`** (verifier interface, verdict dataclass, Play Integrity/DeviceCheck stubs); wired into `recompute_batch_credit`. Test: `backend/tests/test_attestation.py`.
- **T2.4/T2.5 Android**: `android/app/src/main/kotlin/io/dmrv/dmrv_app/MainActivity.kt` (FLAG_SECURE on release), `android/app/build.gradle.kts` (minify+shrink+proguardFiles+buildConfig), new `android/app/proguard-rules.pro`.
- **T2.8 docs**: `DEPLOYMENT.md` (secret rotation, enforcement switches, cert pinning) + `TODO(deploy)` in `_require_secret`.

**New dependency (installed locally, NOT yet in requirements.txt):** none actually — T2.2 used a middleware, not SlowAPI, so no new dep. (`slowapi` was pip-installed during exploration but is unused; ignore it.)

---

## 3. Environment / config switches introduced (all default to SAFE/OFF)

Read live from `os.environ` (so they survive `importlib.reload` and are runtime-tunable):
- `DMRV_RATELIMIT_ENABLED` (default `1` in prod; conftest sets `0`), `DMRV_RATELIMIT_REGISTER/ADMIN/MEDIA/DEFAULT`, `DMRV_RATELIMIT_WINDOW_SECONDS`.
- `DMRV_ALLOW_WEAK_SECRETS` (default unset → floor enforced; set `1` ONLY in test/CI).
- `DMRV_CANONICAL_SKEW_SECONDS` (default 300), `DMRV_REQUIRE_CANONICAL_V2` (default `0` → v1 still accepted).
- `DMRV_ATTESTATION_ENFORCED` (default `0` → attestation inert).

**Two switches to FLIP later (do NOT flip until the precondition is met):**
1. `DMRV_REQUIRE_CANONICAL_V2=1` — only after the field fleet ships a v2-signing app build.
2. `DMRV_ATTESTATION_ENFORCED=1` — only after `backend/attestation.py` gets a REAL Play Integrity/DeviceCheck verifier + Google/Apple credentials.

---

## 4. What is REMAINING (prioritized)

### 🔴 P0 — do first (Tier 0, ~1 day, `docs/ROADMAP/01_TIER0_FOUNDATION.md`)
1. **T0.1 Create a git remote and push.** There is NO remote; 17 commits of work live only on this laptop. Highest priority in the whole project.
2. **T0.3 Commit the untracked docs**: `docs/ROADMAP/` (entire folder), `detailed.md`, `SESSION_HANDOFF.md` (this file), `docs/REMEDIATION_PLAN_NONUI.md`, the UX_*.md and business docs. Also delete cruft: `android/hs_err_pid12464.log` (JVM crash dump from the failed build), `android/.kotlin/`, `New folder.zip`.
4. **T0.4 Commit `.github/workflows/backend-ci.yml`** (it's untracked → CI has never run) and **T0.5 add `cryptography` + `python-dotenv` to `backend/requirements.txt`** (imported but undeclared — clean-host deploy risk).
5. **T0.6 Real Android release keystore** (currently debug-signed — ship blocker) and **T0.7 Flutter CI lane**.

### 🟠 T2 leftover (manual/cross-team)
- **Validate the Android release build on CI/a real device.** We could NOT build a release APK here (gradle daemon crashed, then 10-min timeout — environment resource limits, no R8 error). Run `flutter build apk --release --obfuscate --split-debug-info=build/symbols`, confirm it builds, `apksigner` shows a non-debug cert (needs T0.6), `jadx` shows obfuscation, screenshots blocked. Expect one round of missing ProGuard `-keep` rules.
- Implement the real attestation verifier in `backend/attestation.py` (needs Play Console / Apple Developer creds), then flip `DMRV_ATTESTATION_ENFORCED`.
- Ship a v2-signing app build to the fleet, then flip `DMRV_REQUIRE_CANONICAL_V2`.

### 🟡 T1 leftover (blocked on Rainbow / methodology sign-off — see `02_TIER1_RAINBOW.md` T1.5–T1.8)
Each stays behind a named, tested, inert flag:
- **T1.5** transport fuel emission factors are still `TODO(cite)` placeholders in `backend/emission_factors.py`; `TRANSPORT_EVENTS_ENFORCED=False`. Needs Rainbow annex numbers → cite → flip → wire into LCA.
- **T1.6** C9 methane rate → CH4 penalty (`lca_engine.py` step 7). **T1.7** C9 conversion factor → C1 yield. **T1.8** 1000-yr inertinite pathway election (needs a project-settings table).

### 🟢 Not started (whole tiers)
- **T3** production ops (`04_TIER3_PRODUCTION.md`): Postgres CI lane, Dockerfile/compose, S3/object storage for media, read API + pagination, structured logs/metrics/health, backups, load test.
- **T4** polish (`05_TIER4_POLISH.md`): split `server.py` (2000+ lines) into modules, e2e + golden + widget tests, Marathi locale, analytics, ProGuard hardening.
- **T5** UI & platform (`06_TIER5_UI_PLATFORM.md` + `UI_CONSISTENCY_AUDIT.md`): **the app has TWO coexisting themes** (AppTheme light + FarmerTheme dark) — the batch flow flips dark/light 5 times; 61 hardcoded `Color(0x…)` literals; only 2/9 screens localized. Stage A unifies into one token system → Stage B dual skins (Field/India + Pro/Global-EU) → Stage C white-label → Stage D multi-tenant SaaS backend.

---

## 5. Load-bearing rules (carried from the Rainbow protocol — violating these breaks the shipped field app)

1. **Additive & backward-compatible only.** New nullable columns / optional Pydantic fields / new endpoints. Never rename/drop/require-existing (`BatchPayload` is `extra="forbid"`; deployed devices sign a FROZEN canonical).
2. **Compliance ONLY via the provisional model** — never reject an upload for a methodology reason. Mechanism: pure `derive_*` in `backend/corroboration.py` → reason string → `assemble(extra_reasons=[...])` → `recompute_batch_credit`.
3. **Config that any test reloads must be read LIVE from `os.environ`**, not module constants (learned the hard way: `test_p1_24_cors.py` does `importlib.reload(server)`, which desyncs module-level constants from monkeypatch).
4. **One phase = one commit = one green gate = one `REMEDIATION_LOG.md` entry.**
5. **Alembic**: new migration `down_revision` = current head (`f1a2b3c4d5e6`); must have working `downgrade()`. **Client schema**: bump `AppDatabase.schemaVersion` by exactly 1, `addColumn`/`createTable` only, then `dart run build_runner build --delete-conflicting-outputs`. Schema-shape tests assert `greaterThanOrEqualTo(N)`, never `== N`.
6. **Test gates**: backend `cd backend && python -m pytest -q` (307/1/0); client `flutter analyze` (25 issues/0 errors — add none) + `flutter test` (153/2). Backend suite ~90–120s; use background runs. Commit messages end with `Co-Authored-By: Claude <noreply@anthropic.com>`.

---

## 6. Key file locations (quick reference)

- Backend app: `backend/server.py` (~2100 lines — god file, T4 splits it), `backend/corroboration.py` (pure derivers), `backend/lca_engine.py`, `backend/models.py`, `backend/emission_factors.py`, `backend/attestation.py` (new), `backend/db.py`.
- Backend migrations: `backend/alembic/versions/` (head `f1a2b3c4d5e6`). Tests: `backend/tests/` (~46 files). Test config: `backend/tests/conftest.py`.
- Client: `lib/data/local/{tables,app_database}.dart` (Drift, schema v23), `lib/services/{crypto_signer,sync_queue_manager,device_integrity_service}.dart`, `lib/ui/screens/` + `lib/ui/design/{app_theme,farmer_theme,premium_field_components}.dart`. Tests: `test/`.
- Android: `android/app/build.gradle.kts`, `android/app/proguard-rules.pro`, `android/app/src/main/kotlin/io/dmrv/dmrv_app/MainActivity.kt`.
- CI: `.github/workflows/backend-ci.yml` (untracked!), `.github/workflows/codegen.yml` (tracked).
- Methodology source of truth: `docs/dMRV Criteria Distributed Biochar.md`. Handoff spec: `terracipher_reports/RAINBOW_COMPLIANCE_PROMPT.md`.

---

## 7. One-paragraph prompt to start the next session

> "Continue the dMRV remediation on branch `remediation/phase-by-phase` (HEAD `82a6fe0`) at repo root `c:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`. Read `SESSION_HANDOFF.md` first, then `docs/ROADMAP/00_OVERVIEW.md` and `docs/ROADMAP/TASKBOARD.md`. Tiers T1 (Rainbow) and T2 (security) are DONE & committed; backend `pytest` is 307/1/0 and `flutter test` is 153/2. I want to do **[T0 foundation — push to a remote + CI + release signing]** OR **[T3 production ops]** OR **[T5 Stage A UI unification]** next. Follow the same discipline used for T1/T2: verify code anchors, one phase = one commit = one green gate = one REMEDIATION_LOG entry, additive-only, config read live from os.environ. If a tier has no execution prompt yet, write one under `docs/ROADMAP/prompts/` first."
