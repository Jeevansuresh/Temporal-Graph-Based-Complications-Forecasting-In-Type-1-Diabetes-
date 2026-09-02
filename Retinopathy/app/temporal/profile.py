"""Deterministic per-patient temporal profile.

Combines the raw timeline (app/temporal/patient_timeline.py), per-concept
numeric trend features (app/temporal/numeric_features.py), and the
ordinal retinal-stage trajectory (app/temporal/retinal_trajectory.py) into
one object. No risk-state aggregation, clinical rule evaluation, or
evidence citation happens here -- that is a later step.
"""

from dataclasses import dataclass

from app.graph.patient_validation import FIELD_TO_CONCEPT
from app.temporal.numeric_features import NumericSeriesFeatures, analyze_numeric_series
from app.temporal.patient_timeline import PatientTimeline, load_patient_timeline
from app.temporal.retinal_trajectory import RetinalTrajectory, analyze_retinal_trajectory

NUMERIC_CONCEPTS = sorted(set(FIELD_TO_CONCEPT.values())) + ["T1D_Duration"]


@dataclass(frozen=True)
class PatientTemporalProfile:
    patient_id: str
    context: dict
    numeric_features: dict[str, NumericSeriesFeatures]
    retinal_trajectory: RetinalTrajectory


def _extract_numeric_series(timeline: PatientTimeline, concept: str) -> tuple[list, list]:
    dates, values = [], []
    for visit in timeline.visits:
        value = visit.t1d_duration_years if concept == "T1D_Duration" else visit.measurements.get(concept)
        if value is not None:
            dates.append(visit.date)
            values.append(value)
    return dates, values


def build_patient_temporal_profile(patient_id: str) -> PatientTemporalProfile:
    timeline = load_patient_timeline(patient_id)

    numeric_features = {}
    for concept in NUMERIC_CONCEPTS:
        dates, values = _extract_numeric_series(timeline, concept)
        numeric_features[concept] = analyze_numeric_series(concept, dates, values)

    all_visit_dates = [visit.date for visit in timeline.visits]
    observed = [
        {"date": visit.date, "stage_index": visit.retinal_stage_index}
        for visit in timeline.visits
        if visit.retinal_stage_index is not None
    ]
    retinal_trajectory = analyze_retinal_trajectory(all_visit_dates, observed)

    context = {
        "age": timeline.age,
        "sex": timeline.sex,
        "height_cm": timeline.height_cm,
        "puberty_status": timeline.puberty_status,
        "t1d_diagnosis": timeline.t1d_diagnosis,
    }

    return PatientTemporalProfile(
        patient_id=timeline.patient_id,
        context=context,
        numeric_features=numeric_features,
        retinal_trajectory=retinal_trajectory,
    )
