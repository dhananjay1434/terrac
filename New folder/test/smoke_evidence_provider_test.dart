// ignore_for_file: avoid_print, unnecessary_string_escapes
import 'package:drift/native.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/data/local/database_provider.dart';
import 'package:dmrv_app/data/local/pyrolysis_writer.dart';
import 'package:dmrv_app/providers/batch_session_notifier.dart';
import 'package:dmrv_app/providers/smoke_evidence_provider.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late AppDatabase db;
  late ProviderContainer container;

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    db = AppDatabase.forTesting(NativeDatabase.memory());
    container = ProviderContainer(
      overrides: [appDatabaseProvider.overrideWith((ref) => Future.value(db))],
    );
  });

  tearDown(() {
    container.dispose();
    db.close();
  });

  test('smokeEvidenceProvider returns empty list initially', () async {
    // Set a batch session
    container.read(batchSessionProvider.notifier).state = 'batch-123';

    // Read the stream
    final stream = container.read(smokeEvidenceProvider.future);
    final results = await stream;
    expect(results, isEmpty);
  });

  test('smokeEvidenceProvider yields inserted smoke captures', () async {
    const batchId = 'batch-123';
    container.read(batchSessionProvider.notifier).state = batchId;

    // Listen to the stream
    final capturesFuture = container.read(smokeEvidenceProvider.future);

    // Insert a capture
    await db.insertMediaCaptureAndEnqueue(
      batchUuid: batchId,
      captureType: 'smoke_0',
      sandboxPath: '/path/0',
      sha256Hash: 'hash0',
      isMockLocation: false,
    );

    // Await stream output
    final captures = await capturesFuture;
    expect(captures.length, 1);
    expect(captures.first.captureType, 'smoke_0');

    // Insert another capture
    await db.insertMediaCaptureAndEnqueue(
      batchUuid: batchId,
      captureType: 'smoke_50',
      sandboxPath: '/path/50',
      sha256Hash: 'hash50',
      isMockLocation: false,
    );

    // Refresh and check again
    // Riverpod StreamProvider will emit a new list, we can listen to it.
    final sub = container.listen(smokeEvidenceProvider, (_, next) {});

    // Give drift a microtask to update the stream
    await Future.delayed(Duration.zero);

    final updatedList = container.read(smokeEvidenceProvider).value ?? [];
    expect(updatedList.length, 2);
    expect(updatedList[0].captureType, 'smoke_0');
    expect(updatedList[1].captureType, 'smoke_50');

    sub.close();
  });

  test('smokeEvidenceProvider ignores non-smoke media', () async {
    const batchId = 'batch-123';
    container.read(batchSessionProvider.notifier).state = batchId;

    await db.insertMediaCaptureAndEnqueue(
      batchUuid: batchId,
      captureType: 'moisture', // non-smoke
      sandboxPath: '/path/m',
      sha256Hash: 'hashm',
      isMockLocation: false,
    );

    final sub = container.listen(smokeEvidenceProvider, (_, next) {});
    await Future.delayed(Duration.zero);

    final results = container.read(smokeEvidenceProvider).value ?? [];
    expect(results, isEmpty);
    sub.close();
  });
}
