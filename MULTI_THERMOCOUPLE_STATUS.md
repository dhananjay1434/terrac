# MULTI-THERMOCOUPLE STATUS — single source of truth for what's done vs remaining

**How to read this.** One row per task. Tick ✅ ONLY after its test is green AND it is committed AND the
phase GATE (full `flutter test`) is green — never from memory. `MULTI_THERMOCOUPLE_BLUEPRINT.md` is the
"why"; `REMEDIATION_PROMPT_MULTI_THERMOCOUPLE.md` is the executable steps (byte-exact anchors + verbatim
code, one task per commit, a GATE per phase); this file tracks.

**Legend:** ✅ done & verified · 🟡 in progress · ⬜ not started · 🔵 hardware-later.

---

## Context (as of authoring — NOT yet executed)
- Goal: four thermocouples — **T1/T2/T3 sides, T4 bottom** (hottest) — each a different temperature, all
  signed + hash-chained (one chain per channel) + streamed **live** to the portal during the burn.
- **The whole pipeline below the producer already supports T1–T4** (backend ingest/read/SSE, portal
  ThermalMapChart + BurnLiveView, api2 stream, phone sync relay). Verified in code 2026-08-01.
- The ONLY real gap is the **simulator** (BurnProfile = one curve; SimulatedEdgeDevice = T1 + LOAD).
- Baselines to protect: backend pytest **902/2 skip**; `flutter test` **437/2 skip**; portal `tsc` clean +
  vitest green **minus 2 known pre-existing failures** (`AppShell` snapshot + `no-raw-values`/Ledger.css).

## Phases (each ends with a GATE = full `flutter test` 0 failed before the next starts)
| # | Task | Status | File(s) | Verify |
|---|------|--------|---------|--------|
| MT-A1 | `ProbeSpec` + `DemoProfile.probes` (4-probe default) + `BurnProfile.sampleProbe`; NEW test. **Purely additive → 0 tests break.** | ✅ | `lib/services/simulation/burn_profile.dart` + `test/multi_probe_profile_test.dart` | `flutter test test/multi_probe_profile_test.dart test/burn_profile_test.dart` → GATE A: `flutter test` |
| MT-B1 | Producer emits **T1..T4 + LOAD**, one hash-chain per channel (`collect` + `stream`) **+ the 3 breaking count-fixes IN THE SAME COMMIT** (simulated_edge_device_test 12→30, telemetry_courier_test 4→10, telemetry_courier_stream_test 6→15). | ✅ | `simulated_edge_device.dart` + 3 test files | `flutter test` on the 3 tests → GATE B: `flutter test` |
| MT-C1 | Additive coverage only (green before+after): reconciliation per-probe + demo-wire T2/T3/T4 presence. | ✅ | `demo_reconciliation_test.dart`, `demo_telemetry_wire_test.dart` | `flutter test` on the 2 tests → GATE C: `flutter test` |
| MT-D1 | (optional) portal ThermalMapChart placement labels (T4·bottom, T1·side). Four lines already render. | ✅ | `portal/src/ui/ThermalMapChart/ThermalMapChart.tsx` | GATE D: `cd portal && npx tsc --noEmit && npx vitest run` |
| MT-E1 | docs: DEMO_RUNBOOK four-probe + firmware-oracle note. | ✅ | `docs/DEMO_RUNBOOK.md` | manual |
| MT-F1 | 🔵 (later, only if asked) golden_vectors.json T2/T3/T4 reference vectors. | 🔵 | `test/golden_vectors.json` | spec artifact (no test yet) |
| FINAL | `flutter test` (≥443) + portal tsc+vitest (minus 2 known) + backend pytest **902** (unchanged = proof). | ✅ | — | the three suites |

---

## The one design invariant that must never break
Each channel (T1,T2,T3,T4,LOAD) is an **independent hash-chain**: `seq` starts 0, `prev_hash` starts
`GENESIS`, and every chunk signature-verifies. A red chain/signature test is a producer bug — fix the
producer, never weaken the test. (Only *counts* and the new per-probe blocks may change.)

## Why nothing breaks between phases
- MT-A1 is additive (`sample()` byte-identical) → 0 breaks.
- MT-B1 bundles its 3 breaking count-fixes into the same commit → green at the commit.
- MT-C1 is additive coverage → green before and after.
Each phase's GATE (full `flutter test`) mechanically enforces a green tree at every commit.

## Scalability / future live hardware (the modularity contract)
- Add/remove a probe → one line in `DemoProfile.probes`. The producer loops the list; N probes just work.
- Go live → implement `BleEdgeDeviceLink implements EdgeDeviceLink` (real sensors → signed chunks; does NOT
  read BurnProfile), swap it at the one demo call site in `demo_telemetry_wire.dart`, delete the sim files.
- Courier, outbox, sync loop, backend (ingest/read/SSE), portal (chart/live-view) — all UNCHANGED.
- Proof the boundary holds: backend pytest stays **902 with zero backend edits** through MT-A1…E1.
