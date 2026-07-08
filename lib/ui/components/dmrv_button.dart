import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../design/tokens.dart';

/// The one button in the app. Replaces RuggedButton + PremiumFieldButton.
///
/// Visual: a flat "key-cap" — a face plate sitting on a solid hard bottom edge
/// (a ~28%-darker shade of the face), no shadow, no gradient, no glow (all die
/// in sunlight). Pressing translates the face down onto the edge, so depth is
/// communicated by geometry, not blur — like a physical machine button.
///
/// Feedback: `HapticFeedback.heavyImpact()` fires on press-DOWN (the only thing
/// a gloved hand feels, and it lands even if the async work is slow); the
/// `onPressed` callback fires on release inside the bounds.
///
/// All colors come from [DmrvTokens], so the button is automatically correct in
/// every skin. Passing `onPressed: null` renders the disabled state.
enum DmrvButtonVariant { primary, success, danger, neutral }

class DmrvButton extends StatefulWidget {
  const DmrvButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.variant = DmrvButtonVariant.primary,
    this.icon,
    this.testId,
    this.fullWidth = true,
    this.minHeight = 64,
  });

  final String label;

  /// Null => disabled (flat, muted, no haptic, not tappable).
  final VoidCallback? onPressed;
  final DmrvButtonVariant variant;
  final IconData? icon;

  /// Sets the `Semantics(identifier:)` for widget tests / a11y.
  final String? testId;
  final bool fullWidth;
  final double minHeight;

  @override
  State<DmrvButton> createState() => _DmrvButtonState();
}

class _DmrvButtonState extends State<DmrvButton> {
  bool _pressed = false;

  bool get _enabled => widget.onPressed != null;

  ({Color face, Color edge, Color label}) _palette(DmrvTokens t) {
    switch (widget.variant) {
      case DmrvButtonVariant.primary:
        return (face: t.accent, edge: _darken(t.accent), label: t.onAccent);
      case DmrvButtonVariant.success:
        return (face: t.success, edge: _darken(t.success), label: t.onSuccess);
      case DmrvButtonVariant.danger:
        return (face: t.danger, edge: _darken(t.danger), label: t.onDanger);
      case DmrvButtonVariant.neutral:
        return (
          face: t.surfaceRaised,
          edge: t.borderStrong,
          label: t.textPrimary,
        );
    }
  }

  static Color _darken(Color c, [double amount = 0.28]) {
    final hsl = HSLColor.fromColor(c);
    return hsl.withLightness((hsl.lightness - amount).clamp(0.0, 1.0)).toColor();
  }

  void _down(_) {
    if (!_enabled) return;
    HapticFeedback.heavyImpact();
    setState(() => _pressed = true);
  }

  void _up(_) {
    if (!_enabled) return;
    setState(() => _pressed = false);
    widget.onPressed!.call();
  }

  void _cancel() {
    if (_pressed) setState(() => _pressed = false);
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final radius = BorderRadius.circular(t.radiusM);
    final pal = _palette(t);

    final Color face = _enabled
        ? pal.face
        : t.textPrimary.withValues(alpha: 0.08);
    final Color edge = _enabled ? pal.edge : Colors.transparent;
    final Color labelColor = _enabled ? pal.label : t.textDisabled;
    final double edgeThickness = !_enabled ? 0 : (_pressed ? 1 : 4);

    final child = Semantics(
      identifier: widget.testId,
      button: true,
      enabled: _enabled,
      label: widget.label,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapDown: _down,
        onTapUp: _up,
        onTapCancel: _cancel,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 60),
          curve: Curves.easeOut,
          // The outer fill IS the hard edge; its bottom padding reveals it
          // under the face. Pressing shrinks it 4->1, sinking the key-cap.
          padding: EdgeInsets.only(bottom: edgeThickness),
          decoration: BoxDecoration(color: edge, borderRadius: radius),
          child: Container(
            constraints: BoxConstraints(minHeight: widget.minHeight),
            alignment: Alignment.center,
            padding: EdgeInsets.symmetric(horizontal: t.gapL),
            decoration: BoxDecoration(color: face, borderRadius: radius),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (widget.icon != null) ...[
                  Icon(widget.icon, color: labelColor, size: 26),
                  SizedBox(width: t.gapM),
                ],
                Flexible(
                  child: Text(
                    widget.label,
                    textAlign: TextAlign.center,
                    style: t.buttonLabel.copyWith(color: labelColor),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );

    return widget.fullWidth
        ? SizedBox(width: double.infinity, child: child)
        : child;
  }
}
