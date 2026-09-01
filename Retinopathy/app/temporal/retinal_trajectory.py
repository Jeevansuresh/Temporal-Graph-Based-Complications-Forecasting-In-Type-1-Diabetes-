"""Ordinal (categorical) trajectory analysis for retinal stage.

Retinal stage is an ordered 5-level scale (No_DR < Mild_NPDR < Moderate_NPDR
< Severe_NPDR < PDR), never a continuous numeric measurement. This module
only ever compares stage_index values with ==, <, > -- no slope, no percent
change, no averaging. A missing retinal_stage observation is represented by
its absence from `observed`, never coerced to stage 0 (No_DR).

Transition-type vocabulary intentionally mirrors the output_concept names
already defined in rules.csv (R003 Incident_Retinopathy, R004
Retinopathy_Progression, R005 Stable_Retinal_State) so a later rule-engine
step can consume this module's output directly without reinterpreting it.
IMPROVEMENT has no corresponding rule in rules.csv -- diabetic retinopathy
is not expected to clinically reverse -- so it is reported here purely as a
transparent description of what the ordinal data shows (e.g. re-grading,
data correction), never as a clinical claim that DR regressed.
"""

from dataclasses import dataclass, field

from app.graph.patient_validation import STAGE_INDEX_TO_CONCEPT

STABLE = "STABLE"
PROGRESSION = "PROGRESSION"
INCIDENT_PROGRESSION = "INCIDENT_PROGRESSION"
IMPROVEMENT = "IMPROVEMENT"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

NO_DR_STAGE_INDEX = 0


@dataclass(frozen=True)
class RetinalTransition:
    from_date: str
    to_date: str
    from_stage_index: int
    to_stage_index: int
    transition_type: str
    observation_gap: bool  # a visit with a missing retinal exam falls strictly between these two dates


@dataclass(frozen=True)
class RetinalTrajectory:
    n_visits_total: int
    n_observed: int
    missing_visit_dates: list = field(default_factory=list)
    observed_dates: list = field(default_factory=list)
    observed_stage_indices: list = field(default_factory=list)
    transitions: list = field(default_factory=list)
    latest_observed_date: str | None = None
    latest_observed_stage_index: int | None = None
    latest_observed_stage_label: str | None = None
    latest_visit_date: str | None = None
    latest_visit_has_observation: bool = False
    visits_since_last_observation: int | None = None
    overall_transition_type: str = INSUFFICIENT_DATA
    any_progression_observed: bool = False
    any_improvement_observed: bool = False


def classify_transition(previous_stage_index: int, current_stage_index: int) -> str:
    if current_stage_index == previous_stage_index:
        return STABLE
    if current_stage_index > previous_stage_index:
        return INCIDENT_PROGRESSION if previous_stage_index == NO_DR_STAGE_INDEX else PROGRESSION
    return IMPROVEMENT


def analyze_retinal_trajectory(all_visit_dates: list, observed: list) -> RetinalTrajectory:
    """
    all_visit_dates: every visit date (str, ISO) for the patient.
    observed: [{"date": str, "stage_index": int}, ...] for visits that had a
        retinal exam. Must be a subset of all_visit_dates.
    """
    all_visit_dates = sorted(all_visit_dates)
    observed = sorted(observed, key=lambda o: o["date"])
    observed_dates = [o["date"] for o in observed]
    missing_visit_dates = [d for d in all_visit_dates if d not in observed_dates]

    transitions = [
        RetinalTransition(
            from_date=prev["date"],
            to_date=curr["date"],
            from_stage_index=prev["stage_index"],
            to_stage_index=curr["stage_index"],
            transition_type=classify_transition(prev["stage_index"], curr["stage_index"]),
            observation_gap=any(
                prev["date"] < d < curr["date"] for d in missing_visit_dates
            ),
        )
        for prev, curr in zip(observed, observed[1:])
    ]

    latest_visit_date = all_visit_dates[-1] if all_visit_dates else None
    latest_visit_has_observation = bool(observed_dates) and observed_dates[-1] == latest_visit_date

    visits_since_last_observation = (
        sum(1 for d in all_visit_dates if d > observed_dates[-1]) if observed_dates else None
    )

    overall_transition_type = transitions[-1].transition_type if len(observed) >= 2 else INSUFFICIENT_DATA

    return RetinalTrajectory(
        n_visits_total=len(all_visit_dates),
        n_observed=len(observed),
        missing_visit_dates=missing_visit_dates,
        observed_dates=observed_dates,
        observed_stage_indices=[o["stage_index"] for o in observed],
        transitions=transitions,
        latest_observed_date=observed_dates[-1] if observed_dates else None,
        latest_observed_stage_index=observed[-1]["stage_index"] if observed else None,
        latest_observed_stage_label=(
            STAGE_INDEX_TO_CONCEPT.get(observed[-1]["stage_index"]) if observed else None
        ),
        latest_visit_date=latest_visit_date,
        latest_visit_has_observation=latest_visit_has_observation,
        visits_since_last_observation=visits_since_last_observation,
        overall_transition_type=overall_transition_type,
        any_progression_observed=any(
            t.transition_type in (PROGRESSION, INCIDENT_PROGRESSION) for t in transitions
        ),
        any_improvement_observed=any(t.transition_type == IMPROVEMENT for t in transitions),
    )
