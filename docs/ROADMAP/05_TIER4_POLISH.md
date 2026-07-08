# Tier 4 — Polished Final: "The Best Version of Itself"

> **Benchmark when this tier is green:** a new senior engineer is productive in a day; the test suite catches UI and flow regressions, not just unit ones; the app serves its actual users (Marathi-speaking field operators) in their language with known field reliability numbers; the repo reads like a flagship product. **Registry-grade.**
>
> **Total effort: ~2–3 weeks, fully parallelizable, zero external blockers.** Nothing here is a correctness fix — do not start T4 while T1/T2 items are open unless people are free.

---

## T4.1 — Break up the god file (server.py, 2,073 lines)

- **Where:** `backend/server.py` — 61% of all backend code: schemas + auth + evidence + admin + recompute in one module.
- **What (mechanical, zero behavior change, one PR per step so review stays honest):**
  1. `backend/schemas.py` — every Pydantic model (`BatchPayload`, evidence payloads at server.py:1421-1544, admin payloads, response models).
  2. `backend/auth.py` — `verify_signature`, `verify_media_signature`, `_require_admin` helper (extract the 4× repeated `hmac.compare_digest` header check into one dependency), `_require_secret`, `_load_env`.
  3. `backend/routes/evidence.py` — telemetry/yield/metadata/application/moisture/composite/transport handlers + `_upsert_one_to_one_evidence` + `_assert_batch_ownership` (APIRouter).
  4. `backend/routes/admin.py` — the 6 admin endpoints + compliance report + `_COMPLIANCE_CATALOG`.
  5. `backend/credit.py` — `recompute_batch_credit` + its helpers (haversine, `_evaluate_anchor`, EXIF utils).
  6. `server.py` keeps: app factory, middleware, lifespan, register/mint-token/batches/media.
- **Gate:** full pytest green after every step; `wc -l backend/server.py` < 700 at the end; no route path changes (`test_endpoint_schemas.py` proves it).
- **Effort:** L.

## T4.2 — Name the magic numbers

- **Where/What:** one `backend/constants.py` (or top-of-module constants) with citation comments:
  | Value | Current location | Name |
  |---|---|---|
  | 1.0 km GPS anchor mismatch | server.py:~152 | `GPS_ANCHOR_MISMATCH_KM` (done in T2.7 if that ran) |
  | 100 km transport-penalty threshold | lca_engine.py:~47 | `TRANSPORT_PENALTY_THRESHOLD_KM` (CSI 3.2 §) |
  | 150 km/h implausible movement | server.py:~1157 | `MAX_PLAUSIBLE_SPEED_KMH` |
  | 60 min temperature samples | corroboration.py / server.py:341 | `MIN_TEMP_SAMPLES` (CSI rule) |
  | 10 moisture readings floor | corroboration.py:~132 | `MIN_MOISTURE_READINGS` (Rainbow C2) |
  | 0.5 transport under-report ratio | server.py:853 | `TRANSPORT_UNDERREPORT_RATIO` |
  | 20 kg CO2e/t safety margin | lca_engine.py:~155 | `SAFETY_MARGIN_KG_PER_T` (CSI Step 4) |
- Also standardize the response envelope: pick `{"status": "ok", ...}` and align the `"success"` variants (moisture/composite/transport handlers) — **additive caution:** the deployed client's sync code checks HTTP status, not the body string (sync_queue_manager.dart treats 2xx as success), so this is safe; verify with `grep -n '"status"' lib/services/sync_queue_manager.dart` first.
- **Gate:** grep shows no bare numeric thresholds in handlers; suite green.
- **Effort:** S/M.

## T4.3 — Correction workflow for one-to-many evidence

- **Where:** moisture / composite-sample / transport handlers (server.py:1546-1613). One-to-one tables (telemetry/yield/application) got upsert-corrections; these three can only ever add new UUIDs — a wrong reading is permanent.
- **What:** additive tombstone pattern (never mutate evidence in place — audit trail): new optional field `supersedes_uuid` on each payload; server marks the referenced row `superseded_by=<new_uuid>` (new nullable column ×3 tables + migration) and recompute filters `superseded_by IS NULL`. Client UI for it can come later; the API capability unblocks manual ops corrections immediately.
- **Gate:** test: superseded moisture reading no longer counts toward `insufficient_moisture_samples`; original row still present.
- **Effort:** M.

## T4.4 — Zero-warning clients: clear all 25 analyzer issues

- **Where/What (the actual 25):**
  1. 4 unused `sync_queue_manager.dart` imports in production screens — delete lines: `end_use_application_screen.dart:7`, `moisture_verification_screen.dart:5`, `pyrolysis_screen.dart:4`, `yield_scale_screen.dart:5`.
  2. 3× deprecated `issueCustomQuery` → `customStatement` in migrations: `app_database.dart:128,151,160` (test the v11/v15 migration paths still pass — `migration_v11` tests exist).
  3. Workmanager `isInDebugMode` deprecated: `sync_queue_manager.dart:195` — remove the param.
  4. The rest are in `test/`: unused imports (`background_sync_test.dart:3,6,7`, `location_service_release_guard_test.dart:14`, `pyrolysis_json_check_test.dart:4`), `avoid_print` ×4, relative lib imports ×4 in `test/remediation/device_integrity_enforcement_test.dart` (switch to `package:` imports), deprecated `setMockMethodCallHandler` (same file:43), unused local (same file:53), curly braces (`l10n_test.dart:66`), `unnecessary_this` (`sync_two_phase_test.dart:58`).
  5. Then make CI strict: `flutter analyze --fatal-infos` in `.github/workflows/flutter-ci.yml`.
- Backend twin: run `ruff check backend --fix`, hand-fix the rest of the ~100 legacy findings, flip the CI lint job from `continue-on-error: true` to blocking.
- **Gate:** `flutter analyze` → 0 issues; ruff blocking and green.
- **Effort:** M.

## T4.5 — Test-pyramid completion (client)

- **What, in value order:**
  1. **E2E flow test** (`integration_test/full_flow_test.dart`): start batch → secure capture (mock camera/GPS) → sourcing → moisture ×N → pyrolysis (VirtualBleAdapter already exists in tests) → yield (mock scale) → end-use application → assert outbox contains the complete, correctly-signed JSON set; run against a mock server verifying signatures with the real backend canonical (reuse vectors from `backend/tests/test_client_contract.py` — this closes the client↔server contract loop).
  2. **Widget tests for all 9 screens:** render, error state, disabled-button state, l10n key presence (currently ~3 exist).
  3. **Golden tests** for the shared components + dashboard (guards the theme against dependency-upgrade drift). **Sequencing:** if T5 Stage A (UI unification, [06_TIER5_UI_PLATFORM.md](06_TIER5_UI_PLATFORM.md)) is planned, land it *before* recording goldens — otherwise every golden is re-recorded when the token migration lands, and note `premium_action_card` is deleted by T5.3.
- **Gate:** `flutter test` includes e2e in CI (or a separate integration lane); coverage report ≥70% lines on `lib/services` + `lib/data`.
- **Effort:** XL (the single biggest T4 item; the e2e alone is worth doing early).

## T4.6 — Marathi (mr) locale + l10n completeness

- **Where:** `lib/l10n/` (currently `app_en.arb`, `app_hi.arb`, ~10 keys each), screens with inline strings.
- **Why:** deployment geography (Kolhapur) is Marathi-first; Hindi is a fallback, not the operator's language.
- **What:** sweep every screen for inline user-visible strings → externalize to ARB (expect 60–120 keys, not 10); add `app_mr.arb` (NotoSansDevanagari already bundled covers Marathi); add `Locale('mr')` to supported locales (main.dart:74-80); native-speaker review pass on hi/mr. **Note:** the externalization sweep is the same work as T5.5 in [06_TIER5_UI_PLATFORM.md](06_TIER5_UI_PLATFORM.md) — do it once; whichever tier runs first owns it, and this task then reduces to adding `app_mr.arb` + review.
- **Gate:** extend `test/l10n_test.dart`: all three ARBs have identical key sets; no `Text('` literals with raw English in `lib/ui/screens` (lint or grep-based test).
- **Effort:** L.

## T4.7 — Field telemetry (first-party, opt-in)

- **What:** you're currently blind to field failure modes except crashes. Add a tiny counters payload to the existing sync channel (no third-party SDK): sync attempts/successes, retry counts, permanent failures, capture failures by `CaptureErrorKind`, BLE connect failure counts. New device-authenticated endpoint `POST /api/v1/telemetry-app` (name distinct from pyrolysis telemetry) storing rows keyed by device+day; surfaced in the T3.4 summary endpoint. Opt-in flag in app config; no PII, no location.
- **Gate:** dashboard-able answer to "which devices fail to sync and why".
- **Effort:** M.

## T4.8 — iOS release readiness

- **What:** the iOS lane is configured (Info.plist permissions complete) but has never been release-built: set up signing (certs/profiles), verify freeRASP `TALSEC_IOS_TEAM_ID`, build IPA, run the e2e on a physical iPhone, TestFlight it. Decide honestly whether iOS is in scope for the pilot; if not, say so in README and skip until it is.
- **Effort:** L (mostly Apple ceremony). **Blocked-by:** Apple Developer account.

## T4.9 — Release pipeline + versioning

- **What:** tag-driven releases: on `v*` tag, CI builds the signed, obfuscated APK/AAB (secrets from CI store), attaches symbols, bumps `pubspec.yaml` version from the tag, creates a GitHub Release with the artifact + changelog (conventional commits already in use — `feat(dmrv):`… — so `git-cliff`/`release-please` slots in cleanly).
- **Gate:** pushing `v1.1.0` produces an installable signed artifact with no human on the box.
- **Effort:** M. **Depends on:** T0.6, T2.4.

## T4.10 — Documentation truth pass

- **What:**
  1. **Rewrite `DEPLOYMENT.md`** against the real T3.2 artifacts (delete the aspirational K8s/Heroku sections or move to an "options" appendix); document every env var from `.env.example` including `DMRV_ADMIN_SECRET`, rate-limit vars, storage vars; add the backup/restore runbook (T3.6) and pin-rotation policy (T3.9).
  2. **Fix `PROJECT_README.md`** — the "Project Structure" section cuts off mid-sentence; refresh the endpoint inventory (21 endpoints, not the original 4).
  3. **Reorganize docs/:** `docs/engineering/` (methodology criteria doc, REMEDIATION_PLAN, UX specs, this ROADMAP), `docs/business/` (CBAM/M&A/strategy/articles), `docs/history/` (already exists — move `terracipher_reports/` prompts into it; keep `RAINBOW_C0_C10_HANDOFF.md` and the criteria doc prominent as the two methodology sources of truth).
  4. **Write `docs/engineering/ARCHITECTURE.md`** (1–2 pages): the trust model (what's device-asserted vs server-derived vs admin-asserted vs lab), the provisional gate, the sync design, the canonical-string contract. This is the doc every new engineer and every verifier asks for first.
  5. Add `CHANGELOG.md` seeded from the conventional-commit history.
- **Gate:** a person who has never seen the repo deploys staging from docs alone (actually try this).
- **Effort:** M/L.

## T4.11 — Data lifecycle & privacy note

- **What:** buyer names/contacts (C5) and GPS are personal data under India's DPDP Act. Write a one-page data-handling note: what's collected, retention, deletion path (tombstone pattern from T4.3 helps), who can read it (admin endpoints), and encrypt-at-rest posture (SQLCipher client-side; enable Postgres/at-rest encryption server-side). Add `buyer_contact` redaction to log/Sentry scrubbing (T3.5).
- **Gate:** the note exists and matches the code; grep proves buyer_contact never hits logs.
- **Effort:** S/M.

---

## ✅ Tier 4 exit criteria (the benchmark, verbatim)

- [ ] No file > 800 lines in `backend/`; zero analyzer/ruff findings; both linters blocking in CI.
- [ ] E2E flow test + goldens green in CI; client coverage ≥70% on services/data.
- [ ] en/hi/mr locales with identical key sets; no inline English UI strings.
- [ ] Tag → signed artifact pipeline works hands-free.
- [ ] A stranger deploys staging from documentation alone; ARCHITECTURE.md answers the verifier's first ten questions.
- [ ] Field-telemetry dashboard answers "how is the fleet doing" without a phone call.

**This is the polished, final version: nothing hidden, nothing half-wired, nothing that only works on one laptop — the codebase you'd hand to a registry, an auditor, or an acquirer without flinching.**
