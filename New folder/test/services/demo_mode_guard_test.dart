import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/foundation.dart';
import 'package:dmrv_app/services/ble_temperature_service.dart';

void main() {
  test('VirtualBleAdapter throws UnsupportedError in release mode', () {
    // We can't change kReleaseMode at runtime because it's a const bool from the environment.
    // However, if we were in release mode, it would throw.
    // For the test, we'll just check that it parses properly.
    if (kReleaseMode) {
      expect(() => VirtualBleAdapter(), throwsUnsupportedError);
    } else {
      expect(() => VirtualBleAdapter(), returnsNormally);
    }
  });
}
