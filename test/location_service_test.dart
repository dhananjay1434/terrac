import 'package:flutter_test/flutter_test.dart';
import 'package:geolocator/geolocator.dart';
import 'package:dmrv_app/services/location_service.dart';

/// =============================================================================
/// Phase 1 — GPS Resilience Tests
/// =============================================================================
///
/// In a test environment, there is no platform channel for Geolocator.
/// Therefore GeolocatorLocationService.acquirePosition() will throw a
/// MissingPluginException. DemoLocationService catches this and returns
/// hardcoded coordinates. This is the EXACT same behavior as a boardroom
/// with no GPS signal — the real Geolocator call fails, and the demo
/// fallback kicks in.
/// =============================================================================
void main() {
  group('DemoLocationService', () {
    test(
      'returns a valid Position when Geolocator throws (no platform channel in test)',
      () async {
        final service = DemoLocationService();
        final pos = await service.acquirePosition();
        // Must not be null — the demo fallback must always succeed.
        expect(pos, isNotNull);
        expect(pos, isA<Position>());
      },
    );
    test(
      'returned Position has New Delhi coordinates (28.6139, 77.2090)',
      () async {
        final service = DemoLocationService();
        final pos = await service.acquirePosition();
        expect(
          pos.latitude,
          closeTo(28.6139, 0.001),
          reason: 'Demo latitude must be 28.6139 (New Delhi)',
        );
        expect(
          pos.longitude,
          closeTo(77.2090, 0.001),
          reason: 'Demo longitude must be 77.2090 (New Delhi)',
        );
      },
    );
    test('returned Position has non-negative accuracy', () async {
      final service = DemoLocationService();
      final pos = await service.acquirePosition();
      expect(
        pos.accuracy,
        greaterThanOrEqualTo(0),
        reason: 'Accuracy must be >= 0 to be mathematically valid',
      );
    });
  });
  group('Type hierarchy', () {
    test('GeolocatorLocationService implements ILocationService', () {
      expect(GeolocatorLocationService(), isA<ILocationService>());
    });
    test('DemoLocationService implements ILocationService', () {
      expect(DemoLocationService(), isA<ILocationService>());
    });
  });
}
