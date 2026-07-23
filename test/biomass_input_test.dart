import 'package:dmrv_app/providers/sourcing_notifier.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// P1-S2 — Rainbow C1 biomass capture on the Sourcing screen. The proceed gate
/// requires a positive weight AND a measurement method; setBiomass persists it
/// into the sourcing state so both the gate and the C2 moisture target react.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() => SharedPreferences.setMockInitialValues({}));

  test('hasBiomass requires both a positive weight and a method', () {
    const s0 = SourcingState(
      feedstockSpecies: 'Lantana_camara',
      allowedFeedstocks: ['Lantana_camara'],
    );
    expect(s0.hasBiomass, isFalse);
    expect(s0.copyWith(biomassInputKg: 500).hasBiomass, isFalse);
    expect(
      s0.copyWith(biomassMeasurementMethod: 'direct_weigh').hasBiomass,
      isFalse,
    );
    expect(
      s0
          .copyWith(biomassInputKg: 500, biomassMeasurementMethod: 'direct_weigh')
          .hasBiomass,
      isTrue,
    );
  });

  test('setBiomass persists and updates the sourcing state', () async {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    await container.read(sourcingProvider.future);

    await container
        .read(sourcingProvider.notifier)
        .setBiomass(750, 'direct_weigh');

    final s = container.read(sourcingProvider).requireValue;
    expect(s.biomassInputKg, 750);
    expect(s.biomassMeasurementMethod, 'direct_weigh');
    expect(s.hasBiomass, isTrue);
  });
}
