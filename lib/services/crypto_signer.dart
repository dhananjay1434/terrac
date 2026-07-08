import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:cryptography/cryptography.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:uuid/uuid.dart';
import 'package:http/http.dart' as http;
import 'device_integrity_service.dart';

/// Ed25519 device identity. The PRIVATE seed never leaves the device;
/// only the PUBLIC key is enrolled with the server. This restores true
/// non-repudiation — the server cannot forge a client signature.
class CryptoSigner {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );
  static const _seedKey = 'ed25519_seed';
  static const _deviceIdKey = 'device_id_key';
  static final _algo = Ed25519();

  static SimpleKeyPair? _pair;
  static String? _deviceId;

  static Future<SimpleKeyPair> _keyPair() async {
    if (_pair != null) return _pair!;
    final stored = await _storage.read(key: _seedKey);
    if (stored != null) {
      _pair = await _algo.newKeyPairFromSeed(base64Url.decode(_pad(stored)));
      return _pair!;
    }
    final pair = await _algo.newKeyPair();
    final seed = await pair.extractPrivateKeyBytes();
    await _storage.write(
      key: _seedKey,
      value: base64Url.encode(seed).replaceAll('=', ''),
    );
    _pair = pair;
    return pair;
  }

  static String _pad(String s) {
    while (s.length % 4 != 0) {
      s += '=';
    }
    return s;
  }

  static Future<String> getDeviceId() async {
    if (_deviceId != null) return _deviceId!;
    final existing = await _storage.read(key: _deviceIdKey);
    if (existing != null) {
      _deviceId = existing;
      return existing;
    }
    final id = const Uuid().v4();
    await _storage.write(key: _deviceIdKey, value: id);
    _deviceId = id;
    return id;
  }

  static Future<String> publicKeyB64() async {
    final pub = await (await _keyPair()).extractPublicKey();
    return base64Url.encode(pub.bytes).replaceAll('=', '');
  }

  static Future<void> warmUp() async {
    await _keyPair();
    await getDeviceId();
    await registerDevice();
  }

  static Future<void> registerDevice() async {
    final deviceId = await getDeviceId();
    final publicKey = await publicKeyB64();
    const enrollmentToken = String.fromEnvironment('ENROLLMENT_TOKEN');
    if (enrollmentToken.isEmpty) {
      throw StateError(
        'ENROLLMENT_TOKEN is required; pass via --dart-define-from-file=secrets.json.',
      );
    }
    const apiBaseUrl = String.fromEnvironment('DMRV_API_BASE_URL');
    if (apiBaseUrl.isEmpty) {
      throw StateError('DMRV_API_BASE_URL is required.');
    }
    final response = await http.post(
      Uri.parse('$apiBaseUrl/api/v1/register'),
      headers: {
        'Content-Type': 'application/json',
        'X-Enrollment-Token': enrollmentToken,
      },
      body: jsonEncode({'device_id': deviceId, 'public_key': publicKey}),
    );
    if (response.statusCode != 201 && response.statusCode != 409) {
      throw StateError(
        'Device registration failed: ${response.statusCode} ${response.body}',
      );
    }
  }

  /// CANONICAL STRING (frozen): method\npath\nidempotencyKey\nsha256(jsonBody)\ndeviceId
  static Future<String> signRequest({
    required String method,
    required String path,
    required String idempotencyKey,
    required String deviceId,
    required String jsonBody,
  }) async {
    if (isDeviceCompromisedGlobally) throw StateError('device_compromised');
    final bodySha = sha256.convert(utf8.encode(jsonBody)).toString();
    final canonical = '$method\n$path\n$idempotencyKey\n$bodySha\n$deviceId';
    final sig = await _algo.sign(
      utf8.encode(canonical),
      keyPair: await _keyPair(),
    );
    return base64Url.encode(sig.bytes).replaceAll('=', '');
  }

  /// T2.3 replay protection — v2 request canonical binds a client unix timestamp:
  ///   method\npath\nidempotencyKey\nsha256(jsonBody)\ndeviceId\nsignedAt
  /// The server (verify_signature, X-Canonical-Version: 2) rejects requests
  /// outside its skew window, so a captured request cannot be replayed forever.
  /// Returns (signature, signedAt) — send signedAt as the X-Signed-At header.
  static Future<(String, String)> signRequestV2({
    required String method,
    required String path,
    required String idempotencyKey,
    required String deviceId,
    required String jsonBody,
  }) async {
    if (isDeviceCompromisedGlobally) throw StateError('device_compromised');
    final signedAt =
        (DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000).toString();
    final bodySha = sha256.convert(utf8.encode(jsonBody)).toString();
    final canonical =
        '$method\n$path\n$idempotencyKey\n$bodySha\n$deviceId\n$signedAt';
    final sig = await _algo.sign(
      utf8.encode(canonical),
      keyPair: await _keyPair(),
    );
    return (base64Url.encode(sig.bytes).replaceAll('=', ''), signedAt);
  }

  /// CANONICAL STRING (frozen, media): the multipart body is not byte-reproducible,
  /// so we sign the DECLARED file hash instead of sha256(body). MUST byte-match the
  /// server's verify_media_signature:
  ///   POST\n/api/v1/media\n{idempotencyKey}\n{declaredSha256Lower}\n{batchUuid}\n{deviceId}
  static Future<String> signMediaUpload({
    required String idempotencyKey,
    required String declaredSha256,
    required String batchUuid,
    required String deviceId,
  }) async {
    if (isDeviceCompromisedGlobally) throw StateError('device_compromised');
    final canonical =
        'POST\n/api/v1/media\n$idempotencyKey\n'
        '${declaredSha256.toLowerCase()}\n$batchUuid\n$deviceId';
    final sig = await _algo.sign(
      utf8.encode(canonical),
      keyPair: await _keyPair(),
    );
    return base64Url.encode(sig.bytes).replaceAll('=', '');
  }

  /// Local-only tamper-evidence for the outbox row. NOT sent to the server as proof.
  static Future<String> signPayload(String jsonPayload) async {
    if (isDeviceCompromisedGlobally) throw StateError('device_compromised');
    final sig = await _algo.sign(
      utf8.encode(jsonPayload),
      keyPair: await _keyPair(),
    );
    return base64Url.encode(sig.bytes).replaceAll('=', '');
  }

  static Future<void> clear() async {
    _pair = null;
    _deviceId = null;
    await _storage.delete(key: _seedKey);
    await _storage.delete(key: _deviceIdKey);
  }

  @visibleForTesting
  static void resetForTest() {
    _pair = null;
    _deviceId = null;
  }

  static Future<void> resetKeyForTesting() => clear();
}
