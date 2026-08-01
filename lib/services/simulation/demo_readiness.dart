import 'package:flutter/foundation.dart';
import '../crypto_signer.dart';

/// Whether the demo will actually reach the portal. Computed WITHOUT ever
/// throwing — a missing key must degrade to a log/banner, never crash burn-start.
class DemoReadiness {
  const DemoReadiness({required this.enrolled, required this.detail});
  final bool enrolled;
  final String detail;
  bool get ok => enrolled;
}

/// Idempotent, soft-fail: if already enrolled, done; else try to enroll and
/// swallow any failure, reporting status. NEVER throws.
Future<DemoReadiness> ensureDemoReady() async {
  try {
    if (await CryptoSigner.isEnrolled()) {
      return const DemoReadiness(enrolled: true, detail: 'device enrolled');
    }
    await CryptoSigner.registerDevice();
    final ok = await CryptoSigner.isEnrolled();
    return DemoReadiness(
      enrolled: ok,
      detail: ok ? 'device enrolled' : 'enrollment did not complete',
    );
  } catch (e) {
    debugPrint('[DemoReadiness] enrollment soft-failed (portal will not receive this burn): $e');
    return const DemoReadiness(
      enrolled: false,
      detail: 'not enrolled — enroll in Settings, or bake --dart-define=ENROLLMENT_TOKEN',
    );
  }
}
