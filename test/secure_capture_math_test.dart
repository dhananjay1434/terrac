import 'dart:math' as math;
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/secure_capture_service.dart';

void main() {
  group('SecureCaptureService.computeOrientation', () {
    test('flat phone, mag pointing +Y → azimuth near 0°', () {
      final r = SecureCaptureService.computeOrientation(0, 0, -9.81, 0, 30, 0);
      expect(r['azimuth'], closeTo(0, 10));
      expect(r['pitch']!.abs(), lessThan(10));
      expect(r['roll']!.abs(), lessThan(10));
    });

    test('phone rolled right (gravity on +X) → roll near 90°', () {
      final r = SecureCaptureService.computeOrientation(9.81, 0, 0, 0, 30, 0);
      expect(r['roll'], closeTo(90, 10));
    });

    test('phone pitched forward 45° → pitch near -45°', () {
      final r = SecureCaptureService.computeOrientation(
        0,
        -math.sin(math.pi / 4) * 9.81,
        -math.cos(math.pi / 4) * 9.81,
        0,
        30,
        0,
      );
      expect(r['pitch'], closeTo(-45, 10));
    });
  });
}
