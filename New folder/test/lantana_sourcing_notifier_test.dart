import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dmrv_app/providers/lantana_sourcing_notifier.dart';

/// =============================================================================
/// LantanaSourcingNotifier — Pure-Dart Riverpod state test
/// =============================================================================
/// Verifies:
///   • Feedstock species is immutably set to "Lantana_camara".
///   • The 72-hour temporal lock blocks progression until 72h elapse.
///   • The Dev Bypass flag bypasses the lock immediately.
/// =============================================================================
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late ProviderContainer container;
  late LantanaSourcingNotifier notifier;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    container = ProviderContainer();
    notifier = container.read(lantanaSourcingProvider.notifier);
    await container.read(lantanaSourcingProvider.future);
  });
  tearDown(() => container.dispose());

  test('initial state: Lantana_camara, no harvest, locked', () {
    final s = container.read(lantanaSourcingProvider).requireValue;
    expect(s.feedstockSpecies, 'Lantana_camara');
    expect(s.hasHarvest, isFalse);
    expect(s.canProceedToMoisture, isFalse);
  });

  test('harvest just now → still locked (< 72h)', () async {
    await notifier.logHarvestAt(DateTime.now());
    expect(
      container.read(lantanaSourcingProvider).requireValue.canProceedToMoisture,
      isFalse,
    );
  });

  test('harvest 73h ago → unlocked (≥ 72h)', () async {
    await notifier.logHarvestAt(
      DateTime.now().subtract(const Duration(hours: 73)),
    );
    expect(
      container.read(lantanaSourcingProvider).requireValue.canProceedToMoisture,
      isTrue,
    );
  });

  test('Dev Bypass overrides the temporal lock', () async {
    await notifier.logHarvestAt(
      DateTime.now(),
    ); // fresh harvest → would be locked
    expect(
      container.read(lantanaSourcingProvider).requireValue.canProceedToMoisture,
      isFalse,
    );
    notifier.toggleDevBypass(true);
    expect(
      container.read(lantanaSourcingProvider).requireValue.canProceedToMoisture,
      isTrue,
    );
  });

  test('captureGpsPolygon flips polygonCaptured', () async {
    expect(
      container.read(lantanaSourcingProvider).requireValue.polygonCaptured,
      isFalse,
    );
    await notifier.captureGpsPolygon();
    expect(
      container.read(lantanaSourcingProvider).requireValue.polygonCaptured,
      isTrue,
    );
  });
}
