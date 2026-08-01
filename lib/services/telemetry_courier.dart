import 'dart:convert';
import 'telemetry_envelope_builder.dart';
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

  /// Live drain: enqueue each chunk from [stream] AS it is produced, so chunks
  /// reach the outbox (and the sync loop's POST) DURING the burn. `await for`
  /// awaits every enqueue, so the returned Future completes only once ALL chunks
  /// are durably enqueued (deterministic for tests + callers).
  Future<int> drainStream(
    Stream<SignedChunk> stream, {
    void Function(int count)? onProgress,
  }) async {
    var n = 0;
    await for (final c in stream) {
      await _outbox.enqueueTelemetryChunk(jsonEncode(c.envelope));
      n++;
      onProgress?.call(n);
    }
    return n;
  }
}
