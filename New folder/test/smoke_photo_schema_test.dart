import 'dart:convert';
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:uuid/uuid.dart';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/data/local/pyrolysis_writer.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// =============================================================================
/// Phase 6 — Event-Sourced Media Captures Schema Tests
/// =============================================================================

const _uuid = Uuid();

Future<void> _seedBatch(AppDatabase db, String batchUuid) async {
  await db
      .into(db.systemMetadata)
      .insert(
        SystemMetadataCompanion.insert(
          batchUuid: batchUuid,
          artisanId: 'test-artisan',
          deviceHardwareMac: 'AA:BB:CC:DD:EE:FF',
          appBuildVersion: '1.0.0',
          createdAt: DateTime.now().toUtc().toIso8601String(),
        ),
      );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late AppDatabase db;

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    db = AppDatabase.forTesting(NativeDatabase.memory());
  });

  tearDown(() => db.close());

  test(
    'Insert pyrolysis with 4 smoke captures — JSON round-trips correctly',
    () async {
      final batchId = _uuid.v4();
      await _seedBatch(db, batchId);

      // Seed 4 captures
      final stages = ['0', '50', '90', '100'];
      for (final s in stages) {
        await db.insertMediaCaptureAndEnqueue(
          batchUuid: batchId,
          captureType: 'smoke_$s',
          sandboxPath: '/ev/$s.jpg',
          sha256Hash: 'hash_$s',
          isMockLocation: false,
        );
      }

      final telemetryUuid = await db.insertPyrolysisTelemetryWithOutbox(
        batchUuid: batchId,
        kilnGrossCapacity: 200.0,
        burnStart: DateTime.utc(2026, 6, 1, 10, 0),
        burnEnd: DateTime.utc(2026, 6, 1, 12, 0),
        temperatureReadings: [100.0, 250.0, 420.0],
      );

      expect(telemetryUuid, isNotEmpty);

      final row = await (db.select(
        db.pyrolysisTelemetry,
      )..where((t) => t.telemetryUuid.equals(telemetryUuid))).getSingle();

      final evidence = jsonDecode(row.smokeEvidenceJson) as List;
      expect(evidence.length, 4);
      expect(evidence[0]['stage'], '0');
      expect(evidence[0]['sha256'], 'hash_0');
      expect(row.maxTemp, 420.0);
    },
  );

  test(
    'Insert pyrolysis with LESS than 4 smoke captures — throws StateError',
    () async {
      final batchId = _uuid.v4();
      await _seedBatch(db, batchId);

      // Seed only 2 captures
      final stages = ['0', '50'];
      for (final s in stages) {
        await db.insertMediaCaptureAndEnqueue(
          batchUuid: batchId,
          captureType: 'smoke_$s',
          sandboxPath: '/ev/$s.jpg',
          sha256Hash: 'hash_$s',
          isMockLocation: false,
        );
      }

      // Must throw StateError
      expect(
        () => db.insertPyrolysisTelemetryWithOutbox(
          batchUuid: batchId,
          kilnGrossCapacity: 200.0,
          burnStart: DateTime.utc(2026, 6, 1, 10, 0),
          burnEnd: DateTime.utc(2026, 6, 1, 12, 0),
          temperatureReadings: [100.0, 250.0, 420.0],
        ),
        throwsA(isA<StateError>()),
      );
    },
  );

  test(
    'Media Captures correctly decouple from JSON telemetry outbox payload',
    () async {
      final batchId = _uuid.v4();
      await _seedBatch(db, batchId);

      await db.insertMediaCaptureAndEnqueue(
        batchUuid: batchId,
        captureType: 'smoke_0',
        sandboxPath: '/evidence/smoke_002.jpg',
        sha256Hash: 'xyz789hash',
        isMockLocation: false,
      );

      final outboxRows = await (db.select(
        db.syncOutbox,
      )..where((t) => t.targetTable.equals('media'))).get();

      expect(outboxRows, hasLength(1));
      final payloadJson = outboxRows.single.payloadJson;

      expect(payloadJson, contains('/evidence/smoke_002.jpg'));
      expect(payloadJson, contains('xyz789hash'));
      expect(payloadJson, contains('smoke_0'));
    },
  );

  test(
    'Existing tests pattern: temperatureReadings must not be empty',
    () async {
      final batchId = _uuid.v4();
      await _seedBatch(db, batchId);

      // This must throw ArgumentError — existing validation unchanged.
      expect(
        () => db.insertPyrolysisTelemetryWithOutbox(
          batchUuid: batchId,
          kilnGrossCapacity: 200.0,
          burnStart: DateTime.utc(2026, 6, 1, 10, 0),
          burnEnd: DateTime.utc(2026, 6, 1, 12, 0),
          temperatureReadings: [], // EMPTY — must throw
        ),
        throwsA(isA<ArgumentError>()),
      );
    },
  );
}
