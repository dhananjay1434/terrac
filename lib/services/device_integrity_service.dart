import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freerasp/freerasp.dart';

/// The ONE release identity — MUST equal `android/app/build.gradle.kts`
/// applicationId. freerasp compares this against the running app; a mismatch
/// trips the repackaging check (`onAppIntegrity`) and hard-locks the app.
/// Regression-tested against build.gradle.kts in device_integrity_test.dart.
const String kReleaseAndroidPackage = 'io.dmrv.dmrv_app';

/// iOS bundle id (Android is the shipping target; kept consistent for parity).
const String kReleaseIosBundleId = 'io.dmrv.dmrvApp';

/// Service that initializes FreeRASP to detect rooted/jailbroken devices,
/// emulators, and hooking frameworks (e.g. Frida, Xposed).
class DeviceIntegrityService {
  DeviceIntegrityService(this.ref);
  final Ref ref;

  Future<void> initialize() async {
    if (kIsWeb) return; // FreeRASP doesn't support web

    // Demo mode is a non-release affordance ONLY. A release binary must never
    // silently disable integrity, so refuse to run one built with the bypass.
    final demo = const bool.fromEnvironment('DMRV_DEMO_MODE');
    if (demo && kReleaseMode) {
      throw StateError('DMRV_DEMO_MODE is forbidden in release builds.');
    }
    if (demo || kDebugMode) {
      debugPrint(
        '[DeviceIntegrity] demo/debug build — integrity checks skipped.',
      );
      return;
    }

    // Fail CLOSED: a release build with no integrity configuration is treated
    // as compromised rather than running unprotected.
    const certHash = String.fromEnvironment('TALSEC_SIGNING_CERT_HASH');
    const iosTeam = String.fromEnvironment('TALSEC_IOS_TEAM_ID');
    if (certHash.isEmpty || iosTeam.isEmpty) {
      _compromised('Integrity configuration missing');
      return;
    }

    final config = TalsecConfig(
      androidConfig: AndroidConfig(
        packageName: kReleaseAndroidPackage,
        signingCertHashes: [certHash],
      ),
      iosConfig: IOSConfig(bundleIds: [kReleaseIosBundleId], teamId: iosTeam),
      watcherMail: 'security@kontiki.test',
      isProd: true,
    );

    // Callbacks for threat detection.
    final callback = ThreatCallback(
      onAppIntegrity: () => _compromised('App Integrity Compromised'),
      onObfuscationIssues: () => _compromised('Obfuscation Issues Detected'),
      onDebug: () => _compromised('Debugging Detected'),
      onDeviceBinding: () => _compromised('Device Binding Compromised'),
      onDeviceID: () => _compromised('Device ID Compromised'),
      onHooks: () => _compromised('Hooking Framework Detected'),
      onPrivilegedAccess: () =>
          _compromised('Privilege Escalation (Root/Jailbreak)'),
      onSecureHardwareNotAvailable: () =>
          _compromised('Secure Hardware Unavailable'),
      onSimulator: () => _compromised('Simulator/Emulator Detected'),
      // Private B2B distribution is intentionally NOT via an app store (direct
      // APK / MDM), so a non-store installer is EXPECTED — it must not brick a
      // legitimate install. Log-only: keep the signal in telemetry without
      // flipping the compromised flag. Every genuine tamper vector above
      // (root, hooks, debugger, repackaging/app-integrity, device-binding,
      // emulator) still hard-locks.
      onUnofficialStore: () => debugPrint(
        '[DeviceIntegrity] non-store install (expected for private distribution)',
      ),
    );

    // Fail CLOSED on start failure too: a release build that cannot start the
    // RASP engine must not proceed unprotected.
    Talsec.instance.attachListener(callback);
    try {
      await Talsec.instance.start(config);
    } catch (e) {
      _compromised('Talsec failed to start: $e');
    }
  }

  void _compromised(String reason) {
    debugPrint('[DeviceIntegrity] FATAL: $reason');
    isDeviceCompromisedGlobally = true;
    ref.read(deviceCompromisedProvider.notifier).state = true;
  }
}

/// A boolean state indicating whether a Sybil threat (root/emulator) was detected.
/// The dashboard will watch this and hard-lock if true.
final deviceCompromisedProvider = StateProvider<bool>((ref) => false);

/// Global flag for stateless services like CryptoSigner to check.
bool isDeviceCompromisedGlobally = false;

final deviceIntegrityServiceProvider = Provider<DeviceIntegrityService>((ref) {
  return DeviceIntegrityService(ref);
});
