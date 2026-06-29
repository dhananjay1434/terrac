import 'package:fake_async/fake_async.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dmrv_app/providers/yield_scale_notifier.dart';
import 'package:dmrv_app/services/ble_weight_scale_service.dart';

/// =============================================================================
/// scale_stabilization_test
/// =============================================================================
/// Proves the 5-reading circular buffer + <0.05 kg variance lock works.
///
///   • Test 1 — happy path: 5 readings within 50 g → stableKg = mean.
///   • Test 2 — unstable:   5 readings spanning >50 g → stableKg == null.
///   • Test 3 — recovery:   unstable then stable → lock re-engages.
///   • Test 4 — circular:   buffer >5 → oldest dropped, only last 5 matter.
///   • Test 5 — byte parser: SI flag → kg = raw * 0.005.
/// =============================================================================

void main() {
  group('YieldScaleNotifier — variance stabilization', () {
    test('5 readings within 50g lock → stableKg = arithmetic mean', () {
      final mock = MockBleWeightScaleService();
      final n = YieldScaleNotifier(mock);

      // Tight cluster: spread = 0.04 kg, well under the 0.05 threshold.
      const readings = [10.000, 10.010, 10.020, 10.030, 10.040];
      for (final r in readings) {
        n.pushReading(r);
      }

      expect(
        n.state.isStabilized,
        isTrue,
        reason: 'variance 0.04kg should trip the lock',
      );
      expect(n.state.stableKg, closeTo(10.020, 1e-9));
      expect(n.state.window.length, kStabilizationBufferSize);
      expect(n.state.variance, closeTo(0.04, 1e-9));
    });

    test('5 readings spanning >50g → NOT stabilized', () {
      final mock = MockBleWeightScaleService();
      final n = YieldScaleNotifier(mock);

      // Spread = 0.20 kg → must NOT lock.
      const readings = [10.000, 10.050, 10.100, 10.150, 10.200];
      for (final r in readings) {
        n.pushReading(r);
      }

      expect(n.state.isStabilized, isFalse);
      expect(n.state.stableKg, isNull);
      expect(n.state.variance, closeTo(0.20, 1e-9));
    });

    test('buffer below 5 entries never locks (even if variance is 0)', () {
      final mock = MockBleWeightScaleService();
      final n = YieldScaleNotifier(mock);

      n.pushReading(7.0);
      n.pushReading(7.0);
      n.pushReading(7.0);
      n.pushReading(7.0); // 4 — one short

      expect(n.state.window.length, 4);
      expect(n.state.isStabilized, isFalse);
      expect(n.state.stableKg, isNull);

      n.pushReading(7.0); // 5th identical reading — now lock.
      expect(n.state.isStabilized, isTrue);
      expect(n.state.stableKg, closeTo(7.0, 1e-9));
    });

    test('circular buffer drops oldest beyond capacity', () {
      final mock = MockBleWeightScaleService();
      final n = YieldScaleNotifier(mock);

      // First 5 readings are wild (variance = 1kg) → no lock.
      n.pushReading(5.0);
      n.pushReading(6.0);
      n.pushReading(4.0);
      n.pushReading(5.5);
      n.pushReading(4.5);
      expect(n.state.isStabilized, isFalse);

      // Now feed 5 tight readings — the oldest 5 wild ones must scroll out.
      n.pushReading(8.000);
      n.pushReading(8.010);
      n.pushReading(8.020);
      n.pushReading(8.030);
      n.pushReading(8.040);

      expect(n.state.window.length, kStabilizationBufferSize);
      expect(n.state.isStabilized, isTrue);
      expect(n.state.stableKg, closeTo(8.020, 1e-9));
    });

    test('confirm() only fires when stable', () {
      final mock = MockBleWeightScaleService();
      final n = YieldScaleNotifier(mock);

      n.confirm(); // pre-stable → no-op
      expect(n.state.isConfirmed, isFalse);

      for (final r in const [9.000, 9.005, 9.010, 9.015, 9.020]) {
        n.pushReading(r);
      }
      n.confirm();
      expect(n.state.isConfirmed, isTrue);
      expect(n.state.confirmedKg, closeTo(9.010, 1e-9));
    });

    test('begin() wires the BLE stream into pushReading()', () {
      fakeAsync((async) {
        final mock = MockBleWeightScaleService();
        final n = YieldScaleNotifier(mock);
        n.begin();
        async.flushMicrotasks();

        for (final r in const [11.000, 11.010, 11.020, 11.030, 11.040]) {
          mock.push(r);
        }
        async.flushMicrotasks();

        expect(n.state.isStabilized, isTrue);
        expect(n.state.stableKg, closeTo(11.020, 1e-9));
      });
    });
  });

  group('BleWeightScaleService.parseWeightMeasurement — byte parser', () {
    test('SI flag clear → kg = raw * 0.005', () {
      // flags = 0x00 (SI), raw = 2000 little-endian = [0xD0, 0x07] → 10.000 kg
      final bytes = [0x00, 0xD0, 0x07];
      final kg = BleWeightScaleService.parseWeightMeasurement(bytes);
      expect(kg, closeTo(10.000, 1e-9));
    });

    test('Imperial flag set → lb→kg conversion', () {
      // flags = 0x01 (imperial), raw = 2200 little-endian = [0x98, 0x08]
      // 2200 * 0.01 = 22 lb → 22 * 0.45359237 ≈ 9.979 kg
      final bytes = [0x01, 0x98, 0x08];
      final kg = BleWeightScaleService.parseWeightMeasurement(bytes);
      expect(kg, closeTo(22 * 0.45359237, 1e-9));
    });

    test('malformed (too short) → null', () {
      expect(
        BleWeightScaleService.parseWeightMeasurement([0x00, 0x01]),
        isNull,
      );
    });
  });
}
