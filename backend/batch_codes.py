"""Human-readable provenance batch codes (display identity — UUID stays king).

Format:  {CC}{org:02d}{network}P{site:02d}S{slot}K{kiln:02d}B{DDMMYY}{seq:02d}
Example: IN01A001P03S2K07B23072601
Deterministic; collision-safe via the per-day sequence. NEVER used as a key,
NEVER parsed to recover facts — the DB columns are the truth, the code is a
human handle.
"""
import re
from datetime import datetime, timedelta, timezone

_NETWORK_RE = re.compile(r"^[A-Z]\d{3}$")


def make_batch_code(
    *,
    country: str,
    org_num: int,
    network_code: str,
    site_num: int,
    slot_num: int,
    kiln_num: int,
    day: datetime,
    seq: int,
) -> str:
    if not (len(country) == 2 and country.isalpha()):
        raise ValueError("country must be 2 letters")
    if not _NETWORK_RE.match(network_code):
        raise ValueError("network_code must match ^[A-Z]\\d{3}$, e.g. A001")
    if not (0 <= org_num <= 99):
        raise ValueError("org_num out of range 0..99")
    if not (0 <= site_num <= 99):
        raise ValueError("site_num out of range 0..99")
    if not (0 <= slot_num <= 9):
        raise ValueError("slot_num out of range 0..9")
    if not (0 <= kiln_num <= 99):
        raise ValueError("kiln_num out of range 0..99")
    if not (1 <= seq <= 99):
        raise ValueError("seq out of range 1..99")
    return (
        f"{country.upper()}{org_num:02d}{network_code}"
        f"P{site_num:02d}S{slot_num}K{kiln_num:02d}"
        f"B{day:%d%m%y}{seq:02d}"
    )


_IST = timezone(timedelta(hours=5, minutes=30))


def slot_for(received_at_ist: datetime) -> int:
    """Derived slot bucket from the IST hour (audit A3: Batch has no slot column,
    so slot is a display CONVENIENCE, never a recorded fact). tz-aware inputs are
    converted to IST first; naive inputs are assumed already IST.

    hour < 12 → 1 (morning) · < 17 → 2 (afternoon) · else 3 (evening).
    """
    dt = received_at_ist.astimezone(_IST) if received_at_ist.tzinfo else received_at_ist
    hour = dt.hour
    if hour < 12:
        return 1
    if hour < 17:
        return 2
    return 3
