# dMRV System — Brutal Production-Readiness Audit

**Date:** 2026-07-07
**Branch audited:** `remediation/phase-by-phase` (14 commits ahead of `main`, plus uncommitted work)
**Method:** Full read of backend (all 6 modules, 5,403 lines Python), Flutter client (45 Dart files), all Rainbow/methodology docs, REMEDIATION_LOG, FINDINGS_BACKLOG, CI config, git state — plus fresh runs of all three quality gates. Every claim below was verified against code, not taken from the project's own logs.

**Verified quality-gate baselines (run during this audit):**

| Gate | Result |
|---|---|
| `pytest` (backend) | **262 passed, 1 skipped, 0 failed** (5m50s) |
| `flutter test` | **151 passed, 2 skipped, 0 failed** |
| `flutter analyze` | **25 issues, 0 errors** (4 unused imports in production screens, deprecations, rest in tests) |

---

## 0. Executive Verdict

**This is NOT production-ready. It is a genuinely strong, unusually well-engineered pilot/staging system** — top-quartile for a project at this stage — but it has **hard blockers in four categories**: methodology enforcement (~62% of Rainbow criteria actually gate issuance), security (attestation unverified, no rate limiting, replayable signatures, debug-key-signed Android releases), operations (no remote git repo, CI has never executed, local-disk file storage, no observability), and dependency packaging (two undeclared runtime deps that break a clean deploy).

The most alarming single finding is not in the code at all: **`git remote -v` returns nothing.** The entire codebase — 15 commits of security remediation and compliance work — exists only on one laptop, inside a folder literally named `Downloads/flutter_dmrv_full (1)`. The CI workflow file exists but is **untracked**, meaning CI has never run once. All the "green gates" in the remediation log were run by hand on one machine.

**Honest maturity score: 6.5/10 overall.** Architecture and test discipline are 8–9/10. Methodology completeness is ~6/10 (real, but with dormant gates). Operational readiness is 2/10. Release engineering is 3/10.

---

## 1. What Has Been Built (and What Is Genuinely Good)

### 1.1 System shape

- **Backend:** FastAPI (async) + SQLAlchemy 2.0 + Alembic, 21 endpoints — 15 device-authenticated (Ed25519 request signatures), 6 admin-authenticated (`X-Admin-Secret` with `hmac.compare_digest`). `backend/server.py` (2,073 lines), `corroboration.py`, `lca_engine.py`, `models.py`, `emission_factors.py`, `db.py`.
- **Flutter client:** Offline-first field app (rural India), Drift + **SQLCipher** encrypted DB at schema v22, Riverpod state, BLE thermocouple + BLE scale integration, secure camera capture with EXIF GPS injection and SHA-256 binding, English + Hindi l10n, Sentry crash reporting with GPS-redacting breadcrumb filter.
- **Compliance layer:** Rainbow BiCRS (Riverse) distributed-biochar criteria C0–C10 built as evidence channels + a unified provisional gate (`corroboration.assemble()` → `provisional_reasons` → `GET /api/v1/batches/{uuid}/compliance` admin report, server.py:2033–2073).

### 1.2 Things that are genuinely done well (no sarcasm — these are strong)

1. **Server-side corroboration architecture.** Credit-bearing values are *never* client-asserted. Telemetry, yield, application, moisture, composite samples, and transport arrive as separate signed evidence streams; `recompute_batch_credit()` (server.py:718–973) derives the credit from them. This is the correct trust model for MRV and most projects get it wrong.
2. **Transactional outbox on the client.** Every domain write atomically creates a `SyncOutbox` row (app_database.dart:244–302); two-phase commit (JSON before media; media sync-stamp persisted *before* file deletion, sync_queue_manager.dart:388–442, 560–566); exponential backoff; lease-reclaim of abandoned PROCESSING rows; transient-vs-permanent failure triage. Textbook offline-first.
3. **Cryptography choices.** Ed25519 device signatures over a frozen canonical string (crypto_signer.dart:100–137 ↔ server.py:392–487, byte-matched and comment-frozen on both sides); keys in FlutterSecureStorage/Keystore; HMAC fully removed from the client; timing-safe admin compares on all admin endpoints (server.py:562, 638, 675, 1744); LCA issuance signature is HMAC-SHA256 bound to `batch_uuid` to prevent cross-batch replay (lca_engine.py:307–324); fail-loud `_require_secret()` startup guard.
4. **Certificate pinning, fail-closed.** Release builds refuse to boot without `DMRV_PINNED_CERT_PEM` (sync_queue_manager.dart:138–160). Debug builds use system trust for staging. No cleartext traffic; no WebView; no hardcoded URLs or secrets in the client.
5. **FreeRASP device integrity, fail-closed**, with a global compromise flag checked before every signing operation (crypto_signer.dart:108, 128, 141); `DMRV_DEMO_MODE` throws in release builds (device_integrity_service.dart:16–19).
6. **Idempotency done properly.** Batch creation handles the check-then-insert race via IntegrityError + re-query (server.py:1195–1223); one-to-one evidence supports a correction workflow via `_upsert_one_to_one_evidence` (server.py:1017–1058); DB-level CHECK constraints on lab values (models.py:295–305).
7. **Test discipline.** 42 backend test files (262 tests) including per-phase regression suites (P0-21…P2-4, C1–C10); 51 client test files covering migrations, crypto canonicals, sync deadlock/triage, BLE stabilization, and integrity enforcement.
8. **Paper trail.** REMEDIATION_LOG.md journals every phase with gates; FINDINGS_BACKLOG.md honestly tracks what is *not* done. The docs do not overclaim — the code's dormant gates are documented as dormant. That honesty is rare and valuable.

---

## 2. Rainbow Methodology Compliance — The Real Enforcement State

`COMPLIANCE_ENFORCED = True` (corroboration.py:38) sounds finished. It is not. Verified criterion-by-criterion against `docs/dMRV Criteria Distributed Biochar.md` and the actual `recompute_batch_credit()` call graph:

### 2.1 ENFORCED — actually gates issuance today (8 criteria)

| Criterion | Reason emitted | Wiring |
|---|---|---|
| C1 biomass input | `missing_biomass_input` / `missing_conversion_factor` | server.py:865–869 |
| C2 moisture (≥1/100 kg, min 10, photographed) | `insufficient_moisture_samples` | server.py:789 |
| C3 open-kiln pyrolysis photos, flame < 0.5 m | `missing_pyrolysis_photos`, `flame_height_out_of_range` | server.py:813–817 (kiln-type-conditional) |
| C3b closed-kiln ignition energy | `missing_ignition_energy` | server.py:818–821 |
| C4 composite pile sample | `missing_composite_sample` | server.py:807 |
| C5 delivery record + buyer identity | `missing_delivery_record`, `missing_buyer_identity` | server.py:825 |
| C7 lab Corg (else provisional) | `assumed_corg` (and `assumed_h_corg`) | server.py:899–921 |
| C8 kiln registration | `unregistered_kiln` | server.py:875–882 |

### 2.2 DORMANT — deriver written and unit-tested, but **never fires** (3 criteria)

This is the "someone started and left it in the middle" category, and it is load-bearing for credit integrity:

1. **C8 scale-calibration expiry.** `derive_scale_calibration_compliance` (corroboration.py:262–273) is **never called** in `recompute_batch_credit`. The `scale_calibration_expired` reason sits in the compliance catalog (server.py:2024) but is unreachable. Root cause: **`Batch` has no `project_id`/`scale_id` foreign key**, so the server cannot resolve which calibration applies (comment at server.py:859–861 admits this).
2. **C9 annual methane (≥3 independent runs).** `derive_annual_methane_compliance` (corroboration.py:276–287) — same story: exists, tested, never called. `missing_annual_methane` (catalog server.py:2025) unreachable. A test even asserts the dormancy (`test_annual_verification_c9.py:144`).
3. **C9 PAH for closed kilns — hardcoded bypass.** server.py:890–895: `pah_measured = False` is a literal, and the deriver is called with **`enforced=False` hardcoded**, so `missing_pah` (catalog server.py:2026) can never be emitted *even if* the linkage gap were fixed. This is the single most misleading line in the compliance layer: the catalog advertises a gate that is switched off at the call site.

**All three are blocked on one missing schema change: a batch→project linkage.** That FK is the highest-leverage single item in the entire backlog (tracked as P1.b in docs/REMEDIATION_PLAN_NONUI.md).

### 2.3 AUDIT-ONLY / DATA-CAPTURE-ONLY — collected, never affects the credit

- **C6 transport events:** `TRANSPORT_EVENTS_ENFORCED = False` (emission_factors.py:27). Per-leg fuel emissions are computed and stored in `lca_audit_json.transport_events` (server.py:957–965) but do not move the credit. Every fuel factor is an explicit placeholder: `"diesel": 2.68  # TODO(cite): placeholder, ~DEFRA-order; NOT methodology-sourced` (emission_factors.py:37–39). Deliberate (Rainbow annex never supplied numbers) and honestly flagged — but it means transport decarbonization claims are currently **unquantifiable against the methodology**, and flipping the flag without cited factors would retroactively change issued credits.
- **C7 1000-yr inertinite pathway:** inertinite %, residual Corg, Ro count are captured via the admin lab channel but no project-level pathway election exists, so the alternate permanence calculation has no trigger.
- **C7 biochar moisture (lab):** methodology requires ≥3 samples; `biochar_moisture_samples_json` is stored with **no count validation** anywhere.
- **C9 conversion factor:** captured in `AnnualVerification` but never wired into the C1 `yield_conversion` derivation.
- **C9 leakage assessment, heavy metals, quality-oversight report; C8 operator training and supervisor visits:** all captured through admin endpoints, none gated, none validated beyond schema shape.

### 2.4 Compliance bottom line

**~8 of 15 core methodology requirements actively enforce; 4 are capture-only awaiting sign-off/factors; 3 are dormant behind one missing FK (one of them additionally hard-bypassed).** The C10 "unified gate" is real and well-built, but calling C0–C10 "ALL DONE" (as the internal notes do) is true only for *data capture*, not for *enforcement*. A verifier walking this system today would find three catalog reasons that can never fire.

Also fully absent from code (methodology-adjacent, likely Rainbow/registry-side but worth stating): buffer-pool/uncertainty deductions, verifier workflow/registry integration, permanence monitoring beyond H:Corg math, and any human-verifier UI. The `/compliance` endpoint is the only verifier-facing surface, and it is admin-secret-only JSON.

---

## 3. Security — Brutal Cut

### 3.1 Solid

Ed25519 with frozen canonicals; timing-safe admin auth; one-time expiring enrollment tokens; path-traversal guard (`is_relative_to`, server.py:1352) + filename sanitization + 10 MB cap + streaming SHA-256 on uploads; strict Pydantic `extra="forbid"` everywhere; ORM-only (no raw SQL); CORS explicit-origin with `allow_credentials=False`; batch-ownership authz on all evidence endpoints (403 `not_your_batch`, fixed in commit `4e95e9d` with regression tests); client-side SQLCipher, secure key storage, cert pinning, RASP, GPS-redacting Sentry breadcrumbs.

### 3.2 Open holes (in priority order)

1. **Device attestation is theater.** `_ATTESTATION_ENFORCED = False` (server.py:197); `attestation_verified = False  # TODO(security): real Play Integrity/DeviceCheck` (server.py:760). A rooted device's forged blob passes with a log warning. The client-side FreeRASP checks help but are bypassable on a compromised device by definition. Until Play Integrity/DeviceCheck verdicts are verified server-side, "device-signed evidence" means "signed by a key that *once* lived on a phone." Cross-team item (Google/Apple credentials) — correctly tracked in FINDINGS_BACKLOG, still the #1 security gap for credit integrity.
2. **No rate limiting anywhere.** Zero throttling on enrollment, batch creation, media upload, or admin endpoints. One enrolled device can spam unbounded batches/evidence; `X-Admin-Secret` can be brute-forced at wire speed (mitigated only by secret entropy).
3. **Signatures are replayable.** The canonical string contains no timestamp or nonce beyond the idempotency key. Idempotency prevents duplicate *processing*, but a captured request is valid forever. Add a signed timestamp with a freshness window, or server-issued nonces.
4. **Android release builds are signed with the debug keystore.** android/app/build.gradle.kts: `signingConfig = signingConfigs.getByName("debug")` under a literal `// TODO: Add your own signing config`. Any release APK built today is package-replaceable. 30-minute fix; absolute ship blocker.
5. **No code obfuscation.** No ProGuard/R8 `minifyEnabled`, no rules file. The evidence-capture logic and canonical-string format are trivially readable from the APK (the canonical is not a secret, but RASP-bypass patching is easier on unobfuscated builds).
6. **No screenshot protection** (`FLAG_SECURE`) on screens showing batch UUIDs/GPS.
7. **EXIF GPS corroboration is weak evidence.** 1 km match threshold, and EXIF is attacker-controlled — the client *writes* the EXIF itself (secure_capture_service.dart:30–43), so server-side EXIF checking corroborates the client against the client. Same-device self-corroboration is a known, documented residual: one device's streams corroborate each other, not reality.
8. **Health endpoint lies by omission** — `/api/health` (server.py:379–385) returns OK without touching the DB.
9. **Local `.env`/`dmrv.db` on disk.** To be fair (an earlier internal review overstated this): **neither is git-tracked** — `.gitignore` covers `.env`, `*.db`, `uploads/`, `*.zip`, and only `backend/.env.example` is committed, with all required vars documented. But the dev HMAC secret sitting in a Downloads folder on an unbacked-up laptop is still a rotation candidate the day anything ships.

---

## 4. "Started and Left in the Middle" — Complete Inventory

Every half-finished artifact found, small to large:

| # | Item | Where | State |
|---|---|---|---|
| 1 | CI workflow written, **never committed** | `.github/workflows/backend-ci.yml` (untracked) | CI has never executed; the file even documents its own gaps (black broken locally, mypy not configured, no coverage floor, ruff non-blocking with ~100 legacy issues) |
| 2 | **No git remote** | `git remote -v` → empty | 15 commits + uncommitted work exist on one machine only |
| 3 | Uncommitted P0.a work in progress | `backend/server.py` (+37), `test_p0_21_hmac_secret.py`, REMEDIATION_LOG (+65) | The `DMRV_DISABLE_DOTENV` fix + `_require_secret()` consolidation is done and passing (262/0) but sits unstaged |
| 4 | `main` is 14 commits stale | branch state | Everything post-"initial remediation" lives only on `remediation/phase-by-phase` |
| 5 | PAH gate hard-bypassed | server.py:890–895 (`enforced=False`, `pah_measured = False` literal) | Catalog advertises a reason that cannot fire |
| 6 | Scale-calibration + annual-methane derivers orphaned | corroboration.py:262–287, never called | Blocked on missing batch→project FK (P1.b) |
| 7 | Fuel emission factors are uncited placeholders | emission_factors.py:34–39, `TODO(cite)` ×3 | Deliberate; needs Rainbow annex + sign-off + flag flip |
| 8 | Attestation verification stub | server.py:758–767, two security TODOs | Blob accepted, logged, never verified |
| 9 | 1000-yr inertinite pathway | lab capture only; no project election setting | Needs a project-settings mechanism that doesn't exist |
| 10 | C9 conversion factor / methane rate not wired into LCA math | lca_engine step 7 unchanged | Awaiting methodology sign-off (documented) |
| 11 | Lab biochar-moisture min-3 rule not validated | admin `/api/v1/admin/lab` | Methodology requires ≥3; any count accepted |
| 12 | No correction workflow for one-to-many evidence | moisture/composite/transport endpoints (server.py:1546–1613) | One-to-one tables got upsert corrections; these can only add new UUIDs |
| 13 | Release signing TODO | android/app/build.gradle.kts | Literal TODO comment shipped since scaffold |
| 14 | 4 unused `sync_queue_manager` imports in production screens | end_use_application/moisture_verification/pyrolysis/yield_scale screens | Suggests an abandoned direct-sync-trigger refactor |
| 15 | Deprecated APIs in use | `issueCustomQuery` ×3 (app_database.dart:128,151,160), Workmanager `isInDebugMode` (sync_queue_manager.dart:195) | Will break on dependency upgrades |
| 16 | Response-shape inconsistency | `{"status": "success"}` vs `{"status": "ok"}` across endpoints | Cosmetic but reveals two authorship eras |
| 17 | Remediation plan phases P2–P4 explicitly deferred | docs/REMEDIATION_PLAN_NONUI.md | Hardening, Postgres concurrency/FKs, object storage, idempotency extensions, client robustness — planned, unstarted |
| 18 | Stale scaffolding docs | DEPLOYMENT.md, PROJECT_README.md (June 2, pre-remediation) | Describe a Dockerfile that doesn't exist in-repo; omit `DMRV_ADMIN_SECRET`, admin endpoints, compliance layer entirely |
| 19 | Tracked cruft | `dummy.jpg` (5 bytes), `yarn.lock` (86 bytes, no Node code), `dmrv_app.iml` (IDE file) | Trivial, but tracked |
| 20 | Disk-only cruft (gitignored, still in the working tree) | `New folder.zip` (5.4 MB), `.baseline_*.txt`, `.gradio/`, stray pytest/ruff caches | Working-directory noise |
| 21 | 13 untracked docs | `docs/CBAM_*`, `STRATEGIC_*`, `UX_*`, REMEDIATION_PLAN itself | The remediation *plan of record* is not in version control |
| 22 | pytest asyncio-mark warnings | test_transport_events_flow.py:30,36,46 (12 warnings total) | Sync tests carrying `@pytest.mark.asyncio` |
| 23 | Test deps in runtime requirements | requirements.txt ships pytest/pytest-asyncio | No requirements-dev split |

---

## 5. Backend Engineering Quality

- **God file:** server.py is 2,073 lines — ~61% of the backend. Pydantic schemas, auth, evidence handlers, admin handlers, and the 255-line recompute function all live together. Refactor into `schemas.py` / `evidence.py` / `admin.py` before the next 10 endpoints arrive.
- **Missing dependencies (deploy-breaking):** `cryptography` (imported server.py:44–45) and `python-dotenv` (server.py:26) are **not in requirements.txt**. Today they install transitively/by luck of the dev machine; a clean `pip install -r requirements.txt` on a fresh host is not guaranteed to boot. This is a P0 one-line fix.
- **No read API.** There is no `GET /batches`, no list, no pagination, no device-scoped query. The only read endpoint in the entire API is the single-batch admin compliance report. Operations, support, and any dashboard are impossible without direct DB access.
- **Storage:** uploads go to local disk next to the code (server.py:265–266) — no object storage, no backup, no cleanup job, no virus scanning.
- **Observability: effectively none.** Plain-text logs, no JSON structure, no metrics endpoint, no tracing/correlation IDs, health check without DB probe.
- **Recompute is synchronous** in every evidence request — safe (idempotent) but wasteful under concurrent evidence for one batch; fine for pilot, needs a queue at scale.
- **No connection-pool tuning** (`pool_pre_ping`, sizes) for the Postgres path (db.py:24–28).
- **Magic numbers** scattered with good comments but no named constants: 1 km GPS threshold, 100 km transport threshold, 150 km/h plausibility, 60-sample burn floor, 0.5 under-reporting ratio, etc.
- **Alembic discipline is good** (13 reversible migrations, head `e1f2a3b4c5d6`, auto-upgrade on startup) — but nothing in CI verifies models↔migrations parity, and CI itself doesn't run (see §7).
- **LCA engine is clean:** pure functions, full audit dataclass, CSI Artisan C-Sink 3.2 steps implemented faithfully with the conservative H:Corg ≥ 0.4 → 70% branch.

---

## 6. Flutter Client Quality

Strongest component of the system. Remaining gaps beyond the §3 security items:

- **Test shape is lopsided:** excellent unit coverage (migrations, crypto, sync, BLE) but ~3 real widget tests, **zero golden tests, zero end-to-end flow tests** (capture → sourcing → moisture → pyrolysis → yield → application → sync is never exercised as one path).
- **l10n is real but thin:** English + Hindi with proper Devanagari fonts, but only ~10 externalized keys per locale — a meaningful share of UI copy is inline (some deliberately bilingual, e.g. `subtitleHindi` in dashboard_screen.dart:128). For a Marathi-belt deployment (Kolhapur), a third locale isn't even scaffolded.
- **No analytics/field telemetry** (sync success rate, batch completion funnel) — you will be blind to field failure modes except via Sentry crashes.
- **Versioning is manual** at `1.0.0+1`; no CI bump/tag pipeline (there is no CI).
- Demo affordances are properly caged: Delhi fallback coords only under `DMRV_DEMO_MODE` (location_service.dart:49–74), camera debug view behind a debug-only long-press.
- **Zero TODO/FIXME in lib/** — the client codebase is genuinely finished at its declared scope.

---

## 7. Testing & CI — The Uncomfortable Truth

The suites are excellent **and they have never run anywhere but this laptop.**

- `.github/workflows/backend-ci.yml` is well-designed (blocking pytest with `DMRV_DISABLE_DOTENV=1` and env-supplied secrets; informational ruff) — and **untracked**, so it has never executed.
- `codegen.yml` (tracked) guards Drift codegen drift on PRs — but with **no remote**, there are no PRs, so it has also never executed.
- No Flutter CI at all (analyze/test/build are manual).
- No coverage measurement, no mypy, black documented as broken locally, ruff sitting on ~100 legacy findings.
- No load/perf tests; no integration tests against real Postgres (suite runs on in-memory SQLite — schema-drift risk vs the declared Postgres production path is untested).

---

## 8. Repo Hygiene & Documentation

- **Docs sprawl with mixed concerns:** engineering docs share `docs/` with CBAM strategy, M&A analysis, institutional research briefs, and a newspaper-article draft. Four UX plan documents (UX_BUILD/DESIGN/EXECUTION/FIELD_THEME) are untracked but — verified against `lib/ui` — **actually implemented** (`integrity_footer.dart`, `premium_action_card.dart`, `rugged_button.dart`, `app_theme.dart` all exist and match the specs). The specs are current; they're just not in version control.
- **Source-of-truth confusion:** `terracipher_reports/` (10 tracked prompt/report files), `docs/history/` (17 archived files), REMEDIATION_LOG (102 KB), FINDINGS_BACKLOG, and an untracked REMEDIATION_PLAN_NONUI all overlap. The archive discipline (docs/history) is good; the *current-state* doc is effectively "REMEDIATION_LOG tail + FINDINGS_BACKLOG," which no newcomer would guess.
- **Stale front-door docs:** README.md is literally the one-line placeholder `# Here are your Instructions`; PROJECT_README.md's "Project Structure" section cuts off mid-sentence; DEPLOYMENT.md (352 lines) predates the remediation era and is aspirational — Docker/K8s/Heroku instructions with **no actual Dockerfile, compose file, or manifest anywhere in the repo**, and no mention of `DMRV_ADMIN_SECRET` or the admin/compliance API. A new engineer following it would deploy a server that crashes on boot.
- **Tracked oddities:** `yarn.lock`, two IDE files (`dmrv_app.iml`, `android/dmrv_app_android.iml` — no `*.iml` rule in .gitignore), `backend/dummy.jpg`, and a throwaway `scripts/ci_grep_demo.sh`.
- `.gitignore` is actually good (covers `.env`, `*.db`, uploads, zips, baselines) — hygiene inside the index is far better than the working directory suggests.

---

## 9. What Is Needed for Production — Prioritized

### P0 — Existential / this week (mostly hours, not days)

1. **Create a remote (GitHub/GitLab), push `main` + `remediation/phase-by-phase` today.** A laptop failure currently erases the project.
2. **Commit the in-flight work**: the P0.a server.py/dotenv change, `backend-ci.yml`, REMEDIATION_PLAN_NONUI.md, and triage the other 12 untracked docs. Merge or fast-forward `main`.
3. **Add `cryptography` and `python-dotenv` to requirements.txt** (and split a `requirements-dev.txt`).
4. **Get CI actually running** (it's already written) + add a Flutter lane (analyze/test/build).
5. **Real Android release keystore; delete the debug-signing TODO. Enable R8/ProGuard with rules.**

### P1 — Before any credit is issued to a real buyer

6. **Add `batch.project_id` (and scale linkage), then wire the three dormant gates** — scale-calibration expiry, annual methane, PAH (remove the hardcoded `enforced=False`). This single migration converts ~62% methodology enforcement to ~90%.
7. **Server-side Play Integrity / DeviceCheck verification; flip `_ATTESTATION_ENFORCED`** (cross-team: needs Google/Apple credentials).
8. **Rate limiting** (per-device and per-IP; strict on `/register`, `/admin/*`) and **signature freshness** (signed timestamp window or nonce) to kill replay.
9. **Cited fuel emission factors from Rainbow → flip `TRANSPORT_EVENTS_ENFORCED`** with methodology sign-off; wire C9 methane rate and conversion factor into the LCA (also sign-off-gated).
10. **Postgres in CI + staging** (kill the SQLite/Postgres drift risk); pool tuning; nightly backups with a tested restore.

### P2 — Before scale / external verifier scrutiny

11. Object storage (S3/MinIO) for evidence media; retention & cleanup policy.
12. Read API with pagination + auth (batch lists, device scoping) — prerequisite for any ops dashboard or verifier portal.
13. Observability: structured JSON logs, `/metrics`, correlation IDs, DB-probing health check.
14. Break up server.py (schemas/evidence/admin modules); name the magic numbers; standardize response envelopes.
15. E2E client flow test + widget/golden coverage; `FLAG_SECURE`; correction workflow for one-to-many evidence; validate lab moisture ≥3.
16. Rewrite DEPLOYMENT.md/PROJECT_README.md against reality; add a real Dockerfile/compose; consolidate docs into `docs/engineering` vs `docs/business`; delete `New folder.zip`, `dummy.jpg`, `yarn.lock`, `.iml`.

### Explicitly external (not engineering-blockable)

- Rainbow annex fuel factors and methodology sign-offs (C6/C9 credit-math, C7 1000-yr election policy).
- Play Integrity / DeviceCheck provider credentials.
- Registry/verifier integration requirements (buffer pool, uncertainty deductions, issuance workflow) — nothing in this codebase addresses them yet.

---

## 10. Bottom Line

The team built the **hard parts first and built them well**: trust architecture, offline sync, cryptographic evidence binding, and an honest compliance gate with a written audit trail — this codebase is more trustworthy than its polish suggests. What's missing is almost entirely the **unglamorous productionization ring around it**: version-control basics (a remote!), CI that actually runs, release signing, dependency packaging, rate limiting, storage, observability — plus **one schema migration (batch→project) that three methodology gates have been waiting on**, and one hardcoded `enforced=False` that quietly disables a gate the compliance catalog claims to have.

**Fit for:** a supervised pilot with a known device fleet and manual verification, today.
**Not fit for:** unsupervised field deployment, adversarial devices, or issuing credits a verifier/buyer will audit — until P0 + P1 above are closed. Realistic effort to "verifier-defensible production": **~3–5 focused engineering weeks** for everything not blocked on Rainbow/Google/Apple externals.
