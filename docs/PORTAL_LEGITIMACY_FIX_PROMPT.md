# PORTAL LEGITIMACY FIX PROMPT — phase-wise design-maturity remediation (portal ONLY)

> Repo root: `c:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`.
> Node + npm installed. Execute phases IN ORDER, ONE AT A TIME, and STOP when a
> CHECK fails. FRONTEND-ONLY: every file you touch lives under `portal/`. Do
> NOT modify `backend/`, `lib/`, or anything else. Trust the SOURCE CODE, not
> this doc's line numbers (they drift) — locate the verbatim code before every
> edit. If a verbatim block cannot be found, STOP and report; do not guess.

This addresses a second independent UI/UX audit of the shipped portal (baseline
commit `053f804`). The correctness/a11y problems are already fixed; what
remains is a **design-maturity gap**: two design systems fighting in one repo,
a gutted flagship hero, and trust data the API ships but the UI throws away.

---

## LOGIC FREEZE — unchanged, non-negotiable

This is PRESENTATION + INERT-DATA-DISPLAY work. Behavior, data flow, and
security posture must be byte-for-byte equivalent after every phase.

- **Never change an API call's** endpoint, method, headers, or payload.
  `api.ts` functions and types are READ-ONLY except the ONE additive,
  already-existing `getSummary()` which you may now START CALLING (it already
  exists and is currently dead — calling it is not a new endpoint).
- **Never change** `auth.ts`, `compliance.ts`, `qr.ts`, `lab.ts`,
  `RequireAuth`, route paths, or the `AuthError → nav("/login")` bounce.
- **Never fabricate data.** If the API doesn't return a field, do NOT invent a
  UI for it. Specifically: there is **NO signature/Ed25519 field** in any API
  type — you may surface `capture_type_verified` (which exists) but you must
  NOT add an "Ed25519" / "Signature valid" badge, because the data to back it
  does not exist. Inventing a trust claim is worse than omitting one.
- **`getSummary()` returns exactly** `{ by_status: Record<string,number>,
  provisional: number, reasons_histogram: Record<string,number> }` — there is
  **NO total-tCO₂e field**. Any credit total shown in the summary band must be
  computed client-side by summing the loaded rows, and MUST be labeled as
  "loaded" scope, never presented as a global total.
- Litmus test before every edit: "if I diff network traffic and submitted
  payloads before vs after, is it identical?" `getSummary()` adds ONE new GET
  to `/api/v1/portal/summary` on the Batches screen — that is the ONLY new
  network call permitted in this entire document, and it is a read.

## GLOBAL RULES — apply to every phase

1. **One phase at a time.** Finish phase N (code + all checks green + commit)
   before reading phase N+1.
2. **Never claim a check passed without running it and seeing the output.**
3. All commands run from
   `cd "c:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv/portal"`.
   Gate after EVERY phase, all three, in this order:
   ```bash
   npm test              # vitest run — ALL tests green
   npm run typecheck     # tsc --noEmit — zero errors
   npm run build         # must succeed
   ```
4. One phase = one commit, exact message given. Stage ONLY files under
   `portal/`. Do NOT push — the human reviews and pushes.
5. **No new runtime dependencies.** Everything here is doable with installed
   deps (React, react-router, Radix dialog/tabs/accordion/dropdown/tooltip,
   lucide-react, clsx). `@radix-ui/react-tooltip` IS already installed — use it
   for Phase 5 tooltips; do not add anything.
6. Preserve every existing `data-testid` and exported symbol. Every test green
   today must stay green; only update a selector/assertion when THIS doc's
   phase explicitly changes the thing it asserts, and never delete a coverage
   assertion — rewrite it against the new markup.
7. Each phase lists tests to ADD/UPDATE. New behavior needs a test.
8. **Snapshot note:** `AppShell.test.tsx` has a markup snapshot. If a phase
   changes AppShell markup, delete
   `src/components/AppShell/__tests__/__snapshots__/AppShell.test.tsx.snap`
   and let it regenerate on the next `npm test`. No phase here should touch
   AppShell markup, so this should not be needed — if the snapshot fails
   unexpectedly, STOP and report rather than blindly regenerating.
9. **Radix pointer note (already handled):** `vitest.setup.ts` polyfills
   `PointerEvent`. To open a Radix Tooltip/DropdownMenu in a test, use
   `fireEvent.pointerDown(el, { button: 0, ctrlKey: false, pointerId: 1 })`,
   NOT plain `click`. Tabs activate on `mouseDown`+`click`.

---

<!-- PHASE 1 -->
# PHASE 1 — one design system: spacing + radius + border tokens

**Why first:** everything downstream (hero rebuild, summary band) should be
built on ONE token vocabulary, so unify it before adding new UI.

**Files:** `portal/src/styles.css` ONLY.

## 1a — add a spacing scale (there is none today)

In `:root`, in the `/* layout */` area, add an 8-pt spacing ramp:
```css
  /* spacing (8-pt grid) */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;
  --space-8: 64px;
```

## 1b — collapse the DUPLICATE radius scale

Two identical-valued radius scales exist: `--radius-sm/md/lg` (4/6/8) and
`--r-xs/sm/md/lg/xl` (2/4/6/8/12). `styles.css` uses `--radius-*`; every
`*.module.css` uses `--r-*`. Keep `--r-*` (it is the superset) and retire
`--radius-*`:
1. In `styles.css`, replace every `var(--radius-sm)` → `var(--r-sm)`,
   `var(--radius-md)` → `var(--r-md)`, `var(--radius-lg)` → `var(--r-lg)`.
   (Also any bare `9px`/`10px`/`14px`/`20px`/`999px` radius literals still in
   `styles.css` — snap to the nearest token: 9→`--r-md`, 10→`--r-lg`,
   14→`--r-lg`, 20→`--r-xl`, 999px pills stay `999px` — pills are intentional.)
2. Delete the `--radius-sm/md/lg` declarations from `:root`.
3. Verify: `grep -rn "var(--radius-" src/` returns ZERO. If any remain
   (e.g. inline `style={{}}` in a `.tsx`), migrate those too.

## 1c — replace inline hairline borders with the token

`styles.css` writes `1px solid var(--border-subtle)` inline ~8×. The
`--border-hair` token already equals exactly that. Replace each
`border: 1px solid var(--border-subtle)` → `border: var(--border-hair)` and
`border-bottom: 1px solid var(--border-subtle)` →
`border-bottom: var(--border-hair)`. (Leave `border-color`-only or
`--border-strong` rules alone.)

## 1d — snap the worst off-grid spacing magic numbers

In `styles.css` ONLY, replace these specific off-8pt-grid values with tokens
(do NOT hunt every file — just styles.css, and only spacing, not font-size,
which is Phase 2):
- `13px` gaps/padding → `var(--space-3)` (12px)
- `14px` padding/margin → `var(--space-4)` (16px) EXCEPT table cell
  `padding: 12px 14px` → `padding: var(--space-3) var(--space-4)`
- `18px` (`.card` padding) → `var(--space-5)` (24px) — cards get roomier and
  consistent
- `22px` (`.tiles` margin-bottom) → `var(--space-5)` (24px)
- `30px` (`.hero` padding, `.wrap` top padding) → `var(--space-6)` (32px)
- leave 8/12/16/24/60px as-is (60px is `.wrap` bottom, fine) OR tokenize to the
  matching `--space-*` if trivial.

Do NOT change any value that would alter a layout's fundamental structure
(grid-template, max-width) — spacing only.

**CHECKS:** the three gate commands, plus:
- `grep -rn "var(--radius-" src/` returns 0
- `grep -c "1px solid var(--border-subtle)" src/styles.css` returns 0

**Commit:** `refactor(portal): unify radius scale, add spacing tokens, tokenize borders`

---

<!-- PHASE 2 -->
# PHASE 2 — one type system: purge hardcoded sizes + off-ramp weights

**Why:** the `--fs-*`/`--fw-*` scale exists but `styles.css` ignores it —
26 hardcoded px sizes and 8 non-token weights (550/650/750/800). Half-pixel
sizes (13.5px, 10.5px) and odd weights are the clearest amateur fingerprint.

**Files:** `portal/src/styles.css` ONLY.

## 2a — map every hardcoded font-size to the nearest `--fs-*`

The scale is `--fs-12/13/14/16/18/20/24/32/48/64`. In `styles.css`, replace:
- `font-size: 12px` → `var(--fs-12)`
- `font-size: 13px` → `var(--fs-13)`
- `font-size: 13.5px` → `var(--fs-13)`  (half-pixel dies)
- `font-size: 14px` → `var(--fs-14)`
- `font-size: 15.5px` → `var(--fs-16)`
- `font-size: 18px` → `var(--fs-18)`
- `font-size: 20px` → `var(--fs-20)`
- `font-size: 22px` → `var(--fs-24)`
- `font-size: 30px` → `var(--fs-32)`
- `font-size: 48px` → `var(--fs-48)`
- `font-size: 10.5px` → `var(--fs-12)`  (there is no fs-10/11; 12 is the floor.
  These are thumbnail captions / ring sublabels — 12px is fine and legible.)
- `font-size: 11px` → `var(--fs-12)`  (same reasoning)

After this, `grep -n "font-size:.*px" src/styles.css` should return ONLY the
`code, .mono { font-size: 12px }` rule if it still hardcodes — migrate that to
`var(--fs-12)` too, so the grep returns 0.

## 2b — map every off-ramp font-weight to `--fw-*`

Scale: `--fw-regular/medium/semibold/bold` = 400/500/600/700. Replace in
`styles.css`:
- `font-weight: 550` → `var(--fw-medium)` (500)
- `font-weight: 650` → `var(--fw-semibold)` (600)
- `font-weight: 750` → `var(--fw-bold)` (700)
- `font-weight: 800` → `var(--fw-bold)` (700)
- any literal `400/500/600/700` → the matching `var(--fw-*)` for consistency.

Verify: `grep -nE "font-weight:\s*(550|650|750|800|900)" src/styles.css`
returns 0.

**CHECKS:** the three gate commands, plus:
- `grep -c "font-size:.*[0-9]px" src/styles.css` returns 0
- `grep -cE "font-weight:\s*[0-9]" src/styles.css` returns 0 (all weights are
  now `var(--fw-*)`)

**Visual safety:** these are near-identical remaps (13.5→13, 750→700) so the
screen should look ~identical, just consistent. If anything looks materially
broken in `npm run build` output sizes, you mis-edited — re-check.

**Commit:** `refactor(portal): route all typography through fs/fw tokens`

---

<!-- PHASE 3 -->
# PHASE 3 — delete dead CSS orphaned by earlier redesign

**Why:** AppShell now owns the chrome and CreditRing/badge/verdict were
removed, but their CSS lingers in `styles.css`, feeding the "two systems"
drift. Remove ONLY rules with ZERO remaining references.

**Files:** `portal/src/styles.css` ONLY.

For EACH selector below, FIRST prove it's dead, THEN delete its full rule
block:
```bash
# run for each class; must return NOTHING in src/ outside styles.css itself
grep -rn 'className="[^"]*\bXXX\b' src/pages src/components
```
Candidates the audit flagged as orphaned (verify each before deleting):
- `.top`, `.top-in`, `.top .spacer`, `.brand`, `.brand span` — the old
  TopBar chrome; AppShell replaced it. (Confirm no `className="top"` /
  `"brand"` remain.)
- `.credit`, `.credit .num`, `.credit .unit` — old hero credit layout
  (BatchDetail now uses `<MetricBlock>`). CONFIRM `className="credit"` is gone.
- `.ring`, `.ring svg`, `.ring .track`, `.ring .fill`, `.ring .center`,
  `.ring .center b`, `.ring .center small` — CreditRing was removed from the
  hero. **BUT** `CreditRing.tsx` the component file still exists and uses
  `.ring`. Check: `grep -rn 'className="ring"' src/` — if CreditRing.tsx is the
  ONLY hit and it's not imported anywhere (`grep -rn "CreditRing" src/` shows
  only its own file), delete BOTH the `.ring*` CSS AND `CreditRing.tsx`
  (nothing renders it). If it IS still imported, leave both alone and note it.

Do NOT delete `.credit-label` — it's still used on BatchDetail. Do NOT delete
`.seal` — still used. Do NOT delete `.tile`/`.tiles` — still used.

**CHECKS:** the three gate commands. Also confirm each deleted class has zero
`className` references: `grep -rn 'className="[^"]*\b(top|brand|credit|ring)\b'
src/pages src/components` returns nothing meaningful (matches like
`credit-label`, `credit` inside a word are fine to inspect manually).

**Commit:** `refactor(portal): delete css orphaned by shell + hero redesign`

---

<!-- PHASE 4 -->
# PHASE 4 — rebuild the BatchDetail hero (the flagship, verdict-led)

**Why (highest single leverage):** after CreditRing's removal the hero is a
lonely left-aligned text column in a wide box; the right half is dead
whitespace and the verdict (a verifier's first question) is smaller than the
credit number. Rebuild as a balanced, verdict-led "verification certificate."

**Files:** `portal/src/pages/BatchDetail.tsx`, `portal/src/styles.css`,
`portal/src/components/SealedVerdict/SealedVerdict.tsx` (+ its module.css) IF
you add a size variant, extend `portal/src/pages/__tests__/BatchDetail.test.tsx`.

**DO NOT CHANGE ANY LOGIC.** All hooks, `reload`/`issue`/`exportAs`, the
`ConfirmModal`, `getRole()` gating, `issued` branch, export-row gating, and the
`chainNodes` array stay exactly as they are. This is a MARKUP + CSS reshape of
the returned JSX only.

## 4a — make the hero a real 2-column grid

The hero today is `<div className="hero"><div> …left stack… </div></div>`.
Restructure to two columns:
- **Left column** (primary): the SealedVerdict (promoted — see 4b) as the
  headline, then the batch-id/device metadata line (`.credit-label`), then the
  Issue button / seal, then the export row. Same elements, same order, same
  handlers — just the left cell.
- **Right column** (figure): a bordered inner panel containing the
  `<MetricBlock>` credit figure with its `net credit` caption, plus a compact
  vertical list of the key facts already available: Wet yield
  (`d.batch.wet_yield_kg` kg), Project (`d.batch.project_id ?? "—"`), Received
  (`d.batch.received_at?.slice(0,10) ?? "—"`). This fills the dead space with
  real, already-fetched data (no new API call) and balances the box.

CSS: give `.hero` `display: grid; grid-template-columns: 1.2fr 1fr; gap:
var(--space-6); align-items: start;` and below `900px` collapse to one column
(`@media (max-width: 900px) { .hero { grid-template-columns: 1fr; } }`). Add a
`.hero-figure` class for the right panel: `border: var(--border-hair);
border-radius: var(--r-lg); padding: var(--space-5); background:
var(--surface-page);`. Use ONLY tokens (no raw px).

## 4b — make the verdict the largest thing (fix inverted hierarchy)

The verdict answers "can I issue?" — it should dominate, not the tonnage.
- Give `SealedVerdict` an optional `size?: "md" | "lg"` prop (default `"md"`
  to keep existing usages unchanged). When `"lg"`, the stamp text is
  `var(--fs-24)` and padding is larger. Add a `.stamp[data-size="lg"]` rule in
  its module.css. Keep the existing default path byte-identical so no other
  caller changes.
- In the hero, render `<SealedVerdict size="lg" verdict={…} reasonCount={…} />`.
- Keep `MetricBlock` at its current `size="lg"` (48px) BUT it now lives in the
  right figure panel, visually secondary to the verdict headline on the left.

## 4c — remove the leftover dead whitespace cause

Confirm the hero no longer has an empty implicit second gried cell. The old
`grid-template-columns: 1fr auto` that fed the ring was already changed to a
single column in a prior phase — you are now REPLACING that with the real
2-col layout above. There should be no stray empty `<div>`.

**Tests (extend BatchDetail.test.tsx):**
- verdict renders and is the large variant: assert the ISSUABLE/PROVISIONAL
  text is present AND its element has `data-size="lg"` (add that attribute in
  SealedVerdict when size==="lg", e.g. it already sets `data-verdict`; also set
  `data-size`).
- the right figure shows wet yield: assert `100 kg` (from the fixture's
  `wet_yield_kg: 100`) is present.
- the credit MetricBlock still shows `fmtCredit` value (`1.234`) — unchanged.
- existing tests (issue modal flow, admin gating, chain nodes) STILL PASS
  unchanged.

**CHECKS:** the three gate commands.

**Commit:** `feat(portal): verdict-led two-column batch-detail hero`

---

<!-- PHASE 5 -->
# PHASE 5 — Batches summary band (surface the dead getSummary endpoint)

**Why:** `getSummary()` exists in `api.ts` and is called NOWHERE. A
carbon-ops list with no "N issuable · N provisional · N blocking" header is the
top "unfinished" tell. This is the highest-leverage content fix.

**Files:** `portal/src/pages/Batches.tsx`, a new
`portal/src/components/StatTile/StatTile.tsx` (+ `.module.css` + test),
`portal/src/styles.css` (only if a shared row class is cleaner),
extend `portal/src/pages/__tests__/Batches.test.tsx`.

## 5a — StatTile component

A small presentational tile: `{ label: string; value: string; hint?: string }`.
Renders label (micro), value (tabular, `--fs-24`, `--fw-semibold`), optional
hint (micro, tertiary). Tokens only. Colocated test: renders label + value.

## 5b — wire getSummary into a stat band on Batches

- Add state `const [summary, setSummary] = useState<Awaited<ReturnType<typeof
  getSummary>> | null>(null)`.
- In a `useEffect(() => { getSummary().then(setSummary).catch(() => {}) }, [])`
  — fire ONCE on mount. On failure (incl. AuthError) fail SILENTLY (do not
  block the page; the table has its own error handling). Do NOT redirect from
  here — the list's existing `load()` already handles AuthError→login.
- Render a `.stat-band` row of StatTiles BETWEEN the `<h1>Batches</h1>` and the
  `<Tabs.Root>`. Derive values from `summary`:
  - **Issued**: `summary.by_status["ISSUED"] ?? 0`
  - **Received / in review**: `summary.by_status["RECEIVED"] ?? 0`
  - **Provisional (blocking)**: `summary.provisional`
  - **Credit on loaded rows**: sum `rows.reduce((a,b)=>a+b.net_credit_t_co2e,0)`
    via `fmtCredit`, with hint `"loaded rows"` — because the endpoint has NO
    global total, this MUST be labeled as loaded-scope, never "total".
- While `summary === null`, render the band with `<Skeleton>` placeholders or
  simply omit it (choose omit-until-loaded for simplicity; do not show zeros
  that then jump).
- CSS `.stat-band { display: grid; grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3); margin-bottom: var(--space-5); }` and below 720px
  `repeat(2, 1fr)`. Tokens only.

## 5c — honest pagination count (small, ride-along)

The footer today says `Showing {displayed.length} rows`. When `cursor` is
non-null (more pages exist), change copy to `Showing {displayed.length} loaded`
so it never implies it's the full set. (Do NOT invent a total — the list
endpoint returns a cursor, not a count.)

**Tests (extend Batches.test.tsx):**
- mock `getSummary` (add to the existing `vi.mock("../../api", …)` factory) to
  resolve `{ by_status: { ISSUED: 3, RECEIVED: 7 }, provisional: 2,
  reasons_histogram: {} }`; assert the band shows "3" (issued) and "2"
  (provisional) after load.
- `getSummary` rejecting does NOT crash the page: mock it to reject, assert the
  table rows still render (`dev-1` present) and no redirect fired.
- StatTile.test.tsx: renders label + value.

**CHECKS:** the three gate commands. Also confirm exactly ONE new call site:
`grep -rn "getSummary" src/pages` shows it called once in Batches.

**Commit:** `feat(portal): batches summary stat-band from getSummary`

---

<!-- PHASE 6 -->
# PHASE 6 — Registry forms: real labels, typed inputs, per-field validation

**Why:** Registry's generic `Form` uses `placeholder`-as-label (vanishes on
type — a11y + UX antipattern), free-text date fields, and a 4-second global
toast instead of field-level feedback. It's the weakest screen.

**Files:** `portal/src/pages/Registry.tsx`, extend
`portal/src/pages/__tests__/Registry.test.tsx`, `portal/src/styles.css` (only
if needed).

**DO NOT CHANGE** any `registryPost(...)` call — same kind, same payload keys,
same values (`crypto.randomUUID()` calls, `num()` coercion, `|| null`
fallbacks). This is a presentation upgrade of the `Form` helper + `Field` type
ONLY.

## 6a — extend the Field type + render real labels

Extend `type Field` to `{ key: string; label: string; type?: string;
required?: boolean }`. In the `Form` render:
- Render a real `<label htmlFor={id}>` above each input (id =
  `` `${key}-${someFormScopeId}` `` to stay unique across the 5 forms — derive
  a scope from the form `title` slug, or use React's `useId()`).
- Keep the human `label` text but Title-Case it for display (the raw keys like
  "kiln id" can stay as the label string; just render them as a proper `<label>`
  not a placeholder). Remove the `placeholder={f.label}` (or keep a lighter
  example placeholder only where useful, e.g. dates).
- Pass `type={f.type ?? "text"}` through to the input so date/number fields
  render natively.

## 6b — mark date/number fields with real input types

In the field definitions (do NOT change the POST payload — `num()`/string
coercion already handles the value), set `type`:
- kiln `weight_kg`, `capacity_l` → `type: "number"`
- supervisor-visit `visited_at`, scale-calibration `calibrated_at` /
  `valid_until`, operator-training `completed_at` → `type: "date"`
- annual-verification `year` → `type: "number"`, `methane_rate_g_per_kg` →
  `type: "number"`
Native date pickers replace free-text "(ISO)" hints. Since the value is still a
string, the existing POST bodies are unchanged.

## 6c — de-jargon the titles (microcopy)

Strip engineer-speak from titles the user sees:
- `"Supervisor visit (idempotent on kiln+date)"` → `"Supervisor visit"`
- `"Operator training (idempotent on operator+date)"` → `"Operator training"`
- `"Annual verification (C9, keyed by project+year)"` →
  `"Annual verification (C9)"`
- `"Scale calibration (C8)"` stays; `"Register kiln (C8)"` stays.
"idempotent"/"keyed by" are implementation details — remove from UI copy.

## 6d — keep the save feedback, but tie required-ness in

The generic `Form` may keep its 4s "✓ Saved" chip (it's fine), but if any
`required` field is empty on submit, block the POST and show the chip as
`"Fill required fields"` instead of firing the request. (Only add this if you
introduced `required` on a field; kiln_id is the natural required one. Keep it
minimal — this is not a full validation framework.)

**Tests (extend Registry.test.tsx):**
- the kiln form now renders a real `<label>` "kiln id" bound to an input
  (assert `getByLabelText("kiln id")` still works — it will, via `<label
  htmlFor>` — scoped with `within(kilnForm)` as the existing test already does).
- a date field renders `type="date"`: assert e.g. the supervisor-visit
  "visit date" input has `type="date"`.
- the exact kiln payload is STILL `{ kiln_id, kiln_type, material, weight_kg }`
  — the existing payload-shape test MUST still pass unchanged.

**CHECKS:** the three gate commands.

**Commit:** `feat(portal): registry forms — real labels, typed inputs, de-jargoned copy`

---

<!-- PHASE 7 -->
# PHASE 7 — jargon tooltips (Radix Tooltip, already installed)

**Why:** "Provisional/Issuable", "H:Corg", "C8/C9" appear with zero
explanation. One reusable InfoTip removes the "internal tool" smell.

**Files:** new `portal/src/components/InfoTip/InfoTip.tsx` (+ `.module.css` +
test), `portal/src/pages/Batches.tsx`, `portal/src/pages/LabEntry.tsx`,
`portal/src/App.tsx` (Tooltip.Provider wrap — see note), extend tests.

## 7a — InfoTip component (Radix Tooltip)

`@radix-ui/react-tooltip` is installed. Build `InfoTip`:
- props `{ label: string; children?: ReactNode }` — renders a small `?` icon
  button (lucide `HelpCircle` or `Info`, `size={12}`, `aria-label={\`Help:
  ${label}\`}`) as the trigger; the tooltip content is the `label` text.
- Radix Tooltip needs a `Tooltip.Provider` ancestor. Add ONE
  `<Tooltip.Provider>` wrapping the app — the cleanest spot is inside
  `AppShell` (wrap its returned tree) OR in `App.tsx` around `<Routes>`. Pick
  AppShell so login (unwrapped) doesn't need it. **This is the only AppShell
  change permitted** — a provider wrapper adds no visible markup; if the
  snapshot test trips, regenerate it per Global Rule 8 and note it.
- module.css: tooltip content styled with `--surface-card`, `--border-hair`,
  `--r-md`, `--shadow-md`, `--fs-12`, padding `--space-2`, `max-width: 240px`.

## 7b — apply InfoTip to the worst jargon (keep it to ~4 placements)

- Batches "Status" column header → InfoTip: "Issuable = all compliance gates
  met and ready to issue. Provisional = one or more gates unmet."
- LabEntry "H:Corg ratio" label → InfoTip: "Molar hydrogen-to-organic-carbon
  ratio; a permanence indicator for biochar (target 0.1–1.5)."
- Registry "Register kiln (C8)" and "Annual verification (C9)" titles → an
  InfoTip after the title: C8 = "Kiln & equipment registration criterion." C9
  = "Annual project verification criterion."
Do NOT tooltip everything — 4 placements is the target; more is noise.

**Tests:**
- InfoTip.test.tsx: renders a trigger with the `aria-label` "Help: …"; opening
  it (pointerDown per Global Rule 9) shows the label text. (If Radix tooltip
  open is flaky in jsdom, at minimum assert the trigger + its `aria-label`
  render — do NOT delete the assertion, downgrade it to trigger-presence and
  note it.)
- a Batches test asserting the Status header InfoTip trigger is present.

**CHECKS:** the three gate commands.

**Commit:** `feat(portal): jargon tooltips via radix tooltip`

---

# FINAL WRAP-UP

1. Run all three gate commands once more — paste the output tails.
2. `git log --oneline -8` — expect 7 commits in phase order on top of
   `053f804`.
3. Per phase, report: files touched, checks run with counts, anything
   consciously deferred (with reason), and any snapshot regeneration.
4. Do NOT push. Human reviews, pushes, Vercel redeploys.

## Explicitly OUT OF SCOPE (do not attempt)
- ANY file outside `portal/`; backend, Flutter app, API shapes.
- New runtime dependencies (Radix tooltip is already installed — nothing else).
- **An Ed25519 / "signature valid" badge** — the data does not exist in any
  API type; inventing it is a fabricated trust claim. Only `capture_type_
  verified` (which exists) may be surfaced, and it already is.
- A global credit total in the summary band — `getSummary()` has no such field;
  only the loaded-rows sum, explicitly labeled "loaded".
- Server-side search, real bulk export, activity log, column sorting rewrite of
  DataTable's data model (a later task if wanted).
- Renaming exported symbols, `data-testid`s, `groupMedia`/`STEP_ORDER`/
  `STEP_TITLES`, or touching `compliance.ts`/`qr.ts`/`lab.ts`/`auth.ts`.
- Dark-mode redesign, 1440px grid, new fonts.

## Bright spots to PRESERVE (do not "improve" these)
- `ConfirmModal` typed-token issuance flow, `EmptyState`, `Skeleton` loading,
  the EvidenceGallery/Lightbox hash+GPS+verified UI. Leave them alone.
