import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dmrv_app/services/crypto_signer.dart';
import 'package:dmrv_app/services/device_integrity_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    isDeviceCompromisedGlobally = false;
  });

  // V7 P1: the RASP package identity MUST match the real Android applicationId,
  // or freerasp's repackaging check hard-locks the app on every install.
  test('RASP android package matches build.gradle.kts applicationId', () {
    final gradle = File(
      'android/app/build.gradle.kts',
    ).readAsStringSync();
    final match = RegExp(r'applicationId\s*=\s*"([^"]+)"').firstMatch(gradle);
    expect(match, isNotNull, reason: 'applicationId not found in build.gradle.kts');
    final applicationId = match!.group(1);
    expect(
      kReleaseAndroidPackage,
      applicationId,
      reason:
          'freerasp AndroidConfig.packageName ($kReleaseAndroidPackage) must equal '
          'the release applicationId ($applicationId) or the app self-bricks.',
    );
  });

  // V7 P1: private B2B distribution is sideload/MDM, never a store — a non-store
  // installer must NOT hard-lock, while every real tamper vector still does.
  test('onUnofficialStore is log-only; real threats still hard-lock', () {
    final src = File(
      'lib/services/device_integrity_service.dart',
    ).readAsStringSync();

    // onUnofficialStore must NOT route to _compromised.
    final unofficialLine = RegExp(r'onUnofficialStore:\s*\(\)\s*=>\s*([^\n,]+)')
        .firstMatch(src);
    expect(unofficialLine, isNotNull);
    expect(
      unofficialLine!.group(1)!.contains('_compromised'),
      isFalse,
      reason: 'onUnofficialStore must be log-only for private distribution',
    );

    // The genuine tamper vectors MUST still hard-lock via _compromised.
    for (final cb in [
      'onPrivilegedAccess',
      'onHooks',
      'onDebug',
      'onSimulator',
      'onAppIntegrity',
      'onDeviceBinding',
    ]) {
      expect(
        RegExp('$cb:\\s*\\(\\)\\s*=>\\s*_compromised').hasMatch(src),
        isTrue,
        reason: '$cb must still route to _compromised (fail-closed)',
      );
    }
  });

  test(
    'CryptoSigner throws StateError when device is compromised globally',
    () async {
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
        throwsStateError,
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
        throwsStateError,
        reason: 'Should block request signing if device compromised',
      );
    },
  );

  test(
    'initialize() is a no-op in debug/test mode and does not mark compromised',
    () async {
      // Phase 6: under `flutter test` kDebugMode is true, so initialize() must
      // take the demo/debug skip branch — without touching Talsec and without
      // flipping the compromised flag.
      final container = ProviderContainer();
      addTearDown(container.dispose);
      final service = container.read(deviceIntegrityServiceProvider);

      await service.initialize();

      expect(isDeviceCompromisedGlobally, isFalse);
      expect(container.read(deviceCompromisedProvider), isFalse);
    },
  );

  test(
    'source fails CLOSED: forbids demo in release; requires integrity config; isProd not tied to debug',
    () {
      // Phase 6: the release path cannot be exercised under `flutter test`
      // (kReleaseMode is always false here), so lock the fail-closed guards in
      // at the source level — the same style as device_integrity_enforcement_test.
      final content = File(
        'lib/services/device_integrity_service.dart',
      ).readAsStringSync();

      expect(
        content.contains('forbidden in release builds'),
        isTrue,
        reason: 'release builds with DMRV_DEMO_MODE must throw',
      );
      expect(
        content.contains("_compromised('Integrity configuration missing')"),
        isTrue,
        reason: 'missing TALSEC config in release must fail closed',
      );
      expect(
        content.contains("_compromised('Talsec failed to start:"),
        isTrue,
        reason: 'Talsec start failure must fail closed, not be swallowed',
      );
      expect(
        content.contains('isProd: true'),
        isTrue,
        reason: 'release integrity must run in prod mode',
      );
      expect(
        content.contains('isProd: !kDebugMode'),
        isFalse,
        reason: 'isProd must not be derived from the debug flag',
      );
    },
  );
}
