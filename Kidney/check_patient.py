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
    with driver.session(
        database=os.getenv("KIDNEY_NEO4J_DATABASE")
    ) as session:

        result = session.run("""
            MATCH (p:Patient {patient_id: 'P001'})
                  -[:HAS_VISIT]->
                  (v:Visit)
                  -[:HAS_MEASUREMENT]->
                  (m:Measurement)
                  -[:INSTANCE_OF]->
                  (c:Concept)

            RETURN
                v.date AS date,
                c.name AS measurement,
                m.value AS value

            ORDER BY date, measurement
        """)

        print("\n" + "=" * 70)
        print("PATIENT TEMPORAL GRAPH")
        print("=" * 70)

        for record in result:
            print(
                record["date"],
                "|",
                record["measurement"],
                "=",
                record["value"]
            )

finally:
    driver.close()