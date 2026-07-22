import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:cryptography/cryptography.dart';
import 'package:dmrv_app/services/server_signature_verifier.dart';

/// V8 Part 0.1 — app-side verification of server-signed artifacts.
/// Mirrors the backend's tests/test_server_signing.py: round-trip, tamper
/// rejection, unknown-kid handling, and the fail-closed "nothing cached yet"
/// posture. Uses the pub.dev `cryptography` package directly to generate a
/// real Ed25519 keypair + signature (no backend dependency in a Flutter test).
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  final algo = Ed25519();

  String b64u(List<int> bytes) => base64Url.encode(bytes).replaceAll('=', '');

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
  });

  test('verifyWithKeys: valid signature round-trips', () async {
    final pair = await algo.newKeyPair();
    final pub = await pair.extractPublicKey();
    final pubB64 = b64u(pub.bytes);
    final payload = utf8.encode('config-document-v1');
    final sig = await algo.sign(payload, keyPair: pair);
    final sigB64 = b64u(sig.bytes);

    final ok = await ServerSignatureVerifier.verifyWithKeys(
      payload: payload,
      signatureB64Url: sigB64,
      kid: 'sk1',
      keys: {'sk1': pubB64},
    );
    expect(ok, isTrue);
  });

  test('verifyWithKeys: tampered payload rejected', () async {
    final pair = await algo.newKeyPair();
    final pub = await pair.extractPublicKey();
    final pubB64 = b64u(pub.bytes);
    final sig = await algo.sign(utf8.encode('original'), keyPair: pair);
    final sigB64 = b64u(sig.bytes);

    final ok = await ServerSignatureVerifier.verifyWithKeys(
      payload: utf8.encode('tampered'),
      signatureB64Url: sigB64,
      kid: 'sk1',
      keys: {'sk1': pubB64},
    );
    expect(ok, isFalse);
  });

  test('verifyWithKeys: unknown kid is rejected, not thrown', () async {
    final ok = await ServerSignatureVerifier.verifyWithKeys(
      payload: utf8.encode('payload'),
      signatureB64Url: 'anything',
      kid: 'sk-nonexistent',
      keys: {'sk1': 'irrelevant'},
    );
    expect(ok, isFalse);
  });

  test('verifyWithKeys: malformed key material rejected, not thrown', () async {
    final ok = await ServerSignatureVerifier.verifyWithKeys(
      payload: utf8.encode('payload'),
      signatureB64Url: 'not-valid-base64!!!',
      kid: 'sk1',
      keys: {'sk1': 'also-not-valid-base64!!!'},
    );
    expect(ok, isFalse);
  });

  test('verify(): fails closed when nothing is cached yet', () async {
    final ok = await ServerSignatureVerifier.verify(
      payload: utf8.encode('payload'),
      signatureB64Url: 'anything',
      kid: 'sk1',
    );
    expect(ok, isFalse);
  });

  test('verify(): uses cached keyset once populated', () async {
    final pair = await algo.newKeyPair();
    final pub = await pair.extractPublicKey();
    final pubB64 = b64u(pub.bytes);
    final payload = utf8.encode('cached-keyset-payload');
    final sig = await algo.sign(payload, keyPair: pair);
    final sigB64 = b64u(sig.bytes);

    await ServerSignatureVerifier.cacheKeysForTest({'sk1': pubB64});

    final ok = await ServerSignatureVerifier.verify(
      payload: payload,
      signatureB64Url: sigB64,
      kid: 'sk1',
    );
    expect(ok, isTrue);

    await ServerSignatureVerifier.clearForTest();
    final okAfterClear = await ServerSignatureVerifier.verify(
      payload: payload,
      signatureB64Url: sigB64,
      kid: 'sk1',
    );
    expect(okAfterClear, isFalse);
  });

  test('rotation: old kid stays verifiable alongside a new kid', () async {
    final oldPair = await algo.newKeyPair();
    final newPair = await algo.newKeyPair();
    final oldPub = b64u((await oldPair.extractPublicKey()).bytes);
    final newPub = b64u((await newPair.extractPublicKey()).bytes);

    final oldPayload = utf8.encode('pre-rotation');
    final oldSig = b64u((await algo.sign(oldPayload, keyPair: oldPair)).bytes);

    await ServerSignatureVerifier.cacheKeysForTest({
      'sk1': oldPub,
      'sk2': newPub,
    });

    final newPayload = utf8.encode('post-rotation');
    final newSig = b64u((await algo.sign(newPayload, keyPair: newPair)).bytes);

    expect(
      await ServerSignatureVerifier.verify(
        payload: oldPayload,
        signatureB64Url: oldSig,
        kid: 'sk1',
      ),
      isTrue,
      reason: 'old kid must still verify after a new kid is added',
    );
    expect(
      await ServerSignatureVerifier.verify(
        payload: newPayload,
        signatureB64Url: newSig,
        kid: 'sk2',
      ),
      isTrue,
    );
  });
}
