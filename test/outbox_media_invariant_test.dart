import 'package:dmrv_app/data/local/app_database.dart';
import 'package:flutter_test/flutter_test.dart';

/// P1-C7 — a media-bearing outbox row must carry photo_path at INSERT time, so
/// an unsyncable row fails at the capture site instead of poisoning as
/// FAILED_PERMANENTLY at sync time.
void main() {
  group('assertOutboxMediaInvariant', () {
    test('sha256_hash without photo_path throws', () {
      expect(
        () => assertOutboxMediaInvariant('moisture_readings', {
          'sha256_hash': 'a' * 64,
          'photo_path': null,
        }),
        throwsArgumentError,
      );
    });

    test('sha256_hash with an empty photo_path throws', () {
      expect(
        () => assertOutboxMediaInvariant('composite_pile_samples', {
          'sha256_hash': 'a' * 64,
          'photo_path': '',
        }),
        throwsArgumentError,
      );
    });

    test('sha256_hash with a real photo_path is allowed', () {
      expect(
        () => assertOutboxMediaInvariant('moisture_readings', {
          'sha256_hash': 'a' * 64,
          'photo_path': '/sandbox/p.jpg',
        }),
        returnsNormally,
      );
    });

    test('a non-media row (no sha256_hash) is allowed', () {
      expect(
        () => assertOutboxMediaInvariant('system_metadata', {
          'batch_uuid': 'b1',
        }),
        returnsNormally,
      );
    });
  });
}
