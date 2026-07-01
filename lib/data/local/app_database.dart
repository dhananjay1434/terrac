import 'dart:convert';
import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqlcipher_flutter_libs/sqlcipher_flutter_libs.dart';
import 'package:sqlite3/open.dart';
import 'package:uuid/uuid.dart';

import 'passphrase_resolver.dart';
import 'tables.dart';
import 'wipe_context.dart';
import '../../services/crypto_signer.dart';
import '../../services/sync_queue_manager.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

part 'app_database.g.dart';

const _uuid = Uuid();

@DriftDatabase(
  tables: [
    SystemMetadata,
    BiomassSourcing,
    PyrolysisTelemetry,
    YieldMetrics,
    EndUseApplication,
    SyncOutbox,
    MediaCaptures,
  ],
)
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  /// Test-only constructor. Pass `NativeDatabase.memory()` from unit tests.
  AppDatabase.forTesting(super.executor);

  @override
  int get schemaVersion => 15;

  @override
  MigrationStrategy get migration => MigrationStrategy(
    onCreate: (m) async {
      await m.createAll();
      // P0-6: index must exist on fresh installs (also covered by v11->v12
      // upgrade path for existing devices). IF NOT EXISTS keeps both paths
      // idempotent if Drift's createAll ever emits it directly in future.
      await customStatement(
        'CREATE UNIQUE INDEX IF NOT EXISTS '
        'ux_media_captures_batch_type '
        'ON media_captures(batch_uuid, capture_type);',
      );
      await customStatement(
        'CREATE VIEW IF NOT EXISTS dashboard_stats_v AS '
        'SELECT '
        '(SELECT COUNT(*) FROM system_metadata) AS total_batches, '
        '(SELECT COUNT(*) FROM end_use_application) AS completed_batches, '
        '(SELECT COUNT(*) FROM sync_outbox WHERE status=\'PENDING\') AS pending_sync, '
        'COALESCE((SELECT SUM(wet_yield_weight_kg) FROM yield_metrics), 0.0) AS total_yield_kg;',
      );
    },
    onUpgrade: (m, from, to) async {
      if (from < 2) {
        // Schema v2: chain-of-custody columns on biomass_sourcing.
        await m.addColumn(biomassSourcing, biomassSourcing.photoPath);
        await m.addColumn(biomassSourcing, biomassSourcing.sha256Hash);
        await m.addColumn(biomassSourcing, biomassSourcing.latitude);
        await m.addColumn(biomassSourcing, biomassSourcing.longitude);
      }
      if (from < 3) {
        // Schema v3: mock_location_enabled column on biomass_sourcing.
        await m.addColumn(biomassSourcing, biomassSourcing.mockLocationEnabled);
      }
      if (from < 4) {
        // Schema v4: clock-spoof detection & farmer ID photo & sync logic.
        await m.addColumn(
          biomassSourcing,
          biomassSourcing.harvestUptimeSeconds,
        );
        await m.addColumn(endUseApplication, endUseApplication.farmerPhotoPath);
        await m.addColumn(
          endUseApplication,
          endUseApplication.farmerPhotoSha256,
        );
        await m.addColumn(syncOutbox, syncOutbox.jsonSyncedAt);
        await m.addColumn(syncOutbox, syncOutbox.mediaSyncedAt);
      }
      if (from < 6) {
        // Schema v6: multi-phasic smoke evidence (4 photos).

        await m.addColumn(
          pyrolysisTelemetry,
          pyrolysisTelemetry.smokeEvidenceJson,
        );
      }
      if (from < 7) {
        await m.createTable(mediaCaptures);
      }
      if (from < 8) {
        await m.addColumn(syncOutbox, syncOutbox.hmacSignature);
      }
      if (from < 9) {
        // Schema v9: Compass telemetry for Sybil attack defense.
        await m.addColumn(biomassSourcing, biomassSourcing.azimuth);
        await m.addColumn(biomassSourcing, biomassSourcing.pitch);
        await m.addColumn(biomassSourcing, biomassSourcing.roll);
        await m.addColumn(pyrolysisTelemetry, pyrolysisTelemetry.azimuth);
        await m.addColumn(pyrolysisTelemetry, pyrolysisTelemetry.pitch);
        await m.addColumn(pyrolysisTelemetry, pyrolysisTelemetry.roll);
      }
      if (from < 10) {
        // Schema v10: Hardware attestation blobs from ESP32 secure element.
        await m.addColumn(
          pyrolysisTelemetry,
          pyrolysisTelemetry.hwAttestationJson,
        );
      }
      if (from < 11) {
        // P1-17: normalise legacy timestamps to UTC ISO-8601 with explicit Z.
        await m.issueCustomQuery(
          "UPDATE biomass_sourcing "
          "SET harvest_timestamp = "
          "  CASE "
          "    WHEN harvest_timestamp LIKE '%Z' THEN harvest_timestamp "
          "    WHEN harvest_timestamp LIKE '%+%' OR harvest_timestamp LIKE '%-__:__' "
          "      THEN STRFTIME('%Y-%m-%dT%H:%M:%fZ', harvest_timestamp) "
          "    ELSE harvest_timestamp || 'Z' "
          "  END "
          "WHERE harvest_timestamp IS NOT NULL AND harvest_timestamp NOT LIKE '%Z';",
        );

        final prefs = await SharedPreferences.getInstance();
        final artisanId = prefs.getString('artisan_id') ?? 'UNKNOWN_ARTISAN';
        final deviceMac = prefs.getString('device_mac') ?? 'UNKNOWN_MAC';

        // Retroactively insert SystemMetadata for orphaned batches so they appear in Proof Wallet.
        // Parameterised to prevent SQL injection via SharedPreferences-stored identity.
        await m.issueCustomQuery(
          'INSERT OR IGNORE INTO system_metadata '
          '(batch_uuid, artisan_id, device_hardware_mac, app_build_version, sync_status, created_at) '
          'SELECT batch_uuid, ?, ?, ?, ?, MIN(harvest_timestamp) '
          'FROM biomass_sourcing GROUP BY batch_uuid',
          [artisanId, deviceMac, '3.0.0', 'PENDING'],
        );
      }
      if (from < 12) {
        await m.issueCustomQuery(
          'CREATE UNIQUE INDEX IF NOT EXISTS '
          'ux_media_captures_batch_type '
          'ON media_captures(batch_uuid, capture_type);',
        );
      }
      if (from < 15) {
        // P1-23: Add json_valid constraints to pyrolysis_telemetry.
        // TableMigration automatically performs the table-rewrite (temp table + insert + rename)
        // required by SQLite to add CHECK constraints.
        // ignore: experimental_member_use
        await m.alterTable(TableMigration(pyrolysisTelemetry));
      }
    },
  );

  // ---------------------------------------------------------------------------
  // Transactional Outbox helpers
  // ---------------------------------------------------------------------------

  /// Atomically inserts a [SystemMetadata] row AND a matching
  /// [SyncOutbox] event in a single transaction.
  Future<void> insertSystemMetadataWithOutbox(
    SystemMetadataCompanion meta,
  ) async {
    await transaction(() async {
      await into(systemMetadata).insert(meta);

      final payload = <String, dynamic>{
        'batch_uuid': meta.batchUuid.value,
        'artisan_id': meta.artisanId.value,
        'device_hardware_mac': meta.deviceHardwareMac.value,
        'app_build_version': meta.appBuildVersion.value,
        'sync_status': meta.syncStatus.present
            ? meta.syncStatus.value
            : 'PENDING',
        'created_at': meta.createdAt.value,
      };

      final jsonString = jsonEncode(payload);
      final signature = await CryptoSigner.signPayload(jsonString);

      await into(syncOutbox).insert(
        SyncOutboxCompanion.insert(
          operationId: _uuid.v4(),
          batchUuid: meta.batchUuid.value,
          targetTable: 'system_metadata',
          operationType: 'INSERT',
          payloadJson: jsonString,
          createdAt: DateTime.now().toUtc().toIso8601String(),
          hmacSignature: Value(signature),
        ),
      );
    });
  }

  /// Generic atomic writer used by domain repositories.
  Future<void> insertWithOutbox({
    required String batchUuid,
    required String targetTable,
    required Map<String, dynamic> payload,
    required Future<void> Function() insertRow,
  }) async {
    final jsonString = jsonEncode(payload);
    await transaction(() async {
      // P0-11: Sign inside the transaction to prevent key-rotation races with secureWipe.
      final signature = await CryptoSigner.signPayload(jsonString);
      await insertRow();
      await into(syncOutbox).insert(
        SyncOutboxCompanion.insert(
          operationId: _uuid.v4(),
          batchUuid: batchUuid,
          targetTable: targetTable,
          operationType: 'INSERT',
          payloadJson: jsonString,
          createdAt: DateTime.now().toUtc().toIso8601String(),
          hmacSignature: Value(signature),
        ),
      );
    });
  }

  // ---------------------------------------------------------------------------
  // Prompt 3 — BiomassSourcing convenience writer
  // ---------------------------------------------------------------------------

  /// Persists a [BiomassSourcing] row + matching SyncOutbox event atomically.
  /// Returns the freshly-minted `sourcingUuid` so the caller can log it.
  Future<String> insertBiomassSourcingWithOutbox({
    required String batchUuid,
    required String feedstockSpecies,
    required String harvestTimestamp,
    required double moisturePercent,
    required bool moistureCompliant,
    String? photoPath,
    String? sha256Hash,
    double? latitude,
    double? longitude,
    bool mockLocationEnabled = false,
    // Phase 6 Fix 3: device monotonic uptime at harvest — backend uses this
    int? harvestUptimeSeconds,
    // Phase 7: Compass telemetry
    double? azimuth,
    double? pitch,
    double? roll,
  }) async {
    final sourcingUuid = _uuid.v4();
    final companion = BiomassSourcingCompanion.insert(
      sourcingUuid: sourcingUuid,
      batchUuid: batchUuid,
      feedstockSpecies: feedstockSpecies,
      harvestTimestamp: harvestTimestamp,
      moisturePercent: moisturePercent,
      moistureCompliant: moistureCompliant,
      photoPath: Value(photoPath),
      sha256Hash: Value(sha256Hash),
      latitude: Value(latitude),
      longitude: Value(longitude),
      mockLocationEnabled: Value(mockLocationEnabled),
      harvestUptimeSeconds: Value(harvestUptimeSeconds),
      azimuth: Value(azimuth),
      pitch: Value(pitch),
      roll: Value(roll),
    );

    final payload = <String, dynamic>{
      'sourcing_uuid': sourcingUuid,
      'batch_uuid': batchUuid,
      'feedstock_species': feedstockSpecies,
      'harvest_timestamp': harvestTimestamp,
      'moisture_percent': moisturePercent,
      'moisture_compliant': moistureCompliant,
      'photo_path': photoPath,
      'sha256_hash': sha256Hash,
      'latitude': latitude,
      'longitude': longitude,
      'mock_location_enabled': mockLocationEnabled,
      // Include uptime in the outbox payload so the backend can cross-check.
      'harvest_uptime_seconds': harvestUptimeSeconds ?? 0,
      'azimuth': azimuth,
      'pitch': pitch,
      'roll': roll,
    };

    await insertWithOutbox(
      batchUuid: batchUuid,
      targetTable: 'biomass_sourcing',
      payload: payload,
      insertRow: () => into(biomassSourcing).insert(companion),
    );
    return sourcingUuid;
  }

  /// Raw parameterized telemetry query — TEST-ONLY. Gated behind
  /// [visibleForTesting] so it cannot be called from production code (Phase 12).
  /// Uses a bound variable (no string interpolation), so it is injection-safe.
  @visibleForTesting
  Future<List<QueryRow>> getBatchTelemetryRaw(String batchUuid) async {
    return await customSelect(
      'SELECT * FROM pyrolysis_telemetry WHERE batch_uuid = ?',
      variables: [Variable.withString(batchUuid)],
    ).get();
  }

  /// Securely erases all user data and key material. After this call the
  /// AppDatabase instance is closed; callers MUST `ref.invalidate(appDatabaseProvider)`.
  Future<void> secureWipe({required WipeContext ctx, required Ref ref}) async {
    ref.invalidate(syncQueueManagerProvider);
    await customStatement('PRAGMA secure_delete = ON;');
    await transaction(() async {
      await delete(systemMetadata).go();
      await delete(biomassSourcing).go();
      await delete(pyrolysisTelemetry).go();
      await delete(yieldMetrics).go();
      await delete(endUseApplication).go();
      await delete(syncOutbox).go();
      await delete(mediaCaptures).go();
    });
    await customStatement('VACUUM;');
    await close();

    final dir = await ctx.getDocsDir();
    for (final suffix in const ['', '-wal', '-shm', '-journal']) {
      final f = File(p.join(dir.path, '$_kDbFileName$suffix'));
      if (await f.exists()) {
        await f.delete();
      }
    }

    await ctx.deleteSecureKey(kDbPassphraseKey);
    await ctx.clearHmacKey();
  }
}

/// =============================================================================
/// SQLCipher-backed connection  (Phase 6 — Encryption at rest + Keystore)
/// =============================================================================
/// All on-device data (PII, GPS, photo paths, SHA-256 evidence) is AES-256
/// encrypted using SQLCipher. The passphrase is a 256-bit base64url value
/// generated on first launch and stored in the hardware-backed
/// flutter_secure_storage (Android Keystore / iOS Keychain).
///
/// MIGRATION: Devices with a legacy passphrase in SharedPreferences are
/// silently migrated on first launch — the plaintext copy is then scrubbed.
/// DO NOT store the passphrase in SharedPreferences.
/// =============================================================================

const _kDbFileName = 'dmrv_encrypted.sqlite';

/// Hardware-backed storage (Android Keystore / iOS Keychain).
/// encryptedSharedPreferences: true ensures the backing XML is itself
/// encrypted by the Jetpack EncryptedSharedPreferences layer on Android < 9.
const _secureStorage = FlutterSecureStorage(
  aOptions: AndroidOptions(encryptedSharedPreferences: true),
);

/// Thin wrapper over the public, testable [resolveOrCreatePassphrase] in
/// `passphrase_resolver.dart`. Production code uses this; tests import the
/// public function directly so they exercise the exact same logic.
Future<String> _resolveOrCreatePassphrase() async {
  final prefs = await SharedPreferences.getInstance();
  return resolveOrCreatePassphrase(secureStorage: _secureStorage, prefs: prefs);
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    if (!kIsWeb && Platform.isAndroid) {
      await applyWorkaroundToOpenSqlCipherOnOldAndroidVersions();
    }
    // On Android we MUST route sqlite3 through the SQLCipher .so shipped by
    // sqlcipher_flutter_libs. On iOS / macOS the package statically links
    // SQLCipher into the app binary so no override is needed.
    if (!kIsWeb && Platform.isAndroid) {
      open.overrideFor(OperatingSystem.android, openCipherOnAndroid);
    }

    final passphrase = await _resolveOrCreatePassphrase();
    final dir = await getApplicationDocumentsDirectory();
    final file = File(p.join(dir.path, _kDbFileName));

    return NativeDatabase.createInBackground(
      file,
      isolateSetup: () async {
        if (!kIsWeb && Platform.isAndroid) {
          open.overrideFor(OperatingSystem.android, openCipherOnAndroid);
        }
      },
      setup: (rawDb) {
        // P0-9: Prevent SQL injection without triggering an encrypted read.
        // We cannot use rawDb.select('SELECT quote(?)') here because the database
        // is encrypted and cannot prepare statements until PRAGMA key is set!
        final escapedPassphrase = passphrase.replaceAll("'", "''");
        rawDb.execute("PRAGMA key = '$escapedPassphrase';");
        // Force a decrypt pass so a bad key fails fast at open-time.
        rawDb.execute('SELECT count(*) FROM sqlite_master;');

        // P0-5: Enforce relational integrity
        rawDb.execute('PRAGMA foreign_keys = ON;');
      },
    );
  });
}
