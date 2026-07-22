import 'dart:convert';

import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/services/sync_queue_manager.dart';
import 'package:drift/native.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

/// V8 Part 2 — the farmer onboarding flow enqueues a registration to the sync
/// outbox (→ POST /api/v1/farmers). These assert the app→server contract: the
/// outbox row targets `farmers`, carries the structured fields, masks the
/// account on-device (no full number), and claims NO media it can't upload.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('insertFarmerWithOutbox', () {
    late AppDatabase db;

    setUp(() {
      FlutterSecureStorage.setMockInitialValues({});
      db = AppDatabase.forTesting(NativeDatabase.memory());
    });
    tearDown(() async => db.close());

    Future<Map<String, dynamic>> enqueuedPayload() async {
      final row = await (db.select(
        db.syncOutbox,
      )..where((t) => t.targetTable.equals('farmers'))).getSingle();
      return jsonDecode(row.payloadJson) as Map<String, dynamic>;
    }

    test('routes to the /farmers endpoint', () {
      expect(kEndpointByTable['farmers'], 'farmers');
    });

    test('enqueues the structured farmer fields', () async {
      await db.insertFarmerWithOutbox(
        farmerUuid: 'farmer-uuid-000000000000000000000001',
        projectId: 'proj-1',
        firstName: 'Asha',
        lastName: 'Devi',
        mobileNumber: '9990001111',
        village: 'Rampur',
        kycStatus: 'self_declared',
        consentStatus: 'acknowledged',
        consents: [
          {'exclusivity_ack': true},
        ],
      );

      final payload = await enqueuedPayload();
      expect(payload['farmer_uuid'], 'farmer-uuid-000000000000000000000001');
      expect(payload['project_id'], 'proj-1');
      expect(payload['first_name'], 'Asha');
      expect(payload['mobile_number'], '9990001111');
      expect(payload['village'], 'Rampur');
      expect(payload['consent_status'], 'acknowledged');
      expect((payload['consents'] as List).first['exclusivity_ack'], true);
      // No media-backed documents are claimed in the MVP.
      expect(payload['documents'], isEmpty);
    });

    test('the account number is masked in the payload (no full number)', () async {
      await db.insertFarmerWithOutbox(
        farmerUuid: 'farmer-uuid-000000000000000000000002',
        projectId: 'proj-1',
        firstName: 'Asha',
        mobileNumber: '9990002222',
        payments: [
          {
            'rail': 'bank',
            'account_holder': 'Asha Devi',
            // NOTE: the SCREEN masks before calling this method; here we assert
            // the payload only ever carries a masked value, never a raw number.
            'masked_account': 'XXXXXXXX9012',
            'ifsc_code': 'HDFC0001234',
          },
        ],
      );

      final payload = await enqueuedPayload();
      final pay = (payload['payments'] as List).first as Map<String, dynamic>;
      expect(pay['masked_account'], 'XXXXXXXX9012');
      // The masked value must contain a mask char and not be a bare long number
      // (mirrors the server's masked-field guard).
      expect(RegExp(r'^\d+$').hasMatch(pay['masked_account'] as String), isFalse);
    });
  });
}
