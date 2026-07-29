"""R5 - generate golden signing vectors that BYTE-PIN the canonical form the
backend verifies (TelemetryChunkIn.canonical_bytes). Firmware and the app sign
THESE bytes. If the backend's canonical output ever changes, the committed
vectors stop matching and CI fails (the drift guard). Regenerate with:
    cd backend && python tools/gen_golden_vectors.py
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# db.py refuses to start without DATABASE_URL. This script only needs the pydantic
# model, never a connection, so point it at a scratch in-memory SQLite (same guard
# tests/conftest.py uses) and never at the real .env.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from routers.telemetry import TelemetryChunkIn

_ENVELOPES = [
    dict(device_id="edge-001", session_uuid="sess-0001", batch_uuid=None,
         channel="T1", t_start="2026-07-23T09:00:00Z", sample_period_s=10.0,
         values=[412.5, 418.0, 421.2], seq=0, prev_hash="GENESIS"),
    dict(device_id="edge-001", session_uuid="sess-0001", batch_uuid=None,
         channel="LOAD", t_start="2026-07-23T09:00:00Z", sample_period_s=10.0,
         values=[120.0, 121.6], seq=1, prev_hash="a" * 64),
]


def build() -> list[dict]:
    out = []
    for env in _ENVELOPES:
        model = TelemetryChunkIn(producer_signature="x", **env)
        out.append({"envelope": env, "canonical_hex": model.canonical_bytes().hex()})
    return out


if __name__ == "__main__":
    dest = Path(__file__).resolve().parent / "golden_vectors.json"
    dest.write_text(json.dumps(build(), indent=2), encoding="utf-8")
    print("wrote", dest, "with", len(build()), "vectors")
