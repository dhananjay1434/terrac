import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/data/local/app_database.dart';

/// Drift migration v27 -> v28: Kilns gains a nullable `sensor_profile` cache.
/// Same lightweight style as every migration test here — forTesting builds the
/// CURRENT schema via onCreate; we assert the version and round-trip the new
/// column (there is no schema-dump harness in this repo; see §0.7).
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('v28 Kilns carries a nullable sensor_profile that round-trips', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    expect(db.schemaVersion, 28);

    // Existing shape (no profile) still inserts — column is nullable.
    await db.into(db.kilns).insert(
          KilnsCompanion.insert(
            kilnId: 'K-NONE',
            kilnType: 'open',
            addedAt: DateTime.now().toIso8601String(),
          ),
        );
    final noProfile = await (db.select(db.kilns)
          ..where((t) => t.kilnId.equals('K-NONE')))
        .getSingle();
    expect(noProfile.sensorProfile, null);

    // New shape: a cached 'full' profile round-trips.
    await db.into(db.kilns).insert(
          KilnsCompanion.insert(
            kilnId: 'K-FULL',
            kilnType: 'open',
            addedAt: DateTime.now().toIso8601String(),
            sensorProfile: const Value('full'),
          ),
        );
    final full = await (db.select(db.kilns)
          ..where((t) => t.kilnId.equals('K-FULL')))
        .getSingle();
    expect(full.sensorProfile, 'full');

    await db.close();
  });
}
