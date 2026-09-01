"""Deterministic rule engine for rules.csv.

Loads rule definitions from rules.csv (the authoritative rule set -- never
modified or reinterpreted here) and evaluates each rule's logical_condition
against a PatientTemporalProfile (app/temporal/profile.py). Every
evaluation carries its rule_id, trigger, output_concept, and evidence_id(s)
straight through from rules.csv, unmodified.

Qualitative clauses that need an external reference range/status
("elevated BP status", "Dyslipidemia present", "persistent albuminuria")
are operationalized using app/reasoning/clinical_reference_standards.py --
a deliberately separate module, not rules.csv/evidence.csv content. See
UNEVALUATED_RULE_CLAUSES below for exactly which sub-clauses are, and are
not, evaluated, and why.
"""

from dataclasses import dataclass, field
from pathlib import Path

from app.graph.csv_validation import ROOT_DIR, load_csv_rows
from app.reasoning.clinical_reference_standards import (
    ADA_ELEVATED_UACR_MG_PER_G,
    ADA_PEDIATRIC_T1D_LDL_GOAL_MG_DL,
    ELEVATED_DBP_MMHG,
    ELEVATED_SBP_MMHG,
    PEDIATRIC_ADULT_BP_CATEGORY_AGE_YEARS,
)
from app.temporal.profile import PatientTemporalProfile
from app.temporal.retinal_trajectory import INCIDENT_PROGRESSION, PROGRESSION, STABLE

# Deliberately NOT operationalized -- see clinical_reference_standards.py
# for the full rationale. Surfaced in explanations so a reader can see what
# was intentionally left out, not silently dropped.
UNEVALUATED_RULE_CLAUSES = {
    "R006": (
        "\"high long-term HbA1c exposure\" and \"high HbA1c variability\" are not "
        "evaluated numerically: ADA's pediatric A1C target is explicitly "
        "individualized (no single bright-line cutoff), and no HbA1c-variability "
        "threshold is documented in this repo's evidence base. Only the "
        "threshold-free \"HbA1c slope > 0\" clause is evaluated."
    ),
    "R007": (
        f"Ages < {PEDIATRIC_ADULT_BP_CATEGORY_AGE_YEARS}: BP status is not "
        "classified -- AAP age/sex/height percentile tables are not available "
        "as data in this repository, and a single fixed cutoff would misapply "
        "adult/older-adolescent norms to younger children."
    ),
    "R009": (
        "eGFR trend does not independently trigger this signal. Per explicit "
        "instruction, no longitudinal eGFR percentage-decline cutoff is "
        "invented; eGFR trend remains descriptive only (see numeric_features). "
        "Only persistent UACR elevation (REF001) operationalizes this rule."
    ),
}


@dataclass(frozen=True)
class RuleEvaluation:
    rule_id: str
    trigger: str
    logical_condition: str
    temporal_requirement: str
    output_concept: str
    evidence_ids: list = field(default_factory=list)
    satisfied: bool = False
    reason: str = ""


def _split_evidence_ids(raw: str) -> list:
    return [part for part in (raw or "").split("/") if part]


def load_rule_definitions(root_dir: Path = ROOT_DIR) -> dict:
    rules = load_csv_rows(root_dir)["rules"]
    return {row["rule_id"]: row for row in rules}


# ---- R006-R009: systemic supporting signals ----------------------------
# Each returns (satisfied: bool, reason: str). These are RISK-FACTOR
# ASSOCIATION signals (relationships.csv), never a direct retinopathy
# observation -- see the explanation module's association-vs-observation
# note.

def evaluate_glycemic_risk_signal(profile: PatientTemporalProfile) -> tuple:
    hba1c = profile.numeric_features.get("HbA1c")
    if hba1c is None or hba1c.n_observations < 2:
        return False, "Insufficient HbA1c observations to assess trend."
    if hba1c.direction == "increasing":
        return True, f"HbA1c trend increasing ({hba1c.first_value} -> {hba1c.latest_value} %)."
    return False, f"HbA1c trend not increasing (direction={hba1c.direction})."


def evaluate_bp_risk_signal(profile: PatientTemporalProfile) -> tuple:
    age = profile.context.get("age")
    sbp = profile.numeric_features.get("Systolic_BP")
    dbp = profile.numeric_features.get("Diastolic_BP")

    if age is None or age < PEDIATRIC_ADULT_BP_CATEGORY_AGE_YEARS:
        return False, (
            f"Age ({age}) below {PEDIATRIC_ADULT_BP_CATEGORY_AGE_YEARS} years; "
            "pediatric percentile BP reference table not available in this "
            "build (REF003) -- BP status not classified."
        )
    if sbp is None or dbp is None or sbp.n_observations == 0:
        return False, "No BP observations available."

    elevated_count = sum(
        1
        for s, d in zip(sbp.values, dbp.values)
        if s >= ELEVATED_SBP_MMHG or d >= ELEVATED_DBP_MMHG
    )
    satisfied = elevated_count >= 2
    return satisfied, (
        f"{elevated_count} of {len(sbp.values)} BP observations at/above the "
        f"adult-category elevated threshold ({ELEVATED_SBP_MMHG}/{ELEVATED_DBP_MMHG} "
        f"mmHg, REF003); 'repeated' requires >=2."
    )


def evaluate_lipid_risk_signal(profile: PatientTemporalProfile) -> tuple:
    ldl = profile.numeric_features.get("LDL")
    if ldl is None or ldl.latest_value is None:
        return False, "No LDL observations available."
    satisfied = ldl.latest_value >= ADA_PEDIATRIC_T1D_LDL_GOAL_MG_DL
    return satisfied, (
        f"Latest LDL {ldl.latest_value} mg/dL vs ADA pediatric T1D goal "
        f"< {ADA_PEDIATRIC_T1D_LDL_GOAL_MG_DL} mg/dL (REF002)."
    )


def evaluate_kidney_context_risk_signal(profile: PatientTemporalProfile) -> tuple:
    uacr = profile.numeric_features.get("UACR")
    if uacr is None or not uacr.values:
        return False, "No UACR observations available."
    elevated_count = sum(1 for v in uacr.values if v >= ADA_ELEVATED_UACR_MG_PER_G)
    satisfied = elevated_count >= 2
    return satisfied, (
        f"{elevated_count} of {len(uacr.values)} UACR observations "
        f">= {ADA_ELEVATED_UACR_MG_PER_G} mg/g (REF001); persistence requires "
        "confirmation across >=2 observations. eGFR trend is descriptive only "
        "and does not independently trigger this signal."
    )


def evaluate_all_rules(profile: PatientTemporalProfile, root_dir: Path = ROOT_DIR) -> dict:
    definitions = load_rule_definitions(root_dir)
    trajectory = profile.retinal_trajectory
    evaluations: dict = {}

    def make(rule_id: str, satisfied: bool, reason: str) -> None:
        d = definitions[rule_id]
        evaluations[rule_id] = RuleEvaluation(
            rule_id=rule_id,
            trigger=d["trigger"],
            logical_condition=d["logical_condition"],
            temporal_requirement=d["temporal_requirement"],
            output_concept=d["output_concept"],
            evidence_ids=_split_evidence_ids(d["evidence_id"]),
            satisfied=bool(satisfied),
            reason=reason,
        )

    # R001 Screening_Eligible
    duration = profile.numeric_features.get("T1D_Duration")
    age = profile.context.get("age")
    puberty = profile.context.get("puberty_status")
    duration_val = duration.latest_value if duration else None
    duration_ok = duration_val is not None and duration_val >= 3
    age_or_puberty_ok = (age is not None and age >= 11) or (puberty == "started")
    initial_not_completed = trajectory.n_observed == 0
    make(
        "R001",
        duration_ok and age_or_puberty_ok and initial_not_completed,
        f"T1D_Duration={duration_val} yrs (>=3: {duration_ok}); age={age}, "
        f"puberty_status={puberty!r} (age>=11 or started: {age_or_puberty_ok}); "
        f"no prior retinal exam recorded: {initial_not_completed}.",
    )

    # R002 Screening_Due -- approximate; no evaluation-date reference exists
    # in this build distinct from visit dates, so exact "~2 years" timing is
    # not computed.
    has_initial = trajectory.n_observed >= 1
    due = bool(
        has_initial
        and not trajectory.latest_visit_has_observation
        and (trajectory.visits_since_last_observation or 0) >= 1
    )
    make(
        "R002",
        due,
        "Approximate: an initial exam exists and at least one subsequent visit "
        f"has no new exam (visits_since_last_observation="
        f"{trajectory.visits_since_last_observation}). Exact ~2-year timing is "
        "not computed -- no evaluation-date reference is modeled in this build.",
    )

    # R003 Incident_Retinopathy
    r003 = trajectory.overall_transition_type == INCIDENT_PROGRESSION
    make("R003", r003, f"overall_transition_type={trajectory.overall_transition_type}")

    # R004 Retinopathy_Progression (literal condition "current > previous" is
    # also true for the incident case)
    r004 = trajectory.overall_transition_type in (PROGRESSION, INCIDENT_PROGRESSION)
    make("R004", r004, f"overall_transition_type={trajectory.overall_transition_type}")

    # R005 Stable_Retinal_State
    r005 = trajectory.overall_transition_type == STABLE
    make("R005", r005, f"overall_transition_type={trajectory.overall_transition_type}")

    # R006-R009 systemic supporting signals
    glyc_ok, glyc_reason = evaluate_glycemic_risk_signal(profile)
    make("R006", glyc_ok, glyc_reason + " " + UNEVALUATED_RULE_CLAUSES["R006"])

    bp_ok, bp_reason = evaluate_bp_risk_signal(profile)
    make("R007", bp_ok, bp_reason + " " + UNEVALUATED_RULE_CLAUSES["R007"])

    lipid_ok, lipid_reason = evaluate_lipid_risk_signal(profile)
    make("R008", lipid_ok, lipid_reason)

    kidney_ok, kidney_reason = evaluate_kidney_context_risk_signal(profile)
    make("R009", kidney_ok, kidney_reason + " " + UNEVALUATED_RULE_CLAUSES["R009"])

    signal_count = sum([glyc_ok, bp_ok, lipid_ok, kidney_ok])

    # R010 INCREASING_CONCERN
    has_existing_dr = (
        trajectory.latest_observed_stage_index is not None
        and trajectory.latest_observed_stage_index > 0
    )
    make(
        "R010",
        has_existing_dr and signal_count >= 2,
        f"latest_observed_stage_index={trajectory.latest_observed_stage_index} "
        f"(>0: {has_existing_dr}); systemic_signal_count={signal_count} (>=2: "
        f"{signal_count >= 2}).",
    )

    # R011 HIGH_CONCERN
    make("R011", r003 or r004, f"R003 satisfied={r003} OR R004 satisfied={r004}.")

    # R012 WATCH
    no_progression = not (r003 or r004)
    make(
        "R012",
        no_progression and signal_count >= 2,
        f"no observed retinal progression={no_progression}; "
        f"systemic_signal_count={signal_count} (>=2: {signal_count >= 2}).",
    )

    # R013 INSUFFICIENT_DATA
    make(
        "R013",
        not trajectory.latest_visit_has_observation,
        f"latest_visit_has_observation={trajectory.latest_visit_has_observation}.",
    )

    return evaluations
