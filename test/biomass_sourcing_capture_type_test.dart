import 'dart:convert';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/services/sync_queue_manager.dart';
import 'package:drift/native.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

/// V5 — the batch anchor photo is classified as `batch_photo`, but the
/// classification is DERIVED from the target table and forwarded only as the
/// media X-Capture-Type header. It must NOT be written into the JSON metadata
/// body: /batches is a strict endpoint that rejects unknown fields (422
/// extra_forbidden), which is the regression this test guards against.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('insertBiomassSourcingWithOutbox payload', () {
    late AppDatabase db;

    setUp(() {
      FlutterSecureStorage.setMockInitialValues({});
      db = AppDatabase.forTesting(NativeDatabase.memory());
    });

    tearDown(() async => db.close());

    test('does NOT put capture_type in the JSON body; it is derived from the table', () async {
      await db.insertBiomassSourcingWithOutbox(
        batchUuid: 'b1',
        feedstockSpecies: 'bamboo',
        harvestTimestamp: '2026-07-02T00:00:00Z',
        moisturePercent: 12.0,
        moistureCompliant: true,
        photoPath: '/sandbox/anchor.jpg',
        sha256Hash: 'a' * 64,
      );

      final row = await (db.select(
        db.syncOutbox,
      )..where((t) => t.targetTable.equals('biomass_sourcing'))).getSingle();
      final payload = jsonDecode(row.payloadJson) as Map<String, dynamic>;

      expect(payload.containsKey('capture_type'), isFalse);
      expect(kCaptureTypeByTable['biomass_sourcing'], 'batch_photo');
    });
  });
}
