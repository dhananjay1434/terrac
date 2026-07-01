library;

import 'dart:convert';

/// Yield & EndUseApplication transactional outbox writers. Kept in a separate
/// file so the generated `.g.dart` from earlier prompts doesn't need to be
/// regenerated *just* for these helpers — only when the underlying Drift
/// tables themselves change (Prompt 5 → schema v4 adds farmer-photo cols).

import 'package:drift/drift.dart';
import 'package:uuid/uuid.dart';

import 'app_database.dart';

const _uuid = Uuid();

extension YieldWriter on AppDatabase {
  /// Atomically inserts a YieldMetrics row + SyncOutbox event.
  Future<String> insertYieldMetricsWithOutbox({
    required String batchUuid,
    required String quenchMethodology,
    required double grossVolume,
    required double wetYieldWeightKg,
    double? dryYieldWeightKg,
  }) async {
    if (grossVolume < 0) {
      throw ArgumentError.value(
        grossVolume,
        'grossVolume',
        'Cannot be negative',
      );
    }
    if (wetYieldWeightKg < 0) {
      throw ArgumentError.value(
        wetYieldWeightKg,
        'wetYieldWeightKg',
        'Cannot be negative',
      );
    }

    final yieldUuid = _uuid.v4();

    final companion = YieldMetricsCompanion.insert(
      yieldUuid: yieldUuid,
      batchUuid: batchUuid,
      quenchMethodology: quenchMethodology,
      grossVolume: grossVolume,
      wetYieldWeightKg: wetYieldWeightKg,
      dryYieldWeightKg: Value(dryYieldWeightKg),
    );

    final payload = <String, dynamic>{
      'yield_uuid': yieldUuid,
      'batch_uuid': batchUuid,
      'quench_methodology': quenchMethodology,
      'gross_volume': grossVolume,
      'wet_yield_weight_kg': wetYieldWeightKg,
      'dry_yield_weight_kg': dryYieldWeightKg,
    };

    await insertWithOutbox(
      batchUuid: batchUuid,
      targetTable: 'yield_metrics',
      payload: payload,
      insertRow: () => into(yieldMetrics).insert(companion),
    );
    return yieldUuid;
  }
}

extension EndUseWriter on AppDatabase {
  /// Atomically inserts an EndUseApplication row + SyncOutbox event.
  /// `applicationMethodology` is a controlled vocabulary, e.g.:
  ///   "SURFACE_BROADCAST" | "ROOT_ZONE_TRENCHING" | "BANDED_INCORPORATION"
  Future<String> insertEndUseWithOutbox({
    required String batchUuid,
    required String applicationMethodology,
    required double applicationRateTonnes,
    required double transportDistanceKm,
    required double latitude,
    required double longitude,
    String? farmerPhotoPath,
    String? farmerPhotoSha256,
  }) async {
    final applicationUuid = _uuid.v4();

    final companion = EndUseApplicationCompanion.insert(
      applicationUuid: applicationUuid,
      batchUuid: batchUuid,
      applicationMethodology: applicationMethodology,
      applicationRate: applicationRateTonnes,
      transportDistanceKm: transportDistanceKm,
      latitude: Value(latitude),
      longitude: Value(longitude),
      farmerPhotoPath: Value(farmerPhotoPath),
      farmerPhotoSha256: Value(farmerPhotoSha256),
    );

    final payload = <String, dynamic>{
      'application_uuid': applicationUuid,
      'batch_uuid': batchUuid,
      'application_methodology': applicationMethodology,
      'application_rate_tonnes': applicationRateTonnes,
      'transport_distance_km': transportDistanceKm,
      'latitude': latitude,
      'longitude': longitude,
      'farmer_photo_path': farmerPhotoPath,
      'farmer_photo_sha256': farmerPhotoSha256,
    };

    await insertWithOutbox(
      batchUuid: batchUuid,
      targetTable: 'end_use_application',
      payload: payload,
      insertRow: () => into(endUseApplication).insert(companion),
    );
    return applicationUuid;
  }

  /// Convenience: marks the batch's [SystemMetadata.syncStatus] to
  /// CLOSED_PENDING_UPLOAD once an EndUse row has been written. Best-effort —
  /// silently no-ops if no metadata row exists.
  Future<void> closeBatch(String batchUuid) async {
    await transaction(() async {
      final exists = await (select(
        systemMetadata,
      )..where((t) => t.batchUuid.equals(batchUuid))).getSingleOrNull();
      if (exists == null) return;
      await (update(
        systemMetadata,
      )..where((t) => t.batchUuid.equals(batchUuid))).write(
        const SystemMetadataCompanion(
          syncStatus: Value('CLOSED_PENDING_UPLOAD'),
        ),
      );
    });
  }
}

/// Lightweight JSON helper kept here to avoid circular imports.
String encodePayload(Map<String, dynamic> m) => jsonEncode(m);
