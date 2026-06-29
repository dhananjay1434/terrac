// =====================================================================
// P1-16 — Every Outbox writer must sign INSIDE a transaction.
//
// This is a static-analysis style test: it greps the source rather than
// driving the DB. We accept a small false-positive risk in exchange for
// future-proofing.
// =====================================================================
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('CryptoSigner.signPayload calls are physically inside transaction blocks',
      () {
    final libDir = Directory('lib');
    final offenders = <String>[];

    for (final entity in libDir.listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith('.dart')) continue;
      final source = entity.readAsStringSync();
      if (!source.contains('CryptoSigner.signPayload')) continue;

      // Find each occurrence and walk back to the nearest enclosing
      // `transaction((` or `async {`. Cheap heuristic: the substring
      // from the last `transaction(` to the signPayload call should not
      // be interrupted by a top-level closing brace.
      final idx = source.indexOf('CryptoSigner.signPayload');
      final before = source.substring(0, idx);
      final lastTxn = before.lastIndexOf('transaction(');
      final lastClose = before.lastIndexOf('});');
      if (lastTxn < 0 || lastTxn < lastClose) {
        offenders.add('${entity.path}:'
            'CryptoSigner.signPayload not enclosed in transaction((){})');
      }
    }
    expect(
      offenders,
      isEmpty,
      reason: 'See /app/detailed.md#P1-16. Offenders:\n${offenders.join('\n')}',
    );
  });
}
