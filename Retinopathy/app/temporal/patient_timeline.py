"""Read-side access to the Temporal Patient Graph.

Counterpart to app/graph/patient_loader.py: reconstructs a patient's
chronological visit timeline from Neo4j, preserving observation dates and
temporal ordering exactly as stored. Computes no trend features -- see
app/temporal/numeric_features.py and app/temporal/retinal_trajectory.py.

The only derived value computed here is T1D_Duration (years since
t1d_diagnosis at each visit date): plain calendar arithmetic from data
already on the Patient node, not an inferred clinical value.
"""

from dataclasses import dataclass, field
from datetime import date as date_cls

from app.graph.connection import neo4j_session

PATIENT_TIMELINE_QUERY = """
MATCH (p:Patient {patient_id: $patient_id})
OPTIONAL MATCH (p)-[:HAS_VISIT]->(v:Visit)
OPTIONAL MATCH (v)-[:HAS_MEASUREMENT]->(m:Measurement)-[:INSTANCE_OF]->(c:Concept)
RETURN p.patient_id AS patient_id, p.age AS age, p.sex AS sex,
       p.height_cm AS height_cm, p.puberty_status AS puberty_status,
       p.t1d_diagnosis AS t1d_diagnosis,
       v.date AS visit_date, c.name AS concept, m.value AS value,
       m.stage_index AS stage_index
ORDER BY v.date
"""


@dataclass(frozen=True)
class Visit:
    date: str
    measurements: dict = field(default_factory=dict)  # concept name -> numeric value
    retinal_stage_index: int | None = None
    t1d_duration_years: float | None = None


@dataclass(frozen=True)
class PatientTimeline:
    patient_id: str
    age: int | None
    sex: str | None
    height_cm: float | None
    puberty_status: str | None
    t1d_diagnosis: str | None
    visits: list = field(default_factory=list)  # list[Visit], chronological


def _to_native_date(value):
    return value.to_native() if hasattr(value, "to_native") else value


def _years_between(start: date_cls, end: date_cls) -> float:
    return round((end - start).days / 365.25, 2)


def load_patient_timeline(patient_id: str) -> PatientTimeline:
    with neo4j_session() as session:
        records = list(session.run(PATIENT_TIMELINE_QUERY, patient_id=patient_id))

    if not records or records[0]["patient_id"] is None:
        raise ValueError(f"No patient found with patient_id={patient_id!r}")

    patient_context = records[0]
    t1d_diagnosis = _to_native_date(patient_context["t1d_diagnosis"])

    visits_by_date: dict = {}
    for record in records:
        visit_date = _to_native_date(record["visit_date"])
        if visit_date is None:
            continue
        visit_date_str = visit_date.isoformat()
        visit_data = visits_by_date.setdefault(
            visit_date_str, {"measurements": {}, "retinal_stage_index": None}
        )
        concept = record["concept"]
        if concept is None:
            continue
        if concept == "Retinopathy_Stage":
            visit_data["retinal_stage_index"] = record["stage_index"]
        else:
            visit_data["measurements"][concept] = record["value"]

    visits = []
    for visit_date_str in sorted(visits_by_date):
        data = visits_by_date[visit_date_str]
        duration = (
            _years_between(t1d_diagnosis, date_cls.fromisoformat(visit_date_str))
            if t1d_diagnosis is not None
            else None
        )
        visits.append(
            Visit(
                date=visit_date_str,
                measurements=data["measurements"],
                retinal_stage_index=data["retinal_stage_index"],
                t1d_duration_years=duration,
            )
        )

    return PatientTimeline(
        patient_id=patient_context["patient_id"],
        age=patient_context["age"],
        sex=patient_context["sex"],
        height_cm=patient_context["height_cm"],
        puberty_status=patient_context["puberty_status"],
        t1d_diagnosis=t1d_diagnosis.isoformat() if t1d_diagnosis is not None else None,
        visits=visits,
    )
