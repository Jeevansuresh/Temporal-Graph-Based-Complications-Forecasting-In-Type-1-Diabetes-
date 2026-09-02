"""Pure validation for synthetic_cases.json (the Temporal Patient Graph source).

No Neo4j access happens here. Every observation field is checked against
the concept names already present in nodes.csv (the CKG), so the patient
loader can never write a Measurement pointing at a concept that doesn't
exist in the Clinical Knowledge Graph.
"""

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

# Maps synthetic_cases.json numeric timeline fields to CKG Concept names.
FIELD_TO_CONCEPT = {
    "hba1c": "HbA1c",
    "sbp": "Systolic_BP",
    "dbp": "Diastolic_BP",
    "ldl": "LDL",
    "uacr": "UACR",
    "egfr": "eGFR",
}

# Fixed ICDR retinal severity classification (matches nodes.csv R23-R28 and
# the schema.retinal_stage block embedded in synthetic_cases.json itself).
RETINAL_STAGE_CONCEPT = "Retinopathy_Stage"
STAGE_INDEX_TO_CONCEPT = {
    0: "No_DR",
    1: "Mild_NPDR",
    2: "Moderate_NPDR",
    3: "Severe_NPDR",
    4: "PDR",
}

REQUIRED_CASE_FIELDS = {
    "id",
    "age",
    "sex",
    "height_cm",
    "puberty_status",
    "t1d_diagnosis",
    "timeline",
}


def load_synthetic_cases(root_dir: Path = ROOT_DIR) -> dict:
    with open(root_dir / "synthetic_cases.json", encoding="utf-8") as f:
        return json.load(f)


@dataclass(frozen=True)
class PatientValidationResult:
    missing_top_level_keys: list[str] = field(default_factory=list)
    duplicate_patient_ids: list[str] = field(default_factory=list)
    cases_missing_fields: list[str] = field(default_factory=list)
    invalid_dates: list[str] = field(default_factory=list)
    invalid_retinal_stage: list[str] = field(default_factory=list)
    unmapped_concepts: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(
            (
                self.missing_top_level_keys,
                self.duplicate_patient_ids,
                self.cases_missing_fields,
                self.invalid_dates,
                self.invalid_retinal_stage,
                self.unmapped_concepts,
            )
        )


def _is_valid_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def validate_synthetic_cases(
    data: dict, known_concept_names: set[str]
) -> PatientValidationResult:
    missing_top_level_keys = [key for key in ("schema", "cases") if key not in data]
    if missing_top_level_keys:
        return PatientValidationResult(missing_top_level_keys=missing_top_level_keys)

    duplicate_patient_ids: list[str] = []
    cases_missing_fields: list[str] = []
    invalid_dates: list[str] = []
    invalid_retinal_stage: list[str] = []

    seen_ids: set[str] = set()

    # Concepts this loader will ever try to attach to a Measurement.
    referenced_concepts = set(FIELD_TO_CONCEPT.values()) | {RETINAL_STAGE_CONCEPT} | set(
        STAGE_INDEX_TO_CONCEPT.values()
    )
    unmapped_concepts = sorted(referenced_concepts - known_concept_names)

    for case in data["cases"]:
        case_id = case.get("id", "<missing id>")

        missing = REQUIRED_CASE_FIELDS - case.keys()
        if missing:
            cases_missing_fields.append(f"{case_id}: missing {sorted(missing)}")
            continue

        if case_id in seen_ids:
            duplicate_patient_ids.append(case_id)
        seen_ids.add(case_id)

        if not _is_valid_iso_date(case["t1d_diagnosis"]):
            invalid_dates.append(f"{case_id}: t1d_diagnosis={case['t1d_diagnosis']!r}")

        for visit in case["timeline"]:
            if "date" not in visit or not _is_valid_iso_date(visit["date"]):
                invalid_dates.append(f"{case_id}: visit date={visit.get('date')!r}")

            if "retinal_stage" in visit and visit["retinal_stage"] is not None:
                stage = visit["retinal_stage"]
                if stage not in STAGE_INDEX_TO_CONCEPT:
                    invalid_retinal_stage.append(
                        f"{case_id}@{visit.get('date')}: retinal_stage={stage!r}"
                    )

    return PatientValidationResult(
        missing_top_level_keys=missing_top_level_keys,
        duplicate_patient_ids=duplicate_patient_ids,
        cases_missing_fields=cases_missing_fields,
        invalid_dates=invalid_dates,
        invalid_retinal_stage=invalid_retinal_stage,
        unmapped_concepts=unmapped_concepts,
    )
