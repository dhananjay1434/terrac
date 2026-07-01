// =====================================================================
// P0-20 — Refuse demo / mocked GPS in release builds.
//
// Run:
//     flutter test test/location_service_release_guard_test.dart
//
// In a real CI run, kReleaseMode is `false` under `flutter test`; the
// equivalent assertion belongs in a Patrol / integration test built
// with `--release`. The template below documents both surfaces.
// =====================================================================
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:geolocator/geolocator.dart';

import 'package:dmrv_app/services/location_service.dart';
import 'package:dmrv_app/services/secure_capture_service.dart';

void main() {
  test('Provider exposes Geolocator service when DMRV_DEMO_MODE is unset', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    final svc = container.read(locationServiceProvider);
    expect(svc, isA<GeolocatorLocationService>());
  });

  test(
    'GeolocatorLocationService throws on isMocked=true in release builds',
    () async {
      // NOTE: this test can only pass when run under `flutter test --release`.
      if (!kReleaseMode) {
        markTestSkipped('kReleaseMode is false under default flutter test');
        return;
      }
      // Use a fake Position emitted by a stub here in your real test.
      expect(() async {
        // ... call into the wrapped getter with a mock Position ...
      }, throwsA(isA<SecureCaptureException>()));
    },
  );
}
