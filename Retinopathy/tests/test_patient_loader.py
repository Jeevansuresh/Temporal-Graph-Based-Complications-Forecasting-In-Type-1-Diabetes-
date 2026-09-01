"""Tests for the Temporal Patient Graph loader.

Idempotency and missing-data tests require the live Neo4j instance with the
CKG already loaded (Step 3), since Measurements link to existing Concepts.
The validation-guard test uses injected in-memory data and never writes.
"""

import pytest

from app.graph.connection import neo4j_session
from app.graph.patient_loader import PatientValidationError, load_patients

READ_BACK_COUNTS = """
MATCH (p:Patient) WITH count(p) AS patients
MATCH (v:Visit) WITH patients, count(v) AS visits
MATCH (m:Measurement) RETURN patients, visits, count(m) AS measurements
"""


def _read_counts():
    with neo4j_session() as session:
        return dict(session.run(READ_BACK_COUNTS).single())


def test_load_patients_is_idempotent():
    load_patients()
    first_counts = _read_counts()

    load_patients()
    second_counts = _read_counts()

    assert first_counts == second_counts
    assert first_counts["patients"] == 5


def test_load_patients_refuses_data_referencing_unknown_concept():
    # No CKG concept named "Not_A_Real_Concept" exists; the loader must
    # never map an observation to it, so validation must fail first.
    data = {
        "schema": {},
        "cases": [
            {
                "id": "P999",
                "age": 10,
                "sex": "F",
                "height_cm": 140,
                "puberty_status": "not_started",
                "t1d_diagnosis": "2020-01-01",
                "timeline": [{"date": "2024-01-01", "retinal_stage": 99}],
            }
        ],
    }

    with pytest.raises(PatientValidationError):
        load_patients(data=data)

    with neo4j_session() as session:
        record = session.run(
            "MATCH (p:Patient {patient_id: 'P999'}) RETURN count(p) AS n"
        ).single()
        assert record["n"] == 0


def test_missing_retinal_observation_is_not_fabricated():
    load_patients()

    with neo4j_session() as session:
        rows = list(
            session.run(
                """
                MATCH (p:Patient {patient_id: 'P005'})-[:HAS_VISIT]->(v:Visit)
                OPTIONAL MATCH (v)-[:HAS_MEASUREMENT]->(m:Measurement {concept: 'Retinopathy_Stage'})
                RETURN v.date AS date, m.stage_index AS stage_index
                ORDER BY v.date
                """
            )
        )

    # P005 has retinal_stage 0 on its first visit and null on the next two.
    assert len(rows) == 3
    assert rows[0]["stage_index"] == 0
    assert rows[1]["stage_index"] is None
    assert rows[2]["stage_index"] is None
