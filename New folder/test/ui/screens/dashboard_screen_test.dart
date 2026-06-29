import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/data/local/database_provider.dart';
import 'package:dmrv_app/providers/dashboard_provider.dart';
import 'package:dmrv_app/providers/sync_providers.dart';
import 'package:dmrv_app/services/sync_queue_manager.dart';
import 'package:dmrv_app/ui/design/farmer_theme.dart';
import 'package:dmrv_app/ui/screens/dashboard_screen.dart';
import 'package:dmrv_app/ui/widgets/premium_action_card.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/l10n/app_localizations.dart';

void main() {
  group('DashboardScreen Phase 2 Tests', () {
    late AppDatabase mockDb;

    setUp(() async {
      // Create in-memory database for testing (same as drift_schema_test.dart)
      mockDb = AppDatabase.forTesting(NativeDatabase.memory());
    });

    tearDown(() async {
      await mockDb.close();
    });

    Widget buildTestWidget({
      required DashboardState dashboardState,
      required int pendingOutboxCount,
    }) {
      return ProviderScope(
        overrides: [
          appDatabaseProvider.overrideWith((ref) async => mockDb),
          dashboardProvider.overrideWith(
            () => TestDashboardNotifier(dashboardState),
          ),
          pendingOutboxCountProvider.overrideWith(
            (ref) => Stream.value(pendingOutboxCount),
          ),
          syncQueueManagerProvider.overrideWith((ref) {
            // Return a mock SyncQueueManager that does nothing
            final mockManager = SyncQueueManager(ref, startPeriodicTimer: false);
            ref.onDispose(mockManager.dispose);
            return mockManager;
          }),
        ],
        child: const MaterialApp(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: Locale('en'),
          home: DashboardScreen(),
        ),
      );
    }

    testWidgets(
      'Test 1: pendingOutboxCount = 0 → banner shows "ALL DATA SECURE" in fieldGreen',
      (tester) async {
        await tester.pumpWidget(
          buildTestWidget(
            dashboardState: const DashboardState(
              biomassStatus: CardStatus.verified,
              bleStatus: CardStatus.pending,
              yieldStatus: CardStatus.locked,
            ),
            pendingOutboxCount: 0,
          ),
        );

        // Wait for async providers to load (not pumpAndSettle due to infinite pulse animation)
        await tester.pump(const Duration(milliseconds: 500));

        // Verify sync banner shows "ALL DATA SECURE"
        expect(find.text('ALL DATA SECURE'), findsOneWidget);

        // Verify the checkmark emoji is present
        expect(find.text('✅'), findsOneWidget);

        // Verify the color is fieldGreen (by checking the text widget)
        final textWidget = tester.widget<Text>(find.text('ALL DATA SECURE'));
        expect(textWidget.style?.color, FarmerTheme.fieldGreen);

        // Clean up infinite animation
        await tester.pumpWidget(const SizedBox());
        await tester.pumpAndSettle();
      },
    );

    testWidgets(
      'Test 2: pendingOutboxCount = 3 → banner shows "3 RECORDS PENDING" in neonYellow',
      (tester) async {
        await tester.pumpWidget(
          buildTestWidget(
            dashboardState: const DashboardState(
              biomassStatus: CardStatus.verified,
              bleStatus: CardStatus.pending,
              yieldStatus: CardStatus.locked,
            ),
            pendingOutboxCount: 3,
          ),
        );

        await tester.pump(const Duration(milliseconds: 500));

        // Verify sync banner shows "3 RECORDS PENDING"
        expect(find.text('3 RECORDS PENDING'), findsOneWidget);

        // Verify the cloud emoji is present
        expect(find.text('☁'), findsOneWidget);

        // Verify the color is neonYellow
        final textWidget = tester.widget<Text>(find.text('3 RECORDS PENDING'));
        expect(textWidget.style?.color, FarmerTheme.neonYellow);

        // Clean up infinite animation
        await tester.pumpWidget(const SizedBox());
        await tester.pumpAndSettle();
      },
    );

    testWidgets(
      'Test 3: bleStatus = CardStatus.pending → BLE step renders as RuggedButton (primary)',
      (tester) async {
        await tester.pumpWidget(
          buildTestWidget(
            dashboardState: const DashboardState(
              biomassStatus: CardStatus.verified,
              bleStatus: CardStatus.pending,
              yieldStatus: CardStatus.locked,
            ),
            pendingOutboxCount: 0,
          ),
        );

        await tester.pump(const Duration(milliseconds: 500));

        // Verify BLE step shows as pending with RuggedButton
        expect(find.text('Connect BLE Sensor'), findsOneWidget);

        // Verify the "TAP TO START" button exists (RuggedButton)
        expect(find.text('TAP TO START'), findsAtLeastNWidgets(1));

        // Verify the button has neonYellow background (RuggedButton primary variant)
        final buttonFinder = find
            .ancestor(
              of: find.text('TAP TO START'),
              matching: find.byType(Material),
            )
            .first;
        final material = tester.widget<Material>(buttonFinder);
        expect(material.color, FarmerTheme.neonYellow);

        // Clean up infinite animation
        await tester.pumpWidget(const SizedBox());
        await tester.pumpAndSettle();
      },
    );

    testWidgets(
      'Test 4: yieldStatus = CardStatus.locked → yield row is greyed / not a button',
      (tester) async {
        await tester.pumpWidget(
          buildTestWidget(
            dashboardState: const DashboardState(
              biomassStatus: CardStatus.verified,
              bleStatus: CardStatus.verified,
              yieldStatus: CardStatus.locked,
            ),
            pendingOutboxCount: 0,
          ),
        );

        await tester.pump(const Duration(milliseconds: 500));

        // Verify yield step shows as locked
        expect(find.text('Record Yield Weight'), findsOneWidget);

        // Verify lock icon is present
        expect(find.byIcon(Icons.lock), findsOneWidget);

        // Verify the locked step is wrapped in Opacity (greyed out)
        final opacityFinder = find.ancestor(
          of: find.text('Record Yield Weight'),
          matching: find.byType(Opacity),
        );
        expect(opacityFinder, findsOneWidget);
        final opacity = tester.widget<Opacity>(opacityFinder);
        expect(opacity.opacity, 0.4);

        // Verify no "TAP TO START" button for locked step
        final yieldButtons = find.descendant(
          of: find
              .ancestor(
                of: find.text('Record Yield Weight'),
                matching: find.byType(Container),
              )
              .first,
          matching: find.text('TAP TO START'),
        );
        expect(yieldButtons, findsNothing);

        // Clean up infinite animation
        await tester.pumpWidget(const SizedBox());
        await tester.pumpAndSettle();
      },
    );

    testWidgets('Test 5: Verify IntegrityFooter is preserved', (tester) async {
      await tester.pumpWidget(
        buildTestWidget(
          dashboardState: const DashboardState(
            biomassStatus: CardStatus.verified,
            bleStatus: CardStatus.pending,
            yieldStatus: CardStatus.locked,
            lastHash: 'abc123def456',
          ),
          pendingOutboxCount: 0,
        ),
      );

      await tester.pump(const Duration(milliseconds: 500));

      // Verify IntegrityFooter is present (check for hash text)
      expect(find.textContaining('abc123def456'), findsOneWidget);

      // Clean up infinite animation
      await tester.pumpWidget(const SizedBox());
      await tester.pumpAndSettle();
    });
  });
}

/// Test notifier that returns a fixed state for testing
class TestDashboardNotifier extends DashboardNotifier {
  TestDashboardNotifier(this._state);

  final DashboardState _state;

  @override
  DashboardState build() => _state;
}
