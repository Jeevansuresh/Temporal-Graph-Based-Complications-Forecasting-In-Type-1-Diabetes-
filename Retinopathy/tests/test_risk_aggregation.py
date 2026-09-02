from app.reasoning.risk_aggregation import (
    HIGH_CONCERN,
    INCREASING_CONCERN,
    INSUFFICIENT_DATA,
    STABLE,
    WATCH,
    aggregate_risk_state,
)
from app.reasoning.rule_engine import evaluate_all_rules
from tests.profile_builder import build_test_profile

DATES = ["2024-01-10", "2025-01-10", "2026-01-10"]


def _assess(**kwargs):
    profile = build_test_profile(dates=DATES, **kwargs)
    evaluations = evaluate_all_rules(profile)
    return aggregate_risk_state(profile, evaluations)


def test_stable_retinal_trajectory_no_systemic_signals_is_stable():
    assessment = _assess(retinal_stages=[0, 0, 0], hba1c=[7.0, 7.1, 7.0], ldl=[90, 92, 91])
    assert assessment.risk_state == STABLE
    assert assessment.precedence_step == 6


def test_no_retinal_progression_with_two_systemic_signals_is_watch():
    assessment = _assess(
        retinal_stages=[0, 0, 0],
        hba1c=[7.0, 7.8, 8.4],
        sbp=[110, 120, 128],
        dbp=[70, 76, 82],
        age=13,
    )
    assert assessment.risk_state == WATCH
    assert assessment.deciding_rule_ids == ["R012"]


def test_existing_dr_stable_with_two_systemic_signals_is_increasing_concern():
    assessment = _assess(
        retinal_stages=[1, 1, 1],
        hba1c=[7.0, 7.8, 8.4],
        ldl=[90, 105, 121],
    )
    assert assessment.risk_state == INCREASING_CONCERN
    assert assessment.deciding_rule_ids == ["R010"]


def test_incident_progression_is_high_concern():
    assessment = _assess(retinal_stages=[0, 0, 1])
    assert assessment.risk_state == HIGH_CONCERN
    assert "R011" in assessment.deciding_rule_ids
    assert "R003" in assessment.deciding_rule_ids


def test_direct_progression_takes_precedence_over_systemic_signals():
    # Progression AND >=2 systemic signals present: HIGH_CONCERN must win,
    # not INCREASING_CONCERN/WATCH.
    assessment = _assess(
        retinal_stages=[1, 1, 2],
        hba1c=[7.0, 7.8, 8.4],
        ldl=[90, 105, 121],
    )
    assert assessment.risk_state == HIGH_CONCERN


def test_missing_latest_retinal_observation_is_insufficient_data():
    assessment = _assess(retinal_stages=[0, None, None])
    assert assessment.risk_state == INSUFFICIENT_DATA
    assert assessment.deciding_rule_ids == ["R013"]


def test_zero_retinal_observations_is_insufficient_data():
    assessment = _assess(retinal_stages=[None, None, None])
    assert assessment.risk_state == INSUFFICIENT_DATA
    assert assessment.deciding_rule_ids == ["R013"]


def test_single_observation_no_comparison_is_insufficient_data_not_attributed_to_a_rule():
    profile = build_test_profile(dates=["2024-01-10"], retinal_stages=[0])
    evaluations = evaluate_all_rules(profile)
    assessment = aggregate_risk_state(profile, evaluations)
    assert assessment.risk_state == INSUFFICIENT_DATA
    assert assessment.precedence_step == 2
    assert assessment.deciding_rule_ids == []


def test_insufficient_data_overrides_systemic_signals_and_progression():
    # Even with strong systemic signals, a missing latest retinal exam
    # must still win (recency-first precedence).
    assessment = _assess(
        retinal_stages=[1, None, None],
        hba1c=[7.0, 7.8, 8.4],
        ldl=[90, 105, 121],
    )
    assert assessment.risk_state == INSUFFICIENT_DATA


def test_deterministic_repeatability():
    profile = build_test_profile(
        dates=DATES, retinal_stages=[0, 0, 0], hba1c=[7.0, 7.8, 8.4], ldl=[90, 108, 121]
    )
    evaluations_1 = evaluate_all_rules(profile)
    assessment_1 = aggregate_risk_state(profile, evaluations_1)

    evaluations_2 = evaluate_all_rules(profile)
    assessment_2 = aggregate_risk_state(profile, evaluations_2)

    assert evaluations_1 == evaluations_2
    assert assessment_1 == assessment_2
