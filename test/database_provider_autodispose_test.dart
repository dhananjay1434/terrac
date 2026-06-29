// =====================================================================
// P2-1 — appDatabaseProvider must be autoDispose (with keepAlive()).
// =====================================================================
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('appDatabaseProvider declared with autoDispose and keepAlive', () {
    final f = File('lib/data/local/database_provider.dart');
    expect(f.existsSync(), isTrue);
    final src = f.readAsStringSync();
    expect(src.contains('FutureProvider.autoDispose'), isTrue,
        reason: 'Switch to FutureProvider.autoDispose. See /app/detailed.md#P2-1.');
    expect(src.contains('ref.keepAlive()'), isTrue,
        reason: 'Call ref.keepAlive() inside the autoDispose provider.');
  });
}
