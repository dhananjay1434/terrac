import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:cryptography/cryptography.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dmrv_app/services/crypto_signer.dart';

String _pad(String s) {
  while (s.length % 4 != 0) {
    s += '=';
  }
  return s;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final algo = Ed25519();

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    CryptoSigner.resetForTest();
  });

  test('signPayload is deterministic for a fixed key (Ed25519)', () async {
    const payload = '{"test": 123}';
    final s1 = await CryptoSigner.signPayload(payload);
    final s2 = await CryptoSigner.signPayload(payload);
    expect(s1, s2); // Ed25519 is deterministic: same key + message => same sig.
    expect(s1, isNotEmpty);
  });

  test('signature changes when any canonical component changes', () async {
    Future<String> sign({
      String method = 'POST',
      String path = '/api/v1/telemetry',
      String op = 'op-1',
      String dev = 'dev-1',
      String body = '{"t":1}',
    }) => CryptoSigner.signRequest(
      method: method,
      path: path,
      idempotencyKey: op,
      deviceId: dev,
      jsonBody: body,
    );

    final base = await sign();
    expect(base, isNot(await sign(body: '{"t":2}')));
    expect(base, isNot(await sign(path: '/api/v1/yield')));
    expect(base, isNot(await sign(op: 'op-2')));
    expect(base, isNot(await sign(dev: 'dev-2')));
    expect(base, isNot(await sign(method: 'PUT')));
  });

  test(
    'public key verifies a genuine signature and rejects a tampered body',
    () async {
      const method = 'POST';
      const path = '/api/v1/telemetry';
      const op = 'op-1';
      const dev = 'dev-1';
      const body = '{"t":1}';

      final sigB64 = await CryptoSigner.signRequest(
        method: method,
        path: path,
        idempotencyKey: op,
        deviceId: dev,
        jsonBody: body,
      );

      final pub = SimplePublicKey(
        base64Url.decode(_pad(await CryptoSigner.publicKeyB64())),
        type: KeyPairType.ed25519,
      );

      String canonical(String b) {
        final h = sha256.convert(utf8.encode(b)).toString();
        return '$method\n$path\n$op\n$h\n$dev';
      }

      final sig = Signature(base64Url.decode(_pad(sigB64)), publicKey: pub);

      expect(
        await algo.verify(utf8.encode(canonical(body)), signature: sig),
        isTrue,
      );
      expect(
        await algo.verify(utf8.encode(canonical('{"t":999}')), signature: sig),
        isFalse,
      );
    },
  );

  test('signRequestV2 binds a timestamp and verifies against the v2 canonical',
      () async {
    const method = 'POST';
    const path = '/api/v1/telemetry';
    const op = 'op-1';
    const dev = 'dev-1';
    const body = '{"t":1}';

    final (sigB64, signedAt) = await CryptoSigner.signRequestV2(
      method: method,
      path: path,
      idempotencyKey: op,
      deviceId: dev,
      jsonBody: body,
    );

    // signedAt is a plausible unix-seconds string.
    final ts = int.parse(signedAt);
    expect(ts, greaterThan(1000000000));

    final pub = SimplePublicKey(
      base64Url.decode(_pad(await CryptoSigner.publicKeyB64())),
      type: KeyPairType.ed25519,
    );
    final h = sha256.convert(utf8.encode(body)).toString();
    final canonicalV2 = '$method\n$path\n$op\n$h\n$dev\n$signedAt';
    final sig = Signature(base64Url.decode(_pad(sigB64)), publicKey: pub);
    expect(
      await algo.verify(utf8.encode(canonicalV2), signature: sig),
      isTrue,
    );
    // The v1 canonical (no timestamp) must NOT verify the v2 signature.
    final canonicalV1 = '$method\n$path\n$op\n$h\n$dev';
    expect(
      await algo.verify(utf8.encode(canonicalV1), signature: sig),
      isFalse,
    );
  });
}
