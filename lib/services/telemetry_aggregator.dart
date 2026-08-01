/// 10s bucket reducer, mirroring firmware/src/domain/aggregate.c. Temperatures
/// average; load takes the last reading. Rounds to 1 decimal (FLOAT PRECISION
/// INVARIANT) so canonical bytes match backend & firmware.
enum AggKind { mean, last }
double round1dp(double x) { final s = x < 0 ? -1.0 : 1.0; return s * (x.abs() * 10.0 + 0.5).floorToDouble() / 10.0; }
double aggregateBucket(List<double> samples, AggKind kind) {
  if (samples.isEmpty) return 0.0;
  if (kind == AggKind.last) return round1dp(samples.last);
  final sum = samples.fold<double>(0.0, (a, b) => a + b);
  return round1dp(sum / samples.length);
}
