"""Requires the CKG and patient graph already loaded (Steps 3-4)."""

import pytest

from app.temporal.patient_timeline import load_patient_timeline


def test_p001_timeline_shape_and_order():
    timeline = load_patient_timeline("P001")
    assert timeline.patient_id == "P001"
    assert [v.date for v in timeline.visits] == ["2024-01-10", "2025-01-10", "2026-01-10"]
    assert [v.measurements["HbA1c"] for v in timeline.visits] == [7.0, 7.1, 7.0]
    assert all(v.retinal_stage_index == 0 for v in timeline.visits)


def test_t1d_duration_increases_with_visit_date():
    timeline = load_patient_timeline("P001")
    durations = [v.t1d_duration_years for v in timeline.visits]
    assert durations == sorted(durations)
    assert all(d is not None for d in durations)


def test_p005_missing_retinal_observations_stay_missing():
    timeline = load_patient_timeline("P005")
    assert [v.retinal_stage_index for v in timeline.visits] == [0, None, None]


def test_unknown_patient_raises():
    with pytest.raises(ValueError):
        load_patient_timeline("P_DOES_NOT_EXIST")
