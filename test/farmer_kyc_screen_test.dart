import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:dmrv_app/l10n/app_localizations.dart';
import 'package:dmrv_app/ui/screens/farmer_kyc_screen.dart';

/// V8 Part 4 (J) — field-UX pack coverage for the farmer onboarding screen:
/// save-to-draft persistence + restore, and the consequence-explicit
/// clear-draft confirm dialog. The pincode/IFSC LIVE network lookups can't be
/// exercised here (no client-injection point from the widget layer) — their
/// pure response-parsing logic is covered separately in
/// pincode_lookup_service_test.dart / ifsc_lookup_service_test.dart.
///
/// Fields have no Flutter `Key` (they carry a `Semantics(identifier: ...)`
/// test id instead, matching this codebase's existing pattern — see
/// enrollment_test.dart), so they're located positionally via
/// `find.byType(TextField).at(index)` in render order: first, last, guardian,
/// mobile, village, pincode, account_holder, account_number, ifsc.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const firstNameField = 0;

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
          home: FarmerKycScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  String textOf(WidgetTester tester, int index) => tester
      .widget<TextField>(find.byType(TextField).at(index))
      .controller!
      .text;

  testWidgets('typed fields are saved as a draft and restored on re-open', (
    tester,
  ) async {
    await pumpScreen(tester);

    await tester.enterText(find.byType(TextField).at(firstNameField), 'Asha');
    await tester.pumpAndSettle();
    // Nudge the listener-driven SharedPreferences write to complete.
    await tester.pump(const Duration(milliseconds: 50));

    // Re-mount the screen (simulates leaving and re-opening it).
    await tester.pumpWidget(const SizedBox());
    await pumpScreen(tester);

    expect(find.text('Draft restored from your last session.'), findsOneWidget);
    expect(textOf(tester, firstNameField), 'Asha');
  });

  testWidgets('no draft banner on a genuinely fresh screen', (tester) async {
    await pumpScreen(tester);
    expect(find.text('Draft restored from your last session.'), findsNothing);
  });

  testWidgets('clear-draft shows a consequence-explicit confirm dialog', (
    tester,
  ) async {
    await pumpScreen(tester);
    await tester.enterText(find.byType(TextField).at(firstNameField), 'Asha');
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('Clear draft'));
    await tester.pumpAndSettle();

    expect(find.text('Clear all entered fields?'), findsOneWidget);
    expect(
      find.textContaining('erases every field on this form'),
      findsOneWidget,
    );

    // Cancel first: fields must survive.
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    expect(textOf(tester, firstNameField), 'Asha');

    // Now actually clear.
    await tester.tap(find.byTooltip('Clear draft'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Clear'));
    await tester.pumpAndSettle();

    expect(textOf(tester, firstNameField), isEmpty);
  });

  testWidgets('pincode and IFSC lookup rows render with their controls', (
    tester,
  ) async {
    await pumpScreen(tester);
    // The ListView only builds elements near the viewport (standard sliver
    // lazy-building) — scroll the pincode/IFSC rows into view before
    // searching for them, same as any long-form scrollable in this codebase.
    await tester.dragUntilVisible(
      find.text('Look up'),
      find.byType(Scrollable).first,
      const Offset(0, -300),
    );
    expect(find.text('Look up'), findsOneWidget);

    await tester.dragUntilVisible(
      find.text('Verify'),
      find.byType(Scrollable).first,
      const Offset(0, -300),
    );
    expect(find.text('Verify'), findsOneWidget);
  });
}
