import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/local/database_provider.dart';

/// Dashboard statistics data class.
/// All values are computed using SQL-level aggregation - no rows are loaded
/// into Dart memory, ensuring constant memory consumption regardless of table size.
class DashboardStats {
  final int totalBatches;
  final int completedBatches;
  final int pendingSync;
  final double totalYieldKg;

  const DashboardStats({
    required this.totalBatches,
    required this.completedBatches,
    required this.pendingSync,
    required this.totalYieldKg,
  });

  @override
  String toString() {
    return 'DashboardStats(totalBatches: $totalBatches, completedBatches: $completedBatches, '
        'pendingSync: $pendingSync, totalYieldKg: $totalYieldKg)';
  }
}

/// StreamProvider that computes dashboard statistics using reactive Drift streams.
///
/// This provider combines four separate SQL-level aggregation queries:
/// - totalBatches: COUNT(*) from SystemMetadata
/// - completedBatches: COUNT(*) from EndUseApplication
/// - pendingSync: COUNT(*) from SyncOutbox WHERE status = 'PENDING'
/// - totalYieldKg: SUM(wetYieldWeightKg) from YieldMetrics
///
/// All queries use `selectOnly` with `watchSingle()` to ensure the provider
/// updates automatically when the database changes, without loading any rows
/// into memory.
final dashboardStatsProvider = StreamProvider<DashboardStats>((ref) async* {
  final db = await ref.watch(appDatabaseProvider.future);

  final query = db.customSelect(
    'SELECT * FROM dashboard_stats_v',
    readsFrom: {
      db.systemMetadata,
      db.endUseApplication,
      db.syncOutbox,
      db.yieldMetrics,
    },
  );

  yield* query.map((row) {
    return DashboardStats(
      totalBatches: row.read<int>('total_batches'),
      completedBatches: row.read<int>('completed_batches'),
      pendingSync: row.read<int>('pending_sync'),
      totalYieldKg: row.read<double>('total_yield_kg'),
    );
  }).watchSingle();
});
