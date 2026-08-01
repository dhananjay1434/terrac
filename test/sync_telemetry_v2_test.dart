import 'dart:async';
import 'dart:convert';

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

// Mirrors the shared mock plumbing in sync_two_phase_test.dart.
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
  int status = 200;
  final List<http.BaseRequest> captured = [];

  @override
  Future<http.Response> post(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    captured.add(http.Request('POST', url)..headers.addAll(headers ?? {}));
    return http.Response('{"status":"ok"}', status);
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

Future<void> triggerAndWait(
  MockConnectivity connectivity,
  AppDatabase db,
  String opId, {
  required String expectedStatus,
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
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late AppDatabase db;
  late MockConnectivity connectivity;
  late FakeClient client;
  late MockRef ref;
  late SyncQueueManager manager;

  Future<void> seedRow(String opId) => db
      .into(db.syncOutbox)
      .insert(
        SyncOutboxCompanion.insert(
          operationId: opId,
          batchUuid: const Value(null),
          targetTable: 'telemetry_v2',
          operationType: 'TELEMETRY_V2_CHUNK',
          payloadJson: jsonEncode({'channel': 'T1', 'seq': 0}),
          createdAt: DateTime.now().toUtc().toIso8601String(),
        ),
      );

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

  test('200 relays to /api/v2/telemetry/ingest and marks SYNCED', () async {
    client.status = 200;
    await seedRow('v2-op-1');
    await triggerAndWait(connectivity, db, 'v2-op-1', expectedStatus: 'SYNCED');
    final row = await (db.select(
      db.syncOutbox,
    )..where((t) => t.operationId.equals('v2-op-1'))).getSingle();
    expect(row.status, 'SYNCED');
    expect(
      client.captured.any(
        (r) => r.url.toString() == 'http://test.local/api/v2/telemetry/ingest',
      ),
      isTrue,
    );
  });

  test('422 marks FAILED_PERMANENTLY', () async {
    client.status = 422;
    await seedRow('v2-op-2');
    await triggerAndWait(
      connectivity,
      db,
      'v2-op-2',
      expectedStatus: 'FAILED_PERMANENTLY',
    );
    final row = await (db.select(
      db.syncOutbox,
    )..where((t) => t.operationId.equals('v2-op-2'))).getSingle();
    expect(row.status, 'FAILED_PERMANENTLY');
  });

  test('503 leaves the row PENDING for backoff retry', () async {
    client.status = 503;
    await seedRow('v2-op-3');
    connectivity.emit([ConnectivityResult.wifi]);
    await Future.delayed(const Duration(milliseconds: 500));
    final row = await (db.select(
      db.syncOutbox,
    )..where((t) => t.operationId.equals('v2-op-3'))).getSingle();
    expect(row.status, 'PENDING');
  });
}
