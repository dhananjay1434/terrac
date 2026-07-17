# AI Coder Execution Prompt — TerraCipher Portal UI/UX Redesign

## ROLE
You are a senior frontend engineer executing a scoped UI/UX redesign of the `portal/` Vite + React + TypeScript app in the repo `dhananjay1434/terrac`. You will implement changes **phase by phase**. Do not skip ahead. Do not touch anything outside your whitelist. If any instruction is ambiguous, STOP and ask a single clarifying question — do not guess.

---

## HARD GUARDRAILS — READ BEFORE EVERY PHASE

### Do-NOT-touch list (blacklist, absolute)
1. `backend/**` — entire FastAPI backend. Never open, never edit, never assume behavior.
2. `lib/**`, `android/**`, `ios/**`, `pubspec.yaml`, `pubspec.lock` — Flutter app.
3. `portal/src/api.ts` — API client. Do NOT change function signatures, request bodies, endpoints, error classes, or exported types. You may only READ this file.
4. `portal/src/auth.ts` — session, roles, token handling. READ-ONLY.
5. `portal/src/compliance.ts` — business logic for grouping/status. READ-ONLY.
6. `portal/src/qr.ts` — QR scan/gen helpers. READ-ONLY.
7. Any file matching `*.test.ts(x)` for logic (compliance, auth, api) — READ-ONLY.
8. All route paths in `App.tsx`: `/login`, `/batches`, `/batches/:uuid`, `/lab/scan`, `/lab/:uuid`, `/registry`, `*`. You may restructure `App.tsx` internals but every route path and its component target must remain intact.
9. All exported TypeScript interfaces from `api.ts` (`BatchRow`, `BatchDetail`, `Compliance`, `MediaItem`, `ChecklistItem`, `AuthError`, `ApiError`). Do NOT redeclare, extend, or alter them.
10. `package.json` `dependencies` — only ADD, never remove or upgrade major versions without explicit approval.

### Rules of engagement
- **Never invent** an API endpoint, prop, field, or method. If you need data that `api.ts` doesn't expose, STOP and ask.
- **Never delete** an existing component before its replacement is fully wired, tested, and rendering identical or superset data.
- **Preserve every string** currently shown to the user unless the redesign spec explicitly changes it. Copy stays unless spec says otherwise.
- **Preserve every accessibility label** and add more; never regress a11y.
- **Preserve every existing test**. Every test that passes today must pass after your change. If a test breaks because a class name changed, update the selector — never delete the assertion.
- **Do not introduce new dependencies** outside this approved list:
  - `lucide-react` (icons)
  - `clsx` (classnames)
  - `@radix-ui/react-dialog`, `@radix-ui/react-dropdown-menu`, `@radix-ui/react-tabs`, `@radix-ui/react-tooltip`, `@radix-ui/react-accordion` (headless a11y primitives)
  - `cmdk` (command palette)
  - `date-fns` (date formatting only if not already present)
  - No CSS-in-JS libraries. No Tailwind. Extend the existing `styles.css` + add CSS Modules or plain `.css` files colocated with components.
- **Never edit `vite.config.ts`, `tsconfig.json`, `vitest.setup.ts`** unless a phase explicitly says so.

---

## ENVIRONMENT & COMMANDS

Working directory: `portal/`.

Commands you may run:
```bash
npm install          # only when new deps added (allowed list above)
npm run dev          # visual verification
npm run build        # must pass at end of every phase
npm run typecheck    # must pass at end of every phase
npm run test         # must pass at end of every phase
npm run test -- --coverage   # end of Phase 7 only
```

**End-of-phase gate (ALL must be green):**
1. `npm run typecheck` → 0 errors
2. `npm run build` → succeeds
3. `npm run test` → all existing + new tests pass
4. Manual smoke: run `npm run dev`, visit every route, confirm no console errors and no visual regressions on unchanged pages.

If any gate fails, DO NOT proceed to the next phase. Fix, or STOP and report exactly what is failing.

---

## GLOBAL EXECUTION PROTOCOL (repeat for every phase)

For each phase, in this exact order:

**Step 1 — READ**
List every file you will read (whitelist + relevant existing files). Read them. Summarize in ≤5 lines what the current state is.

**Step 2 — PLAN**
Output a numbered task list of concrete changes. Each task must name file paths. Do not write code yet.

**Step 3 — CONFIRM**
If any task requires touching a blacklisted file, a new dependency not on the approved list, or an API field you can't verify exists, STOP here and ask.

**Step 4 — IMPLEMENT**
Execute tasks in order. After each task, run `npm run typecheck`. Commit-worthy checkpoint after each numbered task (use git if available: `git add -A && git commit -m "phase-N task-M: <desc>"`).

**Step 5 — TEST**
Write tests as specified in the phase. Run full suite.

**Step 6 — VERIFY**
Run all end-of-phase gates. Then run through the phase's Acceptance Criteria list and check each one.

**Step 7 — REPORT**
Post a summary: files added, files modified, tests added, screenshots of key views (dev server), any deviation from the spec with reason.

Then STOP and wait for approval before starting the next phase.

---

## REPO CONVENTIONS TO FOLLOW

- File naming: `PascalCase.tsx` for components, `camelCase.ts` for utilities.
- Colocate component CSS: `Button.tsx` + `Button.module.css` OR one file appended to `styles.css` in the corresponding section. **Prefer CSS Modules for all new components in this redesign.**
- Every new component gets: JSDoc block on default export, a `*.test.tsx` file next to it.
- All imports use existing alias style (relative paths — no path aliases exist today; do not add).
- All new components must be typed. No `any`. Use `unknown` + narrowing.
- Every color, radius, spacing, font-size, duration must reference a CSS variable defined in `styles.css`. Never hardcode hex, px, or ms in new code.

---

# PHASE 1 — Design Tokens, App Shell, Dark Mode

## Objective
Replace the current TopBar-only shell with a full AppShell (left rail + topbar + env banner + breadcrumbs). Introduce the new design token system without breaking any existing page.

## Whitelist (files you may create/edit)
- `portal/src/styles.css` — extend token block only. Do not remove existing variables.
- `portal/src/theme.ts` (new) — theme toggle helper.
- `portal/src/components/AppShell/AppShell.tsx` (new)
- `portal/src/components/AppShell/AppShell.module.css` (new)
- `portal/src/components/AppShell/Sidebar.tsx` (new)
- `portal/src/components/AppShell/Topbar.tsx` (new)
- `portal/src/components/AppShell/Breadcrumbs.tsx` (new)
- `portal/src/components/AppShell/EnvBanner.tsx` (new)
- `portal/src/components/AppShell/__tests__/AppShell.test.tsx` (new)
- `portal/src/App.tsx` — replace `<Shell>` internals only. Keep all `<Route>` definitions unchanged. Keep `RequireAuth`.
- `portal/index.html` — update `<title>` and add `<meta name="color-scheme" content="light dark">` if missing. Nothing else.
- `package.json` — add `lucide-react`, `clsx`, `@radix-ui/react-dropdown-menu`, `@radix-ui/react-tooltip`.

## Blacklist reminder
`api.ts`, `auth.ts`, `compliance.ts`, `qr.ts`, all `pages/*`, all backend paths.

## Tasks

1. **Add tokens** to `styles.css` under a new `/* === Phase 1 tokens === */` section:
   - Basalt scale (`--basalt-0` through `--basalt-950`).
   - Ember scale (`--ember-50` through `--ember-700`).
   - Verde scale (`--verde-50`, `--verde-500`, `--verde-700`).
   - Semantic aliases (`--status-success`, `--status-warning`, `--status-error`, `--status-inert`).
   - Radius (`--r-xs`…`--r-xl`), shadow (`--shadow-modal`), border (`--border-hair`).
   - Type scale variables (`--fs-12`…`--fs-64`), weight variables, line-height variables.
   - Motion variables (`--dur-micro:120ms`, `--dur-trans:200ms`, `--dur-panel:320ms`, `--ease-out`, `--ease-in`).
   - Layout variables (`--rail-w:240px`, `--rail-w-collapsed:64px`, `--topbar-h:56px`, `--content-max:1280px`).
   - Do NOT change or remove any existing `--indigo-*` variable — mark them `/* legacy, kept for back-compat */`.

2. **Add dark-mode block** `[data-theme="dark"]` in `styles.css` mapping semantic tokens to dark values (see spec §2.1). Do NOT flip variable meaning — remap only.

3. **Enforce tabular-nums**: add a utility class `.mono` and `.tabular` in `styles.css`. Set `font-variant-numeric: tabular-nums;` globally on `td` and `th` cells that already exist. This is the only cross-cutting change allowed.

4. **Create `theme.ts`** with:
   - `getTheme(): "light" | "dark"` — reads `localStorage.tc_theme` then `matchMedia`.
   - `setTheme(t): void` — writes localStorage + sets `data-theme` on `document.documentElement`.
   - `initTheme(): void` — call from `main.tsx`.
   - Add a single line `initTheme();` in `main.tsx` before `ReactDOM.createRoot`. This is the only allowed edit to `main.tsx`.

5. **Create AppShell components**:
   - `Sidebar.tsx`: props `{ collapsed: boolean; onToggle(): void }`. Renders logo lockup at top, nav items (Batches, Lab, Registry) with Lucide icons, divider, footer nav (Settings — link disabled if route doesn't exist yet, Help). Active state derived from `useLocation`. Keyboard-nav with `Tab`. Collapse toggle bottom-left with ⌘\ shortcut listener.
   - `Topbar.tsx`: props `{ onCmdK(): void }`. Renders wordmark on the left ONLY when sidebar collapsed. Center: a placeholder search button "Search… ⌘K" that calls `onCmdK` (no-op for now, wire in Phase 2). Right: theme toggle (sun/moon), help icon, avatar menu with Sign out that calls the existing `api.logout()` and `clearSession()` — REUSE, do not duplicate logic.
   - `EnvBanner.tsx`: renders a 4px `--ember-500` bar with text "Sandbox environment" ONLY when `import.meta.env.VITE_ENV === "sandbox"`. NOTE: `VITE_ENV` does not exist in the deployment today — the only env var in use is `VITE_API_BASE`. The banner must therefore default to HIDDEN when the var is undefined (never use `!== "production"`, which would show the banner in production). Read only what's already available; do not add the env var to any config.
   - `Breadcrumbs.tsx`: derives from `useLocation` + a static route→label map defined inline. For `/batches/:uuid` show `Batches / <short-uuid>`.
   - `AppShell.tsx`: composes EnvBanner + Topbar + Sidebar + `<main>{children}</main>` + Breadcrumbs above main. Handles sidebar collapsed state (persist in localStorage `tc_rail_collapsed`).

6. **Rewire `App.tsx`**:
   - Replace the current `<Shell>` component internals with `<AppShell>`.
   - Every `<Route>` must remain byte-identical in path + element. Only the wrapper JSX inside Shell changes.
   - Preserve `RequireAuth` and its behavior exactly.
   - Preserve the catch-all redirect to `/batches`.
   - Login route must remain UNwrapped by AppShell (login has no shell).

## Tests to add (`AppShell.test.tsx`)

Using `@testing-library/react` + `MemoryRouter`:

1. Renders sidebar with 3 primary links when authed.
2. Sign out button calls the mocked `logout` and `clearSession` (mock the modules).
3. Collapse toggle changes `data-collapsed` attribute and persists to localStorage.
4. Theme toggle flips `data-theme` on `documentElement`.
5. Breadcrumbs render correct label for `/batches/abc-123`.
6. EnvBanner does NOT render when `VITE_ENV` is undefined or `"production"`, and DOES render when `VITE_ENV === "sandbox"` (mock via `vi.stubEnv`).
7. Login route does not render AppShell (integration test rendering `<App />` at `/login`).

## Acceptance criteria
- [ ] All existing tests still pass unchanged.
- [ ] Typecheck, build, test suite all green.
- [ ] Visiting `/batches`, `/batches/xxx`, `/lab/scan`, `/lab/xxx`, `/registry` renders the new shell with no visual regression inside the page body (page bodies untouched this phase).
- [ ] Visiting `/login` renders WITHOUT the shell.
- [ ] Toggling theme flips light↔dark instantly and persists on reload.
- [ ] Collapsing sidebar persists on reload.
- [ ] No console errors, no console warnings related to your changes.
- [ ] No hardcoded colors, sizes, or durations in any new file — all reference tokens.
- [ ] Zero changes in `api.ts`, `auth.ts`, `compliance.ts`, `qr.ts`, or any page file.

## Deliverables
- Diff summary (files added / modified).
- Screenshot of `/batches` in light + dark mode.
- Confirmation string: `PHASE 1 COMPLETE — ready for Phase 2 approval.`

STOP after Phase 1. Wait for approval.

---

# PHASE 2 — Batches list redesign

## Objective
Replace the plain table on `/batches` with a proper DataTable + FilterBar + saved views + empty/loading states. No API contract changes.

## Whitelist
- `portal/src/pages/Batches.tsx` — full rewrite ALLOWED, but must call the same `listBatches(...)` with the same argument shape and consume `BatchRow` unchanged.
- `portal/src/components/DataTable/*` (new)
- `portal/src/components/FilterBar/*` (new)
- `portal/src/components/StatusDot/*` (new)
- `portal/src/components/EmptyState/*` (new)
- `portal/src/components/Skeleton/*` (new)
- `portal/src/pages/__tests__/Batches.test.tsx` — extend existing test if present, do NOT delete existing assertions.
- `package.json` — add `cmdk` (for later phase but install now), `@radix-ui/react-tabs`.

## Blacklist reminder
`api.ts` types & functions untouchable. `compliance.ts` untouchable.

## Tasks

1. **Build `StatusDot`**: props `{ variant: "success" | "warning" | "error" | "inert"; label?: string }`. Renders 8px dot + optional label. Uses semantic tokens only.
2. **Build `EmptyState`**: props `{ icon: ReactNode; title: string; description?: string; action?: {label; onClick} }`.
3. **Build `Skeleton`**: shape variants `text | number | row | card`. No animation if `prefers-reduced-motion`.
4. **Build `FilterBar`**: renders search input, filter chips, clear-all. Filter chips are stateless — parent controls value. Emits `onChange(filterState)`. Type the state as a discriminated union.
5. **Build `DataTable<T>`**: generic. Props `{ columns: ColumnDef<T>[]; rows: T[]; rowKey(row): string; onRowClick?(row); loading?: boolean; empty?: ReactNode; }`. Features:
   - Sticky header.
   - Column defs support `align: "left"|"right"`, `mono?: boolean`, `width?: string`.
   - Keyboard: ArrowUp/Down to move focus, Enter to activate `onRowClick`.
   - Loading state: render N skeleton rows matching column widths.
   - Empty state: render `empty` prop.
   - Does NOT do sorting/paging internally — parent supplies rows.

6. **Rewrite `Batches.tsx`**:
   - Keep the exact `listBatches({ status, provisional, cursor })` call. Do NOT add new params.
   - Above table: `Batches` H1 + right actions (Export CSV — disabled placeholder button OK; New batch — hidden if not admin, uses existing `getRole()` from `auth.ts` READ-ONLY).
   - Below H1: saved-view tabs (Radix Tabs): All / Awaiting review / Blocking issues / Issued. Each tab maps to a fixed filter combo → sets state, refetches. Persist active tab in URL query (`?view=awaiting`).
   - Below tabs: FilterBar for search text (client-side filter over already-fetched rows — do NOT change API), status select, provisional select. Clear-all resets to view default.
   - Columns: Batch (mono short + copy button), Kiln/Device (device_id), Received (fmtDate), **Credits (tCO₂e)** right-aligned mono, Status (StatusDot), Blockers (numeric), open detail.
   - Row click → `nav("/batches/" + b.batch_uuid)` (unchanged behavior).
   - Bulk-select checkboxes: render but keep bulk action bar as visual only for this phase; wire actions in a future phase.
   - Empty state: use `EmptyState` component with copy from spec.
   - Loading: `DataTable loading={true}` for initial load; keep-existing-data-visible on subsequent loads.
   - Error state: red-bordered inline card with retry button that re-calls `load()`.
   - Pagination: keep existing cursor logic. Move "Load more" to a right-aligned link-style button at table footer with total shown ("Showing 42 rows").

## Tests

Extend `Batches.test.tsx`:
1. Renders skeleton on initial load.
2. Renders empty state when API returns `{rows: [], nextCursor: null}` (mock `listBatches`).
3. Renders rows with correct StatusDot variant given a mocked `BatchRow`.
4. Clicking a row navigates to `/batches/:uuid`.
5. Changing filter chip triggers a new `listBatches` call with correct args.
6. Copy-hash button copies `batch_uuid` to clipboard (mock `navigator.clipboard`).
7. Blocking issues tab pre-filters to rows with `reason_count > 0`.
8. AuthError from `listBatches` triggers redirect to `/login` (preserve existing behavior).

Add `DataTable.test.tsx`, `FilterBar.test.tsx`, `StatusDot.test.tsx`, `EmptyState.test.tsx` — basic render + interaction tests each.

## Acceptance criteria
- [ ] `/batches` renders with new UI; no console errors.
- [ ] All existing tests still pass.
- [ ] All new tests pass.
- [ ] Keyboard nav works: Tab to table, ArrowDown/Up to move row focus, Enter to open.
- [ ] `listBatches` call signature is unchanged — verify by grepping the file: exactly one call site, same args as before.
- [ ] No hardcoded colors/sizes.
- [ ] `BatchRow` interface not modified anywhere.

## Deliverables
- Diff summary + screenshots (light/dark, empty state, loading state, filled state).
- `PHASE 2 COMPLETE — ready for Phase 3 approval.`

STOP.

---

# PHASE 3 — BatchDetail hero, verification chain, metric block

## Objective
Redesign the top of `BatchDetail.tsx`: verification chain strip, hero card with sealed verdict, provenance tile, LCA breakdown tile.

## Whitelist
- `portal/src/pages/BatchDetail.tsx` — allowed to rewrite render tree. Data-fetching logic (`getBatch`, `fetchMediaUrl`, `issueCredit`, `downloadExport`) MUST remain functionally identical.
- `portal/src/components/VerificationChain/*` (new)
- `portal/src/components/MetricBlock/*` (new)
- `portal/src/components/SealedVerdict/*` (new)
- `portal/src/components/ProvenanceTile/*` (new)
- `portal/src/components/LcaBreakdown/*` (new)
- `portal/src/components/CopyButton/*` (new)
- `portal/src/pages/__tests__/BatchDetail.test.tsx`

## Blacklist reminder
Do NOT modify `BatchDetail` type. Do NOT add new API calls. Do NOT change modal behavior yet (that's Phase 5).

## Tasks

1. **Audit `BatchDetail` interface** by reading `api.ts`. List every field available. If the spec requires a field that doesn't exist on the type, STOP and ask.
2. **VerificationChain**: props `{ nodes: {label: string; sublabel?: string; state: "done" | "current" | "pending" | "failed"}[] }`. Renders horizontal chain with connectors. On mobile stacks vertically.
3. **MetricBlock**: props `{ value: string; unit: string; caption?: string; size?: "sm"|"md"|"lg" }`. Uses mono + tabular-nums. Optional count-up animation gated by `prefers-reduced-motion`.
4. **SealedVerdict**: props `{ verdict: "ISSUABLE" | "PROVISIONAL" | "BLOCKED"; reasonCount?: number }`. Renders a stamp-style badge with icon + subtle border, colored by semantic token.
5. **CopyButton**: props `{ value: string; label?: string }`. Copies value, shows 200ms check-icon swap + toast.
6. **ProvenanceTile**: consumes only fields that exist on `BatchDetail` (submitter/device/hash/gps/methodology_version if present). If a field is missing on the actual type, render an em-dash — never fabricate.
7. **LcaBreakdown**: consumes only fields that exist. If a waterfall is not feasible with current data, render a simple list. Do NOT invent data.
8. **Rewrite BatchDetail render tree**:
   - Preserve all effects/hooks and their dependencies.
   - Preserve every conditional (loading, err, admin gating).
   - Preserve the existing modal component and props for now — Phase 5 redesigns it.
   - Replace visual tree with: VerificationChain → hero card (batch id + kiln + methodology on left, MetricBlock + SealedVerdict + admin action rail on right) → 3-column grid (Production placeholder using existing available fields, LcaBreakdown, ProvenanceTile) → the existing ComplianceChecklist untouched → the existing media grid untouched.

## Tests

Extend `BatchDetail.test.tsx` (mock `getBatch`):
1. Renders MetricBlock with correct credit value in tCO₂e.
2. SealedVerdict shows ISSUABLE when `compliance.issuable === true`.
3. SealedVerdict shows PROVISIONAL with reason count when not issuable.
4. Copy button copies batch_uuid.
5. Admin-only actions render only when `getRole() === "admin"` (mock auth).
6. VerificationChain renders 4 nodes.
7. Loading skeleton renders when `getBatch` unresolved.

## Acceptance criteria
- [ ] Every `api.ts` function called before this phase is still called with identical args.
- [ ] The `ComplianceChecklist` render remains functionally intact (visual polish is Phase 4).
- [ ] Existing "issue credit" modal still opens and works — untouched behavior.
- [ ] All tests green.
- [ ] No fabricated data — if a field is not on `BatchDetail`, it's not rendered.

## Deliverables
- Screenshots (light/dark, ISSUABLE + PROVISIONAL states).
- `PHASE 3 COMPLETE — ready for Phase 4 approval.`

STOP.

---

# PHASE 4 — Compliance checklist + evidence media redesign

## Objective
Replace ComplianceChecklist rendering with grouped accordion + severity sort + sticky mini-nav. Redesign media evidence into case-file chapters + lightbox.

## Whitelist
- `portal/src/components/ComplianceChecklist/*` (new — replaces current inline component wherever it lives)
- `portal/src/components/EvidenceGallery/*` (new)
- `portal/src/components/EvidenceLightbox/*` (new)
- `portal/src/pages/BatchDetail.tsx` — swap in new components. No logic changes.
- `package.json` — add `@radix-ui/react-accordion`, `@radix-ui/react-dialog`.

## Blacklist
`compliance.ts` is READ-ONLY. Use its exported helpers (`groupChecklist`, `statusOf`, `GROUP_LABEL`, `GROUP_ORDER`) exactly as they are.

## Tasks

1. **ComplianceChecklist component**:
   - Props: `{ items: ChecklistItem[] }`.
   - Call `groupChecklist(items)` from `compliance.ts` — do NOT reimplement grouping.
   - Render accordion sections in `GROUP_ORDER`. Header shows group label + counts (ok/blocking/inert) using StatusDot inline.
   - Inside each section: list rows sorted by severity (blocking first, then inert, then ok). Each row: severity icon, `code`, human title, enforcement badge, "View evidence →" anchor that scrolls-into-view of the media chapter with matching `capture_type` (if applicable).
   - Sticky mini-nav on the right (desktop only, >1024px): list of group labels + counts, click scrolls to section.
2. **EvidenceGallery**:
   - Props: `{ media: MediaItem[] }`.
   - Group by `capture_type` using the existing `STEP_ORDER` and `STEP_TITLES` constants — READ them from wherever they currently live (do NOT redefine).
   - Render numbered chapter headers "1. Feedstock preparation · 4 photos".
   - Each cell: thumbnail via `fetchMediaUrl` (unchanged), below it hash-short (mono) + verification tick if `capture_type_verified` + timestamp.
   - Filter tabs above: All / Photos / Videos / Certificates. Client-side filter only.
   - Click cell → opens EvidenceLightbox.
3. **EvidenceLightbox**:
   - Radix Dialog. Full-screen dark backdrop.
   - Shows full media, full hash (mono), GPS with copy button, EXIF timestamp, capture-type verified state, batch link back.
   - Keyboard: Esc to close, ← → to navigate items in current filter.
   - Focus trap handled by Radix; verify.
4. **Wire into BatchDetail**:
   - Replace the old checklist + media grid render blocks with the new components.
   - Keep every prop source the same: pass `d.compliance.checklist` and `d.media` — no transformation in the parent.

## Tests

1. `ComplianceChecklist.test.tsx`: given a fixture with items across groups + statuses, sections render in `GROUP_ORDER`, blocking items sort first, counts are correct. Mock `compliance.ts` is NOT allowed — use real module.
2. `EvidenceGallery.test.tsx`: chapters render in `STEP_ORDER`, filter tabs work, empty chapter is not rendered.
3. `EvidenceLightbox.test.tsx`: opens on click, Esc closes, arrow keys navigate, focus is trapped (assert focus stays inside dialog after Tab).
4. Integration test in `BatchDetail.test.tsx`: after `getBatch` resolves with a fixture containing checklist + media, both new components render with correct data.

## Acceptance criteria
- [ ] No changes to `compliance.ts` or `MediaItem`/`ChecklistItem` types.
- [ ] Keyboard-only user can browse full evidence set (Tab, Enter, Esc, arrows).
- [ ] Screen reader announces group section as landmark region with count.
- [ ] All tests green.

## Deliverables
- Screenshots: expanded checklist with blockers, evidence gallery, lightbox open.
- `PHASE 4 COMPLETE — ready for Phase 5 approval.`

STOP.

---

# PHASE 5 — Activity timeline + redesigned Issue-Credit modal

## Objective
Add an activity log timeline on BatchDetail (using data available on `BatchDetail` — if none, render an informative empty state, do NOT invent). Redesign the issue-credit confirmation modal with dynamic-token confirmation + preview block.

## Whitelist
- `portal/src/components/ActivityTimeline/*` (new)
- `portal/src/components/ConfirmModal/*` (new)
- `portal/src/pages/BatchDetail.tsx` — swap modal usage.

## Blacklist
Do NOT add an "activity log" API call. If `BatchDetail` does not include activity/history fields, the timeline shows an empty state "Activity log will appear here once the backend exposes it" with a `data-testid="activity-empty"`. Do NOT fake events.

## Tasks

1. **ActivityTimeline**: props `{ events: {id, actor, action, at, meta?}[] }`. Vertical timeline. If empty, show empty state.
2. **ConfirmModal**: props `{ open; onOpenChange; title; previewRows: {label; value; mono?}[]; warning?: string; confirmToken: string; confirmLabel: string; danger?: boolean; onConfirm(): Promise<void>; }`. Radix Dialog. Renders preview block, warning box with amber left border, typed confirmation input (disabled confirm until value === token), primary button ember (or red if `danger`).
3. **In BatchDetail**:
   - Replace old modal usage with `<ConfirmModal>`.
   - `confirmToken = "ISSUE-" + batch_uuid.slice(0, 6)` — dynamic per batch.
   - `previewRows`: Batch ID, Kiln, Credits (mono, tCO₂e), Methodology version (if available on type).
   - `warning`: "This is irreversible. Credits will be published to the immutable registry within 10 minutes."
   - `onConfirm`: call existing `issueCredit(batch_uuid)` — do NOT modify.
   - On success: close modal, refetch `getBatch(batch_uuid)`.

## Tests

1. `ConfirmModal.test.tsx`: confirm button disabled until token typed exactly; typing wrong token keeps disabled; onConfirm called once on click; loading state disables all inputs.
2. `BatchDetail.test.tsx` extension: opening issue modal shows dynamic token including partial batch UUID; typing correct token enables button; clicking calls mocked `issueCredit` with correct uuid; on success, `getBatch` is called again.
3. `ActivityTimeline.test.tsx`: renders events chronologically; empty state renders when `events=[]`.

## Acceptance criteria
- [ ] Existing `issueCredit` call signature unchanged.
- [ ] Modal is keyboard accessible (Esc closes, focus trap, focus returns to trigger on close).
- [ ] No fabricated activity events.

## Deliverables
- Screenshots of modal open state and modal with invalid vs valid token.
- `PHASE 5 COMPLETE — ready for Phase 6 approval.`

STOP.

---

# PHASE 6 — Login, LabScan, LabEntry, Registry pages

## Objective
Bring the remaining pages up to spec without altering their API interactions.

## Whitelist
- `portal/src/pages/Login.tsx`
- `portal/src/pages/LabScan.tsx`
- `portal/src/pages/LabEntry.tsx`
- `portal/src/pages/Registry.tsx`
- New components as needed under `portal/src/components/`
- Add `@radix-ui/react-tooltip` if not yet installed.

## Blacklist reminder
`api.ts`, `auth.ts`, `qr.ts` are READ-ONLY. Every login/scan/lab/registry API function call must have identical arguments.

## Tasks (Login)
1. Split-screen layout. Right panel: static proof block for now — hardcode ONLY if the values are already available via existing endpoints; otherwise render a "brand quiet panel" with wordmark + methodology line — no fake numbers.
2. Password show/hide toggle (client-only, does not touch auth).
3. Inline field error with red left-border on invalid.
4. Preserve exact `api.login(email, password)` call and success path (`setSession`, navigate to `/batches`).

## Tasks (LabScan)
1. Full-viewport camera area with rounded reticle overlay in `--ember-500`.
2. Recently scanned list: read from localStorage `tc_recent_scans` (new key, safe to introduce). Store batch_uuid on successful scan navigation.
3. Manual entry fallback input.
4. Preserve QR decoding logic — use `qr.ts` helpers exactly.

## Tasks (LabEntry)
1. Two-column layout: form left, live-preview right.
2. Live preview calls **no new API** — it's a client-side hint using `compliance.ts` group labels + a static mapping of form fields → C-codes if available in the current code; if no such mapping exists, render the preview as "Rules that will be checked when you submit" with a static list from `GROUP_LABEL.lab`.
3. Certificate upload: on file selected, compute SHA-256 in-browser using `crypto.subtle` and display it. This is UI feedback only — the actual upload still uses existing `uploadLabCertificate`.
4. Preserve `submitLabResults` call unchanged.

## Tasks (Registry)
1. Tabs: Kilns / Operator training / Standards (Standards can be a "Coming soon" empty state — no new API).
2. Kilns: card grid from `listKilns` (unchanged call).
3. "Register new kiln" stepper (Radix Dialog + internal step state): 1. Location & GPS, 2. Photos, 3. Operator, 4. Review. Final submit calls existing `registryPost({kind: "kilns", ...})` with the exact payload shape currently used. If current call structure differs, STOP and ask before proceeding.
4. Operator training: use `registryPost({kind: "operator-training", ...})` — same rule.

## Tests
- Extend each existing page test. Add:
  - Login: show/hide password toggles input type; invalid email shows inline error.
  - LabScan: recent scans render from localStorage; manual entry navigates.
  - LabEntry: cert hash displayed matches computed hash for a fixed test blob.
  - Registry: stepper advances, submit payload matches expected shape (assert via mock of `registryPost`).

## Acceptance criteria
- [ ] Zero changes to `api.ts` / `auth.ts` / `qr.ts`.
- [ ] All call sites use identical arg shapes.
- [ ] All new features degrade gracefully when data is missing.
- [ ] All tests green.

## Deliverables
- Screenshots of each page (light/dark).
- `PHASE 6 COMPLETE — ready for Phase 7 approval.`

STOP.

---

# PHASE 7 — Polish, a11y, motion, print, dark-mode QA

## Objective
Final pass. Nothing new — only hardening.

## Whitelist
Any UI-only file in `portal/src/**` except the READ-ONLY list.

## Tasks
1. **A11y audit**: run `npx @axe-core/cli` or `jest-axe` in tests on every page render. Fix all violations. No exceptions granted without explicit approval.
2. **Focus rings**: verify every interactive element has visible focus per token. Add missing.
3. **Motion**: audit every transition. Wrap in `@media (prefers-reduced-motion: reduce)` overrides.
4. **Print styles**: `@media print` — hide sidebar, topbar, buttons, filter bar. Ensure BatchDetail prints as an evidence pack in A4 portrait. Test with browser print preview.
5. **Skip-to-content** link at top of `AppShell`.
6. **Dark-mode QA**: page through every route in dark mode. Fix all contrast + hardcoded-white bugs.
7. **Tabular-nums enforcement**: grep for numeric renders that skip `.mono`/`.tabular` classes on credits, hashes, timestamps. Fix.
8. **Coverage**: run `npm run test -- --coverage`. Ensure new components ≥ 80% line coverage. Add tests to fill gaps.
9. **Bundle check**: run `npm run build`. Confirm no dep is dead-imported. No source-map warnings.
10. **README update** in `portal/README.md` only (if it exists; otherwise create): list new components, token names, theming instructions, accessibility posture.

## Tests
- Add `a11y.test.tsx` for each page rendering, assert axe returns zero violations.
- Add snapshot test for `AppShell` in light and dark data-theme states — visual regression guard.

## Acceptance criteria
- [ ] `jest-axe` reports zero violations across every page.
- [ ] Test coverage ≥ 80% on all new components.
- [ ] Print preview of BatchDetail is legible, one document, no cut UI chrome.
- [ ] Bundle size delta reported. Justify any increase > 100KB gzipped.
- [ ] All hardcoded values eliminated (grep confirms).

## Deliverables
- Coverage report screenshot.
- Axe report (zero violations).
- Screenshots: print preview, dark mode of every page.
- `PHASE 7 COMPLETE — PORTAL REDESIGN SHIPPED.`

---

# COMMON PITFALLS — READ TWICE

- **Do not** run `npm update` or `npm audit fix --force`.
- **Do not** convert function components to class components.
- **Do not** introduce a state management library. `useState` + `useReducer` only.
- **Do not** add server-state libraries (React Query, SWR). The existing pattern of `useEffect + useCallback` is intentional; changing it is out of scope.
- **Do not** move files across directories in ways that break imports elsewhere.
- **Do not** rename any export from `api.ts`, `auth.ts`, `compliance.ts`, `qr.ts`.
- **Do not** hardcode API base URLs. Reuse `import.meta.env.VITE_API_BASE` path.
- **Do not** log tokens, hashes, PII to console.
- **Do not** commit `node_modules`, `dist`, `.env*` files.
- If any spec sentence contradicts a guardrail, the guardrail wins. STOP and ask.

---

# ASK-FIRST TRIGGERS (mandatory)

STOP and ask a single question when:
- The spec references a field, prop, or endpoint you cannot verify by reading `api.ts`.
- A test starts failing that was passing before your change and the fix requires touching a blacklisted file.
- A dependency you need is not on the approved list.
- Visual spec cannot be implemented with the available data (e.g., LCA waterfall needs fields that don't exist).
- You believe a guardrail is wrong for a specific case.

Format: `⚠️ BLOCKED — Phase N Task M — <one-sentence question>`

---

# FINAL WORD

Ship each phase like it will be reviewed by a security auditor and a design partner in the same meeting. No shortcuts. When in doubt, STOP.
