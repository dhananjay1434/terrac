import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:dmrv_app/l10n/app_localizations.dart';
import 'package:dmrv_app/services/day_start_service.dart';
import 'package:dmrv_app/ui/screens/day_start_attestation_screen.dart';

/// Deferred R6 + PR-5 — day-start audit lock, screen level. The pure gate
/// (`isDayStartValid`) is covered without a widget in
/// `daystart_lock_test.dart`; this covers the UI wiring that's genuinely
/// exercisable without a real camera (same documented CameraController
/// limitation as farmer_kyc_media_test.dart): checkbox gating, the
/// facility picker (cached-facilities path), and that confirm stays
/// disabled without a captured facility photo even once every other
/// requirement is met.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({});
  });

  Future<void> pumpScreen(WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: DayStartAttestationScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('confirm button is disabled until all three boxes are checked', (
    tester,
  ) async {
    await pumpScreen(tester);

    final confirmFinder = find.bySemanticsIdentifier('daystart-confirm-btn');
    expect(find.text('CONFIRM & START DAY'), findsOneWidget);

    await tester.tap(find.bySemanticsIdentifier('daystart-clock-check'));
    await tester.pumpAndSettle();
    await tester.tap(find.bySemanticsIdentifier('daystart-project-check'));
    await tester.pumpAndSettle();
    // Still missing the third checkbox — confirm must not have navigated.
    await tester.tap(confirmFinder, warnIfMissed: false);
    await tester.pumpAndSettle();
    expect(find.byType(DayStartAttestationScreen), findsOneWidget);
  });

  testWidgets(
    'confirm stays disabled after all three boxes when no photo is captured',
    (tester) async {
      await pumpScreen(tester);

      await tester.tap(find.bySemanticsIdentifier('daystart-clock-check'));
      await tester.pumpAndSettle();
      await tester.tap(find.bySemanticsIdentifier('daystart-project-check'));
      await tester.pumpAndSettle();
      await tester.tap(find.bySemanticsIdentifier('daystart-calibration-check'));
      await tester.pumpAndSettle();

      // No facility (none cached) and no photo captured (needs a real
      // camera) — confirm must still be a no-op.
      await tester.tap(
        find.bySemanticsIdentifier('daystart-confirm-btn'),
        warnIfMissed: false,
      );
      await tester.pumpAndSettle();
      expect(find.byType(DayStartAttestationScreen), findsOneWidget);
      expect(await DayStartService.loadLastAttestation(), isNull);
    },
  );

  testWidgets('facility photo and video capture buttons render', (tester) async {
    await pumpScreen(tester);
    expect(find.bySemanticsIdentifier('daystart-photo-capture-btn'), findsOneWidget);
    expect(find.bySemanticsIdentifier('daystart-video-capture-btn'), findsOneWidget);
    expect(find.text('CAPTURE FACILITY PHOTO'), findsOneWidget);
  });

  testWidgets('no cached facilities shows the none-found message and retry', (
    tester,
  ) async {
    await pumpScreen(tester);
    expect(find.textContaining('No facilities found'), findsOneWidget);
    expect(find.bySemanticsIdentifier('daystart-facility-retry-btn'), findsOneWidget);
  });

  testWidgets('a cached facility list renders as a picker and can be selected', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({
      'dmrv.facilities.v1': jsonEncode([
        {
          'facility_uuid': 'fac-1',
          'name': 'Test Facility One',
          'facility_type': 'artisanal',
        },
      ]),
    });
    await pumpScreen(tester);
    expect(find.bySemanticsIdentifier('daystart-facility-picker'), findsOneWidget);

    await tester.tap(find.bySemanticsIdentifier('daystart-facility-picker'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Test Facility One').last);
    await tester.pumpAndSettle();

    // Facility selected, but confirm still disabled without a photo.
    await tester.tap(find.bySemanticsIdentifier('daystart-clock-check'));
    await tester.pumpAndSettle();
    await tester.tap(find.bySemanticsIdentifier('daystart-project-check'));
    await tester.pumpAndSettle();
    await tester.tap(find.bySemanticsIdentifier('daystart-calibration-check'));
    await tester.pumpAndSettle();
    await tester.tap(
      find.bySemanticsIdentifier('daystart-confirm-btn'),
      warnIfMissed: false,
    );
    await tester.pumpAndSettle();
    expect(find.byType(DayStartAttestationScreen), findsOneWidget);
  });

  testWidgets('back navigation is blocked (non-dismissible)', (tester) async {
    await pumpScreen(tester);
    // No AppBar/back button rendered at all — the only way forward is the
    // confirm button, enforced by PopScope(canPop: false) at the widget level.
    expect(find.byType(BackButton), findsNothing);
  });
}
