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
// Mock plumbing
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

class ScriptedClient extends Mock implements http.Client {
  final List<
    http.BaseResponse Function(
      Uri, {
      Map<String, String>? headers,
      dynamic body,
      Encoding? encoding,
    })
  >
  _jsonHandlers = [];
  final List<http.BaseResponse Function(http.BaseRequest)> _mediaHandlers = [];
  final List<http.BaseRequest> captured = [];
  int _jsonCallIdx = 0;
  int _mediaCallIdx = 0;

  void onJson(int statusCode) {
    _jsonHandlers.add(
      (url, {headers, body, encoding}) => http.Response('{}', statusCode),
    );
  }

  void onJsonWithBody(int statusCode, Map<String, dynamic> body) {
    _jsonHandlers.add(
      (url, {headers, body, encoding}) =>
          http.Response(jsonEncode(body), statusCode),
    );
  }

  void onMedia(int statusCode, {Map<String, dynamic>? body}) {
    final responseBody = body != null ? jsonEncode(body) : '{}';
    _mediaHandlers.add(
      (_) => http.StreamedResponse(
        Stream.value(responseBody.codeUnits.map((e) => e).toList()),
        statusCode,
      ),
    );
  }

  @override
  Future<http.Response> post(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    final req = http.Request('POST', url);
    if (headers != null) req.headers.addAll(headers);
    captured.add(req);
    final handler = _jsonHandlers[_jsonCallIdx++ % _jsonHandlers.length];
    return handler(url, headers: headers, body: body, encoding: encoding)
        as http.Response;
  }

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    // Drain the request body to ensure file handles are released on Windows
    final stream = request.finalize();
    await stream.drain();
    captured.add(request);
    final handler = _mediaHandlers[_mediaCallIdx++ % _mediaHandlers.length];
    return handler(request) as http.StreamedResponse;
  }
}

class MockProviderSubscription<T> extends Mock implements ProviderSubscription<T> {}

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

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------
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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late AppDatabase db;
  late MockConnectivity connectivity;
  late ScriptedClient client;
  late MockRef ref;
  late SyncQueueManager manager;

  setUp(() async {
    FlutterSecureStorage.setMockInitialValues({});
    db = AppDatabase.forTesting(NativeDatabase.memory());
    connectivity = MockConnectivity();
    client = ScriptedClient();
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
  // Test 1 — 409 on JSON retry still proceeds to media upload
  // -------------------------------------------------------------------------
  test('test_409_on_json_retry_proceeds_to_media_upload', () async {
    final mockFile = File(p.join(Directory.systemTemp.path, 'fix4_test1.jpg'));
    await mockFile.writeAsBytes([0, 1, 2, 3]);

    const opId = 'op-fix4-t1';
    await db
        .into(db.syncOutbox)
        .insert(
          SyncOutboxCompanion.insert(
            operationId: opId,
            batchUuid: 'batch-t1',
            targetTable: 'biomass_sourcing',
            operationType: 'INSERT',
            payloadJson: jsonEncode({
              'sourcing_uuid': 'src-t1',
              'photo_path': mockFile.path,
              'sha256_hash': 'aabbcc',
            }),
            createdAt: DateTime.now().toUtc().toIso8601String(),
          ),
        );

    // First loop: JSON returns 409 (duplicate), media returns 200 with matching hash.
    // The sync engine must treat 409 as "already accepted" and proceed to media.
    client.onJson(409);
    client.onMedia(200, body: {'server_sha256': 'aabbcc', 'stored': true});

    await triggerAndWait(connectivity, db, opId);
    // Allow GC of the local file to complete after status flips to SYNCED.
    await Future.delayed(const Duration(milliseconds: 100));

    // Media must have been attempted (2 requests total: JSON + media).
    expect(
      client.captured.length,
      greaterThanOrEqualTo(2),
      reason: '409 on JSON must NOT abort before media upload',
    );

    // Row must be SYNCED.
    final row = await fetchRow(db, opId);
    expect(
      row.status,
      equals('SYNCED'),
      reason: 'Row must be marked SYNCED after 409+media-200',
    );

    // Local file must be GC'd.
    expect(
      await mockFile.exists(),
      isFalse,
      reason: 'Local evidence file must be deleted after confirmed sync',
    );
  });

  // -------------------------------------------------------------------------
  // Test 2 — media failure keeps JSON synced, row stays PENDING
  // -------------------------------------------------------------------------
  test('test_media_failure_does_not_deadlock_json', () async {
    final mockFile = File(p.join(Directory.systemTemp.path, 'fix4_test2.jpg'));
    await mockFile.writeAsBytes([0xFF, 0xD8]);

    const opId = 'op-fix4-t2';
    await db
        .into(db.syncOutbox)
        .insert(
          SyncOutboxCompanion.insert(
            operationId: opId,
            batchUuid: 'batch-t2',
            targetTable: 'biomass_sourcing',
            operationType: 'INSERT',
            payloadJson: jsonEncode({
              'photo_path': mockFile.path,
              'sha256_hash': 'deadbeef',
            }),
            createdAt: DateTime.now().toUtc().toIso8601String(),
          ),
        );

    // JSON succeeds, media fails with 500.
    client.onJson(200);
    client.onMedia(500);

    // Row will not transition to SYNCED; wait the full window to be sure
    // the sync loop attempted (and recorded failure on) the media step.
    await triggerAndWait(
      connectivity,
      db,
      opId,
      expectedStatus: 'SYNCED',
      maxWaitMs: 1500,
    );

    final row = await fetchRow(db, opId);

    // JSON phase is committed.
    expect(
      row.jsonSyncedAt,
      isNotNull,
      reason: 'json_synced_at must be stamped after JSON 200',
    );

    // Row is still PENDING (media not confirmed).
    expect(
      row.status,
      equals('PENDING'),
      reason: 'Row must stay PENDING when media upload fails',
    );

    // Local file must NOT be deleted (media not confirmed).
    expect(
      await mockFile.exists(),
      isTrue,
      reason: 'Local evidence must be preserved when media upload fails',
    );

    await mockFile.delete();
  });

  // -------------------------------------------------------------------------
  // Test 3 — second loop skips JSON re-POST when json_synced_at is set
  // -------------------------------------------------------------------------
  test('test_retry_skips_json_repost_when_already_json_synced', () async {
    const opId = 'op-fix4-t3';
    final now = DateTime.now().toUtc().toIso8601String();

    // Register a JSON handler that SUCCEEDS — if JSON is re-posted the test
    // will see an extra captured request and fail the assertion below.
    client.onJson(200);
    // Media handler for the no-photo path (still needed for mediaSyncedAt stamp).
    client.onMedia(200, body: {'server_sha256': null});

    await db
        .into(db.syncOutbox)
        .insert(
          SyncOutboxCompanion.insert(
            operationId: opId,
            batchUuid: 'batch-t3',
            targetTable: 'biomass_sourcing',
            operationType: 'INSERT',
            payloadJson: jsonEncode({'photo_path': null}),
            createdAt: now,
            // Pre-stamp json_synced_at directly on insert to avoid race conditions!
            jsonSyncedAt: Value(now),
          ),
        );

    await triggerAndWait(connectivity, db, opId);

    // Count actual HTTP POST requests (not streamed media sends).
    final jsonPosts = client.captured
        .whereType<http.Request>()
        .where((r) => r.method == 'POST' && !r.url.path.contains('/media'))
        .length;

    expect(
      jsonPosts,
      equals(0),
      reason:
          'JSON must NOT be re-posted when json_synced_at is already stamped. '
          'If this is 1, the skip-guard in _processEntry is broken.',
    );
  });

  // -------------------------------------------------------------------------
  // Test 4 — non-200/non-409 JSON response increments retryCount
  // -------------------------------------------------------------------------
  test('test_non_200_non_409_json_increments_retry_count', () async {
    const opId = 'op-fix4-t4';
    await db
        .into(db.syncOutbox)
        .insert(
          SyncOutboxCompanion.insert(
            operationId: opId,
            batchUuid: 'batch-t4',
            targetTable: 'biomass_sourcing',
            operationType: 'INSERT',
            payloadJson: jsonEncode({'photo_path': null}),
            createdAt: DateTime.now().toUtc().toIso8601String(),
          ),
        );

    client.onJson(500); // server error

    // Will never reach SYNCED; wait the full window so the retry counter
    // has time to increment.
    await triggerAndWait(
      connectivity,
      db,
      opId,
      expectedStatus: 'SYNCED',
      maxWaitMs: 1500,
    );

    final row = await fetchRow(db, opId);
    expect(
      row.retryCount,
      greaterThan(0),
      reason: 'retryCount must increment on server 500',
    );
    expect(
      row.status,
      equals('PENDING'),
      reason: 'Row must stay PENDING on JSON 500',
    );
  });
}
