import 'dart:convert';

/// Parsed enrollment payload from the portal's mint QR / copy string.
class EnrollmentPayload {
  const EnrollmentPayload({required this.url, required this.token});
  final String url;
  final String token;
}

/// Parses the portal enrollment payload `dmrv-enroll:v1:{"url":..,"token":..}`.
/// Returns null when [raw] is not a well-formed enrollment payload, so the
/// caller can fall back to treating the input as a bare token. Pure + testable;
/// never throws on bad input.
EnrollmentPayload? parseEnrollmentQr(String raw) {
  const prefix = 'dmrv-enroll:v1:';
  final s = raw.trim();
  if (!s.startsWith(prefix)) return null;
  final jsonPart = s.substring(prefix.length);
  try {
    final decoded = jsonDecode(jsonPart);
    if (decoded is! Map) return null;
    final url = decoded['url'];
    final token = decoded['token'];
    // token is required; url may be empty string (admin minted without a base
    // url) — in that case the operator keeps/edits the URL field manually.
    if (token is! String || token.trim().isEmpty) return null;
    return EnrollmentPayload(
      url: url is String ? url.trim() : '',
      token: token.trim(),
    );
  } catch (_) {
    return null;
  }
}
