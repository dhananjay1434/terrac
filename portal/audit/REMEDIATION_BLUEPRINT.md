# TerraCipher Portal — UI/UX Remediation Blueprint v2 (62 → 95)

**Audience:** AI coding agents executing ONE task at a time.
**Prime directive:** If a code block is provided in a task, copy it VERBATIM. If reality does not match what this document claims, do NOT improvise — follow the BLOCKED protocol (§0.2).
**Source findings:** `portal/audit/UI_UX_AUDIT_REPORT.md` (IDs like X1, BD2, S1).

---

## 0 · GLOBAL RULES (re-read before EVERY task)

### 0.1 Hard rules
1. **Never edit** `src/api.ts`, `src/auth.ts`, `src/compliance.ts`, `src/qr.ts`. Importing FROM them is allowed. Editing them is FORBIDDEN even if a fix seems easier there.
2. **Never** run `npm install <anything>`, edit `package.json`, `vite.config.ts`, or `tsconfig.json`. No new dependencies exist in this plan; if you think you need one, you misread the task → BLOCKED protocol.
3. **No hardcoded values** outside `src/tokens/tokens.css`: no hex colors, no `rgba(...)`, no raw `font-size` px, no raw animation durations. Everything is `var(--…)`. If the token you need does not exist yet, your task is out of order → BLOCKED.
4. **Find code by ANCHOR TEXT, never by line number.** Line numbers in the audit report have drifted. Every task below gives you an anchor string to search for. If the anchor appears 0 times or 2+ times in the named file → BLOCKED.
5. **No god files.** New components: `src/ui/<Name>/<Name>.tsx` + `<Name>.module.css` + `<Name>.test.tsx` (three files, own folder). Component ≤150 lines, CSS module ≤120 lines.
6. **Every task ships/updates its test.** Never delete a failing assertion to go green — fix code or fix the expectation deliberately and say so in your report.
7. **Language law:** sentence case everywhere ("Registered projects"). Missing data = `—` (U+2014). Ellipsis = `…` (U+2026). Never "null", "-", "...", never prose like "no GPS".
8. **Spacing law:** replace raw px with tokens: 4=`--space-1` 8=`--space-2` 12=`--space-3` 16=`--space-4` 24=`--space-5` 32=`--space-6` 48=`--space-7` 64=`--space-8`. Off-scale mapping: 2→4 · 6→8 (control gaps) or 4 (icon-text gaps) · 9→8 · 10→8 (inside controls) or 12 (between blocks) · 14→16 · 18→16 · 20→24 · 28→24 · 40→48 · 60→64. Rule of thumb: inner padding rounds DOWN, outer margins round UP.
9. **Icons:** lucide-react only, size 14 (in pills/sm buttons), 16 (default), 18 (topbar). Never inline-SVG an icon by hand.
10. **Role gating:** any control that calls an admin-only endpoint renders only when `getRole() === "admin"`. Verifiers get read-only equivalents, never disabled forms.

### 0.2 BLOCKED protocol (anti-hallucination)
When anything differs from this document — anchor not found, file missing, test API different, token absent, prior task apparently not done:
1. STOP editing immediately (revert partial edits of this task).
2. Report: `STATUS: blocked` + the exact anchor/file you searched + first 3 lines of what you actually found.
3. Do NOT guess a substitute change. Do NOT skip ahead to the next task.

### 0.3 Environment & commands
- Working dir: `portal/`. Windows shell — prefer `npx` invocations exactly as written.
- After each task: `npx vitest run <your test file(s)>` then `npx tsc --noEmit`.
- Snapshot updates (only when a task says so): `npx vitest run -u src/components/AppShell`.
- End of each phase: `npm run verify` (tests + typecheck + build) must be fully green before the phase is "done".
- Never start the dev server; never run capture scripts unless the task says so.

### 0.4 Per-task report format (mandatory, exactly this)
```
TASK: <id>  STATUS: done|blocked
FILES: <paths touched>
TESTS: <test files run> → <pass count>/<total>
VERIFY: tsc --noEmit → clean|<error count>
NOTES: <max 3 lines; empty if nothing off-spec>
```

### 0.5 Task manifest (tick as you go — this is the definition of "everything fixed")
```
P1: [ ]1.1 [ ]1.2 [ ]1.3 [ ]1.4 [ ]1.5
P2: [ ]2.1 [ ]2.2 [ ]2.3 [ ]2.4 [ ]2.5 [ ]2.6
P3: [ ]3.1 [ ]3.2
P4: [ ]4.1 [ ]4.2 [ ]4.3 [ ]4.4
P5: [ ]5.1 [ ]5.2 [ ]5.3 [ ]5.4 [ ]5.5 [ ]5.6
P6: [ ]6.1 [ ]6.2 [ ]6.3 [ ]6.4 [ ]6.5 [ ]6.6 [ ]6.7
P7: [ ]7.1 [ ]7.2 [ ]7.3 [ ]7.4 [ ]7.5 [ ]7.6 [ ]7.7
P8: [ ]8.1 [ ]8.2 [ ]8.3 [ ]8.4 [ ]8.5 [ ]8.6
```

---

## 0.6 · VISUAL HIERARCHY SPEC (the "which number is big" contract — consult, don't deviate)

| Element | Size | Weight | Color |
|---|---|---|---|
| Page title (h1) | `--fs-20` | `--fw-bold` | `--text-primary` |
| Section title (h2) | `--fs-16` | `--fw-semibold` | `--text-primary` |
| Card micro-label | `--fs-12` | `--fw-medium` | `--text-tertiary` |
| **Hero number** (BatchDetail net credit) | `--fs-48` | `--fw-semibold` | `--text-primary` — biggest number in the app; unit `--fs-16` semibold `--text-secondary` |
| **KPI value** (stat tiles) | `--fs-32` | `--fw-semibold` | `--text-primary`, always `.tabular` |
| Table cell | `--fs-13` | regular | `--text-primary`; numerics right + `.tabular` |
| Table header | `--fs-12` | `--fw-medium` | `--text-tertiary` |
| Verdict stamp (lg) | `--fs-24` | `--fw-bold` | semantic tokens |
| Chart axis label | `--fs-12` | regular | `--text-tertiary` via SVG `fill` |
| Body text | `--fs-14` | regular | `--text-secondary`, `--lh-normal` |
| Hash/UUID/token metadata | `--fs-12` | regular | `.mono`, `--text-primary` |

**Dashboard chart law:** bars = indigo tones only (`indigoTone(0)` strongest for net credit above zero; `indigoTone(1..3)` lighter for deductions hanging below); zero baseline = 1px `--border-strong` (the semantic anchor); period labels `--fs-12` tertiary; tooltip = `--surface-card` + `--border-hair` + `--shadow-md`, net-credit row FIRST and `--fw-semibold`, all values `.tabular`; granularity toggle lives INSIDE the chart card header row, right-aligned; empty state = `EmptyState` component, never bare text.

**Number law (all formats live ONLY in `src/format.ts`):** credits `1,234.560` (3 decimals + grouping) · kg `85,000 kg` · date `02 Feb 2026` · datetime `02 Feb 2026, 10:05 UTC` · percent `92.4%`.

---

# PHASE 1 — TOKEN LAYER (do first, strictly in order)

## P1.1 Dark status aliases (THE critical fix — X1, BD1, CM1, B1, X3)
**File:** `src/tokens/tokens.css`. **Anchor:** `--shadow-modal: 0 20px 48px rgba(0, 0, 0, 0.5)` (inside the `[data-theme="dark"]` block). Insert AFTER that declaration's line, still inside the same block:
```css
  /* single-value status aliases must follow the -fg remaps (audit X1) */
  --status-success: var(--status-success-fg);
  --status-warning: var(--status-warning-fg);
  --status-error: var(--status-error-fg);
  --status-inert: var(--basalt-400);
```
Then find anchor `--action-primary-hover: #8b85ff;` in the SAME dark block and replace with:
```css
  --action-primary-hover: #5148e6;
```
**Test:** create `src/tokens/tokens.test.ts`:
```ts
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
const css = readFileSync(new URL("./tokens.css", import.meta.url), "utf8");
const dark = css.slice(css.indexOf('[data-theme="dark"]'));
describe("dark status aliases (audit X1)", () => {
  it.each(["--status-success: var(--status-success-fg)", "--status-warning: var(--status-warning-fg)", "--status-error: var(--status-error-fg)", "--status-inert: var(--basalt-400)"])("dark block remaps %s", (decl) => {
    expect(dark).toContain(decl);
  });
  it("dark hover is AA-safe", () => expect(dark).toContain("--action-primary-hover: #5148e6"));
});
```
**Done when:** vitest + tsc green.

## P1.2 New tokens
**File:** `src/tokens/tokens.css`. **Anchor (root):** `--space-8: 64px;` — insert AFTER it, inside `:root`:
```css
  /* overlays (audit X8) */
  --overlay-scrim: rgba(15, 17, 21, 0.4);
  --overlay-scrim-strong: rgba(15, 17, 21, 0.7);
  /* radius gap */
  --r-pill: 999px;
  /* z scale (audit X6) */
  --z-sticky: 10;
  --z-dropdown: 20;
  --z-tooltip: 30;
  --z-scrim: 55;
  --z-drawer: 60;
  --z-overlay: 90;
  --z-modal: 100;
  --z-skiplink: 200;
  /* control + icon sizing (audit X9) */
  --control-h-md: 36px;
  --control-h-lg: 44px;
  --icon-sm: 14px;
  --icon-md: 16px;
  --icon-lg: 18px;
  /* motion gaps (audit X7) */
  --dur-spin: 600ms;
  --dur-pulse: 1500ms;
  /* video-overlay reticle — theme-independent by design (audit LE5) */
  --scan-reticle: rgba(255, 255, 255, 0.9);
```
**Anchor (dark):** the `--status-inert: var(--basalt-400);` line you added in P1.1 — insert AFTER it:
```css
  --overlay-scrim: rgba(0, 0, 0, 0.6);
  --overlay-scrim-strong: rgba(0, 0, 0, 0.75);
```
**Test:** extend `tokens.test.ts` — assert each new token name appears in the `:root` slice (`css.slice(0, css.indexOf('[data-theme'))`), and both overlay remaps appear in `dark`.

## P1.3 Kill phantom tokens (X2, BD9)
Five replacements — for each: search the EXACT anchor, replace whole `var(...)` expression.
| File | Anchor (search) | Replace with |
|---|---|---|
| `src/components/ParcelMap/ParcelMap.module.css` | `var(--radius-m, 8px)` | `var(--r-lg)` |
| same | `var(--border-color, #e2e8f0)` (2×: if found twice, replace BOTH) | `var(--border-subtle)` |
| same | `var(--border-color, #cbd5e1)` | `var(--border-strong)` |
| same | `var(--bg-card, #f8fafc)` | `var(--surface-sunken)` |
| `src/components/EvidenceGallery/EvidenceGallery.module.css` | `var(--radius-s, 4px)` | `var(--r-sm)` |
| `src/ui/HorizontalBarList/HorizontalBarList.module.css` | `var(--r-pill, 999px)` | `var(--r-pill)` |
| `src/components/TemperatureChart/TemperatureChart.tsx` | `var(--accent, currentColor)` (3×: replace ALL) | `var(--indigo-600)` |
NOTE: anchors with fallbacks may differ slightly (e.g. `var(--border-color,#e2e8f0)` without space). If exact string not found, search for `--border-color` etc. within that file only and replace each full `var(...)` expression. Anything outside these files → BLOCKED.
**Test:** extend `tokens.test.ts`:
```ts
// phantom tokens must never come back (audit X2)
import { readdirSync, statSync } from "node:fs";
// walk src/, read every .css/.tsx, assert no /var\(--(radius-|border-color|bg-card|accent)/ match
```
(Implement the walk inline; skip `node_modules`, `audit`.)

## P1.4 ParcelMap palette conversion (P2)
**File A:** `src/components/ParcelMap/ParcelMap.module.css` — after P1.3 no hex should remain except possibly `#e2e8f0`/`#cbd5e1`/`#f8fafc` outside var() fallbacks; search each of those three hexes, replace: `#e2e8f0`→`var(--border-subtle)`, `#cbd5e1`→`var(--border-strong)`, `#f8fafc`→`var(--surface-sunken)`. Search `font-size: 12px` (2×) → `font-size: var(--fs-12)`.
**File B:** `src/components/ParcelMap/ParcelMap.tsx` — anchor `color: "#3b82f6"` replace with:
```ts
color: getComputedStyle(document.documentElement).getPropertyValue("--indigo-600").trim() || "#635bff",
```
(Leaflet needs a literal string; resolving the token at runtime keeps tokens authoritative. The `|| "#635bff"` fallback is ALLOWED here — it is the same value as the token, for non-browser test envs.) Also anchor `fontSize: 11` → `fontSize: "var(--fs-12)"`.
**Test:** update `ParcelMap.test.tsx` — add assertion that component source no longer contains `#3b82f6` is NOT testable at runtime; instead assert rendered container exists (keep existing tests green). The file-walk test from P1.3 already guards hex regressions? No — it guards phantom vars only. Acceptable; move on.

## P1.5 Scrim + #fff dedup (X8)
| File | Anchor | Replace |
|---|---|---|
| `src/styles.css` | `background: rgba(15, 17, 21, 0.4);` (inside `.modal-overlay`) | `background: var(--overlay-scrim);` |
| `src/components/ConfirmModal/ConfirmModal.module.css` | `background: rgba(15, 17, 21, 0.4);` | `background: var(--overlay-scrim);` |
| `src/components/AppShell/AppShell.module.css` | `background: rgba(15, 17, 21, 0.4);` | `background: var(--overlay-scrim);` |
| `src/components/EvidenceLightbox/EvidenceLightbox.module.css` | `background: rgba(15, 17, 21, 0.7);` | `background: var(--overlay-scrim-strong);` |
| `src/styles.css` | `color: #fff;` (inside `button.primary` rule — verify the surrounding selector before editing) | `color: var(--basalt-0);` |
| `src/ui/Button/Button.module.css` | `color: #fff;` | `color: var(--basalt-0);` |
| `src/ui/DivergingStackedBarChart/DivergingStackedBarChart.module.css` | `box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);` | `box-shadow: var(--shadow-md);` |
**Test:** extend `tokens.test.ts`: walking test asserts `rgba(15, 17, 21` occurs ONLY in `tokens.css`.

**PHASE 1 GATE:** `npm run verify` green. Report phase summary.

---

# PHASE 2 — SHELL & FOCUS

## P2.1 Topbar cluster right (S1)
**File:** `src/components/AppShell/AppShell.module.css`. **Anchor:** `.topbarRight {`. Inside that rule add `margin-left: auto;` (keep everything else).
**Test:** `npx vitest run -u src/components/AppShell` (snapshot refresh); confirm diff only adds the property.

## P2.2 Z-scale in shell (S2 + part of X6)
Same file, four edits by anchor:
| Anchor | Replace value with |
|---|---|
| `z-index: 100;` inside `.skip` rule | `z-index: var(--z-skiplink);` |
| `z-index: 10;` inside `.topbar` rule | `z-index: var(--z-sticky);` |
| `z-index: 20;` inside `.menu` rule | `z-index: var(--z-dropdown);` |
| `z-index: 60;` inside `.rail` media rule | `z-index: var(--z-drawer);` |
| `z-index: 55;` inside `.scrim` media rule | `z-index: var(--z-scrim);` |
Verify each anchor sits inside the named rule before editing (read 3 lines up). **Test:** snapshot refresh.

## P2.3 Input keyboard focus ring (§1.5 exec summary)
**File:** `src/styles.css`. **Anchor:**
```css
input:focus, select:focus {
```
That rule currently sets `border-color: var(--border-strong); outline: none;` — KEEP it, and add IMMEDIATELY AFTER the closing brace:
```css
input:focus-visible,
select:focus-visible,
textarea:focus-visible {
  outline: 2px solid var(--indigo-600);
  outline-offset: 2px;
}
```
(Mouse focus stays quiet; keyboard focus gets the ring. Dark remap already exists via the `[data-theme="dark"] :focus-visible` rule at the top of styles.css — do not duplicate it.)
**Test:** none runnable in jsdom — NOTES line must say "visual check pending".

## P2.4 Breadcrumbs everywhere (S3)
**File:** `src/components/AppShell/Breadcrumbs.tsx`. Replace the `LABELS` object with:
```ts
const LABELS: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/batches": "Batches",
  "/lab/scan": "Lab / Scan",
  "/registry": "Registry",
  "/projects": "Projects",
  "/farmers": "Farmers",
  "/dispatch": "Dispatch",
};
```
And change the return statement to collapse when empty:
```tsx
if (!crumb) return null;
return <div className={styles.crumbs}>{crumb}</div>;
```
**Test:** create `src/components/AppShell/Breadcrumbs.test.tsx` — render inside `MemoryRouter initialEntries={[path]}` for each of the 7 paths asserting label text; assert `container.firstChild === null` for `/login`.

## P2.5 Account-menu identity + remove dead Help (S4, S5)
**File:** `src/components/AppShell/Topbar.tsx`.
1. DELETE the Help button JSX — anchor: `aria-label="Help"` (remove the whole `<button …>…</button>` containing it, and the now-unused `HelpCircle` import).
2. Inside `<DropdownMenu.Content …>` BEFORE the Sign-out item insert:
```tsx
<DropdownMenu.Label className={styles.menuLabel}>
  Signed in · {getRole() ?? "unknown"}
</DropdownMenu.Label>
```
Add import: `import { getRole, clearSession } from "../../auth";` (clearSession already imported — extend, don't duplicate).
3. **File:** `AppShell.module.css` — after the `.menuItem` rules add:
```css
.menuLabel {
  padding: var(--space-2);
  font-size: var(--fs-12);
  color: var(--text-tertiary);
  border-bottom: var(--border-hair);
  margin-bottom: var(--space-1);
}
```
**Test:** update AppShell tests: help button absent (`queryByLabelText("Help") === null`); open menu shows `Signed in ·` text. Snapshot refresh.
**DO NOT:** invent an email display — email is not stored client-side.

## P2.6 Platform tooltip + theme-color (S6, S7)
1. `src/components/AppShell/Sidebar.tsx` — anchor `title="⌘\"` replace with `` title={typeof navigator !== "undefined" && navigator.platform.toLowerCase().includes("mac") ? "⌘\\" : "Ctrl+\\"} ``.
2. `index.html` — anchor `<meta name="theme-color" content="#0f1115" />` replace with:
```html
    <meta name="theme-color" media="(prefers-color-scheme: light)" content="#f7f8fa" />
    <meta name="theme-color" media="(prefers-color-scheme: dark)" content="#0f1115" />
```
**Test:** snapshot refresh only.

**PHASE 2 GATE:** `npm run verify` green.

---

# PHASE 3 — FORMATTING CORE

## P3.1 `src/format.ts` (this file is editable) — REPLACE its entire contents with:
```ts
// Single source of truth for every human-readable number/date in the portal.
// Audit findings D1/B5/BD11/BD15/BD16 — one format per fact, everywhere.

const CREDIT_FMT = new Intl.NumberFormat(undefined, {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
  useGrouping: true,
});

/** Carbon-credit figure: grouped, always 3 decimals — "1,234.560". */
export function fmtCredit(t: number): string {
  return CREDIT_FMT.format(t);
}

/** Weight in kg: grouped, ≤1 decimal — "85,000 kg". */
export function fmtKg(kg: number): string {
  const s = new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 1,
    useGrouping: true,
  }).format(kg);
  return `${s} kg`;
}

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

/** "02 Feb 2026" (UTC), or "—" for missing. */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return `${String(d.getUTCDate()).padStart(2, "0")} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/** "02 Feb 2026, 10:05 UTC", or "—" for missing. */
export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${fmtDate(iso)}, ${hh}:${mm} UTC`;
}

/** "92.4%" — one decimal max. */
export function fmtPct(p: number): string {
  return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(p)}%`;
}
```
**Test:** create `src/format.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import { fmtCredit, fmtDate, fmtDateTime, fmtKg, fmtPct } from "./format";
describe("format law (audit §0.6)", () => {
  it("credits: grouped, 3 decimals", () => {
    expect(fmtCredit(646.16)).toBe("646.160");
    expect(fmtCredit(45900)).toBe("45,900.000");
    expect(fmtCredit(0)).toBe("0.000");
  });
  it("kg grouped", () => expect(fmtKg(85000)).toBe("85,000 kg"));
  it("date", () => expect(fmtDate("2026-02-02T10:05:00Z")).toBe("02 Feb 2026"));
  it("date null", () => expect(fmtDate(null)).toBe("—"));
  it("datetime", () => expect(fmtDateTime("2026-02-02T10:05:00Z")).toBe("02 Feb 2026, 10:05 UTC"));
  it("garbage in, em-dash out", () => expect(fmtDate("not-a-date")).toBe("—"));
  it("pct", () => expect(fmtPct(92.44)).toBe("92.4%"));
});
```
CAVEAT: `Intl` with `undefined` locale in vitest/jsdom uses the node ICU locale (en-US) → `,` grouping. If assertions fail on grouping char, pin the expectation via `(1234.5).toLocaleString()` sniff — report in NOTES, do not change the implementation.

## P3.2 Apply formatters (mechanical — 6 sub-edits, one file each; keep page tests green as you go)
1. `src/pages/Batches.tsx` — delete local `fmtDate` (anchor `function fmtDate`), add `fmtDate` to the existing `import { fmtCredit } from "../format";`.
2. `src/pages/Farmers.tsx` — same (local fmtDate → import).
3. `src/pages/Dispatch.tsx` — same.
4. `src/pages/Projects.tsx` — same.
5. `src/pages/BatchDetail.tsx` — anchor `d.batch.received_at?.slice(0, 10) ?? "—"` → `fmtDate(d.batch.received_at)`; anchor `{d.batch.wet_yield_kg} kg` (2×) → `{fmtKg(d.batch.wet_yield_kg)}` and the StatTile value ``` `${d.batch.wet_yield_kg} kg` ``` → `fmtKg(d.batch.wet_yield_kg)`; ConfirmModal preview rows keep `fmtCredit`.
6. `src/components/EvidenceGallery/EvidenceGallery.tsx` + `src/components/EvidenceLightbox/EvidenceLightbox.tsx` — anchor `.slice(0, 16).replace("T", " ")` (one each) → `fmtDateTime(item.uploaded_at)` (adjust surrounding ternary: `fmtDateTime` already handles null → `—`, so the whole ternary collapses to one call). Import from `"../../format"`.
7. `src/components/ProvenanceTile/ProvenanceTile.tsx` — READ the file first; replace its date rendering with `fmtDateTime(receivedAt)` equivalent (anchor: whatever `slice(` call it contains; if none → it already receives a preformatted string from BatchDetail — then fix at the BatchDetail call site instead; report which branch you took).
**Test:** update touched page tests' date expectations to the new format (e.g. `2026-02-02` → `02 Feb 2026`).
**Done check:** `grep -rn "slice(0, 10)\|slice(0,10)\|slice(0, 16)" src/pages src/components` → only allowed hits are uuid shorteners like `slice(0, 8)`; report any remainder.

**PHASE 3 GATE:** `npm run verify` green.

---

# PHASE 4 — PRINT EVIDENCE PACK (PR1–PR4, R8)

## P4.1 Evidence images must print (PR1 — Critical)
1. **File:** `src/components/EvidenceGallery/EvidenceGallery.tsx`. Anchor `className={styles.thumbBtn}` → `` className={`${styles.thumbBtn} thumb-print-keep`} `` (template literal — this file does NOT import clsx; do not add it).
2. **File:** `src/styles.css`, inside the existing `@media print {` block, BEFORE the rule that hides buttons, add:
```css
  .thumb-print-keep,
  .thumb-print-keep img,
  .thumb-print-keep video {
    display: block !important;
  }
```
ORDER MATTERS: later `button { display: none !important; }`... both have !important and equal-ish specificity — class selector (0,1,0) beats type selector (0,0,1) regardless of order, but keep the explicit order anyway for readability.
**Test:** `EvidenceGallery.test.tsx` — assert the thumb button's className contains `thumb-print-keep`.

## P4.2 Checklist print structure (PR2)
**File:** `src/components/ComplianceChecklist/ComplianceChecklist.tsx`. Inside the `Accordion.Item`, immediately BEFORE `<Accordion.Header`, add:
```tsx
<h3 className={styles.printTitle}>{g.label}</h3>
```
**File:** `ComplianceChecklist.module.css`, append:
```css
.printTitle {
  display: none;
}
@media print {
  .printTitle {
    display: block;
    margin: 0 0 var(--space-2);
    font-size: var(--fs-13);
    font-weight: var(--fw-semibold);
  }
}
```
**Test:** checklist test asserts one `printTitle`-classed h3 per group (query by heading role level 3).

## P4.3 Print header block (PR3)
**File:** `src/pages/BatchDetail.tsx`. First child inside the main `<div className="wrap">` (anchor `<VerificationChain nodes={chainNodes} />` — insert BEFORE it):
```tsx
<header className="print-only" aria-hidden>
  <div className="mono">{d.batch.batch_uuid}</div>
  <div>
    {d.compliance.issuable ? "ISSUABLE" : "PROVISIONAL"} · net credit{" "}
    {fmtCredit(d.batch.net_credit_t_co2e)} tCO₂e · printed {fmtDateTime(new Date().toISOString())}
  </div>
</header>
```
**File:** `src/styles.css` — near the print block add:
```css
.print-only {
  display: none;
}
@media print {
  .print-only {
    display: block;
    margin-bottom: var(--space-4);
    font-size: var(--fs-12);
  }
}
```
**Test:** BatchDetail test asserts full UUID present in document (it was previously only sliced).

## P4.4 Stamp print survival + Registry print cleanup (PR4, R8)
1. `src/components/SealedVerdict/SealedVerdict.module.css` append:
```css
@media print {
  .stamp {
    clip-path: none;
    border: 2px solid currentColor;
  }
}
```
2. `src/pages/Registry.tsx` — the generic `Form` component's `<Card as="form" …>`: add `className="no-print"` prop (Card passes className through — VERIFY by reading `src/ui/Card/Card.tsx` first; if it doesn't forward className → BLOCKED).
3. `src/styles.css` print block append:
```css
  .no-print {
    display: none !important;
  }
  .media-grid {
    grid-template-columns: repeat(2, 8cm);
    gap: var(--space-4);
  }
```
**Test:** registry test asserts form card has `no-print` class.

**PHASE 4 GATE:** `npm run verify` green.

---

# PHASE 5 — COMPONENT CONSOLIDATION (one extraction per task)

## P5.1 `ui/Field` (kills 13 duplicated label stacks; standardizes error grammar — L3/LE1 root)
Create `src/ui/Field/Field.tsx`:
```tsx
import { cloneElement, isValidElement, useId, type ReactElement, type ReactNode } from "react";
import styles from "./Field.module.css";

/**
 * The one label+control stack. Renders label (with required mark), the
 * control, an optional hint, and an optional error line wired to the
 * control via aria-describedby/aria-invalid. Audit P5.1.
 */
export default function Field({
  label,
  htmlFor,
  required = false,
  hint,
  error,
  children,
}: {
  label: ReactNode;
  htmlFor: string;
  required?: boolean;
  hint?: string;
  error?: string | null;
  children: ReactElement;
}) {
  const errId = useId();
  const control =
    error && isValidElement(children)
      ? cloneElement(children as ReactElement<Record<string, unknown>>, {
          "aria-invalid": true,
          "aria-describedby": errId,
        })
      : children;
  return (
    <div className={styles.field}>
      <label className="micro" htmlFor={htmlFor}>
        {label}
        {required && <span className={styles.required} aria-hidden> *</span>}
      </label>
      {control}
      {hint && !error && <span className={styles.hint}>{hint}</span>}
      {error && (
        <span id={errId} role="alert" className={styles.error}>
          {error}
        </span>
      )}
    </div>
  );
}
```
`Field.module.css`:
```css
.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.required {
  color: var(--status-error-fg);
}
.hint {
  font-size: var(--fs-12);
  color: var(--text-tertiary);
}
.error {
  font-size: var(--fs-12);
  color: var(--status-error-fg);
}
```
`Field.test.tsx`: renders label/required star/hint; error replaces hint, sets `role=alert`, child gets `aria-invalid` + matching `aria-describedby`.
**Migrations (each is its own commit; use anchor `display: "flex", flexDirection: "column", gap: 4`):** `Registry.tsx` (Form helper), `Dispatch.tsx` (3 fields), `pages/Projects/ProjectForm.tsx`, `pages/Projects/ParcelForm.tsx`, `Farmers.tsx` (search field), `Login.tsx` (2 fields), `LabEntry.tsx` (5 fields). Keep each page's behavior identical; only structure changes.
**DO NOT** migrate `FilterBar` (it deliberately has no visible labels until P7.2 decides).

## P5.2 `ui/CardError` (D5 + 4 page copies)
Create `src/ui/CardError/CardError.tsx`:
```tsx
import type { ReactNode } from "react";
import Card from "../Card/Card";
import Button from "../Button/Button";
import styles from "./CardError.module.css";

/** The one fetch-failure card: message + retry. Audit D5. */
export default function CardError({
  message,
  onRetry,
  children,
}: {
  message: ReactNode;
  onRetry?: () => void;
  children?: ReactNode;
}) {
  return (
    <Card className={styles.card}>
      <span className={styles.message}>{message}</span>
      {children}
      {onRetry && (
        <Button variant="neutral" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </Card>
  );
}
```
`CardError.module.css`:
```css
.card {
  border-color: var(--status-error-fg);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.message {
  color: var(--status-error-fg);
  font-size: var(--fs-13);
}
```
(READ `Card.tsx` first to confirm it merges `className` and `style`; if not → BLOCKED.)
**Migrate:** KpiRow, CreditsOverTime, IssuanceBlockerCard, PermanenceQualityCard, PyrolysisQualityCard, Batches, Farmers, Dispatch, Projects — anchor in each: `borderColor: "var(--status-error-fg)"`. Delete the whole inline-styled Card and replace with `<CardError message="…" onRetry={…} />` keeping the exact message strings.
**Test:** `CardError.test.tsx` (message + retry callback); all migrated tests stay green.

## P5.3 Button unification (X4)
1. Migrate remaining raw `className="primary"` / `className="neutral"` `<button>`s to `ui/Button`: search each string in `src/` tsx. Known sites: `EvidenceLightbox.tsx` (Prev/Next/Close), `ConfirmModal.tsx` (Cancel), `EmptyState.tsx` (action), `EvidenceGallery.tsx` verdict buttons use `styles.verdictBtn` — LEAVE those. For each migration preserve label, disabled, onClick, type.
2. When zero usages remain (`grep -rn 'className="primary"\|className="neutral"' src --include=*.tsx` → 0), delete from `styles.css`: the `button.primary {` rule + its `:hover` + `:disabled` rules, the `.neutral {` rule + `:hover` + `:disabled`, and the two dark-mode patch rules whose anchors are `[data-theme="dark"] button.primary` (both). DO NOT delete `.linkbtn` anything.
**Test:** migrated component tests updated (role/name queries unchanged — Button renders a `<button>`); snapshot refreshes.
**Guard:** if any page still references the deleted classes at runtime (grep again incl. `.ts` template strings), BLOCKED.

## P5.4 Status renderer unification (F2, P3, DP3, BD5)
1. `Farmers.tsx` KYC/Consent columns → `StatusDot`:
```tsx
const KYC_VARIANT = { verified: "success", pending: "warning" } as const;
const CONSENT_VARIANT = { signed: "success", revoked: "error" } as const;
// cell: f.kyc_status ? <StatusDot variant={KYC_VARIANT[f.kyc_status] ?? "inert"} label={f.kyc_status} /> : "—"
```
2. `Projects.tsx` status + boundary_status → StatusDot (`active/verified→success`, `draft/provisional→warning`, else inert).
3. `Dispatch.tsx` — humanize labels: anchor `label={d.status}` → `label={d.status === "in_transit" ? "In transit" : d.status === "received" ? "Received" : "Draft"}`.
4. `EvidenceGallery.tsx` + `EvidenceLightbox.tsx` chips → `StatusPill` with axis-distinct labels: `type verified` / `type unverified` (capture axis) and `review approved` / `review rejected` (reviewer axis). Remarks: remove from inside the pill; render below as `.micro` line clamped: new gallery-module class `.remarks { font-size: var(--fs-12); color: var(--status-error-fg); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }`.
5. After 1–4, `grep -rn '"chip' src --include=*.tsx` — if 0 usages of `.chip ok/warn/err` remain, delete the `.chip.ok`, `.chip.warn`, `.chip.err` rules from styles.css (keep bare `.chip` if still used; check).
**Test:** farmers test asserts `revoked` renders `data-variant="error"`; gallery test asserts pill labels.

## P5.5 Copy affordance + stat weight + dead code (B3, X10)
1. `Batches.tsx` — delete the local `CopyId` component (anchor `function CopyId`); in the Batch column cell use `components/CopyButton` (READ `CopyButton.tsx` first for its props: `value`, `label`). Wrap to stop row navigation: `<span onClick={(e) => e.stopPropagation()}><CopyButton value={b.batch_uuid} label="Copy batch id" /></span>`. Remove now-unused `Copy`/`Check` imports.
2. `src/components/StatTile/StatTile.module.css` — anchor `font-weight: var(--fw-bold);` → `font-weight: var(--fw-semibold);` (one voice with MetricBlock).
3. Delete folder `src/components/ActivityTimeline/` — but FIRST run `grep -rn "ActivityTimeline" src --include=*.tsx | grep -v components/ActivityTimeline` → must be 0 hits; else BLOCKED.
**Test:** Batches test green; repo grep confirms deletion.

## P5.6 `.section-title` (P5 headers)
`src/styles.css` — add after the `.page-title` rule:
```css
.section-title {
  font-size: var(--fs-16);
  font-weight: var(--fw-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--space-2);
}
```
Apply: `Projects.tsx` two `<h2 style={{ fontSize: 16, marginBottom: 8 }}>` → `<h2 className="section-title">`; `Dashboard.tsx` anchor `<h2 className="page-title" style={{ fontSize: "var(--fs-20)", marginTop: 32 }}>` → `<h2 className="section-title" style={{ marginTop: "var(--space-6)" }}>`.
**Test:** snapshot/text queries unchanged.

**PHASE 5 GATE:** `npm run verify` green.

---

# PHASE 6 — BATCHDETAIL FLAGSHIP

## P6.1 ISSUED verdict (BD2)
1. `src/components/SealedVerdict/SealedVerdict.tsx`:
   - type: `export type Verdict = "ISSUED" | "ISSUABLE" | "PROVISIONAL" | "BLOCKED";`
   - copy map add: `ISSUED: "Credit issued",`
   - icon: ISSUED uses the SAME check path as ISSUABLE — change condition to `{(verdict === "ISSUABLE" || verdict === "ISSUED") ? (` … `)}`.
2. `SealedVerdict.module.css` append:
```css
.stamp[data-verdict="ISSUED"] {
  color: var(--indigo-600);
  background: var(--indigo-600);
}
.stamp[data-verdict="ISSUED"]::before {
  background: var(--surface-brand-subtle);
}
[data-theme="dark"] .stamp[data-verdict="ISSUED"] {
  color: var(--indigo-400);
  background: var(--indigo-400);
}
```
3. `BatchDetail.tsx` — anchor `verdict={d.compliance.issuable ? "ISSUABLE" : "PROVISIONAL"}` →
`verdict={issued ? "ISSUED" : d.compliance.issuable ? "ISSUABLE" : "PROVISIONAL"}`
(the `issued` const already exists above). Then DELETE the chip line — anchor `<div className="seal">✓ CREDIT ISSUED</div>` — the `issued ? (…) : (…)` ternary becomes: `{!issued && getRole() === "admin" && ( <Button …issue button…/> )}`. Preserve the export-buttons block untouched.
4. `grep -rn '"seal"' src --include=*.tsx` → if 0, delete `.seal` rule from styles.css and its dark patch (anchor `[data-theme="dark"] .seal`).
**Test:** `SealedVerdict.test.tsx` add ISSUED case (`getByText("ISSUED")`, caption "Credit issued"); BatchDetail test: issued fixture → stamp says ISSUED, no "CREDIT ISSUED" text, no Issue button.

## P6.2 ConfirmModal gravity (CM2, CM3, CM4, BD7)
1. `ConfirmModal.tsx` — delete the `<CopyButton …/>` inside the label (anchor `label="Copy confirmation token"`) and the CopyButton import. Wrap the token: `<span className={`mono ${styles.token}`}>{confirmToken}</span>`.
2. `ConfirmModal.module.css` append `.token { user-select: none; }`; in `.content` rule add `border: var(--border-hair);`; replace all three `14px` margins with `var(--space-4)` (anchors `margin: 0 0 14px` ×2, `margin-bottom: 14px`).
3. `BatchDetail.tsx` — remove the `danger` prop from `<ConfirmModal` (anchor line contains just `danger`); remove the preview row `{ label: "Methodology", value: "—" },`.
**Test:** ConfirmModal test: no copy button in label; BatchDetail test: preview rows = 3. KEEP the `danger` prop/style in the component itself (other future callers) — only this call site drops it.

## P6.3 TemperatureChart geometry (BD10)
`TemperatureChart.tsx`:
1. Both `<svg` tags: add `preserveAspectRatio="none"`.
2. Y mapping — anchor `200 - ((t - lo) / (hi - lo)) * 200` → `192 - ((t - lo) / (hi - lo)) * 184` (pads 8px top/bottom).
3. Axis labels: all three `<text … className="micro">` → replace className with `fill="var(--text-tertiary)" fontSize="var(--fs-12)"`; adjust y anchors: `y="16"` stays, `y="104"` stays, `y="196"` stays.
**Test:** update `TemperatureChart.test.tsx`: for readings `[lo, hi]` polyline points' y ∈ [8, 192]; text nodes have `fill` attribute.

## P6.4 `.tiles` responsive (BD8)
`src/styles.css` — anchor `.tiles {` rule: replace `grid-template-columns: repeat(2, 1fr);` with `grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));` and add after the rule:
```css
@media (max-width: 720px) {
  .tiles {
    grid-template-columns: 1fr;
  }
}
```
**Test:** visual only — NOTES "visual check pending".

## P6.5 Evidence verdict lifecycle (BD3, BD4)
`EvidenceGallery.tsx`:
1. `EvidenceGallery` gains prop `locked?: boolean` (default false); `BatchDetail.tsx` passes `locked={d.batch.status === "ISSUED"}`.
2. `VerdictControls` gains `locked` + logic: `if (locked) return null;` and when `item.verification_status` is set render instead:
```tsx
<button type="button" className="linkbtn" onClick={() => setOverride(true)}>Change verdict</button>
```
(`override` local state; when true, show the Approve/Reject row again.)
3. Error feedback: wrap `approve` and `confirmReject` bodies' `await` in try/catch → `setErr("Save failed — retry")`; render `{err && <StatusPill status="error">{err}</StatusPill>}` in the verdict row; clear err on next attempt.
**Test:** gallery test: reviewed item shows "Change verdict" not Approve; `locked` hides all controls; mock `verifyMedia` rejection → error pill appears.

## P6.6 Lightbox states (LB1, LB2, LB4)
`EvidenceLightbox.tsx`:
1. Add `const [failed, setFailed] = useState(false);` reset alongside `setUrl(null)`; the fetch `.catch(() => live && setFailed(true))`.
2. Media area: `{url ? (…existing…) : failed ? (<span className={styles.unavailable}>Media unavailable</span>) : (<Skeleton variant="card" />)}` — import Skeleton.
3. Add to Content: `aria-keyshortcuts="ArrowLeft ArrowRight"`; under the actions row add `<span className="micro">← → to navigate</span>`.
4. Close button → `<Button variant="neutral">Close</Button>` (P5.3 may already have done this — verify, skip if done).
**Test:** lightbox test: pending fetch → skeleton present, no "Media unavailable"; rejected fetch → unavailable text.

## P6.7 Detail error/skeleton/anchor (BD12, BD13, BD6)
`BatchDetail.tsx`:
1. Import `ApiError` from `../api` (import-only — legal). In `reload()` catch: `if (e instanceof AuthError) nav("/login"); else if (e instanceof ApiError && e.status === 404) setErr("Batch not found."); else setErr("Couldn't load batch.");` Error JSX gains `<Button variant="neutral" size="sm" onClick={reload}>Retry</Button>` next to the back link.
2. Skeleton block: replace the four inline-styled divs with:
```tsx
<div className="wrap" style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
  <Skeleton variant="card" />
  <Skeleton variant="card" />
  <Skeleton variant="card" />
  <Skeleton variant="card" />
</div>
```
(import Skeleton).
3. Chain evidence anchor: in `chainNodes` the Evidence node's `sublabel` stays a string — instead add link at render site? SIMPLEST compliant change: wrap the `<VerificationChain…/>` in nothing; instead add below the SealedVerdict credit-label line: `<a className="link-indigo" style={{ fontSize: "var(--fs-13)" }} href="#evidence-media">Review evidence ↓</a>`.
**Test:** BatchDetail test: 500-mock shows "Couldn't load batch." + Retry; anchor href present on issuable batches.

**PHASE 6 GATE:** `npm run verify` green.

---

# PHASE 7 — PAGE TASKS (independent; parallel-safe EXCEPT styles.css edits)

## P7.1 Dashboard (D2, D3, D4, D6, D7, D8)
1. **KpiRow zero-vocabulary (D2):** provisional-credit tile mirrors the issued logic:
```tsx
const noProvisional = totals.provisional_count === 0;
<StatTile label="Provisional credit (tCO₂e)" value={noProvisional ? "—" : fmtCredit(totals.provisional_credit_t_co2e)} hint={noProvisional ? "none in pipeline" : undefined} />
```
2. **Blocker empty honesty (D3):** `IssuanceBlockerCard` gains prop `provisionalCount: number | null` (Dashboard already fetches summary → pass `summary.provisional`; thread through existing `reasons` fetch state — READ Dashboard.tsx: `fetchReasons` stores only `reasons_histogram`; change it to store the whole summary object and pass both down). Empty branch: `provisionalCount === 0` → title "No provisional batches yet"; `provisionalCount > 0 && reasons empty` → "No blockers recorded — check batch details".
3. **Quality-card whitespace (D4):** create `PyrolysisQualityCard.module.css` + `PermanenceQualityCard.module.css` each with:
```css
.statRow {
  display: grid;
  grid-template-columns: repeat(2, minmax(180px, 240px));
  gap: var(--space-3);
}
```
Replace their `<StatBand>` usage with `<div className={styles.statRow}>` (KEEP StatBand for KpiRow — it's correct there at 4-up).
4. **Chart empty state (D6):** in `DivergingStackedBarChart` locate the empty branch (anchor `emptyLabel`) → render `<EmptyState title={emptyLabel} />` instead of bare text (import path `../../components/EmptyState/EmptyState`).
5. **Toggle into card header (D8):** `CreditsOverTime.tsx` — card header becomes flex row (`display:flex; justify-content:space-between; align-items:center` via a small module class or inline var-only style); it renders the micro-label + `<BucketToggle …/>` (new props: `bucket`, `onBucket` passed from Dashboard). Delete the floating toggle row in `Dashboard.tsx` (anchor `justifyContent: "flex-end"`).
6. **Stale comment (D7):** delete the sentence starting `v1 is month-only` in CreditsOverTime.tsx.
**Test:** KpiRow test (— + hint at zero); blocker-card test (both empty messages); CreditsOverTime test (toggle rendered inside card); chart test (EmptyState used).

## P7.2 Batches (B2, B4, B6, B7)
1. StatBand always rendered: replace `{summary && (<StatBand>…)}` with tiles that render `value={summary ? String(…) : "—"}`.
2. DELETE the page-scoped "Credit" tile (4th tile) and its `rows.reduce` — misleading (audit B4).
3. `FilterBar.tsx` option labels → `Received` / `Issued` (values unchanged: `RECEIVED`, `ISSUED`).
4. Blockers pill text: anchor `` {b.reason_count} reason{b.reason_count === 1 ? "" : "s"} `` → `` {b.reason_count} blocker{b.reason_count === 1 ? "" : "s"} ``.
**Test:** batches test: 3 tiles, `—` before summary resolves, "blocker" text.

## P7.3 Farmers (F1, F3, F4, F6)
1. Scroll-into-view: `const detailRef = useRef<HTMLElement>(null);` on the detail Card (`as="section"` supports ref? READ Card.tsx — if it doesn't forward refs, wrap in a plain `<section ref>` around the Card); `useEffect(() => { if (selected) detailRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [selected]);`
2. `openDetail` catch: non-auth → `setErr("Couldn't load farmer detail.")` (renders in existing CardError).
3. `detailLoading` → `<Skeleton variant="card" />` (import).
4. Mono masks: wrap `••••{d.last4}` and `{p.masked_account ?? p.masked_upi_id ?? p.masked_mfs_id ?? "—"}` in `<span className="mono">`.
**Test:** farmers test: scrollIntoView mock called on select; skeleton while loading; `.mono` present on mask.

## P7.4 Dispatch (DP1, DP2, DP4)
1. Role-gate + relocate + disclosure: facility form Card renders only for `getRole() === "admin"`, MOVED to below the pager, collapsed behind:
```tsx
const [showFacilityForm, setShowFacilityForm] = useState(false);
{getRole() === "admin" && (
  <div style={{ marginTop: "var(--space-5)" }}>
    <Button variant="neutral" size="sm" onClick={() => setShowFacilityForm((s) => !s)}>
      {showFacilityForm ? "Hide facility form" : "Register facility…"}
    </Button>
    {showFacilityForm && ( …existing Card… )}
  </div>
)}
```
Import `getRole` from `../auth`.
2. Weights cell delta: anchor the weights render → append `{d.weight_delta_pct != null && !d.weight_flagged && (<span className="micro"> ({d.weight_delta_pct > 0 ? "+" : ""}{fmtPct(d.weight_delta_pct)})</span>)}` (flagged rows keep pill-only).
3. Facility count line moves inside the disclosure block.
**Test:** dispatch test with mocked `getRole`: verifier → no button/form; admin → disclosure toggles; delta text on unflagged row with non-null pct.

## P7.5 Projects (P1, P4, P5, P6)
1. Same disclosure+role-gate pattern as P7.4 for ProjectForm and ParcelForm ("New project…", "New parcel…"); move BELOW the two tables.
2. Anchor `.slice(0, 8) + "..."` → `` .slice(0, 8) + "…" ``.
3. Sentence-case sweep in this file + ProjectForm/ParcelForm: "Registered projects", "Source parcels", "Parcel name", "Declared acres (optional)", "Select project", "— choose project —", "Register source parcel boundary".
4. Area cell: `` render: (p) => p.area_m2.toLocaleString() `` (header keeps `(m²)`).
**Test:** projects test updated for gating + case + area cell.

## P7.6 Registry (R1–R7)
1. **Role-gate the page's admin surfaces:** wrap the THREE tab-content Forms + mint Card in `getRole() === "admin"`. Verifier keeps: tabs, kiln cards, and a NEW read-only kiln DataTable (columns: Kiln ID mono · Type · Material `?? "—"` · Weight right-aligned `fmtKg` `?? "—"`). Import DataTable.
2. **Mint busy + errors (R2):** `const [minting, setMinting] = useState(false);` button label `minting ? "Minting…" : "Mint enrollment token"`, disabled while minting; catch non-auth → `setMintErr("Mint failed — try again.")` rendered as `<StatusPill status="error">`.
3. **Persistent form status (R3):** in the generic `Form` — DELETE the auto-dismiss `useEffect` (anchor `setTimeout(() => setMsg(null), 4000)`); message clears on next submit only. SAME deletion in `Dispatch.tsx` and `Projects.tsx` (anchors identical).
4. **Kiln type select (R6):** replace the `kiln_type` text Field with a select of options: `—` (value "") / `Open` (value "open") / `Closed` (value "closed"). The generic Form's field def gains optional `options?: {label: string; value: string}[]` rendering a `<select>` when present.
5. Required marks come free via Field (P5.1). Token well: remove inline `fontSize: 12` (anchor `fontSize: 12, wordBreak`) — keep `wordBreak` as class `.mono` covers size.
6. `styles.css` print block: `.cap { white-space: normal; }` inside `@media print`.
**Test:** registry test: mocked verifier → no forms, kiln table renders; mint rejection → error pill; kiln type renders select with 3 options; form msg persists (no fake timers needed once setTimeout is gone).

## P7.7 Lab pages (LE1–LE6)
1. **Per-field errors (LE1):** READ `src/lab.ts` `validateLabForm` FIRST and list its exact error strings. Build in `LabEntry.tsx`:
```ts
function fieldOf(err: string): keyof LabForm | null {
  if (/H:Corg/i.test(err)) return "lab_h_corg";
  if (/carbon/i.test(err)) return "organic_carbon_pct";
  if (/moisture/i.test(err)) return "biochar_moisture_samples";
  if (/density/i.test(err)) return "dry_bulk_density";
  return null;
}
```
(ADJUST the regexes to the actual strings you read; report them in NOTES.) Route matched errors to each `Field error=` prop; unmatched → banner list above submit (moved from below — L5 fix pattern). Submit-failure message also goes to the banner.
2. **Batch context card (LE3):** on mount `getBatch(uuid)` → tiny Card above the form: `<span className="mono">{uuid.slice(0, 8)}</span> · {batch.feedstock? — NOT IN BatchRow; use device_id and fmtDate(received_at)}`. EXACT content: `{shortId} · device {device_id ?? "—"} · received {fmtDate(received_at)}`. On ApiError 404 → `<StatusPill status="warning">Unknown batch — check the code</StatusPill>` and DO NOT block the form.
3. **H1 mono (LE2):** `Lab results · <span className="mono">{uuid.slice(0, 8)}</span>`.
4. **Placeholder → hint (LE4):** remove `placeholder="8, 9, 10"`; Field hint `Comma-separated, e.g. 8, 9, 10`.
5. **File input (LE6):** hidden input + `<Button variant="neutral" size="sm" onClick={() => fileRef.current?.click()}>Choose PDF…</Button>`; chosen name echoes beside (already shown in aside pill — keep).
6. **LabScan reticle (LE5):** 4× anchor `3px solid rgba(255,255,255,0.9)` → `3px solid var(--scan-reticle)`.
**Test:** LabEntry test: invalid H:Corg → error under that field with role=alert; context card text; 404 warning pill; LabScan snapshot.

**PHASE 7 GATE:** `npm run verify` green.

---

# PHASE 8 — POLISH + GUARDRAILS (strictly last)

## P8.1 Z-index final sweep (X6) — EXACT assignments, no judgment calls:
| File · rule | New value |
|---|---|
| `ConfirmModal.module.css` `.overlay` | `var(--z-overlay)` |
| `ConfirmModal.module.css` `.content` | `var(--z-modal)` |
| `EvidenceLightbox.module.css` `.overlay` | `var(--z-overlay)` |
| `EvidenceLightbox.module.css` `.content` | `var(--z-modal)` |
| `styles.css` `.modal-overlay` | `var(--z-overlay)` |
| `DataTable.module.css` `.stickyHead th` (currently 5) | `1` (must sit under topbar; plain content-local stacking) |
| `DivergingStackedBarChart.module.css` tooltip (currently 10) | `var(--z-tooltip)` |
| `InfoTip.module.css` bubble (currently 30) | `var(--z-tooltip)` |
| `SealedVerdict.module.css` `::before` `-1` | leave as is |

## P8.2 Motion unification (X7)
1. `tokens.css`: convert legacy names to aliases — anchor `--duration-fast: 150ms;` → `--duration-fast: var(--dur-micro);`, `--duration-standard: 250ms;` → `--duration-standard: var(--dur-trans);`, `--ease-productive: cubic-bezier(0.2, 0, 0, 1);` → `--ease-productive: var(--ease-out);`, `--ease-expressive: cubic-bezier(0.4, 0, 0.2, 1);` → `--ease-expressive: var(--ease-out);`.
2. `Button.module.css`: `animation: spin 0.6s linear infinite` → `animation: spin var(--dur-spin) linear infinite`; delete the reduced-motion `1.5s` override block (global kill-switch covers it).
3. `Skeleton.module.css` + `styles.css` pulse: `1.5s` → `var(--dur-pulse)`.
**Test:** tokens.test.ts asserts no raw `0.6s`/`1.5s` in css outside tokens.css.

## P8.3 Selection, scrollbar, glyph strays (X11, parts of G)
`styles.css` additions:
```css
::selection {
  background: var(--indigo-200);
  color: var(--basalt-950);
}
[data-theme="dark"] ::selection {
  background: var(--indigo-900);
  color: var(--basalt-0);
}
[data-theme="dark"] {
  scrollbar-color: var(--basalt-600) transparent;
}
```
`EvidenceGallery.tsx`: replace the inline `<svg …>` fallback icon with `<ImageOff size={16} aria-hidden />` (lucide import); keep the "Preview unavailable" label.
`EvidenceGallery.tsx` + `EvidenceLightbox.tsx`: `"no GPS"` → `"—"`.
**Test:** gallery test: `—` for missing GPS.

## P8.4 Touch targets (X9)
- `AppShell.module.css` `.iconBtn` width/height `32px` → `var(--control-h-md)`.
- `components/CopyButton/CopyButton.tsx` + `InfoTip` trigger: ensure classes give `min-width/min-height: 28px` + grid-center (module additions; icon sizes unchanged).
- `Login.tsx` password toggle: replace inline positioning styles with a Login-local module? Login has no module — create `src/pages/Login.module.css` with `.pwToggle { position: absolute; right: var(--space-1); top: 50%; transform: translateY(-50%); display: grid; place-items: center; width: 32px; height: 32px; }` and use it.
**Test:** snapshot refreshes.

## P8.5 Spacing sweep (X5) — LAST code task; one file per commit, in this order:
`ConfirmModal.module.css` → `SealedVerdict.module.css` → `VerificationChain.module.css` → `AppShell.module.css` → `ComplianceChecklist.module.css` → `EvidenceGallery.module.css` → `EvidenceLightbox.module.css` → `EmptyState.module.css` → `styles.css` → inline TSX offenders (`marginTop: 14` ×13 → `"var(--space-4)"`, `marginTop: 10` ×10 → `"var(--space-3)"`, `marginBottom: 14` same).
Apply Global Rule 8 mapping mechanically. THEN add the permanent guard `src/tokens/no-raw-values.test.ts`:
```ts
// Walks src/**/*.module.css + styles.css: fails on
//  (padding|margin|gap):[^;]*\b(2|6|9|10|14|18|20|28|40|60)px
//  and on #[0-9a-f]{3,8}\b outside tokens.css
// Allowlist (regex-excluded): data:image/svg URIs, Logo.module.css
```
Implement with fs walk; every regex hit prints file+line in the failure message.

## P8.6 FINAL ACCEPTANCE (definition of "everything fixed")
1. §0.5 manifest: every box ticked, each with a done report.
2. `npm run verify` fully green.
3. `grep -rn 'className="primary"\|className="neutral"' src --include=*.tsx` → 0. `grep -rn '"\.\.\."' src/pages` → 0. `grep -rn "slice(0, 10)" src/pages src/components` → 0.
4. Re-run captures: `node audit/capture.mjs base && node audit/capture.mjs states` (dev server must be started for this step only). Visually confirm, in BOTH themes: batches status column legible (dark), verdict stamp legible (dark), topbar icons far right, ISSUED stamp on issued batch, modal has border + ember confirm, print-emulated shows images + section titles + header.
5. Write `portal/audit/REMEDIATION_RESULT.md`: manifest table with per-task status, the 5 grep outputs, and before/after screenshot pairs for the 6 key screens.

---

# DEPENDENCY GRAPH
```
P1 → P2 → P3 → P4
P5.1, P5.2 → P7.* (pages consume Field/CardError)
P5.3 → P6.2, P6.6 (button swaps)
P1 + P3 → P6.*
P7 tasks: parallel-safe, EXCEPT any task editing styles.css (serialize: P7.6 → others)
P8 strictly last (its guard test would fail mid-migration states)
```
