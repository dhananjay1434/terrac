# Remediation Result — TerraCipher Portal UI/UX

Execution record for `REMEDIATION_BLUEPRINT.md` (v2). Every phase's code is
merged to `origin/main` and passes the full gate (`tsc` + `vitest` + `vite build`).

## Gate (final, HEAD = `e0ecc30`)

| Check | Result |
|---|---|
| `tsc --noEmit` | clean (exit 0) |
| `vitest run` | **357 passed** / 64 files |
| `vite build` | success |

## Acceptance greps (P8.6.3)

| Check | Expected | Actual |
|---|---|---|
| `className="primary"` / `className="neutral"` in `*.tsx` | 0 | 0 |
| literal `"..."` in `src/pages` | 0 | 0 |
| `slice(0, 10)` in pages/components | 0 | 0 |
| raw `0.6s` / `1.5s` in `*.css` | 0 | 0 |

Plus the permanent guard `src/tokens/no-raw-values.test.ts`: fails CI on any
raw spacing px (`padding`/`margin`/`gap`) or hex color outside `tokens.css`.

## Phase manifest

| Phase | Scope | Status | Commit |
|---|---|---|---|
| P1 | Token layer (dark aliases, scales, phantom-token guard) | ✅ | `ad3ea1b` |
| P2 | Shell & focus (topbar right-align, focus rings) | ✅ | `a60d12d` |
| P3 | Formatting core (`fmtCredit`/`fmtDate`/`fmtKg`/`fmtPct`) | ✅ | `1f5884c` |
| P4 | Print evidence pack | ✅ | `e085481` |
| P5 | Primitives (Field, CardError), Button/status unification | ✅ | (P5.1 label-stack migration on non-Lab pages deferred) |
| P6 | BatchDetail flagship (ISSUED verdict, modal gravity, chart geometry, evidence lifecycle, lightbox states, error/skeleton/anchor) | ✅ | `a90b572` |
| P7 | Page tasks — Dashboard, Batches, Farmers, Dispatch, Projects, Registry, Lab (incl. admin role-gating) | ✅ | `55f3f0f`…`53ea63f` |
| P8 | Polish + guardrails (z-index, motion, selection, touch targets, spacing sweep, guard) | ✅ | `e0ecc30` |

### P6 — flagship detail

- **P6.1** `SealedVerdict` gains an `ISSUED` verdict (indigo stamp, "Credit issued"); the redundant chip and its `.seal` CSS removed.
- **P6.2** Confirm token must be typed (copy button removed, token non-selectable); hairline border + normalized spacing; placeholder preview row + `danger` dropped at the call site.
- **P6.3** `TemperatureChart` fills its box (`preserveAspectRatio=none`), pads the plot to y∈[8,192], SVG-`fill` axis labels.
- **P6.4** `.tiles` → `auto-fit minmax(280px,1fr)`, single column < 720px.
- **P6.5** Evidence verdicts lock once issued; reviewed items collapse to "Change verdict"; save errors show a pill.
- **P6.6** Lightbox: skeleton while loading, "Media unavailable" on failure, arrow-key hint + `aria-keyshortcuts`, neutral Close.
- **P6.7** BatchDetail: 404 vs generic load errors + Retry, Skeleton-primitive loading, "Review evidence" anchor when media exists.

### P8 — polish + guardrails

- **P8.1** Overlays/modals/tooltips use `--z-*`; sticky table head sits under the topbar.
- **P8.2** Legacy duration/ease names alias the `--dur-*`/`--ease-*` scale; spin/pulse tokenized; redundant reduced-motion override removed.
- **P8.3** `::selection` + dark scrollbar colors; lucide `ImageOff` fallback glyph; missing GPS renders `—`.
- **P8.4** Topbar icon buttons at `--control-h-md`; InfoTip/CopyButton hit-slop to ~28px without layout shift; login password toggle → module.
- **P8.5** Every `padding`/`margin`/`gap` across 20 CSS files + 18 inline TSX styles now uses `--space-*` tokens, enforced by the new guard test.

## Deviations from the blueprint (recorded for review)

- **P7.4/7.5/7.6 relocation:** admin forms were role-gated in place (with a disclosure on Dispatch) rather than physically relocated below the pager/tables — the security goal (verifiers never see write controls) is met without the higher-risk restructuring of large stateful blocks.
- **P6.7 evidence anchor** renders only when `media.length > 0` (the blueprint's unconditional version would link to a gallery that renders nothing on zero-media batches).
- **P8.1 `DivergingStackedBarChart`** lives under `src/ui/`, not `src/components/` as the blueprint's path stated; the real file was edited.
- Two test assertions that depended on literal CSS-module class names were switched to behavioral / `aria-hidden` checks, since this vitest setup does not preserve module class names as literals.

## Remaining

- **P8.6.4 — screenshot re-capture** (`node audit/capture.mjs base && … states`) requires a running dev server + seeded backend; not run in this pass. The code is verified by tests, the guard, and the acceptance greps, but the dual-theme visual confirmation of the 6 key screens is pending.
- **P5.1** — migrating the remaining inline label-stacks to `<Field>` on the non-Lab pages (Lab already uses `Field`).
