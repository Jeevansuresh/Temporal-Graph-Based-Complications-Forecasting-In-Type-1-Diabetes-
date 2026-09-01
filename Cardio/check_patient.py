import os
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = os.getenv("CARDIO_NEO4J_URI") or os.getenv("NEO4J_URI")
USERNAME = os.getenv("CARDIO_NEO4J_USERNAME") or os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("CARDIO_NEO4J_PASSWORD") or os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("CARDIO_NEO4J_DATABASE") or os.getenv("NEO4J_DATABASE")

patient_id = sys.argv[1] if len(sys.argv) > 1 else "P001"

def get_driver():
    try:
        driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
        driver.verify_connectivity()
        return driver
    except Exception:
        driver = GraphDatabase.driver(URI, auth=("neo4j", PASSWORD))
        driver.verify_connectivity()
        return driver

driver = get_driver()

try:
    with driver.session(database=DATABASE) as session:
        # Patient info
        p_res = session.run("""
            MATCH (p:Patient {patient_id: $pid})
            RETURN p.patient_id AS pid, p.label AS label, p.sex AS sex, p.age AS age,
                   p.t1d_duration AS t1d_duration, p.baseline_cvd_context AS context,
                   p.temporal_pattern AS pattern
        """, pid=patient_id).single()

        if not p_res:
            print(f"Patient {patient_id} not found in database.")
            sys.exit(0)

        print("\n" + "=" * 80)
        print(f"CARDIO PATIENT TEMPORAL GRAPH: {p_res['pid']} ({p_res['label']})")
        print("=" * 80)
        print(f"Sex: {p_res['sex']} | Age: {p_res['age']} | T1D Duration: {p_res['t1d_duration']} yrs")
        print(f"Baseline Context: {p_res['context']}")
        print(f"Temporal Pattern: {p_res['pattern']}")
        print("-" * 80)

        result = session.run("""
            MATCH (p:Patient {patient_id: $pid})
                  -[:HAS_VISIT]->
                  (v:Visit)
                  -[:HAS_MEASUREMENT]->
                  (m:Measurement)
                  -[:INSTANCE_OF]->
                  (c:Concept)
            RETURN
                v.visit_id AS visit_id,
                v.date AS date,
                c.name AS measurement,
                m.value AS value,
                m.unit AS unit
            ORDER BY v.date, measurement
        """, pid=patient_id)

        current_date = None
        for record in result:
            date_str = f"{record['visit_id']} ({record['date']})"
            if date_str != current_date:
                current_date = date_str
                print(f"\n[Visit {current_date}]")
            unit_str = f" {record['unit']}" if record['unit'] else ""
            print(f"  {record['measurement']:22} = {record['value']}{unit_str}")

        print("\n" + "=" * 80)

finally:
    driver.close()
