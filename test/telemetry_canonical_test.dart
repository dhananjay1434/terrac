import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/telemetry_canonical.dart';

void main() {
  // Un-skip this group when canonicalJson is implemented (STITCHING Phase F).
  group('telemetry canonical bytes match backend golden vectors', skip: 'canonicalizer not implemented yet (STITCHING Phase F)', () {
    test('every committed vector reproduces byte-for-byte', () {
      final file = File('test/golden_vectors.json');
      final vectors = jsonDecode(file.readAsStringSync()) as List<dynamic>;
      expect(vectors, isNotEmpty);
      for (final v in vectors) {
        final envelope = Map<String, dynamic>.from(v['envelope'] as Map);
        final expectedHex = v['canonical_hex'] as String;
        final actualHex =
            utf8.encode(canonicalJson(envelope)).map((b) => b.toRadixString(16).padLeft(2, '0')).join();
        expect(actualHex, expectedHex, reason: 'canonical bytes drifted for $envelope');
      }
    });
  });
}
