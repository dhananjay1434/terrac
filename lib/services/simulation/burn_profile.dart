import '../telemetry_aggregator.dart' show round1dp;

/// Config-as-data for the whole demo ("node profile"): one place to tune the
/// burn. accelerationFactor speeds up LIVE emission only (DH-E1); it never
/// changes the values or the 10s bucket math. Default 10× → a 2-min burn's
/// chunks stream to the portal in ~12s.
class DemoProfile {
  const DemoProfile({
    this.ambientC = 25.0,
    this.plateauC = 420.0, // MUST equal VirtualBleAdapter.targetPlateau (drift-guarded in DH-C1)
    this.loadKg = 15.2,
    this.bucketSeconds = 10,
    this.bucketCount = 12,
    this.ignitionBuckets = 2,
    this.accelerationFactor = 10,
    this.probes = const [
      ProbeSpec(channel: 'T4', plateauC: 455.0, lagBuckets: -0.5, placement: 'bottom'),
      ProbeSpec(channel: 'T1', plateauC: 420.0, lagBuckets: 0.0, placement: 'side-A'),
      ProbeSpec(channel: 'T2', plateauC: 405.0, lagBuckets: 0.5, placement: 'side-B'),
      ProbeSpec(channel: 'T3', plateauC: 390.0, lagBuckets: 1.0, placement: 'side-C'),
    ],
  });
  final double ambientC;
  final double plateauC;
  final double loadKg;
  final int bucketSeconds;
  final int bucketCount;
  final int ignitionBuckets;
  final int accelerationFactor;

  /// The physical thermocouples. T1-T3 on the sides, T4 at the bottom (nearest
  /// the flame front → hottest, leads the ramp). T1 stays the reference probe at
  /// plateauC (== VirtualBleAdapter.targetPlateau; the DH-C1 drift guard). The
  /// producer loops this list, so any probe count "just works".
  final List<ProbeSpec> probes;
}

/// One thermocouple's placement-dependent parameters: the same burn shape as the
/// base curve, re-parameterised by plateau height and a ramp phase (lag).
class ProbeSpec {
  const ProbeSpec({
    required this.channel,
    required this.plateauC,
    this.lagBuckets = 0.0,
    this.placement = '',
  });
  final String channel;    // 'T1'..'T4'
  final double plateauC;   // this probe's plateau temperature
  final double lagBuckets; // + = ramps later (cooler side); - = earlier (hot bottom)
  final String placement;  // 'side-A' | 'side-B' | 'side-C' | 'bottom'
}

class BurnSample {
  const BurnSample(this.tempC, this.loadKg);
  final double tempC;
  final double loadKg;
}

/// Deterministic, pure burn: elapsed time → (temperature, load). The ONE curve
/// the signed edge producer reads (and the value the on-phone plateau matches).
/// Rounds through the same round1dp the aggregator/backend use, so values are
/// canonical-safe.
class BurnProfile {
  const BurnProfile(this.profile);
  final DemoProfile profile;

  BurnSample sample(Duration elapsed) {
    final s = elapsed.inMilliseconds / 1000.0;
    final b = s / profile.bucketSeconds; // fractional bucket index
    final temp = _temp(b);
    final load = b >= profile.ignitionBuckets ? profile.loadKg : 0.0;
    return BurnSample(round1dp(temp), round1dp(load));
  }

  double _temp(double b) => _tempFor(b, profile.plateauC, 0.0);

  /// Placement-aware curve: same ignition→ramp→plateau shape, re-scaled to
  /// [plateau] and phase-shifted by [lag] buckets (bottom leads, sides lag).
  double _tempFor(double b0, double plateau, double lag) {
    final ambient = profile.ambientC;
    final b = b0 - lag; // apply ramp phase
    const ignitionEnd = 3.0; // buckets of linear ignition climb
    const rampEnd = 6.0; // buckets to effectively reach plateau
    if (b <= 0) return ambient;
    if (b < ignitionEnd) {
      final frac = b / ignitionEnd;
      return ambient + (plateau - ambient) * 0.35 * frac;
    }
    if (b < rampEnd) {
      final frac = (b - ignitionEnd) / (rampEnd - ignitionEnd);
      final start = ambient + (plateau - ambient) * 0.35;
      return start + (plateau - start) * (1 - _decay(frac));
    }
    final noise = ((b.floor() % 5) - 2) * 0.1; // deterministic plateau shimmer
    return plateau + noise;
  }

  /// One probe's temperature at [elapsed] (canonical 1dp). Used by the signed
  /// producer for T1..T4; LOAD still comes from [sample].
  double sampleProbe(ProbeSpec probe, Duration elapsed) {
    final b = (elapsed.inMilliseconds / 1000.0) / profile.bucketSeconds;
    return round1dp(_tempFor(b, probe.plateauC, probe.lagBuckets));
  }

  // 1 → 0 over [0,1], concave (fast approach then settle).
  double _decay(double f) {
    final x = f.clamp(0.0, 1.0);
    return (1 - x) * (1 - x);
  }
}
