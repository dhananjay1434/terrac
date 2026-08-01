/// Canonical signing bytes for a telemetry envelope — byte-matches the backend's
/// TelemetryChunkIn.canonical_bytes() and the firmware's canonical.c:
///   - keys sorted alphabetically
///   - compact separators (',' and ':'), no whitespace
///   - producer_signature excluded
///   - doubles at 1 decimal place (the FLOAT PRECISION INVARIANT; producers must
///     emit 1-decimal values — the golden-vector test enforces it)
///   - UTF-8
///
/// Proven against backend/tools/golden_vectors.json by
/// test/telemetry_canonical_test.dart.
library;

String canonicalJson(Map<String, dynamic> envelope) {
  final keys = envelope.keys.where((k) => k != 'producer_signature').toList()
    ..sort();
  final sb = StringBuffer('{');
  for (var i = 0; i < keys.length; i++) {
    if (i > 0) sb.write(',');
    sb.write('"');
    sb.write(keys[i]);
    sb.write('":');
    sb.write(_encode(envelope[keys[i]]));
  }
  sb.write('}');
  return sb.toString();
}

String _encode(dynamic v) {
  if (v == null) return 'null';
  if (v is String) return '"$v"'; // ASCII-safe inputs only (see canonical.c note)
  if (v is int) return v.toString();
  if (v is double) return v.toStringAsFixed(1);
  if (v is List) return '[${v.map(_encode).join(',')}]';
  throw ArgumentError('unsupported canonical value: $v');
}
