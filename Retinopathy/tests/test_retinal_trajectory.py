from app.temporal.retinal_trajectory import (
    IMPROVEMENT,
    INCIDENT_PROGRESSION,
    INSUFFICIENT_DATA,
    PROGRESSION,
    STABLE,
    analyze_retinal_trajectory,
    classify_transition,
)


def test_classify_transition_stable():
    assert classify_transition(1, 1) == STABLE


def test_classify_transition_progression_non_incident():
    assert classify_transition(1, 2) == PROGRESSION


def test_classify_transition_incident_progression_from_no_dr():
    assert classify_transition(0, 1) == INCIDENT_PROGRESSION


def test_classify_transition_improvement():
    assert classify_transition(2, 1) == IMPROVEMENT


def test_zero_observations_is_insufficient_data():
    trajectory = analyze_retinal_trajectory(["2024-01-01", "2025-01-01"], [])
    assert trajectory.n_observed == 0
    assert trajectory.overall_transition_type == INSUFFICIENT_DATA
    assert trajectory.latest_observed_stage_index is None
    assert trajectory.latest_visit_has_observation is False
    assert trajectory.visits_since_last_observation is None


def test_single_observation_is_insufficient_data_but_not_discarded():
    trajectory = analyze_retinal_trajectory(
        ["2024-01-01"], [{"date": "2024-01-01", "stage_index": 0}]
    )
    assert trajectory.n_observed == 1
    assert trajectory.overall_transition_type == INSUFFICIENT_DATA
    assert trajectory.latest_observed_stage_index == 0
    assert trajectory.latest_observed_stage_label == "No_DR"
    assert trajectory.transitions == []


def test_stable_trajectory_p001_like():
    dates = ["2024-01-10", "2025-01-10", "2026-01-10"]
    observed = [{"date": d, "stage_index": 0} for d in dates]
    trajectory = analyze_retinal_trajectory(dates, observed)
    assert trajectory.overall_transition_type == STABLE
    assert trajectory.any_progression_observed is False
    assert trajectory.any_improvement_observed is False
    assert [t.transition_type for t in trajectory.transitions] == [STABLE, STABLE]


def test_incident_progression_p003_like():
    dates = ["2024-01-15", "2025-01-15", "2026-01-15"]
    observed = [
        {"date": dates[0], "stage_index": 0},
        {"date": dates[1], "stage_index": 0},
        {"date": dates[2], "stage_index": 1},
    ]
    trajectory = analyze_retinal_trajectory(dates, observed)
    assert [t.transition_type for t in trajectory.transitions] == [STABLE, INCIDENT_PROGRESSION]
    assert trajectory.overall_transition_type == INCIDENT_PROGRESSION
    assert trajectory.any_progression_observed is True


def test_progression_from_existing_dr_is_not_incident_p004_like():
    dates = ["2024-06-01", "2025-06-01", "2026-06-01"]
    observed = [
        {"date": dates[0], "stage_index": 1},
        {"date": dates[1], "stage_index": 1},
        {"date": dates[2], "stage_index": 2},
    ]
    trajectory = analyze_retinal_trajectory(dates, observed)
    assert [t.transition_type for t in trajectory.transitions] == [STABLE, PROGRESSION]
    assert trajectory.overall_transition_type == PROGRESSION


def test_missing_visits_are_reported_not_fabricated_p005_like():
    dates = ["2024-08-01", "2025-08-01", "2026-08-01"]
    observed = [{"date": dates[0], "stage_index": 0}]
    trajectory = analyze_retinal_trajectory(dates, observed)
    assert trajectory.n_visits_total == 3
    assert trajectory.n_observed == 1
    assert trajectory.missing_visit_dates == [dates[1], dates[2]]
    assert trajectory.latest_visit_date == dates[2]
    assert trajectory.latest_visit_has_observation is False
    assert trajectory.visits_since_last_observation == 2
    assert trajectory.overall_transition_type == INSUFFICIENT_DATA


def test_observation_gap_flagged_when_intervening_visit_missing():
    dates = ["2024-01-01", "2025-01-01", "2026-01-01"]
    observed = [
        {"date": dates[0], "stage_index": 0},
        {"date": dates[2], "stage_index": 1},
    ]
    trajectory = analyze_retinal_trajectory(dates, observed)
    assert len(trajectory.transitions) == 1
    assert trajectory.transitions[0].observation_gap is True
    assert trajectory.missing_visit_dates == [dates[1]]
