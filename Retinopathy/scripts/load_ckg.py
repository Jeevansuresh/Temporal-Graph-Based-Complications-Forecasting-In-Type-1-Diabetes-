"""CLI entrypoint: load the Clinical Knowledge Graph and print a read-back
verification (counts + representative relationships/evidence links).

Usage (from Retinopathy/):
    python scripts/load_ckg.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.graph.ckg_loader import CkgValidationError, load_ckg
from app.graph.connection import neo4j_session

READ_BACK_COUNTS = """
MATCH (c:Concept) WITH count(c) AS concepts
MATCH (e:Evidence) WITH concepts, count(e) AS evidence
MATCH (ru:Rule) WITH concepts, evidence, count(ru) AS rules
MATCH ()-[r:CLINICAL_RELATIONSHIP]->() WITH concepts, evidence, rules, count(r) AS relationships
MATCH ()-[p:PRODUCES]->() WITH concepts, evidence, rules, relationships, count(p) AS produces
MATCH ()-[s:SUPPORTED_BY]->() RETURN concepts, evidence, rules, relationships, produces, count(s) AS supported_by
"""

SAMPLE_RELATIONSHIPS = """
MATCH (s:Concept)-[r:CLINICAL_RELATIONSHIP]->(o:Concept)
RETURN s.name AS subject, r.relation AS relation, o.name AS object,
       r.evidence_id AS evidence_id, r.evidence_strength AS evidence_strength
ORDER BY s.name
LIMIT 5
"""

SAMPLE_RULE_EVIDENCE = """
MATCH (ru:Rule)-[:SUPPORTED_BY]->(e:Evidence)
RETURN ru.rule_id AS rule_id, e.evidence_id AS evidence_id, e.evidence_strength AS evidence_strength
ORDER BY ru.rule_id
LIMIT 5
"""


def main() -> int:
    try:
        summary = load_ckg()
    except CkgValidationError as exc:
        print("CKG LOAD ABORTED - validation failed")
        print(exc)
        return 1

    print("CKG LOAD SUMMARY (rows processed)")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    with neo4j_session() as session:
        counts = session.run(READ_BACK_COUNTS).single()
        print("\nREAD-BACK COUNTS (Neo4j)")
        for key in counts.keys():
            print(f"  {key}: {counts[key]}")

        print("\nSAMPLE CLINICAL_RELATIONSHIP EDGES")
        for record in session.run(SAMPLE_RELATIONSHIPS):
            print(
                f"  ({record['subject']}) -[{record['relation']}]-> ({record['object']})"
                f"  evidence_id={record['evidence_id']} strength={record['evidence_strength']}"
            )

        print("\nSAMPLE Rule -> Evidence LINKS")
        for record in session.run(SAMPLE_RULE_EVIDENCE):
            print(
                f"  {record['rule_id']} -[SUPPORTED_BY]-> {record['evidence_id']}"
                f"  strength={record['evidence_strength']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
