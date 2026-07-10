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
    // P1-C6: read-back-VERIFY before scrubbing the only other copy. On some
    // OEMs a secure-storage write reports success but doesn't persist; scrubbing
    // SharedPreferences then would lose the passphrase entirely and leave the
    // SQLCipher DB permanently unreadable. Only scrub once the write is proven;
    // otherwise keep the prefs copy and retry the migration on the next launch.
    final check = await secureStorage.read(key: kDbPassphraseKey);
    if (check == legacy) {
      await prefs.remove(kDbPassphraseKey);
      await prefs.reload(); // P1-22: Force synchronous flush on iOS
      debugPrint('[DB] plaintext passphrase scrubbed from SharedPreferences.');
    } else {
      debugPrint(
        '[DB] secure-storage write NOT verified — keeping SharedPreferences '
        'copy; will retry migration next launch.',
      );
    }
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
  // P1-C6: verify the key actually persisted before the DB is opened/encrypted
  // under it. A silent write failure here would create a database that can
  // never be decrypted again — fail loudly instead.
  final check = await secureStorage.read(key: kDbPassphraseKey);
  if (check != passphrase) {
    throw StateError(
      'Secure storage did not persist the DB passphrase; refusing to open an '
      'unrecoverable encrypted database.',
    );
  }
  debugPrint('[DB] new passphrase generated and written to secure storage.');
  return passphrase;
}
