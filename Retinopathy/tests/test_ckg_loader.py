"""Tests for the CKG loader.

Idempotency tests require the live Neo4j instance (same as
tests/test_connection.py). Validation-guard tests use injected in-memory
rows and never touch Neo4j.
"""

import pytest

from app.graph.ckg_loader import CkgValidationError, build_evidence_records, load_ckg
from app.graph.connection import neo4j_session
from app.graph.csv_validation import load_csv_rows

READ_BACK_COUNTS = """
MATCH (c:Concept) WITH count(c) AS concepts
MATCH (e:Evidence) WITH concepts, count(e) AS evidence
MATCH (ru:Rule) WITH concepts, evidence, count(ru) AS rules
MATCH ()-[r:CLINICAL_RELATIONSHIP]->() WITH concepts, evidence, rules, count(r) AS relationships
MATCH ()-[p:PRODUCES]->() WITH concepts, evidence, rules, relationships, count(p) AS produces
MATCH ()-[s:SUPPORTED_BY]->() RETURN concepts, evidence, rules, relationships, produces, count(s) AS supported_by
"""


def _read_counts():
    with neo4j_session() as session:
        return dict(session.run(READ_BACK_COUNTS).single())


def test_load_ckg_is_idempotent():
    load_ckg()
    first_counts = _read_counts()

    load_ckg()
    second_counts = _read_counts()

    assert first_counts == second_counts


def test_load_ckg_refuses_missing_relationship_node_reference():
    rows = {
        "nodes": [{"name": "T1D", "id": "R01", "type": "Condition", "synonyms": "", "unit": "", "description": ""}],
        "relationships": [
            {
                "subject": "T1D",
                "relation": "associated_with",
                "object": "Nonexistent_Concept",
                "evidence_id": "C001",
                "population": "",
                "directionality": "",
                "evidence_strength": "",
            }
        ],
        "rules": [],
        "evidence": [],
        "evidence_audit": [
            {
                "claim_id": "C001",
                "claim_type": "",
                "clinical_claim": "",
                "source": "",
                "year": "",
                "source_type": "",
                "population": "",
                "identifier": "",
                "url": "",
                "audit_note": "",
            }
        ],
    }

    with pytest.raises(CkgValidationError):
        load_ckg(rows=rows)


def test_c010_merges_consistently_after_evidence_integrity_fix():
    # Regression test for the Milestone 2.5 evidence-id collision fix:
    # evidence.csv's C010 previously pointed to an unrelated pediatric
    # cohort study while evidence_audit.csv's C010 was the ICDR severity
    # classification cited by R003/R004/R005. Both sides of the merged
    # record must now agree.
    rows = load_csv_rows()
    records = {
        r["evidence_id"]: r
        for r in build_evidence_records(rows["evidence"], rows["evidence_audit"])
    }
    c010 = records["C010"]
    assert "severity" in c010["claim"].lower() or "ICDR" in c010["claim"]
    assert "ICDR" in c010["audit_clinical_claim"]


def test_load_ckg_refuses_missing_rule_evidence_reference():
    rows = {
        "nodes": [{"name": "Retinopathy_Risk", "id": "R32", "type": "Risk_State", "synonyms": "", "unit": "", "description": ""}],
        "relationships": [],
        "rules": [
            {
                "rule_id": "RX01",
                "trigger": "",
                "logical_condition": "",
                "temporal_requirement": "",
                "output_concept": "Retinopathy_Risk",
                "evidence_id": "C999",
            }
        ],
        "evidence": [],
        "evidence_audit": [],
    }

    with pytest.raises(CkgValidationError):
        load_ckg(rows=rows)
