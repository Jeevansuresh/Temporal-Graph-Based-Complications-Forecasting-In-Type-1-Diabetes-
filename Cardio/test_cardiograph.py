import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = os.getenv("CARDIO_NEO4J_URI") or os.getenv("NEO4J_URI")
USERNAME = os.getenv("CARDIO_NEO4J_USERNAME") or os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("CARDIO_NEO4J_PASSWORD") or os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("CARDIO_NEO4J_DATABASE") or os.getenv("NEO4J_DATABASE")

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

        print("\n========== CARDIO NODES ==========\n")

        result = session.run("""
            MATCH (n)
            WHERE n:Concept OR n:Rule OR n:Evidence
            RETURN labels(n) AS labels,
                   n
            ORDER BY labels(n), n.name, n.rule_id, n.evidence_id
        """)

        for record in result:
            node = record["n"]
            print(f"{record['labels']}: {dict(node)}")

        print("\n========== CLINICAL RELATIONSHIPS ==========\n")

        result = session.run("""
            MATCH (a:Concept)-[r:CLINICAL_RELATIONSHIP]->(b:Concept)
            RETURN a.name AS source,
                   r.relation AS relationship,
                   properties(r) AS properties,
                   b.name AS target
            ORDER BY source
        """)

        for record in result:
            print(
                f"{record['source']} "
                f"--[{record['relationship']}]--> "
                f"{record['target']}"
            )

            if record["properties"]:
                print(f"    {record['properties']}")

        print("\n========== CLINICAL RULES ==========\n")

        result = session.run("""
            MATCH (r:Rule)
            OPTIONAL MATCH (inp:Concept)-[:INPUT_TO]->(r)
            OPTIONAL MATCH (r)-[:PRODUCES]->(out:Concept)
            OPTIONAL MATCH (r)-[:SUPPORTED_BY]->(e:Evidence)
            RETURN r.rule_id AS rule_id,
                   r.trigger AS trigger,
                   r.logical_condition AS logical_condition,
                   r.temporal_requirement AS temporal_requirement,
                   collect(DISTINCT inp.name) AS inputs,
                   out.name AS output,
                   e.evidence_id AS evidence_id
            ORDER BY r.rule_id
        """)

        for record in result:
            print(f"Rule {record['rule_id']}: {record['trigger']}")
            print(f"  Inputs: {record['inputs']} -> Output: {record['output']}")
            print(f"  Condition: {record['logical_condition']}")
            print(f"  Temporal Requirement: {record['temporal_requirement']}")
            print(f"  Evidence: {record['evidence_id']}")
            print("-" * 50)

        print("\n========== EVIDENCE BASE ==========\n")

        result = session.run("""
            MATCH (e:Evidence)
            RETURN properties(e) AS evidence
            ORDER BY e.evidence_id
        """)

        for record in result:
            ev = record["evidence"]
            print(f"[{ev.get('evidence_id')}] {ev.get('citation')} ({ev.get('year')})")
            print(f"  Population: {ev.get('population')} | Strength: {ev.get('evidence_strength')}")
            print(f"  Summary: {ev.get('summary')}")
            print("-" * 50)

finally:
    driver.close()
