import 'dart:convert';
import 'dart:math';
import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:uuid/uuid.dart';
import 'package:http/http.dart' as http;
import 'device_integrity_service.dart';

/// A stateless utility class that generates HMAC-SHA256 signatures for payloads.
/// The signing key is persisted securely in the device Keystore.
class CryptoSigner {
  static const _storage = FlutterSecureStorage();
  static const _keyName = 'hmac_signing_key';
  static const _deviceIdName = 'device_id_key';

  static Future<List<int>>? _keyFuture;
  static Future<String>? _deviceIdFuture;

  static Future<List<int>> _resolveKey() {
    return _keyFuture ??= _readOrCreateOnce();
  }

  static Future<String> _resolveDeviceId() {
    return _deviceIdFuture ??= _readOrCreateDeviceIdOnce();
  }

  static Future<List<int>> _readOrCreateOnce() async {
    final existingKey = await _storage.read(key: _keyName);
    if (existingKey != null) {
      String padded = existingKey;
      while (padded.length % 4 != 0) {
        padded += '=';
      }
      try {
        return base64Url.decode(padded);
      } catch (e) {
        // Fallback for legacy hex keys, though we assume a clean slate
      }
    }
    Random random;
    try {
      random = Random.secure();
    } catch (e) {
      throw UnsupportedError('Platform lacks a secure entropy source for PRNG.');
    }
    // 32 bytes
    final keyBytes = List<int>.generate(32, (_) => random.nextInt(256));
    final b64Key = base64Url.encode(keyBytes).replaceAll('=', '');
    await _storage.write(key: _keyName, value: b64Key);
    return keyBytes;
  }

  static Future<String> _readOrCreateDeviceIdOnce() async {
    final existingId = await _storage.read(key: _deviceIdName);
    if (existingId != null) {
      return existingId;
    }
    final newId = const Uuid().v4();
    await _storage.write(key: _deviceIdName, value: newId);
    return newId;
  }

  static Future<void> warmUp() async {
    await _resolveKey();
    await _resolveDeviceId();
    await registerDevice();
  }

  static Future<void> registerDevice() async {
    final deviceId = await _resolveDeviceId();
    final keyBytes = await _resolveKey();
    final hmacKey = base64Url.encode(keyBytes).replaceAll('=', '');

    // For testing/development, we use a placeholder token or read from env
    final enrollmentToken = const String.fromEnvironment('ENROLLMENT_TOKEN', defaultValue: 'dev-token');
    final apiBaseUrl = const String.fromEnvironment('DMRV_API_BASE_URL', defaultValue: 'http://10.0.2.2:8000');

    try {
      final response = await http.post(
        Uri.parse('$apiBaseUrl/api/v1/register'),
        headers: {
          'Content-Type': 'application/json',
          'X-Enrollment-Token': enrollmentToken,
        },
        body: jsonEncode({
          'device_id': deviceId,
          'hmac_key': hmacKey,
        }),
      );
      if (response.statusCode != 201) {
        debugPrint('Failed to register device: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error registering device: $e');
    }
  }

  static Future<String> getDeviceId() async {
    return await _resolveDeviceId();
  }

  static Future<String> signPayload(String jsonPayload) async {
    if (isDeviceCompromisedGlobally) throw Exception('Device compromised');
    final keyBytes = await _resolveKey();
    final hmac = Hmac(sha256, keyBytes);
    final digest = hmac.convert(utf8.encode(jsonPayload));
    return digest.toString();
  }

  static Future<String> signRequest({
    required String method,
    required String path,
    required String idempotencyKey,
    required String deviceId,
    required String jsonBody,
  }) async {
    if (isDeviceCompromisedGlobally) throw Exception('Device compromised');
    final keyBytes = await _resolveKey();
    final hmac = Hmac(sha256, keyBytes);
    final bodySha = sha256.convert(utf8.encode(jsonBody)).toString();
    final canonical = '$method\n$path\n$idempotencyKey\n$bodySha\n$deviceId';
    final digest = hmac.convert(utf8.encode(canonical));
    return digest.toString();
  }

  static Future<void> clear() async {
    _keyFuture = null;
    _deviceIdFuture = null;
    await _storage.delete(key: _keyName);
    await _storage.delete(key: _deviceIdName);
  }

  static Future<void> resetKeyForTesting() => clear();

  @visibleForTesting
  static void resetForTest() {
    _keyFuture = null;
    _deviceIdFuture = null;
  }
}