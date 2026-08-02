# Telemetry Chart UX — Status Tracker

Source prompt: `REMEDIATION_PROMPT_TELEMETRY_CHART_UX.md`
Blueprint: `TELEMETRY_CHART_UX_BLUEPRINT.md` (v2, post-CTO-audit)

```
 BASE [x] Baselines recorded — npm run test: 429 passed, 1 known-failing
          (AppShell snapshot, pre-existing per memory "portal 429/1-known"),
          430 total. npm run build: clean (2026-08-02).
 A    [ ] lib/telemetry/lookup.ts (binary-search sampleAt + toCsvRows + elapsed) + test
 B    [ ] ChartFrame optional hover overlay (onHoverFrac + crosshairFrac); other charts untouched
 C    [ ] HoverSync context + synchronized crosshair + shared ChartTooltip in both charts
 D0   [ ] optional height pass-through on both charts
 D1-3 [ ] ChartExpandModal + TelemetryCard (click/keyboard to expand); BurnLiveView grid
 E    [ ] downloadCsv + "Download CSV" action inside the modal
 F    [ ] (OPTIONAL) svgToPng + "Download PNG" action — only if it stays clean
 G    [ ] Final wiring + full gate + human visual QA
```
