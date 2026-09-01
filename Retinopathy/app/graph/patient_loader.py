"""Deterministic loader for the Temporal Patient Graph.

Loads synthetic_cases.json into Neo4j as:

    (:Patient)-[:HAS_VISIT]->(:Visit)-[:HAS_MEASUREMENT]->(:Measurement)-[:INSTANCE_OF]->(:Concept)

Retinal-stage measurements additionally link to their specific Retinal_State
concept via OBSERVED_STATE (e.g. Mild_NPDR), on top of the same INSTANCE_OF
link to the general Retinopathy_Stage concept that every other measurement
uses. This is a Temporal Patient Graph plumbing edge, not a new clinical
relationship, so it needs no evidence provenance.

Rules preserved deliberately:
- A null value for any timeline field means "not observed" -- no
  Measurement node is created for it. This applies uniformly, including to
  retinal_stage: a missing retinal exam produces no Retinopathy_Stage
  Measurement, never a fabricated No_DR observation.
- retinal_stage is stored as stage_index (int) + stage_label (str), never
  merged into the generic numeric `value` property used by other
  measurements, so it cannot accidentally be fed into numeric trend math.
- Dates are taken verbatim from synthetic_cases.json; nothing is
  interpolated, reordered, or backfilled.

This is the Temporal Patient Graph only. It does not compute derived
features, risk states, or rules -- that is a later step.
"""

from pathlib import Path

from neo4j import Session

from app.graph.connection import neo4j_session
from app.graph.csv_validation import ROOT_DIR, load_csv_rows
from app.graph.patient_validation import (
    FIELD_TO_CONCEPT,
    RETINAL_STAGE_CONCEPT,
    STAGE_INDEX_TO_CONCEPT,
    load_synthetic_cases,
    validate_synthetic_cases,
)

CONSTRAINTS = [
    "CREATE CONSTRAINT patient_id_unique IF NOT EXISTS "
    "FOR (p:Patient) REQUIRE p.patient_id IS UNIQUE",
]

MERGE_PATIENT = """
MERGE (p:Patient {patient_id: $patient_id})
SET p.age = $age,
    p.sex = $sex,
    p.height_cm = $height_cm,
    p.puberty_status = $puberty_status,
    p.t1d_diagnosis = date($t1d_diagnosis),
    p.description = $description,
    p.synthetic_expected_risk_state = $expected_risk_state
"""

MERGE_VISITS = """
UNWIND $dates AS visit_date
MATCH (p:Patient {patient_id: $patient_id})
MERGE (v:Visit {patient_id: $patient_id, date: date(visit_date)})
MERGE (p)-[:HAS_VISIT]->(v)
"""

MERGE_NUMERIC_MEASUREMENTS = """
UNWIND $rows AS row
MATCH (v:Visit {patient_id: $patient_id, date: date(row.date)})
MATCH (c:Concept {name: row.concept})
MERGE (m:Measurement {patient_id: $patient_id, date: date(row.date), concept: row.concept})
SET m.value = row.value
MERGE (v)-[:HAS_MEASUREMENT]->(m)
MERGE (m)-[:INSTANCE_OF]->(c)
"""

MERGE_RETINAL_MEASUREMENTS = """
UNWIND $rows AS row
MATCH (v:Visit {patient_id: $patient_id, date: date(row.date)})
MATCH (c:Concept {name: row.concept})
MATCH (state:Concept {name: row.stage_concept})
MERGE (m:Measurement {patient_id: $patient_id, date: date(row.date), concept: row.concept})
SET m.stage_index = row.stage_index,
    m.stage_label = row.stage_concept
MERGE (v)-[:HAS_MEASUREMENT]->(m)
MERGE (m)-[:INSTANCE_OF]->(c)
MERGE (m)-[:OBSERVED_STATE]->(state)
"""


class PatientValidationError(RuntimeError):
    pass


def ensure_constraints(session: Session) -> None:
    for statement in CONSTRAINTS:
        session.run(statement)


def build_case_rows(case: dict) -> dict:
    """Turn one synthetic_cases.json case into loader-ready rows.

    Fields with a null (or absent) value are skipped entirely -- they are
    not observed, not zero, not "No DR".
    """
    dates = [visit["date"] for visit in case["timeline"]]

    numeric_rows = []
    for visit in case["timeline"]:
        for field_name, concept in FIELD_TO_CONCEPT.items():
            value = visit.get(field_name)
            if value is not None:
                numeric_rows.append({"date": visit["date"], "concept": concept, "value": value})

    retinal_rows = []
    for visit in case["timeline"]:
        stage = visit.get("retinal_stage")
        if stage is not None:
            retinal_rows.append(
                {
                    "date": visit["date"],
                    "concept": RETINAL_STAGE_CONCEPT,
                    "stage_index": stage,
                    "stage_concept": STAGE_INDEX_TO_CONCEPT[stage],
                }
            )

    return {"dates": dates, "numeric_rows": numeric_rows, "retinal_rows": retinal_rows}


def load_case_into_session(session: Session, case: dict) -> dict:
    session.run(
        MERGE_PATIENT,
        patient_id=case["id"],
        age=case["age"],
        sex=case["sex"],
        height_cm=case["height_cm"],
        puberty_status=case["puberty_status"],
        t1d_diagnosis=case["t1d_diagnosis"],
        description=case.get("description"),
        expected_risk_state=case.get("expected_risk_state"),
    )

    rows = build_case_rows(case)

    session.run(MERGE_VISITS, patient_id=case["id"], dates=rows["dates"])
    session.run(MERGE_NUMERIC_MEASUREMENTS, patient_id=case["id"], rows=rows["numeric_rows"])
    session.run(MERGE_RETINAL_MEASUREMENTS, patient_id=case["id"], rows=rows["retinal_rows"])

    return {
        "patient_id": case["id"],
        "visits": len(rows["dates"]),
        "numeric_measurements": len(rows["numeric_rows"]),
        "retinal_measurements": len(rows["retinal_rows"]),
    }


def load_patients(
    root_dir: Path = ROOT_DIR,
    data: dict | None = None,
) -> list[dict]:
    """Validate and load all patient cases. Raises PatientValidationError
    and writes nothing if validation fails.
    """
    if data is None:
        data = load_synthetic_cases(root_dir)

    known_concept_names = {row["name"] for row in load_csv_rows(root_dir)["nodes"]}
    validation = validate_synthetic_cases(data, known_concept_names)
    if not validation.is_valid:
        raise PatientValidationError(f"synthetic_cases.json validation failed: {validation}")

    with neo4j_session() as session:
        ensure_constraints(session)
        return [load_case_into_session(session, case) for case in data["cases"]]
