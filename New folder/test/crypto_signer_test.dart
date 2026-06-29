import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dmrv_app/services/crypto_signer.dart';

void main() {
  // Test flutter_secure_storage mock
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
  });

  test(
    'signPayload returns consistent 64-char hex',
    () async {
      const payload = '{"test": 123}';
      final sig1 = await CryptoSigner.signPayload(payload);
      final sig2 = await CryptoSigner.signPayload(payload);
      expect(sig1, sig2);
      expect(sig1.length, 64);
    },
  );

  test(
    'signPayload changes when payload changes',
    () async {
      const payload1 = '{"test": 123}';
      const payload2 = '{"test": 124}';
      final sig1 = await CryptoSigner.signPayload(payload1);
      final sig2 = await CryptoSigner.signPayload(payload2);
      expect(sig1, isNot(sig2));
    },
  );

  test(
    'signPayload changes when key changes',
    () async {
      const payload = '{"test": 123}';
      final sig1 = await CryptoSigner.signPayload(payload);
      await CryptoSigner.resetKeyForTesting();
      final sig2 = await CryptoSigner.signPayload(payload);
      expect(sig1, isNot(sig2));
    },
  );
}
