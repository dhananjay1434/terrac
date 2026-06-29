import 'dart:convert';
import 'package:drift/drift.dart';

import 'app_database.dart';

/// A fully-joined "Cryptographic Receipt" for one batch lifecycle.
class CryptographicReceipt {
  const CryptographicReceipt({
    required this.batchUuid,
    required this.artisanId,
    required this.createdAt,
    this.feedstockSpecies,
    this.moisturePercent,
    this.biomassPhotoSha256,
    this.biomassLat,
    this.biomassLon,
    this.burnStart,
    this.burnEnd,
    this.maxTemp,
    this.minTemp,
    this.sampleCount,
    this.smokeProofs = const [],
    this.yieldWeightKg,
  });

  final String batchUuid;
  final String artisanId;
  final String createdAt;
  final String? feedstockSpecies;
  final double? moisturePercent;
  final String? biomassPhotoSha256;
  final double? biomassLat;
  final double? biomassLon;
  final String? burnStart;
  final String? burnEnd;
  final double? maxTemp;
  final double? minTemp;
  final int? sampleCount;
  final List<Map<String, dynamic>> smokeProofs;
  final double? yieldWeightKg;
}

extension ProofQueries on AppDatabase {
  /// Watches all batch lifecycles as CryptographicReceipts,
  /// ordered by creation date descending (newest first).
  Stream<List<CryptographicReceipt>> watchCryptographicReceipts() {
    final query = select(systemMetadata).join([
      leftOuterJoin(
        biomassSourcing,
        biomassSourcing.batchUuid.equalsExp(systemMetadata.batchUuid),
      ),
      leftOuterJoin(
        pyrolysisTelemetry,
        pyrolysisTelemetry.batchUuid.equalsExp(systemMetadata.batchUuid),
      ),
      leftOuterJoin(
        yieldMetrics,
        yieldMetrics.batchUuid.equalsExp(systemMetadata.batchUuid),
      ),
    ])..orderBy([OrderingTerm.desc(systemMetadata.createdAt)]);

    return query.watch().map((rows) {
      final uniqueReceipts = <String, CryptographicReceipt>{};

      for (final row in rows) {
        final meta = row.readTable(systemMetadata);
        if (uniqueReceipts.containsKey(meta.batchUuid)) continue;

        final sourcing = row.readTableOrNull(biomassSourcing);
        final pyro = row.readTableOrNull(pyrolysisTelemetry);
        final yield_ = row.readTableOrNull(yieldMetrics);

        int? samples;
        List<Map<String, dynamic>> parsedSmokeProofs = [];

        if (pyro?.temperatureReadingsJson != null) {
          try {
            final list = jsonDecode(pyro!.temperatureReadingsJson) as List;
            samples = list.length;
          } catch (_) {
            samples = 0;
          }
        }

        if (pyro?.smokeEvidenceJson != null) {
          try {
            final list = jsonDecode(pyro!.smokeEvidenceJson) as List;
            parsedSmokeProofs = list.whereType<Map<String, dynamic>>().toList();
          } catch (_) {}
        }

        uniqueReceipts[meta.batchUuid] = CryptographicReceipt(
          batchUuid: meta.batchUuid,
          artisanId: meta.artisanId,
          createdAt: meta.createdAt,
          feedstockSpecies: sourcing?.feedstockSpecies,
          moisturePercent: sourcing?.moisturePercent,
          biomassPhotoSha256: sourcing?.sha256Hash,
          biomassLat: sourcing?.latitude,
          biomassLon: sourcing?.longitude,
          burnStart: pyro?.burnStartTimestamp,
          burnEnd: pyro?.burnEndTimestamp,
          maxTemp: pyro?.maxTemp,
          minTemp: pyro?.minTemp,
          sampleCount: samples,
          smokeProofs: parsedSmokeProofs,
          yieldWeightKg: yield_?.wetYieldWeightKg,
        );
      }

      return uniqueReceipts.values.toList();
    });
  }
}
