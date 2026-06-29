// =====================================================================
// P1-23 — JSON CHECK constraints on temperature/smoke/hw_attestation cols.
// =====================================================================
import 'package:drift/drift.dart' show Variable;
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dmrv_app/data/local/app_database.dart';

void main() {
  late AppDatabase db;
  setUp(() => db = AppDatabase.forTesting(NativeDatabase.memory()));
  tearDown(() => db.close());

  test('inserting non-JSON into temperature_readings_json must fail', () async {
    expect(
      () => db.customStatement(
        "INSERT INTO pyrolysis_telemetry "
        "(telemetry_uuid, batch_uuid, kiln_gross_capacity, burn_start_timestamp, "
        " min_temp, max_temp, temperature_readings_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ['t', 'b', 1.0, '2026-01-01T00:00:00Z', 0.0, 0.0, 'NOT JSON AT ALL'],
      ),
      throwsA(anything),
      reason: 'CHECK (json_valid(temperature_readings_json)) missing. '
          'See /app/detailed.md#P1-23.',
    );
  });
}
