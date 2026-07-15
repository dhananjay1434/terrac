# Competitor dMRV Blueprint — Bluelayer + Varaha

> **Purpose.** A rebuild-grade architectural reference distilled from two production
> biochar dMRV systems, captured by reverse engineering:
> - **Bluelayer** (`app.bluelayer.io`) — a declarative, versioned carbon-computation
>   engine. FastAPI 3.1.0 backend (59 paths / 80 operations / 321 schemas), Next.js
>   frontend, Auth0. Source: OpenAPI spec extracted verbatim from the JS bundle.
> - **Varaha "Kalki"** (`com.varaha.biochar` v1.6.2) — an offline-first MRV field-capture
>   app for India/Bangladesh/Kenya. Kotlin Multiplatform + Compose, Room v20, Ktor,
>   WorkManager. Source: R8 decompile; all serial names, SQL DDL, and endpoints survived.
>
> **How to use this.** This is a design reference, NOT a spec of our own system. Field
> names/DDL/schemas below are THEIRS, captured exactly so we can copy patterns with
> confidence. Where a pattern maps to our dMRV, a **→ dMRV** callout says how. Nothing
> here should be pasted into our codebase without reading our real files first (see
> `EXECUTION_MASTER_PLAN.md` errata for our real schema).
>
> **The two systems are complementary:**
> - **Bluelayer = the brain** (calculation, provenance, registry export, credit ledger).
>   This is what our backend should aspire to. Its CSI export schema already closed our
>   E23 gap (see `EXECUTION_MASTER_PLAN.md` E23).
> - **Varaha = the hands** (offline capture, sync, media pipeline, KYC/FPIC, India market).
>   This is what our Flutter app + `feature/t5-india` branch should learn from.

---

# PART A — BLUELAYER (the computation & verification engine)

## A0. The mental model

Bluelayer is a **declarative, versioned computation engine**. A carbon project is one
big JSON document (the `Model`) that is interpreted at runtime. Nothing is hardcoded;
methodologies are *authored as data*.

```
            ┌──────────────────── PROJECT MODEL (versioned blob) ─────────────────────┐
            │  logs[]  entities[]  metrics[]  constants[]  ledgers[]  reports[]  alerts[] │
            └───────────────┬─────────────────────────────────┬────────────────────────┘
                            │ defines                          │ defines
        ┌───────────────────▼──────────┐        ┌──────────────▼───────────────┐
        │  FORMULA / AST ENGINE         │        │  METRICS ENGINE (time-series)  │
        │  ComputedField / ScalarExpr   │───────▶│  Log/Connected/Calculated/     │
        │  ArithmeticFormula / FnCall   │  feeds │  Transformed → Reduction        │
        │  Constants (versioned)        │        │  data-points/stats/histogram    │
        └───────────────┬───────────────┘        └──────────────┬────────────────┘
                        │ evaluated values                       │ metric values
                        ▼                                        ▼
            ┌───────────────────────┐               ┌────────────────────────────┐
            │  EXPLAIN ENGINE        │               │  ALERTS / ANOMALY ENGINE    │
            │  /explain → ExplainNode │               │  Alert(target,formula) →    │
            │  full calc provenance   │               │  Jobs → Incidents → Ack     │
            └───────────────────────┘               └────────────────────────────┘
                        ▲
   capture-time trust   │                       cross-cutting governance
        ┌───────────────┴───────┐               ┌────────────────────────────────┐
        │ TELEMETRY / CAPTURE    │               │  RBAC: Groups (tree) +          │
        │ GPS/EXIF/Attestation   │               │  nested Permission matrix       │
        │ + Validation rules      │               │  (project→component→action)     │
        └───────────────────────┘               └────────────────────────────────┘
```

**Five design principles that make it audit-grade** (steal all five):
1. **Tagged unions everywhere.** Every polymorphic node carries a `_t` literal
   discriminator (validation rules use `rule_name`). This makes an illegal formula a
   422 at the API boundary, not a runtime crash.
2. **Recursive ASTs, reified as JSON** — not string formulas. No `eval`. The tree is
   transported, persisted, and walked by an interpreter.
3. **Versioning is first-class.** The Project Model is versioned; Constants are
   versioned with `valid_from` + evidence documents → point-in-time correctness.
4. **Provenance IS the product.** Every computed number expands into a mirror
   "explain" tree citing source fields, constant versions, and operators.
5. **Governance is a nested matrix**, not flat roles.

---

## A1. The Formula / AST Engine (the crown jewel)

`ComputedField` is a **fully reified Abstract Syntax Tree** serialized as JSON. A
formula is a tree of typed nodes persisted inside the Project Model and walked by a
backend interpreter.

### A1.1 Root node — `ComputedField`

```jsonc
// ComputedField-Input
{
  "name":           "string",                         // machine id of the field
  "formula":        "$ref ComputedFieldTerms-Input",  // the AST root term
  "title":          "string | null",
  "description":    "string | null",
  "unit":           "string | null",                  // semantic dimension e.g. "tCO2e"
  "decimal_places": "integer (default 2)",
  "_t":             "const 'ComputedField'"           // discriminator tag
}
```

The field is **dimensioned** (`unit`), and the engine is unit-aware end-to-end — it can
refuse `kg + m` category errors.

### A1.2 The recursive production rule — `ComputedFieldTerms`

A tagged union of seven alternatives:

```
Term   ::= FieldRef                       // bare JSON string → a column in the SAME row
         | Number | Integer               // literal
         | ConstantVal                    // named, versioned constant
         | MetricLookup                   // a reduction over a time-series Log
         | ArithmeticFormula(Term, Term)  // recursive binary branch
         | FunctionCall(Term*)            // recursive n-ary branch
```

> **Key subtlety:** a bare JSON `string` leaf is a **reference to another field on the
> same record** (a sibling column). `MetricLookup` is the cross-time/cross-row pointer.

### A1.3 Binary branch — `ArithmeticFormula`

```jsonc
// ArithmeticFormula_ComputedFieldTerms_-Input   (FastAPI name-mangles the generic)
{
  "operator":    "$ref ArithmeticOperator",   // enum ["+","-","*","/","^"]
  "left":        "anyOf[ ComputedFieldTerms , ArithmeticFormula ]",
  "right":       "anyOf[ ComputedFieldTerms , ArithmeticFormula ]",
  "left_title":  "string | null",              // human caption, survives into explain tree
  "right_title": "string | null",
  "_t":          "const 'ArithmeticFormula'"
}
```

`^` (exponentiation) exists specifically for IPCC-style power-law growth/decay factors.
`left_title`/`right_title` pre-author the audit narrative at design time
("Wet Biomass × Dry Matter Fraction").

### A1.4 N-ary branch — `FunctionCall`

```jsonc
// FunctionCall_ComputedFieldTerms_-Input
{
  "function_name": "$ref Function",             // enum ["min","max"]  (named → extensible)
  "args":          "array< ComputedFieldTerms >" // 0..n recursive children
}
```

`max(0, wet_mass - tare)` is the canonical use — floor a measured value at zero before
it poisons downstream sums.

### A1.5 Versioned constant injection — `ConstantVal`

```jsonc
// ConstantVal  (a leaf — thin, late-binding, carries NO value)
{
  "constant_name": "string",                    // named constant
  "lookup_value":  "number | string | null"     // optional KEY into a lookup table
}

// Constant = anyOf[ ScalarConstant , LookupTableConstant ]
// ScalarConstant       → { name, unit, initial_value:number?, group, _t }
// LookupTableConstant  → { name, unit, use_ranges:bool, initial_value:[ConstantLookTableEntry]?, _t }
// ConstantLookTableEntry → { key: (string | number | [num,num] | [null,num] | [num,null]), value:number }
```

**Resolution algorithm** when the interpreter hits `ConstantVal("EF_diesel")` while
evaluating a record whose effective date is `T`:
1. Load all `ConstantVersion`s for `EF_diesel`.
2. Select the version with the **greatest `valid_from` ≤ T** (temporal as-of join).
3. If it's a lookup table, apply `lookup_value` (scalar key or half-open range bracket
   like `[null,30]`, `[30,100]`, `[100,null]`) to pick the cell.
4. Inject the resolved number into the tree.

This is why vintage-2022 and vintage-2024 reports run the *identical* formula but use
*different* emission factors. Each version carries `evidence_documents[]` +
`version_description` → every number is traceable to the document that authorized it.

Versioned constant sub-resource:
```
GET   .../constants/{constant_name}/versions
POST  .../constants/{constant_name}/versions                  // ConstantVersionCreate
GET   .../constants/{constant_name}/versions/{version_number}
PATCH .../constants/{constant_name}/versions/{version_number}

// ConstantVersionCreate body:
{ "value": "number | array<ConstantLookTableEntry>",
  "valid_from": "date-time | null",           // TEMPORAL KEY
  "version_description": "string | null",
  "evidence_documents": "array<FilePayload> | null" }
```

### A1.6 The provenance mirror (the moat) — the Explain AST

Evaluating a `ComputedField` does not return a bare number. The `/explain` endpoints
return a **second tree isomorphic to the formula tree**, each node annotated with
resolved value, unit, and source.

```
GET .../logs/{log_name}/entries/{entry_id}/fields/{field_name}/explain → ComputedFieldExplainNode
GET .../entities/{entity_name}/instances/{instance_id}/fields/{field_name}/explain → ComputedFieldExplainNode
```

| Input AST node                | Provenance node                | Resolved payload added |
|-------------------------------|--------------------------------|------------------------|
| `ComputedField`               | `ComputedFieldExplainNode`     | `unit`, `decimal_places` |
| `number`/`integer` literal    | `ScalarExplainNode`            | `{ value, unit }` |
| `string` (field-ref leaf)     | `FieldReferenceExplainNode`    | `{ field_name, value, unit }` |
| `ConstantVal`                 | `ConstantExplainNode`          | `{ constant, constant_name, version, value, lookup_value, unit }` |
| `MetricLookup`                | `MetricLookupExplainNode`      | `{ value, metric, entries:[LogMetricEntryTrace] }` |
| `ArithmeticFormula`           | `ArithmeticFormulaExplainNode` | `{ operator, left, right, left_title, right_title, value, unit }` |
| `FunctionCall`                | `FunctionCallExplainNode`      | `{ function_name, args[], value, unit }` |

`ConstantExplainNode` carries the exact **version** used; `MetricLookupExplainNode.entries`
carries the raw Log-row traces that fed the aggregation. Row-level traceability from a
final carbon number all the way back to the timestamped, attested field observation.

> **→ dMRV.** Our credit engine (`backend/credit_engine.py`) currently computes numbers
> but does not emit a defensible per-number provenance tree. Our closest existing asset
> is `lca_audit_json` on the Batch. **Recommendation:** model an "explain" payload on
> our LCA output — for each credit term, record `{operator, operands, constant_version,
> source_field, value, unit}`. We do NOT need the full AST-interpreter machinery (that's
> a multi-month build); we need the *output shape* — a serialized calc trace attached to
> each issued credit. This is the single most valuable idea to steal and the cheapest to
> approximate. It directly strengthens our anchoring/attestation story for auditors.

---

## A2. The Metrics Engine (time-series → conservative scalar)

The bridge from messy sensor data to the single number a formula needs. Rigid 5-stage
pipeline: **Select → Bucket → Gap-Fill → Smooth → Aggregate**.

```jsonc
// LogMetric — the entry point from the AST (via MetricLookup.metric)
{
  "log_name":          "string",   // WHICH Log (time-series table)
  "field":             "string",   // WHICH column
  "filters":           "object | null",     // dimension slicing
  "frequency":         "Interval (default {days:1})",  // bucket width
  "is_counter":        "bool (default false)",         // delta vs flow semantics
  "gap_filler":        "$ref GapFiller",     // missing-data policy
  "smooth_function":   "SmoothFunction | null",
  "period_aggregator": "$ref Aggregation",   // final collapse
  "_t":                "const 'LogMetric'"
}

// Interval = { weeks, days, hours, minutes, seconds }  (all int)
// GapFiller = ["linear_interpolation","forward_fill","backward_fill","nearest","zero"]
// Aggregation = anyOf[ BaseAggregation , WeightedAverage ]
// BaseAggregation = ["sum","avg","min","max","count","first","last","array_merge","stddev","mean_minus_stddev"]
// WeightedAverage = { weight_field_name }
// Metric = anyOf[ LogMetric , ConnectedMetric , CalculatedMetric , TransformedMetric ]
// CalculatedMetric = { operator: ArithmeticOperator, left, right }  // metric-level AST
// TransformedMetric = { metric, transformation }  // MetricTransformation = ["cumulative_sum","latest"] | MovingAverage
// MetricReduction = { metric, function: ReductionFunction, dimensions }
// ReductionFunction (17): sum, mean, median, max, min, count, std, se, var, last, first,
//                         winsorized_mean/std/se, time_weighted_mean/std/se
```

**Pipeline stages:**
1. **Select/slice** — `log_name` + `field` + `filters`.
2. **Bucket** — snap timestamps to `frequency`; if `is_counter`, take deltas between
   cumulative readings; else place values as-is.
3. **Gap-fill** — synthesize empty buckets per `gap_filler` (`zero` = conservative for
   removals; `forward_fill` = carry last; `linear_interpolation` = straight line).
4. **Smooth** — optional `MovingAverage` for noisy IoT.
5. **Aggregate** — collapse the array via `period_aggregator`.

> **The conservativeness moat: `mean_minus_stddev`.** A first-class aggregation primitive
> (μ − σ). An erratic sensor automatically yields a *lower, safer* carbon claim than a
> stable one with the same mean. This is carbon-accounting DNA, not generic analytics.

> **→ dMRV.** Our moisture and temperature logs (`MoistureReading`, `TemperatureLog`,
> `PyrolysisTelemetry`) are exactly the "Log" concept. Today we store raw
> `payload_json`. **Recommendation:** when we aggregate moisture samples for credit
> gating, adopt `mean_minus_stddev` (or an explicit conservative reducer) rather than a
> plain mean, and record the gap-fill policy. Cheap, and it's a genuine defensibility
> upgrade a verifier will respect.

---

## A3. The Alerts / Anomaly Engine (a second, boolean AST)

A quarantine layer between raw telemetry and the calculation engine. Same interpreter
as the math engine, but boolean operators.

```jsonc
// Alert
{ "name":"string", "target":"anyOf[Metric,MetricRef]",
  "formula":"anyOf[AlertTerm,BinaryBooleanFormula,UnaryBooleanFormula]",
  "monitoring_window":"Interval (default 52 weeks)", "_t":"const 'Alert'" }

// AlertTerm (leaf)
{ "operator":"enum ['<=','<','=','>','>=']",
  "value":"anyOf[Metric,Scalar,ConstantVal,MetricRef]", "_t":"const 'AlertTerm'" }

// BinaryBooleanFormula  { operator:"['AND','OR']", left, right }   (recursive)
// UnaryBooleanFormula   { operator:"'NOT'", term }                 (recursive)
```

**Incident lifecycle** — `Trigger → Acknowledge → Resolve`:
```jsonc
// AlertIncident
{ "id","alert_name","start_time","end_time",
  "values":"array<number>",                 // the exact readings that breached
  "dimensions":"map<string,DimensionRef>",  // WHICH sensor/entity — granular quarantine
  "created_at","acknowledged_at","resolved_at" }
```
```
POST  .../projects/{project_id}/alerts/trigger              → JobResult (evaluate all rules)
GET   .../projects/{project_id}/alerts/status               → AlertJobRead per alert
GET   .../projects/{project_id}/alerts/incidents/active     → open incidents
PATCH .../projects/{project_id}/alerts/incidents/{id}/ack   → acknowledge
// internal cron: POST /internal/dmrv-webhooks/trigger_all_orgs_all_projects_alerts
```

Granular quarantine via `dimensions`: an alert pauses only the offending device, not the
whole project.

> **→ dMRV.** We have compliance gates (C1–C10) that mark a batch provisional. That's a
> *static* rule check at issuance time. Bluelayer adds a *continuous* anomaly monitor with
> a human ack/resolve loop. **Recommendation (later phase, not P0):** a lightweight
> "integrity signals" monitor (we already have `test_t27_integrity_signals`) that opens
> an incident when a batch's readings breach a threshold vs. its cohort, and requires
> admin acknowledgement before issuance. Copy the incident lifecycle fields verbatim.

---

## A4. Telemetry / Capture — the edge-trust layer

Provenance envelopes that prove *who / where / what hardware* captured each datum.

```jsonc
// FilePayload — root entry for digital evidence
{ "filename","user_filename", "exif_metadata":"ExifMetadata", "capture_metadata":"CaptureMetadata" }

// CaptureMetadata
{ "user_id","org_name","project_id","component_type","component_name","captured_at",
  "app_name","app_version",
  "attestation": { "device_id","device_hint" },       // device-binding / anti-spoof
  "gps": { "source","lat","lng","accuracy" } }

// ExifMetadata { coordinates, date_time }   // extracted by BACKEND from file header (not client-trusted)
```

**Dynamic, graph-aware validation** (the breakthrough — rules query the Model at runtime):

```jsonc
// FileValidationRules (discriminator rule_name)
// file_contain_location_metadata:
{ "rule_name":"file_contain_location_metadata",
  "params": { "within_radius": { "geo_location":"GeoLocation | FieldReference", "distance_meters":"number" } } }
// → geo_location can be a FieldReference: "validate this photo was taken within X m of
//   Plot A's polygon", resolved dynamically from the Model. Reject before it hits the math.

// InputValidationRules (discriminator rule_name):
//   greater_than, greater_equal_than, less_than, less_equal_than, is_positive, is_non_negative, in_range
// Bounds can be a literal OR a FieldReference → cross-field / temporal validation:
{ "rule_name":"greater_equal_than", "params": { "min":"integer | number | FieldReference" } }
// → "Year-2 tree height ≥ Year-1 height" enforced by referencing the prior Log.
// FieldReference can carry an aggregation → "≥ mean_minus_stddev of all prior logs".
```

`CaptureMode ∈ {file_only, camera_only, file_or_camera}`;
`CameraMetadataConfig { require_gps, require_watermark }`.

> **→ dMRV.** This is directly adjacent to our `backend/services/evidence.py`, media
> anchoring, and GPS corroboration tests. Two concrete steals:
> 1. **Extract EXIF server-side, never trust client coordinates** — treat client GPS and
>    file-header GPS as two independent signals and cross-check (we already do GPS
>    corroboration; formalize the envelope).
> 2. **Geofenced file rule** — enforce "photo taken within N meters of the registered
>    kiln/site" as a hard gate. We have lat/long on Batch and kiln registry; this is a
>    high-value, low-cost anti-fraud gate. Note Varaha's `RequestMetadata` (Part B) is the
>    mobile-side implementation of exactly this envelope — adopt them together.

---

## A5. The Project Model & Field System (the declarative spine)

Bluelayer has no hand-written business tables. One `Model` blob defines everything and
is interpreted at runtime.

```jsonc
// Model (the "god object")
{ "entities":[Entity], "logs":[Log], "metrics":[Metric], "constants":[Constant],
  "alerts":[Alert], "reports":[Report], "ledgers":[Ledger] }
// ProjectModelResponse = { id, version, model, entry_counts, created_at }
//   → versioned: a 2025 model is retained immutably so historical calcs never break.
```

**Entity vs Log** — the structural divide:
- **`Entity`** = static/spatial dimension (a Farm, a Kiln, a Soil Plot). `{name, fields[], status, qr_code}`.
- **`Log`** = a timestamped event against an Entity (Daily Temp Reading, Soil Sample).
  `{name, fields[], _dependencies[]}`.

**Field type system** (`LogField`/`EntityField`, `oneOf` discriminated on `_t`):

| Field `_t`                        | Meaning | Log-only? |
|-----------------------------------|---------|-----------|
| `InputField`                      | raw measured leaf (+ `validations[]`, options, unique, sources) | no |
| `FileField`                       | evidence (`capture_mode`, `camera_metadata_config`, `allowed_file_types`) | no |
| `ComputedField`                   | AST-derived value (A1) | no |
| `RelationField`                   | graph edge (FK) with **AST filter** as the ON-clause | no |
| `RollinField` / `RolloutField`    | aggregate child→parent / push parent→child | no |
| `StaticField`                     | constant per instance | no |
| `SequenceField`                   | auto-ID `{prefix:[str\|FieldReference], separator}` — graph-aware | no |
| `GeoLocationField`                | geometry | no |
| `UserField`                       | actor reference | no |
| `DeltaField`                      | change vs previous entry | **yes** |
| `TransactionValueField`           | double-entry ledger event | **yes** |
| `ApproximatingRectangleAreaField` | Riemann integration over time | **yes** |

**Two hidden engines inside Log fields:**

1. **Double-entry ledger (`TransactionValueField`)** — carbon credits are treated like
   fiat in a bank. `{ledger, account, unit, decimal_places}`. Sequestering 100 t credits
   one account and debits the baseline; accounting must balance to zero → structurally
   impossible to double-issue.
   ```jsonc
   // Ledger { name, value_title, value_unit, accounts:[LedgerAccount] }
   // CreditLogTransaction  { log, value, units }
   // DebitLogTransaction   { log, units }
   // TransferLogTransaction{ log, out_units, in_units, target_account }
   ```
2. **Riemann integrator (`ApproximatingRectangleAreaField`)** —
   `{value_field, time_unit:[seconds,minutes,hours], height_point:[left,right,middle]}`.
   Integrates area under a curve (kW → kWh) with selectable Left/Right/Midpoint rule to
   match registry rigor.

`RelationField.filter` reuses the **same `BinaryBooleanFormula` AST** as the math and
alerts engines — one interpreter walks calculation rules, anomaly rules, AND join
conditions.

> **→ dMRV.** We should NOT rewrite our backend as a declarative interpreter — that's
> their multi-year moat and overkill for our scope. But two ideas transfer cheaply:
> - **The Entity/Log split is exactly our model** — Batch/kiln/project = Entities;
>   MoistureReading/TransportEvent/PyrolysisTelemetry = Logs. Naming our side-tables
>   consistently as "logs" clarifies the mental model.
> - **The credit ledger idea** is worth considering for issuance integrity: today
>   `batch.provisional` + status transitions gate issuance. A double-entry ledger would
>   make double-issuance structurally impossible. Evaluate for a future hardening phase;
>   not P0.

---

## A6. Registry Export layer (closes our E23 gap)

The export boundary has its own recursive AST (`BatchedScalarExpression`) that can
allocate batched credits down to individual farmers.

```jsonc
// ReportingPeriod { start_time, end_time }  → logs outside the window are excluded (no double-count)

// BatchedScalarExpression = ScalarExpression | BatchedScalarCalculation | Allocation | FieldReference
// BatchedScalarCalculation { operator:ArithmeticOperator, left, right, _breakdown_terms:true }
// Allocation { expression:BatchedScalarExpression,   // e.g. 10,000 t total
//              allocation_field:FieldReference,       // e.g. farm_size_hectares
//              partition_by:FieldReference }          // e.g. crop_type
//   → distributes a pooled credit total proportionally to individual entities.
```

**Registry targets** (Bluelayer supports several; we care about CSI):
- **CSI — `GlobalCSinkVerificationReport`** (this is the one that closed E23; see the full
  field table + dMRV mapping in `EXECUTION_MASTER_PLAN.md` E23). Fields resolve via
  `ReportField = BatchFieldReference | BatchImpactValueTermReference | StaticValue`.
- **Puro** — `PuroBatchedImpactReport`, `PuroSectionDef`, `PuroFieldDef {key,
  emission_impact_type:[EMISSION|SEQUESTRATION], impact_node_ref}`, `PuroSubmission(+Response)`.
- **Isometric** — `IsometricReport`, `IsometricNode {component_blueprint_key,
  inputs:[{input_key, reference: ExplainNodesIndexRef | FieldReference}]}`. Note it ships
  the **entire explainability trace** to the registry.

`ReportField.BatchImpactValueTermReference` reaches into the `BatchedScalarCalculation`
AST and plucks an exact intermediate node by `term_title`.

> **→ dMRV.** CSI export field names are now VERIFIED (E23 updated). Rainbow remains
> unverified — neither dump contains a Rainbow format. The `Allocation` node is worth
> remembering IF we ever aggregate smallholder batches into a pooled issuance; not needed
> for single-batch export today.

---

## A7. RBAC / Governance (nested permission matrix)

```jsonc
// GroupOutput { name, title, description, permission:Permission, parent, timestamps }  // tree via parent
// GroupTreeNodeOutput { name, children[] }   // recursive

// Permission — nested JSON access matrix (additionalProperties:true)
{ "<project_id>": {
    "<component>": {
      "permissions": {
        "add":  "bool | 'inherited'",
        "read": "'none'|'own'|'group'|'assigned'|'all'|'inherited'",
        "update":"'none'|'own'|'group'|'assigned'|'all'|'inherited'",
        "approve":"bool | 'inherited'" },
      "assign_field":"owner" },        // powers the 'assigned' row-level scope
    "*":"inherited|none" },
  "*": "…" }
```
Per-project, per-component, per-action, with **inheritance down the group tree** and
row-level scoping (`own`/`group`/`assigned`). Review governance:
`ReviewStatus {default:[pending,approved,rejected], options}`, `StatusGroup`, `FieldGroup`.

> **→ dMRV.** Our auth is simpler (device signatures + `X-Admin-Secret` + portal
> `require_role`). We do NOT need this matrix now. Keep as reference for if/when we add
> multi-org tenanting.

---

# PART B — VARAHA "KALKI" (the offline-first field-capture app)

## B0. Tech stack (verified from the binary)

| Concern | Technology |
|---|---|
| Language / build | Kotlin 2.1.10, Gradle 8.13, KMP (`androidJvm`, `ios_arm64`, `ios_simulator_arm64`) |
| UI | Compose Multiplatform + Material 3 |
| Navigation | Voyager |
| DI | Koin |
| Networking | Ktor client + OkHttp engine |
| Serialization | kotlinx.serialization (JSON) |
| Local DB | Room (schema **v20**) + bundled SQLite + Paging 3 |
| Preferences | Jetpack DataStore |
| Background | WorkManager (4 workers) |
| Media | CameraX, Coil 3, ML Kit (barcode, doc scanner, face), PDFBox |
| Location/Maps | Google Maps + Play Location, Compass, Connectivity |
| Backend | Firebase (Remote Config, Crashlytics, Analytics…) + 2 REST APIs |
| Distribution | Play App Signing (v2+v3), PairIP integrity wrapper, in-app updates |

> **→ dMRV.** We are Flutter + Drift + Riverpod + BLE sync. The *stack* differs but the
> *patterns* below are stack-agnostic and directly portable.

## B1. The offline-first sync engine (the crown jewel of Part B)

**Principle:** every UI read/write hits the local DB (source of truth); nothing blocks on
network. Each row carries `sync_status` starting at 0. WorkManager workers drain pending
rows + the media queue when online. Local `id` and `server_id` coexist; after push, the
server ID is written back and dependent media rows are repointed.

**`SyncStatus` enum (integer) — adopt this vocabulary verbatim:**

| Value | Name | Meaning |
|---|---|---|
| 0 | SYNC_UPDATE | Pending upload (default on insert/edit) |
| 1 | SYNC_IN_PROGRESS | Being pushed now |
| 2 | SYNC_COMPLETED | Reconciled with server |
| 3 | NOT_FOR_SYNC | Local-only, excluded |
| 4 | SYNC_FAILED | Retries exhausted (≥3) |
| 5 | SYNC_DELETE | Tombstoned, pending remote delete |
| 6 | SYNC_CONFLICT | Server/local divergence |

**Media conversion status (`media.media_conversion_status`, integer):**

| Value | Meaning |
|---|---|
| 0 | CONVERSION_REQUIRED |
| 1 | CONVERSION_IN_PROGRESS |
| 2 | CONVERSION_NOT_REQUIRED / ready to upload |
| 3 | CONVERSION_FAILED |

**The four WorkManager workers:**

| Worker | Foreground | Trigger | Responsibility |
|---|---|---|---|
| `UniversalSyncWorker` | ✅ | periodic / on-demand | Push & pull all non-media domain rows via a sync registry; requires network |
| `MediaPreProcessorWorker` | ❌ | media `conversion_status=0` | Compress images / transcode video → `pre_`-prefixed file; build PDFs; advance enum; drop 0-byte files |
| `UploadMediaWorker` | ✅ | media pending upload | Resolve file → presigned-S3 PUT → track `upload_progress` 0–100 → write `media_url`/`expiry_in`; on error bump `retries`, at ≥3 set `sync_status=4` |
| `MediaCleanupWorker` | ❌ | after successful upload | Delete local temp/processed files |

**Media pipeline state machine:**
```
[capture] media row: sync_status=0, conversion_status=0, upload_progress=0, retries=0
   │ MediaPreProcessorWorker
conversion_status: 0 → 1 → 2  (or → 3 on failure); file rewritten as pre_<name>
   │ UploadMediaWorker
   POST UploadMediaNetworkModel → MediaDetails{s3_data} → PUT file to S3
   upload_progress: 0 … 100
   success → sync_status=2, media_url set, expiry_in set
   failure → retries++ ; if retries ≥ 3 → sync_status=4
   │ MediaCleanupWorker
   local temp files deleted
```

**The `ref_local_id → ref_id` reconciliation (critical pattern):** media rows point to
their parent via `ref_type` + (`ref_id` if synced / `ref_local_id` if not) + `ref_sub_type`.
After a parent receives its `server_id`, its queued media are repointed:
```sql
UPDATE media SET ref_id = ?, sync_status = ? WHERE ref_local_id = ? AND ref_type = ?
```

**Dual-lookup DAO pattern on every table** (local/remote identity reconciliation):
```sql
SELECT * FROM site WHERE id = ?          SELECT * FROM site WHERE server_id = ?
SELECT local_id FROM farmers WHERE server_id IS NULL     -- find unsynced
SELECT COUNT(*) FROM media WHERE sync_status IN (...)    -- powers "N items unsynced"
SELECT * FROM media WHERE ref_local_id = ? AND ref_sub_type = ? AND sync_status != 4 AND sync_status != 5 ORDER BY created_at DESC
```

> **⚠️ Gotcha to fix in our version:** failed media (state 4) and tombstoned (state 5) are
> **excluded from re-upload queries**. Without a **manual retry affordance**, failed data
> silently stalls forever. Varaha exposes this via a `LocalTasksScreen`. We MUST build the
> equivalent retry UI if we adopt this state machine.

> **→ dMRV.** Our BLE sync + Drift is the analog. Concrete steals, ranked:
> 1. Adopt the **7-value `sync_status` enum vocabulary** exactly (we likely have a
>    narrower set today).
> 2. Adopt the **central media queue** with `ref_type`/`ref_sub_type`/`ref_id`/
>    `ref_local_id` so every entity is decoupled from its evidence, plus the repointing
>    update.
> 3. Split media work into **preprocess / upload / cleanup** stages (Flutter
>    `workmanager` + isolates), with `upload_progress` 0–100 and `retries≥3 → failed`.
> 4. Build the **manual retry screen** (non-negotiable, per the gotcha).

## B2. Data model — Room schema v20 (14 tables, exact DDL)

Universal conventions: local PK (`id`/`local_id`/`localDataID`), `server_id` (NULL until
sync), `sync_status`, `created_at` (epoch millis), geometry as WKT text, media never
inline (referenced via `media` table).

```sql
-- media — the central upload queue (most important table to copy)
CREATE TABLE media (
  localDataID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, server_id INTEGER,
  ref_type TEXT NOT NULL, ref_sub_type TEXT NOT NULL, ref_id INTEGER, ref_local_id INTEGER,
  moisture REAL, data TEXT, retries INTEGER NOT NULL, cycle_id INTEGER,
  media_conversion_status INTEGER NOT NULL, sync_status INTEGER NOT NULL,
  upload_progress INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL,
  verification_status TEXT, verification_remarks TEXT, media_url TEXT, expiry_in INTEGER,
  farmer_id INTEGER, metadata TEXT );

-- farmers — the PII-heavy KYC table (see B4)
CREATE TABLE farmers (
  local_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, server_id INTEGER,
  block_id INTEGER NOT NULL, country_id INTEGER NOT NULL, village_id INTEGER NOT NULL DEFAULT 0,
  date_of_birth INTEGER, education_level TEXT, reported_farm_area REAL, total_family_members INTEGER,
  mobile_number_ownership TEXT, farmer_consent INTEGER NOT NULL,
  first_name TEXT NOT NULL, fsm_state TEXT NOT NULL, guardian_name TEXT NOT NULL,
  gender TEXT NOT NULL, kyc_status INTEGER NOT NULL, last_name TEXT NOT NULL,
  mobile_number TEXT NOT NULL, signature TEXT, location TEXT, status INTEGER NOT NULL,
  tags TEXT NOT NULL DEFAULT '', created_datetime INTEGER NOT NULL DEFAULT CURRENT_TIMESTAMP,
  metadata TEXT,
  address_blockName TEXT, address_countryName TEXT, address_districtName TEXT,
  address_pincode TEXT, address_stateName TEXT, address_localAddress TEXT,
  address_wardNumber TEXT, address_villageName TEXT,
  profile_picture_expiryIn INTEGER, profile_picture_filename TEXT,
  profile_picture_mediaUrl TEXT, profile_picture_thumbnailUrl TEXT,
  fpic_englishFpicPdf TEXT, fpic_englishFpicImagesList TEXT,
  fpic_regionalFpicPdf TEXT, fpic_regionalFpicImagesList TEXT, fpic_holdingConsentImage TEXT );

-- facilities (production facility; note registry linkage)
CREATE TABLE facilities (
  local_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, server_id INTEGER,
  name TEXT NOT NULL, state TEXT NOT NULL, district TEXT NOT NULL,
  location_wkt TEXT NOT NULL, status TEXT NOT NULL, biomass_type INTEGER, biomass_name TEXT,
  type TEXT NOT NULL, registry TEXT, registry_config_id INTEGER,
  created_at INTEGER NOT NULL, organization_id INTEGER NOT NULL, sync_status INTEGER NOT NULL );

-- artisanal_cycle (a production run) + batch_kiln (kiln usage in a cycle)
CREATE TABLE artisanal_cycle (
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, server_id INTEGER,
  facility_id INTEGER NOT NULL, start_time INTEGER NOT NULL, end_time INTEGER,
  kiln_use_from INTEGER, kiln_use_until INTEGER, process_status TEXT NOT NULL,
  kiln_count INTEGER NOT NULL, sync_status INTEGER NOT NULL, created_at INTEGER NOT NULL,
  metadata TEXT, all_media_uploaded INTEGER );
CREATE TABLE batch_kiln (
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, server_id INTEGER,
  cycle_id INTEGER, cycle_local_id INTEGER, kiln_id INTEGER NOT NULL, kiln_name TEXT,
  volume REAL, density REAL, moisture REAL, moisture_readings TEXT,
  created_at INTEGER NOT NULL, sync_status INTEGER NOT NULL );

-- site (biomass source) + biomass_dispatch + dispatch_sites (child, FK CASCADE)
CREATE TABLE biomass_dispatch (
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, server_id INTEGER,
  facility_id INTEGER NOT NULL, facility_name TEXT, status TEXT NOT NULL,
  sync_status INTEGER NOT NULL, created_at INTEGER NOT NULL,
  weight_at_facility REAL, weight_at_facility_pdf TEXT, weight_pdf TEXT, weight_type TEXT,
  weights TEXT NOT NULL, weight_images TEXT NOT NULL, empty_truck REAL, loaded_truck REAL,
  driver_name TEXT NOT NULL, driver_phone_number TEXT NOT NULL, truck_number TEXT NOT NULL,
  truck_image_front TEXT, truck_image_back TEXT, created_by_name TEXT,
  farm_id INTEGER, farmer_id INTEGER );
CREATE TABLE dispatch_sites (
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
  dispatch_id INTEGER NOT NULL, site_id INTEGER NOT NULL, site_name TEXT,
  moisture REAL, moisture_image TEXT, truck_percentage_filled REAL, truck_load_image TEXT,
  created_at INTEGER NOT NULL,
  FOREIGN KEY(dispatch_id) REFERENCES biomass_dispatch(id) ON DELETE CASCADE );
```

Other tables: `site`, `biochar_dispatch` (note: its `sync_status` is TEXT — an
inconsistency; normalize to INTEGER in our version), `biomass_input`, `kiln` (PK =
`server_id`, master data), `artisanal_bulk_density`, `artisanal_summary` (per-day
rollup), `remote_keys` (Paging 3 cursor cache).

**Media `ref_sub_type` values** (the evidence taxonomy — maps evidence to workflow stage):
```
SiteImage, SiteDocument
BiomassDispatchTruck, BiomassDispatchTruckLoad, BiomassDispatchWeight, BiomassDispatchMoisture
BiocharDispatchWeight, BiocharDispatchTruck, BiocharDispatchInvoice, BiocharDungMix
density_activity_video, density_activity_mass_image
-- production cycle stages double as ref_type:
pre_start_stage, start_process, biochar_sample, mid_process,
quenching_video, post_quenching, moisture_reading, end_process
```

> **→ dMRV.** Our Batch + side-tables cover much of this. The **`media` table with a
> `ref_sub_type` evidence taxonomy** is the piece we most lack — it gives every photo a
> typed role in the workflow, which is exactly what a verifier wants. Consider adding a
> `media_kind`/`ref_sub_type` to our evidence records.

## B3. API contract (exact paths)

Two JWT services: Identity (`accounts.varahaag.com`) + Operations (`backend.varahaag.com`).

```
# Identity
POST /api/v1/auth/login/otp/                 → LoginOTPResponse {user_full_name, transaction_id, attempt_count}
POST /api/v1/auth/login/otp/resend/
POST /api/v1/auth/login/otp/validate/        → VerifyOTPResponse {token, x_header}
POST /api/v1/auth/token/refresh/             → Token {access_token, refresh_token, token_type}
GET  /api/v1/roles/    GET /api/v1/users/    GET /api/v1/users/login-user/

# Operations — farmers & KYC
GET/POST /api/v2/farmers/    /api/v1/farmers/
POST /api/user/v1/charify_farmer/create/     GET /api/user/v1/charify_farmer/
GET/POST /api/user/v1/charify_farmer/media/  /media/all/  /media/upload/
GET  /api/user/v1/core/check-farmer-mobile/          → {farmer_exist, farmer_info}
GET  /api/user/v1/core/get-farmer-fpic-template/     → {lang, template_url}
GET/POST /api/user/v1/farmer-document/  /all/  /create/

# Farms & sites
GET/POST /api/v2/charify_farms/    GET /api/user/v1/farm/
GET  /api/user/v1/nearest-farm-boundary/     → overlap check

# Media upload (presigned-S3 two-step)
POST UploadMediaNetworkModel → MediaDetails {content_length, content_type, expiry_in, media_type, s3_data}
   → PUT file to s3_data URL   (farmer media uses FarmerMediaS3Data {fields, url} form-POST variant)

# Reference lookups: /core/api/{country,state,district,block,village,bank}/all/
# PIN lookup: https://api.postalpincode.in/pincode/{pin}
```

**Anti-fraud capture envelope — `RequestMetadata`** (wraps every capture; this is
Varaha's mobile-side implementation of Bluelayer's `CaptureMetadata`):
```
RequestMetadata {
  app:      { version_name, version_code, build_type, package_name }
  device:   { manufacturer, model, brand, os_version, api_level }
  system:   { locale, timezone, network_type }
  request:  { timestamp, request_id }
  location: { latitude, longitude, altitude, accuracy, timestamp }
  blur_config
  fov:      { horizontalFOV, verticalFOV, diagonalFOV }
  tilt:     { pitch, roll }
}
```
> FOV + tilt + blur + GPS + device make photo/video evidence tamper-evident.
> **→ dMRV.** We already store `azimuth`, `pitch`, `roll`, `mock_location_enabled` on
> Batch — we're partway there. Adopt the full `RequestMetadata` envelope shape as our
> canonical evidence-capture metadata; it pairs with Bluelayer's server-side geofence
> validation (A4).

## B4. KYC + FPIC (directly relevant to `feature/t5-india`)

**Farmer onboarding flow** (`onboardlibrary`, ordered screens):
```
Personal (name, phone, gender, guardian, DOB, education, area, family size, photo)
 → Identification (Aadhaar India: 12 digits, not starting 0/1; Passport others; NID;
                   store document_last_4_digit ONLY, never full number)
 → Address (driven by CountrySpecificUiConfig — field set + labels vary per country)
 → Bank/payment (bank acct + IFSC + branch OR UPI OR MFS; IFSC→bank lookup)
 → Signature (finger-draw canvas)
 → Read FPIC (English + regional consent PDF from CloudFront)
 → Upload FPIC (signed copy + photo of farmer holding it)
 → Dashboard
```

**`CountrySpecificUiConfig`** (one form, many markets):
```
{ villageFieldLabel, pincodeFieldLabel, stateFieldLabel, districtFieldLabel, blockFieldLabel,
  isOtherVillageNameFieldEnabled, showLocalAddressField, showVillageField, showWardNumberField }
```

**Multi-country payout (`DocumentDetails`):** India = IFSC + branch + account holder +
UPI; International = routing_number + swift_bic_code; MFS = mfs_account_id + mfs_name
(bKash Bangladesh), mfs_kenya_payment_id (M-Pesa Kenya).

**FPIC template selection:** `FPICTemplateRequest {project_type, state_name, district_name}`
→ template URL → download regional+English PDF → sign → upload signed + holding photo.
CloudFront paths reveal a multi-program platform: `/biochar/fpic/...`, `/arr/fpic/...`,
`/regen/...`.

**Pincode auto-fill:** `api.postalpincode.in/pincode/{pin}` → auto-fills district/state
during Indian address entry.

> **→ dMRV.** We just added a Farmer KYC screen (commit `e90b085`). This is a ready
> blueprint for the India onboarding on `feature/t5-india`:
> - Aadhaar validation (12 digits, not starting 0/1) + store only `document_last_4_digit`.
> - Pincode → district/state auto-fill via `api.postalpincode.in`.
> - IFSC → bank lookup; UPI as an alternative payout.
> - The FPIC consent flow (read regional PDF → sign → upload signed + holding photo) is a
>   clean, auditable free-prior-informed-consent implementation to mirror for compliance.

## B5. Dispatch & production state machines

**Dispatch: Draft → In-Transit → Received.** Weight captured at dispatch and *re-captured*
at the facility (`weight_at_facility`), with a locked confirm ("cannot change weight
details") → two-sided mass-balance reconciliation.

**Artisanal production `process_status` stages (sequential):**
```
pre_start_stage → start_process → biochar_sample → mid_process
→ quenching_video → post_quenching → moisture_reading → end_process
```
Each stage requires specific evidence (e.g., `quenching_video` requires a video;
`moisture_reading` requires a meter photo + numeric reading).

**Boundary handling:** WKT geometry, 3 capture modes (draw polygon / GPS-walk / manual
coords), server `nearest-farm-boundary` overlap check ("boundary is overlapping with
existing site") → prevents double-counting land (a real MRV fraud vector).

> **→ dMRV.** The **two-sided weight reconciliation** (dispatch weight vs facility
> re-weigh, locked) is a strong mass-balance gate for biochar credit integrity — worth
> adopting. The **boundary overlap check** prevents land double-counting; relevant if we
> register sourcing polygons.

## B6. Security — what NOT to copy (Varaha's real mistakes)

Varaha shipped these; treat as an anti-checklist:
- **Debug tooling in production** (HIGH): Inspektify (shake-to-open Ktor traffic
  inspector) and Measure.sh APM pointed at a *test* endpoint with key in clear — anyone
  with the device reads all API traffic incl. tokens.
- **Cleartext + no pinning** (HIGH): `usesCleartextTraffic=true`, no
  `networkSecurityConfig`, no cert pinning.
- **PII unencrypted at rest** (MEDIUM): Room plaintext holds farmer names, DOB, mobiles,
  GPS, drawn signatures, ID refs, bank/UPI/MFS payment IDs, FPIC images. Only
  `allowBackup=false` mitigates.
- **Embedded secrets** in the bundle (Maps/Firebase API keys).

**What Varaha did RIGHT** (do copy): Play App Signing v2+v3, PairIP anti-repackaging,
`allowBackup=false`, JWT + refresh + separate tenant `x_header`, and the rich
tamper-evident media provenance envelope (B3).

> **→ dMRV.** We must: (1) never ship debug/inspector tooling in release (we already
> removed the debug-signing fallback, commit `9299a50` — good); (2) encrypt PII at rest
> (SQLCipher for Drift, or field-level encryption) from day one — especially once India
> KYC lands; (3) keep secrets out of the app bundle; (4) TLS pinning for the sync channel.

---

# PART C — Prioritized adoption plan for our dMRV

Ranked by (value × cheapness). Highest leverage first.

| # | Steal | From | Effort | Why |
|---|-------|------|--------|-----|
| 1 | **CSI export field names** (already applied to E23) | Bluelayer A6 | done | Closed our one unverifiable gap |
| 2 | **`sync_status` 7-state enum + central `media` queue + `ref_local_id→ref_id` repoint + manual retry screen** | Varaha B1/B2 | M | Hardens our offline sync; the retry screen is non-negotiable |
| 3 | **`RequestMetadata` capture envelope + server-side EXIF extraction + geofenced file rule** | Varaha B3 + Bluelayer A4 | M | Directly upgrades evidence/anchoring anti-fraud; we're partway (azimuth/pitch/roll already stored) |
| 4 | **India KYC/FPIC blueprint** (Aadhaar validation, pincode auto-fill, IFSC/UPI, FPIC consent flow) | Varaha B4 | M | Directly serves `feature/t5-india`; we just added the KYC screen |
| 5 | **Calc provenance trace on issued credits** (the "explain" *output shape*, not the full AST interpreter) | Bluelayer A1.6 | M–L | Biggest defensibility win; approximate cheaply by serializing our LCA calc steps |
| 6 | **Conservative aggregation (`mean_minus_stddev`) + explicit gap-fill policy** for moisture/temp reduction | Bluelayer A2 | S | Cheap, genuine verifier-respected rigor |
| 7 | **Two-sided weight reconciliation** (dispatch vs facility re-weigh, locked) | Varaha B5 | M | Strong mass-balance integrity gate |
| 8 | **Continuous anomaly incidents** (trigger→ack→resolve) beyond static C1–C10 gates | Bluelayer A3 | L | Later-phase hardening; reuse incident lifecycle fields |
| 9 | **Double-entry credit ledger** (structurally prevents double-issuance) | Bluelayer A5 | L | Evaluate for a future issuance-integrity phase; not P0 |

**Explicitly do NOT do:**
- Do not rewrite our backend as a declarative Model-interpreter (Bluelayer's multi-year
  moat; overkill for our scope).
- Do not invent Rainbow export field names — no captured artifact contains them (E23 TODO stands).
- Do not copy any Varaha security posture from B6.

---

## Provenance of this document

Built 2026-07-15 by reading, in full:
- **Bluelayer:** `bluelayer_complete_architecture_map.md`, `PHASE1_FORMULA_AST_ENGINE.md`,
  `PHASE2_METRICS_ENGINE.md`, `PHASE3_ALERTS_ENGINE.md`, `PHASE4_TELEMETRY_ENGINE.md`,
  `PHASE5_PROJECT_MODEL.md`, `PHASE6_REPORTS_ENGINE.md`, and the raw OpenAPI schema JSON
  (`bluelayer_phase6_reports_schemas_raw.json` for the CSI field set). Location:
  `C:\Users\bit\AppData\Local\WisprFlow\bluelayer_dump\`.
- **Varaha:** the full `REVERSE_ENGINEERING/` doc set (README + 01–10). Location:
  `C:\Users\bit\Downloads\com.varaha.biochar_1.6.2\REVERSE_ENGINEERING\`.

All field names, DDL, enum values, and schema shapes above are quoted from those
captures — they are the competitors' real structures, not our system's. Cross-reference
`EXECUTION_MASTER_PLAN.md` (E23 for the CSI mapping) before writing any of our code.
