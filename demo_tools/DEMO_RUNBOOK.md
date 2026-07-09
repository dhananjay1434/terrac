# dMRV Demo Runbook — flow + word-for-word script

Two devices in front of you: **the phone** (the field app) and **the laptop** (the
backend + the auditor's browser page). The story is: *the farmer captures evidence
on the phone → it syncs to the server → the auditor sees a verified compliance
record in the browser.*

---

## PART A — Set up before the audience arrives (~5 min, do it once)

Open **3 PowerShell terminals** in the project folder
(`C:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`).

**Terminal 1 — the backend** (note `DMRV_ALLOWED_ORIGIN` — this lets the browser
page talk to it). Secrets are NOT written here anymore — the easiest path is to
just run `demo_tools\1_start_backend.bat`, which loads them from the gitignored
`demo_secrets.bat`. To run by hand, first source your secrets, then start:
```powershell
cd backend
# one-time: copy ..\demo_tools\demo_secrets.example.bat to demo_secrets.bat and fill in.
cmd /c "..\demo_tools\demo_secrets.bat && set" | ForEach-Object { if ($_ -match '^(DMRV_[^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1],$matches[2]) } }
$env:DATABASE_URL="sqlite+aiosqlite:///./dmrv.db"; $env:DMRV_ALLOWED_ORIGIN="http://localhost:8080"; python -m uvicorn server:app --host 0.0.0.0 --port 8000
```
Leave it running. Test: open `http://localhost:8000/api/health` in the browser → should say `{"status":"ok"...}`.

**Terminal 2 — the auditor web page:**
```powershell
python -m http.server 8080 -d demo_tools/verifier_view
```
Leave it running.

**Terminal 3 — launch the app on the phone** (phone on the SAME Wi-Fi as the laptop):
```powershell
C:\Users\bit\development\flutter\bin\flutter.bat run -d RZCY511HZBE --dart-define=DMRV_API_BASE_URL=http://192.168.1.19:8000 --dart-define=ENROLLMENT_TOKEN=demo-eu-3 --dart-define=DMRV_DEMO_MODE=true
```
(If `192.168.1.19` isn't the laptop's IP tomorrow, run `ipconfig | findstr IPv4` and use the Wi-Fi one. `demo-eu-3` is the last spare token — the app is already enrolled so it normally won't be used.)

**Get the finale page ready** (Terminal 4, or reuse one):
```powershell
python demo_tools/pick_batch.py
```
It prints your batches and a ready URL. **Copy the printed URL, open it in the browser, and leave that tab open** — it auto-loads the compliance record. That tab is your Act 3.

> Today's best batch to show: `651b7c13-62ad-49b2-aebd-4bdb3da400c0` (highest credit, 0.15 t CO₂e). The `pick_batch.py` URL already points at the most-complete one.

**Have open and ready:** the phone (on the dashboard), and the browser tab with the verifier page loaded. That's it.

---

## PART B — The flow + what to say (3 acts, ~4–5 min)

### ACT 1 — The problem (15 seconds, phone in hand)
> "Today, a rural biochar burn becomes a carbon credit through a paper logbook and trust — and months later an auditor has no way to prove the data wasn't faked. We built the sensor and the notary for that process. This is the field app the operator uses."

### ACT 2 — Capture a burn (2 min, on the phone)
Walk the flow, tapping through. Say this as you go:

- **Dashboard:** "This is the operator's home. One clear next action, and a banner that always tells them their data is safe — because they work offline, in the field, with no signal."
- **Sourcing (Step 01):** "They log the feedstock and the harvest — GPS-anchored, with a 72-hour drying rule the app enforces."
- **Moisture (Step 02):** "They photograph the moisture reading. The photo is hashed and GPS-stamped the instant it's taken — it can't be swapped later."
- **Pyrolysis (Step 03):** "Live kiln temperature from a Bluetooth thermocouple, plus smoke-stage photos. Right now it's a simulated sensor for the demo, but it's the same pipeline as the real hardware."
- **Yield (Step 04):** "The biochar weight, locked in from a Bluetooth crane scale."
- **End-Use (Step 05):** "Where it was applied, who received it, GPS, and a photo — then Commit closes the batch."
- **Proof Wallet** (tap it): "Every batch becomes a cryptographic receipt. This is the operator's proof it happened."

Key line to land: **"Every piece of evidence is signed by a key that never leaves the device — so the server itself can't forge it."**

### ACT 3 — The auditor's view (90 sec, switch to the laptop browser)
Switch to the already-open verifier tab. Say:

> "Everything the operator captured has now synced to the backend. This is what a manager or a Rainbow auditor sees — the compliance record for that batch."

Point at the screen:
- **The verdict badge:** "This batch is marked **PROVISIONAL** — not yet issuable. The system never calls a credit 'issued' until every requirement is met. That conservatism is the whole point — an auditor can trust it."
- **The checklist:** "Every criterion in the methodology — biomass, moisture, pyrolysis photos, yield, delivery, lab carbon, and the annual and project-level gates — is checked here, each with its enforcement status. 'Enforced' means it's a live gate; 'N/A' means it doesn't apply to this batch; 'awaiting methodology' is a gate we've built but that's waiting on external sign-off."
- Closing line: **"So the credit isn't a number someone typed — it's the output of grading real, signed, field-captured evidence against the methodology. That's the trust we're selling."**

---

## PART C — If something goes wrong (glance here)

| Symptom | Fix |
|---|---|
| Browser page shows a red CORS/connection error | Backend wasn't started with `DMRV_ALLOWED_ORIGIN="http://localhost:8080"` — restart Terminal 1 with it (Part A). |
| Page shows `unknown_device` / 403 | That's a phone-sync issue, not the page. The page reads the backend directly and still works — proceed. |
| App stuck on logo | It won't with the current build (boots offline). If it does, the backend/token is unreachable — the app still shows the UI; skip to Act 3 with a pre-existing batch. |
| Phone won't sync | Doesn't matter for the finale — Act 3 shows a batch already on the server. Keep going. |
| Don't want to risk a live capture | Skip Act 2's Commit; just *show* the screens, then jump to Act 3's pre-loaded batch. The finale doesn't depend on the batch you captured live. |

**The golden rule:** Act 3 shows a batch that's **already on the server** (via the `pick_batch.py` URL). It does **not** depend on the batch you capture live — so even if the phone misbehaves, your finale still works.
