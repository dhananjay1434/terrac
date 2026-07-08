import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/ui/design/tokens.dart';

/// WCAG 2.x relative luminance from a color's sRGB channels (0..1 doubles).
double _chan(double v) =>
    v <= 0.03928 ? v / 12.92 : pow((v + 0.055) / 1.055, 2.4).toDouble();

double _luminance(Color c) =>
    0.2126 * _chan(c.r) + 0.7152 * _chan(c.g) + 0.0722 * _chan(c.b);

/// Contrast ratio of [fg] over opaque [bg]. [fg] may be semi-transparent —
/// it is composited onto [bg] first (that is how it actually renders).
double contrast(Color fg, Color bg) {
  final composited = Color.alphaBlend(fg, bg);
  final lf = _luminance(composited);
  final lb = _luminance(bg);
  final hi = max(lf, lb);
  final lo = min(lf, lb);
  return (hi + 0.05) / (lo + 0.05);
}

void main() {
  // As Europe/other skins are added, add them to this map — the loop then
  // enforces AA for every skin automatically.
  final skins = <String, DmrvTokens>{'india': DmrvTokens.india};

  for (final entry in skins.entries) {
    final name = entry.key;
    final t = entry.value;

    group('DmrvTokens.$name — WCAG AA', () {
      // Normal-text pairs must clear 4.5:1.
      test('textPrimary on surface >= 4.5', () {
        expect(contrast(t.textPrimary, t.surface), greaterThanOrEqualTo(4.5));
      });
      test('textPrimary on surfaceRaised >= 4.5', () {
        expect(
          contrast(t.textPrimary, t.surfaceRaised),
          greaterThanOrEqualTo(4.5),
        );
      });
      test('textSecondary on surface >= 4.5', () {
        expect(contrast(t.textSecondary, t.surface), greaterThanOrEqualTo(4.5));
      });
      test('accentText on surface >= 4.5', () {
        expect(contrast(t.accentText, t.surface), greaterThanOrEqualTo(4.5));
      });
      test('success on surface >= 4.5', () {
        expect(contrast(t.success, t.surface), greaterThanOrEqualTo(4.5));
      });
      test('danger on surface >= 4.5', () {
        expect(contrast(t.danger, t.surface), greaterThanOrEqualTo(4.5));
      });
      test('danger on dangerSurface >= 4.5', () {
        expect(
          contrast(t.danger, t.dangerSurface),
          greaterThanOrEqualTo(4.5),
        );
      });
      test('certified on surface >= 4.5', () {
        expect(contrast(t.certified, t.surface), greaterThanOrEqualTo(4.5));
      });

      // Labels ON a colored fill: large/bold text, so the 3:1 floor applies.
      test('onAccent on accent fill >= 4.5', () {
        expect(contrast(t.onAccent, t.accent), greaterThanOrEqualTo(4.5));
      });
      test('onSuccess on success fill >= 3.0', () {
        expect(contrast(t.onSuccess, t.success), greaterThanOrEqualTo(3.0));
      });
      test('onDanger on danger fill >= 3.0', () {
        expect(contrast(t.onDanger, t.danger), greaterThanOrEqualTo(3.0));
      });
    });
  }
}
