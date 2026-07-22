import 'package:shared_preferences/shared_preferences.dart';

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
}
