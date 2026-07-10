// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'app_database.dart';

// ignore_for_file: type=lint
class $SystemMetadataTable extends SystemMetadata
    with TableInfo<$SystemMetadataTable, SystemMetadataData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $SystemMetadataTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _batchUuidMeta = const VerificationMeta(
    'batchUuid',
  );
  @override
  late final GeneratedColumn<String> batchUuid = GeneratedColumn<String>(
    'batch_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _artisanIdMeta = const VerificationMeta(
    'artisanId',
  );
  @override
  late final GeneratedColumn<String> artisanId = GeneratedColumn<String>(
    'artisan_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _deviceHardwareMacMeta = const VerificationMeta(
    'deviceHardwareMac',
  );
  @override
  late final GeneratedColumn<String> deviceHardwareMac =
      GeneratedColumn<String>(
        'device_hardware_mac',
        aliasedName,
        false,
        type: DriftSqlType.string,
        requiredDuringInsert: true,
      );
  static const VerificationMeta _appBuildVersionMeta = const VerificationMeta(
    'appBuildVersion',
  );
  @override
  late final GeneratedColumn<String> appBuildVersion = GeneratedColumn<String>(
    'app_build_version',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _syncStatusMeta = const VerificationMeta(
    'syncStatus',
  );
  @override
  late final GeneratedColumn<String> syncStatus = GeneratedColumn<String>(
    'sync_status',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant('PENDING'),
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    batchUuid,
    artisanId,
    deviceHardwareMac,
    appBuildVersion,
    syncStatus,
    createdAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'system_metadata';
  @override
  VerificationContext validateIntegrity(
    Insertable<SystemMetadataData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('batch_uuid')) {
      context.handle(
        _batchUuidMeta,
        batchUuid.isAcceptableOrUnknown(data['batch_uuid']!, _batchUuidMeta),
      );
    } else if (isInserting) {
      context.missing(_batchUuidMeta);
    }
    if (data.containsKey('artisan_id')) {
      context.handle(
        _artisanIdMeta,
        artisanId.isAcceptableOrUnknown(data['artisan_id']!, _artisanIdMeta),
      );
    } else if (isInserting) {
      context.missing(_artisanIdMeta);
    }
    if (data.containsKey('device_hardware_mac')) {
      context.handle(
        _deviceHardwareMacMeta,
        deviceHardwareMac.isAcceptableOrUnknown(
          data['device_hardware_mac']!,
          _deviceHardwareMacMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_deviceHardwareMacMeta);
    }
    if (data.containsKey('app_build_version')) {
      context.handle(
        _appBuildVersionMeta,
        appBuildVersion.isAcceptableOrUnknown(
          data['app_build_version']!,
          _appBuildVersionMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_appBuildVersionMeta);
    }
    if (data.containsKey('sync_status')) {
      context.handle(
        _syncStatusMeta,
        syncStatus.isAcceptableOrUnknown(data['sync_status']!, _syncStatusMeta),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {batchUuid};
  @override
  SystemMetadataData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return SystemMetadataData(
      batchUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}batch_uuid'],
      )!,
      artisanId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}artisan_id'],
      )!,
      deviceHardwareMac: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}device_hardware_mac'],
      )!,
      appBuildVersion: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}app_build_version'],
      )!,
      syncStatus: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sync_status'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $SystemMetadataTable createAlias(String alias) {
    return $SystemMetadataTable(attachedDatabase, alias);
  }
}

class SystemMetadataData extends DataClass
    implements Insertable<SystemMetadataData> {
  final String batchUuid;
  final String artisanId;
  final String deviceHardwareMac;
  final String appBuildVersion;
  final String syncStatus;
  final String createdAt;
  const SystemMetadataData({
    required this.batchUuid,
    required this.artisanId,
    required this.deviceHardwareMac,
    required this.appBuildVersion,
    required this.syncStatus,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['batch_uuid'] = Variable<String>(batchUuid);
    map['artisan_id'] = Variable<String>(artisanId);
    map['device_hardware_mac'] = Variable<String>(deviceHardwareMac);
    map['app_build_version'] = Variable<String>(appBuildVersion);
    map['sync_status'] = Variable<String>(syncStatus);
    map['created_at'] = Variable<String>(createdAt);
    return map;
  }

  SystemMetadataCompanion toCompanion(bool nullToAbsent) {
    return SystemMetadataCompanion(
      batchUuid: Value(batchUuid),
      artisanId: Value(artisanId),
      deviceHardwareMac: Value(deviceHardwareMac),
      appBuildVersion: Value(appBuildVersion),
      syncStatus: Value(syncStatus),
      createdAt: Value(createdAt),
    );
  }

  factory SystemMetadataData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return SystemMetadataData(
      batchUuid: serializer.fromJson<String>(json['batchUuid']),
      artisanId: serializer.fromJson<String>(json['artisanId']),
      deviceHardwareMac: serializer.fromJson<String>(json['deviceHardwareMac']),
      appBuildVersion: serializer.fromJson<String>(json['appBuildVersion']),
      syncStatus: serializer.fromJson<String>(json['syncStatus']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'batchUuid': serializer.toJson<String>(batchUuid),
      'artisanId': serializer.toJson<String>(artisanId),
      'deviceHardwareMac': serializer.toJson<String>(deviceHardwareMac),
      'appBuildVersion': serializer.toJson<String>(appBuildVersion),
      'syncStatus': serializer.toJson<String>(syncStatus),
      'createdAt': serializer.toJson<String>(createdAt),
    };
  }

  SystemMetadataData copyWith({
    String? batchUuid,
    String? artisanId,
    String? deviceHardwareMac,
    String? appBuildVersion,
    String? syncStatus,
    String? createdAt,
  }) => SystemMetadataData(
    batchUuid: batchUuid ?? this.batchUuid,
    artisanId: artisanId ?? this.artisanId,
    deviceHardwareMac: deviceHardwareMac ?? this.deviceHardwareMac,
    appBuildVersion: appBuildVersion ?? this.appBuildVersion,
    syncStatus: syncStatus ?? this.syncStatus,
    createdAt: createdAt ?? this.createdAt,
  );
  SystemMetadataData copyWithCompanion(SystemMetadataCompanion data) {
    return SystemMetadataData(
      batchUuid: data.batchUuid.present ? data.batchUuid.value : this.batchUuid,
      artisanId: data.artisanId.present ? data.artisanId.value : this.artisanId,
      deviceHardwareMac: data.deviceHardwareMac.present
          ? data.deviceHardwareMac.value
          : this.deviceHardwareMac,
      appBuildVersion: data.appBuildVersion.present
          ? data.appBuildVersion.value
          : this.appBuildVersion,
      syncStatus: data.syncStatus.present
          ? data.syncStatus.value
          : this.syncStatus,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('SystemMetadataData(')
          ..write('batchUuid: $batchUuid, ')
          ..write('artisanId: $artisanId, ')
          ..write('deviceHardwareMac: $deviceHardwareMac, ')
          ..write('appBuildVersion: $appBuildVersion, ')
          ..write('syncStatus: $syncStatus, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    batchUuid,
    artisanId,
    deviceHardwareMac,
    appBuildVersion,
    syncStatus,
    createdAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is SystemMetadataData &&
          other.batchUuid == this.batchUuid &&
          other.artisanId == this.artisanId &&
          other.deviceHardwareMac == this.deviceHardwareMac &&
          other.appBuildVersion == this.appBuildVersion &&
          other.syncStatus == this.syncStatus &&
          other.createdAt == this.createdAt);
}

class SystemMetadataCompanion extends UpdateCompanion<SystemMetadataData> {
  final Value<String> batchUuid;
  final Value<String> artisanId;
  final Value<String> deviceHardwareMac;
  final Value<String> appBuildVersion;
  final Value<String> syncStatus;
  final Value<String> createdAt;
  final Value<int> rowid;
  const SystemMetadataCompanion({
    this.batchUuid = const Value.absent(),
    this.artisanId = const Value.absent(),
    this.deviceHardwareMac = const Value.absent(),
    this.appBuildVersion = const Value.absent(),
    this.syncStatus = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  SystemMetadataCompanion.insert({
    required String batchUuid,
    required String artisanId,
    required String deviceHardwareMac,
    required String appBuildVersion,
    this.syncStatus = const Value.absent(),
    required String createdAt,
    this.rowid = const Value.absent(),
  }) : batchUuid = Value(batchUuid),
       artisanId = Value(artisanId),
       deviceHardwareMac = Value(deviceHardwareMac),
       appBuildVersion = Value(appBuildVersion),
       createdAt = Value(createdAt);
  static Insertable<SystemMetadataData> custom({
    Expression<String>? batchUuid,
    Expression<String>? artisanId,
    Expression<String>? deviceHardwareMac,
    Expression<String>? appBuildVersion,
    Expression<String>? syncStatus,
    Expression<String>? createdAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (batchUuid != null) 'batch_uuid': batchUuid,
      if (artisanId != null) 'artisan_id': artisanId,
      if (deviceHardwareMac != null) 'device_hardware_mac': deviceHardwareMac,
      if (appBuildVersion != null) 'app_build_version': appBuildVersion,
      if (syncStatus != null) 'sync_status': syncStatus,
      if (createdAt != null) 'created_at': createdAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  SystemMetadataCompanion copyWith({
    Value<String>? batchUuid,
    Value<String>? artisanId,
    Value<String>? deviceHardwareMac,
    Value<String>? appBuildVersion,
    Value<String>? syncStatus,
    Value<String>? createdAt,
    Value<int>? rowid,
  }) {
    return SystemMetadataCompanion(
      batchUuid: batchUuid ?? this.batchUuid,
      artisanId: artisanId ?? this.artisanId,
      deviceHardwareMac: deviceHardwareMac ?? this.deviceHardwareMac,
      appBuildVersion: appBuildVersion ?? this.appBuildVersion,
      syncStatus: syncStatus ?? this.syncStatus,
      createdAt: createdAt ?? this.createdAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (batchUuid.present) {
      map['batch_uuid'] = Variable<String>(batchUuid.value);
    }
    if (artisanId.present) {
      map['artisan_id'] = Variable<String>(artisanId.value);
    }
    if (deviceHardwareMac.present) {
      map['device_hardware_mac'] = Variable<String>(deviceHardwareMac.value);
    }
    if (appBuildVersion.present) {
      map['app_build_version'] = Variable<String>(appBuildVersion.value);
    }
    if (syncStatus.present) {
      map['sync_status'] = Variable<String>(syncStatus.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('SystemMetadataCompanion(')
          ..write('batchUuid: $batchUuid, ')
          ..write('artisanId: $artisanId, ')
          ..write('deviceHardwareMac: $deviceHardwareMac, ')
          ..write('appBuildVersion: $appBuildVersion, ')
          ..write('syncStatus: $syncStatus, ')
          ..write('createdAt: $createdAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $BiomassSourcingTable extends BiomassSourcing
    with TableInfo<$BiomassSourcingTable, BiomassSourcingData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $BiomassSourcingTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _sourcingUuidMeta = const VerificationMeta(
    'sourcingUuid',
  );
  @override
  late final GeneratedColumn<String> sourcingUuid = GeneratedColumn<String>(
    'sourcing_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _batchUuidMeta = const VerificationMeta(
    'batchUuid',
  );
  @override
  late final GeneratedColumn<String> batchUuid = GeneratedColumn<String>(
    'batch_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES system_metadata (batch_uuid)',
    ),
  );
  static const VerificationMeta _feedstockSpeciesMeta = const VerificationMeta(
    'feedstockSpecies',
  );
  @override
  late final GeneratedColumn<String> feedstockSpecies = GeneratedColumn<String>(
    'feedstock_species',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _harvestTimestampMeta = const VerificationMeta(
    'harvestTimestamp',
  );
  @override
  late final GeneratedColumn<String> harvestTimestamp = GeneratedColumn<String>(
    'harvest_timestamp',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _moisturePercentMeta = const VerificationMeta(
    'moisturePercent',
  );
  @override
  late final GeneratedColumn<double> moisturePercent = GeneratedColumn<double>(
    'moisture_percent',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _moistureCompliantMeta = const VerificationMeta(
    'moistureCompliant',
  );
  @override
  late final GeneratedColumn<bool> moistureCompliant = GeneratedColumn<bool>(
    'moisture_compliant',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("moisture_compliant" IN (0, 1))',
    ),
  );
  static const VerificationMeta _photoPathMeta = const VerificationMeta(
    'photoPath',
  );
  @override
  late final GeneratedColumn<String> photoPath = GeneratedColumn<String>(
    'photo_path',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _sha256HashMeta = const VerificationMeta(
    'sha256Hash',
  );
  @override
  late final GeneratedColumn<String> sha256Hash = GeneratedColumn<String>(
    'sha256_hash',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _latitudeMeta = const VerificationMeta(
    'latitude',
  );
  @override
  late final GeneratedColumn<double> latitude = GeneratedColumn<double>(
    'latitude',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _longitudeMeta = const VerificationMeta(
    'longitude',
  );
  @override
  late final GeneratedColumn<double> longitude = GeneratedColumn<double>(
    'longitude',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _mockLocationEnabledMeta =
      const VerificationMeta('mockLocationEnabled');
  @override
  late final GeneratedColumn<bool> mockLocationEnabled = GeneratedColumn<bool>(
    'mock_location_enabled',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("mock_location_enabled" IN (0, 1))',
    ),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _harvestUptimeSecondsMeta =
      const VerificationMeta('harvestUptimeSeconds');
  @override
  late final GeneratedColumn<int> harvestUptimeSeconds = GeneratedColumn<int>(
    'harvest_uptime_seconds',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _azimuthMeta = const VerificationMeta(
    'azimuth',
  );
  @override
  late final GeneratedColumn<double> azimuth = GeneratedColumn<double>(
    'azimuth',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _pitchMeta = const VerificationMeta('pitch');
  @override
  late final GeneratedColumn<double> pitch = GeneratedColumn<double>(
    'pitch',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _rollMeta = const VerificationMeta('roll');
  @override
  late final GeneratedColumn<double> roll = GeneratedColumn<double>(
    'roll',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _biomassInputKgMeta = const VerificationMeta(
    'biomassInputKg',
  );
  @override
  late final GeneratedColumn<double> biomassInputKg = GeneratedColumn<double>(
    'biomass_input_kg',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _biomassMeasurementMethodMeta =
      const VerificationMeta('biomassMeasurementMethod');
  @override
  late final GeneratedColumn<String> biomassMeasurementMethod =
      GeneratedColumn<String>(
        'biomass_measurement_method',
        aliasedName,
        true,
        type: DriftSqlType.string,
        requiredDuringInsert: false,
      );
  static const VerificationMeta _projectIdMeta = const VerificationMeta(
    'projectId',
  );
  @override
  late final GeneratedColumn<String> projectId = GeneratedColumn<String>(
    'project_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _scaleIdMeta = const VerificationMeta(
    'scaleId',
  );
  @override
  late final GeneratedColumn<String> scaleId = GeneratedColumn<String>(
    'scale_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    sourcingUuid,
    batchUuid,
    feedstockSpecies,
    harvestTimestamp,
    moisturePercent,
    moistureCompliant,
    photoPath,
    sha256Hash,
    latitude,
    longitude,
    mockLocationEnabled,
    harvestUptimeSeconds,
    azimuth,
    pitch,
    roll,
    biomassInputKg,
    biomassMeasurementMethod,
    projectId,
    scaleId,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'biomass_sourcing';
  @override
  VerificationContext validateIntegrity(
    Insertable<BiomassSourcingData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('sourcing_uuid')) {
      context.handle(
        _sourcingUuidMeta,
        sourcingUuid.isAcceptableOrUnknown(
          data['sourcing_uuid']!,
          _sourcingUuidMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_sourcingUuidMeta);
    }
    if (data.containsKey('batch_uuid')) {
      context.handle(
        _batchUuidMeta,
        batchUuid.isAcceptableOrUnknown(data['batch_uuid']!, _batchUuidMeta),
      );
    } else if (isInserting) {
      context.missing(_batchUuidMeta);
    }
    if (data.containsKey('feedstock_species')) {
      context.handle(
        _feedstockSpeciesMeta,
        feedstockSpecies.isAcceptableOrUnknown(
          data['feedstock_species']!,
          _feedstockSpeciesMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_feedstockSpeciesMeta);
    }
    if (data.containsKey('harvest_timestamp')) {
      context.handle(
        _harvestTimestampMeta,
        harvestTimestamp.isAcceptableOrUnknown(
          data['harvest_timestamp']!,
          _harvestTimestampMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_harvestTimestampMeta);
    }
    if (data.containsKey('moisture_percent')) {
      context.handle(
        _moisturePercentMeta,
        moisturePercent.isAcceptableOrUnknown(
          data['moisture_percent']!,
          _moisturePercentMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_moisturePercentMeta);
    }
    if (data.containsKey('moisture_compliant')) {
      context.handle(
        _moistureCompliantMeta,
        moistureCompliant.isAcceptableOrUnknown(
          data['moisture_compliant']!,
          _moistureCompliantMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_moistureCompliantMeta);
    }
    if (data.containsKey('photo_path')) {
      context.handle(
        _photoPathMeta,
        photoPath.isAcceptableOrUnknown(data['photo_path']!, _photoPathMeta),
      );
    }
    if (data.containsKey('sha256_hash')) {
      context.handle(
        _sha256HashMeta,
        sha256Hash.isAcceptableOrUnknown(data['sha256_hash']!, _sha256HashMeta),
      );
    }
    if (data.containsKey('latitude')) {
      context.handle(
        _latitudeMeta,
        latitude.isAcceptableOrUnknown(data['latitude']!, _latitudeMeta),
      );
    }
    if (data.containsKey('longitude')) {
      context.handle(
        _longitudeMeta,
        longitude.isAcceptableOrUnknown(data['longitude']!, _longitudeMeta),
      );
    }
    if (data.containsKey('mock_location_enabled')) {
      context.handle(
        _mockLocationEnabledMeta,
        mockLocationEnabled.isAcceptableOrUnknown(
          data['mock_location_enabled']!,
          _mockLocationEnabledMeta,
        ),
      );
    }
    if (data.containsKey('harvest_uptime_seconds')) {
      context.handle(
        _harvestUptimeSecondsMeta,
        harvestUptimeSeconds.isAcceptableOrUnknown(
          data['harvest_uptime_seconds']!,
          _harvestUptimeSecondsMeta,
        ),
      );
    }
    if (data.containsKey('azimuth')) {
      context.handle(
        _azimuthMeta,
        azimuth.isAcceptableOrUnknown(data['azimuth']!, _azimuthMeta),
      );
    }
    if (data.containsKey('pitch')) {
      context.handle(
        _pitchMeta,
        pitch.isAcceptableOrUnknown(data['pitch']!, _pitchMeta),
      );
    }
    if (data.containsKey('roll')) {
      context.handle(
        _rollMeta,
        roll.isAcceptableOrUnknown(data['roll']!, _rollMeta),
      );
    }
    if (data.containsKey('biomass_input_kg')) {
      context.handle(
        _biomassInputKgMeta,
        biomassInputKg.isAcceptableOrUnknown(
          data['biomass_input_kg']!,
          _biomassInputKgMeta,
        ),
      );
    }
    if (data.containsKey('biomass_measurement_method')) {
      context.handle(
        _biomassMeasurementMethodMeta,
        biomassMeasurementMethod.isAcceptableOrUnknown(
          data['biomass_measurement_method']!,
          _biomassMeasurementMethodMeta,
        ),
      );
    }
    if (data.containsKey('project_id')) {
      context.handle(
        _projectIdMeta,
        projectId.isAcceptableOrUnknown(data['project_id']!, _projectIdMeta),
      );
    }
    if (data.containsKey('scale_id')) {
      context.handle(
        _scaleIdMeta,
        scaleId.isAcceptableOrUnknown(data['scale_id']!, _scaleIdMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {sourcingUuid};
  @override
  List<Set<GeneratedColumn>> get uniqueKeys => [
    {batchUuid},
  ];
  @override
  BiomassSourcingData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return BiomassSourcingData(
      sourcingUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sourcing_uuid'],
      )!,
      batchUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}batch_uuid'],
      )!,
      feedstockSpecies: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}feedstock_species'],
      )!,
      harvestTimestamp: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}harvest_timestamp'],
      )!,
      moisturePercent: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}moisture_percent'],
      )!,
      moistureCompliant: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}moisture_compliant'],
      )!,
      photoPath: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}photo_path'],
      ),
      sha256Hash: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sha256_hash'],
      ),
      latitude: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}latitude'],
      ),
      longitude: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}longitude'],
      ),
      mockLocationEnabled: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}mock_location_enabled'],
      )!,
      harvestUptimeSeconds: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}harvest_uptime_seconds'],
      ),
      azimuth: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}azimuth'],
      ),
      pitch: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}pitch'],
      ),
      roll: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}roll'],
      ),
      biomassInputKg: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}biomass_input_kg'],
      ),
      biomassMeasurementMethod: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}biomass_measurement_method'],
      ),
      projectId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}project_id'],
      ),
      scaleId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}scale_id'],
      ),
    );
  }

  @override
  $BiomassSourcingTable createAlias(String alias) {
    return $BiomassSourcingTable(attachedDatabase, alias);
  }
}

class BiomassSourcingData extends DataClass
    implements Insertable<BiomassSourcingData> {
  final String sourcingUuid;
  final String batchUuid;
  final String feedstockSpecies;
  final String harvestTimestamp;
  final double moisturePercent;
  final bool moistureCompliant;
  final String? photoPath;
  final String? sha256Hash;
  final double? latitude;
  final double? longitude;
  final bool mockLocationEnabled;

  /// Device monotonic uptime in seconds at the moment the artisan tapped
  /// "LOG HARVEST NOW". The backend cross-checks this against the wall-clock
  /// delta. If the wall clock was advanced manually, the uptime delta will
  /// be much smaller and the sync will be rejected with DRYING_MANDATE_NOT_MET.
  final int? harvestUptimeSeconds;
  final double? azimuth;
  final double? pitch;
  final double? roll;

  /// Mass of biomass fed to the kiln (kg). Methodology requires the biomass
  /// AMOUNT, either directly weighed or derived via a yield-conversion ratio.
  final double? biomassInputKg;

  /// 'direct_weigh' | 'yield_conversion'.
  final String? biomassMeasurementMethod;

  /// Project this device produces for (from --dart-define=DMRV_PROJECT_ID).
  /// Enables the server-side project-scoped compliance gates (C8/C9).
  final String? projectId;

  /// Weighing-scale identity, when known (BLE scale pairing metadata).
  final String? scaleId;
  const BiomassSourcingData({
    required this.sourcingUuid,
    required this.batchUuid,
    required this.feedstockSpecies,
    required this.harvestTimestamp,
    required this.moisturePercent,
    required this.moistureCompliant,
    this.photoPath,
    this.sha256Hash,
    this.latitude,
    this.longitude,
    required this.mockLocationEnabled,
    this.harvestUptimeSeconds,
    this.azimuth,
    this.pitch,
    this.roll,
    this.biomassInputKg,
    this.biomassMeasurementMethod,
    this.projectId,
    this.scaleId,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['sourcing_uuid'] = Variable<String>(sourcingUuid);
    map['batch_uuid'] = Variable<String>(batchUuid);
    map['feedstock_species'] = Variable<String>(feedstockSpecies);
    map['harvest_timestamp'] = Variable<String>(harvestTimestamp);
    map['moisture_percent'] = Variable<double>(moisturePercent);
    map['moisture_compliant'] = Variable<bool>(moistureCompliant);
    if (!nullToAbsent || photoPath != null) {
      map['photo_path'] = Variable<String>(photoPath);
    }
    if (!nullToAbsent || sha256Hash != null) {
      map['sha256_hash'] = Variable<String>(sha256Hash);
    }
    if (!nullToAbsent || latitude != null) {
      map['latitude'] = Variable<double>(latitude);
    }
    if (!nullToAbsent || longitude != null) {
      map['longitude'] = Variable<double>(longitude);
    }
    map['mock_location_enabled'] = Variable<bool>(mockLocationEnabled);
    if (!nullToAbsent || harvestUptimeSeconds != null) {
      map['harvest_uptime_seconds'] = Variable<int>(harvestUptimeSeconds);
    }
    if (!nullToAbsent || azimuth != null) {
      map['azimuth'] = Variable<double>(azimuth);
    }
    if (!nullToAbsent || pitch != null) {
      map['pitch'] = Variable<double>(pitch);
    }
    if (!nullToAbsent || roll != null) {
      map['roll'] = Variable<double>(roll);
    }
    if (!nullToAbsent || biomassInputKg != null) {
      map['biomass_input_kg'] = Variable<double>(biomassInputKg);
    }
    if (!nullToAbsent || biomassMeasurementMethod != null) {
      map['biomass_measurement_method'] = Variable<String>(
        biomassMeasurementMethod,
      );
    }
    if (!nullToAbsent || projectId != null) {
      map['project_id'] = Variable<String>(projectId);
    }
    if (!nullToAbsent || scaleId != null) {
      map['scale_id'] = Variable<String>(scaleId);
    }
    return map;
  }

  BiomassSourcingCompanion toCompanion(bool nullToAbsent) {
    return BiomassSourcingCompanion(
      sourcingUuid: Value(sourcingUuid),
      batchUuid: Value(batchUuid),
      feedstockSpecies: Value(feedstockSpecies),
      harvestTimestamp: Value(harvestTimestamp),
      moisturePercent: Value(moisturePercent),
      moistureCompliant: Value(moistureCompliant),
      photoPath: photoPath == null && nullToAbsent
          ? const Value.absent()
          : Value(photoPath),
      sha256Hash: sha256Hash == null && nullToAbsent
          ? const Value.absent()
          : Value(sha256Hash),
      latitude: latitude == null && nullToAbsent
          ? const Value.absent()
          : Value(latitude),
      longitude: longitude == null && nullToAbsent
          ? const Value.absent()
          : Value(longitude),
      mockLocationEnabled: Value(mockLocationEnabled),
      harvestUptimeSeconds: harvestUptimeSeconds == null && nullToAbsent
          ? const Value.absent()
          : Value(harvestUptimeSeconds),
      azimuth: azimuth == null && nullToAbsent
          ? const Value.absent()
          : Value(azimuth),
      pitch: pitch == null && nullToAbsent
          ? const Value.absent()
          : Value(pitch),
      roll: roll == null && nullToAbsent ? const Value.absent() : Value(roll),
      biomassInputKg: biomassInputKg == null && nullToAbsent
          ? const Value.absent()
          : Value(biomassInputKg),
      biomassMeasurementMethod: biomassMeasurementMethod == null && nullToAbsent
          ? const Value.absent()
          : Value(biomassMeasurementMethod),
      projectId: projectId == null && nullToAbsent
          ? const Value.absent()
          : Value(projectId),
      scaleId: scaleId == null && nullToAbsent
          ? const Value.absent()
          : Value(scaleId),
    );
  }

  factory BiomassSourcingData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return BiomassSourcingData(
      sourcingUuid: serializer.fromJson<String>(json['sourcingUuid']),
      batchUuid: serializer.fromJson<String>(json['batchUuid']),
      feedstockSpecies: serializer.fromJson<String>(json['feedstockSpecies']),
      harvestTimestamp: serializer.fromJson<String>(json['harvestTimestamp']),
      moisturePercent: serializer.fromJson<double>(json['moisturePercent']),
      moistureCompliant: serializer.fromJson<bool>(json['moistureCompliant']),
      photoPath: serializer.fromJson<String?>(json['photoPath']),
      sha256Hash: serializer.fromJson<String?>(json['sha256Hash']),
      latitude: serializer.fromJson<double?>(json['latitude']),
      longitude: serializer.fromJson<double?>(json['longitude']),
      mockLocationEnabled: serializer.fromJson<bool>(
        json['mockLocationEnabled'],
      ),
      harvestUptimeSeconds: serializer.fromJson<int?>(
        json['harvestUptimeSeconds'],
      ),
      azimuth: serializer.fromJson<double?>(json['azimuth']),
      pitch: serializer.fromJson<double?>(json['pitch']),
      roll: serializer.fromJson<double?>(json['roll']),
      biomassInputKg: serializer.fromJson<double?>(json['biomassInputKg']),
      biomassMeasurementMethod: serializer.fromJson<String?>(
        json['biomassMeasurementMethod'],
      ),
      projectId: serializer.fromJson<String?>(json['projectId']),
      scaleId: serializer.fromJson<String?>(json['scaleId']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'sourcingUuid': serializer.toJson<String>(sourcingUuid),
      'batchUuid': serializer.toJson<String>(batchUuid),
      'feedstockSpecies': serializer.toJson<String>(feedstockSpecies),
      'harvestTimestamp': serializer.toJson<String>(harvestTimestamp),
      'moisturePercent': serializer.toJson<double>(moisturePercent),
      'moistureCompliant': serializer.toJson<bool>(moistureCompliant),
      'photoPath': serializer.toJson<String?>(photoPath),
      'sha256Hash': serializer.toJson<String?>(sha256Hash),
      'latitude': serializer.toJson<double?>(latitude),
      'longitude': serializer.toJson<double?>(longitude),
      'mockLocationEnabled': serializer.toJson<bool>(mockLocationEnabled),
      'harvestUptimeSeconds': serializer.toJson<int?>(harvestUptimeSeconds),
      'azimuth': serializer.toJson<double?>(azimuth),
      'pitch': serializer.toJson<double?>(pitch),
      'roll': serializer.toJson<double?>(roll),
      'biomassInputKg': serializer.toJson<double?>(biomassInputKg),
      'biomassMeasurementMethod': serializer.toJson<String?>(
        biomassMeasurementMethod,
      ),
      'projectId': serializer.toJson<String?>(projectId),
      'scaleId': serializer.toJson<String?>(scaleId),
    };
  }

  BiomassSourcingData copyWith({
    String? sourcingUuid,
    String? batchUuid,
    String? feedstockSpecies,
    String? harvestTimestamp,
    double? moisturePercent,
    bool? moistureCompliant,
    Value<String?> photoPath = const Value.absent(),
    Value<String?> sha256Hash = const Value.absent(),
    Value<double?> latitude = const Value.absent(),
    Value<double?> longitude = const Value.absent(),
    bool? mockLocationEnabled,
    Value<int?> harvestUptimeSeconds = const Value.absent(),
    Value<double?> azimuth = const Value.absent(),
    Value<double?> pitch = const Value.absent(),
    Value<double?> roll = const Value.absent(),
    Value<double?> biomassInputKg = const Value.absent(),
    Value<String?> biomassMeasurementMethod = const Value.absent(),
    Value<String?> projectId = const Value.absent(),
    Value<String?> scaleId = const Value.absent(),
  }) => BiomassSourcingData(
    sourcingUuid: sourcingUuid ?? this.sourcingUuid,
    batchUuid: batchUuid ?? this.batchUuid,
    feedstockSpecies: feedstockSpecies ?? this.feedstockSpecies,
    harvestTimestamp: harvestTimestamp ?? this.harvestTimestamp,
    moisturePercent: moisturePercent ?? this.moisturePercent,
    moistureCompliant: moistureCompliant ?? this.moistureCompliant,
    photoPath: photoPath.present ? photoPath.value : this.photoPath,
    sha256Hash: sha256Hash.present ? sha256Hash.value : this.sha256Hash,
    latitude: latitude.present ? latitude.value : this.latitude,
    longitude: longitude.present ? longitude.value : this.longitude,
    mockLocationEnabled: mockLocationEnabled ?? this.mockLocationEnabled,
    harvestUptimeSeconds: harvestUptimeSeconds.present
        ? harvestUptimeSeconds.value
        : this.harvestUptimeSeconds,
    azimuth: azimuth.present ? azimuth.value : this.azimuth,
    pitch: pitch.present ? pitch.value : this.pitch,
    roll: roll.present ? roll.value : this.roll,
    biomassInputKg: biomassInputKg.present
        ? biomassInputKg.value
        : this.biomassInputKg,
    biomassMeasurementMethod: biomassMeasurementMethod.present
        ? biomassMeasurementMethod.value
        : this.biomassMeasurementMethod,
    projectId: projectId.present ? projectId.value : this.projectId,
    scaleId: scaleId.present ? scaleId.value : this.scaleId,
  );
  BiomassSourcingData copyWithCompanion(BiomassSourcingCompanion data) {
    return BiomassSourcingData(
      sourcingUuid: data.sourcingUuid.present
          ? data.sourcingUuid.value
          : this.sourcingUuid,
      batchUuid: data.batchUuid.present ? data.batchUuid.value : this.batchUuid,
      feedstockSpecies: data.feedstockSpecies.present
          ? data.feedstockSpecies.value
          : this.feedstockSpecies,
      harvestTimestamp: data.harvestTimestamp.present
          ? data.harvestTimestamp.value
          : this.harvestTimestamp,
      moisturePercent: data.moisturePercent.present
          ? data.moisturePercent.value
          : this.moisturePercent,
      moistureCompliant: data.moistureCompliant.present
          ? data.moistureCompliant.value
          : this.moistureCompliant,
      photoPath: data.photoPath.present ? data.photoPath.value : this.photoPath,
      sha256Hash: data.sha256Hash.present
          ? data.sha256Hash.value
          : this.sha256Hash,
      latitude: data.latitude.present ? data.latitude.value : this.latitude,
      longitude: data.longitude.present ? data.longitude.value : this.longitude,
      mockLocationEnabled: data.mockLocationEnabled.present
          ? data.mockLocationEnabled.value
          : this.mockLocationEnabled,
      harvestUptimeSeconds: data.harvestUptimeSeconds.present
          ? data.harvestUptimeSeconds.value
          : this.harvestUptimeSeconds,
      azimuth: data.azimuth.present ? data.azimuth.value : this.azimuth,
      pitch: data.pitch.present ? data.pitch.value : this.pitch,
      roll: data.roll.present ? data.roll.value : this.roll,
      biomassInputKg: data.biomassInputKg.present
          ? data.biomassInputKg.value
          : this.biomassInputKg,
      biomassMeasurementMethod: data.biomassMeasurementMethod.present
          ? data.biomassMeasurementMethod.value
          : this.biomassMeasurementMethod,
      projectId: data.projectId.present ? data.projectId.value : this.projectId,
      scaleId: data.scaleId.present ? data.scaleId.value : this.scaleId,
    );
  }

  @override
  String toString() {
    return (StringBuffer('BiomassSourcingData(')
          ..write('sourcingUuid: $sourcingUuid, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('feedstockSpecies: $feedstockSpecies, ')
          ..write('harvestTimestamp: $harvestTimestamp, ')
          ..write('moisturePercent: $moisturePercent, ')
          ..write('moistureCompliant: $moistureCompliant, ')
          ..write('photoPath: $photoPath, ')
          ..write('sha256Hash: $sha256Hash, ')
          ..write('latitude: $latitude, ')
          ..write('longitude: $longitude, ')
          ..write('mockLocationEnabled: $mockLocationEnabled, ')
          ..write('harvestUptimeSeconds: $harvestUptimeSeconds, ')
          ..write('azimuth: $azimuth, ')
          ..write('pitch: $pitch, ')
          ..write('roll: $roll, ')
          ..write('biomassInputKg: $biomassInputKg, ')
          ..write('biomassMeasurementMethod: $biomassMeasurementMethod, ')
          ..write('projectId: $projectId, ')
          ..write('scaleId: $scaleId')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    sourcingUuid,
    batchUuid,
    feedstockSpecies,
    harvestTimestamp,
    moisturePercent,
    moistureCompliant,
    photoPath,
    sha256Hash,
    latitude,
    longitude,
    mockLocationEnabled,
    harvestUptimeSeconds,
    azimuth,
    pitch,
    roll,
    biomassInputKg,
    biomassMeasurementMethod,
    projectId,
    scaleId,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is BiomassSourcingData &&
          other.sourcingUuid == this.sourcingUuid &&
          other.batchUuid == this.batchUuid &&
          other.feedstockSpecies == this.feedstockSpecies &&
          other.harvestTimestamp == this.harvestTimestamp &&
          other.moisturePercent == this.moisturePercent &&
          other.moistureCompliant == this.moistureCompliant &&
          other.photoPath == this.photoPath &&
          other.sha256Hash == this.sha256Hash &&
          other.latitude == this.latitude &&
          other.longitude == this.longitude &&
          other.mockLocationEnabled == this.mockLocationEnabled &&
          other.harvestUptimeSeconds == this.harvestUptimeSeconds &&
          other.azimuth == this.azimuth &&
          other.pitch == this.pitch &&
          other.roll == this.roll &&
          other.biomassInputKg == this.biomassInputKg &&
          other.biomassMeasurementMethod == this.biomassMeasurementMethod &&
          other.projectId == this.projectId &&
          other.scaleId == this.scaleId);
}

class BiomassSourcingCompanion extends UpdateCompanion<BiomassSourcingData> {
  final Value<String> sourcingUuid;
  final Value<String> batchUuid;
  final Value<String> feedstockSpecies;
  final Value<String> harvestTimestamp;
  final Value<double> moisturePercent;
  final Value<bool> moistureCompliant;
  final Value<String?> photoPath;
  final Value<String?> sha256Hash;
  final Value<double?> latitude;
  final Value<double?> longitude;
  final Value<bool> mockLocationEnabled;
  final Value<int?> harvestUptimeSeconds;
  final Value<double?> azimuth;
  final Value<double?> pitch;
  final Value<double?> roll;
  final Value<double?> biomassInputKg;
  final Value<String?> biomassMeasurementMethod;
  final Value<String?> projectId;
  final Value<String?> scaleId;
  final Value<int> rowid;
  const BiomassSourcingCompanion({
    this.sourcingUuid = const Value.absent(),
    this.batchUuid = const Value.absent(),
    this.feedstockSpecies = const Value.absent(),
    this.harvestTimestamp = const Value.absent(),
    this.moisturePercent = const Value.absent(),
    this.moistureCompliant = const Value.absent(),
    this.photoPath = const Value.absent(),
    this.sha256Hash = const Value.absent(),
    this.latitude = const Value.absent(),
    this.longitude = const Value.absent(),
    this.mockLocationEnabled = const Value.absent(),
    this.harvestUptimeSeconds = const Value.absent(),
    this.azimuth = const Value.absent(),
    this.pitch = const Value.absent(),
    this.roll = const Value.absent(),
    this.biomassInputKg = const Value.absent(),
    this.biomassMeasurementMethod = const Value.absent(),
    this.projectId = const Value.absent(),
    this.scaleId = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  BiomassSourcingCompanion.insert({
    required String sourcingUuid,
    required String batchUuid,
    required String feedstockSpecies,
    required String harvestTimestamp,
    required double moisturePercent,
    required bool moistureCompliant,
    this.photoPath = const Value.absent(),
    this.sha256Hash = const Value.absent(),
    this.latitude = const Value.absent(),
    this.longitude = const Value.absent(),
    this.mockLocationEnabled = const Value.absent(),
    this.harvestUptimeSeconds = const Value.absent(),
    this.azimuth = const Value.absent(),
    this.pitch = const Value.absent(),
    this.roll = const Value.absent(),
    this.biomassInputKg = const Value.absent(),
    this.biomassMeasurementMethod = const Value.absent(),
    this.projectId = const Value.absent(),
    this.scaleId = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : sourcingUuid = Value(sourcingUuid),
       batchUuid = Value(batchUuid),
       feedstockSpecies = Value(feedstockSpecies),
       harvestTimestamp = Value(harvestTimestamp),
       moisturePercent = Value(moisturePercent),
       moistureCompliant = Value(moistureCompliant);
  static Insertable<BiomassSourcingData> custom({
    Expression<String>? sourcingUuid,
    Expression<String>? batchUuid,
    Expression<String>? feedstockSpecies,
    Expression<String>? harvestTimestamp,
    Expression<double>? moisturePercent,
    Expression<bool>? moistureCompliant,
    Expression<String>? photoPath,
    Expression<String>? sha256Hash,
    Expression<double>? latitude,
    Expression<double>? longitude,
    Expression<bool>? mockLocationEnabled,
    Expression<int>? harvestUptimeSeconds,
    Expression<double>? azimuth,
    Expression<double>? pitch,
    Expression<double>? roll,
    Expression<double>? biomassInputKg,
    Expression<String>? biomassMeasurementMethod,
    Expression<String>? projectId,
    Expression<String>? scaleId,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (sourcingUuid != null) 'sourcing_uuid': sourcingUuid,
      if (batchUuid != null) 'batch_uuid': batchUuid,
      if (feedstockSpecies != null) 'feedstock_species': feedstockSpecies,
      if (harvestTimestamp != null) 'harvest_timestamp': harvestTimestamp,
      if (moisturePercent != null) 'moisture_percent': moisturePercent,
      if (moistureCompliant != null) 'moisture_compliant': moistureCompliant,
      if (photoPath != null) 'photo_path': photoPath,
      if (sha256Hash != null) 'sha256_hash': sha256Hash,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      if (mockLocationEnabled != null)
        'mock_location_enabled': mockLocationEnabled,
      if (harvestUptimeSeconds != null)
        'harvest_uptime_seconds': harvestUptimeSeconds,
      if (azimuth != null) 'azimuth': azimuth,
      if (pitch != null) 'pitch': pitch,
      if (roll != null) 'roll': roll,
      if (biomassInputKg != null) 'biomass_input_kg': biomassInputKg,
      if (biomassMeasurementMethod != null)
        'biomass_measurement_method': biomassMeasurementMethod,
      if (projectId != null) 'project_id': projectId,
      if (scaleId != null) 'scale_id': scaleId,
      if (rowid != null) 'rowid': rowid,
    });
  }

  BiomassSourcingCompanion copyWith({
    Value<String>? sourcingUuid,
    Value<String>? batchUuid,
    Value<String>? feedstockSpecies,
    Value<String>? harvestTimestamp,
    Value<double>? moisturePercent,
    Value<bool>? moistureCompliant,
    Value<String?>? photoPath,
    Value<String?>? sha256Hash,
    Value<double?>? latitude,
    Value<double?>? longitude,
    Value<bool>? mockLocationEnabled,
    Value<int?>? harvestUptimeSeconds,
    Value<double?>? azimuth,
    Value<double?>? pitch,
    Value<double?>? roll,
    Value<double?>? biomassInputKg,
    Value<String?>? biomassMeasurementMethod,
    Value<String?>? projectId,
    Value<String?>? scaleId,
    Value<int>? rowid,
  }) {
    return BiomassSourcingCompanion(
      sourcingUuid: sourcingUuid ?? this.sourcingUuid,
      batchUuid: batchUuid ?? this.batchUuid,
      feedstockSpecies: feedstockSpecies ?? this.feedstockSpecies,
      harvestTimestamp: harvestTimestamp ?? this.harvestTimestamp,
      moisturePercent: moisturePercent ?? this.moisturePercent,
      moistureCompliant: moistureCompliant ?? this.moistureCompliant,
      photoPath: photoPath ?? this.photoPath,
      sha256Hash: sha256Hash ?? this.sha256Hash,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      mockLocationEnabled: mockLocationEnabled ?? this.mockLocationEnabled,
      harvestUptimeSeconds: harvestUptimeSeconds ?? this.harvestUptimeSeconds,
      azimuth: azimuth ?? this.azimuth,
      pitch: pitch ?? this.pitch,
      roll: roll ?? this.roll,
      biomassInputKg: biomassInputKg ?? this.biomassInputKg,
      biomassMeasurementMethod:
          biomassMeasurementMethod ?? this.biomassMeasurementMethod,
      projectId: projectId ?? this.projectId,
      scaleId: scaleId ?? this.scaleId,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (sourcingUuid.present) {
      map['sourcing_uuid'] = Variable<String>(sourcingUuid.value);
    }
    if (batchUuid.present) {
      map['batch_uuid'] = Variable<String>(batchUuid.value);
    }
    if (feedstockSpecies.present) {
      map['feedstock_species'] = Variable<String>(feedstockSpecies.value);
    }
    if (harvestTimestamp.present) {
      map['harvest_timestamp'] = Variable<String>(harvestTimestamp.value);
    }
    if (moisturePercent.present) {
      map['moisture_percent'] = Variable<double>(moisturePercent.value);
    }
    if (moistureCompliant.present) {
      map['moisture_compliant'] = Variable<bool>(moistureCompliant.value);
    }
    if (photoPath.present) {
      map['photo_path'] = Variable<String>(photoPath.value);
    }
    if (sha256Hash.present) {
      map['sha256_hash'] = Variable<String>(sha256Hash.value);
    }
    if (latitude.present) {
      map['latitude'] = Variable<double>(latitude.value);
    }
    if (longitude.present) {
      map['longitude'] = Variable<double>(longitude.value);
    }
    if (mockLocationEnabled.present) {
      map['mock_location_enabled'] = Variable<bool>(mockLocationEnabled.value);
    }
    if (harvestUptimeSeconds.present) {
      map['harvest_uptime_seconds'] = Variable<int>(harvestUptimeSeconds.value);
    }
    if (azimuth.present) {
      map['azimuth'] = Variable<double>(azimuth.value);
    }
    if (pitch.present) {
      map['pitch'] = Variable<double>(pitch.value);
    }
    if (roll.present) {
      map['roll'] = Variable<double>(roll.value);
    }
    if (biomassInputKg.present) {
      map['biomass_input_kg'] = Variable<double>(biomassInputKg.value);
    }
    if (biomassMeasurementMethod.present) {
      map['biomass_measurement_method'] = Variable<String>(
        biomassMeasurementMethod.value,
      );
    }
    if (projectId.present) {
      map['project_id'] = Variable<String>(projectId.value);
    }
    if (scaleId.present) {
      map['scale_id'] = Variable<String>(scaleId.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('BiomassSourcingCompanion(')
          ..write('sourcingUuid: $sourcingUuid, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('feedstockSpecies: $feedstockSpecies, ')
          ..write('harvestTimestamp: $harvestTimestamp, ')
          ..write('moisturePercent: $moisturePercent, ')
          ..write('moistureCompliant: $moistureCompliant, ')
          ..write('photoPath: $photoPath, ')
          ..write('sha256Hash: $sha256Hash, ')
          ..write('latitude: $latitude, ')
          ..write('longitude: $longitude, ')
          ..write('mockLocationEnabled: $mockLocationEnabled, ')
          ..write('harvestUptimeSeconds: $harvestUptimeSeconds, ')
          ..write('azimuth: $azimuth, ')
          ..write('pitch: $pitch, ')
          ..write('roll: $roll, ')
          ..write('biomassInputKg: $biomassInputKg, ')
          ..write('biomassMeasurementMethod: $biomassMeasurementMethod, ')
          ..write('projectId: $projectId, ')
          ..write('scaleId: $scaleId, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $PyrolysisTelemetryTable extends PyrolysisTelemetry
    with TableInfo<$PyrolysisTelemetryTable, PyrolysisTelemetryData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $PyrolysisTelemetryTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _telemetryUuidMeta = const VerificationMeta(
    'telemetryUuid',
  );
  @override
  late final GeneratedColumn<String> telemetryUuid = GeneratedColumn<String>(
    'telemetry_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _batchUuidMeta = const VerificationMeta(
    'batchUuid',
  );
  @override
  late final GeneratedColumn<String> batchUuid = GeneratedColumn<String>(
    'batch_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES system_metadata (batch_uuid)',
    ),
  );
  static const VerificationMeta _kilnGrossCapacityMeta = const VerificationMeta(
    'kilnGrossCapacity',
  );
  @override
  late final GeneratedColumn<double> kilnGrossCapacity =
      GeneratedColumn<double>(
        'kiln_gross_capacity',
        aliasedName,
        false,
        type: DriftSqlType.double,
        requiredDuringInsert: true,
      );
  static const VerificationMeta _burnStartTimestampMeta =
      const VerificationMeta('burnStartTimestamp');
  @override
  late final GeneratedColumn<String> burnStartTimestamp =
      GeneratedColumn<String>(
        'burn_start_timestamp',
        aliasedName,
        false,
        type: DriftSqlType.string,
        requiredDuringInsert: true,
      );
  static const VerificationMeta _burnEndTimestampMeta = const VerificationMeta(
    'burnEndTimestamp',
  );
  @override
  late final GeneratedColumn<String> burnEndTimestamp = GeneratedColumn<String>(
    'burn_end_timestamp',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _minTempMeta = const VerificationMeta(
    'minTemp',
  );
  @override
  late final GeneratedColumn<double> minTemp = GeneratedColumn<double>(
    'min_temp',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _maxTempMeta = const VerificationMeta(
    'maxTemp',
  );
  @override
  late final GeneratedColumn<double> maxTemp = GeneratedColumn<double>(
    'max_temp',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _temperatureReadingsJsonMeta =
      const VerificationMeta('temperatureReadingsJson');
  @override
  late final GeneratedColumn<String> temperatureReadingsJson =
      GeneratedColumn<String>(
        'temperature_readings_json',
        aliasedName,
        false,
        type: DriftSqlType.string,
        requiredDuringInsert: false,
        defaultValue: const Constant('[]'),
      );
  static const VerificationMeta _smokeEvidenceJsonMeta = const VerificationMeta(
    'smokeEvidenceJson',
  );
  @override
  late final GeneratedColumn<String> smokeEvidenceJson =
      GeneratedColumn<String>(
        'smoke_evidence_json',
        aliasedName,
        false,
        type: DriftSqlType.string,
        requiredDuringInsert: false,
        defaultValue: const Constant('[]'),
      );
  static const VerificationMeta _azimuthMeta = const VerificationMeta(
    'azimuth',
  );
  @override
  late final GeneratedColumn<double> azimuth = GeneratedColumn<double>(
    'azimuth',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _pitchMeta = const VerificationMeta('pitch');
  @override
  late final GeneratedColumn<double> pitch = GeneratedColumn<double>(
    'pitch',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _rollMeta = const VerificationMeta('roll');
  @override
  late final GeneratedColumn<double> roll = GeneratedColumn<double>(
    'roll',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _hwAttestationJsonMeta = const VerificationMeta(
    'hwAttestationJson',
  );
  @override
  late final GeneratedColumn<String> hwAttestationJson =
      GeneratedColumn<String>(
        'hw_attestation_json',
        aliasedName,
        false,
        type: DriftSqlType.string,
        requiredDuringInsert: false,
        defaultValue: const Constant('[]'),
      );
  static const VerificationMeta _kilnTypeMeta = const VerificationMeta(
    'kilnType',
  );
  @override
  late final GeneratedColumn<String> kilnType = GeneratedColumn<String>(
    'kiln_type',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _kilnIdMeta = const VerificationMeta('kilnId');
  @override
  late final GeneratedColumn<String> kilnId = GeneratedColumn<String>(
    'kiln_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _flameHeightMMeta = const VerificationMeta(
    'flameHeightM',
  );
  @override
  late final GeneratedColumn<double> flameHeightM = GeneratedColumn<double>(
    'flame_height_m',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _ignitionEnergyTypeMeta =
      const VerificationMeta('ignitionEnergyType');
  @override
  late final GeneratedColumn<String> ignitionEnergyType =
      GeneratedColumn<String>(
        'ignition_energy_type',
        aliasedName,
        true,
        type: DriftSqlType.string,
        requiredDuringInsert: false,
      );
  static const VerificationMeta _ignitionEnergyAmountMeta =
      const VerificationMeta('ignitionEnergyAmount');
  @override
  late final GeneratedColumn<double> ignitionEnergyAmount =
      GeneratedColumn<double>(
        'ignition_energy_amount',
        aliasedName,
        true,
        type: DriftSqlType.double,
        requiredDuringInsert: false,
      );
  @override
  List<GeneratedColumn> get $columns => [
    telemetryUuid,
    batchUuid,
    kilnGrossCapacity,
    burnStartTimestamp,
    burnEndTimestamp,
    minTemp,
    maxTemp,
    temperatureReadingsJson,
    smokeEvidenceJson,
    azimuth,
    pitch,
    roll,
    hwAttestationJson,
    kilnType,
    kilnId,
    flameHeightM,
    ignitionEnergyType,
    ignitionEnergyAmount,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'pyrolysis_telemetry';
  @override
  VerificationContext validateIntegrity(
    Insertable<PyrolysisTelemetryData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('telemetry_uuid')) {
      context.handle(
        _telemetryUuidMeta,
        telemetryUuid.isAcceptableOrUnknown(
          data['telemetry_uuid']!,
          _telemetryUuidMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_telemetryUuidMeta);
    }
    if (data.containsKey('batch_uuid')) {
      context.handle(
        _batchUuidMeta,
        batchUuid.isAcceptableOrUnknown(data['batch_uuid']!, _batchUuidMeta),
      );
    } else if (isInserting) {
      context.missing(_batchUuidMeta);
    }
    if (data.containsKey('kiln_gross_capacity')) {
      context.handle(
        _kilnGrossCapacityMeta,
        kilnGrossCapacity.isAcceptableOrUnknown(
          data['kiln_gross_capacity']!,
          _kilnGrossCapacityMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_kilnGrossCapacityMeta);
    }
    if (data.containsKey('burn_start_timestamp')) {
      context.handle(
        _burnStartTimestampMeta,
        burnStartTimestamp.isAcceptableOrUnknown(
          data['burn_start_timestamp']!,
          _burnStartTimestampMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_burnStartTimestampMeta);
    }
    if (data.containsKey('burn_end_timestamp')) {
      context.handle(
        _burnEndTimestampMeta,
        burnEndTimestamp.isAcceptableOrUnknown(
          data['burn_end_timestamp']!,
          _burnEndTimestampMeta,
        ),
      );
    }
    if (data.containsKey('min_temp')) {
      context.handle(
        _minTempMeta,
        minTemp.isAcceptableOrUnknown(data['min_temp']!, _minTempMeta),
      );
    } else if (isInserting) {
      context.missing(_minTempMeta);
    }
    if (data.containsKey('max_temp')) {
      context.handle(
        _maxTempMeta,
        maxTemp.isAcceptableOrUnknown(data['max_temp']!, _maxTempMeta),
      );
    } else if (isInserting) {
      context.missing(_maxTempMeta);
    }
    if (data.containsKey('temperature_readings_json')) {
      context.handle(
        _temperatureReadingsJsonMeta,
        temperatureReadingsJson.isAcceptableOrUnknown(
          data['temperature_readings_json']!,
          _temperatureReadingsJsonMeta,
        ),
      );
    }
    if (data.containsKey('smoke_evidence_json')) {
      context.handle(
        _smokeEvidenceJsonMeta,
        smokeEvidenceJson.isAcceptableOrUnknown(
          data['smoke_evidence_json']!,
          _smokeEvidenceJsonMeta,
        ),
      );
    }
    if (data.containsKey('azimuth')) {
      context.handle(
        _azimuthMeta,
        azimuth.isAcceptableOrUnknown(data['azimuth']!, _azimuthMeta),
      );
    }
    if (data.containsKey('pitch')) {
      context.handle(
        _pitchMeta,
        pitch.isAcceptableOrUnknown(data['pitch']!, _pitchMeta),
      );
    }
    if (data.containsKey('roll')) {
      context.handle(
        _rollMeta,
        roll.isAcceptableOrUnknown(data['roll']!, _rollMeta),
      );
    }
    if (data.containsKey('hw_attestation_json')) {
      context.handle(
        _hwAttestationJsonMeta,
        hwAttestationJson.isAcceptableOrUnknown(
          data['hw_attestation_json']!,
          _hwAttestationJsonMeta,
        ),
      );
    }
    if (data.containsKey('kiln_type')) {
      context.handle(
        _kilnTypeMeta,
        kilnType.isAcceptableOrUnknown(data['kiln_type']!, _kilnTypeMeta),
      );
    }
    if (data.containsKey('kiln_id')) {
      context.handle(
        _kilnIdMeta,
        kilnId.isAcceptableOrUnknown(data['kiln_id']!, _kilnIdMeta),
      );
    }
    if (data.containsKey('flame_height_m')) {
      context.handle(
        _flameHeightMMeta,
        flameHeightM.isAcceptableOrUnknown(
          data['flame_height_m']!,
          _flameHeightMMeta,
        ),
      );
    }
    if (data.containsKey('ignition_energy_type')) {
      context.handle(
        _ignitionEnergyTypeMeta,
        ignitionEnergyType.isAcceptableOrUnknown(
          data['ignition_energy_type']!,
          _ignitionEnergyTypeMeta,
        ),
      );
    }
    if (data.containsKey('ignition_energy_amount')) {
      context.handle(
        _ignitionEnergyAmountMeta,
        ignitionEnergyAmount.isAcceptableOrUnknown(
          data['ignition_energy_amount']!,
          _ignitionEnergyAmountMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {telemetryUuid};
  @override
  List<Set<GeneratedColumn>> get uniqueKeys => [
    {batchUuid},
  ];
  @override
  PyrolysisTelemetryData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return PyrolysisTelemetryData(
      telemetryUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}telemetry_uuid'],
      )!,
      batchUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}batch_uuid'],
      )!,
      kilnGrossCapacity: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}kiln_gross_capacity'],
      )!,
      burnStartTimestamp: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}burn_start_timestamp'],
      )!,
      burnEndTimestamp: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}burn_end_timestamp'],
      ),
      minTemp: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}min_temp'],
      )!,
      maxTemp: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}max_temp'],
      )!,
      temperatureReadingsJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}temperature_readings_json'],
      )!,
      smokeEvidenceJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}smoke_evidence_json'],
      )!,
      azimuth: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}azimuth'],
      ),
      pitch: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}pitch'],
      ),
      roll: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}roll'],
      ),
      hwAttestationJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}hw_attestation_json'],
      )!,
      kilnType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}kiln_type'],
      ),
      kilnId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}kiln_id'],
      ),
      flameHeightM: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}flame_height_m'],
      ),
      ignitionEnergyType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}ignition_energy_type'],
      ),
      ignitionEnergyAmount: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}ignition_energy_amount'],
      ),
    );
  }

  @override
  $PyrolysisTelemetryTable createAlias(String alias) {
    return $PyrolysisTelemetryTable(attachedDatabase, alias);
  }
}

class PyrolysisTelemetryData extends DataClass
    implements Insertable<PyrolysisTelemetryData> {
  final String telemetryUuid;
  final String batchUuid;
  final double kilnGrossCapacity;
  final String burnStartTimestamp;
  final String? burnEndTimestamp;
  final double minTemp;
  final double maxTemp;
  final String temperatureReadingsJson;
  final String smokeEvidenceJson;
  final double? azimuth;
  final double? pitch;
  final double? roll;

  /// JSON array of base64-encoded ECDSA attestation blobs from the ESP32
  /// secure element. Each blob is 80 bytes: deviceId(4) + seq(4) + ts(4) +
  /// temp(4) + ecdsaSig(64). The server verifies each signature against the
  /// device's registered public key.
  final String hwAttestationJson;

  /// 'open' | 'closed'. The Rainbow methodology branches on kiln type (ignition
  /// energy, pyrolysis-photo requirements, PAH). Nullable for backward compat.
  final String? kilnType;

  /// Stable kiln identifier / QR (links a run to the project kiln registry).
  final String? kilnId;

  /// Measured flame height (m); open-kiln methodology requires < 0.5 m.
  final double? flameHeightM;

  /// Ignition energy inputs — closed-kiln only (type + amount incl. syngas).
  final String? ignitionEnergyType;
  final double? ignitionEnergyAmount;
  const PyrolysisTelemetryData({
    required this.telemetryUuid,
    required this.batchUuid,
    required this.kilnGrossCapacity,
    required this.burnStartTimestamp,
    this.burnEndTimestamp,
    required this.minTemp,
    required this.maxTemp,
    required this.temperatureReadingsJson,
    required this.smokeEvidenceJson,
    this.azimuth,
    this.pitch,
    this.roll,
    required this.hwAttestationJson,
    this.kilnType,
    this.kilnId,
    this.flameHeightM,
    this.ignitionEnergyType,
    this.ignitionEnergyAmount,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['telemetry_uuid'] = Variable<String>(telemetryUuid);
    map['batch_uuid'] = Variable<String>(batchUuid);
    map['kiln_gross_capacity'] = Variable<double>(kilnGrossCapacity);
    map['burn_start_timestamp'] = Variable<String>(burnStartTimestamp);
    if (!nullToAbsent || burnEndTimestamp != null) {
      map['burn_end_timestamp'] = Variable<String>(burnEndTimestamp);
    }
    map['min_temp'] = Variable<double>(minTemp);
    map['max_temp'] = Variable<double>(maxTemp);
    map['temperature_readings_json'] = Variable<String>(
      temperatureReadingsJson,
    );
    map['smoke_evidence_json'] = Variable<String>(smokeEvidenceJson);
    if (!nullToAbsent || azimuth != null) {
      map['azimuth'] = Variable<double>(azimuth);
    }
    if (!nullToAbsent || pitch != null) {
      map['pitch'] = Variable<double>(pitch);
    }
    if (!nullToAbsent || roll != null) {
      map['roll'] = Variable<double>(roll);
    }
    map['hw_attestation_json'] = Variable<String>(hwAttestationJson);
    if (!nullToAbsent || kilnType != null) {
      map['kiln_type'] = Variable<String>(kilnType);
    }
    if (!nullToAbsent || kilnId != null) {
      map['kiln_id'] = Variable<String>(kilnId);
    }
    if (!nullToAbsent || flameHeightM != null) {
      map['flame_height_m'] = Variable<double>(flameHeightM);
    }
    if (!nullToAbsent || ignitionEnergyType != null) {
      map['ignition_energy_type'] = Variable<String>(ignitionEnergyType);
    }
    if (!nullToAbsent || ignitionEnergyAmount != null) {
      map['ignition_energy_amount'] = Variable<double>(ignitionEnergyAmount);
    }
    return map;
  }

  PyrolysisTelemetryCompanion toCompanion(bool nullToAbsent) {
    return PyrolysisTelemetryCompanion(
      telemetryUuid: Value(telemetryUuid),
      batchUuid: Value(batchUuid),
      kilnGrossCapacity: Value(kilnGrossCapacity),
      burnStartTimestamp: Value(burnStartTimestamp),
      burnEndTimestamp: burnEndTimestamp == null && nullToAbsent
          ? const Value.absent()
          : Value(burnEndTimestamp),
      minTemp: Value(minTemp),
      maxTemp: Value(maxTemp),
      temperatureReadingsJson: Value(temperatureReadingsJson),
      smokeEvidenceJson: Value(smokeEvidenceJson),
      azimuth: azimuth == null && nullToAbsent
          ? const Value.absent()
          : Value(azimuth),
      pitch: pitch == null && nullToAbsent
          ? const Value.absent()
          : Value(pitch),
      roll: roll == null && nullToAbsent ? const Value.absent() : Value(roll),
      hwAttestationJson: Value(hwAttestationJson),
      kilnType: kilnType == null && nullToAbsent
          ? const Value.absent()
          : Value(kilnType),
      kilnId: kilnId == null && nullToAbsent
          ? const Value.absent()
          : Value(kilnId),
      flameHeightM: flameHeightM == null && nullToAbsent
          ? const Value.absent()
          : Value(flameHeightM),
      ignitionEnergyType: ignitionEnergyType == null && nullToAbsent
          ? const Value.absent()
          : Value(ignitionEnergyType),
      ignitionEnergyAmount: ignitionEnergyAmount == null && nullToAbsent
          ? const Value.absent()
          : Value(ignitionEnergyAmount),
    );
  }

  factory PyrolysisTelemetryData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return PyrolysisTelemetryData(
      telemetryUuid: serializer.fromJson<String>(json['telemetryUuid']),
      batchUuid: serializer.fromJson<String>(json['batchUuid']),
      kilnGrossCapacity: serializer.fromJson<double>(json['kilnGrossCapacity']),
      burnStartTimestamp: serializer.fromJson<String>(
        json['burnStartTimestamp'],
      ),
      burnEndTimestamp: serializer.fromJson<String?>(json['burnEndTimestamp']),
      minTemp: serializer.fromJson<double>(json['minTemp']),
      maxTemp: serializer.fromJson<double>(json['maxTemp']),
      temperatureReadingsJson: serializer.fromJson<String>(
        json['temperatureReadingsJson'],
      ),
      smokeEvidenceJson: serializer.fromJson<String>(json['smokeEvidenceJson']),
      azimuth: serializer.fromJson<double?>(json['azimuth']),
      pitch: serializer.fromJson<double?>(json['pitch']),
      roll: serializer.fromJson<double?>(json['roll']),
      hwAttestationJson: serializer.fromJson<String>(json['hwAttestationJson']),
      kilnType: serializer.fromJson<String?>(json['kilnType']),
      kilnId: serializer.fromJson<String?>(json['kilnId']),
      flameHeightM: serializer.fromJson<double?>(json['flameHeightM']),
      ignitionEnergyType: serializer.fromJson<String?>(
        json['ignitionEnergyType'],
      ),
      ignitionEnergyAmount: serializer.fromJson<double?>(
        json['ignitionEnergyAmount'],
      ),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'telemetryUuid': serializer.toJson<String>(telemetryUuid),
      'batchUuid': serializer.toJson<String>(batchUuid),
      'kilnGrossCapacity': serializer.toJson<double>(kilnGrossCapacity),
      'burnStartTimestamp': serializer.toJson<String>(burnStartTimestamp),
      'burnEndTimestamp': serializer.toJson<String?>(burnEndTimestamp),
      'minTemp': serializer.toJson<double>(minTemp),
      'maxTemp': serializer.toJson<double>(maxTemp),
      'temperatureReadingsJson': serializer.toJson<String>(
        temperatureReadingsJson,
      ),
      'smokeEvidenceJson': serializer.toJson<String>(smokeEvidenceJson),
      'azimuth': serializer.toJson<double?>(azimuth),
      'pitch': serializer.toJson<double?>(pitch),
      'roll': serializer.toJson<double?>(roll),
      'hwAttestationJson': serializer.toJson<String>(hwAttestationJson),
      'kilnType': serializer.toJson<String?>(kilnType),
      'kilnId': serializer.toJson<String?>(kilnId),
      'flameHeightM': serializer.toJson<double?>(flameHeightM),
      'ignitionEnergyType': serializer.toJson<String?>(ignitionEnergyType),
      'ignitionEnergyAmount': serializer.toJson<double?>(ignitionEnergyAmount),
    };
  }

  PyrolysisTelemetryData copyWith({
    String? telemetryUuid,
    String? batchUuid,
    double? kilnGrossCapacity,
    String? burnStartTimestamp,
    Value<String?> burnEndTimestamp = const Value.absent(),
    double? minTemp,
    double? maxTemp,
    String? temperatureReadingsJson,
    String? smokeEvidenceJson,
    Value<double?> azimuth = const Value.absent(),
    Value<double?> pitch = const Value.absent(),
    Value<double?> roll = const Value.absent(),
    String? hwAttestationJson,
    Value<String?> kilnType = const Value.absent(),
    Value<String?> kilnId = const Value.absent(),
    Value<double?> flameHeightM = const Value.absent(),
    Value<String?> ignitionEnergyType = const Value.absent(),
    Value<double?> ignitionEnergyAmount = const Value.absent(),
  }) => PyrolysisTelemetryData(
    telemetryUuid: telemetryUuid ?? this.telemetryUuid,
    batchUuid: batchUuid ?? this.batchUuid,
    kilnGrossCapacity: kilnGrossCapacity ?? this.kilnGrossCapacity,
    burnStartTimestamp: burnStartTimestamp ?? this.burnStartTimestamp,
    burnEndTimestamp: burnEndTimestamp.present
        ? burnEndTimestamp.value
        : this.burnEndTimestamp,
    minTemp: minTemp ?? this.minTemp,
    maxTemp: maxTemp ?? this.maxTemp,
    temperatureReadingsJson:
        temperatureReadingsJson ?? this.temperatureReadingsJson,
    smokeEvidenceJson: smokeEvidenceJson ?? this.smokeEvidenceJson,
    azimuth: azimuth.present ? azimuth.value : this.azimuth,
    pitch: pitch.present ? pitch.value : this.pitch,
    roll: roll.present ? roll.value : this.roll,
    hwAttestationJson: hwAttestationJson ?? this.hwAttestationJson,
    kilnType: kilnType.present ? kilnType.value : this.kilnType,
    kilnId: kilnId.present ? kilnId.value : this.kilnId,
    flameHeightM: flameHeightM.present ? flameHeightM.value : this.flameHeightM,
    ignitionEnergyType: ignitionEnergyType.present
        ? ignitionEnergyType.value
        : this.ignitionEnergyType,
    ignitionEnergyAmount: ignitionEnergyAmount.present
        ? ignitionEnergyAmount.value
        : this.ignitionEnergyAmount,
  );
  PyrolysisTelemetryData copyWithCompanion(PyrolysisTelemetryCompanion data) {
    return PyrolysisTelemetryData(
      telemetryUuid: data.telemetryUuid.present
          ? data.telemetryUuid.value
          : this.telemetryUuid,
      batchUuid: data.batchUuid.present ? data.batchUuid.value : this.batchUuid,
      kilnGrossCapacity: data.kilnGrossCapacity.present
          ? data.kilnGrossCapacity.value
          : this.kilnGrossCapacity,
      burnStartTimestamp: data.burnStartTimestamp.present
          ? data.burnStartTimestamp.value
          : this.burnStartTimestamp,
      burnEndTimestamp: data.burnEndTimestamp.present
          ? data.burnEndTimestamp.value
          : this.burnEndTimestamp,
      minTemp: data.minTemp.present ? data.minTemp.value : this.minTemp,
      maxTemp: data.maxTemp.present ? data.maxTemp.value : this.maxTemp,
      temperatureReadingsJson: data.temperatureReadingsJson.present
          ? data.temperatureReadingsJson.value
          : this.temperatureReadingsJson,
      smokeEvidenceJson: data.smokeEvidenceJson.present
          ? data.smokeEvidenceJson.value
          : this.smokeEvidenceJson,
      azimuth: data.azimuth.present ? data.azimuth.value : this.azimuth,
      pitch: data.pitch.present ? data.pitch.value : this.pitch,
      roll: data.roll.present ? data.roll.value : this.roll,
      hwAttestationJson: data.hwAttestationJson.present
          ? data.hwAttestationJson.value
          : this.hwAttestationJson,
      kilnType: data.kilnType.present ? data.kilnType.value : this.kilnType,
      kilnId: data.kilnId.present ? data.kilnId.value : this.kilnId,
      flameHeightM: data.flameHeightM.present
          ? data.flameHeightM.value
          : this.flameHeightM,
      ignitionEnergyType: data.ignitionEnergyType.present
          ? data.ignitionEnergyType.value
          : this.ignitionEnergyType,
      ignitionEnergyAmount: data.ignitionEnergyAmount.present
          ? data.ignitionEnergyAmount.value
          : this.ignitionEnergyAmount,
    );
  }

  @override
  String toString() {
    return (StringBuffer('PyrolysisTelemetryData(')
          ..write('telemetryUuid: $telemetryUuid, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('kilnGrossCapacity: $kilnGrossCapacity, ')
          ..write('burnStartTimestamp: $burnStartTimestamp, ')
          ..write('burnEndTimestamp: $burnEndTimestamp, ')
          ..write('minTemp: $minTemp, ')
          ..write('maxTemp: $maxTemp, ')
          ..write('temperatureReadingsJson: $temperatureReadingsJson, ')
          ..write('smokeEvidenceJson: $smokeEvidenceJson, ')
          ..write('azimuth: $azimuth, ')
          ..write('pitch: $pitch, ')
          ..write('roll: $roll, ')
          ..write('hwAttestationJson: $hwAttestationJson, ')
          ..write('kilnType: $kilnType, ')
          ..write('kilnId: $kilnId, ')
          ..write('flameHeightM: $flameHeightM, ')
          ..write('ignitionEnergyType: $ignitionEnergyType, ')
          ..write('ignitionEnergyAmount: $ignitionEnergyAmount')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    telemetryUuid,
    batchUuid,
    kilnGrossCapacity,
    burnStartTimestamp,
    burnEndTimestamp,
    minTemp,
    maxTemp,
    temperatureReadingsJson,
    smokeEvidenceJson,
    azimuth,
    pitch,
    roll,
    hwAttestationJson,
    kilnType,
    kilnId,
    flameHeightM,
    ignitionEnergyType,
    ignitionEnergyAmount,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is PyrolysisTelemetryData &&
          other.telemetryUuid == this.telemetryUuid &&
          other.batchUuid == this.batchUuid &&
          other.kilnGrossCapacity == this.kilnGrossCapacity &&
          other.burnStartTimestamp == this.burnStartTimestamp &&
          other.burnEndTimestamp == this.burnEndTimestamp &&
          other.minTemp == this.minTemp &&
          other.maxTemp == this.maxTemp &&
          other.temperatureReadingsJson == this.temperatureReadingsJson &&
          other.smokeEvidenceJson == this.smokeEvidenceJson &&
          other.azimuth == this.azimuth &&
          other.pitch == this.pitch &&
          other.roll == this.roll &&
          other.hwAttestationJson == this.hwAttestationJson &&
          other.kilnType == this.kilnType &&
          other.kilnId == this.kilnId &&
          other.flameHeightM == this.flameHeightM &&
          other.ignitionEnergyType == this.ignitionEnergyType &&
          other.ignitionEnergyAmount == this.ignitionEnergyAmount);
}

class PyrolysisTelemetryCompanion
    extends UpdateCompanion<PyrolysisTelemetryData> {
  final Value<String> telemetryUuid;
  final Value<String> batchUuid;
  final Value<double> kilnGrossCapacity;
  final Value<String> burnStartTimestamp;
  final Value<String?> burnEndTimestamp;
  final Value<double> minTemp;
  final Value<double> maxTemp;
  final Value<String> temperatureReadingsJson;
  final Value<String> smokeEvidenceJson;
  final Value<double?> azimuth;
  final Value<double?> pitch;
  final Value<double?> roll;
  final Value<String> hwAttestationJson;
  final Value<String?> kilnType;
  final Value<String?> kilnId;
  final Value<double?> flameHeightM;
  final Value<String?> ignitionEnergyType;
  final Value<double?> ignitionEnergyAmount;
  final Value<int> rowid;
  const PyrolysisTelemetryCompanion({
    this.telemetryUuid = const Value.absent(),
    this.batchUuid = const Value.absent(),
    this.kilnGrossCapacity = const Value.absent(),
    this.burnStartTimestamp = const Value.absent(),
    this.burnEndTimestamp = const Value.absent(),
    this.minTemp = const Value.absent(),
    this.maxTemp = const Value.absent(),
    this.temperatureReadingsJson = const Value.absent(),
    this.smokeEvidenceJson = const Value.absent(),
    this.azimuth = const Value.absent(),
    this.pitch = const Value.absent(),
    this.roll = const Value.absent(),
    this.hwAttestationJson = const Value.absent(),
    this.kilnType = const Value.absent(),
    this.kilnId = const Value.absent(),
    this.flameHeightM = const Value.absent(),
    this.ignitionEnergyType = const Value.absent(),
    this.ignitionEnergyAmount = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  PyrolysisTelemetryCompanion.insert({
    required String telemetryUuid,
    required String batchUuid,
    required double kilnGrossCapacity,
    required String burnStartTimestamp,
    this.burnEndTimestamp = const Value.absent(),
    required double minTemp,
    required double maxTemp,
    this.temperatureReadingsJson = const Value.absent(),
    this.smokeEvidenceJson = const Value.absent(),
    this.azimuth = const Value.absent(),
    this.pitch = const Value.absent(),
    this.roll = const Value.absent(),
    this.hwAttestationJson = const Value.absent(),
    this.kilnType = const Value.absent(),
    this.kilnId = const Value.absent(),
    this.flameHeightM = const Value.absent(),
    this.ignitionEnergyType = const Value.absent(),
    this.ignitionEnergyAmount = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : telemetryUuid = Value(telemetryUuid),
       batchUuid = Value(batchUuid),
       kilnGrossCapacity = Value(kilnGrossCapacity),
       burnStartTimestamp = Value(burnStartTimestamp),
       minTemp = Value(minTemp),
       maxTemp = Value(maxTemp);
  static Insertable<PyrolysisTelemetryData> custom({
    Expression<String>? telemetryUuid,
    Expression<String>? batchUuid,
    Expression<double>? kilnGrossCapacity,
    Expression<String>? burnStartTimestamp,
    Expression<String>? burnEndTimestamp,
    Expression<double>? minTemp,
    Expression<double>? maxTemp,
    Expression<String>? temperatureReadingsJson,
    Expression<String>? smokeEvidenceJson,
    Expression<double>? azimuth,
    Expression<double>? pitch,
    Expression<double>? roll,
    Expression<String>? hwAttestationJson,
    Expression<String>? kilnType,
    Expression<String>? kilnId,
    Expression<double>? flameHeightM,
    Expression<String>? ignitionEnergyType,
    Expression<double>? ignitionEnergyAmount,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (telemetryUuid != null) 'telemetry_uuid': telemetryUuid,
      if (batchUuid != null) 'batch_uuid': batchUuid,
      if (kilnGrossCapacity != null) 'kiln_gross_capacity': kilnGrossCapacity,
      if (burnStartTimestamp != null)
        'burn_start_timestamp': burnStartTimestamp,
      if (burnEndTimestamp != null) 'burn_end_timestamp': burnEndTimestamp,
      if (minTemp != null) 'min_temp': minTemp,
      if (maxTemp != null) 'max_temp': maxTemp,
      if (temperatureReadingsJson != null)
        'temperature_readings_json': temperatureReadingsJson,
      if (smokeEvidenceJson != null) 'smoke_evidence_json': smokeEvidenceJson,
      if (azimuth != null) 'azimuth': azimuth,
      if (pitch != null) 'pitch': pitch,
      if (roll != null) 'roll': roll,
      if (hwAttestationJson != null) 'hw_attestation_json': hwAttestationJson,
      if (kilnType != null) 'kiln_type': kilnType,
      if (kilnId != null) 'kiln_id': kilnId,
      if (flameHeightM != null) 'flame_height_m': flameHeightM,
      if (ignitionEnergyType != null)
        'ignition_energy_type': ignitionEnergyType,
      if (ignitionEnergyAmount != null)
        'ignition_energy_amount': ignitionEnergyAmount,
      if (rowid != null) 'rowid': rowid,
    });
  }

  PyrolysisTelemetryCompanion copyWith({
    Value<String>? telemetryUuid,
    Value<String>? batchUuid,
    Value<double>? kilnGrossCapacity,
    Value<String>? burnStartTimestamp,
    Value<String?>? burnEndTimestamp,
    Value<double>? minTemp,
    Value<double>? maxTemp,
    Value<String>? temperatureReadingsJson,
    Value<String>? smokeEvidenceJson,
    Value<double?>? azimuth,
    Value<double?>? pitch,
    Value<double?>? roll,
    Value<String>? hwAttestationJson,
    Value<String?>? kilnType,
    Value<String?>? kilnId,
    Value<double?>? flameHeightM,
    Value<String?>? ignitionEnergyType,
    Value<double?>? ignitionEnergyAmount,
    Value<int>? rowid,
  }) {
    return PyrolysisTelemetryCompanion(
      telemetryUuid: telemetryUuid ?? this.telemetryUuid,
      batchUuid: batchUuid ?? this.batchUuid,
      kilnGrossCapacity: kilnGrossCapacity ?? this.kilnGrossCapacity,
      burnStartTimestamp: burnStartTimestamp ?? this.burnStartTimestamp,
      burnEndTimestamp: burnEndTimestamp ?? this.burnEndTimestamp,
      minTemp: minTemp ?? this.minTemp,
      maxTemp: maxTemp ?? this.maxTemp,
      temperatureReadingsJson:
          temperatureReadingsJson ?? this.temperatureReadingsJson,
      smokeEvidenceJson: smokeEvidenceJson ?? this.smokeEvidenceJson,
      azimuth: azimuth ?? this.azimuth,
      pitch: pitch ?? this.pitch,
      roll: roll ?? this.roll,
      hwAttestationJson: hwAttestationJson ?? this.hwAttestationJson,
      kilnType: kilnType ?? this.kilnType,
      kilnId: kilnId ?? this.kilnId,
      flameHeightM: flameHeightM ?? this.flameHeightM,
      ignitionEnergyType: ignitionEnergyType ?? this.ignitionEnergyType,
      ignitionEnergyAmount: ignitionEnergyAmount ?? this.ignitionEnergyAmount,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (telemetryUuid.present) {
      map['telemetry_uuid'] = Variable<String>(telemetryUuid.value);
    }
    if (batchUuid.present) {
      map['batch_uuid'] = Variable<String>(batchUuid.value);
    }
    if (kilnGrossCapacity.present) {
      map['kiln_gross_capacity'] = Variable<double>(kilnGrossCapacity.value);
    }
    if (burnStartTimestamp.present) {
      map['burn_start_timestamp'] = Variable<String>(burnStartTimestamp.value);
    }
    if (burnEndTimestamp.present) {
      map['burn_end_timestamp'] = Variable<String>(burnEndTimestamp.value);
    }
    if (minTemp.present) {
      map['min_temp'] = Variable<double>(minTemp.value);
    }
    if (maxTemp.present) {
      map['max_temp'] = Variable<double>(maxTemp.value);
    }
    if (temperatureReadingsJson.present) {
      map['temperature_readings_json'] = Variable<String>(
        temperatureReadingsJson.value,
      );
    }
    if (smokeEvidenceJson.present) {
      map['smoke_evidence_json'] = Variable<String>(smokeEvidenceJson.value);
    }
    if (azimuth.present) {
      map['azimuth'] = Variable<double>(azimuth.value);
    }
    if (pitch.present) {
      map['pitch'] = Variable<double>(pitch.value);
    }
    if (roll.present) {
      map['roll'] = Variable<double>(roll.value);
    }
    if (hwAttestationJson.present) {
      map['hw_attestation_json'] = Variable<String>(hwAttestationJson.value);
    }
    if (kilnType.present) {
      map['kiln_type'] = Variable<String>(kilnType.value);
    }
    if (kilnId.present) {
      map['kiln_id'] = Variable<String>(kilnId.value);
    }
    if (flameHeightM.present) {
      map['flame_height_m'] = Variable<double>(flameHeightM.value);
    }
    if (ignitionEnergyType.present) {
      map['ignition_energy_type'] = Variable<String>(ignitionEnergyType.value);
    }
    if (ignitionEnergyAmount.present) {
      map['ignition_energy_amount'] = Variable<double>(
        ignitionEnergyAmount.value,
      );
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('PyrolysisTelemetryCompanion(')
          ..write('telemetryUuid: $telemetryUuid, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('kilnGrossCapacity: $kilnGrossCapacity, ')
          ..write('burnStartTimestamp: $burnStartTimestamp, ')
          ..write('burnEndTimestamp: $burnEndTimestamp, ')
          ..write('minTemp: $minTemp, ')
          ..write('maxTemp: $maxTemp, ')
          ..write('temperatureReadingsJson: $temperatureReadingsJson, ')
          ..write('smokeEvidenceJson: $smokeEvidenceJson, ')
          ..write('azimuth: $azimuth, ')
          ..write('pitch: $pitch, ')
          ..write('roll: $roll, ')
          ..write('hwAttestationJson: $hwAttestationJson, ')
          ..write('kilnType: $kilnType, ')
          ..write('kilnId: $kilnId, ')
          ..write('flameHeightM: $flameHeightM, ')
          ..write('ignitionEnergyType: $ignitionEnergyType, ')
          ..write('ignitionEnergyAmount: $ignitionEnergyAmount, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $YieldMetricsTable extends YieldMetrics
    with TableInfo<$YieldMetricsTable, YieldMetric> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $YieldMetricsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _yieldUuidMeta = const VerificationMeta(
    'yieldUuid',
  );
  @override
  late final GeneratedColumn<String> yieldUuid = GeneratedColumn<String>(
    'yield_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _batchUuidMeta = const VerificationMeta(
    'batchUuid',
  );
  @override
  late final GeneratedColumn<String> batchUuid = GeneratedColumn<String>(
    'batch_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES system_metadata (batch_uuid)',
    ),
  );
  static const VerificationMeta _quenchMethodologyMeta = const VerificationMeta(
    'quenchMethodology',
  );
  @override
  late final GeneratedColumn<String> quenchMethodology =
      GeneratedColumn<String>(
        'quench_methodology',
        aliasedName,
        false,
        type: DriftSqlType.string,
        requiredDuringInsert: true,
      );
  static const VerificationMeta _grossVolumeMeta = const VerificationMeta(
    'grossVolume',
  );
  @override
  late final GeneratedColumn<double> grossVolume = GeneratedColumn<double>(
    'gross_volume',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _wetYieldWeightKgMeta = const VerificationMeta(
    'wetYieldWeightKg',
  );
  @override
  late final GeneratedColumn<double> wetYieldWeightKg = GeneratedColumn<double>(
    'wet_yield_weight_kg',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _dryYieldWeightKgMeta = const VerificationMeta(
    'dryYieldWeightKg',
  );
  @override
  late final GeneratedColumn<double> dryYieldWeightKg = GeneratedColumn<double>(
    'dry_yield_weight_kg',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    yieldUuid,
    batchUuid,
    quenchMethodology,
    grossVolume,
    wetYieldWeightKg,
    dryYieldWeightKg,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'yield_metrics';
  @override
  VerificationContext validateIntegrity(
    Insertable<YieldMetric> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('yield_uuid')) {
      context.handle(
        _yieldUuidMeta,
        yieldUuid.isAcceptableOrUnknown(data['yield_uuid']!, _yieldUuidMeta),
      );
    } else if (isInserting) {
      context.missing(_yieldUuidMeta);
    }
    if (data.containsKey('batch_uuid')) {
      context.handle(
        _batchUuidMeta,
        batchUuid.isAcceptableOrUnknown(data['batch_uuid']!, _batchUuidMeta),
      );
    } else if (isInserting) {
      context.missing(_batchUuidMeta);
    }
    if (data.containsKey('quench_methodology')) {
      context.handle(
        _quenchMethodologyMeta,
        quenchMethodology.isAcceptableOrUnknown(
          data['quench_methodology']!,
          _quenchMethodologyMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_quenchMethodologyMeta);
    }
    if (data.containsKey('gross_volume')) {
      context.handle(
        _grossVolumeMeta,
        grossVolume.isAcceptableOrUnknown(
          data['gross_volume']!,
          _grossVolumeMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_grossVolumeMeta);
    }
    if (data.containsKey('wet_yield_weight_kg')) {
      context.handle(
        _wetYieldWeightKgMeta,
        wetYieldWeightKg.isAcceptableOrUnknown(
          data['wet_yield_weight_kg']!,
          _wetYieldWeightKgMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_wetYieldWeightKgMeta);
    }
    if (data.containsKey('dry_yield_weight_kg')) {
      context.handle(
        _dryYieldWeightKgMeta,
        dryYieldWeightKg.isAcceptableOrUnknown(
          data['dry_yield_weight_kg']!,
          _dryYieldWeightKgMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {yieldUuid};
  @override
  List<Set<GeneratedColumn>> get uniqueKeys => [
    {batchUuid},
  ];
  @override
  YieldMetric map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return YieldMetric(
      yieldUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}yield_uuid'],
      )!,
      batchUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}batch_uuid'],
      )!,
      quenchMethodology: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}quench_methodology'],
      )!,
      grossVolume: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}gross_volume'],
      )!,
      wetYieldWeightKg: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}wet_yield_weight_kg'],
      )!,
      dryYieldWeightKg: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}dry_yield_weight_kg'],
      ),
    );
  }

  @override
  $YieldMetricsTable createAlias(String alias) {
    return $YieldMetricsTable(attachedDatabase, alias);
  }
}

class YieldMetric extends DataClass implements Insertable<YieldMetric> {
  final String yieldUuid;
  final String batchUuid;
  final String quenchMethodology;
  final double grossVolume;
  final double wetYieldWeightKg;
  final double? dryYieldWeightKg;
  const YieldMetric({
    required this.yieldUuid,
    required this.batchUuid,
    required this.quenchMethodology,
    required this.grossVolume,
    required this.wetYieldWeightKg,
    this.dryYieldWeightKg,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['yield_uuid'] = Variable<String>(yieldUuid);
    map['batch_uuid'] = Variable<String>(batchUuid);
    map['quench_methodology'] = Variable<String>(quenchMethodology);
    map['gross_volume'] = Variable<double>(grossVolume);
    map['wet_yield_weight_kg'] = Variable<double>(wetYieldWeightKg);
    if (!nullToAbsent || dryYieldWeightKg != null) {
      map['dry_yield_weight_kg'] = Variable<double>(dryYieldWeightKg);
    }
    return map;
  }

  YieldMetricsCompanion toCompanion(bool nullToAbsent) {
    return YieldMetricsCompanion(
      yieldUuid: Value(yieldUuid),
      batchUuid: Value(batchUuid),
      quenchMethodology: Value(quenchMethodology),
      grossVolume: Value(grossVolume),
      wetYieldWeightKg: Value(wetYieldWeightKg),
      dryYieldWeightKg: dryYieldWeightKg == null && nullToAbsent
          ? const Value.absent()
          : Value(dryYieldWeightKg),
    );
  }

  factory YieldMetric.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return YieldMetric(
      yieldUuid: serializer.fromJson<String>(json['yieldUuid']),
      batchUuid: serializer.fromJson<String>(json['batchUuid']),
      quenchMethodology: serializer.fromJson<String>(json['quenchMethodology']),
      grossVolume: serializer.fromJson<double>(json['grossVolume']),
      wetYieldWeightKg: serializer.fromJson<double>(json['wetYieldWeightKg']),
      dryYieldWeightKg: serializer.fromJson<double?>(json['dryYieldWeightKg']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'yieldUuid': serializer.toJson<String>(yieldUuid),
      'batchUuid': serializer.toJson<String>(batchUuid),
      'quenchMethodology': serializer.toJson<String>(quenchMethodology),
      'grossVolume': serializer.toJson<double>(grossVolume),
      'wetYieldWeightKg': serializer.toJson<double>(wetYieldWeightKg),
      'dryYieldWeightKg': serializer.toJson<double?>(dryYieldWeightKg),
    };
  }

  YieldMetric copyWith({
    String? yieldUuid,
    String? batchUuid,
    String? quenchMethodology,
    double? grossVolume,
    double? wetYieldWeightKg,
    Value<double?> dryYieldWeightKg = const Value.absent(),
  }) => YieldMetric(
    yieldUuid: yieldUuid ?? this.yieldUuid,
    batchUuid: batchUuid ?? this.batchUuid,
    quenchMethodology: quenchMethodology ?? this.quenchMethodology,
    grossVolume: grossVolume ?? this.grossVolume,
    wetYieldWeightKg: wetYieldWeightKg ?? this.wetYieldWeightKg,
    dryYieldWeightKg: dryYieldWeightKg.present
        ? dryYieldWeightKg.value
        : this.dryYieldWeightKg,
  );
  YieldMetric copyWithCompanion(YieldMetricsCompanion data) {
    return YieldMetric(
      yieldUuid: data.yieldUuid.present ? data.yieldUuid.value : this.yieldUuid,
      batchUuid: data.batchUuid.present ? data.batchUuid.value : this.batchUuid,
      quenchMethodology: data.quenchMethodology.present
          ? data.quenchMethodology.value
          : this.quenchMethodology,
      grossVolume: data.grossVolume.present
          ? data.grossVolume.value
          : this.grossVolume,
      wetYieldWeightKg: data.wetYieldWeightKg.present
          ? data.wetYieldWeightKg.value
          : this.wetYieldWeightKg,
      dryYieldWeightKg: data.dryYieldWeightKg.present
          ? data.dryYieldWeightKg.value
          : this.dryYieldWeightKg,
    );
  }

  @override
  String toString() {
    return (StringBuffer('YieldMetric(')
          ..write('yieldUuid: $yieldUuid, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('quenchMethodology: $quenchMethodology, ')
          ..write('grossVolume: $grossVolume, ')
          ..write('wetYieldWeightKg: $wetYieldWeightKg, ')
          ..write('dryYieldWeightKg: $dryYieldWeightKg')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    yieldUuid,
    batchUuid,
    quenchMethodology,
    grossVolume,
    wetYieldWeightKg,
    dryYieldWeightKg,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is YieldMetric &&
          other.yieldUuid == this.yieldUuid &&
          other.batchUuid == this.batchUuid &&
          other.quenchMethodology == this.quenchMethodology &&
          other.grossVolume == this.grossVolume &&
          other.wetYieldWeightKg == this.wetYieldWeightKg &&
          other.dryYieldWeightKg == this.dryYieldWeightKg);
}

class YieldMetricsCompanion extends UpdateCompanion<YieldMetric> {
  final Value<String> yieldUuid;
  final Value<String> batchUuid;
  final Value<String> quenchMethodology;
  final Value<double> grossVolume;
  final Value<double> wetYieldWeightKg;
  final Value<double?> dryYieldWeightKg;
  final Value<int> rowid;
  const YieldMetricsCompanion({
    this.yieldUuid = const Value.absent(),
    this.batchUuid = const Value.absent(),
    this.quenchMethodology = const Value.absent(),
    this.grossVolume = const Value.absent(),
    this.wetYieldWeightKg = const Value.absent(),
    this.dryYieldWeightKg = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  YieldMetricsCompanion.insert({
    required String yieldUuid,
    required String batchUuid,
    required String quenchMethodology,
    required double grossVolume,
    required double wetYieldWeightKg,
    this.dryYieldWeightKg = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : yieldUuid = Value(yieldUuid),
       batchUuid = Value(batchUuid),
       quenchMethodology = Value(quenchMethodology),
       grossVolume = Value(grossVolume),
       wetYieldWeightKg = Value(wetYieldWeightKg);
  static Insertable<YieldMetric> custom({
    Expression<String>? yieldUuid,
    Expression<String>? batchUuid,
    Expression<String>? quenchMethodology,
    Expression<double>? grossVolume,
    Expression<double>? wetYieldWeightKg,
    Expression<double>? dryYieldWeightKg,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (yieldUuid != null) 'yield_uuid': yieldUuid,
      if (batchUuid != null) 'batch_uuid': batchUuid,
      if (quenchMethodology != null) 'quench_methodology': quenchMethodology,
      if (grossVolume != null) 'gross_volume': grossVolume,
      if (wetYieldWeightKg != null) 'wet_yield_weight_kg': wetYieldWeightKg,
      if (dryYieldWeightKg != null) 'dry_yield_weight_kg': dryYieldWeightKg,
      if (rowid != null) 'rowid': rowid,
    });
  }

  YieldMetricsCompanion copyWith({
    Value<String>? yieldUuid,
    Value<String>? batchUuid,
    Value<String>? quenchMethodology,
    Value<double>? grossVolume,
    Value<double>? wetYieldWeightKg,
    Value<double?>? dryYieldWeightKg,
    Value<int>? rowid,
  }) {
    return YieldMetricsCompanion(
      yieldUuid: yieldUuid ?? this.yieldUuid,
      batchUuid: batchUuid ?? this.batchUuid,
      quenchMethodology: quenchMethodology ?? this.quenchMethodology,
      grossVolume: grossVolume ?? this.grossVolume,
      wetYieldWeightKg: wetYieldWeightKg ?? this.wetYieldWeightKg,
      dryYieldWeightKg: dryYieldWeightKg ?? this.dryYieldWeightKg,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (yieldUuid.present) {
      map['yield_uuid'] = Variable<String>(yieldUuid.value);
    }
    if (batchUuid.present) {
      map['batch_uuid'] = Variable<String>(batchUuid.value);
    }
    if (quenchMethodology.present) {
      map['quench_methodology'] = Variable<String>(quenchMethodology.value);
    }
    if (grossVolume.present) {
      map['gross_volume'] = Variable<double>(grossVolume.value);
    }
    if (wetYieldWeightKg.present) {
      map['wet_yield_weight_kg'] = Variable<double>(wetYieldWeightKg.value);
    }
    if (dryYieldWeightKg.present) {
      map['dry_yield_weight_kg'] = Variable<double>(dryYieldWeightKg.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('YieldMetricsCompanion(')
          ..write('yieldUuid: $yieldUuid, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('quenchMethodology: $quenchMethodology, ')
          ..write('grossVolume: $grossVolume, ')
          ..write('wetYieldWeightKg: $wetYieldWeightKg, ')
          ..write('dryYieldWeightKg: $dryYieldWeightKg, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $EndUseApplicationTable extends EndUseApplication
    with TableInfo<$EndUseApplicationTable, EndUseApplicationData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $EndUseApplicationTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _applicationUuidMeta = const VerificationMeta(
    'applicationUuid',
  );
  @override
  late final GeneratedColumn<String> applicationUuid = GeneratedColumn<String>(
    'application_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _batchUuidMeta = const VerificationMeta(
    'batchUuid',
  );
  @override
  late final GeneratedColumn<String> batchUuid = GeneratedColumn<String>(
    'batch_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES system_metadata (batch_uuid)',
    ),
  );
  static const VerificationMeta _applicationMethodologyMeta =
      const VerificationMeta('applicationMethodology');
  @override
  late final GeneratedColumn<String> applicationMethodology =
      GeneratedColumn<String>(
        'application_methodology',
        aliasedName,
        false,
        type: DriftSqlType.string,
        requiredDuringInsert: true,
      );
  static const VerificationMeta _applicationRateMeta = const VerificationMeta(
    'applicationRate',
  );
  @override
  late final GeneratedColumn<double> applicationRate = GeneratedColumn<double>(
    'application_rate',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _transportDistanceKmMeta =
      const VerificationMeta('transportDistanceKm');
  @override
  late final GeneratedColumn<double> transportDistanceKm =
      GeneratedColumn<double>(
        'transport_distance_km',
        aliasedName,
        false,
        type: DriftSqlType.double,
        requiredDuringInsert: true,
      );
  static const VerificationMeta _latitudeMeta = const VerificationMeta(
    'latitude',
  );
  @override
  late final GeneratedColumn<double> latitude = GeneratedColumn<double>(
    'latitude',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _longitudeMeta = const VerificationMeta(
    'longitude',
  );
  @override
  late final GeneratedColumn<double> longitude = GeneratedColumn<double>(
    'longitude',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _farmerPhotoPathMeta = const VerificationMeta(
    'farmerPhotoPath',
  );
  @override
  late final GeneratedColumn<String> farmerPhotoPath = GeneratedColumn<String>(
    'farmer_photo_path',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _farmerPhotoSha256Meta = const VerificationMeta(
    'farmerPhotoSha256',
  );
  @override
  late final GeneratedColumn<String> farmerPhotoSha256 =
      GeneratedColumn<String>(
        'farmer_photo_sha256',
        aliasedName,
        true,
        type: DriftSqlType.string,
        requiredDuringInsert: false,
      );
  static const VerificationMeta _deliveryDateMeta = const VerificationMeta(
    'deliveryDate',
  );
  @override
  late final GeneratedColumn<String> deliveryDate = GeneratedColumn<String>(
    'delivery_date',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _deliveredAmountKgMeta = const VerificationMeta(
    'deliveredAmountKg',
  );
  @override
  late final GeneratedColumn<double> deliveredAmountKg =
      GeneratedColumn<double>(
        'delivered_amount_kg',
        aliasedName,
        true,
        type: DriftSqlType.double,
        requiredDuringInsert: false,
      );
  static const VerificationMeta _buyerNameMeta = const VerificationMeta(
    'buyerName',
  );
  @override
  late final GeneratedColumn<String> buyerName = GeneratedColumn<String>(
    'buyer_name',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _buyerContactMeta = const VerificationMeta(
    'buyerContact',
  );
  @override
  late final GeneratedColumn<String> buyerContact = GeneratedColumn<String>(
    'buyer_contact',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    applicationUuid,
    batchUuid,
    applicationMethodology,
    applicationRate,
    transportDistanceKm,
    latitude,
    longitude,
    farmerPhotoPath,
    farmerPhotoSha256,
    deliveryDate,
    deliveredAmountKg,
    buyerName,
    buyerContact,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'end_use_application';
  @override
  VerificationContext validateIntegrity(
    Insertable<EndUseApplicationData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('application_uuid')) {
      context.handle(
        _applicationUuidMeta,
        applicationUuid.isAcceptableOrUnknown(
          data['application_uuid']!,
          _applicationUuidMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_applicationUuidMeta);
    }
    if (data.containsKey('batch_uuid')) {
      context.handle(
        _batchUuidMeta,
        batchUuid.isAcceptableOrUnknown(data['batch_uuid']!, _batchUuidMeta),
      );
    } else if (isInserting) {
      context.missing(_batchUuidMeta);
    }
    if (data.containsKey('application_methodology')) {
      context.handle(
        _applicationMethodologyMeta,
        applicationMethodology.isAcceptableOrUnknown(
          data['application_methodology']!,
          _applicationMethodologyMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_applicationMethodologyMeta);
    }
    if (data.containsKey('application_rate')) {
      context.handle(
        _applicationRateMeta,
        applicationRate.isAcceptableOrUnknown(
          data['application_rate']!,
          _applicationRateMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_applicationRateMeta);
    }
    if (data.containsKey('transport_distance_km')) {
      context.handle(
        _transportDistanceKmMeta,
        transportDistanceKm.isAcceptableOrUnknown(
          data['transport_distance_km']!,
          _transportDistanceKmMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_transportDistanceKmMeta);
    }
    if (data.containsKey('latitude')) {
      context.handle(
        _latitudeMeta,
        latitude.isAcceptableOrUnknown(data['latitude']!, _latitudeMeta),
      );
    }
    if (data.containsKey('longitude')) {
      context.handle(
        _longitudeMeta,
        longitude.isAcceptableOrUnknown(data['longitude']!, _longitudeMeta),
      );
    }
    if (data.containsKey('farmer_photo_path')) {
      context.handle(
        _farmerPhotoPathMeta,
        farmerPhotoPath.isAcceptableOrUnknown(
          data['farmer_photo_path']!,
          _farmerPhotoPathMeta,
        ),
      );
    }
    if (data.containsKey('farmer_photo_sha256')) {
      context.handle(
        _farmerPhotoSha256Meta,
        farmerPhotoSha256.isAcceptableOrUnknown(
          data['farmer_photo_sha256']!,
          _farmerPhotoSha256Meta,
        ),
      );
    }
    if (data.containsKey('delivery_date')) {
      context.handle(
        _deliveryDateMeta,
        deliveryDate.isAcceptableOrUnknown(
          data['delivery_date']!,
          _deliveryDateMeta,
        ),
      );
    }
    if (data.containsKey('delivered_amount_kg')) {
      context.handle(
        _deliveredAmountKgMeta,
        deliveredAmountKg.isAcceptableOrUnknown(
          data['delivered_amount_kg']!,
          _deliveredAmountKgMeta,
        ),
      );
    }
    if (data.containsKey('buyer_name')) {
      context.handle(
        _buyerNameMeta,
        buyerName.isAcceptableOrUnknown(data['buyer_name']!, _buyerNameMeta),
      );
    }
    if (data.containsKey('buyer_contact')) {
      context.handle(
        _buyerContactMeta,
        buyerContact.isAcceptableOrUnknown(
          data['buyer_contact']!,
          _buyerContactMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {applicationUuid};
  @override
  List<Set<GeneratedColumn>> get uniqueKeys => [
    {batchUuid},
  ];
  @override
  EndUseApplicationData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return EndUseApplicationData(
      applicationUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}application_uuid'],
      )!,
      batchUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}batch_uuid'],
      )!,
      applicationMethodology: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}application_methodology'],
      )!,
      applicationRate: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}application_rate'],
      )!,
      transportDistanceKm: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}transport_distance_km'],
      )!,
      latitude: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}latitude'],
      ),
      longitude: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}longitude'],
      ),
      farmerPhotoPath: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}farmer_photo_path'],
      ),
      farmerPhotoSha256: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}farmer_photo_sha256'],
      ),
      deliveryDate: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}delivery_date'],
      ),
      deliveredAmountKg: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}delivered_amount_kg'],
      ),
      buyerName: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}buyer_name'],
      ),
      buyerContact: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}buyer_contact'],
      ),
    );
  }

  @override
  $EndUseApplicationTable createAlias(String alias) {
    return $EndUseApplicationTable(attachedDatabase, alias);
  }
}

class EndUseApplicationData extends DataClass
    implements Insertable<EndUseApplicationData> {
  final String applicationUuid;
  final String batchUuid;
  final String applicationMethodology;
  final double applicationRate;
  final double transportDistanceKm;
  final double? latitude;
  final double? longitude;
  final String? farmerPhotoPath;
  final String? farmerPhotoSha256;

  /// When the biochar was delivered to the end user (ISO-8601 UTC).
  final String? deliveryDate;

  /// Mass delivered (kg) — the delivery-tracking amount for this batch.
  final double? deliveredAmountKg;

  /// Buyer / end-user identity. PII — lives only in the SQLCipher DB and is
  /// scrubbed by secureWipe.
  final String? buyerName;
  final String? buyerContact;
  const EndUseApplicationData({
    required this.applicationUuid,
    required this.batchUuid,
    required this.applicationMethodology,
    required this.applicationRate,
    required this.transportDistanceKm,
    this.latitude,
    this.longitude,
    this.farmerPhotoPath,
    this.farmerPhotoSha256,
    this.deliveryDate,
    this.deliveredAmountKg,
    this.buyerName,
    this.buyerContact,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['application_uuid'] = Variable<String>(applicationUuid);
    map['batch_uuid'] = Variable<String>(batchUuid);
    map['application_methodology'] = Variable<String>(applicationMethodology);
    map['application_rate'] = Variable<double>(applicationRate);
    map['transport_distance_km'] = Variable<double>(transportDistanceKm);
    if (!nullToAbsent || latitude != null) {
      map['latitude'] = Variable<double>(latitude);
    }
    if (!nullToAbsent || longitude != null) {
      map['longitude'] = Variable<double>(longitude);
    }
    if (!nullToAbsent || farmerPhotoPath != null) {
      map['farmer_photo_path'] = Variable<String>(farmerPhotoPath);
    }
    if (!nullToAbsent || farmerPhotoSha256 != null) {
      map['farmer_photo_sha256'] = Variable<String>(farmerPhotoSha256);
    }
    if (!nullToAbsent || deliveryDate != null) {
      map['delivery_date'] = Variable<String>(deliveryDate);
    }
    if (!nullToAbsent || deliveredAmountKg != null) {
      map['delivered_amount_kg'] = Variable<double>(deliveredAmountKg);
    }
    if (!nullToAbsent || buyerName != null) {
      map['buyer_name'] = Variable<String>(buyerName);
    }
    if (!nullToAbsent || buyerContact != null) {
      map['buyer_contact'] = Variable<String>(buyerContact);
    }
    return map;
  }

  EndUseApplicationCompanion toCompanion(bool nullToAbsent) {
    return EndUseApplicationCompanion(
      applicationUuid: Value(applicationUuid),
      batchUuid: Value(batchUuid),
      applicationMethodology: Value(applicationMethodology),
      applicationRate: Value(applicationRate),
      transportDistanceKm: Value(transportDistanceKm),
      latitude: latitude == null && nullToAbsent
          ? const Value.absent()
          : Value(latitude),
      longitude: longitude == null && nullToAbsent
          ? const Value.absent()
          : Value(longitude),
      farmerPhotoPath: farmerPhotoPath == null && nullToAbsent
          ? const Value.absent()
          : Value(farmerPhotoPath),
      farmerPhotoSha256: farmerPhotoSha256 == null && nullToAbsent
          ? const Value.absent()
          : Value(farmerPhotoSha256),
      deliveryDate: deliveryDate == null && nullToAbsent
          ? const Value.absent()
          : Value(deliveryDate),
      deliveredAmountKg: deliveredAmountKg == null && nullToAbsent
          ? const Value.absent()
          : Value(deliveredAmountKg),
      buyerName: buyerName == null && nullToAbsent
          ? const Value.absent()
          : Value(buyerName),
      buyerContact: buyerContact == null && nullToAbsent
          ? const Value.absent()
          : Value(buyerContact),
    );
  }

  factory EndUseApplicationData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return EndUseApplicationData(
      applicationUuid: serializer.fromJson<String>(json['applicationUuid']),
      batchUuid: serializer.fromJson<String>(json['batchUuid']),
      applicationMethodology: serializer.fromJson<String>(
        json['applicationMethodology'],
      ),
      applicationRate: serializer.fromJson<double>(json['applicationRate']),
      transportDistanceKm: serializer.fromJson<double>(
        json['transportDistanceKm'],
      ),
      latitude: serializer.fromJson<double?>(json['latitude']),
      longitude: serializer.fromJson<double?>(json['longitude']),
      farmerPhotoPath: serializer.fromJson<String?>(json['farmerPhotoPath']),
      farmerPhotoSha256: serializer.fromJson<String?>(
        json['farmerPhotoSha256'],
      ),
      deliveryDate: serializer.fromJson<String?>(json['deliveryDate']),
      deliveredAmountKg: serializer.fromJson<double?>(
        json['deliveredAmountKg'],
      ),
      buyerName: serializer.fromJson<String?>(json['buyerName']),
      buyerContact: serializer.fromJson<String?>(json['buyerContact']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'applicationUuid': serializer.toJson<String>(applicationUuid),
      'batchUuid': serializer.toJson<String>(batchUuid),
      'applicationMethodology': serializer.toJson<String>(
        applicationMethodology,
      ),
      'applicationRate': serializer.toJson<double>(applicationRate),
      'transportDistanceKm': serializer.toJson<double>(transportDistanceKm),
      'latitude': serializer.toJson<double?>(latitude),
      'longitude': serializer.toJson<double?>(longitude),
      'farmerPhotoPath': serializer.toJson<String?>(farmerPhotoPath),
      'farmerPhotoSha256': serializer.toJson<String?>(farmerPhotoSha256),
      'deliveryDate': serializer.toJson<String?>(deliveryDate),
      'deliveredAmountKg': serializer.toJson<double?>(deliveredAmountKg),
      'buyerName': serializer.toJson<String?>(buyerName),
      'buyerContact': serializer.toJson<String?>(buyerContact),
    };
  }

  EndUseApplicationData copyWith({
    String? applicationUuid,
    String? batchUuid,
    String? applicationMethodology,
    double? applicationRate,
    double? transportDistanceKm,
    Value<double?> latitude = const Value.absent(),
    Value<double?> longitude = const Value.absent(),
    Value<String?> farmerPhotoPath = const Value.absent(),
    Value<String?> farmerPhotoSha256 = const Value.absent(),
    Value<String?> deliveryDate = const Value.absent(),
    Value<double?> deliveredAmountKg = const Value.absent(),
    Value<String?> buyerName = const Value.absent(),
    Value<String?> buyerContact = const Value.absent(),
  }) => EndUseApplicationData(
    applicationUuid: applicationUuid ?? this.applicationUuid,
    batchUuid: batchUuid ?? this.batchUuid,
    applicationMethodology:
        applicationMethodology ?? this.applicationMethodology,
    applicationRate: applicationRate ?? this.applicationRate,
    transportDistanceKm: transportDistanceKm ?? this.transportDistanceKm,
    latitude: latitude.present ? latitude.value : this.latitude,
    longitude: longitude.present ? longitude.value : this.longitude,
    farmerPhotoPath: farmerPhotoPath.present
        ? farmerPhotoPath.value
        : this.farmerPhotoPath,
    farmerPhotoSha256: farmerPhotoSha256.present
        ? farmerPhotoSha256.value
        : this.farmerPhotoSha256,
    deliveryDate: deliveryDate.present ? deliveryDate.value : this.deliveryDate,
    deliveredAmountKg: deliveredAmountKg.present
        ? deliveredAmountKg.value
        : this.deliveredAmountKg,
    buyerName: buyerName.present ? buyerName.value : this.buyerName,
    buyerContact: buyerContact.present ? buyerContact.value : this.buyerContact,
  );
  EndUseApplicationData copyWithCompanion(EndUseApplicationCompanion data) {
    return EndUseApplicationData(
      applicationUuid: data.applicationUuid.present
          ? data.applicationUuid.value
          : this.applicationUuid,
      batchUuid: data.batchUuid.present ? data.batchUuid.value : this.batchUuid,
      applicationMethodology: data.applicationMethodology.present
          ? data.applicationMethodology.value
          : this.applicationMethodology,
      applicationRate: data.applicationRate.present
          ? data.applicationRate.value
          : this.applicationRate,
      transportDistanceKm: data.transportDistanceKm.present
          ? data.transportDistanceKm.value
          : this.transportDistanceKm,
      latitude: data.latitude.present ? data.latitude.value : this.latitude,
      longitude: data.longitude.present ? data.longitude.value : this.longitude,
      farmerPhotoPath: data.farmerPhotoPath.present
          ? data.farmerPhotoPath.value
          : this.farmerPhotoPath,
      farmerPhotoSha256: data.farmerPhotoSha256.present
          ? data.farmerPhotoSha256.value
          : this.farmerPhotoSha256,
      deliveryDate: data.deliveryDate.present
          ? data.deliveryDate.value
          : this.deliveryDate,
      deliveredAmountKg: data.deliveredAmountKg.present
          ? data.deliveredAmountKg.value
          : this.deliveredAmountKg,
      buyerName: data.buyerName.present ? data.buyerName.value : this.buyerName,
      buyerContact: data.buyerContact.present
          ? data.buyerContact.value
          : this.buyerContact,
    );
  }

  @override
  String toString() {
    return (StringBuffer('EndUseApplicationData(')
          ..write('applicationUuid: $applicationUuid, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('applicationMethodology: $applicationMethodology, ')
          ..write('applicationRate: $applicationRate, ')
          ..write('transportDistanceKm: $transportDistanceKm, ')
          ..write('latitude: $latitude, ')
          ..write('longitude: $longitude, ')
          ..write('farmerPhotoPath: $farmerPhotoPath, ')
          ..write('farmerPhotoSha256: $farmerPhotoSha256, ')
          ..write('deliveryDate: $deliveryDate, ')
          ..write('deliveredAmountKg: $deliveredAmountKg, ')
          ..write('buyerName: $buyerName, ')
          ..write('buyerContact: $buyerContact')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    applicationUuid,
    batchUuid,
    applicationMethodology,
    applicationRate,
    transportDistanceKm,
    latitude,
    longitude,
    farmerPhotoPath,
    farmerPhotoSha256,
    deliveryDate,
    deliveredAmountKg,
    buyerName,
    buyerContact,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is EndUseApplicationData &&
          other.applicationUuid == this.applicationUuid &&
          other.batchUuid == this.batchUuid &&
          other.applicationMethodology == this.applicationMethodology &&
          other.applicationRate == this.applicationRate &&
          other.transportDistanceKm == this.transportDistanceKm &&
          other.latitude == this.latitude &&
          other.longitude == this.longitude &&
          other.farmerPhotoPath == this.farmerPhotoPath &&
          other.farmerPhotoSha256 == this.farmerPhotoSha256 &&
          other.deliveryDate == this.deliveryDate &&
          other.deliveredAmountKg == this.deliveredAmountKg &&
          other.buyerName == this.buyerName &&
          other.buyerContact == this.buyerContact);
}

class EndUseApplicationCompanion
    extends UpdateCompanion<EndUseApplicationData> {
  final Value<String> applicationUuid;
  final Value<String> batchUuid;
  final Value<String> applicationMethodology;
  final Value<double> applicationRate;
  final Value<double> transportDistanceKm;
  final Value<double?> latitude;
  final Value<double?> longitude;
  final Value<String?> farmerPhotoPath;
  final Value<String?> farmerPhotoSha256;
  final Value<String?> deliveryDate;
  final Value<double?> deliveredAmountKg;
  final Value<String?> buyerName;
  final Value<String?> buyerContact;
  final Value<int> rowid;
  const EndUseApplicationCompanion({
    this.applicationUuid = const Value.absent(),
    this.batchUuid = const Value.absent(),
    this.applicationMethodology = const Value.absent(),
    this.applicationRate = const Value.absent(),
    this.transportDistanceKm = const Value.absent(),
    this.latitude = const Value.absent(),
    this.longitude = const Value.absent(),
    this.farmerPhotoPath = const Value.absent(),
    this.farmerPhotoSha256 = const Value.absent(),
    this.deliveryDate = const Value.absent(),
    this.deliveredAmountKg = const Value.absent(),
    this.buyerName = const Value.absent(),
    this.buyerContact = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  EndUseApplicationCompanion.insert({
    required String applicationUuid,
    required String batchUuid,
    required String applicationMethodology,
    required double applicationRate,
    required double transportDistanceKm,
    this.latitude = const Value.absent(),
    this.longitude = const Value.absent(),
    this.farmerPhotoPath = const Value.absent(),
    this.farmerPhotoSha256 = const Value.absent(),
    this.deliveryDate = const Value.absent(),
    this.deliveredAmountKg = const Value.absent(),
    this.buyerName = const Value.absent(),
    this.buyerContact = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : applicationUuid = Value(applicationUuid),
       batchUuid = Value(batchUuid),
       applicationMethodology = Value(applicationMethodology),
       applicationRate = Value(applicationRate),
       transportDistanceKm = Value(transportDistanceKm);
  static Insertable<EndUseApplicationData> custom({
    Expression<String>? applicationUuid,
    Expression<String>? batchUuid,
    Expression<String>? applicationMethodology,
    Expression<double>? applicationRate,
    Expression<double>? transportDistanceKm,
    Expression<double>? latitude,
    Expression<double>? longitude,
    Expression<String>? farmerPhotoPath,
    Expression<String>? farmerPhotoSha256,
    Expression<String>? deliveryDate,
    Expression<double>? deliveredAmountKg,
    Expression<String>? buyerName,
    Expression<String>? buyerContact,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (applicationUuid != null) 'application_uuid': applicationUuid,
      if (batchUuid != null) 'batch_uuid': batchUuid,
      if (applicationMethodology != null)
        'application_methodology': applicationMethodology,
      if (applicationRate != null) 'application_rate': applicationRate,
      if (transportDistanceKm != null)
        'transport_distance_km': transportDistanceKm,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      if (farmerPhotoPath != null) 'farmer_photo_path': farmerPhotoPath,
      if (farmerPhotoSha256 != null) 'farmer_photo_sha256': farmerPhotoSha256,
      if (deliveryDate != null) 'delivery_date': deliveryDate,
      if (deliveredAmountKg != null) 'delivered_amount_kg': deliveredAmountKg,
      if (buyerName != null) 'buyer_name': buyerName,
      if (buyerContact != null) 'buyer_contact': buyerContact,
      if (rowid != null) 'rowid': rowid,
    });
  }

  EndUseApplicationCompanion copyWith({
    Value<String>? applicationUuid,
    Value<String>? batchUuid,
    Value<String>? applicationMethodology,
    Value<double>? applicationRate,
    Value<double>? transportDistanceKm,
    Value<double?>? latitude,
    Value<double?>? longitude,
    Value<String?>? farmerPhotoPath,
    Value<String?>? farmerPhotoSha256,
    Value<String?>? deliveryDate,
    Value<double?>? deliveredAmountKg,
    Value<String?>? buyerName,
    Value<String?>? buyerContact,
    Value<int>? rowid,
  }) {
    return EndUseApplicationCompanion(
      applicationUuid: applicationUuid ?? this.applicationUuid,
      batchUuid: batchUuid ?? this.batchUuid,
      applicationMethodology:
          applicationMethodology ?? this.applicationMethodology,
      applicationRate: applicationRate ?? this.applicationRate,
      transportDistanceKm: transportDistanceKm ?? this.transportDistanceKm,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      farmerPhotoPath: farmerPhotoPath ?? this.farmerPhotoPath,
      farmerPhotoSha256: farmerPhotoSha256 ?? this.farmerPhotoSha256,
      deliveryDate: deliveryDate ?? this.deliveryDate,
      deliveredAmountKg: deliveredAmountKg ?? this.deliveredAmountKg,
      buyerName: buyerName ?? this.buyerName,
      buyerContact: buyerContact ?? this.buyerContact,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (applicationUuid.present) {
      map['application_uuid'] = Variable<String>(applicationUuid.value);
    }
    if (batchUuid.present) {
      map['batch_uuid'] = Variable<String>(batchUuid.value);
    }
    if (applicationMethodology.present) {
      map['application_methodology'] = Variable<String>(
        applicationMethodology.value,
      );
    }
    if (applicationRate.present) {
      map['application_rate'] = Variable<double>(applicationRate.value);
    }
    if (transportDistanceKm.present) {
      map['transport_distance_km'] = Variable<double>(
        transportDistanceKm.value,
      );
    }
    if (latitude.present) {
      map['latitude'] = Variable<double>(latitude.value);
    }
    if (longitude.present) {
      map['longitude'] = Variable<double>(longitude.value);
    }
    if (farmerPhotoPath.present) {
      map['farmer_photo_path'] = Variable<String>(farmerPhotoPath.value);
    }
    if (farmerPhotoSha256.present) {
      map['farmer_photo_sha256'] = Variable<String>(farmerPhotoSha256.value);
    }
    if (deliveryDate.present) {
      map['delivery_date'] = Variable<String>(deliveryDate.value);
    }
    if (deliveredAmountKg.present) {
      map['delivered_amount_kg'] = Variable<double>(deliveredAmountKg.value);
    }
    if (buyerName.present) {
      map['buyer_name'] = Variable<String>(buyerName.value);
    }
    if (buyerContact.present) {
      map['buyer_contact'] = Variable<String>(buyerContact.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('EndUseApplicationCompanion(')
          ..write('applicationUuid: $applicationUuid, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('applicationMethodology: $applicationMethodology, ')
          ..write('applicationRate: $applicationRate, ')
          ..write('transportDistanceKm: $transportDistanceKm, ')
          ..write('latitude: $latitude, ')
          ..write('longitude: $longitude, ')
          ..write('farmerPhotoPath: $farmerPhotoPath, ')
          ..write('farmerPhotoSha256: $farmerPhotoSha256, ')
          ..write('deliveryDate: $deliveryDate, ')
          ..write('deliveredAmountKg: $deliveredAmountKg, ')
          ..write('buyerName: $buyerName, ')
          ..write('buyerContact: $buyerContact, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $SyncOutboxTable extends SyncOutbox
    with TableInfo<$SyncOutboxTable, SyncOutboxData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $SyncOutboxTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _operationIdMeta = const VerificationMeta(
    'operationId',
  );
  @override
  late final GeneratedColumn<String> operationId = GeneratedColumn<String>(
    'operation_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _batchUuidMeta = const VerificationMeta(
    'batchUuid',
  );
  @override
  late final GeneratedColumn<String> batchUuid = GeneratedColumn<String>(
    'batch_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _targetTableMeta = const VerificationMeta(
    'targetTable',
  );
  @override
  late final GeneratedColumn<String> targetTable = GeneratedColumn<String>(
    'target_table',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _operationTypeMeta = const VerificationMeta(
    'operationType',
  );
  @override
  late final GeneratedColumn<String> operationType = GeneratedColumn<String>(
    'operation_type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _payloadJsonMeta = const VerificationMeta(
    'payloadJson',
  );
  @override
  late final GeneratedColumn<String> payloadJson = GeneratedColumn<String>(
    'payload_json',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
    'status',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant('PENDING'),
  );
  static const VerificationMeta _retryCountMeta = const VerificationMeta(
    'retryCount',
  );
  @override
  late final GeneratedColumn<int> retryCount = GeneratedColumn<int>(
    'retry_count',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(0),
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _lastAttemptAtMeta = const VerificationMeta(
    'lastAttemptAt',
  );
  @override
  late final GeneratedColumn<String> lastAttemptAt = GeneratedColumn<String>(
    'last_attempt_at',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _failureReasonMeta = const VerificationMeta(
    'failureReason',
  );
  @override
  late final GeneratedColumn<String> failureReason = GeneratedColumn<String>(
    'failure_reason',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _jsonSyncedAtMeta = const VerificationMeta(
    'jsonSyncedAt',
  );
  @override
  late final GeneratedColumn<String> jsonSyncedAt = GeneratedColumn<String>(
    'json_synced_at',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _mediaSyncedAtMeta = const VerificationMeta(
    'mediaSyncedAt',
  );
  @override
  late final GeneratedColumn<String> mediaSyncedAt = GeneratedColumn<String>(
    'media_synced_at',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _hmacSignatureMeta = const VerificationMeta(
    'hmacSignature',
  );
  @override
  late final GeneratedColumn<String> hmacSignature = GeneratedColumn<String>(
    'hmac_signature',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    operationId,
    batchUuid,
    targetTable,
    operationType,
    payloadJson,
    status,
    retryCount,
    createdAt,
    lastAttemptAt,
    failureReason,
    jsonSyncedAt,
    mediaSyncedAt,
    hmacSignature,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'sync_outbox';
  @override
  VerificationContext validateIntegrity(
    Insertable<SyncOutboxData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('operation_id')) {
      context.handle(
        _operationIdMeta,
        operationId.isAcceptableOrUnknown(
          data['operation_id']!,
          _operationIdMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_operationIdMeta);
    }
    if (data.containsKey('batch_uuid')) {
      context.handle(
        _batchUuidMeta,
        batchUuid.isAcceptableOrUnknown(data['batch_uuid']!, _batchUuidMeta),
      );
    } else if (isInserting) {
      context.missing(_batchUuidMeta);
    }
    if (data.containsKey('target_table')) {
      context.handle(
        _targetTableMeta,
        targetTable.isAcceptableOrUnknown(
          data['target_table']!,
          _targetTableMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_targetTableMeta);
    }
    if (data.containsKey('operation_type')) {
      context.handle(
        _operationTypeMeta,
        operationType.isAcceptableOrUnknown(
          data['operation_type']!,
          _operationTypeMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_operationTypeMeta);
    }
    if (data.containsKey('payload_json')) {
      context.handle(
        _payloadJsonMeta,
        payloadJson.isAcceptableOrUnknown(
          data['payload_json']!,
          _payloadJsonMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_payloadJsonMeta);
    }
    if (data.containsKey('status')) {
      context.handle(
        _statusMeta,
        status.isAcceptableOrUnknown(data['status']!, _statusMeta),
      );
    }
    if (data.containsKey('retry_count')) {
      context.handle(
        _retryCountMeta,
        retryCount.isAcceptableOrUnknown(data['retry_count']!, _retryCountMeta),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('last_attempt_at')) {
      context.handle(
        _lastAttemptAtMeta,
        lastAttemptAt.isAcceptableOrUnknown(
          data['last_attempt_at']!,
          _lastAttemptAtMeta,
        ),
      );
    }
    if (data.containsKey('failure_reason')) {
      context.handle(
        _failureReasonMeta,
        failureReason.isAcceptableOrUnknown(
          data['failure_reason']!,
          _failureReasonMeta,
        ),
      );
    }
    if (data.containsKey('json_synced_at')) {
      context.handle(
        _jsonSyncedAtMeta,
        jsonSyncedAt.isAcceptableOrUnknown(
          data['json_synced_at']!,
          _jsonSyncedAtMeta,
        ),
      );
    }
    if (data.containsKey('media_synced_at')) {
      context.handle(
        _mediaSyncedAtMeta,
        mediaSyncedAt.isAcceptableOrUnknown(
          data['media_synced_at']!,
          _mediaSyncedAtMeta,
        ),
      );
    }
    if (data.containsKey('hmac_signature')) {
      context.handle(
        _hmacSignatureMeta,
        hmacSignature.isAcceptableOrUnknown(
          data['hmac_signature']!,
          _hmacSignatureMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {operationId};
  @override
  SyncOutboxData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return SyncOutboxData(
      operationId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}operation_id'],
      )!,
      batchUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}batch_uuid'],
      )!,
      targetTable: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}target_table'],
      )!,
      operationType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}operation_type'],
      )!,
      payloadJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}payload_json'],
      )!,
      status: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}status'],
      )!,
      retryCount: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}retry_count'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}created_at'],
      )!,
      lastAttemptAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}last_attempt_at'],
      ),
      failureReason: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}failure_reason'],
      ),
      jsonSyncedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}json_synced_at'],
      ),
      mediaSyncedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}media_synced_at'],
      ),
      hmacSignature: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}hmac_signature'],
      ),
    );
  }

  @override
  $SyncOutboxTable createAlias(String alias) {
    return $SyncOutboxTable(attachedDatabase, alias);
  }
}

class SyncOutboxData extends DataClass implements Insertable<SyncOutboxData> {
  final String operationId;
  final String batchUuid;
  final String targetTable;
  final String operationType;
  final String payloadJson;
  final String status;
  final int retryCount;
  final String createdAt;
  final String? lastAttemptAt;

  /// P1-C1: human-readable reason a row is stuck (server body or exception
  /// text), surfaced in the Sync Health screen. Set when status becomes
  /// FAILED_PERMANENTLY; retained across an operator-initiated retry.
  final String? failureReason;

  /// Set when the JSON metadata POST is confirmed by the server (200 or 409).
  final String? jsonSyncedAt;

  /// Set when the media multipart POST is confirmed AND server hash matches.
  final String? mediaSyncedAt;

  /// HMAC-SHA256 of payloadJson, calculated at the exact moment of insertion.
  /// If a hacker tampers with payloadJson after insertion, this column will
  /// no longer match and the server will reject the upload.
  final String? hmacSignature;
  const SyncOutboxData({
    required this.operationId,
    required this.batchUuid,
    required this.targetTable,
    required this.operationType,
    required this.payloadJson,
    required this.status,
    required this.retryCount,
    required this.createdAt,
    this.lastAttemptAt,
    this.failureReason,
    this.jsonSyncedAt,
    this.mediaSyncedAt,
    this.hmacSignature,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['operation_id'] = Variable<String>(operationId);
    map['batch_uuid'] = Variable<String>(batchUuid);
    map['target_table'] = Variable<String>(targetTable);
    map['operation_type'] = Variable<String>(operationType);
    map['payload_json'] = Variable<String>(payloadJson);
    map['status'] = Variable<String>(status);
    map['retry_count'] = Variable<int>(retryCount);
    map['created_at'] = Variable<String>(createdAt);
    if (!nullToAbsent || lastAttemptAt != null) {
      map['last_attempt_at'] = Variable<String>(lastAttemptAt);
    }
    if (!nullToAbsent || failureReason != null) {
      map['failure_reason'] = Variable<String>(failureReason);
    }
    if (!nullToAbsent || jsonSyncedAt != null) {
      map['json_synced_at'] = Variable<String>(jsonSyncedAt);
    }
    if (!nullToAbsent || mediaSyncedAt != null) {
      map['media_synced_at'] = Variable<String>(mediaSyncedAt);
    }
    if (!nullToAbsent || hmacSignature != null) {
      map['hmac_signature'] = Variable<String>(hmacSignature);
    }
    return map;
  }

  SyncOutboxCompanion toCompanion(bool nullToAbsent) {
    return SyncOutboxCompanion(
      operationId: Value(operationId),
      batchUuid: Value(batchUuid),
      targetTable: Value(targetTable),
      operationType: Value(operationType),
      payloadJson: Value(payloadJson),
      status: Value(status),
      retryCount: Value(retryCount),
      createdAt: Value(createdAt),
      lastAttemptAt: lastAttemptAt == null && nullToAbsent
          ? const Value.absent()
          : Value(lastAttemptAt),
      failureReason: failureReason == null && nullToAbsent
          ? const Value.absent()
          : Value(failureReason),
      jsonSyncedAt: jsonSyncedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(jsonSyncedAt),
      mediaSyncedAt: mediaSyncedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(mediaSyncedAt),
      hmacSignature: hmacSignature == null && nullToAbsent
          ? const Value.absent()
          : Value(hmacSignature),
    );
  }

  factory SyncOutboxData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return SyncOutboxData(
      operationId: serializer.fromJson<String>(json['operationId']),
      batchUuid: serializer.fromJson<String>(json['batchUuid']),
      targetTable: serializer.fromJson<String>(json['targetTable']),
      operationType: serializer.fromJson<String>(json['operationType']),
      payloadJson: serializer.fromJson<String>(json['payloadJson']),
      status: serializer.fromJson<String>(json['status']),
      retryCount: serializer.fromJson<int>(json['retryCount']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
      lastAttemptAt: serializer.fromJson<String?>(json['lastAttemptAt']),
      failureReason: serializer.fromJson<String?>(json['failureReason']),
      jsonSyncedAt: serializer.fromJson<String?>(json['jsonSyncedAt']),
      mediaSyncedAt: serializer.fromJson<String?>(json['mediaSyncedAt']),
      hmacSignature: serializer.fromJson<String?>(json['hmacSignature']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'operationId': serializer.toJson<String>(operationId),
      'batchUuid': serializer.toJson<String>(batchUuid),
      'targetTable': serializer.toJson<String>(targetTable),
      'operationType': serializer.toJson<String>(operationType),
      'payloadJson': serializer.toJson<String>(payloadJson),
      'status': serializer.toJson<String>(status),
      'retryCount': serializer.toJson<int>(retryCount),
      'createdAt': serializer.toJson<String>(createdAt),
      'lastAttemptAt': serializer.toJson<String?>(lastAttemptAt),
      'failureReason': serializer.toJson<String?>(failureReason),
      'jsonSyncedAt': serializer.toJson<String?>(jsonSyncedAt),
      'mediaSyncedAt': serializer.toJson<String?>(mediaSyncedAt),
      'hmacSignature': serializer.toJson<String?>(hmacSignature),
    };
  }

  SyncOutboxData copyWith({
    String? operationId,
    String? batchUuid,
    String? targetTable,
    String? operationType,
    String? payloadJson,
    String? status,
    int? retryCount,
    String? createdAt,
    Value<String?> lastAttemptAt = const Value.absent(),
    Value<String?> failureReason = const Value.absent(),
    Value<String?> jsonSyncedAt = const Value.absent(),
    Value<String?> mediaSyncedAt = const Value.absent(),
    Value<String?> hmacSignature = const Value.absent(),
  }) => SyncOutboxData(
    operationId: operationId ?? this.operationId,
    batchUuid: batchUuid ?? this.batchUuid,
    targetTable: targetTable ?? this.targetTable,
    operationType: operationType ?? this.operationType,
    payloadJson: payloadJson ?? this.payloadJson,
    status: status ?? this.status,
    retryCount: retryCount ?? this.retryCount,
    createdAt: createdAt ?? this.createdAt,
    lastAttemptAt: lastAttemptAt.present
        ? lastAttemptAt.value
        : this.lastAttemptAt,
    failureReason: failureReason.present
        ? failureReason.value
        : this.failureReason,
    jsonSyncedAt: jsonSyncedAt.present ? jsonSyncedAt.value : this.jsonSyncedAt,
    mediaSyncedAt: mediaSyncedAt.present
        ? mediaSyncedAt.value
        : this.mediaSyncedAt,
    hmacSignature: hmacSignature.present
        ? hmacSignature.value
        : this.hmacSignature,
  );
  SyncOutboxData copyWithCompanion(SyncOutboxCompanion data) {
    return SyncOutboxData(
      operationId: data.operationId.present
          ? data.operationId.value
          : this.operationId,
      batchUuid: data.batchUuid.present ? data.batchUuid.value : this.batchUuid,
      targetTable: data.targetTable.present
          ? data.targetTable.value
          : this.targetTable,
      operationType: data.operationType.present
          ? data.operationType.value
          : this.operationType,
      payloadJson: data.payloadJson.present
          ? data.payloadJson.value
          : this.payloadJson,
      status: data.status.present ? data.status.value : this.status,
      retryCount: data.retryCount.present
          ? data.retryCount.value
          : this.retryCount,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      lastAttemptAt: data.lastAttemptAt.present
          ? data.lastAttemptAt.value
          : this.lastAttemptAt,
      failureReason: data.failureReason.present
          ? data.failureReason.value
          : this.failureReason,
      jsonSyncedAt: data.jsonSyncedAt.present
          ? data.jsonSyncedAt.value
          : this.jsonSyncedAt,
      mediaSyncedAt: data.mediaSyncedAt.present
          ? data.mediaSyncedAt.value
          : this.mediaSyncedAt,
      hmacSignature: data.hmacSignature.present
          ? data.hmacSignature.value
          : this.hmacSignature,
    );
  }

  @override
  String toString() {
    return (StringBuffer('SyncOutboxData(')
          ..write('operationId: $operationId, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('targetTable: $targetTable, ')
          ..write('operationType: $operationType, ')
          ..write('payloadJson: $payloadJson, ')
          ..write('status: $status, ')
          ..write('retryCount: $retryCount, ')
          ..write('createdAt: $createdAt, ')
          ..write('lastAttemptAt: $lastAttemptAt, ')
          ..write('failureReason: $failureReason, ')
          ..write('jsonSyncedAt: $jsonSyncedAt, ')
          ..write('mediaSyncedAt: $mediaSyncedAt, ')
          ..write('hmacSignature: $hmacSignature')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    operationId,
    batchUuid,
    targetTable,
    operationType,
    payloadJson,
    status,
    retryCount,
    createdAt,
    lastAttemptAt,
    failureReason,
    jsonSyncedAt,
    mediaSyncedAt,
    hmacSignature,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is SyncOutboxData &&
          other.operationId == this.operationId &&
          other.batchUuid == this.batchUuid &&
          other.targetTable == this.targetTable &&
          other.operationType == this.operationType &&
          other.payloadJson == this.payloadJson &&
          other.status == this.status &&
          other.retryCount == this.retryCount &&
          other.createdAt == this.createdAt &&
          other.lastAttemptAt == this.lastAttemptAt &&
          other.failureReason == this.failureReason &&
          other.jsonSyncedAt == this.jsonSyncedAt &&
          other.mediaSyncedAt == this.mediaSyncedAt &&
          other.hmacSignature == this.hmacSignature);
}

class SyncOutboxCompanion extends UpdateCompanion<SyncOutboxData> {
  final Value<String> operationId;
  final Value<String> batchUuid;
  final Value<String> targetTable;
  final Value<String> operationType;
  final Value<String> payloadJson;
  final Value<String> status;
  final Value<int> retryCount;
  final Value<String> createdAt;
  final Value<String?> lastAttemptAt;
  final Value<String?> failureReason;
  final Value<String?> jsonSyncedAt;
  final Value<String?> mediaSyncedAt;
  final Value<String?> hmacSignature;
  final Value<int> rowid;
  const SyncOutboxCompanion({
    this.operationId = const Value.absent(),
    this.batchUuid = const Value.absent(),
    this.targetTable = const Value.absent(),
    this.operationType = const Value.absent(),
    this.payloadJson = const Value.absent(),
    this.status = const Value.absent(),
    this.retryCount = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.lastAttemptAt = const Value.absent(),
    this.failureReason = const Value.absent(),
    this.jsonSyncedAt = const Value.absent(),
    this.mediaSyncedAt = const Value.absent(),
    this.hmacSignature = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  SyncOutboxCompanion.insert({
    required String operationId,
    required String batchUuid,
    required String targetTable,
    required String operationType,
    required String payloadJson,
    this.status = const Value.absent(),
    this.retryCount = const Value.absent(),
    required String createdAt,
    this.lastAttemptAt = const Value.absent(),
    this.failureReason = const Value.absent(),
    this.jsonSyncedAt = const Value.absent(),
    this.mediaSyncedAt = const Value.absent(),
    this.hmacSignature = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : operationId = Value(operationId),
       batchUuid = Value(batchUuid),
       targetTable = Value(targetTable),
       operationType = Value(operationType),
       payloadJson = Value(payloadJson),
       createdAt = Value(createdAt);
  static Insertable<SyncOutboxData> custom({
    Expression<String>? operationId,
    Expression<String>? batchUuid,
    Expression<String>? targetTable,
    Expression<String>? operationType,
    Expression<String>? payloadJson,
    Expression<String>? status,
    Expression<int>? retryCount,
    Expression<String>? createdAt,
    Expression<String>? lastAttemptAt,
    Expression<String>? failureReason,
    Expression<String>? jsonSyncedAt,
    Expression<String>? mediaSyncedAt,
    Expression<String>? hmacSignature,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (operationId != null) 'operation_id': operationId,
      if (batchUuid != null) 'batch_uuid': batchUuid,
      if (targetTable != null) 'target_table': targetTable,
      if (operationType != null) 'operation_type': operationType,
      if (payloadJson != null) 'payload_json': payloadJson,
      if (status != null) 'status': status,
      if (retryCount != null) 'retry_count': retryCount,
      if (createdAt != null) 'created_at': createdAt,
      if (lastAttemptAt != null) 'last_attempt_at': lastAttemptAt,
      if (failureReason != null) 'failure_reason': failureReason,
      if (jsonSyncedAt != null) 'json_synced_at': jsonSyncedAt,
      if (mediaSyncedAt != null) 'media_synced_at': mediaSyncedAt,
      if (hmacSignature != null) 'hmac_signature': hmacSignature,
      if (rowid != null) 'rowid': rowid,
    });
  }

  SyncOutboxCompanion copyWith({
    Value<String>? operationId,
    Value<String>? batchUuid,
    Value<String>? targetTable,
    Value<String>? operationType,
    Value<String>? payloadJson,
    Value<String>? status,
    Value<int>? retryCount,
    Value<String>? createdAt,
    Value<String?>? lastAttemptAt,
    Value<String?>? failureReason,
    Value<String?>? jsonSyncedAt,
    Value<String?>? mediaSyncedAt,
    Value<String?>? hmacSignature,
    Value<int>? rowid,
  }) {
    return SyncOutboxCompanion(
      operationId: operationId ?? this.operationId,
      batchUuid: batchUuid ?? this.batchUuid,
      targetTable: targetTable ?? this.targetTable,
      operationType: operationType ?? this.operationType,
      payloadJson: payloadJson ?? this.payloadJson,
      status: status ?? this.status,
      retryCount: retryCount ?? this.retryCount,
      createdAt: createdAt ?? this.createdAt,
      lastAttemptAt: lastAttemptAt ?? this.lastAttemptAt,
      failureReason: failureReason ?? this.failureReason,
      jsonSyncedAt: jsonSyncedAt ?? this.jsonSyncedAt,
      mediaSyncedAt: mediaSyncedAt ?? this.mediaSyncedAt,
      hmacSignature: hmacSignature ?? this.hmacSignature,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (operationId.present) {
      map['operation_id'] = Variable<String>(operationId.value);
    }
    if (batchUuid.present) {
      map['batch_uuid'] = Variable<String>(batchUuid.value);
    }
    if (targetTable.present) {
      map['target_table'] = Variable<String>(targetTable.value);
    }
    if (operationType.present) {
      map['operation_type'] = Variable<String>(operationType.value);
    }
    if (payloadJson.present) {
      map['payload_json'] = Variable<String>(payloadJson.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (retryCount.present) {
      map['retry_count'] = Variable<int>(retryCount.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    if (lastAttemptAt.present) {
      map['last_attempt_at'] = Variable<String>(lastAttemptAt.value);
    }
    if (failureReason.present) {
      map['failure_reason'] = Variable<String>(failureReason.value);
    }
    if (jsonSyncedAt.present) {
      map['json_synced_at'] = Variable<String>(jsonSyncedAt.value);
    }
    if (mediaSyncedAt.present) {
      map['media_synced_at'] = Variable<String>(mediaSyncedAt.value);
    }
    if (hmacSignature.present) {
      map['hmac_signature'] = Variable<String>(hmacSignature.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('SyncOutboxCompanion(')
          ..write('operationId: $operationId, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('targetTable: $targetTable, ')
          ..write('operationType: $operationType, ')
          ..write('payloadJson: $payloadJson, ')
          ..write('status: $status, ')
          ..write('retryCount: $retryCount, ')
          ..write('createdAt: $createdAt, ')
          ..write('lastAttemptAt: $lastAttemptAt, ')
          ..write('failureReason: $failureReason, ')
          ..write('jsonSyncedAt: $jsonSyncedAt, ')
          ..write('mediaSyncedAt: $mediaSyncedAt, ')
          ..write('hmacSignature: $hmacSignature, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $MediaCapturesTable extends MediaCaptures
    with TableInfo<$MediaCapturesTable, MediaCapture> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $MediaCapturesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _batchUuidMeta = const VerificationMeta(
    'batchUuid',
  );
  @override
  late final GeneratedColumn<String> batchUuid = GeneratedColumn<String>(
    'batch_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES system_metadata (batch_uuid)',
    ),
  );
  static const VerificationMeta _captureTypeMeta = const VerificationMeta(
    'captureType',
  );
  @override
  late final GeneratedColumn<String> captureType = GeneratedColumn<String>(
    'capture_type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sandboxPathMeta = const VerificationMeta(
    'sandboxPath',
  );
  @override
  late final GeneratedColumn<String> sandboxPath = GeneratedColumn<String>(
    'sandbox_path',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sha256HashMeta = const VerificationMeta(
    'sha256Hash',
  );
  @override
  late final GeneratedColumn<String> sha256Hash = GeneratedColumn<String>(
    'sha256_hash',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _isMockLocationMeta = const VerificationMeta(
    'isMockLocation',
  );
  @override
  late final GeneratedColumn<bool> isMockLocation = GeneratedColumn<bool>(
    'is_mock_location',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("is_mock_location" IN (0, 1))',
    ),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    batchUuid,
    captureType,
    sandboxPath,
    sha256Hash,
    isMockLocation,
    createdAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'media_captures';
  @override
  VerificationContext validateIntegrity(
    Insertable<MediaCapture> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('batch_uuid')) {
      context.handle(
        _batchUuidMeta,
        batchUuid.isAcceptableOrUnknown(data['batch_uuid']!, _batchUuidMeta),
      );
    } else if (isInserting) {
      context.missing(_batchUuidMeta);
    }
    if (data.containsKey('capture_type')) {
      context.handle(
        _captureTypeMeta,
        captureType.isAcceptableOrUnknown(
          data['capture_type']!,
          _captureTypeMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_captureTypeMeta);
    }
    if (data.containsKey('sandbox_path')) {
      context.handle(
        _sandboxPathMeta,
        sandboxPath.isAcceptableOrUnknown(
          data['sandbox_path']!,
          _sandboxPathMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_sandboxPathMeta);
    }
    if (data.containsKey('sha256_hash')) {
      context.handle(
        _sha256HashMeta,
        sha256Hash.isAcceptableOrUnknown(data['sha256_hash']!, _sha256HashMeta),
      );
    } else if (isInserting) {
      context.missing(_sha256HashMeta);
    }
    if (data.containsKey('is_mock_location')) {
      context.handle(
        _isMockLocationMeta,
        isMockLocation.isAcceptableOrUnknown(
          data['is_mock_location']!,
          _isMockLocationMeta,
        ),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  List<Set<GeneratedColumn>> get uniqueKeys => [
    {batchUuid, captureType},
  ];
  @override
  MediaCapture map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return MediaCapture(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      batchUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}batch_uuid'],
      )!,
      captureType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}capture_type'],
      )!,
      sandboxPath: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sandbox_path'],
      )!,
      sha256Hash: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sha256_hash'],
      )!,
      isMockLocation: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}is_mock_location'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $MediaCapturesTable createAlias(String alias) {
    return $MediaCapturesTable(attachedDatabase, alias);
  }
}

class MediaCapture extends DataClass implements Insertable<MediaCapture> {
  final int id;
  final String batchUuid;
  final String captureType;
  final String sandboxPath;
  final String sha256Hash;
  final bool isMockLocation;
  final String createdAt;
  const MediaCapture({
    required this.id,
    required this.batchUuid,
    required this.captureType,
    required this.sandboxPath,
    required this.sha256Hash,
    required this.isMockLocation,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['batch_uuid'] = Variable<String>(batchUuid);
    map['capture_type'] = Variable<String>(captureType);
    map['sandbox_path'] = Variable<String>(sandboxPath);
    map['sha256_hash'] = Variable<String>(sha256Hash);
    map['is_mock_location'] = Variable<bool>(isMockLocation);
    map['created_at'] = Variable<String>(createdAt);
    return map;
  }

  MediaCapturesCompanion toCompanion(bool nullToAbsent) {
    return MediaCapturesCompanion(
      id: Value(id),
      batchUuid: Value(batchUuid),
      captureType: Value(captureType),
      sandboxPath: Value(sandboxPath),
      sha256Hash: Value(sha256Hash),
      isMockLocation: Value(isMockLocation),
      createdAt: Value(createdAt),
    );
  }

  factory MediaCapture.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return MediaCapture(
      id: serializer.fromJson<int>(json['id']),
      batchUuid: serializer.fromJson<String>(json['batchUuid']),
      captureType: serializer.fromJson<String>(json['captureType']),
      sandboxPath: serializer.fromJson<String>(json['sandboxPath']),
      sha256Hash: serializer.fromJson<String>(json['sha256Hash']),
      isMockLocation: serializer.fromJson<bool>(json['isMockLocation']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'batchUuid': serializer.toJson<String>(batchUuid),
      'captureType': serializer.toJson<String>(captureType),
      'sandboxPath': serializer.toJson<String>(sandboxPath),
      'sha256Hash': serializer.toJson<String>(sha256Hash),
      'isMockLocation': serializer.toJson<bool>(isMockLocation),
      'createdAt': serializer.toJson<String>(createdAt),
    };
  }

  MediaCapture copyWith({
    int? id,
    String? batchUuid,
    String? captureType,
    String? sandboxPath,
    String? sha256Hash,
    bool? isMockLocation,
    String? createdAt,
  }) => MediaCapture(
    id: id ?? this.id,
    batchUuid: batchUuid ?? this.batchUuid,
    captureType: captureType ?? this.captureType,
    sandboxPath: sandboxPath ?? this.sandboxPath,
    sha256Hash: sha256Hash ?? this.sha256Hash,
    isMockLocation: isMockLocation ?? this.isMockLocation,
    createdAt: createdAt ?? this.createdAt,
  );
  MediaCapture copyWithCompanion(MediaCapturesCompanion data) {
    return MediaCapture(
      id: data.id.present ? data.id.value : this.id,
      batchUuid: data.batchUuid.present ? data.batchUuid.value : this.batchUuid,
      captureType: data.captureType.present
          ? data.captureType.value
          : this.captureType,
      sandboxPath: data.sandboxPath.present
          ? data.sandboxPath.value
          : this.sandboxPath,
      sha256Hash: data.sha256Hash.present
          ? data.sha256Hash.value
          : this.sha256Hash,
      isMockLocation: data.isMockLocation.present
          ? data.isMockLocation.value
          : this.isMockLocation,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('MediaCapture(')
          ..write('id: $id, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('captureType: $captureType, ')
          ..write('sandboxPath: $sandboxPath, ')
          ..write('sha256Hash: $sha256Hash, ')
          ..write('isMockLocation: $isMockLocation, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    batchUuid,
    captureType,
    sandboxPath,
    sha256Hash,
    isMockLocation,
    createdAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is MediaCapture &&
          other.id == this.id &&
          other.batchUuid == this.batchUuid &&
          other.captureType == this.captureType &&
          other.sandboxPath == this.sandboxPath &&
          other.sha256Hash == this.sha256Hash &&
          other.isMockLocation == this.isMockLocation &&
          other.createdAt == this.createdAt);
}

class MediaCapturesCompanion extends UpdateCompanion<MediaCapture> {
  final Value<int> id;
  final Value<String> batchUuid;
  final Value<String> captureType;
  final Value<String> sandboxPath;
  final Value<String> sha256Hash;
  final Value<bool> isMockLocation;
  final Value<String> createdAt;
  const MediaCapturesCompanion({
    this.id = const Value.absent(),
    this.batchUuid = const Value.absent(),
    this.captureType = const Value.absent(),
    this.sandboxPath = const Value.absent(),
    this.sha256Hash = const Value.absent(),
    this.isMockLocation = const Value.absent(),
    this.createdAt = const Value.absent(),
  });
  MediaCapturesCompanion.insert({
    this.id = const Value.absent(),
    required String batchUuid,
    required String captureType,
    required String sandboxPath,
    required String sha256Hash,
    this.isMockLocation = const Value.absent(),
    required String createdAt,
  }) : batchUuid = Value(batchUuid),
       captureType = Value(captureType),
       sandboxPath = Value(sandboxPath),
       sha256Hash = Value(sha256Hash),
       createdAt = Value(createdAt);
  static Insertable<MediaCapture> custom({
    Expression<int>? id,
    Expression<String>? batchUuid,
    Expression<String>? captureType,
    Expression<String>? sandboxPath,
    Expression<String>? sha256Hash,
    Expression<bool>? isMockLocation,
    Expression<String>? createdAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (batchUuid != null) 'batch_uuid': batchUuid,
      if (captureType != null) 'capture_type': captureType,
      if (sandboxPath != null) 'sandbox_path': sandboxPath,
      if (sha256Hash != null) 'sha256_hash': sha256Hash,
      if (isMockLocation != null) 'is_mock_location': isMockLocation,
      if (createdAt != null) 'created_at': createdAt,
    });
  }

  MediaCapturesCompanion copyWith({
    Value<int>? id,
    Value<String>? batchUuid,
    Value<String>? captureType,
    Value<String>? sandboxPath,
    Value<String>? sha256Hash,
    Value<bool>? isMockLocation,
    Value<String>? createdAt,
  }) {
    return MediaCapturesCompanion(
      id: id ?? this.id,
      batchUuid: batchUuid ?? this.batchUuid,
      captureType: captureType ?? this.captureType,
      sandboxPath: sandboxPath ?? this.sandboxPath,
      sha256Hash: sha256Hash ?? this.sha256Hash,
      isMockLocation: isMockLocation ?? this.isMockLocation,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (batchUuid.present) {
      map['batch_uuid'] = Variable<String>(batchUuid.value);
    }
    if (captureType.present) {
      map['capture_type'] = Variable<String>(captureType.value);
    }
    if (sandboxPath.present) {
      map['sandbox_path'] = Variable<String>(sandboxPath.value);
    }
    if (sha256Hash.present) {
      map['sha256_hash'] = Variable<String>(sha256Hash.value);
    }
    if (isMockLocation.present) {
      map['is_mock_location'] = Variable<bool>(isMockLocation.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('MediaCapturesCompanion(')
          ..write('id: $id, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('captureType: $captureType, ')
          ..write('sandboxPath: $sandboxPath, ')
          ..write('sha256Hash: $sha256Hash, ')
          ..write('isMockLocation: $isMockLocation, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }
}

class $MoistureReadingsTable extends MoistureReadings
    with TableInfo<$MoistureReadingsTable, MoistureReading> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $MoistureReadingsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _readingUuidMeta = const VerificationMeta(
    'readingUuid',
  );
  @override
  late final GeneratedColumn<String> readingUuid = GeneratedColumn<String>(
    'reading_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _batchUuidMeta = const VerificationMeta(
    'batchUuid',
  );
  @override
  late final GeneratedColumn<String> batchUuid = GeneratedColumn<String>(
    'batch_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES system_metadata (batch_uuid)',
    ),
  );
  static const VerificationMeta _moisturePercentMeta = const VerificationMeta(
    'moisturePercent',
  );
  @override
  late final GeneratedColumn<double> moisturePercent = GeneratedColumn<double>(
    'moisture_percent',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sequenceMeta = const VerificationMeta(
    'sequence',
  );
  @override
  late final GeneratedColumn<int> sequence = GeneratedColumn<int>(
    'sequence',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sandboxPathMeta = const VerificationMeta(
    'sandboxPath',
  );
  @override
  late final GeneratedColumn<String> sandboxPath = GeneratedColumn<String>(
    'sandbox_path',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _sha256HashMeta = const VerificationMeta(
    'sha256Hash',
  );
  @override
  late final GeneratedColumn<String> sha256Hash = GeneratedColumn<String>(
    'sha256_hash',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    readingUuid,
    batchUuid,
    moisturePercent,
    sequence,
    sandboxPath,
    sha256Hash,
    createdAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'moisture_readings';
  @override
  VerificationContext validateIntegrity(
    Insertable<MoistureReading> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('reading_uuid')) {
      context.handle(
        _readingUuidMeta,
        readingUuid.isAcceptableOrUnknown(
          data['reading_uuid']!,
          _readingUuidMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_readingUuidMeta);
    }
    if (data.containsKey('batch_uuid')) {
      context.handle(
        _batchUuidMeta,
        batchUuid.isAcceptableOrUnknown(data['batch_uuid']!, _batchUuidMeta),
      );
    } else if (isInserting) {
      context.missing(_batchUuidMeta);
    }
    if (data.containsKey('moisture_percent')) {
      context.handle(
        _moisturePercentMeta,
        moisturePercent.isAcceptableOrUnknown(
          data['moisture_percent']!,
          _moisturePercentMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_moisturePercentMeta);
    }
    if (data.containsKey('sequence')) {
      context.handle(
        _sequenceMeta,
        sequence.isAcceptableOrUnknown(data['sequence']!, _sequenceMeta),
      );
    } else if (isInserting) {
      context.missing(_sequenceMeta);
    }
    if (data.containsKey('sandbox_path')) {
      context.handle(
        _sandboxPathMeta,
        sandboxPath.isAcceptableOrUnknown(
          data['sandbox_path']!,
          _sandboxPathMeta,
        ),
      );
    }
    if (data.containsKey('sha256_hash')) {
      context.handle(
        _sha256HashMeta,
        sha256Hash.isAcceptableOrUnknown(data['sha256_hash']!, _sha256HashMeta),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  List<Set<GeneratedColumn>> get uniqueKeys => [
    {readingUuid},
    {batchUuid, sequence},
  ];
  @override
  MoistureReading map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return MoistureReading(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      readingUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}reading_uuid'],
      )!,
      batchUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}batch_uuid'],
      )!,
      moisturePercent: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}moisture_percent'],
      )!,
      sequence: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}sequence'],
      )!,
      sandboxPath: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sandbox_path'],
      ),
      sha256Hash: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sha256_hash'],
      ),
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $MoistureReadingsTable createAlias(String alias) {
    return $MoistureReadingsTable(attachedDatabase, alias);
  }
}

class MoistureReading extends DataClass implements Insertable<MoistureReading> {
  final int id;
  final String readingUuid;
  final String batchUuid;
  final double moisturePercent;

  /// Ordinal within the run (1..N). Unique per batch so retakes don't duplicate.
  final int sequence;

  /// Sandboxed photo of the meter reading + its SHA-256 (uploaded via /media).
  final String? sandboxPath;
  final String? sha256Hash;
  final String createdAt;
  const MoistureReading({
    required this.id,
    required this.readingUuid,
    required this.batchUuid,
    required this.moisturePercent,
    required this.sequence,
    this.sandboxPath,
    this.sha256Hash,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['reading_uuid'] = Variable<String>(readingUuid);
    map['batch_uuid'] = Variable<String>(batchUuid);
    map['moisture_percent'] = Variable<double>(moisturePercent);
    map['sequence'] = Variable<int>(sequence);
    if (!nullToAbsent || sandboxPath != null) {
      map['sandbox_path'] = Variable<String>(sandboxPath);
    }
    if (!nullToAbsent || sha256Hash != null) {
      map['sha256_hash'] = Variable<String>(sha256Hash);
    }
    map['created_at'] = Variable<String>(createdAt);
    return map;
  }

  MoistureReadingsCompanion toCompanion(bool nullToAbsent) {
    return MoistureReadingsCompanion(
      id: Value(id),
      readingUuid: Value(readingUuid),
      batchUuid: Value(batchUuid),
      moisturePercent: Value(moisturePercent),
      sequence: Value(sequence),
      sandboxPath: sandboxPath == null && nullToAbsent
          ? const Value.absent()
          : Value(sandboxPath),
      sha256Hash: sha256Hash == null && nullToAbsent
          ? const Value.absent()
          : Value(sha256Hash),
      createdAt: Value(createdAt),
    );
  }

  factory MoistureReading.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return MoistureReading(
      id: serializer.fromJson<int>(json['id']),
      readingUuid: serializer.fromJson<String>(json['readingUuid']),
      batchUuid: serializer.fromJson<String>(json['batchUuid']),
      moisturePercent: serializer.fromJson<double>(json['moisturePercent']),
      sequence: serializer.fromJson<int>(json['sequence']),
      sandboxPath: serializer.fromJson<String?>(json['sandboxPath']),
      sha256Hash: serializer.fromJson<String?>(json['sha256Hash']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'readingUuid': serializer.toJson<String>(readingUuid),
      'batchUuid': serializer.toJson<String>(batchUuid),
      'moisturePercent': serializer.toJson<double>(moisturePercent),
      'sequence': serializer.toJson<int>(sequence),
      'sandboxPath': serializer.toJson<String?>(sandboxPath),
      'sha256Hash': serializer.toJson<String?>(sha256Hash),
      'createdAt': serializer.toJson<String>(createdAt),
    };
  }

  MoistureReading copyWith({
    int? id,
    String? readingUuid,
    String? batchUuid,
    double? moisturePercent,
    int? sequence,
    Value<String?> sandboxPath = const Value.absent(),
    Value<String?> sha256Hash = const Value.absent(),
    String? createdAt,
  }) => MoistureReading(
    id: id ?? this.id,
    readingUuid: readingUuid ?? this.readingUuid,
    batchUuid: batchUuid ?? this.batchUuid,
    moisturePercent: moisturePercent ?? this.moisturePercent,
    sequence: sequence ?? this.sequence,
    sandboxPath: sandboxPath.present ? sandboxPath.value : this.sandboxPath,
    sha256Hash: sha256Hash.present ? sha256Hash.value : this.sha256Hash,
    createdAt: createdAt ?? this.createdAt,
  );
  MoistureReading copyWithCompanion(MoistureReadingsCompanion data) {
    return MoistureReading(
      id: data.id.present ? data.id.value : this.id,
      readingUuid: data.readingUuid.present
          ? data.readingUuid.value
          : this.readingUuid,
      batchUuid: data.batchUuid.present ? data.batchUuid.value : this.batchUuid,
      moisturePercent: data.moisturePercent.present
          ? data.moisturePercent.value
          : this.moisturePercent,
      sequence: data.sequence.present ? data.sequence.value : this.sequence,
      sandboxPath: data.sandboxPath.present
          ? data.sandboxPath.value
          : this.sandboxPath,
      sha256Hash: data.sha256Hash.present
          ? data.sha256Hash.value
          : this.sha256Hash,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('MoistureReading(')
          ..write('id: $id, ')
          ..write('readingUuid: $readingUuid, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('moisturePercent: $moisturePercent, ')
          ..write('sequence: $sequence, ')
          ..write('sandboxPath: $sandboxPath, ')
          ..write('sha256Hash: $sha256Hash, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    readingUuid,
    batchUuid,
    moisturePercent,
    sequence,
    sandboxPath,
    sha256Hash,
    createdAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is MoistureReading &&
          other.id == this.id &&
          other.readingUuid == this.readingUuid &&
          other.batchUuid == this.batchUuid &&
          other.moisturePercent == this.moisturePercent &&
          other.sequence == this.sequence &&
          other.sandboxPath == this.sandboxPath &&
          other.sha256Hash == this.sha256Hash &&
          other.createdAt == this.createdAt);
}

class MoistureReadingsCompanion extends UpdateCompanion<MoistureReading> {
  final Value<int> id;
  final Value<String> readingUuid;
  final Value<String> batchUuid;
  final Value<double> moisturePercent;
  final Value<int> sequence;
  final Value<String?> sandboxPath;
  final Value<String?> sha256Hash;
  final Value<String> createdAt;
  const MoistureReadingsCompanion({
    this.id = const Value.absent(),
    this.readingUuid = const Value.absent(),
    this.batchUuid = const Value.absent(),
    this.moisturePercent = const Value.absent(),
    this.sequence = const Value.absent(),
    this.sandboxPath = const Value.absent(),
    this.sha256Hash = const Value.absent(),
    this.createdAt = const Value.absent(),
  });
  MoistureReadingsCompanion.insert({
    this.id = const Value.absent(),
    required String readingUuid,
    required String batchUuid,
    required double moisturePercent,
    required int sequence,
    this.sandboxPath = const Value.absent(),
    this.sha256Hash = const Value.absent(),
    required String createdAt,
  }) : readingUuid = Value(readingUuid),
       batchUuid = Value(batchUuid),
       moisturePercent = Value(moisturePercent),
       sequence = Value(sequence),
       createdAt = Value(createdAt);
  static Insertable<MoistureReading> custom({
    Expression<int>? id,
    Expression<String>? readingUuid,
    Expression<String>? batchUuid,
    Expression<double>? moisturePercent,
    Expression<int>? sequence,
    Expression<String>? sandboxPath,
    Expression<String>? sha256Hash,
    Expression<String>? createdAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (readingUuid != null) 'reading_uuid': readingUuid,
      if (batchUuid != null) 'batch_uuid': batchUuid,
      if (moisturePercent != null) 'moisture_percent': moisturePercent,
      if (sequence != null) 'sequence': sequence,
      if (sandboxPath != null) 'sandbox_path': sandboxPath,
      if (sha256Hash != null) 'sha256_hash': sha256Hash,
      if (createdAt != null) 'created_at': createdAt,
    });
  }

  MoistureReadingsCompanion copyWith({
    Value<int>? id,
    Value<String>? readingUuid,
    Value<String>? batchUuid,
    Value<double>? moisturePercent,
    Value<int>? sequence,
    Value<String?>? sandboxPath,
    Value<String?>? sha256Hash,
    Value<String>? createdAt,
  }) {
    return MoistureReadingsCompanion(
      id: id ?? this.id,
      readingUuid: readingUuid ?? this.readingUuid,
      batchUuid: batchUuid ?? this.batchUuid,
      moisturePercent: moisturePercent ?? this.moisturePercent,
      sequence: sequence ?? this.sequence,
      sandboxPath: sandboxPath ?? this.sandboxPath,
      sha256Hash: sha256Hash ?? this.sha256Hash,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (readingUuid.present) {
      map['reading_uuid'] = Variable<String>(readingUuid.value);
    }
    if (batchUuid.present) {
      map['batch_uuid'] = Variable<String>(batchUuid.value);
    }
    if (moisturePercent.present) {
      map['moisture_percent'] = Variable<double>(moisturePercent.value);
    }
    if (sequence.present) {
      map['sequence'] = Variable<int>(sequence.value);
    }
    if (sandboxPath.present) {
      map['sandbox_path'] = Variable<String>(sandboxPath.value);
    }
    if (sha256Hash.present) {
      map['sha256_hash'] = Variable<String>(sha256Hash.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('MoistureReadingsCompanion(')
          ..write('id: $id, ')
          ..write('readingUuid: $readingUuid, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('moisturePercent: $moisturePercent, ')
          ..write('sequence: $sequence, ')
          ..write('sandboxPath: $sandboxPath, ')
          ..write('sha256Hash: $sha256Hash, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }
}

class $CompositePileSamplesTable extends CompositePileSamples
    with TableInfo<$CompositePileSamplesTable, CompositePileSample> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CompositePileSamplesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _sampleUuidMeta = const VerificationMeta(
    'sampleUuid',
  );
  @override
  late final GeneratedColumn<String> sampleUuid = GeneratedColumn<String>(
    'sample_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _batchUuidMeta = const VerificationMeta(
    'batchUuid',
  );
  @override
  late final GeneratedColumn<String> batchUuid = GeneratedColumn<String>(
    'batch_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES system_metadata (batch_uuid)',
    ),
  );
  static const VerificationMeta _sampledAtMeta = const VerificationMeta(
    'sampledAt',
  );
  @override
  late final GeneratedColumn<String> sampledAt = GeneratedColumn<String>(
    'sampled_at',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _latitudeMeta = const VerificationMeta(
    'latitude',
  );
  @override
  late final GeneratedColumn<double> latitude = GeneratedColumn<double>(
    'latitude',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _longitudeMeta = const VerificationMeta(
    'longitude',
  );
  @override
  late final GeneratedColumn<double> longitude = GeneratedColumn<double>(
    'longitude',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _kilnQrMeta = const VerificationMeta('kilnQr');
  @override
  late final GeneratedColumn<String> kilnQr = GeneratedColumn<String>(
    'kiln_qr',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _batchQrMeta = const VerificationMeta(
    'batchQr',
  );
  @override
  late final GeneratedColumn<String> batchQr = GeneratedColumn<String>(
    'batch_qr',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _sandboxPathMeta = const VerificationMeta(
    'sandboxPath',
  );
  @override
  late final GeneratedColumn<String> sandboxPath = GeneratedColumn<String>(
    'sandbox_path',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _sha256HashMeta = const VerificationMeta(
    'sha256Hash',
  );
  @override
  late final GeneratedColumn<String> sha256Hash = GeneratedColumn<String>(
    'sha256_hash',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    sampleUuid,
    batchUuid,
    sampledAt,
    latitude,
    longitude,
    kilnQr,
    batchQr,
    sandboxPath,
    sha256Hash,
    createdAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'composite_pile_samples';
  @override
  VerificationContext validateIntegrity(
    Insertable<CompositePileSample> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('sample_uuid')) {
      context.handle(
        _sampleUuidMeta,
        sampleUuid.isAcceptableOrUnknown(data['sample_uuid']!, _sampleUuidMeta),
      );
    } else if (isInserting) {
      context.missing(_sampleUuidMeta);
    }
    if (data.containsKey('batch_uuid')) {
      context.handle(
        _batchUuidMeta,
        batchUuid.isAcceptableOrUnknown(data['batch_uuid']!, _batchUuidMeta),
      );
    } else if (isInserting) {
      context.missing(_batchUuidMeta);
    }
    if (data.containsKey('sampled_at')) {
      context.handle(
        _sampledAtMeta,
        sampledAt.isAcceptableOrUnknown(data['sampled_at']!, _sampledAtMeta),
      );
    }
    if (data.containsKey('latitude')) {
      context.handle(
        _latitudeMeta,
        latitude.isAcceptableOrUnknown(data['latitude']!, _latitudeMeta),
      );
    }
    if (data.containsKey('longitude')) {
      context.handle(
        _longitudeMeta,
        longitude.isAcceptableOrUnknown(data['longitude']!, _longitudeMeta),
      );
    }
    if (data.containsKey('kiln_qr')) {
      context.handle(
        _kilnQrMeta,
        kilnQr.isAcceptableOrUnknown(data['kiln_qr']!, _kilnQrMeta),
      );
    }
    if (data.containsKey('batch_qr')) {
      context.handle(
        _batchQrMeta,
        batchQr.isAcceptableOrUnknown(data['batch_qr']!, _batchQrMeta),
      );
    }
    if (data.containsKey('sandbox_path')) {
      context.handle(
        _sandboxPathMeta,
        sandboxPath.isAcceptableOrUnknown(
          data['sandbox_path']!,
          _sandboxPathMeta,
        ),
      );
    }
    if (data.containsKey('sha256_hash')) {
      context.handle(
        _sha256HashMeta,
        sha256Hash.isAcceptableOrUnknown(data['sha256_hash']!, _sha256HashMeta),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  List<Set<GeneratedColumn>> get uniqueKeys => [
    {sampleUuid},
  ];
  @override
  CompositePileSample map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CompositePileSample(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      sampleUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sample_uuid'],
      )!,
      batchUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}batch_uuid'],
      )!,
      sampledAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sampled_at'],
      ),
      latitude: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}latitude'],
      ),
      longitude: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}longitude'],
      ),
      kilnQr: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}kiln_qr'],
      ),
      batchQr: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}batch_qr'],
      ),
      sandboxPath: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sandbox_path'],
      ),
      sha256Hash: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sha256_hash'],
      ),
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $CompositePileSamplesTable createAlias(String alias) {
    return $CompositePileSamplesTable(attachedDatabase, alias);
  }
}

class CompositePileSample extends DataClass
    implements Insertable<CompositePileSample> {
  final int id;
  final String sampleUuid;
  final String batchUuid;

  /// When the sub-sample was set aside (ISO-8601 UTC).
  final String? sampledAt;

  /// Location where the sub-sample was taken.
  final double? latitude;
  final double? longitude;

  /// Kiln ID/QR and batch ID/QR scanned at sampling (chain-of-custody linkage).
  final String? kilnQr;
  final String? batchQr;

  /// Sandboxed photo of the sub-sample + its SHA-256 (uploaded via /media).
  final String? sandboxPath;
  final String? sha256Hash;
  final String createdAt;
  const CompositePileSample({
    required this.id,
    required this.sampleUuid,
    required this.batchUuid,
    this.sampledAt,
    this.latitude,
    this.longitude,
    this.kilnQr,
    this.batchQr,
    this.sandboxPath,
    this.sha256Hash,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['sample_uuid'] = Variable<String>(sampleUuid);
    map['batch_uuid'] = Variable<String>(batchUuid);
    if (!nullToAbsent || sampledAt != null) {
      map['sampled_at'] = Variable<String>(sampledAt);
    }
    if (!nullToAbsent || latitude != null) {
      map['latitude'] = Variable<double>(latitude);
    }
    if (!nullToAbsent || longitude != null) {
      map['longitude'] = Variable<double>(longitude);
    }
    if (!nullToAbsent || kilnQr != null) {
      map['kiln_qr'] = Variable<String>(kilnQr);
    }
    if (!nullToAbsent || batchQr != null) {
      map['batch_qr'] = Variable<String>(batchQr);
    }
    if (!nullToAbsent || sandboxPath != null) {
      map['sandbox_path'] = Variable<String>(sandboxPath);
    }
    if (!nullToAbsent || sha256Hash != null) {
      map['sha256_hash'] = Variable<String>(sha256Hash);
    }
    map['created_at'] = Variable<String>(createdAt);
    return map;
  }

  CompositePileSamplesCompanion toCompanion(bool nullToAbsent) {
    return CompositePileSamplesCompanion(
      id: Value(id),
      sampleUuid: Value(sampleUuid),
      batchUuid: Value(batchUuid),
      sampledAt: sampledAt == null && nullToAbsent
          ? const Value.absent()
          : Value(sampledAt),
      latitude: latitude == null && nullToAbsent
          ? const Value.absent()
          : Value(latitude),
      longitude: longitude == null && nullToAbsent
          ? const Value.absent()
          : Value(longitude),
      kilnQr: kilnQr == null && nullToAbsent
          ? const Value.absent()
          : Value(kilnQr),
      batchQr: batchQr == null && nullToAbsent
          ? const Value.absent()
          : Value(batchQr),
      sandboxPath: sandboxPath == null && nullToAbsent
          ? const Value.absent()
          : Value(sandboxPath),
      sha256Hash: sha256Hash == null && nullToAbsent
          ? const Value.absent()
          : Value(sha256Hash),
      createdAt: Value(createdAt),
    );
  }

  factory CompositePileSample.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CompositePileSample(
      id: serializer.fromJson<int>(json['id']),
      sampleUuid: serializer.fromJson<String>(json['sampleUuid']),
      batchUuid: serializer.fromJson<String>(json['batchUuid']),
      sampledAt: serializer.fromJson<String?>(json['sampledAt']),
      latitude: serializer.fromJson<double?>(json['latitude']),
      longitude: serializer.fromJson<double?>(json['longitude']),
      kilnQr: serializer.fromJson<String?>(json['kilnQr']),
      batchQr: serializer.fromJson<String?>(json['batchQr']),
      sandboxPath: serializer.fromJson<String?>(json['sandboxPath']),
      sha256Hash: serializer.fromJson<String?>(json['sha256Hash']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'sampleUuid': serializer.toJson<String>(sampleUuid),
      'batchUuid': serializer.toJson<String>(batchUuid),
      'sampledAt': serializer.toJson<String?>(sampledAt),
      'latitude': serializer.toJson<double?>(latitude),
      'longitude': serializer.toJson<double?>(longitude),
      'kilnQr': serializer.toJson<String?>(kilnQr),
      'batchQr': serializer.toJson<String?>(batchQr),
      'sandboxPath': serializer.toJson<String?>(sandboxPath),
      'sha256Hash': serializer.toJson<String?>(sha256Hash),
      'createdAt': serializer.toJson<String>(createdAt),
    };
  }

  CompositePileSample copyWith({
    int? id,
    String? sampleUuid,
    String? batchUuid,
    Value<String?> sampledAt = const Value.absent(),
    Value<double?> latitude = const Value.absent(),
    Value<double?> longitude = const Value.absent(),
    Value<String?> kilnQr = const Value.absent(),
    Value<String?> batchQr = const Value.absent(),
    Value<String?> sandboxPath = const Value.absent(),
    Value<String?> sha256Hash = const Value.absent(),
    String? createdAt,
  }) => CompositePileSample(
    id: id ?? this.id,
    sampleUuid: sampleUuid ?? this.sampleUuid,
    batchUuid: batchUuid ?? this.batchUuid,
    sampledAt: sampledAt.present ? sampledAt.value : this.sampledAt,
    latitude: latitude.present ? latitude.value : this.latitude,
    longitude: longitude.present ? longitude.value : this.longitude,
    kilnQr: kilnQr.present ? kilnQr.value : this.kilnQr,
    batchQr: batchQr.present ? batchQr.value : this.batchQr,
    sandboxPath: sandboxPath.present ? sandboxPath.value : this.sandboxPath,
    sha256Hash: sha256Hash.present ? sha256Hash.value : this.sha256Hash,
    createdAt: createdAt ?? this.createdAt,
  );
  CompositePileSample copyWithCompanion(CompositePileSamplesCompanion data) {
    return CompositePileSample(
      id: data.id.present ? data.id.value : this.id,
      sampleUuid: data.sampleUuid.present
          ? data.sampleUuid.value
          : this.sampleUuid,
      batchUuid: data.batchUuid.present ? data.batchUuid.value : this.batchUuid,
      sampledAt: data.sampledAt.present ? data.sampledAt.value : this.sampledAt,
      latitude: data.latitude.present ? data.latitude.value : this.latitude,
      longitude: data.longitude.present ? data.longitude.value : this.longitude,
      kilnQr: data.kilnQr.present ? data.kilnQr.value : this.kilnQr,
      batchQr: data.batchQr.present ? data.batchQr.value : this.batchQr,
      sandboxPath: data.sandboxPath.present
          ? data.sandboxPath.value
          : this.sandboxPath,
      sha256Hash: data.sha256Hash.present
          ? data.sha256Hash.value
          : this.sha256Hash,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CompositePileSample(')
          ..write('id: $id, ')
          ..write('sampleUuid: $sampleUuid, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('sampledAt: $sampledAt, ')
          ..write('latitude: $latitude, ')
          ..write('longitude: $longitude, ')
          ..write('kilnQr: $kilnQr, ')
          ..write('batchQr: $batchQr, ')
          ..write('sandboxPath: $sandboxPath, ')
          ..write('sha256Hash: $sha256Hash, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    sampleUuid,
    batchUuid,
    sampledAt,
    latitude,
    longitude,
    kilnQr,
    batchQr,
    sandboxPath,
    sha256Hash,
    createdAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CompositePileSample &&
          other.id == this.id &&
          other.sampleUuid == this.sampleUuid &&
          other.batchUuid == this.batchUuid &&
          other.sampledAt == this.sampledAt &&
          other.latitude == this.latitude &&
          other.longitude == this.longitude &&
          other.kilnQr == this.kilnQr &&
          other.batchQr == this.batchQr &&
          other.sandboxPath == this.sandboxPath &&
          other.sha256Hash == this.sha256Hash &&
          other.createdAt == this.createdAt);
}

class CompositePileSamplesCompanion
    extends UpdateCompanion<CompositePileSample> {
  final Value<int> id;
  final Value<String> sampleUuid;
  final Value<String> batchUuid;
  final Value<String?> sampledAt;
  final Value<double?> latitude;
  final Value<double?> longitude;
  final Value<String?> kilnQr;
  final Value<String?> batchQr;
  final Value<String?> sandboxPath;
  final Value<String?> sha256Hash;
  final Value<String> createdAt;
  const CompositePileSamplesCompanion({
    this.id = const Value.absent(),
    this.sampleUuid = const Value.absent(),
    this.batchUuid = const Value.absent(),
    this.sampledAt = const Value.absent(),
    this.latitude = const Value.absent(),
    this.longitude = const Value.absent(),
    this.kilnQr = const Value.absent(),
    this.batchQr = const Value.absent(),
    this.sandboxPath = const Value.absent(),
    this.sha256Hash = const Value.absent(),
    this.createdAt = const Value.absent(),
  });
  CompositePileSamplesCompanion.insert({
    this.id = const Value.absent(),
    required String sampleUuid,
    required String batchUuid,
    this.sampledAt = const Value.absent(),
    this.latitude = const Value.absent(),
    this.longitude = const Value.absent(),
    this.kilnQr = const Value.absent(),
    this.batchQr = const Value.absent(),
    this.sandboxPath = const Value.absent(),
    this.sha256Hash = const Value.absent(),
    required String createdAt,
  }) : sampleUuid = Value(sampleUuid),
       batchUuid = Value(batchUuid),
       createdAt = Value(createdAt);
  static Insertable<CompositePileSample> custom({
    Expression<int>? id,
    Expression<String>? sampleUuid,
    Expression<String>? batchUuid,
    Expression<String>? sampledAt,
    Expression<double>? latitude,
    Expression<double>? longitude,
    Expression<String>? kilnQr,
    Expression<String>? batchQr,
    Expression<String>? sandboxPath,
    Expression<String>? sha256Hash,
    Expression<String>? createdAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (sampleUuid != null) 'sample_uuid': sampleUuid,
      if (batchUuid != null) 'batch_uuid': batchUuid,
      if (sampledAt != null) 'sampled_at': sampledAt,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      if (kilnQr != null) 'kiln_qr': kilnQr,
      if (batchQr != null) 'batch_qr': batchQr,
      if (sandboxPath != null) 'sandbox_path': sandboxPath,
      if (sha256Hash != null) 'sha256_hash': sha256Hash,
      if (createdAt != null) 'created_at': createdAt,
    });
  }

  CompositePileSamplesCompanion copyWith({
    Value<int>? id,
    Value<String>? sampleUuid,
    Value<String>? batchUuid,
    Value<String?>? sampledAt,
    Value<double?>? latitude,
    Value<double?>? longitude,
    Value<String?>? kilnQr,
    Value<String?>? batchQr,
    Value<String?>? sandboxPath,
    Value<String?>? sha256Hash,
    Value<String>? createdAt,
  }) {
    return CompositePileSamplesCompanion(
      id: id ?? this.id,
      sampleUuid: sampleUuid ?? this.sampleUuid,
      batchUuid: batchUuid ?? this.batchUuid,
      sampledAt: sampledAt ?? this.sampledAt,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      kilnQr: kilnQr ?? this.kilnQr,
      batchQr: batchQr ?? this.batchQr,
      sandboxPath: sandboxPath ?? this.sandboxPath,
      sha256Hash: sha256Hash ?? this.sha256Hash,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (sampleUuid.present) {
      map['sample_uuid'] = Variable<String>(sampleUuid.value);
    }
    if (batchUuid.present) {
      map['batch_uuid'] = Variable<String>(batchUuid.value);
    }
    if (sampledAt.present) {
      map['sampled_at'] = Variable<String>(sampledAt.value);
    }
    if (latitude.present) {
      map['latitude'] = Variable<double>(latitude.value);
    }
    if (longitude.present) {
      map['longitude'] = Variable<double>(longitude.value);
    }
    if (kilnQr.present) {
      map['kiln_qr'] = Variable<String>(kilnQr.value);
    }
    if (batchQr.present) {
      map['batch_qr'] = Variable<String>(batchQr.value);
    }
    if (sandboxPath.present) {
      map['sandbox_path'] = Variable<String>(sandboxPath.value);
    }
    if (sha256Hash.present) {
      map['sha256_hash'] = Variable<String>(sha256Hash.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CompositePileSamplesCompanion(')
          ..write('id: $id, ')
          ..write('sampleUuid: $sampleUuid, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('sampledAt: $sampledAt, ')
          ..write('latitude: $latitude, ')
          ..write('longitude: $longitude, ')
          ..write('kilnQr: $kilnQr, ')
          ..write('batchQr: $batchQr, ')
          ..write('sandboxPath: $sandboxPath, ')
          ..write('sha256Hash: $sha256Hash, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }
}

class $TransportEventsTable extends TransportEvents
    with TableInfo<$TransportEventsTable, TransportEvent> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $TransportEventsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _eventUuidMeta = const VerificationMeta(
    'eventUuid',
  );
  @override
  late final GeneratedColumn<String> eventUuid = GeneratedColumn<String>(
    'event_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _batchUuidMeta = const VerificationMeta(
    'batchUuid',
  );
  @override
  late final GeneratedColumn<String> batchUuid = GeneratedColumn<String>(
    'batch_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'REFERENCES system_metadata (batch_uuid)',
    ),
  );
  static const VerificationMeta _materialMeta = const VerificationMeta(
    'material',
  );
  @override
  late final GeneratedColumn<String> material = GeneratedColumn<String>(
    'material',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _distanceKmMeta = const VerificationMeta(
    'distanceKm',
  );
  @override
  late final GeneratedColumn<double> distanceKm = GeneratedColumn<double>(
    'distance_km',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _weightKgMeta = const VerificationMeta(
    'weightKg',
  );
  @override
  late final GeneratedColumn<double> weightKg = GeneratedColumn<double>(
    'weight_kg',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _vehicleTypeMeta = const VerificationMeta(
    'vehicleType',
  );
  @override
  late final GeneratedColumn<String> vehicleType = GeneratedColumn<String>(
    'vehicle_type',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _fuelTypeMeta = const VerificationMeta(
    'fuelType',
  );
  @override
  late final GeneratedColumn<String> fuelType = GeneratedColumn<String>(
    'fuel_type',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _fuelAmountLitresMeta = const VerificationMeta(
    'fuelAmountLitres',
  );
  @override
  late final GeneratedColumn<double> fuelAmountLitres = GeneratedColumn<double>(
    'fuel_amount_litres',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _occurredAtMeta = const VerificationMeta(
    'occurredAt',
  );
  @override
  late final GeneratedColumn<String> occurredAt = GeneratedColumn<String>(
    'occurred_at',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    eventUuid,
    batchUuid,
    material,
    distanceKm,
    weightKg,
    vehicleType,
    fuelType,
    fuelAmountLitres,
    occurredAt,
    createdAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'transport_events';
  @override
  VerificationContext validateIntegrity(
    Insertable<TransportEvent> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('event_uuid')) {
      context.handle(
        _eventUuidMeta,
        eventUuid.isAcceptableOrUnknown(data['event_uuid']!, _eventUuidMeta),
      );
    } else if (isInserting) {
      context.missing(_eventUuidMeta);
    }
    if (data.containsKey('batch_uuid')) {
      context.handle(
        _batchUuidMeta,
        batchUuid.isAcceptableOrUnknown(data['batch_uuid']!, _batchUuidMeta),
      );
    } else if (isInserting) {
      context.missing(_batchUuidMeta);
    }
    if (data.containsKey('material')) {
      context.handle(
        _materialMeta,
        material.isAcceptableOrUnknown(data['material']!, _materialMeta),
      );
    } else if (isInserting) {
      context.missing(_materialMeta);
    }
    if (data.containsKey('distance_km')) {
      context.handle(
        _distanceKmMeta,
        distanceKm.isAcceptableOrUnknown(data['distance_km']!, _distanceKmMeta),
      );
    }
    if (data.containsKey('weight_kg')) {
      context.handle(
        _weightKgMeta,
        weightKg.isAcceptableOrUnknown(data['weight_kg']!, _weightKgMeta),
      );
    }
    if (data.containsKey('vehicle_type')) {
      context.handle(
        _vehicleTypeMeta,
        vehicleType.isAcceptableOrUnknown(
          data['vehicle_type']!,
          _vehicleTypeMeta,
        ),
      );
    }
    if (data.containsKey('fuel_type')) {
      context.handle(
        _fuelTypeMeta,
        fuelType.isAcceptableOrUnknown(data['fuel_type']!, _fuelTypeMeta),
      );
    }
    if (data.containsKey('fuel_amount_litres')) {
      context.handle(
        _fuelAmountLitresMeta,
        fuelAmountLitres.isAcceptableOrUnknown(
          data['fuel_amount_litres']!,
          _fuelAmountLitresMeta,
        ),
      );
    }
    if (data.containsKey('occurred_at')) {
      context.handle(
        _occurredAtMeta,
        occurredAt.isAcceptableOrUnknown(data['occurred_at']!, _occurredAtMeta),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  List<Set<GeneratedColumn>> get uniqueKeys => [
    {eventUuid},
  ];
  @override
  TransportEvent map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return TransportEvent(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      eventUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}event_uuid'],
      )!,
      batchUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}batch_uuid'],
      )!,
      material: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}material'],
      )!,
      distanceKm: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}distance_km'],
      ),
      weightKg: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}weight_kg'],
      ),
      vehicleType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}vehicle_type'],
      ),
      fuelType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}fuel_type'],
      ),
      fuelAmountLitres: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}fuel_amount_litres'],
      ),
      occurredAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}occurred_at'],
      ),
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $TransportEventsTable createAlias(String alias) {
    return $TransportEventsTable(attachedDatabase, alias);
  }
}

class TransportEvent extends DataClass implements Insertable<TransportEvent> {
  final int id;
  final String eventUuid;
  final String batchUuid;

  /// 'biomass' | 'biochar' — which leg of the chain this event covers.
  final String material;
  final double? distanceKm;
  final double? weightKg;
  final String? vehicleType;

  /// Fuel type (e.g. 'diesel') + amount in litres consumed on this leg.
  final String? fuelType;
  final double? fuelAmountLitres;
  final String? occurredAt;
  final String createdAt;
  const TransportEvent({
    required this.id,
    required this.eventUuid,
    required this.batchUuid,
    required this.material,
    this.distanceKm,
    this.weightKg,
    this.vehicleType,
    this.fuelType,
    this.fuelAmountLitres,
    this.occurredAt,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['event_uuid'] = Variable<String>(eventUuid);
    map['batch_uuid'] = Variable<String>(batchUuid);
    map['material'] = Variable<String>(material);
    if (!nullToAbsent || distanceKm != null) {
      map['distance_km'] = Variable<double>(distanceKm);
    }
    if (!nullToAbsent || weightKg != null) {
      map['weight_kg'] = Variable<double>(weightKg);
    }
    if (!nullToAbsent || vehicleType != null) {
      map['vehicle_type'] = Variable<String>(vehicleType);
    }
    if (!nullToAbsent || fuelType != null) {
      map['fuel_type'] = Variable<String>(fuelType);
    }
    if (!nullToAbsent || fuelAmountLitres != null) {
      map['fuel_amount_litres'] = Variable<double>(fuelAmountLitres);
    }
    if (!nullToAbsent || occurredAt != null) {
      map['occurred_at'] = Variable<String>(occurredAt);
    }
    map['created_at'] = Variable<String>(createdAt);
    return map;
  }

  TransportEventsCompanion toCompanion(bool nullToAbsent) {
    return TransportEventsCompanion(
      id: Value(id),
      eventUuid: Value(eventUuid),
      batchUuid: Value(batchUuid),
      material: Value(material),
      distanceKm: distanceKm == null && nullToAbsent
          ? const Value.absent()
          : Value(distanceKm),
      weightKg: weightKg == null && nullToAbsent
          ? const Value.absent()
          : Value(weightKg),
      vehicleType: vehicleType == null && nullToAbsent
          ? const Value.absent()
          : Value(vehicleType),
      fuelType: fuelType == null && nullToAbsent
          ? const Value.absent()
          : Value(fuelType),
      fuelAmountLitres: fuelAmountLitres == null && nullToAbsent
          ? const Value.absent()
          : Value(fuelAmountLitres),
      occurredAt: occurredAt == null && nullToAbsent
          ? const Value.absent()
          : Value(occurredAt),
      createdAt: Value(createdAt),
    );
  }

  factory TransportEvent.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return TransportEvent(
      id: serializer.fromJson<int>(json['id']),
      eventUuid: serializer.fromJson<String>(json['eventUuid']),
      batchUuid: serializer.fromJson<String>(json['batchUuid']),
      material: serializer.fromJson<String>(json['material']),
      distanceKm: serializer.fromJson<double?>(json['distanceKm']),
      weightKg: serializer.fromJson<double?>(json['weightKg']),
      vehicleType: serializer.fromJson<String?>(json['vehicleType']),
      fuelType: serializer.fromJson<String?>(json['fuelType']),
      fuelAmountLitres: serializer.fromJson<double?>(json['fuelAmountLitres']),
      occurredAt: serializer.fromJson<String?>(json['occurredAt']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'eventUuid': serializer.toJson<String>(eventUuid),
      'batchUuid': serializer.toJson<String>(batchUuid),
      'material': serializer.toJson<String>(material),
      'distanceKm': serializer.toJson<double?>(distanceKm),
      'weightKg': serializer.toJson<double?>(weightKg),
      'vehicleType': serializer.toJson<String?>(vehicleType),
      'fuelType': serializer.toJson<String?>(fuelType),
      'fuelAmountLitres': serializer.toJson<double?>(fuelAmountLitres),
      'occurredAt': serializer.toJson<String?>(occurredAt),
      'createdAt': serializer.toJson<String>(createdAt),
    };
  }

  TransportEvent copyWith({
    int? id,
    String? eventUuid,
    String? batchUuid,
    String? material,
    Value<double?> distanceKm = const Value.absent(),
    Value<double?> weightKg = const Value.absent(),
    Value<String?> vehicleType = const Value.absent(),
    Value<String?> fuelType = const Value.absent(),
    Value<double?> fuelAmountLitres = const Value.absent(),
    Value<String?> occurredAt = const Value.absent(),
    String? createdAt,
  }) => TransportEvent(
    id: id ?? this.id,
    eventUuid: eventUuid ?? this.eventUuid,
    batchUuid: batchUuid ?? this.batchUuid,
    material: material ?? this.material,
    distanceKm: distanceKm.present ? distanceKm.value : this.distanceKm,
    weightKg: weightKg.present ? weightKg.value : this.weightKg,
    vehicleType: vehicleType.present ? vehicleType.value : this.vehicleType,
    fuelType: fuelType.present ? fuelType.value : this.fuelType,
    fuelAmountLitres: fuelAmountLitres.present
        ? fuelAmountLitres.value
        : this.fuelAmountLitres,
    occurredAt: occurredAt.present ? occurredAt.value : this.occurredAt,
    createdAt: createdAt ?? this.createdAt,
  );
  TransportEvent copyWithCompanion(TransportEventsCompanion data) {
    return TransportEvent(
      id: data.id.present ? data.id.value : this.id,
      eventUuid: data.eventUuid.present ? data.eventUuid.value : this.eventUuid,
      batchUuid: data.batchUuid.present ? data.batchUuid.value : this.batchUuid,
      material: data.material.present ? data.material.value : this.material,
      distanceKm: data.distanceKm.present
          ? data.distanceKm.value
          : this.distanceKm,
      weightKg: data.weightKg.present ? data.weightKg.value : this.weightKg,
      vehicleType: data.vehicleType.present
          ? data.vehicleType.value
          : this.vehicleType,
      fuelType: data.fuelType.present ? data.fuelType.value : this.fuelType,
      fuelAmountLitres: data.fuelAmountLitres.present
          ? data.fuelAmountLitres.value
          : this.fuelAmountLitres,
      occurredAt: data.occurredAt.present
          ? data.occurredAt.value
          : this.occurredAt,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('TransportEvent(')
          ..write('id: $id, ')
          ..write('eventUuid: $eventUuid, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('material: $material, ')
          ..write('distanceKm: $distanceKm, ')
          ..write('weightKg: $weightKg, ')
          ..write('vehicleType: $vehicleType, ')
          ..write('fuelType: $fuelType, ')
          ..write('fuelAmountLitres: $fuelAmountLitres, ')
          ..write('occurredAt: $occurredAt, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    eventUuid,
    batchUuid,
    material,
    distanceKm,
    weightKg,
    vehicleType,
    fuelType,
    fuelAmountLitres,
    occurredAt,
    createdAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is TransportEvent &&
          other.id == this.id &&
          other.eventUuid == this.eventUuid &&
          other.batchUuid == this.batchUuid &&
          other.material == this.material &&
          other.distanceKm == this.distanceKm &&
          other.weightKg == this.weightKg &&
          other.vehicleType == this.vehicleType &&
          other.fuelType == this.fuelType &&
          other.fuelAmountLitres == this.fuelAmountLitres &&
          other.occurredAt == this.occurredAt &&
          other.createdAt == this.createdAt);
}

class TransportEventsCompanion extends UpdateCompanion<TransportEvent> {
  final Value<int> id;
  final Value<String> eventUuid;
  final Value<String> batchUuid;
  final Value<String> material;
  final Value<double?> distanceKm;
  final Value<double?> weightKg;
  final Value<String?> vehicleType;
  final Value<String?> fuelType;
  final Value<double?> fuelAmountLitres;
  final Value<String?> occurredAt;
  final Value<String> createdAt;
  const TransportEventsCompanion({
    this.id = const Value.absent(),
    this.eventUuid = const Value.absent(),
    this.batchUuid = const Value.absent(),
    this.material = const Value.absent(),
    this.distanceKm = const Value.absent(),
    this.weightKg = const Value.absent(),
    this.vehicleType = const Value.absent(),
    this.fuelType = const Value.absent(),
    this.fuelAmountLitres = const Value.absent(),
    this.occurredAt = const Value.absent(),
    this.createdAt = const Value.absent(),
  });
  TransportEventsCompanion.insert({
    this.id = const Value.absent(),
    required String eventUuid,
    required String batchUuid,
    required String material,
    this.distanceKm = const Value.absent(),
    this.weightKg = const Value.absent(),
    this.vehicleType = const Value.absent(),
    this.fuelType = const Value.absent(),
    this.fuelAmountLitres = const Value.absent(),
    this.occurredAt = const Value.absent(),
    required String createdAt,
  }) : eventUuid = Value(eventUuid),
       batchUuid = Value(batchUuid),
       material = Value(material),
       createdAt = Value(createdAt);
  static Insertable<TransportEvent> custom({
    Expression<int>? id,
    Expression<String>? eventUuid,
    Expression<String>? batchUuid,
    Expression<String>? material,
    Expression<double>? distanceKm,
    Expression<double>? weightKg,
    Expression<String>? vehicleType,
    Expression<String>? fuelType,
    Expression<double>? fuelAmountLitres,
    Expression<String>? occurredAt,
    Expression<String>? createdAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (eventUuid != null) 'event_uuid': eventUuid,
      if (batchUuid != null) 'batch_uuid': batchUuid,
      if (material != null) 'material': material,
      if (distanceKm != null) 'distance_km': distanceKm,
      if (weightKg != null) 'weight_kg': weightKg,
      if (vehicleType != null) 'vehicle_type': vehicleType,
      if (fuelType != null) 'fuel_type': fuelType,
      if (fuelAmountLitres != null) 'fuel_amount_litres': fuelAmountLitres,
      if (occurredAt != null) 'occurred_at': occurredAt,
      if (createdAt != null) 'created_at': createdAt,
    });
  }

  TransportEventsCompanion copyWith({
    Value<int>? id,
    Value<String>? eventUuid,
    Value<String>? batchUuid,
    Value<String>? material,
    Value<double?>? distanceKm,
    Value<double?>? weightKg,
    Value<String?>? vehicleType,
    Value<String?>? fuelType,
    Value<double?>? fuelAmountLitres,
    Value<String?>? occurredAt,
    Value<String>? createdAt,
  }) {
    return TransportEventsCompanion(
      id: id ?? this.id,
      eventUuid: eventUuid ?? this.eventUuid,
      batchUuid: batchUuid ?? this.batchUuid,
      material: material ?? this.material,
      distanceKm: distanceKm ?? this.distanceKm,
      weightKg: weightKg ?? this.weightKg,
      vehicleType: vehicleType ?? this.vehicleType,
      fuelType: fuelType ?? this.fuelType,
      fuelAmountLitres: fuelAmountLitres ?? this.fuelAmountLitres,
      occurredAt: occurredAt ?? this.occurredAt,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (eventUuid.present) {
      map['event_uuid'] = Variable<String>(eventUuid.value);
    }
    if (batchUuid.present) {
      map['batch_uuid'] = Variable<String>(batchUuid.value);
    }
    if (material.present) {
      map['material'] = Variable<String>(material.value);
    }
    if (distanceKm.present) {
      map['distance_km'] = Variable<double>(distanceKm.value);
    }
    if (weightKg.present) {
      map['weight_kg'] = Variable<double>(weightKg.value);
    }
    if (vehicleType.present) {
      map['vehicle_type'] = Variable<String>(vehicleType.value);
    }
    if (fuelType.present) {
      map['fuel_type'] = Variable<String>(fuelType.value);
    }
    if (fuelAmountLitres.present) {
      map['fuel_amount_litres'] = Variable<double>(fuelAmountLitres.value);
    }
    if (occurredAt.present) {
      map['occurred_at'] = Variable<String>(occurredAt.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('TransportEventsCompanion(')
          ..write('id: $id, ')
          ..write('eventUuid: $eventUuid, ')
          ..write('batchUuid: $batchUuid, ')
          ..write('material: $material, ')
          ..write('distanceKm: $distanceKm, ')
          ..write('weightKg: $weightKg, ')
          ..write('vehicleType: $vehicleType, ')
          ..write('fuelType: $fuelType, ')
          ..write('fuelAmountLitres: $fuelAmountLitres, ')
          ..write('occurredAt: $occurredAt, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $SystemMetadataTable systemMetadata = $SystemMetadataTable(this);
  late final $BiomassSourcingTable biomassSourcing = $BiomassSourcingTable(
    this,
  );
  late final $PyrolysisTelemetryTable pyrolysisTelemetry =
      $PyrolysisTelemetryTable(this);
  late final $YieldMetricsTable yieldMetrics = $YieldMetricsTable(this);
  late final $EndUseApplicationTable endUseApplication =
      $EndUseApplicationTable(this);
  late final $SyncOutboxTable syncOutbox = $SyncOutboxTable(this);
  late final $MediaCapturesTable mediaCaptures = $MediaCapturesTable(this);
  late final $MoistureReadingsTable moistureReadings = $MoistureReadingsTable(
    this,
  );
  late final $CompositePileSamplesTable compositePileSamples =
      $CompositePileSamplesTable(this);
  late final $TransportEventsTable transportEvents = $TransportEventsTable(
    this,
  );
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    systemMetadata,
    biomassSourcing,
    pyrolysisTelemetry,
    yieldMetrics,
    endUseApplication,
    syncOutbox,
    mediaCaptures,
    moistureReadings,
    compositePileSamples,
    transportEvents,
  ];
}

typedef $$SystemMetadataTableCreateCompanionBuilder =
    SystemMetadataCompanion Function({
      required String batchUuid,
      required String artisanId,
      required String deviceHardwareMac,
      required String appBuildVersion,
      Value<String> syncStatus,
      required String createdAt,
      Value<int> rowid,
    });
typedef $$SystemMetadataTableUpdateCompanionBuilder =
    SystemMetadataCompanion Function({
      Value<String> batchUuid,
      Value<String> artisanId,
      Value<String> deviceHardwareMac,
      Value<String> appBuildVersion,
      Value<String> syncStatus,
      Value<String> createdAt,
      Value<int> rowid,
    });

final class $$SystemMetadataTableReferences
    extends
        BaseReferences<
          _$AppDatabase,
          $SystemMetadataTable,
          SystemMetadataData
        > {
  $$SystemMetadataTableReferences(
    super.$_db,
    super.$_table,
    super.$_typedResult,
  );

  static MultiTypedResultKey<$BiomassSourcingTable, List<BiomassSourcingData>>
  _biomassSourcingRefsTable(_$AppDatabase db) => MultiTypedResultKey.fromTable(
    db.biomassSourcing,
    aliasName: $_aliasNameGenerator(
      db.systemMetadata.batchUuid,
      db.biomassSourcing.batchUuid,
    ),
  );

  $$BiomassSourcingTableProcessedTableManager get biomassSourcingRefs {
    final manager =
        $$BiomassSourcingTableTableManager($_db, $_db.biomassSourcing).filter(
          (f) => f.batchUuid.batchUuid.sqlEquals(
            $_itemColumn<String>('batch_uuid')!,
          ),
        );

    final cache = $_typedResult.readTableOrNull(
      _biomassSourcingRefsTable($_db),
    );
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: cache),
    );
  }

  static MultiTypedResultKey<
    $PyrolysisTelemetryTable,
    List<PyrolysisTelemetryData>
  >
  _pyrolysisTelemetryRefsTable(_$AppDatabase db) =>
      MultiTypedResultKey.fromTable(
        db.pyrolysisTelemetry,
        aliasName: $_aliasNameGenerator(
          db.systemMetadata.batchUuid,
          db.pyrolysisTelemetry.batchUuid,
        ),
      );

  $$PyrolysisTelemetryTableProcessedTableManager get pyrolysisTelemetryRefs {
    final manager =
        $$PyrolysisTelemetryTableTableManager(
          $_db,
          $_db.pyrolysisTelemetry,
        ).filter(
          (f) => f.batchUuid.batchUuid.sqlEquals(
            $_itemColumn<String>('batch_uuid')!,
          ),
        );

    final cache = $_typedResult.readTableOrNull(
      _pyrolysisTelemetryRefsTable($_db),
    );
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: cache),
    );
  }

  static MultiTypedResultKey<$YieldMetricsTable, List<YieldMetric>>
  _yieldMetricsRefsTable(_$AppDatabase db) => MultiTypedResultKey.fromTable(
    db.yieldMetrics,
    aliasName: $_aliasNameGenerator(
      db.systemMetadata.batchUuid,
      db.yieldMetrics.batchUuid,
    ),
  );

  $$YieldMetricsTableProcessedTableManager get yieldMetricsRefs {
    final manager = $$YieldMetricsTableTableManager($_db, $_db.yieldMetrics)
        .filter(
          (f) => f.batchUuid.batchUuid.sqlEquals(
            $_itemColumn<String>('batch_uuid')!,
          ),
        );

    final cache = $_typedResult.readTableOrNull(_yieldMetricsRefsTable($_db));
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: cache),
    );
  }

  static MultiTypedResultKey<
    $EndUseApplicationTable,
    List<EndUseApplicationData>
  >
  _endUseApplicationRefsTable(_$AppDatabase db) =>
      MultiTypedResultKey.fromTable(
        db.endUseApplication,
        aliasName: $_aliasNameGenerator(
          db.systemMetadata.batchUuid,
          db.endUseApplication.batchUuid,
        ),
      );

  $$EndUseApplicationTableProcessedTableManager get endUseApplicationRefs {
    final manager =
        $$EndUseApplicationTableTableManager(
          $_db,
          $_db.endUseApplication,
        ).filter(
          (f) => f.batchUuid.batchUuid.sqlEquals(
            $_itemColumn<String>('batch_uuid')!,
          ),
        );

    final cache = $_typedResult.readTableOrNull(
      _endUseApplicationRefsTable($_db),
    );
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: cache),
    );
  }

  static MultiTypedResultKey<$MediaCapturesTable, List<MediaCapture>>
  _mediaCapturesRefsTable(_$AppDatabase db) => MultiTypedResultKey.fromTable(
    db.mediaCaptures,
    aliasName: $_aliasNameGenerator(
      db.systemMetadata.batchUuid,
      db.mediaCaptures.batchUuid,
    ),
  );

  $$MediaCapturesTableProcessedTableManager get mediaCapturesRefs {
    final manager = $$MediaCapturesTableTableManager($_db, $_db.mediaCaptures)
        .filter(
          (f) => f.batchUuid.batchUuid.sqlEquals(
            $_itemColumn<String>('batch_uuid')!,
          ),
        );

    final cache = $_typedResult.readTableOrNull(_mediaCapturesRefsTable($_db));
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: cache),
    );
  }

  static MultiTypedResultKey<$MoistureReadingsTable, List<MoistureReading>>
  _moistureReadingsRefsTable(_$AppDatabase db) => MultiTypedResultKey.fromTable(
    db.moistureReadings,
    aliasName: $_aliasNameGenerator(
      db.systemMetadata.batchUuid,
      db.moistureReadings.batchUuid,
    ),
  );

  $$MoistureReadingsTableProcessedTableManager get moistureReadingsRefs {
    final manager =
        $$MoistureReadingsTableTableManager($_db, $_db.moistureReadings).filter(
          (f) => f.batchUuid.batchUuid.sqlEquals(
            $_itemColumn<String>('batch_uuid')!,
          ),
        );

    final cache = $_typedResult.readTableOrNull(
      _moistureReadingsRefsTable($_db),
    );
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: cache),
    );
  }

  static MultiTypedResultKey<
    $CompositePileSamplesTable,
    List<CompositePileSample>
  >
  _compositePileSamplesRefsTable(_$AppDatabase db) =>
      MultiTypedResultKey.fromTable(
        db.compositePileSamples,
        aliasName: $_aliasNameGenerator(
          db.systemMetadata.batchUuid,
          db.compositePileSamples.batchUuid,
        ),
      );

  $$CompositePileSamplesTableProcessedTableManager
  get compositePileSamplesRefs {
    final manager =
        $$CompositePileSamplesTableTableManager(
          $_db,
          $_db.compositePileSamples,
        ).filter(
          (f) => f.batchUuid.batchUuid.sqlEquals(
            $_itemColumn<String>('batch_uuid')!,
          ),
        );

    final cache = $_typedResult.readTableOrNull(
      _compositePileSamplesRefsTable($_db),
    );
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: cache),
    );
  }

  static MultiTypedResultKey<$TransportEventsTable, List<TransportEvent>>
  _transportEventsRefsTable(_$AppDatabase db) => MultiTypedResultKey.fromTable(
    db.transportEvents,
    aliasName: $_aliasNameGenerator(
      db.systemMetadata.batchUuid,
      db.transportEvents.batchUuid,
    ),
  );

  $$TransportEventsTableProcessedTableManager get transportEventsRefs {
    final manager =
        $$TransportEventsTableTableManager($_db, $_db.transportEvents).filter(
          (f) => f.batchUuid.batchUuid.sqlEquals(
            $_itemColumn<String>('batch_uuid')!,
          ),
        );

    final cache = $_typedResult.readTableOrNull(
      _transportEventsRefsTable($_db),
    );
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: cache),
    );
  }
}

class $$SystemMetadataTableFilterComposer
    extends Composer<_$AppDatabase, $SystemMetadataTable> {
  $$SystemMetadataTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get batchUuid => $composableBuilder(
    column: $table.batchUuid,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get artisanId => $composableBuilder(
    column: $table.artisanId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get deviceHardwareMac => $composableBuilder(
    column: $table.deviceHardwareMac,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get appBuildVersion => $composableBuilder(
    column: $table.appBuildVersion,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get syncStatus => $composableBuilder(
    column: $table.syncStatus,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  Expression<bool> biomassSourcingRefs(
    Expression<bool> Function($$BiomassSourcingTableFilterComposer f) f,
  ) {
    final $$BiomassSourcingTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.biomassSourcing,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$BiomassSourcingTableFilterComposer(
            $db: $db,
            $table: $db.biomassSourcing,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return f(composer);
  }

  Expression<bool> pyrolysisTelemetryRefs(
    Expression<bool> Function($$PyrolysisTelemetryTableFilterComposer f) f,
  ) {
    final $$PyrolysisTelemetryTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.pyrolysisTelemetry,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$PyrolysisTelemetryTableFilterComposer(
            $db: $db,
            $table: $db.pyrolysisTelemetry,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return f(composer);
  }

  Expression<bool> yieldMetricsRefs(
    Expression<bool> Function($$YieldMetricsTableFilterComposer f) f,
  ) {
    final $$YieldMetricsTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.yieldMetrics,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$YieldMetricsTableFilterComposer(
            $db: $db,
            $table: $db.yieldMetrics,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return f(composer);
  }

  Expression<bool> endUseApplicationRefs(
    Expression<bool> Function($$EndUseApplicationTableFilterComposer f) f,
  ) {
    final $$EndUseApplicationTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.endUseApplication,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$EndUseApplicationTableFilterComposer(
            $db: $db,
            $table: $db.endUseApplication,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return f(composer);
  }

  Expression<bool> mediaCapturesRefs(
    Expression<bool> Function($$MediaCapturesTableFilterComposer f) f,
  ) {
    final $$MediaCapturesTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.mediaCaptures,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$MediaCapturesTableFilterComposer(
            $db: $db,
            $table: $db.mediaCaptures,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return f(composer);
  }

  Expression<bool> moistureReadingsRefs(
    Expression<bool> Function($$MoistureReadingsTableFilterComposer f) f,
  ) {
    final $$MoistureReadingsTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.moistureReadings,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$MoistureReadingsTableFilterComposer(
            $db: $db,
            $table: $db.moistureReadings,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return f(composer);
  }

  Expression<bool> compositePileSamplesRefs(
    Expression<bool> Function($$CompositePileSamplesTableFilterComposer f) f,
  ) {
    final $$CompositePileSamplesTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.compositePileSamples,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$CompositePileSamplesTableFilterComposer(
            $db: $db,
            $table: $db.compositePileSamples,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return f(composer);
  }

  Expression<bool> transportEventsRefs(
    Expression<bool> Function($$TransportEventsTableFilterComposer f) f,
  ) {
    final $$TransportEventsTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.transportEvents,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$TransportEventsTableFilterComposer(
            $db: $db,
            $table: $db.transportEvents,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return f(composer);
  }
}

class $$SystemMetadataTableOrderingComposer
    extends Composer<_$AppDatabase, $SystemMetadataTable> {
  $$SystemMetadataTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get batchUuid => $composableBuilder(
    column: $table.batchUuid,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get artisanId => $composableBuilder(
    column: $table.artisanId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get deviceHardwareMac => $composableBuilder(
    column: $table.deviceHardwareMac,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get appBuildVersion => $composableBuilder(
    column: $table.appBuildVersion,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get syncStatus => $composableBuilder(
    column: $table.syncStatus,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$SystemMetadataTableAnnotationComposer
    extends Composer<_$AppDatabase, $SystemMetadataTable> {
  $$SystemMetadataTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get batchUuid =>
      $composableBuilder(column: $table.batchUuid, builder: (column) => column);

  GeneratedColumn<String> get artisanId =>
      $composableBuilder(column: $table.artisanId, builder: (column) => column);

  GeneratedColumn<String> get deviceHardwareMac => $composableBuilder(
    column: $table.deviceHardwareMac,
    builder: (column) => column,
  );

  GeneratedColumn<String> get appBuildVersion => $composableBuilder(
    column: $table.appBuildVersion,
    builder: (column) => column,
  );

  GeneratedColumn<String> get syncStatus => $composableBuilder(
    column: $table.syncStatus,
    builder: (column) => column,
  );

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  Expression<T> biomassSourcingRefs<T extends Object>(
    Expression<T> Function($$BiomassSourcingTableAnnotationComposer a) f,
  ) {
    final $$BiomassSourcingTableAnnotationComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.biomassSourcing,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$BiomassSourcingTableAnnotationComposer(
            $db: $db,
            $table: $db.biomassSourcing,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return f(composer);
  }

  Expression<T> pyrolysisTelemetryRefs<T extends Object>(
    Expression<T> Function($$PyrolysisTelemetryTableAnnotationComposer a) f,
  ) {
    final $$PyrolysisTelemetryTableAnnotationComposer composer =
        $composerBuilder(
          composer: this,
          getCurrentColumn: (t) => t.batchUuid,
          referencedTable: $db.pyrolysisTelemetry,
          getReferencedColumn: (t) => t.batchUuid,
          builder:
              (
                joinBuilder, {
                $addJoinBuilderToRootComposer,
                $removeJoinBuilderFromRootComposer,
              }) => $$PyrolysisTelemetryTableAnnotationComposer(
                $db: $db,
                $table: $db.pyrolysisTelemetry,
                $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
                joinBuilder: joinBuilder,
                $removeJoinBuilderFromRootComposer:
                    $removeJoinBuilderFromRootComposer,
              ),
        );
    return f(composer);
  }

  Expression<T> yieldMetricsRefs<T extends Object>(
    Expression<T> Function($$YieldMetricsTableAnnotationComposer a) f,
  ) {
    final $$YieldMetricsTableAnnotationComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.yieldMetrics,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$YieldMetricsTableAnnotationComposer(
            $db: $db,
            $table: $db.yieldMetrics,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return f(composer);
  }

  Expression<T> endUseApplicationRefs<T extends Object>(
    Expression<T> Function($$EndUseApplicationTableAnnotationComposer a) f,
  ) {
    final $$EndUseApplicationTableAnnotationComposer composer =
        $composerBuilder(
          composer: this,
          getCurrentColumn: (t) => t.batchUuid,
          referencedTable: $db.endUseApplication,
          getReferencedColumn: (t) => t.batchUuid,
          builder:
              (
                joinBuilder, {
                $addJoinBuilderToRootComposer,
                $removeJoinBuilderFromRootComposer,
              }) => $$EndUseApplicationTableAnnotationComposer(
                $db: $db,
                $table: $db.endUseApplication,
                $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
                joinBuilder: joinBuilder,
                $removeJoinBuilderFromRootComposer:
                    $removeJoinBuilderFromRootComposer,
              ),
        );
    return f(composer);
  }

  Expression<T> mediaCapturesRefs<T extends Object>(
    Expression<T> Function($$MediaCapturesTableAnnotationComposer a) f,
  ) {
    final $$MediaCapturesTableAnnotationComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.mediaCaptures,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$MediaCapturesTableAnnotationComposer(
            $db: $db,
            $table: $db.mediaCaptures,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return f(composer);
  }

  Expression<T> moistureReadingsRefs<T extends Object>(
    Expression<T> Function($$MoistureReadingsTableAnnotationComposer a) f,
  ) {
    final $$MoistureReadingsTableAnnotationComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.moistureReadings,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$MoistureReadingsTableAnnotationComposer(
            $db: $db,
            $table: $db.moistureReadings,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return f(composer);
  }

  Expression<T> compositePileSamplesRefs<T extends Object>(
    Expression<T> Function($$CompositePileSamplesTableAnnotationComposer a) f,
  ) {
    final $$CompositePileSamplesTableAnnotationComposer composer =
        $composerBuilder(
          composer: this,
          getCurrentColumn: (t) => t.batchUuid,
          referencedTable: $db.compositePileSamples,
          getReferencedColumn: (t) => t.batchUuid,
          builder:
              (
                joinBuilder, {
                $addJoinBuilderToRootComposer,
                $removeJoinBuilderFromRootComposer,
              }) => $$CompositePileSamplesTableAnnotationComposer(
                $db: $db,
                $table: $db.compositePileSamples,
                $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
                joinBuilder: joinBuilder,
                $removeJoinBuilderFromRootComposer:
                    $removeJoinBuilderFromRootComposer,
              ),
        );
    return f(composer);
  }

  Expression<T> transportEventsRefs<T extends Object>(
    Expression<T> Function($$TransportEventsTableAnnotationComposer a) f,
  ) {
    final $$TransportEventsTableAnnotationComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.transportEvents,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$TransportEventsTableAnnotationComposer(
            $db: $db,
            $table: $db.transportEvents,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return f(composer);
  }
}

class $$SystemMetadataTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $SystemMetadataTable,
          SystemMetadataData,
          $$SystemMetadataTableFilterComposer,
          $$SystemMetadataTableOrderingComposer,
          $$SystemMetadataTableAnnotationComposer,
          $$SystemMetadataTableCreateCompanionBuilder,
          $$SystemMetadataTableUpdateCompanionBuilder,
          (SystemMetadataData, $$SystemMetadataTableReferences),
          SystemMetadataData,
          PrefetchHooks Function({
            bool biomassSourcingRefs,
            bool pyrolysisTelemetryRefs,
            bool yieldMetricsRefs,
            bool endUseApplicationRefs,
            bool mediaCapturesRefs,
            bool moistureReadingsRefs,
            bool compositePileSamplesRefs,
            bool transportEventsRefs,
          })
        > {
  $$SystemMetadataTableTableManager(
    _$AppDatabase db,
    $SystemMetadataTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$SystemMetadataTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$SystemMetadataTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$SystemMetadataTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> batchUuid = const Value.absent(),
                Value<String> artisanId = const Value.absent(),
                Value<String> deviceHardwareMac = const Value.absent(),
                Value<String> appBuildVersion = const Value.absent(),
                Value<String> syncStatus = const Value.absent(),
                Value<String> createdAt = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => SystemMetadataCompanion(
                batchUuid: batchUuid,
                artisanId: artisanId,
                deviceHardwareMac: deviceHardwareMac,
                appBuildVersion: appBuildVersion,
                syncStatus: syncStatus,
                createdAt: createdAt,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String batchUuid,
                required String artisanId,
                required String deviceHardwareMac,
                required String appBuildVersion,
                Value<String> syncStatus = const Value.absent(),
                required String createdAt,
                Value<int> rowid = const Value.absent(),
              }) => SystemMetadataCompanion.insert(
                batchUuid: batchUuid,
                artisanId: artisanId,
                deviceHardwareMac: deviceHardwareMac,
                appBuildVersion: appBuildVersion,
                syncStatus: syncStatus,
                createdAt: createdAt,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable(table),
                  $$SystemMetadataTableReferences(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback:
              ({
                biomassSourcingRefs = false,
                pyrolysisTelemetryRefs = false,
                yieldMetricsRefs = false,
                endUseApplicationRefs = false,
                mediaCapturesRefs = false,
                moistureReadingsRefs = false,
                compositePileSamplesRefs = false,
                transportEventsRefs = false,
              }) {
                return PrefetchHooks(
                  db: db,
                  explicitlyWatchedTables: [
                    if (biomassSourcingRefs) db.biomassSourcing,
                    if (pyrolysisTelemetryRefs) db.pyrolysisTelemetry,
                    if (yieldMetricsRefs) db.yieldMetrics,
                    if (endUseApplicationRefs) db.endUseApplication,
                    if (mediaCapturesRefs) db.mediaCaptures,
                    if (moistureReadingsRefs) db.moistureReadings,
                    if (compositePileSamplesRefs) db.compositePileSamples,
                    if (transportEventsRefs) db.transportEvents,
                  ],
                  addJoins: null,
                  getPrefetchedDataCallback: (items) async {
                    return [
                      if (biomassSourcingRefs)
                        await $_getPrefetchedData<
                          SystemMetadataData,
                          $SystemMetadataTable,
                          BiomassSourcingData
                        >(
                          currentTable: table,
                          referencedTable: $$SystemMetadataTableReferences
                              ._biomassSourcingRefsTable(db),
                          managerFromTypedResult: (p0) =>
                              $$SystemMetadataTableReferences(
                                db,
                                table,
                                p0,
                              ).biomassSourcingRefs,
                          referencedItemsForCurrentItem:
                              (item, referencedItems) => referencedItems.where(
                                (e) => e.batchUuid == item.batchUuid,
                              ),
                          typedResults: items,
                        ),
                      if (pyrolysisTelemetryRefs)
                        await $_getPrefetchedData<
                          SystemMetadataData,
                          $SystemMetadataTable,
                          PyrolysisTelemetryData
                        >(
                          currentTable: table,
                          referencedTable: $$SystemMetadataTableReferences
                              ._pyrolysisTelemetryRefsTable(db),
                          managerFromTypedResult: (p0) =>
                              $$SystemMetadataTableReferences(
                                db,
                                table,
                                p0,
                              ).pyrolysisTelemetryRefs,
                          referencedItemsForCurrentItem:
                              (item, referencedItems) => referencedItems.where(
                                (e) => e.batchUuid == item.batchUuid,
                              ),
                          typedResults: items,
                        ),
                      if (yieldMetricsRefs)
                        await $_getPrefetchedData<
                          SystemMetadataData,
                          $SystemMetadataTable,
                          YieldMetric
                        >(
                          currentTable: table,
                          referencedTable: $$SystemMetadataTableReferences
                              ._yieldMetricsRefsTable(db),
                          managerFromTypedResult: (p0) =>
                              $$SystemMetadataTableReferences(
                                db,
                                table,
                                p0,
                              ).yieldMetricsRefs,
                          referencedItemsForCurrentItem:
                              (item, referencedItems) => referencedItems.where(
                                (e) => e.batchUuid == item.batchUuid,
                              ),
                          typedResults: items,
                        ),
                      if (endUseApplicationRefs)
                        await $_getPrefetchedData<
                          SystemMetadataData,
                          $SystemMetadataTable,
                          EndUseApplicationData
                        >(
                          currentTable: table,
                          referencedTable: $$SystemMetadataTableReferences
                              ._endUseApplicationRefsTable(db),
                          managerFromTypedResult: (p0) =>
                              $$SystemMetadataTableReferences(
                                db,
                                table,
                                p0,
                              ).endUseApplicationRefs,
                          referencedItemsForCurrentItem:
                              (item, referencedItems) => referencedItems.where(
                                (e) => e.batchUuid == item.batchUuid,
                              ),
                          typedResults: items,
                        ),
                      if (mediaCapturesRefs)
                        await $_getPrefetchedData<
                          SystemMetadataData,
                          $SystemMetadataTable,
                          MediaCapture
                        >(
                          currentTable: table,
                          referencedTable: $$SystemMetadataTableReferences
                              ._mediaCapturesRefsTable(db),
                          managerFromTypedResult: (p0) =>
                              $$SystemMetadataTableReferences(
                                db,
                                table,
                                p0,
                              ).mediaCapturesRefs,
                          referencedItemsForCurrentItem:
                              (item, referencedItems) => referencedItems.where(
                                (e) => e.batchUuid == item.batchUuid,
                              ),
                          typedResults: items,
                        ),
                      if (moistureReadingsRefs)
                        await $_getPrefetchedData<
                          SystemMetadataData,
                          $SystemMetadataTable,
                          MoistureReading
                        >(
                          currentTable: table,
                          referencedTable: $$SystemMetadataTableReferences
                              ._moistureReadingsRefsTable(db),
                          managerFromTypedResult: (p0) =>
                              $$SystemMetadataTableReferences(
                                db,
                                table,
                                p0,
                              ).moistureReadingsRefs,
                          referencedItemsForCurrentItem:
                              (item, referencedItems) => referencedItems.where(
                                (e) => e.batchUuid == item.batchUuid,
                              ),
                          typedResults: items,
                        ),
                      if (compositePileSamplesRefs)
                        await $_getPrefetchedData<
                          SystemMetadataData,
                          $SystemMetadataTable,
                          CompositePileSample
                        >(
                          currentTable: table,
                          referencedTable: $$SystemMetadataTableReferences
                              ._compositePileSamplesRefsTable(db),
                          managerFromTypedResult: (p0) =>
                              $$SystemMetadataTableReferences(
                                db,
                                table,
                                p0,
                              ).compositePileSamplesRefs,
                          referencedItemsForCurrentItem:
                              (item, referencedItems) => referencedItems.where(
                                (e) => e.batchUuid == item.batchUuid,
                              ),
                          typedResults: items,
                        ),
                      if (transportEventsRefs)
                        await $_getPrefetchedData<
                          SystemMetadataData,
                          $SystemMetadataTable,
                          TransportEvent
                        >(
                          currentTable: table,
                          referencedTable: $$SystemMetadataTableReferences
                              ._transportEventsRefsTable(db),
                          managerFromTypedResult: (p0) =>
                              $$SystemMetadataTableReferences(
                                db,
                                table,
                                p0,
                              ).transportEventsRefs,
                          referencedItemsForCurrentItem:
                              (item, referencedItems) => referencedItems.where(
                                (e) => e.batchUuid == item.batchUuid,
                              ),
                          typedResults: items,
                        ),
                    ];
                  },
                );
              },
        ),
      );
}

typedef $$SystemMetadataTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $SystemMetadataTable,
      SystemMetadataData,
      $$SystemMetadataTableFilterComposer,
      $$SystemMetadataTableOrderingComposer,
      $$SystemMetadataTableAnnotationComposer,
      $$SystemMetadataTableCreateCompanionBuilder,
      $$SystemMetadataTableUpdateCompanionBuilder,
      (SystemMetadataData, $$SystemMetadataTableReferences),
      SystemMetadataData,
      PrefetchHooks Function({
        bool biomassSourcingRefs,
        bool pyrolysisTelemetryRefs,
        bool yieldMetricsRefs,
        bool endUseApplicationRefs,
        bool mediaCapturesRefs,
        bool moistureReadingsRefs,
        bool compositePileSamplesRefs,
        bool transportEventsRefs,
      })
    >;
typedef $$BiomassSourcingTableCreateCompanionBuilder =
    BiomassSourcingCompanion Function({
      required String sourcingUuid,
      required String batchUuid,
      required String feedstockSpecies,
      required String harvestTimestamp,
      required double moisturePercent,
      required bool moistureCompliant,
      Value<String?> photoPath,
      Value<String?> sha256Hash,
      Value<double?> latitude,
      Value<double?> longitude,
      Value<bool> mockLocationEnabled,
      Value<int?> harvestUptimeSeconds,
      Value<double?> azimuth,
      Value<double?> pitch,
      Value<double?> roll,
      Value<double?> biomassInputKg,
      Value<String?> biomassMeasurementMethod,
      Value<String?> projectId,
      Value<String?> scaleId,
      Value<int> rowid,
    });
typedef $$BiomassSourcingTableUpdateCompanionBuilder =
    BiomassSourcingCompanion Function({
      Value<String> sourcingUuid,
      Value<String> batchUuid,
      Value<String> feedstockSpecies,
      Value<String> harvestTimestamp,
      Value<double> moisturePercent,
      Value<bool> moistureCompliant,
      Value<String?> photoPath,
      Value<String?> sha256Hash,
      Value<double?> latitude,
      Value<double?> longitude,
      Value<bool> mockLocationEnabled,
      Value<int?> harvestUptimeSeconds,
      Value<double?> azimuth,
      Value<double?> pitch,
      Value<double?> roll,
      Value<double?> biomassInputKg,
      Value<String?> biomassMeasurementMethod,
      Value<String?> projectId,
      Value<String?> scaleId,
      Value<int> rowid,
    });

final class $$BiomassSourcingTableReferences
    extends
        BaseReferences<
          _$AppDatabase,
          $BiomassSourcingTable,
          BiomassSourcingData
        > {
  $$BiomassSourcingTableReferences(
    super.$_db,
    super.$_table,
    super.$_typedResult,
  );

  static $SystemMetadataTable _batchUuidTable(_$AppDatabase db) =>
      db.systemMetadata.createAlias(
        $_aliasNameGenerator(
          db.biomassSourcing.batchUuid,
          db.systemMetadata.batchUuid,
        ),
      );

  $$SystemMetadataTableProcessedTableManager get batchUuid {
    final $_column = $_itemColumn<String>('batch_uuid')!;

    final manager = $$SystemMetadataTableTableManager(
      $_db,
      $_db.systemMetadata,
    ).filter((f) => f.batchUuid.sqlEquals($_column));
    final item = $_typedResult.readTableOrNull(_batchUuidTable($_db));
    if (item == null) return manager;
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: [item]),
    );
  }
}

class $$BiomassSourcingTableFilterComposer
    extends Composer<_$AppDatabase, $BiomassSourcingTable> {
  $$BiomassSourcingTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get sourcingUuid => $composableBuilder(
    column: $table.sourcingUuid,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get feedstockSpecies => $composableBuilder(
    column: $table.feedstockSpecies,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get harvestTimestamp => $composableBuilder(
    column: $table.harvestTimestamp,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get moisturePercent => $composableBuilder(
    column: $table.moisturePercent,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<bool> get moistureCompliant => $composableBuilder(
    column: $table.moistureCompliant,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get photoPath => $composableBuilder(
    column: $table.photoPath,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sha256Hash => $composableBuilder(
    column: $table.sha256Hash,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get latitude => $composableBuilder(
    column: $table.latitude,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get longitude => $composableBuilder(
    column: $table.longitude,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<bool> get mockLocationEnabled => $composableBuilder(
    column: $table.mockLocationEnabled,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get harvestUptimeSeconds => $composableBuilder(
    column: $table.harvestUptimeSeconds,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get azimuth => $composableBuilder(
    column: $table.azimuth,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get pitch => $composableBuilder(
    column: $table.pitch,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get roll => $composableBuilder(
    column: $table.roll,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get biomassInputKg => $composableBuilder(
    column: $table.biomassInputKg,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get biomassMeasurementMethod => $composableBuilder(
    column: $table.biomassMeasurementMethod,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get projectId => $composableBuilder(
    column: $table.projectId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get scaleId => $composableBuilder(
    column: $table.scaleId,
    builder: (column) => ColumnFilters(column),
  );

  $$SystemMetadataTableFilterComposer get batchUuid {
    final $$SystemMetadataTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableFilterComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$BiomassSourcingTableOrderingComposer
    extends Composer<_$AppDatabase, $BiomassSourcingTable> {
  $$BiomassSourcingTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get sourcingUuid => $composableBuilder(
    column: $table.sourcingUuid,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get feedstockSpecies => $composableBuilder(
    column: $table.feedstockSpecies,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get harvestTimestamp => $composableBuilder(
    column: $table.harvestTimestamp,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get moisturePercent => $composableBuilder(
    column: $table.moisturePercent,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<bool> get moistureCompliant => $composableBuilder(
    column: $table.moistureCompliant,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get photoPath => $composableBuilder(
    column: $table.photoPath,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sha256Hash => $composableBuilder(
    column: $table.sha256Hash,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get latitude => $composableBuilder(
    column: $table.latitude,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get longitude => $composableBuilder(
    column: $table.longitude,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<bool> get mockLocationEnabled => $composableBuilder(
    column: $table.mockLocationEnabled,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get harvestUptimeSeconds => $composableBuilder(
    column: $table.harvestUptimeSeconds,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get azimuth => $composableBuilder(
    column: $table.azimuth,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get pitch => $composableBuilder(
    column: $table.pitch,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get roll => $composableBuilder(
    column: $table.roll,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get biomassInputKg => $composableBuilder(
    column: $table.biomassInputKg,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get biomassMeasurementMethod => $composableBuilder(
    column: $table.biomassMeasurementMethod,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get projectId => $composableBuilder(
    column: $table.projectId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get scaleId => $composableBuilder(
    column: $table.scaleId,
    builder: (column) => ColumnOrderings(column),
  );

  $$SystemMetadataTableOrderingComposer get batchUuid {
    final $$SystemMetadataTableOrderingComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableOrderingComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$BiomassSourcingTableAnnotationComposer
    extends Composer<_$AppDatabase, $BiomassSourcingTable> {
  $$BiomassSourcingTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get sourcingUuid => $composableBuilder(
    column: $table.sourcingUuid,
    builder: (column) => column,
  );

  GeneratedColumn<String> get feedstockSpecies => $composableBuilder(
    column: $table.feedstockSpecies,
    builder: (column) => column,
  );

  GeneratedColumn<String> get harvestTimestamp => $composableBuilder(
    column: $table.harvestTimestamp,
    builder: (column) => column,
  );

  GeneratedColumn<double> get moisturePercent => $composableBuilder(
    column: $table.moisturePercent,
    builder: (column) => column,
  );

  GeneratedColumn<bool> get moistureCompliant => $composableBuilder(
    column: $table.moistureCompliant,
    builder: (column) => column,
  );

  GeneratedColumn<String> get photoPath =>
      $composableBuilder(column: $table.photoPath, builder: (column) => column);

  GeneratedColumn<String> get sha256Hash => $composableBuilder(
    column: $table.sha256Hash,
    builder: (column) => column,
  );

  GeneratedColumn<double> get latitude =>
      $composableBuilder(column: $table.latitude, builder: (column) => column);

  GeneratedColumn<double> get longitude =>
      $composableBuilder(column: $table.longitude, builder: (column) => column);

  GeneratedColumn<bool> get mockLocationEnabled => $composableBuilder(
    column: $table.mockLocationEnabled,
    builder: (column) => column,
  );

  GeneratedColumn<int> get harvestUptimeSeconds => $composableBuilder(
    column: $table.harvestUptimeSeconds,
    builder: (column) => column,
  );

  GeneratedColumn<double> get azimuth =>
      $composableBuilder(column: $table.azimuth, builder: (column) => column);

  GeneratedColumn<double> get pitch =>
      $composableBuilder(column: $table.pitch, builder: (column) => column);

  GeneratedColumn<double> get roll =>
      $composableBuilder(column: $table.roll, builder: (column) => column);

  GeneratedColumn<double> get biomassInputKg => $composableBuilder(
    column: $table.biomassInputKg,
    builder: (column) => column,
  );

  GeneratedColumn<String> get biomassMeasurementMethod => $composableBuilder(
    column: $table.biomassMeasurementMethod,
    builder: (column) => column,
  );

  GeneratedColumn<String> get projectId =>
      $composableBuilder(column: $table.projectId, builder: (column) => column);

  GeneratedColumn<String> get scaleId =>
      $composableBuilder(column: $table.scaleId, builder: (column) => column);

  $$SystemMetadataTableAnnotationComposer get batchUuid {
    final $$SystemMetadataTableAnnotationComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableAnnotationComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$BiomassSourcingTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $BiomassSourcingTable,
          BiomassSourcingData,
          $$BiomassSourcingTableFilterComposer,
          $$BiomassSourcingTableOrderingComposer,
          $$BiomassSourcingTableAnnotationComposer,
          $$BiomassSourcingTableCreateCompanionBuilder,
          $$BiomassSourcingTableUpdateCompanionBuilder,
          (BiomassSourcingData, $$BiomassSourcingTableReferences),
          BiomassSourcingData,
          PrefetchHooks Function({bool batchUuid})
        > {
  $$BiomassSourcingTableTableManager(
    _$AppDatabase db,
    $BiomassSourcingTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$BiomassSourcingTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$BiomassSourcingTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$BiomassSourcingTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> sourcingUuid = const Value.absent(),
                Value<String> batchUuid = const Value.absent(),
                Value<String> feedstockSpecies = const Value.absent(),
                Value<String> harvestTimestamp = const Value.absent(),
                Value<double> moisturePercent = const Value.absent(),
                Value<bool> moistureCompliant = const Value.absent(),
                Value<String?> photoPath = const Value.absent(),
                Value<String?> sha256Hash = const Value.absent(),
                Value<double?> latitude = const Value.absent(),
                Value<double?> longitude = const Value.absent(),
                Value<bool> mockLocationEnabled = const Value.absent(),
                Value<int?> harvestUptimeSeconds = const Value.absent(),
                Value<double?> azimuth = const Value.absent(),
                Value<double?> pitch = const Value.absent(),
                Value<double?> roll = const Value.absent(),
                Value<double?> biomassInputKg = const Value.absent(),
                Value<String?> biomassMeasurementMethod = const Value.absent(),
                Value<String?> projectId = const Value.absent(),
                Value<String?> scaleId = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => BiomassSourcingCompanion(
                sourcingUuid: sourcingUuid,
                batchUuid: batchUuid,
                feedstockSpecies: feedstockSpecies,
                harvestTimestamp: harvestTimestamp,
                moisturePercent: moisturePercent,
                moistureCompliant: moistureCompliant,
                photoPath: photoPath,
                sha256Hash: sha256Hash,
                latitude: latitude,
                longitude: longitude,
                mockLocationEnabled: mockLocationEnabled,
                harvestUptimeSeconds: harvestUptimeSeconds,
                azimuth: azimuth,
                pitch: pitch,
                roll: roll,
                biomassInputKg: biomassInputKg,
                biomassMeasurementMethod: biomassMeasurementMethod,
                projectId: projectId,
                scaleId: scaleId,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String sourcingUuid,
                required String batchUuid,
                required String feedstockSpecies,
                required String harvestTimestamp,
                required double moisturePercent,
                required bool moistureCompliant,
                Value<String?> photoPath = const Value.absent(),
                Value<String?> sha256Hash = const Value.absent(),
                Value<double?> latitude = const Value.absent(),
                Value<double?> longitude = const Value.absent(),
                Value<bool> mockLocationEnabled = const Value.absent(),
                Value<int?> harvestUptimeSeconds = const Value.absent(),
                Value<double?> azimuth = const Value.absent(),
                Value<double?> pitch = const Value.absent(),
                Value<double?> roll = const Value.absent(),
                Value<double?> biomassInputKg = const Value.absent(),
                Value<String?> biomassMeasurementMethod = const Value.absent(),
                Value<String?> projectId = const Value.absent(),
                Value<String?> scaleId = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => BiomassSourcingCompanion.insert(
                sourcingUuid: sourcingUuid,
                batchUuid: batchUuid,
                feedstockSpecies: feedstockSpecies,
                harvestTimestamp: harvestTimestamp,
                moisturePercent: moisturePercent,
                moistureCompliant: moistureCompliant,
                photoPath: photoPath,
                sha256Hash: sha256Hash,
                latitude: latitude,
                longitude: longitude,
                mockLocationEnabled: mockLocationEnabled,
                harvestUptimeSeconds: harvestUptimeSeconds,
                azimuth: azimuth,
                pitch: pitch,
                roll: roll,
                biomassInputKg: biomassInputKg,
                biomassMeasurementMethod: biomassMeasurementMethod,
                projectId: projectId,
                scaleId: scaleId,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable(table),
                  $$BiomassSourcingTableReferences(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: ({batchUuid = false}) {
            return PrefetchHooks(
              db: db,
              explicitlyWatchedTables: [],
              addJoins:
                  <
                    T extends TableManagerState<
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic
                    >
                  >(state) {
                    if (batchUuid) {
                      state =
                          state.withJoin(
                                currentTable: table,
                                currentColumn: table.batchUuid,
                                referencedTable:
                                    $$BiomassSourcingTableReferences
                                        ._batchUuidTable(db),
                                referencedColumn:
                                    $$BiomassSourcingTableReferences
                                        ._batchUuidTable(db)
                                        .batchUuid,
                              )
                              as T;
                    }

                    return state;
                  },
              getPrefetchedDataCallback: (items) async {
                return [];
              },
            );
          },
        ),
      );
}

typedef $$BiomassSourcingTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $BiomassSourcingTable,
      BiomassSourcingData,
      $$BiomassSourcingTableFilterComposer,
      $$BiomassSourcingTableOrderingComposer,
      $$BiomassSourcingTableAnnotationComposer,
      $$BiomassSourcingTableCreateCompanionBuilder,
      $$BiomassSourcingTableUpdateCompanionBuilder,
      (BiomassSourcingData, $$BiomassSourcingTableReferences),
      BiomassSourcingData,
      PrefetchHooks Function({bool batchUuid})
    >;
typedef $$PyrolysisTelemetryTableCreateCompanionBuilder =
    PyrolysisTelemetryCompanion Function({
      required String telemetryUuid,
      required String batchUuid,
      required double kilnGrossCapacity,
      required String burnStartTimestamp,
      Value<String?> burnEndTimestamp,
      required double minTemp,
      required double maxTemp,
      Value<String> temperatureReadingsJson,
      Value<String> smokeEvidenceJson,
      Value<double?> azimuth,
      Value<double?> pitch,
      Value<double?> roll,
      Value<String> hwAttestationJson,
      Value<String?> kilnType,
      Value<String?> kilnId,
      Value<double?> flameHeightM,
      Value<String?> ignitionEnergyType,
      Value<double?> ignitionEnergyAmount,
      Value<int> rowid,
    });
typedef $$PyrolysisTelemetryTableUpdateCompanionBuilder =
    PyrolysisTelemetryCompanion Function({
      Value<String> telemetryUuid,
      Value<String> batchUuid,
      Value<double> kilnGrossCapacity,
      Value<String> burnStartTimestamp,
      Value<String?> burnEndTimestamp,
      Value<double> minTemp,
      Value<double> maxTemp,
      Value<String> temperatureReadingsJson,
      Value<String> smokeEvidenceJson,
      Value<double?> azimuth,
      Value<double?> pitch,
      Value<double?> roll,
      Value<String> hwAttestationJson,
      Value<String?> kilnType,
      Value<String?> kilnId,
      Value<double?> flameHeightM,
      Value<String?> ignitionEnergyType,
      Value<double?> ignitionEnergyAmount,
      Value<int> rowid,
    });

final class $$PyrolysisTelemetryTableReferences
    extends
        BaseReferences<
          _$AppDatabase,
          $PyrolysisTelemetryTable,
          PyrolysisTelemetryData
        > {
  $$PyrolysisTelemetryTableReferences(
    super.$_db,
    super.$_table,
    super.$_typedResult,
  );

  static $SystemMetadataTable _batchUuidTable(_$AppDatabase db) =>
      db.systemMetadata.createAlias(
        $_aliasNameGenerator(
          db.pyrolysisTelemetry.batchUuid,
          db.systemMetadata.batchUuid,
        ),
      );

  $$SystemMetadataTableProcessedTableManager get batchUuid {
    final $_column = $_itemColumn<String>('batch_uuid')!;

    final manager = $$SystemMetadataTableTableManager(
      $_db,
      $_db.systemMetadata,
    ).filter((f) => f.batchUuid.sqlEquals($_column));
    final item = $_typedResult.readTableOrNull(_batchUuidTable($_db));
    if (item == null) return manager;
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: [item]),
    );
  }
}

class $$PyrolysisTelemetryTableFilterComposer
    extends Composer<_$AppDatabase, $PyrolysisTelemetryTable> {
  $$PyrolysisTelemetryTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get telemetryUuid => $composableBuilder(
    column: $table.telemetryUuid,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get kilnGrossCapacity => $composableBuilder(
    column: $table.kilnGrossCapacity,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get burnStartTimestamp => $composableBuilder(
    column: $table.burnStartTimestamp,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get burnEndTimestamp => $composableBuilder(
    column: $table.burnEndTimestamp,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get minTemp => $composableBuilder(
    column: $table.minTemp,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get maxTemp => $composableBuilder(
    column: $table.maxTemp,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get temperatureReadingsJson => $composableBuilder(
    column: $table.temperatureReadingsJson,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get smokeEvidenceJson => $composableBuilder(
    column: $table.smokeEvidenceJson,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get azimuth => $composableBuilder(
    column: $table.azimuth,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get pitch => $composableBuilder(
    column: $table.pitch,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get roll => $composableBuilder(
    column: $table.roll,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get hwAttestationJson => $composableBuilder(
    column: $table.hwAttestationJson,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get kilnType => $composableBuilder(
    column: $table.kilnType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get kilnId => $composableBuilder(
    column: $table.kilnId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get flameHeightM => $composableBuilder(
    column: $table.flameHeightM,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get ignitionEnergyType => $composableBuilder(
    column: $table.ignitionEnergyType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get ignitionEnergyAmount => $composableBuilder(
    column: $table.ignitionEnergyAmount,
    builder: (column) => ColumnFilters(column),
  );

  $$SystemMetadataTableFilterComposer get batchUuid {
    final $$SystemMetadataTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableFilterComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$PyrolysisTelemetryTableOrderingComposer
    extends Composer<_$AppDatabase, $PyrolysisTelemetryTable> {
  $$PyrolysisTelemetryTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get telemetryUuid => $composableBuilder(
    column: $table.telemetryUuid,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get kilnGrossCapacity => $composableBuilder(
    column: $table.kilnGrossCapacity,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get burnStartTimestamp => $composableBuilder(
    column: $table.burnStartTimestamp,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get burnEndTimestamp => $composableBuilder(
    column: $table.burnEndTimestamp,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get minTemp => $composableBuilder(
    column: $table.minTemp,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get maxTemp => $composableBuilder(
    column: $table.maxTemp,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get temperatureReadingsJson => $composableBuilder(
    column: $table.temperatureReadingsJson,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get smokeEvidenceJson => $composableBuilder(
    column: $table.smokeEvidenceJson,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get azimuth => $composableBuilder(
    column: $table.azimuth,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get pitch => $composableBuilder(
    column: $table.pitch,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get roll => $composableBuilder(
    column: $table.roll,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get hwAttestationJson => $composableBuilder(
    column: $table.hwAttestationJson,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get kilnType => $composableBuilder(
    column: $table.kilnType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get kilnId => $composableBuilder(
    column: $table.kilnId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get flameHeightM => $composableBuilder(
    column: $table.flameHeightM,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get ignitionEnergyType => $composableBuilder(
    column: $table.ignitionEnergyType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get ignitionEnergyAmount => $composableBuilder(
    column: $table.ignitionEnergyAmount,
    builder: (column) => ColumnOrderings(column),
  );

  $$SystemMetadataTableOrderingComposer get batchUuid {
    final $$SystemMetadataTableOrderingComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableOrderingComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$PyrolysisTelemetryTableAnnotationComposer
    extends Composer<_$AppDatabase, $PyrolysisTelemetryTable> {
  $$PyrolysisTelemetryTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get telemetryUuid => $composableBuilder(
    column: $table.telemetryUuid,
    builder: (column) => column,
  );

  GeneratedColumn<double> get kilnGrossCapacity => $composableBuilder(
    column: $table.kilnGrossCapacity,
    builder: (column) => column,
  );

  GeneratedColumn<String> get burnStartTimestamp => $composableBuilder(
    column: $table.burnStartTimestamp,
    builder: (column) => column,
  );

  GeneratedColumn<String> get burnEndTimestamp => $composableBuilder(
    column: $table.burnEndTimestamp,
    builder: (column) => column,
  );

  GeneratedColumn<double> get minTemp =>
      $composableBuilder(column: $table.minTemp, builder: (column) => column);

  GeneratedColumn<double> get maxTemp =>
      $composableBuilder(column: $table.maxTemp, builder: (column) => column);

  GeneratedColumn<String> get temperatureReadingsJson => $composableBuilder(
    column: $table.temperatureReadingsJson,
    builder: (column) => column,
  );

  GeneratedColumn<String> get smokeEvidenceJson => $composableBuilder(
    column: $table.smokeEvidenceJson,
    builder: (column) => column,
  );

  GeneratedColumn<double> get azimuth =>
      $composableBuilder(column: $table.azimuth, builder: (column) => column);

  GeneratedColumn<double> get pitch =>
      $composableBuilder(column: $table.pitch, builder: (column) => column);

  GeneratedColumn<double> get roll =>
      $composableBuilder(column: $table.roll, builder: (column) => column);

  GeneratedColumn<String> get hwAttestationJson => $composableBuilder(
    column: $table.hwAttestationJson,
    builder: (column) => column,
  );

  GeneratedColumn<String> get kilnType =>
      $composableBuilder(column: $table.kilnType, builder: (column) => column);

  GeneratedColumn<String> get kilnId =>
      $composableBuilder(column: $table.kilnId, builder: (column) => column);

  GeneratedColumn<double> get flameHeightM => $composableBuilder(
    column: $table.flameHeightM,
    builder: (column) => column,
  );

  GeneratedColumn<String> get ignitionEnergyType => $composableBuilder(
    column: $table.ignitionEnergyType,
    builder: (column) => column,
  );

  GeneratedColumn<double> get ignitionEnergyAmount => $composableBuilder(
    column: $table.ignitionEnergyAmount,
    builder: (column) => column,
  );

  $$SystemMetadataTableAnnotationComposer get batchUuid {
    final $$SystemMetadataTableAnnotationComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableAnnotationComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$PyrolysisTelemetryTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $PyrolysisTelemetryTable,
          PyrolysisTelemetryData,
          $$PyrolysisTelemetryTableFilterComposer,
          $$PyrolysisTelemetryTableOrderingComposer,
          $$PyrolysisTelemetryTableAnnotationComposer,
          $$PyrolysisTelemetryTableCreateCompanionBuilder,
          $$PyrolysisTelemetryTableUpdateCompanionBuilder,
          (PyrolysisTelemetryData, $$PyrolysisTelemetryTableReferences),
          PyrolysisTelemetryData,
          PrefetchHooks Function({bool batchUuid})
        > {
  $$PyrolysisTelemetryTableTableManager(
    _$AppDatabase db,
    $PyrolysisTelemetryTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$PyrolysisTelemetryTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$PyrolysisTelemetryTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$PyrolysisTelemetryTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<String> telemetryUuid = const Value.absent(),
                Value<String> batchUuid = const Value.absent(),
                Value<double> kilnGrossCapacity = const Value.absent(),
                Value<String> burnStartTimestamp = const Value.absent(),
                Value<String?> burnEndTimestamp = const Value.absent(),
                Value<double> minTemp = const Value.absent(),
                Value<double> maxTemp = const Value.absent(),
                Value<String> temperatureReadingsJson = const Value.absent(),
                Value<String> smokeEvidenceJson = const Value.absent(),
                Value<double?> azimuth = const Value.absent(),
                Value<double?> pitch = const Value.absent(),
                Value<double?> roll = const Value.absent(),
                Value<String> hwAttestationJson = const Value.absent(),
                Value<String?> kilnType = const Value.absent(),
                Value<String?> kilnId = const Value.absent(),
                Value<double?> flameHeightM = const Value.absent(),
                Value<String?> ignitionEnergyType = const Value.absent(),
                Value<double?> ignitionEnergyAmount = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => PyrolysisTelemetryCompanion(
                telemetryUuid: telemetryUuid,
                batchUuid: batchUuid,
                kilnGrossCapacity: kilnGrossCapacity,
                burnStartTimestamp: burnStartTimestamp,
                burnEndTimestamp: burnEndTimestamp,
                minTemp: minTemp,
                maxTemp: maxTemp,
                temperatureReadingsJson: temperatureReadingsJson,
                smokeEvidenceJson: smokeEvidenceJson,
                azimuth: azimuth,
                pitch: pitch,
                roll: roll,
                hwAttestationJson: hwAttestationJson,
                kilnType: kilnType,
                kilnId: kilnId,
                flameHeightM: flameHeightM,
                ignitionEnergyType: ignitionEnergyType,
                ignitionEnergyAmount: ignitionEnergyAmount,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String telemetryUuid,
                required String batchUuid,
                required double kilnGrossCapacity,
                required String burnStartTimestamp,
                Value<String?> burnEndTimestamp = const Value.absent(),
                required double minTemp,
                required double maxTemp,
                Value<String> temperatureReadingsJson = const Value.absent(),
                Value<String> smokeEvidenceJson = const Value.absent(),
                Value<double?> azimuth = const Value.absent(),
                Value<double?> pitch = const Value.absent(),
                Value<double?> roll = const Value.absent(),
                Value<String> hwAttestationJson = const Value.absent(),
                Value<String?> kilnType = const Value.absent(),
                Value<String?> kilnId = const Value.absent(),
                Value<double?> flameHeightM = const Value.absent(),
                Value<String?> ignitionEnergyType = const Value.absent(),
                Value<double?> ignitionEnergyAmount = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => PyrolysisTelemetryCompanion.insert(
                telemetryUuid: telemetryUuid,
                batchUuid: batchUuid,
                kilnGrossCapacity: kilnGrossCapacity,
                burnStartTimestamp: burnStartTimestamp,
                burnEndTimestamp: burnEndTimestamp,
                minTemp: minTemp,
                maxTemp: maxTemp,
                temperatureReadingsJson: temperatureReadingsJson,
                smokeEvidenceJson: smokeEvidenceJson,
                azimuth: azimuth,
                pitch: pitch,
                roll: roll,
                hwAttestationJson: hwAttestationJson,
                kilnType: kilnType,
                kilnId: kilnId,
                flameHeightM: flameHeightM,
                ignitionEnergyType: ignitionEnergyType,
                ignitionEnergyAmount: ignitionEnergyAmount,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable(table),
                  $$PyrolysisTelemetryTableReferences(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: ({batchUuid = false}) {
            return PrefetchHooks(
              db: db,
              explicitlyWatchedTables: [],
              addJoins:
                  <
                    T extends TableManagerState<
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic
                    >
                  >(state) {
                    if (batchUuid) {
                      state =
                          state.withJoin(
                                currentTable: table,
                                currentColumn: table.batchUuid,
                                referencedTable:
                                    $$PyrolysisTelemetryTableReferences
                                        ._batchUuidTable(db),
                                referencedColumn:
                                    $$PyrolysisTelemetryTableReferences
                                        ._batchUuidTable(db)
                                        .batchUuid,
                              )
                              as T;
                    }

                    return state;
                  },
              getPrefetchedDataCallback: (items) async {
                return [];
              },
            );
          },
        ),
      );
}

typedef $$PyrolysisTelemetryTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $PyrolysisTelemetryTable,
      PyrolysisTelemetryData,
      $$PyrolysisTelemetryTableFilterComposer,
      $$PyrolysisTelemetryTableOrderingComposer,
      $$PyrolysisTelemetryTableAnnotationComposer,
      $$PyrolysisTelemetryTableCreateCompanionBuilder,
      $$PyrolysisTelemetryTableUpdateCompanionBuilder,
      (PyrolysisTelemetryData, $$PyrolysisTelemetryTableReferences),
      PyrolysisTelemetryData,
      PrefetchHooks Function({bool batchUuid})
    >;
typedef $$YieldMetricsTableCreateCompanionBuilder =
    YieldMetricsCompanion Function({
      required String yieldUuid,
      required String batchUuid,
      required String quenchMethodology,
      required double grossVolume,
      required double wetYieldWeightKg,
      Value<double?> dryYieldWeightKg,
      Value<int> rowid,
    });
typedef $$YieldMetricsTableUpdateCompanionBuilder =
    YieldMetricsCompanion Function({
      Value<String> yieldUuid,
      Value<String> batchUuid,
      Value<String> quenchMethodology,
      Value<double> grossVolume,
      Value<double> wetYieldWeightKg,
      Value<double?> dryYieldWeightKg,
      Value<int> rowid,
    });

final class $$YieldMetricsTableReferences
    extends BaseReferences<_$AppDatabase, $YieldMetricsTable, YieldMetric> {
  $$YieldMetricsTableReferences(super.$_db, super.$_table, super.$_typedResult);

  static $SystemMetadataTable _batchUuidTable(_$AppDatabase db) =>
      db.systemMetadata.createAlias(
        $_aliasNameGenerator(
          db.yieldMetrics.batchUuid,
          db.systemMetadata.batchUuid,
        ),
      );

  $$SystemMetadataTableProcessedTableManager get batchUuid {
    final $_column = $_itemColumn<String>('batch_uuid')!;

    final manager = $$SystemMetadataTableTableManager(
      $_db,
      $_db.systemMetadata,
    ).filter((f) => f.batchUuid.sqlEquals($_column));
    final item = $_typedResult.readTableOrNull(_batchUuidTable($_db));
    if (item == null) return manager;
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: [item]),
    );
  }
}

class $$YieldMetricsTableFilterComposer
    extends Composer<_$AppDatabase, $YieldMetricsTable> {
  $$YieldMetricsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get yieldUuid => $composableBuilder(
    column: $table.yieldUuid,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get quenchMethodology => $composableBuilder(
    column: $table.quenchMethodology,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get grossVolume => $composableBuilder(
    column: $table.grossVolume,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get wetYieldWeightKg => $composableBuilder(
    column: $table.wetYieldWeightKg,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get dryYieldWeightKg => $composableBuilder(
    column: $table.dryYieldWeightKg,
    builder: (column) => ColumnFilters(column),
  );

  $$SystemMetadataTableFilterComposer get batchUuid {
    final $$SystemMetadataTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableFilterComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$YieldMetricsTableOrderingComposer
    extends Composer<_$AppDatabase, $YieldMetricsTable> {
  $$YieldMetricsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get yieldUuid => $composableBuilder(
    column: $table.yieldUuid,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get quenchMethodology => $composableBuilder(
    column: $table.quenchMethodology,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get grossVolume => $composableBuilder(
    column: $table.grossVolume,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get wetYieldWeightKg => $composableBuilder(
    column: $table.wetYieldWeightKg,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get dryYieldWeightKg => $composableBuilder(
    column: $table.dryYieldWeightKg,
    builder: (column) => ColumnOrderings(column),
  );

  $$SystemMetadataTableOrderingComposer get batchUuid {
    final $$SystemMetadataTableOrderingComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableOrderingComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$YieldMetricsTableAnnotationComposer
    extends Composer<_$AppDatabase, $YieldMetricsTable> {
  $$YieldMetricsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get yieldUuid =>
      $composableBuilder(column: $table.yieldUuid, builder: (column) => column);

  GeneratedColumn<String> get quenchMethodology => $composableBuilder(
    column: $table.quenchMethodology,
    builder: (column) => column,
  );

  GeneratedColumn<double> get grossVolume => $composableBuilder(
    column: $table.grossVolume,
    builder: (column) => column,
  );

  GeneratedColumn<double> get wetYieldWeightKg => $composableBuilder(
    column: $table.wetYieldWeightKg,
    builder: (column) => column,
  );

  GeneratedColumn<double> get dryYieldWeightKg => $composableBuilder(
    column: $table.dryYieldWeightKg,
    builder: (column) => column,
  );

  $$SystemMetadataTableAnnotationComposer get batchUuid {
    final $$SystemMetadataTableAnnotationComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableAnnotationComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$YieldMetricsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $YieldMetricsTable,
          YieldMetric,
          $$YieldMetricsTableFilterComposer,
          $$YieldMetricsTableOrderingComposer,
          $$YieldMetricsTableAnnotationComposer,
          $$YieldMetricsTableCreateCompanionBuilder,
          $$YieldMetricsTableUpdateCompanionBuilder,
          (YieldMetric, $$YieldMetricsTableReferences),
          YieldMetric,
          PrefetchHooks Function({bool batchUuid})
        > {
  $$YieldMetricsTableTableManager(_$AppDatabase db, $YieldMetricsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$YieldMetricsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$YieldMetricsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$YieldMetricsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> yieldUuid = const Value.absent(),
                Value<String> batchUuid = const Value.absent(),
                Value<String> quenchMethodology = const Value.absent(),
                Value<double> grossVolume = const Value.absent(),
                Value<double> wetYieldWeightKg = const Value.absent(),
                Value<double?> dryYieldWeightKg = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => YieldMetricsCompanion(
                yieldUuid: yieldUuid,
                batchUuid: batchUuid,
                quenchMethodology: quenchMethodology,
                grossVolume: grossVolume,
                wetYieldWeightKg: wetYieldWeightKg,
                dryYieldWeightKg: dryYieldWeightKg,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String yieldUuid,
                required String batchUuid,
                required String quenchMethodology,
                required double grossVolume,
                required double wetYieldWeightKg,
                Value<double?> dryYieldWeightKg = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => YieldMetricsCompanion.insert(
                yieldUuid: yieldUuid,
                batchUuid: batchUuid,
                quenchMethodology: quenchMethodology,
                grossVolume: grossVolume,
                wetYieldWeightKg: wetYieldWeightKg,
                dryYieldWeightKg: dryYieldWeightKg,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable(table),
                  $$YieldMetricsTableReferences(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: ({batchUuid = false}) {
            return PrefetchHooks(
              db: db,
              explicitlyWatchedTables: [],
              addJoins:
                  <
                    T extends TableManagerState<
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic
                    >
                  >(state) {
                    if (batchUuid) {
                      state =
                          state.withJoin(
                                currentTable: table,
                                currentColumn: table.batchUuid,
                                referencedTable: $$YieldMetricsTableReferences
                                    ._batchUuidTable(db),
                                referencedColumn: $$YieldMetricsTableReferences
                                    ._batchUuidTable(db)
                                    .batchUuid,
                              )
                              as T;
                    }

                    return state;
                  },
              getPrefetchedDataCallback: (items) async {
                return [];
              },
            );
          },
        ),
      );
}

typedef $$YieldMetricsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $YieldMetricsTable,
      YieldMetric,
      $$YieldMetricsTableFilterComposer,
      $$YieldMetricsTableOrderingComposer,
      $$YieldMetricsTableAnnotationComposer,
      $$YieldMetricsTableCreateCompanionBuilder,
      $$YieldMetricsTableUpdateCompanionBuilder,
      (YieldMetric, $$YieldMetricsTableReferences),
      YieldMetric,
      PrefetchHooks Function({bool batchUuid})
    >;
typedef $$EndUseApplicationTableCreateCompanionBuilder =
    EndUseApplicationCompanion Function({
      required String applicationUuid,
      required String batchUuid,
      required String applicationMethodology,
      required double applicationRate,
      required double transportDistanceKm,
      Value<double?> latitude,
      Value<double?> longitude,
      Value<String?> farmerPhotoPath,
      Value<String?> farmerPhotoSha256,
      Value<String?> deliveryDate,
      Value<double?> deliveredAmountKg,
      Value<String?> buyerName,
      Value<String?> buyerContact,
      Value<int> rowid,
    });
typedef $$EndUseApplicationTableUpdateCompanionBuilder =
    EndUseApplicationCompanion Function({
      Value<String> applicationUuid,
      Value<String> batchUuid,
      Value<String> applicationMethodology,
      Value<double> applicationRate,
      Value<double> transportDistanceKm,
      Value<double?> latitude,
      Value<double?> longitude,
      Value<String?> farmerPhotoPath,
      Value<String?> farmerPhotoSha256,
      Value<String?> deliveryDate,
      Value<double?> deliveredAmountKg,
      Value<String?> buyerName,
      Value<String?> buyerContact,
      Value<int> rowid,
    });

final class $$EndUseApplicationTableReferences
    extends
        BaseReferences<
          _$AppDatabase,
          $EndUseApplicationTable,
          EndUseApplicationData
        > {
  $$EndUseApplicationTableReferences(
    super.$_db,
    super.$_table,
    super.$_typedResult,
  );

  static $SystemMetadataTable _batchUuidTable(_$AppDatabase db) =>
      db.systemMetadata.createAlias(
        $_aliasNameGenerator(
          db.endUseApplication.batchUuid,
          db.systemMetadata.batchUuid,
        ),
      );

  $$SystemMetadataTableProcessedTableManager get batchUuid {
    final $_column = $_itemColumn<String>('batch_uuid')!;

    final manager = $$SystemMetadataTableTableManager(
      $_db,
      $_db.systemMetadata,
    ).filter((f) => f.batchUuid.sqlEquals($_column));
    final item = $_typedResult.readTableOrNull(_batchUuidTable($_db));
    if (item == null) return manager;
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: [item]),
    );
  }
}

class $$EndUseApplicationTableFilterComposer
    extends Composer<_$AppDatabase, $EndUseApplicationTable> {
  $$EndUseApplicationTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get applicationUuid => $composableBuilder(
    column: $table.applicationUuid,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get applicationMethodology => $composableBuilder(
    column: $table.applicationMethodology,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get applicationRate => $composableBuilder(
    column: $table.applicationRate,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get transportDistanceKm => $composableBuilder(
    column: $table.transportDistanceKm,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get latitude => $composableBuilder(
    column: $table.latitude,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get longitude => $composableBuilder(
    column: $table.longitude,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get farmerPhotoPath => $composableBuilder(
    column: $table.farmerPhotoPath,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get farmerPhotoSha256 => $composableBuilder(
    column: $table.farmerPhotoSha256,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get deliveryDate => $composableBuilder(
    column: $table.deliveryDate,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get deliveredAmountKg => $composableBuilder(
    column: $table.deliveredAmountKg,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get buyerName => $composableBuilder(
    column: $table.buyerName,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get buyerContact => $composableBuilder(
    column: $table.buyerContact,
    builder: (column) => ColumnFilters(column),
  );

  $$SystemMetadataTableFilterComposer get batchUuid {
    final $$SystemMetadataTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableFilterComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$EndUseApplicationTableOrderingComposer
    extends Composer<_$AppDatabase, $EndUseApplicationTable> {
  $$EndUseApplicationTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get applicationUuid => $composableBuilder(
    column: $table.applicationUuid,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get applicationMethodology => $composableBuilder(
    column: $table.applicationMethodology,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get applicationRate => $composableBuilder(
    column: $table.applicationRate,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get transportDistanceKm => $composableBuilder(
    column: $table.transportDistanceKm,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get latitude => $composableBuilder(
    column: $table.latitude,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get longitude => $composableBuilder(
    column: $table.longitude,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get farmerPhotoPath => $composableBuilder(
    column: $table.farmerPhotoPath,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get farmerPhotoSha256 => $composableBuilder(
    column: $table.farmerPhotoSha256,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get deliveryDate => $composableBuilder(
    column: $table.deliveryDate,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get deliveredAmountKg => $composableBuilder(
    column: $table.deliveredAmountKg,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get buyerName => $composableBuilder(
    column: $table.buyerName,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get buyerContact => $composableBuilder(
    column: $table.buyerContact,
    builder: (column) => ColumnOrderings(column),
  );

  $$SystemMetadataTableOrderingComposer get batchUuid {
    final $$SystemMetadataTableOrderingComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableOrderingComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$EndUseApplicationTableAnnotationComposer
    extends Composer<_$AppDatabase, $EndUseApplicationTable> {
  $$EndUseApplicationTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get applicationUuid => $composableBuilder(
    column: $table.applicationUuid,
    builder: (column) => column,
  );

  GeneratedColumn<String> get applicationMethodology => $composableBuilder(
    column: $table.applicationMethodology,
    builder: (column) => column,
  );

  GeneratedColumn<double> get applicationRate => $composableBuilder(
    column: $table.applicationRate,
    builder: (column) => column,
  );

  GeneratedColumn<double> get transportDistanceKm => $composableBuilder(
    column: $table.transportDistanceKm,
    builder: (column) => column,
  );

  GeneratedColumn<double> get latitude =>
      $composableBuilder(column: $table.latitude, builder: (column) => column);

  GeneratedColumn<double> get longitude =>
      $composableBuilder(column: $table.longitude, builder: (column) => column);

  GeneratedColumn<String> get farmerPhotoPath => $composableBuilder(
    column: $table.farmerPhotoPath,
    builder: (column) => column,
  );

  GeneratedColumn<String> get farmerPhotoSha256 => $composableBuilder(
    column: $table.farmerPhotoSha256,
    builder: (column) => column,
  );

  GeneratedColumn<String> get deliveryDate => $composableBuilder(
    column: $table.deliveryDate,
    builder: (column) => column,
  );

  GeneratedColumn<double> get deliveredAmountKg => $composableBuilder(
    column: $table.deliveredAmountKg,
    builder: (column) => column,
  );

  GeneratedColumn<String> get buyerName =>
      $composableBuilder(column: $table.buyerName, builder: (column) => column);

  GeneratedColumn<String> get buyerContact => $composableBuilder(
    column: $table.buyerContact,
    builder: (column) => column,
  );

  $$SystemMetadataTableAnnotationComposer get batchUuid {
    final $$SystemMetadataTableAnnotationComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableAnnotationComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$EndUseApplicationTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $EndUseApplicationTable,
          EndUseApplicationData,
          $$EndUseApplicationTableFilterComposer,
          $$EndUseApplicationTableOrderingComposer,
          $$EndUseApplicationTableAnnotationComposer,
          $$EndUseApplicationTableCreateCompanionBuilder,
          $$EndUseApplicationTableUpdateCompanionBuilder,
          (EndUseApplicationData, $$EndUseApplicationTableReferences),
          EndUseApplicationData,
          PrefetchHooks Function({bool batchUuid})
        > {
  $$EndUseApplicationTableTableManager(
    _$AppDatabase db,
    $EndUseApplicationTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$EndUseApplicationTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$EndUseApplicationTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$EndUseApplicationTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<String> applicationUuid = const Value.absent(),
                Value<String> batchUuid = const Value.absent(),
                Value<String> applicationMethodology = const Value.absent(),
                Value<double> applicationRate = const Value.absent(),
                Value<double> transportDistanceKm = const Value.absent(),
                Value<double?> latitude = const Value.absent(),
                Value<double?> longitude = const Value.absent(),
                Value<String?> farmerPhotoPath = const Value.absent(),
                Value<String?> farmerPhotoSha256 = const Value.absent(),
                Value<String?> deliveryDate = const Value.absent(),
                Value<double?> deliveredAmountKg = const Value.absent(),
                Value<String?> buyerName = const Value.absent(),
                Value<String?> buyerContact = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => EndUseApplicationCompanion(
                applicationUuid: applicationUuid,
                batchUuid: batchUuid,
                applicationMethodology: applicationMethodology,
                applicationRate: applicationRate,
                transportDistanceKm: transportDistanceKm,
                latitude: latitude,
                longitude: longitude,
                farmerPhotoPath: farmerPhotoPath,
                farmerPhotoSha256: farmerPhotoSha256,
                deliveryDate: deliveryDate,
                deliveredAmountKg: deliveredAmountKg,
                buyerName: buyerName,
                buyerContact: buyerContact,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String applicationUuid,
                required String batchUuid,
                required String applicationMethodology,
                required double applicationRate,
                required double transportDistanceKm,
                Value<double?> latitude = const Value.absent(),
                Value<double?> longitude = const Value.absent(),
                Value<String?> farmerPhotoPath = const Value.absent(),
                Value<String?> farmerPhotoSha256 = const Value.absent(),
                Value<String?> deliveryDate = const Value.absent(),
                Value<double?> deliveredAmountKg = const Value.absent(),
                Value<String?> buyerName = const Value.absent(),
                Value<String?> buyerContact = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => EndUseApplicationCompanion.insert(
                applicationUuid: applicationUuid,
                batchUuid: batchUuid,
                applicationMethodology: applicationMethodology,
                applicationRate: applicationRate,
                transportDistanceKm: transportDistanceKm,
                latitude: latitude,
                longitude: longitude,
                farmerPhotoPath: farmerPhotoPath,
                farmerPhotoSha256: farmerPhotoSha256,
                deliveryDate: deliveryDate,
                deliveredAmountKg: deliveredAmountKg,
                buyerName: buyerName,
                buyerContact: buyerContact,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable(table),
                  $$EndUseApplicationTableReferences(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: ({batchUuid = false}) {
            return PrefetchHooks(
              db: db,
              explicitlyWatchedTables: [],
              addJoins:
                  <
                    T extends TableManagerState<
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic
                    >
                  >(state) {
                    if (batchUuid) {
                      state =
                          state.withJoin(
                                currentTable: table,
                                currentColumn: table.batchUuid,
                                referencedTable:
                                    $$EndUseApplicationTableReferences
                                        ._batchUuidTable(db),
                                referencedColumn:
                                    $$EndUseApplicationTableReferences
                                        ._batchUuidTable(db)
                                        .batchUuid,
                              )
                              as T;
                    }

                    return state;
                  },
              getPrefetchedDataCallback: (items) async {
                return [];
              },
            );
          },
        ),
      );
}

typedef $$EndUseApplicationTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $EndUseApplicationTable,
      EndUseApplicationData,
      $$EndUseApplicationTableFilterComposer,
      $$EndUseApplicationTableOrderingComposer,
      $$EndUseApplicationTableAnnotationComposer,
      $$EndUseApplicationTableCreateCompanionBuilder,
      $$EndUseApplicationTableUpdateCompanionBuilder,
      (EndUseApplicationData, $$EndUseApplicationTableReferences),
      EndUseApplicationData,
      PrefetchHooks Function({bool batchUuid})
    >;
typedef $$SyncOutboxTableCreateCompanionBuilder =
    SyncOutboxCompanion Function({
      required String operationId,
      required String batchUuid,
      required String targetTable,
      required String operationType,
      required String payloadJson,
      Value<String> status,
      Value<int> retryCount,
      required String createdAt,
      Value<String?> lastAttemptAt,
      Value<String?> failureReason,
      Value<String?> jsonSyncedAt,
      Value<String?> mediaSyncedAt,
      Value<String?> hmacSignature,
      Value<int> rowid,
    });
typedef $$SyncOutboxTableUpdateCompanionBuilder =
    SyncOutboxCompanion Function({
      Value<String> operationId,
      Value<String> batchUuid,
      Value<String> targetTable,
      Value<String> operationType,
      Value<String> payloadJson,
      Value<String> status,
      Value<int> retryCount,
      Value<String> createdAt,
      Value<String?> lastAttemptAt,
      Value<String?> failureReason,
      Value<String?> jsonSyncedAt,
      Value<String?> mediaSyncedAt,
      Value<String?> hmacSignature,
      Value<int> rowid,
    });

class $$SyncOutboxTableFilterComposer
    extends Composer<_$AppDatabase, $SyncOutboxTable> {
  $$SyncOutboxTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get operationId => $composableBuilder(
    column: $table.operationId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get batchUuid => $composableBuilder(
    column: $table.batchUuid,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get targetTable => $composableBuilder(
    column: $table.targetTable,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get operationType => $composableBuilder(
    column: $table.operationType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get payloadJson => $composableBuilder(
    column: $table.payloadJson,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get retryCount => $composableBuilder(
    column: $table.retryCount,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get lastAttemptAt => $composableBuilder(
    column: $table.lastAttemptAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get failureReason => $composableBuilder(
    column: $table.failureReason,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get jsonSyncedAt => $composableBuilder(
    column: $table.jsonSyncedAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get mediaSyncedAt => $composableBuilder(
    column: $table.mediaSyncedAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get hmacSignature => $composableBuilder(
    column: $table.hmacSignature,
    builder: (column) => ColumnFilters(column),
  );
}

class $$SyncOutboxTableOrderingComposer
    extends Composer<_$AppDatabase, $SyncOutboxTable> {
  $$SyncOutboxTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get operationId => $composableBuilder(
    column: $table.operationId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get batchUuid => $composableBuilder(
    column: $table.batchUuid,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get targetTable => $composableBuilder(
    column: $table.targetTable,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get operationType => $composableBuilder(
    column: $table.operationType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get payloadJson => $composableBuilder(
    column: $table.payloadJson,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get retryCount => $composableBuilder(
    column: $table.retryCount,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get lastAttemptAt => $composableBuilder(
    column: $table.lastAttemptAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get failureReason => $composableBuilder(
    column: $table.failureReason,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get jsonSyncedAt => $composableBuilder(
    column: $table.jsonSyncedAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get mediaSyncedAt => $composableBuilder(
    column: $table.mediaSyncedAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get hmacSignature => $composableBuilder(
    column: $table.hmacSignature,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$SyncOutboxTableAnnotationComposer
    extends Composer<_$AppDatabase, $SyncOutboxTable> {
  $$SyncOutboxTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get operationId => $composableBuilder(
    column: $table.operationId,
    builder: (column) => column,
  );

  GeneratedColumn<String> get batchUuid =>
      $composableBuilder(column: $table.batchUuid, builder: (column) => column);

  GeneratedColumn<String> get targetTable => $composableBuilder(
    column: $table.targetTable,
    builder: (column) => column,
  );

  GeneratedColumn<String> get operationType => $composableBuilder(
    column: $table.operationType,
    builder: (column) => column,
  );

  GeneratedColumn<String> get payloadJson => $composableBuilder(
    column: $table.payloadJson,
    builder: (column) => column,
  );

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<int> get retryCount => $composableBuilder(
    column: $table.retryCount,
    builder: (column) => column,
  );

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<String> get lastAttemptAt => $composableBuilder(
    column: $table.lastAttemptAt,
    builder: (column) => column,
  );

  GeneratedColumn<String> get failureReason => $composableBuilder(
    column: $table.failureReason,
    builder: (column) => column,
  );

  GeneratedColumn<String> get jsonSyncedAt => $composableBuilder(
    column: $table.jsonSyncedAt,
    builder: (column) => column,
  );

  GeneratedColumn<String> get mediaSyncedAt => $composableBuilder(
    column: $table.mediaSyncedAt,
    builder: (column) => column,
  );

  GeneratedColumn<String> get hmacSignature => $composableBuilder(
    column: $table.hmacSignature,
    builder: (column) => column,
  );
}

class $$SyncOutboxTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $SyncOutboxTable,
          SyncOutboxData,
          $$SyncOutboxTableFilterComposer,
          $$SyncOutboxTableOrderingComposer,
          $$SyncOutboxTableAnnotationComposer,
          $$SyncOutboxTableCreateCompanionBuilder,
          $$SyncOutboxTableUpdateCompanionBuilder,
          (
            SyncOutboxData,
            BaseReferences<_$AppDatabase, $SyncOutboxTable, SyncOutboxData>,
          ),
          SyncOutboxData,
          PrefetchHooks Function()
        > {
  $$SyncOutboxTableTableManager(_$AppDatabase db, $SyncOutboxTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$SyncOutboxTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$SyncOutboxTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$SyncOutboxTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> operationId = const Value.absent(),
                Value<String> batchUuid = const Value.absent(),
                Value<String> targetTable = const Value.absent(),
                Value<String> operationType = const Value.absent(),
                Value<String> payloadJson = const Value.absent(),
                Value<String> status = const Value.absent(),
                Value<int> retryCount = const Value.absent(),
                Value<String> createdAt = const Value.absent(),
                Value<String?> lastAttemptAt = const Value.absent(),
                Value<String?> failureReason = const Value.absent(),
                Value<String?> jsonSyncedAt = const Value.absent(),
                Value<String?> mediaSyncedAt = const Value.absent(),
                Value<String?> hmacSignature = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => SyncOutboxCompanion(
                operationId: operationId,
                batchUuid: batchUuid,
                targetTable: targetTable,
                operationType: operationType,
                payloadJson: payloadJson,
                status: status,
                retryCount: retryCount,
                createdAt: createdAt,
                lastAttemptAt: lastAttemptAt,
                failureReason: failureReason,
                jsonSyncedAt: jsonSyncedAt,
                mediaSyncedAt: mediaSyncedAt,
                hmacSignature: hmacSignature,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String operationId,
                required String batchUuid,
                required String targetTable,
                required String operationType,
                required String payloadJson,
                Value<String> status = const Value.absent(),
                Value<int> retryCount = const Value.absent(),
                required String createdAt,
                Value<String?> lastAttemptAt = const Value.absent(),
                Value<String?> failureReason = const Value.absent(),
                Value<String?> jsonSyncedAt = const Value.absent(),
                Value<String?> mediaSyncedAt = const Value.absent(),
                Value<String?> hmacSignature = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => SyncOutboxCompanion.insert(
                operationId: operationId,
                batchUuid: batchUuid,
                targetTable: targetTable,
                operationType: operationType,
                payloadJson: payloadJson,
                status: status,
                retryCount: retryCount,
                createdAt: createdAt,
                lastAttemptAt: lastAttemptAt,
                failureReason: failureReason,
                jsonSyncedAt: jsonSyncedAt,
                mediaSyncedAt: mediaSyncedAt,
                hmacSignature: hmacSignature,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$SyncOutboxTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $SyncOutboxTable,
      SyncOutboxData,
      $$SyncOutboxTableFilterComposer,
      $$SyncOutboxTableOrderingComposer,
      $$SyncOutboxTableAnnotationComposer,
      $$SyncOutboxTableCreateCompanionBuilder,
      $$SyncOutboxTableUpdateCompanionBuilder,
      (
        SyncOutboxData,
        BaseReferences<_$AppDatabase, $SyncOutboxTable, SyncOutboxData>,
      ),
      SyncOutboxData,
      PrefetchHooks Function()
    >;
typedef $$MediaCapturesTableCreateCompanionBuilder =
    MediaCapturesCompanion Function({
      Value<int> id,
      required String batchUuid,
      required String captureType,
      required String sandboxPath,
      required String sha256Hash,
      Value<bool> isMockLocation,
      required String createdAt,
    });
typedef $$MediaCapturesTableUpdateCompanionBuilder =
    MediaCapturesCompanion Function({
      Value<int> id,
      Value<String> batchUuid,
      Value<String> captureType,
      Value<String> sandboxPath,
      Value<String> sha256Hash,
      Value<bool> isMockLocation,
      Value<String> createdAt,
    });

final class $$MediaCapturesTableReferences
    extends BaseReferences<_$AppDatabase, $MediaCapturesTable, MediaCapture> {
  $$MediaCapturesTableReferences(
    super.$_db,
    super.$_table,
    super.$_typedResult,
  );

  static $SystemMetadataTable _batchUuidTable(_$AppDatabase db) =>
      db.systemMetadata.createAlias(
        $_aliasNameGenerator(
          db.mediaCaptures.batchUuid,
          db.systemMetadata.batchUuid,
        ),
      );

  $$SystemMetadataTableProcessedTableManager get batchUuid {
    final $_column = $_itemColumn<String>('batch_uuid')!;

    final manager = $$SystemMetadataTableTableManager(
      $_db,
      $_db.systemMetadata,
    ).filter((f) => f.batchUuid.sqlEquals($_column));
    final item = $_typedResult.readTableOrNull(_batchUuidTable($_db));
    if (item == null) return manager;
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: [item]),
    );
  }
}

class $$MediaCapturesTableFilterComposer
    extends Composer<_$AppDatabase, $MediaCapturesTable> {
  $$MediaCapturesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get captureType => $composableBuilder(
    column: $table.captureType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sandboxPath => $composableBuilder(
    column: $table.sandboxPath,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sha256Hash => $composableBuilder(
    column: $table.sha256Hash,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<bool> get isMockLocation => $composableBuilder(
    column: $table.isMockLocation,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  $$SystemMetadataTableFilterComposer get batchUuid {
    final $$SystemMetadataTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableFilterComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$MediaCapturesTableOrderingComposer
    extends Composer<_$AppDatabase, $MediaCapturesTable> {
  $$MediaCapturesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get captureType => $composableBuilder(
    column: $table.captureType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sandboxPath => $composableBuilder(
    column: $table.sandboxPath,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sha256Hash => $composableBuilder(
    column: $table.sha256Hash,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<bool> get isMockLocation => $composableBuilder(
    column: $table.isMockLocation,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  $$SystemMetadataTableOrderingComposer get batchUuid {
    final $$SystemMetadataTableOrderingComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableOrderingComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$MediaCapturesTableAnnotationComposer
    extends Composer<_$AppDatabase, $MediaCapturesTable> {
  $$MediaCapturesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get captureType => $composableBuilder(
    column: $table.captureType,
    builder: (column) => column,
  );

  GeneratedColumn<String> get sandboxPath => $composableBuilder(
    column: $table.sandboxPath,
    builder: (column) => column,
  );

  GeneratedColumn<String> get sha256Hash => $composableBuilder(
    column: $table.sha256Hash,
    builder: (column) => column,
  );

  GeneratedColumn<bool> get isMockLocation => $composableBuilder(
    column: $table.isMockLocation,
    builder: (column) => column,
  );

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  $$SystemMetadataTableAnnotationComposer get batchUuid {
    final $$SystemMetadataTableAnnotationComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableAnnotationComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$MediaCapturesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $MediaCapturesTable,
          MediaCapture,
          $$MediaCapturesTableFilterComposer,
          $$MediaCapturesTableOrderingComposer,
          $$MediaCapturesTableAnnotationComposer,
          $$MediaCapturesTableCreateCompanionBuilder,
          $$MediaCapturesTableUpdateCompanionBuilder,
          (MediaCapture, $$MediaCapturesTableReferences),
          MediaCapture,
          PrefetchHooks Function({bool batchUuid})
        > {
  $$MediaCapturesTableTableManager(_$AppDatabase db, $MediaCapturesTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$MediaCapturesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$MediaCapturesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$MediaCapturesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> batchUuid = const Value.absent(),
                Value<String> captureType = const Value.absent(),
                Value<String> sandboxPath = const Value.absent(),
                Value<String> sha256Hash = const Value.absent(),
                Value<bool> isMockLocation = const Value.absent(),
                Value<String> createdAt = const Value.absent(),
              }) => MediaCapturesCompanion(
                id: id,
                batchUuid: batchUuid,
                captureType: captureType,
                sandboxPath: sandboxPath,
                sha256Hash: sha256Hash,
                isMockLocation: isMockLocation,
                createdAt: createdAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String batchUuid,
                required String captureType,
                required String sandboxPath,
                required String sha256Hash,
                Value<bool> isMockLocation = const Value.absent(),
                required String createdAt,
              }) => MediaCapturesCompanion.insert(
                id: id,
                batchUuid: batchUuid,
                captureType: captureType,
                sandboxPath: sandboxPath,
                sha256Hash: sha256Hash,
                isMockLocation: isMockLocation,
                createdAt: createdAt,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable(table),
                  $$MediaCapturesTableReferences(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: ({batchUuid = false}) {
            return PrefetchHooks(
              db: db,
              explicitlyWatchedTables: [],
              addJoins:
                  <
                    T extends TableManagerState<
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic
                    >
                  >(state) {
                    if (batchUuid) {
                      state =
                          state.withJoin(
                                currentTable: table,
                                currentColumn: table.batchUuid,
                                referencedTable: $$MediaCapturesTableReferences
                                    ._batchUuidTable(db),
                                referencedColumn: $$MediaCapturesTableReferences
                                    ._batchUuidTable(db)
                                    .batchUuid,
                              )
                              as T;
                    }

                    return state;
                  },
              getPrefetchedDataCallback: (items) async {
                return [];
              },
            );
          },
        ),
      );
}

typedef $$MediaCapturesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $MediaCapturesTable,
      MediaCapture,
      $$MediaCapturesTableFilterComposer,
      $$MediaCapturesTableOrderingComposer,
      $$MediaCapturesTableAnnotationComposer,
      $$MediaCapturesTableCreateCompanionBuilder,
      $$MediaCapturesTableUpdateCompanionBuilder,
      (MediaCapture, $$MediaCapturesTableReferences),
      MediaCapture,
      PrefetchHooks Function({bool batchUuid})
    >;
typedef $$MoistureReadingsTableCreateCompanionBuilder =
    MoistureReadingsCompanion Function({
      Value<int> id,
      required String readingUuid,
      required String batchUuid,
      required double moisturePercent,
      required int sequence,
      Value<String?> sandboxPath,
      Value<String?> sha256Hash,
      required String createdAt,
    });
typedef $$MoistureReadingsTableUpdateCompanionBuilder =
    MoistureReadingsCompanion Function({
      Value<int> id,
      Value<String> readingUuid,
      Value<String> batchUuid,
      Value<double> moisturePercent,
      Value<int> sequence,
      Value<String?> sandboxPath,
      Value<String?> sha256Hash,
      Value<String> createdAt,
    });

final class $$MoistureReadingsTableReferences
    extends
        BaseReferences<_$AppDatabase, $MoistureReadingsTable, MoistureReading> {
  $$MoistureReadingsTableReferences(
    super.$_db,
    super.$_table,
    super.$_typedResult,
  );

  static $SystemMetadataTable _batchUuidTable(_$AppDatabase db) =>
      db.systemMetadata.createAlias(
        $_aliasNameGenerator(
          db.moistureReadings.batchUuid,
          db.systemMetadata.batchUuid,
        ),
      );

  $$SystemMetadataTableProcessedTableManager get batchUuid {
    final $_column = $_itemColumn<String>('batch_uuid')!;

    final manager = $$SystemMetadataTableTableManager(
      $_db,
      $_db.systemMetadata,
    ).filter((f) => f.batchUuid.sqlEquals($_column));
    final item = $_typedResult.readTableOrNull(_batchUuidTable($_db));
    if (item == null) return manager;
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: [item]),
    );
  }
}

class $$MoistureReadingsTableFilterComposer
    extends Composer<_$AppDatabase, $MoistureReadingsTable> {
  $$MoistureReadingsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get readingUuid => $composableBuilder(
    column: $table.readingUuid,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get moisturePercent => $composableBuilder(
    column: $table.moisturePercent,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get sequence => $composableBuilder(
    column: $table.sequence,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sandboxPath => $composableBuilder(
    column: $table.sandboxPath,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sha256Hash => $composableBuilder(
    column: $table.sha256Hash,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  $$SystemMetadataTableFilterComposer get batchUuid {
    final $$SystemMetadataTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableFilterComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$MoistureReadingsTableOrderingComposer
    extends Composer<_$AppDatabase, $MoistureReadingsTable> {
  $$MoistureReadingsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get readingUuid => $composableBuilder(
    column: $table.readingUuid,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get moisturePercent => $composableBuilder(
    column: $table.moisturePercent,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get sequence => $composableBuilder(
    column: $table.sequence,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sandboxPath => $composableBuilder(
    column: $table.sandboxPath,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sha256Hash => $composableBuilder(
    column: $table.sha256Hash,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  $$SystemMetadataTableOrderingComposer get batchUuid {
    final $$SystemMetadataTableOrderingComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableOrderingComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$MoistureReadingsTableAnnotationComposer
    extends Composer<_$AppDatabase, $MoistureReadingsTable> {
  $$MoistureReadingsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get readingUuid => $composableBuilder(
    column: $table.readingUuid,
    builder: (column) => column,
  );

  GeneratedColumn<double> get moisturePercent => $composableBuilder(
    column: $table.moisturePercent,
    builder: (column) => column,
  );

  GeneratedColumn<int> get sequence =>
      $composableBuilder(column: $table.sequence, builder: (column) => column);

  GeneratedColumn<String> get sandboxPath => $composableBuilder(
    column: $table.sandboxPath,
    builder: (column) => column,
  );

  GeneratedColumn<String> get sha256Hash => $composableBuilder(
    column: $table.sha256Hash,
    builder: (column) => column,
  );

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  $$SystemMetadataTableAnnotationComposer get batchUuid {
    final $$SystemMetadataTableAnnotationComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableAnnotationComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$MoistureReadingsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $MoistureReadingsTable,
          MoistureReading,
          $$MoistureReadingsTableFilterComposer,
          $$MoistureReadingsTableOrderingComposer,
          $$MoistureReadingsTableAnnotationComposer,
          $$MoistureReadingsTableCreateCompanionBuilder,
          $$MoistureReadingsTableUpdateCompanionBuilder,
          (MoistureReading, $$MoistureReadingsTableReferences),
          MoistureReading,
          PrefetchHooks Function({bool batchUuid})
        > {
  $$MoistureReadingsTableTableManager(
    _$AppDatabase db,
    $MoistureReadingsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$MoistureReadingsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$MoistureReadingsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$MoistureReadingsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> readingUuid = const Value.absent(),
                Value<String> batchUuid = const Value.absent(),
                Value<double> moisturePercent = const Value.absent(),
                Value<int> sequence = const Value.absent(),
                Value<String?> sandboxPath = const Value.absent(),
                Value<String?> sha256Hash = const Value.absent(),
                Value<String> createdAt = const Value.absent(),
              }) => MoistureReadingsCompanion(
                id: id,
                readingUuid: readingUuid,
                batchUuid: batchUuid,
                moisturePercent: moisturePercent,
                sequence: sequence,
                sandboxPath: sandboxPath,
                sha256Hash: sha256Hash,
                createdAt: createdAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String readingUuid,
                required String batchUuid,
                required double moisturePercent,
                required int sequence,
                Value<String?> sandboxPath = const Value.absent(),
                Value<String?> sha256Hash = const Value.absent(),
                required String createdAt,
              }) => MoistureReadingsCompanion.insert(
                id: id,
                readingUuid: readingUuid,
                batchUuid: batchUuid,
                moisturePercent: moisturePercent,
                sequence: sequence,
                sandboxPath: sandboxPath,
                sha256Hash: sha256Hash,
                createdAt: createdAt,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable(table),
                  $$MoistureReadingsTableReferences(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: ({batchUuid = false}) {
            return PrefetchHooks(
              db: db,
              explicitlyWatchedTables: [],
              addJoins:
                  <
                    T extends TableManagerState<
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic
                    >
                  >(state) {
                    if (batchUuid) {
                      state =
                          state.withJoin(
                                currentTable: table,
                                currentColumn: table.batchUuid,
                                referencedTable:
                                    $$MoistureReadingsTableReferences
                                        ._batchUuidTable(db),
                                referencedColumn:
                                    $$MoistureReadingsTableReferences
                                        ._batchUuidTable(db)
                                        .batchUuid,
                              )
                              as T;
                    }

                    return state;
                  },
              getPrefetchedDataCallback: (items) async {
                return [];
              },
            );
          },
        ),
      );
}

typedef $$MoistureReadingsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $MoistureReadingsTable,
      MoistureReading,
      $$MoistureReadingsTableFilterComposer,
      $$MoistureReadingsTableOrderingComposer,
      $$MoistureReadingsTableAnnotationComposer,
      $$MoistureReadingsTableCreateCompanionBuilder,
      $$MoistureReadingsTableUpdateCompanionBuilder,
      (MoistureReading, $$MoistureReadingsTableReferences),
      MoistureReading,
      PrefetchHooks Function({bool batchUuid})
    >;
typedef $$CompositePileSamplesTableCreateCompanionBuilder =
    CompositePileSamplesCompanion Function({
      Value<int> id,
      required String sampleUuid,
      required String batchUuid,
      Value<String?> sampledAt,
      Value<double?> latitude,
      Value<double?> longitude,
      Value<String?> kilnQr,
      Value<String?> batchQr,
      Value<String?> sandboxPath,
      Value<String?> sha256Hash,
      required String createdAt,
    });
typedef $$CompositePileSamplesTableUpdateCompanionBuilder =
    CompositePileSamplesCompanion Function({
      Value<int> id,
      Value<String> sampleUuid,
      Value<String> batchUuid,
      Value<String?> sampledAt,
      Value<double?> latitude,
      Value<double?> longitude,
      Value<String?> kilnQr,
      Value<String?> batchQr,
      Value<String?> sandboxPath,
      Value<String?> sha256Hash,
      Value<String> createdAt,
    });

final class $$CompositePileSamplesTableReferences
    extends
        BaseReferences<
          _$AppDatabase,
          $CompositePileSamplesTable,
          CompositePileSample
        > {
  $$CompositePileSamplesTableReferences(
    super.$_db,
    super.$_table,
    super.$_typedResult,
  );

  static $SystemMetadataTable _batchUuidTable(_$AppDatabase db) =>
      db.systemMetadata.createAlias(
        $_aliasNameGenerator(
          db.compositePileSamples.batchUuid,
          db.systemMetadata.batchUuid,
        ),
      );

  $$SystemMetadataTableProcessedTableManager get batchUuid {
    final $_column = $_itemColumn<String>('batch_uuid')!;

    final manager = $$SystemMetadataTableTableManager(
      $_db,
      $_db.systemMetadata,
    ).filter((f) => f.batchUuid.sqlEquals($_column));
    final item = $_typedResult.readTableOrNull(_batchUuidTable($_db));
    if (item == null) return manager;
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: [item]),
    );
  }
}

class $$CompositePileSamplesTableFilterComposer
    extends Composer<_$AppDatabase, $CompositePileSamplesTable> {
  $$CompositePileSamplesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sampleUuid => $composableBuilder(
    column: $table.sampleUuid,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sampledAt => $composableBuilder(
    column: $table.sampledAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get latitude => $composableBuilder(
    column: $table.latitude,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get longitude => $composableBuilder(
    column: $table.longitude,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get kilnQr => $composableBuilder(
    column: $table.kilnQr,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get batchQr => $composableBuilder(
    column: $table.batchQr,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sandboxPath => $composableBuilder(
    column: $table.sandboxPath,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sha256Hash => $composableBuilder(
    column: $table.sha256Hash,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  $$SystemMetadataTableFilterComposer get batchUuid {
    final $$SystemMetadataTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableFilterComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$CompositePileSamplesTableOrderingComposer
    extends Composer<_$AppDatabase, $CompositePileSamplesTable> {
  $$CompositePileSamplesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sampleUuid => $composableBuilder(
    column: $table.sampleUuid,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sampledAt => $composableBuilder(
    column: $table.sampledAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get latitude => $composableBuilder(
    column: $table.latitude,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get longitude => $composableBuilder(
    column: $table.longitude,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get kilnQr => $composableBuilder(
    column: $table.kilnQr,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get batchQr => $composableBuilder(
    column: $table.batchQr,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sandboxPath => $composableBuilder(
    column: $table.sandboxPath,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sha256Hash => $composableBuilder(
    column: $table.sha256Hash,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  $$SystemMetadataTableOrderingComposer get batchUuid {
    final $$SystemMetadataTableOrderingComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableOrderingComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$CompositePileSamplesTableAnnotationComposer
    extends Composer<_$AppDatabase, $CompositePileSamplesTable> {
  $$CompositePileSamplesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get sampleUuid => $composableBuilder(
    column: $table.sampleUuid,
    builder: (column) => column,
  );

  GeneratedColumn<String> get sampledAt =>
      $composableBuilder(column: $table.sampledAt, builder: (column) => column);

  GeneratedColumn<double> get latitude =>
      $composableBuilder(column: $table.latitude, builder: (column) => column);

  GeneratedColumn<double> get longitude =>
      $composableBuilder(column: $table.longitude, builder: (column) => column);

  GeneratedColumn<String> get kilnQr =>
      $composableBuilder(column: $table.kilnQr, builder: (column) => column);

  GeneratedColumn<String> get batchQr =>
      $composableBuilder(column: $table.batchQr, builder: (column) => column);

  GeneratedColumn<String> get sandboxPath => $composableBuilder(
    column: $table.sandboxPath,
    builder: (column) => column,
  );

  GeneratedColumn<String> get sha256Hash => $composableBuilder(
    column: $table.sha256Hash,
    builder: (column) => column,
  );

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  $$SystemMetadataTableAnnotationComposer get batchUuid {
    final $$SystemMetadataTableAnnotationComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableAnnotationComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$CompositePileSamplesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $CompositePileSamplesTable,
          CompositePileSample,
          $$CompositePileSamplesTableFilterComposer,
          $$CompositePileSamplesTableOrderingComposer,
          $$CompositePileSamplesTableAnnotationComposer,
          $$CompositePileSamplesTableCreateCompanionBuilder,
          $$CompositePileSamplesTableUpdateCompanionBuilder,
          (CompositePileSample, $$CompositePileSamplesTableReferences),
          CompositePileSample,
          PrefetchHooks Function({bool batchUuid})
        > {
  $$CompositePileSamplesTableTableManager(
    _$AppDatabase db,
    $CompositePileSamplesTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CompositePileSamplesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CompositePileSamplesTableOrderingComposer(
                $db: db,
                $table: table,
              ),
          createComputedFieldComposer: () =>
              $$CompositePileSamplesTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> sampleUuid = const Value.absent(),
                Value<String> batchUuid = const Value.absent(),
                Value<String?> sampledAt = const Value.absent(),
                Value<double?> latitude = const Value.absent(),
                Value<double?> longitude = const Value.absent(),
                Value<String?> kilnQr = const Value.absent(),
                Value<String?> batchQr = const Value.absent(),
                Value<String?> sandboxPath = const Value.absent(),
                Value<String?> sha256Hash = const Value.absent(),
                Value<String> createdAt = const Value.absent(),
              }) => CompositePileSamplesCompanion(
                id: id,
                sampleUuid: sampleUuid,
                batchUuid: batchUuid,
                sampledAt: sampledAt,
                latitude: latitude,
                longitude: longitude,
                kilnQr: kilnQr,
                batchQr: batchQr,
                sandboxPath: sandboxPath,
                sha256Hash: sha256Hash,
                createdAt: createdAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String sampleUuid,
                required String batchUuid,
                Value<String?> sampledAt = const Value.absent(),
                Value<double?> latitude = const Value.absent(),
                Value<double?> longitude = const Value.absent(),
                Value<String?> kilnQr = const Value.absent(),
                Value<String?> batchQr = const Value.absent(),
                Value<String?> sandboxPath = const Value.absent(),
                Value<String?> sha256Hash = const Value.absent(),
                required String createdAt,
              }) => CompositePileSamplesCompanion.insert(
                id: id,
                sampleUuid: sampleUuid,
                batchUuid: batchUuid,
                sampledAt: sampledAt,
                latitude: latitude,
                longitude: longitude,
                kilnQr: kilnQr,
                batchQr: batchQr,
                sandboxPath: sandboxPath,
                sha256Hash: sha256Hash,
                createdAt: createdAt,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable(table),
                  $$CompositePileSamplesTableReferences(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: ({batchUuid = false}) {
            return PrefetchHooks(
              db: db,
              explicitlyWatchedTables: [],
              addJoins:
                  <
                    T extends TableManagerState<
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic
                    >
                  >(state) {
                    if (batchUuid) {
                      state =
                          state.withJoin(
                                currentTable: table,
                                currentColumn: table.batchUuid,
                                referencedTable:
                                    $$CompositePileSamplesTableReferences
                                        ._batchUuidTable(db),
                                referencedColumn:
                                    $$CompositePileSamplesTableReferences
                                        ._batchUuidTable(db)
                                        .batchUuid,
                              )
                              as T;
                    }

                    return state;
                  },
              getPrefetchedDataCallback: (items) async {
                return [];
              },
            );
          },
        ),
      );
}

typedef $$CompositePileSamplesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $CompositePileSamplesTable,
      CompositePileSample,
      $$CompositePileSamplesTableFilterComposer,
      $$CompositePileSamplesTableOrderingComposer,
      $$CompositePileSamplesTableAnnotationComposer,
      $$CompositePileSamplesTableCreateCompanionBuilder,
      $$CompositePileSamplesTableUpdateCompanionBuilder,
      (CompositePileSample, $$CompositePileSamplesTableReferences),
      CompositePileSample,
      PrefetchHooks Function({bool batchUuid})
    >;
typedef $$TransportEventsTableCreateCompanionBuilder =
    TransportEventsCompanion Function({
      Value<int> id,
      required String eventUuid,
      required String batchUuid,
      required String material,
      Value<double?> distanceKm,
      Value<double?> weightKg,
      Value<String?> vehicleType,
      Value<String?> fuelType,
      Value<double?> fuelAmountLitres,
      Value<String?> occurredAt,
      required String createdAt,
    });
typedef $$TransportEventsTableUpdateCompanionBuilder =
    TransportEventsCompanion Function({
      Value<int> id,
      Value<String> eventUuid,
      Value<String> batchUuid,
      Value<String> material,
      Value<double?> distanceKm,
      Value<double?> weightKg,
      Value<String?> vehicleType,
      Value<String?> fuelType,
      Value<double?> fuelAmountLitres,
      Value<String?> occurredAt,
      Value<String> createdAt,
    });

final class $$TransportEventsTableReferences
    extends
        BaseReferences<_$AppDatabase, $TransportEventsTable, TransportEvent> {
  $$TransportEventsTableReferences(
    super.$_db,
    super.$_table,
    super.$_typedResult,
  );

  static $SystemMetadataTable _batchUuidTable(_$AppDatabase db) =>
      db.systemMetadata.createAlias(
        $_aliasNameGenerator(
          db.transportEvents.batchUuid,
          db.systemMetadata.batchUuid,
        ),
      );

  $$SystemMetadataTableProcessedTableManager get batchUuid {
    final $_column = $_itemColumn<String>('batch_uuid')!;

    final manager = $$SystemMetadataTableTableManager(
      $_db,
      $_db.systemMetadata,
    ).filter((f) => f.batchUuid.sqlEquals($_column));
    final item = $_typedResult.readTableOrNull(_batchUuidTable($_db));
    if (item == null) return manager;
    return ProcessedTableManager(
      manager.$state.copyWith(prefetchedData: [item]),
    );
  }
}

class $$TransportEventsTableFilterComposer
    extends Composer<_$AppDatabase, $TransportEventsTable> {
  $$TransportEventsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get eventUuid => $composableBuilder(
    column: $table.eventUuid,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get material => $composableBuilder(
    column: $table.material,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get distanceKm => $composableBuilder(
    column: $table.distanceKm,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get weightKg => $composableBuilder(
    column: $table.weightKg,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get vehicleType => $composableBuilder(
    column: $table.vehicleType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get fuelType => $composableBuilder(
    column: $table.fuelType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get fuelAmountLitres => $composableBuilder(
    column: $table.fuelAmountLitres,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get occurredAt => $composableBuilder(
    column: $table.occurredAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  $$SystemMetadataTableFilterComposer get batchUuid {
    final $$SystemMetadataTableFilterComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableFilterComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$TransportEventsTableOrderingComposer
    extends Composer<_$AppDatabase, $TransportEventsTable> {
  $$TransportEventsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get eventUuid => $composableBuilder(
    column: $table.eventUuid,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get material => $composableBuilder(
    column: $table.material,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get distanceKm => $composableBuilder(
    column: $table.distanceKm,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get weightKg => $composableBuilder(
    column: $table.weightKg,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get vehicleType => $composableBuilder(
    column: $table.vehicleType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get fuelType => $composableBuilder(
    column: $table.fuelType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get fuelAmountLitres => $composableBuilder(
    column: $table.fuelAmountLitres,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get occurredAt => $composableBuilder(
    column: $table.occurredAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  $$SystemMetadataTableOrderingComposer get batchUuid {
    final $$SystemMetadataTableOrderingComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableOrderingComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$TransportEventsTableAnnotationComposer
    extends Composer<_$AppDatabase, $TransportEventsTable> {
  $$TransportEventsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get eventUuid =>
      $composableBuilder(column: $table.eventUuid, builder: (column) => column);

  GeneratedColumn<String> get material =>
      $composableBuilder(column: $table.material, builder: (column) => column);

  GeneratedColumn<double> get distanceKm => $composableBuilder(
    column: $table.distanceKm,
    builder: (column) => column,
  );

  GeneratedColumn<double> get weightKg =>
      $composableBuilder(column: $table.weightKg, builder: (column) => column);

  GeneratedColumn<String> get vehicleType => $composableBuilder(
    column: $table.vehicleType,
    builder: (column) => column,
  );

  GeneratedColumn<String> get fuelType =>
      $composableBuilder(column: $table.fuelType, builder: (column) => column);

  GeneratedColumn<double> get fuelAmountLitres => $composableBuilder(
    column: $table.fuelAmountLitres,
    builder: (column) => column,
  );

  GeneratedColumn<String> get occurredAt => $composableBuilder(
    column: $table.occurredAt,
    builder: (column) => column,
  );

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  $$SystemMetadataTableAnnotationComposer get batchUuid {
    final $$SystemMetadataTableAnnotationComposer composer = $composerBuilder(
      composer: this,
      getCurrentColumn: (t) => t.batchUuid,
      referencedTable: $db.systemMetadata,
      getReferencedColumn: (t) => t.batchUuid,
      builder:
          (
            joinBuilder, {
            $addJoinBuilderToRootComposer,
            $removeJoinBuilderFromRootComposer,
          }) => $$SystemMetadataTableAnnotationComposer(
            $db: $db,
            $table: $db.systemMetadata,
            $addJoinBuilderToRootComposer: $addJoinBuilderToRootComposer,
            joinBuilder: joinBuilder,
            $removeJoinBuilderFromRootComposer:
                $removeJoinBuilderFromRootComposer,
          ),
    );
    return composer;
  }
}

class $$TransportEventsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $TransportEventsTable,
          TransportEvent,
          $$TransportEventsTableFilterComposer,
          $$TransportEventsTableOrderingComposer,
          $$TransportEventsTableAnnotationComposer,
          $$TransportEventsTableCreateCompanionBuilder,
          $$TransportEventsTableUpdateCompanionBuilder,
          (TransportEvent, $$TransportEventsTableReferences),
          TransportEvent,
          PrefetchHooks Function({bool batchUuid})
        > {
  $$TransportEventsTableTableManager(
    _$AppDatabase db,
    $TransportEventsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$TransportEventsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$TransportEventsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$TransportEventsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> eventUuid = const Value.absent(),
                Value<String> batchUuid = const Value.absent(),
                Value<String> material = const Value.absent(),
                Value<double?> distanceKm = const Value.absent(),
                Value<double?> weightKg = const Value.absent(),
                Value<String?> vehicleType = const Value.absent(),
                Value<String?> fuelType = const Value.absent(),
                Value<double?> fuelAmountLitres = const Value.absent(),
                Value<String?> occurredAt = const Value.absent(),
                Value<String> createdAt = const Value.absent(),
              }) => TransportEventsCompanion(
                id: id,
                eventUuid: eventUuid,
                batchUuid: batchUuid,
                material: material,
                distanceKm: distanceKm,
                weightKg: weightKg,
                vehicleType: vehicleType,
                fuelType: fuelType,
                fuelAmountLitres: fuelAmountLitres,
                occurredAt: occurredAt,
                createdAt: createdAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String eventUuid,
                required String batchUuid,
                required String material,
                Value<double?> distanceKm = const Value.absent(),
                Value<double?> weightKg = const Value.absent(),
                Value<String?> vehicleType = const Value.absent(),
                Value<String?> fuelType = const Value.absent(),
                Value<double?> fuelAmountLitres = const Value.absent(),
                Value<String?> occurredAt = const Value.absent(),
                required String createdAt,
              }) => TransportEventsCompanion.insert(
                id: id,
                eventUuid: eventUuid,
                batchUuid: batchUuid,
                material: material,
                distanceKm: distanceKm,
                weightKg: weightKg,
                vehicleType: vehicleType,
                fuelType: fuelType,
                fuelAmountLitres: fuelAmountLitres,
                occurredAt: occurredAt,
                createdAt: createdAt,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable(table),
                  $$TransportEventsTableReferences(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: ({batchUuid = false}) {
            return PrefetchHooks(
              db: db,
              explicitlyWatchedTables: [],
              addJoins:
                  <
                    T extends TableManagerState<
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic,
                      dynamic
                    >
                  >(state) {
                    if (batchUuid) {
                      state =
                          state.withJoin(
                                currentTable: table,
                                currentColumn: table.batchUuid,
                                referencedTable:
                                    $$TransportEventsTableReferences
                                        ._batchUuidTable(db),
                                referencedColumn:
                                    $$TransportEventsTableReferences
                                        ._batchUuidTable(db)
                                        .batchUuid,
                              )
                              as T;
                    }

                    return state;
                  },
              getPrefetchedDataCallback: (items) async {
                return [];
              },
            );
          },
        ),
      );
}

typedef $$TransportEventsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $TransportEventsTable,
      TransportEvent,
      $$TransportEventsTableFilterComposer,
      $$TransportEventsTableOrderingComposer,
      $$TransportEventsTableAnnotationComposer,
      $$TransportEventsTableCreateCompanionBuilder,
      $$TransportEventsTableUpdateCompanionBuilder,
      (TransportEvent, $$TransportEventsTableReferences),
      TransportEvent,
      PrefetchHooks Function({bool batchUuid})
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$SystemMetadataTableTableManager get systemMetadata =>
      $$SystemMetadataTableTableManager(_db, _db.systemMetadata);
  $$BiomassSourcingTableTableManager get biomassSourcing =>
      $$BiomassSourcingTableTableManager(_db, _db.biomassSourcing);
  $$PyrolysisTelemetryTableTableManager get pyrolysisTelemetry =>
      $$PyrolysisTelemetryTableTableManager(_db, _db.pyrolysisTelemetry);
  $$YieldMetricsTableTableManager get yieldMetrics =>
      $$YieldMetricsTableTableManager(_db, _db.yieldMetrics);
  $$EndUseApplicationTableTableManager get endUseApplication =>
      $$EndUseApplicationTableTableManager(_db, _db.endUseApplication);
  $$SyncOutboxTableTableManager get syncOutbox =>
      $$SyncOutboxTableTableManager(_db, _db.syncOutbox);
  $$MediaCapturesTableTableManager get mediaCaptures =>
      $$MediaCapturesTableTableManager(_db, _db.mediaCaptures);
  $$MoistureReadingsTableTableManager get moistureReadings =>
      $$MoistureReadingsTableTableManager(_db, _db.moistureReadings);
  $$CompositePileSamplesTableTableManager get compositePileSamples =>
      $$CompositePileSamplesTableTableManager(_db, _db.compositePileSamples);
  $$TransportEventsTableTableManager get transportEvents =>
      $$TransportEventsTableTableManager(_db, _db.transportEvents);
}
