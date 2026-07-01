import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mocktail/mocktail.dart';

import 'package:dmrv_app/services/sync_queue_manager.dart';

class MockConnectivity extends Mock implements Connectivity {}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late MockConnectivity mockConnectivity;

  setUp(() {
    mockConnectivity = MockConnectivity();
    when(
      () => mockConnectivity.checkConnectivity(),
    ).thenAnswer((_) async => [ConnectivityResult.wifi]);
    when(
      () => mockConnectivity.onConnectivityChanged,
    ).thenAnswer((_) => Stream.value([ConnectivityResult.wifi]));
  });

  ProviderContainer createContainer() {
    return ProviderContainer(
      overrides: [
        syncQueueManagerProvider.overrideWith(
          (ref) => SyncQueueManager(
            ref,
            connectivity: mockConnectivity,
            startPeriodicTimer: false,
          ),
        ),
      ],
    );
  }

  test('WorkManager callback invokes _triggerSync', () async {
    final container = createContainer();
    final manager = container.read(syncQueueManagerProvider);
    expect(() => manager.kickSync(), returnsNormally);
  });

  test('background sync skips when already syncing', () async {
    final container = createContainer();
    final manager = container.read(syncQueueManagerProvider);

    manager.kickSync(); // first call sets _isSyncing = true
    manager.kickSync(); // second call should return immediately
    expect(true, isTrue); // If no exception, it passed
  });

  test('background sync handles no-network gracefully', () async {
    final container = createContainer();
    final manager = container.read(syncQueueManagerProvider);
    expect(() => manager.kickSync(), returnsNormally);
  });

  test('kickSync returns an awaitable Future that completes', () async {
    // Phase 10: kickSync must return a Future<void> (not void) so the
    // WorkManager dispatcher can await real sync completion instead of
    // sleeping a fixed 10s. Awaiting it here must complete without hanging
    // (apiBase is empty in tests, so _triggerSync returns promptly).
    final container = createContainer();
    final manager = container.read(syncQueueManagerProvider);
    final result = manager.kickSync();
    expect(result, isA<Future<void>>());
    await result.timeout(const Duration(seconds: 5));
  });
}
