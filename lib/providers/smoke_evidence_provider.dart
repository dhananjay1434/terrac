import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:drift/drift.dart';
import '../data/local/app_database.dart';
import '../data/local/database_provider.dart';
import 'batch_session_notifier.dart';

final smokeEvidenceProvider = StreamProvider<List<MediaCapture>>((ref) async* {
  final batchUuid = ref.watch(batchSessionProvider);
  if (batchUuid == null) {
    yield [];
    return;
  }
  final db = await ref.watch(appDatabaseProvider.future);

  yield* (db.select(db.mediaCaptures)
        ..where(
          (t) =>
              t.batchUuid.equals(batchUuid) &
              t.captureType.isIn([
                'smoke_0',
                'smoke_50',
                'smoke_90',
                'smoke_100',
              ]),
        )
        ..orderBy([(t) => OrderingTerm(expression: t.createdAt)]))
      .watch();
});

/// P1-S4: the SET of evidence captureType strings recorded for the active batch
/// (smoke proofs + the flame-stage photos). Backs the kiln-type-aware END BURN
/// gate and the completion summary.
final capturedStagesProvider = StreamProvider<Set<String>>((ref) async* {
  final batchUuid = ref.watch(batchSessionProvider);
  if (batchUuid == null) {
    yield <String>{};
    return;
  }
  final db = await ref.watch(appDatabaseProvider.future);
  yield* (db.select(db.mediaCaptures)
        ..where((t) => t.batchUuid.equals(batchUuid)))
      .watch()
      .map((rows) => rows.map((r) => r.captureType).toSet());
});
