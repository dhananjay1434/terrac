# Rainbow BiCRS Compliance — Remediation Plan (Phases C1–C10)

**Author's framing (Head of Engineering):** the security remediation (Phases 1–16) made the dMRV
pipeline *trustworthy*. This plan makes it *methodology-complete* — i.e. able to capture every data
point the **Rainbow BiCRS / Riverse methodology** (`docs/dMRV Criteria Distributed Biochar.md`) requires
for issuance. We do it **additively, one requirement-cluster at a time, without breaking a single
existing flow.** Each phase is independently shippable and gated.

## Non-negotiable engineering principles (apply to every phase)
1. **Additive & backward-compatible only.** New tables, new **nullable** columns, new endpoints, and
   new **optional** fields on the strict Pydantic models. **Never** rename/drop a column or change a
   field's required-ness in a way that breaks the shipped client. Drift migrations are cumulative
   `if (from < N)` blocks that only `addColumn`/`createTable`.
2. **Bump `schemaVersion` by exactly 1 per phase** and add exactly one `if (from < N)` block; update the
   `tables.dart` header history (kept honest in Phase 13). Verify `migration_test.dart` (v1→latest) after
   every phase.
3. **Compliance is enforced through the existing PROVISIONAL model, not by rejecting uploads.** A batch
   accepts partial data and stays `provisional` with a specific reason (e.g. `insufficient_moisture_samples`)
   until methodology-complete. This reuses `corroboration.assemble` + `provisional_reasons` (Phases 7-R/8-R)
   — do NOT invent a parallel gate. Issuance already keys on `provisional`.
4. **Lab / verification `[V]` data is authoritative → admin-authenticated, never device-asserted.** Reuse
   the `X-Admin-Secret` + range-checked pattern from `ingest_lab_hcorg` (Phase 8-R). Device payloads carry
   operational data only.
5. **One phase = one gate.** Backend baseline: 195 passed / 1 skipped / 1 pre-existing failure
   (`test_p0_21_hmac_secret`). Client baseline: `flutter test` 149 / 2 skipped; `flutter analyze` 34 / 0
   errors. 0 new failures. `ruff` + `dart format` at the end. Migration up/down/up clean. Journal each
   phase in `REMEDIATION_LOG.md`.
6. **Kiln-type aware.** The methodology branches open- vs closed-kiln. Land C0 first so later phases can
   condition on it.

## Compliance matrix (requirement → current → phase)
| Methodology requirement | Frequency | Current state | Phase |
|---|---|---|---|
| Open vs closed kiln type | project | not modeled | **C0** |
| Biomass input **amount** + method (weigh / conversion) | per run | only species + biochar yield | **C1** |
| Moisture ≥1/100 kg, **min 10/run, each photo'd** | per run | single `moisture_percent` + 1 photo | **C2** |
| Temperature curve | per run | ✅ `temperature_readings` | done |
| Pyrolysis photos: flame curtain / quenching / **flame height <0.5 m** (open) | per run | generic 4 `smoke_evidence` | **C3** |
| Ignition energy inputs (closed only) | per run | not modeled | **C3b** |
| Mass/volume fresh biochar | per run | ✅ `yield_metrics` | done |
| Site Composite Pile sub-sample (kiln/batch QR, GPS, photos) | per run | not modeled | **C4** |
| Volume delivered + spreading GPS | per batch | ✅ `end_use_application` | done |
| Delivery tracking (date, amount, batch id) + **buyer name/contact** | per batch | absent | **C5** |
| Transport **events**: distance, weight, vehicle, fuel — biomass & biochar | per event | single derived `transport_distance_km` | **C6** |
| Lab H/Corg `[V]` | per batch | ✅ admin channel (8-R/15D) | done |
| Lab **organic carbon (Corg)** `[V]` | per batch | **species constant** (`CORG_TABLE`) | **C7** |
| Lab biochar moisture (≥3), dry bulk density, inertinite/Ro `[V]` | per batch | absent | **C7** |
| Project registry: kiln material/weight/lifetime, operator training, supervisor visits, scale calibration | once/annual | absent | **C8** |
| Annual `[V]`: methane rate, PAH/heavy metals, leakage, conversion factor, bulk density | annual | absent | **C9** |
| Per-batch **issuance compliance gate** | — | partial (provisional) | **C10** |

---

## 0. Anti-hallucination protocol
Verify each "Current state" (grep/Read) before editing; identifiers are quoted from real code. Client
schema: `lib/data/local/tables.dart` (+ `app_database.dart` `onUpgrade`, `schemaVersion`). Server: side
tables (`system_metadata`, `pyrolysis_telemetry`, `yield_metrics`, `end_use_application`) store a
`payload_json` blob keyed by uuid — so adding fields server-side is mostly extending the strict Pydantic
model (Phase 11) + reading the new key in `recompute_batch_credit`/corroboration. `Batch` holds the
derived, credit-bearing columns.

---

## Phase C0 — Kiln type + kiln registry foundation  `[schema]`
**Why first:** open/closed kiln changes which data is required (C3/C3b/C9). Land the dimension now.
**Client:** new nullable `kilnType` (`'open'|'closed'`) + `kilnId` on `PyrolysisTelemetry` (or a
`system_metadata`-level field). Drift: `schemaVersion 15→16`, `if (from<16) addColumn(...)`.
**Server:** add `kiln_type`/`kiln_id` optional fields to `TelemetryPayload`; persist in `payload_json`.
**Compliance:** none yet (dimension only).
**Tests:** payload with `kiln_type` persists; missing → still accepted (nullable). Migration v1→16 green.
**Gate:** standard.

---

## Phase C1 — Biomass input amount + measurement method  `[per-run]`
**Requirement:** "Type and amount of biomass input (direct weighing or yield conversion ratio)."
**Current:** `BiomassSourcing` has `feedstockSpecies` (type) but no biomass **mass**; only biochar
`wet_yield_weight_kg` exists on `yield_metrics`.
**Client (`tables.dart` + writer `insertBiomassSourcingWithOutbox`):** add nullable
`biomassInputKg: real().nullable()` and `biomassMeasurementMethod: text().nullable()`
(`'direct_weigh'|'yield_conversion'`). Drift v16→17. Extend the payload map in the writer.
**Server:** add `biomass_input_kg`, `biomass_measurement_method` to the batch payload model
(`BatchPayload`, **Optional**) OR — since biomass is a sourcing concept — to a sourcing field on the
batch payload. Persist on `Batch` (new nullable columns + migration).
**Compliance (C10 hook):** if `biomass_input_kg` is null AND method is `direct_weigh`, add reason
`missing_biomass_input`. If `yield_conversion`, require an annual conversion factor (C9) — else
`missing_conversion_factor`.
**Tests:** batch with biomass amount persists + is retrievable; absent → provisional reason present.
**Gate:** standard + migration.

---

## Phase C2 — Multi-sample moisture capture  `[per-run]`  (highest-value data gap)
**Requirement:** handheld meter, **≥1 reading per 100 kg of biomass, min 10 per run, each photo uploaded.**
**Current:** `BiomassSourcing.moisturePercent` (single) + one `photoPath`.
**Client:** new table `MoistureReadings(id, batchUuid FK, readingUuid, moisturePercent, sequence,
sandboxPath, sha256Hash, createdAt)` with a `{batchUuid, sequence}` unique key; a writer
`insertMoistureReadingWithOutbox` (atomic domain-row + outbox, reuse the pattern) that also enqueues each
reading photo through the existing signed `/media` channel (Phase 15-A). Keep `moisturePercent` on
`BiomassSourcing` as the summary (mean/first) for backward compatibility — do NOT remove it. Drift v17→18
`createTable(moistureReadings)`.
**Server:** new `/api/v1/moisture` endpoint (strict `MoisturePayload`, `extra="forbid"`, signed via
`verify_signature`) OR fold into a `moisture_readings` array on the batch/sourcing payload (array
`max_length` bounded, Phase 11-R style). Persist rows keyed by `reading_uuid`.
**Compliance:** `derive_moisture_compliance(readings, biomass_input_kg)` (pure, in `corroboration.py`):
compliant iff `len(readings) >= max(10, ceil(biomass_input_kg/100))` and each reading has a photo. Else
reason `insufficient_moisture_samples`. Keeps batch provisional.
**Tests:** unit (compliance thresholds incl. the 100 kg rule); flow (10 readings → compliant; 9 →
provisional); each reading photo signs through media.
**Gate:** standard + migration.

---

## Phase C3 — Pyrolysis evidence taxonomy (open-kiln)  `[per-run]`
**Requirement (open-kiln):** photographs of **flame curtain**, **quenching**, and **flame height <0.5 m**.
**Current:** `smoke_evidence` is a generic list of 4 `{stage, sha256}`; `media_captures.captureType`
free-text.
**Client:** define a controlled `captureType` vocabulary constant (`flame_curtain`, `quenching`,
`flame_height`, plus existing `smoke_*`); add nullable `flameHeightM: real().nullable()` on
`PyrolysisTelemetry`. The capture UI tags each photo with its stage. Drift v18→19.
**Server:** `TelemetryPayload` gains optional `flame_height_m` (`ge=0.0, le=5.0`) and the smoke/pyro
evidence entries keep `{stage, sha256}` but `stage` is validated against the vocabulary.
**Compliance (open-kiln only, keyed off C0 `kiln_type`):** require the three tagged photos AND
`flame_height_m < 0.5`; else reasons `missing_pyrolysis_photos` / `flame_height_out_of_range`.
**Tests:** open-kiln batch missing quenching photo → provisional; `flame_height_m >= 0.5` → provisional;
closed-kiln batch → these checks skipped.
**Gate:** standard + migration.

### Phase C3b — Ignition energy inputs (closed-kiln only)  `[per-run]`
Add optional `ignition_energy_type` / `ignition_energy_amount` (incl. syngas combustion) to
`TelemetryPayload` + `Batch`; required only when `kiln_type == 'closed'` (else reason
`missing_ignition_energy`). Small; ship with or right after C3.

---

## Phase C4 — Site Composite Pile sub-sample  `[per-run]`
**Requirement:** biochar sub-sample set aside, with date/time, location, **kiln ID/QR**, **batch ID/QR**,
photos.
**Client:** new table `CompositePileSample(id, batchUuid FK, sampleUuid, sampledAt, latitude, longitude,
kilnQr, batchQr, sandboxPath, sha256Hash)` + writer + signed media for the photo. Drift v19→20.
**Server:** `/api/v1/composite-sample` (strict, signed) persisting by `sample_uuid`.
**Compliance:** reason `missing_composite_sample` until one exists for the batch.
**Tests:** create sample → compliance clears; QR fields round-trip; photo signs through media.
**Gate:** standard + migration.

---

## Phase C5 — Delivery records + buyer identity  `[per-batch]`
**Requirement:** volume delivered (have), spreading GPS (have), **delivery tracking (date, amount, batch
id)**, **buyer/user name + contact**.
**Client (`EndUseApplication` + `insertEndUseWithOutbox`):** add nullable `deliveryDate`,
`deliveredAmountKg`, `buyerName`, `buyerContact`. Drift v20→21. (PII note: these live in the SQLCipher-
encrypted DB already; ensure they are covered by `secureWipe` — they are, it wipes the whole table.)
**Server:** extend `ApplicationPayload` with the four optional, length-bounded fields (Phase 11-R style);
persist in `payload_json`.
**Compliance:** reason `missing_buyer_identity` / `missing_delivery_record` until present.
**Tests:** application with buyer/delivery persists; absent → provisional reasons.
**Gate:** standard + migration.

---

## Phase C6 — Transport events (biomass + biochar)  `[per-event]`
**Requirement:** per transport event — **distance, weight, vehicle type, fuel consumed**, separately for
**biomass** and **biochar**.
**Current:** a single derived `transport_distance_km` (from application GPS haversine).
**Client:** new table `TransportEvent(id, batchUuid FK, eventUuid, material('biomass'|'biochar'),
distanceKm, weightKg, vehicleType, fuelType, fuelAmount, occurredAt)` + writer. Drift v21→22.
**Server:** `/api/v1/transport` (strict `TransportEventPayload`, signed) persisting by `event_uuid`
(multiple events per batch — NOT unique on batch_uuid).
**LCA integration:** `recompute_batch_credit` sums fuel-based transport emissions from the events
(fuel × emission factor) instead of / in addition to the GPS-derived distance. Keep the GPS haversine as a
**cross-check** (flag if reported transport ≪ GPS distance — reuse the Phase-9 under-reporting guard idea).
**Compliance:** reason `missing_transport_events` until at least the biochar-delivery event exists.
**Tests:** unit for fuel→emissions; multiple events per batch persist; credit reflects transport emissions;
GPS-vs-reported cross-check flags under-reporting.
**Gate:** standard + migration. **This is the one that touches the credit math — review carefully.**

---

## Phase C7 — Per-batch lab results via authenticated channel  `[V]`
**Requirement `[V]`:** organic **Corg** (elemental), biochar moisture (≥3 samples), dry bulk density,
inertinite + residual Corg (1000-yr pathway, ≥500 Ro).
**Current:** `Corg` is a **species constant** (`CORG_TABLE`) — a methodology-integrity gap of the same
class as the H:Corg hole. Lab moisture/bulk-density/inertinite absent.
**Server (extend the Phase-8-R admin lab channel):** widen `/api/v1/admin/lab-hcorg` → `/api/v1/admin/lab`
accepting `LabResultsRequest` (admin-authenticated, range-checked): `lab_h_corg`, `organic_carbon_pct`,
`biochar_moisture_samples: list[float] (min_length=3)`, `dry_bulk_density`, `inertinite_pct`,
`residual_corg_pct`, `ro_measurements_count`. Persist on `Batch` (new nullable columns + migration).
**LCA:** `calculate_carbon_credit` uses **lab `organic_carbon_pct` when present**, else falls back to
`CORG_TABLE` **and marks the batch provisional** (reason `assumed_corg`) — exactly mirroring the H:Corg
provisional pattern. For the 1000-yr pathway, require inertinite/Ro or reason `missing_inertinite_data`.
**Client:** none (lab data never comes from the device).
**Tests:** admin sets Corg → credit uses it + `assumed_corg` cleared; out-of-range → 422; non-admin → 401;
`<3` moisture samples → 422; 1000-yr pathway without Ro → provisional.
**Gate:** standard + migration. Deprecate the old `/admin/lab-hcorg` route as an alias (don't break 8-R tests).

---

## Phase C8 — Project registry (once / on change)  `[admin]`
**Requirement:** kiln material/weight/lifetime; operator training records; supervisor site-visit reports;
scale calibration proof; quality-oversight report (per verification).
**Server:** new admin-authenticated tables + endpoints (not the mobile per-run app): `kilns`
(material, weight_kg, lifetime_years, kiln_type), `operator_training`, `supervisor_visits`,
`scale_calibrations`. Alembic migrations. These are low-frequency; a document/attestation upload
(reuse signed media) per record.
**Compliance:** a batch's kiln must reference a registered `kiln_id` with valid scale calibration in date,
else reasons `unregistered_kiln` / `scale_calibration_expired`.
**Tests:** register kiln (admin) → batch referencing it clears `unregistered_kiln`; expired calibration →
provisional.
**Gate:** standard + migrations.

---

## Phase C9 — Annual verification inputs  `[V][admin]`
**Requirement `[V]` (annual/independent):** methane emission rate (3 runs), PAH/heavy metals
(closed-kiln PAH mandatory), biomass leakage assessment, biomass→biochar conversion factor, dry bulk
density per site.
**Server:** admin endpoints + tables keyed by `(project/site, year)`; store the signed report artifacts.
The **methane rate** and **conversion factor** feed the LCA (methane feeds the CH₄ penalty already
modeled from telemetry; conversion factor feeds C1's `yield_conversion`).
**Compliance:** a batch in a period lacking a current methane measurement / (closed-kiln) PAH →
`missing_annual_methane` / `missing_pah`.
**Tests:** period with valid annual data → cleared; stale/absent → provisional.
**Gate:** standard + migrations.

---

## Phase C10 — Unified issuance compliance gate  `[capstone]`
**Goal:** one place that decides a batch is **methodology-complete and issuable**. Extend
`corroboration.assemble` (or a new `evaluate_compliance(batch, evidence)` pure function) to fold ALL the
per-phase reasons above into `provisional_reasons`; `provisional == (reasons != [])`. Issuance (final
signature) already requires `not provisional` (Phase 8-R/15-B) — so this capstone is the single source of
truth for "ready to mint".
**Deliverable:** a `GET /api/v1/batches/{uuid}/compliance` (admin) returning the reason list + a
human-readable checklist mirroring the methodology sections, so the Project Developer can see exactly
what's missing per batch.
**Tests:** a fully-populated batch (all C1–C9 data) → `provisional False`, empty reasons, signed; each
missing datum → its specific reason present and unsigned.
**Gate:** full regression; write a `## Rainbow Compliance — Final` block mapping every methodology line
to its enforcing test.

---

## Sequencing & risk
1. **C0 → C1 → C2 → C3/C3b** (per-run operational data; C2 is the biggest real gap).
2. **C4 → C5 → C6** (batch/transport; C6 touches credit math — most care).
3. **C7** (lab Corg — closes the Corg-constant integrity gap; high methodology value).
4. **C8 → C9** (project/annual registries — admin surface, likely a separate console).
5. **C10** capstone.

Each phase is **independently mergeable** and leaves the app fully working (new data is optional until its
compliance reason is switched on). Nothing here rejects an existing upload; it only makes a batch
*provisional with a precise reason* until the methodology datum arrives — the same mechanism the security
remediation already established. Flip each reason "live" only after the client can supply that datum.

## Out of scope / dependencies
- The 1000-year permanence pathway (inertinite/Ro) is only needed if the project elects it — gate behind a
  project setting (C8).
- Real hardware attestation (Phase 17) and the client hardware-key epic remain separate security items.
- Emission factors (fuel, transport, methane GWP) must come from the Rainbow methodology annexes — do NOT
  invent constants; source them and put them in one audited config module.
