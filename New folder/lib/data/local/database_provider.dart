import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app_database.dart';

/// Global Riverpod provider exposing the singleton [AppDatabase] instance.
///
/// The provider uses `autoDispose` to mitigate a rare race condition during
/// `secureWipe` (where the DB is re-opened before storage is wiped). It ships
/// a `dispose` hook to prevent file-handle leaks.
final appDatabaseProvider = FutureProvider.autoDispose<AppDatabase>((ref) async {
  ref.keepAlive();
  final db = AppDatabase();
  ref.onDispose(db.close);
  return db;
});
