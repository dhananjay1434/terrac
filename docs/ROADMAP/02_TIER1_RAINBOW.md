# Tier 1 — Rainbow-Compliant: "Methodology-Complete dMRV"

> **▶ Ready-to-run handoff:** a fully expanded, copy-paste-anchored execution prompt for this tier (every edit with exact code blocks, line anchors, test skeletons, commit plan, and traps) lives at [prompts/T1_EXECUTION_PROMPT.md](prompts/T1_EXECUTION_PROMPT.md). Give that file verbatim to the implementing engineer/agent.

> **Benchmark when this tier is green:** every reason string in the C10 compliance catalog (`server.py:1993-2030`) is *reachable* — no dormant derivers, no hardcoded `enforced=False`, no catalog entries that can never fire. Every Rainbow criterion is either **actively gating issuance** or is an **explicit, named, inert flag documented as awaiting Rainbow's own input** (cited factors / sign-off). A verifier can read `GET /api/v1/batches/{uuid}/compliance` and trust that "pass" means pass.
>
> Enforcement coverage moves from ~62% → ~100% of what is achievable without Rainbow externals.
>
> **Total effort: ~1–1.5 weeks.** Tasks T1.1–T1.4 are pure engineering. T1.5–T1.8 are blocked on Rainbow/methodology sign-off but their *code paths* get built and tested inert.

**Ground rules recap:** compliance only via the provisional model (never reject uploads); additive schema only; lab data admin-authenticated; kiln-conditional rules inert without explicit `kiln_type`.

---

## T1.1 — THE keystone: batch→project linkage (unblocks 3 dormant gates)

Everything dormant traces to one fact: `Batch` (models.py:289-335) has no `project_id`, so `recompute_batch_credit` cannot resolve *which* scale calibration or annual verification applies (admitted at server.py:858-861).

### T1.1a — Server schema

- **Where:** `backend/models.py` — `Batch` class; add after `device_id` (models.py:328):
  ```python
  # Rainbow linkage (T1.1): resolves project-scoped gates (scale calibration,
  # annual verification). Nullable — legacy batches predate the linkage and the
  # gates must stay inert for them (never gate spuriously).
  project_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
  scale_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
  ```
- **Migration:** new file `backend/alembic/versions/<hash>_batches_project_linkage.py`, `down_revision = "e1f2a3b4c5d6"` (current head). `upgrade()`: two nullable `add_column` + two `create_index`; `downgrade()` reverses. **Never** NOT NULL — legacy rows exist.

### T1.1b — API (additive, optional)

- **Where:** `BatchPayload` Pydantic model in `server.py` (the strict `extra="forbid"` model used by `POST /api/v1/batches`, defined near server.py:270-348).
- **What:** add
  ```python
  project_id: Optional[str] = Field(default=None, max_length=128)
  scale_id: Optional[str] = Field(default=None, max_length=128)
  ```
  and persist both in the batch-creation handler (server.py:1081-1247) next to the other payload fields. Old clients omit them → null → gates stay inert (backward compatible by construction).

### T1.1c — Client schema (build loop)

- **Where:** `lib/data/local/tables.dart` — add nullable `TextColumn get projectId` / `scaleId` to the biomass-sourcing/batch table; `lib/data/local/app_database.dart` — bump `schemaVersion` 22 → 23 with one `if (from < 23)` block using `addColumn` only; then `dart run build_runner build --delete-conflicting-outputs`; include both fields in the outbox JSON writer so they reach `POST /api/v1/batches`.
- **Config source:** the field app knows its project: add a `DMRV_PROJECT_ID` dart-define (same pattern as `DMRV_API_BASE_URL` in `lib/services/sync_queue_manager.dart:599`) and stamp it on batch creation. `scale_id` comes from the BLE scale pairing metadata if available, else null.
- **Test gotcha (documented past regression):** schema-shape tests must assert `greaterThanOrEqualTo(23)`, never `== 23`.

### T1.1d — Gate

- New `backend/tests/test_batch_project_linkage.py`: payload with/without `project_id` both 201; column persisted; legacy payload (no field) unchanged behavior. Full suite 262+ green; `flutter test` green.
- **Effort:** L (schema on both sides + codegen). **Blocked-by:** nothing.

---

## T1.2 — Wire the scale-calibration gate (kill dormant deriver #1)

- **Where:** `backend/server.py` `recompute_batch_credit`, in the C10 block (after the kiln check, server.py:882); deriver already exists and is unit-tested: `derive_scale_calibration_compliance` (corroboration.py:262-273); catalog entry `scale_calibration_expired` already at server.py:2024.
- **What:** insert:
  ```python
  # C8: the batch's weighing scale must have an in-date calibration.
  # Inert when the batch has no scale linkage (legacy batches / no scale_id).
  if batch.scale_id:
      _now = datetime.now(timezone.utc)
      _cal_ok_row = (
          await session.execute(
              select(ScaleCalibration.id).where(
                  ScaleCalibration.scale_id == batch.scale_id,
                  ScaleCalibration.valid_until.is_not(None),
                  ScaleCalibration.valid_until >= _now,
              )
          )
      ).first()
      _sc_ok, _sc_reason = derive_scale_calibration_compliance(_cal_ok_row is not None)
      if _sc_reason:
          c10_reasons.append(_sc_reason)
  ```
  Import `ScaleCalibration` in the models import block (server.py:49) and `derive_scale_calibration_compliance` in the corroboration import block (server.py:69).
- **Gate:** new tests in `test_project_registry_c8.py`: (a) batch with `scale_id` + expired-only calibration → `scale_calibration_expired` in `provisional_reasons`, batch provisional; (b) in-date calibration → reason absent; (c) batch without `scale_id` → reason absent (inert). Update the existing dormancy assertion that currently proves the reason never fires.
- **Effort:** M. **Depends on:** T1.1.

## T1.3 — Wire the annual-methane gate (kill dormant deriver #2)

- **Where:** same C10 block; deriver `derive_annual_methane_compliance` (corroboration.py:276-287, requires `methane_run_count >= 3`); catalog entry `missing_annual_methane` at server.py:2025. `AnnualVerification` is keyed `(project_id, year)` (models.py:262-267).
- **What:** insert after T1.2's block:
  ```python
  # C9: the batch's project must have a current-year methane verification (>=3 runs).
  # Inert when the batch has no project linkage.
  annual_verif = None
  if batch.project_id:
      _year = datetime.now(timezone.utc).year
      annual_verif = (
          await session.execute(
              select(AnnualVerification).where(
                  AnnualVerification.project_id == batch.project_id,
                  AnnualVerification.year == _year,
              )
          )
      ).scalar_one_or_none()
      _am_ok, _am_reason = derive_annual_methane_compliance(
          annual_verif.methane_run_count if annual_verif else None
      )
      if _am_reason:
          c10_reasons.append(_am_reason)
  ```
  (Keep `annual_verif` in scope — T1.4 and T1.6 reuse it.) **Year policy decision to record in REMEDIATION_LOG:** current-UTC-year vs batch-harvest-year — recommend harvest-timestamp year (`batch.harvest_timestamp.year`) since verification vintage should match production vintage; confirm with methodology owner in the task PR.
- **Gate:** extend `test_annual_verification_c9.py`: project-linked batch with no verification → `missing_annual_methane` present; with `methane_run_count=3` → absent; unlinked batch → absent. Delete/replace the existing assertions that prove dormancy (test_annual_verification_c9.py:121,144).
- **Effort:** M. **Depends on:** T1.1.

## T1.4 — Un-bypass the PAH gate (kill the hardcoded `enforced=False`)

- **Where:** `backend/server.py:890-895` — currently:
  ```python
  pah_measured = False  # no batch→project linkage yet; stays dormant unless closed
  _pah_ok, _pah_reason = derive_pah_compliance(
      kiln_type, pah_measured, enforced=False   # <-- the bypass
  )
  ```
  This is the most misleading code in the compliance layer: catalog entry `missing_pah` (server.py:2026) exists but can never fire.
- **What:** replace with:
  ```python
  # C9: PAH measurement is mandatory for closed kilns. Resolved from the batch's
  # project-year verification; inert (deriver returns passing) when the batch has
  # no project linkage or kiln_type isn't explicitly 'closed'.
  if batch.project_id and kiln_type == "closed":
      _pah_measured = bool(annual_verif and annual_verif.pah_measured)
      _pah_ok, _pah_reason = derive_pah_compliance(kiln_type, _pah_measured)
      if _pah_reason:
          c10_reasons.append(_pah_reason)
  ```
  Note: `derive_pah_compliance` (corroboration.py:~294) already implements the kiln-conditional logic; the outer `if` just avoids a pointless call. Default `enforced=COMPLIANCE_ENFORCED` now applies — the whole point.
- **Gate:** new tests: closed-kiln project-linked batch without `pah_measured=True` verification → `missing_pah` in reasons; with it → absent; open-kiln → absent; unlinked → absent.
- **Effort:** S. **Depends on:** T1.1, T1.3 (shares `annual_verif`).

---

## T1.5 — Transport emissions: cited factors → flip `TRANSPORT_EVENTS_ENFORCED` ⛔ blocked on Rainbow

- **Where:** `backend/emission_factors.py` — `TRANSPORT_EVENTS_ENFORCED = False` (line 27); placeholder factors lines 34-39 (`"diesel": 2.68  # TODO(cite): placeholder…`). Audit-only wiring already computes per-leg fuel CO2e into `lca_audit_json.transport_events` (server.py:842-854, 957-965) — the plumbing is DONE; only the numbers and the flip are missing.
- **What (when Rainbow supplies annex factors):**
  1. Replace every factor value; replace each `TODO(cite)` with the annex citation (document, table, unit). Confirm CNG unit (per-kg vs per-litre — flagged in the code comment line 39).
  2. Flip `TRANSPORT_EVENTS_ENFORCED = True`.
  3. Wire into the credit: in `recompute_batch_credit`, when enforced, pass `transport_fuel_co2e_kg` into the LCA total — recommended shape: extend `calculate_carbon_credit` (lca_engine.py:223-299) with optional `transport_fuel_co2e_kg: float = 0.0` added into the Step-8 deduction sum (lca_engine.py:193-217), replacing (not stacking with) the distance-heuristic penalty of Steps 5-6 **only per methodology sign-off** — record the decision in the audit dataclass either way.
  4. Update `test_transport_events_flow.py:48` which currently asserts `TRANSPORT_EVENTS_ENFORCED is False` — replace with tests of the credited path; add a golden-number regression for one known batch.
  5. Also fix (can do NOW, no sign-off needed): the three tests at test_transport_events_flow.py:30,36,46 carry `@pytest.mark.asyncio` on sync functions (12 pytest warnings) — remove the marks.
- **Gate:** credit changes only when flag flips; audit JSON carries citation metadata; regression numbers signed off by methodology owner in the PR.
- **Effort:** M once unblocked. **Blocked-by:** Rainbow annex factors + methodology sign-off.

## T1.6 — Wire C9 methane rate into the CH4 penalty ⛔ blocked on sign-off

- **Where:** `lca_engine.py` Step 7 (lines 172-190) currently uses the binary heuristic: compliant burn → 0.005 kg/t, else 30 kg/t. `AnnualVerification.methane_rate_g_per_kg` (models.py:269) is captured but unused.
- **What (on sign-off):** extend `calculate_carbon_credit` with optional `measured_ch4_rate_g_per_kg: Optional[float] = None`; when present, Step 7 uses the measured rate (converted to kg CO2e via GWP-100 = 28 unless methodology says otherwise — cite it) instead of the heuristic; `recompute_batch_credit` passes `annual_verif.methane_rate_g_per_kg` (from T1.3). Record `assumed_ch4` in the audit when falling back to the heuristic.
- **Gate:** unit tests for both paths; audit JSON distinguishes measured vs heuristic.
- **Effort:** M once unblocked. **Depends on:** T1.3. **Blocked-by:** methodology sign-off (GWP + substitution rule).

## T1.7 — Wire C9 conversion factor into C1 yield-conversion ⛔ blocked on sign-off

- **Where:** `derive_biomass_compliance` (corroboration.py, wired at server.py:865-869) emits `missing_conversion_factor` when method is `yield_conversion`, but the *actual* factor from `AnnualVerification.conversion_factor` (models.py:271) is never used to derive/validate `biomass_input_kg`.
- **What (on sign-off):** when `biomass_measurement_method == "yield_conversion"` and a project-year verification exists, derive expected biomass = `wet_yield_kg / conversion_factor`, cross-check against the reported `biomass_input_kg` (tolerance from methodology), and append a new catalog reason `biomass_conversion_mismatch` on violation. Add the reason to `_COMPLIANCE_CATALOG` (server.py:1993-2030) with its methodology section.
- **Effort:** M once unblocked. **Depends on:** T1.3.

## T1.8 — 1000-yr inertinite pathway election (project setting)

- **Where:** lab capture already lands `inertinite_pct`, `residual_corg_pct`, `ro_measurements_count` on `Batch` via `POST /api/v1/admin/lab` (server.py:660-715). No project-level election exists, so the alternate permanence branch has no trigger.
- **What:**
  1. New table `projects` (`backend/models.py` + migration): `project_id (unique)`, `permanence_pathway` enum-ish String (`"100yr"` default / `"1000yr"`), `payload_json`, timestamps. New admin endpoint `POST /api/v1/admin/project` following exactly the `admin/kiln` pattern (server.py:1797-1829): `X-Admin-Secret` + `hmac.compare_digest`, upsert on `project_id`.
  2. Deriver: `derive_inertinite_compliance(pathway, inertinite_pct, residual_corg_pct, ro_count)` in corroboration.py — when pathway is `"1000yr"`, require all three present and `ro_count >= 500` (methodology floor), else reason `missing_inertinite_data`; inert for `"100yr"`.
  3. Credit math for the 1000-yr branch itself stays **behind a flag** (same pattern as T1.5) until methodology sign-off; the *gate* (data completeness) can be enforced immediately.
- **Gate:** tests: 1000yr-elected project without Ro data → provisional with `missing_inertinite_data`; 100yr project unaffected. Catalog updated.
- **Effort:** L. **Depends on:** T1.1.

## T1.9 — Validate lab biochar-moisture ≥ 3 samples (small, do anytime)

- **Where:** `POST /api/v1/admin/lab` handler (server.py:660-715) accepts `biochar_moisture_samples_json` with no count check; methodology requires ≥3 samples.
- **What:** in the Pydantic model for the lab payload, add a validator: if `biochar_moisture_samples` is provided, `len() >= 3` else 422 `moisture_samples_min_3` (this is admin/lab data, not device evidence — rejecting at the API is correct here, per the lab-channel range-check precedent `lab_h_corg ∈ [0.1,1.5]`).
- **Gate:** test: 2 samples → 422; 3 → 200.
- **Effort:** S.

## T1.10 — Compliance report: expose gate provenance

- **Where:** `GET /api/v1/batches/{uuid}/compliance` (server.py:2033-2073) + `_COMPLIANCE_CATALOG` (server.py:1993-2030).
- **What:** after T1.2–T1.4, add to each checklist item an `enforcement` field: `"enforced" | "inert_no_linkage" | "awaiting_methodology"` so a verifier sees *why* a check passed (actually checked vs not applicable). Pure additive JSON.
- **Gate:** `test_compliance_gate_c10.py` asserts the new field for one batch of each kind.
- **Effort:** S. **Depends on:** T1.2–T1.4.

---

## ✅ Tier 1 exit criteria (the benchmark, verbatim)

- [ ] `grep -n "enforced=False" backend/server.py` → no hits in recompute.
- [ ] Every reason in `_COMPLIANCE_CATALOG` has a test that makes it fire.
- [ ] A project-linked, closed-kiln batch with no scale calibration, no annual verification, and no PAH goes provisional with exactly `scale_calibration_expired`, `missing_annual_methane`, `missing_pah` present.
- [ ] Legacy (unlinked) batches: zero behavior change — full regression suite green.
- [ ] The only non-enforced criteria remaining are T1.5/T1.6/T1.7 credit-math flips, each behind a named module flag with a `# blocked-by: Rainbow <citation needed>` comment.

**You may now honestly tell Rainbow/a verifier: "every dMRV criterion in the methodology is either enforced or explicitly awaiting your numbers — here is the endpoint that proves it per batch."**
