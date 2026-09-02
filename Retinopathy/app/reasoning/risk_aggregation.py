"""Deterministic risk-state aggregation.

Combines the retinal-stage trajectory (the primary direct signal) with the
systemic supporting signals (R006-R009) into exactly one of the five
allowed risk states: STABLE, WATCH, INCREASING_CONCERN, HIGH_CONCERN,
INSUFFICIENT_DATA.

This is NOT a point score. It is a precedence-ordered sequence of rule-
trigger checks, following rules.csv's own rule structure (R003-R005 feed
R010-R013) directly. No numeric weighting or summation is used anywhere.

PRECEDENCE (evaluated top to bottom; first match wins):

  1. INSUFFICIENT_DATA -- R013: no retinal observation recorded at the
     latest visit. Recency-first: this overrides every other signal,
     because without a current retinal read no other conclusion is a
     reliable *current* assessment. A missing exam is NEVER treated as
     No_DR.

  2. INSUFFICIENT_DATA -- documented extension, not a literal rules.csv
     rule: a retinal observation exists at the latest visit, but there is
     no prior observation to compare it against (fewer than 2 total
     retinal observations), so no trajectory (progression/stability) can
     be determined. Asserting STABLE here would overclaim "no change" that
     cannot actually be verified from a single data point. No rule_id is
     attributed to this step.

  3. HIGH_CONCERN -- R011: direct retinal progression dominates. Fires
     when R003 (Incident_Retinopathy) or R004 (Retinopathy_Progression) is
     satisfied, regardless of systemic signal count. Direct observed
     retinal-stage change is always the primary signal.

  4. INCREASING_CONCERN -- R010: retinopathy already present (latest
     observed stage > No_DR), this visit's retinal trajectory is stable or
     improved (not progressing -- otherwise step 3 would already have
     matched), AND at least 2 independent systemic risk signals
     (R006-R009) are satisfied.

  5. WATCH -- R012: no observed retinal progression AND at least 2
     systemic risk signals are satisfied, regardless of whether
     retinopathy already exists (R010's more specific existing-DR
     condition is checked first, at step 4, so it takes precedence when it
     also applies).

  6. STABLE -- default V1 baseline. No progression, no insufficient-data
     condition, and fewer than 2 systemic signals. Supported by R005
     (Stable_Retinal_State) when the retinal trajectory itself is stable.
"""

from dataclasses import dataclass, field

from app.reasoning.rule_engine import UNEVALUATED_RULE_CLAUSES

STABLE = "STABLE"
WATCH = "WATCH"
INCREASING_CONCERN = "INCREASING_CONCERN"
HIGH_CONCERN = "HIGH_CONCERN"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

SYSTEMIC_SIGNAL_RULE_IDS = ("R006", "R007", "R008", "R009")


@dataclass(frozen=True)
class RiskAssessment:
    risk_state: str
    deciding_rule_ids: list = field(default_factory=list)
    precedence_step: int = 0
    precedence_reason: str = ""
    systemic_signal_count: int = 0
    systemic_signals: dict = field(default_factory=dict)
    operational_notes: list = field(default_factory=list)


def _signal_dict(rule_evaluations: dict) -> dict:
    return {
        rule_id: {
            "satisfied": rule_evaluations[rule_id].satisfied,
            "output_concept": rule_evaluations[rule_id].output_concept,
            "reason": rule_evaluations[rule_id].reason,
        }
        for rule_id in SYSTEMIC_SIGNAL_RULE_IDS
        if rule_id in rule_evaluations
    }


def _signal_count(rule_evaluations: dict) -> int:
    return sum(1 for rule_id in SYSTEMIC_SIGNAL_RULE_IDS if rule_evaluations.get(rule_id) and rule_evaluations[rule_id].satisfied)


def aggregate_risk_state(profile, rule_evaluations: dict) -> RiskAssessment:
    trajectory = profile.retinal_trajectory
    signal_count = _signal_count(rule_evaluations)
    signals = _signal_dict(rule_evaluations)
    operational_notes = list(UNEVALUATED_RULE_CLAUSES.values())

    common = dict(
        systemic_signal_count=signal_count,
        systemic_signals=signals,
        operational_notes=operational_notes,
    )

    r013 = rule_evaluations["R013"]
    if r013.satisfied:
        return RiskAssessment(
            risk_state=INSUFFICIENT_DATA,
            deciding_rule_ids=["R013"],
            precedence_step=1,
            precedence_reason=r013.reason,
            **common,
        )

    if trajectory.n_observed < 2:
        return RiskAssessment(
            risk_state=INSUFFICIENT_DATA,
            deciding_rule_ids=[],
            precedence_step=2,
            precedence_reason=(
                "A retinal observation exists at the latest visit, but there is "
                "no prior observation to compare it against, so no trajectory "
                "can be determined. Documented extension beyond rules.csv's "
                "literal R013 condition; not attributed to any rules.csv rule_id."
            ),
            **common,
        )

    r003 = rule_evaluations["R003"]
    r004 = rule_evaluations["R004"]
    r011 = rule_evaluations["R011"]
    if r011.satisfied:
        deciding = ["R011"]
        deciding += ["R003"] if r003.satisfied else []
        deciding += ["R004"] if r004.satisfied else []
        return RiskAssessment(
            risk_state=HIGH_CONCERN,
            deciding_rule_ids=deciding,
            precedence_step=3,
            precedence_reason=r011.reason,
            **common,
        )

    r010 = rule_evaluations["R010"]
    if r010.satisfied:
        return RiskAssessment(
            risk_state=INCREASING_CONCERN,
            deciding_rule_ids=["R010"],
            precedence_step=4,
            precedence_reason=r010.reason,
            **common,
        )

    r012 = rule_evaluations["R012"]
    if r012.satisfied:
        return RiskAssessment(
            risk_state=WATCH,
            deciding_rule_ids=["R012"],
            precedence_step=5,
            precedence_reason=r012.reason,
            **common,
        )

    r005 = rule_evaluations["R005"]
    return RiskAssessment(
        risk_state=STABLE,
        deciding_rule_ids=["R005"] if r005.satisfied else [],
        precedence_step=6,
        precedence_reason=(
            "No retinal progression, no insufficient-data condition, and fewer "
            "than 2 systemic risk signals; default V1 baseline state."
        ),
        **common,
    )
