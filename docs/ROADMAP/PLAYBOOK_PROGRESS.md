# PLAYBOOK PROGRESS — the live execution tracker

**This file is the single source of truth for "where are we."** One checkbox per task, in dependency order (Section 9 of `AGENT_EXECUTION_PLAYBOOK.md`). The rule (playbook §0.8): work the first UNCHECKED task whose dependencies are all checked; tick its box in the SAME commit that lands the task; never start a new phase until the prior phase's EXIT GATE is fully green.

**Legend:** `[ ]` not started · `[~]` in progress · `[x]` done (committed) · `⏸` blocked (waiting on a human/decision — note what it needs)

**Started:** 2026-07-10
**Current phase:** P0 — Protect & release-able
**Next actionable task:** P0.5 (Flutter CI lane) — agent-doable. Then P0.10. Human-blocked: P0.3 (fresh secrets), P0.6–P0.8 (keystore + device), P0.1 follow-up (branch protection).

---

## PHASE P0 — Protect & release-able
- [x] **P0.1** — Push repo to remote · pushed all 4 branches to github.com/dhananjay1434/terra (commits 9686a11, 2ea6fba, 356bf24); remote verified clean of secrets/demo_tools · `⏸ FOLLOW-UP (HUMAN, after P0.5): enable branch protection on main requiring backend-ci + flutter-ci`
- [x] **P0.2** — Pin `cryptography` + `python-dotenv` in requirements.txt · commit 1d20989 · hermetic venv import OK, suite 307/1 green
- [ ] **P0.3** — Scrub secrets from demo_tools, then commit it · `⏸ needs HUMAN: rotate to fresh secret values`
- [x] **P0.4** — Sentry release-build guard · extracted `validateReleaseConfig` in main.dart (throws in release when DSN empty) + test/release_guards_test.dart (4 tests) · G2 zero new issues, G3 169 passed
- [ ] **P0.5** — Flutter CI lane
- [ ] **P0.6** — Real release keystore + signing config · `⏸ needs HUMAN: generate + back up keystore`
- [ ] **P0.7** — Validate release build on-device; close ProGuard gaps · `⏸ needs HUMAN: physical Android device`
- [ ] **P0.8** — 16 KB page-size compliance · `⏸ needs HUMAN: re-run on-device checklist`
- [ ] **P0.9** — Finalize applicationId · `DECISION (default: keep io.dmrv.dmrv_app)`
- [ ] **P0.10** — Dependency policy: lock is law
- [ ] **P0 EXIT GATE** — remote+CI green · no secret in repo · signed release APK passes full on-device checklist · fresh-venv `import server` works

## PHASE P1a — Backend robustness
- [ ] **P1-B1** — Guard every json.loads in recompute/compliance
- [ ] **P1-B2** — Harden create_batch race fallback
- [ ] **P1-B3** — Timezone-aware UTC normalization
- [ ] **P1-B4** — Canonical UUID normalization at write
- [ ] **P1-B5** — Media temp-file cleanup + payload validator bounds
- [ ] **P1-B6** — Regression tests for already-fixed races

## PHASE P1b — Client robustness
- [ ] **P1-C1** — failure_reason column + retry API
- [ ] **P1-C2** — Clock-skew detection (deps: P1-C1)
- [ ] **P1-C3** — Resume covers every partial-batch state
- [ ] **P1-C4** — BLE stream error handling + disconnect banner
- [ ] **P1-C5** — Pyrolysis END BURN pre-validation
- [ ] **P1-C6** — Read-back-verified passphrase migration
- [ ] **P1-C7** — Two-phase invariant at insert time

## PHASE P1c — Rainbow capture screens
- [ ] **P1-S2** — Biomass input on Sourcing (do before S1)
- [ ] **P1-S1** — Moisture multi-reading loop (THE bug) (deps: P1-C1, P1-S2)
- [ ] **P1-S3** — Kiln selection at burn start
- [ ] **P1-S4** — Pyrolysis completion rework (deps: P1-S3) · `DECISION (default: ADD 3 gate stages, keep 4 smoke photos)`
- [ ] **P1-S5** — Composite sample screen
- [ ] **P1-S6** — Delivery & buyer fields on End-Use
- [ ] **P1-S7** — Sync Health screen (deps: P1-C1, P1-C2)
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
- 2026-07-10 · P0.4 · main.dart validateReleaseConfig + release_guards_test.dart (4 tests) · G2 24 issues all pre-existing (0 new), G3 169 passed. Release builds now refuse to boot without SENTRY_DSN.
- 2026-07-10 · P0.2 · commit 1d20989 · pinned cryptography==44.0.3 + python-dotenv==1.0.1 · proved via hermetic venv import + full suite 307 passed/1 skipped (G1 green). Note: initial run showed 29 false failures from exporting DMRV_*_SECRET over conftest's setdefault — resolved by letting conftest own the test secrets.
- 2026-07-10 · P0.1 · pushed all 4 branches to github.com/dhananjay1434/terra; remote verified free of .env/demo_tools/keystores. Branch protection = human follow-up after flutter-ci exists (P0.5).
- 2026-07-10 · P0.1 (local) · 3 commits: gitignore hardening + docs corpus + Dockerfile · verified backend/.env absent from history, secrets-scanned docs (clean)
