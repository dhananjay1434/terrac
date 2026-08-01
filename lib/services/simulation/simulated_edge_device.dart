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
  double _probeTemp(ProbeSpec probe, int b) => profile.sampleProbe(probe, _elapsedAt(b));
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
    final seq = <String, int>{};      // per-channel monotonic seq (starts 0)
    final prev = <String, String>{};  // per-channel prev_hash chain (starts GENESIS)
    for (var b = 0; b < buckets; b++) {
      for (final probe in profile.profile.probes) {
        out.add(await _emit(probe.channel, _iso(b), _probeTemp(probe, b), seq, prev));
      }
      out.add(await _emit('LOAD', _iso(b), _weight(b), seq, prev));
    }
    return out;
  }

  /// Build one signed chunk on [channel]'s OWN chain (GENESIS at seq 0), advance it.
  Future<SignedChunk> _emit(
    String channel, String tStartIso, double value,
    Map<String, int> seq, Map<String, String> prev,
  ) async {
    final s = seq[channel] ?? 0;
    final p = prev[channel] ?? 'GENESIS';
    final c = await TelemetryEnvelopeBuilder.build(
      deviceId: deviceId, sessionUuid: sessionUuid, batchUuid: null, channel: channel,
      tStartIso: tStartIso, samplePeriodS: 10.0, values: [value], seq: s, prevHash: p);
    seq[channel] = s + 1;
    prev[channel] = c.nextPrevHash;
    return c;
  }

  /// Live emission: yields one bucket's T1+LOAD chunks every
  /// bucketSeconds/accelerationFactor, so the courier can relay them DURING the
  /// burn (not all at t=0). collect() stays for the batch/test path.
  Stream<SignedChunk> stream() async* {
    final period = Duration(
      milliseconds: (profile.profile.bucketSeconds * 1000 ~/ profile.profile.accelerationFactor)
          .clamp(1, 1 << 30),
    );
    final seq = <String, int>{};
    final prev = <String, String>{};
    for (var b = 0; b < buckets; b++) {
      if (b > 0) await Future<void>.delayed(period);
      for (final probe in profile.profile.probes) {
        yield await _emit(probe.channel, _iso(b), _probeTemp(probe, b), seq, prev);
      }
      yield await _emit('LOAD', _iso(b), _weight(b), seq, prev);
    }
  }

  @override
  Future<void> ack(String sessionUuid, String channel, int throughSeq) async {
    // Simulated: nothing to reclaim. A real device drops flash <= throughSeq here.
  }
}
