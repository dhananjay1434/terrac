# ADR-002 — Edge transport & local cryptography
**Status:** DECIDED (CPO/architect, 2026-07-27) · Complements ADR-001 · Amends `docs/edge-firmware-contract.md` (v2 sections below)
**Question:** How does sensor telemetry travel from remote kilns to the server, and how is data protected while it sits on the device — consistent with the platform's core cryptographic architecture?

---

## 1 · Transport decision: BLE phone-gateway standard; cellular as an optional module

**DECIDED: the standard artisanal transport is store-and-forward over the operator's phone.** The edge unit records everything locally; when a phone is in Bluetooth range, the app drains the backlog and relays it to the existing ingest endpoint. Cellular-direct (SIM in the unit) becomes an **optional plug-in module** for industrial/fixed sites only — never a fleet requirement.

### Independent scaling rationale (why this wins, not just preference)
1. **Artisanal burns are attended *by definition*.** Kon-Tiki flame-curtain operation requires an operator continuously feeding feedstock layers — a human (with a phone) is at the kiln for the whole burn. "Live view of an unattended burn" is a phantom requirement at Tier-artisanal; the phone is *always* there when liveness matters.
2. **Fleet economics.** SIM-per-kiln = recurring opex + procurement + top-ups + dead-SIM debugging across 259→thousands of kilns in three countries' worth of telecom bureaucracy. BLE costs ₹0/month forever. The marginal kiln costs a sensor kit, not a subscription.
3. **Coverage reality.** Kiln sites are chosen by biomass logistics, not tower coverage. A design that *requires* signal at the kiln fails exactly where we operate (the user's own words: "this is our remote area"). Phones travel to coverage; kilns don't.
4. **Ops simplicity.** One connectivity fleet to manage (phones — which already exist for evidence capture) instead of two.
5. **Industrial is genuinely different** (grid power, fixed site, often Wi-Fi/Ethernet, unattended runs) — there the cellular/LAN module earns its cost. Same firmware, same envelope, different transport plug — the server cannot tell the difference and doesn't care.

### What this changes
- The phone becomes a **courier, not a trust party** (see §2 — it relays sealed envelopes it cannot forge, alter, or silently drop).
- Flutter work enters scope as a **new phase M7** (it does NOT amend the M0–M6 "no mobile changes" rule — M0–M6 stay exactly as scoped; M7 is additive and can run any time after M2.2 exists).
- Liveness semantics: "live" = operator-present (BLE latency <1 s → phone shows the curve in real time; phone online → portal sees it seconds later). Unattended periods are captured locally and reconciled at next sync — **complete-always, live-when-present.**

## 2 · Local cryptography: the same architecture, extended to rest

Core platform principle: *sign at the moment of capture with a per-device key; storage and transport are untrusted.* The edge unit follows it exactly.

### 2.1 Keys & provisioning
- **Ed25519 keypair generated ON the ESP32-S3 at provisioning; the private key never leaves the device.** Public key registered through the existing `EnrollmentToken` flow (`POST /api/v1/register`) — an edge unit is just another device to the backend. Same primitive as the phones (`security.py` verifies Ed25519; nothing new server-side).
- Key storage: ESP32-S3 **NVS with flash encryption enabled + secure boot v2** (eFuse-burned). Extracting the key requires silicon-level attack, not SD-card theft.

### 2.2 Sign-at-capture + per-batch hash chain (the new part)
Every 10 s-aggregated chunk is signed **at write time, before it touches storage**, and chained:

```
envelope_n = {
  device_id, batch_uuid, channel, t_start, sample_period_s, values[],
  seq: n,                          // monotonic per (batch_uuid, channel)
  prev_hash: SHA256(envelope_{n-1})  // "GENESIS" for n = 0
}
signature_n = Ed25519_sign(device_key, canonical_bytes(envelope_n))
SD_card.append(envelope_n, signature_n)
```

What the chain buys (this is the point):
| Attack on the SD card / courier phone | Outcome |
|---|---|
| Alter a value in any chunk | signature of that chunk fails → rejected |
| Forge a new chunk | no device key → impossible |
| Delete a chunk from the middle | next chunk's `prev_hash` doesn't match → **gap is evident**, recorded as a sensor gap (which, per ADR-001 A3/A4, can only *shorten* eligibility — tampering can never help a batch) |
| Reorder chunks | seq + prev_hash mismatch → evident |
| Replay/duplicate a chunk | server idempotency key dedups → counted once |
| Steal the SD card | data is evidence, not secrets (temperatures aren't confidential); the KEY isn't on the card |

Net: **SD card and phone are untrusted by construction.** A hostile courier can at worst *withhold* data — and withholding is visible (chain gap) and only ever reduces the credit claim. This is strictly stronger than Circonomy's trusted-IoT model and is the same story as the rest of the moat: *we don't trust; we verify.*

### 2.3 Server-side verification (deltas to M2 — small and additive)
- `telemetry_chunks` gains two nullable columns: `seq INT NULL`, `prev_hash VARCHAR(64) NULL` (nullable → legacy/cellular chunks without chains stay valid; additive migration — if M2.1's migration has already landed, this is a follow-up migration, 5 lines).
- Ingest (M2.2) additionally: verify chain continuity per (batch, channel); a break is stored and surfaced as a **gap annotation**, never a rejection (the data on either side is still individually signed and true).
- No change to `telemetry_bus`, charts, bridge, or anything pre-built — the envelope is what they already consume, plus two fields they ignore.

### 2.4 Time integrity
- RTC (DS3231 + coin cell) mandatory on the unit; GPS time when the module exists.
- Existing rule stands (audit A5): future `t_start` rejected; old chunks always accepted (offline backfill is normal).
- At each phone sync, the app includes its own GPS/network time in the sync session record — a free, independent cross-check on device clock drift (flag drift > 10 min as an advisory, never a block).

## 3 · The sync protocol (phone ↔ edge, M7)
1. Phone connects over BLE (edge advertises when it has unsent data; pairing pinned to the site's registered units).
2. `GET unsent` → edge streams envelopes oldest-first (chunked, resumable mid-transfer).
3. Phone forwards each to `/api/v2/telemetry/ingest` (existing endpoint, existing retry/idempotency semantics); buffers locally (existing offline-first machinery) when the phone itself has no signal.
4. Server ack per chunk → phone acks edge → edge marks sent (retained on SD as archive until space pressure).
5. Operator sees a sync-health line (same UX language as the app's existing `sync_health_screen`).

## 4 · Scope & sequencing
- **M0–M6: unchanged.** Everything the coordinator is executing right now is transport-agnostic (the ingest endpoint doesn't know or care whether a chunk arrived via phone or SIM).
- **NEW Phase M7 (mobile gateway)** — after M2.2 lands, parallel to M3–M6: M7.1 BLE receive/pair service (Flutter) · M7.2 relay + offline queue reuse · M7.3 live-burn screen (operator-side curve) · M7.4 sync-session time cross-check. Task-level specs to be added to the agent plan **when the coordinator's current WIP on that file lands** (plan file is mid-edit by another agent at time of writing — deltas parked here to avoid collision).
- **Firmware contract v2:** transport section replaced (BLE gateway primary, cellular optional), envelope gains `seq`/`prev_hash`, RTC mandatory, SD sizing note (~60 KB/burn → years on a microSD). See `docs/edge-firmware-contract.md`.
- Hardware BOM delta: + microSD module, + DS3231 RTC (~₹200 total per unit); − modem/SIM on artisanal units (net cost REDUCTION per kiln).

## 5 · What we deliberately did NOT choose
- **Phone-as-sensor-reader (no edge MCU, thermocouple dongle on the phone):** rejected — ties data capture to phone presence for the whole burn, no local integrity, wrong trust boundary.
- **Cellular-everywhere:** rejected on economics/coverage (see §1); remains available per-site as a module.
- **Encrypting the SD contents:** not required — telemetry is evidence, not a secret; integrity (signatures + chain) is the requirement, and key material never touches the card. Revisit only if PII ever lands on the edge (it must not).

---

# ADDENDUM A — Re-audit (2026-07-27, post-M2.2 landing)
Hostile re-review against the real code (`security.py` canonicalization, landed
M2.1/M2.2). Three amendments. A1 is a genuine design hole; A2/A3 are
code-forced sharpenings. Everything else in ADR-002 survives scrutiny
(BLE throughput: a full 72 h backlog ≈ 2 MB drains in ~3–5 min on BLE 5;
Ed25519 on ESP32-S3 ≈ ms per envelope — neither is a bottleneck).

## A1 · THE HOLE: the edge unit cannot know `batch_uuid` — introduce BURN SESSIONS with late binding
The envelope (and the landed M2.2 ingest) requires `batch_uuid` — but batches
are created in the phone app; a headless logger bolted to a kiln has no way to
know which batch is burning. In the field this becomes wrong-or-missing batch
IDs at burn time = compliance garbage. Fix — **separation of concerns: the edge
logs SESSIONS; binding to a batch happens later, auditable:**
- Envelope: `session_uuid` (generated on-device, part of the signed chain)
  becomes the primary key-in-motion; `batch_uuid` becomes OPTIONAL (a
  cellular/industrial unit that is told its batch may still set it).
- New table `burn_sessions` (session_uuid PK, device_id, started_at, ended_at,
  batch_uuid NULL, binding_source `operator|auto|admin`, bound_by, bound_at) +
  additive columns on `telemetry_chunks`: `session_uuid` NULL; relax
  `batch_uuid` to NULLABLE (expand-safe alter, no drop/rename).
- Binding: at sync, the app/portal proposes matches by **kiln + time-overlap**
  with the batch's own pyrolysis records; operator confirms (or admin binds in
  portal). Binding = one UPDATE on the session's chunks + an AuditEvent. Until
  bound, a session's data is simply invisible to compliance — correct
  semantics, nothing fails (Global Rule 10 intact).
- Read APIs / bridge / charts are UNCHANGED — they already query by batch_uuid
  and simply see the data the moment it is bound.

## A2 · Two-layer auth: the COURIER signs the transport, the EDGE signs the cargo
`verify_signature` binds Ed25519 over [method, path, idempotency-key,
sha256(body), device_id] — and canonical **v2 adds a signed-at replay window**.
A store-and-forward edge unit pre-signing HTTP requests hours earlier would be
rejected as stale the moment v2 is enforced. The clean resolution (and it drops
out of the courier metaphor):
- **Transport layer:** the PHONE signs the ingest HTTP request with ITS OWN
  enrolled device key, fresh at send time — v2 replay window works naturally.
- **Evidence layer:** the edge unit's signature lives IN the envelope
  (+ chain), verified separately against the edge's registered pubkey.
- Ingest delta (M2.2): the authenticated transport device may differ from the
  envelope's producing device; verify BOTH keys; store both identities
  (`courier_device_id`, producer = envelope signer). For cellular-direct units
  producer == courier — the same code path, zero special-casing.
- Security win: a phone can never alter/forge cargo (no edge key); an edge key
  can never be exercised for arbitrary API calls from a phone (transport auth
  is the phone's own, already-scoped identity).

## A3 · Operational sharpenings (contract-level)
1. **Envelope close every 10 min (60 values), not 2 h** — power loss mid-burn
   costs ≤10 min of unsigned buffer instead of 2 h. (≤720-value ceiling stays
   for backfill compaction.)
2. **Chain verification is lazy/eventual:** chunks may arrive out of order via
   multiple couriers; verify per-session continuity as neighbors arrive; a
   persistent break = stored gap annotation, never a rejection of valid chunks.
3. **BLE link needs no secrecy:** cargo is signed and non-secret, so use open
   GATT + app-level device filtering; pairing/bonding adds field-support pain
   and zero security (any phone MAY courier — the server dedups and verifies).
4. Multiple phones draining the same backlog is a FEATURE (any visiting
   operator syncs the site) — idempotency already makes it safe.

## Sequencing note
The M2 agent is mid-flight: M2.1/M2.2 landed with batch_uuid-required
semantics. A1/A2 are **additive follow-ups** (one migration: burn_sessions +
2 columns + nullable relax; one ingest amendment) — schedule as **M2.9
"sessions + courier auth"** immediately after M2.5, before the M2 stitch is
declared done. M7 (phone relay) consumes A1/A2 as its server contract.
