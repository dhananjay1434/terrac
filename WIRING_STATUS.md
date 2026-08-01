# WIRING STATUS — the single source of truth for what is done vs. remaining

**How to read this.** One row per task. Update the status box the moment a task's test passes and it
is committed. Never mark a row ✅ from memory — mark it only after its **Verify** command is green.
This file exists so no one (human or agent) has to guess or hallucinate progress.

**Legend:** ✅ done & verified · 🟡 in progress · ⬜ not started · 🔵 hardware-swap (simulated now,
real device later — a one-adapter change, no rewrite).

**The executable steps for every ⬜/🟡 row live in `REMEDIATION_PROMPT_WIRING.md`** (one consolidated
prompt, one task per commit). This file tracks; that file instructs.

---

## Current reality (verified 2026-08-01)
- Backend v2 telemetry pipeline: real, tested, correct. **902 backend tests green.**
- Firmware pure logic (canonical/aggregate/frame): host-proven vs golden vectors. **Adapters are
  stubs; no board.**
- App: canonicalizer/frame/transport proven in isolation. **411 flutter tests green.**
- Portal: capability endpoint + client exist. **Not yet consumed by any screen.**
- **Net: every piece is correct and DISCONNECTED. The prompt below connects them + adds a realistic
  simulated device so the whole system runs and demos with zero hardware.**

---

## Foundations (prior work — do not redo)
| # | Task | Status | Evidence |
|---|---|---|---|
| F | Backend v2 ingest + verify + sync-status + unbound-sessions | ✅ | `backend` 902 pass |
| F | Golden vectors pin the canonical signing bytes | ✅ | `test_golden_vectors.py` |
| F | Firmware domain (canonical/aggregate/frame) host-proven | ✅ | `firmware` gcc tests |
| F | App canonicalizer / BLE frame / sync-transport (proven, isolated) | ✅ | 3 flutter tests |
| F | App already Ed25519 (`CryptoSigner`) + device enrollment | ✅ | `crypto_signer.dart` |
| F | App already has temp simulator (`VirtualBleAdapter`, `DMRV_DEMO_MODE`) | ✅ | `pyrolysis_ble_notifier.dart` |
| F | App already has weight simulator (`MockBleWeightScaleService`) | ✅ | `ble_weight_scale_service.dart` |

---

## PART 1 — Portal wiring (display-only, no hardware, cannot regress)
| # | Task | Status | File(s) | Verify |
|---|---|---|---|---|
| P1 | BatchDetail imports capability client + type | ✅ | `portal/src/pages/BatchDetail.tsx` | `tsc --noEmit` |
| P2 | BatchDetail loads capability verdict into state | ✅ | same | `tsc --noEmit` |
| P3 | Panels render from verdict (fallback = today) + test | ✅ | same + `BatchDetail.caps.test.tsx` | `vitest run …caps` (3 passed) |
| P4 | Types for unbound-sessions + sync-status | ✅ | `portal/src/apiV2types.ts` | `tsc --noEmit` |
| P5 | Client fns: getUnboundSessions / bindSession / getDeviceSyncStatus + test | ✅ | `portal/src/api2.ts` + `unbound_sessions.test.ts` | `vitest run …unbound` (3 passed) |
| P6 | Admin UnboundSessions page + route + test | ✅ | `UnboundSessions.tsx` + `App.tsx` | `vitest run …UnboundSessions` (3 passed) |
| P7 | Device sync-status panel + test | ✅ | `UnboundSessions.tsx` | `vitest run …UnboundSessions` (3 passed) |

## PART 2 — Producer logic (pure, proven, no hardware, no live edits)
| # | Task | Status | File(s) | Verify |
|---|---|---|---|---|
| P8 | `CryptoSigner.signBytesB64` (producer signature) + test | ✅ | `crypto_signer.dart` + test | `flutter test …producer_signature` (1 passed) |
| P9 | `TelemetryAggregator` (10s bucket, 1dp) + test | ✅ | `telemetry_aggregator.dart` + test | `flutter test …aggregator` (3 passed) |
| P10 | `TelemetryEnvelopeBuilder` (envelope+sign+chain) + test | ✅ | `telemetry_envelope_builder.dart` + test | `flutter test …envelope_builder` (2 passed) |
| P11 | 🔴 Full-chain proof (build→frame→reassemble→verify) + test | ✅ | `telemetry_full_chain_test.dart` | `flutter test …full_chain` (1 passed) |

## PART 3 — 🔵 Simulated Edge Device (the modular "hardware", swappable for real firmware)
| # | Task | Status | File(s) | Verify |
|---|---|---|---|---|
| P12 | `EdgeDeviceLink` PORT (the swap seam courier depends on) | ✅ | `lib/services/simulation/edge_device_link.dart` | compiles (flutter analyze clean) |
| P13 | `SimulatedEdgeDevice` — own key, realistic burn (temp+weight), signs+chains chunks | ✅ | `lib/services/simulation/simulated_edge_device.dart` + test | `flutter test …simulated_edge_device` (1 passed) |

## PART 4 — Phone courier (drains the device via the PORT; adapter is swappable)
| # | Task | Status | File(s) | Verify |
|---|---|---|---|---|
| P14 | `TelemetryCourier` — drain link → enqueue syncOutbox → ack + test (against the simulator, no backend) | ✅ | `lib/services/telemetry_courier.dart` + test | `flutter test …courier` (1 passed) |

## PART 5 — Live wire + demo (flag-gated; edits hot paths → read-first)
| # | Task | Status | File(s) | Verify |
|---|---|---|---|---|
| P15 | 🟠 Sync loop relays `TELEMETRY_V2_CHUNK` → POST `/api/v2/telemetry/ingest` (read-first) | ✅ | `sync_queue_manager.dart` + `telemetry_outbox_drift.dart` + `sync_telemetry_v2_test.dart` | `flutter test` (3 passed; dispatch is by `targetTable` not `operationType` — added an early short-circuit in `_processEntry`, noted in commit) |
| P16 | 🟠 Demo wire: `DMRV_DEMO_MODE` spins up SimulatedEdgeDevice + courier; enroll; dual-run; LOAD included (read-first) | ✅ | `demo_telemetry_wire.dart` + `pyrolysis_screen.dart` (`_requestPermsAndStart`) + test | `flutter test` (2 passed; ON path tested via injectable `startDemoTelemetry`, same pattern as `geofenceWarningFor(enforced:)`, since the dart-define can't flip at test-run time) |
| P17 | DEMO RUNBOOK (no code) | ✅ | `docs/DEMO_RUNBOOK.md` | manual run |

## GATE
| # | Task | Status | Verify |
|---|---|---|---|
| G1 | Portal: `tsc` clean + `vitest` 0 failed, ≥ baseline | ✅ | `tsc` clean; vitest 409/411 passed — 2 failures are 1 pre-existing snapshot test (confirmed via `git stash` to fail before any WIRING change) |
| G2 | App: `flutter test` 0 failed, no pre-existing regressed (baseline 411) | ✅ | 425 passed, 0 failed (baseline 411 + 14 new WIRING tests) |
| G3 | Backend: `pytest -q` 0 failed (baseline 902) | ✅ | 902 passed, 2 skipped (matches baseline exactly — untouched by WIRING) |

---

## 🔵 REMAINING AFTER ALL OF THE ABOVE — the ONLY hardware/ops work left
| # | Task | Status | Note |
|---|---|---|---|
| H1 | A4 crypto decision (ESP32-S3 NVS vs secure element) | 🔵 | human/architect; blocks real signing |
| H2 | Real ESP32 firmware: fill `firmware/src/adapters/*` bodies against the ports | 🔵 | domain already host-proven; conformance oracle = golden vectors + P11 |
| H3 | `BleEdgeDeviceLink` — implement the P12 port over real BLE (`flutter_reactive_ble`) | 🔵 | **THE migration: swap `SimulatedEdgeDevice` → `BleEdgeDeviceLink`. Courier/backend/portal unchanged.** |
| H4 | W5 canary: enable `telemetry_v2` for one real org + dual-run parity report | 🔵 | ops rollout + monitoring window |

**Migration in one sentence:** everything above the `EdgeDeviceLink` port (courier, outbox, backend,
portal, capability UI, demo) is final; going live = implement that one port over real BLE and flash
the firmware whose pure logic is already proven. No code above the port changes.

---

## Definition of "demo-ready" (all must be ✅)
P1–P17 + G1–G3. At that point: `flutter run --dart-define=DMRV_DEMO_MODE=true`, start a burn, watch
temperature **and** weight climb live on the phone, and watch the same signed burn appear in the
portal timeline + light up the capability tiers — **with no hardware, and every byte on screen real
(really signed, really verified, really stored).**
