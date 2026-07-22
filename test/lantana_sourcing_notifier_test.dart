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

  // V8 Part 0.3 regression guard: the fake boundary attestation
  // (`captureGpsPolygon()` persisting a `polygonCaptured` boolean with no
  // real geometry behind it — the UI even claimed "4 vertices" that were
  // never captured) has been removed entirely, not just hidden. Real source
  // parcels arrive in V8 Part 1 via a portal-registered `parcel_uuid`.
  test('no boundary boolean is persisted — the fake attestation is gone', () async {
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getBool('polygon_captured'), isNull);
  });

  // V8 Part 1.6: real source-parcel selection replaces the fake stub. The
  // operator's choice must persist (SharedPreferences) so it survives the
  // sourcing → moisture → capture steps where the batch is actually written.
  test('selectParcel persists the choice and exposes it in state', () async {
    expect(
      container.read(lantanaSourcingProvider).requireValue.parcelUuid,
      isNull,
    );

    await notifier.selectParcel('parcel-123', 'North Field');

    final s = container.read(lantanaSourcingProvider).requireValue;
    expect(s.parcelUuid, 'parcel-123');
    expect(s.parcelName, 'North Field');

    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('selected_parcel_uuid'), 'parcel-123');
    expect(prefs.getString('selected_parcel_name'), 'North Field');
  });

  test('a persisted parcel selection is restored on reload', () async {
    SharedPreferences.setMockInitialValues({
      'selected_parcel_uuid': 'parcel-restore',
      'selected_parcel_name': 'Restored Field',
    });
    final freshContainer = ProviderContainer();
    addTearDown(freshContainer.dispose);
    final s = await freshContainer.read(lantanaSourcingProvider.future);
    expect(s.parcelUuid, 'parcel-restore');
    expect(s.parcelName, 'Restored Field');
  });
}
