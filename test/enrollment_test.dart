import 'dart:async';

import 'package:dmrv_app/services/api_base.dart';
import 'package:dmrv_app/ui/screens/enrollment_screen.dart';
import 'package:flutter/material.dart';
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

  group('EnrollmentScreen paste-to-autofill', () {
    Future<void> pump(WidgetTester tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(home: EnrollmentScreen()),
        ),
      );
      await tester.pumpAndSettle();
    }

    // The token field is the first TextField on the screen, the URL field the
    // second (their build order in EnrollmentScreen).
    Finder tokenField() => find.byType(TextField).first;

    testWidgets('pasting a full dmrv-enroll payload splits url + token',
        (tester) async {
      await pump(tester);

      await tester.enterText(
        tokenField(),
        'dmrv-enroll:v1:{"url":"https://dmrv-api.onrender.com","token":"NCt_ABC"}',
      );
      await tester.pumpAndSettle();

      // Token field is reduced to the bare token; URL field is filled.
      expect(find.text('NCt_ABC'), findsOneWidget);
      expect(find.text('https://dmrv-api.onrender.com'), findsOneWidget);
      // The raw payload string must NOT remain in any field.
      expect(find.textContaining('dmrv-enroll:v1:'), findsNothing);
    });

    testWidgets('pasting a bare token leaves it as-is (manual flow intact)',
        (tester) async {
      await pump(tester);

      await tester.enterText(
        tokenField(),
        'NCt_VLaTnV9oMnpk8gdelqWyhqA7aP2PNxVW7irq7S8',
      );
      await tester.pumpAndSettle();

      expect(
        find.text('NCt_VLaTnV9oMnpk8gdelqWyhqA7aP2PNxVW7irq7S8'),
        findsOneWidget,
      );
    });
  });
}
