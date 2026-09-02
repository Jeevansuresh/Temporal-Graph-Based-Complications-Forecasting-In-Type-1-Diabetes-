"""Pure unit tests for the view-model layer -- no Streamlit, no DB.
Constructs known scenarios via tests/profile_builder.py.
"""

from app.reasoning.explanation import build_explanation
from app.reasoning.risk_aggregation import aggregate_risk_state
from app.reasoning.rule_engine import evaluate_all_rules
from app.ui.view_model import assemble_view, build_numeric_chart_data, build_retinal_chart_data
from tests.profile_builder import build_test_profile

DATES = ["2024-01-10", "2025-01-10", "2026-01-10"]


def _view(**kwargs):
    profile = build_test_profile(dates=DATES, **kwargs)
    evaluations = evaluate_all_rules(profile)
    assessment = aggregate_risk_state(profile, evaluations)
    explanation = build_explanation(profile, evaluations, assessment)
    return assemble_view(profile, assessment, explanation)


def test_retinal_chart_data_marks_missing_visits_not_no_dr():
    view = _view(retinal_stages=[0, None, None])
    chart = view.retinal_chart_data

    assert chart.dates == DATES
    assert chart.stage_indices == [0, None, None]
    assert chart.stage_labels == ["No_DR", None, None]
    assert chart.is_missing == [False, True, True]


def test_retinal_chart_data_all_observed_has_no_missing_markers():
    view = _view(retinal_stages=[0, 0, 1])
    chart = view.retinal_chart_data
    assert chart.stage_indices == [0, 0, 1]
    assert chart.is_missing == [False, False, False]


def test_numeric_chart_data_only_includes_concepts_with_observations():
    view = _view(retinal_stages=[0, 0, 0], hba1c=[7.0, 7.8, 8.4], ldl=[90, 108, 121])
    assert set(view.numeric_chart_data) == {"HbA1c", "LDL"}
    assert view.numeric_chart_data["HbA1c"].values == [7.0, 7.8, 8.4]
    assert view.numeric_chart_data["HbA1c"].dates == DATES


def test_numeric_chart_data_empty_when_no_systemic_measurements():
    view = _view(retinal_stages=[0, 0, 0])
    assert view.numeric_chart_data == {}


def test_view_risk_state_matches_underlying_assessment():
    profile = build_test_profile(dates=DATES, retinal_stages=[0, 0, 1])
    evaluations = evaluate_all_rules(profile)
    assessment = aggregate_risk_state(profile, evaluations)
    explanation = build_explanation(profile, evaluations, assessment)
    view = assemble_view(profile, assessment, explanation)

    assert view.risk_state == assessment.risk_state == "HIGH_CONCERN"
    assert view.precedence_reason == assessment.precedence_reason
    assert view.triggered_rules == explanation.triggered_rules
    assert view.evidence_citations == explanation.evidence_citations
    assert view.missing_data_notes == explanation.missing_data_notes


def test_view_reference_standards_are_present_and_labeled():
    view = _view(retinal_stages=[0, 0, 0])
    ids = {r["standard_id"] for r in view.reference_standards}
    assert ids == {"REF001", "REF002", "REF003"}
    for r in view.reference_standards:
        assert r["operationalizes_rule_clause"]


def test_build_numeric_chart_data_uses_units_from_nodes_csv():
    profile = build_test_profile(dates=DATES, hba1c=[7.0, 7.8, 8.4])
    chart_data = build_numeric_chart_data(profile)
    assert chart_data["HbA1c"].unit == "%"


def test_build_retinal_chart_data_standalone():
    profile = build_test_profile(dates=DATES, retinal_stages=[1, None, 2])
    chart = build_retinal_chart_data(profile)
    assert chart.stage_indices == [1, None, 2]
    assert chart.is_missing == [False, True, False]
