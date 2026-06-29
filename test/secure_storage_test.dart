import 'package:dmrv_app/data/local/passphrase_resolver.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late FlutterSecureStorage secureStorage;
  late SharedPreferences prefs;

  setUp(() async {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({});
    secureStorage = const FlutterSecureStorage();
    prefs = await SharedPreferences.getInstance();
  });

  test('test_passphrase_written_to_secure_storage_not_shared_prefs', () async {
    final passphrase = await resolveOrCreatePassphrase(
      secureStorage: secureStorage,
      prefs: prefs,
    );
    expect(passphrase, isNotEmpty);
    expect(await secureStorage.read(key: kDbPassphraseKey), equals(passphrase));
    expect(
      prefs.getString(kDbPassphraseKey),
      isNull,
      reason: 'Passphrase must NEVER be in plaintext SharedPreferences',
    );
  });

  test('test_legacy_migration_moves_key_and_deletes_plaintext', () async {
    const legacy = 'deadbeef1234567890abcdef';
    await prefs.setString(kDbPassphraseKey, legacy);

    final result = await resolveOrCreatePassphrase(
      secureStorage: secureStorage,
      prefs: prefs,
    );

    expect(result, equals(legacy));
    expect(await secureStorage.read(key: kDbPassphraseKey), equals(legacy));
    expect(
      prefs.getString(kDbPassphraseKey),
      isNull,
      reason: 'Plaintext copy must be scrubbed after migration',
    );
  });

  test('test_passphrase_is_stable_across_calls', () async {
    final first = await resolveOrCreatePassphrase(
      secureStorage: secureStorage,
      prefs: prefs,
    );
    final second = await resolveOrCreatePassphrase(
      secureStorage: secureStorage,
      prefs: prefs,
    );
    expect(
      first,
      equals(second),
      reason: 'Re-generating on every call would lock devices out of their DB',
    );
  });
}
