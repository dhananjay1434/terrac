import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/services/demo_telemetry_wire.dart';
import 'package:drift/native.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

Future<List<SyncOutboxData>> v2Rows(AppDatabase db) => (db.select(
  db.syncOutbox,
)..where((t) => t.operationType.equals('TELEMETRY_V2_CHUNK'))).get();

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late AppDatabase db;

  setUp(() async {
    // Pre-enrolled so startDemoTelemetry signs without a network round-trip.
    FlutterSecureStorage.setMockInitialValues({
      'device_enrolled': '1',
      'device_id_key': 'edge-demo-001',
    });
    db = AppDatabase.forTesting(NativeDatabase.memory());
  });
  tearDown(() => db.close());

  test(
    'flag OFF (default in tests): maybeStartDemoTelemetry produces zero v2 rows',
    () async {
      await maybeStartDemoTelemetry(db: db, sessionUuid: 'sess-demo-off');
      expect(await v2Rows(db), isEmpty);
    },
  );

  test(
    'ON path (provably correct even though it ships behind the flag today): '
    'startDemoTelemetry enqueues signed T1 + LOAD chunks, dual-run safe',
    () async {
      await startDemoTelemetry(db: db, sessionUuid: 'sess-demo-on');
      final rows = await v2Rows(db);
      expect(rows, isNotEmpty);
      expect(
        rows.any((r) => r.payloadJson.contains('"channel":"T1"')),
        isTrue,
      );
      expect(
        rows.any((r) => r.payloadJson.contains('"channel":"LOAD"')),
        isTrue,
      );
      // dual-run: nothing here touches pyrolysis_telemetry (the legacy write
      // lives entirely in pyrolysis_screen.dart's _endBurn, untouched by P16).
    },
  );
}
