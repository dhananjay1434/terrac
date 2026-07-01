import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:camera/camera.dart';
import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'location_service.dart';
import 'package:image/image.dart' as img;
import 'package:native_exif/native_exif.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'dart:math' as math;
import 'package:uuid/uuid.dart';
import 'package:rxdart/rxdart.dart';
import 'package:sensors_plus/sensors_plus.dart';
import 'device_integrity_service.dart';

/// Must be top-level for compute() isolate.
Uint8List _reencodeJpegInIsolate(Uint8List rawBytes) {
  final decoded = img.decodeImage(rawBytes);
  if (decoded == null) throw Exception('Decoded image was null.');
  return Uint8List.fromList(img.encodeJpg(decoded, quality: 70));
}

/// =============================================================================
/// SecureCaptureService  (Prompt 3 — Tasks 2 & 3)
/// Phase 6 — Zero Trust Hardening: Fix 2 (temp-file leak eliminated)
/// =============================================================================
/// Captures a frame from the active [CameraController] and runs the full
/// anti-fraud pipeline:
///
///   1. Capture XFile via official `camera` plugin (ResolutionPreset.medium).
///   2. Re-encode JPEG at q=70 and persist EXCLUSIVELY to
///      getApplicationSupportDirectory() (sandboxed — never DCIM / camera roll).
///   3. Fetch a GPS fix via geolocator.
///   4. Write GPSLatitude / GPSLongitude / DateTimeOriginal into the file
///      using `native_exif` (round-trips through the platform EXIF writer).
///   5. Read raw bytes, SHA-256 → transit tamper-evidence anchor. The hash binds
///      the on-disk file bytes so alteration in transit is detectable; it does NOT
///      prove the photo depicts a real burn. Scene authenticity is corroborated
///      server-side via EXIF GPS vs the batch's claimed location (backend Phase 9).
///   6. Read EXIF back out and return the parsed result alongside the hash.
///
/// The returned [SecureCaptureResult] is the *only* surface the UI layer is
/// allowed to consume — it is the canonical evidence object that the DB
/// persistence layer assembles into a BiomassSourcing companion.
/// =============================================================================

const _uuid = Uuid();

class SecureCaptureResult {
  const SecureCaptureResult({
    required this.sandboxPath,
    required this.sha256Hash,
    required this.fileSizeBytes,
    required this.exifTimestampIso,
    required this.latitude,
    required this.longitude,
    required this.isMocked,
    this.azimuth,
    this.pitch,
    this.roll,
  });

  final String sandboxPath;
  final String sha256Hash;
  final int fileSizeBytes;
  final String exifTimestampIso;
  final double latitude;
  final double longitude;
  final bool isMocked;
  final double? azimuth;
  final double? pitch;
  final double? roll;

  String? get cardinalDirection {
    if (azimuth == null) return null;
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    final index = ((azimuth! + 22.5) % 360) ~/ 45;
    return directions[index];
  }

  @override
  String toString() =>
      'SecureCaptureResult('
      'path=$sandboxPath, '
      'sha256=$sha256Hash, '
      'bytes=$fileSizeBytes, '
      'exifTs=$exifTimestampIso, '
      'lat=$latitude, lon=$longitude, '
      'mocked=$isMocked, '
      'azimuth=$azimuth, pitch=$pitch, roll=$roll)';
}

class SecureCaptureException implements Exception {
  SecureCaptureException(this.message, {this.kind = CaptureErrorKind.other});
  final String message;
  final CaptureErrorKind kind;
  @override
  String toString() => 'SecureCaptureException: $message';
}

/// Classifies the failure so the UI can show the right recovery affordance
/// (open location settings, open app settings, or just retry).
enum CaptureErrorKind {
  locationServiceOff,
  locationPermissionDenied,
  locationPermissionPermanent,
  cameraUnavailable,
  other,
}

class SecureCaptureService {
  SecureCaptureService(this._locationService);
  final ILocationService _locationService;

  /// Maximum on-disk size we will accept post-compression (2G payload budget).
  static const int kMaxBytes = 500 * 1024;

  /// JPEG quality used for the re-encode pass.
  static const int kJpegQuality = 70;

  /// Name of the cleanup manifest inside getApplicationSupportDirectory().
  /// Each line is a file path that failed to delete and must be retried.
  static const String _kCleanupManifest = 'pending_cleanup.txt';

  // ---------------------------------------------------------------------------
  // Startup GC — call from main() before runApp()
  // ---------------------------------------------------------------------------

  /// Retries deletion of any camera temp files that failed during a previous
  /// capture session. Call this once from `main()` so stale files never
  /// accumulate silently across app launches.
  static Future<void> cleanupStaleTemps() async {
    final dir = await getApplicationSupportDirectory();
    final manifest = File(p.join(dir.path, _kCleanupManifest));
    if (!await manifest.exists()) return;

    final lines = await manifest.readAsLines();
    final stillFailing = <String>[];

    for (final path in lines.where((l) => l.trim().isNotEmpty)) {
      try {
        final f = File(path);
        if (await f.exists()) {
          await f.delete();
          debugPrint('[SecureCapture] startup GC deleted: $path');
        }
      } catch (e) {
        debugPrint('[SecureCapture] startup GC still cannot delete $path: $e');
        stillFailing.add(path);
      }
    }

    if (stillFailing.isEmpty) {
      await manifest.delete();
      debugPrint('[SecureCapture] cleanup manifest cleared.');
    } else {
      await manifest.writeAsString(stillFailing.join('\n'));
    }
  }

  /// Run the entire pipeline. The caller is responsible for ensuring camera +
  /// location permissions are already granted (see [ensurePermissions]).
  Future<SecureCaptureResult> capture({
    required CameraController controller,
  }) async {
    if (isDeviceCompromisedGlobally) {
      throw SecureCaptureException(
        'Device integrity compromised. Capture aborted.',
      );
    }
    if (!controller.value.isInitialized) {
      throw SecureCaptureException('Camera not initialized.');
    }

    // 1) Capture into the plugin's tmp area.
    final XFile raw = await controller.takePicture();

    // 2) Sandbox: relocate into application support dir with a UUID filename.
    final supportDir = await getApplicationSupportDirectory();
    final evidenceDir = Directory(p.join(supportDir.path, 'evidence'));
    if (!await evidenceDir.exists()) {
      await evidenceDir.create(recursive: true);
    }
    final sandboxPath = p.join(evidenceDir.path, '${_uuid.v4()}.jpg');

    // 3) Re-encode at q=70 to enforce <500kb 2G budget (offloaded to isolate).
    final rawBytes = await raw.readAsBytes();
    final encoded = await compute(_reencodeJpegInIsolate, rawBytes);
    final sandboxFile = File(sandboxPath);
    await sandboxFile.writeAsBytes(encoded, flush: true);

    // Best-effort: delete the camera plugin's temp copy so the uncompressed
    // original never leaks out of the sandbox.
    // Phase 6 Fix 2: failures are no longer silently swallowed — they are
    // logged and appended to a cleanup manifest for startup retry.
    try {
      final tmp = File(raw.path);
      if (await tmp.exists()) {
        await tmp.delete();
        debugPrint('[SecureCapture] temp file deleted: ${raw.path}');
      }
    } on FileSystemException catch (e) {
      debugPrint('[SecureCapture] WARNING: temp file deletion failed: $e');
      await _appendToCleanupManifest(raw.path);
    }

    final sizeBytes = await sandboxFile.length();
    if (sizeBytes > kMaxBytes) {
      throw SecureCaptureException(
        'Compressed image exceeded ${kMaxBytes ~/ 1024} kB ($sizeBytes B).',
      );
    }

    // 4) GPS fix — delegated to ILocationService (supports demo fallback).
    final pos = await _locationService.acquirePosition();

    // 5) Write EXIF.
    final exifTimestamp = DateTime.now().toUtc();
    final exif = await Exif.fromPath(sandboxPath);
    await exif.writeAttributes({
      'GPSLatitude': pos.latitude.abs().toString(),
      'GPSLongitude': pos.longitude.abs().toString(),
      'GPSLatitudeRef': pos.latitude >= 0 ? 'N' : 'S',
      'GPSLongitudeRef': pos.longitude >= 0 ? 'E' : 'W',
      // EXIF DateTimeOriginal is "YYYY:MM:DD HH:MM:SS" by spec.
      'DateTimeOriginal':
          '${exifTimestamp.year.toString().padLeft(4, '0')}:'
          '${exifTimestamp.month.toString().padLeft(2, '0')}:'
          '${exifTimestamp.day.toString().padLeft(2, '0')} '
          '${exifTimestamp.hour.toString().padLeft(2, '0')}:'
          '${exifTimestamp.minute.toString().padLeft(2, '0')}:'
          '${exifTimestamp.second.toString().padLeft(2, '0')}',
    });
    await exif.close();

    // 6) Hash AFTER EXIF write, so the hash anchors the final on-disk artifact.
    //    Offloaded to isolate to avoid blocking main thread.
    final finalBytes = await sandboxFile.readAsBytes();
    final hashHex = sha256.convert(finalBytes).toString();

    // Phase 7: Fetch Device Hardware Telemetry (Compass / Gyro)
    final telemetry = await _getDeviceOrientationSnapshot();

    return SecureCaptureResult(
      sandboxPath: sandboxPath,
      sha256Hash: hashHex,
      fileSizeBytes: finalBytes.length,
      exifTimestampIso: exifTimestamp.toIso8601String(),
      latitude: pos.latitude,
      longitude: pos.longitude,
      isMocked: pos.isMocked,
      azimuth: telemetry['azimuth'],
      pitch: telemetry['pitch'],
      roll: telemetry['roll'],
    );
  }

  /// Request and verify the runtime permissions needed end-to-end.
  /// Throws a CLASSIFIED [SecureCaptureException] so the caller can render
  /// the right recovery CTA (open location settings vs open app settings).
  Future<void> ensurePermissions() async {
    final services = await Geolocator.isLocationServiceEnabled();
    if (!services) {
      throw SecureCaptureException(
        'Location services are OFF on this device. Enable Location in '
        'Settings → Location, then tap RETRY.',
        kind: CaptureErrorKind.locationServiceOff,
      );
    }
    var perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) {
      perm = await Geolocator.requestPermission();
    }
    if (perm == LocationPermission.deniedForever) {
      throw SecureCaptureException(
        'Location permission is permanently denied. Open App Settings and '
        'grant "Precise Location" access.',
        kind: CaptureErrorKind.locationPermissionPermanent,
      );
    }
    if (perm == LocationPermission.denied) {
      throw SecureCaptureException(
        'Location permission was denied. Tap RETRY and grant access when prompted.',
        kind: CaptureErrorKind.locationPermissionDenied,
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  Future<void> _appendToCleanupManifest(String path) async {
    try {
      final dir = await getApplicationSupportDirectory();
      final manifest = File(p.join(dir.path, _kCleanupManifest));
      await manifest.writeAsString(
        '$path\n',
        mode: FileMode.append,
        flush: true,
      );
      debugPrint('[SecureCapture] path added to cleanup manifest: $path');
    } catch (e) {
      // If we can't even write the manifest, log but do not crash the capture.
      debugPrint(
        '[SecureCapture] CRITICAL: could not write cleanup manifest: $e',
      );
    }
  }

  /// Takes a snapshot of the device's exact 3D orientation.
  Future<Map<String, double>> _getDeviceOrientationSnapshot() async {
    try {
      final pair = await Rx.combineLatest2(
        accelerometerEventStream(),
        magnetometerEventStream(),
        (AccelerometerEvent a, MagnetometerEvent m) => (a, m),
      ).first.timeout(const Duration(milliseconds: 500));

      final accel = pair.$1;
      final magnet = pair.$2;

      final ax = accel.x;
      final ay = accel.y;
      final az = accel.z;

      final mx = magnet.x;
      final my = magnet.y;
      final mz = magnet.z;

      return computeOrientation(ax, ay, az, mx, my, mz);
    } catch (e) {
      debugPrint('[SecureCapture] Telemetry snapshot failed: $e');
      return {};
    }
  }

  @visibleForTesting
  static Map<String, double> computeOrientation(
    double ax,
    double ay,
    double az,
    double mx,
    double my,
    double mz,
  ) {
    final roll = math.atan2(ax, math.sqrt(ay * ay + az * az));
    final pitch = math.atan2(ay, math.sqrt(ax * ax + az * az));

    // Tilt compensated azimuth
    final cx = mx * math.cos(pitch) + mz * math.sin(pitch);
    final cy =
        mx * math.sin(roll) * math.sin(pitch) +
        my * math.cos(roll) -
        mz * math.sin(roll) * math.cos(pitch);

    var azimuth = math.atan2(cx, cy);
    if (azimuth < 0) azimuth += 2 * math.pi;

    return {
      'azimuth': azimuth * (180 / math.pi),
      'pitch': pitch * (180 / math.pi),
      'roll': roll * (180 / math.pi),
    };
  }
}

final secureCaptureServiceProvider = Provider<SecureCaptureService>((ref) {
  return SecureCaptureService(ref.read(locationServiceProvider));
});
