import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secure-storage key holding the operator-entered API base URL (P1-S8). Set at
/// enrollment; read on every launch so the device talks to the right backend
/// without a compile-time `--dart-define`.
const kApiBaseUrlKey = 'dmrv.api.base_url.v1';

const _envApiBase = String.fromEnvironment(
  'DMRV_API_BASE_URL',
  defaultValue: '',
);

const _secureStorage = FlutterSecureStorage(
  aOptions: AndroidOptions(encryptedSharedPreferences: true),
);

/// THE single base-URL resolver, used by both enrollment/signing and sync:
/// the enrolled secure-storage value wins; the `DMRV_API_BASE_URL` dart-define
/// is the fallback (dev/CI). Returns '' when neither is set.
Future<String> resolveApiBaseUrl({FlutterSecureStorage? storage}) async {
  final s = storage ?? _secureStorage;
  final stored = await s.read(key: kApiBaseUrlKey);
  if (stored != null && stored.isNotEmpty) return stored;
  return _envApiBase;
}

/// Persist the operator-entered base URL so future launches (and sync) use it.
Future<void> persistApiBaseUrl(String url, {FlutterSecureStorage? storage}) {
  final s = storage ?? _secureStorage;
  return s.write(key: kApiBaseUrlKey, value: url);
}

/// The live API base URL for this session. Seeded at startup (main.dart) from
/// [resolveApiBaseUrl] and updated on successful enrollment, so `syncConfigProvider`
/// reacts without a restart. Defaults to the dart-define value.
final apiBaseUrlProvider = StateProvider<String>((ref) => _envApiBase);
