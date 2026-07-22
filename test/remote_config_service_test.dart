import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:cryptography/cryptography.dart';
import 'package:dmrv_app/services/remote_config_service.dart';
import 'package:dmrv_app/services/server_signature_verifier.dart';

/// V8 Part 0.4 — remote control plane: Flutter-side tests.
///
/// Covers: signed config round-trip, tampered config rejected, kill-switch
/// enforcement, min-version enforcement, fail-safe (unreachable → last cached
/// config used), and the dormant-by-default posture (no cached config ⇒ no
/// enforcement).
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  final algo = Ed25519();

  String b64u(List<int> bytes) => base64Url.encode(bytes).replaceAll('=', '');

  /// Generate a signed config document matching the backend's format.
  Future<Map<String, dynamic>> makeSignedConfig({
    required SimpleKeyPair keyPair,
    required String kid,
    Map<String, dynamic>? flags,
    bool killSwitch = false,
    String? minVersion,
    String? message,
  }) async {
    final signedFields = <String, dynamic>{
      'flags': flags ?? {},
      'kill_switch': killSwitch,
      'message': message,
      'min_version': minVersion,
      'signed_at': DateTime.now().toIso8601String(),
    };
    final payload = RemoteConfigService.canonicalPayload(signedFields);
    final sig = await algo.sign(payload, keyPair: keyPair);
    return {
      ...signedFields,
      'signing_configured': true,
      'kid': kid,
      'signature': b64u(sig.bytes),
    };
  }

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    RemoteConfigService.clearForTest();
  });

  // -------------------------------------------------------------------------
  // parseAndVerify — pure core tests
  // -------------------------------------------------------------------------

  test('parseAndVerify: valid signed config round-trips', () async {
    final pair = await algo.newKeyPair();
    final pub = b64u((await pair.extractPublicKey()).bytes);
    final body = await makeSignedConfig(
      keyPair: pair,
      kid: 'sk1',
      flags: {'boundary_v2': true},
      minVersion: '1.4.0',
    );

    final config = await RemoteConfigService.parseAndVerify(
      body,
      {'sk1': pub},
    );
    expect(config, isNotNull);
    expect(config!.flags['boundary_v2'], isTrue);
    expect(config.minVersion, '1.4.0');
    expect(config.killSwitch, isFalse);
  });

  test('parseAndVerify: tampered config rejected', () async {
    final pair = await algo.newKeyPair();
    final pub = b64u((await pair.extractPublicKey()).bytes);
    final body = await makeSignedConfig(
      keyPair: pair,
      kid: 'sk1',
      killSwitch: false,
    );

    // Tamper: flip kill_switch after signing
    body['kill_switch'] = true;

    final config = await RemoteConfigService.parseAndVerify(
      body,
      {'sk1': pub},
    );
    expect(config, isNull, reason: 'tampered document must be rejected');
  });

  test('parseAndVerify: unsigned config (signing_configured=false) rejected',
      () async {
    final config = await RemoteConfigService.parseAndVerify(
      {'signing_configured': false, 'flags': {}, 'kill_switch': false},
      {'sk1': 'irrelevant'},
    );
    expect(config, isNull);
  });

  test('parseAndVerify: unknown kid rejected', () async {
    final pair = await algo.newKeyPair();
    final pub = b64u((await pair.extractPublicKey()).bytes);
    final body = await makeSignedConfig(
      keyPair: pair,
      kid: 'sk1',
    );

    final config = await RemoteConfigService.parseAndVerify(
      body,
      {'sk-other': pub}, // key exists but under a different kid
    );
    expect(config, isNull);
  });

  // -------------------------------------------------------------------------
  // Kill-switch enforcement
  // -------------------------------------------------------------------------

  test('kill-switch: active when config says so', () async {
    RemoteConfigService.setCurrentForTest(const RemoteConfig(
      flags: {},
      killSwitch: true,
      message: 'Emergency maintenance.',
    ));
    expect(RemoteConfigService.isKillSwitchActive, isTrue);
    expect(RemoteConfigService.killSwitchMessage, 'Emergency maintenance.');
  });

  test('kill-switch: inactive by default (no config)', () {
    expect(RemoteConfigService.isKillSwitchActive, isFalse);
    expect(RemoteConfigService.killSwitchMessage, isNull);
  });

  // -------------------------------------------------------------------------
  // Min-version enforcement
  // -------------------------------------------------------------------------

  test('min-version: below floor blocks', () async {
    RemoteConfigService.setCurrentForTest(const RemoteConfig(
      flags: {},
      killSwitch: false,
      minVersion: '2.0.0',
    ));
    expect(RemoteConfigService.isBelowMinVersion('1.9.0'), isTrue);
    expect(RemoteConfigService.isBelowMinVersion('2.0.0'), isFalse);
    expect(RemoteConfigService.isBelowMinVersion('2.0.1'), isFalse);
  });

  test('min-version: no floor = always ok', () {
    RemoteConfigService.setCurrentForTest(const RemoteConfig(
      flags: {},
      killSwitch: false,
    ));
    expect(RemoteConfigService.isBelowMinVersion('0.0.1'), isFalse);
  });

  // -------------------------------------------------------------------------
  // Version comparison
  // -------------------------------------------------------------------------

  test('compareVersions: basic semver ordering', () {
    expect(RemoteConfigService.compareVersions('1.0.0', '1.0.0'), 0);
    expect(RemoteConfigService.compareVersions('1.0.0', '2.0.0'), isNegative);
    expect(RemoteConfigService.compareVersions('2.0.0', '1.0.0'), isPositive);
    expect(RemoteConfigService.compareVersions('1.0.9', '1.1.0'), isNegative);
    expect(RemoteConfigService.compareVersions('1.10.0', '1.9.0'), isPositive);
    expect(RemoteConfigService.compareVersions('1.0', '1.0.0'), 0);
  });

  // -------------------------------------------------------------------------
  // Cache + fail-safe
  // -------------------------------------------------------------------------

  test('loadCached: returns null when nothing is cached', () async {
    final config = await RemoteConfigService.loadCached(keysOverride: {});
    expect(config, isNull);
    expect(RemoteConfigService.current, isNull);
  });

  test('loadCached: valid cached config is loaded and verified', () async {
    final pair = await algo.newKeyPair();
    final pub = b64u((await pair.extractPublicKey()).bytes);
    final body = await makeSignedConfig(
      keyPair: pair,
      kid: 'sk1',
      killSwitch: true,
      message: 'Cached kill-switch.',
    );

    await RemoteConfigService.cacheConfigForTest(jsonEncode(body));
    await ServerSignatureVerifier.cacheKeysForTest({'sk1': pub});

    final config = await RemoteConfigService.loadCached(
      keysOverride: {'sk1': pub},
    );
    expect(config, isNotNull);
    expect(config!.killSwitch, isTrue);
    expect(config.message, 'Cached kill-switch.');
    expect(RemoteConfigService.current, isNotNull);
  });

  test('loadCached: tampered cached config is rejected', () async {
    final pair = await algo.newKeyPair();
    final pub = b64u((await pair.extractPublicKey()).bytes);
    final body = await makeSignedConfig(
      keyPair: pair,
      kid: 'sk1',
      killSwitch: false,
    );
    // Tamper the cached version
    body['kill_switch'] = true;
    await RemoteConfigService.cacheConfigForTest(jsonEncode(body));

    final config = await RemoteConfigService.loadCached(
      keysOverride: {'sk1': pub},
    );
    expect(config, isNull,
        reason: 'tampered cache must be rejected, not trusted');
  });

  // -------------------------------------------------------------------------
  // Fail-safe: no enforcement when unconfigured
  // -------------------------------------------------------------------------

  test('dormant by default: no config = no enforcement', () {
    expect(RemoteConfigService.current, isNull);
    expect(RemoteConfigService.isKillSwitchActive, isFalse);
    expect(RemoteConfigService.isBelowMinVersion('0.0.1'), isFalse);
  });

  // -------------------------------------------------------------------------
  // Cross-language canonical contract (mirrors backend
  // tests/test_remote_config.py::test_canonical_payload_is_ascii_free_...).
  // The other tests sign and verify with the SAME Dart canonical, so they'd
  // pass even if it disagreed with Python. This pins the exact bytes Python's
  // json.dumps(sort_keys=True, ensure_ascii=False, separators=(",",":"))
  // produces, so a regression (ASCII-escaping, or non-recursive sorting of the
  // nested flags map) fails HERE instead of silently disabling the fleet's
  // kill-switch in production.
  // -------------------------------------------------------------------------

  test('canonicalPayload matches Python bytes for non-ASCII + multi-flag', () {
    final signedFields = <String, dynamic>{
      // Deliberately out of order (b before a) and a non-ASCII message.
      'flags': {'b_flag': true, 'a_flag': false},
      'kill_switch': true,
      'message': 'चेतावनी',
      'min_version': '1.2.0',
      'signed_at': '2026-07-22T00:00:00+00:00',
    };
    const expected =
        '{"flags":{"a_flag":false,"b_flag":true},"kill_switch":true,'
        '"message":"चेतावनी","min_version":"1.2.0",'
        '"signed_at":"2026-07-22T00:00:00+00:00"}';
    expect(
      utf8.decode(RemoteConfigService.canonicalPayload(signedFields)),
      expected,
    );
  });

  test('loadCached: a bad cache does NOT clobber an already-good config',
      () async {
    // Establish a good, verified in-memory config through the real path.
    final pair = await algo.newKeyPair();
    final pub = b64u((await pair.extractPublicKey()).bytes);
    final good = await makeSignedConfig(
      keyPair: pair,
      kid: 'sk1',
      killSwitch: true,
      message: 'Good config.',
    );
    await RemoteConfigService.cacheConfigForTest(jsonEncode(good));
    await ServerSignatureVerifier.cacheKeysForTest({'sk1': pub});
    final loaded =
        await RemoteConfigService.loadCached(keysOverride: {'sk1': pub});
    expect(loaded, isNotNull);
    expect(RemoteConfigService.isKillSwitchActive, isTrue);

    // Now a tampered cache load returns null — but must NOT disarm the
    // enforcement the good load already established.
    final tampered = Map<String, dynamic>.from(good)..['kill_switch'] = false;
    await RemoteConfigService.cacheConfigForTest(jsonEncode(tampered));
    final rejected =
        await RemoteConfigService.loadCached(keysOverride: {'sk1': pub});
    expect(rejected, isNull, reason: 'tampered cache must not verify');
    expect(
      RemoteConfigService.isKillSwitchActive,
      isTrue,
      reason: 'a failed re-load must not silently disarm the kill-switch',
    );
  });
}
