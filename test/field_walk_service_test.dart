import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/field_walk_service.dart';

/// V8 Part 5 (A phase-2) — pure guard test. The network-dependent
/// `verifyLink`/`submit` paths need a live server pubkey cache and API base
/// respectively (same documented-elsewhere limitation as other
/// network/camera-backed services in this codebase); this covers the part
/// that's genuinely pure.
void main() {
  group('FieldWalkService.hasEnoughPoints', () {
    test('fewer than 3 points is insufficient', () {
      expect(FieldWalkService.hasEnoughPoints([]), isFalse);
      expect(FieldWalkService.hasEnoughPoints([
        [0.0, 0.0],
      ]), isFalse);
      expect(FieldWalkService.hasEnoughPoints([
        [0.0, 0.0],
        [0.01, 0.0],
      ]), isFalse);
    });

    test('exactly 3 points is sufficient', () {
      expect(
        FieldWalkService.hasEnoughPoints([
          [0.0, 0.0],
          [0.01, 0.0],
          [0.01, 0.01],
        ]),
        isTrue,
      );
    });

    test('more than 3 points is sufficient', () {
      expect(
        FieldWalkService.hasEnoughPoints([
          [0.0, 0.0],
          [0.01, 0.0],
          [0.01, 0.01],
          [0.0, 0.01],
        ]),
        isTrue,
      );
    });
  });
}
