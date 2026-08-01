import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dmrv_app/services/crypto_signer.dart';
import 'package:dmrv_app/services/ble_temperature_service.dart';
import 'package:dmrv_app/services/simulation/burn_profile.dart';
import 'package:dmrv_app/services/simulation/demo_clock.dart';
import 'package:dmrv_app/services/simulation/simulated_edge_device.dart';
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  test('signed producer T1..T4 values ARE the BurnProfile curve (one source)', () async {
    const profile = BurnProfile(DemoProfile());
    final dev = SimulatedEdgeDevice(
      deviceId: await CryptoSigner.getDeviceId(),
      sessionUuid: 'sess-recon',
      profile: profile,
      clock: FakeDemoClock(startedAt: DateTime.utc(2026, 8, 1, 9)),
      buckets: 8,
    );
    final chunks = await dev.collect();
    for (final probe in profile.profile.probes) {
      final series = chunks.where((c) => c.envelope['channel'] == probe.channel).toList();
      for (var b = 0; b < series.length; b++) {
        final signed = (series[b].envelope['values'] as List).first as double;
        final expected = profile.sampleProbe(probe, Duration(seconds: b * profile.profile.bucketSeconds));
        expect(signed, closeTo(expected, 1e-9), reason: '${probe.channel} bucket $b');
      }
    }
  });
  test('on-phone plateau + load cannot drift from the signed profile', () {
    const p = DemoProfile();
    // temperature plateau: the on-phone adapter and the signed profile share 420.
    final adapter = VirtualBleAdapter(tickInterval: const Duration(milliseconds: 10));
    expect(adapter.targetPlateau, p.plateauC);
    // load: the signed LOAD channel and the on-phone weight mock share loadKg.
    expect(p.loadKg, 15.2);
  });
}
