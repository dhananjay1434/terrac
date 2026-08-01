# BLE Store-and-Forward Sync Protocol (STITCHING Phase D)

The single wire contract both the ESP32 firmware (Phase E) and the phone app (Phase F) implement.
Neither side may deviate; a change here is a change to both, in the same PR, with the vectors below
regenerated.

## Transport
- One GATT service, two characteristics: `TX` (device -> phone, notify) and `RX` (phone -> device,
  write). Nordic-UART-style byte stream. No other characteristics carry protocol data.
- No pairing/bonding (ADR-002 A3.3 / Addendum B). Filter by advertised device_id. The Ed25519
  signature is the security boundary.

## Framing
Every logical message is length-prefixed and split to fit the negotiated MTU:
`{ msg_type: u8, chunk_id: u32, packet_index: u16, total_packets: u16, payload: bytes }`.
The receiver reassembles by `chunk_id` and verifies the reassembled length before acting.

## Message types
| msg_type | name | direction | payload |
|---|---|---|---|
| 1 | ChunkRequest | phone -> device | `{channel, from_seq?}` (omit from_seq = oldest unsynced) |
| 2 | ChunkData | device -> phone | one signed envelope (the exact JSON the backend ingests) |
| 3 | SyncAck | phone -> device | `{channel, synced_through_seq}` — server-CONFIRMED, not BLE-received |
| 4 | SyncNack | phone -> device | `{channel, seq, reason}` — permanently rejected (e.g. 422), stop offering |
| 5 | TimeSync | phone -> device | `{utc_ms}` — first action every connection |
| 6 | Health | device -> phone | `{unsynced_bytes, flash_full, fw_version}` |

## Advertising
- Advertise the sync service when there is unsynced data (include device_id + unsynced-byte-count).
- ALSO advertise on a slow interval (~every few minutes) when idle, so a phone can TimeSync and read
  Health on a drifting-but-quiet unit (STITCHING D2a). A 16-byte device_id may exceed the 31-byte
  legacy advert budget — use BLE 5 extended advertising or a scan response.

## Eviction safety (the point of the ack cycle)
1. Phone sends ChunkRequest. 2. Device streams ChunkData oldest-first. 3. Phone relays each envelope
to `/api/v2/telemetry/ingest` via its OFFLINE OUTBOX (not live pass-through). 4. Only after the
SERVER confirms (200 ok/duplicate) does the phone send SyncAck. 5. Device marks flash reclaimable
ONLY on SyncAck — never on BLE transfer completing.
- **Retention floor:** never evict anything younger than 90 days regardless of any ack (guards
  against a spoofed unauthenticated SyncAck — STITCHING D3a). Evictable = synced-AND-older-than-90d.
- **Any courier** can carry the watermark from `GET /api/v2/telemetry/sync-status/{device_id}`, not
  only the phone that delivered the data (STITCHING D3b).

## Signed envelope (what ChunkData carries)
The envelope and its canonical signing bytes are defined by `backend/tools/golden_vectors.json` —
that file is the authority. Firmware and app MUST reproduce `canonical_hex` for every vector byte
for byte. See STITCHING Phase G.

## FLOAT PRECISION INVARIANT (contract-level, load-bearing)
Every float a producer emits (`values[]`, `sample_period_s`) MUST carry exactly 1 decimal place. The
edge firmware guarantees this by rounding each 10 s bucket to 1 dp (`aggregate.c`); that is what lets
Python `json.dumps`, C `%.1f`, and Dart `toStringAsFixed(1)` produce identical bytes. A producer that
emits more precision (e.g. `412.25`) would sign bytes the 1-dp implementations cannot reproduce —
never do so without changing all three canonicalizers together in the same PR and regenerating the
golden vectors.
