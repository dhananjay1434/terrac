import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/main.dart';

/// P0.4 — a release build must never ship with crash reporting silently off.
/// [validateReleaseConfig] is the pure, testable core of that guard.
void main() {
  group('validateReleaseConfig', () {
    test('release build with empty DSN throws (refuses to boot blind)', () {
      expect(
        () => validateReleaseConfig(isRelease: true, dsn: ''),
        throwsA(isA<StateError>()),
      );
    });

    test('release build with a DSN returns it', () {
      const dsn = 'https://abc123@o0.ingest.sentry.io/1';
      expect(
        validateReleaseConfig(isRelease: true, dsn: dsn),
        equals(dsn),
      );
    });

    test('debug/profile build with empty DSN is allowed (returns empty)', () {
      expect(
        validateReleaseConfig(isRelease: false, dsn: ''),
        equals(''),
      );
    });

    test('debug build with a DSN returns it', () {
      const dsn = 'https://xyz@o0.ingest.sentry.io/2';
      expect(
        validateReleaseConfig(isRelease: false, dsn: dsn),
        equals(dsn),
      );
    });
  });
}
