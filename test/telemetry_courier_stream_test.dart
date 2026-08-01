import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dmrv_app/services/telemetry_courier.dart';
import 'package:dmrv_app/services/simulation/burn_profile.dart';
import 'package:dmrv_app/services/simulation/demo_clock.dart';
import 'package:dmrv_app/services/simulation/simulated_edge_device.dart';
class _FakeOutbox implements ChunkOutbox {
  final List<String> payloads = [];
  @override
  Future<void> enqueueTelemetryChunk(String p) async => payloads.add(p);
}
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  test('drainStream enqueues every chunk (all durable when the Future completes)', () async {
    final outbox = _FakeOutbox();
    final dev = SimulatedEdgeDevice(
      deviceId: 'edge-x',
      sessionUuid: 'sess-stream',
      profile: const BurnProfile(DemoProfile(bucketCount: 3, accelerationFactor: 100000)),
      clock: FakeDemoClock(),
    );
    final n = await TelemetryCourier(outbox).drainStream(dev.stream());
    expect(n, 6); // 3 buckets × 2 channels
    expect(outbox.payloads.length, 6);
    for (final p in outbox.payloads) {
      final e = jsonDecode(p) as Map<String, dynamic>;
      expect(e.containsKey('producer_signature'), isTrue);
      expect(['T1', 'LOAD'].contains(e['channel']), isTrue);
    }
  });
}
