import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'app_theme.dart';

/// Button states for PremiumFieldButton. Preserved from the legacy design
/// system for call-site compatibility across all step screens.
enum FieldButtonState { go, stop, locked, hiVis }

// =============================================================================
// PremiumFieldPanel — flat card chassis on pureAlbedo with subtle cobalt edge.
// Replaces the legacy FieldPanel (dark olive surface, sharp corners) with a
// premium light-theme surface tuned for direct-sunlight readability.
// =============================================================================
class PremiumFieldPanel extends StatelessWidget {
  const PremiumFieldPanel({
    super.key,
    required this.child,
    this.accentBorderColor,
    this.padding = const EdgeInsets.all(20),
  });

  final Widget child;

  /// When provided, becomes the panel border at 2px (used to flag a panel as
  /// verified/yieldGold or pending/cobaltShield). When null, the panel uses
  /// the default 1px cobaltShield-20% edge.
  final Color? accentBorderColor;

  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final bool hasAccent = accentBorderColor != null;
    final Color borderColor = hasAccent
        ? accentBorderColor!
        : AppTheme.cobaltShield20;
    final double borderWidth = hasAccent ? 2 : 1;

    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: AppTheme.pureAlbedo,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: borderColor, width: borderWidth),
        boxShadow: [
          BoxShadow(
            color: AppTheme.black06,
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: child,
    );
  }
}

// =============================================================================
// PremiumFieldButton — 64px glove-target CTA. Reuses FieldButtonState so
// existing screen call sites compile unchanged. Heavy-impact haptic fires
// BEFORE onPressed so the user gets confirmation even if onPressed is async.
// =============================================================================
class PremiumFieldButton extends StatelessWidget {
  const PremiumFieldButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.state = FieldButtonState.hiVis,
    this.testId,
  });

  final String label;
  final VoidCallback? onPressed;
  final FieldButtonState state;
  final String? testId;

  static const Color _stopRed = Color(0xFFDC2626);

  @override
  Widget build(BuildContext context) {
    final bool isLocked = state == FieldButtonState.locked;
    final bool enabled = onPressed != null && !isLocked;

    final (Color bg, Color fg) = switch (state) {
      FieldButtonState.go => (AppTheme.cobaltShield, AppTheme.pureAlbedo),
      FieldButtonState.locked => (
        AppTheme.tacticalTitanium,
        AppTheme.armorSlate40,
      ),
      FieldButtonState.stop => (_stopRed, AppTheme.pureAlbedo),
      FieldButtonState.hiVis => (AppTheme.yieldGold, AppTheme.armorSlate),
    };

    return Semantics(
      identifier: testId ?? label,
      button: true,
      enabled: enabled,
      child: Material(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: enabled
              ? () {
                  // Industrial gloves dampen vibration; heavyImpact is the
                  // only level the user reliably feels through the leather.
                  HapticFeedback.heavyImpact();
                  onPressed!.call();
                }
              : null,
          child: Container(
            constraints: const BoxConstraints(minHeight: 64),
            alignment: Alignment.center,
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Text(
              label,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontFamily: 'SpaceGrotesk',
                fontSize: 16,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.5,
              ).copyWith(color: fg),
            ),
          ),
        ),
      ),
    );
  }
}

// =============================================================================
// PremiumScreenHeader — back chevron + numbered step badge + screen title.
// Drop-in replacement for the inline Row( back, title, ... ) pattern used at
// the top of every step screen.
// =============================================================================
class PremiumScreenHeader extends StatelessWidget {
  const PremiumScreenHeader({
    super.key,
    required this.stepNumber,
    required this.title,
    this.onBack,
    this.backTestId,
  });

  final String stepNumber; // e.g. "01", "02"
  final String title;
  final VoidCallback? onBack;
  final String? backTestId;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Semantics(
            identifier: backTestId ?? 'header.back',
            button: true,
            enabled: onBack != null,
            child: Material(
              color: AppTheme.pureAlbedo,
              borderRadius: BorderRadius.circular(10),
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: onBack == null
                    ? null
                    : () {
                        HapticFeedback.heavyImpact();
                        onBack!.call();
                      },
                child: Container(
                  width: 48,
                  height: 48,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.black06,
                        blurRadius: 6,
                        offset: const Offset(0, 1),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.arrow_back_ios_new,
                    size: 20,
                    color: AppTheme.armorSlate,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: AppTheme.cobaltShield,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              'STEP $stepNumber',
              style: const TextStyle(
                fontFamily: 'SpaceGrotesk',
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: AppTheme.pureAlbedo,
                letterSpacing: 0.8,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// PremiumStatusChip — compact uppercase pill for inline status markers.
// =============================================================================
enum PremiumChipStatus { verified, pending, locked, error }

class PremiumStatusChip extends StatelessWidget {
  const PremiumStatusChip({
    super.key,
    required this.label,
    required this.status,
  });

  final String label;
  final PremiumChipStatus status;

  static const Color _errorRed = Color(0xFFDC2626);

  @override
  Widget build(BuildContext context) {
    final (Color bg, Color fg) = switch (status) {
      PremiumChipStatus.verified => (AppTheme.yieldGold, AppTheme.armorSlate),
      PremiumChipStatus.pending => (
        AppTheme.cobaltShield15,
        AppTheme.cobaltShield,
      ),
      PremiumChipStatus.locked => (
        const Color(0xFFE2E8F0),
        AppTheme.armorSlate60,
      ),
      PremiumChipStatus.error => (_errorRed, AppTheme.pureAlbedo),
    };

    return Container(
      height: 28,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label.toUpperCase(),
        style: TextStyle(
          fontFamily: 'SpaceGrotesk',
          fontSize: 11,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.8,
          color: fg,
        ),
      ),
    );
  }
}

// =============================================================================
// PremiumInputField — SpaceMono numeric/text input on pureAlbedo. Used for
// moisture % readings, scale weights, GPS coords, batch IDs, etc.
// =============================================================================
class PremiumInputField extends StatelessWidget {
  const PremiumInputField({
    super.key,
    this.controller,
    this.hint,
    this.suffix,
    this.onChanged,
    this.semanticId,
    this.keyboardType,
    this.inputFormatters,
    this.errorText,
    this.enabled = true,
  });

  final TextEditingController? controller;
  final String? hint;
  final Widget? suffix;
  final ValueChanged<String>? onChanged;
  final String? semanticId;
  final TextInputType? keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final String? errorText;
  final bool enabled;

  static const Color _errorRed = Color(0xFFDC2626);

  @override
  Widget build(BuildContext context) {
    final bool hasError = errorText != null && errorText!.isNotEmpty;

    final OutlineInputBorder baseBorder = OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: BorderSide(color: AppTheme.cobaltShield20, width: 1),
    );

    final OutlineInputBorder focusBorder = OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: AppTheme.cobaltShield, width: 2),
    );

    final OutlineInputBorder errorBorder = OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: _errorRed, width: 2),
    );

    final Widget field = TextField(
      controller: controller,
      onChanged: onChanged,
      keyboardType: keyboardType,
      inputFormatters: inputFormatters,
      enabled: enabled,
      cursorColor: AppTheme.cobaltShield,
      style: const TextStyle(
        fontFamily: 'SpaceMono',
        fontSize: 20,
        fontWeight: FontWeight.w400,
        color: AppTheme.armorSlate,
      ),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: TextStyle(
          fontFamily: 'SpaceMono',
          fontSize: 20,
          fontWeight: FontWeight.w400,
          color: AppTheme.armorSlate35,
        ),
        suffixIcon: suffix,
        filled: true,
        fillColor: AppTheme.pureAlbedo,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 16,
        ),
        border: baseBorder,
        enabledBorder: hasError ? errorBorder : baseBorder,
        focusedBorder: hasError ? errorBorder : focusBorder,
        errorBorder: errorBorder,
        focusedErrorBorder: errorBorder,
      ),
    );

    final Widget input = semanticId == null
        ? field
        : Semantics(identifier: semanticId, textField: true, child: field);

    if (!hasError) return input;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        input,
        const SizedBox(height: 6),
        Text(
          errorText!,
          style: const TextStyle(
            fontFamily: 'SpaceMono',
            fontSize: 12,
            fontWeight: FontWeight.w400,
            color: _errorRed,
          ),
        ),
      ],
    );
  }
}
