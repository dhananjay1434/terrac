import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'tokens.dart';

/// Button states for PremiumFieldButton. Preserved from the legacy design
/// system for call-site compatibility across all step screens. (These screens
/// are migrating to [DmrvButton]; until then this widget is token-skinned so it
/// matches the rest of the India surface.)
enum FieldButtonState { go, stop, locked, hiVis }

// =============================================================================
// PremiumFieldPanel — the card chassis. Token-skinned: raised paper surface
// defined by a hairline border (no shadow — shadows die in sunlight).
// =============================================================================
class PremiumFieldPanel extends StatelessWidget {
  const PremiumFieldPanel({
    super.key,
    required this.child,
    this.accentBorderColor,
    this.padding = const EdgeInsets.all(20),
  });

  final Widget child;

  /// When provided, becomes a 2px accent border (flags the panel as focused /
  /// verified / blocked). When null, the neutral hairline border is used.
  final Color? accentBorderColor;

  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final bool hasAccent = accentBorderColor != null;
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: t.surfaceRaised,
        borderRadius: BorderRadius.circular(t.radiusM),
        border: Border.all(
          color: hasAccent ? accentBorderColor! : t.border,
          width: hasAccent ? 2 : 1.5,
        ),
      ),
      child: child,
    );
  }
}

// =============================================================================
// PremiumFieldButton — 64px glove-target CTA, token-skinned. Heavy-impact
// haptic fires BEFORE onPressed so the user feels confirmation even if the
// callback is async.
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

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final bool isLocked = state == FieldButtonState.locked;
    final bool enabled = onPressed != null && !isLocked;

    final (Color bg, Color fg) = switch (state) {
      // "go" and "hiVis" are the primary action → safety-orange, like the
      // dashboard's primary DmrvButton.
      FieldButtonState.go => (t.accent, t.onAccent),
      FieldButtonState.hiVis => (t.accent, t.onAccent),
      FieldButtonState.stop => (t.danger, t.onDanger),
      FieldButtonState.locked => (
        t.textPrimary.withValues(alpha: 0.08),
        t.textDisabled,
      ),
    };

    return Semantics(
      identifier: testId ?? label,
      button: true,
      enabled: enabled,
      child: Material(
        color: bg,
        borderRadius: BorderRadius.circular(t.radiusM),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: enabled
              ? () {
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
              style: t.buttonLabel.copyWith(color: fg),
            ),
          ),
        ),
      ),
    );
  }
}

// =============================================================================
// PremiumScreenHeader — back chevron + numbered step badge + screen title.
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
    final t = context.tokens;
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: t.gapL, vertical: t.gapM),
      child: Row(
        children: [
          Semantics(
            identifier: backTestId ?? 'header.back',
            button: true,
            enabled: onBack != null,
            child: Material(
              color: t.surfaceRaised,
              borderRadius: BorderRadius.circular(t.radiusM),
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
                    borderRadius: BorderRadius.circular(t.radiusM),
                    border: Border.all(color: t.border, width: 1.5),
                  ),
                  child: Icon(
                    Icons.arrow_back_ios_new,
                    size: 20,
                    color: t.textPrimary,
                  ),
                ),
              ),
            ),
          ),
          SizedBox(width: t.gapM),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: t.accent,
              borderRadius: BorderRadius.circular(t.radiusS),
            ),
            child: Text(
              'STEP $stepNumber',
              style: t.chipLabel.copyWith(color: t.onAccent),
            ),
          ),
          SizedBox(width: t.gapM),
          Expanded(
            child: Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: t.blockHeader.copyWith(color: t.textPrimary),
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

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final (Color bg, Color fg) = switch (status) {
      PremiumChipStatus.verified => (t.success, t.onSuccess),
      PremiumChipStatus.pending => (
        t.accent.withValues(alpha: 0.14),
        t.accentText,
      ),
      PremiumChipStatus.locked => (
        t.textPrimary.withValues(alpha: 0.08),
        t.textSecondary,
      ),
      PremiumChipStatus.error => (t.danger, t.onDanger),
    };

    return Container(
      height: 28,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(t.radiusL),
      ),
      child: Text(label.toUpperCase(), style: t.chipLabel.copyWith(color: fg)),
    );
  }
}

// =============================================================================
// PremiumInputField — numeric/text input, token-skinned. Used for moisture %
// readings, scale weights, GPS coords, batch IDs, etc.
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

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final bool hasError = errorText != null && errorText!.isNotEmpty;

    OutlineInputBorder borderOf(Color c, double w) => OutlineInputBorder(
      borderRadius: BorderRadius.circular(t.radiusM),
      borderSide: BorderSide(color: c, width: w),
    );

    final baseBorder = borderOf(t.border, 1.5);
    final focusBorder = borderOf(t.accent, 2);
    final errorBorder = borderOf(t.danger, 2);

    final Widget field = TextField(
      controller: controller,
      onChanged: onChanged,
      keyboardType: keyboardType,
      inputFormatters: inputFormatters,
      enabled: enabled,
      cursorColor: t.accent,
      style: t.numericMedium.copyWith(
        fontSize: 20,
        fontWeight: FontWeight.w400,
        color: t.textPrimary,
      ),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: t.numericMedium.copyWith(
          fontSize: 20,
          fontWeight: FontWeight.w400,
          color: t.textDisabled,
        ),
        suffixIcon: suffix,
        filled: true,
        fillColor: t.surfaceRaised,
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
        Text(errorText!, style: t.metadata.copyWith(color: t.danger)),
      ],
    );
  }
}
