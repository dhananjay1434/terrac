# Phone Capability Telemetry — Status Tracker

Source prompt: `REMEDIATION_PROMPT_PHONE_CAPABILITY_TELEMETRY.md`
Plan: `~/.claude/plans/wild-conjuring-firefly.md` (v2, post-audit)

```
 BASE  [x] Baselines recorded — flutter analyze: 17 pre-existing infos, 0 errors (182.6s).
             flutter test: 443 passed, 2 skipped, 0 failed (2026-08-02).
 P1.1  [x] SensorProfile resolver (pure) + test — commit 85a2aee
 P1.2  [x] BleMultiChannelSource + VirtualMultiChannelAdapter (demo) + test — commit 818a966
 P1.3  [x] MultiChannelBurnNotifier (beside PyrolysisBleNotifier) + test — commit 70c431c
 P1.4  [x] MultiChannelBurnHud + view-only/demo-only override; wired into pyrolysis screen
          — commit f03013a. DEVIATION FROM RULE 1 (one task per commit): P1.5's
          resolveLegacyTemperatureReadings + its _endBurn wiring were written and
          committed together with P1.4, not as a separate commit, because both were
          designed and typed in the same edit pass to `pyrolysis_screen.dart` before
          the gate was re-run. Functionally correct and covered by
          test/ui/multichannel_override_viewonly_test.dart; recorded here for honesty
          per "verify, don't trust."
 P1.5  [x] Legacy END-write fed the T1 reference series for multi-channel profiles
          — bundled into commit f03013a (see P1.4 deviation note above). Also fixed
          two `invalid_use_of_protected_member`/`visible_for_testing` analyze
          warnings introduced by reading StateNotifier.state from outside the
          notifier — replaced with an addListener-fed `_multiState` field.
 GATE1 [~] Flutter gate GREEN: flutter analyze 17 pre-existing infos/0 errors (282.7s);
          flutter test 452 passed (443 baseline + 9 new), 2 skipped, 0 failed.
          Visual QA on the phone NOT YET DONE this session — no Android device was
          connected (adb devices: empty). Run before the recording:
          `flutter run -d <device-id> --dart-define=DMRV_DEMO_MODE=true
          --dart-define=DMRV_API_BASE_URL=https://dmrv-api.onrender.com
          --dart-define=DMRV_PROJECT_ID=demo-lantana-01`, start a burn, confirm
          T1-T4 + LOAD tiles live, and that the VIEW override chips (shown only in
          demo mode) swap tiles without restarting the burn.
 P2.1  [ ] backend: KilnRequest + upsert_kiln accept sensor_profile + test
 P2.2  [ ] backend: device GET /api/v1/kiln + test
 P2.3  [ ] phone: Kilns.sensorProfile column + schema v27→28 migration
 P2.4  [ ] phone: KilnService (offline-first, never throws) + fetch/cache at kiln-select
 P2.5  [ ] phone: signed producer gated by kiln's REAL profile (never the override)
 P2.6  [ ] backend config: KILN-DEMO-01 → full (local+remote) + telemetry_v2 flag ON for org
 GATE2 [ ] Backend + Flutter gates green; end-to-end verified
```
