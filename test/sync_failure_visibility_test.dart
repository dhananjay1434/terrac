import 'dart:async';
import 'dart:convert';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/data/local/database_provider.dart';
import 'package:dmrv_app/services/sync_queue_manager.dart';
import 'package:drift/native.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:mockito/mockito.dart';

// Minimal mock plumbing (mirrors sync_queue_triage_test.dart).
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

class MockClient extends Mock implements http.Client {
  http.Response? nextResponse;
  @override
  Future<http.Response> post(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async => nextResponse ?? http.Response('{}', 200);
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
  }) => MockProviderSubscription<T>();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late AppDatabase db;
  late MockConnectivity connectivity;
  late MockClient client;
  late MockRef ref;
  late SyncQueueManager manager;

  Future<SyncOutboxData> fetch(String opId) => (db.select(
    db.syncOutbox,
  )..where((t) => t.operationId.equals(opId))).getSingle();

  Future<void> waitForStatus(String opId, String status,
      {int maxMs = 3000}) async {
    final deadline = DateTime.now().add(Duration(milliseconds: maxMs));
    while (DateTime.now().isBefore(deadline)) {
      await Future.delayed(const Duration(milliseconds: 50));
      final rows = await (db.select(
        db.syncOutbox,
      )..where((t) => t.operationId.equals(opId))).get();
      if (rows.isNotEmpty && rows.first.status == status) return;
    }
  }

  Future<void> seedJsonRow(String opId) => db.into(db.syncOutbox).insert(
    SyncOutboxCompanion.insert(
      operationId: opId,
      batchUuid: 'b1',
      targetTable: 'system_metadata',
      operationType: 'INSERT',
      payloadJson: jsonEncode({'batch_uuid': 'b1'}),
      createdAt: DateTime.now().toUtc().toIso8601String(),
    ),
  );

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    db = AppDatabase.forTesting(NativeDatabase.memory());
    connectivity = MockConnectivity();
    client = MockClient();
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

  test('a 422 marks the row FAILED_PERMANENTLY with a failure reason', () async {
    client.nextResponse = http.Response('bad payload body', 422);
    await seedJsonRow('op-fail-1');

    connectivity.emit([ConnectivityResult.wifi]);
    await waitForStatus('op-fail-1', 'FAILED_PERMANENTLY');

    final row = await fetch('op-fail-1');
    expect(row.status, 'FAILED_PERMANENTLY');
    expect(row.failureReason, isNotNull);
    expect(
      row.failureReason!.contains('422'),
      isTrue,
      reason: 'the operator-visible reason should carry the server status',
    );

    // watchProblemRows surfaces it.
    final problems = await manager.watchProblemRows().first;
    expect(problems.any((r) => r.operationId == 'op-fail-1'), isTrue);
  });

  test('retryPermanentlyFailed resets a stuck row and it recovers', () async {
    client.nextResponse = http.Response('bad payload body', 422);
    await seedJsonRow('op-fail-2');
    connectivity.emit([ConnectivityResult.wifi]);
    await waitForStatus('op-fail-2', 'FAILED_PERMANENTLY');
    expect((await fetch('op-fail-2')).status, 'FAILED_PERMANENTLY');

    // Operator fixes the cause; server now accepts.
    client.nextResponse = http.Response('{}', 200);
    await manager.retryPermanentlyFailed('op-fail-2');
    await waitForStatus('op-fail-2', 'SYNCED');
    expect((await fetch('op-fail-2')).status, 'SYNCED');
  });
}
