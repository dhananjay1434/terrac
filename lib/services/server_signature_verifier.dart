import 'dart:convert';
import 'package:cryptography/cryptography.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

/// V8 Part 0.1 — verifies signatures made by the SERVER's Ed25519 signing key
/// (opposite direction from [CryptoSigner], which signs on-device). Two future
/// consumers share this: Part 0.4's signed remote-config document and Part 1's
/// signed field-walk link.
///
/// Design mirrors the pure-core/thin-edge split from the production execution
/// plan: [verifyWithKeys] is a pure function (no I/O) so it is unit-testable in
/// isolation; [verify] is the thin edge that resolves the current keyset from
/// secure-storage cache and calls it.
class ServerSignatureVerifier {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );
  static const _keysStorageKey = 'dmrv.server_pubkeys.v1';
  static final _algo = Ed25519();

  static String _pad(String s) {
    while (s.length % 4 != 0) {
      s += '=';
    }
    return s;
  }

  /// Pure verify: given an explicit kid->base64url-pubkey map, checks
  /// [signatureB64Url] over [payload] under [kid]. Returns false (never
  /// throws) for an unknown kid, a malformed key/signature, or a genuine
  /// mismatch — callers cannot distinguish "tampered" from "misconfigured"
  /// by design, since both must be treated as untrusted.
  static Future<bool> verifyWithKeys({
    required List<int> payload,
    required String signatureB64Url,
    required String kid,
    required Map<String, String> keys,
  }) async {
    final pubB64 = keys[kid];
    if (pubB64 == null || pubB64.isEmpty) return false;
    try {
      final pubBytes = base64Url.decode(_pad(pubB64));
      final sigBytes = base64Url.decode(_pad(signatureB64Url));
      final publicKey = SimplePublicKey(pubBytes, type: KeyPairType.ed25519);
      final signature = Signature(sigBytes, publicKey: publicKey);
      return await _algo.verify(payload, signature: signature);
    } catch (e) {
      // Malformed base64/key length etc. is indistinguishable from tamper —
      // reject, don't crash the caller.
      debugPrint('[ServerSignatureVerifier] verify error (rejecting): $e');
      return false;
    }
  }

  /// Thin edge: verify against the currently cached keyset (from the last
  /// successful [refreshFromServer]). Returns false if nothing is cached yet
  /// — a device that has never synced pubkeys cannot verify anything, which
  /// is the correct fail-closed posture for a signature check.
  static Future<bool> verify({
    required List<int> payload,
    required String signatureB64Url,
    required String kid,
  }) async {
    final keys = await _loadCachedKeys();
    if (keys.isEmpty) return false;
    return verifyWithKeys(
      payload: payload,
      signatureB64Url: signatureB64Url,
      kid: kid,
      keys: keys,
    );
  }

  static Future<Map<String, String>> _loadCachedKeys() async {
    final raw = await _storage.read(key: _keysStorageKey);
    if (raw == null || raw.isEmpty) return {};
    try {
      final decoded = jsonDecode(raw);
      if (decoded is Map) {
        return decoded.map((k, v) => MapEntry(k.toString(), v.toString()));
      }
    } catch (_) {
      // Corrupt cache — treat as empty rather than crashing a verify call.
    }
    return {};
  }

  /// Fetch the verify-set from `GET /api/v1/pubkeys` and cache it. Network
  /// failure or `signing_configured: false` leaves the existing cache
  /// untouched (fail-safe: a device that once had a good keyset keeps it
  /// rather than being blanked by a transient outage). Never throws.
  static Future<void> refreshFromServer(
    String apiBaseUrl, {
    http.Client? client,
  }) async {
    if (apiBaseUrl.isEmpty) return;
    final c = client ?? http.Client();
    try {
      final resp = await c
          .get(Uri.parse('$apiBaseUrl/api/v1/pubkeys'))
          .timeout(const Duration(seconds: 8));
      if (resp.statusCode != 200) return;
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      if (body['signing_configured'] != true) return;
      final keys = (body['keys'] as Map<String, dynamic>?) ?? {};
      // Never overwrite a known-good cached keyset with an empty one: a
      // degenerate 200 (signing_configured:true but keys:{}) would otherwise
      // blank the cache and make every signature verification fail closed
      // until the next good fetch. A missing key is worse than a stale one.
      if (keys.isEmpty) return;
      await _storage.write(
        key: _keysStorageKey,
        value: jsonEncode(keys.map((k, v) => MapEntry(k, v.toString()))),
      );
    } catch (e) {
      debugPrint('[ServerSignatureVerifier] refresh failed (using cache): $e');
    } finally {
      if (client == null) c.close();
    }
  }

  /// The currently cached verify-set (kid -> base64url pubkey), or empty if
  /// none. Public so other verifiers (e.g. RemoteConfigService) resolve keys
  /// through this single owner rather than duplicating the storage-key literal.
  static Future<Map<String, String>> cachedKeys() => _loadCachedKeys();

  @visibleForTesting
  static Future<void> cacheKeysForTest(Map<String, String> keys) =>
      _storage.write(key: _keysStorageKey, value: jsonEncode(keys));

  @visibleForTesting
  static Future<void> clearForTest() => _storage.delete(key: _keysStorageKey);
}
