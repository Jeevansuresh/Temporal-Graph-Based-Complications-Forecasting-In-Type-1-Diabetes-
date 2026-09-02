import os
import csv
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = os.getenv("CARDIO_NEO4J_URI") or os.getenv("NEO4J_URI")
USERNAME = os.getenv("CARDIO_NEO4J_USERNAME") or os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("CARDIO_NEO4J_PASSWORD") or os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("CARDIO_NEO4J_DATABASE") or os.getenv("NEO4J_DATABASE")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODES_CSV = os.path.join(BASE_DIR, "nodes.csv")
RELATIONSHIPS_CSV = os.path.join(BASE_DIR, "relationships.csv")
RULES_CSV = os.path.join(BASE_DIR, "rules.csv")
EVIDENCE_CSV = os.path.join(BASE_DIR, "evidence.csv")


def get_driver():
    # Try username from env first, and fallback to neo4j/instance id if needed
    try:
        driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
        driver.verify_connectivity()
        return driver
    except Exception:
        # Fallback to neo4j
        driver = GraphDatabase.driver(URI, auth=("neo4j", PASSWORD))
        driver.verify_connectivity()
        return driver


def clear_knowledge_graph(session):
    print("Clearing existing Knowledge Graph concepts, rules, and evidence...")
    session.run("""
        MATCH (n)
        WHERE n:Concept OR n:Rule OR n:Evidence
        DETACH DELETE n
    """)


def setup_constraints(session):
    print("Setting up uniqueness constraints...")
    try:
        session.run("CREATE CONSTRAINT concept_name_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE")
    except Exception as e:
        print(f"Constraint note (Concept): {e}")

    try:
        session.run("CREATE CONSTRAINT rule_id_unique IF NOT EXISTS FOR (r:Rule) REQUIRE r.rule_id IS UNIQUE")
    except Exception as e:
        print(f"Constraint note (Rule): {e}")

    try:
        session.run("CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS FOR (e:Evidence) REQUIRE e.evidence_id IS UNIQUE")
    except Exception as e:
        print(f"Constraint note (Evidence): {e}")


def load_concepts(session):
    print(f"Loading concepts from {NODES_CSV}...")
    with open(NODES_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            concept_type = row.get("type", "").strip()
            # Clean synonyms
            synonyms = [s.strip() for s in row.get("synonyms", "").split(";") if s.strip()]
            
            # Base query to merge Concept
            query = f"""
                MERGE (c:Concept {{name: $name}})
                SET c.concept_id = $concept_id,
                    c.type = $type,
                    c.synonyms = $synonyms,
                    c.unit = $unit,
                    c.description = $description
            """
            session.run(
                query,
                name=row["name"].strip(),
                concept_id=int(row["concept_id"]) if row.get("concept_id") else None,
                type=concept_type,
                synonyms=synonyms,
                unit=row.get("unit", "").strip(),
                description=row.get("description", "").strip()
            )
            
            # Add specific type label if present (e.g. :Measurement, :Condition)
            if concept_type:
                # Sanitize label
                valid_label = concept_type.replace(" ", "_").replace("-", "_")
                label_query = f"MATCH (c:Concept {{name: $name}}) SET c:{valid_label}"
                session.run(label_query, name=row["name"].strip())
            
            count += 1
        print(f"Loaded {count} Concept nodes.")


def load_evidence(session):
    print(f"Loading evidence from {EVIDENCE_CSV}...")
    with open(EVIDENCE_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            session.run("""
                MERGE (e:Evidence {evidence_id: $evidence_id})
                SET e.citation = $citation,
                    e.year = $year,
                    e.source_type = $source_type,
                    e.population = $population,
                    e.url_doi = $url_doi,
                    e.summary = $summary,
                    e.evidence_strength = $evidence_strength
            """,
                evidence_id=row["evidence_id"].strip(),
                citation=row.get("citation", "").strip(),
                year=int(row["year"]) if row.get("year") and row["year"].isdigit() else None,
                source_type=row.get("source_type", "").strip(),
                population=row.get("population", "").strip(),
                url_doi=row.get("URL/DOI", "").strip(),
                summary=row.get("summary", "").strip(),
                evidence_strength=row.get("evidence_strength", "").strip()
            )
            count += 1
        print(f"Loaded {count} Evidence nodes.")


def load_relationships(session):
    print(f"Loading relationships from {RELATIONSHIPS_CSV}...")
    with open(RELATIONSHIPS_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            subject = row["subject"].strip()
            relation = row["relation"].strip()
            obj = row["object"].strip()
            evidence_id = row.get("evidence_id", "").strip()
            population = row.get("population", "").strip()
            directionality = row.get("directionality", "").strip()
            confidence = row.get("confidence", "").strip()

            session.run("""
                MATCH (a:Concept {name: $subject})
                MATCH (b:Concept {name: $object})
                MERGE (a)-[r:CLINICAL_RELATIONSHIP {relation: $relation}]->(b)
                SET r.evidence_id = $evidence_id,
                    r.population = $population,
                    r.directionality = $directionality,
                    r.confidence = $confidence
            """,
                subject=subject,
                object=obj,
                relation=relation,
                evidence_id=evidence_id,
                population=population,
                directionality=directionality,
                confidence=confidence
            )
            count += 1
        print(f"Loaded {count} CLINICAL_RELATIONSHIP edges.")


def load_rules(session):
    print(f"Loading rules from {RULES_CSV}...")
    
    # Input mapping for rules based on trigger concepts
    RULE_INPUT_MAP = {
        "R001": ["Systolic_BP", "Diastolic_BP"],
        "R002": ["UACR"],
        "R003": ["eGFR"],
        "R004": ["BNP_NTproBNP"],
        "R005": ["BNP_NTproBNP"],
        "R006": ["T1D", "ASCVD"],
        "R007": ["T1D", "ECG_Abnormality"]
    }

    with open(RULES_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            rule_id = row["rule_id"].strip()
            trigger = row.get("trigger", "").strip()
            logical_condition = row.get("logical_condition", "").strip()
            temporal_requirement = row.get("temporal_requirement", "").strip()
            output_concept = row.get("output_concept", "").strip()
            evidence_id = row.get("evidence_id", "").strip()

            session.run("""
                MERGE (r:Rule {rule_id: $rule_id})
                SET r.name = $rule_id,
                    r.trigger = $trigger,
                    r.logical_condition = $logical_condition,
                    r.temporal_requirement = $temporal_requirement,
                    r.output_concept = $output_concept,
                    r.evidence_id = $evidence_id
            """,
                rule_id=rule_id,
                trigger=trigger,
                logical_condition=logical_condition,
                temporal_requirement=temporal_requirement,
                output_concept=output_concept,
                evidence_id=evidence_id
            )

            # Link Output concept: (r:Rule)-[:PRODUCES]->(output:Concept)
            if output_concept:
                session.run("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (out:Concept {name: $output_concept})
                    MERGE (r)-[:PRODUCES]->(out)
                """, rule_id=rule_id, output_concept=output_concept)

            # Link Input concepts: (input:Concept)-[:INPUT_TO]->(r:Rule)
            inputs = RULE_INPUT_MAP.get(rule_id, [])
            for input_name in inputs:
                session.run("""
                    MATCH (inp:Concept {name: $input_name})
                    MATCH (r:Rule {rule_id: $rule_id})
                    MERGE (inp)-[:INPUT_TO]->(r)
                """, rule_id=rule_id, input_name=input_name)

            # Link Evidence: (r:Rule)-[:SUPPORTED_BY]->(e:Evidence)
            if evidence_id:
                session.run("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (e:Evidence {evidence_id: $evidence_id})
                    MERGE (r)-[:SUPPORTED_BY]->(e)
                """, rule_id=rule_id, evidence_id=evidence_id)

            count += 1
        print(f"Loaded {count} Rule nodes and connected relationships.")


def main():
    driver = get_driver()
    try:
        print("Connected to Neo4j successfully.")
        with driver.session(database=DATABASE) as session:
            setup_constraints(session)
            clear_knowledge_graph(session)
            load_concepts(session)
            load_evidence(session)
            load_relationships(session)
            load_rules(session)

            # Print summary stats
            res_concepts = session.run("MATCH (c:Concept) RETURN count(c) AS cnt").single()["cnt"]
            res_rels = session.run("MATCH ()-[r:CLINICAL_RELATIONSHIP]->() RETURN count(r) AS cnt").single()["cnt"]
            res_rules = session.run("MATCH (r:Rule) RETURN count(r) AS cnt").single()["cnt"]
            res_ev = session.run("MATCH (e:Evidence) RETURN count(e) AS cnt").single()["cnt"]

            print("\n" + "=" * 50)
            print("CARDIO KNOWLEDGE GRAPH BUILD COMPLETE")
            print("=" * 50)
            print(f"Concepts:      {res_concepts}")
            print(f"Relationships: {res_rels}")
            print(f"Rules:         {res_rules}")
            print(f"Evidence:      {res_ev}")
            print("=" * 50)

    finally:
        driver.close()


if __name__ == "__main__":
    main()
