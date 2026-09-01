"""Integration tests: full rule engine + risk aggregation + explanation
against the 5 loaded synthetic patients (Steps 3-4), compared against the
expected_risk_state documented in synthetic_cases.json. Requires the live
Neo4j instance with CKG + patient graph loaded.
"""

import json

from app.graph.csv_validation import ROOT_DIR
from app.reasoning.assess import assess_patient

EXPECTED_RISK_STATES = {
    case["id"]: case["expected_risk_state"]
    for case in json.loads((ROOT_DIR / "synthetic_cases.json").read_text(encoding="utf-8"))["cases"]
}


def test_expected_risk_states_are_the_five_documented_in_synthetic_cases_json():
    assert EXPECTED_RISK_STATES == {
        "P001": "STABLE",
        "P002": "WATCH",
        "P003": "HIGH_CONCERN",
        "P004": "HIGH_CONCERN",
        "P005": "INSUFFICIENT_DATA",
    }


def test_p001_matches_expected_risk_state():
    assessment, explanation = assess_patient("P001")
    assert assessment.risk_state == EXPECTED_RISK_STATES["P001"]
    assert explanation.risk_state == assessment.risk_state


def test_p002_matches_expected_risk_state():
    assessment, explanation = assess_patient("P002")
    assert assessment.risk_state == EXPECTED_RISK_STATES["P002"]
    triggered_ids = {r["rule_id"] for r in explanation.triggered_rules}
    assert "R012" in triggered_ids


def test_p003_matches_expected_risk_state():
    assessment, explanation = assess_patient("P003")
    assert assessment.risk_state == EXPECTED_RISK_STATES["P003"]
    triggered_ids = {r["rule_id"] for r in explanation.triggered_rules}
    assert "R003" in triggered_ids  # incident
    assert "R011" in triggered_ids


def test_p004_matches_expected_risk_state():
    assessment, explanation = assess_patient("P004")
    assert assessment.risk_state == EXPECTED_RISK_STATES["P004"]
    triggered_ids = {r["rule_id"] for r in explanation.triggered_rules}
    assert "R004" in triggered_ids  # progression, not incident (existing DR)
    assert "R003" not in triggered_ids
    assert "R011" in triggered_ids


def test_p005_matches_expected_risk_state():
    assessment, explanation = assess_patient("P005")
    assert assessment.risk_state == EXPECTED_RISK_STATES["P005"]
    assert explanation.latest_retinal_state["is_current_visit"] is False
    assert explanation.missing_data_notes


def test_all_five_patients_deterministic_across_repeated_assessment():
    for patient_id in ("P001", "P002", "P003", "P004", "P005"):
        first_assessment, first_explanation = assess_patient(patient_id)
        second_assessment, second_explanation = assess_patient(patient_id)
        assert first_assessment == second_assessment
        assert first_explanation == second_explanation


def test_every_triggered_rule_across_all_patients_has_evidence_provenance():
    for patient_id in ("P001", "P002", "P003", "P004", "P005"):
        _, explanation = assess_patient(patient_id)
        for rule in explanation.triggered_rules:
            assert rule["evidence_ids"], f"{patient_id} rule {rule['rule_id']} has no evidence_ids"
            for eid in rule["evidence_ids"]:
                assert eid in explanation.evidence_citations
                citation = explanation.evidence_citations[eid]
                assert citation["citation"]
                assert citation["evidence_strength"]
