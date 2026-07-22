import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/day_start_service.dart';

/// Deferred R6 — day-start audit lock. `isDayStartValid` is the pure
/// reconciliation: gate-off (default) always passes (grandfather); gate-on
/// requires an attestation dated today (device-local calendar day).
void main() {
  group('isDayStartValid', () {
    final today = DateTime(2026, 7, 23, 14, 30);

    test('gate off (default/grandfather) is always valid regardless of attestation', () {
      expect(
        isDayStartValid(enforced: false, lastAttestation: null, now: today),
        isTrue,
      );
      expect(
        isDayStartValid(
          enforced: false,
          lastAttestation: DateTime(2020, 1, 1),
          now: today,
        ),
        isTrue,
      );
    });

    test('gate on, no prior attestation -> invalid', () {
      expect(
        isDayStartValid(enforced: true, lastAttestation: null, now: today),
        isFalse,
      );
    });

    test('gate on, attestation earlier the SAME calendar day -> valid', () {
      final earlierToday = DateTime(2026, 7, 23, 6, 0);
      expect(
        isDayStartValid(enforced: true, lastAttestation: earlierToday, now: today),
        isTrue,
      );
    });

    test('gate on, attestation from a PRIOR day -> invalid (stale)', () {
      final yesterday = DateTime(2026, 7, 22, 23, 59);
      expect(
        isDayStartValid(enforced: true, lastAttestation: yesterday, now: today),
        isFalse,
      );
    });

    test('gate on, attestation from a future day (clock skew) -> invalid', () {
      // Never trust a future-dated attestation as "still valid" — a clock
      // that jumped forward and back could otherwise wedge the gate open.
      final tomorrow = DateTime(2026, 7, 24, 0, 1);
      expect(
        isDayStartValid(enforced: true, lastAttestation: tomorrow, now: today),
        isFalse,
      );
    });

    test('boundary: attestation at 00:00:00 of today -> valid', () {
      final midnightToday = DateTime(2026, 7, 23, 0, 0, 0);
      expect(
        isDayStartValid(enforced: true, lastAttestation: midnightToday, now: today),
        isTrue,
      );
    });

    test('boundary: attestation at 23:59:59 of yesterday -> invalid', () {
      final justBeforeMidnight = DateTime(2026, 7, 22, 23, 59, 59);
      expect(
        isDayStartValid(
          enforced: true,
          lastAttestation: justBeforeMidnight,
          now: today,
        ),
        isFalse,
      );
    });
  });
}
