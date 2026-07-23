import 'package:dmrv_app/providers/sourcing_notifier.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    // Isolate SharedPreferences between tests. Without this, _loadState() in
    // LantanaSourcingNotifier reads stale keys from a prior test's writes.
    SharedPreferences.setMockInitialValues({});
  });

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  ProviderContainer makeContainer() => ProviderContainer();

  // ---------------------------------------------------------------------------
  // Test 1 — wall-clock spoof state is accessible on the notifier state.
  //
  // The previous Test 1 was pure math (73 > 72) and exercised zero application
  // code. This version drives the actual notifier state machine.
  // ---------------------------------------------------------------------------
  test('test_wall_clock_spoof_state_is_accessible_on_state', () async {
    final container = makeContainer();
    addTearDown(container.dispose);

    final notifier = container.read(sourcingProvider.notifier);
    // FM-4: feedstock only resolves from a configured project; no
    // DMRV_PROJECT_ID in the test env, so simulate "resolved" directly.
    // build() must complete before debugSetFeedstock touches state.
    await container.read(sourcingProvider.future);
    notifier.debugSetFeedstock('Lantana_camara');

    // Log harvest 73h ago on wall clock. On non-Android CI, uptime will be null.
    await notifier.logHarvestAt(
      DateTime.now().toUtc().subtract(const Duration(hours: 73)),
    );

    final s = container.read(sourcingProvider).requireValue;

    // State must carry the uptime field (null on non-Android is valid).
    expect(
      s.harvestUptimeSeconds,
      anyOf(isNull, isA<int>()),
      reason: 'harvestUptimeSeconds must be int or null, never throws',
    );

    // Wall clock says compliant.
    expect(
      s.canProceedToMoisture,
      isTrue,
      reason: '73h elapsed — workflow must be unlocked regardless of uptime',
    );

    // Uptime field is accessible and correctly typed.
    if (s.harvestUptimeSeconds != null) {
      expect(s.harvestUptimeSeconds, isA<int>());
      expect(s.harvestUptimeSeconds! >= 0, isTrue);
    }
  });

  // ---------------------------------------------------------------------------
  // Test 2 — legitimate 72h pass-through
  // ---------------------------------------------------------------------------
  test('test_legitimate_72h_pass_through', () async {
    final container = makeContainer();
    addTearDown(container.dispose);

    final notifier = container.read(sourcingProvider.notifier);
    await container.read(sourcingProvider.future);
    notifier.debugSetFeedstock('Lantana_camara');

    // Log harvest 73h ago.
    await notifier.logHarvestAt(
      DateTime.now().toUtc().subtract(const Duration(hours: 73)),
    );

    final s = container.read(sourcingProvider).requireValue;
    expect(s.hasHarvest, isTrue);
    expect(s.elapsedSinceHarvest.inHours, greaterThanOrEqualTo(73));
    expect(
      s.canProceedToMoisture,
      isTrue,
      reason: '73h > 72h mandate — workflow should be unlocked',
    );
  });

  // ---------------------------------------------------------------------------
  // Test 3 — harvest logged 1h ago stays locked
  // ---------------------------------------------------------------------------
  test('test_premature_harvest_keeps_workflow_locked', () async {
    final container = makeContainer();
    addTearDown(container.dispose);

    final notifier = container.read(sourcingProvider.notifier);
    await notifier.logHarvestAt(
      DateTime.now().toUtc().subtract(const Duration(hours: 1)),
    );

    final s = container.read(sourcingProvider).requireValue;
    expect(
      s.canProceedToMoisture,
      isFalse,
      reason: 'Only 1h elapsed — 72h mandate not satisfied',
    );
  });

  // ---------------------------------------------------------------------------
  // Test 4 — harvestUptimeSeconds is stored in state when harvest is logged
  //
  // On non-Android (e.g. CI / Windows), _readUptimeSeconds returns null.
  // We verify the state field is populated (either with a value or null),
  // and that it does NOT blow up the app.
  // ---------------------------------------------------------------------------
  test('test_harvest_uptime_seconds_stored_in_state', () async {
    final container = makeContainer();
    addTearDown(container.dispose);

    final notifier = container.read(sourcingProvider.notifier);
    await notifier.logHarvestNow();

    final s = container.read(sourcingProvider).requireValue;
    expect(s.hasHarvest, isTrue);
    // harvestUptimeSeconds may be null on non-Android CI, but must not throw.
    expect(
      () => s.harvestUptimeSeconds,
      returnsNormally,
      reason: '_readUptimeSeconds must not throw on any platform',
    );
  });

  // ---------------------------------------------------------------------------
  // Test 5 — dev bypass overrides the mandate (QA path)
  // ---------------------------------------------------------------------------
  test('test_dev_bypass_overrides_72h_lock', () async {
    final container = makeContainer();
    addTearDown(container.dispose);

    final notifier = container.read(sourcingProvider.notifier);
    await container.read(sourcingProvider.future);
    notifier.debugSetFeedstock('Lantana_camara');

    // Harvest just happened — mandate definitely not met.
    await notifier.logHarvestNow();
    expect(
      container.read(sourcingProvider).requireValue.canProceedToMoisture,
      isFalse,
    );

    // Flip bypass.
    notifier.toggleDevBypass(true);
    expect(
      container.read(sourcingProvider).requireValue.canProceedToMoisture,
      isTrue,
      reason: 'Dev bypass must unlock the workflow regardless of elapsed time',
    );
  });
}
