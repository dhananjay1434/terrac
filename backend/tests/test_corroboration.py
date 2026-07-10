"""Unit tests for the pure corroboration derivers (Phase 7-R).

These need no DB and no FastAPI — they pin the exact rules by which server-side
evidence becomes a credit input, and when a batch is PROVISIONAL.
"""

import math

from corroboration import (
    MIN_TEMPERATURE_SAMPLES,
    assemble,
    derive_min_temp,
    derive_transport_km,
    derive_wet_yield,
)


# ---- derive_min_temp -------------------------------------------------------


def test_min_temp_none_when_no_telemetry():
    assert derive_min_temp(None) == (None, "no_telemetry")


def test_min_temp_requires_enough_samples():
    payload = {"temperature_readings": [650.0] * (MIN_TEMPERATURE_SAMPLES - 1)}
    assert derive_min_temp(payload) == (None, "insufficient_temperature_samples")


def test_min_temp_reads_snake_case_and_returns_min():
    payload = {"temperature_readings": [650.0] * 59 + [210.0]}
    val, reason = derive_min_temp(payload)
    assert reason is None
    assert val == 210.0


def test_min_temp_ignores_camelcase_legacy_key():
    # The old camelCase key must NOT be honored — that was the production bug.
    payload = {"temperatureReadingsJson": [650.0] * 60}
    assert derive_min_temp(payload) == (None, "insufficient_temperature_samples")


# ---- derive_wet_yield ------------------------------------------------------


def test_wet_yield_none_when_no_record():
    assert derive_wet_yield(None) == (None, "no_yield_record")


def test_wet_yield_reads_wet_yield_weight_kg():
    assert derive_wet_yield({"wet_yield_weight_kg": 42.5}) == (42.5, None)


def test_wet_yield_rejects_nonpositive():
    assert derive_wet_yield({"wet_yield_weight_kg": 0}) == (None, "invalid_wet_yield")
    assert derive_wet_yield({"wet_yield_weight_kg": "x"}) == (
        None,
        "invalid_wet_yield",
    )


# ---- derive_transport_km ---------------------------------------------------


def _haversine(lon1, lat1, lon2, lat2):
    # minimal reference haversine so the test is independent of server.py
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def test_transport_none_without_application():
    assert derive_transport_km(1.0, 1.0, None, haversine=_haversine) == (
        None,
        "no_application_record",
    )


def test_transport_none_without_batch_gps():
    assert derive_transport_km(
        None, None, {"latitude": 1.0, "longitude": 1.0}, haversine=_haversine
    ) == (None, "no_application_record")


def test_transport_missing_application_gps():
    assert derive_transport_km(1.0, 1.0, {"foo": "bar"}, haversine=_haversine) == (
        None,
        "application_missing_gps",
    )


def test_transport_computes_positive_distance():
    val, reason = derive_transport_km(
        0.0, 0.0, {"latitude": 1.0, "longitude": 0.0}, haversine=_haversine
    )
    assert reason is None
    assert val > 100.0  # ~111 km per degree of latitude


# ---- assemble --------------------------------------------------------------


def test_fully_corroborated_is_not_provisional():
    c = assemble(50.0, 300.0, 12.0, has_lab_hcorg=True)
    assert c.provisional is False
    assert c.reasons == []


def test_each_missing_input_flips_provisional_with_reason():
    c = assemble(None, 300.0, 12.0, has_lab_hcorg=True)
    assert c.provisional is True and c.reasons == ["wet_yield_uncorroborated"]

    c = assemble(50.0, None, 12.0, has_lab_hcorg=True)
    assert c.reasons == ["min_temp_uncorroborated"]

    c = assemble(50.0, 300.0, None, has_lab_hcorg=True)
    assert c.reasons == ["transport_uncorroborated"]


def test_assumed_hcorg_is_provisional_even_when_inputs_present():
    c = assemble(50.0, 300.0, 12.0, has_lab_hcorg=False)
    assert c.provisional is True
    assert c.reasons == ["assumed_h_corg"]


# ---- Rainbow C2: moisture compliance ---------------------------------------

from corroboration import derive_moisture_compliance  # noqa: E402


def test_moisture_floor_is_ten_readings():
    assert derive_moisture_compliance(9, None) == (
        False,
        "insufficient_moisture_samples",
    )
    assert derive_moisture_compliance(10, None) == (True, None)


def test_moisture_one_per_100kg_rule():
    # 1500 kg biomass → ceil(1500/100)=15 required.
    assert derive_moisture_compliance(14, 1500.0)[0] is False
    assert derive_moisture_compliance(15, 1500.0)[0] is True
    # Small run still needs the floor of 10.
    assert derive_moisture_compliance(10, 200.0)[0] is True


def test_moisture_reason_flips_provisional():
    ok = assemble(50.0, 300.0, 12.0, has_lab_hcorg=True, moisture_ok=True)
    assert "insufficient_moisture_samples" not in ok.reasons
    bad = assemble(50.0, 300.0, 12.0, has_lab_hcorg=True, moisture_ok=False)
    assert bad.provisional is True
    assert bad.reasons == ["insufficient_moisture_samples"]


# ---- Rainbow C3 / C3b: kiln-type-conditional pyrolysis compliance -----------

from corroboration import (  # noqa: E402
    derive_pyrolysis_photo_compliance,
    derive_ignition_compliance,
)

_ALL_STAGES = [
    {"stage": "flame_curtain", "sha256": "a"},
    {"stage": "quenching", "sha256": "b"},
    {"stage": "flame_height", "sha256": "c"},
]


def test_pyrolysis_checks_inert_for_non_open_kiln():
    # None or closed kiln → both checks pass regardless of evidence.
    assert derive_pyrolysis_photo_compliance(None, None, None) == (True, True)
    assert derive_pyrolysis_photo_compliance("closed", None, None) == (True, True)


def test_open_kiln_requires_all_three_photos_and_low_flame():
    photos_ok, flame_ok = derive_pyrolysis_photo_compliance("open", _ALL_STAGES, 0.4)
    assert photos_ok and flame_ok
    # Missing quenching photo.
    two = [e for e in _ALL_STAGES if e["stage"] != "quenching"]
    assert derive_pyrolysis_photo_compliance("open", two, 0.4)[0] is False
    # Flame height too high.
    assert derive_pyrolysis_photo_compliance("open", _ALL_STAGES, 0.6)[1] is False
    # Flame height missing.
    assert derive_pyrolysis_photo_compliance("open", _ALL_STAGES, None)[1] is False


def test_open_kiln_passes_with_the_apps_full_seven_stage_list():
    # P1-S4: the client emits the 4 smoke-opacity proofs alongside the 3
    # required flame stages. The extra smoke_* stages must not break the subset
    # check — photos_ok stays True.
    app_stages = [
        {"stage": "0", "sha256": "s0"},
        {"stage": "50", "sha256": "s1"},
        {"stage": "90", "sha256": "s2"},
        {"stage": "100", "sha256": "s3"},
        {"stage": "flame_curtain", "sha256": "a"},
        {"stage": "quenching", "sha256": "b"},
        {"stage": "flame_height", "sha256": "c"},
    ]
    photos_ok, flame_ok = derive_pyrolysis_photo_compliance("open", app_stages, 0.3)
    assert photos_ok and flame_ok


def test_ignition_required_only_for_closed_kiln():
    assert derive_ignition_compliance("closed", None) is False
    assert derive_ignition_compliance("closed", "syngas") is True
    assert derive_ignition_compliance("open", None) is True
    assert derive_ignition_compliance(None, None) is True


def test_pyrolysis_reasons_flip_provisional():
    c = assemble(
        50.0,
        300.0,
        12.0,
        has_lab_hcorg=True,
        pyrolysis_photos_ok=False,
        flame_height_ok=False,
        ignition_ok=False,
    )
    assert c.provisional is True
    assert "missing_pyrolysis_photos" in c.reasons
    assert "flame_height_out_of_range" in c.reasons
    assert "missing_ignition_energy" in c.reasons


def test_attestation_ok_defaults_true_and_is_inert():
    # Phase 9-R: default (no enforcement) adds no attestation reason.
    c = assemble(50.0, 300.0, 12.0, has_lab_hcorg=True)
    assert "attestation_unverified" not in c.reasons
    assert c.provisional is False


def test_unverified_attestation_flips_provisional_when_enforced():
    # When the caller passes attestation_ok=False (Option A enforcement), an
    # otherwise fully-corroborated batch is held PROVISIONAL.
    c = assemble(50.0, 300.0, 12.0, has_lab_hcorg=True, attestation_ok=False)
    assert c.provisional is True
    assert c.reasons == ["attestation_unverified"]
