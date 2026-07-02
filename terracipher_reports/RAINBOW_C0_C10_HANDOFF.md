# Rainbow BiCRS Compliance — C0–C10 Full Plan & Handoff

**Purpose:** hand this to another engineer/AI to continue making the dMRV system
**methodology-complete** for the Rainbow BiCRS (Riverse) distributed-biochar standard. It records
(1) the operating rules, (2) exactly what is **already implemented** (C0–C3b, verified & gated), and
(3) implementation-ready specs for the **remaining** phases (C4–C10).

Source of truth for the methodology: `docs/dMRV Criteria Distributed Biochar.md`. Original design plan:
`terracipher_reports/RAINBOW_COMPLIANCE_PROMPT.md`. Per-phase build journal: `REMEDIATION_LOG.md`
(sections `## Phase C0` … `## Phase C3`). Prior security work: Phases 1–16 + R-series (same log).

---

## 0. Operating protocol (MUST follow — these are load-bearing)

### 0.1 Non-negotiable principles
1. **Additive & backward-compatible ONLY.** New tables, new **nullable** columns, new endpoints, and
   new **optional** Pydantic fields. Never rename/drop a column or make an existing field required in a
   way that breaks the shipped client.
2. **Compliance is enforced through the PROVISIONAL model, never by rejecting uploads.** A batch accepts
   partial data and stays `provisional=True` with a specific string reason until methodology-complete.
   The single mechanism is `backend/corroboration.py::assemble(...)` → `Corroboration.provisional` +
   `Corroboration.reasons`, persisted to `Batch.provisional` + `Batch.provisional_reasons` by
   `server.py::recompute_batch_credit(...)`. Issuance (final `lca_signature`) already requires
   `not provisional` (Phases 8-R/15-B). **Do NOT invent a parallel gate.**
3. **Lab / verification `[V]` data is authoritative → admin-authenticated, never device-asserted.** Reuse
   the `X-Admin-Secret` + `hmac.compare_digest` + range-check pattern from `ingest_lab_hcorg`
   (`POST /api/v1/admin/lab-hcorg`, Phase 8-R). Device payloads carry operational data only.
4. **Kiln-type-aware, and inert by default.** Rules that branch open/closed key off `kiln_type` (C0) and
   MUST be **inert when `kiln_type` is not explicitly `'open'`/`'closed'`**, so existing flows (which
   don't set it) never regress. See C3's derivers for the pattern.
5. **One phase = one gate = one journal entry.** No phase starts on a red gate.

### 0.2 The build/gate loop for a client-schema phase (do this every time)
1. Edit `lib/data/local/tables.dart` (add columns/table) **and** bump `AppDatabase.schemaVersion` by
   exactly 1 in `lib/data/local/app_database.dart`, adding exactly one `if (from < N)` block in
   `onUpgrade` that only `addColumn`/`createTable`. Update the schema-history comment header in
   `tables.dart`.
2. Update the relevant Drift writer (payload map + companion). Writers:
   `insertBiomassSourcingWithOutbox` (app_database.dart), `pyrolysis_writer.dart`,
   `yield_end_use_writers.dart`, `insertMoistureReadingWithOutbox` (app_database.dart).
3. **Regenerate Drift code (REQUIRED — the app won't compile otherwise):**
   `dart run build_runner build --delete-conflicting-outputs` (≈20–60 s here; exit 0 expected). Confirm
   the new identifier appears in `lib/data/local/app_database.g.dart`.
4. Server: extend the strict Pydantic model (`extra="forbid"`, so new fields MUST be declared) and, if a
   real (non-payload_json) column is needed, add it to `backend/models.py` + a **reversible** Alembic
   migration (copy an existing one; set `down_revision` to the current head).
5. Wire compliance in `corroboration.py` (pure function) + `recompute_batch_credit` + `assemble`.
6. **Gate:** `cd backend && python -m pytest -q --timeout=60 --timeout-method=thread` → **0 new failures**
   vs baseline; `flutter analyze` → 0 errors; `flutter test` → all pass; if a migration was added,
   `alembic upgrade head → downgrade base → upgrade head` on an isolated aiosqlite DB (path must be
   **space-free** — the repo path has spaces; use `mktemp`). `ruff format` + `dart format` touched files.
   Journal `## Phase Cx` in `REMEDIATION_LOG.md`.

### 0.3 Known baselines (as of C3b complete)
- Backend `pytest`: **208 passed, 1 skipped, 1 failed**. The 1 failure — `test_p0_21_hmac_secret::
  test_server_refuses_to_import_without_hmac_secret` — is a **documented pre-existing** import-isolation
  artifact, NOT a regression. "0 new failures" = only this one remains.
- `flutter test`: **149 passed, 2 skipped**. `flutter analyze`: **25 issues, 0 errors** (all info/warn in
  throwaway/legacy files).
- Client Drift `AppDatabase.schemaVersion` = **19**. Alembic head = **`f6a7b8c9d0e1`**.

### 0.4 Environment caveats (bit us already)
- **Untracked `New folder/` (and `uploaded/`, `scratch/`) duplicate cruft can reappear** on session
  interruptions and pollute `flutter analyze` with 100+ phantom errors *inside the duplicate*. It is
  NOT the real app. `analysis_options.yaml` now `exclude`s these; if analyze still explodes, `rm -rf
  "New folder"` and confirm the real app is clean with `flutter analyze 2>&1 | grep 'error' | grep -v 'New folder'`.
- Two hygiene tests (`test_hardening.py::test_p0_17_*`, `::test_p1_20_*`) were retargeted to the real
  `backend/db.py` / repo-root `.gitignore` (they used to point at the duplicate).
- **Commit discipline:** the tree currently carries Phases 15, 16 + C0–C3b **uncommitted** (5 Drift
  migrations, 3 Alembic migrations, regenerated `.g.dart`). Strongly recommend committing per-phase
  before continuing. Commit message convention ends with the Co-Authored-By trailer.

### 0.5 The corroboration/provisional model (the spine you extend each phase)
`Batch.provisional_reasons` currently can contain (all emitted by `corroboration.assemble`):
`wet_yield_uncorroborated`, `min_temp_uncorroborated`, `transport_uncorroborated`, `assumed_h_corg`,
`attestation_unverified`, `insufficient_moisture_samples`, `missing_pyrolysis_photos`,
`flame_height_out_of_range`, `missing_ignition_energy`. Each new compliance rule adds a pure
`derive_*` function + an `assemble(...)` keyword param (default = passing/inert) + one `reasons.append`.
`recompute_batch_credit` computes the inputs (from evidence rows / `tel_payload` / `batch` columns) and
passes them to `assemble`; it runs on batch create AND from every evidence endpoint via
`_recompute_if_batch_exists`, so credit/compliance converges as data arrives.

---

## PART A — ALREADY IMPLEMENTED (C0–C3b) — ground truth, do not redo

### C0 — Kiln type/id  ✅
- Client: `PyrolysisTelemetry.kilnType` (`'open'|'closed'`), `kilnId` (nullable). schemaVersion→16.
- Server: `TelemetryPayload.kiln_type: Optional[Literal["open","closed"]]`, `kiln_id`. Persisted in the
  telemetry `payload_json` (side tables store a JSON blob; **no server migration**).
- Writer: `pyrolysis_writer.dart` params `kilnType`/`kilnId`.

### C1 — Biomass input amount + method  ✅
- Client: `BiomassSourcing.biomassInputKg`, `biomassMeasurementMethod`. schemaVersion→17.
- Server: `BatchPayload.biomass_input_kg` (`ge=0,le=1e6`), `biomass_measurement_method:
  Literal["direct_weigh","yield_conversion"]`. Persisted on **`Batch`** (real columns). Alembic
  **`e5f6a7b8c9d0`**. `create_batch` sets them.
- Writer: `insertBiomassSourcingWithOutbox` params.
- Compliance reason wiring deferred to **C10** (data capture only).

### C2 — Multi-sample moisture  ✅ (biggest gap closed)
- Client: new table **`MoistureReadings`** (`readingUuid`, `batchUuid`, `moisturePercent`, `sequence`,
  `sandboxPath`, `sha256Hash`, `createdAt`; unique `{readingUuid}` and `{batchUuid,sequence}`).
  Registered in `@DriftDatabase`. schemaVersion→18. Writer `insertMoistureReadingWithOutbox`
  (`targetTable 'moisture_readings'`); the photo rides the existing signed two-phase `/media` path.
  `kEndpointByTable` maps `moisture_readings → moisture`.
- Server: `MoistureReading` model (`batch_uuid` indexed, **not unique** — many per batch);
  `MoisturePayload` (strict) + `POST /api/v1/moisture` (signed via `verify_signature`), then
  `_recompute_if_batch_exists`. Alembic **`f6a7b8c9d0e1`**.
- Compliance: `derive_moisture_compliance(photographed_count, biomass_input_kg)` → compliant iff
  `count >= max(10, ceil(biomass/100))`. `assemble(moisture_ok=...)` → `insufficient_moisture_samples`.
  `recompute` counts moisture rows whose payload has a `sha256_hash` (photographed).

### C3 / C3b — Pyrolysis evidence + ignition energy  ✅ (kiln-conditional)
- Client: `PyrolysisTelemetry.flameHeightM`, `ignitionEnergyType`, `ignitionEnergyAmount` (nullable).
  schemaVersion→19. Writer params. **No server migration** (read from `tel_payload`).
- Server: `TelemetryPayload.flame_height_m` (`ge=0,le=5`), `ignition_energy_type`, `ignition_energy_amount`.
- Compliance: `derive_pyrolysis_photo_compliance(kiln_type, smoke_evidence, flame_height_m)` →
  `(photos_ok, flame_height_ok)`; open-kiln requires photographed stages
  `{"flame_curtain","quenching","flame_height"}` (`corroboration.REQUIRED_OPEN_KILN_STAGES`) AND
  `flame_height_m < 0.5` (`MAX_OPEN_KILN_FLAME_HEIGHT_M`). `derive_ignition_compliance(kiln_type,
  ignition_energy_type)` → closed-kiln requires ignition energy. **Inert unless kiln_type is open/closed.**
  Reasons: `missing_pyrolysis_photos`, `flame_height_out_of_range`, `missing_ignition_energy`.

---

## PART B — REMAINING (C4–C10) — implementation-ready specs

> Each follows the §0.2 loop. Bump schemaVersion in order (next is **20**). Set each new Alembic
> `down_revision` to the then-current head (starts at `f6a7b8c9d0e1`). Add compliance as a pure deriver
> + `assemble` param + reason. Add unit + flow tests. Gate. Journal.

### C4 — Site Composite Pile sub-sample  `[per-run]`
**Requirement:** biochar sub-sample set aside, with date/time, location (GPS), **kiln ID/QR**, **batch
ID/QR**, photos.
- Client: new table `CompositePileSample(id, sampleUuid, batchUuid FK, sampledAt, latitude, longitude,
  kilnQr, batchQr, sandboxPath, sha256Hash)`; register in `@DriftDatabase`; schemaVersion→20;
  `createTable` migration. Writer `insertCompositePileSampleWithOutbox` (photo via signed `/media`);
  `kEndpointByTable` add `composite_pile_samples → composite-sample`.
- Server: `CompositePileSample` model (`sample_uuid` unique, `batch_uuid` indexed);
  `CompositeSamplePayload` (strict, signed) + `POST /api/v1/composite-sample` → persist +
  `_recompute_if_batch_exists`. Alembic migration (create table).
- Compliance: `derive_composite_sample_compliance(exists: bool)` → reason `missing_composite_sample`.
  `recompute` checks `select(CompositePileSample).where(batch_uuid==buid)` exists.
- Tests: post sample → reason cleared; absent → present; QR/photo round-trip.

### C5 — Delivery records + buyer identity  `[per-batch]`
**Requirement:** delivery tracking (date, amount, batch id) + **buyer/user name + contact**.
- Client: add nullable `deliveryDate`, `deliveredAmountKg`, `buyerName`, `buyerContact` to
  `EndUseApplication` (+ `insertEndUseWithOutbox` params). schemaVersion→21. (PII lives in the SQLCipher
  DB and is covered by `secureWipe`.)
- Server: extend `ApplicationPayload` with the four **optional, length-bounded** fields; persist in
  `end_use_application.payload_json` (no `Batch` column needed unless C10 wants to read them — it reads
  the application payload via `recompute`, so keep in payload_json).
- Compliance: `derive_delivery_compliance(app_payload)` → reasons `missing_buyer_identity`,
  `missing_delivery_record`. `recompute` already loads `app_row`; read fields from `app_payload`.
- Tests: application with buyer/delivery → reasons cleared; absent → present.

### C6 — Transport events (biomass + biochar)  `[per-event]`  ⚠ TOUCHES CREDIT MATH
**Requirement:** per transport event — **distance, weight, vehicle type, fuel consumed**, separately for
**biomass** and **biochar**.
- Client: new table `TransportEvent(id, eventUuid, batchUuid FK, material('biomass'|'biochar'),
  distanceKm, weightKg, vehicleType, fuelType, fuelAmount, occurredAt)`; schemaVersion→22; writer;
  `kEndpointByTable` add `transport_events → transport`.
- Server: `TransportEvent` model (`event_uuid` unique, `batch_uuid` indexed — **many per batch**);
  `TransportEventPayload` (strict, signed) + `POST /api/v1/transport` → persist + recompute.
- **LCA:** in `recompute_batch_credit`, sum fuel-based transport emissions from the events
  (`fuel_amount × emission_factor`) and feed the LCA instead of / in addition to the GPS-derived
  `transport_distance_km`. **Keep the GPS haversine as an under-reporting cross-check** (reuse the
  Phase-9 idea: flag if reported transport ≪ GPS distance). **Emission factors MUST come from the
  Rainbow methodology annexes — do not invent constants; put them in one audited config module (e.g.
  `backend/emission_factors.py`) and cite the source.**
- Compliance: reason `missing_transport_events` until ≥ the biochar-delivery event exists.
- Tests: fuel→emissions unit; multiple events per batch; credit reflects transport; GPS-vs-reported
  cross-check flags under-reporting. **Review credit changes carefully; re-run all LCA/corroboration tests.**

### C7 — Per-batch lab results via authenticated channel  `[V]`
**Requirement `[V]`:** organic **Corg** (elemental), biochar moisture (≥3 samples), dry bulk density,
inertinite + residual Corg (1000-yr pathway, ≥500 Ro).
- **Corg is currently a species constant** (`lca_engine.CORG_TABLE`) — a methodology-integrity gap of the
  same class as the H:Corg hole. Fix: accept lab Corg on an admin channel and prefer it.
- Server: widen the Phase-8-R admin lab endpoint. Add `POST /api/v1/admin/lab` (keep `/admin/lab-hcorg`
  as a back-compat alias so its tests pass) accepting `LabResultsRequest` (admin-auth, range-checked):
  `lab_h_corg`, `organic_carbon_pct`, `biochar_moisture_samples: list[float]` (`min_length=3`),
  `dry_bulk_density`, `inertinite_pct`, `residual_corg_pct`, `ro_measurements_count`. Persist on `Batch`
  (new nullable columns + Alembic migration).
- LCA: `calculate_carbon_credit` uses lab `organic_carbon_pct` when present, else falls back to
  `CORG_TABLE` **and marks provisional** (`assumed_corg`) — mirror the H:Corg provisional pattern. For the
  1000-yr pathway, require inertinite/Ro or reason `missing_inertinite_data`.
- Client: none (lab data never comes from the device).
- Tests: admin sets Corg → credit uses it + `assumed_corg` cleared; out-of-range → 422; non-admin → 401;
  `<3` moisture samples → 422; 1000-yr pathway w/o Ro → provisional.

### C8 — Project registry (once / on change)  `[admin]`
**Requirement:** kiln material/weight/lifetime; operator training records; supervisor site-visit reports;
scale calibration proof; quality-oversight report (per verification).
- Server: admin-authenticated tables + endpoints (a project console, NOT the per-run mobile app):
  `kilns(kiln_id, material, weight_kg, lifetime_years, kiln_type)`, `operator_training`,
  `supervisor_visits`, `scale_calibrations`. Reuse signed-media for report artifacts. Alembic migrations.
- Compliance: a batch's `kiln_id` must reference a registered kiln with in-date scale calibration, else
  reasons `unregistered_kiln` / `scale_calibration_expired`.
- Tests: register kiln → `unregistered_kiln` clears; expired calibration → provisional.

### C9 — Annual verification inputs  `[V][admin]`
**Requirement `[V]` (annual/independent):** methane emission rate (3 runs), PAH/heavy metals (closed-kiln
PAH mandatory), biomass leakage assessment, biomass→biochar conversion factor, dry bulk density per site.
- Server: admin endpoints + tables keyed by `(project/site, year)`; store signed report artifacts. The
  **methane rate** feeds the CH₄ penalty (currently modeled from telemetry) and the **conversion factor**
  feeds C1's `yield_conversion` method.
- Compliance: a batch in a period lacking current methane / (closed-kiln) PAH → `missing_annual_methane`
  / `missing_pah`.

### C10 — Unified issuance compliance gate  `[capstone]`
- Fold ALL per-phase reasons into one place. `assemble` already aggregates the corroboration reasons;
  extend it (or add `evaluate_compliance(batch, evidence)`) so `provisional == (reasons != [])` reflects
  full methodology completeness. Wire the C1 biomass reason (`missing_biomass_input` /
  `missing_conversion_factor`) here.
- Deliverable: `GET /api/v1/batches/{uuid}/compliance` (admin) returning the ordered reason list + a
  human-readable checklist mirroring the methodology sections (project / per-run / per-batch / per-event /
  lab), so a Project Developer sees exactly what's missing per batch.
- Tests: a fully-populated batch (all C1–C9 data) → `provisional False`, empty reasons, signed; each
  missing datum → its specific reason present and unsigned. Write a `## Rainbow Compliance — Final` block
  mapping every methodology line to its enforcing test.

---

## Sequencing
C4 → C5 → C6 (credit-math; most care) → C7 (closes the Corg-constant integrity gap) → C8 → C9 → C10.
Each independently mergeable; the app stays fully working (new data optional until its reason is enforced).

## Do-not-touch / dependencies
- Do not invent emission factors, GWP values, or the 0.4 H:Corg tier boundary — source them from the
  Rainbow annexes; the 0.4 cliff is flagged to the methodology owner (see Phase 15-D).
- The 1000-yr inertinite pathway is a project election — gate behind C8 project settings.
- Security epics still open (separate track): real Play Integrity/DeviceCheck attestation
  (`server._ATTESTATION_ENFORCED`), hardware-bound non-extractable device key. See `FINDINGS_BACKLOG.md`.
