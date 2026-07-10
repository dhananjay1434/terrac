import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/local/app_database.dart';

/// Lifecycle state of a dashboard step card. (Relocated here from the deleted
/// premium_action_card widget — this is the dashboard's domain enum.)
enum CardStatus {
  locked, // inactive, waiting for a prior step
  pending, // active, awaiting capture / BLE response
  verified, // evidence confirmed for this step
}

/// P1-C3: which capture stages already have persisted rows for a batch. Used to
/// restore the dashboard card statuses when resuming a batch after an app kill,
/// so a resumed batch shows the correct step instead of a fresh-start layout.
@immutable
class BatchProgress {
  final bool hasSourcing;
  final bool hasMoisture;
  final bool hasTelemetry;
  final bool hasYield;
  final bool hasEndUse;
  const BatchProgress({
    this.hasSourcing = false,
    this.hasMoisture = false,
    this.hasTelemetry = false,
    this.hasYield = false,
    this.hasEndUse = false,
  });
}

@immutable
class DashboardState {
  final CardStatus biomassStatus;
  final CardStatus bleStatus;
  final CardStatus yieldStatus;
  final String lastHash;
  final bool isBleConnecting;

  const DashboardState({
    this.biomassStatus = CardStatus.pending,
    this.bleStatus = CardStatus.locked,
    this.yieldStatus = CardStatus.locked,
    this.lastHash = 'N/A',
    this.isBleConnecting = false,
  });

  DashboardState copyWith({
    CardStatus? biomassStatus,
    CardStatus? bleStatus,
    CardStatus? yieldStatus,
    String? lastHash,
    bool? isBleConnecting,
  }) {
    return DashboardState(
      biomassStatus: biomassStatus ?? this.biomassStatus,
      bleStatus: bleStatus ?? this.bleStatus,
      yieldStatus: yieldStatus ?? this.yieldStatus,
      lastHash: lastHash ?? this.lastHash,
      isBleConnecting: isBleConnecting ?? this.isBleConnecting,
    );
  }
}

class DashboardNotifier extends Notifier<DashboardState> {
  @override
  DashboardState build() => const DashboardState();

  void resetForNewBatch() {
    state = const DashboardState();
  }

  void markBiomassVerified() {
    state = state.copyWith(
      biomassStatus: CardStatus.verified,
      bleStatus: state.bleStatus == CardStatus.locked
          ? CardStatus.pending
          : state.bleStatus,
    );
  }

  void markBleVerified() {
    state = state.copyWith(
      bleStatus: CardStatus.verified,
      yieldStatus: state.yieldStatus == CardStatus.locked
          ? CardStatus.pending
          : state.yieldStatus,
    );
  }

  void markYieldVerified() {
    state = state.copyWith(yieldStatus: CardStatus.verified);
  }

  Future<void> startBleHandshake() async {
    // No-op shim retained for backwards compatibility with the dashboard tap
    // handler. Real BLE handshake is owned by PyrolysisScreen.
    state = state.copyWith(isBleConnecting: false);
  }

  /// Queries the local database for batches that have a BiomassSourcing
  /// record but NO EndUseApplication record (meaning workflow is incomplete).
  /// Returns the most recent incomplete batchUuid, or null if none found.
  Future<String?> findIncompleteBatch(AppDatabase db) async {
    final result = await db
        .customSelect(
          'SELECT bs.batch_uuid FROM biomass_sourcing bs '
          'WHERE bs.batch_uuid NOT IN '
          '(SELECT eu.batch_uuid FROM end_use_application eu) '
          'ORDER BY bs.harvest_timestamp DESC '
          'LIMIT 1',
        )
        .getSingleOrNull();
    return result?.read<String>('batch_uuid');
  }

  /// P1-C3: which capture stages already have rows for [batchUuid].
  Future<BatchProgress> loadBatchProgress(
    AppDatabase db,
    String batchUuid,
  ) async {
    Future<bool> has(Future<List<Object?>> rows) async =>
        (await rows).isNotEmpty;
    return BatchProgress(
      hasSourcing: await has(
        (db.select(db.biomassSourcing)
              ..where((t) => t.batchUuid.equals(batchUuid))
              ..limit(1))
            .get(),
      ),
      hasMoisture: await has(
        (db.select(db.moistureReadings)
              ..where((t) => t.batchUuid.equals(batchUuid))
              ..limit(1))
            .get(),
      ),
      hasTelemetry: await has(
        (db.select(db.pyrolysisTelemetry)
              ..where((t) => t.batchUuid.equals(batchUuid))
              ..limit(1))
            .get(),
      ),
      hasYield: await has(
        (db.select(db.yieldMetrics)
              ..where((t) => t.batchUuid.equals(batchUuid))
              ..limit(1))
            .get(),
      ),
      hasEndUse: await has(
        (db.select(db.endUseApplication)
              ..where((t) => t.batchUuid.equals(batchUuid))
              ..limit(1))
            .get(),
      ),
    );
  }

  /// P1-C3: restore the dashboard card statuses from [p] on resume so a resumed
  /// batch shows the correct step. Verified stages show verified; the first
  /// undone stage is pending; later stages stay locked.
  void restoreProgress(BatchProgress p) {
    state = state.copyWith(
      biomassStatus: p.hasSourcing ? CardStatus.verified : CardStatus.pending,
      bleStatus: p.hasTelemetry
          ? CardStatus.verified
          : (p.hasSourcing ? CardStatus.pending : CardStatus.locked),
      yieldStatus: p.hasYield
          ? CardStatus.verified
          : (p.hasTelemetry ? CardStatus.pending : CardStatus.locked),
    );
  }
}

final dashboardProvider = NotifierProvider<DashboardNotifier, DashboardState>(
  () => DashboardNotifier(),
);
