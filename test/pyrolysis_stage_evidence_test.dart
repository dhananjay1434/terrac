import 'dart:convert';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/data/local/pyrolysis_writer.dart';
import 'package:drift/native.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

/// P1-S4 — the telemetry writer's `smoke_evidence` must carry the 3 Rainbow C3
/// flame stages (flame_curtain/quenching/flame_height) alongside the 4 smoke
/// proofs, with a sha256 on each, plus the open-kiln flame height. This is the
/// exact shape the server gate `derive_pyrolysis_photo_compliance` grades.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late AppDatabase db;
  const sha = '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef';

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    db = AppDatabase.forTesting(NativeDatabase.memory());
  });
  tearDown(() async => db.close());

  test('open-kiln telemetry payload carries all 7 stages + flame height', () async {
    await db.customStatement(
      'INSERT INTO system_metadata '
      '(batch_uuid, artisan_id, device_hardware_mac, app_build_version, '
      'sync_status, created_at) '
      "VALUES ('b1','a','m','v','PENDING','2026-07-10T00:00:00Z')",
    );

    for (final type in const [
      'smoke_0',
      'smoke_50',
      'smoke_90',
      'smoke_100',
      'flame_curtain',
      'quenching',
      'flame_height',
    ]) {
      await db.insertMediaCaptureAndEnqueue(
        batchUuid: 'b1',
        captureType: type,
        sandboxPath: '/sandbox/$type.jpg',
        sha256Hash: sha,
        isMockLocation: false,
      );
    }

    await db.insertPyrolysisTelemetryWithOutbox(
      batchUuid: 'b1',
      kilnGrossCapacity: 200,
      kilnId: 'KILN-42',
      kilnType: 'open',
      burnStart: DateTime.utc(2026, 7, 10, 10),
      burnEnd: DateTime.utc(2026, 7, 10, 11),
      temperatureReadings: const [650, 660, 655],
      flameHeightM: 0.3,
    );

    final row = await (db.select(db.syncOutbox)
          ..where((t) => t.targetTable.equals('pyrolysis_telemetry')))
        .getSingle();
    final payload = jsonDecode(row.payloadJson) as Map<String, dynamic>;
    final evidence = (payload['smoke_evidence'] as List).cast<Map>();
    final stages = evidence.map((e) => e['stage'] as String).toSet();

    expect(stages, containsAll(<String>{'flame_curtain', 'quenching', 'flame_height'}));
    expect(stages, containsAll(<String>{'0', '50', '90', '100'}));
    expect(evidence.length, 7);
    expect(evidence.every((e) => (e['sha256'] as String).isNotEmpty), isTrue);
    expect(payload['flame_height_m'], 0.3);
    expect(payload['kiln_type'], 'open');
  });
}
