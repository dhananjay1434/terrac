import 'package:flutter_test/flutter_test.dart';
import 'package:drift/native.dart';
import 'package:dmrv_app/data/local/app_database.dart';

void main() {
  test(
    'getBatchTelemetryRaw executes safely with parameterized variable',
    () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      final results = await db.getBatchTelemetryRaw(
        "'; DROP TABLE pyrolysis_telemetry; --",
      );
      expect(results, isEmpty);
      await db.close();
    },
  );
}
