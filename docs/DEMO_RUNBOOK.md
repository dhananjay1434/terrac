# Live demo — no hardware

## Step 0 — MAKE THE PORTAL ABLE TO RECEIVE (do this first)
Signed chunks only reach the portal if the device is enrolled server-side.
- Enroll the device in-app (Settings → enroll), OR build with
  `--dart-define=ENROLLMENT_TOKEN=<token>` so first launch self-enrolls.
- Confirm the backend has the `DeviceKey` row and the `telemetry_v2` feature flag ON for the demo org.
- If skipped: the phone burn still runs and looks correct, but the portal will NOT receive it, and the
  app logs a non-fatal "device not enrolled" note. Nothing crashes, START never blocks (DH-D1).

## Run
1. `flutter run --dart-define=DMRV_DEMO_MODE=true`
2. Start a burn. On the phone, temperature climbs past 350°C toward the 420°C plateau and the load
   cell settles at 15.2 kg — live. Under the hood a SimulatedEdgeDevice signs & hash-chains 10s chunks
   for FOUR thermocouples — T1/T2/T3 on the sides and T4 at the bottom (hottest, nearest the flame
   front) — plus LOAD, EACH ON ITS OWN CHAIN, off the shared BurnProfile, timestamps them now-relative
   (backward-anchored so the burn ends ≈now), and streams them to POST /api/v2/telemetry/ingest DURING
   the burn (default 10× — tune `DemoProfile.accelerationFactor`).
3. Portal → the burn's batch: timeline + thermal + LOAD tiles light from the capability verdict. The
   thermal map draws all four lines fanning out during ramp and holding a steady gradient
   (T4 > T1 > T2 > T3) at plateau, beside the LOAD curve. T1 stays the 420°C reference that matches the
   phone; T2–T4 are placement offsets of the same signed curve. The real ESP32 must reproduce the
   T1–T4 vectors in `test/golden_vectors.json` (MT-F1). If the session is unbound, bind it at
   /telemetry/unbound, then refresh.

## What reconciles (and what doesn't)
The signed portal record and the on-phone UI agree on the plateau (420°C), the load (15.2 kg), and
now-relative timestamps — proven by `test/demo_reconciliation_test.dart`. The instantaneous ramp
values are generated independently (both climb 25→420, both plausible); bit-exact instantaneous
cross-surface identity is intentionally not implemented (it would need one shared accelerated clock).

## Turning it off / going to real hardware
- Drop `--dart-define=DMRV_DEMO_MODE` (release builds already force it off).
- Real ESP32: implement EdgeDeviceLink as BleEdgeDeviceLink over flutter_reactive_ble (firmware
  reproduces golden_vectors.json). Swap SimulatedEdgeDevice → BleEdgeDeviceLink at the demo call site;
  delete BurnProfile/DemoClock/simulators. Courier, outbox, sync loop, backend, portal — UNCHANGED.
