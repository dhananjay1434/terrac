import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

const kDbPassphraseKey = 'dmrv.db.passphrase.v1';

/// Resolves or creates the SQLCipher DB passphrase.
/// Extracted as a standalone testable function — both [app_database.dart]
/// and the test suite import THIS function. Tests therefore exercise the
/// exact production logic, not a copy.
Future<String> resolveOrCreatePassphrase({
  required FlutterSecureStorage secureStorage,
  required SharedPreferences prefs,
}) async {
  final existing = await secureStorage.read(key: kDbPassphraseKey);
  if (existing != null && existing.isNotEmpty) {
    debugPrint('[DB] passphrase resolved from secure storage.');
    return existing;
  }

  final legacy = prefs.getString(kDbPassphraseKey);
  if (legacy != null && legacy.isNotEmpty) {
    debugPrint('[DB] migrating passphrase SharedPreferences → secure storage.');
    await secureStorage.write(key: kDbPassphraseKey, value: legacy);
    await prefs.remove(kDbPassphraseKey);
    await prefs.reload(); // P1-22: Force synchronous flush on iOS
    debugPrint('[DB] plaintext passphrase scrubbed from SharedPreferences.');
    return legacy;
  }

  Random rng;
  try {
    rng = Random.secure();
  } catch (e) {
    throw UnsupportedError('Platform lacks a secure entropy source for PRNG.');
  }
  
  final bytes = List<int>.generate(32, (_) => rng.nextInt(256));
  final passphrase = base64Url.encode(bytes);
  await secureStorage.write(key: kDbPassphraseKey, value: passphrase);
  debugPrint('[DB] new passphrase generated and written to secure storage.');
  return passphrase;
}
