// ignore_for_file: avoid_print, unnecessary_string_escapes
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:uuid/uuid.dart';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/data/local/database_provider.dart';
import 'package:dmrv_app/providers/dashboard_stats_provider.dart';
import 'package:dmrv_app/providers/sync_providers.dart';

void main() {
  // ---------------------------------------------------------------------------
  // Task 2.3 — Dashboard Statistics Provider SQL-level Aggregation Test
  // ---------------------------------------------------------------------------
  //
  // Verifies that dashboardStatsProvider:
  //   1. totalBatches counts SystemMetadata rows
  //   2. completedBatches counts EndUseApplication rows
  //   3. pendingSync matches existing pendingOutboxCountProvider
  //   4. totalYieldKg sums wetYieldWeightKg from YieldMetrics
  //
  // All queries use selectOnly + SQL aggregation - no rows loaded into memory.
  // ---------------------------------------------------------------------------

  late AppDatabase db;
  late ProviderContainer container;
  const uuid = Uuid();

  setUp(() {
    db = AppDatabase.forTesting(NativeDatabase.memory());
    container = ProviderContainer(
      overrides: [appDatabaseProvider.overrideWith((ref) => Future.value(db))],
    );
  });

  tearDown(() async {
    container.dispose();
    await db.close();
  });

  test('totalBatches counts SystemMetadata rows', () async {
    // Arrange: Insert 3 metadata rows
    for (int i = 0; i < 3; i++) {
      await db
          .into(db.systemMetadata)
          .insert(
            SystemMetadataCompanion.insert(
              batchUuid: uuid.v4(),
              artisanId: 'ARTISAN-$i',
              deviceHardwareMac: 'AA:BB:CC:DD:EE:0$i',
              appBuildVersion: '1.0.0+1',
              createdAt: DateTime.now().toUtc().toIso8601String(),
            ),
          );
    }

    // Act
    final stream = container.read(dashboardStatsProvider.future);
    final stats = await stream;

    // Assert
    expect(stats.totalBatches, 3);
    print('✓ totalBatches correctly counts SystemMetadata rows');
  });

  test('completedBatches counts batches with EndUseApplication', () async {
    // Arrange: Create 3 batches, but only 2 with end-use records
    final batch1 = uuid.v4();
    final batch2 = uuid.v4();
    final batch3 = uuid.v4();

    // All 3 have sourcing
    for (final batchUuid in [batch1, batch2, batch3]) {
      await db
          .into(db.biomassSourcing)
          .insert(
            BiomassSourcingCompanion.insert(
              sourcingUuid: uuid.v4(),
              batchUuid: batchUuid,
              feedstockSpecies: 'Lantana_camara',
              harvestTimestamp: DateTime.now().toUtc().toIso8601String(),
              moisturePercent: 12.5,
              moistureCompliant: true,
            ),
          );
    }

    // Only batch1 and batch2 have end-use
    for (final batchUuid in [batch1, batch2]) {
      await db
          .into(db.endUseApplication)
          .insert(
            EndUseApplicationCompanion.insert(
              applicationUuid: uuid.v4(),
              batchUuid: batchUuid,
              applicationMethodology: 'broadcast',
              applicationRate: 2.5,
              transportDistanceKm: 5.0,
            ),
          );
    }

    // Act
    final stream = container.read(dashboardStatsProvider.future);
    final stats = await stream;

    // Assert: completedBatches should be 2
    expect(stats.completedBatches, 2);
    print('✓ completedBatches correctly counts EndUseApplication rows');
  });

  test('pendingSync matches SyncOutbox PENDING count', () async {
    // Arrange: Insert 3 outbox entries - 2 PENDING, 1 SYNCED
    final batch1 = uuid.v4();

    // PENDING entry 1
    await db
        .into(db.syncOutbox)
        .insert(
          SyncOutboxCompanion.insert(
            operationId: uuid.v4(),
            batchUuid: batch1,
            targetTable: 'system_metadata',
            operationType: 'INSERT',
            payloadJson: '{\"test\": 1}',
            createdAt: DateTime.now().toUtc().toIso8601String(),
            status: const Value('PENDING'),
          ),
        );

    // PENDING entry 2
    await db
        .into(db.syncOutbox)
        .insert(
          SyncOutboxCompanion.insert(
            operationId: uuid.v4(),
            batchUuid: batch1,
            targetTable: 'biomass_sourcing',
            operationType: 'INSERT',
            payloadJson: '{\"test\": 2}',
            createdAt: DateTime.now().toUtc().toIso8601String(),
            status: const Value('PENDING'),
          ),
        );

    // SYNCED entry (should not be counted)
    await db
        .into(db.syncOutbox)
        .insert(
          SyncOutboxCompanion.insert(
            operationId: uuid.v4(),
            batchUuid: batch1,
            targetTable: 'yield_metrics',
            operationType: 'INSERT',
            payloadJson: '{\"test\": 3}',
            createdAt: DateTime.now().toUtc().toIso8601String(),
            status: const Value('SYNCED'),
          ),
        );

    // Act: Get stats from both providers
    final statsStream = container.read(dashboardStatsProvider.future);
    final stats = await statsStream;

    final pendingCountStream = container.read(
      pendingOutboxCountProvider.future,
    );
    final pendingCount = await pendingCountStream;

    // Assert: Both should return 2 (only PENDING entries)
    expect(stats.pendingSync, 2);
    expect(pendingCount, 2);
    expect(
      stats.pendingSync,
      pendingCount,
      reason:
          'dashboardStatsProvider.pendingSync must match pendingOutboxCountProvider',
    );

    print('✓ pendingSync matches existing pendingOutboxCountProvider');
  });

  test('totalYieldKg sums wetYieldWeightKg', () async {
    // Arrange: Insert yield metrics rows with different weights
    final batch1 = uuid.v4();
    final batch2 = uuid.v4();
    final batch3 = uuid.v4();

    final weights = [10.0, 20.0, 30.0];
    final batches = [batch1, batch2, batch3];

    for (int i = 0; i < 3; i++) {
      await db
          .into(db.yieldMetrics)
          .insert(
            YieldMetricsCompanion.insert(
              yieldUuid: uuid.v4(),
              batchUuid: batches[i],
              quenchMethodology: 'water',
              grossVolume: 100.0,
              wetYieldWeightKg: weights[i],
            ),
          );
    }

    // Act
    final stream = container.read(dashboardStatsProvider.future);
    final stats = await stream;

    // Assert: Sum should be 10 + 20 + 30 = 60.0
    expect(stats.totalYieldKg, 60.0);
    print('✓ totalYieldKg correctly sums wetYieldWeightKg');
  });

  test('reactive updates when database changes', () async {
    // Listen continuously instead of read(.future), which caches the first emission.
    final emissions = <DashboardStats>[];
    final sub = container.listen<AsyncValue<DashboardStats>>(
      dashboardStatsProvider,
      (_, next) => next.whenData(emissions.add),
      fireImmediately: true,
    );
    // Allow initial emission to land.
    await Future.delayed(const Duration(milliseconds: 100));
    expect(emissions.isNotEmpty, true);
    expect(emissions.last.totalYieldKg, 0.0);

    final batchUuid = uuid.v4();
    await db
        .into(db.yieldMetrics)
        .insert(
          YieldMetricsCompanion.insert(
            yieldUuid: uuid.v4(),
            batchUuid: batchUuid,
            quenchMethodology: 'water',
            grossVolume: 100.0,
            wetYieldWeightKg: 25.5,
          ),
        );
    // Allow drift's watch stream to re-emit.
    await Future.delayed(const Duration(milliseconds: 100));
    expect(emissions.last.totalYieldKg, 25.5);

    sub.close();
    print('✓ Provider reactively updates when database changes');
  });
}
