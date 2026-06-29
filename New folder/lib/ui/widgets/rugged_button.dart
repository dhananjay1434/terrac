import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../design/farmer_theme.dart';

/// Visual + interaction variants for [RuggedButton], each mapped to a token
/// from the "Rugged Field Tool" [FarmerTheme] palette.
enum RuggedButtonVariant { primary, success, danger, disabled }

/// RuggedButton — the giant, glove-friendly, full-width CTA of the field flow.
///
/// It belongs to the same family as [PremiumFieldButton] and reuses its proven
/// interaction chassis verbatim:
///   * a >=64px touch target (gloves dampen 48px taps),
///   * [HapticFeedback.heavyImpact] fired BEFORE [onPressed] so the user feels
///     confirmation even when the callback is async,
///   * a [Semantics] identifier for driven UI flows / tests.
///
/// The one deliberate difference is palette. [PremiumFieldButton] hardcodes the
/// light theme tokens (cobalt / gold / titanium); RuggedButton paints the dark
/// FarmerTheme tokens (neonYellow / fieldGreen / crimsonRed / fogWhite). We do
/// NOT tint or modify [PremiumFieldButton] — it stays exactly as-is so every
/// existing step screen keeps compiling.
class RuggedButton extends StatelessWidget {
  const RuggedButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.variant = RuggedButtonVariant.primary,
    this.semanticId,
  });

  final String label;
  final VoidCallback? onPressed;
  final RuggedButtonVariant variant;
  final String? semanticId;

  @override
  Widget build(BuildContext context) {
    final bool isDisabled = variant == RuggedButtonVariant.disabled;
    final bool enabled = onPressed != null && !isDisabled;

    final (Color bg, Color fg) = switch (variant) {
      RuggedButtonVariant.primary => (
        FarmerTheme.neonYellow,
        FarmerTheme.deepSlate,
      ),
      RuggedButtonVariant.success => (
        FarmerTheme.fieldGreen,
        FarmerTheme.deepSlate,
      ),
      RuggedButtonVariant.danger => (
        FarmerTheme.crimsonRed,
        FarmerTheme.pureAlbedo,
      ),
      RuggedButtonVariant.disabled => (
        FarmerTheme.fogWhite,
        FarmerTheme.deepSlate40,
      ),
    };

    return Semantics(
      label: semanticId ?? label,
      button: true,
      enabled: enabled,
      child: ConstrainedBox(
        constraints: const BoxConstraints(
          minHeight: 64,
          minWidth: double.infinity,
        ),
        child: Material(
          color: bg,
          borderRadius: BorderRadius.circular(12),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: enabled
                ? () {
                    // Heavy impact is the only level reliably felt through
                    // industrial leather gloves; fire it before the callback.
                    HapticFeedback.heavyImpact();
                    onPressed!.call();
                  }
                : null,
            child: Container(
              constraints: const BoxConstraints(minHeight: 64, minWidth: 64),
              alignment: Alignment.center,
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Text(
                label,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontFamily: 'SpaceGrotesk',
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.5,
                  color: fg,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
