# MASTER PROMPT v2 — TerraCipher Portal "Billion-Dollar Trust" (layout-locked to mockups)

> Repo root: `c:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`.
> Node + npm installed. Execute phases IN ORDER, ONE AT A TIME, STOP when a
> CHECK fails. FRONTEND-ONLY: every file lives under `portal/`. Never touch
> `backend/`, `lib/`, or anything else. Trust SOURCE CODE, not this doc's line
> numbers (they drift) — locate verbatim code before every edit. If a verbatim
> block can't be found, STOP and report; do not guess.

## ROLE & GOAL
You are a senior fintech product designer + front-end engineer. Raise the
VISUAL design + UX of this existing React app to Stripe / Mercury / Ramp
trust level. **Trust is the product.** Three pixel-target mockups accompany
this prompt (Batch Detail "Verified & Sealed", Compliance checklist, Evidence
gallery). Match their LAYOUT, HIERARCHY, and COMPONENT PLACEMENT closely; you
may exceed them. The COLOR SYSTEM is yours to choose within the constraints
below — the mockups' palette is a direction, not a spec.

## THE ONE RULE ABOVE ALL — layout yes, data no
The mockups contain **placeholder data the real API does not return.** You
must reproduce their LAYOUT while binding ONLY to fields that actually exist.
You must NOT invent, hardcode, or fabricate any of the following (verified
absent from `api.ts`):
- ❌ A reviewer / verifier name ("Reviewed by A. Okafor") — NO such field.
- ❌ Crop type, Harvest date, Farmer ID, Region — NO such fields.
- ❌ LCA Scope 1 / Scope 2 / Scope 3 / Baseline numbers — NO such fields.
- ❌ Lot number, Transport, Documentation status — NO such fields.
- ❌ A batch-level SHA-256 on the verdict card — there is NO batch hash;
  `sha256_hash` exists ONLY per evidence `MediaItem`.

**What actually exists** (bind only to these — from `api.ts`, READ-ONLY):
- `BatchRow`: `batch_uuid, device_id, project_id, status, provisional,
  reason_count, net_credit_t_co2e, wet_yield_kg, received_at`
- `Compliance`: `provisional, issuable, reasons[], checklist[]` where each
  `ChecklistItem` = `{ code, section, label, ok, enforcement }`
- `MediaItem`: `operation_id, filename, sha256_hash, uploaded_at,
  capture_type, capture_type_verified, exif_lat, exif_lon`
- `BatchDetail`: `batch, compliance, evidence_counts, media`
- `getSummary()`: `{ by_status, provisional, reasons_histogram }`

If a mockup card shows 4 rows of data but the API only backs 2, **render the 2
real rows and drop the card's fabricated rows** — a shorter honest card beats a
padded fake one. Missing single values render as an em-dash "—", never a guess.
Reproducing the mockup's *fake numbers* is a defect, not fidelity.

## STACK & HARD RULES (do not violate)
- React 18 + Vite + TS. Styling = design tokens in `src/styles.css` +
  per-component CSS Modules. NO Tailwind / CSS framework / new UI kit. Radix
  and lucide-react stay; add NO new runtime dependency.
- **Accessibility is non-negotiable and OUTRANKS pixel-matching the mockup.**
  WCAG AA, `axe` = 0 violations in BOTH themes, `:focus-visible` on every
  interactive element, `prefers-reduced-motion` respected, focus trap in
  dialogs, and **color is NEVER the sole status cue** (always icon or text +
  color). If a mockup color fails AA for its text/icon, you MUST adjust the
  value until it passes — the existing tokens are annotated with real contrast
  ratios; keep that discipline.
- DO NOT touch `api.ts`, `auth.ts`, `compliance.ts`, `qr.ts`, `lab.ts`, route
  paths, `RequireAuth`, or any `issueCredit` / `registryPost` /
  `submitLabResults` call shape. UI / markup / CSS only.
- **Zero hardcoded visual values in components** — add a token to `styles.css`
  first, then reference it. (Layout-only inline values like `gap`/`width` in a
  one-off flex row may stay if they use a `--space-*` token.)
- Never add reassurance copy. No new strings asserting "secure", "bank-grade",
  "trusted", "SOC2", trust seals, or security iconography that isn't backed by
  an actual verification state already in the data. `capture_type_verified` is
  real and already surfaced; the compliance `issuable` state is real. Trust is
  shown by craft — precision, restraint, consistency — never claimed in words.
- Self-hosted fonts only (already: Inter + IBM Plex Mono via @fontsource).
- Keep all routes, component names, exported symbols, and `data-testid`s;
  every change is additive or a swap, never a rename.

## DESIGN LAW: SUBTRACTION
Fewer colors, tighter type, more space, perfect hierarchy. Emptiness must read
as deliberate restraint, never as unfinished. Cleanliness is the trust signal.
Before adding anything, ask "can hierarchy do this instead of decoration?"

## TOKEN STRATEGY — remap in place, one system, AA-safe (CRITICAL)
The shipped app already has a disciplined token system used by ~13 CSS modules
(`--indigo-600`, `--text-primary`, `--surface-page`, `--border-hair`,
`--status-success-fg/-bg`, `--fs-*`, `--fw-*`, `--space-*`, `--r-*`,
`--shadow-sm/md`, `--dur-*`, `--ease-*`). **You will UPDATE THE VALUES of these
existing tokens toward the mockups' Stripe/Mercury feel — you will NOT
introduce a parallel set of new token names** (no `--brand-indigo` alongside
`--indigo-600`). One vocabulary. This avoids the two-systems drift that a
prior audit round just eliminated.

When you retune a color, VERIFY contrast with a real calculator before
committing. Targets (pick exact hexes yourself; these are the constraints):
- **Brand / action color** (`--indigo-600`): a confident indigo used ONLY for
  primary buttons, links, focus rings, active nav — never decoration. It must
  hit **≥4.5:1 on `--surface-card` white** because it's used for text/links.
  (Stripe's `#635BFF` is ~3.7:1 and FAILS this — do not use it for text; if you
  want that exact hue for a large button FILL only, that's allowed since the
  button text sits on the fill, but the link/focus token must stay AA.)
- **Cool-tinted neutrals**: near-black text with a blue undertone (not pure
  black), a faint cool off-white page, white cards, a sunken surface for wells,
  hairline + strong borders. All text pairs ≥4.5:1 (≥7:1 in dark theme).
- **Status colors**: verified/issuable green, provisional amber, error red —
  each with an fg (≥4.5:1 on white) and a soft bg tint. Keep the existing
  `-fg`/`-bg` naming.
- **Layered elevation**: replace any flat single shadow so cards read as
  gently lifted, modals as clearly floating. Use the existing
  `--shadow-sm/md/modal` names; deepen their values.
- **Dark theme**: an indigo-black canvas (Mercury-like), slightly lifted cards,
  text ≥7:1, borders low-contrast, brand indigo unchanged, shadows become
  low-opacity glows. Remap ONLY the semantic layer (the primitives stay), as
  the existing `[data-theme="dark"]` block already does.

You MAY add genuinely-new tokens for things that don't exist yet (e.g. a
`--r-pill: 999px` if absent, or a `--shadow-xs`), but never a renamed duplicate
of a token that already exists.

## LOGIC FREEZE litmus (run before every edit)
"If I diff the network traffic and the rendered DATA (not styling) before vs
after, is it identical?" If not, STOP — you're out of scope.

## GLOBAL RULES — every phase
1. One phase at a time. Finish (code + all checks green + commit) before
   reading the next phase.
2. Never claim a check passed without running it and seeing the output.
3. All commands from
   `cd "c:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv/portal"`.
   Gate after EVERY phase, in order:
   ```bash
   npm test           # vitest run — ALL green
   npm run typecheck  # tsc --noEmit — 0 errors
   npm run build      # must succeed
   ```
4. One phase = one commit, exact message given. Stage ONLY `portal/` files.
   Do NOT push.
5. No new runtime deps. CSS-only motion (transitions + `@keyframes`) so the
   existing `prefers-reduced-motion` global override keeps working. Every
   duration/easing MUST reference `--dur-*` / `--ease-*` tokens.
6. Preserve every `data-testid` and exported symbol. A test green today stays
   green; update a selector/assertion ONLY when this phase changes the thing it
   asserts, and never delete a coverage assertion — rewrite it.
7. Each phase lists tests to ADD/UPDATE. New state (hover/focus/open) needs a
   test asserting the state.
8. **Radix in jsdom:** `vitest.setup.ts` polyfills `PointerEvent`. Open Radix
   triggers with `fireEvent.pointerDown(el,{button:0,ctrlKey:false,pointerId:1})`,
   not plain click. Tabs need `mouseDown`+`click`.
9. **Snapshot:** `AppShell.test.tsx` has a markup snapshot. If a phase changes
   AppShell markup, delete
   `src/components/AppShell/__tests__/__snapshots__/AppShell.test.tsx.snap`,
   regenerate, and eyeball the diff before trusting it.

---

<!-- PHASE 1 -->
# PHASE 1 — token retune: color, elevation, type, container (global lift)

**Files:** `portal/src/styles.css` ONLY.

Retune the VALUES of existing tokens toward the mockups' calm, cool,
high-trust feel, keeping every token NAME the components already use. Do all
of this in `:root` and the `[data-theme="dark"]` block:

1. **Neutrals**: near-black text with blue undertone (not `#000`), a faint
   cool page off-white, white cards, add a sunken-surface token if missing for
   wells/inputs, hairline + strong borders. Every text pair ≥4.5:1 (verify).
2. **Brand indigo** (`--indigo-600`): retune to a confident Stripe/Mercury-era
   indigo that STILL passes ≥4.5:1 on white (it's used for links/focus/text).
   You may define a separate large-fill hue for primary-button backgrounds if
   you want the punchier Stripe `#635BFF` look, but the button LABEL on it must
   pass AA and the link/focus token must remain AA on white.
3. **Status**: verified-green / provisional-amber / error-red, each fg ≥4.5:1
   on white + a soft bg. Keep `-fg`/`-bg` names.
4. **Elevation**: deepen `--shadow-sm/md/modal` into layered multi-shadows so
   cards read lifted and modals clearly float. Cards in light theme may get a
   subtle top inset highlight.
5. **Type scale**: ensure display/h1/h2/h3/body/label/caption/mono steps exist
   in the `--fs-*` / `--fw-*` vocabulary with the mockups' calibrated weights
   (section/card titles should have real weight — 600). ALL numeric contexts
   keep `font-variant-numeric: tabular-nums`. Do not introduce parallel
   `--type-*` names; express the scale through the existing `--fs-*`/`--fw-*`.
6. **Container**: add `--content-max` usage — ensure `.wrap` is centered with a
   max width and side padding so nothing floats in empty gutters. (Confirm the
   token exists; if `--content-max` is defined but unused, wire it into
   `.wrap`.)
7. **Dark theme**: indigo-black canvas, lifted cards, AA-plus text, glow-style
   shadows — remap the semantic layer only.

**CHECKS:** three gate commands. Because this is values-only, all existing
tests MUST pass unchanged — if any fail, a token the tests assert on changed
shape, not just value; investigate before proceeding.

**Commit:** `refactor(portal): retune color, elevation, type + container tokens toward fintech-trust palette`

---

<!-- PHASE 2 -->
# PHASE 2 — Batch Detail hero: the "Verified & Sealed" receipt moment

Match mockup #1's layout. Read `pages/BatchDetail.tsx`,
`components/SealedVerdict/*`, `components/MetricBlock/*`,
`components/VerificationChain/*` first. Behavior/hooks/`issue()` flow UNCHANGED
— markup + CSS reshape only.

**Layout to hit (top to bottom):**
1. **Stepper** (VerificationChain) stays across the top: Received → Evidence →
   Compliance → Issued, states derived from real data as they are now. Polish
   the node treatment per the "stepper" spec below.
2. **Two-column hero row:**
   - **Left = the verdict card.** A prominent card with a colored LEFT ACCENT
     bar (emerald when `issuable`/issued, amber when provisional). Inside: a
     **seal badge** (the SealedVerdict stamp — its own signature shape), the
     verdict word large, and:
     - **Issued/verified state:** show what's REAL — the verdict, and (only if
       the batch status is issued) the seal treatment. The mockup's "Reviewed
       by A. Okafor / timestamp / SHA-256" is FABRICATED — do NOT add a
       reviewer name or a batch-level hash. If you want a "sealed" detail line,
       use only real data (e.g. `received_at`, or the issued status itself).
       Do not print a fake hash well on this card.
     - **Provisional state:** the verdict, then the blocker list — render
       `compliance.reasons[]` as rows (each a real reason string), and/or a
       "N blockers" line that is NOT a dead end (see Phase 4 — these can link
       to the failing checklist rows by scrolling to them). "N blockers" must
       always point to the next action.
   - **Right = the metric card.** The hero credit number (`net_credit_t_co2e`
     via `fmtCredit`) in the display size, `tCO₂e` unit + a caption, then a
     definition list of REAL key-values only: Wet yield (`wet_yield_kg` kg),
     Project (`project_id ?? "—"`), Received (`received_at` date). The mockup's
     green "View issued credit" button maps to the EXISTING export/issue
     actions — reuse the real Issue button (admin+issuable) and the real Export
     buttons; do not add a new fake CTA. If issued, the existing seal/exports
     already convey this.
3. **Below: a row of real cards.** The mockup shows Production / LCA summary /
   Provenance. Keep this 3-card rhythm but fill each ONLY with real fields:
   - **Production**: Wet yield (`wet_yield_kg`). (Crop/harvest/farmer/region are
     fabricated — omit.) If this leaves one row, that's fine — one honest row
     in a clean card.
   - **LCA summary**: keep the existing `LcaBreakdown` real content (wet yield +
     net credit + its honest "factors not exposed" note). Do NOT add Scope
     1/2/3/Baseline — fabricated.
   - **Provenance**: keep the existing `ProvenanceTile` real content
     (batch id + copy, device, project, received; methodology "—"). Do NOT add
     lot/transport/documentation — fabricated.

**Signature detail (do this well — it's the whole point):** the credit number
and the verdict seal are the two elements that must feel engineered. The
number: display weight, tabular, tight tracking, a subtle settle-in transition
on value change (CSS `@keyframes` fade+2px translate, `--dur-panel`
`--ease-out`, keyed by value; NO digit count-up). The seal: a real stamp
silhouette (e.g. a scalloped/notched shape via `clip-path` or an inline SVG
seal — no image asset, no new dep) with a one-time impress transition
(fade+scale-down-to-1, `--ease-out`, not a bounce).

**Tests:** extend `BatchDetail.test.tsx` — verdict renders large in the hero;
credit value renders; real key-values (wet yield, project, received) present;
existing issue-modal + admin-gating + chain-node tests pass unchanged. Assert
that NO fabricated label appears — e.g. `queryByText(/Reviewed by/)` is null,
`queryByText(/Farmer ID/i)` is null.

**CHECKS:** three gate commands.

**Commit:** `feat(portal): verified-and-sealed batch-detail hero — verdict card + metric card, real data only`

---

<!-- PHASE 3 -->
# PHASE 3 — evidence gallery: real thumbnails + designed fallbacks

Match mockup #3. Read `components/EvidenceGallery/*` and
`components/EvidenceLightbox/*` first.

1. **Chapter headers**: numbered "1. {STEP_TITLE} · {N} items" with a count
   badge (already close — polish to the mockup's weight/spacing).
2. **Thumbnails**: real photo via the existing authed blob fetch; fade in on
   load (`onLoad` + opacity transition, `--dur-trans`), skeleton (thumbnail
   variant) while loading.
3. **Designed fallback — the key fix**: on a failed/absent image, NEVER show
   the browser broken-image glyph. Render a designed placeholder: a
   document/file icon (lucide, `--text-tertiary`) + the words "Preview
   unavailable" in a `--surface-sunken` well with the SAME border-radius as the
   thumbnail, so loading→failed reads as one continuous surface. The metadata
   below stays fully visible (a dead image never breaks the chain of custody).
4. **Metadata block, unified hierarchy** (fixes an audit finding): hash,
   timestamp, and GPS render as three EQUALLY-weighted label+value rows —
   mono middle-ellipsis SHA-256 + CopyButton, timestamp, and GPS coords in
   NEUTRAL mono (NOT link-blue; if GPS links to a map, the value is a link but
   its label treatment matches hash/timestamp — don't let link-color imply
   GPS is more important than the hash).
5. **Verified chip**: `capture_type_verified` → green "✓ Verified" (icon +
   text). Unverified-but-classified → amber "Unverified". Unclassified →
   render nothing (no empty gap).
6. **Grid**: auto-fill `minmax(200px, 1fr)`, `--space-4` gap, inside the
   content container so tiles never float in empty gutters.

**Tests:** extend `EvidenceGallery.test.tsx` — image `onLoad` swaps to the
loaded class; a failed fetch shows "Preview unavailable" (not a broken img);
hash/timestamp/GPS all render; verified chip logic for all three states.

**CHECKS:** three gate commands.

**Commit:** `feat(portal): evidence gallery — fade-in thumbnails, designed fallbacks, unified forensic metadata`

---

<!-- PHASE 4 -->
# PHASE 4 — compliance checklist: MISSING screams, human text primary

Match mockup #2. Read `components/ComplianceChecklist/*` first. Grouping comes
from `compliance.ts` (READ-ONLY — use its exports, never reimplement).

1. **Header**: section/group title + a "{ok} passed · {missing} missing" pill.
2. **Row hierarchy (the core change)**: the human `label` is PRIMARY
   (`--type-body-strong` weight), the `code` is secondary (mono,
   `--text-tertiary`, smaller) beneath it. Today the code is too loud — demote
   it.
3. **Failing rows are unmissable**: red circle-x icon + human label + red-tinted
   row background + red LEFT accent + a "⚠ Missing" badge on the right. OK rows
   are calm: green check + "⊘ OK" badge, no tint.
4. **`enforced` is quiet metadata**: one subtle chip inline, not repeated
   loudly on every row.
5. **Right-hand summary panel** (mockup shows it): a compact "Compliance
   Summary" card with per-group `ok/total` counts (from `groupChecklist`) and a
   "View full report" affordance ONLY if a real target exists — if there is no
   report route, omit the link rather than adding a dead one. On narrow
   viewports it stacks below.
6. **Blocker linkage**: failing rows are the target that Phase 2's verdict-card
   "N blockers" points to (e.g. anchor id per group/row + smooth scroll). Keep
   it real — no fake deep-links.

**Tests:** extend the checklist test — failing item shows the Missing badge +
`data-status`/tinted treatment; OK items show OK; group counts correct; the
human label is present and the code is present but secondary. Use the REAL
`compliance.ts` module (no mock), as the existing test does.

**CHECKS:** three gate commands.

**Commit:** `feat(portal): compliance checklist — human-first rows, screaming MISSING state, summary panel`

---

<!-- PHASE 5 -->
# PHASE 5 — chrome, controls, motion, dark-mode QA (the finishing pass)

**Files:** AppShell (Sidebar/Topbar), `DataTable`, `StatTile`, buttons/chips
in `styles.css`, native inputs in `styles.css`, and a dark-mode sweep.

1. **Sidebar**: dark canvas, indigo LEFT-accent on the active item (mockups
   show this), logo lockup, quiet footer. Reconcile the two `.mark`
   definitions into one shape/size.
2. **Topbar**: keep the existing hamburger/drawer + theme toggle + account
   menu. If a global search is desired, `cmdk` is already installed — you MAY
   wire a ⌘K command palette, but ONLY if you can make it real (navigating to
   existing routes / batches); a fake non-functional search box is worse than
   none, so if you can't wire it for real, leave the topbar as is. An env chip
   (sandbox) already exists via EnvBanner — keep it.
3. **Native control chrome (audit's #1 tell)**: style `input[type="number"]`
   (hide spin buttons) and `input[type="date"]` (`color-scheme` per theme +
   recolor the calendar indicator) so no OS-default chrome leaks, especially in
   dark mode.
4. **Buttons/chips**: primary (indigo fill, hover darken + 1px lift),
   secondary (white + border), ghost; disabled = opacity + helper text, never a
   dead end. Status chips always icon + text + color. Give the primary "Issue
   credit" trigger a weight appropriate to an irreversible action (the
   ConfirmModal already carries the type-to-confirm gate — don't weaken it).
5. **DataTable**: sticky header, hover row tint + subtle lift, `--shadow-sm`
   container, designed skeleton + empty states, keyboard focus accent (not just
   the outline ring). Preserve the existing roving-tabindex a11y.
6. **StatTile / cards**: give the stat band a hover lift so the summary numbers
   feel live; ensure the credit stat is visually weightier than a raw count.
7. **Motion budget**: row hover 120–150ms bg + 1px lift; card/modal enter
   fade + 4px translate ~180ms; verdict seal fade+scale on confirm; animated
   focus rings — ALL via `--dur-*`/`--ease-*` tokens, ALL under the existing
   reduced-motion guard.
8. **Micro-consistency sweep**: dedupe the double brand mark on Login; kill any
   off-token font-weight (e.g. `650`); unify page `<h1>`s into one
   `.page-title` class; normalize Registry label casing to match LabEntry;
   give the ConfirmModal confirm-input `font-family: var(--font-mono)` to match
   the token it's diffed against.
9. **Dark-mode QA**: page through every route in dark theme; fix any hardcoded
   white/contrast bug; re-run axe in dark.

**Tests:** update AppShell/DataTable/Registry/Login/ConfirmModal tests for any
markup/label change; regenerate the AppShell snapshot if markup changed (Global
Rule 9). Add: native number input has no spinner styling leak (assert the CSS
class/attr you added); DataTable focus accent state.

**CHECKS:** three gate commands + a MANUAL dark-mode date-picker check (open
`npm run dev`, Registry, dark theme, open a date field — report what you saw;
this can't be asserted in jsdom).

**Commit:** `feat(portal): chrome, native-control styling, systemic motion + dark-mode QA`

---

# ACCEPTANCE CRITERIA (verify at the end, paste evidence)
- `axe` 0 violations in BOTH light and dark (the a11y test suite passes).
- No hardcoded visual values in components (grep `#[0-9a-fA-F]{3,6}` and bare
  `px` font-sizes in `src/**/*.tsx` + `*.module.css` → none outside
  styles.css).
- No broken-image glyph anywhere; every failed thumbnail is a designed
  fallback.
- Every id/hash/UUID renders in mono with the same CopyButton pattern.
- MISSING vs OK compliance rows are unmistakable without relying on color
  alone.
- Nothing floats in empty gutters — all content within `--content-max`.
- All numbers tabular.
- `npm test` + `npm run typecheck` + `npm run build` all pass.
- **No fabricated data** — grep the diff for any of the forbidden labels
  (Reviewed by / Farmer ID / Scope 1 / Lot number / Crop type / Harvest date /
  Region / Transport) → none present.
- Both themes fully styled.

# FINAL WRAP-UP
1. Run all three gate commands once more — paste the tails.
2. `git log --oneline -6` — 5 phase commits on top of the baseline.
3. Per phase: files touched, checks + counts, and the Phase 5 manual
   dark-mode observation.
4. Do NOT push.

# THE TEST EVERY PHASE MUST PASS BEFORE "DONE"
View it with the sound off and the copy blurred. If it doesn't feel more
confident, more precise, more inevitable than before — you added decoration,
not trust. And if any card is padded with data the API doesn't return, you
faked trust, which is worse than a plainer honest card. Fix the real visual
mechanism, on real data.

## OUT OF SCOPE (do not attempt)
- Any file outside `portal/`; backend, Flutter app, API shapes.
- New runtime/animation deps (framer-motion, gsap, lottie). CSS-only motion.
- Fabricating any field the API doesn't return (see "THE ONE RULE").
- A parallel token naming system (`--brand-indigo` alongside `--indigo-600`).
- Renaming exports, `data-testid`s, `groupMedia`/`STEP_ORDER`/`STEP_TITLES`,
  or editing `compliance.ts`/`qr.ts`/`lab.ts`/`auth.ts`/`api.ts`.
- Reassurance copy / trust badges / security-theater iconography.
- A non-functional search box (wire cmdk for real or omit it).
