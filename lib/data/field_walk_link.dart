import 'dart:convert';

/// V8 Part 5 (A phase-2) — a server-signed field-walk link, exactly as
/// minted by portal `POST /portal/parcels/{uuid}/field-walk-link` and
/// encoded for QR display as `dmrv-fieldwalk:v1:{"payload":...,"kid":...,
/// "signature":...}`. `payload` itself is the raw JSON string the server
/// signed (containing parcel_uuid/nonce/issued_at/expires_at) — kept intact
/// (not re-encoded) so the signature the app verifies is over the EXACT
/// bytes the server signed.
class FieldWalkLink {
  const FieldWalkLink({
    required this.payload,
    required this.kid,
    required this.signature,
    required this.parcelUuid,
    required this.expiresAt,
  });

  final String payload;
  final String kid;
  final String signature;
  final String parcelUuid;
  final DateTime expiresAt;

  bool get isExpired => DateTime.now().toUtc().isAfter(expiresAt);
}

/// Parses `dmrv-fieldwalk:v1:{...}` into a [FieldWalkLink]. Returns null for
/// anything malformed — pure + testable, never throws on bad input (mirrors
/// `parseEnrollmentQr`).
FieldWalkLink? parseFieldWalkLink(String raw) {
  const prefix = 'dmrv-fieldwalk:v1:';
  final s = raw.trim();
  if (!s.startsWith(prefix)) return null;
  final jsonPart = s.substring(prefix.length);
  try {
    final decoded = jsonDecode(jsonPart);
    if (decoded is! Map) return null;
    final payload = decoded['payload'];
    final kid = decoded['kid'];
    final signature = decoded['signature'];
    if (payload is! String || payload.isEmpty) return null;
    if (kid is! String || kid.isEmpty) return null;
    if (signature is! String || signature.isEmpty) return null;

    final innerDecoded = jsonDecode(payload);
    if (innerDecoded is! Map) return null;
    final parcelUuid = innerDecoded['parcel_uuid'];
    final expiresAtRaw = innerDecoded['expires_at'];
    if (parcelUuid is! String || parcelUuid.isEmpty) return null;
    if (expiresAtRaw is! String) return null;
    final expiresAt = DateTime.tryParse(expiresAtRaw);
    if (expiresAt == null) return null;

    return FieldWalkLink(
      payload: payload,
      kid: kid,
      signature: signature,
      parcelUuid: parcelUuid,
      expiresAt: expiresAt.toUtc(),
    );
  } catch (_) {
    return null;
  }
}
