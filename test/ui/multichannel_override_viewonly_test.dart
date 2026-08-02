import 'package:dmrv_app/services/simulation/sensor_profile.dart';
import 'package:dmrv_app/ui/screens/pyrolysis_screen.dart';
import 'package:flutter_test/flutter_test.dart';

/// P1.4.d — the demo-only view override must NEVER reach the path that
/// starts the multi-channel SOURCE (and therefore what can end up in the
/// legacy/signed write). `persistedBurnProfile` is what `_requestPermsAndStart`
/// calls to pick that source's profile; its signature and behaviour prove the
/// override is not one of its inputs — no matter what override is passed in,
/// the result tracks only the resolved profile.
void main() {
  test('persisted burn profile ignores the view-only override entirely', () {
    for (final resolved in SensorProfile.values) {
      for (final override in SensorProfile.values) {
        expect(
          persistedBurnProfile(
            resolvedProfile: resolved,
            viewOverride: override,
          ),
          resolved,
        );
      }
    }
  });

  test(
    'legacy telemetry write is fed by the resolved profile, never the override',
    () {
      // Even though this "override" value differs from the resolved profile,
      // resolveLegacyTemperatureReadings never takes an override parameter —
      // it only sees the resolved profile and the logs already produced.
      final t1Log = [400.0, 410.0, 420.0];
      final legacyLog = [399.0, 409.0];

      // Resolved = full (has thermal) → prefers the T1 reference series.
      expect(
        resolveLegacyTemperatureReadings(
          resolvedProfile: SensorProfile.full,
          multiChannelLog: {'T1': t1Log},
          legacyTemperatureLog: legacyLog,
        ),
        t1Log,
      );

      // Resolved = loadOnly (no thermal) → T1 is irrelevant even if present;
      // falls back to the legacy log.
      expect(
        resolveLegacyTemperatureReadings(
          resolvedProfile: SensorProfile.loadOnly,
          multiChannelLog: {'T1': t1Log},
          legacyTemperatureLog: legacyLog,
        ),
        legacyLog,
      );

      // Resolved = full but T1 never produced a sample → falls back, never
      // invents values.
      expect(
        resolveLegacyTemperatureReadings(
          resolvedProfile: SensorProfile.full,
          multiChannelLog: const {},
          legacyTemperatureLog: legacyLog,
        ),
        legacyLog,
      );
    },
  );
}
