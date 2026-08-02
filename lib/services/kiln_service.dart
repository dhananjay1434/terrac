import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'api_base.dart';
import 'crypto_signer.dart';

/// P2.4 — fetches the calling device's kiln's DECLARED sensor_profile from
/// the backend so the burn UI can pick the right telemetry view. Modeled
/// exactly on [ProjectService] (see project_service.dart): device-signed GET,
/// same header/timeout discipline, offline-first cache.
///
/// Never throws — a failed fetch returns the cache; kiln selection must never
/// block on the network. Returns the raw profile string; parse it with
/// `sensorProfileFromString` at the call site.
class KilnService {
  static String _cacheKey(String kilnId) => 'dmrv.kiln_profile.v1.$kilnId';

  /// Fetch [kilnId]'s declared sensor_profile (device-signed GET), cache on
  /// success, and return it. On any failure (offline, error status, bad
  /// body) returns the cached profile instead — never throws. Returns null
  /// only when there is neither a live fetch nor a cache.
  static Future<String?> fetchKilnProfile(
    String kilnId, {
    http.Client? client,
    String? apiBaseUrl,
  }) async {
    if (kilnId.isEmpty) return null;
    final base = apiBaseUrl ?? await resolveApiBaseUrl();
    if (base.isEmpty) return loadCached(kilnId);

    final c = client ?? http.Client();
    try {
      const path = '/api/v1/kiln';
      final deviceId = await CryptoSigner.getDeviceId();
      // Sign the v2 canonical (empty body for a GET), matching the server's
      // verify_signature. The query string is not part of the signed path.
      final (signature, signedAt) = await CryptoSigner.signRequestV2(
        method: 'GET',
        path: path,
        idempotencyKey: '',
        deviceId: deviceId,
        jsonBody: '',
      );
      final resp = await c.get(
        Uri.parse('$base$path?kiln_id=${Uri.encodeQueryComponent(kilnId)}'),
        headers: {
          'X-Device-Id': deviceId,
          'X-Signature': signature,
          'X-Canonical-Version': '2',
          'X-Signed-At': signedAt,
        },
      ).timeout(const Duration(seconds: 8));

      if (resp.statusCode != 200) return loadCached(kilnId);
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      final profile = body['sensor_profile'] as String?;
      if (profile == null) return loadCached(kilnId);
      await _cache(kilnId, profile);
      return profile;
    } catch (e) {
      debugPrint('[KilnService] fetch failed (using cache): $e');
      return loadCached(kilnId);
    } finally {
      if (client == null) c.close();
    }
  }

  static Future<String?> loadCached(String kilnId) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_cacheKey(kilnId));
  }

  static Future<void> _cache(String kilnId, String profile) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_cacheKey(kilnId), profile);
  }
}
