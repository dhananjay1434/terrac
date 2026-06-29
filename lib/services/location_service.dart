import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'secure_capture_service.dart'; // for SecureCaptureException, CaptureErrorKind

/// Abstract interface for GPS position acquisition.
/// Production uses Geolocator. Demo mode uses hardcoded fallback.
abstract class ILocationService {
  /// Returns a [Position]. Throws [SecureCaptureException] if GPS is
  /// completely unavailable AND no fallback is configured.
  Future<Position> acquirePosition();
}

/// Production GPS service. Extracted verbatim from SecureCaptureService lines 191-209.
class GeolocatorLocationService implements ILocationService {
  @override
  Future<Position> acquirePosition() async {
    Position? pos;
    try {
      pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 12),
        ),
      );
    } catch (_) {
      // Slow or unavailable GPS — try the OS-cached fix before giving up.
      pos = await Geolocator.getLastKnownPosition();
    }
    if (pos == null) {
      throw SecureCaptureException(
        'Could not acquire a GPS fix. Step outside or wait a few seconds and retry.',
        kind: CaptureErrorKind.locationServiceOff,
      );
    }
    if (pos.isMocked && kReleaseMode) {
      throw SecureCaptureException(
        'Mock locations are not allowed. Disable "Mock location app" in '
        'Developer Options and retry.',
        kind: CaptureErrorKind.locationServiceOff,
      );
    }
    return pos;
  }
}

/// Demo-safe GPS service. Tries real GPS first, falls back to hardcoded
/// coordinates if the device is indoors (boardroom demo scenario).
class DemoLocationService implements ILocationService {
  @override
  Future<Position> acquirePosition() async {
    try {
      return await GeolocatorLocationService().acquirePosition();
    } catch (e) {
      debugPrint(
        '[DemoLocation] GPS unavailable ($e) — injecting demo coordinates.',
      );
      return Position(
        latitude: 28.6139,
        longitude: 77.2090,
        timestamp: DateTime.now(),
        accuracy: 5.0,
        altitude: 200.0,
        altitudeAccuracy: 0.0,
        heading: 0.0,
        headingAccuracy: 0.0,
        speed: 0.0,
        speedAccuracy: 0.0,

        isMocked: true,
      );
    }
  }
}

/// Riverpod provider. Injected via `--dart-define=DMRV_DEMO_MODE=true`.
final locationServiceProvider = Provider<ILocationService>((ref) {
  const isDemo = bool.fromEnvironment('DMRV_DEMO_MODE', defaultValue: false);
  if (kReleaseMode && isDemo) {
    throw StateError(
      'DMRV_DEMO_MODE is forbidden in release builds. '
      'Rebuild without --dart-define=DMRV_DEMO_MODE=true.',
    );
  }
  return isDemo ? DemoLocationService() : GeolocatorLocationService();
});
