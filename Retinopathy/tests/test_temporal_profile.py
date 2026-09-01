"""Integration tests: full temporal profile built from the loaded synthetic
cases (Steps 3-4). Requires the live Neo4j instance with CKG + patient graph
loaded. Checks trajectory shape only -- no risk-state assertions, since risk
aggregation is not implemented yet.
"""

from app.temporal.profile import build_patient_temporal_profile
from app.temporal.retinal_trajectory import (
    INCIDENT_PROGRESSION,
    INSUFFICIENT_DATA,
    PROGRESSION,
    STABLE,
)


def test_p001_stable_no_dr_profile():
    profile = build_patient_temporal_profile("P001")
    assert profile.retinal_trajectory.overall_transition_type == STABLE
    assert profile.retinal_trajectory.any_progression_observed is False
    hba1c = profile.numeric_features["HbA1c"]
    assert hba1c.direction == "stable"


def test_p002_systemic_worsening_without_retinal_progression():
    profile = build_patient_temporal_profile("P002")
    assert profile.retinal_trajectory.overall_transition_type == STABLE
    hba1c = profile.numeric_features["HbA1c"]
    assert hba1c.direction == "increasing"
    assert hba1c.monotonicity == "monotonic_increase"
    uacr = profile.numeric_features["UACR"]
    assert uacr.direction == "increasing"


def test_p003_incident_mild_npdr():
    profile = build_patient_temporal_profile("P003")
    assert profile.retinal_trajectory.overall_transition_type == INCIDENT_PROGRESSION
    assert profile.retinal_trajectory.any_progression_observed is True
    assert profile.retinal_trajectory.latest_observed_stage_label == "Mild_NPDR"


def test_p004_progression_not_incident():
    profile = build_patient_temporal_profile("P004")
    assert profile.retinal_trajectory.overall_transition_type == PROGRESSION
    assert profile.retinal_trajectory.latest_observed_stage_label == "Moderate_NPDR"


def test_p005_insufficient_retinal_data_despite_systemic_trend():
    profile = build_patient_temporal_profile("P005")
    trajectory = profile.retinal_trajectory
    assert trajectory.n_observed == 1
    assert trajectory.overall_transition_type == INSUFFICIENT_DATA
    assert trajectory.latest_visit_has_observation is False
    assert trajectory.visits_since_last_observation == 2
    # Systemic data is still fully present even though retinal data is not.
    assert profile.numeric_features["HbA1c"].n_observations == 3


def test_all_synthetic_patients_produce_a_profile_without_error():
    for patient_id in ("P001", "P002", "P003", "P004", "P005"):
        profile = build_patient_temporal_profile(patient_id)
        assert profile.patient_id == patient_id
        assert set(profile.numeric_features) == {
            "HbA1c",
            "Systolic_BP",
            "Diastolic_BP",
            "LDL",
            "UACR",
            "eGFR",
            "T1D_Duration",
        }
