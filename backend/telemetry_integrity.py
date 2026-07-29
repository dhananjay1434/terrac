"""R5 - read-time chain-gap detection (ADR-002 A3.2). Each chunk is already
individually signed at ingest, so this only needs to catch DELETION / REORDER,
which a monotonic per-(session, channel) seq makes evident. A gap is annotated,
never a rejection.
"""
from collections import defaultdict
from typing import Any, Iterable


def _get(o: Any, k: str) -> Any:
    return o.get(k) if isinstance(o, dict) else getattr(o, k, None)


def detect_chain_gaps(chunks: Iterable[Any]) -> list[dict]:
    """chunks: objects/dicts exposing session_uuid, channel, seq. Returns a list of
    {session_uuid, channel, after_seq, before_seq} wherever the monotonic seq per
    (session, channel) skips a value. Chunks with seq=None (legacy/cellular, no
    chain) are ignored. Never raises."""
    by_key: dict[tuple, list[int]] = defaultdict(list)
    for c in chunks:
        seq = _get(c, "seq")
        if seq is None:
            continue
        by_key[(_get(c, "session_uuid"), _get(c, "channel"))].append(int(seq))
    gaps: list[dict] = []
    for (sess, chan), seqs in by_key.items():
        ordered = sorted(set(seqs))
        for a, b in zip(ordered, ordered[1:]):
            if b != a + 1:
                gaps.append(
                    {"session_uuid": sess, "channel": chan, "after_seq": a, "before_seq": b}
                )
    return gaps
