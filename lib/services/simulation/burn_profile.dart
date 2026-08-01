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
  });
  final double ambientC;
  final double plateauC;
  final double loadKg;
  final int bucketSeconds;
  final int bucketCount;
  final int ignitionBuckets;
  final int accelerationFactor;
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

  double _temp(double b) {
    final ambient = profile.ambientC;
    final plateau = profile.plateauC;
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

  // 1 → 0 over [0,1], concave (fast approach then settle).
  double _decay(double f) {
    final x = f.clamp(0.0, 1.0);
    return (1 - x) * (1 - x);
  }
}
