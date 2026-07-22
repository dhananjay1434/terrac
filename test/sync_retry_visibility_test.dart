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

/// V7 P2 — operator force-retry of a row stuck in exponential backoff.
///
/// `retryNow` clears ONLY the backoff gate (nulls `lastAttemptAt`) so the loop
/// re-attempts a PENDING backoff row immediately, WITHOUT resetting the
/// retry-count ceiling, and it must NOT touch FAILED_PERMANENTLY rows (those
/// use `retryPermanentlyFailed`). We assert the observable OUTCOME (the row is
/// un-stuck and re-processed) with a controllable fake client, rather than the
/// transient DB state that the immediately-triggered loop races to overwrite.
class _MockConnectivity extends Mock implements Connectivity {
  final _ctrl = StreamController<List<ConnectivityResult>>.broadcast();
  @override
  Stream<List<ConnectivityResult>> get onConnectivityChanged => _ctrl.stream;
  @override
  Future<List<ConnectivityResult>> checkConnectivity() async =>
      [ConnectivityResult.wifi];
  void dispose() => _ctrl.close();
}

class _FakeClient extends Mock implements http.Client {
  int jsonStatus = 200;
  @override
  Future<http.Response> post(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async =>
      http.Response('{}', jsonStatus);
}

class _MockSub<T> extends Mock implements ProviderSubscription<T> {}

class _MockRef extends Mock implements Ref {
  final Map<dynamic, Object?> overrides = {};
  @override
  T read<T>(ProviderListenable<T> provider) => overrides[provider] as T;
  @override
  ProviderSubscription<T> listen<T>(
    ProviderListenable<T> provider,
    void Function(T?, T) listener, {
    void Function(Object, StackTrace)? onError,
    bool fireImmediately = false,
  }) => _MockSub<T>();
}

Future<SyncOutboxData> _row(AppDatabase db, String op) =>
    (db.select(db.syncOutbox)..where((t) => t.operationId.equals(op)))
        .getSingle();

Future<String> _waitForStatus(
  AppDatabase db,
  String op, {
  required String want,
  int maxMs = 3000,
}) async {
  final deadline = DateTime.now().add(Duration(milliseconds: maxMs));
  while (DateTime.now().isBefore(deadline)) {
    await Future.delayed(const Duration(milliseconds: 40));
    final r = await _row(db, op);
    if (r.status == want) return r.status;
  }
  return (await _row(db, op)).status;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late AppDatabase db;
  late _MockConnectivity connectivity;
  late _FakeClient client;
  late _MockRef ref;
  late SyncQueueManager manager;

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    db = AppDatabase.forTesting(NativeDatabase.memory());
    connectivity = _MockConnectivity();
    client = _FakeClient();
    ref = _MockRef();
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

  // A JSON-only (no photo) backoff row: PENDING, retryCount>0, lastAttemptAt
  // set — normally skipped by the exponential backoff gate.
  Future<void> seedBackoffRow(String op, {int retryCount = 6}) async {
    await db.into(db.syncOutbox).insert(
          SyncOutboxCompanion.insert(
            operationId: op,
            batchUuid: Value('batch-1'),
            targetTable: 'moisture_readings',
            operationType: 'INSERT',
            payloadJson: jsonEncode({'reading_uuid': op, 'moisture': 12.0}),
            createdAt: DateTime.now().toUtc().toIso8601String(),
            status: const Value('PENDING'),
            retryCount: Value(retryCount),
            lastAttemptAt: Value(DateTime.now().toUtc().toIso8601String()),
            failureReason: const Value('JSON upload failed (client error 500)'),
          ),
        );
  }

  test('retryNow un-sticks a backoff row so the loop re-attempts it now',
      () async {
    await seedBackoffRow('op-backoff');
    client.jsonStatus = 200; // this time the server accepts

    // Without retryNow the row would sit out its 2^6s backoff window. Forcing
    // it must clear the gate and let the immediately-kicked loop sync it.
    await manager.retryNow('op-backoff');

    final status = await _waitForStatus(db, 'op-backoff', want: 'SYNCED');
    expect(status, 'SYNCED',
        reason: 'force-retry should clear the backoff gate and sync the row');
  });

  test('retryNow leaves FAILED_PERMANENTLY rows untouched (wrong scope)',
      () async {
    await db.into(db.syncOutbox).insert(
          SyncOutboxCompanion.insert(
            operationId: 'op-dead',
            batchUuid: Value('batch-1'),
            targetTable: 'moisture_readings',
            operationType: 'INSERT',
            payloadJson: jsonEncode({'reading_uuid': 'op-dead'}),
            createdAt: DateTime.now().toUtc().toIso8601String(),
            status: const Value('FAILED_PERMANENTLY'),
            retryCount: const Value(11),
            lastAttemptAt: Value(DateTime.now().toUtc().toIso8601String()),
          ),
        );

    await manager.retryNow('op-dead');
    // Give any (incorrectly) triggered processing a beat to NOT happen.
    await Future.delayed(const Duration(milliseconds: 200));

    final after = await _row(db, 'op-dead');
    expect(after.status, 'FAILED_PERMANENTLY',
        reason: 'retryNow must not resurrect a permanently-failed row');
  });
}
