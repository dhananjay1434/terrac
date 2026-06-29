import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/crypto_signer.dart';
import 'package:dmrv_app/services/device_integrity_service.dart';

void main() {
  test('CryptoSigner throws Exception when device is compromised globally', () async {
    // Reset global state
    isDeviceCompromisedGlobally = false;
    
    // Ensure the key exists for the test to get past that check if we didn't throw early
    // But since it throws early, we don't strictly need a valid key unless it resolves first.
    // Let's test the early throw.
    
    // Act & Assert for signPayload
    // We expect an exception when isDeviceCompromisedGlobally = true
    isDeviceCompromisedGlobally = true;
    
    expect(
      () => CryptoSigner.signPayload('{}'),
      throwsException,
      reason: 'Should block payload signing if device compromised',
    );

    expect(
      () => CryptoSigner.signRequest(
        method: 'POST',
        path: '/api',
        idempotencyKey: 'idemp',
        deviceId: 'dev',
        jsonBody: '{}',
      ),
      throwsException,
      reason: 'Should block request signing if device compromised',
    );
  });
}
