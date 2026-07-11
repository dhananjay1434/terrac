import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/sync_queue_manager.dart';

/// P3.3 — the TLS trust decision. Cloud Run uses system trust (rotated leaf
/// certs); self-hosted keeps pinning; a release with pinning but no PEM must
/// fail closed rather than silently trust the system store.
void main() {
  group('resolveTlsTrust', () {
    test('debug/profile always uses system trust', () {
      expect(
        resolveTlsTrust(isRelease: false, trustMode: 'pinned', pinnedPem: ''),
        TlsTrust.systemDebug,
      );
      // Even a debug build that names pinned+PEM still uses the system store.
      expect(
        resolveTlsTrust(isRelease: false, trustMode: 'pinned', pinnedPem: 'PEM'),
        TlsTrust.systemDebug,
      );
    });

    test('release + system trust mode → system (Cloud Run)', () {
      expect(
        resolveTlsTrust(isRelease: true, trustMode: 'system', pinnedPem: ''),
        TlsTrust.system,
      );
    });

    test('release + pinned + PEM → pinned (self-hosted)', () {
      expect(
        resolveTlsTrust(
          isRelease: true,
          trustMode: 'pinned',
          pinnedPem: '-----BEGIN CERTIFICATE-----',
        ),
        TlsTrust.pinned,
      );
    });

    test('release + pinned + empty PEM → fail closed', () {
      expect(
        () => resolveTlsTrust(
          isRelease: true,
          trustMode: 'pinned',
          pinnedPem: '',
        ),
        throwsStateError,
      );
    });
  });
}
