import 'dart:convert';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/services/sync_queue_manager.dart';
import 'package:drift/native.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

/// V8 Part 3.4 — dispatch draft creation enqueues to the sync outbox
/// (→ POST /api/v1/dispatch). Mirrors farmer_outbox_test.dart's contract-test
/// style: assert the exact shape the server's DispatchCreate schema expects.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('insertDispatchWithOutbox', () {
    late AppDatabase db;

    setUp(() {
      FlutterSecureStorage.setMockInitialValues({});
      db = AppDatabase.forTesting(NativeDatabase.memory());
    });
    tearDown(() async => db.close());

    Future<Map<String, dynamic>> enqueuedPayload() async {
      final row = await (db.select(
        db.syncOutbox,
      )..where((t) => t.targetTable.equals('dispatches'))).getSingle();
      return jsonDecode(row.payloadJson) as Map<String, dynamic>;
    }

    test('routes to the /dispatch endpoint', () {
      expect(kEndpointByTable['dispatches'], 'dispatch');
    });

    test('enqueues the structured dispatch fields', () async {
      await db.insertDispatchWithOutbox(
        dispatchUuid: 'dispatch-uuid-0000000000000000000001',
        kind: 'biomass',
        destFacilityUuid: 'facility-uuid-1',
        weightSourceKg: 250.0,
        weightSourceMethod: 'platform_scale',
        driverName: 'Ramesh',
        driverPhone: '9998887777',
        truckNumber: 'DL01AB1234',
      );

      final payload = await enqueuedPayload();
      expect(payload['dispatch_uuid'], 'dispatch-uuid-0000000000000000000001');
      expect(payload['kind'], 'biomass');
      expect(payload['dest_facility_uuid'], 'facility-uuid-1');
      expect(payload['weight_source_kg'], 250.0);
      expect(payload['weight_source_method'], 'platform_scale');
      expect(payload['driver_name'], 'Ramesh');
      expect(payload['truck_number'], 'DL01AB1234');
    });

    test('omitting optional fields leaves them null (not fabricated)', () async {
      await db.insertDispatchWithOutbox(
        dispatchUuid: 'dispatch-uuid-0000000000000000000002',
        kind: 'biochar',
      );

      final payload = await enqueuedPayload();
      expect(payload['weight_source_kg'], isNull);
      expect(payload['dest_facility_uuid'], isNull);
      expect(payload['driver_name'], isNull);
      expect(payload['sites'], isEmpty);
    });
  });
}
