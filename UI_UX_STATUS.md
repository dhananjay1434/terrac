# UI/UX Migration Status

Tracking execution of `REMEDIATION_PROMPT_UI_UX.md`.

```
 UX-A1 [x] ChartFrame primitive (NEW files, verbatim) + test        (additive; 0 breaks)
 UX-B1 [x] Migrate ThermalMapChart onto ChartFrame (worked example)
 UX-B2 [x] Migrate LoadTelemetryChart onto ChartFrame
 UX-B3 [x] Migrate TemperatureChart onto ChartFrame
 UX-B4 [x] Migrate BarChart onto ChartFrame
 UX-B5 [-] HorizontalBarList/BurnTelemetryChart/DivergingStackedBarChart — SKIPPED, see log
 UX-C1 [ ] CellStack primitive (NEW) + test
 UX-C2 [ ] Migrate Ledger / UnboundSessions / JourneyPanel tables → DataTable + CellStack
 UX-D1 [ ] Extract page data into features/*/useX hooks (Dispatch, BatchDetail, Projects)
 UX-E1 [ ] DetailDrawer (promote JourneyPanel shell) + MetricBlock rows
 UX-F1 [ ] Polish layer: motion + focus-visible + count-up (per §4 of the blueprint)
 UX-F2 [ ] State layer: 4-state taxonomy (loading/empty/filtered-empty/error) + CLS-safe skeletons
 UX-F3 [ ] Responsive: DataTable mobile (card/scroll), ChartFrame narrow, DetailDrawer full-width
 UX-G1 [ ] Guard tests: no raw <table> in pages, no inline chart <svg>, no fetch in page JSX
 UX-G2 [ ] A11y: fix z-index order (tooltip topmost); chart aria-describedby; icon-btn aria-label guard
 FINAL [ ] tsc + vitest green (minus the 1 known) + Visual QA (§0.8) passed for B/C/E/F
```

## Log
- **UX-A1** (2026-08-01): Created `src/ui/ChartFrame/{ChartFrame.tsx,ChartFrame.module.css,ChartFrame.test.tsx}` verbatim. `tsc --noEmit` clean, 4/4 tests green.
- **UX-B1** (2026-08-01): ThermalMapChart now composes ChartFrame (title/legend/badge via props); manual head div + end-labels removed. 5/5 tests green, no correction needed.
- **UX-B2** (2026-08-01): LoadTelemetryChart composes ChartFrame (chips → `headerStats`), added an emphasized endpoint marker per §UX-B* acceptance criteria. Corrected the circle-count assertion 4→5 (endpoint marker is new, intentional).
- **UX-B3** (2026-08-01): TemperatureChart composes ChartFrame for both the single-reading and multi-reading paths; deduped `yTicks` to avoid a React key collision when all readings are equal. Corrected 2 tests whose assertions were about the OLD chrome's inline mechanics (exact plot-bound pixels 192→180 now that ChartFrame owns `X_AXIS_H`; fill-attribute styling → shared `.axisLabel`/`.micro` class) — structural/count assertions kept, only the source-of-truth values changed.
- **UX-B4** (2026-08-01): BarChart composes ChartFrame with `yTicks={[]}` (BarChart never had numeric y-axis labels, only decorative gridlines with no test coverage) so category labels stay under the 8-label thinning cap. All 11 existing tests green with zero corrections.
- **UX-B5** (2026-08-01): **Skipped, by design — not a ChartFrame fit.** `HorizontalBarList` is a CSS/HTML bar list, no SVG at all. `BurnTelemetryChart` is a pure data-source switcher (v2 live vs. legacy `TemperatureChart`) with no chrome of its own — nothing to migrate. `DivergingStackedBarChart` has a diverging, per-label zero-baseline scale (not a single linear yDomain) plus an interactive floating tooltip and focusable per-bar hit-areas requiring `role="group"` — ChartFrame hardcodes `role="img"`, and nesting focusable controls inside an img-roled region is an ARIA violation the component's own code comments explicitly warn against. Forcing these into ChartFrame would misrepresent the abstraction rather than remove real duplication; the 4 charts in B1–B4 were the actual shared-chrome duplication target.
