"""Evidence-grounded explanation generation.

Builds a structured explanation for one risk assessment, tracing every
triggered rule back to its rule_id (rules.csv) and evidence_id
(evidence.csv/evidence_audit.csv). Never invents a citation, evidence
strength, or clinical claim: evidence text comes only from
app/graph/ckg_loader.build_evidence_records (the same merge used to load
the CKG in Step 3), and operational-threshold notes come only from
app/reasoning/clinical_reference_standards.py, clearly labeled as a
separate, non-CKG layer.
"""

from dataclasses import dataclass, field
from pathlib import Path

from app.graph.ckg_loader import build_evidence_records
from app.graph.csv_validation import ROOT_DIR, load_csv_rows
from app.reasoning.risk_aggregation import RiskAssessment
from app.temporal.profile import PatientTemporalProfile

ASSOCIATION_VS_OBSERVATION_NOTE = (
    "Retinal-stage transitions (STABLE / PROGRESSION / INCIDENT_PROGRESSION / "
    "IMPROVEMENT) are directly observed facts from recorded retinal exams -- "
    "the primary signal. Systemic supporting signals (glycemic, BP, lipid, "
    "kidney-context) are documented risk-factor ASSOCIATIONS with retinopathy "
    "risk (relationships.csv), not independent diagnoses of retinopathy and not "
    "proof that retinopathy is present or progressing."
)


@dataclass(frozen=True)
class Explanation:
    patient_id: str
    risk_state: str
    precedence_step: int
    precedence_reason: str
    latest_retinal_state: dict
    retinal_trajectory: dict
    supporting_signals: list = field(default_factory=list)
    triggered_rules: list = field(default_factory=list)
    evidence_citations: dict = field(default_factory=dict)
    missing_data_notes: list = field(default_factory=list)
    association_vs_observation_note: str = ASSOCIATION_VS_OBSERVATION_NOTE
    operational_notes: list = field(default_factory=list)


def _evidence_lookup(root_dir: Path = ROOT_DIR) -> dict:
    rows = load_csv_rows(root_dir)
    records = build_evidence_records(rows["evidence"], rows["evidence_audit"])
    return {r["evidence_id"]: r for r in records}


def build_explanation(
    profile: PatientTemporalProfile,
    rule_evaluations: dict,
    risk_assessment: RiskAssessment,
    root_dir: Path = ROOT_DIR,
) -> Explanation:
    evidence_lookup = _evidence_lookup(root_dir)
    trajectory = profile.retinal_trajectory

    latest_retinal_state = {
        "stage_index": trajectory.latest_observed_stage_index,
        "stage_label": trajectory.latest_observed_stage_label,
        "date": trajectory.latest_observed_date,
        "is_current_visit": trajectory.latest_visit_has_observation,
    }

    triggered = [rule for rule in rule_evaluations.values() if rule.satisfied]

    triggered_rules_out = []
    evidence_ids_used: set = set()
    for rule in triggered:
        evidence_ids_used.update(rule.evidence_ids)
        triggered_rules_out.append(
            {
                "rule_id": rule.rule_id,
                "trigger": rule.trigger,
                "output_concept": rule.output_concept,
                "evidence_ids": rule.evidence_ids,
                "reason": rule.reason,
            }
        )
    triggered_rules_out.sort(key=lambda r: r["rule_id"])

    evidence_citations = {}
    for eid in sorted(evidence_ids_used):
        record = evidence_lookup.get(eid)
        if record:
            evidence_citations[eid] = {
                "citation": record.get("citation") or record.get("audit_source"),
                "claim": record.get("claim") or record.get("audit_clinical_claim"),
                "evidence_strength": record.get("evidence_strength"),
                "population": record.get("population") or record.get("audit_population"),
                "url": record.get("url"),
            }

    supporting_signals = []
    for rid in ("R006", "R007", "R008", "R009"):
        rule = rule_evaluations.get(rid)
        if rule is not None:
            supporting_signals.append(
                {
                    "rule_id": rule.rule_id,
                    "output_concept": rule.output_concept,
                    "satisfied": rule.satisfied,
                    "reason": rule.reason,
                    "evidence_ids": rule.evidence_ids,
                }
            )

    missing_data_notes = []
    if not trajectory.latest_visit_has_observation:
        if trajectory.latest_observed_date:
            missing_data_notes.append(
                f"No retinal exam recorded at the latest visit "
                f"({trajectory.latest_visit_date}); most recent known stage is "
                f"{trajectory.latest_observed_stage_label} as of "
                f"{trajectory.latest_observed_date}."
            )
        else:
            missing_data_notes.append(
                f"No retinal exam has ever been recorded for this patient "
                f"(latest visit: {trajectory.latest_visit_date})."
            )
    if trajectory.missing_visit_dates:
        missing_data_notes.append(
            f"Visits with no retinal exam: {', '.join(trajectory.missing_visit_dates)}."
        )
    if trajectory.n_observed == 1 and trajectory.latest_visit_has_observation:
        missing_data_notes.append(
            "Only one retinal observation exists; no prior observation is "
            "available for trajectory comparison."
        )

    return Explanation(
        patient_id=profile.patient_id,
        risk_state=risk_assessment.risk_state,
        precedence_step=risk_assessment.precedence_step,
        precedence_reason=risk_assessment.precedence_reason,
        latest_retinal_state=latest_retinal_state,
        retinal_trajectory={
            "n_visits_total": trajectory.n_visits_total,
            "n_observed": trajectory.n_observed,
            "overall_transition_type": trajectory.overall_transition_type,
            "any_progression_observed": trajectory.any_progression_observed,
            "any_improvement_observed": trajectory.any_improvement_observed,
            "transitions": [
                {
                    "from_date": t.from_date,
                    "to_date": t.to_date,
                    "from_stage_index": t.from_stage_index,
                    "to_stage_index": t.to_stage_index,
                    "transition_type": t.transition_type,
                }
                for t in trajectory.transitions
            ],
        },
        supporting_signals=supporting_signals,
        triggered_rules=triggered_rules_out,
        evidence_citations=evidence_citations,
        missing_data_notes=missing_data_notes,
        operational_notes=risk_assessment.operational_notes,
    )
