"""M5.1 core — pure biomass-ledger aggregation (ORM-free)."""
from datetime import datetime

import pytest

from ledger_aggregate import build_biomass_ledger, bucket_key


def _row(day, species, kg, code=None):
    return {"date": datetime(2026, day // 100, day % 100), "species": species, "kg": kg, "batch_code": code}


def test_month_bucketing_and_totals():
    rows = [
        _row(731, "Prosopis", 100, "IN01A001P01S1K01B31072601"),
        _row(715, "Prosopis", 50),
        _row(610, "Lantana", 30),
    ]
    out = build_biomass_ledger(rows, bucket="month")
    periods = [b["period"] for b in out["buckets"]]
    assert periods == ["2026-06", "2026-07"]  # chronological
    jul = next(b for b in out["buckets"] if b["period"] == "2026-07")
    assert jul["total_kg"] == 150.0
    assert jul["by_species"]["Prosopis"] == 150.0
    assert out["totals"]["total_kg"] == 180.0
    assert out["totals"]["row_count"] == 3


def test_day_bucketing():
    rows = [_row(715, "Prosopis", 10), _row(715, "Prosopis", 5), _row(716, "Prosopis", 20)]
    out = build_biomass_ledger(rows, bucket="day")
    assert [b["period"] for b in out["buckets"]] == ["2026-07-15", "2026-07-16"]
    assert out["buckets"][0]["total_kg"] == 15.0


def test_date_range_filter_inclusive():
    rows = [_row(701, "P", 10), _row(715, "P", 10), _row(731, "P", 10)]
    out = build_biomass_ledger(
        rows, date_from=datetime(2026, 7, 10), date_to=datetime(2026, 7, 20)
    )
    assert out["totals"]["total_kg"] == 10.0  # only the 15th survives
    assert out["totals"]["row_count"] == 1


def test_species_ordered_by_kg_desc():
    rows = [_row(715, "Lantana", 10), _row(715, "Prosopis", 90)]
    out = build_biomass_ledger(rows, bucket="month")
    assert list(out["totals"]["by_species"].keys()) == ["Prosopis", "Lantana"]


def test_empty_and_missing_fields_never_fabricated():
    assert build_biomass_ledger([])["totals"]["total_kg"] == 0.0
    # undated row is skipped; null kg counts as 0
    rows = [{"species": "P", "kg": 5}, _row(715, "P", None)]
    out = build_biomass_ledger(rows)
    assert out["totals"]["row_count"] == 1  # only the dated row placed
    assert out["totals"]["total_kg"] == 0.0  # its kg was None → 0


def test_batch_codes_collected_per_bucket():
    rows = [_row(715, "P", 10, "CODE-A"), _row(716, "P", 10, "CODE-B")]
    out = build_biomass_ledger(rows, bucket="month")
    assert out["buckets"][0]["batch_codes"] == ["CODE-A", "CODE-B"]


def test_bad_bucket_raises():
    with pytest.raises(ValueError):
        build_biomass_ledger([], bucket="week")
    with pytest.raises(ValueError):
        bucket_key(datetime(2026, 7, 1), "week")


def test_accepts_attribute_objects():
    class R:
        date = datetime(2026, 7, 15)
        species = "Prosopis"
        kg = 42.0
        batch_code = None

    out = build_biomass_ledger([R()])
    assert out["totals"]["total_kg"] == 42.0
