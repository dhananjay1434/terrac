import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/data/capture_types.dart';
import 'package:dmrv_app/services/secure_capture_service.dart';

/// V8 Part 4 (O) — video capture caps. `startVideoRecording`/
/// `stopVideoRecording` need a real `CameraController` (hardware), so per
/// this codebase's established limitation they aren't exercised here; the
/// pure cap-check that guards against an oversized/overlong clip is fully
/// testable in isolation and is what actually protects the 2G upload budget.
void main() {
  group('SecureCaptureService.assertVideoWithinCaps', () {
    test('accepts a clip within both caps', () {
      expect(
        () => SecureCaptureService.assertVideoWithinCaps(
          1 * 1024 * 1024,
          const Duration(seconds: 10),
        ),
        returnsNormally,
      );
    });

    test('rejects a clip over the duration cap', () {
      expect(
        () => SecureCaptureService.assertVideoWithinCaps(
          1 * 1024 * 1024,
          const Duration(seconds: 16),
        ),
        throwsA(isA<SecureCaptureException>()),
      );
    });

    test('rejects a clip over the byte cap', () {
      expect(
        () => SecureCaptureService.assertVideoWithinCaps(
          9 * 1024 * 1024,
          const Duration(seconds: 5),
        ),
        throwsA(isA<SecureCaptureException>()),
      );
    });

    test('boundary: exactly at both caps is accepted (inclusive)', () {
      expect(
        () => SecureCaptureService.assertVideoWithinCaps(
          SecureCaptureService.kMaxVideoBytes,
          SecureCaptureService.kMaxVideoDuration,
        ),
        returnsNormally,
      );
    });
  });

  group('CaptureType video kinds', () {
    test('quenching_video and density_video are distinct, valid identifiers', () {
      expect(CaptureType.quenchingVideo, 'quenching_video');
      expect(CaptureType.densityVideo, 'density_video');
      final validPattern = RegExp(r'^[a-z0-9_]{1,64}$');
      expect(validPattern.hasMatch(CaptureType.quenchingVideo), isTrue);
      expect(validPattern.hasMatch(CaptureType.densityVideo), isTrue);
    });
  });
}
