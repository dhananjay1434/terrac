import 'package:dmrv_app/services/sync_queue_manager.dart';
import 'package:flutter_test/flutter_test.dart';

/// P1-C2 — a skewed device clock is why v2-signed uploads 401 in a loop.
/// computeClockSkew turns the server `date` header into a surfaced skew so the
/// Sync Health screen can tell the operator to fix their clock.
void main() {
  final now = DateTime.utc(2026, 1, 1, 12, 0, 0); // 2026-01-01 is a Thursday

  group('computeClockSkew', () {
    test('server 30 min ahead is detected as a positive skew', () {
      final skew = computeClockSkew('Thu, 01 Jan 2026 12:30:00 GMT', now);
      expect(skew, isNotNull);
      expect(skew!.inMinutes, inInclusiveRange(29, 31));
      expect(skew.isNegative, isFalse);
    });

    test('server 30 min behind is detected as a negative skew', () {
      final skew = computeClockSkew('Thu, 01 Jan 2026 11:30:00 GMT', now);
      expect(skew, isNotNull);
      expect(skew!.isNegative, isTrue);
    });

    test('within tolerance (1 min) → null', () {
      expect(computeClockSkew('Thu, 01 Jan 2026 12:01:00 GMT', now), isNull);
    });

    test('null / empty / garbage header → null', () {
      expect(computeClockSkew(null, now), isNull);
      expect(computeClockSkew('', now), isNull);
      expect(computeClockSkew('not-a-date', now), isNull);
    });
  });
}
