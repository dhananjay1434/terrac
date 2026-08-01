import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/ble_frame.dart';

void main() {
  test('encode/decode round-trips and matches the firmware byte layout', () {
    final payload = Uint8List.fromList([0xDE, 0xAD, 0xBE, 0xEF]);
    final f = DmrvFrame(
      msgType: 2, chunkId: 0x01020304,
      packetIndex: 1, totalPackets: 3, payload: payload,
    );
    final bytes = f.encode();
    expect(bytes[0], 2);
    expect(bytes.sublist(1, 5), [0x01, 0x02, 0x03, 0x04]); // big-endian chunk_id
    expect(bytes.sublist(5, 7), [0x00, 0x01]);             // packet_index
    expect(bytes.sublist(7, 9), [0x00, 0x03]);             // total_packets

    final g = DmrvFrame.decode(bytes);
    expect(g.msgType, 2);
    expect(g.chunkId, 0x01020304);
    expect(g.packetIndex, 1);
    expect(g.totalPackets, 3);
    expect(g.payload, payload);
  });

  test('decode rejects a short buffer', () {
    expect(() => DmrvFrame.decode(Uint8List.fromList([1, 2, 3])),
        throwsArgumentError);
  });
}
