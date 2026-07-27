# Parallel-Lane Stitch Notes (M2/M3/M4)

Nine far-end pieces were pre-built and independently gated while the coordinator
held M1. They are all NEW files — none touch `models.py`, migrations,
`app_factory.py`, `credit_engine.py`, `EXECUTION_LOG.md`, or any page/shared
component. This is the map for wiring them in once the coordinator lands the
serialized schema/endpoint tasks. Each stitch is small and explicitly scoped.

## Pre-built inventory (all committed, all green)
| Piece | File(s) | Task | Commit |
|---|---|---|---|
| Telemetry pub/sub + SSE tickets | `backend/telemetry_bus.py` (+test) | M2.4 | 3008d74 |
| Emissions factors (pure, versioned) | `backend/emissions_factors.py` (+test) | M4.2 | 3008d74 |
| Portal v2 client (telemetry read + ticket stream + hierarchy) | `portal/src/api2.ts` (+test) | M2.6 | 3008d74 |
| Thermal map chart | `portal/src/ui/ThermalMapChart/` | M2.7 | 3008d74 |
| Load telemetry chart | `portal/src/ui/LoadTelemetryChart/` | M2.8 | 3008d74 |
| Edge firmware contract | `docs/edge-firmware-contract.md` | M2h | b285877 |
| Stage projection (pure) | `backend/stage_projection.py` (+test) | M3.1-logic | 8a20a02 |
| Stage timeline component | `portal/src/components/StageTimeline/` | M3.3 | 23421d5 |
| Journey panel component | `portal/src/components/JourneyPanel/` | M4.4 | 21301da |

## Stitches owed (coordinator, after the serialized schema/endpoints land)

### M2.1 (BLOCKER for the whole telemetry path) — NOT done
`backend/telemetry_store.py` (the `insert_points` verbatim helper in the plan)
is absent on disk, and `TelemetryChunk`/`TelemetryPoint` models + migration are
not landed. This is the coordinator's serialized lane. Everything below marked
"needs M2.1" waits on it. `telemetry_bus.py` does NOT depend on it (pure), so it
is safe as-is.

### M2.2 ingest router — needs M2.1
Write `backend/routers/telemetry.py` per plan; it imports `telemetry_store.insert_points`
and `verify_signature`. Register in `app_factory.py` after the `evidence_router`
line. On each accepted chunk, call `telemetry_bus.publish(batch_uuid, frame)`.

### M2.4 SSE endpoints — pre-built logic, needs HTTP shell
`telemetry_bus` already has `mint_ticket`/`redeem_ticket`/`subscribe`/`publish`.
Add to the portal router: `POST /streams/burn/{uuid}/ticket` (bearer-auth →
`mint_ticket`) and `GET /streams/burn/{uuid}?ticket=` (→ `redeem_ticket`, then
`StreamingResponse` draining `subscribe(uuid)` in a finally-unsubscribe loop).

### M2.5 credit bridge — needs M2.1 + edits credit_engine.py:511
`telemetry_bridge.temperature_array_for` per plan; the ONE guarded conditional
at the `temperature_readings` anchor. Use `COMPLIANCE_CHANNELS=("T1","T2","T3")`
pending methodology sign-off (see plan M2.5 + `PYROLYSIS_MIN_C=350`).

### M2.7/M2.8 chart wiring — needs M2.3 read endpoint
In `BatchDetail.tsx` "Burn telemetry" card: `api2.getTelemetry2(uuid)` →
if channels present render `ThermalMapChart` (+ `LoadTelemetryChart` when a LOAD
channel exists) else the legacy `TemperatureChart` (Tier-0, unchanged). Live
mode: `api2.openBurnStream`. Pass `gateSatisfied` from the compliance result.

### M3.2/M3.3 timeline — needs M3.1 schema
`stage_projection.project_stages` is ready; the M3.1 backfill tool + M3.2
endpoint call it (adapt ORM rows → the dict shapes it accepts via `_get`).
Wire `StageTimeline` into `BatchDetail.tsx` above the evidence gallery when the
`timeline_v2` flag is on and the timeline is non-empty.

### M4.3/M4.4 journeys — needs M4.1 schema
`emissions_factors.estimate_emissions` is ready for the LCA hook (A7: manual
distances use `max(measured, default)`). Wire `JourneyPanel` into `Dispatch.tsx`
as a select→panel side view (scroll-into-view — don't repeat audit F1); mount a
Leaflet polyline into `JourneyPanel`'s `data-testid="route-slot"`.

## Both blocking decisions are now RESOLVED — see `docs/adr-001-thermal-and-identity.md`
1. ~~M1.3 batch-code numbering~~ → **ADR-001 Part B**: add explicit ordinal
   columns (`org_ordinal`, `network_code`, `site_ordinal`, `kiln_ordinal`,
   `country_code`), an `allocate_ordinal` service, and a 5-step backfill. M1.3
   unblocks once that migration lands (coordinator lane).
2. ~~Compliance channels~~ → **ADR-001 Part A**: `COMPLIANCE_CHANNELS =
   ("T1","T2","T3")`, T4 context-only (literature: below the pyrolysis front
   legitimately runs 150–450 °C). **Plus a defect fix the ADR uncovered — the
   mandatory BURN WINDOW (§A3):** compliance must use only samples between
   first and last crossing of 350 °C, or instrumented kilns fail where
   app-evidenced kilns pass (Global Rule 10 violation). M2.5 in the agent plan
   has been patched with the algorithm + required parity tests.
