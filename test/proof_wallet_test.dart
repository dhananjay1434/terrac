import 'package:drift/drift.dart' hide isNull, isNotNull;
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:uuid/uuid.dart';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/data/local/pyrolysis_writer.dart';
import 'package:dmrv_app/data/local/proof_queries.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// =============================================================================
/// Phase 4 — Proof Wallet / CryptographicReceipt Tests
/// =============================================================================

const _uuid = Uuid();

Future<void> _seedBatch(
  AppDatabase db,
  String batchUuid,
  String createdAt,
) async {
  await db
      .into(db.systemMetadata)
      .insert(
        SystemMetadataCompanion.insert(
          batchUuid: batchUuid,
          artisanId: 'artisan-001',
          deviceHardwareMac: 'AA:BB:CC:DD:EE:FF',
          appBuildVersion: '1.0.0',
          createdAt: createdAt,
        ),
      );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late AppDatabase db;

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    db = AppDatabase.forTesting(NativeDatabase.memory());
  });

  tearDown(() => db.close());

  test('Empty database returns empty receipts list', () async {
    final receipts = await db.watchCryptographicReceipts().first;
    expect(receipts, isEmpty);
  });

  test('Full lifecycle produces complete CryptographicReceipt', () async {
    final batchId = _uuid.v4();
    await _seedBatch(db, batchId, '2026-06-01T10:00:00Z');

    // Biomass sourcing
    await db
        .into(db.biomassSourcing)
        .insert(
          BiomassSourcingCompanion.insert(
            sourcingUuid: _uuid.v4(),
            batchUuid: batchId,
            feedstockSpecies: 'Lantana camara',
            harvestTimestamp: '2026-06-01T10:05:00Z',
            moisturePercent: 12.5,
            moistureCompliant: true,
            sha256Hash: const Value('biomass_sha_abc123'),
            latitude: const Value(28.6139),
            longitude: const Value(77.2090),
          ),
        );

    // Seed 4 smoke photos
    final stages = ['0', '50', '90', '100'];
    for (final s in stages) {
      await db.insertMediaCaptureAndEnqueue(
        batchUuid: batchId,
        captureType: 'smoke_$s',
        sandboxPath: '/evidence/smoke_$s.jpg',
        sha256Hash: 'smoke_sha_xyz$s',
        isMockLocation: false,
      );
    }

    // Pyrolysis telemetry with smoke photo
    await db.insertPyrolysisTelemetryWithOutbox(
      batchUuid: batchId,
      kilnGrossCapacity: 200.0,
      burnStart: DateTime.utc(2026, 6, 1, 11, 0),
      burnEnd: DateTime.utc(2026, 6, 1, 13, 0),
      temperatureReadings: [100.0, 250.0, 420.0, 415.0],
    );

    // Yield metrics
    await db
        .into(db.yieldMetrics)
        .insert(
          YieldMetricsCompanion.insert(
            yieldUuid: _uuid.v4(),
            batchUuid: batchId,
            quenchMethodology: 'water_quench',
            grossVolume: 150.0,
            wetYieldWeightKg: 45.5,
          ),
        );

    final receipts = await db.watchCryptographicReceipts().first;
    expect(receipts, hasLength(1));

    final r = receipts.first;
    expect(r.batchUuid, batchId);
    expect(r.artisanId, 'artisan-001');
    expect(r.feedstockSpecies, 'Lantana camara');
    expect(r.moisturePercent, 12.5);
    expect(r.biomassPhotoSha256, 'biomass_sha_abc123');
    expect(r.biomassLat, closeTo(28.6139, 0.001));
    expect(r.biomassLon, closeTo(77.2090, 0.001));
    expect(r.burnStart, isNotNull);
    expect(r.burnEnd, isNotNull);
    expect(r.maxTemp, 420.0);
    expect(r.smokeProofs, hasLength(4));
    expect(r.yieldWeightKg, 45.5);
  });

  test('Incomplete batch produces partial CryptographicReceipt', () async {
    final batchId = _uuid.v4();
    await _seedBatch(db, batchId, '2026-06-01T10:00:00Z');

    final receipts = await db.watchCryptographicReceipts().first;
    expect(receipts, hasLength(1));

    final r = receipts.first;
    expect(r.batchUuid, batchId);
    expect(r.artisanId, 'artisan-001');

    // All downstream fields should be null since no rows exist
    expect(r.feedstockSpecies, isNull);
    expect(r.moisturePercent, isNull);
    expect(r.burnStart, isNull);
    expect(r.maxTemp, isNull);
    expect(r.smokeProofs, isEmpty);
    expect(r.yieldWeightKg, isNull);
  });

  test('Stream updates when new tables are inserted', () async {
    final batchId = _uuid.v4();
    await _seedBatch(db, batchId, '2026-06-01T10:00:00Z');

    // Subscribe to the stream
    final stream = db.watchCryptographicReceipts();
    var lastReceipts = await stream.first;
    expect(lastReceipts.first.feedstockSpecies, isNull);

    // Insert sourcing data
    await db
        .into(db.biomassSourcing)
        .insert(
          BiomassSourcingCompanion.insert(
            sourcingUuid: _uuid.v4(),
            batchUuid: batchId,
            feedstockSpecies: 'Bamboo',
            harvestTimestamp: '2026-06-01T10:05:00Z',
            moisturePercent: 14.0,
            moistureCompliant: true,
          ),
        );

    // Since stream.first cancels the previous subscription, we can just
    // await stream.first again to get the current state of the database.
    lastReceipts = await stream.first;
    expect(lastReceipts.first.feedstockSpecies, 'Bamboo');
    expect(lastReceipts.first.moisturePercent, 14.0);
  });
}
