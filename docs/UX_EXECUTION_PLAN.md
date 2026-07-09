# Kon-Tiki dMRV — UI/UX Execution Plan (phase-by-phase, with test gates)

*The granular work-breakdown + test roadmap. Reads on top of:*
- [`UX_DESIGN_PLAN.md`](UX_DESIGN_PLAN.md) — **what/why** (tokens, palette, type, screens, rationale)
- [`UX_BUILD_PLAN.md`](UX_BUILD_PLAN.md) — **how** (villager doctrine, trust architecture, build order)
- **this doc** — **execution**: numbered tasks (file-level), deliverables, and a hard **test gate
  per phase**. Nothing is "done" until its gate is green.

Stack (fixed): Flutter · Riverpod · Drift · existing BLE/sync services. Fonts: SpaceGrotesk /
SpaceMono / NotoSansDevanagari. Grounded scope (measured): **10 screens import `app_theme`, 4
import `farmer_theme`, 8 screens use `RuggedButton`/`PremiumFieldButton`.** Test infra today:
`flutter_test` + `mockito`/`mocktail`, 3 widget tests, **no golden or integration harness** → Phase 0
adds them.

---

## A. The quality bar carried through every phase: "premium, trusted, NOT overwhelming"

"Not overwhelming" is the hardest and most important constraint for this user. It is enforced as
**hard budgets** checked in every phase's gate — not left to taste:

| Rule (the "calm budget") | Limit | Why |
|---|---|---|
| Primary actions per screen | **exactly 1** | One obvious next tap; zero decision paralysis. |
| Distinct accent colors visible at once | **≤ 2** (+ neutrals) | More than two "loud" colors = anxiety; the palette has one action + one state color live at a time. |
| Above-the-fold interactive elements | **≤ 5** | A villager scans, doesn't study. Overflow → progressive disclosure. |
| Text blocks (sentences) per screen | **≤ 1** | Icon/number/voice carry meaning; prose is a last resort. |
| Simultaneous animations | **1** | Motion confirms one thing; never competes. |
| Whitespace | ≥ 24px between groups; cards breathe | Emptiness reads as premium + calm; density reads as cheap + stressful. |
| Font families on screen | **≤ 2 of the 3** at once | Grotesk+Mono, or Grotesk+Devanagari — never all three shouting. |

**Premium finish** is likewise concrete: one design language end-to-end (no half-migrated screen),
pixel-consistent 8px rhythm, real (but restrained) confirmation motion, zero jank on cheap Android,
and the single "vault gold" moment reserved for the certified proof. These are gate items, not vibes.

---

## B. Test strategy (the pyramid this plan builds against)

Every phase writes tests at the right level; the phase gate lists exactly which must pass.

1. **Unit** (`flutter_test`) — token math, formatters, provider logic (checklist %, sync counts).
2. **Widget** (`flutter_test`) — each component's interaction (tap → haptic → callback, disabled
   states, semantics). Pattern already exists (`rugged_button_test.dart`).
3. **Golden / visual regression** (ADD `golden_toolkit` or `alchemist` in Phase 0) — every
   component + every screen state, rendered in the light theme at 1x and at 130% text scale, so
   the "premium, consistent, not-overwhelming" bar is regression-locked. Golden diffs fail CI.
4. **Contrast gate** (Phase 0 script + WebAIM/axe at handoff) — design-plan §5.5; CI-blocking.
5. **Integration** (ADD `integration_test` in Phase 0) — full-flow: cold start → log a burn →
   kill app mid-flow → resume with zero data loss → offline capture → sync. On an emulator profile.
6. **Manual / field** — the grandmother test + sunlight + gloves + real operators (Phase 5).

**Definition of "gate green" for any phase:** all listed automated tests pass in CI, goldens
updated + reviewed, the calm-budget (§A) checklist ticked for any screen touched, `flutter analyze`
0 errors, and the phase's manual checklist signed off.

---

## PHASE D — Detailed Design (the "very detailed design" you start next) · design track

**Objective:** produce the high-fidelity, buildable design so every later phase implements from a
locked spec, not from imagination. This is where "make it look best" happens — before code.

**Tasks**
- **D.1** Render the **living design-system artifact**: a single page showing the real palette
  swatches (with the §5.5 verified ratios), the type scale in all three fonts, spacing tokens, and
  every component in all states. (Deliverable can be an Artifact page or Figma; must be the visual
  source of truth.)
- **D.2** High-fidelity mockups for all 12 screens (design-plan §3), each in **4 states**: default,
  loading, empty, error/offline — plus the sunlight/high-contrast variant.
- **D.3** The **calm-budget audit** (§A) applied to every mockup: annotate the single primary
  action, the ≤2 accents, the ≤5 above-fold elements. Reject/redo any screen that exceeds budget.
- **D.4** Interaction/motion spec: the confirmation micro-motion, the checklist ring fill, the
  minted celebration — as short prototypes or precise specs (duration, easing, trigger).
- **D.5** Icon set + voice-prompt script list (Hindi + dialect) per screen.state (from build-plan §1.1).
- **D.6** Localization string inventory (every label, keyed) so ARB files in Phase 0 are complete.

**Deliverables:** design-system artifact, 12×4 screen mockups, motion specs, icon set, voice script,
string inventory.

**Test gate (design review, not code):**
- Every screen passes the §A calm-budget checklist (documented per screen).
- Contrast of every text/bg pair in the mockups computed and ✅ (design-plan §5.5).
- A 3-person "glance test" on static mockups: can they answer the §0.1 three questions in <2s?
- Sign-off that no screen shows provisional-as-certified (build-plan §3.3).

**Unblocks:** all build phases. **Risk:** scope creep → cap at the 12 core screens; Console (Priya)
mockups deferred to Phase 6.

---

## PHASE 0 — Foundations & harness · ~1 sprint · unblocks everything

**Objective:** one token source, test harness, i18n + voice pipeline, motion/contrast gates in CI.

**Tasks**
- **0.1** `lib/ui/design/design_tokens.dart` (NEW) — the single semantic token set from design-plan
  §5 (`surface`, `onSurface`, `onSurfaceMuted`, `action`, `confirmed`, `error`+`errorText`, `live`,
  `verifiedVault`, `verifiedGold`, `telemetryCyan`, `hairline`) + type scale + spacing constants.
- **0.2** Alias `AppTheme` and `FarmerTheme` names to `DesignTokens` (deprecation shims) so the 14
  importing files keep compiling during migration; mark both `@Deprecated`.
- **0.3** Add dev deps: a golden harness (`golden_toolkit` or `alchemist`) + `integration_test`.
  Commit a golden baseline workflow (`flutter test --update-goldens` policy documented).
- **0.4** i18n: `flutter_localizations` + `intl`, ARB files (`hi`, `en`) seeded from D.6 inventory;
  a lint/CI check that fails on any hardcoded user-facing string.
- **0.5** Voice-asset pipeline: `assets/audio/{locale}/{screen}.{state}.mp3` + a `VoicePrompt`
  loader keyed by `screen.state`; graceful no-op if an asset is missing.
- **0.6** Motion controller: a `MotionBudget` util that reads `MediaQuery.disableAnimations` /
  a runtime frame probe and exposes `fast()/instant()` durations; low-end → instant.
- **0.7** Contrast gate: a small script/test that asserts the token pairs from §5.5 against the
  `#F0F4F8` surface; wire into CI alongside the codegen check.

**Deliverables:** `design_tokens.dart`, deprecation shims, golden+integration harness, ARB files,
voice loader, motion util, contrast CI check.

**Test gate**
- Unit: token contrast test (§5.5 values) passes; `MotionBudget` returns instant under reduce-motion.
- CI: analyze 0 errors; hardcoded-string check active; golden harness runs (even if baseline empty).
- Existing 3 widget tests + full backend suite still green (no regression from shims).

**Risk:** golden flakiness across machines → pin a single render device/font in the golden config.

---

## PHASE 1 — Component kit · ~1 sprint · (build-plan §6)

**Objective:** every reusable widget built once, to spec, tested, golden-locked.

**Tasks (each = build + widget test + goldens in all states)**
- **1.1** `FieldButton` (NEW) — merge `RuggedButton` + `PremiumFieldButton`; variants
  primary/confirm/danger/disabled; ≥64px; `heavyImpact` before callback; `Semantics`.
- **1.2** Codemod the 8 screens' button call-sites to `FieldButton`; delete `rugged_button.dart`
  + the button in `premium_field_components.dart` (keep other premium bits until their screen migrates).
- **1.3** `ProgressRing`, `ChecklistRow` (states ○/◐/●/failed + fixHint).
- **1.4** `ReadingCard` (live/idle/lost pill, lock-disabled-until-stable, green sweep on lock).
- **1.5** `IntegrityFooter` — promote existing widget to a global, provider-driven strip.
- **1.6** `ImageTileSelect`, `NumberPadSheet` (no-keyboard inputs), `VoicePrompt` button.
- **1.7** State widgets: `LoadingState`, `EmptyState`, `ErrorState` (plain fix + "other data safe"),
  `OfflinePill`.

**Deliverables:** the widget library in `lib/ui/widgets/` + `lib/ui/design/`, all golden-tested.

**Test gate**
- Widget tests: each component's primary interaction (tap fires haptic + callback; disabled blocks;
  `ReadingCard` lock disabled until `stable`; semantics labels present).
- Goldens: every component in every state, light theme, 1x + 130% text — reviewed & committed.
- Calm-budget: no component alone exceeds its role; `FieldButton` renders one accent only.
- `RuggedButton` deleted; grep for `PremiumFieldButton` on migrated screens = only unmigrated ones.

**Unblocks:** all screens. **Risk:** the button codemod touches 8 screens → do it screen-by-screen
with goldens catching visual drift.

---

## PHASE 2 — The spine: Checklist + Home + global footer · ~1 sprint · (build-plan §3.1)

**Objective:** reframe the app from wizard to resumable, progress-visible checklist — the single
highest-leverage change for "easy + trusted."

**Tasks**
- **2.1** `batchComplianceProvider` (Riverpod) — computes the checklist from local Drift state;
  when online, reconciles with `GET /api/v1/batches/{uuid}/compliance`; offline path is truthful.
- **2.2** `batch_checklist_screen.dart` (NEW) — `ProgressRing` hero + `ChecklistRow` list; SUBMIT
  absent < 100%; failed rows show a plain fix.
- **2.3** `dashboard_screen` (Home/Batch List) recolor to tokens + batch cards with progress ring.
- **2.4** Wire `IntegrityFooter` globally (app shell) + the Sync detail screen (skeleton).
- **2.5** Navigation: every capture screen returns to Checklist (build-plan §3.2), not linearly.

**Deliverables:** checklist hub, reworked home, global footer, provider.

**Test gate**
- Unit: `batchComplianceProvider` — % correct for N combinations of captured/missing evidence;
  offline compute == online reconcile for the same state; SUBMIT gating at exactly 100%.
- Widget/golden: checklist in 0%/partial/100%/failed-row states.
- Integration: create batch → checklist shows all ○ → capture one item → row goes ◐→● and ring
  ticks up, **offline** (no network).
- Honesty check (automated): a `provisional` batch never renders a "certified" element.

**Risk:** local-vs-server checklist divergence → the provider treats server as authoritative when
reachable, local as truthful-optimistic offline, and reconciles on sync; test both directions.

---

## PHASE 3 — Capture screens · ~2–3 sprints · (build-plan §4)

**Objective:** build the 8 capture screens to spec + villager doctrine; finish the theme migration.

**Build order (dependency-correct):** Secure Camera → Biomass Sourcing → Moisture → Pyrolysis →
Yield → Transport → Composite Sample → End-Use/Delivery.

**Per-screen task template (repeat for each):**
- **3.x.a** Build layout from its design-plan §4 spec + Phase-D mockup, tokens only.
- **3.x.b** No-keyboard inputs (ImageTileSelect / NumberPadSheet / QR / BLE); wire to its Drift
  writer (`insert…WithOutbox`).
- **3.x.c** All 4 states (loading/empty/error/offline) + `VoicePrompt` + integrity footer.
- **3.x.d** Widget test (primary capture), goldens (4 states), calm-budget checklist.
- **3.x.e** Delete that screen's `farmer_theme`/`premium` imports.

**Screen-specific gate highlights**
- **Secure Camera:** hash computed at source; a failed/denied capture **cannot** be mistaken for
  success (integrity test); EXIF GPS attached.
- **Moisture:** counter enforces the ≥1/100kg-min-10 rule; every reading photographed; resumable.
- **Pyrolysis:** BLE temp stream renders ≥30fps on the low-end profile; disconnect is non-blocking
  and holds last-good; open-kiln enforces 3 flame photos before ●.
- **Yield:** cannot lock a mid-swing value; manual fallback works.

**Test gate (whole phase)**
- Every screen: widget + goldens (4 states) + calm-budget ticked + keyboard-free critical path
  (except End-Use buyer name) + offline-first write verified.
- **`farmer_theme.dart` deleted** after the last screen migrates; grep = 0 references.
- Integration: full burn logged end-to-end, offline, resumable after kill.

**Risk:** BLE flakiness in tests → mock the BLE services (mocktail) for widget/integration; keep a
manual on-device BLE checklist for Phase 5.

---

## PHASE 4 — Trust surfaces & reward · ~1 sprint · (build-plan §3.3/§3.4)

**Objective:** the payoff + the honesty contract, visibly premium.

**Tasks**
- **4.1** Proof Wallet — proof cards, state badge, hidden crypto block behind "🔒 details".
- **4.2** `verifiedVault` + `verifiedGold` treatment for **server-signed** batches only.
- **4.3** The one "minted" celebration (design-plan §8), motion-budget-gated, skippable.
- **4.4** Sync/Integrity detail screen — plain-language outbox states + retry.

**Test gate**
- Issued visual is gated on server signature (`provisional=false` + `lca_signature` present) —
  automated test that a locally-complete-but-unsigned batch shows "in progress", not "certified".
- Golden: provisional card vs issued card are visibly distinct (different token families).
- Minted animation runs once per issuance, respects `MotionBudget`, never mid-capture.

**Risk:** the celebration feeling "toy" vs "premium" → keep it a single restrained gold sigil
draw-on, not confetti; review against the §A calm budget.

---

## PHASE 5 — Polish, accessibility, field validation · ~1–2 sprints

**Objective:** prove the bar with real users and lock a11y/contrast.

**Tasks**
- **5.1** Motion pass; empty/error/offline states audited on every screen.
- **5.2** Full a11y: `Semantics` coverage, 130% text scale layout pass, colorblind-safe (icon+color),
  screen-reader flow.
- **5.3** WebAIM/axe AA gate on the rendered build (design-plan §5.5 done-criterion) — the two
  fragile tokens (`error` body text → `#B91C1C`; `onSurfaceMuted` ≥16px/65–70%) signed off.
- **5.4** Device matrix: 2× cheap Android, 1× mid, 1× tablet, Android 9–14; sunlight rig; gloved tap.
- **5.5** **Field usability test with ≥3 real kiln operators**, no training, Hindi/dialect — measure
  task-completion %, time-to-first-correct-action, hesitation points, "do you trust it saved?".
- **5.6** Iterate on findings; re-gate affected screens.

**Test gate (this is the whole-UI DoD from build-plan §7.2)**
- Grandmother test ≥90% unaided task completion with real operators.
- Zero-data-loss resume test passes on a cheap device in simulated sunlight.
- WebAIM/axe AA CI-green; no provisional-as-certified anywhere; one design language (no
  `farmer_theme`, no raw hex) confirmed by grep.

**Risk:** field access to operators → line up the test cohort during Phase 3 so Phase 5 isn't blocked.

---

## PHASE 6 — Priya's Console (desk/admin) · parallel later track

Dense, English, data-table register (design-plan §5.4): the `/compliance` checklist as a first-class
audit screen, project/kiln/scale registries, verification records. Same tokens, different density.
Own mockups + gate; **not** required for the field-app ship.

---

## C. Per-screen build checklist (the repeatable DoD — paste into each screen's PR)

```
[ ] Answers the 3 questions (<2s, glance test)         [ ] All 4 states built (load/empty/error/offline)
[ ] Exactly 1 primary action, ≥64px, thumb-reach       [ ] Tokens only — no farmer_theme, no raw hex
[ ] Keyboard-free critical path (note exceptions)      [ ] Contrast AA on #F0F4F8 (fragile tokens fixed)
[ ] Calm budget: ≤2 accents, ≤5 above-fold, ≤1 prose   [ ] Semantics labels + 130% text scale OK
[ ] Icon+color+number lead; Hindi + VoicePrompt        [ ] Offline-first: local write before network
[ ] Provisional≠certified (no false "done")            [ ] Widget test + goldens (4 states) committed
[ ] Haptic on commit; ≤1 animation; MotionBudget       [ ] flutter analyze 0 errors
```

## D. Sequencing & tracking
- **Order:** Phase D (design) → 0 (foundations) → 1 (components) → 2 (spine) → 3 (capture) →
  4 (trust) → 5 (field). Phase 6 parallel/after. D can start now; 0 can start in parallel since
  tokens are already decided.
- **Tracking:** each phase = one milestone; "done" = its Test gate green + goldens reviewed +
  checklist (§C) ticked for touched screens. Commit per phase (per the repo's per-phase discipline).
- **The line we hold:** a premium, honest UI on top of a credit engine whose numbers are still
  methodology-blocked (see the meeting questions doc). The UI must stay as conservative as the
  compliance gate — never render a credit as final that the backend calls provisional.

## E. First move
Start **Phase D.1** (the living design-system artifact — real swatches, type, components) so the
"make it look best" work has a concrete, reviewable source of truth; then **Phase 0.1** (`design_tokens.dart`)
in parallel. Say the word and I'll produce the design-system artifact and scaffold the tokens.
