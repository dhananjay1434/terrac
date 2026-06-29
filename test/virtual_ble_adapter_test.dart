import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/ble_temperature_service.dart';

/// =============================================================================
/// Phase 2 — VirtualBleAdapter Tests
/// =============================================================================
/// Verifies the 3-stage thermodynamic state machine:
///   1. Connection lifecycle: scanning → connected → idle on stop.
///   2. First temperature tick is in ambient/ignition range (< 50°C).
///   3. Temperature eventually climbs past 350°C towards the plateau.
///   4. stop() halts the stream and emits idle.
/// =============================================================================

void main() {
  group('VirtualBleAdapter', () {
    test('emits BleConnState.scanning then .connected on start()', () async {
      final adapter = VirtualBleAdapter(
        tickInterval: const Duration(milliseconds: 10),
      );
      final states = <BleConnState>[];
      final sub = adapter.connectionStream.listen(states.add);

      await adapter.start();
      // The 1.5s handshake delay means we need to wait for it
      // start() already awaits the delay internally, so by this point
      // both scanning and connected should have been emitted.
      await Future.delayed(const Duration(milliseconds: 100));

      expect(
        states.length,
        greaterThanOrEqualTo(2),
        reason: 'Must emit at least scanning + connected',
      );
      expect(states[0], BleConnState.scanning);
      expect(states[1], BleConnState.connected);

      await adapter.stop();
      await sub.cancel();
    });

    test(
      'first temperature tick is in ambient/ignition range (< 50°C)',
      () async {
        final adapter = VirtualBleAdapter(
          tickInterval: const Duration(milliseconds: 10),
        );
        final completer = Completer<double>();
        final sub = adapter.temperatureStream.listen((temp) {
          if (!completer.isCompleted) completer.complete(temp);
        });

        await adapter.start();
        final firstTemp = await completer.future.timeout(
          const Duration(seconds: 5),
          onTimeout: () => throw TimeoutException('No temperature emitted'),
        );

        expect(
          firstTemp,
          lessThan(50.0),
          reason: 'Tick 1 is ignition stage: 25 + (1*15) = 40°C',
        );

        await adapter.stop();
        await sub.cancel();
      },
    );

    test('temperature ramps past 350°C towards plateau', () async {
      final adapter = VirtualBleAdapter(
        tickInterval: const Duration(milliseconds: 10),
        targetPlateau: 420.0,
      );
      double maxSeen = 0;
      final sub = adapter.temperatureStream.listen((temp) {
        if (temp > maxSeen) maxSeen = temp;
      });

      await adapter.start();
      // Let it run through all 3 stages (20+ ticks at 10ms = 200ms + 1.5s handshake)
      await Future.delayed(const Duration(seconds: 3));

      expect(
        maxSeen,
        greaterThan(350.0),
        reason: 'After 20+ ticks, should have ramped past 350°C',
      );

      await adapter.stop();
      await sub.cancel();
    });

    test('stop() emits BleConnState.idle', () async {
      final adapter = VirtualBleAdapter(
        tickInterval: const Duration(milliseconds: 10),
      );
      final states = <BleConnState>[];
      final sub = adapter.connectionStream.listen(states.add);

      await adapter.start();
      await Future.delayed(const Duration(milliseconds: 100));
      await adapter.stop();

      expect(
        states.last,
        BleConnState.idle,
        reason: 'stop() must emit idle as the final connection state',
      );

      await sub.cancel();
    });

    test('implements BleTemperatureSource interface', () {
      final adapter = VirtualBleAdapter();
      expect(adapter, isA<BleTemperatureSource>());
    });
  });
}
