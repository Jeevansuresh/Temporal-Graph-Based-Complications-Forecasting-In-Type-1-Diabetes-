"""Operational clinical reference standards used to evaluate the
qualitative reference-range/status clauses in rules.csv (R007-R009).

WHY THIS FILE EXISTS AND IS SEPARATE FROM THE CKG
--------------------------------------------------
rules.csv deliberately writes some clauses in plain clinical language
without a number: "elevated pediatric-contextualized BP status",
"Dyslipidemia present", "Persistent albuminuria". A clinician evaluating
these in practice would apply well-known external reference values (an
albuminuria cutoff, a pediatric lipid goal, an age-based BP category).
Those numbers are NOT in rules.csv or evidence.csv/evidence_audit.csv, and
this module does not add them there, rewrite them, or claim they are part
of this repository's own evidence base. This is a separate, clearly
labeled "operationalization layer" that the rule engine (rule_engine.py)
consults only for the specific clauses named below. The Clinical Knowledge
Graph's own relationship/rule provenance (evidence_id -> evidence.csv/
evidence_audit.csv) is untouched and remains the sole source of *clinical
relationships*.

EPISTEMIC CAVEAT
----------------
The values below reflect long-standing, stable conventions from named
organizations (ADA Standards of Care; the AAP/AHA pediatric BP guideline
that ADA's own pediatric section references) that have been consistent
across many consecutive guideline editions. Their exact wording in the
specific "ADA Standards of Care in Diabetes-2026" document cited elsewhere
in this repo's evidence.csv has not been independently verified against
source text in this session -- these are cited as the general, current
standard of practice, not as a verbatim quotation from a specific page.

WHAT IS DELIBERATELY *NOT* HERE
--------------------------------
- No numeric HbA1c "high exposure" or "high variability" cutoff: ADA's
  pediatric glycemic target is explicitly individualized (no single
  bright-line number), and no HbA1c-variability threshold is documented
  anywhere in this repo's evidence base.
- No eGFR percentage-decline cutoff: per explicit build instruction, no
  longitudinal eGFR decline percentage is invented. eGFR trend stays
  descriptive only (see app/temporal/numeric_features.py) and does not
  independently operationalize any rule here.
- No single pediatric BP cutoff for children under the adult-category
  cutover age: age/sex/height percentile tables would be required, and
  those tables are not available as data in this repository.
"""

from dataclasses import dataclass

# ADA-defined elevated ("moderately increased") albuminuria threshold.
# Operationalizes R009's "Persistent albuminuria" clause. R009 requires
# *persistence*, so the rule engine additionally requires >=2 observations
# at/above this value (consistent with ADA's own recommendation to confirm
# elevated UACR across repeated samples), not a single reading.
ADA_ELEVATED_UACR_MG_PER_G = 30

# ADA pediatric type 1 diabetes LDL treatment goal. Operationalizes R008's
# "Dyslipidemia present" clause (latest LDL at/above goal).
ADA_PEDIATRIC_T1D_LDL_GOAL_MG_DL = 100

# Age at which pediatric BP interpretation switches from age/sex/height
# percentile tables to adult BP categories (AAP 2017 pediatric BP
# guideline convention, referenced by ADA's pediatric section). Below this
# age, BP status is not classified in this build (no percentile table
# available as repository data).
PEDIATRIC_ADULT_BP_CATEGORY_AGE_YEARS = 13

# Adult "elevated BP or higher" category boundary (>= either value).
# Operationalizes R007's "elevated ... BP status" clause for patients at
# or above the adult-category cutover age. R007 requires "repeated", so
# the rule engine additionally requires >=2 qualifying observations.
ELEVATED_SBP_MMHG = 120
ELEVATED_DBP_MMHG = 80


@dataclass(frozen=True)
class ClinicalReferenceStandard:
    standard_id: str
    source_name: str
    publication_version: str
    exact_threshold: str
    population_context: str
    unit: str
    operationalizes_rule_clause: str


CLINICAL_REFERENCE_STANDARDS = [
    ClinicalReferenceStandard(
        standard_id="REF001",
        source_name="American Diabetes Association, Standards of Care in Diabetes",
        publication_version="2026 edition (current ADA Standards of Care; exact "
        "section wording not independently verified in this session -- see "
        "epistemic caveat in this module's docstring)",
        exact_threshold=f"UACR >= {ADA_ELEVATED_UACR_MG_PER_G}",
        population_context="People with diabetes; definition of elevated "
        "('moderately increased') albuminuria. Confirmation across >=2 samples "
        "is applied here to represent 'persistence'.",
        unit="mg/g creatinine",
        operationalizes_rule_clause="R009 'Persistent albuminuria'",
    ),
    ClinicalReferenceStandard(
        standard_id="REF002",
        source_name="American Diabetes Association, Standards of Care in Diabetes, "
        "Children and Adolescents section",
        publication_version="2026 edition (current ADA Standards of Care; exact "
        "section wording not independently verified in this session -- see "
        "epistemic caveat in this module's docstring)",
        exact_threshold=f"LDL >= {ADA_PEDIATRIC_T1D_LDL_GOAL_MG_DL}",
        population_context="Children/adolescents with type 1 diabetes; LDL "
        "cholesterol treatment goal.",
        unit="mg/dL",
        operationalizes_rule_clause="R008 'Dyslipidemia present' (evaluated on "
        "the latest LDL observation)",
    ),
    ClinicalReferenceStandard(
        standard_id="REF003",
        source_name="American Academy of Pediatrics / American Heart Association "
        "pediatric blood pressure guideline (2017), as referenced by ADA "
        "Standards of Care's pediatric section",
        publication_version="AAP 2017 Clinical Practice Guideline; ADA Standards "
        "of Care 2026 edition (exact wording not independently verified in this "
        "session -- see epistemic caveat in this module's docstring)",
        exact_threshold=(
            f"Age < {PEDIATRIC_ADULT_BP_CATEGORY_AGE_YEARS}: not classified in "
            "this build (age/sex/height percentile table not available as "
            f"repository data). Age >= {PEDIATRIC_ADULT_BP_CATEGORY_AGE_YEARS}: "
            f"'elevated or higher' = SBP >= {ELEVATED_SBP_MMHG} mmHg OR "
            f"DBP >= {ELEVATED_DBP_MMHG} mmHg (adult categories). 'Repeated' is "
            "applied here as >=2 qualifying observations."
        ),
        population_context="Children and adolescents with type 1 diabetes",
        unit="mmHg",
        operationalizes_rule_clause="R007 'Repeated elevated pediatric-"
        "contextualized BP status'",
    ),
]
