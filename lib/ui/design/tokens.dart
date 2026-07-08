import 'package:flutter/material.dart';

/// DmrvTokens — the single semantic design-token layer for the dMRV app.
///
/// Names describe FUNCTION, never a color. Screens read tokens through
/// `context.tokens`; they never name a hex value. This is the one place the
/// look of the whole app is decided, which is also what makes a second skin
/// (e.g. a Europe/Pro surface) a value-swap rather than a rewrite.
///
/// The one shipped instance today is [DmrvTokens.india] — the "paper, ink &
/// machinery" field skin from docs/UX_FIELD_THEME_SPEC.md: a warm sun-bleached
/// paper surface, carbon-ink text, safety-orange for the primary action,
/// tractor-green for confirmed, and stamp-ink blue for certified. It is built
/// for a gloved, low-literacy operator reading a cheap panel in direct sun —
/// so it is high-contrast and minimal, with no gradients, glows, or soft
/// shadows (all of which die in sunlight).
///
/// Every field is `required` (no defaults): adding a token without giving it a
/// value for every skin is a compile error, which is how we guarantee skins
/// stay complete as they multiply.
@immutable
class DmrvTokens extends ThemeExtension<DmrvTokens> {
  const DmrvTokens({
    required this.surface,
    required this.surfaceRaised,
    required this.chartPanel,
    required this.textPrimary,
    required this.textSecondary,
    required this.textDisabled,
    required this.accent,
    required this.accentText,
    required this.onAccent,
    required this.success,
    required this.onSuccess,
    required this.danger,
    required this.onDanger,
    required this.dangerSurface,
    required this.certified,
    required this.live,
    required this.border,
    required this.borderStrong,
    required this.radiusS,
    required this.radiusM,
    required this.radiusL,
    required this.gapS,
    required this.gapM,
    required this.gapL,
    required this.gapXL,
    required this.screenTitle,
    required this.blockHeader,
    required this.body,
    required this.bodyHindi,
    required this.numericHero,
    required this.numericMedium,
    required this.buttonLabel,
    required this.metadata,
    required this.chipLabel,
  });

  // ---- Surfaces ----
  final Color surface; // scaffold background
  final Color surfaceRaised; // cards / panels
  final Color chartPanel; // the single dark instrument panel (live temp chart)

  // ---- Content ----
  final Color textPrimary;
  final Color textSecondary;
  final Color textDisabled; // exempt from AA (disabled controls)

  // ---- Semantic states (one meaning each) ----
  final Color accent; // primary-action FILL ("do this next" / pending)
  final Color accentText; // the accent as TEXT/icon on the paper surface
  final Color onAccent; // label color ON an accent fill
  final Color success; // confirmed / locked / synced
  final Color onSuccess;
  final Color danger; // blocks-your-credit errors only
  final Color onDanger;
  final Color dangerSurface; // error-panel background
  final Color certified; // server-signed / issued only (the mohar / seal)
  final Color live; // active BLE / GPS indicator

  // ---- Structure ----
  final Color border;
  final Color borderStrong;
  final double radiusS, radiusM, radiusL; // 8 / 12 / 20
  final double gapS, gapM, gapL, gapXL; // 8 / 12 / 16 / 24

  // ---- Typography roles (function-named, not size-named) ----
  final TextStyle screenTitle,
      blockHeader,
      body,
      bodyHindi,
      numericHero,
      numericMedium,
      buttonLabel,
      metadata,
      chipLabel;

  /// India / field skin — "paper, ink & machinery".
  /// Contrast ratios in comments are computed WCAG 2.x against the noted
  /// surface (see docs/UX_FIELD_THEME_SPEC.md §1.5) and are re-asserted by
  /// test/design/tokens_contrast_test.dart.
  static const DmrvTokens india = DmrvTokens(
    // Ground
    surface: Color(0xFFECE7DC), // paper — high-albedo, warm, ~8% dimmer glare
    surfaceRaised: Color(0xFFF6F3EB), // paperRaised — cards; defined by border
    chartPanel: Color(0xFF26221C), // charcoal — the one dark panel
    // Content
    textPrimary: Color(0xFF211D16), // ink — 13.60:1 on paper
    textSecondary: Color(0xB8211D16), // ink @72% — 5.92:1 on paper
    textDisabled: Color(0x61211D16), // ink @38% — disabled only (AA-exempt)
    // Semantics
    accent: Color(0xFFE8590C), // machineOrange fill (safety orange)
    accentText: Color(0xFF9A3412), // orange as text/icon on paper — 5.93:1
    onAccent: Color(0xFF211D16), // ink on orange — 4.68:1 (never white, 3.58)
    success: Color(0xFF2E6B1F), // tractorGreen — 5.26:1 on paper
    onSuccess: Color(0xFFFFFFFF), // white on green fill — 6.48:1
    danger: Color(0xFFB91C1C), // hotIronRed — 5.25:1 on paper
    onDanger: Color(0xFFFFFFFF), // white on red fill — ~5.8:1
    dangerSurface: Color(
      0xFFF4E4E0,
    ), // warm light error wash (danger ~6:1 on it)
    certified: Color(0xFF2E3A8C), // sealBlue (the mohar) — 8.11:1 on paper
    live: Color(0xFF2E6B1F), // live indicator = tractorGreen dot
    // Structure
    border: Color(0x26211D16), // ink @15% — ruled-form lines
    borderStrong: Color(0x4D211D16), // ink @30%
    radiusS: 8,
    radiusM: 12,
    radiusL: 20,
    gapS: 8,
    gapM: 12,
    gapL: 16,
    gapXL: 24,
    // Type — one humanist superfamily (NotoSansDevanagari carries Latin too),
    // weights 400/700 only (the bundled set), tabular figures for readouts.
    screenTitle: TextStyle(
      fontFamily: 'NotoSansDevanagari',
      fontSize: 24,
      fontWeight: FontWeight.w700,
      height: 1.2,
    ),
    blockHeader: TextStyle(
      fontFamily: 'NotoSansDevanagari',
      fontSize: 20,
      fontWeight: FontWeight.w700,
      height: 1.2,
    ),
    body: TextStyle(
      fontFamily: 'NotoSansDevanagari',
      fontSize: 18,
      fontWeight: FontWeight.w400,
      height: 1.4,
    ),
    bodyHindi: TextStyle(
      fontFamily: 'NotoSansDevanagari',
      fontSize: 18,
      fontWeight: FontWeight.w400,
      height: 1.45,
    ),
    numericHero: TextStyle(
      fontFamily: 'NotoSansDevanagari',
      fontSize: 64,
      fontWeight: FontWeight.w700,
      height: 1.0,
      fontFeatures: [FontFeature.tabularFigures()],
    ),
    numericMedium: TextStyle(
      fontFamily: 'NotoSansDevanagari',
      fontSize: 28,
      fontWeight: FontWeight.w700,
      height: 1.05,
      fontFeatures: [FontFeature.tabularFigures()],
    ),
    buttonLabel: TextStyle(
      fontFamily: 'NotoSansDevanagari',
      fontSize: 18,
      fontWeight: FontWeight.w700,
      letterSpacing: 0.25,
    ),
    metadata: TextStyle(
      fontFamily: 'NotoSansDevanagari',
      fontSize: 16,
      fontWeight: FontWeight.w400,
    ),
    chipLabel: TextStyle(
      fontFamily: 'NotoSansDevanagari',
      fontSize: 13,
      fontWeight: FontWeight.w700,
      letterSpacing: 0.4,
    ),
  );

  @override
  DmrvTokens copyWith({
    Color? surface,
    Color? surfaceRaised,
    Color? chartPanel,
    Color? textPrimary,
    Color? textSecondary,
    Color? textDisabled,
    Color? accent,
    Color? accentText,
    Color? onAccent,
    Color? success,
    Color? onSuccess,
    Color? danger,
    Color? onDanger,
    Color? dangerSurface,
    Color? certified,
    Color? live,
    Color? border,
    Color? borderStrong,
    double? radiusS,
    double? radiusM,
    double? radiusL,
    double? gapS,
    double? gapM,
    double? gapL,
    double? gapXL,
    TextStyle? screenTitle,
    TextStyle? blockHeader,
    TextStyle? body,
    TextStyle? bodyHindi,
    TextStyle? numericHero,
    TextStyle? numericMedium,
    TextStyle? buttonLabel,
    TextStyle? metadata,
    TextStyle? chipLabel,
  }) {
    return DmrvTokens(
      surface: surface ?? this.surface,
      surfaceRaised: surfaceRaised ?? this.surfaceRaised,
      chartPanel: chartPanel ?? this.chartPanel,
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      textDisabled: textDisabled ?? this.textDisabled,
      accent: accent ?? this.accent,
      accentText: accentText ?? this.accentText,
      onAccent: onAccent ?? this.onAccent,
      success: success ?? this.success,
      onSuccess: onSuccess ?? this.onSuccess,
      danger: danger ?? this.danger,
      onDanger: onDanger ?? this.onDanger,
      dangerSurface: dangerSurface ?? this.dangerSurface,
      certified: certified ?? this.certified,
      live: live ?? this.live,
      border: border ?? this.border,
      borderStrong: borderStrong ?? this.borderStrong,
      radiusS: radiusS ?? this.radiusS,
      radiusM: radiusM ?? this.radiusM,
      radiusL: radiusL ?? this.radiusL,
      gapS: gapS ?? this.gapS,
      gapM: gapM ?? this.gapM,
      gapL: gapL ?? this.gapL,
      gapXL: gapXL ?? this.gapXL,
      screenTitle: screenTitle ?? this.screenTitle,
      blockHeader: blockHeader ?? this.blockHeader,
      body: body ?? this.body,
      bodyHindi: bodyHindi ?? this.bodyHindi,
      numericHero: numericHero ?? this.numericHero,
      numericMedium: numericMedium ?? this.numericMedium,
      buttonLabel: buttonLabel ?? this.buttonLabel,
      metadata: metadata ?? this.metadata,
      chipLabel: chipLabel ?? this.chipLabel,
    );
  }

  @override
  DmrvTokens lerp(DmrvTokens? other, double t) {
    if (other is! DmrvTokens) return this;
    return DmrvTokens(
      surface: Color.lerp(surface, other.surface, t)!,
      surfaceRaised: Color.lerp(surfaceRaised, other.surfaceRaised, t)!,
      chartPanel: Color.lerp(chartPanel, other.chartPanel, t)!,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t)!,
      textSecondary: Color.lerp(textSecondary, other.textSecondary, t)!,
      textDisabled: Color.lerp(textDisabled, other.textDisabled, t)!,
      accent: Color.lerp(accent, other.accent, t)!,
      accentText: Color.lerp(accentText, other.accentText, t)!,
      onAccent: Color.lerp(onAccent, other.onAccent, t)!,
      success: Color.lerp(success, other.success, t)!,
      onSuccess: Color.lerp(onSuccess, other.onSuccess, t)!,
      danger: Color.lerp(danger, other.danger, t)!,
      onDanger: Color.lerp(onDanger, other.onDanger, t)!,
      dangerSurface: Color.lerp(dangerSurface, other.dangerSurface, t)!,
      certified: Color.lerp(certified, other.certified, t)!,
      live: Color.lerp(live, other.live, t)!,
      border: Color.lerp(border, other.border, t)!,
      borderStrong: Color.lerp(borderStrong, other.borderStrong, t)!,
      radiusS: _lerpD(radiusS, other.radiusS, t),
      radiusM: _lerpD(radiusM, other.radiusM, t),
      radiusL: _lerpD(radiusL, other.radiusL, t),
      gapS: _lerpD(gapS, other.gapS, t),
      gapM: _lerpD(gapM, other.gapM, t),
      gapL: _lerpD(gapL, other.gapL, t),
      gapXL: _lerpD(gapXL, other.gapXL, t),
      screenTitle: TextStyle.lerp(screenTitle, other.screenTitle, t)!,
      blockHeader: TextStyle.lerp(blockHeader, other.blockHeader, t)!,
      body: TextStyle.lerp(body, other.body, t)!,
      bodyHindi: TextStyle.lerp(bodyHindi, other.bodyHindi, t)!,
      numericHero: TextStyle.lerp(numericHero, other.numericHero, t)!,
      numericMedium: TextStyle.lerp(numericMedium, other.numericMedium, t)!,
      buttonLabel: TextStyle.lerp(buttonLabel, other.buttonLabel, t)!,
      metadata: TextStyle.lerp(metadata, other.metadata, t)!,
      chipLabel: TextStyle.lerp(chipLabel, other.chipLabel, t)!,
    );
  }

  static double _lerpD(double a, double b, double t) => a + (b - a) * t;
}

/// Build a full Material [ThemeData] from tokens so stock widgets (dialogs,
/// snackbars, text selection, progress indicators) inherit the skin too, and
/// carry the [DmrvTokens] as a theme extension for `context.tokens`.
ThemeData buildDmrvTheme(DmrvTokens t) {
  return ThemeData(
    useMaterial3: true,
    scaffoldBackgroundColor: t.surface,
    primaryColor: t.accent,
    colorScheme: ColorScheme.light(
      primary: t.accent,
      onPrimary: t.onAccent,
      secondary: t.success,
      onSecondary: t.onSuccess,
      error: t.danger,
      onError: t.onDanger,
      surface: t.surfaceRaised,
      onSurface: t.textPrimary,
    ),
    textTheme: TextTheme(
      titleLarge: t.screenTitle.copyWith(color: t.textPrimary),
      titleMedium: t.blockHeader.copyWith(color: t.textPrimary),
      bodyLarge: t.body.copyWith(color: t.textPrimary),
      bodyMedium: t.metadata.copyWith(color: t.textSecondary),
    ),
    cardTheme: CardThemeData(
      color: t.surfaceRaised,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(t.radiusM),
        side: BorderSide(color: t.border, width: 1.5),
      ),
    ),
    extensions: <ThemeExtension<dynamic>>[t],
  );
}

/// `context.tokens` — the access pattern used everywhere in the UI. Falls back
/// to the India skin if no DmrvTokens extension is installed (single-skin
/// today), so a screen or a widget test can never crash on a missing theme.
extension DmrvTokensContext on BuildContext {
  DmrvTokens get tokens =>
      Theme.of(this).extension<DmrvTokens>() ?? DmrvTokens.india;
}
