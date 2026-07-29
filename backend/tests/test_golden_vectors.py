"""V1 - golden vectors byte-pin the canonical signed form (the drift guard)."""
import json
from pathlib import Path

from routers.telemetry import TelemetryChunkIn

_VEC = Path(__file__).resolve().parent.parent / "tools" / "golden_vectors.json"


def test_vectors_file_exists():
    assert _VEC.exists(), "run: cd backend && python tools/gen_golden_vectors.py"


def test_canonical_bytes_match_committed_vectors():
    vectors = json.loads(_VEC.read_text(encoding="utf-8"))
    assert vectors, "no vectors present"
    for v in vectors:
        model = TelemetryChunkIn(producer_signature="x", **v["envelope"])
        assert model.canonical_bytes().hex() == v["canonical_hex"], (
            "canonical signed form drifted from the committed golden vector. If this "
            "change is intentional: regenerate the vectors AND notify firmware/app."
        )
