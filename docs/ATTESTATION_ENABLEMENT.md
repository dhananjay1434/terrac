# Device Attestation — Enablement Runbook (V7 P4, option b)

## Status: mechanism BUILT + TESTED, enforcement OFF by design

Device attestation gates whether an unverified (rooted / emulated / repackaged /
non-genuine) device can produce an **issuable** batch. The full enforcement
machinery, policy evaluation, anti-replay, and fleet-grace window are
implemented and covered by tests (`backend/tests/test_p4_1_attestation.py`,
`test_attestation.py`). It is **intentionally OFF** because the final decode
step needs *your* Google Play Integrity credentials, which don't exist yet.

**This is a deliberate, honest state — not a stub pretending to work.** Until
enforcement is turned on, the interim device-trust control is the client-side
RASP (freerasp) shipped in V7 P1, which hard-locks the app on root / hooks /
emulator / debugger / repackaging.

## What "off" means today (be honest with auditors)

- A genuine Play Integrity token still returns `unverified` (no decoder wired),
  and with `DMRV_ATTESTATION_ENFORCED` unset, `attestation_ok` is forced true
  (`backend/credit_engine.py:183`). So server-side, device authenticity is NOT
  yet a gate on issuance.
- The signed-payload GPS, replay protection, mock-location detection, and (V7
  P3) EXIF-GPS corroboration ARE active — attestation is the one remaining
  fraud layer that's dormant.

## What is already in place (no code needed to turn on)

| Piece | Where | State |
|---|---|---|
| Enforcement switch | `DMRV_ATTESTATION_ENFORCED` env (`credit_engine.py:183`) | ready — unset = off |
| Policy evaluation | `evaluate_play_integrity_verdict` (`attestation.py:55`) | fully implemented + tested |
| Decoder seam (needs creds) | `configure_play_integrity_decoder(decoder)` (`attestation.py:44`) | returns "verifier_not_configured" until wired |
| Expected package | `DMRV_PLAY_INTEGRITY_PACKAGE` env (`attestation.py:52`) | set to `io.dmrv.dmrv_app` when enabling |
| Fleet grace window | `attestation_in_grace` (`credit_engine.py:190`) | ready — devices enrolled pre-enforcement tolerated |
| Anti-replay nonce | bound to per-request `signed_at` (`attestation.py:81`) | ready |
| App-side attestation blob | `hw_attestation_json` (ESP32 secure-element ECDSA), Drift schema v10 | app already collects it |

## How to TURN IT ON (when Play Integrity credentials exist)

1. **Create a Google Play Integrity project** for package `io.dmrv.dmrv_app`
   (Play Console → app integrity), obtain the decode credentials (either the
   `playintegrity.googleapis.com decodeIntegrityToken` service-account path, or
   the local JWE decrypt keys).
2. **Wire the decoder** at deploy/startup — call once during app boot:
   ```python
   from attestation import configure_play_integrity_decoder
   configure_play_integrity_decoder(my_decoder)  # token:str -> claims:dict, raises on bad token
   ```
   The decoder is the ONLY new code; the policy/enforcement around it already
   exists. `None` = "no verifier configured" (current default).
3. **Set env** on the backend (Render / compose):
   - `DMRV_ATTESTATION_ENFORCED=1`
   - `DMRV_PLAY_INTEGRITY_PACKAGE=io.dmrv.dmrv_app`
   - (optional) tune the grace-window duration used by `attestation_in_grace`.
4. **App side:** confirm the Flutter client attaches a FRESH Play Integrity
   token per telemetry submission, bound to that request's `signed_at` (the
   nonce anti-replay contract in `attestation.py:81`). The ESP32
   `hw_attestation_json` path already flows in `tel_payload["hw_attestation"]`;
   the phone Play Integrity token needs to ride the same channel. This is the
   one app-side task required before flipping enforcement on.

## How to VERIFY after enabling

- Run `python -m pytest backend/tests/test_p4_1_attestation.py backend/tests/test_attestation.py`
  — the policy + grace + nonce tests already assert enforced behavior via an
  injected decoder double.
- Smoke: a batch from a genuine device → issuable; a batch with a
  missing/invalid token and a device OUT of grace → PROVISIONAL with reason
  `attestation_unverified`.

## Demo note

For demos, leave it OFF (this state). Attestation-off does not affect the demo
flow — batches still capture, sync, and render. Turning it on only matters for
real credit issuance, where an auditor will ask "how do you know the device is
genuine?" — at which point steps 1-4 above are the answer.
