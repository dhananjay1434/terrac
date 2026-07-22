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

/// Deferred R2 — reconcile a persisted (possibly stale) local wizard phase
/// against server truth for dispatch restart-resilience. Pure, string-based
/// ('draft'|'in_transit'|'received') rather than sharing dispatch_screen.dart's
/// private `_Phase` enum — this is the currency the server's status field
/// already uses.
///
/// Server truth always wins when available: a persisted phase can only be
/// STALE (a transition already succeeded right before the app was killed,
/// so resuming to the old phase would re-show an editable form for a
/// dispatch that's already moved on) or, in a rare case, momentarily AHEAD —
/// either way, trusting the server avoids resurrecting a wrong phase. Only
/// when the server is unreachable (offline resume) does the persisted value
/// stand in. No persisted value and no server status means a genuinely
/// fresh dispatch — draft.
String resolveResumePhase({
  required String? persistedPhase,
  required String? serverStatus,
}) {
  if (serverStatus != null && serverStatus.isNotEmpty) return serverStatus;
  if (persistedPhase != null && persistedPhase.isNotEmpty) return persistedPhase;
  return 'draft';
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

  /// Deferred R2 — device-signed status read (GET /api/v1/dispatch/{uuid}),
  /// used to reconcile a resumed wizard against server truth. Returns null
  /// on ANY failure (offline, 404, error) — the caller falls back to the
  /// persisted phase via [resolveResumePhase], never assumes a status.
  static Future<String?> fetchStatus({
    required String dispatchUuid,
    http.Client? client,
    String? apiBaseUrl,
  }) async {
    final base = apiBaseUrl ?? await resolveApiBaseUrl();
    if (base.isEmpty) return null;

    final c = client ?? http.Client();
    try {
      final path = '/api/v1/dispatch/$dispatchUuid';
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

      if (resp.statusCode != 200) return null;
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      return body['status'] as String?;
    } catch (e) {
      debugPrint('[DispatchService] status fetch failed (offline?): $e');
      return null;
    } finally {
      if (client == null) c.close();
    }
  }

  // ---------------------------------------------------------------------
  // Deferred R2 — persisted in-flight wizard state (restart-resilience).
  // Only a dispatch_uuid + phase string are stored here — neither is PII,
  // which is why SharedPreferences (unencrypted) is an acceptable store for
  // this, unlike evidence/PII which always goes through the encrypted
  // SQLCipher database. One fixed key, not uuid-keyed: this screen only
  // ever has ONE active dispatch wizard at a time, and the uuid itself
  // isn't known until _createDraft() succeeds — the screen needs to
  // discover "is there an in-progress one at all" on initState, before it
  // has a uuid to key by.
  // ---------------------------------------------------------------------

  static const _wizardStateKey = 'dmrv.dispatch_wizard.v1';

  static Future<void> saveInFlightDispatch(String dispatchUuid, String phase) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _wizardStateKey,
      jsonEncode({'dispatch_uuid': dispatchUuid, 'phase': phase}),
    );
  }

  /// Returns `(dispatchUuid, phase)`, or null if nothing is persisted or the
  /// stored value is corrupt (never throws — worst case is losing the resume
  /// convenience, not crashing the screen).
  static Future<(String, String)?> loadInFlightDispatch() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_wizardStateKey);
    if (raw == null || raw.isEmpty) return null;
    try {
      final decoded = jsonDecode(raw) as Map<String, dynamic>;
      final uuid = decoded['dispatch_uuid'] as String?;
      final phase = decoded['phase'] as String?;
      if (uuid == null || uuid.isEmpty || phase == null || phase.isEmpty) {
        return null;
      }
      return (uuid, phase);
    } catch (_) {
      return null;
    }
  }

  static Future<void> clearInFlightDispatch() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_wizardStateKey);
  }
}
