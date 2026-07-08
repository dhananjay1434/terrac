# Demo-Tomorrow + Dual-UI Map (report only — nothing executed)

**Written:** 2026-07-08 evening · **Author context:** post brutal-audit (3 independent code audits + analyzer), all six UI/UX docs read end-to-end.
**Companion docs:** [UX_FIELD_THEME_SPEC.md](../UX_FIELD_THEME_SPEC.md) · [UX_DESIGN_PLAN.md](../UX_DESIGN_PLAN.md) · [UX_BUILD_PLAN.md](../UX_BUILD_PLAN.md) · [UX_EXECUTION_PLAN.md](../UX_EXECUTION_PLAN.md) · [UI_CONSISTENCY_AUDIT.md](UI_CONSISTENCY_AUDIT.md) · [06_TIER5_UI_PLATFORM.md](06_TIER5_UI_PLATFORM.md)

This file maps (1) everything tomorrow's demo needs, and (2) the full execution path for the two-skin
(India Field + Europe/Universal Pro) + white-label goal. It makes **no changes** — it is the map.

---

# PART 1 — Tomorrow's demo

## 1.1 Hard blockers (no code — setup; ~1 hour total)

| # | Blocker | Evidence | Action |
|---|---|---|---|
| B1 | Backend will not boot: `DMRV_ADMIN_SECRET` missing from `backend/.env` | server.py:218 `_require_secret` raises at import | Add a 32+ char secret to `.env`, start backend, `curl http://localhost:8001/api/health` → 200 |
| B2 | App crashes at startup without compile-time defines | crypto_signer.dart:75-83 throws StateError when `ENROLLMENT_TOKEN`/`DMRV_API_BASE_URL` empty | Build a **debug** APK with all three defines (see 1.2) |
| B3 | No enrollment token exists | tokens are minted via `POST /api/v1/admin/mint-token` (server.py:732) | Mint 1 token **+ 2 spares** (single-use; app reinstall burns one) |
| B4 | Phone can't reach the backend | sync + registration need the laptop over LAN | `DMRV_API_BASE_URL=http://<laptop-LAN-IP>:8001`; phone + laptop on the same Wi-Fi; Windows firewall allows :8001 |
| B5 | The demo has no visible payoff in the app | the credit/compliance result exists ONLY on the admin API (`GET /api/v1/batches/{uuid}/compliance`, server.py:2266); the app UI ends at "ALL DATA SECURE" | Stage the finale: terminal curl of the compliance endpoint (or a small local verifier page — see 1.3 F4) |

## 1.2 The demo build command (debug, not release)

```
flutter build apk --debug ^
  --dart-define=DMRV_API_BASE_URL=http://<LAN-IP>:8001 ^
  --dart-define=ENROLLMENT_TOKEN=<minted-token> ^
  --dart-define=DMRV_DEMO_MODE=true
```

Why debug + demo mode (all verified in code):
- `DMRV_DEMO_MODE=true` swaps in the **VirtualBleAdapter** (simulated thermocouple — pyrolysis_ble_notifier.dart:166), the **MockBleWeightScaleService** (yield_scale_notifier.dart:143), and **mock GPS** (location_service.dart:78). **Zero hardware needed**: no kiln, no scale, no ESP32.
- Debug build skips FreeRASP integrity hard-lock and TLS cert-pinning (both release-only paths).
- Demo mode is **forbidden in release** by code (three separate guards) — do not attempt a release build tonight; the release path (keystore/R8) is unvalidated anyway (T0.6/T2 leftover).

## 1.3 Demo-visible code fixes (optional; ranked; NOT executed)

| # | Fix | File:line | Effort | Risk | Why it matters tomorrow |
|---|---|---|---|---|---|
| F1 | Hide the visible **"-73h TEST"** button behind the same debug-gate as the existing triple-tap dev bypass | lantana_sourcing_screen.dart:344 | ~15 min | trivial | An investor WILL see/tap a button labeled TEST |
| F2 | Recolor **Yield Scale** to the light AppTheme | yield_scale_screen.dart:137 (21 FarmerTheme refs) | ~1–1.5 h | low-med (tests exist) | Removes both mid-flow dark flips — the capture flow becomes one continuous light experience for a European audience. Dashboard + Proof Wallet stay dark (presentable as the deliberate "home/vault" surfaces) |
| F3 | Replace raw `e.toString()` error text with a human sentence | moisture_verification_screen.dart:137 (+1 sibling) | ~30 min | trivial | Raw exceptions on screen read as broken |
| F4 | Local **"verifier view"** page: static HTML served via `python -m http.server`, `DMRV_ALLOWED_ORIGIN` pointed at it, polls the compliance endpoint and renders checklist + credit | new file, no app/backend changes | ~1–2 h | low (isolated) | Turns the B5 curl into a demo-winning finale ("this is what the verifier sees") |
| — | NOT tonight: spinner timeouts, UNKNOWN_ARTISAN fallback, theme-system work, any backend change, any release build | | | | Risk/benefit fails the night before a demo |

## 1.4 Rehearsal checklist (evening-of)

1. Boot backend → health 200. 2. Mint token+spares. 3. Build+install debug APK. 4. Enroll (auto at startup). 5. Run the FULL flow once: sourcing → moisture → pyrolysis (virtual temp ramp) → yield (mock scale stabilizes) → end-use → dashboard shows synced. 6. Hit the compliance endpoint for that batch — confirm the checklist/credit renders. 7. Leave this completed batch in place so Proof Wallet is non-empty on stage. 8. Grant camera+location permissions before presenting. 9. Screen-record a full successful run as the fallback video.

## 1.5 Known demo risks (accepted, with counters)

- Sync shows only "N RECORDS PENDING" with no reason on failure → keep the backend visible in a terminal; restart fixes most.
- Token reuse crash → spares (B3).
- Media >10 MB rejected → default camera captures are fine; don't feed gallery photos.
- First backend boot runs migrations (~10–30 s) → start it minutes before, not during.

---

# PART 2 — The dual-UI (India + Europe) + white-label map

## 2.0 The one open DECISION (blocks Stage A step 5, nothing before it)

**D1 — What is the India (Field) skin's visual identity?** The docs conflict, and the roadmap misquotes the spec:
- [06_TIER5_UI_PLATFORM.md](06_TIER5_UI_PLATFORM.md) T5.2 says unify on **dark neon** (FarmerTheme) "per the UX_FIELD_THEME_SPEC".
- But [UX_FIELD_THEME_SPEC.md](../UX_FIELD_THEME_SPEC.md) (the newest design doc, 2026-07-03) specifies the opposite: **warm light "paper & machinery"** (`paper #ECE7DC`, machine-orange actions, tractor-green confirmed, blue *mohar* stamp for certified) and argues from sunlight physics that dark loses outdoors — it kills the dark "vault" aesthetic by name.
- Legacy option: light titanium (old AppTheme) for both, differentiating skins only by density.

**Recommendation on record:** paper-&-machinery for India (newest thinking, strongest reasoning, computed AA contrast table already in the spec, distinctly Indian trust metaphors); Europe/Pro starts from light titanium per T5.8 (docs agree on that half). The dark FarmerTheme retires. Decision is the user's; the token architecture (2.1) is identical under any choice — only the `DmrvTokens.field` values change.

## 2.1 Execution map (merged: T5 roadmap × UX execution phases)

The T5 roadmap (engineering) and the UX_EXECUTION_PLAN (design system) describe the same work at
different altitudes. Merged sequence, with the authoritative source per step:

| Step | What | Source of truth | Effort | Gate (proof of done) |
|---|---|---|---|---|
| **A0** | `DmrvTokens` ThemeExtension: semantic roles (surface/textPrimary/accent/success/danger/…), two instances (`field`, `pro`), `buildTheme()` feeding real Material ThemeData, `context.tokens` getter, old themes as `@Deprecated` aliases | T5.1 (architecture) + UX_FIELD_THEME_SPEC §1 (field values, post-D1) + AppTheme (pro values) | L | Non-null test for both skins; **WCAG ≥4.5:1 unit test** for text pairs on both surfaces (kills U7 forever); suites green |
| **A1** | Golden-test harness + contrast gate in CI + goldens baseline | UX_EXECUTION_PLAN Phase 0.3/0.7 (the T5 plan defers this to T4.5 — do it HERE; migrating 9 screens without visual regression lock is how drift happened the first time) | M | Golden harness runs in CI; baseline committed |
| **A2** | Migrate all 12 UI files to tokens, leaf-first: integrity_footer → premium_field_components → rugged_button → 7 product screens → camera_debug_view. Delete the 9 private `_errorRed` consts + 61 hex literals; normalize radii/spacing | T5.2 (mechanical per-file tables in UI_CONSISTENCY_AUDIT §2–4) | XL | `grep "Color(0x" lib/ui/` = 0 outside tokens.dart; zero `AppTheme.`/`FarmerTheme.` refs; batch flow = one continuous theme; goldens + 153 tests green |
| **A3** | Merge components: `DmrvButton` (RuggedButton+PremiumFieldButton), `DmrvPanel`, one `DmrvErrorPanel`/`DmrvLoading`/`DmrvEmptyState`; delete dead `PremiumActionCard`+`PremiumInputField`; fix armorSlate35 WCAG fail | T5.3 + T5.4 | L+M | grep for old names = 0; error states render identically (golden per skin) |
| **A4** | String externalization: ~10 → 60–120 ARB keys (en/hi); brand strings ("TerraCipher", "dMRV Field Terminal v3.0" — dashboard_screen.dart:511,518) go to brand config, NOT ARB | T5.5 (supersedes half of T4.6) | L | en/hi parity test; no-raw-literal grep test |
| **A5** | Navigation coherence: named routes; total freeze-forward back policy with `PopScope` (today it's half-enforced — the actual bug) | T5.6 | M | Widget test asserts back-stack policy per step |
| **B1** | Skin switch: `AppSkin {field, pro}` from `--dart-define=DMRV_SKIN` (later: tenant remote config); debug live-toggle | T5.7 | M | `--dart-define=DMRV_SKIN=pro` re-skins every screen, zero code edits — the honesty test of Stage A |
| **B2** | Calibrate the Pro/EU skin as a real surface: restrained success-green (gold reads "warning" to EU eyes), 56sp max hero (not 96sp glove sizing), denser gaps, locale-driven date/number formats via one `formats.dart`, `SKINS.md` | T5.8 | L | Side-by-side screenshot sheet signed off; contrast tests pass for pro values |
| **B3** | Golden matrix: 9 screens × 2 skins × (en, hi); structural both-skins-defined enforcement (required ctor params, no defaults) | T5.9 | M | CI renders both skins |
| **C1** | `Brand` config: appTitle/logo/footer/accent-override via `--dart-define-from-file=brand/<name>.json`; `grep TerraCipher lib/` → 0 | T5.10 | M | Fictional-partner JSON boots visibly rebranded |
| **C2** | Android/iOS flavors per brand (own id/icon/label; keystore-per-brand) | T5.11 — **depends on T0.6 (real keystore) — currently missing** | L | Two branded builds coexist on one device |
| **C3** | `scripts/new_whitelabel.sh` + WHITELABEL.md runbook; target <1 day/brand | T5.12 | M | Run end-to-end for a fictional brand; timed |

**Not in this track (explicitly):** Stage D multi-tenant SaaS (T5.13–16 — wants T3.4 read API + T4.1 module split first); the Batch-Checklist UX restructure + voice prompts (UX_BUILD_PLAN Phases 2–5 — a product-shape change, valuable but separable from the skin/white-label goal; do after B3 or in parallel by a second track); Priya's Console.

## 2.2 Dependency & sequencing notes

- **Order within the goal:** A0→A1 can start immediately after D1 is decided; A2 must not start before A1 (golden lock first); B* must not start before the Stage-A gate (skinning two inconsistent UIs doubles the mess — roadmap's own rule); C2 blocked by T0.6 (release keystore).
- **vs the demo:** none of Part 2 touches tomorrow. Cut the demo build first; start A0 on a branch after.
- **vs T3 (paused mid-tier):** T3.1 is committed; T3.4-onward paused. UI track and T3 are independent — resume T3 opportunistically (T3.4's read API also powers a real verifier dashboard, the grown-up version of demo fix F4).
- **vs T4.5 goldens:** A1 builds the golden infra early; T4.5 then inherits it (don't build twice).
- **Rough sizing honestly:** Stage A ≈ 2–3 weeks, Stage B ≈ 1 week, Stage C ≈ 1 week (C2 gated on keystore). The XL item is A2 (12 files) — mechanical but wide; the audit's per-file tables make it a checklist job.

## 2.3 Gaps the docs do NOT cover (flagged, not solved)

1. **Phase D mockups were never produced** (UX_EXECUTION_PLAN Phase D deliverables don't exist) — A2 can proceed from token tables without them, but the paper-&-machinery *stamp/receipt* visual motifs (mohar, parchi) need at least rough visual definition before Proof Wallet is restyled.
2. **Voice-prompt assets** (recorded Hindi clips) — a content/budget item, no engineering blocker.
3. **EU locale content** — Pro skin ships en first; de/fr/etc. are new ARB files later (cheap after A4).
4. **The demo-mode virtual sensors are debug-only** — fine for demos from your laptop, but a Europe-facing sales build that works without hardware would need a sanctioned "training mode" design (currently forbidden in release, deliberately).
