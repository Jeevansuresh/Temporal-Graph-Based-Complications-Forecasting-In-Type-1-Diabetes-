import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("KIDNEY_NEO4J_URI"),
    auth=(
        os.getenv("KIDNEY_NEO4J_USERNAME"),
        os.getenv("KIDNEY_NEO4J_PASSWORD")
    )
)

try:
    driver.verify_connectivity()
    print("CONNECTED")

    with driver.session(
        database=os.getenv("KIDNEY_NEO4J_DATABASE")
    ) as session:

        result = session.run("""
            MATCH (input:Concept)-[:INPUT_TO]->(r:Rule)-[:PRODUCES]->(output:Concept)
            OPTIONAL MATCH (r)-[:SUPPORTED_BY]->(e:Evidence)

            WITH
                r.rule_id AS rule_id,
                r.trigger AS trigger,
                r.temporal_requirement AS temporal_requirement,
                input.name AS input,
                output.name AS output,
                e.evidence_id AS evidence_id,
                e.citation AS evidence,
                e.population AS population

            RETURN
                rule_id AS rule,
                trigger,
                temporal_requirement,
                input,
                output,
                evidence_id,
                evidence,
                population

            ORDER BY rule_id
        """)

        print("\n" + "=" * 70)
        print("CLINICAL RULES")
        print("=" * 70)

        for record in result:
            print(dict(record))

finally:
    driver.close()