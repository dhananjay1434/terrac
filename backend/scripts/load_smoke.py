#!/usr/bin/env python3
"""P3.8 — device-fleet load smoke.

Simulates N devices each pushing a full batch (create -> metadata -> moisture x10
-> large telemetry -> yield -> media xM -> application) against a target URL,
with bounded concurrency, and reports p50/p95/p99 latency per endpoint plus the
error / 5xx counts.

Registration is skipped: device Ed25519 keys are pre-minted straight into the DB
(the setup helper needs DATABASE_URL) so the run measures the evidence path, not
enrollment. Requests are signed exactly like the Flutter client (see
CryptoSigner / server.verify_signature).

Pass criteria (exit non-zero otherwise):
  * zero 5xx responses
  * p95 < 2.0 s for JSON endpoints
  * p95 < 10.0 s for media uploads

Usage:
  python scripts/load_smoke.py --url http://localhost:8001 \
      --database-url postgresql+asyncpg://dmrv:dmrv@localhost:5432/dmrv \
      --devices 200 --concurrency 20 --media-count 2

For CI against the compose stack a reduced --devices 20 is used
(see .github/workflows/load-smoke.yml).
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Import the backend package (models) — script lives in backend/scripts/.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


class Device:
    __slots__ = ("device_id", "priv", "pub_b64")

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.priv = Ed25519PrivateKey.generate()
        self.pub_b64 = _b64u(
            self.priv.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        )

    def sign_json(self, method: str, path: str, op_id: str, body: bytes) -> str:
        body_hash = hashlib.sha256(body).hexdigest()
        canonical = f"{method}\n{path}\n{op_id}\n{body_hash}\n{self.device_id}"
        return _b64u(self.priv.sign(canonical.encode("utf-8")))

    def sign_media(self, op_id: str, declared_sha: str, batch_uuid: str) -> str:
        canonical = (
            f"POST\n/api/v1/media\n{op_id}\n{declared_sha.lower()}\n"
            f"{batch_uuid}\n{self.device_id}"
        )
        return _b64u(self.priv.sign(canonical.encode("utf-8")))


async def premint_devices(database_url: str, devices: list[Device]) -> None:
    """Insert DeviceKey rows so requests authenticate without enrollment."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from models import DeviceKey

    engine = create_async_engine(database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        for d in devices:
            s.add(DeviceKey(device_id=d.device_id, public_key=d.pub_b64))
        await s.commit()
    await engine.dispose()


class Stats:
    def __init__(self):
        self.samples: dict[str, list[float]] = defaultdict(list)
        self.errors = 0
        self.fivexx = 0
        self.status_counts: dict[int, int] = defaultdict(int)

    def record(self, label: str, dur: float, status: int) -> None:
        self.samples[label].append(dur)
        self.status_counts[status] += 1
        if status >= 500:
            self.fivexx += 1
        if status >= 400:
            self.errors += 1


def _pct(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = max(0, min(len(sorted_vals) - 1, int(round((p / 100.0) * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


async def _timed(stats: Stats, label: str, coro):
    t0 = time.perf_counter()
    resp = await coro
    dur = time.perf_counter() - t0
    stats.record(label, dur, resp.status_code)
    return resp


async def run_device(
    client: httpx.AsyncClient,
    dev: Device,
    stats: Stats,
    *,
    media_count: int,
    telemetry_size: int,
) -> None:
    bu = str(uuid.uuid4())
    short = bu[:8]

    async def post_json(path: str, op: str, payload: dict, label: str):
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "X-Device-Id": dev.device_id,
            "X-Idempotency-Key": op,
            "X-Signature": dev.sign_json("POST", path, op, body),
            "Content-Type": "application/json",
        }
        return await _timed(
            stats, label, client.post(path, content=body, headers=headers)
        )

    # 1. Create the batch (ownership anchor for all following evidence).
    await post_json(
        "/api/v1/batches",
        f"b-{short}",
        {
            "batch_uuid": bu,
            "feedstock_species": "Lantana_camara",
            "harvest_timestamp": _now_iso(),
            "moisture_percent": 12.0,
            "harvest_uptime_seconds": 100,
            "latitude": 12.9716,
            "longitude": 77.5946,
            "biomass_input_kg": 500.0,
            "biomass_measurement_method": "direct_weigh",
        },
        "POST /batches",
    )

    # 2. Metadata.
    await post_json(
        "/api/v1/metadata",
        f"meta-{short}",
        {"batch_uuid": bu, "artisan_id": "load", "app_build_version": "load-smoke"},
        "POST /metadata",
    )

    # 3. Moisture x10 (C2).
    for i in range(1, 11):
        await post_json(
            "/api/v1/moisture",
            f"m-{short}-{i}",
            {
                "reading_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "moisture_percent": 12.0,
                "sequence": i,
                "sha256_hash": "a" * 64,
            },
            "POST /moisture",
        )

    # 4. Large telemetry (exercises the H3 off-thread parse path).
    await post_json(
        "/api/v1/telemetry",
        f"tel-{short}",
        {
            "telemetry_uuid": str(uuid.uuid4()),
            "batch_uuid": bu,
            "kiln_type": "open",
            "temperature_readings": [650.0] * telemetry_size,
            "flame_height_m": 0.3,
            "smoke_evidence": [
                {"stage": "flame_curtain", "sha256": "a" * 64},
                {"stage": "quenching", "sha256": "a" * 64},
                {"stage": "flame_height", "sha256": "a" * 64},
            ],
        },
        "POST /telemetry",
    )

    # 5. Yield.
    await post_json(
        "/api/v1/yield",
        f"yld-{short}",
        {
            "yield_uuid": str(uuid.uuid4()),
            "batch_uuid": bu,
            "wet_yield_weight_kg": 100.0,
        },
        "POST /yield",
    )

    # 6. Media xN (multipart, Ed25519 media canonical).
    for j in range(media_count):
        op = f"media-{short}-{j}"
        content = f"proof-bytes-{bu}-{j}".encode("utf-8") + os.urandom(256)
        declared = hashlib.sha256(content).hexdigest()
        headers = {
            "X-Device-Id": dev.device_id,
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": declared,
            "X-Batch-UUID": bu,
            "X-Signature": dev.sign_media(op, declared, bu),
        }
        await _timed(
            stats,
            "POST /media",
            client.post(
                "/api/v1/media",
                files={"file": ("proof.jpg", content, "image/jpeg")},
                headers=headers,
            ),
        )

    # 7. Application (with transport GPS + delivery).
    await post_json(
        "/api/v1/application",
        f"app-{short}",
        {
            "application_uuid": str(uuid.uuid4()),
            "batch_uuid": bu,
            "latitude": 13.9716,
            "longitude": 77.5946,
            "delivery_date": _now_iso(),
            "delivered_amount_kg": 50.0,
            "buyer_name": "Load Co-op",
        },
        "POST /application",
    )


def _now_iso() -> str:
    # time.gmtime avoids a tz dependency; server parses ISO-8601 Z.
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


async def main() -> int:
    ap = argparse.ArgumentParser(description="dMRV device-fleet load smoke")
    ap.add_argument("--url", default=os.environ.get("DMRV_LOAD_URL", "http://localhost:8001"))
    ap.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    ap.add_argument("--devices", type=int, default=200)
    ap.add_argument("--concurrency", type=int, default=20)
    ap.add_argument("--media-count", type=int, default=2)
    ap.add_argument("--telemetry-size", type=int, default=50_000)
    ap.add_argument("--json-p95-budget", type=float, default=2.0)
    ap.add_argument("--media-p95-budget", type=float, default=10.0)
    args = ap.parse_args()

    if not args.database_url:
        print("ERROR: --database-url (or DATABASE_URL) is required to pre-mint keys")
        return 2

    run = int(time.time())
    devices = [Device(f"load-{run}-{i}") for i in range(args.devices)]
    print(f"pre-minting {len(devices)} device keys …")
    await premint_devices(args.database_url, devices)

    stats = Stats()
    sem = asyncio.Semaphore(args.concurrency)
    limits = httpx.Limits(max_connections=args.concurrency * 2)
    timeout = httpx.Timeout(30.0)

    async with httpx.AsyncClient(
        base_url=args.url, limits=limits, timeout=timeout
    ) as client:
        async def _one(dev: Device):
            async with sem:
                try:
                    await run_device(
                        client,
                        dev,
                        stats,
                        media_count=args.media_count,
                        telemetry_size=args.telemetry_size,
                    )
                except Exception as exc:  # noqa: BLE001 — count, don't abort the fleet
                    stats.errors += 1
                    print(f"  device {dev.device_id} error: {exc!r}")

        t0 = time.perf_counter()
        await asyncio.gather(*[_one(d) for d in devices])
        wall = time.perf_counter() - t0

    return _report(stats, wall, args)


def _report(stats: Stats, wall: float, args) -> int:
    print("\n=== load smoke report ===")
    print(f"devices={args.devices} concurrency={args.concurrency} wall={wall:.1f}s")
    print(f"status counts: {dict(sorted(stats.status_counts.items()))}")
    print(f"{'endpoint':<20}{'n':>7}{'p50':>9}{'p95':>9}{'p99':>9}")
    worst_json_p95 = 0.0
    worst_media_p95 = 0.0
    for label in sorted(stats.samples):
        vals = sorted(stats.samples[label])
        p50, p95, p99 = _pct(vals, 50), _pct(vals, 95), _pct(vals, 99)
        print(f"{label:<20}{len(vals):>7}{p50:>9.3f}{p95:>9.3f}{p99:>9.3f}")
        if "media" in label.lower():
            worst_media_p95 = max(worst_media_p95, p95)
        else:
            worst_json_p95 = max(worst_json_p95, p95)

    print(f"\nerrors(4xx+ / exceptions)={stats.errors}  5xx={stats.fivexx}")

    ok = True
    if stats.fivexx > 0:
        print(f"FAIL: {stats.fivexx} 5xx responses (must be zero)")
        ok = False
    if worst_json_p95 > args.json_p95_budget:
        print(f"FAIL: JSON p95 {worst_json_p95:.3f}s > {args.json_p95_budget}s")
        ok = False
    if worst_media_p95 > args.media_p95_budget:
        print(f"FAIL: media p95 {worst_media_p95:.3f}s > {args.media_p95_budget}s")
        ok = False
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
