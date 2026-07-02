import 'package:drift/drift.dart';

/// =============================================================================
/// Kon-Tiki Biochar dMRV — Local Drift Schema  (schemaVersion = 21)
/// =============================================================================
///
/// The authoritative version is `AppDatabase.schemaVersion` (currently 21). Keep
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
///   v16:            kiln_type + kiln_id on pyrolysis_telemetry (Rainbow C0).
///   v17:            biomass_input_kg + biomass_measurement_method on biomass_sourcing (Rainbow C1).
///   v18:            moisture_readings table — per-reading moisture + photo (Rainbow C2).
///   v19:            flame_height_m + ignition_energy_type/amount on pyrolysis_telemetry (Rainbow C3/C3b).
///   v20:            composite_pile_samples table — site composite sub-sample + photo (Rainbow C4).
///   v21:            delivery + buyer identity on end_use_application (Rainbow C5).
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

  // ---------- v17 biomass input (Rainbow compliance C1) ----------
  /// Mass of biomass fed to the kiln (kg). Methodology requires the biomass
  /// AMOUNT, either directly weighed or derived via a yield-conversion ratio.
  RealColumn get biomassInputKg => real().nullable()();

  /// 'direct_weigh' | 'yield_conversion'.
  TextColumn get biomassMeasurementMethod => text().nullable()();

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

  // ---------- v16 kiln registry (Rainbow compliance C0) ----------
  /// 'open' | 'closed'. The Rainbow methodology branches on kiln type (ignition
  /// energy, pyrolysis-photo requirements, PAH). Nullable for backward compat.
  TextColumn get kilnType => text().nullable()();

  /// Stable kiln identifier / QR (links a run to the project kiln registry).
  TextColumn get kilnId => text().nullable()();

  // ---------- v19 pyrolysis evidence (Rainbow compliance C3 / C3b) ----------
  /// Measured flame height (m); open-kiln methodology requires < 0.5 m.
  RealColumn get flameHeightM => real().nullable()();

  /// Ignition energy inputs — closed-kiln only (type + amount incl. syngas).
  TextColumn get ignitionEnergyType => text().nullable()();
  RealColumn get ignitionEnergyAmount => real().nullable()();

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

  // ---------- v21 delivery + buyer identity (Rainbow compliance C5) ----------
  /// When the biochar was delivered to the end user (ISO-8601 UTC).
  TextColumn get deliveryDate => text().nullable()();

  /// Mass delivered (kg) — the delivery-tracking amount for this batch.
  RealColumn get deliveredAmountKg => real().nullable()();

  /// Buyer / end-user identity. PII — lives only in the SQLCipher DB and is
  /// scrubbed by secureWipe.
  TextColumn get buyerName => text().nullable()();
  TextColumn get buyerContact => text().nullable()();

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

/// v18 — Rainbow compliance C2: individual moisture-meter readings.
/// The methodology requires ≥1 reading per 100 kg of biomass, min 10 per run,
/// EACH with a photo. One row per reading (not a single summary value).
class MoistureReadings extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get readingUuid => text()();
  TextColumn get batchUuid => text().references(SystemMetadata, #batchUuid)();
  RealColumn get moisturePercent => real()();

  /// Ordinal within the run (1..N). Unique per batch so retakes don't duplicate.
  IntColumn get sequence => integer()();

  /// Sandboxed photo of the meter reading + its SHA-256 (uploaded via /media).
  TextColumn get sandboxPath => text().nullable()();
  TextColumn get sha256Hash => text().nullable()();
  TextColumn get createdAt => text()();

  @override
  List<Set<Column>> get uniqueKeys => [
    {readingUuid},
    {batchUuid, sequence},
  ];
}

/// v20 — Rainbow compliance C4: site composite pile sub-sample.
/// The methodology requires a biochar sub-sample set aside per run, tagged with
/// date/time, GPS, the kiln ID/QR and batch ID/QR, and photographed. One row per
/// sub-sample (many per batch); the photo rides the existing signed /media path.
class CompositePileSamples extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get sampleUuid => text()();
  TextColumn get batchUuid => text().references(SystemMetadata, #batchUuid)();

  /// When the sub-sample was set aside (ISO-8601 UTC).
  TextColumn get sampledAt => text().nullable()();

  /// Location where the sub-sample was taken.
  RealColumn get latitude => real().nullable()();
  RealColumn get longitude => real().nullable()();

  /// Kiln ID/QR and batch ID/QR scanned at sampling (chain-of-custody linkage).
  TextColumn get kilnQr => text().nullable()();
  TextColumn get batchQr => text().nullable()();

  /// Sandboxed photo of the sub-sample + its SHA-256 (uploaded via /media).
  TextColumn get sandboxPath => text().nullable()();
  TextColumn get sha256Hash => text().nullable()();
  TextColumn get createdAt => text()();

  @override
  List<Set<Column>> get uniqueKeys => [
    {sampleUuid},
  ];
}
