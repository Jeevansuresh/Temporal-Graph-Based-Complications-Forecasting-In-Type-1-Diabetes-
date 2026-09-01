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
    driver.verify_connectivity()
    print("CONNECTED TO CARDIO NEO4J GRAPH")

    with driver.session(database=DATABASE) as session:

        result = session.run("""
            MATCH (input:Concept)-[:INPUT_TO]->(r:Rule)-[:PRODUCES]->(output:Concept)
            OPTIONAL MATCH (r)-[:SUPPORTED_BY]->(e:Evidence)

            WITH
                r.rule_id AS rule_id,
                r.trigger AS trigger,
                r.logical_condition AS logical_condition,
                r.temporal_requirement AS temporal_requirement,
                input.name AS input,
                output.name AS output,
                e.evidence_id AS evidence_id,
                e.citation AS evidence,
                e.population AS population

            RETURN
                rule_id AS rule,
                trigger,
                logical_condition,
                temporal_requirement,
                input,
                output,
                evidence_id,
                evidence,
                population

            ORDER BY rule_id, input
        """)

        print("\n" + "=" * 80)
        print("CARDIO CLINICAL RULES & EVIDENCE GROUNDING")
        print("=" * 80)

        for record in result:
            print(dict(record))

finally:
    driver.close()
