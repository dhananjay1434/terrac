import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/local/app_database.dart';
import '../ui/widgets/premium_action_card.dart';

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
}

final dashboardProvider = NotifierProvider<DashboardNotifier, DashboardState>(
  () => DashboardNotifier(),
);
