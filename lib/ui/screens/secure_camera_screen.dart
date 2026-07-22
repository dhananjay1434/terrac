import 'dart:async';
import 'dart:io';

import 'package:camera/camera.dart';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../services/secure_capture_service.dart';
import '../design/premium_field_components.dart';
import '../design/tokens.dart';

/// V8 Part 4 (O) — whether [SecureCameraScreen] captures a still or a short
/// video clip. Photo mode pops a [SecureCaptureResult]; video mode pops a
/// [SecureVideoCaptureResult] (`Navigator.pop<T>` is chosen at the push
/// call-site, so the same screen widget serves both).
enum SecureCaptureMode { photo, video }

/// =============================================================================
/// SecureCameraScreen  (Prompt 3 — Task 2)
/// =============================================================================
/// Full-screen `CameraPreview` that BYPASSES the native gallery entirely.
///
///   • ResolutionPreset.medium  (per spec — 2G-friendly).
///   • Image format YUV420 → JPEG re-encode at q=70 (handled in service layer).
///   • Returns a [SecureCaptureResult] via Navigator.pop when capture succeeds.
///   • Returns null on cancel / fatal error.
///
/// Usage:
///   final result = await Navigator.of(context).push`<SecureCaptureResult>`(
///     MaterialPageRoute(builder: (_) => const SecureCameraScreen()),
///   );
/// =============================================================================
class SecureCameraScreen extends ConsumerStatefulWidget {
  const SecureCameraScreen({
    super.key,
    this.preferFrontCamera = false,
    this.captureMode = SecureCaptureMode.photo,
    this.parcelBoundaryRing,
  });

  final bool preferFrontCamera;
  final SecureCaptureMode captureMode;

  /// Deferred R4 — the batch's parcel boundary ring (GeoJSON-order [lon,
  /// lat] pairs), when available, so the already-built geofence gate in
  /// [SecureCaptureService.capture] can evaluate. Null when no geometry is
  /// cached for this parcel (flag off, or not yet fetched) — capture
  /// proceeds ungated in that case (grandfathered).
  final List<List<double>>? parcelBoundaryRing;

  @override
  ConsumerState<SecureCameraScreen> createState() => _SecureCameraScreenState();
}

class _SecureCameraScreenState extends ConsumerState<SecureCameraScreen> {
  CameraController? _controller;
  Future<void>? _initFuture;
  bool _capturing = false;
  String? _errorMessage;
  CaptureErrorKind _errorKind = CaptureErrorKind.other;
  late CameraLensDirection _currentDirection;

  /// V8 Part 4 (M) — in-app capture review. Set right after a successful
  /// capture; the operator must explicitly confirm before this pops back to
  /// the caller (or discard + retake). Rendered from the SANDBOXED file the
  /// capture service already wrote — never the OS gallery/DCIM.
  SecureCaptureResult? _pendingReview;

  /// V8 Part 4 (O) — video mode state: recording flag, wall-clock start (for
  /// the elapsed-time readout + duration passed to the service on stop), and
  /// the resulting clip pending confirm/retake.
  bool _recording = false;
  DateTime? _recordStart;
  Timer? _elapsedTimer;
  Duration _elapsed = Duration.zero;
  SecureVideoCaptureResult? _pendingVideoReview;

  @override
  void initState() {
    super.initState();
    _currentDirection = widget.preferFrontCamera
        ? CameraLensDirection.front
        : CameraLensDirection.back;
    _initFuture = _bootstrap();
  }

  Future<void> _bootstrap() async {
    try {
      await ref.read(secureCaptureServiceProvider).ensurePermissions();
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        throw SecureCaptureException('No cameras available on this device.');
      }
      final selectedCamera = cameras.firstWhere(
        (c) => c.lensDirection == _currentDirection,
        orElse: () => cameras.first,
      );
      final controller = CameraController(
        selectedCamera,
        ResolutionPreset.medium, // <-- per spec
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );
      await controller.initialize();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      setState(() => _controller = controller);
    } catch (e) {
      if (mounted) setState(() => _errorMessage = e.toString());
    }
  }

  @override
  void dispose() {
    _elapsedTimer?.cancel();
    _controller?.dispose();
    super.dispose();
  }

  Future<void> _flipCamera() async {
    if (_capturing || _controller == null) return;
    final oldController = _controller;
    setState(() {
      _controller = null; // hide preview
    });
    await oldController?.dispose();

    setState(() {
      _currentDirection = _currentDirection == CameraLensDirection.back
          ? CameraLensDirection.front
          : CameraLensDirection.back;
      _initFuture = _bootstrap();
    });
  }

  void _retry() {
    setState(() {
      _errorMessage = null;
      _errorKind = CaptureErrorKind.other;
      _capturing = false;
      _controller = null;
    });
    _initFuture = _bootstrap();
  }

  Future<void> _onShutter() async {
    if (widget.captureMode == SecureCaptureMode.video) {
      return _toggleVideoRecording();
    }
    final controller = _controller;
    if (controller == null || _capturing) return;
    setState(() => _capturing = true);
    try {
      final result = await ref
          .read(secureCaptureServiceProvider)
          .capture(
            controller: controller,
            parcelBoundaryRing: widget.parcelBoundaryRing,
          );
      if (!mounted) return;
      // V8 Part 4 (M): review before committing — do NOT pop yet.
      setState(() {
        _capturing = false;
        _pendingReview = result;
      });
    } on SecureCaptureException catch (e) {
      debugPrint('[SecureCameraScreen] capture failed: $e');
      if (mounted) {
        setState(() {
          _capturing = false;
          _errorMessage = e.message;
          _errorKind = e.kind;
        });
      }
    } catch (e) {
      debugPrint('[SecureCameraScreen] capture failed: $e');
      if (mounted) {
        setState(() {
          _capturing = false;
          _errorMessage = e.toString();
        });
      }
    }
  }

  /// V8 Part 4 (O) — first tap starts recording (and an elapsed-time timer
  /// that auto-stops at the service's duration cap); second tap (or the
  /// auto-stop) hands off to [_stopVideoRecording].
  Future<void> _toggleVideoRecording() async {
    final controller = _controller;
    if (controller == null || _capturing) return;
    if (_recording) {
      await _stopVideoRecording();
      return;
    }
    setState(() => _capturing = true);
    try {
      await ref
          .read(secureCaptureServiceProvider)
          .startVideoRecording(controller: controller);
      if (!mounted) return;
      _recordStart = DateTime.now();
      setState(() {
        _capturing = false;
        _recording = true;
        _elapsed = Duration.zero;
      });
      _elapsedTimer = Timer.periodic(const Duration(milliseconds: 200), (_) {
        if (!mounted || _recordStart == null) return;
        final elapsed = DateTime.now().difference(_recordStart!);
        setState(() => _elapsed = elapsed);
        if (elapsed >= SecureCaptureService.kMaxVideoDuration) {
          _stopVideoRecording();
        }
      });
    } on SecureCaptureException catch (e) {
      if (mounted) {
        setState(() {
          _capturing = false;
          _errorMessage = e.message;
          _errorKind = e.kind;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _capturing = false;
          _errorMessage = e.toString();
        });
      }
    }
  }

  Future<void> _stopVideoRecording() async {
    final controller = _controller;
    final start = _recordStart;
    _elapsedTimer?.cancel();
    _elapsedTimer = null;
    if (controller == null || start == null || !_recording) return;
    final recordedDuration = DateTime.now().difference(start);
    setState(() {
      _recording = false;
      _recordStart = null;
      _capturing = true;
    });
    try {
      final result = await ref
          .read(secureCaptureServiceProvider)
          .stopVideoRecording(
            controller: controller,
            recordedDuration: recordedDuration,
          );
      if (!mounted) return;
      setState(() {
        _capturing = false;
        _pendingVideoReview = result;
      });
    } on SecureCaptureException catch (e) {
      if (mounted) {
        setState(() {
          _capturing = false;
          _errorMessage = e.message;
          _errorKind = e.kind;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _capturing = false;
          _errorMessage = e.toString();
        });
      }
    }
  }

  /// Discard the pending video (best-effort delete of the sandboxed file)
  /// and return to the live preview for another attempt.
  Future<void> _retakeVideo() async {
    final pending = _pendingVideoReview;
    if (pending == null) return;
    try {
      final f = File(pending.sandboxPath);
      if (await f.exists()) await f.delete();
    } catch (e) {
      debugPrint('[SecureCameraScreen] video retake cleanup failed: $e');
    }
    if (!mounted) return;
    setState(() => _pendingVideoReview = null);
  }

  void _confirmUseVideo() {
    final pending = _pendingVideoReview;
    if (pending == null) return;
    Navigator.of(context).pop<SecureVideoCaptureResult>(pending);
  }

  /// Discard the pending capture (best-effort delete of the SANDBOXED file —
  /// never touches DCIM, since the file never left the sandbox) and return to
  /// the live camera preview for another attempt.
  Future<void> _retakePhoto() async {
    final pending = _pendingReview;
    if (pending == null) return;
    try {
      final f = File(pending.sandboxPath);
      if (await f.exists()) await f.delete();
    } catch (e) {
      debugPrint('[SecureCameraScreen] retake cleanup failed (non-fatal): $e');
    }
    if (!mounted) return;
    setState(() => _pendingReview = null);
  }

  void _confirmUsePhoto() {
    final pending = _pendingReview;
    if (pending == null) return;
    Navigator.of(context).pop<SecureCaptureResult>(pending);
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: FutureBuilder<void>(
          future: _initFuture,
          builder: (context, _) {
            if (_pendingReview != null) {
              return _CaptureReviewView(
                result: _pendingReview!,
                onRetake: _retakePhoto,
                onUsePhoto: _confirmUsePhoto,
              );
            }
            if (_pendingVideoReview != null) {
              return _VideoReviewView(
                result: _pendingVideoReview!,
                onRetake: _retakeVideo,
                onUseVideo: _confirmUseVideo,
              );
            }
            if (_errorMessage != null) {
              return _ErrorView(
                message: _errorMessage!,
                kind: _errorKind,
                onRetry: _retry,
                onClose: () => Navigator.of(context).pop(),
              );
            }
            final controller = _controller;
            if (controller == null || !controller.value.isInitialized) {
              return Center(child: CircularProgressIndicator(color: t.accent));
            }
            return Stack(
              children: [
                Positioned.fill(child: CameraPreview(controller)),
                // Crosshair / scope overlay for the moisture meter
                Positioned.fill(
                  child: IgnorePointer(
                    child: CustomPaint(
                      painter: _ReticulePainter(color: t.accent),
                    ),
                  ),
                ),
                // Header
                Align(
                  alignment: Alignment.topCenter,
                  child: Container(
                    color: Colors.black.withValues(alpha: 0.55),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 24,
                      vertical: 16,
                    ),
                    child: Row(
                      children: [
                        InkWell(
                          onTap: () => Navigator.of(context).pop(),
                          child: const Padding(
                            padding: EdgeInsets.all(8),
                            child: Icon(
                              Icons.close,
                              color: Colors.white,
                              size: 22,
                            ),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Text(
                            widget.captureMode == SecureCaptureMode.video
                                ? (_recording
                                      ? 'RECORDING // ${_elapsed.inSeconds}s / '
                                            '${SecureCaptureService.kMaxVideoDuration.inSeconds}s'
                                      : 'SECURE VIDEO // SHA-256')
                                : 'SECURE CAPTURE // EXIF + SHA-256',
                            style: Theme.of(context).textTheme.titleMedium!
                                .copyWith(color: Colors.white),
                          ),
                        ),
                        const SizedBox(width: 16),
                        InkWell(
                          onTap: _flipCamera,
                          child: const Padding(
                            padding: EdgeInsets.all(8),
                            child: Icon(
                              Icons.flip_camera_ios,
                              color: Colors.white,
                              size: 24,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                // Shutter
                Align(
                  alignment: Alignment.bottomCenter,
                  child: Container(
                    color: Colors.black.withValues(alpha: 0.55),
                    padding: const EdgeInsets.all(32),
                    child: GestureDetector(
                      onTap: _onShutter,
                      child: Semantics(
                        identifier: 'secure-shutter-btn',
                        button: true,
                        enabled: !_capturing,
                        child: Container(
                          width: 86,
                          height: 86,
                          decoration: BoxDecoration(
                            color: _recording
                                ? t.danger
                                : (_capturing ? t.surfaceRaised : t.accent),
                            border: Border.all(color: Colors.black, width: 6),
                          ),
                          alignment: Alignment.center,
                          child: _capturing
                              ? CircularProgressIndicator(
                                  color: t.accent,
                                  strokeWidth: 3,
                                )
                              : Icon(
                                  widget.captureMode == SecureCaptureMode.video
                                      ? (_recording
                                            ? Icons.stop
                                            : Icons.videocam)
                                      : Icons.camera_alt,
                                  color: t.onAccent,
                                  size: 36,
                                ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({
    required this.message,
    required this.kind,
    required this.onRetry,
    required this.onClose,
  });
  final String message;
  final CaptureErrorKind kind;
  final VoidCallback onRetry;
  final VoidCallback onClose;

  String get _title => switch (kind) {
    CaptureErrorKind.locationServiceOff => 'LOCATION SERVICES OFF',
    CaptureErrorKind.locationPermissionDenied => 'LOCATION PERMISSION DENIED',
    CaptureErrorKind.locationPermissionPermanent =>
      'LOCATION BLOCKED — APP SETTINGS',
    CaptureErrorKind.cameraUnavailable => 'CAMERA UNAVAILABLE',
    CaptureErrorKind.tooBlurry => 'IMAGE TOO BLURRY',
    CaptureErrorKind.other => 'CAPTURE ERROR',
  };

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final showLocationSettings = kind == CaptureErrorKind.locationServiceOff;
    final showAppSettings =
        kind == CaptureErrorKind.locationPermissionPermanent;

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              InkWell(
                onTap: onClose,
                child: const Padding(
                  padding: EdgeInsets.all(8),
                  child: Icon(Icons.close, color: Colors.white, size: 22),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  _title,
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge!.copyWith(color: t.danger),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          PremiumFieldPanel(
            accentBorderColor: t.danger,
            child: Text(
              message,
              style: t.metadata.copyWith(color: t.textPrimary),
            ),
          ),
          const SizedBox(height: 32),
          PremiumFieldButton(
            label: 'RETRY',
            testId: 'capture-retry-btn',
            state: FieldButtonState.hiVis,
            onPressed: onRetry,
          ),
          if (showLocationSettings) ...[
            const SizedBox(height: 16),
            PremiumFieldButton(
              label: 'OPEN LOCATION SETTINGS',
              testId: 'open-location-settings-btn',
              state: FieldButtonState.go,
              onPressed: () async {
                // Best-effort: opens the Location settings screen on Android,
                // a generic Settings dialog on iOS.
                await Geolocator.openLocationSettings();
              },
            ),
          ],
          if (showAppSettings) ...[
            const SizedBox(height: 16),
            PremiumFieldButton(
              label: 'OPEN APP SETTINGS',
              testId: 'open-app-settings-btn',
              state: FieldButtonState.go,
              onPressed: () async {
                await openAppSettings();
              },
            ),
          ],
        ],
      ),
    );
  }
}

/// V8 Part 4 (M) — in-app capture review: confirm/retake before the capture
/// is committed to the caller. Renders the SANDBOXED file directly (the same
/// path the outbox will later hash+upload) — never the OS gallery/DCIM, so
/// review adds usability without weakening the hash-as-proof/sandbox model.
class _CaptureReviewView extends StatelessWidget {
  const _CaptureReviewView({
    required this.result,
    required this.onRetake,
    required this.onUsePhoto,
  });

  final SecureCaptureResult result;
  final VoidCallback onRetake;
  final VoidCallback onUsePhoto;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: double.infinity,
          color: Colors.black.withValues(alpha: 0.55),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          child: Text(
            'REVIEW CAPTURE',
            style: Theme.of(
              context,
            ).textTheme.titleMedium!.copyWith(color: Colors.white),
          ),
        ),
        if (result.geofenceWarning)
          Container(
            width: double.infinity,
            color: Colors.orange.withValues(alpha: 0.85),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Semantics(
              identifier: 'capture-geofence-warning',
              child: const Text(
                'This GPS fix looks outside the registered parcel boundary. '
                'You can still use this photo — it will be reviewed.',
                style: TextStyle(color: Colors.black, fontSize: 13),
              ),
            ),
          ),
        Expanded(
          child: Semantics(
            identifier: 'capture-review-image',
            image: true,
            child: Image.file(
              File(result.sandboxPath),
              fit: BoxFit.contain,
              width: double.infinity,
            ),
          ),
        ),
        Container(
          width: double.infinity,
          color: Colors.black.withValues(alpha: 0.55),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
          child: Row(
            children: [
              Expanded(
                child: PremiumFieldButton(
                  label: 'RETAKE',
                  testId: 'capture-review-retake-btn',
                  state: FieldButtonState.hiVis,
                  onPressed: onRetake,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: PremiumFieldButton(
                  label: 'USE PHOTO',
                  testId: 'capture-review-use-btn',
                  state: FieldButtonState.go,
                  onPressed: onUsePhoto,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// V8 Part 4 (O) — video review: confirm/retake before committing a clip.
/// No `video_player` dependency was pulled in for a preview — the clip is
/// already sandboxed+hashed by this point, so review shows the evidence
/// summary (duration, size, GPS) rather than a scrubber.
class _VideoReviewView extends StatelessWidget {
  const _VideoReviewView({
    required this.result,
    required this.onRetake,
    required this.onUseVideo,
  });

  final SecureVideoCaptureResult result;
  final VoidCallback onRetake;
  final VoidCallback onUseVideo;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final seconds = (result.durationMs / 1000).toStringAsFixed(1);
    final kb = (result.fileSizeBytes / 1024).toStringAsFixed(0);
    return Column(
      children: [
        Container(
          width: double.infinity,
          color: Colors.black.withValues(alpha: 0.55),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          child: Text(
            'REVIEW CLIP',
            style: Theme.of(
              context,
            ).textTheme.titleMedium!.copyWith(color: Colors.white),
          ),
        ),
        Expanded(
          child: Center(
            child: Semantics(
              identifier: 'video-review-summary',
              child: PremiumFieldPanel(
                accentBorderColor: t.accent,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.videocam, color: t.accent, size: 48),
                    const SizedBox(height: 12),
                    Text(
                      '$seconds s · $kb kB',
                      style: t.metadata.copyWith(color: t.textPrimary),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'SHA-256 ${result.sha256Hash.substring(0, 12)}…',
                      style: t.metadata.copyWith(color: t.textSecondary),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
        Container(
          width: double.infinity,
          color: Colors.black.withValues(alpha: 0.55),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
          child: Row(
            children: [
              Expanded(
                child: PremiumFieldButton(
                  label: 'RETAKE',
                  testId: 'video-review-retake-btn',
                  state: FieldButtonState.hiVis,
                  onPressed: onRetake,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: PremiumFieldButton(
                  label: 'USE CLIP',
                  testId: 'video-review-use-btn',
                  state: FieldButtonState.go,
                  onPressed: onUseVideo,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ReticulePainter extends CustomPainter {
  _ReticulePainter({required this.color});
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;
    final w = size.width;
    final h = size.height;
    final boxW = w * 0.7;
    final boxH = h * 0.35;
    final rect = Rect.fromLTWH((w - boxW) / 2, (h - boxH) / 2, boxW, boxH);
    canvas.drawRect(rect, paint);
    // Corner ticks
    const t = 16.0;
    canvas.drawLine(rect.topLeft, rect.topLeft + const Offset(t, 0), paint);
    canvas.drawLine(rect.topLeft, rect.topLeft + const Offset(0, t), paint);
    canvas.drawLine(rect.topRight, rect.topRight + const Offset(-t, 0), paint);
    canvas.drawLine(rect.topRight, rect.topRight + const Offset(0, t), paint);
    canvas.drawLine(
      rect.bottomLeft,
      rect.bottomLeft + const Offset(t, 0),
      paint,
    );
    canvas.drawLine(
      rect.bottomLeft,
      rect.bottomLeft + const Offset(0, -t),
      paint,
    );
    canvas.drawLine(
      rect.bottomRight,
      rect.bottomRight + const Offset(-t, 0),
      paint,
    );
    canvas.drawLine(
      rect.bottomRight,
      rect.bottomRight + const Offset(0, -t),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter old) => false;
}
