import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/dispatch_service.dart';

/// Deferred R2 — dispatch wizard restart-resilience. `resolveResumePhase` is
/// the pure reconciliation: server truth always wins over a locally-
/// persisted phase (which can only be stale, because a transition already
/// succeeded server-side right before the app was killed) — resurrecting a
/// phase the backend has already moved past would be a real bug, not just a
/// UI inconvenience (e.g. re-showing an editable draft form for a dispatch
/// that's already in_transit).
void main() {
  group('resolveResumePhase', () {
    test('persisted behind server -> resumes to server phase', () {
      expect(
        resolveResumePhase(persistedPhase: 'draft', serverStatus: 'in_transit'),
        'in_transit',
      );
    });

    test('persisted ahead of server -> resumes to server phase (server wins)', () {
      expect(
        resolveResumePhase(persistedPhase: 'received', serverStatus: 'in_transit'),
        'in_transit',
      );
    });

    test('persisted equals server -> resumes to that phase', () {
      expect(
        resolveResumePhase(persistedPhase: 'in_transit', serverStatus: 'in_transit'),
        'in_transit',
      );
    });

    test('no persisted phase, server has one -> uses server phase', () {
      expect(
        resolveResumePhase(persistedPhase: null, serverStatus: 'draft'),
        'draft',
      );
    });

    test('no persisted phase, no server status -> fresh draft', () {
      expect(
        resolveResumePhase(persistedPhase: null, serverStatus: null),
        'draft',
      );
    });

    test('persisted phase, server unreachable (null status) -> trusts persisted', () {
      expect(
        resolveResumePhase(persistedPhase: 'in_transit', serverStatus: null),
        'in_transit',
      );
    });
  });
}
