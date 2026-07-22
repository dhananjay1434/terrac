import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'api_base.dart';
import 'crypto_signer.dart';

/// Deferred R3 — bulk-density calibration capture. Submits to the new
/// device-signed `POST /api/v1/density-tests` (F's existing
/// `/portal/bulk-density-tests` route is admin/portal-only and cannot be
/// called by a device). Direct signed call, mirroring
/// [DispatchService.transition] — this needs an immediate result (the
/// server-computed density, to show the operator right now), so it is NOT
/// an outbox operation; offline submission fails honestly (returns null)
/// rather than queuing a fake "submitted" state.
class DensityTestResult {
  const DensityTestResult({
    required this.testUuid,
    required this.densityKgPerL,
  });
  final String testUuid;
  final double densityKgPerL;
}

/// Pure, DISPLAY ONLY: mirrors the server's authoritative formula
/// (mass_kg / volume_l) exactly, so the operator sees a live estimate before
/// submitting — but the server always recomputes and stores its own value;
/// this is never sent as a trusted input. Returns null on a non-positive
/// mass/volume rather than throwing (the operator just sees no readout yet).
double? displayDensityKgPerL({required double massKg, required double volumeL}) {
  if (massKg <= 0 || volumeL <= 0) return null;
  return massKg / volumeL;
}

class DensityService {
  /// Submit a density calibration test. Returns null on ANY failure
  /// (offline, rejected, error) — the caller must treat null as "did not
  /// happen", never assume success.
  static Future<DensityTestResult?> submitDensityTest({
    required String testUuid,
    required String projectId,
    required double massKg,
    required double volumeL,
    http.Client? client,
    String? apiBaseUrl,
  }) async {
    final base = apiBaseUrl ?? await resolveApiBaseUrl();
    if (base.isEmpty) return null;

    final c = client ?? http.Client();
    try {
      const path = '/api/v1/density-tests';
      final deviceId = await CryptoSigner.getDeviceId();
      final bodyMap = <String, dynamic>{
        'test_uuid': testUuid,
        'project_id': projectId,
        'mass_kg': massKg,
        'volume_l': volumeL,
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

      if (resp.statusCode != 201) {
        debugPrint(
          '[DensityService] submit rejected: ${resp.statusCode} ${resp.body}',
        );
        return null;
      }
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      return DensityTestResult(
        testUuid: (body['test_uuid'] ?? '').toString(),
        densityKgPerL: (body['density_kg_per_l'] as num?)?.toDouble() ?? 0.0,
      );
    } catch (e) {
      debugPrint('[DensityService] submit failed (offline?): $e');
      return null;
    } finally {
      if (client == null) c.close();
    }
  }
}
