import 'dart:convert';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/data/local/pyrolysis_writer.dart';
import 'package:drift/native.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

/// Deferred R1 — entity-scoped media (farmer/dispatch), the writer half.
/// Asserts: the outbox row has a NULL batchUuid (not the batch shape), the
/// payload carries subject_type/subject_uuid instead of batch_uuid, an
/// EntityMediaCaptures row is written (not MediaCaptures — that table can't
/// represent a batch-less row), and the returned media id has the
/// `<opId>_media` shape sync_queue_manager's _uploadMedia derives.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('insertEntityMediaWithOutbox', () {
    late AppDatabase db;

    setUp(() {
      FlutterSecureStorage.setMockInitialValues({});
      db = AppDatabase.forTesting(NativeDatabase.memory());
    });
    tearDown(() async => db.close());

    test('farmer media enqueues with null batchUuid + subject fields', () async {
      final mediaId = await db.insertEntityMediaWithOutbox(
        subjectType: 'farmer',
        subjectUuid: 'farmer-uuid-1',
        captureType: 'farmer_signature',
        sandboxPath: '/sandbox/sig.jpg',
        sha256Hash: 'a' * 64,
        isMockLocation: false,
      );

      expect(mediaId, endsWith('_media'));

      final row = await (db.select(
        db.syncOutbox,
      )..where((t) => t.targetTable.equals('media'))).getSingle();
      expect(row.batchUuid, null);

      final payload = jsonDecode(row.payloadJson) as Map<String, dynamic>;
      expect(payload['subject_type'], 'farmer');
      expect(payload['subject_uuid'], 'farmer-uuid-1');
      expect(payload['capture_type'], 'farmer_signature');
      expect(payload.containsKey('batch_uuid'), isFalse);
      // No PII beyond what's already legitimately part of the capture.
      expect(payload.containsKey('mobile_number'), isFalse);

      final mediaRow = await db.select(db.entityMediaCaptures).getSingle();
      expect(mediaRow.subjectType, 'farmer');
      expect(mediaRow.subjectUuid, 'farmer-uuid-1');
    });

    test('dispatch media enqueues with subject_type=dispatch', () async {
      await db.insertEntityMediaWithOutbox(
        subjectType: 'dispatch',
        subjectUuid: 'dispatch-uuid-1',
        captureType: 'dispatch_truck_photo',
        sandboxPath: '/sandbox/truck.jpg',
        sha256Hash: 'b' * 64,
        isMockLocation: false,
      );

      final row = await (db.select(
        db.syncOutbox,
      )..where((t) => t.targetTable.equals('media'))).getSingle();
      final payload = jsonDecode(row.payloadJson) as Map<String, dynamic>;
      expect(payload['subject_type'], 'dispatch');
      expect(payload['subject_uuid'], 'dispatch-uuid-1');
    });

    test('returned media id is derived from the outbox operationId, not a fresh uuid', () async {
      final mediaId = await db.insertEntityMediaWithOutbox(
        subjectType: 'farmer',
        subjectUuid: 'farmer-uuid-2',
        captureType: 'farmer_id_document',
        sandboxPath: '/sandbox/id.jpg',
        sha256Hash: 'c' * 64,
        isMockLocation: false,
      );

      final row = await db.select(db.syncOutbox).getSingle();
      expect(mediaId, '${row.operationId}_media');
    });
  });
}
