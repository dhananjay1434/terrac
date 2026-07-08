# DEMO + DUAL-UI — Execution Prompt (mechanical, phase-by-phase, fully reversible)

> **What this file is:** the executable companion to [`../DEMO_AND_DUAL_UI_MAP.md`](../DEMO_AND_DUAL_UI_MAP.md),
> written so that any engineer or AI model can execute it **verbatim** — exact files, exact search
> strings (verified against HEAD `5a90b72` on 2026-07-08), full source for every new file, a test
> gate after every phase, and a **kill switch for every phase**.
>
> **The reversibility doctrine (the #1 rule of this prompt):**
> 1. **Nothing in Part 1 or Part 2 touches the backend, the sync canonical, the Drift schema, or any
>    service contract.** UI-layer + docs + one standalone HTML tool only.
> 2. **Part 1 (demo) lives on its own branch** — `demo/eu-demo`. It is never merged unless explicitly
>    decided. Deleting the branch removes every demo change. Production work continues from
>    `remediation/phase-by-phase` untouched.
> 3. **Part 2 (dual UI) is additive-first**: new files + deprecated aliases; old themes keep compiling
>    until the final cleanup phase. Every phase = one commit = one `git revert`-able unit.
> 4. Each phase below ends with **GATE** (commands that must pass) and **KILL SWITCH** (the one-click
>    undo). Do not start phase N+1 with phase N's gate red.
>
> **Baseline gates (must hold after EVERY phase):**
> `flutter analyze` → **25 issues, 0 errors** (never add any) · `flutter test` → **153 passed, 2 skipped**
> (Part 2 phases add tests — counts go UP, never down) · backend untouched → no backend gate needed
> except where a phase says so.

---

# PART 1 — DEMO (branch `demo/eu-demo`) — do these in order, tonight-sized

## Phase DP0 — Branch + backend boot + token mint (setup, no app code)

```powershell
# 1. Cut the demo branch (THE kill switch for all of Part 1)
git checkout -b demo/eu-demo

# 2. Backend: add the missing admin secret (backend/.env has DMRV_HMAC_SECRET but NOT DMRV_ADMIN_SECRET)
#    Append this line to backend/.env (any 32+ char string with >=10 distinct chars):
#    DMRV_ADMIN_SECRET=demo-admin-secret-0123456789abcdefghij

# 3. Boot the backend (from repo root)
cd backend; uvicorn server:app --host 0.0.0.0 --port 8001

# 4. Verify health (new terminal)
curl.exe http://localhost:8001/api/health        # expect {"status":"ok"}

# 5. Find the laptop's LAN IP (the phone must reach this)
ipconfig | findstr IPv4

# 6. Allow inbound 8001 through Windows firewall (admin PowerShell)
netsh advfirewall firewall add rule name="dmrv-demo-8001" dir=in action=allow protocol=TCP localport=8001

# 7. Mint ONE demo token + TWO spares (tokens are single-use; a reinstall burns one)
$H = @{ "X-Admin-Secret" = "demo-admin-secret-0123456789abcdefghij"; "Content-Type" = "application/json" }
Invoke-RestMethod -Method Post -Uri http://localhost:8001/api/v1/admin/mint-token -Headers $H -Body '{"token":"demo-eu-1","expires_in_days":7}'
Invoke-RestMethod -Method Post -Uri http://localhost:8001/api/v1/admin/mint-token -Headers $H -Body '{"token":"demo-eu-2","expires_in_days":7}'
Invoke-RestMethod -Method Post -Uri http://localhost:8001/api/v1/admin/mint-token -Headers $H -Body '{"token":"demo-eu-3","expires_in_days":7}'
```

**GATE:** health returns 200; three tokens minted.
**KILL SWITCH:** remove the `.env` line + firewall rule (`netsh advfirewall firewall delete rule name="dmrv-demo-8001"`).

---

## Phase DP1 — F1: hide the "-73h TEST" button in demo builds

**File:** `lib/ui/screens/lantana_sourcing_screen.dart`
**Anchor (verified):** lines 318–359 — inside a `Row(children: [...])`, after the
`PremiumFieldButton(label: 'LOG HARVEST :: NOW', ...)` `Expanded`, there is a
`const SizedBox(width: 12),` followed by a `SizedBox(width: 96, child: Material(...))` whose inner
`Text` is exactly `'-73h\nTEST'` with `Semantics(identifier: 'log-harvest-minus-73h-btn')`.

**Edit 1 — add a file-scope const near the top of the file (after the imports):**
```dart
/// Demo builds (DMRV_DEMO_MODE=true) hide the -73h QA affordance entirely.
/// Non-demo builds keep it — QA depends on it. Remove this gate when the
/// T5 Stage-A migration gives the button a proper kDebugMode+long-press home.
const bool _kIsDemoBuild = bool.fromEnvironment('DMRV_DEMO_MODE', defaultValue: false);
```

**Edit 2 — wrap the two Row children (the spacer AND the 96px button) in a collection-if.**
Replace this (exact current code, starting from the line after the `Expanded(...)`'s closing `),`):
```dart
              const SizedBox(width: 12),
              SizedBox(
                width: 96,
```
with:
```dart
              if (!_kIsDemoBuild) ...[
                const SizedBox(width: 12),
                SizedBox(
                  width: 96,
```
…and at the end of that `SizedBox` widget (its closing `),` at what is currently line 359, i.e. the
`),` that closes `SizedBox(width: 96, ...)` — the one directly before the Row's closing `],`),
change:
```dart
              ),
            ],
          ),
```
to:
```dart
                ),
              ],
            ],
          ),
```
(Re-indent the wrapped block by one level; `dart format lib/ui/screens/lantana_sourcing_screen.dart`
afterwards makes indentation exact automatically — run it.)

**GATE:** `flutter analyze` 25/0 · `flutter test` 153/2 · `flutter run --dart-define=DMRV_DEMO_MODE=true`
shows NO TEST button on the sourcing screen; a plain `flutter run` still shows it.
**KILL SWITCH:** the button is only hidden when `DMRV_DEMO_MODE=true` — a normal build is already
unchanged. Branch delete removes even the gate.

---

## Phase DP2 — F3: humanize the two raw `e.toString()` error displays

**File 1:** `lib/ui/screens/moisture_verification_screen.dart`
**Anchor (verified, line 137):**
```dart
      setState(() => _persistError = e.toString());
```
Replace with:
```dart
      setState(
        () => _persistError =
            'Could not save this reading. Your other data is safe — please try again.',
      );
```
(The `debugPrint('[MoistureScreen] persist failed: $e\n$st');` on the line above already preserves
the technical detail for the log — do not touch it.)

**File 2:** `lib/ui/screens/end_use_application_screen.dart`
**Anchor (verified, line 143):**
```dart
      setState(() => _err = e.toString());
```
Replace with:
```dart
      setState(
        () => _err =
            'Could not save this record. Your other data is safe — please try again.',
      );
```
**Anchor (verified, line 82):**
```dart
      setState(() => _gpsError = e.toString());
```
Replace with:
```dart
      setState(() => _gpsError = 'GPS fix failed. Move to open sky and retry.');
```
(Note: `secure_camera_screen.dart:77,137` also use `e.toString()` — leave them; the camera error
panel is technical-by-design and rarely surfaces. Scope discipline.)

**GATE:** `flutter analyze` 25/0 · `flutter test` 153/2.
**KILL SWITCH:** three one-line reverts; branch delete.

---

## Phase DP3 — F2: recolor Yield Scale to the light theme (kills both mid-flow dark flips)

**File:** `lib/ui/screens/yield_scale_screen.dart` — the ONLY dark screen inside the capture flow.
After this phase the flow is: light → light → light → light → light (dashboard/proof-wallet stay
dark by design — the "home/vault" surfaces).

**Step 1 — imports.** Remove the `farmer_theme.dart` import and the `rugged_button.dart` import;
ensure `app_theme.dart` and `premium_field_components.dart` are imported (the file already imports
premium components — `PremiumStatusChip` is used at line 297).

**Step 2 — add two file-scope consts** (same idiom as the other light screens use today; Stage A
deletes all of these later):
```dart
const Color _errorRed = Color(0xFFDC2626);
const Color _errorRedSoftBg = Color(0xFFFEF2F2);
```

**Step 3 — mechanical color replacements.** Every `FarmerTheme.*` reference, by verified line:

| Line | Current | Replace with | Why |
|---|---|---|---|
| 133 | `? FarmerTheme.fieldGreen` | `? AppTheme.yieldGold10` | stabilized bg flash → light-era success tint |
| 134 | `: FarmerTheme.deepSlate` | `: AppTheme.tacticalTitanium` | scaffold: dark → light |
| 169 | `color: FarmerTheme.crimsonRed15` | `color: _errorRedSoftBg` | error panel bg, light idiom |
| 172 | `color: FarmerTheme.crimsonRed` | `color: _errorRed` | |
| 181 | `color: FarmerTheme.crimsonRed` | `color: _errorRed` | |
| 196 | `color: FarmerTheme.crimsonRed` | `color: _errorRed` | |
| 206 | `color: FarmerTheme.fogWhite` | `color: AppTheme.armorSlate` | text on light panel |
| 277 | `color: FarmerTheme.panelSlate` | `color: AppTheme.pureAlbedo` | card surface |
| 279 | `color: FarmerTheme.fogWhite20` | `color: AppTheme.cobaltShield15` | card border, light idiom |
| 293 | `color: FarmerTheme.pureAlbedo` | `color: AppTheme.armorSlate` | primary text |
| 307 | `color: FarmerTheme.fogWhite65` | `color: AppTheme.armorSlate65` | secondary text |
| 318 | `color: FarmerTheme.neonYellow` | `color: AppTheme.cobaltShield` | accent |
| 340 | `? FarmerTheme.neonYellow` | `? AppTheme.yieldGold` | stabilized hero digits → success |
| 341 | `: FarmerTheme.pureAlbedo` | `: AppTheme.armorSlate` | moving hero digits |
| 346 | `color: FarmerTheme.panelSlate` | `color: AppTheme.pureAlbedo` | readout card |
| 349 | `stable ? FarmerTheme.fieldGreen : FarmerTheme.fogWhite20` | `stable ? AppTheme.yieldGold : AppTheme.armorSlate20` | readout border |
| 377 | `color: FarmerTheme.fogWhite70` | `color: AppTheme.armorSlate70` | |
| 389 | `color: FarmerTheme.fieldGreen` | `color: AppTheme.yieldGold` | stabilized badge icon |
| 399 | `color: FarmerTheme.fieldGreen` | `color: AppTheme.yieldGold` | stabilized badge text |
| 414 | `color: FarmerTheme.fogWhite60` | `color: AppTheme.armorSlate60` | |
| 424 | `color: FarmerTheme.fogWhite60` | `color: AppTheme.armorSlate60` | |

**Step 4 — swap the three `RuggedButton`s (dark component) for `PremiumFieldButton` (light).**
API mapping: `RuggedButtonVariant.primary → FieldButtonState.hiVis`,
`.success → FieldButtonState.go`, `.disabled → FieldButtonState.locked`;
`semanticId:` → `testId:`; `key:` is kept (both accept `super.key`).

Site 1 (verified lines 155–163):
```dart
                      PremiumFieldButton(
                        key: const Key('connect-crane-scale-btn'),
                        label: AppLocalizations.of(
                          context,
                        )!.connect_crane_scale,
                        state: FieldButtonState.hiVis,
                        testId: 'connect-crane-scale-btn',
                        onPressed: _requestPermsAndStart,
                      ),
```
Site 2 (verified lines 225–239):
```dart
                      PremiumFieldButton(
                        key: const Key('lock-yield-btn'),
                        label: s.isStabilized
                            ? 'LOCK YIELD @ ${s.stableKg!.toStringAsFixed(3)} kg'
                            : AppLocalizations.of(context)!.stabilize_reading,
                        state: s.isStabilized
                            ? FieldButtonState.go
                            : FieldButtonState.locked,
                        testId: 'lock-yield-btn',
                        onPressed: s.isStabilized
                            ? () => ref
                                  .read(yieldScaleProvider.notifier)
                                  .confirm()
                            : null,
                      )
```
Site 3 (verified lines 241–249):
```dart
                      PremiumFieldButton(
                        key: const Key('save-yield-btn'),
                        label: _saving ? 'PERSISTING…' : 'SAVE YIELD → END USE',
                        state: _saving
                            ? FieldButtonState.locked
                            : FieldButtonState.hiVis,
                        testId: 'save-yield-btn',
                        onPressed: _saving ? null : _saveYield,
                      ),
```

**Step 5 — self-check:** `grep -n "FarmerTheme\.\|RuggedButton" lib/ui/screens/yield_scale_screen.dart`
must return **0 matches**.

**GATE:** `flutter analyze` 25/0 · `flutter test` 153/2 (widget tests key off `Key('lock-yield-btn')`
etc. — kept) · manual walkthrough: pyrolysis → yield → end-use shows NO dark flash.
**KILL SWITCH:** `git revert` of this single commit; branch delete.

---

## Phase DP4 — F4: the "verifier view" finale page (new standalone folder — zero app/backend edits)

**New file:** `demo_tools/verifier_view/index.html` — full source:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>dMRV Verifier View</title>
<style>
  :root { --ink:#0F172A; --paper:#F0F4F8; --card:#FFF; --ok:#047857; --warn:#B45309; --bad:#B91C1C; --line:rgba(15,23,42,.12); }
  * { box-sizing: border-box; margin: 0; }
  body { font: 15px/1.5 system-ui, sans-serif; background: var(--paper); color: var(--ink); padding: 24px; }
  .wrap { max-width: 860px; margin: 0 auto; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  .sub { color: rgba(15,23,42,.6); margin-bottom: 20px; }
  .bar { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
  input { flex: 1; min-width: 220px; padding: 10px 12px; border: 1.5px solid var(--line); border-radius: 8px; font: inherit; }
  button { padding: 10px 18px; border: 0; border-radius: 8px; background: var(--ink); color: #fff; font: inherit; font-weight: 600; cursor: pointer; }
  .card { background: var(--card); border: 1.5px solid var(--line); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
  .headline { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .badge { padding: 6px 14px; border-radius: 999px; font-weight: 700; font-size: 13px; letter-spacing: .4px; }
  .badge.ok { background: rgba(4,120,87,.12); color: var(--ok); }
  .badge.warn { background: rgba(180,83,9,.12); color: var(--warn); }
  .credit { font-size: 34px; font-weight: 800; font-variant-numeric: tabular-nums; }
  .unit { font-size: 14px; color: rgba(15,23,42,.6); }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; }
  td, th { text-align: left; padding: 9px 8px; border-top: 1px solid var(--line); }
  th { border-top: 0; font-size: 12px; text-transform: uppercase; letter-spacing: .6px; color: rgba(15,23,42,.55); }
  .st { font-weight: 700; }
  .st.pass { color: var(--ok); } .st.fail { color: var(--bad); } .st.inert { color: rgba(15,23,42,.45); }
  .err { color: var(--bad); font-weight: 600; margin-top: 8px; }
  .muted { color: rgba(15,23,42,.5); font-size: 13px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Verifier View — Batch Compliance</h1>
  <div class="sub">Live read of the registry-facing compliance API (what the auditor sees).</div>
  <div class="bar">
    <input id="api"    placeholder="API base, e.g. http://localhost:8001">
    <input id="secret" placeholder="X-Admin-Secret" type="password">
    <input id="uuid"   placeholder="Batch UUID">
    <button onclick="start()">Watch batch</button>
  </div>
  <div id="out" class="card"><span class="muted">Enter the batch UUID captured on the phone, then Watch.</span></div>
</div>
<script>
let timer = null;
function start() {
  if (timer) clearInterval(timer);
  poll(); timer = setInterval(poll, 5000);
}
async function poll() {
  const api = document.getElementById('api').value.replace(/\/+$/,'');
  const uuid = document.getElementById('uuid').value.trim();
  const out = document.getElementById('out');
  try {
    const r = await fetch(`${api}/api/v1/batches/${uuid}/compliance`, {
      headers: { 'X-Admin-Secret': document.getElementById('secret').value }
    });
    if (!r.ok) { out.innerHTML = `<div class="err">HTTP ${r.status} — ${await r.text()}</div>`; return; }
    render(await r.json(), out);
  } catch (e) { out.innerHTML = `<div class="err">${e.message} — is the backend up and DMRV_ALLOWED_ORIGIN set?</div>`; }
}
function render(d, out) {
  const prov = d.provisional === true;
  const credit = d.net_credit_t_co2e ?? d.net_credit ?? null;
  const checks = d.checklist || [];
  const rows = checks.map(c => {
    const ok = (c.status || '').toLowerCase() === 'pass' || c.ok === true;
    const enf = c.enforcement || '';
    const cls = ok ? 'pass' : (enf.startsWith('inert') || enf === 'awaiting_methodology' ? 'inert' : 'fail');
    const word = ok ? 'PASS' : (cls === 'inert' ? '—' : 'OPEN');
    return `<tr><td>${c.criterion || c.id || ''}</td><td>${c.title || c.description || ''}</td>
            <td class="st ${cls}">${word}</td><td class="muted">${enf}</td></tr>`;
  }).join('');
  out.innerHTML = `
    <div class="headline">
      <span class="badge ${prov ? 'warn' : 'ok'}">${prov ? 'PROVISIONAL — being verified' : 'ISSUABLE ✓'}</span>
      ${credit !== null ? `<span class="credit">${Number(credit).toFixed(3)}</span><span class="unit">t CO₂e net credit</span>` : ''}
    </div>
    ${(d.provisional_reasons||[]).length ? `<div class="err">Open reasons: ${(d.provisional_reasons||[]).join(', ')}</div>` : ''}
    <table><tr><th>Criterion</th><th>Requirement</th><th>Status</th><th>Enforcement</th></tr>${rows}</table>
    <div class="muted" style="margin-top:10px">Auto-refreshing every 5 s · ${new Date().toLocaleTimeString()}</div>`;
}
</script>
</body>
</html>
```

**Run it (two commands — no code changes anywhere):**
```powershell
# Backend terminal: allow the page's origin (single explicit origin, matches the CORS middleware)
$env:DMRV_ALLOWED_ORIGIN = "http://localhost:8080"; cd backend; uvicorn server:app --host 0.0.0.0 --port 8001
# Second terminal:
python -m http.server 8080 -d demo_tools/verifier_view
# Browser: http://localhost:8080 → fill API/secret/UUID → Watch batch
```
> If the checklist field names differ at runtime (the page guards with fallbacks), open DevTools →
> Network → inspect the JSON once and adjust `render()` keys — 2-minute fix, isolated to this file.

**GATE:** page renders the compliance checklist + provisional badge for the rehearsal batch.
**KILL SWITCH:** delete `demo_tools/` — nothing references it.

---

## Phase DP5 — Build, rehearse, freeze

```powershell
flutter build apk --debug --dart-define=DMRV_API_BASE_URL=http://<LAN-IP>:8001 --dart-define=ENROLLMENT_TOKEN=demo-eu-1 --dart-define=DMRV_DEMO_MODE=true
# APK: build\app\outputs\flutter-apk\app-debug.apk → install on the phone
```
Rehearse the FULL flow once (§1.4 of the map): sourcing → moisture → pyrolysis (virtual temp ramps
automatically) → yield (mock scale stabilizes) → end-use → dashboard green → verifier page shows the
result. Leave that batch in place (Proof Wallet non-empty on stage). Screen-record a clean run as
the fallback video. **Then stop touching the branch.**

**KILL SWITCH for all of Part 1:** `git checkout remediation/phase-by-phase` — the demo branch is
never merged; production is untouched by construction.

---

# PART 2 — DUAL UI (India Field + Europe/Universal Pro) — branch `feature/t5-stage-a`, after the demo

> **DECISION D1 (must be recorded before Phase A2, not before A0):** the India skin's identity.
> This prompt implements the **recommended** choice — the warm "paper & machinery" spec from
> [`../../UX_FIELD_THEME_SPEC.md`](../../UX_FIELD_THEME_SPEC.md). If the decision goes to dark-neon
> instead, ONLY the `DmrvTokens.field` value block in Phase A0 changes (swap in the FarmerTheme hex
> values listed in the alternative block) — every other instruction is identical. That containment
> is deliberate.

## Phase A0 — The token layer (new files only; app rendering UNCHANGED)

**New file:** `lib/ui/design/tokens.dart` — full source:

```dart
import 'package:flutter/material.dart';

/// DmrvTokens — the single semantic design-token layer (T5.1).
///
/// Names describe FUNCTION, never color. Two built-in instances:
///  * [DmrvTokens.field] — India/operator skin ("paper & machinery",
///    UX_FIELD_THEME_SPEC.md — decision D1).
///  * [DmrvTokens.pro]   — Europe/universal skin (from the shipped AppTheme
///    light palette, calibrated in Stage B).
///
/// Access anywhere: `final t = context.tokens;`
/// RULE: every field is `required` with NO defaults — adding a token without
/// defining it for BOTH skins is a compile error (structural both-skins gate).
@immutable
class DmrvTokens extends ThemeExtension<DmrvTokens> {
  const DmrvTokens({
    required this.surface,
    required this.surfaceRaised,
    required this.chartPanel,
    required this.textPrimary,
    required this.textSecondary,
    required this.textDisabled,
    required this.accent,
    required this.onAccent,
    required this.success,
    required this.onSuccess,
    required this.danger,
    required this.onDanger,
    required this.dangerSurface,
    required this.certified,
    required this.live,
    required this.border,
    required this.borderStrong,
    required this.radiusS,
    required this.radiusM,
    required this.radiusL,
    required this.gapS,
    required this.gapM,
    required this.gapL,
    required this.gapXL,
    required this.screenTitle,
    required this.blockHeader,
    required this.body,
    required this.bodyHindi,
    required this.numericHero,
    required this.numericMedium,
    required this.buttonLabel,
    required this.metadata,
    required this.chipLabel,
  });

  // Surfaces
  final Color surface;        // scaffold
  final Color surfaceRaised;  // cards / panels
  final Color chartPanel;     // THE one permitted dark panel (live temp chart)
  // Content
  final Color textPrimary;
  final Color textSecondary;
  final Color textDisabled;
  // Semantics — exactly ONE of each meaning (kills U10)
  final Color accent;         // primary CTA / "do this next" / pending
  final Color onAccent;       // label color ON an accent fill
  final Color success;        // confirmed / locked / synced
  final Color onSuccess;
  final Color danger;         // blocks-your-credit errors ONLY
  final Color onDanger;
  final Color dangerSurface;  // error-panel background (kills the 4-variant panel, U5)
  final Color certified;      // server-signed/issued ONLY (the mohar / seal)
  final Color live;           // active BLE / GPS lock indicator
  // Structure
  final Color border;
  final Color borderStrong;
  final double radiusS, radiusM, radiusL;             // 8, 12, 20 (kills U8)
  final double gapS, gapM, gapL, gapXL;               // 8, 12, 16, 24
  // Typography roles (kills U12 — the full set, not 4 of 10)
  final TextStyle screenTitle, blockHeader, body, bodyHindi,
      numericHero, numericMedium, buttonLabel, metadata, chipLabel;

  // ---- India / Field skin — "paper, ink & machinery" (UX_FIELD_THEME_SPEC §1) ----
  // D1 ALTERNATIVE (dark-neon): surface 0xFF1A1D20, surfaceRaised 0xFF23272B,
  // textPrimary 0xFFE2E8F0, accent 0xFFE0FF00/onAccent 0xFF1A1D20,
  // success 0xFF00E676, danger 0xFFDC2626, certified 0xFFF59E0B.
  static const DmrvTokens field = DmrvTokens(
    surface: Color(0xFFECE7DC),        // paper
    surfaceRaised: Color(0xFFF6F3EB),  // paperRaised
    chartPanel: Color(0xFF26221C),     // charcoal (ember trace lives here)
    textPrimary: Color(0xFF211D16),    // ink
    textSecondary: Color(0xB8211D16),  // ink @72%
    textDisabled: Color(0x61211D16),   // ink @38%
    accent: Color(0xFFE8590C),         // machineOrange fill
    onAccent: Color(0xFF211D16),       // ink-on-orange (white-on-orange BANNED, 3.58:1)
    success: Color(0xFF2E6B1F),        // tractorGreen
    onSuccess: Color(0xFFFFFFFF),
    danger: Color(0xFFB91C1C),         // hotIronRed
    onDanger: Color(0xFFFFFFFF),
    dangerSurface: Color(0x26B91C1C),
    certified: Color(0xFF2E3A8C),      // sealBlue — the mohar, nothing else
    live: Color(0xFF2E6B1F),           // live = pulsing green dot (spec §1.3)
    border: Color(0x26211D16),         // ink @15%
    borderStrong: Color(0x4D211D16),
    radiusS: 8, radiusM: 12, radiusL: 20,
    gapS: 8, gapM: 12, gapL: 16, gapXL: 24,
    screenTitle: TextStyle(fontFamily: 'NotoSansDevanagari', fontSize: 24, fontWeight: FontWeight.w700),
    blockHeader: TextStyle(fontFamily: 'NotoSansDevanagari', fontSize: 20, fontWeight: FontWeight.w700),
    body: TextStyle(fontFamily: 'NotoSansDevanagari', fontSize: 18, fontWeight: FontWeight.w400),
    bodyHindi: TextStyle(fontFamily: 'NotoSansDevanagari', fontSize: 18, fontWeight: FontWeight.w400),
    numericHero: TextStyle(fontFamily: 'NotoSansDevanagari', fontSize: 64, fontWeight: FontWeight.w700, fontFeatures: [FontFeature.tabularFigures()]),
    numericMedium: TextStyle(fontFamily: 'NotoSansDevanagari', fontSize: 28, fontWeight: FontWeight.w700, fontFeatures: [FontFeature.tabularFigures()]),
    buttonLabel: TextStyle(fontFamily: 'NotoSansDevanagari', fontSize: 18, fontWeight: FontWeight.w700, letterSpacing: 0.25),
    metadata: TextStyle(fontFamily: 'NotoSansDevanagari', fontSize: 16, fontWeight: FontWeight.w500),
    chipLabel: TextStyle(fontFamily: 'NotoSansDevanagari', fontSize: 13, fontWeight: FontWeight.w700, letterSpacing: 0.4),
  );

  // ---- Europe / Pro skin — from the shipped AppTheme light palette ----
  static const DmrvTokens pro = DmrvTokens(
    surface: Color(0xFFF0F4F8),        // tacticalTitanium
    surfaceRaised: Color(0xFFFFFFFF),  // pureAlbedo
    chartPanel: Color(0xFF0B1026),     // midnightCyber (retained for pro chart)
    textPrimary: Color(0xFF0F172A),    // armorSlate
    textSecondary: Color(0xA60F172A),  // armorSlate65
    textDisabled: Color(0x730F172A),   // armorSlate45 (>=4.5:1 fix of the armorSlate35 fail, U7)
    accent: Color(0xFF1D4ED8),         // cobaltShield
    onAccent: Color(0xFFFFFFFF),
    success: Color(0xFF047857),        // restrained green (gold reads "warning" to EU eyes — T5.8)
    onSuccess: Color(0xFFFFFFFF),
    danger: Color(0xFFB91C1C),
    onDanger: Color(0xFFFFFFFF),
    dangerSurface: Color(0xFFFEF2F2),
    certified: Color(0xFF0B1026),      // vault-dark chip with gold sigil (Stage B refines)
    live: Color(0xFF1D4ED8),
    border: Color(0x1F0F172A),
    borderStrong: Color(0x4D0F172A),
    radiusS: 8, radiusM: 12, radiusL: 20,
    gapS: 8, gapM: 12, gapL: 16, gapXL: 24,
    screenTitle: TextStyle(fontFamily: 'SpaceGrotesk', fontSize: 24, fontWeight: FontWeight.w700),
    blockHeader: TextStyle(fontFamily: 'SpaceGrotesk', fontSize: 20, fontWeight: FontWeight.w600),
    body: TextStyle(fontFamily: 'NotoSansDevanagari', fontSize: 16, fontWeight: FontWeight.w400),
    bodyHindi: TextStyle(fontFamily: 'NotoSansDevanagari', fontSize: 16, fontWeight: FontWeight.w400),
    numericHero: TextStyle(fontFamily: 'SpaceMono', fontSize: 56, fontWeight: FontWeight.w700),
    numericMedium: TextStyle(fontFamily: 'SpaceMono', fontSize: 24, fontWeight: FontWeight.w700),
    buttonLabel: TextStyle(fontFamily: 'SpaceGrotesk', fontSize: 16, fontWeight: FontWeight.w700, letterSpacing: 0.5),
    metadata: TextStyle(fontFamily: 'SpaceMono', fontSize: 13, fontWeight: FontWeight.w400),
    chipLabel: TextStyle(fontFamily: 'SpaceGrotesk', fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 0.6),
  );

  @override
  DmrvTokens copyWith({
    Color? surface, Color? surfaceRaised, Color? chartPanel,
    Color? textPrimary, Color? textSecondary, Color? textDisabled,
    Color? accent, Color? onAccent, Color? success, Color? onSuccess,
    Color? danger, Color? onDanger, Color? dangerSurface,
    Color? certified, Color? live, Color? border, Color? borderStrong,
    double? radiusS, double? radiusM, double? radiusL,
    double? gapS, double? gapM, double? gapL, double? gapXL,
    TextStyle? screenTitle, TextStyle? blockHeader, TextStyle? body,
    TextStyle? bodyHindi, TextStyle? numericHero, TextStyle? numericMedium,
    TextStyle? buttonLabel, TextStyle? metadata, TextStyle? chipLabel,
  }) {
    return DmrvTokens(
      surface: surface ?? this.surface,
      surfaceRaised: surfaceRaised ?? this.surfaceRaised,
      chartPanel: chartPanel ?? this.chartPanel,
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      textDisabled: textDisabled ?? this.textDisabled,
      accent: accent ?? this.accent,
      onAccent: onAccent ?? this.onAccent,
      success: success ?? this.success,
      onSuccess: onSuccess ?? this.onSuccess,
      danger: danger ?? this.danger,
      onDanger: onDanger ?? this.onDanger,
      dangerSurface: dangerSurface ?? this.dangerSurface,
      certified: certified ?? this.certified,
      live: live ?? this.live,
      border: border ?? this.border,
      borderStrong: borderStrong ?? this.borderStrong,
      radiusS: radiusS ?? this.radiusS,
      radiusM: radiusM ?? this.radiusM,
      radiusL: radiusL ?? this.radiusL,
      gapS: gapS ?? this.gapS,
      gapM: gapM ?? this.gapM,
      gapL: gapL ?? this.gapL,
      gapXL: gapXL ?? this.gapXL,
      screenTitle: screenTitle ?? this.screenTitle,
      blockHeader: blockHeader ?? this.blockHeader,
      body: body ?? this.body,
      bodyHindi: bodyHindi ?? this.bodyHindi,
      numericHero: numericHero ?? this.numericHero,
      numericMedium: numericMedium ?? this.numericMedium,
      buttonLabel: buttonLabel ?? this.buttonLabel,
      metadata: metadata ?? this.metadata,
      chipLabel: chipLabel ?? this.chipLabel,
    );
  }

  @override
  DmrvTokens lerp(DmrvTokens? other, double t) {
    if (other is! DmrvTokens) return this;
    return DmrvTokens(
      surface: Color.lerp(surface, other.surface, t)!,
      surfaceRaised: Color.lerp(surfaceRaised, other.surfaceRaised, t)!,
      chartPanel: Color.lerp(chartPanel, other.chartPanel, t)!,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t)!,
      textSecondary: Color.lerp(textSecondary, other.textSecondary, t)!,
      textDisabled: Color.lerp(textDisabled, other.textDisabled, t)!,
      accent: Color.lerp(accent, other.accent, t)!,
      onAccent: Color.lerp(onAccent, other.onAccent, t)!,
      success: Color.lerp(success, other.success, t)!,
      onSuccess: Color.lerp(onSuccess, other.onSuccess, t)!,
      danger: Color.lerp(danger, other.danger, t)!,
      onDanger: Color.lerp(onDanger, other.onDanger, t)!,
      dangerSurface: Color.lerp(dangerSurface, other.dangerSurface, t)!,
      certified: Color.lerp(certified, other.certified, t)!,
      live: Color.lerp(live, other.live, t)!,
      border: Color.lerp(border, other.border, t)!,
      borderStrong: Color.lerp(borderStrong, other.borderStrong, t)!,
      radiusS: radiusS, radiusM: radiusM, radiusL: radiusL,
      gapS: gapS, gapM: gapM, gapL: gapL, gapXL: gapXL,
      screenTitle: TextStyle.lerp(screenTitle, other.screenTitle, t)!,
      blockHeader: TextStyle.lerp(blockHeader, other.blockHeader, t)!,
      body: TextStyle.lerp(body, other.body, t)!,
      bodyHindi: TextStyle.lerp(bodyHindi, other.bodyHindi, t)!,
      numericHero: TextStyle.lerp(numericHero, other.numericHero, t)!,
      numericMedium: TextStyle.lerp(numericMedium, other.numericMedium, t)!,
      buttonLabel: TextStyle.lerp(buttonLabel, other.buttonLabel, t)!,
      metadata: TextStyle.lerp(metadata, other.metadata, t)!,
      chipLabel: TextStyle.lerp(chipLabel, other.chipLabel, t)!,
    );
  }
}

/// Build a full Material ThemeData from tokens so stock widgets (dialogs,
/// snackbars, progress indicators) inherit correctly too.
ThemeData buildDmrvTheme(DmrvTokens t) {
  return ThemeData(
    scaffoldBackgroundColor: t.surface,
    primaryColor: t.accent,
    colorScheme: ColorScheme.light(
      primary: t.accent,
      onPrimary: t.onAccent,
      secondary: t.success,
      onSecondary: t.onSuccess,
      error: t.danger,
      onError: t.onDanger,
      surface: t.surfaceRaised,
      onSurface: t.textPrimary,
    ),
    textTheme: TextTheme(
      titleLarge: t.screenTitle.copyWith(color: t.textPrimary),
      titleMedium: t.blockHeader.copyWith(color: t.textPrimary),
      bodyLarge: t.body.copyWith(color: t.textPrimary),
      bodyMedium: t.metadata.copyWith(color: t.textPrimary),
    ),
    cardTheme: CardThemeData(
      color: t.surfaceRaised,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(t.radiusL * 0.8),
        side: BorderSide(color: t.border, width: 1.5),
      ),
    ),
    extensions: <ThemeExtension<dynamic>>[t],
  );
}

extension DmrvTokensContext on BuildContext {
  DmrvTokens get tokens => Theme.of(this).extension<DmrvTokens>()!;
}
```

**New file:** `test/design/tokens_contrast_test.dart` — full source (the mechanical WCAG gate that
kills U7 regressions forever):

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/ui/design/tokens.dart';

/// WCAG 2.x relative luminance + contrast ratio.
double _lum(Color c) {
  double ch(double v) =>
      v <= 0.03928 ? v / 12.92 : pow((v + 0.055) / 1.055, 2.4).toDouble();
  return 0.2126 * ch(c.r) + 0.7152 * ch(c.g) + 0.0722 * ch(c.b);
}

double contrast(Color a, Color b) {
  // Composite semi-transparent foregrounds onto the background first.
  Color comp(Color fg, Color bg) => Color.alphaBlend(fg, bg);
  final f = _lum(comp(a, b)), g = _lum(b);
  final hi = f > g ? f : g, lo = f > g ? g : f;
  return (hi + 0.05) / (lo + 0.05);
}

void main() {
  for (final entry in {'field': DmrvTokens.field, 'pro': DmrvTokens.pro}.entries) {
    final name = entry.key;
    final t = entry.value;
    group('DmrvTokens.$name WCAG AA (>=4.5:1)', () {
      test('textPrimary on surface', () => expect(contrast(t.textPrimary, t.surface), greaterThanOrEqualTo(4.5)));
      test('textPrimary on surfaceRaised', () => expect(contrast(t.textPrimary, t.surfaceRaised), greaterThanOrEqualTo(4.5)));
      test('textSecondary on surface', () => expect(contrast(t.textSecondary, t.surface), greaterThanOrEqualTo(4.5)));
      test('success on surface', () => expect(contrast(t.success, t.surface), greaterThanOrEqualTo(4.5)));
      test('danger on surface', () => expect(contrast(t.danger, t.surface), greaterThanOrEqualTo(4.5)));
      test('danger on dangerSurface', () => expect(contrast(t.danger, Color.alphaBlend(t.dangerSurface, t.surface)), greaterThanOrEqualTo(4.5)));
      test('certified on surface', () => expect(contrast(t.certified, t.surface), greaterThanOrEqualTo(4.5)));
      test('onAccent on accent fill', () => expect(contrast(t.onAccent, t.accent), greaterThanOrEqualTo(4.5)));
      test('onSuccess on success fill (18px+ bold, 3:1 floor)', () => expect(contrast(t.onSuccess, t.success), greaterThanOrEqualTo(3.0)));
      test('onDanger on danger fill (18px+ bold, 3:1 floor)', () => expect(contrast(t.onDanger, t.danger), greaterThanOrEqualTo(3.0)));
    });
  }
}
```
(Import `dart:math` for `pow`; if the package name in `pubspec.yaml` is not `dmrv_app`, fix the
import path — check `name:` in pubspec first.)

**GATE:** new tests pass; `flutter analyze` 25/0 (new files clean); `flutter test` = 153 + new
contrast tests, 0 failures. **App rendering is bit-identical — nothing consumes the tokens yet.**
**KILL SWITCH:** delete `lib/ui/design/tokens.dart` + `test/design/` — zero references exist yet.

---

## Phase A1 — Golden harness + baseline (test-only; still zero app changes)

1. **New file** `test/goldens/golden_config.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/ui/design/tokens.dart';

Widget goldenHost({required Widget child, DmrvTokens tokens = DmrvTokens.pro}) {
  return MaterialApp(
    debugShowCheckedModeBanner: false,
    theme: buildDmrvTheme(tokens),
    home: Scaffold(body: Center(child: child)),
  );
}
```
2. Record baseline goldens for the CURRENT screens as they are (pre-migration) using plain
   `matchesGoldenFile` (no new dependency needed):
   one `testWidgets` per product screen pumping it inside a `MaterialApp` with today's theme, then
   `await expectLater(find.byType(<ScreenWidget>), matchesGoldenFile('baseline/<screen>.png'));`
   Run once with `flutter test --update-goldens test/goldens/` to record.
   *Screens with providers/BLE need their notifiers overridden with fixed fakes — reuse the fakes
   from the existing widget tests (`test/` already fakes the BLE notifiers).* If a screen is too
   entangled to golden cheaply, SKIP it and note it — do not sink hours here; the value is drift
   detection on the easy 6+.
3. **CI:** goldens run in the normal `flutter test` lane (they're just tests). Document the
   `--update-goldens` policy in the test folder README (one paragraph).

**GATE:** `flutter test` green including goldens on this machine.
**KILL SWITCH:** delete `test/goldens/` — test-only.

---

## Phase A2 — Migrate the 12 UI files to tokens (the XL phase — ONE FILE = ONE COMMIT)

**Order (leaf-first, exactly this):**
1. `lib/ui/widgets/integrity_footer.dart`
2. `lib/ui/design/premium_field_components.dart`
3. `lib/ui/widgets/rugged_button.dart` *(will be deleted in A3 — migrate minimally: colors only)*
4. `lib/ui/screens/dashboard_screen.dart`
5. `lib/ui/screens/lantana_sourcing_screen.dart`
6. `lib/ui/screens/moisture_verification_screen.dart`
7. `lib/ui/screens/pyrolysis_screen.dart`
8. `lib/ui/screens/yield_scale_screen.dart`
9. `lib/ui/screens/end_use_application_screen.dart`
10. `lib/ui/screens/proof_wallet_screen.dart`
11. `lib/ui/screens/secure_camera_screen.dart` *(keep `Colors.black` for the viewfinder — cameras are black; everything else to tokens)*
12. `lib/ui/screens/camera_debug_view.dart`

**Per-file mechanical recipe (identical every time):**
1. `main.dart:72` first (once, in commit #1): `theme: AppTheme.lightTheme` → `theme: buildDmrvTheme(DmrvTokens.field)`.
2. In the file: add `import '../design/tokens.dart';`, get `final t = context.tokens;` at the top of `build()` (for helper widgets/consts that have no context, pass `DmrvTokens` in or use static `DmrvTokens.field` TEMPORARILY with a `// TODO(A2-cleanup)` marker — zero of these may survive phase A2's final commit).
3. Replace by INTENT using this master mapping (UI_CONSISTENCY_AUDIT §2–4 lists every file's refs):

| Old (either era) | Token |
|---|---|
| `tacticalTitanium` / `deepSlate` (scaffold) | `t.surface` |
| `pureAlbedo` / `panelSlate` (cards) | `t.surfaceRaised` |
| `armorSlate*` / `fogWhite*` (text ladders) | `t.textPrimary` / `t.textSecondary` / `t.textDisabled` by opacity intent |
| `cobaltShield*` / `neonYellow*` (CTA/accent) | `t.accent` (labels on fills: `t.onAccent`) |
| `yieldGold*` / `fieldGreen*` (success/confirmed) | `t.success` |
| every private `_errorRed` / `_stopRed` / `crimsonRed*` (9 declarations — audit §3 lists file:line) | `t.danger`; soft bgs (`0xFFFEF2F2`, `crimsonRed15`) → `t.dangerSurface` |
| `midnightCyber` (footer/vault bg) | `t.chartPanel` (footer restyle per spec §3.5 happens in A3, not here) |
| `telemetryCyan` (chart trace) | keep as a file-local `const _emberTrace = Color(0xFFFFA94D);` on the field skin chart panel (spec §1.1) |
| radii 8/10/12/16/20 | `t.radiusS/M/L` (10→M, 16→L*0.8 exception documented in tokens.dart) |
| one-off paddings 6/14/18 | nearest `t.gap*` |
4. Delete the file's private color consts. Run `dart format` on the file.
5. **GATE per file (every commit):** `flutter analyze` 0 errors, no new infos; `flutter test` green;
   that file's golden updated + eyeballed; and:
   `grep -n "Color(0x" <file>` → 0 (except documented chart-trace exceptions)
   `grep -n "AppTheme\.\|FarmerTheme\." <file>` → 0.

**Phase-final gate:**
```
grep -rn "Color(0x" lib/ui/ --include=*.dart | grep -v tokens.dart     → only documented exceptions
grep -rn "AppTheme\.\|FarmerTheme\." lib/ui/screens lib/ui/widgets     → 0
```
Full batch-flow walkthrough: ZERO background/brightness changes between screens.
**KILL SWITCH:** every file is one commit → `git revert <sha>` restores any screen independently;
the deprecated `AppTheme`/`FarmerTheme` classes still exist (deleted only in A6), so a revert compiles.

---

## Phase A3 — Component merge (T5.3/T5.4)

1. **New** `lib/ui/components/dmrv_button.dart`: union API of `RuggedButton` + `PremiumFieldButton`
   — `DmrvButton({required label, required onPressed, variant = DmrvButtonVariant.primary, icon, testId, key})`,
   `enum DmrvButtonVariant { primary, success, danger, neutral, disabled }`, min-height 64,
   radius `t.radiusM`, `HapticFeedback.heavyImpact()` fired BEFORE `onPressed`, `Semantics(identifier: testId)`.
   All colors from tokens.
2. Codemod call-sites screen-by-screen (grep `RuggedButton\(|PremiumFieldButton\(`), then DELETE
   `rugged_button.dart` and the button class inside `premium_field_components.dart`.
3. **New** `lib/ui/components/dmrv_status.dart`: `DmrvErrorPanel(message)` (bg `t.dangerSurface`,
   border `t.danger` 2px, text `t.danger`, `t.blockHeader`, always appends the reassurance line
   from ARB key `error_other_data_safe`), `DmrvLoading(label)`, `DmrvEmptyState(icon, message)`.
   Replace the four divergent error panels (audit §4 table: moisture/pyrolysis/yield/endUse).
4. Delete dead code: `lib/ui/widgets/premium_action_card.dart` (148 lines, 0 references) and
   `PremiumInputField` (premium_field_components.dart:287, 0 references).

**GATE:** `grep -rn "RuggedButton\|PremiumFieldButton\|PremiumActionCard\|PremiumInputField" lib/` → 0;
widget tests migrated (keys preserved); goldens updated; analyze/test green.
**KILL SWITCH:** per-step commits; dead-code deletion is its own commit (revert restores).

---

## Phase A4 — String externalization (T5.5)

1. Sweep every user-visible literal in `lib/ui/screens/` into `lib/l10n/app_en.arb` + `app_hi.arb`
   (~10 keys today → 60–120). The audit §6 lists the offenders (proof_wallet 49/98, pyrolysis
   154/307, all moisture/endUse block headers, camera screens).
2. **Brand strings are NOT l10n:** `'TerraCipher'` and `'dMRV Field Terminal v3.0'`
   (dashboard_screen.dart:511,518) go into `lib/config/brand.dart` (Phase C1 stub now: a const class).
3. **New test** `test/l10n_parity_test.dart`: en/hi key sets are equal; and a source test asserting
   no `Text('` raw literal in `lib/ui/screens/` (allowlist: `camera_debug_view.dart`).

**GATE:** parity test green; app runs in hi + en; analyze/test green.
**KILL SWITCH:** ARB additions are additive; per-screen commits.

---

## Phase A5 — Navigation policy (T5.6)

1. **New** `lib/ui/routes.dart` with named route constants; replace inline `MaterialPageRoute`s.
2. Freeze-forward made TOTAL: post-pyrolysis screens wrapped in `PopScope(canPop: false)` with a
   "batch in progress" explanation; `pushReplacement` used consistently from pyrolysis onward
   (today: pyrolysis_screen.dart:78 and yield_scale_screen.dart:82 replace, sourcing→moisture pushes
   — half-enforced is the bug).
3. **New test:** widget test drives the full flow, asserts back-stack at each step.

**GATE:** flow test green; manual back-button walkthrough matches the documented policy.

## Phase A6 — Delete the old themes (the point of no return — LAST)

Only when A2–A5 gates are all green: delete `app_theme.dart` + `farmer_theme.dart`, fix any
stragglers the compiler finds. **GATE:** `grep -rn "app_theme\|farmer_theme" lib/` → 0; everything green.
**KILL SWITCH:** this commit alone can be reverted to restore the aliases.

---

## Phase B1 — The skin switch (T5.7)

**New file** `lib/config/app_skin.dart`:
```dart
import '../ui/design/tokens.dart';

enum AppSkin { field, pro }

AppSkin resolveSkin() {
  const raw = String.fromEnvironment('DMRV_SKIN', defaultValue: 'field');
  return raw == 'pro' ? AppSkin.pro : AppSkin.field;
}

extension AppSkinTokens on AppSkin {
  DmrvTokens get tokens =>
      this == AppSkin.pro ? DmrvTokens.pro : DmrvTokens.field;
}
```
`main.dart`: `theme: buildDmrvTheme(resolveSkin().tokens)`. Debug-only skin toggle: a long-press on
the dashboard version footer flips a `StateProvider<AppSkin>` override (debug builds only).

**GATE:** `flutter run --dart-define=DMRV_SKIN=pro` renders EVERY screen in pro with zero code
edits — this is the honesty test of Stage A. Goldens recorded for both skins (9 screens × 2).
**KILL SWITCH:** default is `field`; omit the define and nothing changed.

## Phase B2 — Pro-skin calibration (T5.8) + `lib/util/formats.dart`
Token-value-only changes (screens untouched): denser gaps, 56px hero cap, locale-driven
`DateFormat.yMMMd(locale)` / decimal separators through one `formats.dart`. Write
`docs/engineering/SKINS.md` (personas, defaults, the both-skins-in-same-PR rule — already enforced
structurally by required constructor params).
**GATE:** side-by-side screenshot sheet; contrast tests still green (they run on both skins already).

## Phase B3 — Golden matrix (T5.9)
Extend goldens to (screen × skin × {en, hi}); CI renders both. **GATE:** matrix green in CI.

## Phase C1–C3 — White-label (T5.10–12)
1. **C1** `lib/config/brand.dart` (`Brand{appTitle, shortName, logoAsset, footerLine, accentOverride?, supportContact}`)
   loaded via `--dart-define-from-file=brand/<name>.json`; replace the dashboard brand strings;
   gate: `grep -rn "TerraCipher" lib/` → 0; a unit test loads every `brand/*.json` against the model.
2. **C2** Android `productFlavors` per brand (own id/label/icon; keystore-per-brand). **BLOCKED by
   T0.6 (real release keystore) — do C1/C3 first.**
3. **C3** `scripts/new_whitelabel.sh` + `docs/engineering/WHITELABEL.md`; gate: fictional brand
   end-to-end in <1 day, timed.
**KILL SWITCH:** default `brand/terracipher.json` reproduces today's strings; no JSON → compile-time defaults.

---

# Appendix — Kill-switch summary (the one-click table)

| Change | Off switch |
|---|---|
| ALL demo edits (DP1–DP5) | never merge / delete branch `demo/eu-demo` |
| TEST-button hiding | only active when built with `DMRV_DEMO_MODE=true` |
| Verifier page | delete `demo_tools/` (nothing references it) |
| Token layer (A0) | delete 2 files (unreferenced until A2) |
| Golden harness (A1) | delete `test/goldens/` |
| Any migrated screen (A2) | `git revert` that screen's single commit (aliases keep it compiling until A6) |
| Component merge / dead-code delete (A3) | revert the step's commit |
| Skin switch (B1) | omit `--dart-define=DMRV_SKIN` → default unchanged |
| Brand config (C1) | omit the dart-define file → built-in TerraCipher defaults |
| Backend / schema / sync canonical | **never touched by anything in this file** |
