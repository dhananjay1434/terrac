import 'dart:convert';

import 'package:drift/native.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dmrv_app/data/local/app_database.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late AppDatabase db;

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    db = AppDatabase.forTesting(NativeDatabase.memory());
  });

  tearDown(() async {
    await db.close();
  });

  test('insertWithOutbox generates HMAC signature', () async {
    final batchUuid = 'test-batch-uuid';
    final payload = {'test': 'data'};

    await db.insertWithOutbox(
      batchUuid: batchUuid,
      targetTable: 'system_metadata',
      payload: payload,
      insertRow: () async {
        // mock row insertion
      },
    );

    final outboxEntries = await db.select(db.syncOutbox).get();
    expect(outboxEntries.length, 1);

    final entry = outboxEntries.first;
    expect(entry.payloadJson, jsonEncode(payload));
    expect(entry.hmacSignature, isNot(null));
    expect(entry.hmacSignature, isNotEmpty);
  });
}
