# Telemetry Chart UX — Status Tracker

Source prompt: `REMEDIATION_PROMPT_TELEMETRY_CHART_UX.md`
Blueprint: `TELEMETRY_CHART_UX_BLUEPRINT.md` (v2, post-CTO-audit)

```
 BASE [x] Baselines recorded — npm run test: 429 passed, 1 known-failing
          (AppShell snapshot, pre-existing per memory "portal 429/1-known"),
          430 total. npm run build: clean (2026-08-02).
 A    [x] lib/telemetry/lookup.ts (binary-search sampleAt + toCsvRows + elapsed) + test
          — commit 70482d6. 6 new tests, all pure/jsdom-free.
 B    [x] ChartFrame optional hover overlay (onHoverFrac + crosshairFrac); other charts untouched
          — commit f42fd72. BarChart + TemperatureChart re-verified green, unchanged.
          Added data-crosshair="true" to the crosshair <line> (not in the original
          spec) so tests can disambiguate it from the pre-existing axis gridlines,
          which also use strokeWidth=1.
 C    [x] HoverSync context + synchronized crosshair + shared ChartTooltip in both charts
          — commit 2b4429d. Both chart .module.css files got `position: relative`
          added to `.wrap` (confirmed missing, not just "verify" as the prompt
          flagged) so the absolutely-positioned tooltip anchors correctly. Added an
          integration test in BurnLiveView.test.tsx proving the SHARED-ness: firing
          pointermove on the thermal chart's capture rect lights up the load
          chart's tooltip at the same instant (both render the label "t+0:00").
 D0   [x] optional height pass-through on both charts — commit 6a8b2a1.
 D1-3 [x] ChartExpandModal + TelemetryCard (click/keyboard to expand); BurnLiveView grid
          — commit fb904b0. ChartExpandModal's Close button uses the existing
          `ui/Button` primitive (variant="neutral") per repo convention, not a raw
          <button> as an early draft had. 4 new TelemetryCard tests (click opens,
          Enter/Space opens, Close dismisses, compact vs expanded content).
 E    [x] downloadCsv + "Download CSV" action inside the modal — commit fa5d3a3.
          CSV building uses the EXACT Object.fromEntries expression from the
          prompt. Test verifies actual escaping via a Blob-subclass capture trick
          (jsdom's Blob has no .text() method in this environment). One
          TypeScript fix needed: the createObjectURL mock had to be given an
          explicit (Blob) parameter type or `tsc --noEmit` failed inferring an
          empty-tuple mock signature.
 F    [~] (OPTIONAL) svgToPng + "Download PNG" action — NOT BUILT, per the prompt's
          own "only if it stays clean" clause. Checked BEFORE writing any code:
          no `canvas` npm package is installed (jsdom's HTMLCanvasElement
          .getContext('2d') throws "Not implemented" without it, and adding one
          would violate rule 6 — no new deps), and jsdom does not fire
          `Image.onload` for data URLs without enabling resource loading, so the
          function's two load-bearing steps (canvas draw, image decode) are
          unverifiable with `npm run test` — the only oracle available. Rather
          than ship untestable code or add a dependency, stopped here per the
          prompt's explicit permission. CSV (Phase E) is the shipped download.
 G    [x] Final wiring + full gate — npm run test: 445 passed (429 baseline + 16
          new), 1 known pre-existing failure (AppShell snapshot, untouched by this
          work). npm run build: clean. BarChart + TemperatureChart (the other 2
          ChartFrame consumers) unchanged and green throughout.

## Real-browser verification (playwright-core) — 2 real bugs found + fixed (commit 381fdfb)

jsdom unit tests alone were NOT sufficient — verified per repo convention
("verify UI in a browser" — jsdom/vitest miss real hit-testing and CSS layout).
Set up: local backend (`uvicorn app_factory:app`) against local sqlite with a
local portal admin user + seeded T1-T4+LOAD `telemetry_points` on an existing
batch + `ff.telemetry_v2` flag on, `vite` dev server pointed at it (CORS
origin matched via `DMRV_ALLOWED_ORIGIN`), driven with `playwright-core`
(chromium), auth token seeded into localStorage via `page.addInitScript`.
Found and fixed:

1. **Hover/crosshair/tooltip did not work at all** in a real browser, despite
   the unit tests being green. Root cause: the pointer-capture
   `<rect fill="transparent">` relies on SVG's default
   `pointer-events: visiblePainted`, which does NOT hit-test a transparent
   fill — only real paint. jsdom's `fireEvent.pointerMove()` calls the React
   handler directly, bypassing hit-testing entirely, so the tests could never
   have caught this. Fixed with `pointerEvents="all"` on the capture rect.
2. **Both the compact card and the expanded modal showed the chart's title
   TWICE** — once from the card/modal's own heading, once from ChartFrame's
   own internal title (which the chart always renders). Fixed by dropping the
   card's redundant visible label (kept as `aria-label` for a11y) and making
   the modal's `Dialog.Title` visually-hidden (kept in the DOM for Radix/a11y)
   since the chart's own title is the on-screen heading.

Also had to fix my OWN verification script twice before it was trustworthy:
first it grabbed the wrong `<svg>` (a `lucide-react` icon also renders as
`<svg>`, needed `svg[role="img"]`), then raw `page.mouse.move()` coordinates
were below the fold and silently hit nothing (`document.elementFromPoint`
returned null) until `scrollIntoViewIfNeeded()` was added — a reminder that a
"looks done" Playwright script needs its own scrutiny, not just a green run.

Re-verified after both fixes: compact grid (side-by-side desktop, stacked
narrow/375px), synchronized hover crosshair + tooltip on BOTH charts
simultaneously (same elapsed-time label, proving the shared HoverSync), click
AND keyboard (Enter) expand, Esc/Close dismiss, Download CSV triggers with the
correct filename — all confirmed via screenshots, not just DOM queries.
Full gate re-run after the fixes: 445 passed (same count — same tests now
exercising CORRECT code), build clean.

**Pushed to origin/main.**
```
