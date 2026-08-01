import '../telemetry_envelope_builder.dart';
import 'burn_profile.dart';
import 'demo_clock.dart';
import 'edge_device_link.dart';

/// Software stand-in for the ESP32 edge unit. Generates a realistic burn —
/// temperature climbing through 350°C to a plateau, plus a load cell settling —
/// aggregated to 10s buckets and emitted as SIGNED, HASH-CHAINED chunks (T1 +
/// LOAD), exactly the shape the backend verifies. This is the modular "hardware":
/// delete it / swap it for BleEdgeDeviceLink with zero change above this file.
class SimulatedEdgeDevice implements EdgeDeviceLink {
  SimulatedEdgeDevice({
    required this.deviceId,
    required this.sessionUuid,
    BurnProfile? profile,
    DemoClock? clock,
    int? buckets,
  })  : profile = profile ?? const BurnProfile(DemoProfile()),
        clock = clock ?? WallDemoClock(),
        buckets = buckets ?? (profile ?? const BurnProfile(DemoProfile())).profile.bucketCount;
  @override
  final String deviceId;
  final String sessionUuid;
  final BurnProfile profile;
  final DemoClock clock;
  final int buckets;

  Duration _elapsedAt(int b) => Duration(seconds: b * profile.profile.bucketSeconds);
  double _temp(int b) => profile.sample(_elapsedAt(b)).tempC;
  double _weight(int b) => profile.sample(_elapsedAt(b)).loadKg;

  // Now-relative AND always in the PAST: model the burn as ENDING at
  // clock.startedAt, so bucket b covers [startedAt - (buckets-1-b)*bs, …].
  // Every t_start <= startedAt (≈now); a forward "startedAt + b*bs" would make
  // late buckets FUTURE and the backend (future-skew 300s) would 422 them on a
  // long burn. Backward-anchoring is future-proof for any bucketCount.
  String _iso(int b) => clock.startedAt
      .subtract(Duration(seconds: (buckets - 1 - b) * profile.profile.bucketSeconds))
      .toIso8601String();

  @override
  Future<List<SignedChunk>> collect() async {
    final out = <SignedChunk>[];
    var seqT = 0, seqL = 0;
    var prevT = 'GENESIS', prevL = 'GENESIS';
    for (var b = 0; b < buckets; b++) {
      final t = await TelemetryEnvelopeBuilder.build(
        deviceId: deviceId, sessionUuid: sessionUuid, batchUuid: null, channel: 'T1',
        tStartIso: _iso(b), samplePeriodS: 10.0, values: [_temp(b)], seq: seqT, prevHash: prevT);
      prevT = t.nextPrevHash; seqT++; out.add(t);
      final l = await TelemetryEnvelopeBuilder.build(
        deviceId: deviceId, sessionUuid: sessionUuid, batchUuid: null, channel: 'LOAD',
        tStartIso: _iso(b), samplePeriodS: 10.0, values: [_weight(b)], seq: seqL, prevHash: prevL);
      prevL = l.nextPrevHash; seqL++; out.add(l);
    }
    return out;
  }

  @override
  Future<void> ack(String sessionUuid, String channel, int throughSeq) async {
    // Simulated: nothing to reclaim. A real device drops flash <= throughSeq here.
  }
}
