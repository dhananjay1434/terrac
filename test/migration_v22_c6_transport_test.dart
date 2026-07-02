import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/data/local/app_database.dart';

/// C6 (v22): the transport_events table must exist and accept a many-per-batch
/// insert after a fresh open. Locks the schema shape; the createTable upgrade
/// block is structurally identical to prior additive table blocks.
void main() {
  test('v22 transport_events table exists and is many-per-batch', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    // schemaVersion is the single latest version (>= the one that introduced
    // this table); assert the C6 TABLE exists, not a pinned number.
    expect(db.schemaVersion, greaterThanOrEqualTo(22));

    await db.customStatement(
      'INSERT INTO system_metadata '
      '(batch_uuid, artisan_id, device_hardware_mac, app_build_version, sync_status, created_at) '
      "VALUES ('b1','a','m','v','PENDING','2026-07-02T00:00:00Z')",
    );
    for (final mat in ['biomass', 'biochar']) {
      await db.customStatement(
        'INSERT INTO transport_events '
        '(event_uuid, batch_uuid, material, distance_km, weight_kg, vehicle_type, '
        'fuel_type, fuel_amount_litres, occurred_at, created_at) '
        "VALUES ('e-$mat','b1','$mat',30.0,500.0,'tractor','diesel',12.0,NULL,'2026-07-02T00:00:00Z')",
      );
    }
    final rows = await db
        .customSelect(
          "SELECT material FROM transport_events WHERE batch_uuid='b1'",
        )
        .get();
    expect(rows.length, 2);
    await db.close();
  });
}
