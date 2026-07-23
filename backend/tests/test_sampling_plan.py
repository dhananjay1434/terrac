"""PR-3.1 — pure sampling-plan (representative-sampling cadence) deriver.

samples_required_per_rule is a cadence RATE (kg of batch mass per required
in-scope lab result), sourced from the methodology config
(RegistryConfig.params_json -> LcaParams.sampling_kg_per_lab_result) — never
invented here. None/unset means the cadence isn't configured for this
project, so the gate stays inert (grandfathered): every existing batch and
every project that hasn't opted in gets exactly today's behavior.
"""

from corroboration import derive_sampling_compliance


def test_inert_when_cadence_not_configured():
    assert derive_sampling_compliance(10_000.0, 0, None) == (True, None)


def test_inert_when_not_enforced():
    assert derive_sampling_compliance(10_000.0, 0, 1_000.0, enforced=False) == (
        True,
        None,
    )


def test_sufficient_single_sample_covers_small_batch():
    # 1 lab result required per 5,000 kg; a 3,000 kg batch needs only 1.
    assert derive_sampling_compliance(3_000.0, 1, 5_000.0) == (True, None)


def test_insufficient_lab_sampling_for_large_batch():
    # 12,000 kg / 5,000 kg-per-sample -> 3 required; only 1 on file.
    ok, reason = derive_sampling_compliance(12_000.0, 1, 5_000.0)
    assert ok is False
    assert reason == "insufficient_lab_sampling"


def test_exact_boundary_is_sufficient():
    # Exactly 10,000 kg at a 5,000 kg cadence requires exactly 2 samples.
    assert derive_sampling_compliance(10_000.0, 2, 5_000.0) == (True, None)


def test_just_over_boundary_requires_one_more_sample():
    # 10,000.1 kg rounds the requirement up to 3 samples.
    ok, reason = derive_sampling_compliance(10_000.1, 2, 5_000.0)
    assert ok is False
    assert reason == "insufficient_lab_sampling"


def test_inert_when_batch_mass_missing():
    assert derive_sampling_compliance(None, 0, 5_000.0) == (True, None)


def test_inert_when_batch_mass_zero_or_negative():
    assert derive_sampling_compliance(0.0, 0, 5_000.0) == (True, None)
    assert derive_sampling_compliance(-5.0, 0, 5_000.0) == (True, None)


def test_inert_when_cadence_rate_zero_or_negative():
    assert derive_sampling_compliance(10_000.0, 0, 0.0) == (True, None)
    assert derive_sampling_compliance(10_000.0, 0, -5.0) == (True, None)
