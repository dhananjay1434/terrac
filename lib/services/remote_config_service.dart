import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'server_signature_verifier.dart';

/// V8 Part 0.4 — remote control plane: signed feature flags, kill-switch,
/// and minimum supported app version.
///
/// Consumes the backend's `GET /api/v1/config` (signed via Part 0.1's
/// Ed25519 server key). The app verifies the signature offline using
/// [ServerSignatureVerifier] before trusting ANY field — an unsigned or
/// tampered document is treated as "no remote config available" (fail-safe).
///
/// **Fail-safe posture:** if the server is unreachable OR the signature fails,
/// the last successfully verified config (cached in secure storage) is used.
/// A device that has NEVER received a valid config operates without
/// remote-config enforcement (kill-switch off, no min-version floor) — this
/// is the correct default for a field device's first offline launch.
///
/// **Pure-core split:** [RemoteConfig] is a plain data class; [parseAndVerify]
/// is a pure function (no I/O) that takes raw JSON + keys and returns either
/// a verified config or null. [fetchAndCache] is the thin I/O edge.
class RemoteConfigService {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );
  static const _configCacheKey = 'dmrv.remote_config.v1';

  // ---------------------------------------------------------------------------
  // Data class
  // ---------------------------------------------------------------------------

  /// Immutable snapshot of a verified remote config document.
  static RemoteConfig? _current;

  /// The most recently verified config, or null if none has been loaded yet.
  static RemoteConfig? get current => _current;

  // ---------------------------------------------------------------------------
  // Pure core (unit-testable without I/O)
  // ---------------------------------------------------------------------------

  /// Canonical byte representation of the signed fields — MUST exactly match
  /// the backend's `routers.config._canonical_payload`
  /// (`json.dumps(sort_keys=True, ensure_ascii=False, separators=(",",":"))`).
  ///
  /// Two subtleties that a naive implementation gets wrong (both would make
  /// the app silently reject valid configs):
  ///  1. Python `sort_keys=True` sorts keys RECURSIVELY, including the nested
  ///     `flags` map — so we sort deeply, not just the five top-level keys.
  ///  2. `ensure_ascii=False` emits raw UTF-8 for non-ASCII strings (e.g. a
  ///     Hindi kill-switch message); Dart's `jsonEncode` already does this, so
  ///     `utf8.encode(jsonEncode(...))` matches byte-for-byte.
  @visibleForTesting
  static List<int> canonicalPayload(Map<String, dynamic> signedFields) {
    final doc = <String, dynamic>{
      'flags': signedFields['flags'],
      'kill_switch': signedFields['kill_switch'],
      'message': signedFields['message'],
      'min_version': signedFields['min_version'],
      'signed_at': signedFields['signed_at'],
    };
    return utf8.encode(jsonEncode(_sortDeep(doc)));
  }

  /// Recursively rebuild [value] with every map's keys in sorted order, to
  /// mirror Python's recursive `sort_keys=True`.
  static dynamic _sortDeep(dynamic value) {
    if (value is Map) {
      final sortedKeys = value.keys.map((k) => k.toString()).toList()..sort();
      final out = <String, dynamic>{};
      for (final k in sortedKeys) {
        out[k] = _sortDeep(value[k]);
      }
      return out;
    }
    if (value is List) return value.map(_sortDeep).toList();
    return value;
  }

  /// Pure verify: given a parsed config body and an explicit keyset, checks
  /// the Ed25519 signature. Returns a [RemoteConfig] if valid, null otherwise.
  /// Never throws.
  static Future<RemoteConfig?> parseAndVerify(
    Map<String, dynamic> body,
    Map<String, String> keys,
  ) async {
    if (body['signing_configured'] != true) return null;
    final kid = body['kid'] as String?;
    final sig = body['signature'] as String?;
    if (kid == null || sig == null || kid.isEmpty || sig.isEmpty) return null;

    final signedFields = <String, dynamic>{
      'flags': body['flags'],
      'kill_switch': body['kill_switch'],
      'message': body['message'],
      'min_version': body['min_version'],
      'signed_at': body['signed_at'],
    };

    final ok = await ServerSignatureVerifier.verifyWithKeys(
      payload: canonicalPayload(signedFields),
      signatureB64Url: sig,
      kid: kid,
      keys: keys,
    );
    if (!ok) return null;

    return RemoteConfig(
      flags: (body['flags'] as Map<String, dynamic>?) ?? {},
      killSwitch: body['kill_switch'] == true,
      minVersion: body['min_version'] as String?,
      message: body['message'] as String?,
      signedAt: body['signed_at'] as String?,
    );
  }

  // ---------------------------------------------------------------------------
  // Thin I/O edge
  // ---------------------------------------------------------------------------

  /// Fetch config from the server, verify signature, cache if valid, and
  /// update [current]. Network failure or bad signature leaves the existing
  /// cache untouched (fail-safe). Never throws.
  static Future<RemoteConfig?> fetchAndCache(
    String apiBaseUrl, {
    http.Client? client,
    Map<String, String>? keysOverride,
  }) async {
    if (apiBaseUrl.isEmpty) return _current;
    final c = client ?? http.Client();
    try {
      final resp = await c
          .get(Uri.parse('$apiBaseUrl/api/v1/config'))
          .timeout(const Duration(seconds: 8));
      if (resp.statusCode != 200) return _current;

      final body = jsonDecode(resp.body) as Map<String, dynamic>;

      // Resolve keys: use override (tests) or load from cached pubkeys.
      final keys = keysOverride ?? await _loadCachedPubkeys();
      if (keys.isEmpty) return _current;

      final config = await parseAndVerify(body, keys);
      if (config == null) return _current;

      // Verified — cache and promote.
      await _storage.write(key: _configCacheKey, value: resp.body);
      _current = config;
      return config;
    } catch (e) {
      debugPrint('[RemoteConfigService] fetch failed (using cache): $e');
      return _current;
    } finally {
      if (client == null) c.close();
    }
  }

  /// Load the last verified config from secure-storage cache. Called at boot
  /// before the first network fetch so kill-switch/min-version enforcement
  /// is active even when offline. Never throws.
  static Future<RemoteConfig?> loadCached({
    Map<String, String>? keysOverride,
  }) async {
    try {
      final raw = await _storage.read(key: _configCacheKey);
      if (raw == null || raw.isEmpty) return null;

      final body = jsonDecode(raw) as Map<String, dynamic>;
      final keys = keysOverride ?? await _loadCachedPubkeys();
      if (keys.isEmpty) return null;

      final config = await parseAndVerify(body, keys);
      // Only promote a VERIFIED config. Never clobber an already-good in-memory
      // config with null (e.g. if called after a successful fetch, or if the
      // cached doc fails verification) — a verify failure must not silently
      // disarm enforcement that a prior good load established.
      if (config != null) _current = config;
      return config;
    } catch (e) {
      debugPrint('[RemoteConfigService] loadCached failed: $e');
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // Enforcement helpers
  // ---------------------------------------------------------------------------

  /// Returns true if the kill-switch is active in the current config.
  static bool get isKillSwitchActive => _current?.killSwitch ?? false;

  /// Returns the kill-switch message, if any.
  static String? get killSwitchMessage =>
      isKillSwitchActive ? _current?.message : null;

  /// Compare [currentVersion] against [minVersion]. Returns true if the app
  /// is below the minimum (must block). Null min-version = no floor = always ok.
  static bool isBelowMinVersion(String currentVersion) {
    final min = _current?.minVersion;
    if (min == null || min.isEmpty) return false;
    return _compareVersions(currentVersion, min) < 0;
  }

  /// Simple semver comparison: splits on '.', compares numerically left-to-right.
  /// Returns negative if a < b, 0 if equal, positive if a > b.
  @visibleForTesting
  static int compareVersions(String a, String b) => _compareVersions(a, b);

  static int _compareVersions(String a, String b) {
    final aParts = a.split('.').map((s) => int.tryParse(s) ?? 0).toList();
    final bParts = b.split('.').map((s) => int.tryParse(s) ?? 0).toList();
    final len = aParts.length > bParts.length ? aParts.length : bParts.length;
    for (var i = 0; i < len; i++) {
      final av = i < aParts.length ? aParts[i] : 0;
      final bv = i < bParts.length ? bParts[i] : 0;
      if (av != bv) return av - bv;
    }
    return 0;
  }

  // ---------------------------------------------------------------------------
  // Internal helpers
  // ---------------------------------------------------------------------------

  /// Resolve the server verify-set through its single owner, so the
  /// storage-key literal isn't duplicated here (a drift between the two would
  /// silently break verification).
  static Future<Map<String, String>> _loadCachedPubkeys() =>
      ServerSignatureVerifier.cachedKeys();

  // ---------------------------------------------------------------------------
  // Test helpers
  // ---------------------------------------------------------------------------

  @visibleForTesting
  static Future<void> cacheConfigForTest(String rawJson) =>
      _storage.write(key: _configCacheKey, value: rawJson);

  @visibleForTesting
  static Future<void> clearForTest() async {
    _current = null;
    await _storage.delete(key: _configCacheKey);
  }

  @visibleForTesting
  static void setCurrentForTest(RemoteConfig? config) => _current = config;
}

/// Immutable snapshot of a verified remote config document.
class RemoteConfig {
  final Map<String, dynamic> flags;
  final bool killSwitch;
  final String? minVersion;
  final String? message;
  final String? signedAt;

  const RemoteConfig({
    required this.flags,
    required this.killSwitch,
    this.minVersion,
    this.message,
    this.signedAt,
  });
}
