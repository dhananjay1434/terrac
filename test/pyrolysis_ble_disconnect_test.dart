import 'dart:async';

import 'package:dmrv_app/providers/pyrolysis_ble_notifier.dart';
import 'package:dmrv_app/services/ble_temperature_service.dart';
import 'package:flutter_test/flutter_test.dart';

/// P1-C4 — a dropped thermocouple link during a burn must surface (banner),
/// not silently truncate telemetry. Tests the watchdog + stream-error handling
/// deterministically via the injected clock and debug hooks (no real timers).
class _FakeSource implements BleTemperatureSource {
  final _temp = StreamController<double>.broadcast();
  final _conn = StreamController<BleConnState>.broadcast();
  final _attest = StreamController<List<int>>.broadcast();
  @override
  Stream<double> get temperatureStream => _temp.stream;
  @override
  Stream<BleConnState> get connectionStream => _conn.stream;
  @override
  Stream<List<int>> get attestationStream => _attest.stream;
  @override
  Future<void> start() async {}
  @override
  Future<void> stop() async {}
  @override
  Future<void> dispose() async {}
}

void main() {
  test('watchdog flips connectionLost after 30s silence; next sample clears it',
      () async {
    var now = DateTime(2026, 1, 1, 12, 0, 0);
    final n = PyrolysisBleNotifier(_FakeSource(), clock: () => now);
    await n.beginBurn();
    n.debugIngest(300); // _lastSampleAt = now
    expect(n.state.connectionLost, isFalse);

    now = now.add(const Duration(seconds: 45)); // link goes silent
    n.debugRunWatchdog();
    expect(n.state.connectionLost, isTrue);

    n.debugIngest(310); // a fresh sample arrives
    expect(n.state.connectionLost, isFalse);
    n.dispose();
  });

  test('a stream error surfaces as bleError', () async {
    final n = PyrolysisBleNotifier(_FakeSource());
    await n.beginBurn();
    expect(n.state.bleError, isNull);

    n.debugStreamError('boom');
    expect(n.state.bleError, isNotNull);
    expect(n.state.bleError!.contains('boom'), isTrue);
    n.dispose();
  });

  test('beginBurn clears a prior bleError', () async {
    final n = PyrolysisBleNotifier(_FakeSource());
    await n.beginBurn();
    n.debugStreamError('boom');
    expect(n.state.bleError, isNotNull);

    await n.beginBurn(); // restart the burn
    expect(n.state.bleError, isNull);
    expect(n.state.connectionLost, isFalse);
    n.dispose();
  });
}
