"""Top-level orchestrator: patient_id -> (RiskAssessment, Explanation).

Wires together the temporal profile (Step 5-6), the rule engine, risk
aggregation, and explanation generation. No new logic lives here.
"""

from app.reasoning.explanation import Explanation, build_explanation
from app.reasoning.risk_aggregation import RiskAssessment, aggregate_risk_state
from app.reasoning.rule_engine import evaluate_all_rules
from app.temporal.profile import PatientTemporalProfile, build_patient_temporal_profile


def assess_patient(patient_id: str) -> tuple:
    profile = build_patient_temporal_profile(patient_id)
    return assess_profile(profile)


def assess_patient_full(patient_id: str) -> tuple:
    """Like assess_patient, but also returns the PatientTemporalProfile --
    for consumers (e.g. the UI) that need the raw numeric/retinal series
    for charting in addition to the risk assessment and explanation,
    without querying Neo4j twice.
    """
    profile = build_patient_temporal_profile(patient_id)
    risk_assessment, explanation = assess_profile(profile)
    return profile, risk_assessment, explanation


def assess_profile(profile: PatientTemporalProfile) -> tuple:
    rule_evaluations = evaluate_all_rules(profile)
    risk_assessment = aggregate_risk_state(profile, rule_evaluations)
    explanation = build_explanation(profile, rule_evaluations, risk_assessment)
    return risk_assessment, explanation
