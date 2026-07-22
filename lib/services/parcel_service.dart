import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'api_base.dart';
import 'crypto_signer.dart';
import 'geofence_check.dart';

/// V8 Part 1.6 — fetches the approved source parcels for a project so the
/// sourcing screen can let the operator pick the batch's source parcel. The
/// selected `parcel_uuid` then rides the batch payload and the server checks
/// the batch GPS point-in-polygon against that approved, non-overlapping
/// parcel (geo.py → QUARANTINE_GPS_OUTSIDE_PARCEL).
///
/// Offline-first: the last successful list is cached in SharedPreferences per
/// project, so a field device with no connectivity can still show and select
/// from the parcels it last saw. A failed fetch returns the cache, never throws.
class ParcelOption {
  const ParcelOption({required this.uuid, required this.name, this.boundaryGeojson});
  final String uuid;
  final String name;

  /// Deferred R4 — present only when the backend's
  /// `device_parcel_geometry_enabled()` flag is on; null otherwise
  /// (today's default). Rides the SAME SharedPreferences cache as
  /// uuid/name — no separate store or Drift table needed.
  final String? boundaryGeojson;

  Map<String, dynamic> toJson() => {
        'parcel_uuid': uuid,
        'name': name,
        if (boundaryGeojson != null) 'boundary_geojson': boundaryGeojson,
      };

  static ParcelOption fromJson(Map<String, dynamic> j) => ParcelOption(
        uuid: (j['parcel_uuid'] ?? '').toString(),
        name: (j['name'] ?? '').toString(),
        boundaryGeojson: j['boundary_geojson'] as String?,
      );

  /// The boundary ring for the on-device geofence check, or null when no
  /// geometry is cached (flag off, or unparsable) — capture proceeds
  /// ungated in that case (grandfathered).
  List<List<double>>? get boundaryRing =>
      boundaryGeojson != null ? parsePolygonExteriorRing(boundaryGeojson!) : null;
}

class ParcelService {
  static String _cacheKey(String projectId) => 'dmrv.parcels.v1.$projectId';

  /// Fetch approved parcels for [projectId] from the backend (device-signed
  /// GET), cache on success, and return them. On any failure (offline, error
  /// status, bad body) returns the cached list instead — never throws.
  static Future<List<ParcelOption>> fetchForProject(
    String projectId, {
    http.Client? client,
    String? apiBaseUrl,
  }) async {
    if (projectId.isEmpty) return const [];
    final base = apiBaseUrl ?? await resolveApiBaseUrl();
    if (base.isEmpty) return loadCached(projectId);

    final c = client ?? http.Client();
    try {
      const path = '/api/v1/parcels';
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
      final list = (body['parcels'] as List<dynamic>? ?? [])
          .map((e) => ParcelOption.fromJson(e as Map<String, dynamic>))
          .toList();
      await _cache(projectId, list);
      return list;
    } catch (e) {
      debugPrint('[ParcelService] fetch failed (using cache): $e');
      return loadCached(projectId);
    } finally {
      if (client == null) c.close();
    }
  }

  static Future<List<ParcelOption>> loadCached(String projectId) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_cacheKey(projectId));
    if (raw == null || raw.isEmpty) return const [];
    try {
      final decoded = jsonDecode(raw) as List<dynamic>;
      return decoded
          .map((e) => ParcelOption.fromJson(e as Map<String, dynamic>))
          .toList();
    } catch (_) {
      return const [];
    }
  }

  /// Deferred R4 — the cached boundary ring for [parcelUuid] within
  /// [projectId]'s last-fetched parcel list, or null when the parcel isn't
  /// cached, has no geometry (flag off), or the geometry doesn't parse.
  /// Reads the cache directly rather than re-fetching — the picker screen
  /// already populated it via [fetchForProject] when the operator selected
  /// this parcel.
  static Future<List<List<double>>?> boundaryRingFor(
    String projectId,
    String parcelUuid,
  ) async {
    final cached = await loadCached(projectId);
    for (final p in cached) {
      if (p.uuid == parcelUuid) return p.boundaryRing;
    }
    return null;
  }

  static Future<void> _cache(String projectId, List<ParcelOption> list) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _cacheKey(projectId),
      jsonEncode(list.map((p) => p.toJson()).toList()),
    );
  }
}
