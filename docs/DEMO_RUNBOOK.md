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
   (T1 + LOAD) off the shared BurnProfile, timestamps them now-relative (backward-anchored so the burn
   ends ≈now), and streams them to POST /api/v2/telemetry/ingest DURING the burn (default 10× — tune
   `DemoProfile.accelerationFactor`).
3. Portal → the burn's batch: timeline + thermal + LOAD tiles light from the capability verdict. If
   the session is unbound, bind it at /telemetry/unbound, then refresh.

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
