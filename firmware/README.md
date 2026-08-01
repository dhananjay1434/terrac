# dMRV Edge Firmware

Ports & adapters. **Change hardware = change an adapter; never touch `domain/`.**

- `src/domain/`  — pure logic, ZERO hardware deps, host-tested. Build: `make test`.
  - `canonical.*` — byte-exact signing form (proven vs backend/tools/golden_vectors.json)
  - `aggregate.*` — 10s bucket, 1-decimal (the FLOAT PRECISION INVARIANT that keeps canonical exact)
  - `frame.*`     — BLE wire frame codec (mirror of the app's lib/services/ble_frame.dart)
- `src/ports/`   — interfaces the domain depends on (crypto, storage, rtc, ble).
- `src/adapters/`— hardware impls of the ports (ESP-IDF/mbedTLS/FATFS/NVS). STUBS today.

## Still human/hardware work (🔵)
Fill the adapter stubs; wire the GATT server; implement the SD log + eviction (E6/D3a 90-day floor);
the boot-time chain resume (E3) using `storage_max_seq`; the A4 crypto decision. The domain contract
they must satisfy is already defined and tested — implement to the headers, run `make test` stays
green (it tests domain, which you did not touch), then bench-test on real hardware (Phase E gate).
