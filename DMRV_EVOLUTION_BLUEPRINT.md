# TerraCipher dMRV — Platform Evolution Blueprint
### Circonomy teardown → gap analysis → no-break migration to a long-term scalable platform

**Author role:** CTO / systems architect. **Prime rule:** every phase ships behind the existing test wall (500+ backend tests stay green), every schema change is expand-migrate-contract, nothing user-visible breaks mid-flight.
**Grounding:** all "we have" claims below reference actual code (`backend/models.py`, `backend/routers/*`, `portal/src/*`, `lib/ui/screens/*`). All "they have" claims reference the 9 Circonomy screens captured 23 Jul 2026 (admin.circonomy.co).

---

## 1 · CIRCONOMY TEARDOWN (what they've actually built, screen by screen)

### 1.1 Production batch registry (`/dashboard/production/batches`, `/iot-artisanal/production/batches`)
- **Scale:** 35.3K batches paginated (25/row pages), multi-country (India ID, Namibia NA, Kenya KE, Indonesia…).
- **Hierarchy filters:** Company selector → network tabs (`All / Artisan Pro / Csink Network`) → status filter → biomass filter → date presets (`All / MTD / YTD / Custom`) → **standard selector (CSI / Rainbow)** → **mode selector (Artisanal / IoT-artisanal)**.
- **Structured, human-readable batch IDs:** `NA02A001P06S1K07B22072601` — country+region (`NA02`), artisan network (`A001`), production site (`P06`), slot (`S1`), kiln (`K07`), batch date+seq (`B22072601`). The ID *is* the provenance path.
- **Columns:** date+time, batch ID, biomass chip (species), network/kiln (with **`(IoT)` / `(Non-IoT)` tag per kiln**), site/farmer, **IN (kg)** biomass, **OUT (L)** biochar (volumetric!), **status lifecycle** (`Started` → `Not Assessed` → assessed states).

### 1.2 Batch detail — the "C-Sink Timeline"
- Staged custody chain, each stage a timeline node with its own media gallery: **Chimney → Firing (photos + videos) → Kiln process biochar addition → Pre-quenching → Quenching → Temperature → Mixing → Packaging → Application** — with explicit **empty states** ("No mixing records") so absence is visible.
- Batch header: production **Started / Ended timestamps** (22/07/2026 6:32 PM → 9:21 PM), headline **TEMPERATURE 908.3 °C**, **Download** (evidence pack).

### 1.3 Real-time thermal mapping (the chart you want to mimic)
- Multi-series line chart, **4 thermocouples (T1–T4) as separate colored series**, full burn curve start→finish, legend dots, **MAX badge (477.3 °C)** pinned top-right, clean axis (0–500 °C gridlines). Continuous recording, not end-of-burn upload.

### 1.4 Load telemetry
- **Continuous weight tracking** step-curve for the whole burn (feedstock loads visible as steps, ~0→450 kg spike shape), chips: **BIOMASS 121.6 kg / BIOCHAR 40.9 kg**, footer **LAST LOAD 16.25 kg**. Mass balance per batch, machine-recorded.

### 1.5 Biomass intake ledger (`/dashboard/production/biomass?startDate…&period=month`)
- Date-ranged feedstock arrivals: site + network, species chip, **kg quantity**, source tag (**Manual** vs device), **linked batch-ID chips**, thumbnail photo evidence per row.

### 1.6 Distribution / Sink (`/dashboard/production/sink`)
- Distribution rows: network, recipient (name + phone), type (`Biochar-Solid Manure` / `Biochar - Only`), **PACKED** chip, transport mode.
- **Distribution Details panel:** journey metrics (**distance 9.20 km, vehicle Tractor KTWB463A, fuel Diesel, est. emissions 1,122.40 kgCO₂e**), recipient with phone, **Google Map with route line**, **CARGO MANIFEST** (total 518.59 L, 4× Gunia bags, sack 50 kg, product chips), **Application Evidences** section (state: "Application Not Started").

### 1.7 What to note and NOT copy
- Their "Manual" source tags carry no cryptographic integrity — typed data at scale. Our signing layer is the differentiator; keep it mandatory.
- Litres-first biochar measurement (C-Sink volumetric convention) — we should **add** volume, not replace mass.

---

## 2 · WHAT WE HAVE TODAY (grounded in code)

**Strengths (keep, never regress):**
- **Evidence integrity no one matches:** every device write behind `verify_signature` HMAC (`routers/evidence.py`), per-device keys (`DeviceKey`), SHA-256 on media (`MediaFile.sha256_hash`), signed LCA audit (`Batch.lca_signature` + versioned `lca_signature_key_id`), append-only `AuditEvent`.
- **Compliance engine:** C0–C10 hard gates, `provisional`/`provisional_reasons`, DB-level invariants (`ck_batches_lab_h_corg_range`), CSI + Rainbow exports, issuance behind typed confirmation.
- **Entity breadth already close to theirs:** `Batch` (rich), `PyrolysisTelemetry`, `YieldMetrics`, `MoistureReading`, `CompositePileSample`, `EndUseApplication`, `TransportEvent`, `Dispatch`+`DispatchSite`+`Facility` (weight-delta reconciliation!), `Farmer`+KYC docs, `Kiln`, `Project`, `SourceParcel`, `FieldWalkTrack`, `BulkDensityTest`, org-scoped `PortalUser`.
- **Offline-first mobile** (18 Flutter screens incl. `pyrolysis_screen`, `yield_scale_screen`, `sync_health_screen`, `proof_wallet_screen`, `secure_camera_screen`) + verifier portal + registry QR flows.

**Structural gaps (why we can't just "add a chart"):**
1. **Telemetry is a document, not a stream.** `PyrolysisTelemetry.payload_json` holds `temperature_readings: [floats]` — single logical channel, no per-reading timestamps, no channel identity, uploaded once. Live T1–T4 charts are impossible on this shape.
2. **Weight is a scalar, not a curve.** `YieldMetrics.payload_json` = final wet yield only. No load events, no mass-balance curve.
3. **Evidence stages are implicit.** Portal groups media by `capture_type` (`STEP_ORDER` in `BatchDetail.tsx`) — close to a timeline, but there's no stage entity with started/ended/empty-state semantics.
4. **Hierarchy is flat.** `org_id` scoping exists, but no Company→Network→Site→Kiln tree; `Kiln` has no site linkage, no IoT flag.
5. **IDs are UUIDs only.** Zero provenance readable by humans; operations teams cannot speak UUIDs on the phone.
6. **Dispatch lacks journey intelligence.** `Dispatch` has weights/driver/truck, but no distance, fuel, emissions estimate, cargo manifest lines, recipient contact, or application-evidence linkage.
7. **No date-ranged analytics ledgers** (biomass intake view, MTD/YTD presets).
8. **JSON-blob evidence rows** (`payload_json` TEXT everywhere) are fine as signed snapshots, but unqueryable for analytics at 35K-batch scale.

---

## 3 · GAP MATRIX

| Capability | Circonomy | Us today | Verdict |
|---|---|---|---|
| 4-channel live thermal mapping | ✅ T1–T4, live | ⚠ 1 array, end-of-burn | **BUILD (M2)** |
| Continuous load telemetry + mass balance | ✅ | ⚠ final scalar | **BUILD (M2)** |
| Staged evidence timeline w/ empty states | ✅ | ⚠ capture-type groups | **BUILD (M3, mostly UI+view)** |
| Human-readable provenance batch IDs | ✅ | ❌ UUID only | **BUILD (M1, additive)** |
| Company→Network→Site→Kiln hierarchy | ✅ | ⚠ org_id + flat Kiln/Facility | **BUILD (M1)** |
| IoT / Non-IoT kiln distinction | ✅ | ❌ | M1 (one column) |
| Journey metrics + emissions + manifest | ✅ | ⚠ Dispatch weights only | **BUILD (M4)** |
| Route map on distribution | ✅ Google Maps | ❌ (Leaflet already in portal) | M4 (Leaflet, no new dep) |
| Biomass intake ledger + MTD/YTD | ✅ | ❌ | M5 |
| Volumetric (L) biochar measurement | ✅ | ❌ kg only | M2 (add field, never replace kg) |
| Assessment lifecycle states | ✅ | ⚠ RECEIVED/ISSUED + provisional | M3 (map, don't rename) |
| Evidence pack download | ✅ | ✅ print pack | parity |
| Multi-standard (CSI/Rainbow) | ✅ selector | ✅ exports live | parity |
| Cryptographic evidence integrity | ❌ ("Manual" typed rows) | ✅ | **OUR MOAT — extend to sensors** |
| Hard compliance gating | ❌ visible | ✅ C0–C10 | OUR MOAT |
| Farmer KYC + PII masking | partial | ✅ | OUR MOAT |

---

## 4 · TARGET ARCHITECTURE (the 0.1% version — platform, not patch)

### 4.1 New plane: **Telemetry Ingestion & Time-Series Store**
The one genuinely new subsystem. Everything else is extension.

```
[Kiln Edge Unit]                      [Backend]                       [Portal]
 4× K-type thermocouple                POST /api/v2/telemetry/ingest    GET  /portal/batches/{id}/telemetry
 (MAX31855) + 4× load cell             (device-HMAC signed chunks)      ?channels=T1..T4,LOAD&res=10s
 (HX711, summed)                        │                                │
 ESP32 · 1 Hz sample                    ▼                                ▼
 → 10 s aggregate                      telemetry_points                 SSE /portal/streams/burn/{id}
 → flash ring buffer (72 h)            (narrow table, partitioned)      (live view while burn active)
 → chunk = {device, batch, ch,         + telemetry_chunks
    t0..tN, values[], HMAC}            (signed raw chunks, audit)
```

**Schema (additive, two tables):**
```sql
-- the audit truth: exactly what the device signed, never rewritten
CREATE TABLE telemetry_chunks (
  id BIGSERIAL PRIMARY KEY,
  batch_uuid UUID NOT NULL REFERENCES batches(batch_uuid),
  device_id VARCHAR(255) NOT NULL,
  channel VARCHAR(16) NOT NULL,          -- 'T1'..'T4','LOAD'
  t_start TIMESTAMPTZ NOT NULL, t_end TIMESTAMPTZ NOT NULL,
  payload_json TEXT NOT NULL,            -- raw values + sample period
  signature VARCHAR(128) NOT NULL,       -- device HMAC (reuses DeviceKey)
  received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- the query plane: unpacked points, monthly partitions, BRIN index on ts
CREATE TABLE telemetry_points (
  batch_uuid UUID NOT NULL, channel VARCHAR(16) NOT NULL,
  ts TIMESTAMPTZ NOT NULL, value REAL NOT NULL
) PARTITION BY RANGE (ts);
```
- **Scale math:** 1,000 kilns × 5 channels × 6 points/min × 4 h/burn/day ≈ 7.2 M points/day worst case → trivially fine in partitioned Postgres with BRIN; TimescaleDB is an optional later swap, not a dependency now.
- **Downsampling policy:** raw 10 s kept 90 days → 1 min rollups kept forever (`telemetry_rollup_1m` materialized nightly). Charts read rollups by default.
- **Integrity story extends the moat:** *every chunk signed at the edge with the same `DeviceKey` HMAC scheme the app uses* — Circonomy's IoT rows are trusted-because-server; ours are provable.
- **Live view:** while a burn is open, portal subscribes via SSE (plain `EventSource`, no new deps); backend fans out from the ingest path. Offline kilns backfill from ring buffer on reconnect — the chart just fills in.
- **Compatibility bridge:** `recompute_batch_credit`'s C3 gate currently reads `payload_json.temperature_readings`. A shim view assembles the same array from `telemetry_points` when a batch has streaming data, so the credit engine is untouched in M2 (contract phase later).

### 4.2 Hardware spec (your 4-thermocouple plan, productionized)
- **Placement:** T1/T2/T3 on the cone wall at 120° spacing, T1 at ⅓ height, T2 at ⅔ height, T3 opposite T1 at ½ height (catches asymmetric burns); **T4 center of the base plate** (your "bottom base") — the permanence-relevant sustained-heat reading. All K-type, MAX31855 amplifiers (cold-junction compensated, 14-bit).
- **Load:** 4× 200 kg HX711 load cells under the stand feet, summed = live gross weight; delta-detection emits `LOAD` events (your Kon-Tiki designer's stand geometry already defines the four mount points).
- **Edge unit:** ESP32-S3, 1 Hz sampling → 10 s mean/max aggregation, 72 h flash ring buffer, RTC + GPS time, LTE-M/2G fallback, per-device key provisioned via the existing `EnrollmentToken` flow. Firmware signs every chunk (HMAC-SHA256, same scheme as `security.verify_signature`).
- **Failure honesty:** gaps are rendered as gaps (no interpolation — "never fabricate" is already the codebase's stated rule; sensors obey it too).

### 4.3 Hierarchy & identity (M1 — pure additive)
```
organizations (exists as org_id strings → promote to table)
 └─ networks            (NEW: e.g. "Artisan Pro 7")
     └─ production_sites (extend Facility: network_id, site_code)
         └─ kilns        (add: site_id FK, kiln_code, is_iot BOOL)
             └─ batches  (add: batch_code VARCHAR(32) UNIQUE, site_id, network_id denorm)
```
- **Batch code generator** (display identity; UUID remains the key everywhere):
  `{country}{org#}{network}{site}{slot}{kiln}B{DDMMYY}{seq}` → `IN01A001P03S2K07B230726 01`. Deterministic, backfillable for all 7,356+ historical batches, and **it matches how ops teams already talk**.
- Portal filter bar gains Company/Network/Site cascading selects (same `FilterBar` pattern, server-side params already cursor-paginated).

### 4.4 Stage timeline (M3 — mostly a projection, not a migration)
- New `batch_stage_events` table: `(batch_uuid, stage, started_at, ended_at, source)` — written going forward by app/edge events; **backfilled for old batches by projecting existing data** (capture_type timestamps, telemetry t_start/t_end, dispatch/application rows).
- Stage vocabulary (superset of Circonomy's): `sourcing → moisture → loading → firing → biochar_addition → pre_quenching → quenching → yield → mixing → packaging → dispatch → application → lab`.
- Portal `BatchDetail` renders the timeline from ONE endpoint `GET /portal/batches/{id}/timeline` (stages + media + telemetry summaries + empty states). Our current `STEP_ORDER` gallery becomes the M3 fallback for pre-migration batches — **both render paths ship simultaneously; zero break**.

### 4.5 Distribution intelligence (M4 — extends `Dispatch`, no reshape)
Additive columns/tables: `dispatch_journeys` (distance_km from GPS trace or manual, vehicle_reg, fuel_type, **emissions_kg = distance × factor table** — factors versioned like the LCA constants), `dispatch_manifest_lines` (container type, count, unit, volume_l, mass_kg), recipient contact on `DispatchSite`, and a `dispatch → end_use_application` linkage so "Application evidence: not started / n records" is computable. Route map = Leaflet polyline (already a dependency via `ParcelMap`) — no Google dependency.
Emissions estimates feed the LCA transport deduction we already compute — **closing the loop Circonomy leaves open** (they display emissions; we subtract them from credits).

### 4.6 Analytics ledgers (M5)
- `GET /portal/ledgers/biomass?from&to&bucket` (intake rows + aggregates) and MTD/YTD presets in the portal FilterBar — served from indexed base tables now; materialized `ledger_daily` if p95 > 300 ms.
- Volumetric support: `yield_volume_l` + `bulk_density_applied` on yield ingestion (C-Sink convention), kg remains canonical for LCA.

### 4.7 Charting system (portal — extend, don't adopt a chart lib)
- `ThermalMapChart`: multi-series SVG line chart (pattern of existing `TemperatureChart`, which already does clean polylines): 4 series with direct end-labels T1–T4, MAX badge chip (top-right, `--status-warning-fg` when >450 °C gate satisfied — the compliance tie-in they don't have), hairline grid ≤4, `preserveAspectRatio="none"`, time x-axis from real timestamps, live-append via SSE.
- `LoadTelemetryChart`: step-after line, load-event markers, BIOMASS/BIOCHAR/LAST-LOAD chips (mono, tabular).
- Both live in `src/ui/` per the audit's component rules; tokens only.

---

## 5 · MIGRATION PLAN (no-break, phased, each phase independently shippable)

**Global rules (every phase):**
- Expand-migrate-contract only: new tables/columns first (nullable/defaulted), dual-write window, backfill script, reads switched behind a flag, contract (drop/rename) earliest one phase later.
- New endpoint shapes go to `/api/v2/…` or new portal paths; existing `/api/v1` responses NEVER change shape (the frozen `portal/src/api.ts` contract survives untouched until portal opts in).
- Per-org feature flags via existing `AppConfig` — Circonomy-parity features roll out org-by-org.
- Gate: `pytest -q` (500+) + `npm run verify` + one seeded staging replay before merge; Alembic migration has a tested downgrade.

| Phase | Scope | Key deliverables | Risk | Duration |
|---|---|---|---|---|
| **M0** | Foundations | Postgres partitioning enabled in compose; `AppConfig` flag plumbing; staging seed replay harness | none — infra only | 1 wk |
| **M1** | Identity & hierarchy | `networks`, site extension, kiln `site_id`+`is_iot`, `batch_code` + backfill for all historical batches; portal cascading filters + code shown beside short-UUID (both visible during transition) | low — all additive | 1–2 wk |
| **M2** | **Telemetry plane** | `telemetry_chunks`/`points`, `/api/v2/telemetry/ingest` (device-HMAC), SSE stream, rollups, credit-engine shim view; `ThermalMapChart` + `LoadTelemetryChart` reading new endpoint, falling back to legacy payload arrays for old batches | medium — new subsystem, but zero writes to existing tables | 2–3 wk |
| **M2h** | Hardware pilot | 2 edge units built to §4.2 spec on live kilns; ring-buffer/backfill soak test; firmware signing against `EnrollmentToken` provisioning | field risk, isolated | parallel w/ M2 |
| **M3** | Stage timeline | `batch_stage_events` + projection backfill; `/portal/batches/{id}/timeline`; BatchDetail timeline UI with empty states; status-label mapping (`RECEIVED`→"In production", assessed states derived from compliance) — labels only, enum untouched | low | 1–2 wk |
| **M4** | Distribution intelligence | journey/manifest tables, emissions factor table (versioned), recipient contact, application linkage, Leaflet route map, LCA transport-deduction wiring | medium (touches credit math — behind flag, provisional-safe: missing journey ⇒ existing conservative default) | 2 wk |
| **M5** | Ledgers & analytics | biomass ledger endpoint + MTD/YTD presets; volumetric yield fields; ledger UI | low | 1 wk |
| **M6** | Contract & polish | Retire legacy telemetry read path once 100% batches ≥ M2 era; drop dual renders; perf pass (p95 budgets); portal remediation blueprint (`portal/audit/REMEDIATION_BLUEPRINT.md`) executed alongside | low | 1 wk |

**Sequencing logic:** M1 before M2 because telemetry chunks want kiln/site identity; M3 after M2 because the timeline's firing stage is derived from telemetry start/end; M4/M5 independent after M1.

## 6 · WHAT WE DELIBERATELY DO BETTER (not just parity)
1. **Signed sensors, not trusted sensors** — every telemetry chunk device-HMAC'd; their IoT rows are server-trusted.
2. **Charts tied to compliance** — MAX badge turns semantic when the ≥450 °C gate passes; their chart is decoration, ours is a gate visual.
3. **Emissions that bite** — journey emissions flow into the LCA deduction, not just a display field.
4. **Absence is evidence** — empty stages render explicitly AND feed `provisional_reasons`; their empty states are cosmetic.
5. **No "Manual" backdoor** — unsigned rows stay impossible; manual corrections go through the audited admin channel (`AuditEvent`).

## 7 · IMMEDIATE NEXT ACTIONS (this fortnight)
1. M0 flags + partitioning groundwork (backend, 2 days).
2. M1 schema PR + `batch_code` generator with backfill dry-run against the seeded DB (3 days).
3. Order hardware for 2 edge units (MAX31855 ×8, K-type probes ×8, HX711+cells ×8, ESP32-S3 ×2) — long lead item, order now.
4. `ThermalMapChart` built against a fixture stream (front-end can start before ingestion lands — SSE contract in §4.1 is the interface).
5. Write `/api/v2/telemetry/ingest` OpenAPI stub + firmware chunk format doc so hardware and backend converge on one contract.
