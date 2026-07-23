import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'api_base.dart';
import 'crypto_signer.dart';

/// FM-4 — fetches the calling device's project config (registered feedstock
/// list + the methodology's positive list) so the sourcing screen can
/// resolve a real, project-scoped species instead of a hard-coded one.
///
/// Offline-first: the last successful fetch is cached in SharedPreferences
/// per project (mirrors ParcelService exactly), so a field device with no
/// connectivity can still resolve its feedstock from the last-seen config.
/// A failed fetch returns the cache, never throws.
class ProjectConfig {
  const ProjectConfig({
    required this.allowedFeedstocks,
    required this.positiveList,
    this.clientTarget,
  });

  final List<String> allowedFeedstocks;
  final List<String> positiveList;
  final int? clientTarget;

  Map<String, dynamic> toJson() => {
        'allowed_feedstocks': allowedFeedstocks,
        'positive_list': positiveList,
        if (clientTarget != null) 'client_target': clientTarget,
      };

  static ProjectConfig fromJson(Map<String, dynamic> j) => ProjectConfig(
        allowedFeedstocks: (j['allowed_feedstocks'] as List<dynamic>? ?? [])
            .map((e) => e.toString())
            .toList(),
        positiveList: (j['positive_list'] as List<dynamic>? ?? [])
            .map((e) => e.toString())
            .toList(),
        clientTarget: (j['client_target'] as num?)?.toInt(),
      );
}

class ProjectService {
  static String _cacheKey(String projectId) => 'dmrv.project_config.v1.$projectId';

  /// Fetch [projectId]'s config from the backend (device-signed GET), cache
  /// on success, and return it. On any failure (offline, error status, bad
  /// body) returns the cached config instead — never throws. Returns null
  /// only when there is neither a live fetch nor a cache (true offline
  /// first-run) — callers must treat null as "feedstock unresolved", never
  /// substitute a hard-coded species.
  static Future<ProjectConfig?> fetchProjectConfig(
    String projectId, {
    http.Client? client,
    String? apiBaseUrl,
  }) async {
    if (projectId.isEmpty) return null;
    final base = apiBaseUrl ?? await resolveApiBaseUrl();
    if (base.isEmpty) return loadCached(projectId);

    final c = client ?? http.Client();
    try {
      const path = '/api/v1/project';
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
        Uri.parse('$base$path?project_id=${Uri.encodeQueryComponent(projectId)}'),
        headers: {
          'X-Device-Id': deviceId,
          'X-Signature': signature,
          'X-Canonical-Version': '2',
          'X-Signed-At': signedAt,
        },
      ).timeout(const Duration(seconds: 8));

      if (resp.statusCode != 200) return loadCached(projectId);
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      final config = ProjectConfig.fromJson(body);
      await _cache(projectId, config);
      return config;
    } catch (e) {
      debugPrint('[ProjectService] fetch failed (using cache): $e');
      return loadCached(projectId);
    } finally {
      if (client == null) c.close();
    }
  }

  static Future<ProjectConfig?> loadCached(String projectId) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_cacheKey(projectId));
    if (raw == null || raw.isEmpty) return null;
    try {
      final decoded = jsonDecode(raw) as Map<String, dynamic>;
      return ProjectConfig.fromJson(decoded);
    } catch (_) {
      return null;
    }
  }

  static Future<void> _cache(String projectId, ProjectConfig config) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_cacheKey(projectId), jsonEncode(config.toJson()));
  }
}
