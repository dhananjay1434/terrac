import 'package:drift/drift.dart';
import 'package:uuid/uuid.dart';

import '../data/local/app_database.dart';
import 'telemetry_courier.dart';

const _uuid = Uuid();

/// Real [ChunkOutbox] adapter: enqueues a signed telemetry chunk as a
/// SyncOutbox row (operationType 'TELEMETRY_V2_CHUNK'), riding the existing
/// outbox table — no schema migration. The sync loop relays it to
/// POST /api/v2/telemetry/ingest (see sync_queue_manager.dart).
class TelemetryOutboxDrift implements ChunkOutbox {
  TelemetryOutboxDrift(this._db);
  final AppDatabase _db;

  @override
  Future<void> enqueueTelemetryChunk(String payloadJson) async {
    final now = DateTime.now().toUtc().toIso8601String();
    await _db
        .into(_db.syncOutbox)
        .insert(
          SyncOutboxCompanion.insert(
            operationId: _uuid.v4(),
            batchUuid: const Value(null),
            targetTable: 'telemetry_v2',
            operationType: 'TELEMETRY_V2_CHUNK',
            payloadJson: payloadJson,
            createdAt: now,
          ),
        );
  }
}
