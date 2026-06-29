// =====================================================================
// P0-19 — Re-take of a smoke capture must NOT discard temperature log.
//
// Run from <REPO_ROOT>:
//     flutter test test/pyrolysis_writer_retake_test.dart
//
// This is a template. Adjust import paths to match your project package
// name (`dmrv_app` in the provided codebase).
// =====================================================================
import 'package:drift/native.dart';
import 'package:drift/drift.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/data/local/pyrolysis_writer.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late AppDatabase db;

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    db = AppDatabase.forTesting(NativeDatabase.memory());
  });

  tearDown(() async {
    await db.close();
  });

  test('retake of a smoke_1 capture replaces the row (upsert)', () async {
    const batchUuid = 'BATCH-RETAKE-001';
    // 1st capture for smoke_1
    await db.insertMediaCaptureAndEnqueue(
      batchUuid: batchUuid,
      captureType: 'smoke_1',
      sandboxPath: '/sandbox/v1.jpg',
      sha256Hash: 'a' * 64,
      isMockLocation: false,
    );
    // Re-take — must NOT throw UNIQUE constraint
    await db.insertMediaCaptureAndEnqueue(
      batchUuid: batchUuid,
      captureType: 'smoke_1',
      sandboxPath: '/sandbox/v2.jpg',
      sha256Hash: 'b' * 64,
      isMockLocation: false,
    );

    final rows = await db.customSelect(
      'SELECT sandbox_path, sha256_hash FROM media_captures '
      'WHERE batch_uuid = ? AND capture_type = ?',
      variables: [Variable.withString(batchUuid), Variable.withString('smoke_1')],
    ).get();
    expect(rows.length, 1);
    expect(rows.first.data['sandbox_path'], '/sandbox/v2.jpg');
    expect(rows.first.data['sha256_hash'], 'b' * 64);
  });

  test('insertPyrolysisTelemetry persists temperature log even if photos incomplete',
      () async {
    const batchUuid = 'BATCH-RETAKE-002';
    // Only 3 of the 4 required smoke captures present.
    for (final s in ['smoke_1', 'smoke_2', 'smoke_3']) {
      await db.insertMediaCaptureAndEnqueue(
        batchUuid: batchUuid,
        captureType: s,
        sandboxPath: '/sandbox/$s.jpg',
        sha256Hash: 'a' * 64,
        isMockLocation: false,
      );
    }

    final readings = List.generate(60, (i) => 200.0 + i.toDouble());
    await expectLater(
      () => db.insertPyrolysisTelemetryWithOutbox(
        batchUuid: batchUuid,
        kilnGrossCapacity: 1.0,
        burnStart: DateTime.utc(2026, 1, 1, 0, 0, 0),
        burnEnd: DateTime.utc(2026, 1, 1, 1, 0, 0),
        temperatureReadings: readings,
      ),
      throwsStateError,
    );

    // Critical assertion: even though end-burn threw, the telemetry row
    // must already exist with the full 60-sample log. See /app/detailed.md#P0-19.
    final saved = await db.customSelect(
      'SELECT temperature_readings_json FROM pyrolysis_telemetry '
      'WHERE batch_uuid = ?',
      variables: [Variable.withString(batchUuid)],
    ).get();
    expect(saved.length, 1, reason: 'Telemetry row not persisted before photo check.');
    expect(saved.first.data['temperature_readings_json'].toString().contains('200.0'),
        isTrue);
  });
}
