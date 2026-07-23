import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'api_base.dart';
import 'crypto_signer.dart';

/// Deferred R6 — day-start audit lock. Same `bool.fromEnvironment` pattern
/// as `DMRV_DEMO_MODE`/`DMRV_DEVICE_PARCEL_GEOMETRY` elsewhere in this
/// codebase. Defaults OFF (grandfather): this is a new UX-blocking gate
/// with no field validation yet, not a data-integrity backstop, so it does
/// not follow the "default-on" convention other compliance gates use.
const bool kDayStartLockEnabled = bool.fromEnvironment(
  'DMRV_DAYSTART_LOCK',
  defaultValue: false,
);

/// Pure gate: is the day-start attestation valid right now?
///
/// - [enforced] false (the default) → always valid — a device that has
///   never seen this feature is never retroactively locked out.
/// - [enforced] true → valid only when [lastAttestation] falls on the SAME
///   device-local calendar day as [now]. A null, prior-day, OR future-day
///   attestation (clock skew) is invalid — never trust a future-dated
///   attestation as "still good", which could otherwise wedge the gate open
///   across a clock jump.
bool isDayStartValid({
  required bool enforced,
  required DateTime? lastAttestation,
  required DateTime now,
}) {
  if (!enforced) return true;
  if (lastAttestation == null) return false;
  return lastAttestation.year == now.year &&
      lastAttestation.month == now.month &&
      lastAttestation.day == now.day;
}

/// Deferred R6 — persisted attestation date (SharedPreferences; not PII —
/// the stored value is just "operator confirmed on date X", same reasoning
/// as R2's dispatch-wizard-phase persistence).
class DayStartService {
  static const _prefsKey = 'dmrv.daystart_attestation.v1';

  /// Returns the last attestation timestamp, or null if none is stored or
  /// the stored value is corrupt (never throws).
  static Future<DateTime?> loadLastAttestation() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_prefsKey);
    if (raw == null || raw.isEmpty) return null;
    return DateTime.tryParse(raw);
  }

  static Future<void> saveAttestationNow() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefsKey, DateTime.now().toIso8601String());
  }

  // ---------------------------------------------------------------------
  // PR-5.2 — the operator's facility, persisted once picked (a device is
  // effectively tied to one facility across days; SharedPreferences is
  // fine here — a facility_uuid is not PII, same reasoning as R2's
  // dispatch-wizard-phase persistence).
  // ---------------------------------------------------------------------

  static const _facilityPrefsKey = 'dmrv.daystart_facility.v1';

  static Future<String?> loadSelectedFacility() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_facilityPrefsKey);
    return (raw == null || raw.isEmpty) ? null : raw;
  }

  static Future<void> saveSelectedFacility(String facilityUuid) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_facilityPrefsKey, facilityUuid);
  }

  // ---------------------------------------------------------------------
  // PR-5.2 — submit the server-side DayStartAudit record (mirrors
  // dispatch_service.dart's signed-call shape). Best-effort, NON-BLOCKING:
  // unlike DispatchService.transition (which deliberately requires
  // connectivity), a day-start gate must not brick the operator's day over
  // a network blip — a facility at dawn is exactly when signal is weakest.
  // Returns true on confirmed success; false on ANY failure (offline,
  // rejected, error), which the caller treats as "proceed anyway, evidence
  // media queues via its own outbox regardless of this call's outcome."
  // ---------------------------------------------------------------------

  static Future<bool> submitAudit({
    required String auditUuid,
    required String facilityUuid,
    required String auditDate,
    http.Client? client,
    String? apiBaseUrl,
  }) async {
    final base = apiBaseUrl ?? await resolveApiBaseUrl();
    if (base.isEmpty) return false;

    final c = client ?? http.Client();
    try {
      const path = '/api/v1/day-start-audits';
      final deviceId = await CryptoSigner.getDeviceId();
      final bodyMap = <String, dynamic>{
        'audit_uuid': auditUuid,
        'facility_uuid': facilityUuid,
        'audit_date': auditDate,
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
          .timeout(const Duration(seconds: 8));
      return resp.statusCode == 200 || resp.statusCode == 201;
    } catch (e) {
      debugPrint('[DayStartService] audit submit failed (offline?): $e');
      return false;
    } finally {
      if (client == null) c.close();
    }
  }
}
