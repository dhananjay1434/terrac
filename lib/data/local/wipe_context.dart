import 'dart:io';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';

import '../../services/crypto_signer.dart';

/// Side-effects required by [AppDatabase.secureWipe]. Production callers use
/// [ProductionWipeContext]; tests can substitute a fake.
abstract class WipeContext {
  Future<Directory> getDocsDir();
  Future<void> deleteSecureKey(String key);
  Future<void> clearHmacKey();
}

class ProductionWipeContext implements WipeContext {
  const ProductionWipeContext();

  static const _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  @override
  Future<Directory> getDocsDir() => getApplicationDocumentsDirectory();

  @override
  Future<void> deleteSecureKey(String key) => _secureStorage.delete(key: key);

  @override
  Future<void> clearHmacKey() => CryptoSigner.clear();
}

final wipeContextProvider = Provider<WipeContext>(
  (ref) => const ProductionWipeContext(),
);
