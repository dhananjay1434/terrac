import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../data/field_walk_link.dart';
import 'api_base.dart';
import 'crypto_signer.dart';
import 'server_signature_verifier.dart';

/// V8 Part 5 (A phase-2) — ground-truthed parcel boundary. A field-walk
/// [FieldWalkLink] authorizes exactly one walk of one parcel (server-signed,
/// single-use); this service verifies that link client-side (reusing
/// [ServerSignatureVerifier] — the SAME cached-pubkey mechanism Part 0.4's
/// remote-config document uses), then submits the recorded GPS points as a
/// direct signed call (like [DispatchService.transition] — this needs an
/// immediate result, so it is NOT an outbox operation; offline submission
/// fails honestly rather than queuing a walk the server hasn't verified).
class FieldWalkResult {
  const FieldWalkResult({
    required this.parcelUuid,
    required this.computedAreaM2,
    required this.overlapRatioVsDeclared,
  });
  final String parcelUuid;
  final double computedAreaM2;
  final double? overlapRatioVsDeclared;
}

class FieldWalkService {
  /// Verify the link's server signature. False on any tamper, expiry, or
  /// missing/unrefreshed pubkey cache — fail-closed, never throws.
  static Future<bool> verifyLink(FieldWalkLink link) async {
    if (link.isExpired) return false;
    return ServerSignatureVerifier.verify(
      payload: utf8.encode(link.payload),
      signatureB64Url: link.signature,
      kid: link.kid,
    );
  }

  /// Pure guard mirroring the backend's `min_length=3` on `points` — checked
  /// client-side too so the operator gets immediate feedback instead of a
  /// round-trip 422.
  @visibleForTesting
  static bool hasEnoughPoints(List<List<double>> points) => points.length >= 3;

  /// Submit the walked track. Returns null on any failure (offline, rejected
  /// link, malformed track) — the caller must treat null as "did not
  /// happen," never assume success.
  static Future<FieldWalkResult?> submit({
    required FieldWalkLink link,
    required List<List<double>> points,
    http.Client? client,
    String? apiBaseUrl,
  }) async {
    if (!hasEnoughPoints(points)) return null;
    final base = apiBaseUrl ?? await resolveApiBaseUrl();
    if (base.isEmpty) return null;

    final c = client ?? http.Client();
    try {
      const path = '/api/v1/field-walk';
      final deviceId = await CryptoSigner.getDeviceId();
      final bodyMap = <String, dynamic>{
        'link_payload': link.payload,
        'link_kid': link.kid,
        'link_signature': link.signature,
        'points': points,
      };
      final jsonBody = jsonEncode(bodyMap);
      final (signature, signedAt) = await CryptoSigner.signRequestV2(
        method: 'POST',
        path: path,
        idempotencyKey: '',
        deviceId: deviceId,
        jsonBody: jsonBody,
      );
      final resp = await c
          .post(
            Uri.parse('$base$path'),
            headers: {
              'Content-Type': 'application/json',
              'X-Device-Id': deviceId,
              'X-Signature': signature,
              'X-Canonical-Version': '2',
              'X-Signed-At': signedAt,
            },
            body: jsonBody,
          )
          .timeout(const Duration(seconds: 15));

      if (resp.statusCode != 201) {
        debugPrint(
          '[FieldWalkService] submit rejected: ${resp.statusCode} ${resp.body}',
        );
        return null;
      }
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      return FieldWalkResult(
        parcelUuid: (body['parcel_uuid'] ?? '').toString(),
        computedAreaM2: (body['computed_area_m2'] as num?)?.toDouble() ?? 0.0,
        overlapRatioVsDeclared:
            (body['overlap_ratio_vs_declared'] as num?)?.toDouble(),
      );
    } catch (e) {
      debugPrint('[FieldWalkService] submit failed (offline?): $e');
      return null;
    } finally {
      if (client == null) c.close();
    }
  }
}
