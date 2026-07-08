import 'package:camera/camera.dart';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../services/secure_capture_service.dart';
import '../design/premium_field_components.dart';
import '../design/tokens.dart';

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
  const SecureCameraScreen({super.key, this.preferFrontCamera = false});

  final bool preferFrontCamera;

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
    final controller = _controller;
    if (controller == null || _capturing) return;
    setState(() => _capturing = true);
    try {
      final result = await ref
          .read(secureCaptureServiceProvider)
          .capture(controller: controller);
      if (!mounted) return;
      Navigator.of(context).pop<SecureCaptureResult>(result);
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

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: FutureBuilder<void>(
          future: _initFuture,
          builder: (context, _) {
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
                            'SECURE CAPTURE // EXIF + SHA-256',
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
                            color: _capturing ? t.surfaceRaised : t.accent,
                            border: Border.all(color: Colors.black, width: 6),
                          ),
                          alignment: Alignment.center,
                          child: _capturing
                              ? CircularProgressIndicator(
                                  color: t.accent,
                                  strokeWidth: 3,
                                )
                              : Icon(
                                  Icons.camera_alt,
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
