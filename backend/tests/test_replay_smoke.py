"""M0.3 — replay harness smoke. Marked `slow` (runs the full seed pipeline in a
subprocess), so the fast gate can exclude it with `-m "not slow"`."""
import pytest


@pytest.mark.slow
def test_replay_smoke():
    from tools.replay_seed import main

    assert main() > 0
