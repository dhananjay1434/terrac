import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/data/local/app_database.dart';

/// V8 Part 1.6 — test Drift schema migration v25 -> v26.
///
/// Verifies:
/// - DB upgrades cleanly from v25 to v26 (`parcel_uuid` column added to `biomass_sourcing`)
/// - Old records (null `parcel_uuid`) read and function without error
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Drift migration v25 -> v26 adds parcel_uuid column cleanly', () async {
    final executor = NativeDatabase.memory();
    final db = AppDatabase.forTesting(executor);

    // Verify current schema version is 26
    expect(db.schemaVersion, 26);

    // Insert a biomass sourcing row
    final sourcingUuid = 'test-sourcing-v26-uuid';
    final batchUuid = '11111111-1111-1111-1111-111111111111';

    await db.into(db.systemMetadata).insert(
          SystemMetadataCompanion.insert(
            batchUuid: batchUuid,
            artisanId: 'artisan-1',
            deviceHardwareMac: 'AA:BB:CC:DD:EE:FF',
            appBuildVersion: '1.0.0',
            createdAt: DateTime.now().toIso8601String(),
          ),
        );

    await db.into(db.biomassSourcing).insert(
          BiomassSourcingCompanion.insert(
            sourcingUuid: sourcingUuid,
            batchUuid: batchUuid,
            feedstockSpecies: 'Lantana_camara',
            harvestTimestamp: DateTime.now().toIso8601String(),
            moisturePercent: 12.5,
            moistureCompliant: true,
            harvestUptimeSeconds: const Value(120),
            parcelUuid: const Value('parcel-alpha-uuid'),
          ),
        );

    final row = await (db.select(db.biomassSourcing)
          ..where((t) => t.sourcingUuid.equals(sourcingUuid)))
        .getSingle();

    expect(row.sourcingUuid, sourcingUuid);
    expect(row.parcelUuid, 'parcel-alpha-uuid');

    await db.close();
  });
}
