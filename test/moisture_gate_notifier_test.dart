// ignore_for_file: avoid_print, unnecessary_string_escapes
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dmrv_app/providers/moisture_gate_notifier.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:dmrv_app/providers/lantana_sourcing_notifier.dart';

/// =============================================================================
/// MoistureGateNotifier — Pure-Dart Riverpod state test
/// =============================================================================
/// Verifies the strict compliance gate around the 15.0% moisture ceiling.
/// =============================================================================

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late ProviderContainer container;
  late MoistureGateNotifier notifier;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    container = ProviderContainer();

    await container.read(lantanaSourcingProvider.future);

    // Bypass the Lantana lock so Moisture can initiate pyrolysis
    container.read(lantanaSourcingProvider.notifier).toggleDevBypass(true);

    notifier = container.read(moistureGateProvider.notifier);
  });

  tearDown(() => container.dispose());

  test('initial state is PENDING and locked', () {
    final s = container.read(moistureGateProvider);
    expect(s.status, MoistureGateStatus.pending);
    expect(s.isLocked, isTrue);
    expect(s.errorMessage, isNull);
  });

  test('moisture = 16.5 → NON-COMPLIANT, locked, error rendered', () {
    notifier.updateReading('16.5');
    final s = container.read(moistureGateProvider);

    expect(s.moisturePercent, 16.5);
    expect(s.status, MoistureGateStatus.nonCompliant);
    expect(s.errorMessage, 'Moisture > 15%. Dry further.');

    print(
      '[16.5%] ✓ flagged non-compliant — workflow LOCKED — '
      'error="${s.errorMessage}"',
    );
  });

  test('moisture = 12.4 → COMPLIANT', () {
    notifier.updateReading('12.4');

    final s = container.read(moistureGateProvider);

    expect(s.moisturePercent, 12.4);
    expect(s.status, MoistureGateStatus.compliant);
    expect(s.errorMessage, isNull);

    print('[12.4%] ✓ flagged compliant — workflow UNLOCKED');
  });

  test('boundary: 15.0 → COMPLIANT (≤ 15.0 is inclusive)', () {
    notifier.updateReading('15.0');
    expect(
      container.read(moistureGateProvider).status,
      MoistureGateStatus.compliant,
    );
  });

  test('boundary: 15.01 → NON-COMPLIANT', () {
    notifier.updateReading('15.01');
    expect(
      container.read(moistureGateProvider).status,
      MoistureGateStatus.nonCompliant,
    );
  });

  test('garbage input stays PENDING (no crash)', () {
    notifier.updateReading('abc');
    expect(
      container.read(moistureGateProvider).status,
      MoistureGateStatus.pending,
    );
  });

  test('full sequence: 16.5 locks, then 12.4 unlocks', () {
    notifier.updateReading('16.5');
    expect(
      container.read(moistureGateProvider).status,
      MoistureGateStatus.nonCompliant,
    );

    notifier.updateReading('12.4');
    expect(
      container.read(moistureGateProvider).status,
      MoistureGateStatus.compliant,
    );

    print('SEQUENCE OK :: 16.5 → LOCKED → 12.4 → UNLOCKED');
  });
}
