import 'package:flutter/material.dart';

import '../design/tokens.dart';

/// The one card/panel surface. Replaces PremiumFieldPanel.
///
/// A raised paper plane defined by its 1.5px hairline border, not by a shadow
/// (soft shadows die in direct sun; the border always reads). Minimal by
/// design: generous internal padding, no gradient, no elevation.
class DmrvPanel extends StatelessWidget {
  const DmrvPanel({
    super.key,
    required this.child,
    this.padding,
    this.accent = false,
  });

  final Widget child;
  final EdgeInsets? padding;

  /// When true the border uses the accent color (for the one "focus" panel on
  /// a screen). Otherwise the neutral hairline.
  final bool accent;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Container(
      width: double.infinity,
      padding: padding ?? EdgeInsets.all(t.gapL),
      decoration: BoxDecoration(
        color: t.surfaceRaised,
        borderRadius: BorderRadius.circular(t.radiusM),
        border: Border.all(
          color: accent ? t.accent : t.border,
          width: 1.5,
        ),
      ),
      child: child,
    );
  }
}
