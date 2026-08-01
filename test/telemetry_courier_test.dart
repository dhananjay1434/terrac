import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dmrv_app/services/crypto_signer.dart';
import 'package:dmrv_app/services/telemetry_courier.dart';
import 'package:dmrv_app/services/simulation/simulated_edge_device.dart';

class _FakeOutbox implements ChunkOutbox {
  final List<String> payloads = [];
  @override
  Future<void> enqueueTelemetryChunk(String p) async => payloads.add(p);
}
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();          // device signs via CryptoSigner → secure storage
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  test('courier drains the simulated device into the outbox', () async {
    final outbox = _FakeOutbox();
    final device = SimulatedEdgeDevice(deviceId: await CryptoSigner.getDeviceId(), sessionUuid: 'sess-demo', buckets: 2);
    final n = await TelemetryCourier(outbox).drain(device);
    expect(n, 10); // 2 buckets × 5 channels (T1..T4 + LOAD)
    expect(outbox.payloads.length, 10);
    // each enqueued payload is a complete signed envelope
    for (final p in outbox.payloads) {
      final e = jsonDecode(p) as Map<String, dynamic>;
      expect(e.containsKey('producer_signature'), isTrue);
      expect(['T1', 'T2', 'T3', 'T4', 'LOAD'].contains(e['channel']), isTrue);
    }
  });
}
