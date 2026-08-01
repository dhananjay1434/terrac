import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/ble_frame.dart';
import 'package:dmrv_app/services/ble_sync_transport.dart';

Uint8List _pkt(int chunkId, int idx, int total, List<int> payload) =>
    DmrvFrame(
      msgType: 2, chunkId: chunkId, packetIndex: idx, totalPackets: total,
      payload: Uint8List.fromList(payload),
    ).encode();

void main() {
  test('reassembler returns null until all packets arrive, then the payload', () {
    final r = ChunkReassembler();
    expect(r.offer(_pkt(7, 0, 3, [1, 2])), isNull);
    expect(r.offer(_pkt(7, 1, 3, [3, 4])), isNull);
    final done = r.offer(_pkt(7, 2, 3, [5, 6]));
    expect(done, isNotNull);
    expect(done, [1, 2, 3, 4, 5, 6]);
  });

  test('interleaved chunk_ids reassemble independently', () {
    final r = ChunkReassembler();
    expect(r.offer(_pkt(1, 0, 2, [10])), isNull);
    expect(r.offer(_pkt(2, 0, 1, [99])), [99]); // chunk 2 completes alone
    expect(r.offer(_pkt(1, 1, 2, [11])), [10, 11]);
  });

  test('in-memory transport records sends and echoes device emissions', () async {
    final t = InMemorySyncTransport();
    final got = <Uint8List>[];
    final sub = t.incoming().listen(got.add);
    await t.send(_pkt(1, 0, 1, [1]));
    t.deviceEmits(_pkt(2, 0, 1, [2]));
    await Future<void>.delayed(Duration.zero);
    expect(t.sent.length, 1);
    expect(got.length, 1);
    await sub.cancel();
    t.dispose();
  });
}
