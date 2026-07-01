library;

import 'dart:convert';

/// Add to AppDatabase. This extension lives here so the generated `.g.dart`
/// from Prompt 3 does NOT need to be regenerated *just* for this writer.
///
/// Usage:
///   import 'package:dmrv_app/data/local/app_database.dart';
///   import 'package:dmrv_app/data/local/pyrolysis_writer.dart';
///   await db.insertPyrolysisTelemetryWithOutbox(...);

import 'package:drift/drift.dart';
import 'package:uuid/uuid.dart';

import '../../services/crypto_signer.dart';
import 'app_database.dart';

const _uuid = Uuid();

extension PyrolysisWriter on AppDatabase {
  Future<void> insertMediaCaptureAndEnqueue({
    required String batchUuid,
    required String captureType,
    required String sandboxPath,
    required String sha256Hash,
    required bool isMockLocation,
  }) async {
    final now = DateTime.now().toUtc().toIso8601String();

    await transaction(() async {
      await into(mediaCaptures).insert(
        MediaCapturesCompanion.insert(
          batchUuid: batchUuid,
          captureType: captureType,
          sandboxPath: sandboxPath,
          sha256Hash: sha256Hash,
          isMockLocation: Value(isMockLocation),
          createdAt: now,
        ),
        mode: InsertMode.replace,
      );

      final payload = {
        'photo_path': sandboxPath,
        'sha256_hash': sha256Hash,
        'capture_type': captureType,
        'batch_uuid': batchUuid,
        'isMockLocation': isMockLocation,
      };

      final jsonString = jsonEncode(payload);
      final signature = await CryptoSigner.signPayload(jsonString);

      await into(syncOutbox).insert(
        SyncOutboxCompanion.insert(
          operationId: _uuid.v4(),
          batchUuid: batchUuid,
          targetTable: 'media',
          operationType: 'INSERT',
          payloadJson: jsonString,
          createdAt: now,
          hmacSignature: Value(signature),
        ),
      );
    });
  }

  /// Atomically inserts a PyrolysisTelemetry row + SyncOutbox event.
  Future<String> insertPyrolysisTelemetryWithOutbox({
    required String batchUuid,
    required double kilnGrossCapacity,
    required DateTime burnStart,
    required DateTime burnEnd,
    required List<double> temperatureReadings,
    List<List<int>> attestationBlobs = const [],
  }) async {
    if (temperatureReadings.isEmpty) {
      throw ArgumentError(
        'temperatureReadings must contain at least one sample.',
      );
    }

    // 1. Fetch exactly 4 smoke photos from the database.
    final captures =
        await (select(mediaCaptures)
              ..where((t) => t.batchUuid.equals(batchUuid))
              ..where((t) => t.captureType.like('smoke_%'))
              ..orderBy([(t) => OrderingTerm.asc(t.createdAt)]))
            .get();

    final smokeEvidence = captures
        .map(
          (c) => {
            'stage': c.captureType.replaceFirst('smoke_', ''),
            'sha256': c.sha256Hash,
          },
        )
        .toList();

    final telemetryUuid = _uuid.v4();
    final minT = temperatureReadings.reduce((a, b) => a < b ? a : b);
    final maxT = temperatureReadings.reduce((a, b) => a > b ? a : b);

    final evidenceJsonString = jsonEncode(smokeEvidence);

    final companion = PyrolysisTelemetryCompanion.insert(
      telemetryUuid: telemetryUuid,
      batchUuid: batchUuid,
      kilnGrossCapacity: kilnGrossCapacity,
      burnStartTimestamp: burnStart.toUtc().toIso8601String(),
      burnEndTimestamp: Value(burnEnd.toUtc().toIso8601String()),
      minTemp: minT,
      maxTemp: maxT,
      temperatureReadingsJson: Value(jsonEncode(temperatureReadings)),
      smokeEvidenceJson: Value(evidenceJsonString),
      hwAttestationJson: Value(
        jsonEncode(attestationBlobs.map((b) => base64Encode(b)).toList()),
      ),
    );

    final payload = <String, dynamic>{
      'telemetry_uuid': telemetryUuid,
      'batch_uuid': batchUuid,
      'kiln_gross_capacity': kilnGrossCapacity,
      'burn_start_timestamp': burnStart.toUtc().toIso8601String(),
      'burn_end_timestamp': burnEnd.toUtc().toIso8601String(),
      'min_temp': minT,
      'max_temp': maxT,
      'temperature_readings': temperatureReadings,
      'smoke_evidence': smokeEvidence,
      'hw_attestation': attestationBlobs.map((b) => base64Encode(b)).toList(),
    };

    await insertWithOutbox(
      batchUuid: batchUuid,
      targetTable: 'pyrolysis_telemetry',
      payload: payload,
      insertRow: () => into(
        pyrolysisTelemetry,
      ).insert(companion, mode: InsertMode.insertOrReplace),
    );

    if (captures.length != 4) {
      throw StateError(
        'Saved telemetry. Cannot finalise burn: '
        'need 4 smoke captures, found ${captures.length}. '
        'Retake the missing stages and call finaliseBurn(telemetryUuid: $telemetryUuid).',
      );
    }
    return telemetryUuid;
  }
}
