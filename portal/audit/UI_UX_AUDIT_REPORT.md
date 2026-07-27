# TerraCipher Verifier Portal — UI/UX Engineering Audit

**Date:** 2026-07-26 · **Scope:** `portal/` (React 18 + Vite 5, CSS Modules, token layer in `src/tokens/tokens.css` + `src/styles.css`)
**Method:** Mock-first Playwright capture — all `/api/v1/portal/*` fulfilled from fixtures typed 1:1 against `src/api.ts`; `localStorage` seeded per role (`dmrv.portal.token` / `dmrv.portal.role`) and theme (`tc_theme`). **264 captures**: 10 routes × 4 viewports (1440/1280/768/390) × 2 themes × 2 roles base grid, plus loading / empty / error / overflow / provisional / ready-to-issue / ConfirmModal-mid-token / lightbox / filters / collapsed-rail / account-menu / login-error / validation states, print emulation + A4 PDFs, and element-level micro-states. See `audit/manifest.json`; reproduce with `npm run dev` + `node audit/capture.mjs all`.

**Capture caveats (verified, not product bugs):** full-page screenshots reflow layout by ~9 px (scrollbar removal) and downscaled review of tall pages can distort the rail — a 1:1 viewport probe confirmed the shell renders correctly (240 px rail, full wordmark, icons). Map tiles were blocked (external hosts); ParcelMap chrome audited from code. LabScan camera state audited from code + fallback screenshots (headless has no camera).

---

## 1 · Executive summary — the 5 highest perception-per-effort changes

1. **Dark theme breaks every status voice in the app (Critical, ~10 lines).** The single-value aliases `--status-success/warning/error/inert` (`tokens.css:77–80`) are never remapped in `[data-theme="dark"]`, so the SealedVerdict stamp, every table StatusDot, checklist OK/MISSING text, VerificationChain markers, and the ConfirmModal's *irreversible-action warning* render light-theme colors on dark surfaces — measured **2.2:1** on the verdict stamp and **2.8:1** on the modal warning. A verifier at night literally cannot read the verdict. Fix: remap the four aliases in the dark block (`--status-success: var(--status-success-fg);` etc.).
2. **The topbar action cluster is stranded on the left (High, 1 line).** With the rail expanded, `.topbarWordmark` — the only `margin-right: auto` carrier — is `display: none` (`AppShell.module.css:178`), so theme/help/account icons sit at x≈256 with ~1,100 px of dead topbar. Users look top-right for account controls (Jakob's law); finding them mid-left reads as broken. Fix: move `margin-left: auto` onto `.topbarRight`.
3. **The printed "evidence pack" contains no evidence (Critical, ~6 lines).** `@media print { button { display: none } }` (`styles.css:556`) hides the `<button class="thumbBtn">` that wraps every evidence image and the Accordion triggers that hold the checklist's section titles. The forensic deliverable prints as metadata cards without photos and a checklist without chapters. Fix: scope the rule (`button:not(.print-keep)`) or unwrap images from buttons in print via a `.thumbBtn { all: unset; display: block }` print override.
4. **The ISSUED state is the least visible fact on an issued batch (High, small change).** `BatchDetail.tsx:176` maps an issued batch to the big green `ISSUABLE` stamp + a small indigo `.seal` chip. The one irreversible, legally-meaningful state gets the weakest signal, and green "issuable" on an already-issued batch is semantically wrong. Fix: extend `SealedVerdict` with an `ISSUED` verdict (indigo family, `--indigo-600` border / `--surface-brand-subtle` fill) and pass it when `status === "ISSUED"`; drop the redundant chip.
5. **Keyboard focus is invisible on every input (High, 2 lines).** `input:focus, select:focus { outline: none }` (`styles.css:146–149`) defeats the global `:focus-visible` ring; the only cue is a hairline border-color shift (verified in `_micro/light/filter-input-focus.png` — buttons show a strong double ring, inputs show nothing). Fix: replace with `input:focus-visible, select:focus-visible { outline: 2px solid var(--indigo-600); outline-offset: 2px; }` (dark remap already exists).

---

## 2 · Design-system health score: **62 / 100**

| Area | Score | |
|---|---|---|
| A · Layout & alignment | 62 | strong bones, two real layout bugs, spacing anti-scale |
| B · Typography | 78 | best-in-class token adherence in CSS; inline drift |
| C · Color | 55 | disciplined light palette; dark aliases + phantom tokens |
| D · Components & consistency | 60 | good primitives, three-way duplication everywhere |
| E · Interaction & feedback | 58 | silent failures, invisible input focus, copyable confirm token |
| F · IA & cognitive load | 64 | verdict-first is right; issued-state and form-first pages aren't |
| G · Micro-details | 66 | em-dash discipline mostly holds; z-index chaos, glyph drift |
| H · Accessibility | 63 | excellent bones (Radix, roving tabindex); three real gaps |

**A · Layout & alignment — 62.** The shell is genuinely well-architected (sticky rail + `--topbar-h`-offset sticky table headers is a premium detail), but two verified layout bugs (left-stranded topbar cluster; `.tiles` has no mobile breakpoint so LCA cards squeeze into ~167 px columns at 390 px) plus a systemic spacing anti-scale — 48 off-scale px values (`10px`×13, `14px`×11, `6px`×8) and 92 on-scale-but-raw values across CSS Modules, mirrored by ~120 inline TSX magic numbers (`marginTop: 14` ×13 is an undeclared token) — mean the 8-pt grid exists in `tokens.css` but not in practice.

**B · Typography — 78.** Only 2 of 86 CSS `font-size` declarations bypass `--fs-*` (both in ParcelMap); mono discipline for hashes/UUIDs/tokens is near-airtight (`.mono`+`.tabular` on SHA-256 cells, ConfirmModal token, breadcrumb IDs) and `td, th { font-variant-numeric: tabular-nums }` is exactly right for a forensic UI. Docked for: inline `fontSize: 22` (Login) and `11` (ParcelMap) that exist in no scale, `fontSize: 18/16/13/12` inline instead of vars (BatchDetail:123, Projects:330/369, LabEntry, Registry:270), the batch ID in LabEntry's H1 not mono, and three date dialects on one product (ISO `2026-02-02` in tables, `Jul 20` on Dashboard, `2026-02-02 10:00` in Provenance vs date-only in the hero on the *same screen*).

**C · Color — 55.** The light palette is genuinely restrained — indigo is the only accent, semantic colors come from `--status-*` only, and the near-duplicate-gray problem common at this stage is absent. Three things drag it down: (1) the dark-theme alias failure (§1.1) — the single worst defect in the product; (2) **five phantom tokens** (`--radius-m`, `--radius-s`, `--border-color`, `--bg-card`, `--r-pill`, plus `--accent` in TemperatureChart) that silently render fallbacks — the burn-temperature curve is *achromatic* because `--accent` doesn't exist; (3) four hand-written scrims in two alphas, ParcelMap still on a slate/Tailwind palette (`#e2e8f0`, `#3b82f6` polygon stroke — off-brand blue on the boundary-drawing surface), and the issue-credit modal confirming in destructive **red** (`danger` → `--red-700`) when the designed register for permanent-but-constructive was ember.

**D · Components & consistency — 60.** The primitive layer (`ui/Button`, `Card`, `StatusPill`, `DataTable`) is well built — but each has an unretired legacy twin: **three button systems** (`ui/Button`, global `button.primary`/`.neutral` with different H-padding 18 px vs 16 px, `.linkbtn`), **three status renderers** (StatusDot, StatusPill, `.chip.ok/warn/err`) *plus* two pages (Farmers, Projects) rendering status as raw lowercase strings, **two copy buttons** (`CopyButton` vs `Batches.tsx` local `CopyId`), **two stat-number components** (StatTile `--fw-bold` vs MetricBlock `--fw-semibold`), two skeleton pulse implementations, and one dead component (`ActivityTimeline` — zero imports). Consistency is the difference between "designed" and "assembled"; this is the assembled end.

**E · Interaction & feedback — 58.** Loading is handled well where it matters (DataTable skeleton rows, dashboard card skeletons, BatchDetail layout-mimicking skeleton) and every mutation has a pending label ("Issuing…", "Submitting…"). Docked for: **silent failures** (`verifyMedia` approve/reject and Registry `mintToken` swallow non-auth errors with zero feedback — a verifier's verdict can vanish), the lightbox's loading state *being* the failure message ("media unavailable" flashes before every image), form success/error pills that auto-dismiss in 4 s (`Registry.tsx:38`, `Dispatch.tsx:103`) so a slow glance misses the outcome, the invisible input focus (§1.5), and a CopyButton *on the typed confirmation token* (`ConfirmModal.tsx:76`) that converts the deliberate type-to-confirm friction into click-paste-confirm.

**F · IA & cognitive load — 64.** BatchDetail's chain → verdict → LCA → checklist → telemetry → evidence order is defensible (verdict-first is correct for triage) and status/flags land in the table hot zones with real affordances (chevron column, blockers pill). Docked for: the issued-state inversion (§1.4), evidence living below the issue CTA with no in-page anchor, **admin forms rendered above the primary content for all roles** on Dispatch, Projects, and Registry (a verifier's Dispatch page leads with a facility-registration form they cannot legally submit — the server's 403 surfaces as "check values"), Farmers' detail panel appearing *below the pager* with no scroll-into-view (a row click appears to do nothing), and blank breadcrumbs on 4 of 8 authed routes (`Breadcrumbs.tsx` maps only 3 paths).

**G · Micro-details — 66.** Em-dash discipline is mostly excellent (`—` for null device/project/date everywhere in tables; never "null"). Docked for: "no GPS" prose and `"…"` vs `"..."` (Projects `parcel_uuid.slice(0,8) + "..."`) breaking the missing-data vocabulary; 9 ad-hoc z-indexes with a **skip-link/modal tie at 100**; kiln QR captions truncating (`.cap` ellipsis) on cards meant to be printed and mounted; `<meta name="theme-color">` pinned to dark `#0f1115` in light mode; no scrollbar or `::selection` styling in either theme; Title Case ("Registered Projects", "Parcel Name") vs sentence case everywhere else; the hand-rolled camera SVG in EvidenceGallery beside lucide icons; icon sizes 12/14/16/18 mixed within single surfaces.

**H · Accessibility — 63.** The bones are strong: Radix focus traps, roving-tabindex DataTable with Home/End, real skip link, `aria-label` on every icon-only control, `aria-live` pagers, `aria-invalid`+`aria-describedby` on the confirm token. Beyond-axe gaps: input focus invisibility (§1.5), skip link losing its z-battle with open modals, 24–32 px touch targets at 390 px (CopyId ≈24 px, password toggle ≈20 px, iconBtn 32 px vs the 44 px `input-lg` proves the intent exists), lightbox arrow-key nav requiring focus inside the dialog with no visible hint, and LabEntry's global-only error with no per-field `aria-describedby` link.

---

## 3 · Screen-by-screen findings

Severity: **Critical** = trust/task-blocking · **High** = perceptibly broken or misleading · **Medium** = visible quality drag · **Polish** = sub-perceptual, compounds.

### 3.1 Shell (Topbar / Sidebar / Breadcrumbs) — all routes

Screens: `screenshots/*/…/default.png`, `dashboard/*/1440x900/sidebar-collapsed.png`, `account-menu-open.png`, probe `audit/probe2-viewport.png`

| # | Sev | Cat | What's wrong | Impact | Exact fix |
|---|---|---|---|---|---|
| S1 | High | Layout | Theme/help/account cluster left-stranded at x≈256 when rail is expanded — sole `margin-right:auto` carrier (`.topbarWordmark`) is `display:none` on desktop | Account/session controls in an unscannable position; page reads unfinished | `AppShell.module.css:205` — add `margin-left: auto;` to `.topbarRight` (keep the wordmark's auto margin for mobile) |
| S2 | High | A11y | Skip link `z-index: 100` (`AppShell.module.css:9`) ties modal/lightbox panels (also 100); DOM order puts it behind open overlays | Keyboard users lose the skip affordance exactly when trapped | Set `z-index: 200` (or `var(--z-skiplink)` once the scale in §4.2 lands) |
| S3 | Medium | IA | Breadcrumbs blank on `/dashboard`, `/projects`, `/farmers`, `/dispatch` — `LABELS` map (`Breadcrumbs.tsx:5–9`) covers 3 routes; `min-height: 12px` reserves a dead strip | Wayfinding appears and disappears route-to-route; perceived instability | Extend `LABELS` with the 4 missing routes (`"/dashboard": "Dashboard"` …), or hide the strip when empty (`:empty { display: none }` won't fire — return `null` when no crumb) |
| S4 | Medium | Feedback | Help icon button (`Topbar.tsx:84`) has no handler — a silent interactive | Dead control erodes trust in every other control | Wire to docs URL or remove until it does something |
| S5 | Medium | IA | Account menu shows only "Sign out" — no user email or role; roles gate real capabilities | Verifier/admin can't confirm which hat they wear; support burden | Add a disabled `DropdownMenu.Label` with email + role chip (both already in `auth.ts` storage) |
| S6 | Polish | Micro | `title="⌘\"` on collapse button is macOS-only glyph on a Windows deploy | Tooltip teaches a wrong shortcut | Derive from `navigator.platform` → `Ctrl+\` |
| S7 | Polish | Color | `meta[name=theme-color]` fixed `#0f1115` (`index.html:6`) | Light-mode mobile chrome gets a dark browser frame | Two `<meta name="theme-color" media="(prefers-color-scheme: …)">` entries |

### 3.2 Login (`/login`)

Screens: `login/{theme}/{vp}/default.png`, `login/*/1440x900/error-invalid-credentials.png`

| # | Sev | Cat | What's wrong | Impact | Exact fix |
|---|---|---|---|---|---|
| L1 | Medium | Type | Brand panel wordmark `fontSize: 22` (`Login.tsx:111`) — a size that exists in no scale (20/24 exist); body `lineHeight: 1.6` also off-scale | The first screen quietly breaks the system it introduces | `fontSize: "var(--fs-24)"`, `lineHeight: "var(--lh-normal)"` |
| L2 | Medium | A11y | Password reveal (`Login.tsx:76–89`) is a ~20 px absolute-positioned `.linkbtn` with 14 px icon | Sub-44 px target on the one field every user touches | Give it `width/height: 32px; display: grid; place-items: center` via a class, not inline styles |
| L3 | Medium | Components | Error affordance is a red *left border* on both fields via inline `invalidStyle` (`Login.tsx:42–44`) — a pattern used nowhere else (LabEntry uses ⚠ lines, Registry uses pills) | Third error grammar on the third form | Use `.err` text under the field + `aria-invalid` on inputs; drop the border hack |
| L4 | Polish | Color | Brand aside hardcodes primitives (`--basalt-950` bg, `--basalt-50`/`--basalt-300` text) rather than semantic tokens | Bypasses the theme layer; fine today, drifts tomorrow | Introduce `--surface-inverse` / `--text-inverse` aliases if the panel stays theme-fixed |
| L5 | Polish | Micro | Error message renders *below* the submit button (`Login.tsx:95`) | Eye is at the button; message appears outside the scan path | Move `{err && …}` above the `<Button>` |

### 3.3 Dashboard (`/dashboard`)

Screens: `dashboard/{theme}/{vp}/default.png`, `empty.png`, `error.png`, `loading.png`, smoke shot

| # | Sev | Cat | What's wrong | Impact | Exact fix |
|---|---|---|---|---|---|
| D1 | High | Micro/Type | `fmtCredit` renders `646.160` (`format.ts:4`) — three fixed decimals with no thousands separator; in `1.234` locales this *is* a thousands figure | Ambiguous headline number on a carbon-credit KPI; trust-critical | Keep 3 decimals but add grouping: `t.toLocaleString("en-IN"|undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 })` in `format.ts` (single source — one change fixes every screen) |
| D2 | High | IA | Zero-vocabulary conflict in one KPI row: Credits issued → `—`, Issued batches → `0`, Provisional credit → `0.000` (`KpiRow.tsx:61–79`) | Three different "nothing"s read as three different facts | Apply the `noIssuedYet` treatment to provisional credit too (`—` + hint when `provisional_count === 0`) |
| D3 | Medium | IA | Empty-DB blocker card claims "No blockers — all batches issuable" (`IssuanceBlockerCard`) when there are zero batches | Fabricated-sounding claim in an audit tool | Distinguish `no data` from `no blockers`: when `by_status` totals 0, say "No batches yet" |
| D4 | Medium | Layout | Quality cards put two fixed StatTiles in a full-width card leaving ~60% whitespace right (`PyrolysisQualityCard`, `PermanenceQualityCard` + `StatBand`) | Unbalanced figure-ground; reads unfinished at 1440 | Cap tile width and let the bar list share the row: `grid-template-columns: repeat(2, minmax(180px, 240px)) 1fr` on a local wrapper, or render the two cards side-by-side in `Dashboard.tsx` (`.registry-grid`) |
| D5 | Medium | Components | Five dashboard cards copy-paste the same inline error-card object (`KpiRow.tsx:39`, `CreditsOverTime.tsx:104`, etc.) with `marginTop: 2` off-scale | Guaranteed drift; already three slightly different paddings | Extract `<CardError message onRetry>` into `ui/`; use `var(--space-1)` |
| D6 | Medium | Motion/Layout | Chart empty state is bare centered text in a ~320 px void; quality cards left-align theirs | Two empty-state grammars on one screen | Use `EmptyState` (icon-less) inside `DivergingStackedBarChart`'s empty branch |
| D7 | Polish | Type | Stale comment "v1 is month-only — there is no week toggle" (`CreditsOverTime.tsx:73`) beside a live Month/Week/Day toggle | Misleads the next engineer | Delete the sentence |
| D8 | Polish | Layout | `BucketToggle` row uses inline `marginBottom: 8` and hangs detached right (`Dashboard.tsx:107`) | Floating control without a card anchor | Move toggle into the chart card header row (`CreditsOverTime`), `gap: var(--space-2)` |

### 3.4 Batches (`/batches`)

Screens: `batches/{theme}/{vp}/default.png`, `filters-active.png`, `empty.png`, `error.png`, `loading.png`, `overflow.png`

| # | Sev | Cat | What's wrong | Impact | Exact fix |
|---|---|---|---|---|---|
| B1 | High | Color | Status column dots+labels use non-remapped aliases → "Issuable" ≈2.9:1, "Provisional" ≈3.1:1 on dark cards (verified `batches/dark/1440x900/default.png`) | The scan-column of the primary worklist is illegible at night | §4.1 alias remap fixes globally |
| B2 | Medium | Layout | Summary StatBand pops in after fetch (`Batches.tsx:259` renders only when `summary` truthy) → table jumps down ~120 px | Layout shift on every visit; premium UIs reserve space | Render the band always; pass `value="—"` tiles while `summary === null` (Skeleton variant also fine) |
| B3 | Medium | Components | Local `CopyId` (`Batches.tsx:50–67`) duplicates `CopyButton` with different sizing (12 px vs 14 px icon), ~24 px target | Two copy affordances drift; sub-44 px target | Use `components/CopyButton` (it already stops propagation via label pattern — add `e.stopPropagation()` wrapper if needed) |
| B4 | Medium | Micro | `Credit` StatTile sums only the loaded page with hint "this page" (`Batches.tsx:268–273`) | A page-scoped sum beside org-scoped counts invites misreading | Drop the tile, or fetch the org total from the timeseries endpoint like Dashboard does |
| B5 | Medium | Type | `fmtDate` = ISO slice (`2026-02-02`) vs Dashboard's `Jul 20` and Provenance's `2026-02-02 10:00` | Three date dialects; tables feel machine-dumped | One `fmtDate`/`fmtDateTime` in `format.ts` used by all pages (recommend `02 Feb 2026` — unambiguous, sorts visually) |
| B6 | Polish | Micro | Filter selects expose raw enum caps (`RECEIVED`, `ISSUED`) in `FilterBar.tsx:44–45` while the status column says "Issuable/Provisional" | Two vocabularies for one concept | Option labels "Received", "Issued" |
| B7 | Polish | Micro | Blockers pill "2 reasons" vs column header "Blockers" | Same concept, two words | Pill text `2 blockers` |

### 3.5 Batch detail (`/batches/:uuid`) — the flagship screen

Screens: `batch-detail/{theme}/{vp}/default.png`, `provisional.png`, `ready-to-issue.png`, `confirm-modal-mid-token.png`, `lightbox-open.png`, `loading.png`, print pair

| # | Sev | Cat | What's wrong | Impact | Exact fix |
|---|---|---|---|---|---|
| BD1 | Critical | Color | SealedVerdict stamp text ≈**2.2:1** in dark (`--status-success` on `--status-success-bg` remap); same for PROVISIONAL/BLOCKED | The verdict — the screen's entire point — is unreadable in dark | §4.1; verified fix target `SealedVerdict.module.css:48–53` needs no change once aliases remap |
| BD2 | High | IA | Issued batch shows big green `ISSUABLE` + small indigo `✓ CREDIT ISSUED` chip (`BatchDetail.tsx:174–185`) | Strongest signal describes the wrong state; the permanent fact whispers | Add `ISSUED` to `SealedVerdict` (`Verdict` union, copy "Credit issued", indigo tokens) and map `issued ? "ISSUED" : issuable ? "ISSUABLE" : "PROVISIONAL"`; delete the `.seal` chip |
| BD3 | High | Feedback | Approve/Reject still rendered on already-reviewed media and on issued batches (`EvidenceGallery.tsx:116–135`) | Post-issuance evidence verdicts mutate the record behind a sealed credit — gravity violation | Hide `VerdictControls` when `verification_status` set (offer "Change verdict" ghost) and when batch status is `ISSUED` |
| BD4 | High | Feedback | `verifyMedia` failures silently swallowed (`try/finally`, no catch — `EvidenceGallery.tsx:61–84`) | A verifier's rejection can vanish without trace — forensic integrity | Catch → inline `StatusPill status="error"` beside the buttons, persist until dismissed |
| BD5 | High | Color | Media cell can show `✓ verified` (green) and `rejected: …` (red) simultaneously (`EvidenceGallery.tsx:236–250`) | Two verdict colors on one item = contradiction to a scanning eye | Prefix the first chip's label: `type ✓ verified` vs `review rejected` — make the two axes lexically distinct; or demote capture-type chip to `.chip` neutral once a reviewer verdict exists |
| BD6 | Medium | IA | Reading order: Issue CTA (hero) sits above evidence; no anchor from verdict to `#evidence-media` | Admin can issue without the page ever *showing* evidence on screen | Add `href="#evidence-media"` ghost link "Review evidence ↓" beside the count in the chain node |
| BD7 | Medium | Micro | ConfirmModal preview includes fabricated row `Methodology: "—"` (`BatchDetail.tsx:297`) | A dead placeholder inside the highest-gravity dialog | Remove the row until the API exposes methodology |
| BD8 | Medium | Layout | `.tiles` grid: 3 children in 2 columns leaves a hole beside Provenance; no <720 px collapse (`styles.css:282–287`) | Dead quadrant at desktop; crushed cards at 390 (verified mobile shot) | Add `@media (max-width: 720px) { .tiles { grid-template-columns: 1fr; } }` and `grid-column: 1 / -1` for the odd card, or make it `repeat(auto-fit, minmax(280px, 1fr))` |
| BD9 | Medium | Color | Burn-temperature curve strokes `var(--accent, currentColor)` — `--accent` doesn't exist (`TemperatureChart.tsx:47,66,73`) | The one chart on the forensic screen renders achromatic | Use `var(--indigo-600)`; dark inherits fine (line on card) |
| BD10 | Medium | Layout | SVG `viewBox 600×200` + `height=200` + default `preserveAspectRatio` letterboxes the chart to ~60% of card width; extreme points at y=0/200 clip dot radii | Chart looks broken/half-drawn | Add `preserveAspectRatio="none"` (or compute width) and pad the y-domain: map to `[8, 192]` |
| BD11 | Medium | Micro | Same fact, two formats on one screen: hero `2026-02-02` vs Provenance `2026-02-02 10:00` | Reads as two different events | Both through `fmtDateTime` (§B5) |
| BD12 | Medium | Feedback | All non-auth load errors → "Batch not found." (`BatchDetail.tsx:80`) — including 500s | Wrong diagnosis; verifier gives up on a live batch | Branch on `ApiError.status === 404`; else "Couldn't load batch — retry" + Retry button |
| BD13 | Medium | Layout | Skeleton uses raw magic heights (180/72/200/300 + `marginBottom: 18/14`) inline (`BatchDetail.tsx:131–137`) | Off-grid; duplicates Skeleton variants | Use `Skeleton variant="card"` stack with `var(--space-4)` gaps |
| BD14 | Polish | Micro | Evidence section silently absent when `media.length === 0` (`EvidenceGallery.tsx:271`) | Absence of evidence is itself forensic information | Render the card with `EmptyState title="No evidence media"` |
| BD15 | Polish | Micro | `wet_yield_kg` printed raw (`{d.batch.wet_yield_kg} kg`) — no grouping at ≥10,000 | `85000 kg` reads worse than `85,000 kg` | `toLocaleString()` via a `fmtKg` helper in `format.ts` |
| BD16 | Polish | Micro | Timestamps `slice(0,16).replace("T"," ")` with no timezone marker (gallery + lightbox) | Forensic timestamps need an explicit clock | Suffix ` UTC` (values are ISO-Z) |

### 3.6 Issue-credit ConfirmModal

Screens: `batch-detail/{theme}/1440x900/confirm-modal-mid-token.png`, `confirm-modal-token-match.png`

| # | Sev | Cat | What's wrong | Impact | Exact fix |
|---|---|---|---|---|---|
| CM1 | Critical | Color | Warning text `--status-warning` on dark `--status-warning-bg` ≈ **2.8:1** (`ConfirmModal.module.css:53–55`); ✓/✗ feedback lines same class of failure | The irreversibility disclosure is the least legible text in the dialog | §4.1 remap; verified in dark capture |
| CM2 | High | Interaction | `CopyButton` on the confirmation token (`ConfirmModal.tsx:76`) | Type-to-confirm exists to force System-2 attention; copy-paste reduces it to two clicks | Remove the CopyButton; keep the token selectable-off (`user-select: none` on the label span) |
| CM3 | High | Color | `danger` flag turns confirm red (`--red-700`) for credit issuance (`BatchDetail.tsx:302`, `ConfirmModal.module.css:97`) while the trigger is calm indigo | Red = destructive-delete in every mental model; issuing is constructive-permanent — ember was the designed register | Drop `danger` from BatchDetail's modal; default `.confirm` ember-600/700 already carries gravity. Trade-off noted: red is "safer-looking", but semantic dissonance costs more trust than it buys caution |
| CM4 | Medium | Layout | Modal has no border in dark; `--shadow-modal` is black-on-black and overlay is `rgba(15,17,21,0.4)` on an already-dark page | Dialog edges melt into the page; modality weak | Add `border: var(--border-hair)` on `.content`; introduce `--overlay-scrim: rgba(15,17,21,0.4)` + dark remap `rgba(0,0,0,0.6)` (§4.2) |
| CM5 | Polish | Micro | `.feedback` `min-height: 18px` off-grid; title margin `14px` | Off-scale internals in the flagship dialog | `var(--space-4)`-based values with §4.2's `--space-3-5` decision |

### 3.7 Evidence lightbox

Screens: `batch-detail/{theme}/1440x900/lightbox-open.png`

| # | Sev | Cat | What's wrong | Impact | Exact fix |
|---|---|---|---|---|---|
| LB1 | High | Feedback | Loading state *is* the failure message — `url === null` renders "media unavailable" while bytes fetch (`EvidenceLightbox.tsx:68–82`) | Every open flashes a false negative; forensic tool crying wolf | Track `failed` separately (as GalleryThumb already does); show `Skeleton variant="card"` while loading |
| LB2 | Medium | A11y | ←/→ nav only via `onKeyDown` on content + buttons; no visible hint, and `1 / 5` counter is the only position cue | Keyboard affordance undiscoverable | Add `aria-keyshortcuts="ArrowLeft ArrowRight"` + a `.micro` hint line "← → to navigate" |
| LB3 | Polish | Micro | "no GPS" prose vs `—` for missing timestamp in the same `<dl>` | Two missing-data dialects in four rows | Use `—` + keep the label "GPS" |
| LB4 | Polish | Components | Close is `button.primary` (indigo, heaviest weight in dialog) for a dismiss action | Primary weight on the least important action | `className="neutral"` |

### 3.8 Lab scan (`/lab/scan`) + Lab entry (`/lab/:uuid`)

Screens: `lab-scan/*/default.png`, `lab-entry/*/default.png`, `lab-entry/*/1440x900/validation-error.png`

| # | Sev | Cat | What's wrong | Impact | Exact fix |
|---|---|---|---|---|---|
| LE1 | High | Feedback | Global-only validation, rendered *below* submit, no field association or `aria-describedby` (`LabEntry.tsx:114–118`) | Scientist must map "H:Corg ratio out of range" back to a field themselves | Return per-field errors from `validateLabForm` display map (UI-side only — `lab.ts` API untouched: derive `field → message` from existing strings), render under each input with `aria-invalid` |
| LE2 | Medium | Type | Batch ID in H1 not mono (`LabEntry.tsx:63–65`) while breadcrumb gets `.mono` | Mono discipline broken in the most prominent spot on the page | `Lab results · <span className="mono">{uuid.slice(0,8)}</span>` |
| LE3 | Medium | IA | Zero batch context — no species/received-date/status confirmation before entering results | Wrong-batch data entry is the costliest lab error | Fetch `getBatch` header info; show a one-line context card (id · species · received) above the form |
| LE4 | Medium | Components | Placeholder `"8, 9, 10"` on moisture samples reads as a value (`LabEntry.tsx:93`) | Classic placeholder-misuse; field looks filled | Move format guidance into the label or a `.micro` hint below; kill the placeholder |
| LE5 | Medium | Micro | LabScan reticle corners hardcode `rgba(255,255,255,0.9)` ×4 + raw 28 px (`LabScan.tsx:190–201`) | Token violation in an otherwise tokenized page | Add `--scan-reticle: rgba(255,255,255,0.9)` to tokens (theme-independent overlay-on-video is legitimately fixed) |
| LE6 | Polish | Components | Native file input beside custom inputs (`LabEntry.tsx:104–110`) | One raw OS control breaks the row's rhythm | Styled label-as-button pattern triggering the hidden input |
| LE7 | Polish | Micro | LabEntry inputs are `input-lg` (44 px) — the only 44 px controls in the app | Height band inconsistency (§4.2 control tokens) | Keep 44 px; migrate others up via `--control-h` |

### 3.9 Registry (`/registry`)

Screens: `registry/{theme}/{vp}/default.png` + `.verifier.png`, `operators-tab.png`, `token-minted.png`, print pair

| # | Sev | Cat | What's wrong | Impact | Exact fix |
|---|---|---|---|---|---|
| R1 | High | IA/Roles | No `getRole()` gate anywhere — verifiers see all admin forms (verified `default.verifier.png` identical to admin); server 403 would surface as "Save failed — check values" | Role-affordance leak + misdiagnosed failure on a compliance surface | Wrap forms in `getRole() === "admin"` (mirror BatchDetail's pattern); verifiers get read-only kiln cards |
| R2 | High | Feedback | `mintToken` swallows non-auth errors (`Registry.tsx:256–262` catch handles only AuthError) and has no busy state | Admin clicks Mint, nothing happens, no explanation — on a credentialing action | Add `busy` state to the button + error `StatusPill` on failure |
| R3 | Medium | Feedback | Form status pills auto-dismiss after 4 s (`Registry.tsx:38`; same in Dispatch/Projects) | Registrar glances away, outcome evaporates — audit-adjacent actions need persistent confirmation | Keep success visible until next interaction; only auto-dismiss purely cosmetic notices |
| R4 | Medium | Components | Required fields have no visual mark; only failure message "Fill required fields" reveals them | Error-recovery instead of error-prevention | Append `*` via `.micro` label suffix for `required: true` fields in the `Form` helper (`Registry.tsx:73`) |
| R5 | Medium | Micro | Kiln card caption truncates (`.cap` ellipsis, `styles.css:311–317`) on print-and-mount artifacts | Mounted card loses its type identity | `.cap { white-space: normal }` inside `.media-cell` print context; also add kiln_id as QR `<title>` |
| R6 | Medium | IA | "Type (open/closed)" free-text input for a two-value enum (`Registry.tsx:167`) | Data-quality leak at entry point | `<select>` with Open/Closed/— options (payload shape unchanged — still a string) |
| R7 | Polish | Micro | Minted token `fontSize: 12` raw + `wordBreak` inline (`Registry.tsx:270`) | Off-token in the token well | `className="mono"` already 12px; drop inline size |
| R8 | Polish | Print | Print shows empty form husks and QR cards overlapping (8 cm cells in an unchanged grid — verified print capture) | Print output looks broken | `@media print` hide `form.filters`/form Cards on Registry; give `.media-grid` `grid-template-columns: repeat(2, 8cm)` in print |

### 3.10 Projects (`/projects`)

Screens: `projects/{theme}/{vp}/default.png`, `empty.png`, `overflow.png`

| # | Sev | Cat | What's wrong | Impact | Exact fix |
|---|---|---|---|---|---|
| P1 | High | IA/Roles | Two admin forms above both tables for all roles (`Projects.tsx:273–304`); primary data buried a screen down | Verifier's landing view is forms they can't use | Role-gate the forms; move them below tables or behind a "New project / New parcel" disclosure `Button` |
| P2 | Medium | Color | ParcelMap is off-system: slate hexes (`ParcelMap.module.css:12,34,44,45`), Tailwind-blue polygon stroke `#3b82f6` (`ParcelMap.tsx:125`), phantom `--radius-m`/`--border-color`/`--bg-card`, raw 12/11 px fonts | The boundary-drawing surface — high-trust geography — looks pasted from another product | Convert wholesale: strokes `var(--indigo-600)`, fills `var(--surface-sunken)`, radii `var(--r-lg)`, fonts `var(--fs-12)` |
| P3 | Medium | Components | Status columns raw lowercase strings (`p.status`, `p.boundary_status` — `Projects.tsx:255,265`) | "draft"/"provisional" carry no signal weight; inconsistent with Batches | `StatusDot` mapping: active/verified→success, draft/provisional→warning |
| P4 | Medium | Micro | `parcel_uuid.slice(0, 8) + "..."` three ASCII dots (`Projects.tsx:260`) vs `…` elsewhere | Glyph drift visible in mono columns | Use `…` (single char) |
| P5 | Polish | Type | `<h2 style={{ fontSize: 16, marginBottom: 8 }}>` twice (`Projects.tsx:330,369`); Title Case headers ("Registered Projects", "Parcel Name", "Declared Acres (Optional)") vs sentence case app-wide | Inline-invented type + case drift | Add `.section-title` (fs-16/semibold/space-2) to `styles.css`; sentence-case the strings |
| P6 | Polish | Micro | `Area (m²)` header *and* `m²` in every cell (`Projects.tsx:263`) | Unit noise ×N rows | Cell renders `48,210.5` only |

### 3.11 Farmers (`/farmers`)

Screens: `farmers/{theme}/{vp}/default.png`, `empty.png`, `error.png`, `loading.png`, `overflow.png`

| # | Sev | Cat | What's wrong | Impact | Exact fix |
|---|---|---|---|---|---|
| F1 | High | IA | Detail panel renders below the pager with no scroll-into-view (`Farmers.tsx:175`) | Row click appears to do nothing — verified at 1440 (panel off-viewport) | `ref` + `scrollIntoView({ behavior: "smooth", block: "nearest" })` on select; better: side-panel or route |
| F2 | High | Components | KYC/Consent raw lowercase strings (`Farmers.tsx:92–93`) — `revoked` looks identical to `signed` | A *revoked consent* is a compliance red flag rendered with zero weight | `StatusDot`: verified/signed→success, pending→warning, revoked→error |
| F3 | Medium | Feedback | `openDetail` failure (non-auth) silently swallowed (`Farmers.tsx:57–66`) | Click → nothing, no error | Set an `err` state → inline error card |
| F4 | Medium | Feedback | Detail loading is bare "Loading…" text (`Farmers.tsx:177`) | Only non-skeleton loading state in the app | `Skeleton variant="card"` |
| F5 | Medium | Components | Labeled search + Search button vs Batches' placeholder-only live filter | Two search grammars in adjacent worklists | Keep the label (it's the better pattern); make Batches' FilterBar match with a visible label |
| F6 | Polish | Type | Masked values (`••••4821`, `asha····@okaxis`) not `.mono` in detail lists (`Farmers.tsx:244,262`) | Identifier discipline gap on PII — mono communicates "verbatim record" | Add `className="mono"` to document/payment `<li>` value spans |

### 3.12 Dispatch (`/dispatch`)

Screens: `dispatch/{theme}/{vp}/default.png` + `.verifier.png`, states

| # | Sev | Cat | What's wrong | Impact | Exact fix |
|---|---|---|---|---|---|
| DP1 | High | IA/Roles | "Register facility" admin form is the page lead for all roles (`Dispatch.tsx:211–273`, no `getRole()` check) | The page named Dispatch leads with a form most users can't submit; weight-flag triage demoted | Role-gate + move below the table (or disclosure), as P1 |
| DP2 | Medium | Micro | Weight column `1385 → 1381 kg` — flag signal only in a separate column; delta not shown for unflagged rows | The single most fraud-relevant number needs no eye-travel | Append delta to the weights cell: `1385 → 1381 kg (−0.3%)` `.micro`; keep pill for flagged |
| DP3 | Medium | Components | Status `in_transit` raw snake_case in StatusDot label (`Dispatch.tsx:177`) | Enum leakage to UI | Humanize: `In transit`, `Received`, `Draft` |
| DP4 | Polish | Micro | Facility count line "2 facilities registered." buried under form | Context without actionability | Move count into the card's `.micro` title row |

### 3.13 Print / evidence pack

Screens: `batch-detail/{theme}/print/print-emulated.png`, `_print/*.pdf`, `registry/*/print/print-emulated.png`

| # | Sev | Cat | What's wrong | Impact | Exact fix |
|---|---|---|---|---|---|
| PR1 | Critical | Print | Evidence images do not print — `@media print { button { display:none } }` (`styles.css:556`) hides `.thumbBtn` wrappers (verified: every media cell prints metadata-only) | The evidence pack ships without evidence | In the print block: `.thumbBtn { all: unset; display: block; }` before the button rule, or change selector to `button:not(.thumbBtn)` |
| PR2 | High | Print | Checklist group titles vanish (Accordion triggers are `<button>`s); mini-nav gone leaves unlabeled row groups | Auditor reading the PDF loses the C1–C10 chapter structure | Print-only static heading: render `<h3 className={styles.printTitle}>{g.label}</h3>` hidden on screen (`display:none`; `@media print { display:block }`) |
| PR3 | Medium | Print | No document header: no full batch UUID, printed-on timestamp, or signature block; breadcrumb is the only ID | A forensic artifact should self-identify | Print-only header div in BatchDetail: full UUID (mono), verdict, net credit, `Printed <date> UTC` |
| PR4 | Medium | Print | Verdict stamp relies on `printBackground`; plain print loses the clip-path fill | Verdict may print as unstyled text | Add `border: 2px solid currentColor` on `.stamp` in print block (survives background-less printing) |

### 3.14 Cross-cutting (verified by token-audit sweep)

| # | Sev | Cat | What's wrong | Impact | Exact fix |
|---|---|---|---|---|---|
| X1 | Critical | Color | Dark alias failure (blast radius: SealedVerdict, StatusDot everywhere, ComplianceChecklist `.ok/.blocking`, ConfirmModal, VerificationChain) | See §1.1 | `tokens.css` dark block: `--status-success: var(--status-success-fg); --status-warning: var(--status-warning-fg); --status-error: var(--status-error-fg); --status-inert: var(--basalt-400);` |
| X2 | High | Color | Phantom tokens silently falling back: `--radius-m/-s`, `--border-color`, `--bg-card` (ParcelMap, EvidenceGallery:79), `--r-pill` (HorizontalBarList:43), `--accent` (TemperatureChart) | Unstylable-by-token bugs invisible to hex greps | Replace with real tokens; add `--r-pill: 999px` to scale |
| X3 | High | Color | Dark primary-button hover: white text on `--action-primary-hover: #8b85ff` ≈ **3.0:1** (`tokens.css:149`) | Hover state fails AA exactly while the cursor is on it | Dark remap hover to `#5148e6` (same as light) or keep bg and darken label via `[data-theme="dark"] button.primary:hover { color: var(--basalt-950) }` — recommend the former |
| X4 | Medium | Components | Three button systems; primary twins differ (`10px 18px` vs `10px 16px` padding); `.neutral` duplicated verbatim | Same-named buttons render different widths across pages | Migrate remaining `className="primary"/"neutral"` usages to `ui/Button`; delete legacy blocks `styles.css:115–128, 590–607` |
| X5 | Medium | Layout | Spacing anti-scale: 48 off-scale + 92 raw-on-scale px in CSS; `marginTop: 14`×13 and `marginTop: 10`×10 inline; `gap: 4` label stack ×13 = missing `<Field>` component | The 8-pt grid exists only in tokens.css | Decide 10/14 policy (§4.2), extract `<Field label htmlFor>` into `ui/`, sweep with stylelint rule |
| X6 | Medium | Micro | Nine ad-hoc z-indexes (−1…100); chart tooltip (10) ties topbar (10) | Stacking is accidental, not designed | Add `--z-sticky:10 --z-dropdown:20 --z-tooltip:30 --z-scrim:55 --z-drawer:60 --z-overlay:90 --z-modal:100 --z-skiplink:200`; assign per Explore-agent table |
| X7 | Medium | Motion | Two motion vocabularies (`--duration-fast/--ease-productive` vs `--dur-micro/--ease-out`) used ~50/50; spinner `0.6s` + pulse `1.5s` raw ×3 | Guaranteed easing drift between adjacent components | Deprecate one set (keep `--dur-*`/`--ease-*` per repo doc); add `--dur-spin: 600ms`, `--dur-pulse: 1500ms` |
| X8 | Medium | Components | Four scrim implementations, two alphas (0.4 ×3, 0.7 lightbox); `#fff` on primary buttons ×2; print `#fff` | Overlay dimness varies by dialog | `--overlay-scrim` + `--overlay-scrim-strong` tokens + dark remaps; `--basalt-0` for button text |
| X9 | Medium | A11y | Icon-only targets 20–32 px (CopyId ~24, password eye ~20, iconBtn 32, hamburger ~30) vs 44 px proven by `.input-lg` | Mobile verifiers mis-tap in the field | `--control-h-md: 36px`, `--control-h-lg: 44px`; min 40×40 hit area on icon buttons (padding, not icon size) |
| X10 | Polish | Components | Dead component `ActivityTimeline` (zero non-test imports); StatTile vs MetricBlock overlap (fs-32 bold vs semibold) | Debt masquerading as system surface | Delete ActivityTimeline; fold StatTile onto MetricBlock `size="md"` + label/hint props |
| X11 | Polish | Micro | No `::selection` or scrollbar styling; default blue selection on indigo brand, OS-bright scrollbars on dark | Last-mile texture gap in dark especially | `::selection { background: var(--indigo-200); }` + dark remap; `scrollbar-color: var(--basalt-600) transparent` on `[data-theme="dark"]` |

---

## 4 · Systemic recommendations

### 4.1 Dark-theme remap (do first — it's ~10 lines)

Append to `[data-theme="dark"]` in `tokens.css`:

```css
--status-success: var(--status-success-fg);
--status-warning: var(--status-warning-fg);
--status-error:   var(--status-error-fg);
--status-inert:   var(--basalt-400);
--action-primary-hover: #5148e6;
```

This single block repairs BD1/CM1/B1/X1/X3 — the verdict stamp, all StatusDots, checklist statuses, modal warning, chain markers, and primary hover, in every dark capture.

### 4.2 Missing tokens (add before migrating anything)

```css
/* overlays */        --overlay-scrim: rgba(15,17,21,.4); --overlay-scrim-strong: rgba(15,17,21,.7);
/* dark remap */      --overlay-scrim: rgba(0,0,0,.6);    --overlay-scrim-strong: rgba(0,0,0,.75);
/* radii */           --r-pill: 999px;
/* z scale */         --z-sticky:10; --z-dropdown:20; --z-tooltip:30; --z-scrim:55;
                      --z-drawer:60; --z-overlay:90; --z-modal:100; --z-skiplink:200;
/* controls */        --control-h-md: 36px; --control-h-lg: 44px;
/* icons */           --icon-sm: 14px; --icon-md: 16px; --icon-lg: 18px;
/* motion */          --dur-spin: 600ms; --dur-pulse: 1500ms;
/* video overlay */   --scan-reticle: rgba(255,255,255,.9);
```

**Spacing decision (pick one, we recommend the second):** (a) bless the shadow scale with `--space-2-5: 10px` and `--space-3-5: 14px` — zero visual change, honest tokens; or (b) snap 10→`--space-2|3` and 14→`--space-3|4` per context during the sweep — one afternoon of nudging, and the grid becomes real. (b) is what a Linear-calibre bar demands; 1–2 px shifts at these sizes are imperceptible per-instance and compounding in rhythm.

### 4.3 Consolidations

1. **Buttons:** migrate all `className="primary"/"neutral"` to `ui/Button`; delete `styles.css:115–128, 590–607`. `.linkbtn` stays as the tab/tertiary voice but moves into `ui/Button` as `variant="link"`.
2. **Status:** StatusPill for chips-with-text, StatusDot for table cells; retire `.chip.ok/.warn/.err` (5 call sites, all in EvidenceGallery/Lightbox); replace Farmers/Projects/Dispatch raw strings per F2/P3/DP3.
3. **Copy affordance:** delete `CopyId` (Batches) → `CopyButton`.
4. **Stat values:** StatTile becomes a thin wrapper over MetricBlock (one weight: semibold; bold loses).
5. **Field:** extract `<Field label htmlFor children hint error>` into `ui/` — kills the 13× `gap: 4` stacks and standardizes label/error placement in one move (fixes L3/LE1 error-grammar drift structurally).
6. **CardError:** one component for the five dashboard copies + Batches/Farmers/Dispatch/Projects error cards (identical inline styles today).
7. **Delete:** `ActivityTimeline` (dead), the stale week-toggle comment (`CreditsOverTime.tsx:73`).

### 4.4 Migration order (dependency-safe)

1. Tokens (§4.1 + §4.2) — everything else lands on them.
2. Phantom-token fixes (X2) + ParcelMap conversion (P2) — pure find/replace, high visual yield.
3. Shell fixes S1/S2 + input focus (§1.5) — 4 lines total.
4. Print block rewrite (PR1–PR4) — self-contained in `styles.css`.
5. Component consolidations (§4.3) — page-by-page, verifiable with existing tests.
6. Spacing sweep (X5) — last, mechanical, behind a stylelint rule (`declaration-property-value-disallowed-list` on raw px for padding/margin/gap/font-size/border-radius/z-index outside tokens.css) so it never regresses.

---

## 5 · Prioritized roadmap

### Quick wins (< 1 day) — perception impact: **transforms dark mode + the two most-cited "broken" moments**
| Item | Fixes |
|---|---|
| Dark alias + hover remap (§4.1) | X1, X3, BD1, CM1, B1 |
| `.topbarRight { margin-left: auto }` | S1 |
| Input `:focus-visible` ring | §1.5 |
| Skip-link `z-index: 200` | S2 |
| Print `.thumbBtn` unset + checklist print titles | PR1, PR2 |
| `fmtCredit` grouping + shared `fmtDate` | D1, B5, BD11 |
| `--accent` → `--indigo-600` + `preserveAspectRatio` | BD9, BD10 |
| Remove ConfirmModal CopyButton + `danger` flag | CM2, CM3 |
| Breadcrumb labels ×4 | S3 |

### Medium (1–3 days) — perception impact: **role-correct, state-correct, feedback-correct**
| Item | Fixes |
|---|---|
| `ISSUED` verdict in SealedVerdict + chip removal | BD2 |
| Role-gate Registry/Dispatch/Projects admin forms + move below content | R1, DP1, P1 |
| Error feedback for verifyMedia/mint/openDetail + persistent form status | BD4, R2, R3, F3 |
| StatusDot for Farmers/Projects/Dispatch statuses | F2, P3, DP3 |
| Farmers detail scroll-into-view + skeleton | F1, F4 |
| Lightbox loading state + hints | LB1, LB2 |
| LabEntry per-field errors + batch context card | LE1, LE3 |
| `.tiles` responsive collapse + hole fix | BD8 |
| Dashboard KPI zero-vocabulary + empty-claim fix + CardError extraction | D2, D3, D5 |
| Phantom tokens + ParcelMap conversion | X2, P2 |
| Print header + Registry print cleanup | PR3, R8 |

### Structural (1–2 weeks) — perception impact: **"assembled" → "designed"; drift becomes impossible**
| Item | Fixes |
|---|---|
| Button/status/copy/stat consolidation + `<Field>` extraction | X4, §4.3 |
| Spacing sweep to the 8-pt grid + stylelint guard | X5 |
| Z-index scale + motion-vocabulary unification | X6, X7 |
| Control-height + icon-size tokens; 40 px+ touch targets | X9 |
| Evidence-verdict lifecycle (hide post-review/post-issuance controls, distinct chip axes) | BD3, BD5 |
| Overlay tokens + dark modal border | CM4, X8 |
| Selection/scrollbar/theme-color texture pass | X11, S7 |

---

## Appendix — contrast measurements (computed from token values)

| Pair | Theme | Ratio | Verdict |
|---|---|---|---|
| `--status-success` #067647 on `--surface-card` #1c1e27 | dark | **2.91:1** | FAIL (AA 4.5) |
| `--status-warning` #b54708 on #1c1e27 | dark | **3.06:1** | FAIL |
| `--status-error` #d92d20 on #1c1e27 | dark | **3.43:1** | FAIL |
| Stamp: #067647 on `--status-success-bg` #0b3a26 | dark | **2.24:1** | FAIL (the verdict) |
| Modal warning: #b54708 on #431a03 | dark | **2.77:1** | FAIL |
| `#fff` on `--action-primary-hover` #8b85ff | dark | **3.04:1** | FAIL (hover only) |
| `--status-warning-fg` #fdba74 on #431a03 | dark | 8.9:1 | pass (the `-fg/-bg` pairs are correct — only aliases fail) |
| `--indigo-600` on `--indigo-50` (active nav) | light | ≈4.3:1 | borderline for 13 px — acceptable at `--fw-medium`, watch it |
| `--indigo-400` #8b85ff on #1c1e27 | dark | 5.45:1 | pass (as documented) |
| `--basalt-500` on `--surface-card` #fff | light | 4.83:1 | pass |

Retracted during audit (verified as capture artifacts, not bugs): rail wordmark "clipping" and rail width variance — 1:1 viewport probes confirm a correct 240 px rail; full-page capture reflows layout ~9 px via scrollbar removal.
