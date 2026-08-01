import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:cryptography/cryptography.dart';
import 'package:dmrv_app/services/crypto_signer.dart';
import 'package:dmrv_app/services/telemetry_canonical.dart';
import 'package:dmrv_app/services/telemetry_envelope_builder.dart';
import 'package:dmrv_app/services/ble_frame.dart';
import 'package:dmrv_app/services/ble_sync_transport.dart';
List<Uint8List> _frames(int chunkId, Uint8List p, {int maxLen = 8}) {
  final parts = <List<int>>[];
  for (var i = 0; i < p.length; i += maxLen) parts.add(p.sublist(i, (i + maxLen).clamp(0, p.length)));
  return [for (var i = 0; i < parts.length; i++) DmrvFrame(msgType: 2, chunkId: chunkId, packetIndex: i, totalPackets: parts.length, payload: Uint8List.fromList(parts[i])).encode()];
}
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();          // builder + publicKeyB64 → secure storage
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  test('produce → frame → reassemble → parse → verify, in-process', () async {
    final chunk = await TelemetryEnvelopeBuilder.build(deviceId: 'edge-001', sessionUuid: 'sess-0001', batchUuid: null, channel: 'T1', tStartIso: '2026-07-23T09:00:00Z', samplePeriodS: 10.0, values: [412.5, 418.0, 421.2], seq: 0, prevHash: 'GENESIS');
    final wire = Uint8List.fromList(utf8.encode(jsonEncode(chunk.envelope)));
    final r = ChunkReassembler(); Uint8List? whole;
    for (final pkt in _frames(1, wire)) whole = r.offer(pkt) ?? whole;
    expect(whole, isNotNull);
    final got = jsonDecode(utf8.decode(whole!)) as Map<String, dynamic>;
    final canonical = utf8.encode(canonicalJson(got));
    final pub = SimplePublicKey(base64Url.decode(_pad(await CryptoSigner.publicKeyB64())), type: KeyPairType.ed25519);
    final ok = await Ed25519().verify(canonical, signature: Signature(base64Url.decode(_pad(got['producer_signature'] as String)), publicKey: pub));
    expect(ok, isTrue, reason: 'reassembled envelope must verify against the device key');
  });
}
String _pad(String b) { final m = b.length % 4; return m == 0 ? b : b + '=' * (4 - m); }
