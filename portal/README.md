# TerraCipher Verifier Portal

React 18 + Vite + TypeScript back-office where verifiers review
cryptographically signed biochar evidence and admins permanently issue carbon
credits. No CSS framework — a token system in `src/styles.css` plus CSS
Modules per component.

## Commands

```bash
npm run dev        # local dev server
npm test           # vitest (jsdom), includes the axe a11y suite
npm run typecheck  # tsc --noEmit
npm run build      # typecheck + vite build
npm test -- --coverage
```

## Design tokens (`src/styles.css`)

- **Neutrals**: `--basalt-0…950` (cool gray scale).
- **Brand**: `--indigo-600` (sole brand accent), `--indigo-50`.
- **Semantic status** (the only place green/amber/red may come from):
  `--status-success[-fg/-bg]`, `--status-warning[-fg/-bg]`,
  `--status-error[-fg/-bg]`, `--status-inert`; plus `--ember-*` (banners,
  scan reticle, high-stakes confirm) and `--verde-*`.
- **Surfaces/text**: `--surface-page/card/brand-subtle`,
  `--text-primary/secondary/tertiary`, `--border-subtle/strong/hair`.
- **Shape/elevation/motion**: `--r-xs…xl`, `--shadow-sm/md/modal`,
  `--dur-micro/trans/panel`, `--ease-out/in`.
- **Type**: `--fs-12…64`, `--fw-*`, `--lh-*`; `.mono`/`.tabular` utilities.
  Fonts are self-hosted via @fontsource (Inter for UI, IBM Plex Mono for
  hashes/UUIDs/tokens) — no runtime CDN.

**Rule: no hardcoded hex/durations outside `styles.css`.** New CSS references
tokens only (grep-enforced in review).

## Theming

Light/dark via `data-theme` on `<html>`. `src/theme.ts` exposes
`getTheme/setTheme/initTheme` (localStorage `tc_theme`, falls back to OS
preference). Dark mode remaps only the semantic layer — primitives untouched.

## Component inventory (`src/components/`)

- `AppShell/` — shell chrome: Sidebar (collapsible, ⌘\\), Topbar (theme
  toggle, account menu), Breadcrumbs, EnvBanner (shows only when
  `VITE_ENV === "sandbox"`), skip-to-content link.
- `DataTable/` — generic table: sticky header, keyboard row nav, skeleton +
  empty states. `FilterBar/` emits a `FilterPatch` discriminated union.
- `StatusDot/`, `SealedVerdict/`, `MetricBlock/`, `VerificationChain/` —
  status and numeric-authority primitives (color is never the only signal).
- `ProvenanceTile/`, `LcaBreakdown/` — render ONLY fields the API exposes;
  missing data is an em-dash, never fabricated.
- `ComplianceChecklist/` — accordion over `compliance.ts` grouping (that
  module is the single source of truth; never reimplement it).
- `EvidenceGallery/` + `EvidenceLightbox/` — case-file chapters ordered by
  `STEP_ORDER`/`STEP_TITLES` (exported from `pages/BatchDetail.tsx`), forensic
  metadata per cell (SHA-256, GPS, timestamp, verified chip) that survives
  dead thumbnails.
- `ConfirmModal/` — typed dynamic-token confirmation (e.g. `ISSUE-abc123`)
  for irreversible actions. `ActivityTimeline/`, `CopyButton/`,
  `EmptyState/`, `Skeleton/`.

## Accessibility posture

- Axe (WCAG 2.x A/AA) runs in CI via `src/__tests__/a11y.test.tsx` over every
  page — zero violations is the bar. jsdom can't compute color-contrast;
  contrast is enforced at the token level (every documented pair ≥ 4.5:1).
- Global `:focus-visible` ring (`--indigo-600`); focus trap + return in all
  dialogs (Radix); `prefers-reduced-motion` collapses every animation and
  transition; icon-only buttons carry `aria-label`s.
- Print (`@media print` + A4 `@page`): chrome hidden, BatchDetail prints as
  an evidence pack, kiln QR cards at 8cm, mono preserved for hashes.

## Hard rules for contributors

`api.ts`, `auth.ts`, `compliance.ts`, `qr.ts` are read-only for UI work; API
call shapes must not change; never log tokens/hashes/PII; blob URLs from
`fetchMediaUrl` are revoked on unmount; clipboard writes are user-initiated.
