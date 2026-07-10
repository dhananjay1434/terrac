import 'package:dmrv_app/ui/screens/pyrolysis_screen.dart';
import 'package:flutter_test/flutter_test.dart';

/// P1-C5 + P1-S4 — END BURN gating is kiln-type aware. Every burn needs the 4
/// smoke proofs; an OPEN kiln also needs the 3 flame-stage photos + a recorded
/// flame height; a CLOSED kiln needs a declared ignition-energy type. Pure
/// predicate, so we cover the matrix without the burn widget harness.
void main() {
  const smoke = {'smoke_0', 'smoke_50', 'smoke_90', 'smoke_100'};
  const allOpen = {
    'smoke_0',
    'smoke_50',
    'smoke_90',
    'smoke_100',
    'flame_curtain',
    'quenching',
    'flame_height',
  };

  group('canEndBurn — always requires the 4 smoke proofs', () {
    test('blocked when a smoke proof is missing', () {
      expect(
        canEndBurn(
          ending: false,
          isOpenKiln: false,
          capturedStages: const {'smoke_0', 'smoke_50', 'smoke_90'},
          flameHeightM: null,
          ignitionEnergyType: 'LPG',
        ),
        isFalse,
      );
    });

    test('blocked while a persist is in flight', () {
      expect(
        canEndBurn(
          ending: true,
          isOpenKiln: false,
          capturedStages: smoke,
          flameHeightM: null,
          ignitionEnergyType: 'LPG',
        ),
        isFalse,
      );
    });
  });

  group('canEndBurn — open kiln', () {
    test('needs all 3 flame stages AND a flame height', () {
      // 4 smoke only → blocked.
      expect(
        canEndBurn(
          ending: false,
          isOpenKiln: true,
          capturedStages: smoke,
          flameHeightM: 0.3,
          ignitionEnergyType: null,
        ),
        isFalse,
      );
      // all 7 stages but no flame height → blocked.
      expect(
        canEndBurn(
          ending: false,
          isOpenKiln: true,
          capturedStages: allOpen,
          flameHeightM: null,
          ignitionEnergyType: null,
        ),
        isFalse,
      );
      // all 7 stages + flame height → allowed.
      expect(
        canEndBurn(
          ending: false,
          isOpenKiln: true,
          capturedStages: allOpen,
          flameHeightM: 0.3,
          ignitionEnergyType: null,
        ),
        isTrue,
      );
    });
  });

  group('canEndBurn — closed kiln', () {
    test('needs an ignition-energy type, not the flame stages', () {
      // 4 smoke, no ignition → blocked.
      expect(
        canEndBurn(
          ending: false,
          isOpenKiln: false,
          capturedStages: smoke,
          flameHeightM: null,
          ignitionEnergyType: null,
        ),
        isFalse,
      );
      // 4 smoke + ignition type → allowed (no flame stages required).
      expect(
        canEndBurn(
          ending: false,
          isOpenKiln: false,
          capturedStages: smoke,
          flameHeightM: null,
          ignitionEnergyType: 'LPG',
        ),
        isTrue,
      );
    });
  });
}
