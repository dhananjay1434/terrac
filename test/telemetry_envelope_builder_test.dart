import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:crypto/crypto.dart';
import 'package:dmrv_app/services/telemetry_canonical.dart';
import 'package:dmrv_app/services/telemetry_envelope_builder.dart';
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();          // builder → CryptoSigner → secure storage
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  test('canonical excludes producer_signature and matches golden shape', () async {
    final c = await TelemetryEnvelopeBuilder.build(deviceId: 'edge-001', sessionUuid: 'sess-0001', batchUuid: null, channel: 'T1', tStartIso: '2026-07-23T09:00:00Z', samplePeriodS: 10.0, values: [412.5, 418.0, 421.2], seq: 0, prevHash: 'GENESIS');
    final canon = canonicalJson(c.envelope);
    expect(canon, isNot(contains('producer_signature')));
    expect(canon.startsWith('{"batch_uuid":null,"channel":"T1"'), isTrue);
  });
  test('chain links: nextPrevHash == sha256(canonical)', () async {
    final c = await TelemetryEnvelopeBuilder.build(deviceId: 'edge-001', sessionUuid: 'sess-0001', batchUuid: null, channel: 'T1', tStartIso: '2026-07-23T09:00:00Z', samplePeriodS: 10.0, values: [400.0], seq: 0, prevHash: 'GENESIS');
    expect(c.nextPrevHash, sha256.convert(utf8.encode(canonicalJson(c.envelope))).toString());
  });
}
