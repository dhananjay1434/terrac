import '../telemetry_envelope_builder.dart';

/// The seam between the phone courier and an edge device. SIMULATED now
/// (SimulatedEdgeDevice); a real ESP32 over BLE later (BleEdgeDeviceLink) —
/// swapping the implementation IS the entire hardware migration. Nothing above
/// this port (courier, outbox, backend, portal) changes.
abstract class EdgeDeviceLink {
  /// The device's enrolled producer id.
  String get deviceId;

  /// All signed, hash-chained chunks the device has for this burn, oldest-first.
  /// (Real device: streamed on demand over BLE; simulator: generated in memory.)
  Future<List<SignedChunk>> collect();

  /// Confirm the server stored through [throughSeq] for (session, channel); the
  /// device may reclaim that storage. No-op for the simulator.
  Future<void> ack(String sessionUuid, String channel, int throughSeq);
}
