# Telemetry Upgrade Plan — matching Circonomy's thermal + load telemetry

Goal: bring our batch-detail telemetry up to the level of Circonomy's
`admin.circonomy.co/.../batches/{id}/details`, which shows (1) **4-thermocouple
real-time thermal mapping** (T1–T4, continuous over the full burn), (2)
**continuous load telemetry** (biomass in / biochar out, weight-vs-time), and
(3) a **C-Sink process timeline** (Mixing / Packaging / Application).

---

## 1. What Circonomy is doing (from the reference screen)

| Feature | Detail observed |
|---|---|
| Thermal mapping | 4 series **T1 T2 T3 T4**, continuous curves start→finish, `MAX: 472.3 °C` callout, colored-dot legend, real y-axis (0–500 °C) |
| Load telemetry | "Continuous weight tracking", `BIOMASS 121.6 kg` / `BIOCHAR 40.9 kg` toggle, a weight-vs-time curve with a load spike |
| C-Sink timeline | Vertical stage rail: Mixing / Packaging / Application, each with a "No … records" empty state |

Their sensor plan (per the meeting): **4 thermocouples — 3 inside the kiln at
different heights + 1 at the bottom/base — sampling continuously for the whole
burn.**

---

## 2. What we have today (verified in code)

### Thermal
- **DB:** `pyrolysis_telemetry` is a single JSON blob, **one row per batch**
  (`backend/models.py:41-55`, `batch_uuid` unique).
- **Shape:** `TelemetryPayload` (`backend/schemas.py:263-291`) stores
  `temperature_readings: list[float]` — **one flat array, single sensor, no
  timestamps**, plus scalar `min_temp` / `max_temp` and burn start/end strings.
  There is **no T1–T4 / channel / thermocouple concept anywhere**.
- **Chart:** `TemperatureChart` plots one `readings: number[]` series against
  index (not time), 3 y-ticks, no legend (`components/TemperatureChart`).
- **Ingestion:** `POST /api/v1/telemetry` — **one whole-burn upload per batch**
  (device buffers the full burn, uploads once; `routers/evidence.py:91-128`).
- **Served:** `telemetry = { temperature_readings, min_temp, max_temp,
  burn_start_timestamp, burn_end_timestamp }` (`portal/routes.py:1166-1188`).

### Weight / load
- **No continuous weight series exists.** Only discrete scalars: `wet_yield_kg`,
  `biomass_input_kg` (`models.py:469,493`), dispatch source/facility weigh
  (`models.py:701-710`), transport-leg `weight_kg`. Batch-detail even documents
  this: *"Weight is a single post-burn measurement, not a time series."*

### Timeline
- **No process-timeline table.** Stages are inferred from evidence rows'
  `received_at` + `smoke_evidence` stage labels (`flame_curtain`, `quenching`,
  `flame_height`; `corroboration.py:230`). No mixing/packaging/application
  ordering (application is its own table, `EndUseApplication`).

### ⚠️ Compliance dependency (the important one)
`temperature_readings` is **load-bearing for credit eligibility**:
- `MIN_TEMPERATURE_SAMPLES = 60` — a burn needs ≥60 samples to qualify.
- `derive_min_temp` = `min(temperature_readings)`.
- Plausibility gate: **≥50 % of samples ≥ 350 °C** or the batch is flagged
  `insufficient_temp_sustain` (`corroboration.py:486-539`).

Any move to 4 channels forces a **methodology decision**: is the "min temp" and
the "≥350 °C sustain" rule evaluated on the *interior* thermocouples only
(T1–T3), on *all four*, or per-channel? The base sensor (T4) runs cooler by
design, so including it would wrongly fail good burns. **This is a
carbon-methodology call, not just an engineering one — decide it before building.**

---

## 3. The core gap

Circonomy's UI is downstream of a **richer data contract** than ours. Getting
the *look* is a frontend job; getting the *real data* is a firmware + schema +
ingestion + methodology job. These are separable and should be phased.

Target telemetry contract (v2, additive/back-compatible):

```jsonc
telemetry: {
  "version": 2,
  "sample_interval_s": 5,                 // fixed cadence → x-axis is index*interval
  "burn_start_timestamp": "...",
  "burn_end_timestamp": "...",
  "channels": [                           // NEW: per-thermocouple
    { "id": "T1", "placement": "internal_upper", "readings": [/* °C */] },
    { "id": "T2", "placement": "internal_mid",   "readings": [/* °C */] },
    { "id": "T3", "placement": "internal_lower", "readings": [/* °C */] },
    { "id": "T4", "placement": "base",           "readings": [/* °C */] }
  ],
  "min_temp": 0, "max_temp": 0,           // still derived server-side
  // legacy: temperature_readings kept as the primary interior channel so old
  // clients AND current corroboration keep working unchanged.
  "temperature_readings": [/* = T-interior aggregate */]
}

weight_series: {                          // NEW, optional: continuous load cell
  "sample_interval_s": 5,
  "readings_kg": [/* gross load-cell mass over time */],
  "biomass_kg": 121.6,                    // discrete markers we already capture
  "biochar_kg": 40.9
}
```

---

## 4. Migration plan (phased)

### Phase A — Frontend "professional look," current data (fast, low-risk)
No backend/hardware change. Closes most of the *visual* gap immediately, honestly.
1. **TemperatureChart v2** (rewrite, back-compatible): real x-axis (time =
   `index * sample_interval_s`), gridlines + y-axis labels (already partly done
   in P6.3), a `MAX xxx °C` callout, and **multi-series support** — accept
   `channels[]`; when only `temperature_readings` exists, render it as a single
   "Interior" series. Colored-dot legend. Downsample >~600 points for perf.
2. **LoadTelemetry panel:** with today's data we can only show the two discrete
   stats (biomass/biochar) honestly — render them as a labeled pair, and gate
   the *curve* behind `weight_series` existing (no fake curve). This matches our
   existing honesty rule.
3. **Process timeline:** reuse the capture stages + `EndUseApplication` we
   already have to render a Circonomy-style vertical rail with real "No …
   records" empty states.

*Deliverable: the page looks ~80 % like Circonomy with zero new data.* Clearly
labels which panels are live vs awaiting-hardware.

### Phase B — Backend v2 contract (medium; the real capability)
1. **Schema:** extend `TelemetryPayload` with optional `channels[]` +
   `sample_interval_s`; add optional `weight_series`. Keep `temperature_readings`
   required-or-derived for back-compat.
2. **Ingestion:** `POST /api/v1/telemetry` accepts v1 *and* v2 payloads (version
   sniff). Consider a chunked variant if full-burn 4-channel arrays get large
   (4 × ~1 h @ 5 s ≈ 2 880 floats — fine as one upload; only revisit if cadence
   drops below ~1 s).
3. **Corroboration:** implement the agreed multi-channel semantics (recommend:
   min/sustain over interior channels T1–T3; base T4 stored for context only).
   Back-fill `temperature_readings` = interior aggregate so nothing downstream
   breaks.
4. **Serving:** `portal/routes.py` batch-detail returns `channels` +
   `weight_series` when present, else the legacy fields.

### Phase C — Field hardware / firmware (long pole, NOT software-only)
1. 4 thermocouples wired at **3 interior heights + 1 base**; a **continuous
   load cell** under the kiln.
2. Firmware: fixed sample cadence, ring-buffer the full burn, upload v2 payload
   on completion (same Ed25519 signed-body auth we already use).
3. Calibration + placement SOP so T1–T4 mean the same thing across kilns.

---

## 5. Sequencing & the one decision to make first

```
Phase A (frontend look)  ──►  ships now, no dependencies
Phase B (backend v2)     ──►  needs the methodology decision (§2 ⚠)
Phase C (hardware)       ──►  gates real 4-channel + weight data; longest lead
```

**Blocking decision for the meeting:** define the multi-thermocouple compliance
rule (which channels the ≥350 °C / min-temp gates evaluate). Everything in
Phase B/C keys off that. Recommendation: **interior channels drive compliance,
base is context** — but that's a methodology call for the carbon side to ratify.

**"Mimic exactly" caveat:** the professional *appearance* is achievable in
Phase A within our current data; the *4-thermocouple, full-burn, continuous
weight* data itself cannot be faked — it requires Phase C hardware in the field.
The plan gets us visual parity now and real data as the hardware rolls out.
