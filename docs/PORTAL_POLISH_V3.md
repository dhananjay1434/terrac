# PORTAL POLISH V3 — Post-Screenshot Defect & Subtraction Pass

## ROLE & GOAL

You are a senior product engineer executing a UI/UX-only polish pass on the
TerraCipher Verifier Portal (`portal/` — React 18 + Vite + TypeScript, CSS
Modules + one global `styles.css`, vitest + testing-library + jest-axe).

A design crit of live screenshots (post-V2) found **3 visible defects and 5
design-judgment failures**. This document fixes exactly those, nothing else.
The V2 foundation (tokens, palette, hero layout, checklist hierarchy) is
correct — do not redesign it. This is a surgical pass.

## THE ONE RULE ABOVE ALL — LOGIC FREEZE

UI/CSS/markup/copy changes ONLY. You MUST NOT touch:

- `src/api.ts`, `src/auth.ts`, `src/compliance.ts`, `src/qr.ts`, `src/lab.ts`
- Any route path, network call, payload shape, or state-management logic
- Any data binding — every rendered value must come from the same field it
  comes from today

Litmus test before every commit: *if I diff the network traffic and the
rendered DATA (not styling, not static copy), is it byte-identical?* If no,
revert.

**Fabricated-data ban (carried from V2):** never add reviewer names, farmer/
crop/region fields, LCA scope breakdowns, lot/transport info, or batch-level
hashes. The API does not return them.

## GLOBAL RULES

1. **Locate verbatim before every edit.** Read the target file section first;
   match `old_string` exactly. Never edit from memory.
2. **Gate after every phase:** `npm test -- --run` → `npm run typecheck` →
   `npm run build` (run inside `portal/`). All three green before commit.
3. **One commit per phase**, message given per phase. Do NOT push.
4. **Read the test file for any component before touching it.** Tests are the
   contract. When a phase requires a test change, it is explicitly listed —
   any other test change means you broke something; fix the code, not the test.
5. Tokens only — no new hex values outside `styles.css`, no new token *names*,
   no `!important`, no new dependencies.
6. `jest-axe` runs on every page — if the a11y suite fails after your change,
   your change caused it.

---

## PHASE 1 — Hero defects (the three things visible in 5 seconds)

Files: `portal/src/components/SealedVerdict/SealedVerdict.module.css`,
`portal/src/styles.css`.
**No `.tsx` changes in this phase.** The tests in
`SealedVerdict.test.tsx` and `BatchDetail.test.tsx` must pass UNCHANGED.

### 1a. "Pending verification2 blockers" — missing gap

In `SealedVerdict.module.css`, the `.count` span renders flush against the
caption text. Fix with spacing only (do NOT re-add a "·" separator in JSX —
the test `getByText("2 blockers")` requires the count to stay its own exact
text node):

```css
.count {
  font-weight: var(--fw-semibold);
  color: var(--text-primary);
  margin-left: 8px;
}
```

### 1b. Seal border clipped at the notched corners

`clip-path` on `.stamp` slices through the 1.5px border, so the border
vanishes at every corner cut — it reads as a rendering glitch. Replace the
`border` with a two-layer clip: the element background becomes the "border"
color, and a `::before` inset by the border width paints the fill *under* the
text via negative z-index inside an isolated stacking context.

Rewrite the `.stamp` block in `SealedVerdict.module.css` (keep the existing
`--notch` variable, `data-size` rules, and `.icon` rule as they are):

```css
.stamp {
  --notch: 6px;
  --seal-border: 1.5px;
  position: relative;
  isolation: isolate;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  font-size: var(--fs-13);
  font-weight: var(--fw-bold);
  letter-spacing: 0.04em;
  clip-path: polygon(
    var(--notch) 0%, calc(100% - var(--notch)) 0%, 100% var(--notch),
    100% calc(100% - var(--notch)), calc(100% - var(--notch)) 100%,
    var(--notch) 100%, 0% calc(100% - var(--notch)), 0% var(--notch)
  );
}
.stamp::before {
  content: "";
  position: absolute;
  inset: var(--seal-border);
  z-index: -1;
  clip-path: polygon(
    var(--notch) 0%, calc(100% - var(--notch)) 0%, 100% var(--notch),
    100% calc(100% - var(--notch)), calc(100% - var(--notch)) 100%,
    var(--notch) 100%, 0% calc(100% - var(--notch)), 0% var(--notch)
  );
}
```

Then re-key the per-verdict rules so the element `background` is the border
color and `::before` carries the fill:

```css
.stamp[data-verdict="ISSUABLE"] { color: var(--status-success); background: var(--status-success); }
.stamp[data-verdict="ISSUABLE"]::before { background: var(--status-success-bg); }
.stamp[data-verdict="PROVISIONAL"] { color: var(--status-warning); background: var(--status-warning); }
.stamp[data-verdict="PROVISIONAL"]::before { background: var(--status-warning-bg); }
.stamp[data-verdict="BLOCKED"] { color: var(--status-error); background: var(--status-error); }
.stamp[data-verdict="BLOCKED"]::before { background: var(--status-error-bg); }
```

Delete the old `border: 1.5px solid;` and old per-verdict `border-color`/
`background` lines. The `lg` size rule keeps `--notch: 9px` and may bump
`--seal-border: 2px`.

### 1c. The giant lavender "Not yet issuable" bar

Two root causes, two CSS fixes in `styles.css`:

1. `.hero-verdict` is a flex column with default `align-items: stretch`, so
   the button stretches full width. Add `align-items: flex-start;` to the
   existing `.hero-verdict` rule.
2. A disabled primary button currently renders as 50%-opacity indigo — a dead
   click target that still reads as the page's main CTA. Replace the existing
   `button.primary:disabled` rule with a quiet, obviously-inert treatment:

```css
button.primary:disabled {
  background: var(--surface-sunken);
  color: var(--text-tertiary);
  opacity: 1;
  cursor: not-allowed;
  box-shadow: none;
}
```

Also add a dark-mode counterpart next to the other `[data-theme="dark"]`
button rules: `[data-theme="dark"] button.primary:disabled { background:
var(--basalt-800); color: var(--basalt-400); }`.

Do NOT change the JSX or the button's label/disabled logic — behavior is
frozen; only its appearance changes.

**Required tests (all pre-existing, must pass unchanged):**
`SealedVerdict.test.tsx` (3), `BatchDetail.test.tsx` (11), full a11y suite.

**Commit:** `fix(portal): hero defects - count gap, seal border under clip-path, quiet disabled primary`

---

## PHASE 2 — Subtraction (remove what says nothing)

Files: `portal/src/pages/BatchDetail.tsx`,
`portal/src/components/LcaBreakdown/LcaBreakdown.tsx` (+ its `.module.css`),
`portal/src/components/ComplianceChecklist/ComplianceChecklist.tsx`,
`portal/src/components/EvidenceGallery/EvidenceGallery.tsx`,
`portal/src/styles.css`.

### 2a. Kill the Production tile (same number, three renderings)

"30 kg" currently renders in the hero facts, the Production tile, AND the LCA
summary — within one viewport. In `BatchDetail.tsx`, delete this block from
the `.tiles` row:

```tsx
<div className="card tile">
  <span className="micro">Production</span>
  <div className="v tabular">{d.batch.wet_yield_kg} kg</div>
</div>
```

Then in `styles.css` change `.tiles` to `grid-template-columns: repeat(2, 1fr);`
and update the loading skeleton in `BatchDetail.tsx` from three 72px skeleton
divs to two (keep the same markup pattern).

Test guard: `BatchDetail.test.tsx` asserts `getAllByText("100 kg").length ≥ 1`
— still satisfied by the hero facts and LCA summary. Do not touch the test.

### 2b. Kill the LCA apology sentence

In `LcaBreakdown.tsx`, delete the note block:

```tsx
<div className={styles.note}>
  Full LCA factor breakdown is not exposed by the API yet.
</div>
```

and remove the now-dead `.note` rule from `LcaBreakdown.module.css`. Internal
API limitations are never user-facing copy. `LcaBreakdown.test.tsx` does not
assert this text — it must pass unchanged.

### 2c. "enforced" chip wallpaper

Eleven identical grey "enforced" chips down the checklist is noise; the chip
only carries information when enforcement is *unusual*. In
`ComplianceChecklist.tsx`, render the chip conditionally:

```tsx
{item.enforcement !== "enforced" && (
  <span className={`chip ${styles.enforcement}`}>
    {item.enforcement}
  </span>
)}
```

No checklist test asserts the chip text (verify by reading both
`ComplianceChecklist.test.tsx` files first — if either does, stop and leave
the chip alone).

### 2d. Double count in evidence group headers

Each group header shows "· 1 item" in the `<h3>` AND a `1` chip on the right.
In `EvidenceGallery.tsx`, delete `<div className="chip">{items.length}</div>`
from `.evidence-group-head`, keep the count in the heading text
(`BatchDetail.test.tsx` matches the heading by regex — the h3 text must not
change).

### 2e. Breadcrumb vs "← All batches" (conditional)

Read `portal/src/components/AppShell/Breadcrumbs.tsx` first. IF the "Batches"
crumb is a real `<Link to="/batches">`, delete the `<Link className="back">`
from `BatchDetail.tsx`'s **success render only** (keep it in the error state,
which renders outside the shell context visually). IF the crumb is plain text,
leave the back link alone and note it in the commit body. Also remove the now
orphaned `<div style={{ marginTop: 12 }}>` wrapper spacing if it depended on
the link (keep the VerificationChain's top margin sane — 0 or 12px, check
visually via the markup).

### 2f. Calm the OK rows (semantic inversion softening)

Checklist labels are failure descriptions from the API ("Biomass input amount
not recorded") — pairing them with a green OK reads contradictory. The strings
are frozen (logic freeze), so soften at the presentation layer: in
`ComplianceChecklist.module.css`, on OK rows dim the label so the green dot +
OK carry the meaning and the failure-phrased text recedes:

```css
.row[data-status="ok"] .labelCol > :first-child {
  color: var(--text-secondary);
}
```

(`.labelCol`'s first child is the `crit-label` span.) MISSING rows keep full
contrast — the asymmetry is the design.

**Required tests:** full suite green, zero test-file edits in this phase.

**Commit:** `polish(portal): subtraction pass - dedupe production tile, drop apology copy, quiet chips + counts`

---

## PHASE 3 — Registry form + Lab scanner

Files: `portal/src/pages/Registry.tsx`,
`portal/src/pages/__tests__/Registry.test.tsx`, `portal/src/styles.css`,
`portal/src/pages/LabScan.tsx`.

### 3a. Registry label casing — do it properly this time

The V2 CSS-only fix (`text-transform: capitalize`) produced Title Case
artifacts: "Kiln Id", "Weight Kg", "Capacity Litres". Fix the label *strings*
to sentence case with correct unit formatting, and update the test's
`getByLabelText` queries to match. This is UI copy, explicitly allowed —
**the POST payload keys and shapes must not change** (the test's
`toHaveBeenCalledWith("kilns", { kiln_id: ..., weight_kg: 12, ... })`
assertion stays byte-identical).

New label strings in `Registry.tsx` field defs:

| old | new |
|---|---|
| `kiln id` | `Kiln ID` |
| `type (open/closed)` | `Type (open/closed)` |
| `material` | `Material` |
| `weight kg` | `Weight (kg)` |
| `capacity litres` | `Capacity (litres)` |
| `visit date` | `Visit date` |
| `notes` | `Notes` |
| `scale id` | `Scale ID` |
| `calibrated at` | `Calibrated at` |
| `valid until` | `Valid until` |
| `operator id` | `Operator ID` |
| `completed date` | `Completed date` |
| `training type` | `Training type` |
| `project id` | `Project ID` |
| `year` | `Year` |
| `methane g/kg` | `Methane (g/kg)` |

Update `Registry.test.tsx`: `getByLabelText("kiln id")` → `"Kiln ID"`,
`"type (open/closed)"` → `"Type (open/closed)"`, `"material"` → `"Material"`,
`"weight kg"` → `"Weight (kg)"`, `"visit date"` → `"Visit date"`, and the
label-binding test's `textContent` assertion `"kiln id"` → `"Kiln ID"`.
**These are the ONLY test edits permitted in this entire document.**

Then delete the `.field-label { text-transform: capitalize; }` rule from
`styles.css` and remove `field-label` from the label's `className` in
`Registry.tsx` (the class has no other purpose).

### 3b. Save button alignment

The Save button floats mid-grid beside the last field. In `Registry.tsx` the
button sits as a bare flex child of `.filters` next to label+input columns.
Give it bottom alignment so it lines up with the input row, via inline style
on that button only: `style={{ alignSelf: "flex-end" }}`.

### 3c. Scanner viewfinder

In `LabScan.tsx` the aiming frame is `border: "2px solid var(--ember-500)"`
with `borderRadius: "var(--r-xl)"` — **`--r-xl` does not exist** (only
`--r-sm/md/lg` are defined), so the radius silently fails. Change to:

```
border: "2px solid rgba(255, 255, 255, 0.9)",
borderRadius: "var(--r-lg)",
```

White is the universal scanner-viewfinder convention and reads correctly on
the black video field; the undefined token becomes a real one.

**Required tests:** full suite green; only the `Registry.test.tsx` label-string
edits listed in 3a.

**Commit:** `polish(portal): registry sentence-case labels + save alignment, white scanner frame`

---

## PHASE 4 — Final gate & visual QA

1. Run the full gate one last time: `npm test -- --run`,
   `npm run typecheck`, `npm run build` — all green.
2. Fabricated-data grep (must return nothing relevant):
   `grep -inE "reviewed by|farmer|crop|region|lot number|transport|scope [123]" src/pages/*.tsx src/components/**/*.tsx`
   (aria-live "region" comments in CopyButton are known false positives).
3. Confirm zero diffs outside: `SealedVerdict.module.css`, `styles.css`,
   `BatchDetail.tsx`, `LcaBreakdown.tsx` + module css,
   `ComplianceChecklist.tsx` + module css, `EvidenceGallery.tsx`,
   `Registry.tsx`, `Registry.test.tsx`, `LabScan.tsx`.
4. `git status` clean after the Phase 3 commit → done. Do not push.

## OUT OF SCOPE — DO NOT ATTEMPT

- The "Preview unavailable" wall on the evidence gallery: the thumbnails fail
  because `fetchMediaUrl` requests fail in that environment, and 12/15 items
  arrive with no `capture_type`. Both are backend/data issues — the designed
  fallback is already correct UI. Touch nothing.
- Rewriting checklist label strings ("Biomass input amount not recorded") —
  they come from the API checklist payload. Presentation softening only (2f).
- The `Methodology "—"` row in ConfirmModal/Provenance — the API has no
  methodology field; showing "—" is honest. Leave it.
- No new tokens, no layout-width changes (`--content-max` stays 1040px),
  no new dependencies, no parallel naming systems.
