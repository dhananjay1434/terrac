# UI Consistency Audit — The Seams Paper

**Date:** 2026-07-07 · **Scope:** every file under `lib/ui/` (12 screens/widgets + 3 design files, 5,188 lines) plus `lib/main.dart` theme wiring. Every claim verified against code with file:line.

This is the research the platform tier ([06_TIER5_UI_PLATFORM.md](06_TIER5_UI_PLATFORM.md)) executes against. It documents **every visual seam** in the current app — where the UI is dark vs light, where the same thing is styled two ways, where strings/colors/radii/paddings drift.

---

## 1. The root cause: two design systems shipped side by side

The app has **two complete, deliberate, incompatible palettes**, both alive:

| | `AppTheme` ("Tactical Titanium") | `FarmerTheme` ("Rugged Field Tool") |
|---|---|---|
| File | [lib/ui/design/app_theme.dart](../../lib/ui/design/app_theme.dart) (85 lines) | [lib/ui/design/farmer_theme.dart](../../lib/ui/design/farmer_theme.dart) (63 lines) |
| Brightness | **Light** — off-white `tacticalTitanium 0xFFF0F4F8` scaffold | **Dark** — `deepSlate 0xFF1A1D20` scaffold |
| Primary accent | `cobaltShield 0xFF1D4ED8` (blue) | `neonYellow 0xFFE0FF00` |
| Success | `yieldGold 0xFFF59E0B` | `fieldGreen 0xFF00E676` |
| Applied | **Globally** — `MaterialApp(theme: AppTheme.lightTheme)` at main.dart:72 | **Never globally** — imported ad hoc per screen |
| Self-description | — | farmer_theme.dart:7-10: *"This lives ALONGSIDE AppTheme; it does not replace it."* |

Neither is a Material `ThemeData` consumers actually read from context — both are static-constant classes, and every screen hard-assigns its own `Scaffold(backgroundColor:)`, so the global theme is effectively decorative. There are **no ThemeExtensions**, no semantic tokens, no dark/light variants of one system — just two systems.

## 2. The seam the user feels: the batch flow flips theme five times

Verified per-screen adoption (grep counts of theme references):

| Order in flow | Screen | Theme | Refs | Background |
|---|---|---|---|---|
| 1 | `dashboard_screen.dart` | **DARK** Farmer | 37 | `FarmerTheme.deepSlate` (line 433) |
| 2 | `lantana_sourcing_screen.dart` | **LIGHT** App | 20 | `AppTheme.tacticalTitanium` (line 54) |
| 3 | `moisture_verification_screen.dart` | **LIGHT** App | 15 (+6 hardcoded hex) | `AppTheme.tacticalTitanium` |
| 4 | `pyrolysis_screen.dart` | **LIGHT** App | 7 (+3 hardcoded hex) | `AppTheme.tacticalTitanium` |
| 5 | `yield_scale_screen.dart` | **DARK** Farmer | 21 | animated `deepSlate`→`fieldGreen` (lines 132-140) |
| 6 | `end_use_application_screen.dart` | **LIGHT** App | 37 (+1 hardcoded) | `AppTheme.tacticalTitanium` |
| 7 (return) | `dashboard_screen.dart` | **DARK** Farmer | — | — |
| side | `proof_wallet_screen.dart` | **DARK** Farmer | 18 | `FarmerTheme.deepSlate` |
| side | `secure_camera_screen.dart` | **BLACK** (neither) | 10 App refs | `Colors.black` (camera feed — acceptable, but overlay uses AppTheme gold on a Farmer-adjacent surface) |
| debug | `camera_debug_view.dart` | **LIGHT** App | 5 | `AppTheme.tacticalTitanium` |

**A field operator walking one batch sees: dark → light → light → light → dark(+green flash) → light → dark.** That's the "some part is dark, some part is different" experience, precisely.

The widget layer forked the same way:

| Widget | Palette | Used by |
|---|---|---|
| `RuggedButton` (rugged_button.dart, 105 lines) | Farmer (8 refs) | Dashboard, YieldScale, Pyrolysis(!) — a Farmer button on a light AppTheme screen |
| `PremiumFieldButton` + `PremiumFieldPanel` + `PremiumScreenHeader` + `PremiumStatusChip` (premium_field_components.dart, 392 lines) | App (24 refs, +4 hardcoded) | all light screens |
| `IntegrityFooter` (integrity_footer.dart) | App (`midnightCyber` bg + `telemetryCyan`) | ALL screens — a third mini-palette present everywhere |
| `PremiumActionCard` (premium_action_card.dart, 148 lines) | App | **NOBODY — dead code** |
| `PremiumInputField` (premium_field_components.dart:287) | App | **NOBODY — dead code** |

So the same semantic element — "the big confirm button" — is `neonYellow`/dark on three screens and `cobaltShield`/light on four, and two full components exist to do one job.

## 3. Hardcoded color literals bypassing both themes (61 `Color(0x…)` in lib/)

The worst repeat offender: **error red `0xFFDC2626` is privately re-declared 9 times** even though it exists as `FarmerTheme.crimsonRed`:

| File:Line | Local name |
|---|---|
| moisture_verification_screen.dart:47, 245, 453, 520 | `_errorRed` (×4 **within one file**) + `_errorRedSoftBg 0xFFFEF2F2` (:48, :521) |
| pyrolysis_screen.dart:33 | `_errorRed` |
| end_use_application_screen.dart:49 | `_errorRed` |
| lantana_sourcing_screen.dart:377 | `_stopRed` |
| premium_field_components.dart:78, 244, 311 | `_stopRed` / `_errorRed` (×3 within the shared component file itself) |

Other literals: pyrolysis_screen.dart:269, 283 hardcode `0xFF00E676` — which **is** `FarmerTheme.fieldGreen` — inside an AppTheme-light screen (a Farmer color pasted across the fence); integrity_footer.dart:21 shadow `0x66000000`; premium_field_components.dart:255 pastes `0xFFE2E8F0` (= `FarmerTheme.fogWhite`) into an App-side component; camera_debug_view uses raw `Colors.red`.

## 4. Same semantic, different styling — the drift catalog

**Error panels** (should be one pattern):

| Screen | Background | Border | Text color | Font | Padding |
|---|---|---|---|---|---|
| Moisture | hardcoded pink `0xFFFEF2F2` | crimson 2px | crimson | SpaceGrotesk 18sp | 20px |
| Pyrolysis | crimson @15% | crimson 2px | crimson | SpaceGrotesk 14sp | 16px |
| YieldScale | `FarmerTheme.crimsonRed15` | crimson 2px | **fogWhite** | **SpaceMono 13sp** | 16px |
| EndUse | **none** (border only) | crimson 1px | crimson | SpaceGrotesk 14sp | 16px |

**Success color:** `yieldGold` on light screens vs `fieldGreen` on dark screens — two different "verified" colors in one flow.

**Corner radii:** the de-facto standard is 12px (panels, buttons), but: dashboard stat boxes 8px (dashboard_screen.dart:75), moisture meter container 10px (moisture_verification_screen.dart:275), EndUse GPS/photo buttons 10px (end_use_application_screen.dart:304-305), header back buttons 10px, status chips 20px pill. Five radii where a token scale would define three.

**Spacing:** mostly a clean 8/12/16/20/24 scale, with strays: 6px one-off (moisture), 14px one-offs (EndUse), camera_debug 20px frame where every other screen uses 16px, 18px dashboard section gap.

**Typography:** three families with clear roles (SpaceGrotesk labels / SpaceMono numerics / NotoSansDevanagari Hindi) — genuinely consistent — but sizes for the same role drift: screen titles 20sp vs 24sp; metadata 11/13/14sp; giant counters intentionally 56/72/96sp (fine). The global `TextTheme` (app_theme.dart:52-77) defines only 4 of the ~10 styles actually used, so most text is inline `TextStyle` — the theme can't restyle the app.

**Loading/pending:** `CircularProgressIndicator` colored `neonYellow` on dark screens, `yieldGold` on light; pulsing-card animation exists only on Dashboard.

## 5. Contrast & accessibility findings

- **WCAG failure:** moisture hint text `armorSlate35` (35% opacity slate on off-white, ≈3:1) at moisture_verification_screen.dart:351 — fails AA (4.5:1) even at 20sp bold. Use ≥`armorSlate60`.
- Dark-screen text (`fogWhite` on `deepSlate`, ~17:1) and primary text (`armorSlate` on `tacticalTitanium`) are excellent — the field-readability intent is real.
- Touch targets: uniformly ≥64px CTAs, 48px back buttons, 86px shutter — **pass**, genuinely well done.
- Semantics: inconsistent `identifier` vs `label` usage between `PremiumFieldButton` and `RuggedButton`; several raw `InkWell`s (e.g. lantana_sourcing_screen.dart:217) with no semantics at all. No screen-reader pass has ever been done.

## 6. Strings & localization seams

Only **2 of 9 screens** import `AppLocalizations` (dashboard, yield_scale). Everything else hardcodes UI copy: "PROOF WALLET" / "NO BATCHES RECORDED" (proof_wallet_screen.dart:49, 98), "CONNECT ESP32 THERMOCOUPLE" / "END BURN" (pyrolysis_screen.dart:154, 307), all Moisture/EndUse block headers, plus brand strings "TerraCipher" / "dMRV Field Terminal v3.0" baked into dashboard_screen.dart:511, 518 (a white-label blocker, not just an l10n gap). The ARB files hold only ~10 keys per locale — the real string count is 6–10× that.

## 7. Navigation seams

- Inline `MaterialPageRoute` everywhere; **no named routes** (harder to deep-link, test, or instrument).
- **Back-stack inconsistency:** pyrolysis→yield and yield→endUse use `pushReplacement` (pyrolysis_screen.dart:78, yield_scale_screen.dart:82) so the user *cannot* navigate back mid-flow, while sourcing→moisture→pyrolysis use `push` so they *can*; the final screen `popUntil(isFirst)`. Either freeze-forward is the policy (then enforce it everywhere and disable back) or it isn't (then stop replacing).
- Custom back buttons on every screen (no AppBar anywhere) — consistent as a pattern, but each is hand-rolled.

## 8. What is genuinely good (protect it during unification)

1. The **field-UX fundamentals** are excellent and consistent: ≥64px glove targets, haptics on CTAs, giant numeric readouts, uppercase scannable labels, three-font role system.
2. `premium_field_components.dart` is a real component library with state enums (`FieldButtonState`, `PremiumChipStatus`) — the right architecture, just single-palette.
3. Pre-computed opacity constants (Phase 7 performance work) show deliberate engineering.
4. `IntegrityFooter` on every screen is a strong trust-signal pattern.
5. Both palettes are *individually* coherent and documented with intent comments. The problem is not bad design — it's **two good designs never reconciled**.

## 9. Consolidated defect list (feeds Tier 5 tasks)

| # | Finding | Severity | Fix task |
|---|---|---|---|
| U1 | Two theme systems; flow flips dark/light 5× | **CRITICAL** | T5.2 |
| U2 | No semantic token layer; screens hard-assign colors; global ThemeData decorative | **CRITICAL** | T5.1 |
| U3 | 61 hardcoded `Color(0x…)`; `0xFFDC2626` ×9; Farmer colors pasted into App screens | HIGH | T5.1/T5.2 |
| U4 | Two button components for one semantic; `PremiumActionCard` + `PremiumInputField` dead | HIGH | T5.3 |
| U5 | Error/status/loading patterns differ per screen (4 variants) | HIGH | T5.4 |
| U6 | Only 2/9 screens localized; brand strings hardcoded | HIGH (white-label blocker) | T5.5 / T5.10 |
| U7 | WCAG AA failure (armorSlate35 hint); no semantics pass | MEDIUM | T5.4 |
| U8 | Radius drift (8/10/12/20) and spacing strays (6/14/18/20) | LOW | T5.1 tokens |
| U9 | `push` vs `pushReplacement` inconsistency; no named routes | MEDIUM | T5.6 |
| U10 | Success color differs by theme era (gold vs green) | MEDIUM | T5.1 semantic `success` token |
| U11 | `IntegrityFooter` third mini-palette (midnightCyber/telemetryCyan) unthemed | LOW | T5.1 |
| U12 | TextTheme covers 4 of ~10 real text roles; inline TextStyles dominate | MEDIUM | T5.1 typography roles |
