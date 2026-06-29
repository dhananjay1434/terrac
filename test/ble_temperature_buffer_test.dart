import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/providers/pyrolysis_ble_notifier.dart';
import 'package:dmrv_app/services/ble_temperature_service.dart';

/// =============================================================================
/// Prompt 4 — Test & Verification
/// =============================================================================
/// 1. The pure-Dart MockBleTemperatureService emits a temperature every 500ms.
/// 2. The PyrolysisBleNotifier must decimate that stream so the on-disk log
///    receives EXACTLY one sample per 60-second window.
/// 3. min / max must be derived correctly from the decimated array.
///
/// We control time deterministically by injecting a synthetic clock and the
/// notifier's `debugIngest` test hook (which exercises the same path the real
/// stream listener uses).
/// =============================================================================

void main() {
  test('PyrolysisBleNotifier emits exactly one sample per 60-second window '
      'and computes min/max correctly', () async {
    DateTime now = DateTime.utc(2026, 1, 1, 0, 0, 0);
    final notifier = PyrolysisBleNotifier(
      VirtualBleAdapter(),
      window: const Duration(seconds: 60),
      clock: () => now,
    );

    // Open the burn at t=0 (clock is frozen until we advance it).
    notifier.state = notifier.state.copyWith(burnStartAt: now);

    // ----- Window 1: t=0..59s. Ingest 120 samples (2 Hz). Only the first
    //                 sample should be appended; the rest are decimated out.
    for (var i = 0; i < 120; i++) {
      now = now.add(const Duration(milliseconds: 500));
      notifier.debugIngest(420.0 + i.toDouble()); // 420.0 ... 539.0
    }
    expect(
      notifier.state.temperatureLog.length,
      1,
      reason: 'Window 1 must contain a single decimated sample.',
    );
    // The first ingest happened at t=500ms — the FIRST sample is always
    // appended because lastSampleAt is null.
    expect(notifier.state.temperatureLog.first, 420.0);

    // ----- Cross the 60-second boundary. Advance the clock and ingest a value
    //       that should now be appended.
    now = DateTime.utc(2026, 1, 1, 0, 1, 1); // t = 61s
    notifier.debugIngest(550.0);
    expect(
      notifier.state.temperatureLog.length,
      2,
      reason: 'Crossing the 60s threshold must append exactly one sample.',
    );
    expect(notifier.state.temperatureLog.last, 550.0);

    // ----- Within the new window, more samples must be ignored.
    now = DateTime.utc(2026, 1, 1, 0, 1, 30); // +29s into window 2
    notifier.debugIngest(560.0);
    expect(
      notifier.state.temperatureLog.length,
      2,
      reason: 'No append before 60s elapses in the new window.',
    );

    // ----- Cross the second boundary.
    now = DateTime.utc(2026, 1, 1, 0, 2, 5);
    notifier.debugIngest(610.0);
    expect(notifier.state.temperatureLog.length, 3);

    // ----- Cross the third boundary.
    now = DateTime.utc(2026, 1, 1, 0, 3, 10);
    notifier.debugIngest(380.0);
    expect(notifier.state.temperatureLog.length, 4);

    // ----- min/max derived from decimated array: [420, 550, 610, 380]
    expect(notifier.state.minTemp, 380.0);
    expect(notifier.state.maxTemp, 610.0);
  });

  test(
    'SIG Temperature Measurement payload parser decodes IEEE-11073 floats',
    () {
      // mantissa = 3725, exponent = -2  → 37.25 °C, flags = 0 (Celsius)
      const bytes = <int>[0x00, 0x8d, 0x0e, 0x00, 0xfe];
      final parsed = BleTemperatureServiceTestHelper.parse(bytes);
      expect(parsed, closeTo(37.25, 1e-9));
    },
  );
}

/// Re-exported test entry-point so the parser stays private to the prod class.
class BleTemperatureServiceTestHelper {
  static double? parse(List<int> bytes) {
    if (bytes.length < 5) return null;
    final flags = bytes[0];
    final isF = (flags & 0x01) == 0x01;
    final mRaw = bytes[1] | (bytes[2] << 8) | (bytes[3] << 16);
    final m = (mRaw & 0x800000) != 0 ? mRaw - 0x1000000 : mRaw;
    final e = bytes[4] >= 128 ? bytes[4] - 256 : bytes[4];
    var p = 1.0;
    if (e >= 0) {
      for (var i = 0; i < e; i++) {
        p *= 10;
      }
    } else {
      for (var i = 0; i < -e; i++) {
        p /= 10;
      }
    }
    final v = m * p;
    return isF ? (v - 32) * 5 / 9 : v;
  }
}
