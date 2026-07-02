import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/data/local/app_database.dart';

/// C5 (v21): the delivery + buyer-identity columns must exist and accept
/// nullable writes after a fresh open. This locks the schema shape; the
/// addColumn upgrade block is structurally identical to prior additive blocks.
void main() {
  test('v21 end_use_application carries delivery + buyer columns', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    // schemaVersion is the single latest version (>= the one that introduced
    // these columns); assert the C5 COLUMNS exist, not a pinned number.
    expect(db.schemaVersion, greaterThanOrEqualTo(21));

    // A raw insert naming the new columns proves they exist in the built schema.
    await db.customStatement(
      'INSERT INTO system_metadata '
      '(batch_uuid, artisan_id, device_hardware_mac, app_build_version, sync_status, created_at) '
      "VALUES ('b1','a','m','v','PENDING','2026-07-02T00:00:00Z')",
    );
    await db.customStatement(
      'INSERT INTO end_use_application '
      '(application_uuid, batch_uuid, application_methodology, application_rate, transport_distance_km, '
      'delivery_date, delivered_amount_kg, buyer_name, buyer_contact) '
      "VALUES ('a1','b1','SURFACE_BROADCAST',1.0,0.0,'2026-07-02T00:00:00Z',42.5,'Asha','x')",
    );
    final rows = await db
        .customSelect(
          'SELECT buyer_name, delivered_amount_kg FROM end_use_application',
        )
        .get();
    expect(rows.single.data['buyer_name'], 'Asha');
    expect(rows.single.data['delivered_amount_kg'], 42.5);
    await db.close();
  });
}
