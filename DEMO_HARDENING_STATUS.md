# DEMO HARDENING STATUS — single source of truth for what's done vs remaining

**How to read this.** One row per task. Tick a row ✅ ONLY after its test is green AND it is committed —
never from memory. `DEMO_HARDENING_BLUEPRINT.md` is the "why"; `REMEDIATION_PROMPT_DEMO_HARDENING.md`
is the executable steps (anchors + verbatim code, one task per commit); this file tracks.

**Legend:** ✅ done & verified · 🟡 in progress · ⬜ not started · 🔵 hardware-swap (later, one adapter).

---

## Context (as of authoring — NOT yet executed)
- WIRING P1–P17 + GATE all ✅ (main @ ~3102d4c). v2 crypto is REAL, end-to-end.
- This migration fixes the 4 demo landmines from the audit, additively + flag-gated, without touching
  the legacy v1 write, the v2 backend, the `EdgeDeviceLink` port, or the Drift schema.
- **No application code has been changed yet** — only the three planning docs exist.

## The 4 landmines being migrated
| # | Sev | Landmine | Fixed by |
|---|-----|----------|----------|
| L1 | 🔴 | Demo's portal half dies / burn-start can throw (enrollment) | DH-D1 |
| L2 | 🟠 | Phone 420°C vs signed 455°C (unshared simulators) | DH-A1, DH-B1, DH-C1 |
| L3 | 🟠 | Hardcoded past timestamps in signed data | DH-A2, DH-B1 |
| L4 | 🟡 | "Live" is a facade (all buckets at t=0) | DH-E1 |

---

## Phase A — Foundation (pure; zero consumers → cannot break)
| # | Task | Status | File(s) | Verify |
|---|------|--------|---------|--------|
| DH-A1 | BurnProfile + DemoProfile + BurnSample | ✅ | `lib/services/simulation/burn_profile.dart` + test | `flutter test test/burn_profile_test.dart` |
| DH-A2 | DemoClock (wall + fake) | ✅ | `lib/services/simulation/demo_clock.dart` + test | `flutter test test/demo_clock_test.dart` |

## Phase B — Signed producer unifies values + time (L2-temp, L3)
| # | Task | Status | File(s) | Verify |
|---|------|--------|---------|--------|
| DH-B1 | SimulatedEdgeDevice ← BurnProfile + DemoClock (now-relative); test correction | ✅ | `simulated_edge_device.dart` + its test | `flutter test test/simulated_edge_device_test.dart` |

## Phase C — On-phone parity + drift-guard (L2 headline fixed by B; C locks it in)
| # | Task | Status | File(s) | Verify |
|---|------|--------|---------|--------|
| DH-C1 | MockBleWeightScaleService ← BurnProfile.loadKg; reconciliation + plateau/load drift-guard (adapter NOT rewritten — already 420) | ✅ | `ble_weight_scale_service.dart` + `demo_reconciliation_test.dart` | `flutter test test/demo_reconciliation_test.dart test/virtual_ble_adapter_test.dart` |

## Phase D — Enrollment hardening (L1) — CRITICAL, independent of A–C
| # | Task | Status | File(s) | Verify |
|---|------|--------|---------|--------|
| DH-D1 | Soft-fail `ensureDemoReady` + hardened burn-start call site (+ optional banner) | ✅ | `simulation/demo_readiness.dart`, `demo_telemetry_wire.dart`, `pyrolysis_screen.dart` + test | `flutter test test/demo_readiness_test.dart` |

## Phase E — Live streaming (L4)
| # | Task | Status | File(s) | Verify |
|---|------|--------|---------|--------|
| DH-E1 | `SimulatedEdgeDevice.stream()` + `TelemetryCourier.drainStream()` + demo wire | ✅ | `simulated_edge_device.dart`, `telemetry_courier.dart`, `demo_telemetry_wire.dart` + test | `flutter test test/telemetry_courier_stream_test.dart` |

## Phase F — Docs + GATE
| # | Task | Status | Verify |
|---|------|--------|--------|
| DH-F1 | Runbook rewrite (enrollment step 0 + acceleration + reconciliation guarantee) | ✅ | manual |
| G1 | Portal `tsc` clean + vitest 0 failed (minus known AppShell snapshot) | ✅* | `cd portal && npx vitest run` |
| G2 | `flutter test` 0 failed; nothing pre-existing regressed; reconciliation + streaming green | ✅ | `flutter test` |
| G3 | Backend `pytest -q` 902 passed (untouched) | ✅ | `cd backend && python -m pytest -q` |

\* G1: tsc clean. vitest has 2 failing test files, NOT 1 — both pre-existing, neither touched by
DH-A1…F1 (this run made zero commits under `portal/`): the known `AppShell.test.tsx` snapshot, AND
`src/tokens/no-raw-values.test.ts` (raw px in `Ledger.module.css`, introduced by earlier commits
5aafa95/693a38d). Confirmed pre-existing via `git log f4831e7..HEAD -- portal/` = empty.

---

## Sequencing note
Dependency spine: **DH-A1 → DH-A2 → DH-B1 → DH-C1 → DH-E1**. **DH-D1 depends on nothing** — if a demo
is needed before the spine lands, execute DH-D1 alone first (makes the demo reliably WORK), then the
spine (makes it unfalsifiable + live). DH-F1 + GATE close out.

## Definition of "hardened demo-ready" (all must be ✅)
DH-A1…DH-F1 + G1–G3, with the reconciliation and streaming invariants green. Then:
`flutter run --dart-define=DMRV_DEMO_MODE=true` → start a burn → phone and portal show the SAME
now-timestamped values, streamed live — and a missing enrollment degrades to a banner, never a crash.

## 🔵 Remaining after this — hardware/ops only
A4 crypto decision · real ESP32 firmware (oracle = golden vectors + P11) · `BleEdgeDeviceLink` (swap
`SimulatedEdgeDevice`, delete BurnProfile/DemoClock/simulators) · W5 canary.
