import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/local/app_database.dart';
import '../data/local/database_provider.dart';
import '../data/local/proof_queries.dart';
import '../services/sync_queue_manager.dart';

/// Streams the live count of `SyncOutbox` rows whose status is still `PENDING`.
///
/// The dashboard "trust badge" subscribes to this provider so the artisan
/// always sees, in real time, how many offline events are buffered locally
/// awaiting upload.
final pendingOutboxCountProvider = StreamProvider<int>((ref) async* {
  final db = await ref.watch(appDatabaseProvider.future);
  final outbox = db.syncOutbox;

  final query = db.selectOnly(outbox)
    ..addColumns([outbox.operationId.count()])
    ..where(outbox.status.equals('PENDING'));

  yield* query
      .map((row) => row.read(outbox.operationId.count()) ?? 0)
      .watchSingle();
}, name: 'pendingOutboxCountProvider');

/// Streams the most recent N PENDING outbox events (for the dashboard's
/// "last activity" strip).
final recentPendingEventsProvider = StreamProvider<List<SyncOutboxData>>((
  ref,
) async* {
  final db = await ref.watch(appDatabaseProvider.future);
  final query = db.select(db.syncOutbox)
    ..where((t) => t.status.equals('PENDING'))
    ..orderBy([(t) => OrderingTerm.desc(t.createdAt)])
    ..limit(5);
  yield* query.watch();
}, name: 'recentPendingEventsProvider');

/// Streams the outbox rows an operator needs to act on in the Sync Health
/// screen — anything stuck (`FAILED_PERMANENTLY`) or actively retrying. Thin
/// wrapper over [SyncQueueManager.watchProblemRows] so the screen (and its
/// widget tests) subscribe through Riverpod rather than holding the manager.
final problemOutboxRowsProvider = StreamProvider<List<SyncOutboxData>>((
  ref,
) async* {
  yield* ref.watch(syncQueueManagerProvider).watchProblemRows();
}, name: 'problemOutboxRowsProvider');

/// Streams the live count of `SyncOutbox` rows that have fully synced, for the
/// Sync Health summary chips.
final syncedOutboxCountProvider = StreamProvider<int>((ref) async* {
  final db = await ref.watch(appDatabaseProvider.future);
  final outbox = db.syncOutbox;

  final query = db.selectOnly(outbox)
    ..addColumns([outbox.operationId.count()])
    ..where(outbox.status.equals('SYNCED'));

  yield* query
      .map((row) => row.read(outbox.operationId.count()) ?? 0)
      .watchSingle();
}, name: 'syncedOutboxCountProvider');

/// Streams all batch lifecycles as premium cryptographic receipts.
final cryptographicReceiptsProvider =
    StreamProvider<List<CryptographicReceipt>>((ref) async* {
      final db = await ref.watch(appDatabaseProvider.future);
      yield* db.watchCryptographicReceipts();
    });

final batchMediaProvider = StreamProvider.family<List<MediaCapture>, String>((
  ref,
  batchUuid,
) async* {
  final db = await ref.watch(appDatabaseProvider.future);
  yield* (db.select(
    db.mediaCaptures,
  )..where((t) => t.batchUuid.equals(batchUuid))).watch();
});
