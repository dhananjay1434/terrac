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
          work), 446 total. npm run build: clean. BarChart + TemperatureChart
          (the other 2 ChartFrame consumers) unchanged and green throughout.
          HUMAN VISUAL QA STILL NEEDED — no browser was driven this session, only
          jsdom unit tests + tsc + vite build. Before trusting the UX: `npm run
          dev`, open a batch with v2 telemetry (e.g. the KILN-DEMO-01 batch bound
          in the phone-capability-telemetry session), and check — compact grid
          side-by-side/stacked; click AND keyboard (Tab+Enter) open the modal;
          hovering either chart moves BOTH crosshairs together; Download CSV
          produces a correct file; at both desktop and narrow (~375px) widths.
```
