import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:cryptography/cryptography.dart';
import 'package:dmrv_app/services/crypto_signer.dart';
import 'package:dmrv_app/services/telemetry_canonical.dart';
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();          // CryptoSigner uses secure storage
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  test('signBytesB64 verifies against the device public key', () async {
    final env = <String, dynamic>{'device_id': 'edge-001','session_uuid':'sess-0001','batch_uuid':null,'channel':'T1','t_start':'2026-07-23T09:00:00Z','sample_period_s':10.0,'values':<double>[412.5,418.0,421.2],'seq':0,'prev_hash':'GENESIS'};
    final canonical = utf8.encode(canonicalJson(env));
    final sigB64 = await CryptoSigner.signBytesB64(canonical);
    final pub = SimplePublicKey(base64Url.decode(_pad(await CryptoSigner.publicKeyB64())), type: KeyPairType.ed25519);
    final ok = await Ed25519().verify(canonical, signature: Signature(base64Url.decode(_pad(sigB64)), publicKey: pub));
    expect(ok, isTrue);
  });
}
String _pad(String b) { final m = b.length % 4; return m == 0 ? b : b + '=' * (4 - m); }
