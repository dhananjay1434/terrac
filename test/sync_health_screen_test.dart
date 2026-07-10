import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/providers/sync_providers.dart';
import 'package:dmrv_app/services/sync_queue_manager.dart';
import 'package:dmrv_app/ui/screens/sync_health_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';

/// Records the operator retry calls the screen issues. `extends Mock` supplies
/// `noSuchMethod` for the rest of the manager surface we never touch here.
class FakeSyncQueueManager extends Mock implements SyncQueueManager {
  final List<String> retried = [];
  int retryAllCount = 0;

  @override
  Future<void> retryPermanentlyFailed(String operationId) async =>
      retried.add(operationId);

  @override
  Future<void> retryAllPermanentlyFailed() async => retryAllCount++;
}

SyncOutboxData _stuckRow({
  String operationId = 'op-stuck-1',
  String targetTable = 'moisture_readings',
  String? failureReason = 'HTTP 422: photo_path exceeds max length',
}) => SyncOutboxData(
  operationId: operationId,
  batchUuid: 'abcd1234-0000-0000-0000-000000000000',
  targetTable: targetTable,
  operationType: 'INSERT',
  payloadJson: '{}',
  status: 'FAILED_PERMANENTLY',
  retryCount: 5,
  createdAt: '2026-07-10T08:00:00.000Z',
  lastAttemptAt: '2026-07-10T09:30:00.000Z',
  failureReason: failureReason,
);

Future<void> _pump(
  WidgetTester tester, {
  required List<SyncOutboxData> rows,
  Duration? skew,
  SyncQueueManager? manager,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        problemOutboxRowsProvider.overrideWith((ref) => Stream.value(rows)),
        syncedOutboxCountProvider.overrideWith((ref) => Stream.value(3)),
        clockSkewProvider.overrideWith((ref) => skew),
        if (manager != null) syncQueueManagerProvider.overrideWithValue(manager),
      ],
      child: const MaterialApp(home: SyncHealthScreen()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('renders a stuck row with its verbatim failure reason', (
    tester,
  ) async {
    await _pump(tester, rows: [_stuckRow()]);

    expect(find.text('Moisture reading'), findsOneWidget);
    expect(
      find.text('HTTP 422: photo_path exceeds max length'),
      findsOneWidget,
    );
    // Summary chip counts: 3 synced, 0 waiting, 1 stuck.
    expect(find.text('SYNCED'), findsOneWidget);
    // "STUCK" appears in both the summary chip and the row's status label.
    expect(find.text('STUCK'), findsNWidgets(2));
  });

  testWidgets('per-row RETRY calls retryPermanentlyFailed with the op id', (
    tester,
  ) async {
    final manager = FakeSyncQueueManager();

    await _pump(tester, rows: [_stuckRow()], manager: manager);

    await tester.tap(find.text('RETRY'));
    await tester.pump();

    expect(manager.retried, ['op-stuck-1']);
  });

  testWidgets('RETRY ALL calls retryAllPermanentlyFailed', (tester) async {
    final manager = FakeSyncQueueManager();

    await _pump(
      tester,
      rows: [_stuckRow(operationId: 'a'), _stuckRow(operationId: 'b')],
      manager: manager,
    );

    await tester.tap(find.textContaining('RETRY ALL STUCK'));
    await tester.pump();

    expect(manager.retryAllCount, 1);
  });

  testWidgets('clock-skew banner renders when the provider is set', (
    tester,
  ) async {
    await _pump(tester, rows: const [], skew: const Duration(minutes: 30));

    expect(find.text('PHONE CLOCK IS OFF'), findsOneWidget);
    expect(find.textContaining('off by 30 minutes'), findsOneWidget);
  });

  testWidgets('no banner and empty state when nothing is stuck', (
    tester,
  ) async {
    await _pump(tester, rows: const []);

    expect(find.text('PHONE CLOCK IS OFF'), findsNothing);
    expect(
      find.textContaining('Everything is synced'),
      findsOneWidget,
    );
  });
}
