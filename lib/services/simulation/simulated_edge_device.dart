import '../telemetry_aggregator.dart';
import '../telemetry_envelope_builder.dart';
import 'edge_device_link.dart';

/// Software stand-in for the ESP32 edge unit. Generates a realistic burn —
/// temperature climbing through 350°C to a plateau, plus a load cell settling —
/// aggregated to 10s buckets and emitted as SIGNED, HASH-CHAINED chunks (T1 +
/// LOAD), exactly the shape the backend verifies. This is the modular "hardware":
/// delete it / swap it for BleEdgeDeviceLink with zero change above this file.
class SimulatedEdgeDevice implements EdgeDeviceLink {
  SimulatedEdgeDevice({required this.deviceId, required this.sessionUuid, this.buckets = 12});
  @override
  final String deviceId;
  final String sessionUuid;
  final int buckets;

  // Deterministic burn profile (per 10s bucket index b).
  double _temp(int b) {
    if (b == 0) return 45.0;             // ambient/ignition
    if (b < 4) return 60.0 + b * 95.0;   // 155, 250, 345 → climbing
    if (b < 6) return 360.0 + (b - 4) * 60.0; // 360, 420 → past 350
    return 455.0 + (b % 2);              // plateau ~455°C
  }
  double _weight(int b) => b < 2 ? 0.0 : 15.2; // load settles after ignition
  String _iso(int b) {
    final sec = b * 10;
    final mm = (sec ~/ 60).toString().padLeft(2, '0');
    final ss = (sec % 60).toString().padLeft(2, '0');
    return '2026-07-23T09:$mm:${ss}Z';
  }

  @override
  Future<List<SignedChunk>> collect() async {
    final out = <SignedChunk>[];
    var seqT = 0, seqL = 0;
    var prevT = 'GENESIS', prevL = 'GENESIS';
    for (var b = 0; b < buckets; b++) {
      final t = await TelemetryEnvelopeBuilder.build(
        deviceId: deviceId, sessionUuid: sessionUuid, batchUuid: null, channel: 'T1',
        tStartIso: _iso(b), samplePeriodS: 10.0, values: [round1dp(_temp(b))], seq: seqT, prevHash: prevT);
      prevT = t.nextPrevHash; seqT++; out.add(t);
      final l = await TelemetryEnvelopeBuilder.build(
        deviceId: deviceId, sessionUuid: sessionUuid, batchUuid: null, channel: 'LOAD',
        tStartIso: _iso(b), samplePeriodS: 10.0, values: [round1dp(_weight(b))], seq: seqL, prevHash: prevL);
      prevL = l.nextPrevHash; seqL++; out.add(l);
    }
    return out;
  }

  @override
  Future<void> ack(String sessionUuid, String channel, int throughSeq) async {
    // Simulated: nothing to reclaim. A real device drops flash <= throughSeq here.
  }
}
