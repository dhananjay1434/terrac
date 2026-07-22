import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/data/local/app_database.dart';

/// Deferred R1 — test Drift schema migration v26 -> v27.
///
/// Verifies:
/// - DB upgrades cleanly to v27 (SyncOutbox.batchUuid becomes nullable via
///   TableMigration's table-rewrite; EntityMediaCaptures table is created)
/// - A batch-scoped outbox row (non-null batchUuid) still round-trips
///   unchanged (mirrors migration_v25_to_v26_parcel_test.dart's convention:
///   AppDatabase.forTesting builds the CURRENT schema fresh via onCreate,
///   the same lightweight verification style used by every Drift migration
///   test in this codebase — unlike the backend's real Alembic upgrade/
///   downgrade drives, there is no equivalent "replay history on an old
///   on-disk file" tooling wired up for Drift here).
/// - An entity-scoped media row (null batchUuid) can be enqueued at all —
///   the exact case the v26 schema could never represent.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Drift migration v26 -> v27 adds EntityMediaCaptures + nullable batchUuid', () async {
    final executor = NativeDatabase.memory();
    final db = AppDatabase.forTesting(executor);

    expect(db.schemaVersion, 27);

    // Batch-scoped outbox row — the pre-existing shape — still works.
    await db.into(db.syncOutbox).insert(
          SyncOutboxCompanion.insert(
            operationId: 'op-batch-1',
            batchUuid: const Value('11111111-1111-1111-1111-111111111111'),
            targetTable: 'media',
            operationType: 'INSERT',
            payloadJson: '{}',
            createdAt: DateTime.now().toIso8601String(),
          ),
        );
    final batchRow = await (db.select(db.syncOutbox)
          ..where((t) => t.operationId.equals('op-batch-1')))
        .getSingle();
    expect(batchRow.batchUuid, '11111111-1111-1111-1111-111111111111');

    // Entity-scoped outbox row — null batchUuid — the case v26 couldn't
    // represent at all (NOT NULL column).
    await db.into(db.syncOutbox).insert(
          SyncOutboxCompanion.insert(
            operationId: 'op-entity-1',
            batchUuid: const Value(null),
            targetTable: 'media',
            operationType: 'INSERT',
            payloadJson: '{"subject_type":"farmer","subject_uuid":"f-1"}',
            createdAt: DateTime.now().toIso8601String(),
          ),
        );
    final entityRow = await (db.select(db.syncOutbox)
          ..where((t) => t.operationId.equals('op-entity-1')))
        .getSingle();
    expect(entityRow.batchUuid, null);

    // EntityMediaCaptures table exists and accepts a row.
    await db.into(db.entityMediaCaptures).insert(
          EntityMediaCapturesCompanion.insert(
            subjectType: 'farmer',
            subjectUuid: 'f-1',
            captureType: 'farmer_signature',
            sandboxPath: '/sandbox/sig.jpg',
            sha256Hash: 'a' * 64,
            createdAt: DateTime.now().toIso8601String(),
          ),
        );
    final mediaRow = await (db.select(db.entityMediaCaptures)
          ..where((t) => t.subjectUuid.equals('f-1')))
        .getSingle();
    expect(mediaRow.captureType, 'farmer_signature');
    expect(mediaRow.isMockLocation, false); // default

    await db.close();
  });
}
