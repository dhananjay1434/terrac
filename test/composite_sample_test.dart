import 'dart:convert';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/ui/screens/composite_sample_screen.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

/// P1-S5 — Rainbow C4 site composite pile sub-sample. ≥1 photographed sample is
/// required to continue; the writer must emit an outbox row on the
/// `composite_pile_samples` table carrying the batch-QR + photo hash.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Future<void> pump(WidgetTester tester, {required int count}) async {
    // Tall surface so the whole ListView (incl. the CONTINUE button) is built
    // rather than viewport-culled.
    tester.view.physicalSize = const Size(1200, 2600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          compositeSampleCountProvider.overrideWith((ref) => Stream.value(count)),
        ],
        child: const MaterialApp(home: CompositeSampleScreen()),
      ),
    );
    await tester.pumpAndSettle();
  }

  test('batchQrValue is the versioned chain-of-custody format', () {
    expect(batchQrValue('abc-123'), 'dmrv-batch:v1:abc-123');
  });

  testWidgets('CONTINUE is locked with zero samples', (tester) async {
    await pump(tester, count: 0);
    expect(find.text('LOCKED // CAPTURE ≥1 SAMPLE'), findsOneWidget);
    expect(find.text('CONTINUE TO END-USE'), findsNothing);
  });

  testWidgets('CONTINUE unlocks once at least one sample is captured', (
    tester,
  ) async {
    await pump(tester, count: 1);
    expect(find.text('CONTINUE TO END-USE'), findsOneWidget);
    expect(find.text('1'), findsWidgets); // counter hero
  });

  group('insertCompositePileSampleWithOutbox', () {
    late AppDatabase db;

    setUp(() {
      FlutterSecureStorage.setMockInitialValues({});
      db = AppDatabase.forTesting(NativeDatabase.memory());
    });

    tearDown(() async => db.close());

    test('writes a composite_pile_samples outbox row with QR + photo hash', () async {
      await db.customStatement(
        'INSERT INTO system_metadata '
        '(batch_uuid, artisan_id, device_hardware_mac, app_build_version, '
        'sync_status, created_at) '
        "VALUES ('b1','a','m','v','PENDING','2026-07-02T00:00:00Z')",
      );

      await db.insertCompositePileSampleWithOutbox(
        batchUuid: 'b1',
        sampledAt: '2026-07-02T10:00:00Z',
        latitude: 12.9,
        longitude: 77.6,
        batchQr: batchQrValue('b1'),
        photoPath: '/sandbox/sample.jpg',
        sha256Hash: 'a' * 64,
      );

      final row = await (db.select(db.syncOutbox)
            ..where((t) => t.targetTable.equals('composite_pile_samples')))
          .getSingle();
      final payload = jsonDecode(row.payloadJson) as Map<String, dynamic>;

      expect(payload['batch_qr'], 'dmrv-batch:v1:b1');
      expect(payload['sha256_hash'], 'a' * 64);
      expect(payload['photo_path'], '/sandbox/sample.jpg');
      expect(payload['latitude'], 12.9);
    });
  });
}
