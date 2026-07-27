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
