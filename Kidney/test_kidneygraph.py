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

database = os.getenv("KIDNEY_NEO4J_DATABASE")

try:
    with driver.session(database=database) as session:

        print("\n========== NODES ==========\n")

        result = session.run("""
            MATCH (n)
            RETURN labels(n) AS labels,
                   n
            ORDER BY labels(n)
        """)

        for record in result:
            node = record["n"]
            print(f"{record['labels']}: {dict(node)}")

        print("\n========== RELATIONSHIPS ==========\n")

        result = session.run("""
            MATCH (a)-[r]->(b)
            RETURN labels(a) AS source_labels,
                   a.name AS source,
                   type(r) AS relationship,
                   properties(r) AS properties,
                   labels(b) AS target_labels,
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

        print("\n========== RULES ==========\n")

        result = session.run("""
            MATCH (r:Rule)
            RETURN properties(r) AS rule
            ORDER BY r.name
        """)

        for record in result:
            print(record["rule"])

        print("\n========== EVIDENCE ==========\n")

        result = session.run("""
            MATCH (e:Evidence)
            RETURN properties(e) AS evidence
            ORDER BY e.evidence_id
        """)

        for record in result:
            print(record["evidence"])

finally:
    driver.close()