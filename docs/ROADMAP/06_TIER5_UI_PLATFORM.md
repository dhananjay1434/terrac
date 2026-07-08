# Tier 5 — UI Unification & Platformization: "One Codebase, Any Brand, Any Market"

> **Benchmark when this tier is green:** the app renders from a **single semantic design-token system** with zero hardcoded colors; the same codebase ships two first-class skins — **Field (India)** and **Pro (Global/EU)** — selected by configuration, not code; any third party can be white-labeled (name, logo, colors, package id) in under a day without touching a screen file; and the backend serves **multiple isolated tenants**, making the product sellable as SaaS dMRV rather than a single-customer app.
>
> **Evidence base:** every task below traces to a numbered finding (U1–U12) in [UI_CONSISTENCY_AUDIT.md](UI_CONSISTENCY_AUDIT.md) — read that first.
>
> **Total effort: ~4–6 weeks**, in four stages that ship independently: **A** unify (fix the seams) → **B** dual skins → **C** white-label → **D** multi-tenant SaaS.
>
> **Ordering:** Stage A can start any time (pure client work, no backend dependency) and should land **before T4.5's golden tests** (or you'll write goldens twice). Stage C/D depend on T1.1 (project linkage) and are much easier after T3.4 (read API). Do NOT start Stage B until Stage A's gate is green — skinning two inconsistent UIs doubles the mess.

---

# Stage A — Unify: one design system (fixes U1–U5, U7–U12)

## T5.1 — Semantic design-token layer (the foundation everything else stands on)

- **Where:** new `lib/ui/design/tokens.dart`; rewires `lib/main.dart:72`.
- **Why:** today there are two static-constant palettes (`AppTheme`, `FarmerTheme`), the global `ThemeData` is decorative (every screen hard-assigns colors — U2), and 61 hex literals bypass both (U3). A skinnable app needs *semantic* names resolved through context, not brand-color constants referenced directly.
- **What:**
  1. Define a `DmrvTokens` **`ThemeExtension<DmrvTokens>`** carrying *semantic role* fields — names describe function, never color:
     ```dart
     class DmrvTokens extends ThemeExtension<DmrvTokens> {
       // surfaces
       final Color surface;        // scaffold
       final Color surfaceRaised;  // cards/panels
       final Color surfaceSunken;  // input wells
       // content
       final Color textPrimary, textSecondary, textDisabled;
       // semantic states — ONE success color, ONE danger, ONE warning (kills U10)
       final Color accent, onAccent;        // primary CTA
       final Color success, onSuccess;
       final Color danger, dangerSurface;   // dangerSurface kills the 4-variant error panel (U5)
       final Color warning, warningSurface;
       final Color info;                    // telemetry/live indicators (absorbs telemetryCyan, U11)
       final Color border, borderStrong;
       // shape & space scales (kills U8)
       final double radiusS, radiusM, radiusL;   // 8, 12, 20
       final EdgeInsets padPanel, padScreen;     // 16, 16/4/16/16
       final double gapS, gapM, gapL, gapXL;     // 8, 12, 16, 24
       // typography roles (kills U12) — full set, not 4 of 10
       final TextStyle screenTitle, blockHeader, body, bodyHindi,
                       numericHero, numericMedium, buttonLabel, metadata, chipLabel;
       // ... copyWith/lerp boilerplate
     }
     ```
  2. Provide **two built-in instances**: `DmrvTokens.field` (from FarmerTheme values: deepSlate/panelSlate/neonYellow/fieldGreen/crimson/fogWhite) and `DmrvTokens.pro` (from AppTheme values: tacticalTitanium/pureAlbedo/cobaltShield/yieldGold/armorSlate) — this *preserves* both existing designs as skins instead of deleting one.
  3. Install via `MaterialApp(theme: buildTheme(tokens))` where `buildTheme` also fills real `ColorScheme`, `TextTheme`, `CardThemeData`, `scaffoldBackgroundColor` from the tokens (so stock Material widgets — dialogs, progress indicators, snackbars — inherit correctly too).
  4. Access pattern everywhere: `final t = Theme.of(context).extension<DmrvTokens>()!;` — add a `context.tokens` extension getter for brevity.
  5. Keep `AppTheme`/`FarmerTheme` classes temporarily as deprecated aliases delegating to token values, so migration (T5.2) can proceed screen-by-screen without a big bang.
- **Gate:** `tokens.dart` exists with both instances; `flutter test` green; a unit test asserts every token field non-null for both skins and that `success`/`danger` meet ≥4.5:1 contrast against `surface` and `surfaceRaised` (mechanical WCAG guard — kills U7 regressions forever).
- **Effort:** L.

## T5.2 — Migrate all 9 screens + 3 shared widgets to tokens; end the dark/light flip (U1, U3)

- **Where:** every file in `lib/ui/screens/` and `lib/ui/widgets/`, in this order (leaf widgets first): `integrity_footer.dart` → `premium_field_components.dart` → `rugged_button.dart` → the 7 product screens → `camera_debug_view.dart`.
- **What, mechanically per file:**
  1. Replace every `AppTheme.X` / `FarmerTheme.X` / `Color(0x…)` with the semantic token that matches the *intent* (e.g. all nine `_errorRed` declarations → `t.danger`; `_errorRedSoftBg 0xFFFEF2F2` → `t.dangerSurface`; pyrolysis's pasted `0xFF00E676` → `t.success`; `Scaffold(backgroundColor: t.surface)`).
  2. Delete the per-file private color consts (moisture_verification_screen.dart:47,48,245,453,520,521; pyrolysis_screen.dart:33; end_use_application_screen.dart:49; lantana_sourcing_screen.dart:377; premium_field_components.dart:78,244,311).
  3. Replace inline `TextStyle(...)` with the typography-role tokens; keep the intentional hero sizes (56/72/96sp) as `numericHero` variants.
  4. Normalize radii to `radiusS/M/L` (the 8px dashboard stat boxes at dashboard_screen.dart:75, 10px meter container at moisture_verification_screen.dart:275, 10px GPS/photo buttons at end_use_application_screen.dart:304-305 all become `radiusM` unless a deliberate exception is documented in the token file).
  5. **The launch skin decision:** ship with `DmrvTokens.field` (dark) as the default for the field app — three screens already live there, it's the newer design era (per the UX_FIELD_THEME_SPEC), and it's the sunlight/glove-optimized one. The light design survives as `DmrvTokens.pro` (Stage B). After this task the batch flow is **one continuous dark experience** — the user-reported seam is gone.
- **Gate:** `grep -rn "Color(0x" lib/ui/` returns **0** outside `tokens.dart`; `grep -rn "AppTheme\.\|FarmerTheme\." lib/ui/screens lib/ui/widgets` returns 0; walkthrough of the full batch flow shows no background/brightness change between screens; `flutter test` + existing widget tests green.
- **Effort:** XL (it touches every screen — but each file is a mechanical substitution against the audit's per-file tables).

## T5.3 — One button, one panel: merge the duplicated component pairs (U4)

- **Where:** `rugged_button.dart` (105 lines, Farmer palette) + `PremiumFieldButton` (premium_field_components.dart:64, App palette) — two components, one semantic job.
- **What:**
  1. Create `DmrvButton` (new `lib/ui/components/dmrv_button.dart`): union of both feature sets — variants `primary / success / danger / hiVis / locked`, 64px min target, haptic feedback, full-width option, `Semantics(identifier:)` standardized (U7). All colors from tokens, so it's automatically correct in every skin.
  2. Migrate call sites (Dashboard, YieldScale, Pyrolysis ×RuggedButton; light screens + camera ×PremiumFieldButton), then delete both old components.
  3. Same treatment for panels: `PremiumFieldPanel` → `DmrvPanel` (token-driven surface/border/shadow — shadows only render meaningfully on the pro skin; keep the border-lift style for field skin, both encoded in tokens).
  4. **Delete dead code:** `premium_action_card.dart` (148 lines, used by nobody) and `PremiumInputField` (premium_field_components.dart:287, used by nobody) — or, if numeric entry is planned, resurrect `PremiumInputField` as `DmrvInput` in the same pass.
- **Gate:** `grep -rn "RuggedButton\|PremiumFieldButton\|PremiumActionCard" lib/` → 0; all screens render; widget tests updated.
- **Effort:** L.

## T5.4 — Standard status patterns: error / loading / empty / success (U5, U7)

- **Where:** new `lib/ui/components/dmrv_status.dart`; call sites per the audit §4 table.
- **What:** one `DmrvErrorPanel(message, {details})` (bg `t.dangerSurface`, border `t.danger` 2px, text `t.danger`, `blockHeader` typography, `padPanel`) replacing the four divergent error treatments (moisture/pyro/yield/endUse); one `DmrvLoading` (progress indicator colored `t.accent`); one `DmrvEmptyState(icon, message)` (proof wallet's "NO BATCHES RECORDED" pattern, generalized). Fix the WCAG failure while there: moisture hint `armorSlate35` → `t.textDisabled` defined at ≥4.5:1 (moisture_verification_screen.dart:351).
- **Gate:** all four screens' error states render identically (golden test per skin); contrast unit test from T5.1 covers `textDisabled`.
- **Effort:** M.

## T5.5 — Full string externalization (U6) — prerequisite for both skins and white-label

- **Where:** all screens; `lib/l10n/app_en.arb`, `app_hi.arb` (~10 keys today, real count is 60–120).
- **What:** sweep every user-visible literal into ARB keys (the audit §6 lists the offenders: proof_wallet_screen.dart:49,98; pyrolysis_screen.dart:154,307; all moisture/endUse block headers; camera screens). **Brand strings are NOT l10n:** "TerraCipher" and "dMRV Field Terminal v3.0" (dashboard_screen.dart:511,518) move to the brand config (T5.10), not to ARB. This task merges with/supersedes the T4.6 string sweep — do it once, here, and T4.6 reduces to "add app_mr.arb".
- **Gate:** extend `test/l10n_test.dart`: en/hi key parity; a grep-based test asserting no `Text('` with raw literals in `lib/ui/screens` (allowlist for debug-only camera_debug_view).
- **Effort:** L.

## T5.6 — Navigation coherence (U9)

- **Where:** route pushes at pyrolysis_screen.dart:78 and yield_scale_screen.dart:82 (`pushReplacement`), all inline `MaterialPageRoute`s.
- **What:**
  1. **Decide and document the back policy.** Recommendation: the evidence flow is *deliberately* forward-only after pyrolysis starts (you can't un-burn biomass) — so keep freeze-forward but make it explicit and total: wrap post-pyrolysis screens in `PopScope(canPop: false)` with a "batch in progress" explanation, and use `pushReplacement` consistently from pyrolysis onward (today sourcing→moisture allows back but yield doesn't — half-enforced is the bug).
  2. Introduce named routes (`Routes.dashboard`, `.sourcing`, `.moisture`, …) in one `lib/ui/routes.dart` — needed later for tenant deep-links and analytics screen names (T4.7/T5.14), and it makes the flow order testable.
- **Gate:** a widget test drives the full flow and asserts the back-stack state at each step matches the documented policy.
- **Effort:** M.

### ✅ Stage A gate (do not start Stage B before this)
- Zero hex literals / era-theme references outside `tokens.dart`; one continuous theme through the batch flow; one button/panel/error/loading/empty component each; all strings externalized; nav policy enforced; goldens recorded for the field skin.

---

# Stage B — Dual skins: Field (India) and Pro (Global/EU)

## T5.7 — Skin architecture: config-selected, not code-selected

- **Where:** new `lib/config/app_skin.dart`; `lib/main.dart`.
- **What:**
  1. `enum AppSkin { field, pro }` resolved at startup from (in priority order): tenant remote config (T5.14, once it exists) → `--dart-define=DMRV_SKIN=` → default `field`.
  2. `MaterialApp(theme: buildTheme(skin.tokens))`. Because Stage A made every screen token-driven, **the entire skin switch is this one line** — that's the payoff and the test of whether Stage A was done honestly.
  3. Add `themeMode`-style hot support in debug builds (a debug-drawer toggle) so designers can flip skins live.
- **Gate:** `flutter run --dart-define=DMRV_SKIN=pro` renders every screen in the pro palette with no code edits; goldens exist for both skins per screen (matrix: 9 screens × 2 skins).
- **Effort:** M (given Stage A).

## T5.8 — Design the Pro skin as a real product surface, not a recolor

The **Field skin** is operator-facing: dark, neon, glove-first, Devanagari, giant numerals — keep as-is from Stage A.
The **Pro skin** targets the *other* persona this platform must serve to go global: EU project developers, verifiers, buyers, and demo audiences — people on whom neon-on-slate reads as a toy.

- **What (token-level, screens untouched):**
  1. Start `DmrvTokens.pro` from the preserved AppTheme values (titanium/albedo/cobalt) — it was *designed* as the professional light surface; this is why we didn't delete it.
  2. Calibrate: `success` = a restrained green (not yieldGold — gold reads "warning" to EU eyes; keep gold as `warning`), tighter `numericHero` (96sp is a glove affordance, not a desk one — pro uses 56sp max), denser `gap*` scale, subtler `hiVis` variant.
  3. Region format layer (locale-driven, skin-independent but shipped here): dates via `intl` `DateFormat.yMMMd(locale)` instead of any hardcoded formats; decimal separators from locale; units stay metric (both markets) but temperature/weight formatting goes through one `lib/util/formats.dart`.
  4. Written one-pager `docs/engineering/SKINS.md`: personas, when each skin is the default, and the rule that **new tokens must be defined for both skins in the same PR** (enforced by the non-null unit test from T5.1).
- **Gate:** side-by-side screenshot sheet (both skins × key screens) reviewed and signed off; contrast tests pass for pro values.
- **Effort:** L.

## T5.9 — Skin regression safety

- **What:** golden tests per (screen × skin × locale-script) — en-field, hi-field, en-pro minimum; CI job renders both skins (extends T0.7 workflow). Token diff check: a test that fails if a `DmrvTokens` field is added without both skin instances defining it (constructor with required params gives this for free — keep it that way, no defaults).
- **Effort:** M. **Depends on:** T4.5's golden infra or builds it here — whichever runs first.

---

# Stage C — White-label: any brand in a day

## T5.10 — Brand configuration object

- **Where:** new `lib/config/brand.dart` + `assets/brand/` + `--dart-define-from-file=brand/<name>.json`.
- **What:**
  1. `Brand` model: `appTitle`, `shortName`, `logoAsset`, `footerLine` (replaces "dMRV Field Terminal v3.0"), `primaryOverride?`/`accentOverride?` (optional token overrides — most white-labels only need logo+name+accent), `supportContact`, `privacyUrl`.
  2. Replace the hardcoded "TerraCipher" / "dMRV Field Terminal v3.0" at dashboard_screen.dart:511,518 (and any splash/about surfaces) with `Brand.of(context)` reads. Grep-gate: `grep -rn "TerraCipher" lib/` → 0.
  3. Brand JSONs live in `brand/terracipher.json` (default), `brand/example_partner.json` (template with comments).
- **Gate:** `flutter run --dart-define-from-file=brand/example_partner.json` boots a visibly re-branded app; unit test loads every brand JSON against the model (schema drift guard).
- **Effort:** M.

## T5.11 — Per-brand app identity (flavors)

- **Where:** `android/app/build.gradle.kts`, iOS schemes/xcconfig.
- **What:** Android `productFlavors` per white-label: `applicationIdSuffix` (or full id), app label, launcher icon (`flutter_launcher_icons` with per-flavor config), and the brand JSON wired via flavor-specific dart-defines in CI. iOS mirrored with schemes + xcconfig. Keystore strategy: **one keystore per brand** (partners may later take over publishing — don't fuse their identity to yours).
- **Gate:** `flutter build apk --flavor examplePartner --release` produces an installable app with its own id, name, icon coexisting on one device with the TerraCipher build.
- **Effort:** L. **Depends on:** T0.6, T5.10.

## T5.12 — White-label factory script + doc

- **What:** `scripts/new_whitelabel.sh <name>` scaffolds: brand JSON from template, flavor block insertion, icon placeholder, CI matrix entry; plus `docs/engineering/WHITELABEL.md` — the checklist a non-founder engineer follows: assets needed from the partner (name, logo SVG, two colors, package id, support email), steps, build command, store-listing notes. Target: **<1 day per white-label, zero screen-file edits**.
- **Gate:** run the script for a fictional brand end-to-end; time it.
- **Effort:** M.

---

# Stage D — Multi-tenant SaaS backend: from app to platform

> This is what turns "white-label builds" into "**SaaS dMRV**": one deployed backend serving many isolated organizations, each with their own devices, projects, batches, branding, and (eventually) methodology profile. Builds directly on T1.1's `project_id` and T3.4's read API.

## T5.13 — Tenant model + scoped data

- **Where:** `backend/models.py` + migration (additive, per the load-bearing rules).
- **What:**
  1. New table `organizations`: `org_id (unique str)`, `display_name`, `brand_json` (Text — serves T5.14), `api_key_hash` (per-tenant admin key, sha256; the global `X-Admin-Secret` becomes the *platform-operator* key only), `created_at`, `status`.
  2. Nullable `org_id` columns (+ index) on `projects` (from T1.8), `device_keys`, `batches`, `enrollment_tokens`. Backfill migration sets existing rows to `org_id='terracipher'` seed org. Nullable-with-backfill, never NOT NULL in the same release (deployed-client rule).
  3. **Tenancy assignment at the trust root:** enrollment tokens are minted *for* an org (`POST /api/v1/admin/mint-token` gains optional `org_id`, platform-key-authenticated); device inherits org at registration; batch inherits org from its device (server-derived — never client-asserted, same trust philosophy as everything else).
- **Gate:** migration round-trips; every new batch carries the creating device's org; suite green.
- **Effort:** L.

## T5.14 — Tenant-scoped auth, reads, and remote app config

- **Where:** `backend/routes/admin.py` (post-T4.1) / server.py.
- **What:**
  1. New auth dependency `require_org(request) -> Organization`: `X-Org-Key` header, `hmac.compare_digest` against `api_key_hash`, timing-safe, rate-limited (T2.2 buckets keyed per org).
  2. All T3.4 read endpoints + lab/registry admin endpoints gain org-scoped variants (or a scope filter): an org key sees **only** its own devices/projects/batches; the platform key sees all. Every query gains `WHERE org_id = :org` — centralize in one query helper so a missed filter is structurally impossible, and add the **cross-tenant leak test**: org A's key requesting org B's batch uuid → 404 (not 403 — don't confirm existence).
  3. `GET /api/v1/app-config` (device-authenticated): returns the device's org branding (`brand_json`) + skin choice + feature flags → the app applies tenant brand/skin at runtime **without a rebuild** (white-label-lite for SaaS customers who don't want their own store listing).
  4. Per-org storage prefixes in T3.3 object storage (`s3://bucket/<org_id>/…`) and per-org metrics labels in T3.5.
- **Gate:** `test_tenancy.py`: leak test matrix (keys × resources), app-config returns correct brand per device, platform key unaffected.
- **Effort:** XL. **Depends on:** T1.1, T3.4; much safer after T4.1 modularization.

## T5.15 — Per-tenant methodology profile (the "personal dMRV" seed)

- **Where:** `backend/corroboration.py` + `organizations`/`projects` config.
- **What:** today `assemble()`'s rules are global constants. Make thresholds a `MethodologyProfile` dataclass (min moisture readings, min temp samples, GPS mismatch km, kiln-conditional toggles, which reasons are enforced) loaded per project/org with the **Rainbow profile as the frozen default**. Rules stay pure functions; only their parameters become data. This is deliberately *parameters-not-plugins*: new *rules* still ship as code + tests (credit integrity is not configurable by customers), but a tenant running a different standard's thresholds becomes a config row, not a fork.
  - Guard: profile stored on the org/project, admin-write-only, every batch's audit JSON records the profile hash it was evaluated under (verifier traceability).
- **Gate:** two orgs with different moisture minimums produce different provisional reasons on identical evidence; Rainbow-default org byte-identical to today's behavior (regression suite is the proof).
- **Effort:** L.

## T5.16 — Tenant lifecycle & ops

- **What:** provisioning script/endpoint (create org → mint org key → seed brand → mint first enrollment tokens); org suspend/archive status honored by auth; per-org usage counters (batches, devices, storage bytes) exposed in the T3.4 summary endpoint — the future billing meter; `docs/engineering/TENANCY.md` runbook (onboard, rotate org key, offboard/export: org data dump = batches+audits+media manifest for verifier handoff).
- **Gate:** onboard a fictional second tenant end-to-end on staging: provision → enroll a device (dev build) → sync a batch → see it only under that org's key → app shows that org's brand via `/app-config`.
- **Effort:** L.

---

## ✅ Tier 5 exit criteria (the benchmark, verbatim)

**Stage A —** zero hex/era-theme references outside tokens; one continuous theme across the batch flow; single button/panel/error/loading components; strings externalized; nav policy total.
**Stage B —** `--dart-define=DMRV_SKIN=pro` re-skins the whole app in one flag; goldens for 9 screens × 2 skins; both-skins-defined enforced structurally.
**Stage C —** a fictional partner brand builds, installs, and coexists with the TerraCipher app; `grep TerraCipher lib/` → 0; white-label runbook timed at <1 day.
**Stage D —** two orgs on one staging backend with provable isolation (leak-test matrix green); tenant branding served remotely; methodology thresholds per-tenant with Rainbow as frozen default; onboarding runbook executed once for real.

**You may now honestly sell this three ways: (1) TerraCipher's own field app, (2) a white-labeled app operated for a partner, (3) SaaS dMRV where a customer signs up, gets an org key, enrolls devices, and runs their own branded, isolated, methodology-parameterized carbon-evidence pipeline on your platform.**
