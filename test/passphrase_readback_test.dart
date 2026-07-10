import 'package:dmrv_app/data/local/passphrase_resolver.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// P1-C6 — the passphrase migration must never scrub the last copy. If a
/// secure-storage write silently doesn't persist (a known OEM behaviour),
/// scrubbing SharedPreferences would brick the SQLCipher DB forever.
class _MockStorage extends Mock implements FlutterSecureStorage {}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('migration scrubs prefs only after a verified read-back', () async {
    final store = <String, String?>{};
    final storage = _MockStorage();
    when(
      () => storage.read(key: any(named: 'key')),
    ).thenAnswer((i) async => store[i.namedArguments[#key]]);
    when(
      () => storage.write(key: any(named: 'key'), value: any(named: 'value')),
    ).thenAnswer((i) async {
      store[i.namedArguments[#key]] = i.namedArguments[#value] as String?;
    });

    SharedPreferences.setMockInitialValues({kDbPassphraseKey: 'legacy-pass'});
    final prefs = await SharedPreferences.getInstance();

    final result = await resolveOrCreatePassphrase(
      secureStorage: storage,
      prefs: prefs,
    );
    expect(result, 'legacy-pass');
    expect(prefs.getString(kDbPassphraseKey), isNull, reason: 'prefs scrubbed');
  });

  test('migration keeps the prefs copy when the write does NOT persist',
      () async {
    final storage = _MockStorage();
    // read always null → the write silently dropped (OEM bug).
    when(() => storage.read(key: any(named: 'key'))).thenAnswer((_) async => null);
    when(
      () => storage.write(key: any(named: 'key'), value: any(named: 'value')),
    ).thenAnswer((_) async {});

    SharedPreferences.setMockInitialValues({kDbPassphraseKey: 'legacy-pass'});
    final prefs = await SharedPreferences.getInstance();

    final result = await resolveOrCreatePassphrase(
      secureStorage: storage,
      prefs: prefs,
    );
    expect(result, 'legacy-pass', reason: 'app still resolves this run');
    expect(
      prefs.getString(kDbPassphraseKey),
      'legacy-pass',
      reason: 'the only surviving copy must NOT be scrubbed',
    );
  });

  test('fresh generation throws if the write is not persisted', () async {
    final storage = _MockStorage();
    when(() => storage.read(key: any(named: 'key'))).thenAnswer((_) async => null);
    when(
      () => storage.write(key: any(named: 'key'), value: any(named: 'value')),
    ).thenAnswer((_) async {});

    SharedPreferences.setMockInitialValues({}); // no legacy value
    final prefs = await SharedPreferences.getInstance();

    expect(
      () => resolveOrCreatePassphrase(secureStorage: storage, prefs: prefs),
      throwsA(isA<StateError>()),
    );
  });
}
