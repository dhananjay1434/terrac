# 01 — Security Analysis

This product's entire value proposition is *trust* ("Truth Machine" for carbon
credits). The security controls are extensive on paper but collapse under
scrutiny. Below, ordered by severity, with exact locations.

---

## 🔴 SEC-1 — Device "authentication" provides no identity assurance
**Files:** `backend/server.py:196-213` (register), `:155-194` (verify_hmac),
`lib/services/crypto_signer.dart:27-81`

The trust chain is circular:
1. The Flutter client **generates its own random HMAC key** on first launch
   (`crypto_signer.dart:_readOrCreateOnce`).
2. It then **registers that key itself** via `POST /api/v1/register`, which is
   **completely unauthenticated** — no token, no attestation, no proof of
   anything.
3. The server later "verifies" a request's signature against the very key the
   client uploaded.

Net effect: an HMAC check only proves *"whoever sent this also told us the key
earlier."* That is tamper-evidence in transit, **not authentication**. Any
attacker can:
- Register an arbitrary `device_id` + key and submit fully "verified" batches.
- **Overwrite an existing device's key** — `register_device` does
  `existing.hmac_key = payload.hmac_key` (`server.py:205-206`) with no ownership
  check → device hijack / denial of service.

**Fix direction:** Registration must be gated (enrollment token, server-issued
device credential, or hardware attestation / Play Integrity / DeviceCheck).
Keys must be server-issued or bound to an attested device, and never
overwritable without proving control of the existing key.

---

## 🔴 SEC-2 — Unknown/forged devices silently fall back to a shared global secret
**File:** `backend/server.py:171-180`

```python
if not x_device_id:
    secret = _HMAC_SECRET.encode("utf-8")
else:
    ... if not device: secret = _HMAC_SECRET.encode("utf-8")
```

If the device id is missing **or unknown**, verification falls back to a single
process-wide `DMRV_HMAC_SECRET`. So one leaked/guessed shared secret signs for
*everyone*, and an unregistered attacker is treated as a first-class signer.
There is no per-device isolation and no concept of "unknown device = reject."

**Fix direction:** Unknown device → reject (401/403). No global fallback secret
for production request signing.

---

## 🔴 SEC-3 — Carbon credits are minted for unverified & unsigned batches
**File:** `backend/server.py:165-167, 263-287`

When the HMAC header is missing, `verify_hmac` **does not reject** — it logs a
warning and `return False`. `create_batch` then **still runs the full LCA** and
writes `net_credit_t_co2e`, only flipping `status` to `"UNVERIFIED"`:

```python
status="RECEIVED" if is_verified else "UNVERIFIED",
net_credit_t_co2e=net_credit,   # computed regardless
```

For a registry, an `UNVERIFIED` row carrying a real credit number is a landmine:
anyone can submit unsigned payloads and get issuance math attached.

**Fix direction:** Unsigned/invalid signature → `401`/`403`, no row, no credit.
If "draft" capture is desired, store it in a quarantine table with **no credit
field** until verified.

---

## 🔴 SEC-4 — Mock-GPS / fraud detection is self-reported by the attacker
**Files:** `backend/server.py:162-163, 358-359`, `lib/services/sync_queue_manager.dart:281-293,370`,
`lib/services/location_service.dart:36-44`

The server rejects mock location by reading the **`X-Mock-Location` request
header** — which the *client* sets from its own payload flag
(`sync_queue_manager.dart:370`). A fraudster simply sends `false`. This is the
textbook "ask the liar if they're lying" anti-pattern.

Compounding it: the client's own mock check (`location_service.dart:36`) only
fires `if (pos.isMocked && kReleaseMode)`, so debug/sideloaded builds skip it
entirely, and `DemoLocationService` **fabricates Delhi coordinates** with
`isMocked: true` as a fallback.

**Fix direction:** GPS authenticity must be assessed server-side from
signals the client cannot trivially forge (attested location, plausibility vs.
declared polygon, server timestamp vs. EXIF, speed/teleport checks), not a
self-declared boolean.

---

## 🔴 SEC-5 — Secrets and full prompt history committed to the repo
**Files:** `backend/.env`, `.gitignore`, `all_user_inputs.txt`

- `backend/.env` is committed and contains DB credentials
  (`DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dmrv`)
  plus leftover `MONGO_URL`, `DB_NAME`, `CORS_ORIGINS="*"`.
- `.gitignore`'s "Environment files" section is **empty** (only ignores
  `*token.json*` / `*credentials.json*`) — so `.env` is **not** ignored.
- The `.gitignore` file itself is **corrupted** — it contains UTF-16 / NUL-byte
  garbage near the end (`b a c k e n d / u p l o a d s /`), so git treats it as
  binary and ignore rules there are unreliable.
- `all_user_inputs.txt` (547 KB) and `longest_msg.txt` are a full dump of the
  development chat/prompt history — internal information leak; should never be
  in a product repo.

**Fix direction:** Purge secrets from history, rotate the DB password, rewrite
`.gitignore` as clean UTF-8 with real env/db/build/uploads rules, delete prompt
dumps. (See `06_REPO_HYGIENE_AND_CONFIG.md`.)

---

## 🟠 SEC-6 — `DMRV_HMAC_SECRET` is required but absent → server won't boot; and key sizing is wrong
**Files:** `backend/server.py:32-34`, `backend/.env`, `crypto_signer.dart:39-42,64`

- `server.py` hard-requires `DMRV_HMAC_SECRET`, but it is **not in `.env`** — the
  service raises `RuntimeError` at import. Config and code disagree.
- The per-device key is 32 random bytes rendered as a 64-char **hex string**,
  then HMAC is keyed on the *UTF-8 bytes of the hex string* (`utf8.encode(hexKey)`),
  and the server keys on `device.hmac_key.encode('utf-8')`. It "works" only
  because both sides made the same mistake. The effective key is the hex text,
  not the 32 raw bytes — fragile and confusing; any refactor on one side breaks
  auth silently.

---

## 🟠 SEC-7 — CORS configuration is dead / inconsistent
**Files:** `backend/server.py:53-61`, `backend/.env:3`

The code reads `DMRV_ALLOWED_ORIGIN` (singular, never set), while `.env` sets
`CORS_ORIGINS="*"` (never read). So `allow_origins` is effectively `[]`
(all browser cross-origin calls blocked) — *or*, if someone "fixes" it by wiring
`CORS_ORIGINS="*"` in, it becomes wide-open. Pick one variable, validate it, and
never combine `*` with credentials.

---

## 🟠 SEC-8 — Device-integrity (RASP) shipped with placeholder config
**File:** `lib/services/device_integrity_service.dart:17-28`

FreeRASP is initialized with literal placeholders:
`signingCertHashes: ['YOUR_BASE64_CERT_HASH']`, `teamId: 'YOUR_TEAM_ID'`.
With wrong cert hashes, integrity/binding checks are meaningless. Worse,
detection only sets a Riverpod flag (`deviceCompromisedProvider`) —
**capture and sync continue regardless**; enforcement depends on a screen
choosing to watch the flag. Detection without enforcement is not a control.

---

## 🟡 SEC-9 — Information leakage in logs & responses
**Files:** `backend/server.py:471, 413, 330`, `:445/476` (`file_path`)

- Full `sha256_hash` and `operation_id` are logged at INFO (`[media] STORED …`).
- The media upload **returns the absolute server filesystem path**
  (`file_path=str(file_path)`) to the client, leaking server layout.
- `sentry_flutter` scrubbing in `main.dart:35-39` only drops breadcrumbs whose
  message literally contains `lat=`/`lon=`; other GPS/PII formats pass through.

---

## 🟡 SEC-10 — Cleartext + hardcoded endpoint in registration
**File:** `lib/services/crypto_signer.dart:67-68`

`registerDevice()` posts to a hardcoded `http://10.0.2.2:8000/...` (emulator
loopback, plaintext HTTP) while the sync layer uses an env-driven (presumably
HTTPS) base URL. In the field this both (a) leaks the key over cleartext on the
dev path and (b) guarantees registration fails in production (see BUG-4).

---

## Security scorecard

| Control claimed | Reality |
|---|---|
| Device authentication | ❌ Self-asserted, unauthenticated enrollment |
| Per-device key isolation | ❌ Global secret fallback |
| Reject unverified data | ❌ Stored + credited as `UNVERIFIED` |
| Anti-mock-GPS | ❌ Client self-reports a header |
| RASP / root detection | ⚠️ Placeholder config, no enforcement |
| Encryption at rest (SQLCipher) | ✅ Genuinely implemented (one real strength) |
| TLS cert pinning (release) | ✅ Implemented & fails-closed (`sync_queue_manager.dart:76-102`) |
| Secret management | ❌ `.env` + prompt dump committed |
