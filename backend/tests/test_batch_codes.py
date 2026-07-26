"""M1.2 — batch-code generator + slot derivation (pure functions, zero I/O)."""
from datetime import datetime, timezone

import pytest

from batch_codes import make_batch_code, slot_for


def test_golden_code():
    assert (
        make_batch_code(
            country="IN",
            org_num=1,
            network_code="A001",
            site_num=3,
            slot_num=2,
            kiln_num=7,
            day=datetime(2026, 7, 23),
            seq=1,
        )
        == "IN01A001P03S2K07B23072601"
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(country="IND", org_num=1, network_code="A001", site_num=3,
             slot_num=2, kiln_num=7, day=datetime(2026, 7, 23), seq=1),  # bad country
        dict(country="IN", org_num=1, network_code="AA01", site_num=3,
             slot_num=2, kiln_num=7, day=datetime(2026, 7, 23), seq=1),  # bad network
        dict(country="IN", org_num=100, network_code="A001", site_num=3,
             slot_num=2, kiln_num=7, day=datetime(2026, 7, 23), seq=1),  # org range
        dict(country="IN", org_num=1, network_code="A001", site_num=3,
             slot_num=2, kiln_num=7, day=datetime(2026, 7, 23), seq=0),  # seq range
    ],
)
def test_validation_raises(kwargs):
    with pytest.raises(ValueError):
        make_batch_code(**kwargs)


def test_slot_buckets():
    assert slot_for(datetime(2026, 7, 23, 9, 0)) == 1   # morning
    assert slot_for(datetime(2026, 7, 23, 14, 0)) == 2  # afternoon
    assert slot_for(datetime(2026, 7, 23, 20, 0)) == 3  # evening


def test_slot_ist_boundary():
    # 06:45 UTC == 12:15 IST → afternoon (crossed the noon boundary via +05:30)
    assert slot_for(datetime(2026, 7, 23, 6, 45, tzinfo=timezone.utc)) == 2
    # 06:15 UTC == 11:45 IST → still morning
    assert slot_for(datetime(2026, 7, 23, 6, 15, tzinfo=timezone.utc)) == 1
