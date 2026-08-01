import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:crypto/crypto.dart';
import 'package:cryptography/cryptography.dart';
import 'package:dmrv_app/services/crypto_signer.dart';
import 'package:dmrv_app/services/telemetry_canonical.dart';
import 'package:dmrv_app/services/simulation/burn_profile.dart';
import 'package:dmrv_app/services/simulation/demo_clock.dart';
import 'package:dmrv_app/services/simulation/simulated_edge_device.dart';
String _pad(String b) { final m = b.length % 4; return m == 0 ? b : b + '=' * (4 - m); }
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();          // device signs via CryptoSigner → secure storage
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  test('simulated burn emits signed, chained, verifiable T1 + LOAD chunks', () async {
    final fixedStart = DateTime.utc(2026, 8, 1, 9, 1); // 09:01:00 → burn ENDS here
    final dev = SimulatedEdgeDevice(
      deviceId: await CryptoSigner.getDeviceId(),
      sessionUuid: 'sess-demo',
      profile: const BurnProfile(DemoProfile()),
      clock: FakeDemoClock(startedAt: fixedStart),
      buckets: 6,
    );
    final chunks = await dev.collect();
    expect(chunks.length, 12); // 6 buckets × 2 channels (T1 + LOAD)
    // every chunk verifies against the device key
    final pub = SimplePublicKey(base64Url.decode(_pad(await CryptoSigner.publicKeyB64())), type: KeyPairType.ed25519);
    for (final c in chunks) {
      final canonical = utf8.encode(canonicalJson(c.envelope));
      final ok = await Ed25519().verify(canonical, signature: Signature(base64Url.decode(_pad(c.envelope['producer_signature'] as String)), publicKey: pub));
      expect(ok, isTrue);
    }
    final t1 = chunks.where((c) => c.envelope['channel'] == 'T1').toList();
    final load = chunks.where((c) => c.envelope['channel'] == 'LOAD').toList();
    expect(t1.length, 6); expect(load.length, 6);
    // hash chain: T1 seq1.prev_hash == sha256(canonical of T1 seq0); seq0 is GENESIS
    expect(t1[0].envelope['prev_hash'], 'GENESIS');
    expect(t1[1].envelope['prev_hash'], sha256.convert(utf8.encode(canonicalJson(t1[0].envelope))).toString());
    // temperature climbs past 350 by the end of the burn; load settles at 15.2
    expect((t1.last.envelope['values'] as List).first, greaterThan(350.0));
    expect((load.last.envelope['values'] as List).first, closeTo(15.2, 1e-9));
    // now-relative + backward-anchored: bucket 5 (last) ENDS at startedAt (09:01:00),
    // earlier buckets step back by 10s each. NONE is the old hardcoded July date.
    expect(t1[0].envelope['t_start'], startsWith('2026-08-01T09:00:10'));
    expect(t1[1].envelope['t_start'], startsWith('2026-08-01T09:00:20'));
    expect(t1.last.envelope['t_start'], startsWith('2026-08-01T09:01:00'));
  });
}
