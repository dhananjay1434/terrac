"""V2 - chain-gap detection (deletion/reorder is evident; legacy chunks ignored)."""
from telemetry_integrity import detect_chain_gaps


def test_contiguous_no_gap():
    chunks = [{"session_uuid": "s", "channel": "T1", "seq": i} for i in range(4)]
    assert detect_chain_gaps(chunks) == []


def test_deleted_middle_chunk_is_a_gap():
    chunks = [{"session_uuid": "s", "channel": "T1", "seq": q} for q in (0, 1, 3)]
    assert detect_chain_gaps(chunks) == [
        {"session_uuid": "s", "channel": "T1", "after_seq": 1, "before_seq": 3}
    ]


def test_seqless_chunks_ignored():
    chunks = [{"session_uuid": "s", "channel": "T1", "seq": None} for _ in range(3)]
    assert detect_chain_gaps(chunks) == []


def test_channels_independent():
    chunks = [
        {"session_uuid": "s", "channel": "T1", "seq": 0},
        {"session_uuid": "s", "channel": "T1", "seq": 1},
        {"session_uuid": "s", "channel": "LOAD", "seq": 0},
        {"session_uuid": "s", "channel": "LOAD", "seq": 2},
    ]
    assert detect_chain_gaps(chunks) == [
        {"session_uuid": "s", "channel": "LOAD", "after_seq": 0, "before_seq": 2}
    ]
