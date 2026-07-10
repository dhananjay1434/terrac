import 'package:dmrv_app/ui/screens/pyrolysis_screen.dart';
import 'package:flutter_test/flutter_test.dart';

/// P1-C5 — END BURN must stay disabled until all 4 smoke-stage proofs are
/// captured (and no persist is in flight), so the writer's "need 4 captures"
/// throw can only be reached via a race, never normal use.
void main() {
  group('canEndBurn', () {
    test('blocked below 4 proofs', () {
      expect(canEndBurn(proofCount: 0, ending: false), isFalse);
      expect(canEndBurn(proofCount: 3, ending: false), isFalse);
    });

    test('allowed at exactly 4 proofs when idle', () {
      expect(canEndBurn(proofCount: 4, ending: false), isTrue);
      expect(canEndBurn(proofCount: 5, ending: false), isTrue);
    });

    test('blocked while a persist is already in flight', () {
      expect(canEndBurn(proofCount: 4, ending: true), isFalse);
    });
  });
}
