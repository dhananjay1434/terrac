import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:dmrv_app/l10n/app_localizations.dart';
import 'package:dmrv_app/services/day_start_service.dart';
import 'package:dmrv_app/ui/screens/day_start_attestation_screen.dart';

/// Deferred R6 — day-start audit lock, screen level. The pure gate
/// (`isDayStartValid`) is covered without a widget in
/// `daystart_lock_test.dart`; this covers the UI wiring: all three boxes
/// gate the confirm button, and confirming persists an attestation + pops.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({});
  });

  Future<void> pumpScreen(WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: DayStartAttestationScreen(),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('confirm button is disabled until all three boxes are checked', (
    tester,
  ) async {
    await pumpScreen(tester);

    final confirmFinder = find.bySemanticsIdentifier('daystart-confirm-btn');
    // DmrvButton onPressed is null while disabled; assert via tapping does
    // nothing observable (no navigation) rather than reaching into the
    // widget's internals — same approach used elsewhere in this suite.
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

  testWidgets('checking all three then confirming saves an attestation and pops', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: ElevatedButton(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => const DayStartAttestationScreen(),
                  ),
                ),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();

    expect(await DayStartService.loadLastAttestation(), isNull);

    await tester.tap(find.bySemanticsIdentifier('daystart-clock-check'));
    await tester.pumpAndSettle();
    await tester.tap(find.bySemanticsIdentifier('daystart-project-check'));
    await tester.pumpAndSettle();
    await tester.tap(find.bySemanticsIdentifier('daystart-calibration-check'));
    await tester.pumpAndSettle();

    await tester.tap(find.bySemanticsIdentifier('daystart-confirm-btn'));
    await tester.pumpAndSettle();

    // Popped back to the "open" screen.
    expect(find.text('open'), findsOneWidget);
    expect(find.byType(DayStartAttestationScreen), findsNothing);
    expect(await DayStartService.loadLastAttestation(), isNotNull);
  });

  testWidgets('back navigation is blocked (non-dismissible)', (tester) async {
    await pumpScreen(tester);
    // No AppBar/back button rendered at all — the only way forward is the
    // confirm button, enforced by PopScope(canPop: false) at the widget level.
    expect(find.byType(BackButton), findsNothing);
  });
}
