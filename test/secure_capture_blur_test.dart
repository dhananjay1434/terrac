import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:dmrv_app/services/secure_capture_service.dart';

/// V8 Part 4 (E) — blur-gate pure math. `computeBlurVariance` takes a
/// decoded `img.Image` so it's fully testable without a camera: a uniform
/// (flat-color) image is the degenerate "maximally blurry" case, and a
/// checkerboard is the degenerate "maximally sharp" case.
void main() {
  group('SecureCaptureService.computeBlurVariance', () {
    test('a uniform flat-color image has ~zero variance (blurry)', () {
      final image = img.Image(width: 40, height: 40);
      img.fill(image, color: img.ColorRgb8(128, 128, 128));
      final variance = SecureCaptureService.computeBlurVariance(image);
      expect(variance, closeTo(0, 0.001));
    });

    test('a high-contrast checkerboard has high variance (sharp)', () {
      final image = img.Image(width: 40, height: 40);
      for (var y = 0; y < 40; y++) {
        for (var x = 0; x < 40; x++) {
          final on = (x ~/ 4 + y ~/ 4) % 2 == 0;
          image.setPixelRgb(x, y, on ? 255 : 0, on ? 255 : 0, on ? 255 : 0);
        }
      }
      final variance = SecureCaptureService.computeBlurVariance(image);
      expect(variance, greaterThan(SecureCaptureService.kBlurVarianceThreshold));
    });

    test('downsamples wide images rather than scaling cost with resolution', () {
      final image = img.Image(width: 800, height: 600);
      img.fill(image, color: img.ColorRgb8(50, 50, 50));
      expect(
        () => SecureCaptureService.computeBlurVariance(image),
        returnsNormally,
      );
    });
  });
}
