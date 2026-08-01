import 'dart:convert';
import 'simulation/edge_device_link.dart';

/// Durable outbox port the courier writes chunks to. The real adapter inserts a
/// SyncOutbox row (operationType 'TELEMETRY_V2_CHUNK'); tests use a fake.
abstract class ChunkOutbox {
  Future<void> enqueueTelemetryChunk(String payloadJson);
}

/// The phone as COURIER: collect signed chunks from an EdgeDeviceLink (simulated
/// now, BLE later) and hand each to the durable outbox for upload. The courier
/// neither signs nor trusts the transport — it only carries verified cargo.
class TelemetryCourier {
  TelemetryCourier(this._outbox);
  final ChunkOutbox _outbox;

  /// Drain a device and enqueue every chunk. Returns the count relayed.
  Future<int> drain(EdgeDeviceLink device) async {
    final chunks = await device.collect();
    for (final c in chunks) {
      await _outbox.enqueueTelemetryChunk(jsonEncode(c.envelope));
    }
    return chunks.length;
  }
}
