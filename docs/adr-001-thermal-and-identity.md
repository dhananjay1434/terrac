# ADR-001 — Thermal compliance model & batch-code identity
**Status:** DECIDED (CPO/architect call, 2026-07-27) · Supersedes the two open items in `docs/parallel-lane-stitch-notes.md`
**Decided by:** CPO/system-architect review with literature + code verification.
**Verification basis:** `backend/corroboration.py` (`derive_min_temp`, `PYROLYSIS_MIN_C=350.0`, `TEMP_SUSTAIN_MIN_FRACTION=0.5`, `MIN_TEMPERATURE_SAMPLES=60`); Kon-Tiki literature (Schmidt/Taylor, Biochar Journal); Global Artisan C-Sink standard (Carbon Standards International, in force 2024-06-15).

---

# PART A — THERMAL COMPLIANCE MODEL

## A0 · The finding that forced this ADR (a real defect in the M2.5 spec)
Legacy telemetry is **app-captured spot readings taken during the hot phase** of a burn. Continuous 1 Hz sensors record something categorically different: **the entire thermal history, including ambient ramp-up and post-quench cool-down.**

Feeding that raw history into the existing checks silently punishes instrumented kilns:
- `derive_min_temp` = `min(readings)` → becomes ~ambient (20 °C) instead of ~400 °C.
- `TEMP_SUSTAIN_MIN_FRACTION` (≥50 % of samples ≥350 °C) → a long monitored cool-down can drag a legitimate burn under 50 %.

That directly violates **Global Rule 10** ("sensor data may never make a batch less eligible than the same batch on app evidence"). The M2.5 spec as written ("resample all points, gaps excluded") would have shipped this. **Fix is A3 below — mandatory.**

## A1 · Sensor hardware — CONFIRMED
- **Type K thermocouples** are correct and stay. Range −200…+1260 °C covers the real envelope: Kon-Tiki pyrolysis just below the flame curtain runs **680–750 °C**, working temperature **650–700 °C**, and observed peaks reach ~**900 °C** (Circonomy screen showed 908.3 °C). K-type has headroom; J/T-type do not — do not substitute.
- Amplifier MAX31855 (cold-junction compensated) confirmed adequate. Probe sheath: mineral-insulated Inconel or SS310 (not SS304 — scaling above 870 °C).
- **Placement (locked):** T1 wall ⅓ height · T2 wall ⅔ height · T3 wall ½ height opposite T1 · **T4 base-plate centre**.

## A2 · Compliance channels — DECIDED: `COMPLIANCE_CHANNELS = ("T1","T2","T3")`
**T4 (base) is CONTEXT ONLY — stored, charted, never in a compliance computation.**

Rationale (literature-backed, not preference): in Kon-Tiki flame-curtain pyrolysis the zone **below the main pyrolysis front legitimately cools to 150–450 °C** as fresh feedstock layers are added. A base-plate probe therefore *correctly* reads far below the wall probes on a perfectly good burn. Including T4 in any min- or fraction-based test would fail compliant batches — a false negative that costs real credits.

T4's real jobs: (i) detecting under-fired bottom layers as an *operator quality signal*, (ii) future char-quality research, (iii) probe-fault detection.

## A3 · The burn window — NEW, MANDATORY (fixes A0)
The compliance array is built from the **active pyrolysis window only**, never the full recording.

```
burn_start := first timestamp where max(T1,T2,T3) >= PYROLYSIS_MIN_C (350 °C)
burn_end   := last  timestamp where max(T1,T2,T3) >= PYROLYSIS_MIN_C (350 °C)
compliance_array := 10 s-bucketed max(T1,T2,T3) for ts in [burn_start, burn_end], gaps excluded
```
- Ramp-up and cool-down are **excluded from compliance** but **retained in storage and charts** (the chart shows the true full curve; the gate sees the burn).
- If fewer than `MIN_TEMPERATURE_SAMPLES` (60) buckets survive → return `None` (no claim), exactly like a short legacy log. Never a fabricated pass.
- Gaps still excluded (audit A4) → a gap can only shorten the window, never extend eligibility. Conservative direction preserved.
- **Parity test is the acceptance criterion:** an instrumented batch and an equivalent legacy batch must produce the *same* compliance outcome. This is a required test in M2.5.

## A4 · Threshold ladder (single source of truth — operators, portal, firmware)
| Level | Value | Meaning | Where enforced |
|---|---|---|---|
| Plausibility floor | **350 °C** | below this the "biochar" claim is physically implausible; also the burn-window boundary | `PYROLYSIS_MIN_C` (existing) |
| Sustain fraction | **≥50 %** of in-window buckets ≥350 °C | substantiates a sustained burn | `TEMP_SUSTAIN_MIN_FRACTION` (existing) |
| **C3 compliance gate** | **peak ≥450 °C sustained** | the credit gate shown on the checklist | existing C3 logic — unchanged |
| **Operator target band** | **650–700 °C** | the working temperature good Kon-Tiki practice aims for; where smoke goes clear | portal/app guidance only, never a gate |
| Upper watch | **>900 °C** | probe/'runaway' watch; log, don't block | portal advisory |
| T4 context band | **150–450 °C** | *expected* base range — NOT a failure | context only |
| T4 fault hint | `<100 °C` while T1–T3 >500 °C for >10 min | probable probe/wiring fault | portal advisory chip |

**Operator-facing rule of thumb (put this on the app/portal, in this wording):**
> *Aim for 650–700 °C at the wall. Below 450 °C the batch won't meet C3. Below 350 °C it isn't pyrolysis. The base reading runs cooler than the walls — that's normal.*

## A5 · Implementation deltas (exact)
1. `backend/telemetry_bridge.py` (M2.5) — module header constants, verbatim:
```python
COMPLIANCE_CHANNELS: tuple[str, ...] = ("T1", "T2", "T3")  # ADR-001 A2 — T4 is context only
BURN_WINDOW_FLOOR_C: float = 350.0                          # ADR-001 A3 — mirrors PYROLYSIS_MIN_C
```
   Implement the A3 window algorithm before resampling. Import the floor from `corroboration.PYROLYSIS_MIN_C` rather than duplicating the literal if the import is clean.
2. M2.5 tests gain the **parity test** (instrumented vs equivalent legacy → identical verdict) and a **ramp-up/cool-down test** (full-history batch must NOT fail where its hot-phase-only twin passes).
3. Chart (`ThermalMapChart`) keeps rendering all four channels including T4 — presentation is unaffected by the compliance decision. Optionally shade the in-window region at the M2 stitch.
4. `docs/edge-firmware-contract.md` §3 already says "firmware sends T4; the backend decides" — that stays correct; add a pointer to this ADR.

## A6 · Still deferred to methodology sign-off (does NOT block engineering)
Whether a **multi-probe** claim (max across T1–T3) is the registry-preferred aggregation vs. a single designated probe. We ship `max(T1..T3)` because it matches the legacy single-probe semantics most closely (the app operator measured the hot zone). If the auditor later requires a single nominated probe, it is a one-constant change. **`telemetry_v2` may be enabled in production once a methodology reviewer initials this section** — engineering is not blocked in the meantime.

---

# PART B — BATCH-CODE IDENTITY (unblocks M1.3)

## B1 · Decision: explicit ordinals on entities — assign, don't derive
`make_batch_code` needs small integers; the schema has free-form strings. **We add the numbers as first-class, permanent attributes** rather than deriving them.

Rejected alternatives and why:
- *Hash/derive from `org_id` strings* — unreadable, and a rename silently changes a permanent code.
- *Parse existing `site_code`/`kiln_code`* — circular (those are the codes we're generating).
- *Sequence-per-batch only* — loses the provenance path, which is the whole point of the format.

## B2 · Schema (additive, nullable, one migration in the coordinator's lane)
| Table | New column | Rule |
|---|---|---|
| `networks` | `org_ordinal SMALLINT NULL` | 0–99, unique per `org_id` |
| `networks` | `network_code VARCHAR(4) NULL` | `^[A-Z]\d{3}$` (e.g. `A001`), unique per `org_id` |
| `facilities` | `site_ordinal SMALLINT NULL` | 0–99, unique per `network_id` |
| `kilns` | `kiln_ordinal SMALLINT NULL` | 0–99, unique per `site_id` |
| `networks` | `country_code CHAR(2) NULL` | ISO-3166-1 alpha-2, e.g. `IN` |
All nullable → nothing breaks; a NULL anywhere in the chain simply leaves `batch_code` NULL.

## B3 · Allocation service (new pure-ish module `backend/ordinals.py`)
`allocate_ordinal(session, kind, parent_id) -> int` = `max(existing for that parent) + 1`, inside the caller's transaction, protected by the unique constraint (retry once on conflict). **Ordinals are never reused** — a decommissioned kiln keeps its number forever, because historical codes must stay resolvable.
`network_code` = `"A" + f"{org_ordinal_of_network:03d}"` at creation (letter reserved for a future partition dimension; `A` for all current networks).

## B4 · Backfill order (unblocks M1.3, all `--dry-run` first)
1. Assign `org_ordinal` per distinct `org_id`, ordered by first-seen `created_at`.
2. Assign `network_code` per network.
3. Assign `site_ordinal` per facility within its network; `kiln_ordinal` per kiln within its site.
4. Set `country_code` — default `IN` for existing rows (all current operations are India; single documented default, not a guess per-row).
5. **Then** re-run `backfill_batch_codes.py` unchanged — it now finds complete lineage and generates codes; anything still incomplete stays NULL (audit A3 preserved).
`slot` continues to come from `slot_for(received_at)` (IST hour) — already shipped in M1.2.

## B5 · Operational rules
- A batch's code is written **once** and never regenerated, even if a kiln is later re-parented (the code records where it *was made*).
- Portal shows `batch_code ?? shortId(uuid)` — already implemented in M1.4, no change.
- New entities get ordinals at creation from `allocate_ordinal`, so the backfill is a one-time catch-up, not a recurring job.

---

# EXECUTION ORDER (what happens next, in order)
1. **Coordinator, M1.3-unblock:** migration for B2 + `backend/ordinals.py` + allocation wiring + the B4 backfill sequence, then re-run `backfill_batch_codes.py`. (M1.3 moves from BLOCKED to done.)
2. **Coordinator, M2.1:** the still-missing `telemetry_store.py` + `TelemetryChunk`/`TelemetryPoint` models + migration — the blocker for the whole telemetry path.
3. **Coordinator, M2.2–M2.5:** ingest router, read API, SSE shell over the pre-built `telemetry_bus`, and the bridge implementing **A2 + A3** with the parity tests.
4. **Stitches** per `docs/parallel-lane-stitch-notes.md` — the nine pre-built pieces wire in.
5. **Human, non-blocking:** methodology reviewer initials A6; bench-validate load-cell heat isolation.
