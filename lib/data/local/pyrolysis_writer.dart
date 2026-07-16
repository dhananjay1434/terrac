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
    String? kilnType, // 'open' | 'closed' (Rainbow compliance C0)
    String? kilnId,
    double? flameHeightM, // Rainbow C3 (open-kiln)
    String? ignitionEnergyType, // Rainbow C3b (closed-kiln)
    double? ignitionEnergyAmount,
  }) async {
    if (temperatureReadings.isEmpty) {
      throw ArgumentError(
        'temperatureReadings must contain at least one sample.',
      );
    }

    // 1. Fetch the burn evidence photos: the 4 smoke-opacity proofs plus the
    //    P1-S4 Rainbow C3 stage photos (flame_curtain/quenching/flame_height).
    //    The server gate keys off the `stage` string, so smoke_* stays '0'/'50'
    //    /'90'/'100' and the flame stages pass through verbatim.
    final captures =
        await (select(mediaCaptures)
              ..where((t) => t.batchUuid.equals(batchUuid))
              ..where(
                (t) =>
                    t.captureType.like('smoke_%') |
                    t.captureType.isIn(const [
                      'flame_curtain',
                      'quenching',
                      'flame_height',
                    ]),
              )
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
      kilnType: Value(kilnType),
      kilnId: Value(kilnId),
      flameHeightM: Value(flameHeightM),
      ignitionEnergyType: Value(ignitionEnergyType),
      ignitionEnergyAmount: Value(ignitionEnergyAmount),
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
      'kiln_type': kilnType,
      'kiln_id': kilnId,
      'flame_height_m': flameHeightM,
      'ignition_energy_type': ignitionEnergyType,
      'ignition_energy_amount': ignitionEnergyAmount,
    };

    await insertWithOutbox(
      batchUuid: batchUuid,
      targetTable: 'pyrolysis_telemetry',
      payload: payload,
      insertRow: () => into(
        pyrolysisTelemetry,
      ).insert(companion, mode: InsertMode.insertOrReplace),
    );

    final smokeCount = captures
        .where((c) => c.captureType.startsWith('smoke_'))
        .length;
        
    if (kilnType != 'open' && smokeCount != 4) {
      throw StateError(
        'Saved telemetry. Cannot finalise burn: '
        'need 4 smoke captures, found $smokeCount. '
        'Retake the missing stages and call finaliseBurn(telemetryUuid: $telemetryUuid).',
      );
    } else if (kilnType == 'open') {
      final flameCount = captures
          .where((c) => const ['flame_curtain', 'quenching', 'flame_height'].contains(c.captureType))
          .length;
      if (flameCount != 3) {
        throw StateError(
          'Saved telemetry. Cannot finalise burn: '
          'need 3 flame captures (curtain, quenching, height), found $flameCount. '
          'Retake the missing stages and call finaliseBurn(telemetryUuid: $telemetryUuid).'
        );
      }
    }
    
    return telemetryUuid;
  }
}
