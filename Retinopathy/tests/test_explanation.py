from app.reasoning.explanation import build_explanation
from app.reasoning.risk_aggregation import aggregate_risk_state
from app.reasoning.rule_engine import evaluate_all_rules
from tests.profile_builder import build_test_profile

DATES = ["2024-01-15", "2025-01-15", "2026-01-15"]


def _explain(**kwargs):
    profile = build_test_profile(dates=DATES, **kwargs)
    evaluations = evaluate_all_rules(profile)
    assessment = aggregate_risk_state(profile, evaluations)
    return build_explanation(profile, evaluations, assessment)


def test_incident_progression_explanation_has_c010_citation_and_no_fabrication():
    explanation = _explain(retinal_stages=[0, 0, 1])
    assert explanation.risk_state == "HIGH_CONCERN"
    assert explanation.latest_retinal_state["stage_label"] == "Mild_NPDR"
    assert explanation.latest_retinal_state["is_current_visit"] is True

    triggered_ids = {r["rule_id"] for r in explanation.triggered_rules}
    assert {"R003", "R004", "R011"}.issubset(triggered_ids)

    assert "C010" in explanation.evidence_citations
    citation = explanation.evidence_citations["C010"]
    # Every field must come from evidence.csv/evidence_audit.csv verbatim,
    # not be synthesized. C010 correctly means the ICDR severity
    # classification in BOTH files as of the Milestone 2.5 evidence-
    # integrity correction (previously evidence.csv's C010 pointed at an
    # unrelated pediatric cohort study -- see test_csv_validation.py's
    # collision-detection tests).
    assert citation["claim"]
    assert citation["citation"]
    assert citation["evidence_strength"] is not None
    assert "severity" in citation["claim"].lower() or "ICDR" in citation["claim"]


def test_watch_explanation_cites_only_triggered_signal_evidence():
    explanation = _explain(
        retinal_stages=[0, 0, 0],
        hba1c=[7.0, 7.8, 8.4],
        ldl=[90, 108, 121],
    )
    assert explanation.risk_state == "WATCH"
    triggered_ids = {r["rule_id"] for r in explanation.triggered_rules}
    assert "R012" in triggered_ids
    assert "R006" in triggered_ids  # glycemic signal fired
    assert "R008" in triggered_ids  # lipid signal fired
    assert "R007" not in triggered_ids  # BP never elevated -- must not appear as triggered
    assert "R009" not in triggered_ids  # UACR never elevated -- must not appear as triggered


def test_missing_retinal_observation_surfaces_uncertainty_not_no_dr():
    explanation = _explain(retinal_stages=[0, None, None])
    assert explanation.risk_state == "INSUFFICIENT_DATA"
    assert explanation.latest_retinal_state["is_current_visit"] is False
    # Must describe the gap, never claim No_DR at the missing visits.
    assert any("No retinal exam recorded" in note for note in explanation.missing_data_notes)
    assert explanation.latest_retinal_state["stage_label"] == "No_DR"  # last *known* stage, correctly labeled as historical
    assert "2025-01-15, 2026-01-15" in ", ".join(explanation.missing_data_notes)


def test_observed_facts_are_distinguished_from_associations():
    explanation = _explain(retinal_stages=[0, 0, 0], hba1c=[7.0, 7.8, 8.4], ldl=[90, 108, 121])
    note = explanation.association_vs_observation_note.lower()
    assert "observed" in note
    assert "association" in note
    assert "not" in note  # explicitly states these are not diagnoses


def test_supporting_signals_always_reported_whether_or_not_triggered():
    explanation = _explain(retinal_stages=[0, 0, 0])
    reported_ids = {s["rule_id"] for s in explanation.supporting_signals}
    assert reported_ids == {"R006", "R007", "R008", "R009"}
    assert all(s["satisfied"] is False for s in explanation.supporting_signals)


def test_evidence_citations_never_include_unrelated_ids():
    explanation = _explain(retinal_stages=[0, 0, 0])  # STABLE, no rule triggered but R005
    triggered_ids = {r["rule_id"] for r in explanation.triggered_rules}
    for rule in explanation.triggered_rules:
        for eid in rule["evidence_ids"]:
            assert eid in explanation.evidence_citations
    assert triggered_ids == {"R005"}
