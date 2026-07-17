# PORTAL REDESIGN PROMPT — "Forensic Serenity" execution plan (portal ONLY)

> Copy everything below the line into the agent. Repo root:
> `c:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`. Node + npm
> installed. The agent must do the phases IN ORDER, ONE AT A TIME, and STOP
> when a CHECK fails. This is a FRONTEND-ONLY task: every file you touch
> lives under `portal/` — you must NOT modify anything in `backend/`, `lib/`,
> or any other directory.

---

You are executing an approved design specification ("Forensic Serenity") on
the TerraCipher Verifier Portal — a React 18 + Vite + TypeScript web app in
`portal/`. It is the back-office where verifiers review cryptographically
signed biochar evidence and admins permanently issue carbon credits. The
design goal: stop looking like a consumer demo; look like a financial-grade
audit instrument. Trust ONLY the source code, not .md docs.

## THE DESIGN THESIS (context, not instructions)

- Brand and status colors are currently in collision: 4 different greens, a
  meaningless sky-blue, and 2 mismatched indigos. The fix: **indigo becomes
  the only brand accent; green becomes strictly semantic** (= verified/
  issuable), amber = provisional, red = error.
- Current `--emerald #0f9d63` (3.5:1) and `--faint #96a0ad` (2.3:1) FAIL
  WCAG AA on white. Every replacement color below passes ≥4.5:1 for text.
- Typography moves from system stack to self-hosted **Inter** (UI) +
  **IBM Plex Mono** (hashes/UUIDs/tokens = "forensic" material).
- Radii shrink (4/6/8px, kill 20px and pills→4px), spacing goes 8-pt grid,
  motion gets a 150/250ms system, `window.confirm` on issuance is replaced
  by a type-to-confirm modal, and evidence thumbnails become forensic tiles
  (photo + hash in mono + GPS + timestamp + verified badge) that keep their
  metadata visible even when the image blob is dead.

## LOGIC FREEZE — the most important rule in this document

This is a PRESENTATION-ONLY redesign. The portal's behavior, data flow, and
security posture must be byte-for-byte equivalent after every phase:

- **Never change any API call**: same endpoints, same methods, same headers,
  same payloads, same response handling. `api.ts` may ONLY gain the two
  optional type fields named in Phase 2a — no function bodies change.
- **Never change auth, routing, or guards**: `auth.ts`, `RequireAuth`, route
  paths, `AuthError → nav("/login")` bounces all stay exactly as they are.
- **Never change data logic**: `groupMedia`, `groupChecklist`, `statusOf`,
  `validateLabForm`, QR parsing (`qr.ts`, `lab.ts`), pagination/cursor
  logic, filter state — untouched. If a phase needs a display name for a
  value, ADD a lookup map; never transform the underlying data.
- **Never weaken a safeguard**: the issuance modal in Phase 2d REPLACES
  `window.confirm` with a STRICTER confirmation (typed "ISSUE") — the
  `issueCredit(uuid)` call itself, its error handling, and the
  admin-role + issuable gating around it must remain identical. That is
  the ONLY behavioral substitution in this entire document, and it only
  swaps the confirmation surface, not what is confirmed or who can do it.
- Allowed additions are strictly cosmetic side-effects: `document.title`,
  clipboard-copy buttons, auto-clearing feedback chips, skeletons while
  the EXISTING fetches run. None of these may alter when or how data is
  fetched or submitted.
- Litmus test before every edit: "if I diff the network traffic and the
  data rendered before vs after, is it identical?" If not, STOP — you are
  out of scope.

## GLOBAL RULES — apply to every phase

1. **One phase at a time.** Finish phase N (code + checks green + commit)
   before you even READ phase N+1.
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
   `portal/`. Do NOT push.
5. No new runtime UI libraries. The ONLY permitted new dependencies are the
   two font packages in Phase 1 (`@fontsource-variable/inter`,
   `@fontsource/ibm-plex-mono`) — they bundle font files locally via Vite,
   no CDN at runtime.
6. Existing tests import `groupMedia` from `pages/BatchDetail.tsx` and
   render `ComplianceChecklist` (see `portal/src/__tests__/`). Keep every
   existing export and `data-testid` intact.
7. **Token migration strategy (critical):** Phase 1 REDEFINES the existing
   custom-property names (`--emerald`, `--amber`, `--faint`, etc.) to the
   new values and ADDS the new semantic tokens alongside. Old names keep
   working as aliases so nothing breaks mid-migration; they are deleted only
   in the final phase after every reference is migrated. Never delete a
   token name while `grep -r "var(--name)" src/` still returns hits.
8. Line numbers cited below may have drifted — locate the verbatim code
   shown before editing. If a verbatim block cannot be found, STOP and
   report; do not guess.

---

<!-- PHASE0 -->
# PHASE 0 — baseline

```bash
cd "c:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv/portal"
npm test                # record the passing test count — this is your gate
npm run typecheck
npm run build
git log --oneline -3    # record the start commit
```
No commit. STOP if anything fails — report and wait.

<!-- PHASE1 -->
# PHASE 1 — foundation: tokens, fonts, type scale, motion, focus

**Files:** `portal/package.json` (+lockfile), `portal/src/main.tsx`,
`portal/src/styles.css`, `portal/index.html`.

## 1a — fonts

```bash
npm install @fontsource-variable/inter @fontsource/ibm-plex-mono
```

At the TOP of `portal/src/main.tsx` (before other imports):

```ts
import "@fontsource-variable/inter";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
```

## 1b — replace the ENTIRE `:root` block in `styles.css`

The current file opens with `:root {` containing `--bg: #eef1f6;` …
`--shadow-lg`. Replace that whole block with:

```css
:root {
  /* ── primitives: Basalt neutral scale ─────────────────────────── */
  --basalt-50:  #f4f5f6;
  --basalt-100: #e5e7eb;
  --basalt-300: #d1d5db;
  --basalt-500: #6a6e7d;   /* 5.07:1 on white — AA pass */
  --basalt-700: #4a4e5a;   /* 8.31:1 */
  --basalt-950: #0f1115;   /* 18.9:1 */
  /* ── primitives: brand + semantic hues ────────────────────────── */
  --indigo-600: #3b32b3;   /* THE brand accent. 9.16:1 */
  --indigo-50:  #f5f4ff;
  --green-700:  #0b663e;   /* semantic "verified/issuable" ONLY. 7.04:1 */
  --green-50:   #f0faf5;
  --amber-700:  #9e4200;   /* "provisional/missing". 6.50:1 */
  --amber-50:   #fef6ee;
  --red-700:    #b91c1c;   /* errors. 6.47:1 */
  --red-50:     #fef2f2;
  /* ── semantic layer ───────────────────────────────────────────── */
  --surface-page: var(--basalt-50);
  --surface-card: #ffffff;
  --surface-brand-subtle: var(--indigo-50);
  --border-subtle: var(--basalt-100);
  --border-strong: var(--basalt-300);
  --text-primary: var(--basalt-950);
  --text-secondary: var(--basalt-700);
  --text-tertiary: var(--basalt-500);
  --status-success-fg: var(--green-700);
  --status-success-bg: var(--green-50);
  --status-warning-fg: var(--amber-700);
  --status-warning-bg: var(--amber-50);
  --status-error-fg: var(--red-700);
  --status-error-bg: var(--red-50);
  --action-primary-bg: var(--basalt-950);
  --action-primary-hover: var(--basalt-700);
  /* ── shape / elevation / motion ───────────────────────────────── */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --shadow-sm: 0 1px 2px rgba(15, 17, 21, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(15, 17, 21, 0.1),
               0 2px 4px -1px rgba(15, 17, 21, 0.06);
  --duration-fast: 150ms;
  --duration-standard: 250ms;
  --ease-productive: cubic-bezier(0.2, 0, 0, 1);
  --ease-expressive: cubic-bezier(0.4, 0, 0.2, 1);
  /* ── legacy aliases (DELETE in the final phase, keep until then) ─ */
  --bg: var(--surface-page);
  --card: var(--surface-card);
  --ink: var(--text-primary);
  --muted: var(--text-secondary);
  --faint: var(--text-tertiary);
  --line: var(--border-subtle);
  --emerald: var(--status-success-fg);
  --emerald-d: var(--status-success-fg);
  --emerald-bg: var(--status-success-bg);
  --amber: var(--status-warning-fg);
  --amber-bg: var(--status-warning-bg);
  --red: var(--status-error-fg);
  --indigo: var(--indigo-600);
  --shadow: var(--shadow-sm);
  --shadow-lg: var(--shadow-md);
}
```

Because the aliases remap old names to new values, every existing
`var(--emerald)` etc. (including the DOT map in
`components/ComplianceChecklist.tsx`) instantly renders in the new,
AA-compliant colors with zero component edits in this phase.

## 1c — typography + global polish in `styles.css`

1. In the `body` rule: replace the `font-family` line with
   `font-family: "Inter Variable", -apple-system, "Segoe UI", sans-serif;`
   and DELETE the entire `background-image: radial-gradient(...)` decoration
   (both radial gradients — the atmosphere is killed).
2. Add after the body rule:
   ```css
   code, .mono {
     font-family: "IBM Plex Mono", ui-monospace, monospace;
     font-size: 12px;
   }
   :focus-visible {
     outline: 2px solid var(--indigo-600);
     outline-offset: 2px;
     border-radius: inherit;
   }
   ```
3. Restyle `.micro` in place (same class name, new voice — do NOT rename;
   it is used in every screen): `font-size: 12px; font-weight: 500;
   letter-spacing: 0.01em; text-transform: none; color: var(--text-tertiary);`
   (uppercase micro-labels are killed for legibility).
4. `.top`: remove `backdrop-filter` and the rgba background; set
   `background: var(--surface-card);` (solid white, 1px border stays).
5. `.mark`: replace the green→sky gradient with
   `background: var(--indigo-600);` (solid).
6. `.card`: `border-radius: var(--radius-lg);`
7. `button.primary`: `border-radius: var(--radius-md); background:
   var(--action-primary-bg); transition: background var(--duration-fast)
   var(--ease-expressive);` and add
   `button.primary:hover:not(:disabled) { background: var(--action-primary-hover); }`
8. `input`, `select`: `border-radius: var(--radius-md);` border color
   `var(--border-subtle)`, and add
   `input:focus, select:focus { border-color: var(--border-strong); outline: none; }`
   (the `:focus-visible` rule still covers keyboard nav).
9. `.badge`: `border-radius: var(--radius-sm); font-weight: 500;
   font-size: 12px;` (pills → 4px chips).
10. `.hero`: `border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);`
11. `.credit .num`: DELETE the gradient text-clip block
    (`background: linear-gradient…; -webkit-background-clip…;
    -webkit-text-fill-color…`) and set `font-size: 48px; font-weight: 600;
    letter-spacing: -0.02em; color: var(--text-primary);`
12. `.seal`: `background: var(--surface-brand-subtle); color:
    var(--indigo-600); border-radius: var(--radius-sm);`
13. `tbody tr:hover`: `background: var(--surface-page);` and on `tbody tr`
    add `transition: background var(--duration-fast) var(--ease-expressive);`
14. Table header `th`: `text-transform: none; letter-spacing: 0.01em;
    font-size: 12px; font-weight: 500; color: var(--text-tertiary);`
15. Table radius: `var(--radius-lg)`.

## 1d — CreditRing gradient → solid

In `portal/src/components/CreditRing.tsx`: delete the `<defs>` block with
`ringgrad` (`#12b981`/`#0ea5e9`). In `styles.css`, `.ring .fill`:
`stroke: var(--status-success-fg);` (solid semantic green — % criteria met
is a STATUS, not brand).

## 1e — index.html

Set `<meta name="theme-color" content="#0f1115" />` and add a favicon: an
inline SVG data-URI link (`<link rel="icon" href="data:image/svg+xml,...">`)
rendering a `#3b32b3` rounded square with white "TC" — keep it a one-liner.

**CHECKS:** the three gate commands. Also
`grep -c "0ea5e9\|12b981\|radial-gradient" src/styles.css` must return 0.

**Commit:** `feat(portal): forensic-serenity token architecture, Inter/Plex Mono, focus + motion`

<!-- PHASE2 -->
# PHASE 2 — Batch Detail: forensic evidence tiles + issuance modal

**Files:** `portal/src/api.ts`, `portal/src/pages/BatchDetail.tsx`,
`portal/src/styles.css`, extend `portal/src/__tests__/api.test.ts`.

## 2a — surface the GPS fields the API already sends

The backend media projection already returns `exif_lat`/`exif_lon`
(verified: `backend/portal/routes.py` batch_detail — DO NOT touch that
file). The frontend type just doesn't declare them. In `portal/src/api.ts`
extend `MediaItem` (additive only):

```ts
  exif_lat: number | null;
  exif_lon: number | null;
```

## 2b — human-readable step titles

In `BatchDetail.tsx`, next to the existing `STEP_ORDER`, add and EXPORT:

```ts
export const STEP_TITLES: Record<string, string> = {
  batch_photo: "Batch photo",
  flame_curtain: "Burn — flame curtain",
  quenching: "Burn — quenching",
  flame_height: "Burn — flame height",
  smoke_0: "Smoke opacity — 0%", "0": "Smoke opacity — 0%",
  smoke_50: "Smoke opacity — 50%", "50": "Smoke opacity — 50%",
  smoke_90: "Smoke opacity — 90%", "90": "Smoke opacity — 90%",
  smoke_100: "Smoke opacity — 100%", "100": "Smoke opacity — 100%",
  lab_certificate: "Lab certificate",
};
```

Title resolution: `STEP_TITLES[key] ?? (key === "__unclassified__"
? "Unclassified" : key)`. Do NOT change `groupMedia` — it has a passing test.

## 2c — the forensic tile (replace `MediaThumb`'s render)

Keep the component name, props, and blob-fetch logic. New render:

- Image area (90px): the photo; while loading, a `.skeleton` block; on
  failure, a `--surface-page` well with a small inline slashed-camera SVG
  (draw it inline, ~16×16, `stroke="currentColor"`, color
  `var(--text-tertiary)`) — NOT the word "unavailable". The metadata below
  stays fully visible either way (a dead blob does not break the chain of
  custody).
- Metadata block (below the image, padding 8px, 11–12px sizes):
  1. hash row: `<span className="mono">{item.sha256_hash.slice(0, 12)}…</span>`
     plus a copy button (`navigator.clipboard.writeText(item.sha256_hash)`,
     `aria-label="Copy SHA-256"`, ghost style, shows "✓" for 1.5s after copy).
  2. timestamp row (when `uploaded_at`):
     `item.uploaded_at.slice(0, 16).replace("T", " ")` in `--text-tertiary`.
  3. GPS row: when both coords present —
     `{item.exif_lat.toFixed(5)}, {item.exif_lon.toFixed(5)}` as an `<a>` to
     `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=17/${lat}/${lon}`
     (`target="_blank" rel="noreferrer"`); else muted text `no GPS`.
  4. verification badge: `capture_type_verified` → green chip `✓ verified`
     (`--status-success-fg` on `--status-success-bg`); a non-null,
     unverified `capture_type` → amber chip `unverified`; unclassified →
     no chip.
- Replace the gallery's inline-styled group boxes (`border: '1px solid
  #ddd'`, `color: '#888'`, dead Tailwind classes `space-y-6`,
  `bg-gray-50`, `font-semibold text-lg mb-4 capitalize`) with classes:
  `.evidence-group` (background `--surface-page`, `--radius-md`, 12px
  padding, 12px bottom margin) and `.evidence-group-head` (flex; title from
  STEP_TITLES in `.micro`-style 12px/500 `--text-secondary`; item-count
  chip right-aligned). Add both classes plus `.forensic-meta`, `.chip`,
  `.chip.ok`, `.chip.warn` to `styles.css`. NO hardcoded hex anywhere.

## 2d — type-to-confirm issuance modal (kill `window.confirm`)

In `BatchDetail.tsx`, the current `issue()` wraps the POST in
`window.confirm(...)`. Replace with modal state:

- `const [confirmOpen, setConfirmOpen] = useState(false)` and
  `const [confirmText, setConfirmText] = useState("")`. "Issue credit"
  button → `setConfirmOpen(true)`.
- Modal: fixed overlay `rgba(15, 17, 21, 0.4)` covering the viewport,
  centered 420px `--surface-card` panel, `--radius-lg`, `--shadow-md`,
  entering with `--duration-standard var(--ease-productive)` (single
  `@keyframes` fade/translate). `role="dialog" aria-modal="true"`; Escape
  closes; overlay click closes.
- Content: heading "Issue credit — permanent"; body text: `You are about to
  permanently issue {d.batch.net_credit_t_co2e.toFixed(2)} tCO₂e to batch
  {d.batch.batch_uuid.slice(0, 8)}. This writes to the permanent ledger and
  cannot be undone.`; a labeled input "Type ISSUE to confirm"; buttons
  [Cancel] (ghost) and [Issue permanently] (primary, `disabled={confirmText
  !== "ISSUE" || issuing}`) which calls the existing `issueCredit(uuid)`
  path, then closes and reloads.
- Also give the two export buttons the `.neutral` ghost style — the class
  is used in JSX today but NOT defined in styles.css (they currently render
  as browser-default buttons). Define `.neutral` in `styles.css`:
  transparent bg, `1px solid var(--border-subtle)`, `--text-primary`,
  `--radius-md`, same hover transition as primary.

## 2e — tests (extend `portal/src/__tests__/api.test.ts` only)

- `STEP_TITLES` maps `"0"` → `"Smoke opacity — 0%"` and `flame_curtain` →
  `"Burn — flame curtain"` (import from `../pages/BatchDetail`).
- `groupMedia` existing test must still pass UNCHANGED.
- Note: `MediaItem` gained two required fields — if any test builds
  MediaItem literals, add `exif_lat: null, exif_lon: null` to those
  literals; that is the ONLY permitted edit to existing test code.

**CHECKS:** the three gate commands. Also
`grep -n "window.confirm" src/pages/BatchDetail.tsx` must return nothing,
and `grep -n "#ddd\|#888" src/pages/BatchDetail.tsx` must return nothing.

**Commit:** `feat(portal): forensic evidence tiles + type-to-confirm issuance modal`

<!-- PHASE3 -->
# PHASE 3 — component states: skeletons, empty states, feedback

**Files:** `portal/src/styles.css`, `portal/src/pages/Batches.tsx`,
`portal/src/pages/BatchDetail.tsx`, `portal/src/pages/Registry.tsx`.

## 3a — skeleton system (`styles.css`)

```css
.skeleton {
  background: var(--basalt-100);
  border-radius: var(--radius-sm);
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: .5; } 100% { opacity: 1; } }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important; }
}
```

- `Batches.tsx`: while `loading && rows.length === 0`, render 5 table rows
  of `.skeleton` cell blocks (heights ~14px) instead of an empty table.
- `BatchDetail.tsx`: replace the bare `Loading…` return with a skeleton
  page: one hero-shaped block (~180px) + three tile blocks + two list
  blocks, inside `.wrap`.

## 3b — empty + error states

- `Batches.tsx` empty state (replaces the "No batches." row): a centered
  block inside the table area — 18px/600 "No batches found" +
  13px `--text-secondary` "Adjust the filters above, or wait for field
  devices to sync." No icon dependency — text only is fine.
- `BatchDetail.tsx` error: "Batch not found" as 18px/600 + a "← All
  batches" link back.

## 3c — save feedback on Registry

In `Registry.tsx`'s `Form` helper, the current feedback is a micro line
"Saved." / "Save failed.". Upgrade: success renders
`<div className="chip ok">✓ Saved</div>`, failure
`<div className="chip err">Save failed — check values</div>` (add
`.chip.err` = red pair to styles.css). Auto-clear after 4s (`setTimeout` in
the submit handler, cleared on unmount).

**CHECKS:** the three gate commands.

**Commit:** `feat(portal): skeleton loading, designed empty/error states, save feedback chips`

<!-- PHASE4 -->
# PHASE 4 — screen sweep: top bar, login, tables, lab, registry + print

**Files:** `portal/src/App.tsx`, `portal/src/pages/Login.tsx`,
`portal/src/pages/Batches.tsx`, `portal/src/pages/LabScan.tsx`,
`portal/src/pages/LabEntry.tsx`, `portal/src/pages/Registry.tsx`,
`portal/src/styles.css`, `portal/index.html`.

## 4a — top bar (`App.tsx` + css)

- Wordmark: `TerraCipher <span>| Verifier Portal</span>` (pipe, suffix
  stays muted).
- Nav buttons (`.linkbtn`): restyle as ghost buttons — padding 6px 12px,
  `--radius-md`, hover `background: var(--surface-page)` with the fast
  transition. Active route (compare `useLocation().pathname`): 2px
  `--indigo-600` underline via `box-shadow: inset 0 -2px 0 var(--indigo-600)`
  or a border — pick one, apply consistently.

## 4b — login (`Login.tsx`)

- h1 → "Sign in to TerraCipher"; delete the micro subtitle.
- Placeholder-only inputs become labeled: `<label className="micro"
  htmlFor="email">Email</label>` + `id="email"` (same for password);
  placeholders removed.

## 4c — batches table (`Batches.tsx` + css)

- Credit column: right-align header + cells (`.num-col { text-align:
  right; font-weight: 500; }`), header becomes `Credit (tCO₂e)` unchanged
  text but right-aligned.
- Wrap the two `<select>`s in a `.select-wrap` styled span with a custom
  chevron (inline SVG background-image on the wrapper, `appearance: none`
  on the select) so they read as designed controls.
- Flags column: `b.reason_count > 0` → `<span className="chip warn">{n}
  reason{n===1?"":"s"}</span>`; zero → `—` in `--text-tertiary`.

## 4d — lab screens

- `LabScan.tsx`: video background `#000` → `var(--basalt-950)`. Move the
  manual-UUID input OUT of the error-only flow: always render it below the
  camera card ("or paste batch UUID" + Open). Error line stays for camera
  denial.
- `LabEntry.tsx`: inputs get `style={{ height: 44 }}` or a `.input-lg`
  class (44px touch target); each field keeps its `.micro` label (now
  sentence-case from Phase 1); errors render below their form as today but
  prefixed with "⚠ ".

## 4e — registry two-column + print (`Registry.tsx` + css)

- Layout: wrap the page content in `.registry-grid { display: grid;
  grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }` —
  left column: kiln cards section + enrollment token; right column: the
  four data-entry forms. Below 900px it collapses:
  `@media (max-width: 900px) { .registry-grid { grid-template-columns:
  1fr; } }`.
- Token secret: wrap the `<code>` token in a `.token-well` (mono, 1px
  `--border-strong`, `--radius-md`, 10px padding) + a copy button + a
  `--text-secondary` note "Shown once — store it now."
- Print styles in `styles.css`:
  ```css
  @media print {
    .top, .filters, button, .linkbtn { display: none !important; }
    body { background: #fff; }
    .media-cell { break-inside: avoid; width: 8cm; }
  }
  ```

## 4f — per-page titles

In each page component, set `document.title` in a `useEffect` (e.g.
`Batch ${uuid.slice(0, 8)} · TerraCipher`, "Batches · TerraCipher",
"Registry · TerraCipher", "Sign in · TerraCipher").

**CHECKS:** the three gate commands.

**Commit:** `feat(portal): nav/login/table/lab/registry sweep + kiln-card print styles`

<!-- PHASE5 -->
# PHASE 5 — cleanup: retire legacy aliases

1. `grep -rn "var(--emerald\|var(--amber\|var(--faint\|var(--muted\|var(--ink\|var(--line\|var(--card\|var(--bg\|var(--indigo)\|var(--red)\|var(--shadow" src/`
   — migrate every remaining reference to its semantic token
   (`--emerald`→`--status-success-fg`, `--faint`→`--text-tertiary`,
   `--muted`→`--text-secondary`, `--ink`→`--text-primary`,
   `--line`→`--border-subtle`, `--card`→`--surface-card`,
   `--bg`→`--surface-page`, `--amber`→`--status-warning-fg`,
   `--red`→`--status-error-fg`, `--indigo`→`--indigo-600`,
   `--shadow`→`--shadow-sm`, `--shadow-lg`→`--shadow-md`,
   `--emerald-bg`→`--status-success-bg`, `--amber-bg`→`--status-warning-bg`,
   `--emerald-d`→`--status-success-fg`).
   The DOT map in `components/ComplianceChecklist.tsx` references
   `var(--emerald)`, `var(--amber)`, `var(--faint)` — migrate it too.
2. Only when the grep returns ZERO hits: delete the entire
   "legacy aliases" block from `:root`.
3. Final sweep: `grep -rn "style={{" src/pages src/components` — for each
   hit that sets a COLOR or BORDER with a raw value, move it to a class.
   (Layout-only inline styles — margins, gaps, widths — may stay.)

**CHECKS:** the three gate commands, plus
`grep -c "legacy aliases" src/styles.css` returns 0 and the color-token
grep from step 1 returns 0 hits.

**Commit:** `refactor(portal): retire legacy color aliases, inline color styles → tokens`

<!-- WRAPUP -->
# FINAL WRAP-UP

1. Run all three gate commands one more time — paste the output tails.
2. `git log --oneline -6` — expected: 5 commits in phase order on top of
   the Phase 0 start commit.
3. Report per phase: files touched, checks run with counts, anything
   adapted (drifted line numbers, missing verbatim blocks) explicitly.
4. Do NOT push. The human reviews, pushes, and Vercel redeploys.

## Explicitly OUT OF SCOPE (do not attempt)
- ANY file outside `portal/` (backend, Flutter app, root index.html).
- Dark mode (the token architecture enables it later; do not build it now).
- The 12-column / 1440px grid restructure — keep `max-width: 1040px`; a
  layout-width change is a separate reviewed task.
- New component/CSS frameworks, icon libraries, or any runtime dependency
  beyond the two font packages.
- Renaming `groupMedia`, `STEP_ORDER`, any exported symbol, or any
  `data-testid`.
- The backend media projection, API shapes, or auth flows.
