import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../design/premium_field_components.dart';
import '../design/tokens.dart';

/// V8 Part 5 (L) — generic on-device QR/barcode scanner. Pops the raw decoded
/// string via `Navigator.pop<String>` on the FIRST successful decode (or null
/// on cancel), same pattern as [SecureCameraScreen] popping a capture result.
/// Deliberately dumb: it does not know or care what format the caller
/// expects (enrollment payload, bare token, plain URL) — that parsing stays
/// in the caller's existing pure functions (e.g. `parseEnrollmentQr`), so
/// this screen adds zero new parsing logic to get wrong.
class QrScanScreen extends StatefulWidget {
  const QrScanScreen({super.key, this.title = 'SCAN QR CODE'});

  final String title;

  @override
  State<QrScanScreen> createState() => _QrScanScreenState();
}

class _QrScanScreenState extends State<QrScanScreen> {
  final MobileScannerController _controller = MobileScannerController(
    formats: const [BarcodeFormat.qrCode],
  );
  bool _handled = false;
  String? _errorMessage;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onDetect(BarcodeCapture capture) {
    if (_handled) return;
    for (final barcode in capture.barcodes) {
      final value = barcode.rawValue;
      if (value != null && value.trim().isNotEmpty) {
        _handled = true;
        Navigator.of(context).pop<String>(value.trim());
        return;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Stack(
          children: [
            Positioned.fill(
              child: MobileScanner(
                controller: _controller,
                onDetect: _onDetect,
                errorBuilder: (context, error) {
                  // Camera unavailable/permission denied — never crash the
                  // screen; show a retry-or-cancel affordance instead.
                  WidgetsBinding.instance.addPostFrameCallback((_) {
                    if (mounted) {
                      setState(() => _errorMessage = error.errorDetails?.message ?? error.errorCode.name);
                    }
                  });
                  return const SizedBox.shrink();
                },
              ),
            ),
            Positioned.fill(
              child: IgnorePointer(
                child: CustomPaint(painter: _ScanFramePainter(color: t.accent)),
              ),
            ),
            Align(
              alignment: Alignment.topCenter,
              child: Container(
                width: double.infinity,
                color: Colors.black.withValues(alpha: 0.55),
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                child: Row(
                  children: [
                    InkWell(
                      onTap: () => Navigator.of(context).pop<String>(null),
                      child: const Padding(
                        padding: EdgeInsets.all(8),
                        child: Icon(Icons.close, color: Colors.white, size: 22),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Text(
                        widget.title,
                        style: Theme.of(context).textTheme.titleMedium!
                            .copyWith(color: Colors.white),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (_errorMessage != null)
              Align(
                alignment: Alignment.bottomCenter,
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: PremiumFieldPanel(
                    accentBorderColor: t.danger,
                    child: Text(
                      'Camera unavailable: $_errorMessage',
                      style: t.metadata.copyWith(color: t.textPrimary),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ScanFramePainter extends CustomPainter {
  _ScanFramePainter({required this.color});
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke;
    final side = size.width * 0.65;
    final rect = Rect.fromCenter(
      center: Offset(size.width / 2, size.height / 2),
      width: side,
      height: side,
    );
    const t = 24.0;
    canvas.drawLine(rect.topLeft, rect.topLeft + const Offset(t, 0), paint);
    canvas.drawLine(rect.topLeft, rect.topLeft + const Offset(0, t), paint);
    canvas.drawLine(rect.topRight, rect.topRight + const Offset(-t, 0), paint);
    canvas.drawLine(rect.topRight, rect.topRight + const Offset(0, t), paint);
    canvas.drawLine(rect.bottomLeft, rect.bottomLeft + const Offset(t, 0), paint);
    canvas.drawLine(rect.bottomLeft, rect.bottomLeft + const Offset(0, -t), paint);
    canvas.drawLine(rect.bottomRight, rect.bottomRight + const Offset(-t, 0), paint);
    canvas.drawLine(rect.bottomRight, rect.bottomRight + const Offset(0, -t), paint);
  }

  @override
  bool shouldRepaint(covariant _ScanFramePainter old) => old.color != color;
}
