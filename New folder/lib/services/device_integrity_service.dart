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
    
    // TEMPORARY: Bypass Talsec completely in Debug/Demo mode to prevent it from blocking initialization on some devices.
    if (kDebugMode || const bool.fromEnvironment('DMRV_DEMO_MODE')) {
        debugPrint("[DeviceIntegrity] Bypassing FreeRASP initialization in Demo Mode.");
        return;
    }

    // Talsec configuration.
    // We provide dummy values for androidConfig/iosConfig to allow initialization.
    // In production, these should match the real app package/bundle ID.
    final config = TalsecConfig(
      androidConfig: AndroidConfig(
        packageName: 'com.kontiki.dmrv',
        signingCertHashes: [const String.fromEnvironment('TALSEC_SIGNING_CERT_HASH')],
      ),
      iosConfig: IOSConfig(
        bundleIds: ['com.kontiki.dmrv'],
        teamId: const String.fromEnvironment('TALSEC_IOS_TEAM_ID'),
      ),
      watcherMail: 'security@kontiki.test',
      isProd: !kDebugMode,
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

    Talsec.instance.attachListener(callback);
    try {
      await Talsec.instance.start(config);
    } catch (e, st) {
      debugPrint('Talsec initialization failed (this is normal in debug/demo without certs): $e');
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
