/// STITCHING Phase G — canonical signing bytes for a telemetry envelope.
///
/// MUST byte-match backend TelemetryChunkIn.canonical_bytes():
///   - keys sorted alphabetically
///   - compact separators (no spaces): , and :
///   - the producer_signature field EXCLUDED from the signed bytes
///   - UTF-8
///
/// NOT YET IMPLEMENTED. This throws on purpose so the conformance test in
/// test/telemetry_canonical_test.dart fails until a real implementation lands
/// (pairs with the app-courier work, STITCHING Phase F). Do not fake it.
library;

String canonicalJson(Map<String, dynamic> envelope) {
  throw UnimplementedError(
    'canonicalJson not implemented — see STITCHING Phase F/G',
  );
}
