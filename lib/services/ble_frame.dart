import 'dart:typed_data';

/// BLE sync-protocol frame (STITCHING Phase D), identical layout to the
/// firmware's frame.c: msg_type(u8) chunk_id(u32) packet_index(u16)
/// total_packets(u16) payload, all big-endian.
const int kFrameHeaderLen = 9;

class DmrvFrame {
  final int msgType;
  final int chunkId;
  final int packetIndex;
  final int totalPackets;
  final Uint8List payload;

  DmrvFrame({
    required this.msgType,
    required this.chunkId,
    required this.packetIndex,
    required this.totalPackets,
    required this.payload,
  });

  Uint8List encode() {
    final out = Uint8List(kFrameHeaderLen + payload.length);
    final bd = ByteData.sublistView(out);
    bd.setUint8(0, msgType);
    bd.setUint32(1, chunkId, Endian.big);
    bd.setUint16(5, packetIndex, Endian.big);
    bd.setUint16(7, totalPackets, Endian.big);
    out.setRange(kFrameHeaderLen, out.length, payload);
    return out;
  }

  static DmrvFrame decode(Uint8List buf) {
    if (buf.length < kFrameHeaderLen) {
      throw ArgumentError('frame shorter than header');
    }
    final bd = ByteData.sublistView(buf);
    return DmrvFrame(
      msgType: bd.getUint8(0),
      chunkId: bd.getUint32(1, Endian.big),
      packetIndex: bd.getUint16(5, Endian.big),
      totalPackets: bd.getUint16(7, Endian.big),
      payload: Uint8List.sublistView(buf, kFrameHeaderLen),
    );
  }
}
