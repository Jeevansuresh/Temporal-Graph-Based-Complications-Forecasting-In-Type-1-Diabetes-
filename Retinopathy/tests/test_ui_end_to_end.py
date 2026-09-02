"""End-to-end check: for each of P001-P005, the view the UI would display
is built purely from -- and never diverges from -- the same assessment
object app/reasoning/assess.py already produces. Requires the live Neo4j
instance with CKG + patient graph loaded (Steps 3-4).
"""

from app.reasoning.assess import assess_patient_full
from app.ui.charts import build_numeric_trend_figure, build_retinal_trajectory_figure
from app.ui.view_model import build_patient_view

EXPECTED_RISK_STATES = {
    "P001": "STABLE",
    "P002": "WATCH",
    "P003": "HIGH_CONCERN",
    "P004": "HIGH_CONCERN",
    "P005": "INSUFFICIENT_DATA",
}


def test_each_patient_view_derives_from_the_existing_assessment_object():
    for patient_id, expected_state in EXPECTED_RISK_STATES.items():
        profile, risk_assessment, explanation = assess_patient_full(patient_id)
        view = build_patient_view(patient_id)

        assert view.patient_id == patient_id
        assert view.risk_state == expected_state
        assert view.risk_state == risk_assessment.risk_state
        assert view.precedence_step == risk_assessment.precedence_step
        assert view.precedence_reason == risk_assessment.precedence_reason
        assert view.triggered_rules == explanation.triggered_rules
        assert view.evidence_citations == explanation.evidence_citations
        assert view.missing_data_notes == explanation.missing_data_notes
        assert view.latest_retinal_state == explanation.latest_retinal_state
        assert view.retinal_trajectory_summary == explanation.retinal_trajectory


def test_each_patient_charts_build_without_error():
    for patient_id in EXPECTED_RISK_STATES:
        view = build_patient_view(patient_id)
        retinal_fig = build_retinal_trajectory_figure(view.retinal_chart_data)
        assert retinal_fig.data  # at least the observed-stage trace exists

        for chart_data in view.numeric_chart_data.values():
            fig = build_numeric_trend_figure(chart_data)
            assert len(fig.data[0].x) == len(chart_data.dates)


def test_p005_missing_retinal_visits_visible_in_chart_data_not_no_dr():
    view = build_patient_view("P005")
    chart = view.retinal_chart_data

    missing_dates = [d for d, m in zip(chart.dates, chart.is_missing) if m]
    assert missing_dates == ["2025-08-01", "2026-08-01"]
    for d in missing_dates:
        idx = chart.dates.index(d)
        assert chart.stage_indices[idx] is None
        assert chart.stage_labels[idx] is None


def test_p003_incident_progression_visible_in_chart_data():
    view = build_patient_view("P003")
    chart = view.retinal_chart_data
    assert chart.stage_indices == [0, 0, 1]
    assert chart.is_missing == [False, False, False]
    assert view.retinal_trajectory_summary["overall_transition_type"] == "INCIDENT_PROGRESSION"


def test_all_patients_produce_a_risk_state_from_the_allowed_five():
    allowed = {"STABLE", "WATCH", "INCREASING_CONCERN", "HIGH_CONCERN", "INSUFFICIENT_DATA"}
    for patient_id in EXPECTED_RISK_STATES:
        view = build_patient_view(patient_id)
        assert view.risk_state in allowed
