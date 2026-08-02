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

    test('carries the selected parcel_uuid into the outbox JSON body (Part 1.6)',
        () async {
      await db.insertBiomassSourcingWithOutbox(
        batchUuid: 'b-parcel',
        feedstockSpecies: 'Lantana_camara',
        harvestTimestamp: '2026-07-02T00:00:00Z',
        moisturePercent: 12.0,
        moistureCompliant: true,
        photoPath: '/sandbox/anchor.jpg',
        sha256Hash: 'a' * 64,
        projectId: 'proj-1',
        parcelUuid: 'parcel-xyz',
      );

      final row = await (db.select(
        db.syncOutbox,
      )..where((t) => t.targetTable.equals('biomass_sourcing'))).getSingle();
      final payload = jsonDecode(row.payloadJson) as Map<String, dynamic>;

      // The server's /batches schema geofences on this field; it must be in the
      // signed JSON body the app sends.
      expect(payload['parcel_uuid'], 'parcel-xyz');
      expect(payload['project_id'], 'proj-1');
    });

    test('omitting the parcel leaves parcel_uuid null (grandfathered batch)',
        () async {
      await db.insertBiomassSourcingWithOutbox(
        batchUuid: 'b-noparcel',
        feedstockSpecies: 'Lantana_camara',
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

      // Present as an explicit null (server treats null as "no geofence").
      expect(payload['parcel_uuid'], isNull);
    });

    // Regression: moisture (C2) and composite-pile (C4) photos ride the same
    // /media path but their signed metadata payloads cannot carry capture_type
    // (strict endpoints). They were absent from kCaptureTypeByTable, so their
    // photos uploaded with a NULL capture_type and the verifier portal bucketed
    // them under "Other / Uncategorized". They must now derive a type from the
    // table — while still NOT writing capture_type into the JSON body.
    test('moisture + composite photos derive a capture_type from the table, not the body', () async {
      await db.insertMoistureReadingWithOutbox(
        batchUuid: 'b-moist',
        moisturePercent: 5.0,
        sequence: 1,
        photoPath: '/sandbox/moist.jpg',
        sha256Hash: 'a' * 64,
      );
      await db.insertCompositePileSampleWithOutbox(
        batchUuid: 'b-comp',
        photoPath: '/sandbox/comp.jpg',
        sha256Hash: 'b' * 64,
      );

      final moist = await (db.select(db.syncOutbox)
            ..where((t) => t.targetTable.equals('moisture_readings')))
          .getSingle();
      final comp = await (db.select(db.syncOutbox)
            ..where((t) => t.targetTable.equals('composite_pile_samples')))
          .getSingle();

      // capture_type stays OUT of the strict JSON metadata bodies.
      expect((jsonDecode(moist.payloadJson) as Map).containsKey('capture_type'), isFalse);
      expect((jsonDecode(comp.payloadJson) as Map).containsKey('capture_type'), isFalse);

      // ...and is derived from the table for the X-Capture-Type header.
      // 'moisture' is the canonical string the backend custody-timeline
      // projection (stage_projection._CAPTURE_STAGE) already maps to a stage.
      expect(kCaptureTypeByTable['moisture_readings'], 'moisture');
      expect(kCaptureTypeByTable['composite_pile_samples'], 'composite_sample');
    });
  });
}
