import 'dart:convert';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:uuid/uuid.dart';

import 'package:dmrv_app/data/local/app_database.dart';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  FlutterSecureStorage.setMockInitialValues({});
  // ---------------------------------------------------------------------------
  // Drift Schema & Transactional Outbox Test
  // ---------------------------------------------------------------------------
  //
  // Verifies:
  //   1. Drift schema bootstraps cleanly under NativeDatabase.memory().
  //   2. UUID-v4 primary keys persist without collision.
  //   3. A single atomic transaction writes to SystemMetadata AND SyncOutbox.
  //   4. Foreign-key relationship batch_uuid <-> SyncOutbox.batch_uuid holds.
  //   5. JSON payload round-trips correctly through the outbox.
  // ---------------------------------------------------------------------------

  late AppDatabase db;
  const uuid = Uuid();

  setUp(() {
    db = AppDatabase.forTesting(NativeDatabase.memory());
  });

  tearDown(() async {
    await db.close();
  });

  test('atomic transaction writes SystemMetadata + SyncOutbox event', () async {
    // ------- Arrange: build a mock carbon-credit batch ------------------------
    final batchUuid = uuid.v4();
    final nowIso = DateTime.now().toUtc().toIso8601String();

    final metaCompanion = SystemMetadataCompanion.insert(
      batchUuid: batchUuid,
      artisanId: 'ARTISAN-RURAL-007',
      deviceHardwareMac: 'AA:BB:CC:DD:EE:01',
      appBuildVersion: '1.0.0+1',
      createdAt: nowIso,
      syncStatus: const Value('PENDING'),
    );

    // ------- Act: execute the atomic insert -----------------------------------
    await db.insertSystemMetadataWithOutbox(metaCompanion);

    // ------- Assert: SystemMetadata row exists --------------------------------
    final metaRows = await db.select(db.systemMetadata).get();
    expect(metaRows, hasLength(1));
    expect(metaRows.single.batchUuid, batchUuid);
    expect(metaRows.single.artisanId, 'ARTISAN-RURAL-007');
    expect(metaRows.single.syncStatus, 'PENDING');

    // ------- Assert: SyncOutbox row is paired with the same batch_uuid --------
    final outboxRows = await db.select(db.syncOutbox).get();
    expect(
      outboxRows,
      hasLength(1),
      reason: 'Outbox event must be written in the same transaction',
    );
    final outbox = outboxRows.single;
    expect(
      outbox.batchUuid,
      batchUuid,
      reason: 'FK linkage from outbox -> system_metadata must hold',
    );
    expect(outbox.targetTable, 'system_metadata');
    expect(outbox.operationType, 'INSERT');
    expect(outbox.status, 'PENDING');
    expect(outbox.retryCount, 0);

    // operation_id must itself be a valid UUID-v4 (offline-collision-safe)
    expect(
      RegExp(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-'
        r'[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
      ).hasMatch(outbox.operationId),
      isTrue,
      reason: 'operation_id must be a v4 UUID',
    );

    // ------- Assert: JSON payload round-trips ---------------------------------
    final decodedPayload =
        jsonDecode(outbox.payloadJson) as Map<String, dynamic>;
    expect(decodedPayload['batch_uuid'], batchUuid);
    expect(decodedPayload['artisan_id'], 'ARTISAN-RURAL-007');
    expect(decodedPayload['app_build_version'], '1.0.0+1');

    // ------- Print final state for explicit human verification ---------------
    final dump = {
      'system_metadata': metaRows
          .map(
            (r) => {
              'batch_uuid': r.batchUuid,
              'artisan_id': r.artisanId,
              'device_hardware_mac': r.deviceHardwareMac,
              'app_build_version': r.appBuildVersion,
              'sync_status': r.syncStatus,
              'created_at': r.createdAt,
            },
          )
          .toList(),
      'sync_outbox': outboxRows
          .map(
            (r) => {
              'operation_id': r.operationId,
              'batch_uuid': r.batchUuid,
              'target_table': r.targetTable,
              'operation_type': r.operationType,
              'status': r.status,
              'retry_count': r.retryCount,
              'created_at': r.createdAt,
              'payload': jsonDecode(r.payloadJson),
            },
          )
          .toList(),
    };

    // ignore: avoid_print
    print('--- drift_schema_test :: final state ---');
    // ignore: avoid_print
    print(const JsonEncoder.withIndent('  ').convert(dump));
  });

  test('transaction rollback leaves both tables empty on failure', () async {
    // Attempting to insert two rows with the same primary key inside one
    // transaction must roll back BOTH the metadata insert AND any outbox event
    // emitted before the failure.
    final batchUuid = uuid.v4();
    final nowIso = DateTime.now().toUtc().toIso8601String();

    final meta = SystemMetadataCompanion.insert(
      batchUuid: batchUuid,
      artisanId: 'ARTISAN-A',
      deviceHardwareMac: 'AA:BB:CC:DD:EE:02',
      appBuildVersion: '1.0.0+1',
      createdAt: nowIso,
    );

    await db.insertSystemMetadataWithOutbox(meta);

    // Second insert with the same PK should throw and not corrupt state.
    await expectLater(
      db.insertSystemMetadataWithOutbox(meta),
      throwsA(isA<Exception>()),
    );

    final metaCount = (await db.select(db.systemMetadata).get()).length;
    final outboxCount = (await db.select(db.syncOutbox).get()).length;

    // Exactly one row each (only the first successful txn persisted).
    expect(metaCount, 1);
    expect(outboxCount, 1);
  });

  test('SyncOutbox has hmacSignature column', () async {
    final columns = db.syncOutbox.$columns;
    final hasHmacColumn = columns.any((c) => c.$name == 'hmac_signature');
    expect(hasHmacColumn, isTrue);
  });

  test('p0_6_media_captures_unique_index_exists_on_fresh_install', () async {
    final db2 = AppDatabase.forTesting(NativeDatabase.memory());
    final rows = await db2
        .customSelect(
          "SELECT name FROM sqlite_master WHERE type='index' AND name='ux_media_captures_batch_type'",
        )
        .get();
    expect(
      rows,
      isNotEmpty,
      reason: 'ux_media_captures_batch_type must exist on fresh install',
    );
    await db2.close();
  });
}
