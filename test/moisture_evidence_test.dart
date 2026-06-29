// ignore_for_file: avoid_print, unnecessary_string_escapes
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:uuid/uuid.dart';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/data/local/database_provider.dart';
import 'package:dmrv_app/providers/batch_session_notifier.dart';
import 'package:dmrv_app/providers/moisture_gate_notifier.dart';

void main() {
  // ---------------------------------------------------------------------------
  // Task 2.2 — moistureEvidenceProvider SQL-level WHERE Test
  // ---------------------------------------------------------------------------
  //
  // Verifies that the rewritten moistureEvidenceProvider:
  //   1. Returns false when no photo exists
  //   2. Returns true when photo exists for matching batch
  //   3. Does not match photos from other batches (WHERE clause works)
  // ---------------------------------------------------------------------------

  late AppDatabase db;
  late ProviderContainer container;
  const uuid = Uuid();

  setUp(() {
    db = AppDatabase.forTesting(NativeDatabase.memory());
    container = ProviderContainer(
      overrides: [appDatabaseProvider.overrideWith((ref) => Future.value(db))],
    );
  });

  tearDown(() async {
    container.dispose();
    await db.close();
  });

  test('returns false when no photo exists', () async {
    // Arrange: Create batch with null photoPath
    final batchUuid = uuid.v4();

    await db
        .into(db.biomassSourcing)
        .insert(
          BiomassSourcingCompanion.insert(
            sourcingUuid: uuid.v4(),
            batchUuid: batchUuid,
            feedstockSpecies: 'Lantana_camara',
            harvestTimestamp: DateTime.now().toUtc().toIso8601String(),
            moisturePercent: 12.5,
            moistureCompliant: true,
            photoPath: const Value(null), // No photo
          ),
        );

    // Override the batch session provider to return our test batch
    container = ProviderContainer(
      overrides: [
        appDatabaseProvider.overrideWith((ref) => Future.value(db)),
        requiredBatchUuidProvider.overrideWith((ref) => batchUuid),
      ],
    );

    // Wait for DB to be available to avoid loading states
    await container.read(appDatabaseProvider.future);

    // Act: Read the future which gets the latest value
    final val = await container.read(moistureEvidenceProvider.future);

    // Assert
    expect(val, false);
  });

  test('returns true when photo exists for matching batch', () async {
    // Arrange: Create batch with non-null photoPath
    final batchUuid = uuid.v4();
    final photoPath = '/sandbox/evidence/moisture_${uuid.v4()}.jpg';

    await db
        .into(db.biomassSourcing)
        .insert(
          BiomassSourcingCompanion.insert(
            sourcingUuid: uuid.v4(),
            batchUuid: batchUuid,
            feedstockSpecies: 'Lantana_camara',
            harvestTimestamp: DateTime.now().toUtc().toIso8601String(),
            moisturePercent: 12.5,
            moistureCompliant: true,
            photoPath: Value(photoPath),
          ),
        );

    // Override the batch session provider
    container = ProviderContainer(
      overrides: [
        appDatabaseProvider.overrideWith((ref) => Future.value(db)),
        requiredBatchUuidProvider.overrideWith((ref) => batchUuid),
      ],
    );

    // Wait for DB to be available to avoid loading states
    await container.read(appDatabaseProvider.future);

    // Act
    final val = await container.read(moistureEvidenceProvider.future);

    // Assert
    expect(val, true);
  });

  test('does not match photos from other batches', () async {
    // Arrange: Create batch-A with photo, query for batch-B (no photo)
    final batchA = uuid.v4();
    final batchB = uuid.v4();
    final photoPath = '/sandbox/evidence/moisture_${uuid.v4()}.jpg';

    // Batch A has a photo
    await db
        .into(db.biomassSourcing)
        .insert(
          BiomassSourcingCompanion.insert(
            sourcingUuid: uuid.v4(),
            batchUuid: batchA,
            feedstockSpecies: 'Lantana_camara',
            harvestTimestamp: DateTime.now().toUtc().toIso8601String(),
            moisturePercent: 12.5,
            moistureCompliant: true,
            photoPath: Value(photoPath),
          ),
        );

    // Batch B has no photo
    await db
        .into(db.biomassSourcing)
        .insert(
          BiomassSourcingCompanion.insert(
            sourcingUuid: uuid.v4(),
            batchUuid: batchB,
            feedstockSpecies: 'Lantana_camara',
            harvestTimestamp: DateTime.now().toUtc().toIso8601String(),
            moisturePercent: 13.0,
            moistureCompliant: true,
            photoPath: const Value(null),
          ),
        );

    // Query for batch B (should return false even though batch A has a photo)
    container = ProviderContainer(
      overrides: [
        appDatabaseProvider.overrideWith((ref) => Future.value(db)),
        requiredBatchUuidProvider.overrideWith((ref) => batchB),
      ],
    );

    // Wait for DB to be available to avoid loading states
    await container.read(appDatabaseProvider.future);

    // Act
    final val = await container.read(moistureEvidenceProvider.future);

    // Assert: Should be false because we're querying batch B which has no photo
    expect(val, false);

    print('✓ WHERE clause correctly filters by batchUuid');
  });
}
