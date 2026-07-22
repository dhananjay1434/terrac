import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'api_base.dart';
import 'crypto_signer.dart';

/// V8 Part 3.4 — facility picker (mirrors ParcelService) + dispatch state
/// transitions (Submit → in_transit, Mark Received → received).
///
/// Transitions are deliberately NOT outbox operations: unlike a batch/farmer/
/// dispatch-DRAFT write (fire-and-forget, syncs whenever connectivity
/// returns), a transition needs (a) the draft to already exist server-side and
/// (b) an IMMEDIATE result — specifically whether the facility's re-weigh was
/// flagged as a discrepancy — to show the operator right now. Both requirements
/// mean this must be a direct, connectivity-required signed call: attempting a
/// transition while offline fails honestly (returns null) rather than queuing
/// a fake "submitted" state the operator would trust.
class FacilityOption {
  const FacilityOption({required this.uuid, required this.name, required this.type});
  final String uuid;
  final String name;
  final String type;

  Map<String, dynamic> toJson() => {
        'facility_uuid': uuid,
        'name': name,
        'facility_type': type,
      };

  static FacilityOption fromJson(Map<String, dynamic> j) => FacilityOption(
        uuid: (j['facility_uuid'] ?? '').toString(),
        name: (j['name'] ?? '').toString(),
        type: (j['facility_type'] ?? '').toString(),
      );
}

class DispatchTransitionResult {
  const DispatchTransitionResult({
    required this.status,
    this.weightFlagged,
    this.weightDeltaPct,
  });
  final String status;
  final bool? weightFlagged;
  final double? weightDeltaPct;
}

class DispatchService {
  static const _facilityCacheKey = 'dmrv.facilities.v1';

  /// Fetch active facilities (device-signed GET), cache on success, and
  /// return them. On any failure returns the cache instead — never throws.
  static Future<List<FacilityOption>> fetchFacilities({
    http.Client? client,
    String? apiBaseUrl,
  }) async {
    final base = apiBaseUrl ?? await resolveApiBaseUrl();
    if (base.isEmpty) return _loadCachedFacilities();

    final c = client ?? http.Client();
    try {
      const path = '/api/v1/facilities';
      final deviceId = await CryptoSigner.getDeviceId();
      final (signature, signedAt) = await CryptoSigner.signRequestV2(
        method: 'GET',
        path: path,
        idempotencyKey: '',
        deviceId: deviceId,
        jsonBody: '',
      );
      final resp = await c.get(
        Uri.parse('$base$path'),
        headers: {
          'X-Device-Id': deviceId,
          'X-Signature': signature,
          'X-Canonical-Version': '2',
          'X-Signed-At': signedAt,
        },
      ).timeout(const Duration(seconds: 8));

      if (resp.statusCode != 200) return _loadCachedFacilities();
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      final list = (body['facilities'] as List<dynamic>? ?? [])
          .map((e) => FacilityOption.fromJson(e as Map<String, dynamic>))
          .toList();
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(
        _facilityCacheKey,
        jsonEncode(list.map((f) => f.toJson()).toList()),
      );
      return list;
    } catch (e) {
      debugPrint('[DispatchService] facility fetch failed (using cache): $e');
      return _loadCachedFacilities();
    } finally {
      if (client == null) c.close();
    }
  }

  static Future<List<FacilityOption>> _loadCachedFacilities() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_facilityCacheKey);
    if (raw == null || raw.isEmpty) return const [];
    try {
      final decoded = jsonDecode(raw) as List<dynamic>;
      return decoded
          .map((e) => FacilityOption.fromJson(e as Map<String, dynamic>))
          .toList();
    } catch (_) {
      return const [];
    }
  }

  /// Advance [dispatchUuid] to [targetStatus] ('in_transit' | 'received').
  /// [weightFacilityKg] is required when targetStatus == 'received'.
  /// Returns null on ANY failure (offline, rejected, error) — the caller must
  /// treat null as "did not happen", never assume success.
  static Future<DispatchTransitionResult?> transition({
    required String dispatchUuid,
    required String targetStatus,
    double? weightFacilityKg,
    http.Client? client,
    String? apiBaseUrl,
  }) async {
    final base = apiBaseUrl ?? await resolveApiBaseUrl();
    if (base.isEmpty) return null;

    final c = client ?? http.Client();
    try {
      final path = '/api/v1/dispatch/$dispatchUuid/transition';
      final deviceId = await CryptoSigner.getDeviceId();
      final bodyMap = <String, dynamic>{
        'target_status': targetStatus,
        'weight_facility_kg': ?weightFacilityKg,
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
          .timeout(const Duration(seconds: 10));

      if (resp.statusCode != 200) {
        debugPrint('[DispatchService] transition rejected: ${resp.statusCode} ${resp.body}');
        return null;
      }
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      return DispatchTransitionResult(
        status: (body['dispatch_status'] ?? '').toString(),
        weightFlagged: body['weight_flagged'] as bool?,
        weightDeltaPct: (body['weight_delta_pct'] as num?)?.toDouble(),
      );
    } catch (e) {
      debugPrint('[DispatchService] transition failed (offline?): $e');
      return null;
    } finally {
      if (client == null) c.close();
    }
  }
}
