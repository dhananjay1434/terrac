# TerraCipher dMRV — Production-Readiness EXECUTION PROMPT (agent-runnable)

> **You are an execution agent.** This closes the gap between "computes a credit" and
> "issues a real, registry-verifiable credit," per `docs/PRODUCT_REALITY_MAP.md` and
> `docs/PATH_TO_ISSUANCE.md`. Follow this literally, one Part per PR, test-first. This is
> the companion to `docs/DEFERRED_WORK_EXECUTION_PROMPT.md` — same rules, same style.
> `§0` of `docs/PRODUCTION_EXECUTION_PLAN.md` (the Engineering Constitution) is **binding
> here verbatim** — read it first.

---

## 0. OPERATING RULES (obey always)

1. **One Part per session/PR.** Land it green + committed before the next.
2. **Never commit red.** Run the relevant suite after every change; fix before proceeding.
3. **Never fabricate.** If a feature can't produce data, render it "missing," never faked.
   **This is load-bearing for two Parts below (PR-C1, PR-C2) that an agent MUST NOT complete
   by inventing methodology numbers.**
4. **Additive, non-breaking.** New DB columns nullable; new API fields optional; every
   migration has a real `downgrade()`; old app + new backend must still work.
5. **NO GOD FILES.** One module = one responsibility. Business rules (state machines, gate
   math, methodology selection) are **pure functions in their own module**
   (`services/issuance_state.py`, `services/methodology.py`, extend `corroboration.py`) —
   routers/screens are thin adapters that call them. If a function mixes I/O with logic, or
   exceeds ~40 lines, split it. A reviewer must not be able to tell new files from old by
   style.
6. **Reuse the rails.** New evidence → the R1 entity-media rail. New device endpoint →
   mirror `routers/dispatch.py`. New portal action → `require_role`. New gate → the
   `corroboration.py` deriver pattern. New pure state machine → mirror `dispatch_state.py`.
   Writing a second copy of something that exists = you did it wrong.
7. **Test-first for all pure logic.** Write the failing unit test before the implementation.
8. **Layering.** Backend: `routers → services/domain → models`. App: `ui → providers →
   services/data`. No cross-layer shortcuts, no Drift/`http` in a screen.
9. **Resolve every `<placeholder>` from the live repo** — never paste it literally. New
   alembic revision → `python -m alembic revision -m "slug"` (never hand-write the id).
   Drift bump → re-read `lib/data/local/app_database.dart` `schemaVersion` and take next+1,
   then `dart run build_runner build --delete-conflicting-outputs`.
10. **Do not push. Do not open PRs. Do not rewrite git history.** Commit locally only. The
    human handles remote + any history rewrite (PR-8).

### Commands
```bash
cd backend && python -m pytest -q                 # backend suite
cd backend && python -m pytest tests/<f> -v       # one file
cd backend && python -m alembic heads             # migration head
flutter test                                       # app suite
flutter test test/<f>                              # one file
flutter analyze lib/<f> test/<f>                   # lint
cd portal && npm test -- --run && npx tsc --noEmit && npm run build
```

### GLOBAL PREFLIGHT — before ANY Part, confirm all green
```bash
cd backend && python -m alembic heads     # record; new migrations chain from it
grep -n "int get schemaVersion" lib/data/local/app_database.dart   # record
cd backend && python -m pytest -q         # must pass before you touch anything
flutter test                              # must pass
cd portal && npm test -- --run            # must pass
```
State-at-authoring (verify, don't trust): alembic head `fbad0d51b1b1`; Drift `v27`; Batch has
`status`/`net_credit_t_co2e`/`provisional`/`lca_methodology_version`/`lca_signature`; roles
`admin,lab,verifier,org_admin`; R1 entity-media rail accepts `subject_type ∈ {farmer,dispatch}`.

---

## ⛔ PARTS AN AGENT CANNOT COMPLETE — DO NOT FAKE THESE

These gate real issuance harder than any code, but they are **external/human**. An agent may
build the *plumbing* and the *skeleton doc*, but MUST NOT assert conformance or invent numbers.

### PR-C1 — Methodology conformance sign-off (CSI + Rainbow) · [PROCESS]
- **Agent may:** create `docs/METHODOLOGY_CONFORMANCE.md` — a table skeleton mapping each CSI
  Artisan/Global C-Sink formula AND each Rainbow formula → the exact code path in
  `lca_engine.py`/`corroboration.py` that implements it → a "VALIDATED BY / DATE / SOURCE"
  column left **blank**.
- **Agent must NOT:** write "conforms" / tick any validation box / invent a reference number.
  That column is filled only by a qualified carbon-methodology reviewer or VVB. State this at
  the top of the file in bold.

### PR-C2 — Fill Rainbow's numeric annexes · [PROCESS]
- `backend/emission_factors.py` already says it: transport fuel factors are placeholders,
  `TRANSPORT_EVENTS_ENFORCED=False`, "we DO NOT invent factors."
- **Agent may:** keep the plumbing ready so that when cited values arrive, flipping the flag
  wires them in (and add a test that the flag-off path is inert — likely already exists).
- **Agent must NOT:** populate `_FUEL_FACTORS_KG_CO2E_PER_L` with invented numbers or flip the
  flag. Leave a `TODO(cite)` per value. Report this Part as "blocked on methodology owner."

---

# PART PR-1 — Credit issuance ledger (serialized, issue-once units)

**The single biggest architecture gap.** Today a credit is a number on a batch. This makes it
a serialized unit with a lifecycle, immutable once issued, traceable to one physical batch.

**Rails to reuse:** pure state machine like `services/dispatch_state.py`; model in `models.py`;
thin portal endpoints under `require_role`; append-only audit via the existing `write_audit`;
migration via `alembic revision`.

### PR-1 PREFLIGHT
```bash
cd backend && python -m alembic heads      # record as <HEAD>
grep -n "net_credit_t_co2e\|lca_signature\|provisional\|status:" backend/models.py | head
grep -n "def write_audit\|require_role" backend/portal/routes.py | head
sed -n '1,40p' backend/services/dispatch_state.py   # mirror this pure-module shape
```

### STEP PR-1.1 — Pure lifecycle state machine (test-first)
1. Create `backend/tests/test_issuance_state.py` FIRST. Test a pure module
   `services/issuance_state.py`:
   - `validate_transition(current, target)` — legal: `pending → verified → issued →
     retired`; also `pending/verified → cancelled`; everything else raises
     `IllegalIssuanceTransition`.
   - `assert_issuable(batch_is_provisional, batch_is_signed, independently_verified)` —
     issuance requires: not provisional, signed (`lca_signature` present), AND
     independently verified (PR-2). Returns/raises with an explicit reason.
   - Immutability rule: `is_mutable(status)` → False once `issued`.
2. Implement `services/issuance_state.py` as pure functions only (no DB/HTTP), mirroring
   `dispatch_state.py`'s shape and error-class style.
3. **CHECKPOINT:** `python -m pytest tests/test_issuance_state.py -v` green.

### STEP PR-1.2 — Model + migration (additive)
1. `models.py`: add `class CreditIssuance(Base)`:
   - `issuance_uuid` (PK, str 36), `batch_uuid` (indexed, **FK to `batches.batch_uuid`** —
     unlike media/offline-first tables, issuance is a PORTAL action on an already-synced,
     signed, non-provisional batch, so the batch always exists; an FK is correct and safer
     here. If the FK-enforcing engine ever complicates tests, match the sibling no-FK
     convention instead — but do NOT justify it with the offline-first rationale, which does
     not apply to issuance), `serial` (unique, str), `vintage`
     (int, the production year), `t_co2e_frozen` (float — the credit amount snapshotted at
     issuance), `methodology_version` (str), `status` (str, default `pending`),
     `verified_by_user_id` (int, nullable), `issued_at` (datetime, nullable),
     `registry_submission_ref` (str, nullable), `created_at`.
   - `UniqueConstraint('serial')` and `UniqueConstraint('batch_uuid', name=...)` — **one
     issuance per batch** (anti-double-issue at the DB layer, per §0.7.1 concurrency rule).
2. `python -m alembic revision -m "create_credit_issuance"`; fill `upgrade()`/`downgrade()`
   (mirror `b7c1d2e3f4a5`'s style; real `downgrade` drops the table).
3. **CHECKPOINT:** `alembic heads` shows one head (yours); `alembic upgrade head` on a
   throwaway db succeeds.

### STEP PR-1.3 — Serial generation (pure + tested)
1. Test-first (`tests/test_issuance_serial.py`): a pure `make_serial(project_id, vintage,
   sequence)` → a deterministic, collision-resistant, human-legible serial (e.g.
   `{project_id}-{vintage}-{zero-padded sequence}`). Test determinism + uniqueness across a
   sequence.
2. Implement in `services/issuance_state.py` (or a small `services/issuance_serial.py` if
   cleaner — one responsibility).

### STEP PR-1.4 — Portal endpoints (thin adapters)
1. New `backend/routers/issuance.py` (mirror `routers/dispatch.py` structure), mounted in
   `app_factory.py`. Endpoints, all `require_role("admin")` (issue/retire) or
   `require_role("verifier","admin")` (verify):
   - `POST /api/v1/portal/batches/{batch_uuid}/issuance/verify` — records independent
     verification (calls PR-2's gate first; sets status `verified`, `verified_by_user_id`).
   - `POST /api/v1/portal/batches/{batch_uuid}/issuance/issue` — calls
     `assert_issuable(...)`; on pass, generates serial, freezes `t_co2e_frozen` from
     `batch.net_credit_t_co2e`, sets `issued`, writes audit. **Idempotent:** re-issuing an
     already-issued batch returns the existing issuance (never a second row / second serial).
   - `POST /.../issuance/retire` and `/cancel` — legal transitions only, via the pure machine.
   - `GET /api/v1/portal/issuances` — cursor-paginated list (reuse the existing pagination
     pattern), filterable by status/project.
2. Explicit Pydantic request/response schemas in `portal/schemas.py`. No `dict[str,Any]`.

### STEP PR-1.5 — Export references the serial
1. `services/export.py`: `export_batch_common` — when an issuance exists for the batch, include
   `{issuance: {serial, vintage, status, t_co2e_frozen, issued_at, registry_submission_ref}}`.
   Keeps the registry export traceable event→serial.

### STEP PR-1.6 — Tests
1. `tests/test_issuance_endpoint.py` (mirror `test_dispatch_endpoint.py` helpers): verify →
   issue happy path; issue-before-verify rejected; issue-of-provisional rejected;
   issue-of-unsigned rejected; **duplicate issue is idempotent (one serial, one row)**;
   illegal transition (e.g. retire a pending) → 409; export includes the serial after issue;
   role-gating (non-admin can't issue).
2. **CHECKPOINT:** file green, then full `python -m pytest -q` green.

### PR-1 DoD
- [x] Credit is a serialized, issue-once, immutable-after-issued unit with a lifecycle.
- [x] Anti-double-issue enforced at the DB layer (unique batch_uuid) — concurrency test.
- [x] Pure state machine + serial are unit-tested with no DB; endpoints are thin.
- [x] Export traces serial → batch. Three suites green before + after. One commit.

**DONE — 2026-07-23.** `services/issuance_state.py` (pure, 30 tests) +
`portal/issuance_routes.py` (new router, kept separate from the already-large
portal/routes.py) + `CreditIssuance` model/migration (`c3b4875454a4`) +
export wiring. **Correction vs the plan:** a pre-existing flat
`POST /batches/{uuid}/issue` endpoint (P2.6) already flipped
`Batch.status="ISSUED"` directly — not mentioned in this prompt. Left it
working (existing tests depend on it) but the new `.../issuance/issue` path
now also syncs `batch.status="ISSUED"` so the two don't disagree, with a
comment marking the ledger as the authoritative path going forward and the
old endpoint a deprecation candidate. Backend 675 passed / flutter 387
passed / portal 151 passed, before and after.

**COMMIT:** `feat(backend): credit issuance ledger — serialized, issue-once, traceable units`

---

# PART PR-2 — Enforced independent (4-eyes) verification gate

**⚠️ VERIFIED CONSTRAINT — read before coding.** The producer is a `device_id` (a device;
`Batch.device_id`); the verifier is a portal `PortalUser.id` (a human). **There is no
device↔operator-human mapping in the schema** — so you CANNOT check "verifier ≠ producer"
by id equality. Do not pretend to. The honest, implementable MVP and its explicit limit:
- **MVP (this Part):** issuance requires a sign-off by a portal user holding `verifier` or
  `admin` role — a *separate human channel* from the device that produced the batch (devices
  sign with Ed25519 and have no portal login, so a portal verifier is definitionally not the
  producing device). Record the verifier's `user_id` immutably.
- **Known limit (do NOT fake closure):** true anti-collusion (the human verifier is not the
  same person who operated the producing device) needs a **device↔operator-user identity
  map** that does not exist yet. Add `TODO(identity): link device_id → operator user to
  enforce person-level 4-eyes` and list it as a follow-up. Building that map is its own Part.

**Rail to reuse:** the `verifier` role + `write_audit`; the pure-deriver pattern in
`corroboration.py`. Depends on PR-1 (issuance `verify` step calls this).

### STEP PR-2.1 — Pure gate (test-first)
1. `tests/test_independent_verification.py`: a pure
   `derive_independent_verification(verifier_role, verifier_user_id)` → `(ok, reason)`.
   Rule (MVP): ok only when `verifier_role in {"verifier","admin"}` AND `verifier_user_id`
   is present. Reason `not_an_authorized_verifier` otherwise. (Do NOT add a
   producer-equality check — there's no id to compare against; see the constraint above.)
2. Implement in `corroboration.py` (extends the existing deriver family; pure).
3. **CHECKPOINT:** file green.

### STEP PR-2.2 — Wire into issuance verify
1. PR-1's `.../issuance/verify` endpoint calls this gate before setting `verified`. It runs
   under `require_role("verifier","admin")` already, so the role check is enforced by the
   dependency; the gate additionally records `verified_by_user_id` immutably and rejects
   (403 `not_an_authorized_verifier`) any path that reaches it without a valid verifier user.
2. Extend `tests/test_issuance_endpoint.py`: a non-verifier role is rejected; a verifier
   passes and `verified_by_user_id` is recorded.
3. **CHECKPOINT:** backend suite green.

### PR-2 DoD
- [x] A batch cannot reach `issued` without a recorded sign-off by a `verifier`/`admin`
      portal user (a human channel separate from the producing device).
- [x] Enforced at the gate, `verified_by_user_id` recorded immutably, reason-coded, unit-tested.
- [x] `TODO(identity)` filed: person-level anti-collusion needs a device↔operator-user map
      (its own Part) — NOT claimed as done here.

**DONE — 2026-07-23.** `derive_independent_verification` in `corroboration.py`
(pure, 6 tests) wired into `verify_issuance` alongside `require_role`.
Backend-only; 681 passed / 0 failed before and after.

**COMMIT:** `feat(backend): enforced 4-eyes independent verification before issuance`

---

# PART PR-3 — Sampling-plan + all-instrument calibration enforcement

**Rail to reuse:** the `corroboration.py` deriver + C10 signal pattern (see
`derive_density_calibration_compliance`, `derive_scale_calibration_compliance`). Env-gated
like the others; default per §0.4 but see the honesty note.

### STEP PR-3.1 — Sampling-plan deriver (test-first)
1. `tests/test_sampling_plan.py`: pure `derive_sampling_compliance(batch_mass_kg,
   in_scope_lab_result_count, samples_required_per_rule, *, enforced)` → `(ok, reason)`.
   Rule = the methodology's representative-sampling cadence (e.g. ≥1 composite lab result per
   N kg / per period). Reason `insufficient_lab_sampling`.
   **Do NOT invent the cadence number** — take it from the methodology config (PR-4 /
   `RegistryConfig`), default to the existing behavior when unset (grandfather).
2. Implement in `corroboration.py`.

### STEP PR-3.2 — Extend calibration gate to all instruments
**⚠️ VERIFIED CONSTRAINT.** Only `derive_density_calibration_compliance` and
`derive_scale_calibration_compliance` exist, and the only calibration MODEL is
`ScaleCalibration` — there is **NO thermocouple or moisture-meter calibration model, table,
or registry endpoint.** So this is NOT "just add a deriver": a deriver with no data source
gates on nothing. You must first create the record type, or you are faking a gate.
1. **Data source first (per instrument you add):** add a calibration model mirroring
   `ScaleCalibration` (e.g. `ThermocoupleCalibration`, `MoistureMeterCalibration` — project-
   or instrument-scoped, with `valid_until`), an Alembic migration (`alembic revision`), and
   a portal registry endpoint to create/list it (mirror the existing scale-calibration
   admin endpoint). Only then does a `valid_until` exist to gate on.
2. **Then the deriver:** add `derive_thermocouple_calibration_compliance` /
   `derive_moisture_meter_calibration_compliance` mirroring the density/scale derivers —
   in-date record required when enforced; inert + grandfathered when absent (legacy batches).
3. Fold all into the C10 unified gate in `credit_engine.py` alongside the existing signals.
4. **Scope honestly:** if you only have time/authority to wire the *scale + density* gates
   (which already have models) into issuance and defer thermocouple/moisture, that is a valid
   smaller Part — do that and list the deferred instruments, rather than shipping a deriver
   that reads a table that doesn't exist.

### STEP PR-3.3 — Tests
1. Pure derivers: enforced+missing → blocked; enforced+present → ok; unenforced → inert.
2. `credit_engine` wiring test: a batch missing required sampling/calibration is provisional
   with the right reason; a complete batch is not.
3. **CHECKPOINT:** backend suite green.

### PR-3 DoD
- [x] Under-sampled or uncalibrated-instrument batches are not issuable (reason-coded).
- [x] Every new gate: pure, tested (enforced/present/absent), grandfathers legacy rows.
- [x] Cadence/thresholds come from config, never hardcoded/invented.

**DONE — 2026-07-23, smaller scope taken per STEP PR-3.2.4's explicit
allowance.** `derive_sampling_compliance` (pure, 9 tests) wired into C10 via
a new config-driven `LcaParams.sampling_kg_per_lab_result` (default None =
inert/grandfathered), with a wiring test suite (3 tests) proving inert /
blocked / satisfied. Scale + density calibration gates were found ALREADY
wired into C10 from prior work — confirmed, not rebuilt.
**Deferred, listed explicitly:** thermocouple and moisture-meter calibration
enforcement — no model/table/registry endpoint exists for either instrument
in the schema (only `ScaleCalibration` and `BulkDensityTest` do); building
that data model is real, separate work and is NOT done here. Backend-only;
693 passed / 0 failed before and after.

**COMMIT:** `feat(backend): sampling-plan + all-instrument calibration issuance gates`

---

# PART PR-4 — Methodology as a first-class switch (CSI *and* Rainbow, for real)

**Why:** today every batch is gated by Rainbow's rules, computed with CSI-3.2 math, exported
as JSON+label — one path, two labels. This makes methodology select **gate-set + LCA params +
report**, per project, back-compat by default.

**Rail to reuse:** `RegistryConfig` (already per-project LCA params + `methodology_version`);
`_resolve_lca_config` in `credit_engine.py`; the two export services.

### STEP PR-4.1 — Methodology resolver (test-first, pure)
1. `tests/test_methodology.py`: pure `services/methodology.py::resolve_methodology(project)` →
   an enum/const (`CSI` | `RAINBOW`), defaulting to today's behavior (CSI-3.2 math + Rainbow
   gates) when a project has no explicit methodology, so **nothing changes for existing
   projects** (grandfather — assert this explicitly).
2. Pure `gate_set_for(methodology)` → the ordered list of C-gates that apply. Today's gates
   become the `RAINBOW` set; define the `CSI` set from CSI's actual requirements **only where
   a code gate already exists** — do NOT invent CSI rules; where CSI needs a gate we don't
   have, leave a `TODO(methodology)` and list it, don't fake it.

### STEP PR-4.2 — Route gating + export through the resolver
1. `credit_engine.py`: select the gate-set via `gate_set_for(resolve_methodology(project))`
   instead of the hardcoded Rainbow list. Default path must reproduce today's result exactly
   (regression-pin test: an existing batch's provisional reasons + credit are byte-identical).
2. `portal/routes.py` export route: dispatch to CSI vs Rainbow export by the resolved
   methodology (not a caller-supplied `{fmt}` alone — the methodology is the project's, the
   format must match it or 400).

### STEP PR-4.3 — Tests
1. Resolver: unset → default (grandfather); explicit CSI → CSI set; explicit Rainbow →
   Rainbow set.
2. **Regression pin:** a batch under the default methodology produces the exact same credit +
   reasons as before this Part (proves back-compat).
3. **CHECKPOINT:** backend suite green.

### PR-4 DoD
- [x] Methodology selects gate-set + LCA + report, per project; default = today's behavior,
      proven by a byte-identical regression pin.
- [x] No invented CSI rules — gaps are `TODO(methodology)`-listed, not faked.

**DONE — 2026-07-23.** `services/methodology.py` (pure, 9 tests):
`resolve_methodology` + `gate_set_for`. DEFAULT == RAINBOW's gate set
(regression pin, 4 wiring tests) — CSI excludes the Rainbow-labeled C10
extras (biomass/kiln/calibration/methane/PAH/sampling/plausibility) with a
`TODO(methodology)` in the module docstring, since none are confirmed
CSI-3.2 requirements; core corroboration (yield/temp/lab/moisture/
composite/delivery/buyer) still gates every methodology equally. Export
route now dispatches by resolved methodology (400 on mismatch), DEFAULT
projects keep free format choice (3 new tests). Backend-only;
709 passed / 0 failed before and after.

**COMMIT:** `feat(backend): methodology as a first-class switch (gate-set + LCA + report)`

---

# PART PR-5 — Day-start audit evidence (photo + video)

**Why:** R6 shipped the day-start lock as a checkbox; the incumbent captures facility photo +
walkthrough video. Add real evidence.

**⚠️ VERIFIED CONSTRAINT — the prerequisite the naive version misses.** R6's day-start
attestation lives **only in client SharedPreferences** (`day_start_service.dart`). There is
**NO server-side day-start entity/table/route** (`grep day_start` in `models.py`/`routers/`
→ nothing). So there is no `subject_uuid` to attach media to. You must FIRST promote the
day-start audit to a real server record, THEN attach media to it. Skipping PR-5.1a means
uploading media that references a subject that doesn't exist.

### STEP PR-5.1a — Backend: create the day-start audit record (prerequisite)
1. `models.py`: `class DayStartAudit(Base)` — `audit_uuid` (PK, client-generated str 36),
   `facility_id`/`facility_uuid`, `audit_date` (device-local calendar date), `device_id`
   (indexed), `created_at`. `UniqueConstraint(facility + audit_date)` — one audit per
   facility per day. No FK on facility (mirror the offline-first sibling pattern).
2. Migration via `alembic revision`; real `downgrade`.
3. Device-signed create endpoint `POST /api/v1/day-start-audits` (mirror
   `routers/dispatch.py`: `verify_signature`, client-generated `audit_uuid`, idempotent
   upsert on the unique key). Register in `app_factory.py`.
4. Tests (`tests/test_day_start_audit_endpoint.py`, mirror `test_dispatch_endpoint.py`):
   create happy path; idempotent same-day re-post; foreign-device rejected.
5. **CHECKPOINT:** backend suite green. NOW there's an `audit_uuid` to be a media subject.

### STEP PR-5.1b — Backend: accept the day-start subject on the media rail
1. `routers/media.py`: add `day_start_audit` to the allowed `subject_type` set; add
   `_assert_day_start_ownership` in `services/evidence.py` (mirror
   `_assert_dispatch_ownership`: load the `DayStartAudit`, confirm `device_id == caller`).
   Additive; batch/farmer/dispatch paths unchanged.
2. Tests (`tests/test_media_entity_scope.py`, extend): day-start media upload happy path;
   foreign-device rejected; back-compat unchanged.

### STEP PR-5.2 — App: submit the audit record, then capture photo (+ optional video)
1. `lib/services/day_start_service.dart`: on confirm, generate an `audit_uuid`, submit the
   `DayStartAudit` via a signed call (mirror `dispatch_service.dart`), and keep the existing
   SharedPreferences date-stamp for the offline gate. The `audit_uuid` is what media points at.
2. `lib/data/capture_types.dart`: add `dayStartFacilityPhoto`, `dayStartWalkthroughVideo`.
3. `day_start_attestation_screen.dart`: required facility-photo capture (`SecureCameraScreen`)
   + optional walkthrough video (`SecureCameraScreen(captureMode: SecureCaptureMode.video)`),
   routed through the R1 entity-media writer with `subjectType:'day_start_audit'`,
   `subjectUuid: <audit_uuid>`. Confirm stays disabled until the photo is captured.
4. Tests (`test/day_start_attestation_screen_test.dart`, extend): confirm blocked until photo
   present; captured media enqueues a day-start-scoped op with the audit_uuid.
5. i18n en+hi for the new strings.
6. **CHECKPOINT:** analyze clean; app + backend suites green.

### PR-5 DoD
- [x] A server-side `DayStartAudit` record exists (the missing prerequisite); media attaches
      to its `audit_uuid`, not to a phantom subject.
- [x] Day-start requires a facility photo (video optional), synced via the reused media rail.
- [x] Rail extension is additive; existing subjects unchanged. en+hi. Three suites green.

**DONE — 2026-07-23.** Backend: `DayStartAudit` model/migration/device-signed
endpoint (4 tests) + `day_start_audit` as a third media subject_type
(4 tests). App: facility picker (reusing `DispatchService.fetchFacilities`,
persisted) + mandatory facility photo/optional video via
`insertEntityMediaWithOutbox` scoped to the audit_uuid. Two scope decisions
made with the user mid-Part (confirmed, not unilateral): server submission
is best-effort/non-blocking (not connectivity-required like dispatch
transitions — a day-start gate must not brick the operator over a network
blip), and facility selection is an in-screen persisted picker rather than
a separate prerequisite Part. Backend 715 passed, flutter 390 passed,
0 failed either.

**COMMIT:** `feat: day-start audit photo/video evidence via the entity-media rail`

---

# PART PR-6 — Required quench video + density-test video

**Why:** quench is permanence-critical and density is fraud-sensitive; the incumbent requires
video at both. We already have `SecureCaptureMode.video` and the `quenching_video`/
`density_video` capture types.

### STEP PR-6.1 — Quench video required in the pyrolysis flow
1. `lib/ui/screens/pyrolysis_screen.dart`: at the quench stage, require a
   `quenching_video` capture (video mode) in addition to the existing quench photo. Gate
   `canEndBurn` on it (extend the pure gate + its test in `pyrolysis_end_burn_gate_test.dart`).
2. **CHECKPOINT:** pyrolysis gate tests green.

### STEP PR-6.2 — Density video required in the density flow
1. `lib/ui/screens/density_calibration_screen.dart`: require a `density_video` capture before
   submit. Wire through the media rail; block submit until present.
2. Test (`test/density_calibration_screen_test.dart`, extend): submit blocked until video.
3. **CHECKPOINT:** app suite green.

### PR-6 DoD
- [x] Quench and density each require their video; pure gates updated + tested.
- [x] Reused existing video capture + capture types; no new capture stack.

**DONE — 2026-07-23.** `canEndBurn` gates open kilns on `quenchVideoCaptured`;
`density_calibration_screen.dart` blocks submit until a `density_video` is
captured. **Correction vs the plan (found mid-Part, mirrors PR-5.1a):**
`BulkDensityTest` had no `device_id` column at all — added one (additive
migration), persisted it in `routers/density.py`, added
`_assert_density_test_ownership`, and extended the media rail with
`density_test` as a fourth subject_type. Backend 718 passed, flutter 391
passed, 0 failed either.

**COMMIT:** `feat(app): require quench + density-test video evidence`

---

# PART PR-7 — Make the capture-integrity gates shippable (not dormant)

**Why:** blur + geofence gates exist but `defaultValue:false` and are unverified in the field.
Do NOT flip defaults blindly. Make the ON-path tested + documented for staged rollout.

### STEP PR-7.1
1. Add tests proving the ON-path works end-to-end (blur below threshold blocks; geofence
   out-of-bounds trips) — some exist from E/R4; fill any gaps.
2. `docs/CAPTURE_GATE_ROLLOUT.md`: the calibration procedure (collect real field photos,
   tune `kBlurVarianceThreshold`) and the OFF→canary→on rollout order (§0.7.5). Leave
   defaults OFF; document the enable dart-defines.
3. **CHECKPOINT:** app suite green.

### PR-7 DoD
- [x] ON-path tested; rollout documented; defaults stay OFF until field-calibrated (honest).

**DONE — 2026-07-23.** Extracted `shouldRejectForBlur`/`geofenceWarningFor`
(pure, `enforced` as an explicit param) from `secure_capture_service.dart`'s
capture() pipeline so the ON-path — previously unexercised by any test,
since the dart-define consts are compile-time — is proven correct (7 new
tests). `docs/CAPTURE_GATE_ROLLOUT.md`: calibration procedure + OFF→canary→
full rollout order + exact dart-defines. No default flipped, no threshold
invented. App-only; flutter suite 398 passed, 0 failed.

**COMMIT:** `test+docs: capture-integrity gate on-path coverage + rollout runbook`

---

# PART PR-8 — Deployment hardening (⚠️ human-gated destructive steps)

**Agent may** do the non-destructive parts and PREPARE the destructive ones with exact
commands; **the human runs anything that rewrites history or touches prod.**

### STEP PR-8.1 — Secret hygiene (VERIFY current state first — do not assume it's broken)
**Current state (verified 2026-07-23):** `demo_tools/demo_secrets.bat` is **gitignored, NOT
tracked, and `git log --all -- demo_tools/demo_secrets.bat` shows it was never committed to
any branch.** Only `demo_secrets.example.bat` is tracked. So there is **nothing in history to
purge** — the earlier "secrets committed, rewrite history" concern does NOT apply. First
re-confirm this (state may have changed):
```bash
git ls-files demo_tools/ | grep -i secret          # expect ONLY demo_secrets.example.bat
git check-ignore demo_tools/demo_secrets.bat        # expect it to print (i.e. ignored)
git log --all --oneline -- demo_tools/demo_secrets.bat   # expect EMPTY (never committed)
```
1. **If all three confirm the clean state above:** no history rewrite needed. The only
   residual action is operational — if those local secret VALUES were ever shared/exposed
   outside git (chat, screenshare), rotate them. Note this in `docs/SECRET_ROTATION.md` and
   move on. Do NOT invent a history-purge for a file that was never committed.
2. **Only if the re-check shows it IS tracked/in-history:** then write the rotation +
   `git rm --cached` + gitignore + `git filter-repo`/BFG purge steps in
   `docs/SECRET_ROTATION.md` — **but DO NOT run the history rewrite or force-push.**
3. **Agent must NOT** commit real secrets or force-push under any branch of this.

### STEP PR-8.2 — Deploy checklist (doc)
1. `docs/DEPLOY_CHECKLIST.md`: hosted Postgres (`DATABASE_URL`), Android release signing,
   iOS per `IOS_BUILD_RUNBOOK.md`, required dart-defines (`SENTRY_DSN`, `DMRV_API_BASE_URL`,
   TLS trust), and which gates to enable per environment.

### PR-8 DoD
- [x] Secret state re-verified; history-purge only if the re-check actually shows tracking
      (current state: clean — nothing to purge). No destructive action by the agent.
- [x] Deploy checklist committed.

**DONE — 2026-07-23.** Re-ran all three verification commands — state
unchanged (clean, nothing to purge). `docs/SECRET_ROTATION.md` +
`docs/DEPLOY_CHECKLIST.md` committed. Docs-only; no code changed, no
destructive action taken.

**COMMIT:** `docs: secret-rotation + deploy checklist (destructive steps human-gated)`

---

# TIER 3 — Optional breadth (only when scale/geography forces it; one Part each, same rules)

Not production-gating. Build only on explicit election; each still gets its own test-first PR.
- **doc scanner** (ML Kit document scanner for ID/land/invoice) · app.
- **on-device PDF** (weight slips / consent) · app, pure builder + tests.
- **task system** (assign/track field work) · backend model + endpoints + app.
- **multi-country** (country field configs + UPI/bKash/M-Pesa) · schema + UI.
- **presigned-S3 media** (direct-to-S3 upload) · backend + sync-manager, keep two-phase commit.
- **sync-conflict state** (explicit divergence resolution) · sync engine.

---

## FINAL — after the elected Parts land
Full three-suite regression on the merged tree (not just per-Part):
```bash
cd backend && python -m pytest -q
flutter test
cd portal && npm test -- --run && npx tsc --noEmit && npm run build
```
Then: PR-C1/PR-C2 remain open (external), and issuance is real only once a verified batch
flows through the ledger into a serialized unit. Update `docs/PATH_TO_ISSUANCE.md` +
`docs/PRODUCT_REALITY_MAP.md` checkboxes. Do NOT push — the human does.
```
