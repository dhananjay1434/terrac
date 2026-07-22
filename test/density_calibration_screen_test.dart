import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dmrv_app/providers/yield_scale_notifier.dart';
import 'package:dmrv_app/services/ble_weight_scale_service.dart';
import 'package:dmrv_app/ui/screens/density_calibration_screen.dart';

/// Deferred R3 — reuses [yieldScaleProvider] (the existing BLE weight-scale
/// stack), which must be overridden in tests exactly like
/// yield_scale_screen_test.dart does: the real provider eagerly constructs
/// `FlutterReactiveBle()`, which throws `UnimplementedError` outside a real
/// device/emulator. This verifies the entry state (before the scale
/// connects) renders correctly; the live-reading/stabilized states are
/// covered by yield_scale_screen_test.dart's equivalent coverage of the
/// same underlying notifier — no need to re-prove BLE stabilization math
/// here, only that this screen wires it up in "not yet connected" mode.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  testWidgets('initial state shows the connect-scale entry point', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          yieldScaleProvider.overrideWith(
            (ref) => _MockYieldScaleNotifier(const YieldScaleState()),
          ),
        ],
        child: const MaterialApp(home: DensityCalibrationScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('CONNECT WEIGHT SCALE'), findsOneWidget);
    expect(find.text('Bulk-Density Calibration'), findsOneWidget);
    // Volume field and submit button are not shown before connecting.
    expect(find.bySemanticsIdentifier('density-volume-input'), findsNothing);
  });
}

class _MockYieldScaleNotifier extends YieldScaleNotifier {
  _MockYieldScaleNotifier(YieldScaleState initialState)
    : super(MockBleWeightScaleService()) {
    state = initialState;
  }
}
