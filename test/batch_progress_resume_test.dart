import 'package:drift/native.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:uuid/uuid.dart';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/providers/dashboard_provider.dart';

/// P1-C3a — resuming a killed batch must restore the dashboard card statuses
/// (which stage the operator was on), not drop back to a fresh-start layout.
void main() {
  const uuid = Uuid();
  late AppDatabase db;

  setUp(() => db = AppDatabase.forTesting(NativeDatabase.memory()));
  tearDown(() async => db.close());

  test('loadBatchProgress detects present vs absent stages', () async {
    final notifier = DashboardNotifier();
    final bu = uuid.v4();
    await db
        .into(db.biomassSourcing)
        .insert(
          BiomassSourcingCompanion.insert(
            sourcingUuid: uuid.v4(),
            batchUuid: bu,
            feedstockSpecies: 'Lantana_camara',
            harvestTimestamp: DateTime.now().toUtc().toIso8601String(),
            moisturePercent: 12.0,
            moistureCompliant: true,
          ),
        );

    final p = await notifier.loadBatchProgress(db, bu);
    expect(p.hasSourcing, isTrue);
    expect(p.hasTelemetry, isFalse);
    expect(p.hasYield, isFalse);
    expect(p.hasEndUse, isFalse);

    final none = await notifier.loadBatchProgress(db, uuid.v4());
    expect(none.hasSourcing, isFalse);
  });

  group('restoreProgress maps stages to card statuses', () {
    late ProviderContainer c;
    setUp(() => c = ProviderContainer());
    tearDown(() => c.dispose());

    test('sourcing done → biomass verified, ble pending, yield locked', () {
      c
          .read(dashboardProvider.notifier)
          .restoreProgress(const BatchProgress(hasSourcing: true));
      final s = c.read(dashboardProvider);
      expect(s.biomassStatus, CardStatus.verified);
      expect(s.bleStatus, CardStatus.pending);
      expect(s.yieldStatus, CardStatus.locked);
    });

    test('sourcing + telemetry done → ble verified, yield pending', () {
      c.read(dashboardProvider.notifier).restoreProgress(
        const BatchProgress(hasSourcing: true, hasTelemetry: true),
      );
      final s = c.read(dashboardProvider);
      expect(s.biomassStatus, CardStatus.verified);
      expect(s.bleStatus, CardStatus.verified);
      expect(s.yieldStatus, CardStatus.pending);
    });

    test('nothing captured → biomass pending, others locked', () {
      c
          .read(dashboardProvider.notifier)
          .restoreProgress(const BatchProgress());
      final s = c.read(dashboardProvider);
      expect(s.biomassStatus, CardStatus.pending);
      expect(s.bleStatus, CardStatus.locked);
      expect(s.yieldStatus, CardStatus.locked);
    });
  });
}
