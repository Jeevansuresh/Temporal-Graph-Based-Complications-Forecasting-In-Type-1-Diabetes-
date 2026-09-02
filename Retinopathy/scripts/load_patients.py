"""CLI entrypoint: load synthetic_cases.json into the Temporal Patient Graph
and print a read-back verification (counts + representative observation
links). Requires the CKG (Step 3) to already be loaded, since every
Measurement links to an existing Concept.

Usage (from Retinopathy/):
    python scripts/load_patients.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.graph.connection import neo4j_session
from app.graph.patient_loader import PatientValidationError, load_patients

READ_BACK_COUNTS = """
MATCH (p:Patient) WITH count(p) AS patients
MATCH (v:Visit) WITH patients, count(v) AS visits
MATCH (m:Measurement) WITH patients, visits, count(m) AS measurements
MATCH (m2:Measurement {concept: "Retinopathy_Stage"})
RETURN patients, visits, measurements, count(m2) AS retinal_measurements
"""

SAMPLE_OBSERVATIONS = """
MATCH (p:Patient)-[:HAS_VISIT]->(v:Visit)-[:HAS_MEASUREMENT]->(m:Measurement)-[:INSTANCE_OF]->(c:Concept)
OPTIONAL MATCH (m)-[:OBSERVED_STATE]->(state:Concept)
RETURN p.patient_id AS patient_id, v.date AS date, c.name AS concept,
       m.value AS value, m.stage_index AS stage_index, state.name AS observed_state
ORDER BY p.patient_id, v.date, c.name
LIMIT 10
"""

MISSING_RETINAL_VISITS = """
MATCH (p:Patient)-[:HAS_VISIT]->(v:Visit)
WHERE NOT EXISTS {
    MATCH (v)-[:HAS_MEASUREMENT]->(:Measurement {concept: "Retinopathy_Stage"})
}
RETURN p.patient_id AS patient_id, v.date AS date
ORDER BY p.patient_id, v.date
"""


def main() -> int:
    try:
        summary = load_patients()
    except PatientValidationError as exc:
        print("PATIENT LOAD ABORTED - validation failed")
        print(exc)
        return 1

    print("PATIENT LOAD SUMMARY (per case)")
    for case in summary:
        print(
            f"  {case['patient_id']}: visits={case['visits']} "
            f"numeric_measurements={case['numeric_measurements']} "
            f"retinal_measurements={case['retinal_measurements']}"
        )

    with neo4j_session() as session:
        counts = session.run(READ_BACK_COUNTS).single()
        print("\nREAD-BACK COUNTS (Neo4j)")
        for key in counts.keys():
            print(f"  {key}: {counts[key]}")

        print("\nSAMPLE OBSERVATION -> CONCEPT LINKS")
        for record in session.run(SAMPLE_OBSERVATIONS):
            extra = ""
            if record["observed_state"]:
                extra = f" stage_index={record['stage_index']} observed_state={record['observed_state']}"
            print(
                f"  {record['patient_id']} @ {record['date']}: {record['concept']}"
                f" = {record['value']}{extra}"
            )

        print("\nVISITS WITH NO RETINAL MEASUREMENT (expected missing data, not fabricated No_DR)")
        for record in session.run(MISSING_RETINAL_VISITS):
            print(f"  {record['patient_id']} @ {record['date']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
