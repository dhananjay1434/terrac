import 'dart:async';

import 'package:dmrv_app/services/api_base.dart';
import 'package:dmrv_app/ui/screens/enrollment_screen.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

/// P1-S8 — in-app enrollment replaces the compile-time ENROLLMENT_TOKEN.
/// Covers the shared base-URL resolver precedence, the enrollment state machine
/// (unenrolled → enrolling → enrolled/failed), and the failure-message mapping.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  group('resolveApiBaseUrl precedence', () {
    test('stored secure-storage value wins over the dart-define', () async {
      await persistApiBaseUrl('https://stored.example');
      expect(await resolveApiBaseUrl(), 'https://stored.example');
    });

    test('falls back to the dart-define (empty in tests) when unset', () async {
      // No stored value; the DMRV_API_BASE_URL define is absent under `flutter
      // test`, so the resolver yields ''.
      expect(await resolveApiBaseUrl(), '');
    });
  });

  group('enrollmentErrorMessage mapping', () {
    test('timeouts map to a connectivity message', () {
      expect(
        enrollmentErrorMessage(TimeoutException('x')),
        contains("Can't reach the server"),
      );
    });

    test('401/403/409 map to a token message', () {
      for (final code in ['401', '403', '409']) {
        expect(
          enrollmentErrorMessage(
            StateError('Device registration failed: $code bad'),
          ),
          contains('Token invalid or already used'),
        );
      }
    });

    test('anything else maps to the generic retry message', () {
      expect(
        enrollmentErrorMessage(StateError('boom')),
        contains('Enrollment failed'),
      );
    });
  });

  group('EnrollmentController state machine', () {
    test('success → enrolled, persists + retargets the base URL', () async {
      final container = ProviderContainer(
        overrides: [
          enrollmentRegisterProvider.overrideWithValue((token, url) async {}),
        ],
      );
      addTearDown(container.dispose);

      expect(
        container.read(enrollmentControllerProvider).status,
        EnrollmentStatus.idle,
      );

      await container
          .read(enrollmentControllerProvider.notifier)
          .enroll('tok-123', 'https://api.example');

      expect(
        container.read(enrollmentControllerProvider).status,
        EnrollmentStatus.enrolled,
      );
      // Live provider retargeted + persisted for the next launch.
      expect(container.read(apiBaseUrlProvider), 'https://api.example');
      expect(await resolveApiBaseUrl(), 'https://api.example');
    });

    test('a 401 leaves it failed with the token message', () async {
      final container = ProviderContainer(
        overrides: [
          enrollmentRegisterProvider.overrideWithValue(
            (token, url) async =>
                throw StateError('Device registration failed: 401 bad token'),
          ),
        ],
      );
      addTearDown(container.dispose);

      await container
          .read(enrollmentControllerProvider.notifier)
          .enroll('bad', 'https://api.example');

      final s = container.read(enrollmentControllerProvider);
      expect(s.status, EnrollmentStatus.failed);
      expect(s.error, contains('Token invalid or already used'));
    });
  });
}
