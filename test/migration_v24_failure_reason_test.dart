import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/data/local/app_database.dart';

/// P1-C1 (v24): sync_outbox gains a nullable failure_reason column (surfaced in
/// the Sync Health screen). Locks the schema shape; the addColumn upgrade
/// mirrors prior additive columns.
void main() {
  test('v24 sync_outbox has a nullable failure_reason column', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    expect(db.schemaVersion, greaterThanOrEqualTo(24));

    // Insert without failure_reason -> NULL allowed.
    await db.customStatement(
      'INSERT INTO sync_outbox '
      '(operation_id, batch_uuid, target_table, operation_type, payload_json, created_at) '
      "VALUES ('op1','b1','system_metadata','INSERT','{}','2026-07-10T00:00:00Z')",
    );
    final before = await db
        .customSelect(
          "SELECT failure_reason FROM sync_outbox WHERE operation_id='op1'",
        )
        .getSingle();
    expect(before.data['failure_reason'], isNull);

    // A reason can be stored and read back.
    await db.customStatement(
      "UPDATE sync_outbox SET failure_reason='boom' WHERE operation_id='op1'",
    );
    final after = await db
        .customSelect(
          "SELECT failure_reason FROM sync_outbox WHERE operation_id='op1'",
        )
        .getSingle();
    expect(after.data['failure_reason'], 'boom');

    await db.close();
  });
}
