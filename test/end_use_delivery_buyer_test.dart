import 'dart:convert';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/data/local/yield_end_use_writers.dart';
import 'package:dmrv_app/ui/screens/end_use_application_screen.dart';
import 'package:drift/native.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

/// P1-S6 — Rainbow C5 delivery record + buyer identity on the End-Use screen.
/// The commit gate now also requires a buyer name and a positive delivered
/// amount (≤ yield); the writer must serialize the four fields with the exact
/// snake_case keys the server's ApplicationPayload expects.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  // Everything-else-satisfied baseline; each case perturbs one input.
  bool commit({
    bool hasMethod = true,
    bool tonnageValid = true,
    bool transportValid = true,
    bool hasGps = true,
    bool hasPhoto = true,
    String buyerName = 'Asha Farmer Collective',
    double? deliveredKg = 42.5,
    double? wetYieldKg = 100,
  }) => endUseCanCommit(
    hasMethod: hasMethod,
    tonnageValid: tonnageValid,
    transportValid: transportValid,
    hasGps: hasGps,
    hasPhoto: hasPhoto,
    buyerName: buyerName,
    deliveredKg: deliveredKg,
    wetYieldKg: wetYieldKg,
  );

  group('endUseCanCommit', () {
    test('passes when every field including delivery + buyer is present', () {
      expect(commit(), isTrue);
    });

    test('blocked when the buyer name is missing or blank', () {
      expect(commit(buyerName: ''), isFalse);
      expect(commit(buyerName: '   '), isFalse);
    });

    test('blocked when there is no positive delivered amount', () {
      expect(commit(deliveredKg: null), isFalse);
      expect(commit(deliveredKg: 0), isFalse);
      expect(commit(deliveredKg: -5), isFalse);
    });

    test('blocked when delivered amount exceeds the recorded yield', () {
      expect(commit(deliveredKg: 150, wetYieldKg: 100), isFalse);
      expect(commit(deliveredKg: 100, wetYieldKg: 100), isTrue);
    });

    test('delivered amount allowed when yield is unknown', () {
      expect(commit(deliveredKg: 9999, wetYieldKg: null), isTrue);
    });

    test('still requires the pre-existing gps + photo + method fields', () {
      expect(commit(hasGps: false), isFalse);
      expect(commit(hasPhoto: false), isFalse);
      expect(commit(hasMethod: false), isFalse);
    });
  });

  group('insertEndUseWithOutbox payload', () {
    late AppDatabase db;

    setUp(() {
      FlutterSecureStorage.setMockInitialValues({});
      db = AppDatabase.forTesting(NativeDatabase.memory());
    });

    tearDown(() async => db.close());

    test('serializes delivery + buyer with the server field names', () async {
      await db.customStatement(
        'INSERT INTO system_metadata '
        '(batch_uuid, artisan_id, device_hardware_mac, app_build_version, '
        'sync_status, created_at) '
        "VALUES ('b1','a','m','v','PENDING','2026-07-02T00:00:00Z')",
      );

      await db.insertEndUseWithOutbox(
        batchUuid: 'b1',
        applicationMethodology: 'SURFACE_BROADCAST',
        applicationRateTonnes: 1.0,
        transportDistanceKm: 0.0,
        latitude: 1.0,
        longitude: 2.0,
        deliveryDate: '2026-07-02T10:00:00Z',
        deliveredAmountKg: 42.5,
        buyerName: 'Asha Farmer Collective',
        buyerContact: '+91-99999-00000',
      );

      final row = await (db.select(
        db.syncOutbox,
      )..where((t) => t.targetTable.equals('end_use_application'))).getSingle();
      final payload = jsonDecode(row.payloadJson) as Map<String, dynamic>;

      expect(payload['delivery_date'], '2026-07-02T10:00:00Z');
      expect(payload['delivered_amount_kg'], 42.5);
      expect(payload['buyer_name'], 'Asha Farmer Collective');
      expect(payload['buyer_contact'], '+91-99999-00000');
    });

    test('stamps capture_type=end_use so the farmer photo is classified at source', () async {
      await db.customStatement(
        'INSERT INTO system_metadata '
        '(batch_uuid, artisan_id, device_hardware_mac, app_build_version, '
        'sync_status, created_at) '
        "VALUES ('b2','a','m','v','PENDING','2026-07-02T00:00:00Z')",
      );

      await db.insertEndUseWithOutbox(
        batchUuid: 'b2',
        applicationMethodology: 'SURFACE_BROADCAST',
        applicationRateTonnes: 1.0,
        transportDistanceKm: 0.0,
        latitude: 1.0,
        longitude: 2.0,
        farmerPhotoPath: '/sandbox/farmer.jpg',
        farmerPhotoSha256: 'a' * 64,
      );

      final row = await (db.select(
        db.syncOutbox,
      )..where((t) => t.targetTable.equals('end_use_application'))).getSingle();
      final payload = jsonDecode(row.payloadJson) as Map<String, dynamic>;

      expect(payload['capture_type'], 'end_use');
    });
  });
}
