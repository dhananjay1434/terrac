import 'dart:io';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/data/local/database_provider.dart';
import 'package:dmrv_app/ui/screens/kiln_select_screen.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// P1-S3 — mandatory kiln selection before pyrolysis. A new local Kilns table
/// (schema v25) backs the pick-list; the burn cannot start until a kiln is
/// chosen; the selected kiln's id/type/capacity replace the old 200 L /
/// WATER_QUENCH hardcodes in telemetry and yield.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('schema v25 Kilns table', () {
    test('exists and round-trips a kiln row', () async {
      FlutterSecureStorage.setMockInitialValues({});
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      expect(db.schemaVersion, greaterThanOrEqualTo(25));

      await db.into(db.kilns).insertOnConflictUpdate(
        Kiln(
          kilnId: 'KILN-42',
          kilnType: 'open',
          capacityLitres: 200,
          label: 'North yard',
          addedAt: '2026-07-10T00:00:00Z',
        ),
      );
      final row = await (db.select(
        db.kilns,
      )..where((t) => t.kilnId.equals('KILN-42'))).getSingle();
      expect(row.kilnType, 'open');
      expect(row.capacityLitres, 200);
      await db.close();
    });
  });

  group('KilnSelectScreen', () {
    // Override the kiln list with a fixed stream so the test doesn't depend on a
    // live Drift watch (which keeps a timer alive and never lets pumpAndSettle
    // drain). Selection itself is a plain StateProvider — no DB involved.
    Future<void> pump(WidgetTester tester, {required List<Kiln> kilns}) async {
      tester.view.physicalSize = const Size(1200, 2600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            kilnListProvider.overrideWith((ref) => Stream.value(kilns)),
          ],
          child: const MaterialApp(home: KilnSelectScreen()),
        ),
      );
      await tester.pumpAndSettle();
    }

    final kiln42 = Kiln(
      kilnId: 'KILN-42',
      kilnType: 'open',
      capacityLitres: 200,
      label: null,
      addedAt: '2026-07-10T00:00:00Z',
    );

    testWidgets('START BURN is locked until a kiln is selected', (tester) async {
      await pump(tester, kilns: [kiln42]);
      expect(find.text('LOCKED // SELECT A KILN'), findsOneWidget);
      expect(find.text('START BURN'), findsNothing);

      await tester.tap(find.text('KILN-42'));
      await tester.pumpAndSettle();

      expect(find.text('START BURN'), findsOneWidget);
      expect(find.text('LOCKED // SELECT A KILN'), findsNothing);
    });

    testWidgets('with no kilns, the empty hint + ADD KILN are shown', (
      tester,
    ) async {
      await pump(tester, kilns: const []);
      expect(find.text('ADD KILN'), findsOneWidget);
      expect(find.textContaining('No kilns yet'), findsOneWidget);
      expect(find.text('LOCKED // SELECT A KILN'), findsOneWidget);
    });

    // Bug found via a real device burn: after a fresh install, a burn using a
    // just-selected kiln signed ZERO v2 channels even though the backend had
    // that kiln correctly declared 'full'. Root cause: tapping a kiln row
    // fires `_syncKilnProfile` (fetch+cache the real profile), but it only
    // wrote the LOCAL DB row — `selectedKilnProvider` kept holding the STALE
    // in-memory `Kiln` (sensorProfile: null) that the burn screen actually
    // reads. Fixed by also updating the provider's Kiln when the sync lands.
    testWidgets(
      'selecting a kiln updates selectedKilnProvider with the synced sensorProfile',
      (tester) async {
        SharedPreferences.setMockInitialValues({
          'dmrv.kiln_profile.v1.KILN-42': 'full',
        });
        final db = AppDatabase.forTesting(NativeDatabase.memory());
        await db.into(db.kilns).insertOnConflictUpdate(kiln42);
        addTearDown(db.close);

        final container = ProviderContainer(
          overrides: [
            appDatabaseProvider.overrideWith((ref) => Future.value(db)),
            kilnListProvider.overrideWith((ref) => Stream.value([kiln42])),
          ],
        );
        addTearDown(container.dispose);

        tester.view.physicalSize = const Size(1200, 2600);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        await tester.pumpWidget(
          UncontrolledProviderScope(
            container: container,
            child: const MaterialApp(home: KilnSelectScreen()),
          ),
        );
        await tester.pumpAndSettle();

        // Before selection: no profile known yet.
        expect(container.read(selectedKilnProvider), isNull);

        await tester.tap(find.text('KILN-42'));
        await tester.pumpAndSettle();

        // After the fire-and-forget sync lands, the IN-MEMORY selection must
        // carry the fetched profile — not just the DB row.
        final selected = container.read(selectedKilnProvider);
        expect(selected, isNotNull);
        expect(selected!.sensorProfile, 'full');
      },
    );
  });

  group('hardcodes removed at the call sites', () {
    test('pyrolysis_screen no longer passes kilnGrossCapacity: 200.0', () {
      final src = File(
        'lib/ui/screens/pyrolysis_screen.dart',
      ).readAsStringSync();
      expect(src.contains('kilnGrossCapacity: 200.0'), isFalse);
      expect(src.contains('kilnId: kiln.kilnId'), isTrue);
      expect(src.contains('kilnType: kiln.kilnType'), isTrue);
    });

    test('yield_scale_screen no longer hardcodes WATER_QUENCH / 200.0', () {
      final src = File(
        'lib/ui/screens/yield_scale_screen.dart',
      ).readAsStringSync();
      expect(src.contains("quenchMethodology: 'WATER_QUENCH'"), isFalse);
      expect(src.contains('grossVolume: 200.0'), isFalse);
      expect(src.contains('quenchMethodology: _quench'), isTrue);
    });
  });
}
