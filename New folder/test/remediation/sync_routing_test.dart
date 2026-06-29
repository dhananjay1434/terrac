// Phase 1 / Task 1.1 — explicit per-table sync routing contract (BUG-1, BUG-3).
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/sync_queue_manager.dart';

void main() {
  group('sync routing contract', () {
    test('biomass_sourcing routes to batches', () {
      expect(endpointForTable('biomass_sourcing'), 'batches');
    });

    test('system_metadata routes to metadata (not the batches stub)', () {
      expect(endpointForTable('system_metadata'), 'metadata');
    });

    test('telemetry/yield/application route correctly', () {
      expect(endpointForTable('pyrolysis_telemetry'), 'telemetry');
      expect(endpointForTable('yield_metrics'), 'yield');
      expect(endpointForTable('end_use_application'), 'application');
    });

    test('unknown table throws instead of defaulting', () {
      expect(() => endpointForTable('totally_unknown'), throwsStateError);
    });
  });
}
