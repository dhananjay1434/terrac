import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:camera/camera.dart';
import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'geofence_check.dart';
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
class _ReencodeResult {
  const _ReencodeResult(this.jpegBytes, this.blurVariance);
  final Uint8List jpegBytes;
  final double blurVariance;
}

_ReencodeResult _reencodeJpegInIsolate(Uint8List rawBytes) {
  final decoded = img.decodeImage(rawBytes);
  if (decoded == null) throw Exception('Decoded image was null.');
  final blurVariance = SecureCaptureService.computeBlurVariance(decoded);
  final encoded = Uint8List.fromList(img.encodeJpg(decoded, quality: 70));
  return _ReencodeResult(encoded, blurVariance);
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
    this.blurVariance,
    this.geofenceWarning = false,
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

  /// V8 Part 4 (E) — Laplacian-variance sharpness score of the captured
  /// frame (higher = sharper); null only if the isolate somehow failed to
  /// compute it. Purely informational unless `kBlurGateEnforced` is on, in
  /// which case a too-low score aborts the capture before this result ever
  /// exists (see [SecureCaptureService.capture]).
  final double? blurVariance;

  /// V8 Part 4 (E) — true if a parcel boundary was supplied to [capture] AND
  /// the GPS fix fell outside it (+ buffer). This WARNS the operator; it
  /// never blocks the capture (the authoritative check is server-side).
  /// Always false when no boundary was supplied — most call sites today
  /// don't yet thread the batch's parcel geometry down to the camera
  /// screen, so this is inert for them (documented gap, not fabricated
  /// enforcement).
  final bool geofenceWarning;

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

/// V8 Part 4 (O) — result of a video capture. Mirrors [SecureCaptureResult]
/// but there is no EXIF sink for video, so GPS/timestamp travel as plain
/// signed fields on the media-insert payload instead of being burned into
/// the file (see PyrolysisWriter.insertMediaCaptureAndEnqueue callers).
class SecureVideoCaptureResult {
  const SecureVideoCaptureResult({
    required this.sandboxPath,
    required this.sha256Hash,
    required this.fileSizeBytes,
    required this.durationMs,
    required this.recordedAtIso,
    required this.latitude,
    required this.longitude,
    required this.isMocked,
  });

  final String sandboxPath;
  final String sha256Hash;
  final int fileSizeBytes;
  final int durationMs;
  final String recordedAtIso;
  final double latitude;
  final double longitude;
  final bool isMocked;

  @override
  String toString() =>
      'SecureVideoCaptureResult('
      'path=$sandboxPath, sha256=$sha256Hash, bytes=$fileSizeBytes, '
      'durationMs=$durationMs, recordedAt=$recordedAtIso, '
      'lat=$latitude, lon=$longitude, mocked=$isMocked)';
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
  tooBlurry,
  other,
}

/// V8 Part 4 (E) — capture-integrity env gates, same `bool.fromEnvironment`
/// pattern as `DMRV_DEMO_MODE` elsewhere in this codebase. Both default OFF:
/// these are new UI-blocking/warning gates with no field validation of the
/// blur threshold yet, so shipping them pre-armed risks blocking legitimate
/// captures on an uncalibrated cutoff. Flip on via
/// `--dart-define=DMRV_BLUR_GATE_ENFORCED=true` once field-tuned.
const bool kBlurGateEnforced = bool.fromEnvironment(
  'DMRV_BLUR_GATE_ENFORCED',
  defaultValue: false,
);
const bool kGeofenceCaptureEnforced = bool.fromEnvironment(
  'DMRV_GEOFENCE_CAPTURE',
  defaultValue: false,
);

/// PR-7 — the blur-gate DECISION, extracted pure so the ON-path (which the
/// dart-define consts above can't exercise in a normal `flutter test` run —
/// they're compile-time and default false) is unit-testable by passing
/// `enforced` explicitly. `capture()` below calls this with the real
/// [kBlurGateEnforced] const; tests call it with `enforced: true`.
bool shouldRejectForBlur({
  required bool enforced,
  required double variance,
  required double threshold,
}) {
  return enforced && variance < threshold;
}

/// PR-7 — the geofence-warning DECISION, extracted pure for the same reason
/// as [shouldRejectForBlur]. `isPointNearPolygon` itself is already
/// thoroughly tested (geofence_check_test.dart); this covers the
/// enforcement + "ring supplied at all" wiring around it.
bool geofenceWarningFor({
  required bool enforced,
  required List<List<double>>? parcelBoundaryRing,
  required double longitude,
  required double latitude,
  required double bufferMeters,
}) {
  if (!enforced || parcelBoundaryRing == null) return false;
  return !isPointNearPolygon(
    longitude,
    latitude,
    parcelBoundaryRing,
    bufferMeters: bufferMeters,
  );
}

class SecureCaptureService {
  SecureCaptureService(this._locationService);
  final ILocationService _locationService;

  /// Maximum on-disk size we will accept post-compression (2G payload budget).
  static const int kMaxBytes = 500 * 1024;

  /// JPEG quality used for the re-encode pass.
  static const int kJpegQuality = 70;

  /// V8 Part 4 (O) — video evidence caps (2G payload budget: short clips
  /// only, no compression pass since `camera` records H.264 already).
  static const Duration kMaxVideoDuration = Duration(seconds: 15);
  static const int kMaxVideoBytes = 8 * 1024 * 1024;

  /// V8 Part 4 (E) — below this Laplacian variance a frame is judged too
  /// blurry to be usable evidence. Chosen conservatively from the classic
  /// "variance of Laplacian" blur-detection literature; not yet calibrated
  /// against real kiln-site photos, hence [kBlurGateEnforced] defaults off.
  static const double kBlurVarianceThreshold = 60.0;

  /// V8 Part 4 (E) — on-device geofence warning buffer, meters. Matches the
  /// backend's default corroboration buffer (see geometry.py) so an
  /// operator standing right at the parcel edge doesn't get warned when the
  /// server itself would accept the same fix.
  static const double kGeofenceBufferMeters = 10.0;

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
  ///
  /// [parcelBoundaryRing] — V8 Part 4 (E): optional GeoJSON-order `[lon,
  /// lat]` exterior ring for the batch's registered parcel. When supplied
  /// AND [kGeofenceCaptureEnforced] is on, a GPS fix that falls outside the
  /// ring (+ [kGeofenceBufferMeters]) sets [SecureCaptureResult.geofenceWarning]
  /// — a WARNING surfaced to the operator, never a block. Omitted by most
  /// call sites today (see [SecureCaptureResult.geofenceWarning] doc).
  Future<SecureCaptureResult> capture({
    required CameraController controller,
    List<List<double>>? parcelBoundaryRing,
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

    // 3) Re-encode at q=70 to enforce <500kb 2G budget (offloaded to isolate),
    //    also scoring sharpness (V8 Part 4 (E)) while the decoded image is
    //    already in hand, rather than decoding twice.
    final rawBytes = await raw.readAsBytes();
    final reencoded = await compute(_reencodeJpegInIsolate, rawBytes);
    final encoded = reencoded.jpegBytes;
    final blurVariance = reencoded.blurVariance;

    if (shouldRejectForBlur(
      enforced: kBlurGateEnforced,
      variance: blurVariance,
      threshold: kBlurVarianceThreshold,
    )) {
      // Reject BEFORE anything is written to the sandbox — no orphan file,
      // no wasted GPS fix. The plugin's own temp copy is cleaned up below
      // exactly like the size-cap rejection path.
      try {
        final tmp = File(raw.path);
        if (await tmp.exists()) await tmp.delete();
      } catch (_) {}
      throw SecureCaptureException(
        'Image too blurry to use as evidence (sharpness $blurVariance < '
        '$kBlurVarianceThreshold). Hold steady and retake.',
        kind: CaptureErrorKind.tooBlurry,
      );
    }

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

    // V8 Part 4 (E) — geofence-to-parcel warning (non-blocking; see doc).
    final geofenceWarning = geofenceWarningFor(
      enforced: kGeofenceCaptureEnforced,
      parcelBoundaryRing: parcelBoundaryRing,
      longitude: pos.longitude,
      latitude: pos.latitude,
      bufferMeters: kGeofenceBufferMeters,
    );

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
      blurVariance: blurVariance,
      geofenceWarning: geofenceWarning,
    );
  }

  // ---------------------------------------------------------------------------
  // V8 Part 4 (O) — Video capture
  // ---------------------------------------------------------------------------

  /// Begin recording. The caller (UI) is responsible for enforcing
  /// [kMaxVideoDuration] in wall-clock time and calling [stopVideoRecording]
  /// — the cap is re-checked server-side of this call too, via
  /// [assertVideoWithinCaps], so a UI bug can't ship an oversized clip.
  Future<void> startVideoRecording({required CameraController controller}) async {
    if (isDeviceCompromisedGlobally) {
      throw SecureCaptureException(
        'Device integrity compromised. Capture aborted.',
      );
    }
    if (!controller.value.isInitialized) {
      throw SecureCaptureException('Camera not initialized.');
    }
    await controller.startVideoRecording();
  }

  /// Stop recording, sandbox the artifact (never DCIM), hash it, enforce the
  /// duration/size caps, and stamp a GPS fix — same anti-fraud shape as
  /// [capture], adapted for a file format that has no EXIF sink.
  Future<SecureVideoCaptureResult> stopVideoRecording({
    required CameraController controller,
    required Duration recordedDuration,
  }) async {
    final XFile raw = await controller.stopVideoRecording();

    final supportDir = await getApplicationSupportDirectory();
    final evidenceDir = Directory(p.join(supportDir.path, 'evidence'));
    if (!await evidenceDir.exists()) {
      await evidenceDir.create(recursive: true);
    }
    final sandboxPath = p.join(evidenceDir.path, '${_uuid.v4()}.mp4');

    final rawFile = File(raw.path);
    await rawFile.copy(sandboxPath);
    try {
      if (await rawFile.exists()) {
        await rawFile.delete();
        debugPrint('[SecureCapture] video temp file deleted: ${raw.path}');
      }
    } on FileSystemException catch (e) {
      debugPrint('[SecureCapture] WARNING: video temp deletion failed: $e');
      await _appendToCleanupManifest(raw.path);
    }

    final sandboxFile = File(sandboxPath);
    final sizeBytes = await sandboxFile.length();

    try {
      assertVideoWithinCaps(sizeBytes, recordedDuration);
    } on SecureCaptureException {
      // Reject: don't leave an over-cap artifact sitting in the sandbox.
      try {
        await sandboxFile.delete();
      } catch (_) {}
      rethrow;
    }

    final pos = await _locationService.acquirePosition();
    final finalBytes = await sandboxFile.readAsBytes();
    final hashHex = sha256.convert(finalBytes).toString();

    return SecureVideoCaptureResult(
      sandboxPath: sandboxPath,
      sha256Hash: hashHex,
      fileSizeBytes: finalBytes.length,
      durationMs: recordedDuration.inMilliseconds,
      recordedAtIso: DateTime.now().toUtc().toIso8601String(),
      latitude: pos.latitude,
      longitude: pos.longitude,
      isMocked: pos.isMocked,
    );
  }

  /// Pure cap check — testable without a real camera/recording. Throws
  /// [SecureCaptureException] the moment either the duration or size budget
  /// is exceeded.
  @visibleForTesting
  static void assertVideoWithinCaps(int sizeBytes, Duration duration) {
    if (duration > kMaxVideoDuration) {
      throw SecureCaptureException(
        'Video exceeded the ${kMaxVideoDuration.inSeconds}s cap '
        '(${duration.inSeconds}s recorded).',
      );
    }
    if (sizeBytes > kMaxVideoBytes) {
      throw SecureCaptureException(
        'Video exceeded ${kMaxVideoBytes ~/ (1024 * 1024)}MB cap ($sizeBytes B).',
      );
    }
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

  /// V8 Part 4 (E) — "variance of Laplacian" sharpness score. Downsamples to
  /// a fixed width first (sharpness signal survives a modest resize; this
  /// keeps the isolate cost bounded regardless of the camera's native
  /// resolution), converts to grayscale, convolves the discrete Laplacian
  /// kernel `[[0,1,0],[1,-4,1],[0,1,0]]`, and returns the variance of the
  /// response. Higher = sharper; a near-uniform (blurry) image collapses
  /// toward 0.
  static double computeBlurVariance(img.Image image) {
    final small = image.width > 200
        ? img.copyResize(image, width: 200)
        : image;
    final gray = img.grayscale(small);
    final w = gray.width, h = gray.height;
    if (w < 3 || h < 3) return 0;

    var sum = 0.0;
    var sumSq = 0.0;
    var count = 0;
    for (var y = 1; y < h - 1; y++) {
      for (var x = 1; x < w - 1; x++) {
        final c = gray.getPixel(x, y).r;
        final up = gray.getPixel(x, y - 1).r;
        final down = gray.getPixel(x, y + 1).r;
        final left = gray.getPixel(x - 1, y).r;
        final right = gray.getPixel(x + 1, y).r;
        final value = (up + down + left + right - 4 * c).toDouble();
        sum += value;
        sumSq += value * value;
        count++;
      }
    }
    if (count == 0) return 0;
    final mean = sum / count;
    return (sumSq / count) - (mean * mean);
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
