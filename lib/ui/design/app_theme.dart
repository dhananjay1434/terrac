import 'package:flutter/material.dart';

class AppTheme {
  static const Color tacticalTitanium = Color(
    0xFFF0F4F8,
  ); // Main scaffold background, high-albedo off-white for sunlight readability.
  static const Color pureAlbedo = Color(0xFFFFFFFF); // Card surface color only.
  static const Color armorSlate = Color(
    0xFF0F172A,
  ); // All primary text and icons, maximum contrast.
  static const Color cobaltShield = Color(
    0xFF1D4ED8,
  ); // Primary brand accent, trust and BLE active state.

  static const Color yieldGold = Color(
    0xFFF59E0B,
  ); // Verified/success state only, cryptographic confirmation.
  static const Color midnightCyber = Color(
    0xFF0B1026,
  ); // Cryptographic footer background only, never used elsewhere.

  // Pre-computed opacities for performance (Phase 7)
  static const Color cobaltShield40 = Color(0x661D4ED8);
  static const Color cobaltShield30 = Color(0x4D1D4ED8);
  static const Color cobaltShield25 = Color(0x401D4ED8);
  static const Color cobaltShield20 = Color(0x331D4ED8);
  static const Color cobaltShield15 = Color(0x261D4ED8);
  static const Color cobaltShield06 = Color(0x0F1D4ED8);

  static const Color armorSlate75 = Color(0xBF0F172A);
  static const Color armorSlate70 = Color(0xB30F172A);
  static const Color armorSlate65 = Color(0xA60F172A);
  static const Color armorSlate60 = Color(0x990F172A);
  static const Color armorSlate55 = Color(0x8C0F172A);
  static const Color armorSlate45 = Color(0x730F172A);
  static const Color armorSlate40 = Color(0x660F172A);
  static const Color armorSlate35 = Color(0x590F172A);
  static const Color armorSlate20 = Color(0x330F172A);

  static const Color yieldGold40 = Color(0x66F59E0B);
  static const Color yieldGold30 = Color(0x4DF59E0B);
  static const Color yieldGold10 = Color(0x1AF59E0B);

  static const Color telemetryCyan = Color(0xFF00E5FF);
  static const Color telemetryCyan70 = Color(0xB300E5FF);
  static const Color black06 = Color(0x0F000000);

  static ThemeData get lightTheme {
    return ThemeData(
      scaffoldBackgroundColor: tacticalTitanium,
      primaryColor: cobaltShield,
      textTheme: const TextTheme(
        titleLarge: TextStyle(
          fontFamily: 'SpaceGrotesk',
          fontSize: 24,
          fontWeight: FontWeight.w700,
          color: armorSlate,
        ),
        titleMedium: TextStyle(
          fontFamily: 'SpaceGrotesk',
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: armorSlate,
        ),
        bodyLarge: TextStyle(
          fontFamily: 'NotoSansDevanagari',
          fontSize: 18,
          fontWeight: FontWeight.w500,
          color: armorSlate,
        ),
        bodyMedium: TextStyle(
          fontFamily: 'SpaceMono',
          fontSize: 14,
          fontWeight: FontWeight.w400,
          color: armorSlate,
        ),
      ),
      cardTheme: CardThemeData(
        color: pureAlbedo,
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
    );
  }
}
