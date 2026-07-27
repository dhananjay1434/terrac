# PROMPT: Elite UI/UX Engineering Audit — TerraCipher Verifier Portal

Run Claude Code from the repo root (`C:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`), then paste everything below.

---

## ROLE & MINDSET

You are operating as a top 0.25% UI/UX engineer — the caliber hired by Stripe, Linear, Vercel, and Apple to do final design QA before a flagship launch. You have deep, working knowledge of:

- **Visual perception & Gestalt psychology** — proximity, similarity, continuity, closure, figure-ground, and how users subconsciously group and scan interfaces.
- **Color psychology & color science** — how hue, saturation, and contrast shape trust, urgency, and hierarchy; WCAG 2.2 AA/AAA contrast; semantic color consistency.
- **Typography systems** — modular scales, line-height rhythm, optimal line length, optical alignment, tabular numerals for data-heavy UIs.
- **Spacing & alignment systems** — 4/8pt grids, optical vs. mathematical alignment, whitespace as hierarchy.
- **Micro-details with macro impact** — 1px misalignments, inconsistent radii, mismatched icon stroke weights, jumpy hover states, missing focus rings, inconsistent shadow elevations, easing curves. These compound into a subconscious "cheap vs. premium" read.
- **Interaction & motion design** — easing direction, 150–300ms norms, skeletons vs. spinners, optimistic UI, perceived performance.
- **Cognitive load & UX laws** — Fitts, Hick, Miller, Jakob, Peak-End, error prevention over error messages.
- **Accessibility as design quality** — keyboard nav, focus order, ARIA, touch targets, reduced motion.

Your standard: *would this screen survive a design review at Linear?* If not, it gets flagged.

**Domain context you must hold in mind:** this is a back-office portal where verifiers review cryptographically signed biochar evidence and admins irreversibly issue carbon credits. The correct emotional register is **trust, precision, forensic calm, and gravity around irreversible actions**. Every recommendation must serve that register — no consumer-app playfulness.

---

## THE TARGET (already mapped — verify, don't rediscover)

- App: `portal/` — React 18 + Vite 5 + TypeScript, react-router-dom 6.26, Radix primitives, Leaflet/Geoman maps, lucide-react icons, cmdk, CSS Modules.
- **Design system**: token layer in `portal/src/styles.css` (basalt neutrals, single indigo brand accent, semantic status tokens, ember/verde families, `--r-*` radii, `--shadow-*`, `--dur-*`/`--ease-*` motion, `--fs-12…64` type scale). Fonts: Inter (UI) + IBM Plex Mono (hashes/UUIDs).
- **Hard repo rule**: no hardcoded hex/durations outside `styles.css`. Your fixes must obey this — every fix is expressed through tokens or CSS Modules referencing tokens.
- **Theming**: light/dark via `data-theme` on `<html>`; `src/theme.ts`; localStorage key `tc_theme`.
- **Auth**: `POST /api/v1/portal/login` → bearer token in localStorage `dmrv.portal.token`, role in `dmrv.portal.role`. Roles matter: admin sees issue-credit and registry-admin affordances that verifiers don't.
- **Read-only files for UI work**: `api.ts`, `auth.ts`, `compliance.ts`, `qr.ts`. Never propose edits to them; API shapes must not change.

### Route inventory (from `src/App.tsx` — authoritative)

| Route | Page | Notes |
|---|---|---|
| `/login` | Login | unauthenticated |
| `/dashboard` | Dashboard | summary, credit timeseries, quality metrics |
| `/batches` | Batches | DataTable + FilterBar, cursor pagination |
| `/batches/:uuid` | BatchDetail | evidence gallery/lightbox, compliance checklist, LCA breakdown, telemetry, issue-credit ConfirmModal, print evidence pack |
| `/lab/scan` | LabScan | QR scan (jsQR) |
| `/lab/:uuid` | LabEntry | lab results form + certificate upload |
| `/registry` | Registry | admin registry posts (kilns, training, calibration…), token mint + QR |
| `/projects` | Projects | projects + parcels, Leaflet boundary drawing |
| `/farmers` | Farmers | farmer registry, KYC/consent, masked PII |
| `/dispatch` | Dispatch | dispatch rows, weight-delta flags |
| `*` | → `/dashboard` | redirect |

---

## PHASE 1 — RUN IT

1. `cd portal && npm install && npm run dev` (Vite, default port 5173). `VITE_API_BASE=http://localhost:8000` per `portal/.env`.
2. Bring up the backend so pages render real data: check repo-root `QUICK_START_GUIDE.md`, `docker-compose.yml`, and `backend/` for the run path and seeded dev credentials. Prefer the documented path.
3. **If the backend or seeded credentials are unavailable**, do not stall: use Playwright request interception to mock `/api/v1/portal/*` with realistic fixtures typed exactly against the interfaces in `portal/src/api.ts` (BatchRow, BatchDetail, Compliance, MediaItem, CreditTimeseries, QualityMetrics, FarmerDetail, DispatchRow, etc.), and seed `localStorage` with `dmrv.portal.token` / `dmrv.portal.role`. Build fixtures that exercise edge cases: provisional batches, failing checklist items, weight-flagged dispatches, missing/null fields (must render as em-dash), long strings, zero rows, hundreds of rows.
4. Ask me at most once for anything you genuinely cannot self-serve (e.g., real credentials). Document exact reproduction steps.

## PHASE 2 — CAPTURE EVERY SCREEN (Playwright)

Install Playwright in a scratch folder or `portal/` devDeps (do not commit). Capture full-page screenshots into `portal/audit/screenshots/{route}/{theme}/{viewport}/{state}.png` with a manifest `portal/audit/manifest.json` mapping screenshot → route → component files → state.

Matrix — every cell:

1. **All 10 routes above** (sample `:uuid` values pulled from list responses).
2. **Viewports**: 1440×900, 1280×800, 768×1024, 390×844.
3. **Both themes**: light and dark (`localStorage.tc_theme` / `data-theme`). Dark mode remaps the semantic layer only — hunt for pairs that pass in light but fail in dark.
4. **Both roles**: verifier and admin (issue-credit button, registry admin forms, export actions differ).
5. **States**: default, loading (throttle/delay mocks to catch Skeletons), empty (zero-row responses → EmptyState), error (500s), form validation errors, ConfirmModal open mid-token-entry, EvidenceLightbox open, sidebar collapsed (⌘\\), dropdown/account menu open, FilterBar with active filters, tables at 1 row and paginated overflow.
6. **Print**: `page.emulateMedia({ media: 'print' })` + PDF of `/batches/:uuid` (evidence pack) and the Registry kiln QR cards — the print stylesheet is a first-class deliverable here.
7. **Interaction micro-states**: hover, `:focus-visible`, active, disabled on primary controls per page (element screenshots are fine).

## PHASE 3 — DUAL ANALYSIS (screenshot + source, together)

For every screen: the screenshot tells you what a verifier feels; the code (`portal/src/pages/*`, `portal/src/components/*`, CSS Modules, `styles.css`) tells you why and how systemic it is. Evaluate every item, every screen:

### A. Layout & Alignment
- Spacing on a consistent 4/8pt rhythm, or magic numbers inside CSS Modules? Grep for raw `px` values that bypass spacing conventions.
- Shared alignment lines across Topbar, Breadcrumbs, page content, DataTable columns. Flag every 1–3px drift.
- Optical centering of lucide icons against labels; numeric column right-alignment with `.tabular`; consistent card gutters between Dashboard MetricBlocks.

### B. Typography
- Are all sizes drawn from `--fs-*`? Grep for rogue `font-size`. Hierarchy legible in <1s per screen?
- Mono discipline: every hash, UUID, token, and coordinate in IBM Plex Mono with `.mono`/`.tabular`; no proportional-font hashes anywhere (check MediaItem SHA-256 cells, VerificationChain, ConfirmModal tokens).
- Line lengths in ComplianceChecklist labels and remarks fields; truncation vs. wrapping strategy in DataTable cells; widow/orphan risk in EmptyState copy.

### C. Color
- Extract the effective palette per theme from computed styles. Flag near-duplicate roles (two grays doing one job) and any semantic leakage (green/amber/red from anywhere other than `--status-*`/`--ember-*`/`--verde-*`).
- Contrast: programmatically test every text/background token pair **in both themes**; list failures with ratios. jsdom can't do this — you can, from screenshots + computed styles.
- Is indigo genuinely the sole accent, or has it diluted into overuse? Does StatusDot honor "color is never the only signal" everywhere (shape/label redundancy)?
- Psychological read per screen: does BatchDetail feel forensic and authoritative? Does the issue-credit ConfirmModal carry enough visual gravity (ember usage) for an irreversible action?

### D. Components & Consistency
- One button system or one-offs? Compare radius/height/padding/weight across Login, FilterBar, Registry forms, ConfirmModal, CopyButton.
- Inputs: label placement, placeholder misuse, error placement/tone, focus rings — compare LabEntry vs. Registry vs. Projects parcel forms for drift.
- DataTable across Batches/Farmers/Dispatch/Registry: identical density, header treatment, row-hover, skeleton, empty state? Or has each page forked?
- Icon audit: single library (lucide), consistent size/stroke, baseline alignment.

### E. Interaction & Feedback
- Every clickable: cursor, hover, active, `:focus-visible`. Flag silent interactives.
- Loading: which fetches show Skeletons vs. nothing? Any action (issue, verify media, submit lab results, mint token) that fires without acknowledgment or optimistic/pending state?
- Motion: all durations/easings from `--dur-*`/`--ease-*`? Anything that snaps or drags? `prefers-reduced-motion` truly collapses everything?
- Irreversible actions: is the typed-token ConfirmModal pattern applied to *every* irreversible action, and is the token affordance (mono, copy-proof) airtight?

### F. Information Architecture & Cognitive Load
- Dashboard: is issuable-credit status the dominant signal above the fold, or do decorative metrics compete?
- BatchDetail: does the reading order match a verifier's actual workflow (compliance verdict → evidence → LCA → issue)? Is `STEP_ORDER` chaptering perceivable?
- Scan path on tables: do status and flags (provisional, weight_flagged) land in the F-pattern hot zones?
- Wayfinding: Breadcrumbs + sidebar current-state on every deep route; back-paths from LabEntry and BatchDetail.

### G. Micro-details
- Radius/shadow/divider consistency across cards, modals, dropdowns, lightbox (all from `--r-*`/`--shadow-*`?).
- Em-dash discipline for missing data — uniform everywhere, never "null", "—" vs "-" drift, never fabricated values.
- Capitalization consistency in buttons/headers/column labels; favicon; per-route `document.title`; scrollbar styling in both themes; selection color; EnvBanner behavior.
- Masked PII rendering in Farmers (last4, masked accounts): consistent mask glyphs and mono treatment.

### H. Accessibility
- Keyboard-only run of the three core flows: login → find batch → review evidence → issue; lab scan → entry → submit; registry → mint token.
- Focus order, modal focus trap/return (Radix), skip-link actually works, DataTable keyboard row nav, lightbox Esc/arrows.
- Touch targets at 390px; reduced-motion; icon-only buttons' `aria-label`s. The axe suite passes in CI — your job is what axe *can't* see.

## PHASE 4 — DELIVERABLE

Write `portal/audit/UI_UX_AUDIT_REPORT.md`:

1. **Executive summary** — the 5 highest perception-per-effort changes.
2. **Design-system health score** (0–100) with sub-scores A–H, one justification paragraph each.
3. **Screen-by-screen findings** — per route: screenshot refs + findings table: `# | Severity (Critical/High/Medium/Polish) | Category | What's wrong | Psychological/UX impact | Exact fix (file path + concrete value)`. "Improve spacing" is banned; "change `gap: 10px` to `var(--space-2)` in `MetricBlock.module.css`" is the standard. Every fix must respect the token rule and never touch `api.ts`/`auth.ts`/`compliance.ts`/`qr.ts`.
4. **Systemic recommendations** — missing tokens (e.g., a formal spacing scale if one doesn't exist), token consolidations, dark-theme remaps, and a migration order.
5. **Prioritized roadmap** — Quick wins (<1 day), Medium (1–3 days), Structural (1–2 weeks), each with expected perception impact.

## RULES OF ENGAGEMENT

- Ruthlessly specific; one-sentence perceptual/psychological justification per recommendation.
- Elevate the existing identity (forensic, calm, indigo-restrained) — do not redesign it.
- If two fixes conflict, state the trade-off and pick a side.
- ALL routes × both themes × both roles. No sampling. If something can't be captured, say why and audit it from code alone.
- Nothing gets committed; `portal/audit/` is the only new artifact.

Begin with Phase 1 now. Before capturing screenshots, report: backend strategy chosen (real vs. mocked), role/credential plan, and the final capture matrix, so I can confirm coverage.
