# SESSION HANDOFF — dMRV production hardening

**Purpose:** paste this (or point the next AI session at it) and it will know exactly
where we are, what's done, what's next, and how to work. Last updated **2026-07-10**.

> Supersedes the 2026-07-08 handoff (old `remediation/phase-by-phase` T1/T2 work).
> That work is already merged into history; this session continued from `fc5d65b`.

---

## 0. RESUME IN 30 SECONDS

- **Repo:** `flutter_dmrv/` · **branch:** `feature/t5-india` · **remote:** `origin` → `github.com/dhananjay1434/terra` (all work pushed).
- **HEAD:** `25d187d` (P1-S1). Everything below is committed **and pushed**.
- **Green state:** backend suite **325 passed / 1 skipped**; Flutter suite **199 passed / ~2 skipped**.
- **Three authoritative docs (read in this order):**
  1. `docs/ROADMAP/PLAYBOOK_PROGRESS.md` — **LIVE task tracker** (checkbox + one-line status + commit per task, newest-first execution log). Source of truth for "what's done / what's next."
  2. `docs/ROADMAP/AGENT_EXECUTION_PLAYBOOK.md` — full task specs (P0–P5), global rules (§0), the run loop (§0.8), the anti-hallucination protocol (§0.7).
  3. This file — orientation + environment gotchas.
- **To resume:** open PLAYBOOK_PROGRESS.md → find the first `[ ]` task whose deps are `[x]` → that's next. Currently **P1-S7 (Sync Health screen)**.
- **How to work:** one task = one commit = all gates green. Verify code (§0.7) → change → write tests → run gates → commit + tick the tracker in the same commit → push. Details in §4.

---

## 1. WHAT'S DONE (this session — 17 commits on top of `fc5d65b`)

### Phase P0 — Protect & release-able (8/10 done; 2 hardware/decision-parked)
| Task | What | Commit |
|---|---|---|
| P0.1 | Repo pushed to GitHub; `.gitignore` hardened (keystores/logs/secrets) | `9686a11` `2ea6fba` `356bf24` |
| P0.2 | Pinned `cryptography`+`python-dotenv` (fresh-install import crash) | `1d20989` |
| P0.3 | Rotated + scrubbed the burned demo secrets everywhere | `182b8c3` |
| P0.4 | Release refuses to boot without `SENTRY_DSN` (`validateReleaseConfig`) | `f46c6e9` |
| P0.5 | **Flutter CI lane** (analyze+test+release-apk); cleared 9 legacy warnings | `1df6058` |
| P0.6 | **Real release keystore + signing** (PKCS12; verified `CN=dMRV` via apksigner) | `b9fd2e9` |
| P0.9 | Finalized applicationId `io.dmrv.dmrv_app` | `7ce570e` |
| P0.10 | Lockfile enforcement (`--enforce-lockfile` + `pip check`) | `a523ea8` |
| — | P0 milestone tracker + `docs/RELEASE_CHECKLIST.md` | `51a3492` |

**P0 PARKED (blocked, NOT done — external only):**
- **P0.7** on-device release validation — needs a **physical Android device**.
- **P0.8** 16 KB page-size — needs a **freeRASP 6.12→8.0 MAJOR bump** (API-breaking security SDK; deferred to P4.1). Diagnosed device-free: only 5 freeRASP `.so` are 4KB-aligned; Flutter/SQLCipher/Sentry libs are fine.
- **Keystore backup** — the `.jks` is at `C:\Users\bit\dmrv-keystore\dmrv-release.jks` on ONE machine; back it up off-machine or the Play identity is lost forever.
- **Branch protection** on `main` — GitHub UI toggle (human).
- **Remote CI green** — UNVERIFIED (no `gh` CLI here). Workflows are valid + locally-proven; confirm the GitHub Actions tab is green.

### Phase P1a — Backend robustness (COMPLETE, B1–B6)
`1fe9f57` corrupt-JSON guards (`_safe_json`) · `c064539` create_batch race fallback (no 500, device-verified) · `898bb1f` timezone UTC normalization (`_as_utc`) · `82097d3` batch_uuid canonicalization (`_BatchScopedPayload`) · `cf2cb44`+`5f13bca` media orphan-cleanup + payload bounds · `0141976` GC-ordering regression test.

### Phase P1b — Client robustness (COMPLETE, C1–C7)
`295859f` failure_reason column + retry API (Drift **schema v24** + migration) · `f6c27a7` clock-skew detection (`computeClockSkew`/`clockSkewProvider`) · `ea151f1` resume restores dashboard card statuses (`loadBatchProgress`/`restoreProgress`) · `0ca9705` BLE disconnect banner + 30s watchdog · `854b4ee` END-BURN testable gate (`canEndBurn`) + humanized errors · `9414082` read-back-verified passphrase migration · `5ca9133` media invariant at insert (`assertOutboxMediaInvariant`).

### Phase P1c — Rainbow capture screens (IN PROGRESS — 2 of 8)
- `6577e39` **S2** biomass input on Sourcing (weight + WEIGHED/EST-FROM-YIELD; gates proceed; feeds C2 target).
- `25d187d` **S1** moisture multi-reading loop — **THE compliance bug**: writes N photographed `moisture_readings` rows vs `max(10, ceil(biomassKg/100))`; counter-hero UI; pyrolysis gated on target. **C2 is now passable from the field.**

---

## 2. WHAT'S NEXT (in order)

### P1c remaining screens (each = a real screen + widget tests; mostly UI wiring over EXISTING writers/endpoints)
1. **P1-S7 — Sync Health screen** ← NEXT. Data layer DONE (C1 `watchProblemRows`/`retryPermanentlyFailed`/`retryAllPermanentlyFailed`; C2 `clockSkewProvider`). Build: entered from a tappable integrity footer; clock-skew banner; Synced/Waiting/Stuck counts; per-row human label + `failureReason` + RETRY; RETRY ALL; NO delete action.
2. **P1-S6** — Delivery + buyer on End-Use (`EndUseApplication` columns + server `create_application` exist; UI only).
3. **P1-S5** — Composite sample screen (writer `insertCompositePileSampleWithOutbox` + endpoint exist; gate = ≥1 photographed sample; add batch-QR card → pin `qr_flutter`).
4. **P1-S3** — Kiln selection at burn start (new `Kilns` client table → **Drift migration v25** + G4; removes the 200L/WATER_QUENCH hardcodes at `pyrolysis_screen.dart:63` + `yield_scale_screen.dart:71-72`; telemetry already has kiln_id/kiln_type params).
5. **P1-S4** — Pyrolysis completion rework (DECISION default: ADD flame_curtain/quenching/flame_height captures + keep the 4 smoke photos; gate keys `smoke_evidence` stages `{flame_curtain,quenching,flame_height}` + `flame_height_m<0.5` for kiln_type `"open"`; update the C5 END-BURN count).
6. **P1-S8** — In-app enrollment (replaces compile-time `ENROLLMENT_TOKEN`; refactor `CryptoSigner.registerDevice` to take params + keep dart-define fallback; base-URL resolver secure-storage→dart-define).

**P1c EXIT GATE:** fresh phone enrolls in-app + captures a batch where every field criterion goes green; kill/resume at 3 points; stuck sync visible+retryable; BLE-disconnect banner.

### Then P2 (portal), P3 (deploy), P4 (trust/privacy/release pipeline), P5 (platform) — see the playbook.

### Deferred sub-item to remember
- **P1-C3b** — re-anchor `findIncompleteBatch` on `system_metadata` (metadata-only batch resume). Low value (no evidence on such a batch); would require reworking the 218-line `find_incomplete_batch_test`.

---

## 3. ENVIRONMENT GOTCHAS (learned the hard way)

- **Backend tests:** `cd backend && DMRV_DISABLE_DOTENV=1 python -m pytest -q`. **DO NOT export `DMRV_HMAC_SECRET`/`DMRV_ADMIN_SECRET`** — `tests/conftest.py` sets them via `setdefault` (`test-secret`/`test-admin-secret`); exporting your own fails every auth test (a false 29-failure scare happened once). Baseline **325 passed, 1 skipped**.
- **Flutter tests:** `flutter test` (**199 passed, ~2 skipped**). `flutter analyze` baseline ≈15 legacy info-level issues + a couple pre-existing deprecations (`isInDebugMode`, `issueCustomQuery`); **add ZERO new issues**. CI runs `flutter analyze --no-fatal-infos` (warnings fatal) so keep the tree warning-clean.
- **Drift schema change:** edit `tables.dart` → bump `schemaVersion` in `app_database.dart` + add additive `if (from < N)` step → `dart run build_runner build --delete-conflicting-outputs` (G4) → **commit the regenerated `app_database.g.dart`** (codegen.yml checks it). Current schemaVersion = **24**.
- **`gh` CLI NOT installed** + private repo → cannot verify remote Actions; prove CI locally and say the remote run is unverified.
- **Keystore:** `C:\Users\bit\dmrv-keystore\dmrv-release.jks`; passwords in gitignored `android/key.properties`. **PKCS12 gotcha:** keytool defaults to PKCS12 which ignores a separate `-keypass` → `keyPassword` MUST equal `storePassword`.
- **Secrets:** `backend/.env` + `demo_tools/demo_secrets.bat` are gitignored (real values only there). Old demo secrets are rotated/dead. Never commit a secret.
- **Line endings:** "LF will be replaced by CRLF" warnings on every commit are harmless (Windows).
- **Java:** Flutter uses Android Studio JBR (JDK 21) at `C:\Program Files\Android\Android Studio\jbr`. Running `./gradlew` directly may grab JDK 23 (Oracle) which crashes compiling CameraX — a red herring; always build via `flutter build`.
- **apksigner:** `C:\Users\bit\AppData\Local\Android\Sdk\build-tools\36.0.0\apksigner.bat`.
- Backend test runs ~100–200s; use background runs / long timeouts.

---

## 4. HOW TO WORK (the disciplined loop — non-negotiable)

Per playbook §0.7 (anti-hallucination) + §0.8 (run loop):
1. **Re-read every file a task cites BEFORE editing** — line numbers drift; locate by quoted content. Never invent a field/enum/endpoint/JSON key — copy from source of truth (`server.py` pydantic models, `backend/corroboration.py` gates, `lib/data/local/tables.dart`, `sync_queue_manager.dart` `kEndpointByTable`). **Grep for an existing writer/screen/test before creating one** — this codebase is FURTHER ALONG than plans assume.
2. Implement the smallest reviewable change.
3. Write tests. Prefer extracting a **pure function** and testing that (pattern used repeatedly: `validateReleaseConfig`, `_safe_json`, `_as_utc`, `computeClockSkew`, `canEndBurn`, `moistureSampleTarget`, `assertOutboxMediaInvariant`) — deterministic, no fragile widget harness.
4. Run **all** gates (G1 backend pytest / G2 flutter analyze / G3 flutter test / G4 drift codegen if schema touched / G5 alembic if models touched). Never commit red. Never weaken an existing test — fix the root cause (e.g. P1-B4 broke a test using a non-UUID placeholder → gave it a valid UUID, didn't loosen the validator).
5. Commit `<type>(<scope>): <what> (<TASK-ID>)`, co-author `Claude Fable 5`, tick the tracker checkbox in the SAME commit, push, report a 3-liner.
6. **Hard fences:** additive-only API/schema; never touch the Ed25519 signing scheme; compliance only via the provisional/reasons model (never reject, never auto-issue); 401/403 stay transient (16C); `demo_tools/` never ships; never hand-edit generated `*.g.dart` or existing alembic migrations.
7. **Use parallel Explore agents** for context-gathering + verification (fed every P1 batch this session); keep edits/gates/commits serial on the branch.

---

## 5. REALITY-CORRECTIONS FROM THIS SESSION (don't re-discover these)

- The data layer for moisture/composite/transport (Drift tables + `*WithOutbox` writers + `kEndpointByTable` routing + server endpoints + models) **already existed** — the P1c screens are UI wiring, not full-stack.
- Two-phase sync = **ONE outbox row** (photo rides the payload's `photo_path`/`sha256_hash`), not two rows.
- The END-BURN 4-photo gate, the media path-traversal guard, and the GC stamp-before-delete were **already implemented** (some just unpinned by tests).
- Most pydantic payload fields were **already bounded**; P1-B5b touched only ~12 genuinely-unbounded fields.
- Backend already has `/api/v1/moisture|composite-sample|transport` + `create_application` (delivery/buyer), so S5/S6 are UI-only.

---

## 6. ONE-PARAGRAPH PROMPT TO START THE NEXT SESSION

> "Continue dMRV production hardening on branch `feature/t5-india` (HEAD `25d187d`) at repo root `c:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`. Read `SESSION_HANDOFF.md`, then `docs/ROADMAP/PLAYBOOK_PROGRESS.md` (live tracker) and `docs/ROADMAP/AGENT_EXECUTION_PLAYBOOK.md` (task specs + §0 rules). P0 (bar hardware/keystore-backup), P1a, and P1b are done and pushed; P1c is underway (S1+S2 done — the moisture C2 bug is fixed). Backend pytest = 325/1, flutter test = 199/~2, all green. Next task is **P1-S7 (Sync Health screen)** — its C1/C2 data layer already exists. Follow the loop: verify code before editing (never invent names, grep for existing impls first), one task = one commit = all gates green, additive-only, tick the tracker in the same commit, push. Use parallel Explore agents to gather exact ground truth before each screen."
