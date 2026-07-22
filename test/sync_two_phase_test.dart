import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/data/local/database_provider.dart';
import 'package:dmrv_app/services/sync_queue_manager.dart';
import 'package:drift/drift.dart' show Value;
import 'package:drift/native.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:mockito/mockito.dart';
import 'package:path/path.dart' as p;

// ---------------------------------------------------------------------------
// Shared mock plumbing (same pattern as sync_deadlock_test.dart)
// ---------------------------------------------------------------------------
class MockConnectivity extends Mock implements Connectivity {
  final _ctrl = StreamController<List<ConnectivityResult>>.broadcast();
  @override
  Stream<List<ConnectivityResult>> get onConnectivityChanged => _ctrl.stream;

  @override
  Future<List<ConnectivityResult>> checkConnectivity() async => [
    ConnectivityResult.wifi,
  ];

  void emit(List<ConnectivityResult> r) => _ctrl.add(r);
  void dispose() => _ctrl.close();
}

class FakeClient extends Mock implements http.Client {
  int jsonStatus = 200;
  int mediaStatus = 200;
  String? serverSha256;
  final List<http.BaseRequest> captured = [];

  @override
  Future<http.Response> post(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    captured.add(http.Request('POST', url)..headers.addAll(headers ?? {}));
    return http.Response('{}', jsonStatus);
  }

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    // Drain the request body to ensure file handles are released on Windows
    final stream = request.finalize();
    await stream.drain();
    captured.add(request);
    print(
      '[FakeClient] send called on ${this.hashCode}, serverSha256 is: $serverSha256',
    );
    final body = jsonEncode({
      if (serverSha256 != null) 'server_sha256': serverSha256,
      'stored': true,
    });
    print('[FakeClient] sending body: $body');
    return http.StreamedResponse(
      Stream.value(body.codeUnits.map((e) => e).toList()),
      mediaStatus,
    );
  }
}

class MockProviderSubscription<T> extends Mock
    implements ProviderSubscription<T> {}

class MockRef extends Mock implements Ref {
  final Map<dynamic, Object?> overrides = {};

  @override
  T read<T>(ProviderListenable<T> provider) => overrides[provider] as T;

  @override
  ProviderSubscription<T> listen<T>(
    ProviderListenable<T> provider,
    void Function(T?, T) listener, {
    void Function(Object, StackTrace)? onError,
    bool fireImmediately = false,
  }) {
    return MockProviderSubscription<T>();
  }
}

Future<SyncOutboxData> fetchRow(AppDatabase db, String opId) => (db.select(
  db.syncOutbox,
)..where((t) => t.operationId.equals(opId))).getSingle();

/// Triggers sync and polls until the row reaches [expectedStatus] or
/// [maxWaitMs] elapses. Much more reliable than a fixed delay on CI.
Future<void> triggerAndWait(
  MockConnectivity connectivity,
  AppDatabase db,
  String opId, {
  String expectedStatus = 'SYNCED',
  int maxWaitMs = 3000,
  int pollIntervalMs = 50,
}) async {
  connectivity.emit([ConnectivityResult.wifi]);
  final deadline = DateTime.now().add(Duration(milliseconds: maxWaitMs));
  while (DateTime.now().isBefore(deadline)) {
    await Future.delayed(Duration(milliseconds: pollIntervalMs));
    final rows = await (db.select(
      db.syncOutbox,
    )..where((t) => t.operationId.equals(opId))).get();
    if (rows.isNotEmpty && rows.first.status == expectedStatus) return;
  }
  // Let the test fail with a meaningful assertion rather than timing out.
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late AppDatabase db;
  late MockConnectivity connectivity;
  late FakeClient client;
  late MockRef ref;
  late SyncQueueManager manager;

  Future<File> seedRow(String opId, String sha256, String filePath) async {
    final f = File(filePath);
    await f.writeAsBytes([0xFF, 0xD8, 0xFF, 0xE0]);
    await db
        .into(db.syncOutbox)
        .insert(
          SyncOutboxCompanion.insert(
            operationId: opId,
            batchUuid: Value('batch-5'),
            targetTable: 'biomass_sourcing',
            operationType: 'INSERT',
            payloadJson: jsonEncode({
              'photo_path': filePath,
              'sha256_hash': sha256,
            }),
            createdAt: DateTime.now().toUtc().toIso8601String(),
          ),
        );
    return f;
  }

  setUp(() async {
    FlutterSecureStorage.setMockInitialValues({});
    db = AppDatabase.forTesting(NativeDatabase.memory());
    connectivity = MockConnectivity();
    client = FakeClient();
    ref = MockRef();
    ref.overrides[appDatabaseProvider] = db;
    ref.overrides[appDatabaseProvider.future] = Future.value(db);
    manager = SyncQueueManager(
      ref,
      config: const SyncConfig(
        apiBase: 'http://test.local',
        enablePeriodicPolling: false,
      ),
      connectivity: connectivity,
      client: client,
    );
  });

  tearDown(() async {
    manager.dispose();
    connectivity.dispose();
    await db.close();
  });

  // -------------------------------------------------------------------------
  // Test 1 — local file preserved if server returns no sha256
  // -------------------------------------------------------------------------
  test('test_local_file_preserved_if_server_sha256_missing', () async {
    client.jsonStatus = 200;
    client.mediaStatus = 200;
    client.serverSha256 = null; // server returns no hash

    final f = await seedRow(
      'op-5-t1',
      'abc123',
      p.join(Directory.systemTemp.path, 'fix5_t1.jpg'),
    );

    // No server sha256 means the row stays PENDING (can't confirm integrity).
    await triggerAndWait(
      connectivity,
      db,
      'op-5-t1',
      expectedStatus: 'SYNCED',
      maxWaitMs: 1500,
    );
    await Future.delayed(const Duration(milliseconds: 100));

    expect(
      await f.exists(),
      isTrue,
      reason: 'File must NOT be deleted when server provides no sha256',
    );

    await f.delete();
  });

  // -------------------------------------------------------------------------
  // Test 2 — local file preserved if server sha256 mismatches
  // -------------------------------------------------------------------------
  test('test_local_file_preserved_if_server_sha256_mismatches', () async {
    client.jsonStatus = 200;
    client.mediaStatus = 200;
    client.serverSha256 = 'WRONG_HASH_FROM_SERVER'; // mismatch

    const localSha = 'correct_hash_value';
    final f = await seedRow(
      'op-5-t2',
      localSha,
      p.join(Directory.systemTemp.path, 'fix5_t2.jpg'),
    );

    // Mismatch keeps the row PENDING; wait the full window so the sync loop
    // has time to perform both phases and record the integrity failure.
    await triggerAndWait(
      connectivity,
      db,
      'op-5-t2',
      expectedStatus: 'SYNCED',
      maxWaitMs: 1500,
    );
    await Future.delayed(const Duration(milliseconds: 100));

    expect(
      await f.exists(),
      isTrue,
      reason:
          'File must be preserved when server sha256 does not match local sha256',
    );

    // Row must remain PENDING (not SYNCED) since evidence integrity failed.
    final row = await fetchRow(db, 'op-5-t2');
    expect(
      row.status,
      equals('PENDING'),
      reason: 'Row must stay PENDING on sha256 mismatch',
    );

    await f.delete();
  });

  // -------------------------------------------------------------------------
  // Test 3 — local file deleted only when hashes match
  // -------------------------------------------------------------------------
  test('test_local_file_deleted_only_on_hash_match', () async {
    const localSha = 'matching_sha256_hash';
    client.jsonStatus = 200;
    client.mediaStatus = 200;
    client.serverSha256 = localSha; // correct match

    final f = await seedRow(
      'op-5-t3',
      localSha,
      p.join(Directory.systemTemp.path, 'fix5_t3.jpg'),
    );

    print('Setting serverSha256 to $localSha on client ${client.hashCode}');

    await triggerAndWait(connectivity, db, 'op-5-t3');
    await Future.delayed(const Duration(milliseconds: 100));

    expect(
      await f.exists(),
      isFalse,
      reason: 'File must be GC\'d when server sha256 matches local sha256',
    );

    final row = await fetchRow(db, 'op-5-t3');
    expect(row.status, equals('SYNCED'));
  });

  // -------------------------------------------------------------------------
  // Test 4 — row with no photo_path syncs cleanly without media phase
  // -------------------------------------------------------------------------
  test('test_row_without_photo_syncs_without_media_request', () async {
    const opId = 'op-5-t4';
    await db
        .into(db.syncOutbox)
        .insert(
          SyncOutboxCompanion.insert(
            operationId: opId,
            batchUuid: Value('batch-5'),
            targetTable: 'system_metadata',
            operationType: 'INSERT',
            payloadJson: jsonEncode({'batch_uuid': 'batch-5'}),
            createdAt: DateTime.now().toUtc().toIso8601String(),
          ),
        );

    client.jsonStatus = 200;

    await triggerAndWait(connectivity, db, opId);

    // Only the JSON POST should have been made.
    expect(
      client.captured.length,
      equals(1),
      reason: 'No media request should be made when payload has no photo_path',
    );

    final row = await fetchRow(db, opId);
    expect(row.status, equals('SYNCED'));
  });

  // -------------------------------------------------------------------------
  // Test 5 — P1-B6: crash-safety of the stamp-before-delete GC ordering.
  // The sync loop stamps media_synced_at BEFORE deleting the local file. If the
  // process dies AFTER the delete (file gone) but the stamp is already
  // committed, a retry must resume the row as SYNCED — it must NOT re-read the
  // missing file and mark server-accepted evidence FAILED_PERMANENTLY.
  // -------------------------------------------------------------------------
  test('test_stamped_media_row_with_missing_file_resumes_synced', () async {
    const opId = 'op-5-t5';
    final missingPath = p.join(Directory.systemTemp.path, 'fix5_t5_gone.jpg');
    final gone = File(missingPath);
    if (await gone.exists()) await gone.delete(); // file already GC'd

    final now = DateTime.now().toUtc().toIso8601String();
    await db
        .into(db.syncOutbox)
        .insert(
          SyncOutboxCompanion.insert(
            operationId: opId,
            batchUuid: Value('batch-5'),
            targetTable: 'biomass_sourcing',
            operationType: 'INSERT',
            payloadJson: jsonEncode({
              'photo_path': missingPath,
              'sha256_hash': 'abc',
            }),
            createdAt: now,
            // Both phases were confirmed before the crash: JSON posted, media
            // bytes verified + stamped. Only the local file GC didn't finish.
            jsonSyncedAt: Value(now),
            mediaSyncedAt: Value(now),
          ),
        );

    await triggerAndWait(connectivity, db, opId);

    final row = await fetchRow(db, opId);
    expect(
      row.status,
      equals('SYNCED'),
      reason:
          'A row already stamped media_synced_at must resume as SYNCED even '
          'though its file was already GC\'d — never FAILED on the missing file',
    );
    expect(
      client.captured.isEmpty,
      isTrue,
      reason: 'Both phases were already confirmed; resume makes no network call',
    );
  });
}
