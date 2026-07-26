# Edge Firmware ↔ dMRV Ingest Contract (M2h)

The single interface the kiln edge unit and the backend both build against.
Written contract-first so firmware and `routers/telemetry.py` (M2.2) can be
developed in parallel and meet without rework.

**Status:** DRAFT — the endpoint (M2.2) is not yet merged. This doc is the spec;
when M2.2 lands it MUST match this or update it in the same PR.

---

## 1 · Device identity & provisioning
- Each edge unit is a **device** in the existing enrollment system — it is NOT a
  new concept. Provision exactly like a phone: an operator redeems an
  `EnrollmentToken` (`POST /api/v1/register` with `{device_id, public_key}` +
  header `X-Enrollment-Token`), the unit stores its keypair.
- The unit signs every request the same way the mobile app does
  (`verify_signature` in `backend/security.py` is the authority — read it; the
  canonicalization below MUST match it exactly). One kiln = one device_id; if a
  kiln has separate thermal and load MCUs, they may share one device_id or use
  two — both are fine (channels are independent).

## 2 · Sampling → aggregation (on-device)
- Sample each channel at **1 Hz**.
- Aggregate into **10-second buckets**: emit the bucket's **mean** for `T*`
  channels and the bucket's **last** value for `LOAD` (weight is a level, not a
  rate). `sample_period_s = 10`.
- Buffer aggregated buckets in a **flash ring buffer sized for ≥72 h** so a
  connectivity outage never loses data — on reconnect, backfill oldest-first.
  Old timestamps are ACCEPTED by the server (audit A5); only a `t_start` more
  than 300 s in the FUTURE is rejected, so keep the RTC sane (GPS time when
  available).

## 3 · Channels
| channel | source | unit | bucket agg |
|---|---|---|---|
| `T1` | thermocouple, cone wall ⅓ height | °C | mean |
| `T2` | thermocouple, cone wall ⅔ height | °C | mean |
| `T3` | thermocouple, cone wall ½ height, opposite T1 | °C | mean |
| `T4` | thermocouple, **base plate center** | °C | mean |
| `LOAD` | summed load cells under the stand feet | kg | last |
- A unit sends only the channels it physically has (Global Rule 10 — tiers are
  derived from what streams). A load-only kiln sends only `LOAD`; a thermal-only
  kiln sends only `T*`. No channel is mandatory.
- **Compliance note:** the credit gate reads interior probes `T1–T3` only; `T4`
  (base) is stored and charted as context (pending methodology sign-off — see
  `DMRV_EVOLUTION_AGENT_PLAN.md` M2.5). Firmware still SENDS T4; the backend
  decides how to use it.

## 4 · Chunk format (the request body — exactly what gets signed)
`POST /api/v2/telemetry/ingest`, one chunk per (channel, time-window),
**≤720 values per chunk** (= 2 h at 10 s). Body:
```json
{
  "batch_uuid": "0a73dcc2-9823-4054-abeb-b252f2406070",
  "channel": "T1",
  "t_start": "2026-07-22T13:02:00Z",
  "sample_period_s": 10.0,
  "values": [412.5, 418.0, 421.2, "... up to 720 floats ..."]
}
```
- `values[i]` is the reading at `t_start + i * sample_period_s`.
- Timestamps are UTC ISO-8601 with `Z`. The device clock is UTC; display-side
  IST conversion is the backend/portal's job, never the firmware's.
- All values finite (no `NaN`/`Inf`). A dropped sample = a **gap**: split into
  two chunks around the hole rather than sending a placeholder — the backend
  renders gaps as breaks and never interpolates (audit A4). Never zero-fill.

## 5 · Signing (canonicalization — must match `security.verify_signature`)
- Read `backend/security.py` for the exact scheme (Ed25519 over a canonical
  byte string per the existing device write path). Firmware reuses that same
  routine — do NOT invent a telemetry-specific signature.
- Headers on every ingest call mirror the app's signed writes (device id +
  signature headers exactly as `routers/evidence.py` receives them).

## 6 · Responses & retry
| response | meaning | firmware action |
|---|---|---|
| `200 {"status":"ok","points":N}` | accepted, N points stored | drop chunk from ring buffer |
| `200 {"status":"duplicate"}` | already ingested (idempotent, audit A2) | drop chunk (success — a prior retry landed) |
| `401` / `403` | signature/enrollment problem | stop, re-provision; do NOT drop data |
| `422` | malformed (bad channel, >720 values, future t_start, non-finite) | log locally, drop chunk (it will never succeed), raise a health flag |
| `5xx` / timeout | transient | keep in ring buffer, exponential backoff, retry |
- Idempotency is total: re-sending an identical chunk is always safe (server
  dedups on `(batch_uuid, channel, t_start, signature)` and on point PK). Prefer
  over-sending to losing data.

## 7 · Live view interaction (informational — firmware does nothing extra)
When a verifier opens the live burn view, the portal mints a stream ticket and
subscribes; each accepted chunk the backend receives is fanned out to that
viewer in real time (`telemetry_bus.publish`). The firmware just keeps POSTing —
"live" is a backend/portal concern, no special mode on the device.

## 8 · Open hardware questions for the build team (not firmware-blocking)
1. Load-cell heat isolation: cells under the stand feet on ceramic standoffs +
   a radiant shield — validate drift at sustained 450 °C+ on the bench first.
2. Thermocouple type/amplifier: K-type + MAX31855 assumed; confirm range covers
   observed peaks (Circonomy showed 908 °C — ensure headroom).
3. Power: burn-duration + backfill window on battery/solar for off-grid kilns.
