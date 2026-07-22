import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:dmrv_app/ui/screens/dispatch/dispatch_screen.dart';

/// Deferred R2 — dispatch wizard restart-resilience, screen level. The
/// server-status fetch always fails in this offline widget-test environment
/// (no network), which — per `resolveResumePhase`'s own documented fallback
/// — means these tests exercise the "server unreachable, trust persisted"
/// path specifically. The pure reconciliation logic itself (server-wins,
/// etc.) is covered without any widget/network dependency in
/// dispatch_wizard_resume_test.dart.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  Future<void> pumpScreen(WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(home: DispatchScreen()),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('a persisted in-flight dispatch is resumed with a banner', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({
      'dmrv.dispatch_wizard.v1': jsonEncode({
        'dispatch_uuid': 'dispatch-uuid-resume-1',
        'phase': 'in_transit',
      }),
    });

    await pumpScreen(tester);

    expect(find.bySemanticsIdentifier('dispatch-resume-banner'), findsOneWidget);
    expect(find.text('In-Transit'), findsOneWidget);
  });

  testWidgets('a genuinely fresh screen shows no resume banner', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});

    await pumpScreen(tester);

    expect(find.bySemanticsIdentifier('dispatch-resume-banner'), findsNothing);
    expect(find.text('New Dispatch'), findsOneWidget);
  });

  testWidgets('the resume banner is dismissible', (tester) async {
    SharedPreferences.setMockInitialValues({
      'dmrv.dispatch_wizard.v1': jsonEncode({
        'dispatch_uuid': 'dispatch-uuid-resume-2',
        'phase': 'draft',
      }),
    });

    await pumpScreen(tester);
    expect(find.bySemanticsIdentifier('dispatch-resume-banner'), findsOneWidget);

    await tester.tap(find.byTooltip('Dismiss'));
    await tester.pumpAndSettle();

    expect(find.bySemanticsIdentifier('dispatch-resume-banner'), findsNothing);
  });

  testWidgets('corrupt persisted state degrades to a fresh screen, no crash', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({
      'dmrv.dispatch_wizard.v1': 'not valid json at all',
    });

    await pumpScreen(tester);

    expect(find.bySemanticsIdentifier('dispatch-resume-banner'), findsNothing);
    expect(find.text('New Dispatch'), findsOneWidget);
  });
}
