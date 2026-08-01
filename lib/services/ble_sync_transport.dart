import 'dart:async';
import 'dart:typed_data';
import 'ble_frame.dart';

/// Port: something that carries framed packets to/from one edge device.
/// Real adapter = flutter_reactive_ble (🔵 human-gated, needs hardware).
/// Test adapter = InMemorySyncTransport below.
abstract class BleSyncTransport {
  Future<void> send(Uint8List packet);
  Stream<Uint8List> incoming();
}

/// Reassembles multi-packet chunks (STITCHING D1). Feed raw packets; get a
/// complete payload once all packets of a chunk_id have arrived.
class ChunkReassembler {
  final _parts = <int, Map<int, Uint8List>>{};
  final _totals = <int, int>{};

  /// Returns the reassembled payload when the chunk is complete, else null.
  Uint8List? offer(Uint8List packet) {
    final f = DmrvFrame.decode(packet);
    _totals[f.chunkId] = f.totalPackets;
    (_parts[f.chunkId] ??= {})[f.packetIndex] = f.payload;
    if (_parts[f.chunkId]!.length != f.totalPackets) return null;
    final b = BytesBuilder();
    for (var i = 0; i < f.totalPackets; i++) {
      b.add(_parts[f.chunkId]![i]!);
    }
    _parts.remove(f.chunkId);
    _totals.remove(f.chunkId);
    return b.toBytes();
  }
}

/// In-memory transport for tests: whatever you `send` is echoed to `incoming`
/// (loopback), so a test can push device-style packets through the reassembler.
class InMemorySyncTransport implements BleSyncTransport {
  final _out = <Uint8List>[];
  final _ctrl = StreamController<Uint8List>.broadcast();
  List<Uint8List> get sent => List.unmodifiable(_out);

  @override
  Future<void> send(Uint8List packet) async => _out.add(packet);

  @override
  Stream<Uint8List> incoming() => _ctrl.stream;

  /// Test helper: simulate the device emitting a packet.
  void deviceEmits(Uint8List packet) => _ctrl.add(packet);
  void dispose() => _ctrl.close();
}
