import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freerasp/freerasp.dart';

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
        packageName: 'com.kontiki.dmrv',
        signingCertHashes: [certHash],
      ),
      iosConfig: IOSConfig(bundleIds: ['com.kontiki.dmrv'], teamId: iosTeam),
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
      onUnofficialStore: () => _compromised('Unofficial Store Detected'),
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
