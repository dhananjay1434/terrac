# Live demo — no hardware

1. Backend: enable telemetry_v2 for the demo org (a feature_flags row; reversible).
2. App:  flutter run --dart-define=DMRV_DEMO_MODE=true
3. Start a burn. On the phone: temperature climbs past 350°C and the load cell settles (live).
   Under the hood the SimulatedEdgeDevice signs & hash-chains 10s chunks (T1 + LOAD) and the courier
   relays them to POST /api/v2/telemetry/ingest.
4. Portal → the burn's batch: the custody timeline + thermal + LOAD tiles light up from the capability
   verdict; if the session is unbound, bind it at /telemetry/unbound, then refresh.
5. Everything on screen is real: really signed (Ed25519), really verified server-side, really stored.

## Turning it off / going to real hardware
- Remove the demo: drop --dart-define=DMRV_DEMO_MODE (release builds already force it off).
- Real ESP32: implement EdgeDeviceLink as BleEdgeDeviceLink over flutter_reactive_ble talking to the
  device (whose firmware reproduces golden_vectors.json). Swap SimulatedEdgeDevice → BleEdgeDeviceLink
  at the P16 call site. Courier, outbox, sync loop, backend, portal — UNCHANGED.
