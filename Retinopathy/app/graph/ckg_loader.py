"""Deterministic loader for the Retinopathy Clinical Knowledge Graph (CKG).

Loads nodes.csv, relationships.csv, rules.csv, evidence.csv, and
evidence_audit.csv into Neo4j as:

    (:Concept {name, id, type, synonyms, unit, description})
    (:Evidence {evidence_id, ...citation fields..., ...audit fields...})
    (:Concept)-[:CLINICAL_RELATIONSHIP {relation, evidence_id, population,
        directionality, evidence_strength}]->(:Concept)
    (:Rule {rule_id, trigger, logical_condition, temporal_requirement})
    (:Rule)-[:PRODUCES]->(:Concept)
    (:Rule)-[:SUPPORTED_BY]->(:Evidence)

This is the Clinical Knowledge Graph only. It does not touch patient,
visit, or observation data (the Temporal Patient Graph is a separate
concern, loaded elsewhere), and it does not add any relationship or rule
beyond what the CSVs already contain.

All writes are MERGE-based and safe to rerun.
"""

import subprocess
import sys
from pathlib import Path

from neo4j import Session

from app.graph.connection import neo4j_session
from app.graph.csv_validation import ROOT_DIR, load_csv_rows, validate_references

CONSTRAINTS = [
    "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS "
    "FOR (c:Concept) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS "
    "FOR (e:Evidence) REQUIRE e.evidence_id IS UNIQUE",
    "CREATE CONSTRAINT rule_id_unique IF NOT EXISTS "
    "FOR (r:Rule) REQUIRE r.rule_id IS UNIQUE",
]

LOAD_CONCEPTS = """
UNWIND $rows AS row
MERGE (c:Concept {name: row.name})
SET c.id = row.id,
    c.type = row.type,
    c.synonyms = row.synonyms,
    c.unit = row.unit,
    c.description = row.description
"""

LOAD_EVIDENCE = """
UNWIND $rows AS row
MERGE (e:Evidence {evidence_id: row.evidence_id})
SET e += row
"""

LOAD_RELATIONSHIPS = """
UNWIND $rows AS row
MATCH (s:Concept {name: row.subject})
MATCH (o:Concept {name: row.object})
MERGE (s)-[r:CLINICAL_RELATIONSHIP {relation: row.relation}]->(o)
SET r.evidence_id = row.evidence_id,
    r.population = row.population,
    r.directionality = row.directionality,
    r.evidence_strength = row.evidence_strength
"""

LOAD_RULES = """
UNWIND $rows AS row
MERGE (ru:Rule {rule_id: row.rule_id})
SET ru.trigger = row.trigger,
    ru.logical_condition = row.logical_condition,
    ru.temporal_requirement = row.temporal_requirement
WITH ru, row
MATCH (out:Concept {name: row.output_concept})
MERGE (ru)-[:PRODUCES]->(out)
"""

LOAD_RULE_EVIDENCE = """
UNWIND $pairs AS pair
MATCH (ru:Rule {rule_id: pair.rule_id})
MATCH (e:Evidence {evidence_id: pair.evidence_id})
MERGE (ru)-[:SUPPORTED_BY]->(e)
"""


class CkgValidationError(RuntimeError):
    pass


def run_preflight_validate_kg(root_dir: Path = ROOT_DIR) -> None:
    """Run the existing validate_kg.py script and require exit code 0."""
    result = subprocess.run(
        [sys.executable, str(root_dir / "validate_kg.py")],
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise CkgValidationError(
            "validate_kg.py failed (exit "
            f"{result.returncode}):\n{result.stdout}\n{result.stderr}"
        )


def build_evidence_records(evidence: list[dict], evidence_audit: list[dict]) -> list[dict]:
    """Merge evidence.csv and evidence_audit.csv rows keyed by id.

    Fields are kept distinct (not overwritten) so both the citation-facing
    view and the audit-trail view are preserved exactly.
    """
    by_id: dict[str, dict] = {}

    for row in evidence:
        by_id.setdefault(row["evidence_id"], {"evidence_id": row["evidence_id"]})
        record = by_id[row["evidence_id"]]
        record["citation"] = row["citation"]
        record["year"] = row["year"]
        record["source_type"] = row["source_type"]
        record["population"] = row["population"]
        record["identifier"] = row["identifier"]
        record["url"] = row["url"]
        record["claim"] = row["claim"]
        record["evidence_strength"] = row["evidence_strength"]

    for row in evidence_audit:
        by_id.setdefault(row["claim_id"], {"evidence_id": row["claim_id"]})
        record = by_id[row["claim_id"]]
        record["audit_claim_type"] = row["claim_type"]
        record["audit_clinical_claim"] = row["clinical_claim"]
        record["audit_source"] = row["source"]
        record["audit_year"] = row["year"]
        record["audit_source_type"] = row["source_type"]
        record["audit_population"] = row["population"]
        record["audit_identifier"] = row["identifier"]
        record["audit_url"] = row["url"]
        record["audit_note"] = row["audit_note"]

    return list(by_id.values())


def build_rule_evidence_pairs(rules: list[dict]) -> list[dict]:
    pairs = []
    for row in rules:
        for eid in (row["evidence_id"] or "").split("/"):
            eid = eid.strip()
            if eid:
                pairs.append({"rule_id": row["rule_id"], "evidence_id": eid})
    return pairs


def ensure_constraints(session: Session) -> None:
    for statement in CONSTRAINTS:
        session.run(statement)


def load_ckg_into_session(session: Session, rows: dict[str, list[dict]]) -> dict[str, int]:
    ensure_constraints(session)

    session.run(LOAD_CONCEPTS, rows=rows["nodes"])

    evidence_records = build_evidence_records(rows["evidence"], rows["evidence_audit"])
    session.run(LOAD_EVIDENCE, rows=evidence_records)

    session.run(LOAD_RELATIONSHIPS, rows=rows["relationships"])

    session.run(LOAD_RULES, rows=rows["rules"])
    rule_evidence_pairs = build_rule_evidence_pairs(rows["rules"])
    session.run(LOAD_RULE_EVIDENCE, pairs=rule_evidence_pairs)

    return {
        "nodes": len(rows["nodes"]),
        "evidence": len(evidence_records),
        "relationships": len(rows["relationships"]),
        "rules": len(rows["rules"]),
        "rule_evidence_pairs": len(rule_evidence_pairs),
    }


def load_ckg(
    root_dir: Path = ROOT_DIR,
    rows: dict[str, list[dict]] | None = None,
    run_preflight: bool = True,
) -> dict[str, int]:
    """Validate and load the CKG. Raises CkgValidationError and writes
    nothing if validation fails.

    `rows` may be injected (e.g. in tests) to bypass reading from disk;
    in that case `run_preflight` (which shells out to validate_kg.py
    against the real CSV files) is skipped automatically.
    """
    if rows is None:
        if run_preflight:
            run_preflight_validate_kg(root_dir)
        rows = load_csv_rows(root_dir)
    else:
        run_preflight = False

    validation = validate_references(
        rows["nodes"], rows["relationships"], rows["rules"], rows["evidence_audit"]
    )
    if not validation.is_valid:
        raise CkgValidationError(f"CSV reference validation failed: {validation}")

    with neo4j_session() as session:
        return load_ckg_into_session(session, rows)
