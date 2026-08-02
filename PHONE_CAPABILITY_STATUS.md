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
 P2.1  [x] backend: KilnRequest + upsert_kiln accept sensor_profile + test — commit 2bd1efc
 P2.2  [x] backend: device GET /api/v1/kiln + test — commit da4edb6
 P2.3  [x] phone: Kilns.sensorProfile column + schema v27→28 migration — commit 6388604
 P2.4  [x] phone: KilnService (offline-first, never throws) + fetch/cache at kiln-select
          — commit 8b2748d. Also added a P2.4-scoped, view-only "sensor profile
          unknown — connect to sync" banner on KilnSelectScreen per the plan's audit
          fix #3 (never silently under-capture); not unit-tested (no dedicated test
          task was specified for the UI banner itself, only for KilnService's
          offline-first contract, which is covered).
 P2.5  [x] phone: signed producer gated by kiln's REAL profile (never the override)
          — commit 59a3d66. Confirmed by grep that `_viewOverride` never reaches
          `maybeStartDemoTelemetry` (it only feeds `persistedBurnProfile`, tested to
          ignore it, and the HUD's view filter).
 P2.6  [~] backend config: KILN-DEMO-01 → full (local+remote) DONE; telemetry_v2 flag
          ON for org BLOCKED.
          — User approved proceeding with the current DMRV_ADMIN_SECRET (2026-08-02).
          Pushed all 12 local commits to origin/main (8312e0a..255fce7) so Render
          would redeploy with the P2.1/P2.2 backend code (the remote previously
          rejected `sensor_profile` as `extra_forbidden` — old code). Confirmed the
          redeploy landed, then set KILN-DEMO-01 sensor_profile='full' via
          POST /api/v1/admin/kiln on BOTH the local server (127.0.0.1:8010, temp
          uvicorn against local sqlite) and the remote (dmrv-api.onrender.com).
          Verified on both by reading the `kilns` row directly (local sqlite,
          remote Postgres via DATABASE_URL from backend/.env): sensor_profile='full'
          on both.
          telemetry_v2 flag flip is a SEPARATE write — POST /api/v1/portal/config,
          gated by `require_role("admin")` (a PORTAL JWT login), not the device
          X-Admin-Secret used above. No portal admin credentials were available this
          session; per memory (project_phone_capability_telemetry) this exact step
          was also blocked in an earlier session. Not attempted — stopped rather than
          hunt for credentials. NEXT ACTION: a human with portal admin access must
          GET /api/v1/config to read the current flags_json, merge in
          `"ff.telemetry_v2.<demo-org-id>": "on"` (the POST replaces the whole flags
          dict, so read-merge-write, not a partial patch), and POST it to
          /api/v1/portal/config.
          SECURITY NOTE: DMRV_ADMIN_SECRET was exposed in this session's chat/.env
          reads (again) — still recommend rotating it in Render once this feature is
          done being iterated on.
 GATE2 [~] Backend gate GREEN: pytest 906 passed (902 baseline + 4 new), 2 skipped,
          0 failed. Flutter gate GREEN: flutter analyze 17 pre-existing infos/0
          errors; flutter test 461 passed (452 after Phase 1 + 9 new), 2 skipped, 0
          failed — includes a CORRECTION to
          test/migration_v26_to_v27_entity_media_test.dart (exact `schemaVersion==27`
          → `greaterThanOrEqualTo(27)`, matching its own predecessor test's style,
          because P2.3 legitimately advanced the current schema to 28; see commit
          17ac00c). End-to-end verification NOT DONE — the remote kiln is
          correctly configured 'full' now, but telemetry_v2 stays OFF (P2.6 blocked
          above) so the portal's capability tier won't reflect 'full'/'load' yet, and
          no physical phone was connected this session to drive an actual burn.
```
