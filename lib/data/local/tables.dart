import 'package:drift/drift.dart';

/// =============================================================================
/// Kon-Tiki Biochar dMRV — Local Drift Schema  (schemaVersion = 15)
/// =============================================================================
///
/// The authoritative version is `AppDatabase.schemaVersion` (currently 15). Keep
/// this header in sync with it. `onUpgrade` applies cumulative `if (from < N)`
/// blocks, so v5, v13 and v14 have no dedicated block (nothing new landed there).
///
/// Design notes
///   • All primary/foreign keys are UUID v4 strings (offline-collision-safe).
///   • Timestamps are stored as ISO-8601 UTC strings (portable across registries).
///   • Temperature arrays are persisted as JSON-encoded text (Drift has no
///     first-class list column on SQLite).
///   • Every primary-table insert is paired with a `SyncOutbox` row in a single
///     atomic transaction (Transactional Outbox Pattern).
///
/// Migration history (see AppDatabase.migration):
///   v2  (Prompt 3): chain-of-custody photo evidence columns.
///   v3  (Prompt 5): mock_location_enabled column.
///   v4  (Phase 6):  harvest_uptime_seconds + farmer photo cols + json_synced_at
///                   + media_synced_at (clock-spoof detection, two-phase commit).
///   v6:             smoke_evidence_json (multi-phasic smoke evidence).
///   v7:             media_captures table.
///   v8:             sync_outbox.hmac_signature.
///   v9:             compass telemetry (azimuth/pitch/roll) on biomass_sourcing
///                   and pyrolysis_telemetry (Sybil-attack defence).
///   v10:            pyrolysis_telemetry.hw_attestation_json.
///   v11:            legacy timestamp → UTC-Z normalization; orphan-batch metadata
///                   backfill (data migration).
///   v12:            unique index ux_media_captures_batch_type.
///   v15:            json_valid CHECK constraints on pyrolysis_telemetry.
/// =============================================================================

class SystemMetadata extends Table {
  TextColumn get batchUuid => text()();
  TextColumn get artisanId => text()();
  TextColumn get deviceHardwareMac => text()();
  TextColumn get appBuildVersion => text()();
  TextColumn get syncStatus => text().withDefault(const Constant('PENDING'))();
  TextColumn get createdAt => text()();

  @override
  Set<Column> get primaryKey => {batchUuid};
}

/// Documents additionality, origin, initial material properties, AND the
/// SHA-256-anchored photo evidence of the moisture-meter reading.
class BiomassSourcing extends Table {
  TextColumn get sourcingUuid => text()();
  TextColumn get batchUuid => text().references(SystemMetadata, #batchUuid)();
  TextColumn get feedstockSpecies => text()();
  TextColumn get harvestTimestamp => text()();
  RealColumn get moisturePercent => real()();
  BoolColumn get moistureCompliant => boolean()();

  // ---------- v2 chain-of-custody evidence ----------
  TextColumn get photoPath => text().nullable()();
  TextColumn get sha256Hash => text().nullable()();
  RealColumn get latitude => real().nullable()();
  RealColumn get longitude => real().nullable()();
  BoolColumn get mockLocationEnabled =>
      boolean().withDefault(const Constant(false))();

  // ---------- v4 clock-spoof defence ----------
  /// Device monotonic uptime in seconds at the moment the artisan tapped
  /// "LOG HARVEST NOW". The backend cross-checks this against the wall-clock
  /// delta. If the wall clock was advanced manually, the uptime delta will
  /// be much smaller and the sync will be rejected with DRYING_MANDATE_NOT_MET.
  IntColumn get harvestUptimeSeconds => integer().nullable()();

  // ---------- v9 compass telemetry ----------
  RealColumn get azimuth => real().nullable()();
  RealColumn get pitch => real().nullable()();
  RealColumn get roll => real().nullable()();

  @override
  Set<Column> get primaryKey => {sourcingUuid};

  @override
  List<Set<Column>> get uniqueKeys => [
    {batchUuid},
  ];
}

class PyrolysisTelemetry extends Table {
  TextColumn get telemetryUuid => text()();
  TextColumn get batchUuid => text().references(SystemMetadata, #batchUuid)();
  RealColumn get kilnGrossCapacity => real()();
  TextColumn get burnStartTimestamp => text()();
  TextColumn get burnEndTimestamp => text().nullable()();
  RealColumn get minTemp => real()();
  RealColumn get maxTemp => real()();
  TextColumn get temperatureReadingsJson =>
      text().withDefault(const Constant('[]'))();

  // ---------- v6 multi-phasic smoke photo evidence ----------
  TextColumn get smokeEvidenceJson =>
      text().withDefault(const Constant('[]'))();

  // ---------- v9 compass telemetry ----------
  RealColumn get azimuth => real().nullable()();
  RealColumn get pitch => real().nullable()();
  RealColumn get roll => real().nullable()();

  // ---------- v10 hardware attestation ----------
  /// JSON array of base64-encoded ECDSA attestation blobs from the ESP32
  /// secure element. Each blob is 80 bytes: deviceId(4) + seq(4) + ts(4) +
  /// temp(4) + ecdsaSig(64). The server verifies each signature against the
  /// device's registered public key.
  TextColumn get hwAttestationJson =>
      text().withDefault(const Constant('[]'))();

  @override
  Set<Column> get primaryKey => {telemetryUuid};

  @override
  List<Set<Column>> get uniqueKeys => [
    {batchUuid},
  ];

  @override
  List<String> get customConstraints => const [
    "CHECK (json_valid(temperature_readings_json))",
    "CHECK (json_valid(smoke_evidence_json))",
    "CHECK (json_valid(hw_attestation_json))",
  ];
}

class YieldMetrics extends Table {
  TextColumn get yieldUuid => text()();
  TextColumn get batchUuid => text().references(SystemMetadata, #batchUuid)();
  TextColumn get quenchMethodology => text()();
  RealColumn get grossVolume => real()();
  RealColumn get wetYieldWeightKg => real()();
  RealColumn get dryYieldWeightKg => real().nullable()();

  @override
  Set<Column> get primaryKey => {yieldUuid};

  @override
  List<Set<Column>> get uniqueKeys => [
    {batchUuid},
  ];
}

class EndUseApplication extends Table {
  TextColumn get applicationUuid => text()();
  TextColumn get batchUuid => text().references(SystemMetadata, #batchUuid)();
  TextColumn get applicationMethodology => text()();
  RealColumn get applicationRate => real()();
  RealColumn get transportDistanceKm => real()();
  RealColumn get latitude => real().nullable()();
  RealColumn get longitude => real().nullable()();

  // ---------- v4 chain-of-custody evidence (farmer ID photo) ----------
  TextColumn get farmerPhotoPath => text().nullable()();
  TextColumn get farmerPhotoSha256 => text().nullable()();

  @override
  Set<Column> get primaryKey => {applicationUuid};

  @override
  List<Set<Column>> get uniqueKeys => [
    {batchUuid},
  ];
}

class SyncOutbox extends Table {
  TextColumn get operationId => text()();
  TextColumn get batchUuid => text()();
  TextColumn get targetTable => text()();
  TextColumn get operationType => text()();
  TextColumn get payloadJson => text()();
  TextColumn get status => text().withDefault(const Constant('PENDING'))();
  IntColumn get retryCount => integer().withDefault(const Constant(0))();
  TextColumn get createdAt => text()();
  TextColumn get lastAttemptAt => text().nullable()();

  // ---------- v4 two-phase sync commit ----------
  /// Set when the JSON metadata POST is confirmed by the server (200 or 409).
  TextColumn get jsonSyncedAt => text().nullable()();

  /// Set when the media multipart POST is confirmed AND server hash matches.
  TextColumn get mediaSyncedAt => text().nullable()();

  // ---------- v8 HMAC payload signing ----------
  /// HMAC-SHA256 of payloadJson, calculated at the exact moment of insertion.
  /// If a hacker tampers with payloadJson after insertion, this column will
  /// no longer match and the server will reject the upload.
  TextColumn get hmacSignature => text().nullable()();

  @override
  Set<Column> get primaryKey => {operationId};
}

class MediaCaptures extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get batchUuid => text().references(SystemMetadata, #batchUuid)();
  TextColumn get captureType => text()();
  TextColumn get sandboxPath => text()();
  TextColumn get sha256Hash => text()();
  BoolColumn get isMockLocation =>
      boolean().withDefault(const Constant(false))();
  TextColumn get createdAt => text()();

  @override
  List<Set<Column>> get uniqueKeys => [
    {batchUuid, captureType},
  ];
}
