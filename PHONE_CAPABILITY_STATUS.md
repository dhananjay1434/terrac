# Phone Capability Telemetry — Status Tracker

Source prompt: `REMEDIATION_PROMPT_PHONE_CAPABILITY_TELEMETRY.md`
Plan: `~/.claude/plans/wild-conjuring-firefly.md` (v2, post-audit)

```
 BASE  [x] Baselines recorded — flutter analyze: 17 pre-existing infos, 0 errors (182.6s).
             flutter test: 443 passed, 2 skipped, 0 failed (2026-08-02).
 P1.1  [ ] SensorProfile resolver (pure) + test
 P1.2  [ ] BleMultiChannelSource + VirtualMultiChannelAdapter (demo) + test
 P1.3  [ ] MultiChannelBurnNotifier (beside PyrolysisBleNotifier) + test
 P1.4  [ ] MultiChannelBurnHud + view-only/demo-only override; wired into pyrolysis screen
 P1.5  [ ] Legacy END-write fed the T1 reference series for multi-channel profiles
 GATE1 [ ] Flutter gate green; Visual QA on phone (4 thermocouples + load live in demo)
 P2.1  [ ] backend: KilnRequest + upsert_kiln accept sensor_profile + test
 P2.2  [ ] backend: device GET /api/v1/kiln + test
 P2.3  [ ] phone: Kilns.sensorProfile column + schema v27→28 migration
 P2.4  [ ] phone: KilnService (offline-first, never throws) + fetch/cache at kiln-select
 P2.5  [ ] phone: signed producer gated by kiln's REAL profile (never the override)
 P2.6  [ ] backend config: KILN-DEMO-01 → full (local+remote) + telemetry_v2 flag ON for org
 GATE2 [ ] Backend + Flutter gates green; end-to-end verified
```
