import 'dart:convert';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:drift/native.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

/// V5 — the batch anchor photo must be stamped `capture_type=batch_photo` at
/// the outbox boundary, not left null for a backend backfill to guess later.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('insertBiomassSourcingWithOutbox payload', () {
    late AppDatabase db;

    setUp(() {
      FlutterSecureStorage.setMockInitialValues({});
      db = AppDatabase.forTesting(NativeDatabase.memory());
    });

    tearDown(() async => db.close());

    test('stamps capture_type=batch_photo so the anchor photo is classified at source', () async {
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

      expect(payload['capture_type'], 'batch_photo');
    });
  });
}
