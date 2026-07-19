# ENROLLMENT QR — Paste-to-Autofill (V6)

## THE FRICTION

Enrolling a device needs TWO fields typed by hand: the server URL and a long
one-time token (`NCt_VLaTnV9oMnpk8gdelqWyhqA7aP2PNxVW7irq7S8`). Typing a 43-char
token on a phone is error-prone; the URL is easy to get wrong. The portal
already mints a QR that contains BOTH values, so the operator shouldn't have to
type either.

## KEY FACT (verified in code)

The portal's mint endpoint (`backend/portal/routes.py:165`) builds:

```
dmrv-enroll:v1:{"url":"<server url>","token":"<token>"}
```

— a versioned prefix + compact JSON with `url` and `token`. So ONE payload
carries everything the enrollment screen needs.

## THE DECISION (and why)

Two ways to get that payload into the app:

1. **Camera scan** — requires adding a QR-SCANNER dependency. The app today has
   `qr_flutter` (generation only) and **no scanning capability whatsoever** — no
   `mobile_scanner`, no `BarcodeDetector`. Adding one means a new native
   dependency, new camera-permission surface, and build/hardware risk on the
   target device (an old Android 11 Micromax). Higher blast radius.

2. **Paste-to-autofill (CHOSEN)** — the enrollment screen already has a token
   text field. Make it recognize a pasted `dmrv-enroll:v1:...` payload and
   auto-split it into the URL + token fields. ZERO new dependencies, no camera,
   no native surface, no build risk. Solves the typing friction (operator/admin
   copies one string; the app parses it). This is the "best that won't break
   anything" path.

Camera scan is documented as an OPTIONAL later phase (Phase 3) once a scanner
package is vetted on the real hardware — it reuses the same parser this prompt
builds, so no rework.

## HARD RULES

- **No new dependencies** in Phases 1-2. (Phase 3, if ever done, adds one — but
  only with explicit approval.)
- No API changes, no change to `CryptoSigner.registerDevice`, no change to the
  enrollment network call or the `EnrollmentController` state machine.
- The parser is PURE (no Flutter/IO imports) so it unit-tests without a device.
- Backward compatible: a plain token (no `dmrv-enroll:` prefix) pasted into the
  token field must STILL work exactly as today. The URL field must still be
  editable by hand. Nothing about the current manual flow regresses.
- Gate each phase: `flutter analyze` (changed files) + `flutter test`. One
  commit per phase. Do NOT push.
- Read every target file verbatim before editing.

---

## PHASE 1 — Pure parser + tests

New file: `lib/data/enrollment_qr.dart`.

```dart
import 'dart:convert';

/// Parsed enrollment payload from the portal's mint QR / copy string.
class EnrollmentPayload {
  const EnrollmentPayload({required this.url, required this.token});
  final String url;
  final String token;
}

/// Parses the portal enrollment payload `dmrv-enroll:v1:{"url":..,"token":..}`.
/// Returns null when [raw] is not a well-formed enrollment payload, so the
/// caller can fall back to treating the input as a bare token. Pure + testable;
/// never throws on bad input.
EnrollmentPayload? parseEnrollmentQr(String raw) {
  const prefix = 'dmrv-enroll:v1:';
  final s = raw.trim();
  if (!s.startsWith(prefix)) return null;
  final jsonPart = s.substring(prefix.length);
  try {
    final decoded = jsonDecode(jsonPart);
    if (decoded is! Map) return null;
    final url = decoded['url'];
    final token = decoded['token'];
    // token is required; url may be empty string (admin minted without a base
    // url) — in that case the operator keeps/edits the URL field manually.
    if (token is! String || token.trim().isEmpty) return null;
    return EnrollmentPayload(
      url: url is String ? url.trim() : '',
      token: token.trim(),
    );
  } catch (_) {
    return null;
  }
}
```

New test: `test/enrollment_qr_test.dart` — cover:
- valid payload → correct url + token
- valid payload with empty `"url":""` → token set, url ''
- bare token (no prefix) → null (caller treats as plain token)
- malformed JSON after prefix → null (no throw)
- missing/blank token → null
- surrounding whitespace tolerated
- prefix present but wrong version (`dmrv-enroll:v2:`) → null

Gate: `flutter test test/enrollment_qr_test.dart` green; `flutter analyze
lib/data/enrollment_qr.dart test/enrollment_qr_test.dart` clean.

**Commit:** `feat(app): pure parser for the dmrv-enroll QR/copy payload`

---

## PHASE 2 — Wire paste-to-autofill into the enrollment screen

File: `lib/ui/screens/enrollment_screen.dart` (read it verbatim first).

The token field is built by `_field(...)` with `_tokenCtrl`. Add an
`onChanged`-driven detection: when the text pasted into the TOKEN field parses
as an enrollment payload, split it — set the token field to the bare token and
the URL field to the payload URL (only overwrite the URL when the payload
carried a non-empty one, so a URL-less payload leaves the operator's URL
intact).

Concretely:
- Import `../../data/enrollment_qr.dart`.
- In the token field's `onChanged` (currently `(_) => setState(() {})` via the
  shared `_field`), special-case the token controller. Simplest robust approach:
  give the token field its own `onChanged` rather than the shared one. On each
  change, run `parseEnrollmentQr(value)`; if non-null:
  - `_tokenCtrl.text = payload.token;` (strip it down to the bare token)
  - if `payload.url.isNotEmpty` → `_urlCtrl.text = payload.url;`
  - reset both controllers' selection to end to avoid cursor jump
  - `setState(() {})` so `_canEnroll` re-evaluates
- Add a one-line hint under the token field: `"Tip: paste the whole enrollment
  code — the server URL fills in automatically."` (static Text, themed like the
  existing secondary copy).
- Everything else on the screen is UNCHANGED — the URL field stays hand-editable,
  the Enroll button, the KYC button, the error panel, the controller call all
  stay exactly as they are.

Do NOT change `_field`'s signature in a way that breaks the URL field's existing
call. If you add an optional `onChanged` param to `_field`, default it to the
current behavior so the URL field is untouched.

Gate: `flutter analyze lib/ui/screens/enrollment_screen.dart` clean;
`flutter test` full suite green (the pure enrollmentErrorMessage /
controller tests must still pass unchanged). If an existing widget test drives
the token field, confirm it still passes; do not weaken it.

**Commit:** `feat(app): enrollment screen auto-splits a pasted dmrv-enroll payload into url + token`

---

## PHASE 3 — OPTIONAL camera scan (DO NOT build without explicit approval)

Only if the user later asks for in-app camera scanning:
- Add a vetted scanner dep (evaluate `mobile_scanner` on the real Micromax
  first — camera2 compat on old MediaTek SoCs is not guaranteed).
- Add a "Scan enrollment QR" button that opens the scanner, reads one QR, and
  runs the SAME `parseEnrollmentQr` from Phase 1 → fills both fields → lets the
  operator review, then tap Enroll (no auto-submit).
- New native permission + build surface → full regression + on-device test.

This phase is intentionally deferred; Phases 1-2 already remove the typing
friction with zero dependency risk.

## ACCEPTANCE

- Pasting `dmrv-enroll:v1:{"url":"https://dmrv-api.onrender.com","token":"..."}`
  into the token field fills both fields correctly; Enroll works.
- Pasting a bare token still works (URL kept as-is / hand-entered).
- A URL-less payload fills the token, leaves the URL field editable.
- No new dependency added; full `flutter test` suite green; nothing pushed.
