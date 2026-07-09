# Kon-Tiki dMRV — UI Build Plan ("Trusted, Clean, Villager-First")

*Execution companion to [`UX_DESIGN_PLAN.md`](UX_DESIGN_PLAN.md). That doc is the source of
truth for tokens, palette, type, and rationale. This doc is **how we build it** to a bar where
a non-reading kiln operator (Aarav, §1) uses it without training and a carbon buyer/auditor
(Priya) trusts it enough to pay. Stack is fixed: Flutter + Riverpod + Drift + the existing
BLE/sync services. This plan does not change the architecture; it specifies the build.*

---

## 0. What "billion-dollar trusted, clean, easy for a villager" means — made testable

Adjectives don't ship. We convert the aspiration into **pass/fail acceptance criteria** the
whole team builds against. If a screen fails any of these, it isn't done.

### 0.1 The three questions every screen answers in < 2 seconds
A villager glancing at any screen, in sunlight, must instantly know:
1. **Where am I?** — batch + step, top-left, icon + number ("🔥 Burn #A47 · 4/9").
2. **What do I do now?** — exactly ONE obvious primary action, bottom, full-width, thumb-reach.
3. **Is my data safe?** — the persistent integrity footer, always visible.

If answering any of the three requires reading a sentence, scrolling, or thinking — redesign.

### 0.2 The "grandmother test" (villager-easy, made concrete)
The build target: **a first-time user who cannot read completes a full burn log with zero
training and zero typing.** Operationalized as hard rules:
- **Icon-first, text-second, number-third, prose-last.** Every actionable element leads with a
  glyph and a color, not a word. Hindi label supports the icon; it never carries the meaning alone.
- **No keyboard on the critical path.** Weight comes from BLE or a big number-pad; identity from
  QR scan; choices from large image-tiles — never a free-text field the villager must spell into.
  (Free text exists only for the desk persona Priya, never for Aarav.)
- **One decision per screen.** If a screen forces two independent choices, split it.
- **Every action is reversible or confirmable.** No destructive action without a physical
  "hold-to-confirm"; no silent commits.
- **Nothing is ever a dead end.** Every error/empty/offline state offers exactly one way forward.

### 0.3 What "billion-dollar trusted" is engineered from (not decoration)
Trust here is *earned and shown*, not skinned on. Four pillars, each a build requirement:
1. **Visible integrity** — the app continuously proves data is captured, signed, and safe
   (§3). The `IntegrityFooter` and `Proof Wallet` are the load-bearing trust surfaces.
2. **Radical honesty about state** — the UI must **never show a batch as "credit / certified"
   when the backend says `provisional`.** Provisional-vs-issued is rendered as two visibly
   different things (§3.3). Faking "done" is the fastest way to destroy buyer trust in an audit.
   *This is the direct UI contract with the C0–C10 compliance gate.*
2. **Never-lose-data** — every capture writes to the encrypted local outbox *before* any network
   attempt; the UI says "saved on device" the instant it's local, and treats offline as normal,
   not as failure. A villager who loses one burn's data once will never trust the app again.
4. **Premium finish** — consistent tokens, real micro-motion on confirmations, no jank on cheap
   devices, no half-migrated screens. "Clean" = one design language end-to-end (kills the
   two-theme debt in §2 of the design plan) + disciplined whitespace + a single, calm accent
   system. Cheap-feeling inconsistency reads as "untrustworthy" to both personas.

### 0.4 Non-negotiable device reality (the build must survive these)
- Cheap Android (2–3 GB RAM, weak GPU) → 60fps is not guaranteed; motion has a budget (§7.4).
- Direct sun → the contrast gate from design-plan §5.5 is a build blocker, not a nicety.
- Gloves/ash hands → ≥64px targets, ≥12px gaps, heavy haptics (already in `RuggedButton`).
- 2G/offline default → no spinner ever blocks a local action.

---

## 1. Villager-first interaction doctrine (the "how it feels")

These are the concrete tactics that make it *look easy to work with*. Applied to every screen.

### 1.1 Communicate in four channels, ranked
In priority order, because literacy is not assumed: **① Icon/color → ② Number → ③ Hindi word →
④ Voice.** Every state and action uses at least the first two.
- **Color = meaning, consistently** (from design tokens): grey ○ = not started, amber ◐ =
  pending/do-this, green ● = done/safe, red = problem-that-blocks-your-credit, blue = live/connected.
  A villager learns these five colors once and can then operate the whole app by color alone.
- **Voice prompts (NEW — highest-leverage villager feature; extension beyond the design plan).**
  A speaker icon on every screen plays a ~5s Hindi (and local-dialect) audio instruction:
  *"अब कोयले का वज़न तराज़ू पर रखें"* ("now put the biochar weight on the scale"). Rationale:
  many target users read Hindi haltingly; audio removes the literacy barrier entirely and is the
  single biggest driver of the "no training needed" goal. Ship as pre-recorded audio assets keyed
  to screen+state; **not** TTS (offline + dialect quality). Flag for content/localization budget.

### 1.2 Input without typing
- **Weight/temp:** BLE sensor first; if absent, a giant number-pad sheet (not a text field).
- **Identity (kiln/batch/buyer):** QR scan first; manual = large digit entry, never spelling.
- **Choices (species, kiln type, methodology):** full-width **image tiles** with a photo + icon +
  Hindi word, single-select, ≥72px tall. Selecting = one tap, visibly locks in (green + haptic).
- **Yes/no / confirm:** the big `FieldButton`, plus hold-to-confirm for anything irreversible.

### 1.3 Progressive disclosure
Show only what this step needs. Cryptographic detail (hashes, signatures, GPS coords) is **hidden
by default** behind a "🔒 details" tap — present for the auditor's confidence, absent from
Aarav's daily path. Rationale: villagers need calm and few elements; the trust machinery should be
*provable on demand*, not *cluttering the flow*.

### 1.4 Confirm by feel, not just sight
Every commit fires `HapticFeedback.heavyImpact` **before** the async work (already the code's
pattern) + a visible grey→green state change. Under sun where color is hard to see, the villager
still *feels* the confirmation. This is core to trust-before-action: the tap "did something."

### 1.5 Forgiveness
- Autosave every field to the local DB on change; a killed app resumes exactly where it was.
- "Undo" for the last capture (10s window) instead of a confirm dialog on every step.
- Errors say what to *do* ("फ़ोटो दोबारा लें" + retake icon), never what went wrong technically.

---

## 2. Build order (phased, dependency-correct)

Expands design-plan §9 into a delivery sequence. Each phase ends green (analyze/tests/goldens)
and is independently demoable. Estimates are relative sizing, not calendar promises.

**Phase 0 — Foundations (unblocks everything) · ~1 sprint**
- `DesignTokens` (design-plan §5) as the single source; alias old `AppTheme`/`FarmerTheme` names
  to it so nothing breaks mid-migration.
- Localization scaffold: `intl` ARB files (Hindi + English), an icon registry, and the **voice-
  asset pipeline** (audio keyed by `screen.state`).
- Golden-test harness + the contrast gate wired into CI (design-plan §5.5 done-criterion).
- Low-end device profile + `prefers-reduced-motion`/frame-budget motion switch (§7.4).

**Phase 1 — Component kit · ~1 sprint** (§6)
- `FieldButton` (merge `RuggedButton`+`PremiumFieldButton`), `ReadingCard`, `ChecklistRow`,
  `IntegrityFooter` (promote existing widget), `FieldFormRow`, `ImageTileSelect`, `VoicePrompt`,
  and the state widgets (loading/empty/error/offline). All with `Semantics` + haptics baked in.
- Every component ships with a golden test in light theme + a sunlight-contrast assertion.

**Phase 2 — The spine: Batch Checklist + navigation · ~1 sprint** (§3.1 design plan)
- The `Checklist` hub wired to the backend `provisional_reasons` / `/compliance` response.
- Home / Batch List. Global `IntegrityFooter`. This is the highest-leverage phase — it reframes
  the whole app from "wizard" to "resumable checklist" and makes progress/trust visible.

**Phase 3 — Capture screens · ~2–3 sprints**
- In dependency order: Secure Camera (used by others) → Biomass Sourcing → Moisture → Pyrolysis
  (BLE temp) → Yield (BLE scale) → Transport → Composite Sample → End-Use/Delivery.
- Recolor to tokens as each is built; **delete `FarmerTheme` after the last screen migrates.**

**Phase 4 — Trust surfaces & reward · ~1 sprint**
- Proof Wallet + the `verifiedVault` treatment + the "minted" celebration (design-plan §8).
- Sync/Integrity detail screen.

**Phase 5 — Polish, a11y, field test · ~1–2 sprints**
- Motion pass, empty/error/offline states everywhere, full a11y audit, the WebAIM/axe gate,
  and **real usability testing with actual operators** (§8.3) — the only true proof of §0.2.

**Phase 6 (parallel, later track)** — Priya's Console (desk/admin, dense, English).

---

## 3. Trust architecture (the load-bearing surfaces, in build detail)

### 3.1 The Checklist is the trust spine
- Renders the batch's live `provisional_reasons` as rows; each row = one methodology item with
  an ○/◐/● state chip (design-plan §3.1) + icon + Hindi label + optional voice.
- A **progress ring** (% complete) is the screen's hero. Rationale: turns an opaque compliance
  gate into an obvious "you're 6 of 9 done" — the single strongest "this is easy and I'm making
  progress" signal.
- **"SUBMIT" does not exist until 100%.** You cannot submit an incomplete credit — the UI mirrors
  the backend refusing to sign a provisional batch. This is honesty rendered as interaction.
- Data source: a Riverpod provider that reads the local batch + outbox state and, when online,
  reconciles with `GET /api/v1/batches/{uuid}/compliance`. Offline, it computes the same checklist
  locally from what's captured, so progress is always truthful without a network.

### 3.2 The Integrity Footer (always-on reassurance)
- Persistent bottom strip on every screen: `🔒 3 saved · 1 uploading · all signed`.
- Tap → Sync detail (what's local, what's uploaded, when last synced). On the `verifiedVault`
  dark surface so it reads as "the secure layer."
- Rationale: directly answers Aarav's #1 anxiety ("is it lost if I have no signal?") continuously,
  so he never has to wonder. This is why villagers will *keep* using it.

### 3.3 Provisional vs Issued — two visibly different things (the honesty contract)
- A batch that is captured-but-not-issuable shows a **calm amber "In progress / being verified"**
  state — never a checkmark, never "credit," never a number that looks final.
- A batch the backend has signed (`lca_signature` present, `provisional=false`) shows the
  **`verifiedGold` sigil on the `verifiedVault` surface** — the one premium "certified" moment.
- Build rule: the "issued" visual is **gated on the server's signed state**, not on local
  completion. The client must not self-promote a batch to "certified." Rationale: an auditor who
  finds the app calling a provisional batch "issued" will distrust the entire dataset — real
  trust requires the UI to be as conservative as the compliance engine.

### 3.4 The Proof Wallet (the reward loop)
- Batches as "proof cards": feedstock, date, GPS thumbnail, credit state badge, and a hidden-by-
  default cryptographic block (signature/hash/anchor) behind "🔒 details."
- The provisional→issued transition triggers the one lavish animation in the whole app
  (design-plan §8). Rationale: this payoff is what sustains months of disciplined capture — the
  villager sees his burns become certified, valuable proofs.

---

## 4. Screen-by-screen build spec

Format per screen: **Job · Layout skeleton (top→bottom) · Villager-simplification · States ·
Flutter/data · Definition of Done.** All screens inherit: global `IntegrityFooter`, `VoicePrompt`
button top-right, back→Checklist, 24px layout padding, tokens only.

### 4.1 Home / Batch List (`dashboard_screen`)
- **Job:** see my burns + their progress; start a new one.
- **Layout:** title "मेरे बर्न" (My Burns) · list of batch cards (each = feedstock icon, date,
  progress ring, state chip) · sticky bottom `FieldButton` primary "＋ नया बर्न" (New Burn).
- **Villager:** batches are big tappable cards with a photo + ring, not a text table. New-burn is
  the one obvious action.
- **States:** empty = friendly illustration + the one CTA; offline = normal (footer shows counts);
  loading = skeleton cards.
- **Flutter/data:** `batchListProvider` (Drift query, live). No network needed to render.
- **DoD:** first-time user identifies "start a new burn" in <2s without reading; ring state matches
  backend; renders offline.

### 4.2 Batch Checklist (NEW — the hub) §3.1
- **Job:** show the 7–9 steps + % to issuable; route to any step.
- **Layout:** progress ring (hero) · `ChecklistRow` list · (at 100%) a `confirm` `FieldButton`
  "जमा करें" (Submit).
- **Villager:** color-coded rows; tap any to do it; any order allowed; voice reads the next
  undone step.
- **States:** a failed/expired check (GPS mismatch, expired calibration) = a red row with a plain
  fix; never a raw reason code.
- **Flutter/data:** `batchComplianceProvider` (local compute + online reconcile with `/compliance`).
- **DoD:** progress truthful offline; SUBMIT absent < 100%; red rows give an action, not a code.

### 4.3 Secure Camera (`secure_camera_screen`) — built first (dependency)
- **Job:** capture a photo hashed + GPS/EXIF-stamped at source.
- **Layout:** full-bleed viewfinder · big shutter · after capture: preview + "✓ use" / "↺ retake".
- **Villager:** it's just a camera — the hashing/stamping is invisible. Guidance overlay (e.g.
  "flame curtain" framing) as a simple silhouette, not instructions.
- **States:** permission/hardware fail = block with a clear reason + retry; **never fabricate a
  capture** (integrity). Low light = torch prompt.
- **Flutter/data:** existing capture service; returns an asset ref + sha256 to the caller.
- **DoD:** hash computed at source; a failed capture cannot be mistaken for a success; EXIF GPS
  attached.

### 4.4 Biomass Sourcing (`lantana_sourcing_screen`) — C1
- **Job:** feedstock + input amount + measurement method.
- **Layout:** species `ImageTileSelect` (photo tiles) · amount (BLE weight or number-pad) · method
  toggle (direct-weigh / yield-conversion as two big icon tiles) · primary "आगे" (Next).
- **Villager:** species chosen by picture; method by icon; amount by scale/pad — zero typing.
- **States:** offline-safe (local write); manual-weight fallback always present.
- **Flutter/data:** `insertBiomassSourcingWithOutbox`; writes then returns to Checklist.
- **DoD:** completable without reading or keyboard; C1 checklist row → ◐ then ● on sync.

### 4.5 Moisture Capture (`moisture_verification_screen`) — C2
- **Job:** ≥10 photographed readings, ≥1 per 100 kg biomass.
- **Layout:** a **counter hero** ("7 / 10") · big "＋ रीडिंग जोड़ें" (add reading) → number-pad +
  auto camera · a grid of captured reading thumbnails.
- **Villager:** the counter makes the goal obvious ("need 10, have 7"); each reading is pad + snap.
- **States:** photo hash fail → retake; the required count adapts to biomass (from C2 rule) and is
  shown, never assumed.
- **Flutter/data:** `insertMoistureReadingWithOutbox` per reading; photo via Secure Camera.
- **DoD:** counter matches the ≥1/100kg-min-10 rule; each reading photographed; resumable.

### 4.6 Pyrolysis / Burn (`pyrolysis_screen`) — C0/C3
- **Job:** live temp curve + kiln type + (open-kiln) flame photos.
- **Layout:** kiln-type tiles (open/closed, once) · **live temp hero** on a `verifiedVault`-dark
  chart with `telemetryCyan` trace · connection pill (blue live / grey / red lost) · flame-photo
  slots (open-kiln: 3 labeled by silhouette) · "बर्न पूरा" (End Burn) confirm.
- **Villager:** watches a big number + line; the required photos are obvious empty slots to fill.
- **States:** BLE thermocouple drop → top banner + last-good reading held; **session never lost**;
  burn continues.
- **Flutter/data:** BLE temperature service stream → `pyrolysis_writer`; photos via Secure Camera.
- **DoD:** temp stream renders at ≥30fps on low-end; disconnect is non-blocking; open-kiln photo
  slots enforce C3 before the row goes ●.

### 4.7 Yield Capture (`yield_scale_screen`) — C6 mass
- **Job:** BLE crane-scale wet-yield reading.
- **Layout:** `ReadingCard` — live kg hero (`SpaceMono`) · connection pill · "लॉक करें" (Lock In)
  disabled until the reading is stable (code already models `idle → "----"`).
- **Villager:** one number, one button that lights up only when the weight settles.
- **States:** scale disconnected → big reconnect card + manual-entry escape hatch.
- **Flutter/data:** BLE weight service; `insertYieldMetricsWithOutbox`.
- **DoD:** cannot lock a mid-swing value; manual fallback works; lock fires haptic + green sweep.

### 4.8 Transport Event(s) (NEW small) — C6
- **Job:** per leg: distance, weight, vehicle, fuel — for biomass and biochar.
- **Layout:** "＋ यात्रा जोड़ें" (add trip) → sheet with material toggle (biomass/biochar tiles),
  vehicle tiles, number-pads for distance/weight/fuel · list of added legs.
- **Villager:** vehicles as icons; everything a pad or tile; add as many legs as needed.
- **States:** offline-safe; a leg is deletable (undo).
- **Flutter/data:** `insertTransportEventWithOutbox` (many per batch).
- **DoD:** multiple legs; no typing; audit-only today (matches backend `TRANSPORT_EVENTS_ENFORCED`).

### 4.9 Composite Sample (NEW small) — C4
- **Job:** set-aside sub-sample photo + kiln/batch QR.
- **Layout:** QR-scan kiln + batch (or manual digits) · one photo · "सहेजें" (Save).
- **Villager:** scan two codes, take one photo, done.
- **Flutter/data:** `insertCompositePileSampleWithOutbox`; photo via Secure Camera.
- **DoD:** QR or manual both work; photo hashed; C4 row → ●.

### 4.10 End-Use / Delivery (`end_use_application_screen`) — C5
- **Job:** delivery record + buyer identity + GPS.
- **Layout:** delivery date (date wheel) · amount (pad) · buyer (QR of buyer card, or name via the
  *one* allowed text field — this is a per-batch, not per-reading, so acceptable) · GPS auto-captured
  · farmer/field photo.
- **Villager:** mostly scan/pad/auto; the buyer name is the single unavoidable text entry, kept large.
- **States:** GPS degraded → capture anyway, flag for review (don't block).
- **Flutter/data:** `insertEndUseWithOutbox`.
- **DoD:** C5 row → ● with delivery + buyer present; GPS attached.

### 4.11 Proof Wallet (`proof_wallet_screen`) §3.4
- **Job:** the reward — batches as signed proofs; provisional vs issued.
- **Layout:** proof cards; state badge; hidden crypto block behind "🔒 details"; issued cards get
  the `verifiedGold`/`verifiedVault` treatment + minted animation.
- **DoD:** issued state gated on server signature (§3.3); crypto detail present-on-demand; the
  minted celebration fires once per issuance.

### 4.12 Sync / Integrity detail (`integrity_footer` → full screen) §3.2
- **Job:** the offline story in full — what's local, uploaded, last sync, retry state.
- **Villager:** a simple list with green ●/amber ◐ per item + "सब सुरक्षित" (all safe) summary.
- **DoD:** every outbox state is explained in plain terms; a stuck item shows a human reason + retry.

---

## 5. Cross-cutting systems

### 5.1 Localization & literacy
- `intl`/ARB, Hindi default + English; **no hardcoded strings.** Every string has an icon; the
  icon is the primary carrier. Voice asset per `screen.state`. RTL not required (Devanagari LTR)
  but layouts use `Directionality`-safe widgets anyway.
- Numbers rendered in the user's numeral preference (Devanagari vs Latin digits) — decide with the
  operator group; default Latin (scales/sensors show Latin).

### 5.2 Offline & sync UX (never-lose-data, made visible)
- Every capture: local encrypted write FIRST → UI says "सहेजा गया" (saved) immediately → outbox
  syncs opportunistically. Network state changes the footer, never blocks a screen.
- Sync conflicts/failures surface only in the Sync detail screen, in plain language, with retry.

### 5.3 Accessibility (beyond literacy)
- ≥64px targets, ≥12px gaps, AA contrast (design-plan §5.5 gate).
- Full `Semantics` labels (already in `RuggedButton`) → screen-reader + automated-flow testable.
- Text scales to the device font-size setting without breaking layout (test at 130%).
- Color is never the *only* signal — pair with icon + position (colorblind-safe).

### 5.4 Motion budget (cheap devices)
- Default animations 150–250ms ease-out. A runtime frame-budget probe (or `reduce motion`)
  downgrades to instant transitions + a single state-color change on low-end hardware.
- The only "expensive" animation (minted celebration) is capped and skippable; it never runs
  mid-capture.

### 5.5 Error philosophy
- Errors are actionable, plain, and localized; they name the fix, not the fault.
- Every error state reassures that other data is safe (§0.3).
- Integrity-critical failures (hash mismatch, camera fake) **fail loud and block** — the one place
  we are deliberately *not* frictionless, because a silent bad capture poisons a credit.

---

## 6. Component build spec (Flutter API sketch)

All in `lib/ui/design/` + `lib/ui/widgets/`. Tokens from `DesignTokens`. Each ships with a golden
test and a `Semantics` label.

- **`FieldButton`** — `variant {primary, confirm, danger, disabled}`, `label`, `icon?`,
  `onPressed`, `semanticId`. ≥64px, radius 12, `heavyImpact` before callback, disabled state
  visually unmistakable. Replaces `RuggedButton` + `PremiumFieldButton`.
- **`ReadingCard`** — `value`, `unit`, `connectionState {live, idle, lost}`, `onLock`,
  `stable:bool`. Hero `SpaceMono`; lock disabled until `stable`; green sweep + haptic on lock.
- **`ChecklistRow`** — `icon`, `labelKey`, `state {notStarted, pending, done, failed}`, `onTap`,
  `fixHint?`. Chip color from tokens; failed shows `fixHint`.
- **`ProgressRing`** — `completed/total`; the Checklist hero.
- **`IntegrityFooter`** — reads sync provider; `savedCount/uploadingCount`; tap → Sync detail;
  `verifiedVault` surface.
- **`ImageTileSelect`** — `options[{image, icon, labelKey}]`, single-select, ≥72px tiles, lock+haptic.
- **`NumberPadSheet`** — big glove-friendly pad; returns a number; no keyboard.
- **`VoicePrompt`** — `audioKey`; plays the localized clip; visible speaker glyph.
- **State widgets** — `LoadingState` ("saving to device…", skeleton), `EmptyState` (illustration +
  1 CTA), `ErrorState` (plain cause + 1 fix + "other data safe"), `OfflinePill` (neutral, not error).

---

## 7. Quality gates — "done" is proven, not claimed

### 7.1 Per-screen Definition of Done (all must pass)
1. Answers the three questions (§0.1) in <2s — verified in the grandmother test.
2. Completable with no keyboard on the critical path (except §4.10 buyer name).
3. One primary action, thumb-reachable, ≥64px.
4. All four states built: loading / empty / error / offline.
5. Tokens only (no `FarmerTheme`, no raw hex); passes the contrast gate on `#F0F4F8`.
6. `Semantics` labels present; text scales to 130%; haptic on commit.
7. Offline-first: local write before network; footer truthful.
8. Golden test (light) + widget test for the primary interaction.

### 7.2 Whole-UI Definition of Done ("billion-dollar villager-trusted")
- One design language end-to-end; `FarmerTheme` deleted; zero half-migrated screens.
- The grandmother test passes with ≥3 real operators (§8.3) at ≥90% task completion, unaided.
- No screen shows a provisional batch as certified (audited against the backend state).
- Cold-start, a full burn logged, app killed mid-flow and resumed with zero data loss — on a
  cheap Android in simulated sunlight.
- WebAIM/axe AA pass (design-plan §5.5) — CI-gated.

### 7.3 Device & condition matrix
- 2× cheap Android (≤3 GB), 1× mid, 1× tablet; Android 9–14.
- Sunlight rig (or max-brightness + glare) for the contrast check.
- Gloved-tap test. Airplane-mode / 2G-throttle test for the offline story.

### 7.4 Field usability testing (the only real proof of §0.2)
- Test with **actual kiln operators**, in Hindi/local dialect, no training, on the real device.
- Measure: task completion %, time-to-first-correct-action, points of hesitation, and the
  "do you trust this saved your data?" question. Iterate before Phase 6.

---

## 8. What this plan deliberately does NOT do (honesty)
- It does not make the credit *correct* — that's the backend/methodology work (transport factors,
  the dormant gates, attestation). A beautiful UI on an unverified credit is a liability; the UI's
  honesty contract (§3.3) is what keeps the two in sync.
- It does not add TTS or online dependencies to the villager path — voice is pre-recorded, offline.
- It does not restyle Priya's Console to the field aesthetic — that's a separate register (Phase 6).

---

## 9. First concrete step
Phase 0 → `DesignTokens` + the `FieldButton` merge are the smallest change that removes the
two-theme debt and unblocks every screen. If you want, that's where I start turning this plan into
code.
