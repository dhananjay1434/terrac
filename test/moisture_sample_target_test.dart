import 'package:dmrv_app/providers/moisture_gate_notifier.dart';
import 'package:flutter_test/flutter_test.dart';

/// P1-S1 — the moisture loop's target must mirror the backend C2 rule exactly:
/// max(10, ceil(biomassKg / 100)). This is the number of photographed readings
/// the operator must capture before pyrolysis unlocks.
void main() {
  group('moistureSampleTarget', () {
    test('null / zero / negative biomass falls back to the floor of 10', () {
      expect(moistureSampleTarget(null), 10);
      expect(moistureSampleTarget(0), 10);
      expect(moistureSampleTarget(-5), 10);
    });

    test('below the scaling threshold still floors at 10', () {
      expect(moistureSampleTarget(250), 10); // ceil(2.5)=3 → floor 10
      expect(moistureSampleTarget(999), 10); // ceil(9.99)=10
      expect(moistureSampleTarget(1000), 10);
    });

    test('above the threshold scales as ceil(kg/100)', () {
      expect(moistureSampleTarget(1050), 11);
      expect(moistureSampleTarget(1600), 16);
      expect(moistureSampleTarget(9000), 90);
    });
  });
}
