"""M3.1 — pure stage-timeline projection (ORM-free, dict-driven)."""
from datetime import datetime

from stage_projection import STAGE_ORDER, project_stages


def _dt(day: int, hour: int = 10) -> datetime:
    return datetime(2026, 7, day, hour, 0)


def test_rich_batch_projects_ordered_stages():
    events = project_stages(
        batch={"harvest_timestamp": _dt(1), "received_at": _dt(3)},
        media=[
            {"capture_type": "batch_photo", "uploaded_at": _dt(1)},
            {"capture_type": "flame_curtain", "uploaded_at": _dt(2, 9)},
            {"capture_type": "smoke_50", "uploaded_at": _dt(2, 10)},
            {"capture_type": "quenching", "uploaded_at": _dt(2, 11)},
            {"capture_type": "post_burn_mass", "uploaded_at": _dt(2, 12)},
            {"capture_type": "packaging", "uploaded_at": _dt(2, 13)},
            {"capture_type": "lab_certificate", "uploaded_at": _dt(5)},
        ],
        telemetry={"t_start": _dt(2, 8), "t_end": _dt(2, 10)},
        dispatches=[{"created_at": _dt(3), "received_at": _dt(4)}],
        applications=[{"delivery_date": _dt(4, 15)}],
    )
    stages = [e.stage for e in events]
    # every emitted stage is a known one, and output is in canonical order
    assert all(s in STAGE_ORDER for s in stages)
    assert stages == sorted(stages, key=STAGE_ORDER.index)
    assert {"sourcing", "firing", "quenching", "yield", "packaging",
            "dispatch", "application", "lab"} <= set(stages)


def test_firing_window_prefers_telemetry():
    events = project_stages(
        batch={"harvest_timestamp": _dt(1)},
        telemetry={"t_start": _dt(2, 8), "t_end": _dt(2, 11)},
    )
    firing = next(e for e in events if e.stage == "firing")
    assert firing.started_at == _dt(2, 8)
    assert firing.ended_at == _dt(2, 11)
    assert firing.source == "projected"


def test_sparse_batch_only_emits_evidenced_stages():
    # only a harvest timestamp → only sourcing, nothing fabricated
    events = project_stages(batch={"harvest_timestamp": _dt(1)})
    assert [e.stage for e in events] == ["sourcing"]


def test_absence_is_absent_no_phantom_stages():
    events = project_stages(batch={"harvest_timestamp": None})
    assert events == []


def test_smoke_variants_map_to_firing():
    for token in ("smoke_0", "smoke_90", "0", "100"):
        events = project_stages(
            batch={"harvest_timestamp": None},
            media=[{"capture_type": token, "uploaded_at": _dt(2)}],
        )
        assert [e.stage for e in events] == ["firing"]


def test_single_timestamp_has_no_end():
    events = project_stages(
        batch={"harvest_timestamp": None},
        media=[{"capture_type": "packaging", "uploaded_at": _dt(2)}],
    )
    pkg = events[0]
    assert pkg.started_at == _dt(2)
    assert pkg.ended_at is None


def test_accepts_attribute_objects_not_just_dicts():
    class M:
        capture_type = "quenching"
        uploaded_at = _dt(2)

    class B:
        harvest_timestamp = None

    events = project_stages(batch=B(), media=[M()])
    assert [e.stage for e in events] == ["quenching"]
