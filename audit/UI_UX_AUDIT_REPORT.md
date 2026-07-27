# TerraCipher Portal — Elite UI/UX Engineering Audit

**Method:** Ran the portal locally (Vite dev + FastAPI on an isolated seeded SQLite), enumerated all routes from `src/App.tsx`, and captured **66 full-page screenshots** with Playwright across 11 screens × 4 viewports (1440/1280/768/390) × light+dark. Each screen was analyzed against the rendered pixels **and** the source that produced it. Screenshots: `audit/screenshots/{route}/{viewport}/{theme}.png`; index: `audit/manifest.json`.

**One-line verdict:** This is a **well-built product on a genuinely mature design-token foundation** — it would *not* embarrass itself in a Linear review. It falls short of flagship in a **small, fixable set** of places: one real layout bug in the top bar, load-time layout shift, native form-control chrome breaking the component system, a handful of copy/label defects, and a non-responsive data table. None are structural; most are <1-day fixes.

---

## 1. Executive Summary — 5 highest perception-per-effort fixes

| # | Fix | Why it matters | Effort |
|---|-----|----------------|--------|
| 1 | **Right-align the top-bar controls.** Add `margin-left:auto` to `.topbarRight` (`AppShell.module.css:205`). Today, on desktop the theme/help/**account+sign-out** icons sit at the far *left* because their only right-push spacer (`.topbarWordmark { margin-right:auto }`) is `display:none` on desktop (`:178`). | Jakob's Law: users reflexively look **top-right** for account/settings/sign-out. Mis-placed, it reads as "prototype." Highest impact, ~1 line. | 15 min |
| 2 | **Kill the load-time layout shift (CLS).** The Inter variable font and `lucide-react` icons pop in after paint, so the rail wordmark clips to "TerraC" and nav icons appear late, resizing content. `font-display: optional`/preload + reserve icon box + render the shell with a stable width. | Layout that visibly reflows on every load is the #1 subconscious "cheap" signal. Affects **every** screen. | 2–4 hr |
| 3 | **Replace native `<input type=date>` and `<input type=file>` chrome** (Registry, Lab entry, Dispatch). They render OS-default and break the otherwise-consistent input system. | Similarity/consistency: one foreign-looking control per form makes the whole form feel unfinished. | 3–5 hr |
| 4 | **Fix copy/label defects:** "1 batches" → "1 batch" (pluralize in `HorizontalBarList` usage), truncated section label "Field evidence (per ru…", raw `Lantana_camara` feedstock. | Micro-details that a top-tier reviewer flags instantly; near-zero effort each. | 1–2 hr |
| 5 | **Make the batches/dispatch tables responsive** (horizontal-scroll container or card-reflow < 768px). Today 6–8 columns compress into 390px and headers wrap. | Mobile is a first-class context for field/verifier users; a squished table is unusable. | 3–6 hr |

---

## 2. Design-System Health Score

### **Overall: 81 / 100** — "Strong system, flagship-adjacent; held back by polish + one shell bug."

| Cat | Area | Score | One-paragraph justification |
|-----|------|-------|------------------------------|
| A | Layout & Alignment | **80** | Disciplined 8-pt grid (`--space-1..8`), a fixed 240px rail, consistent card widths and section rhythm. Docked for the top-bar right-align bug (A1), visible **CLS on load** (A2), and a fixed `--content-max: 1040px` that leaves wide screens left-weighted with a large right void. |
| B | Typography | **86** | A real modular scale (`--fs-12..64`, 4 weights, 3 line-heights) with clear H1→body→caption hierarchy on every screen; monospace (`IBM Plex Mono`) correctly reserved for IDs/codes. Minor: `--fs-13` is a tweener rarely justified; a couple of headings could use tighter tracking. |
| C | Color | **88** | Mature semantic layer (surface/border/text/status/action) over a calibrated primitive scale, **every hue annotated with its WCAG ratio**, full dark-mode remap. Docked for a `--verde-*` scale that duplicates `--green-*`, and inconsistent status *presentation* (colored pills in Batches vs. plain lowercase "active" in Projects). |
| D | Components & Consistency | **78** | One button/card/tab/badge system applied consistently; Radix primitives for menu/dialog/tabs. Docked for **native date/file inputs** breaking the input system, the two status-rendering conventions, and the "1 batches" pluralization. |
| E | Interaction & Feedback | **81** | Hover/focus states, skeleton loaders, **per-section error cards with Retry**, and a global `:focus-visible` ring. Docked for **two competing motion-token sets** (`--duration-*`/`--ease-productive` vs `--dur-*`/`--ease-out`) inviting inconsistent easing, and 32×32px icon buttons (below the 44px touch target). |
| F | IA & Cognitive Load | **83** | Clean primary nav, tabbed sub-navigation, a 4-step batch stepper, and genuinely good empty states with guidance. Docked for the very dense batch-detail page (could use in-page anchors) and the mis-placed top-bar controls. |
| G | Micro-details | **73** | Mostly tidy, but this is where the gaps cluster: pluralization, truncated labels, native-control chrome, a **blank gray map with no loading/empty state**, empty Min/Max-temp tiles despite telemetry, and the FOUT wordmark clip. |
| H | Accessibility | **84** | Skip link, `aria-label`s throughout, Radix (focus-trap/Esc/outside-click for free), `aria-pressed` on the theme toggle, and a graceful "camera unavailable → paste UUID" fallback. Docked for sub-44px touch targets and the non-responsive table. |

---

## 3. Screen-by-Screen Findings

Severity: **Critical** (broken/unusable) · **High** (clearly sub-flagship) · **Medium** (noticeable) · **Polish** (micro).

### 3.0 AppShell (chrome on all 9 authed screens)
| # | Sev | Cat | What's wrong | Impact | Fix |
|---|-----|-----|--------------|--------|-----|
| 0.1 | **High** | IA/Layout | Top-bar controls (theme/help/**account+sign-out**) render far-left on desktop. Root cause: `.topbarWordmark{margin-right:auto}` is the only right-spacer and it's `display:none` on desktop (`AppShell.module.css:172,178`). | Sign-out/account not where anyone looks (Jakob's Law). | `AppShell.module.css:205` — add `margin-left:auto` to `.topbarRight` (or `justify-content:space-between` on `.topbar:155`). |
| 0.2 | **High** | Micro/Perf | FOUT + lazy icons cause visible layout shift: rail wordmark clips to "TerraC"/"TerraCiphe" and nav icons pop in late (compare `batches/desktop/light` vs `farmers/desktop/light`). | Reflow-on-load reads as unpolished on every visit. | Preload Inter + `font-display:optional`; give `.iconBtn`/nav-icon a fixed box; ensure rail renders at `--rail-w` pre-hydration. |
| 0.3 | **Medium** | A11y | `.iconBtn` is 32×32px (`AppShell.module.css:213-214`); mobile touch target minimum is 44×44. | Harder taps on tablet/phone for field users. | Bump to 40–44px hit area (padding or min-size) at `≤768px`. |
| 0.4 | **Polish** | Layout | Sticky rail is full-height per viewport; on very tall pages the "Collapse" control floats mid-page in full-page capture (sticky, cosmetic only). | None in real use; noted to pre-empt a false bug report. | No action. |

### 3.1 `/login`
| # | Sev | Cat | What's wrong | Impact | Fix |
|---|-----|-----|--------------|--------|-----|
| 1.1 | **Polish** | Layout | Left form card and right brand panel are near-equal height but not locked to a shared baseline; the brand-panel body copy is `--text` on dark at a smallish size. | Slightly loose two-up composition. | Equalize card heights (`align-items:stretch`) and bump brand copy to `--fs-14`/higher line-height. |
| 1.2 | **Polish** | A11y/Interaction | Password reveal is an icon-only control; verify `aria-label` + visible focus. | Minor a11y. | Confirm `aria-label="Show password"` + `:focus-visible`. |

### 3.2 `/dashboard`
| # | Sev | Cat | What's wrong | Impact | Fix |
|---|-----|-----|--------------|--------|-----|
| 2.1 | **Medium** | Micro/Copy | Blocker rows read **"1 batches"** (should be "1 batch"). Source: `HorizontalBarList` `valueSuffix="batches"` is static (`IssuanceBlockerCard.tsx`). | Grammatical defect on the flagship screen. | Pass a pluralizing formatter, or make `valueSuffix` a `(n)=>string`; render `n===1 ? "batch":"batches"`. |
| 2.2 | **Low/Verify** | Interaction | Under rapid load the dashboard showed **all sections in the error state** (`dashboard/desktop/dark`); likely the backend `_rate_limit` middleware under burst. | If reproducible in normal use, users hit spurious "Failed to load". | Verify per-user rate-limit headroom for the dashboard's ~4 parallel fetches; consider a single batched metrics call. |
| 2.3 | **Polish** | Layout | The three quality sub-cards have generous internal whitespace; Pyrolysis card is much taller than its content. | Slightly sparse. | Tighten card min-heights or align the stat tiles' baseline. |
| — | ✔ Strength | — | The 3 reworked charts (weekly diverging credits, permanence **durability-tier split**, ranked **blocker bar-table** with humanized labels + counts) read cleanly and on-brand. | — | — |

### 3.3 `/batches`
| # | Sev | Cat | What's wrong | Impact | Fix |
|---|-----|-----|--------------|--------|-----|
| 3.1 | **High** | Responsive | 6-column table doesn't reform < 768px; headers wrap and data would be badly cramped (`batches/mobile/light`). | Unusable on phone. | Wrap in `overflow-x:auto` container, or reflow to stacked cards at `≤768px`. |
| 3.2 | **Polish** | Micro | Small "Batches" breadcrumb above the "Batches" H1 is redundant on a top-level page. | Duplicated label. | Drop the breadcrumb on top-level routes, keep it on detail pages. |
| — | ✔ Strength | — | Excellent status semantics (green "Issuable" / amber "Provisional" dots), correctly-pluralized "1 reason", monospace IDs with copy affordance, right-aligned numeric credit column, clear tabs + filters + pagination. | — | — |

### 3.4 `/batches/:uuid` (detail)
| # | Sev | Cat | What's wrong | Impact | Fix |
|---|-----|-----|--------------|--------|-----|
| 4.1 | **Medium** | Data/Micro | **Min temp / Max temp** stat tiles show "—" despite burn telemetry being present (constant ~665°C rendered). | Looks like missing data on a compliance screen. | Derive min/max from the parsed telemetry series; only show "—" when truly absent. |
| 4.2 | **Medium** | Micro | Right-rail compliance summary label truncates: "Field evidence (per ru… 12/12". | Truncated label on a verifier-critical panel. | Widen the label column or wrap; avoid mid-word ellipsis. |
| 4.3 | **Polish** | Layout | "LCA summary" and "Credit formula" are side-by-side but unequal height (LCA card has large empty tail). | Minor imbalance. | `align-items:stretch` or move a field to balance. |
| 4.4 | **Polish** | Density | Page is ~3000px tall; all compliance categories expanded. | Long scroll to Issued step. | Consider anchor links from the stepper, or collapse "OK" groups by default. |
| — | ✔ Strength | — | Strong 4-step stepper, prominent PROVISIONAL status hero, disabled "Not yet issuable" CTA, red-bordered MISSING lab rows, human-label + raw-code checklist. | — | — |

### 3.5 `/lab/scan`
| # | Sev | Cat | What's wrong | Impact | Fix |
|---|-----|-----|--------------|--------|-----|
| 5.1 | **Polish** | Layout | Scanner viewport is right-offset, leaving the left half empty at desktop. | Off-center focal point. | Center the scanner column, or add a left-side help/recent-scans panel. |
| — | ✔ Strength | — | Camera-unavailable path degrades gracefully to a "paste batch UUID" input — exemplary error prevention. | — | — |

### 3.6 `/lab/:uuid` (entry)
| # | Sev | Cat | What's wrong | Impact | Fix |
|---|-----|-----|--------------|--------|-----|
| 6.1 | **Medium** | Components | Native `<input type=file>` "Choose file / No file chosen" breaks the custom control system. | Foreign chrome in an otherwise-clean form. | Custom file-drop/button styled to the input system; keep the native input visually hidden. |
| 6.2 | **Polish** | Layout | Form uses only the left ~40%; the "Rules checked on submit" card floats right with a wide gap. | Unbalanced canvas. | Constrain to a centered 2-col form/aside grid with a defined gutter. |
| — | ✔ Strength | — | Surfacing validation rules *before* submit is excellent error-prevention UX. | — | — |

### 3.7 `/registry`
| # | Sev | Cat | What's wrong | Impact | Fix |
|---|-----|-----|--------------|--------|-----|
| 7.1 | **Medium** | Components | Native `<input type=date>` (`dd-mm-yyyy` + OS calendar) in Supervisor-visit / Scale-calibration clashes with custom inputs. | Inconsistent form controls. | Adopt one date-input treatment (styled wrapper or a JS date picker matching tokens). |
| 7.2 | **Polish** | Layout | Supervisor-visit vs Scale-calibration cards are unequal height. | Minor. | Equalize or align Save buttons to a shared baseline. |
| — | ✔ Strength | — | Clean tabbed forms, QR kiln-card generation, `(C8)` methodology hints with info icons. | — | — |

### 3.8 `/projects`
| # | Sev | Cat | What's wrong | Impact | Fix |
|---|-----|-----|--------------|--------|-----|
| 8.1 | **High** | Micro/Feedback | The Leaflet/OSM map renders as a **blank gray box** with floating draw tools and no loading/empty/error state (`projects/desktop/light`). | If tiles are slow/blocked it looks broken; even normally there's no skeleton. | Add a map loading skeleton + a tile-error fallback ("map unavailable — paste GeoJSON below"); style the map container border to match cards. |
| 8.2 | **Medium** | Consistency | Registered-Projects "Status" shows plain lowercase **"active"** text, unlike the colored status pills in Batches. | Two status languages across tables. | Reuse the Batches status-pill component for all status cells. |
| 8.3 | **Polish** | Copy | Feedstock shown as raw `Lantana_camara` (underscore). | Machine-string leak. | Humanize/italicize species names ("*Lantana camara*"). |

### 3.9 `/farmers`
| # | Sev | Cat | What's wrong | Impact | Fix |
|---|-----|-----|--------------|--------|-----|
| 9.1 | **Polish** | Responsive | 6-column table (Name/Mobile/Village/KYC/Consent/Registered) will need the same mobile treatment as Batches (3.1). | Mobile cramping when populated. | Shared responsive-table solution. |
| — | ✔ Strength | — | Clean search + a genuinely helpful empty state ("wait for field devices to sync"). Correct loaded-shell state (full wordmark + all icons) confirms the target look. | — | — |

### 3.10 `/dispatch`
| # | Sev | Cat | What's wrong | Impact | Fix |
|---|-----|-----|--------------|--------|-----|
| 10.1 | **High** | Responsive | 8-column table (Dispatch/Kind/Status/Weight/Reconciliation/Driver/Truck/Created) — the widest table; mobile reflow is essential. | Worst-case mobile cramping. | Priority target for the responsive-table fix. |
| 10.2 | **Polish** | Consistency | Native `<select>` "Type = Artisanal" chrome vs custom dropdowns elsewhere (Batches filters use a styled dropdown). | Mixed select styling. | Standardize on one select treatment. |

---

## 4. Systemic Recommendations (tokens & structure)

1. **Consolidate the two motion systems.** `tokens.css` ships `--duration-fast/standard` + `--ease-productive/expressive` (`:50-53`) **and** `--dur-micro/trans/panel` + `--ease-out/in` (`:109-113`). Pick one naming, alias the other for back-compat, and document "entrances = ease-out 200ms, exits = ease-in 120ms." Prevents drift where two components animate the same interaction differently.
2. **Remove the duplicate color scale.** `--verde-*` (`:73-75`) mirrors `--green-*` (`verde-700 == green-700`). Delete `--verde-*` and point any references at `--green-*`; a near-duplicate hue doing the same job is exactly the "three slightly different greens" smell.
3. **One status-presentation primitive.** Extract the Batches status pill (dot + label + semantic color) into a shared `StatusPill`-driven cell and use it in Projects/Dispatch/Farmers so "active/provisional/issued/in-transit" always look identical.
4. **One form-control layer.** Wrap native `date`/`file`/`select` in token-styled components (or a headless lib) so no OS chrome ever surfaces. This is the single biggest "consistency" win.
5. **A responsive-table pattern.** One `<DataTable>` that (a) `overflow-x:auto` with a sticky first column ≥768px→<1024, and (b) reflows to labeled cards <768px. Adopt across Batches/Dispatch/Farmers/Projects.
6. **Load-stability budget.** Preload Inter + primary icon set, reserve icon boxes, and gate first paint on the shell width. Target CLS < 0.02.
7. **Pluralization helper.** A tiny `plural(n, "batch", "batches")` used by every count label (fixes 2.1 and prevents recurrence).

Migration order: **4 & 5 first** (they touch the most screens and carry the most perceived-quality lift), then **3**, then **1/2/6/7** as cleanups.

---

## 5. Prioritized Roadmap

**Quick wins (< 1 day, high perception lift)**
- Top-bar right-align (0.1) — 1 line.
- Pluralization + truncated-label + `Lantana_camara` copy fixes (2.1, 4.2, 8.3).
- Min/Max-temp derivation (4.1).
- Map loading/error state + container styling (8.1).
- Touch-target bump to ≥40px (0.3).

**Medium (1–3 days)**
- Custom date/file/select controls (3, 6.1, 7.1, 10.2).
- Responsive-table pattern across the 4 tables (3.1, 9.1, 10.1).
- Shared StatusPill cell for Projects/Dispatch (8.2).
- CLS/FOUT elimination (0.2).

**Structural (1–2 weeks)**
- Motion-token consolidation + documented easing/duration usage (systemic 1).
- Color-scale de-dup + status-presentation unification (systemic 2–3).
- Batch-detail information architecture (stepper anchors / collapsible OK-groups) (4.4).
- Revisit `--content-max` for wide screens (a reviewed task per the token comment).

---

### Appendix — reproduction
- Backend: `DATABASE_URL="sqlite+aiosqlite:///<path>/audit.db" DMRV_ALLOWED_ORIGIN="http://localhost:5173" python -m uvicorn app_factory:app --port 8000` (after `python seed_demo_rich.py` against the same SQLite).
- Frontend: `VITE_API_BASE="http://localhost:8000" npm run dev -- --port 5173` (from `portal/`).
- Auth: seeded `demo@terracipher.local` / `demo-pass-12345`.
- Capture: `scratchpad/runner/capture.mjs` (Playwright Chromium) → `audit/screenshots/**` + `audit/manifest.json` (66 shots).
