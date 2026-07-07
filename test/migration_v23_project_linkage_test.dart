import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/data/local/app_database.dart';

/// T1.1 (v23): biomass_sourcing must carry the nullable project_id + scale_id
/// linkage columns and accept both a linked and a legacy (null) row. Locks the
/// schema shape; the addColumn upgrade block mirrors prior additive columns.
void main() {
  test('v23 biomass_sourcing has nullable project_id + scale_id', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    // schemaVersion is the single latest version (>= the one that introduced
    // this linkage); assert the columns exist, not a pinned number.
    expect(db.schemaVersion, greaterThanOrEqualTo(23));

    // biomass_sourcing.batch_uuid is UNIQUE, so each row needs its own batch.
    for (final b in ['b1', 'b2']) {
      await db.customStatement(
        'INSERT INTO system_metadata '
        '(batch_uuid, artisan_id, device_hardware_mac, app_build_version, sync_status, created_at) '
        "VALUES ('$b','a','m','v','PENDING','2026-07-08T00:00:00Z')",
      );
    }

    // Linked row: project_id + scale_id present.
    await db.customStatement(
      'INSERT INTO biomass_sourcing '
      '(sourcing_uuid, batch_uuid, feedstock_species, harvest_timestamp, '
      'moisture_percent, moisture_compliant, project_id, scale_id) '
      "VALUES ('s1','b1','Lantana_camara','2026-07-08T00:00:00Z',12.0,1,'proj-khp-01','scale-7')",
    );

    // Legacy row: linkage columns omitted -> NULL (must be allowed).
    await db.customStatement(
      'INSERT INTO biomass_sourcing '
      '(sourcing_uuid, batch_uuid, feedstock_species, harvest_timestamp, '
      'moisture_percent, moisture_compliant) '
      "VALUES ('s2','b2','Lantana_camara','2026-07-08T00:00:00Z',12.0,1)",
    );

    final linked = await db
        .customSelect(
          "SELECT project_id, scale_id FROM biomass_sourcing WHERE sourcing_uuid='s1'",
        )
        .getSingle();
    expect(linked.data['project_id'], 'proj-khp-01');
    expect(linked.data['scale_id'], 'scale-7');

    final legacy = await db
        .customSelect(
          "SELECT project_id, scale_id FROM biomass_sourcing WHERE sourcing_uuid='s2'",
        )
        .getSingle();
    expect(legacy.data['project_id'], isNull);
    expect(legacy.data['scale_id'], isNull);

    await db.close();
  });
}
