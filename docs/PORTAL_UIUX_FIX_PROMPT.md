# PORTAL UI/UX FIX PROMPT — phased remediation of the audit findings (portal ONLY)

> Repo root: `c:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`.
> Node + npm installed. Execute phases IN ORDER, ONE AT A TIME, and STOP when a
> CHECK fails. FRONTEND-ONLY: every file you touch lives under `portal/`. You
> must NOT modify `backend/`, `lib/`, or any other directory. Trust the SOURCE
> CODE, not this doc's line numbers (they drift) — locate the verbatim code
> before editing.

These fixes come from an independent three-part UI/UX audit of the shipped
portal (commits through `c53c3d2`). Findings are grouped by phase in
descending leverage: correctness-grade bugs first, then blockers, then the
"looks broken" cleanup, then a11y/polish.

## LOGIC FREEZE — unchanged from the redesign

This is still PRESENTATION + INTERACTION repair, not a data/behavior rewrite.

- **Never change an API call**: same endpoints, methods, headers, payloads,
  response handling. `api.ts` types/functions are READ-ONLY.
- **Never change auth/routing/guards**: `auth.ts`, `RequireAuth`, route paths,
  `AuthError → nav("/login")` stay exactly as they are.
- **Never change data logic**: `compliance.ts`, `qr.ts`, `lab.ts`
  (`validateLabForm`, `parseBatchQr`), `groupMedia`, `STEP_ORDER`,
  `STEP_TITLES`, pagination/cursor logic — untouched. Add lookup maps or
  client-side derivations; never mutate the underlying data or the API shape.
- The ONE sanctioned new behavior is **input validation that only GATES an
  existing navigation/submit** (Phase 1b) — it must reuse `parseBatchQr`/the
  existing validators, add no new endpoint, and change no payload.
- Litmus test before every edit: "if I diff network traffic and submitted
  payloads before vs after, is it identical?" If not, STOP.

## GLOBAL RULES — apply to every phase

1. **One phase at a time.** Finish phase N (code + all checks green + commit)
   before reading phase N+1.
2. **Never claim a check passed without running it and seeing the output.**
3. All commands run from
   `cd "c:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv/portal"`.
   Gate after EVERY phase, all three, in order:
   ```bash
   npm test              # vitest run — ALL tests green
   npm run typecheck     # tsc --noEmit — zero errors
   npm run build         # must succeed
   ```
4. One phase = one commit, exact message given. Stage ONLY files under
   `portal/`. Do NOT push — the human reviews and pushes.
5. No new runtime dependencies. Everything here is achievable with the deps
   already installed (React, react-router, Radix dialog/tabs/accordion/
   dropdown/tooltip, lucide-react, clsx). Dev-only test deps are fine if a
   phase explicitly needs one (none should).
6. Every color/radius/spacing/duration references a token in `styles.css`.
   No hardcoded hex/px/ms in `.tsx` or `.module.css` (grep-enforced).
7. Preserve every existing `data-testid` and exported symbol. Every test
   green today must stay green; update a selector only if a class/label you
   intentionally changed moved — never delete an assertion.
8. Each phase lists tests to ADD. New interactive behavior needs a test.

---

<!-- PHASE 1 -->
# PHASE 1 — correctness bugs wearing UX clothing (HIGHEST LEVERAGE)

**Why first:** two defects change or corrupt what the user sees in a
compliance tool. Fix before anything cosmetic.

**Files:** `portal/src/pages/Batches.tsx`, `portal/src/pages/LabScan.tsx`,
extend `portal/src/pages/__tests__/Batches.test.tsx` and
`portal/src/pages/__tests__/LabScan.test.tsx`.

## 1a — Batches: kill the tab/select contradiction

Today the saved-view tabs derive their active state from the URL `view=`
param, while the FilterBar `status`/`provisional` selects write the same
state WITHOUT updating `view`. Result: the highlighted tab and the selects
can disagree, and a refresh re-reads `view=` and silently changes the data.

Fix — make the selects authoritative and DERIVE the active view from state:

1. Add a pure helper next to `VIEWS`:
   ```ts
   function viewFromFilters(status: string, provisional: string): ViewKey | null {
     const hit = (Object.keys(VIEWS) as ViewKey[]).find(
       (k) => VIEWS[k].status === status && VIEWS[k].provisional === provisional,
     );
     return hit ?? null; // null = "custom" (selects diverge from any saved view)
   }
   ```
2. Replace the URL-derived `view` used for the tab's `active` class and
   `Tabs.Root value` with `viewFromFilters(status, provisional)`. When it
   returns `null`, no tab is `active` and `Tabs.Root` gets a value that
   matches none (e.g. `"custom"`), so the highlight honestly reflects state.
3. Keep the URL in sync FROM state (write `view=` in the `status`/`provisional`
   effect, or drop the query param entirely if you prefer — but the tab
   highlight must never contradict the selects). The `blocking` client-side
   narrowing (`reason_count > 0`) must still key off the resolved view.
4. `switchView` still sets `status`/`provisional` from `VIEWS[v]` — that path
   is fine; only the read/derive side was wrong.

**Test (Batches):** set the Issued tab, then change the status select to
RECEIVED; assert no tab has the `active` class (query `[aria-selected="true"]`
or the `.active` class) and that the rows reflect the select, not the tab.

## 1b — LabScan: validate manual entry before navigating

The camera path guards via `parseBatchQr`; the manual "paste batch UUID" path
navigates to `/lab/<anything>` and records garbage in recent scans.

1. On the manual Open handler, resolve the id through the SAME validation the
   camera uses. `parseBatchQr` accepts the `dmrv-batch:v1:<uuid>` form; a
   pasted bare UUID should also be accepted. Add a small helper:
   ```ts
   function resolveManual(raw: string): string | null {
     const s = raw.trim();
     if (!s) return null;
     const fromQr = parseBatchQr(s);              // handles dmrv-batch:v1:<uuid>
     if (fromQr) return fromQr;
     const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
     return UUID.test(s) ? s : null;
   }
   ```
   Do NOT change `parseBatchQr` itself (it's in `lab.ts`, READ-ONLY).
2. If it returns null: show an inline error (`.err` class, e.g. "Not a valid
   batch code") and do NOT navigate or push to recent. If valid: `pushRecent`
   then `nav`.

**Test (LabScan):** typing a garbage string + Open shows the error, does NOT
navigate, and does NOT write to `tc_recent_scans`; a valid UUID navigates and
records.

**CHECKS:** the three gate commands.

**Commit:** `fix(portal): reconcile batches tab/filter state, validate manual lab entry`

---

<!-- PHASE 2 -->
# PHASE 2 — blockers: mobile shell + escapable menu

**Files:** `portal/src/components/AppShell/AppShell.tsx` (+ module.css),
`portal/src/components/AppShell/Sidebar.tsx`,
`portal/src/components/AppShell/Topbar.tsx`,
extend `portal/src/components/AppShell/__tests__/AppShell.test.tsx`.

## 2a — responsive shell (the app is currently unusable on phones)

1. In `AppShell.module.css` add a `@media (max-width: 768px)` block:
   - `.rail` becomes an overlay drawer: `position: fixed; inset: 0 auto 0 0;
     transform: translateX(-100%); transition: transform var(--dur-trans)
     var(--ease-out); z-index: 50;` and slides in (`translateX(0)`) when open.
   - Add a scrim behind the open drawer (a sibling div, `position: fixed;
     inset: 0; background: rgba(15,17,21,0.4)`) that closes it on click.
   - The main content column takes full width (no rail gutter) on mobile.
2. Add mobile-drawer open state to `AppShell` (`useState`), default closed;
   close on route change and on scrim click and on Escape.
3. In `Topbar`, add a hamburger button (lucide `Menu`, `aria-label="Open
   navigation"`) that is visible ONLY at ≤768px (CSS, `display:none` above)
   and toggles the drawer. Ensure the brand wordmark is visible on mobile.
4. The existing ⌘\ collapse behavior stays for desktop; it must not conflict
   with the mobile drawer state.

## 2b — account menu must be dismissible

In `Topbar.tsx` the account dropdown has no outside-click/Escape handling.
Either:
- **Preferred:** replace the hand-rolled dropdown with the already-installed
  `@radix-ui/react-dropdown-menu` (gives outside-click, Escape, focus
  management, roving focus for free). Keep the same trigger `aria-label` and
  the Sign out item calling the existing `logout()` + `clearSession()` path
  UNCHANGED.
- If you keep the custom menu: add a `useEffect` document `pointerdown`
  listener that closes when the click is outside `avatarWrap`, and a `keydown`
  Escape handler; move focus to the first item on open and back to the trigger
  on close.

Also: disable the Sign out button while `logout()` is in flight (guard against
double-fire), and give the theme toggle a dynamic `aria-label`
("Switch to light theme" / "Switch to dark theme") plus `aria-pressed`.

**Tests (AppShell):** (1) at a mobile width — simulate by asserting the
hamburger is in the DOM and toggling it adds the drawer-open state/attribute;
(2) opening the account menu then firing a document `pointerdown` outside (or
Escape) closes it. (jsdom can't do real media queries — assert on the state/
attribute your JS sets, and keep the CSS `@media` purely presentational.)

**CHECKS:** the three gate commands.

**Commit:** `fix(portal): responsive drawer shell + dismissible account menu`

---

<!-- PHASE 3 -->
# PHASE 3 — kill dead surface (the "looks broken" cleanup)

**Why:** the single biggest hit to the "billion-dollar" impression is
visible-but-inert controls and internal notes leaking to users.

**Files:** `portal/src/components/AppShell/Topbar.tsx`,
`portal/src/components/AppShell/Sidebar.tsx`,
`portal/src/pages/Batches.tsx`, `portal/src/pages/Registry.tsx`,
`portal/src/pages/BatchDetail.tsx`.

1. **⌘K search:** it renders a prominent button whose `onCmdK` is a no-op.
   Remove the search button from `Topbar` entirely (and drop the now-unused
   `onCmdK` prop threading). Do NOT leave a disabled placeholder pretending a
   feature exists.
2. **Batches dead controls:** remove "Export CSV" (disabled), "New batch"
   (disabled), the bulk-select checkboxes column, and the "Export selected"
   bar — none are wired. Keep the table, tabs, filter, and row navigation.
   (If the team wants selection later, it returns with a working action.)
3. **Standards tab (Registry):** delete the `EmptyState` card that renders
   "Coming soon — … No new API exists for this yet." Never ship API-status
   commentary to users. Leave the working annual-verification form; if that
   leaves a lone cell, drop the two-column grid for that tab so it reads as
   intentional, not half-empty.
4. **ActivityTimeline on BatchDetail:** it is mounted with `events={[]}` and
   renders a permanent "will appear once the backend exposes it" card. Remove
   the `<ActivityTimeline events={[]} />` usage from BatchDetail. KEEP the
   component file and its tests (it's ready for when the API exists) — only
   stop mounting the always-empty instance.
5. **Help / Settings:** remove the second "Help" button (keep at most one, and
   only if it has a destination; otherwise remove both), and remove the
   permanently-`disabled` "Settings" sidebar item until it has a route.

**Tests:** update any assertion that referenced a removed control; add a test
that BatchDetail does NOT render the `activity-empty` testid anymore. Do not
delete unrelated assertions.

**CHECKS:** the three gate commands.

**Commit:** `fix(portal): remove non-functional controls and internal placeholder copy`

---

<!-- PHASE 4 -->
# PHASE 4 — honest search + issuance feedback + number precision

**Files:** `portal/src/pages/Batches.tsx`,
`portal/src/components/FilterBar/FilterBar.tsx`,
`portal/src/components/ConfirmModal/ConfirmModal.tsx` (+ module.css),
`portal/src/pages/BatchDetail.tsx`, a new
`portal/src/format.ts` + `portal/src/__tests__/format.test.ts`,
extend `ConfirmModal.test.tsx`.

## 4a — stop the client-side search from lying

Search filters only the loaded ≤50 rows but looks global. Since changing the
API is out of scope:
- Change the FilterBar search placeholder/`aria-label` to make scope explicit,
  e.g. "Filter loaded rows".
- When a search term is active and yields zero visible rows while more pages
  exist (`cursor` is non-null), the empty state must say so — e.g. "No matches
  in the loaded rows. Load more, or refine." (not the global "No batches
  found"). Pass an `isFiltered`/`hasMore` signal into the empty node.

## 4b — issuance confirm: token copy + mismatch feedback

In `ConfirmModal.tsx`:
- Render a `CopyButton` next to the visible confirm token so the user can copy
  it rather than hand-transcribe.
- `trim()` the typed value before the `=== confirmToken` comparison.
- When `text.length > 0 && text !== confirmToken`, render a red helper line
  ("Doesn't match — type it exactly"); when it matches, a subtle confirmation
  cue. Do NOT change the gating logic itself (still admin + issuable +
  `issueCredit(uuid)`, disabled until exact match, no double-submit).

## 4c — one precision for the money figure

Create `portal/src/format.ts`:
```ts
export function fmtCredit(t: number): string {
  return t.toFixed(3);
}
```
Route every carbon-credit render through it: BatchDetail hero, the ConfirmModal
preview row, and the Batches table cell (and anywhere else `toFixed(2|3)` is
applied to `net_credit_t_co2e`). Pick 3 dp everywhere. Do not touch non-credit
numbers (percentages, counts).

**Tests:** `format.test.ts` (fmtCredit(1.2) === "1.200"); ConfirmModal — wrong
token shows the mismatch line and keeps confirm disabled, correct token clears
it and enables; Batches — empty-while-filtered copy differs from empty-global.

**CHECKS:** the three gate commands, plus
`grep -rn "toFixed(2)\|toFixed(3)" src/pages src/components` shows no
`net_credit` renders bypassing `fmtCredit`.

**Commit:** `fix(portal): honest search scope, issuance copy+mismatch feedback, unified credit precision`

---

<!-- PHASE 5 -->
# PHASE 5 — a11y + hierarchy polish

**Files:** `portal/src/components/AppShell/AppShell.tsx`,
`portal/src/components/DataTable/DataTable.tsx` (+ module.css),
`portal/src/components/CopyButton/CopyButton.tsx`,
`portal/src/pages/BatchDetail.tsx`,
`portal/src/pages/LabScan.tsx`, `portal/src/pages/LabEntry.tsx`,
`portal/src/styles.css`.

1. **Skip link focus:** add `tabIndex={-1}` to `<main id="main-content">` so
   the skip link actually moves keyboard focus, not just scroll.
2. **DataTable keyboard model:** implement roving tabindex — the table is ONE
   tab stop; only the focused row is `tabIndex={0}`, the rest `-1`; Arrow
   Up/Down move focus, Home/End jump to first/last, Enter/Space activate
   `onRowClick`. Add `role="row"`/appropriate semantics and set
   `aria-busy={loading}` on the table. Keep the existing tests green (adjust
   the arrow-key test to the roving model).
3. **CopyButton accessibility:** add an `aria-live="polite"` "Copied"
   announcement (visually-hidden text is fine) so success isn't icon-only.
   This covers all reuse sites automatically.
4. **BatchDetail hierarchy:** reduce the "criteria met" redundancy — demote or
   remove the `CreditRing` from the hero (SealedVerdict + VerificationChain +
   the checklist already convey status). If removed, delete only the hero
   usage; keep the component + its test unless nothing references it (then
   remove all of it, tests included, and note it).
5. **Production tile:** stop dumping raw `evidence_counts` under "Production".
   Keep wet yield in Production; move the evidence tally into the Evidence
   section (or drop it — the gallery already shows per-group counts).
6. **LabEntry:** either make the right-column rule list genuinely reactive to
   the form (tick/error per rule as inputs change, reusing `validateLabForm`
   READ-ONLY for the check) OR relabel it so it no longer implies live preview;
   remove the raw SHA-256 hex dump (replace with a plain "✓ certificate
   attached" confirmation) unless it earns its place.
7. **LabScan recent scans:** clear `tc_recent_scans` in `clearSession()`
   callers' flow — since `auth.ts` is READ-ONLY, clear it in the Sign out
   handler in `Topbar` right after `clearSession()` (a cosmetic side-effect,
   not an auth change).
8. **StatusDot contrast:** verify each status text color meets ≥4.5:1 on
   `--surface-card` in BOTH themes; if a pair fails, adjust the token value in
   `styles.css` (not per-component). Show the contrast math in the commit body.

**Tests:** skip-link moves focus to main; DataTable roving tabindex (one tab
stop, arrows move, Home/End); CopyButton exposes an aria-live "Copied".

**CHECKS:** the three gate commands.

**Commit:** `fix(portal): a11y (roving grid, skip-focus, copy announce) + hierarchy cleanup`

---

<!-- PHASE 6 -->
# PHASE 6 — CSS hygiene + Registry consistency

**Files:** `portal/src/styles.css`, `portal/src/pages/Registry.tsx`.

1. **De-duplicate CSS:** `.linkbtn` is defined 3×, `.media-cell`/`.media-grid`/
   `.chip.warn` 2×, `.neutral`/`button.neutral` overlap. Collapse each to a
   single definition (keep the last-winning visual result so nothing changes
   on screen), and delete the dead earlier copies. Also delete the now-unused
   `.modal-overlay`/`.modal-panel` rules if Phase-5 ConfirmModal/Radix fully
   replaced them (grep first — remove only if zero references).
2. **Registry interaction consistency:** pick ONE model. Simplest and lowest
   risk: convert the kiln `KilnStepper` dialog to a single inline `Form` (5
   fields aren't worth 3 steps), matching supervisor-visit/scale-calibration —
   OR keep the stepper and note explicitly why the others stay flat. Submit
   payload for kilns must remain the exact
   `{kiln_id, kiln_type, material, weight_kg}` via `registryPost("kilns", …)`.
   Preserve the capacity→QR client behavior.

**CHECKS:** the three gate commands, plus
`grep -c "^\.linkbtn\|^\.media-cell\|^\.media-grid" src/styles.css` shows one
of each selector block (allow pseudo/nested variants).

**Commit:** `refactor(portal): de-duplicate css, unify registry form interaction`

---

# FINAL WRAP-UP

1. Run all three gate commands once more — paste the output tails.
2. `git log --oneline -7` — expected: 6 fix/refactor commits on top of the
   audit baseline.
3. Per phase, report: files touched, checks run with counts, and any finding
   you consciously deferred (with reason).
4. Do NOT push. The human reviews, pushes, and Vercel redeploys.

## Explicitly OUT OF SCOPE
- Any file outside `portal/`; the backend, Flutter app, or API shapes.
- New runtime dependencies or a component/CSS framework.
- Server-side search, real bulk export, real activity log, LCA factor data,
  methodology values — these need backend work; design around today's data and
  hide (don't fake) what the API doesn't provide.
- Renaming exported symbols, `data-testid`s, `groupMedia`/`STEP_ORDER`/
  `STEP_TITLES`, or touching `compliance.ts`/`qr.ts`/`lab.ts`/`auth.ts`/
  `api.ts` logic.
