import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'api_base.dart';
import 'crypto_signer.dart';

/// V8 Part 4 (K) — device-facing read of reviewer verdicts on a batch's
/// media, so the app can surface "rejected: (reason)" and prompt a targeted
/// recapture instead of the operator learning only when the whole batch is
/// provisional. On-demand, no cache (small per-batch call); any failure
/// (offline, error) returns an empty list — a missing verdict list is not an
/// error state, just "nothing to show yet".
class MediaVerdict {
  const MediaVerdict({
    required this.operationId,
    required this.captureType,
    required this.status,
    required this.remarks,
  });

  final String operationId;
  final String? captureType;
  final String status;
  final String? remarks;

  static MediaVerdict fromJson(Map<String, dynamic> j) => MediaVerdict(
        operationId: (j['operation_id'] ?? '').toString(),
        captureType: j['capture_type'] as String?,
        status: (j['verification_status'] ?? '').toString(),
        remarks: j['verification_remarks'] as String?,
      );
}

class MediaVerdictService {
  static Future<List<MediaVerdict>> fetchForBatch(
    String batchUuid, {
    http.Client? client,
    String? apiBaseUrl,
  }) async {
    if (batchUuid.isEmpty) return const [];
    final base = apiBaseUrl ?? await resolveApiBaseUrl();
    if (base.isEmpty) return const [];

    final c = client ?? http.Client();
    try {
      final path = '/api/v1/batches/$batchUuid/media-verdicts';
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

      if (resp.statusCode != 200) return const [];
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      return (body['media'] as List<dynamic>? ?? [])
          .map((e) => MediaVerdict.fromJson(e as Map<String, dynamic>))
          .toList();
    } catch (e) {
      debugPrint('[MediaVerdictService] fetch failed: $e');
      return const [];
    } finally {
      if (client == null) c.close();
    }
  }
}
