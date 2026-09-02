"""Pure view-model layer for the Streamlit demo.

Every function here takes the existing reasoning-layer objects
(PatientTemporalProfile, RiskAssessment, Explanation -- produced by
app/reasoning/assess.py) and reshapes them into display-ready structures.
NO clinical logic is computed here: no rule evaluation, no risk
aggregation, no threshold comparison. This module only reformats what the
reasoning layer already decided, so the UI can never diverge from it.

Contains no Streamlit or Plotly imports, so it is fully unit-testable
without a running app or a browser.
"""

from dataclasses import dataclass, field

from app.graph.csv_validation import ROOT_DIR, load_csv_rows
from app.graph.patient_validation import STAGE_INDEX_TO_CONCEPT
from app.reasoning.assess import assess_patient_full
from app.reasoning.clinical_reference_standards import CLINICAL_REFERENCE_STANDARDS
from app.reasoning.explanation import Explanation
from app.reasoning.risk_aggregation import RiskAssessment
from app.temporal.profile import NUMERIC_CONCEPTS, PatientTemporalProfile

RISK_STATES_IN_SEVERITY_ORDER = (
    "INSUFFICIENT_DATA",
    "STABLE",
    "WATCH",
    "INCREASING_CONCERN",
    "HIGH_CONCERN",
)

RETINAL_STAGE_ORDER = [STAGE_INDEX_TO_CONCEPT[i] for i in range(5)]


@dataclass(frozen=True)
class RetinalTrajectoryChartData:
    """One entry per visit, in date order. A None stage_index means no
    retinal exam was recorded at that visit -- missing, not No_DR."""

    dates: list = field(default_factory=list)
    stage_indices: list = field(default_factory=list)  # int | None, len == len(dates)
    stage_labels: list = field(default_factory=list)  # str | None, len == len(dates)
    is_missing: list = field(default_factory=list)  # bool, len == len(dates)


@dataclass(frozen=True)
class NumericChartData:
    concept: str
    unit: str
    dates: list = field(default_factory=list)
    values: list = field(default_factory=list)


@dataclass(frozen=True)
class PatientView:
    patient_id: str
    context: dict
    risk_state: str
    precedence_step: int
    precedence_reason: str
    latest_retinal_state: dict
    retinal_trajectory_summary: dict
    retinal_chart_data: RetinalTrajectoryChartData
    numeric_chart_data: dict  # concept -> NumericChartData, only concepts with data
    supporting_signals: list = field(default_factory=list)
    triggered_rules: list = field(default_factory=list)
    evidence_citations: dict = field(default_factory=dict)
    missing_data_notes: list = field(default_factory=list)
    association_vs_observation_note: str = ""
    operational_notes: list = field(default_factory=list)
    reference_standards: list = field(default_factory=list)  # list[dict]


def _concept_units(root_dir=ROOT_DIR) -> dict:
    nodes = load_csv_rows(root_dir)["nodes"]
    return {row["name"]: row.get("unit", "") for row in nodes}


def build_retinal_chart_data(profile: PatientTemporalProfile) -> RetinalTrajectoryChartData:
    trajectory = profile.retinal_trajectory
    all_dates = sorted(set(trajectory.missing_visit_dates) | set(trajectory.observed_dates))
    observed_lookup = dict(zip(trajectory.observed_dates, trajectory.observed_stage_indices))

    stage_indices = [observed_lookup.get(d) for d in all_dates]
    stage_labels = [
        STAGE_INDEX_TO_CONCEPT.get(i) if i is not None else None for i in stage_indices
    ]
    is_missing = [d in trajectory.missing_visit_dates for d in all_dates]

    return RetinalTrajectoryChartData(
        dates=all_dates,
        stage_indices=stage_indices,
        stage_labels=stage_labels,
        is_missing=is_missing,
    )


def build_numeric_chart_data(profile: PatientTemporalProfile) -> dict:
    chart_data = {}
    units = _concept_units()
    for concept in NUMERIC_CONCEPTS:
        features = profile.numeric_features.get(concept)
        if features and features.n_observations >= 1:
            chart_data[concept] = NumericChartData(
                concept=concept,
                unit=units.get(concept, ""),
                dates=list(features.dates),
                values=list(features.values),
            )
    return chart_data


def build_patient_view(patient_id: str) -> PatientView:
    profile, risk_assessment, explanation = assess_patient_full(patient_id)
    return assemble_view(profile, risk_assessment, explanation)


def assemble_view(
    profile: PatientTemporalProfile,
    risk_assessment: RiskAssessment,
    explanation: Explanation,
) -> PatientView:
    return PatientView(
        patient_id=profile.patient_id,
        context=dict(profile.context),
        risk_state=risk_assessment.risk_state,
        precedence_step=risk_assessment.precedence_step,
        precedence_reason=risk_assessment.precedence_reason,
        latest_retinal_state=dict(explanation.latest_retinal_state),
        retinal_trajectory_summary=dict(explanation.retinal_trajectory),
        retinal_chart_data=build_retinal_chart_data(profile),
        numeric_chart_data=build_numeric_chart_data(profile),
        supporting_signals=list(explanation.supporting_signals),
        triggered_rules=list(explanation.triggered_rules),
        evidence_citations=dict(explanation.evidence_citations),
        missing_data_notes=list(explanation.missing_data_notes),
        association_vs_observation_note=explanation.association_vs_observation_note,
        operational_notes=list(explanation.operational_notes),
        reference_standards=[vars(std) for std in CLINICAL_REFERENCE_STANDARDS],
    )
