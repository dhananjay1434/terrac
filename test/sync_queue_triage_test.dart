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
  final List<http.BaseRequest> capturedRequests = [];
  http.Response? nextResponse;

  @override
  Future<http.Response> post(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    final request = http.Request('POST', url);
    if (headers != null) request.headers.addAll(headers);
    if (body != null) request.body = body as String;
    capturedRequests.add(request);
    return nextResponse ?? http.Response('{}', 200);
  }

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    // Drain the request body to ensure file handles are released on Windows
    final stream = request.finalize();
    await stream.drain();
    capturedRequests.add(request);
    // sha256 of [0, 1, 2, 3] is '054edec1d0211f624fed0cbca9d4f9400b0e491c43742af2c5b0abebf0c990d8'
    final bodyStream = Stream.value(
      utf8.encode(
        jsonEncode({
          'server_sha256':
              '054edec1d0211f624fed0cbca9d4f9400b0e491c43742af2c5b0abebf0c990d8',
        }),
      ),
    );
    return http.StreamedResponse(bodyStream, 200);
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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late AppDatabase db;
  late MockConnectivity connectivity;
  late MockClient client;
  late MockRef ref;
  late SyncQueueManager manager;

  setUp(() async {
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
    await db.close();
  });

  test(
    'Sync loop triggers on network restoration and processes JSON then Media',
    () async {
      // 1. Seed a pending record with a mock file path
      final mockFile = File(
        p.join(Directory.systemTemp.path, 'mock_evidence.jpg'),
      );
      await mockFile.writeAsBytes([0, 1, 2, 3]);

      final opId = 'test-op-123';
      await db
          .into(db.syncOutbox)
          .insert(
            SyncOutboxCompanion.insert(
              operationId: opId,
              batchUuid: Value('batch-123'),
              targetTable: 'biomass_sourcing',
              operationType: 'INSERT',
              payloadJson: jsonEncode({
                'sourcing_uuid': 'src-123',
                'photo_path': mockFile.path,
                'sha256_hash':
                    '054edec1d0211f624fed0cbca9d4f9400b0e491c43742af2c5b0abebf0c990d8',
              }),
              createdAt: DateTime.now().toIso8601String(),
            ),
          );

      // 2. Set offline state initially
      connectivity.emit([ConnectivityResult.none]);
      await Future.delayed(const Duration(milliseconds: 100));
      expect(client.capturedRequests.isEmpty, true);

      // 3. Toggle to online
      connectivity.emit([ConnectivityResult.wifi]);

      // Allow the async loop to run. Since it's triggered by a stream, we wait a bit.
      await Future.delayed(const Duration(milliseconds: 500));

      // 4. Assertions
      expect(client.capturedRequests.length, 2);

      // First request: JSON
      final jsonReq = client.capturedRequests[0] as http.Request;
      expect(jsonReq.url.toString(), 'http://test.local/api/v1/batches');
      expect(jsonReq.headers['X-Idempotency-Key'], opId);

      // Second request: Media
      final mediaReq = client.capturedRequests[1] as http.MultipartRequest;
      expect(mediaReq.url.toString(), 'http://test.local/api/v1/media');
      expect(mediaReq.headers['X-Idempotency-Key'], '${opId}_media');

      // Check DB status
      final entry = await (db.select(
        db.syncOutbox,
      )..where((t) => t.operationId.equals(opId))).getSingle();
      expect(entry.status, 'SYNCED');

      // Check GC: file should be deleted
      expect(await mockFile.exists(), false);
    },
  );
}
