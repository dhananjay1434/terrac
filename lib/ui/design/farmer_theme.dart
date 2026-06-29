import 'package:flutter/material.dart';

import 'app_theme.dart';

/// FarmerTheme — the "Rugged Field Tool" dark palette.
///
/// This lives ALONGSIDE [AppTheme]; it does not replace it. The existing
/// light theme keeps powering anything already wired to it. FarmerTheme adds
/// a high-contrast dark theme tuned for a leather-gloved farmer reading a
/// tablet in direct sunlight.
///
/// Font families are inherited verbatim from [AppTheme.lightTheme] (SpaceGrotesk
/// for labels/headers, SpaceMono for readings, NotoSansDevanagari for Hindi);
/// only the colours are flipped for the dark surface.
class FarmerTheme {
  FarmerTheme._();

  // ---- Colour tokens -------------------------------------------------------

  /// ALL scaffold backgrounds (replaces tacticalTitanium for the field theme).
  static const Color deepSlate = Color(0xFF1A1D20);

  /// Primary CTA, sync warnings, "action required" state.
  static const Color neonYellow = Color(0xFFE0FF00);

  /// Stabilized / locked-in state, sensor confirmed.
  static const Color fieldGreen = Color(0xFF00E676);

  /// Hardware errors (identical to the existing _errorRed / _stopRed value).
  static const Color crimsonRed = Color(0xFFDC2626);

  /// Card and panel surfaces only.
  static const Color pureAlbedo = Color(0xFFFFFFFF);

  /// Locked/inactive text and surfaces.
  static const Color fogWhite = Color(0xFFE2E8F0);

  /// Slightly lighter slate used for card / panel surfaces so they lift off the
  /// [deepSlate] scaffold without resorting to muddy gradients.
  static const Color panelSlate = Color(0xFF23272B);

  // Pre-computed opacities for performance (Phase 7)
  static const Color fogWhite70 = Color(0xB3E2E8F0);
  static const Color fogWhite65 = Color(0xA6E2E8F0);
  static const Color fogWhite60 = Color(0x99E2E8F0);
  static const Color fogWhite50 = Color(0x80E2E8F0);
  static const Color fogWhite30 = Color(0x4DE2E8F0);
  static const Color fogWhite20 = Color(0x33E2E8F0);
  static const Color fogWhite10 = Color(0x1AE2E8F0);
  static const Color fogWhite05 = Color(0x0DE2E8F0);

  static const Color neonYellow30 = Color(0x4DE0FF00);
  static const Color neonYellow20 = Color(0x33E0FF00);
  static const Color neonYellow15 = Color(0x26E0FF00);

  static const Color fieldGreen30 = Color(0x4D00E676);
  static const Color fieldGreen15 = Color(0x2600E676);

  static const Color crimsonRed70 = Color(0xB3DC2626);
  static const Color crimsonRed15 = Color(0x26DC2626);

  static const Color deepSlate40 = Color(0x661A1D20);
}
