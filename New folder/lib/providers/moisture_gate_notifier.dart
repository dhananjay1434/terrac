import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dmrv_app/data/local/database_provider.dart';
import 'package:dmrv_app/providers/batch_session_notifier.dart';

/// =============================================================================
/// MoistureGateNotifier (Event-Sourced version)
/// =============================================================================
/// Enforces the registry compliance rule:
///     moisture% <= 15.0  →  workflow unlocked, "Initiate Pyrolysis" rendered
///     moisture% >  15.0  →  workflow locked, severe red error, button removed
///
/// Photo evidence state is entirely derived from Drift (MediaCaptures table).
/// We do NOT hold sha256 or photo_path in memory here to avoid RAM bloat/loss.
/// =============================================================================

const double kMoistureComplianceCeiling = 15.0;

enum MoistureGateStatus { pending, compliant, nonCompliant }

class MoistureGateState {
  const MoistureGateState({
    this.rawInput = '',
    this.moisturePercent,
    this.status = MoistureGateStatus.pending,
  });

  final String rawInput;
  final double? moisturePercent;
  final MoistureGateStatus status;

  bool get isCompliant => status == MoistureGateStatus.compliant;
  bool get isLocked =>
      status == MoistureGateStatus.nonCompliant ||
      status == MoistureGateStatus.pending;

  String? get errorMessage => status == MoistureGateStatus.nonCompliant
      ? 'Moisture > 15%. Dry further.'
      : null;

  MoistureGateState copyWith({
    String? rawInput,
    double? moisturePercent,
    MoistureGateStatus? status,
    bool clearMoisture = false,
  }) {
    return MoistureGateState(
      rawInput: rawInput ?? this.rawInput,
      moisturePercent: clearMoisture
          ? null
          : (moisturePercent ?? this.moisturePercent),
      status: status ?? this.status,
    );
  }
}

class MoistureGateNotifier extends Notifier<MoistureGateState> {
  @override
  MoistureGateState build() => const MoistureGateState();

  void updateReading(String raw) {
    final trimmed = raw.trim();
    if (trimmed.isEmpty) {
      state = const MoistureGateState();
      return;
    }
    final parsed = double.tryParse(trimmed);
    if (parsed == null || parsed.isNaN || parsed < 0) {
      state = MoistureGateState(rawInput: trimmed);
      return;
    }
    final newStatus = parsed <= kMoistureComplianceCeiling
        ? MoistureGateStatus.compliant
        : MoistureGateStatus.nonCompliant;
    state = state.copyWith(
      rawInput: trimmed,
      moisturePercent: parsed,
      status: newStatus,
    );
  }

  void reset() {
    state = const MoistureGateState();
  }
}

final moistureGateProvider =
    NotifierProvider<MoistureGateNotifier, MoistureGateState>(
      MoistureGateNotifier.new,
    );

/// A reactive StreamProvider that watches the database for the moisture photo.
/// Yields true if a BiomassSourcing row exists with a photoPath for the current batch.
final moistureEvidenceProvider = StreamProvider<bool>((ref) {
  final batchUuid = ref.watch(requiredBatchUuidProvider);
  final db = ref.watch(appDatabaseProvider).value;

  if (db == null) {
    return Stream.value(false);
  }

  final query = db.select(db.biomassSourcing)
    ..where((t) => t.batchUuid.equals(batchUuid))
    ..where((t) => t.photoPath.isNotNull());
  return query.watch().map((rows) => rows.isNotEmpty);
});
