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

# Single patient template example
patient = {
    "patient_id": "P001",
    "label": "Synthetic Patient 001",
    "age": 30,
    "sex": "M",
    "t1d_duration": 14.1,
    "baseline_cvd_context": "No known ASCVD",
    "temporal_pattern": "Stable low-moderate longitudinal pattern"
}

timeline = [
    {
        "visit_id": "V001",
        "date": "2026-01-12",
        "Systolic_BP": 118,
        "Diastolic_BP": 74,
        "HbA1c": 5.8,
        "LDL_Cholesterol": 112,
        "HDL_Cholesterol": 52,
        "Triglycerides": 48,
        "UACR": 8.5,
        "BNP_NTproBNP": 42,
        "eGFR": 112
    },
    {
        "visit_id": "V002",
        "date": "2026-02-23",
        "Systolic_BP": 121,
        "Diastolic_BP": 76,
        "HbA1c": 5.9,
        "LDL_Cholesterol": 118,
        "HDL_Cholesterol": 50,
        "Triglycerides": 46,
        "UACR": 9.0,
        "BNP_NTproBNP": 40,
        "eGFR": 118
    },
    {
        "visit_id": "V003",
        "date": "2026-04-06",
        "Systolic_BP": 124,
        "Diastolic_BP": 78,
        "HbA1c": 6.0,
        "LDL_Cholesterol": 121,
        "HDL_Cholesterol": 51,
        "Triglycerides": 47,
        "UACR": 8.8,
        "BNP_NTproBNP": 43,
        "eGFR": 121
    },
    {
        "visit_id": "V004",
        "date": "2026-06-01",
        "Systolic_BP": 119,
        "Diastolic_BP": 75,
        "HbA1c": 5.9,
        "LDL_Cholesterol": 115,
        "HDL_Cholesterol": 52,
        "Triglycerides": 49,
        "UACR": 8.2,
        "BNP_NTproBNP": 41,
        "eGFR": 115
    },
    {
        "visit_id": "V005",
        "date": "2026-08-10",
        "Systolic_BP": 122,
        "Diastolic_BP": 77,
        "HbA1c": 6.1,
        "LDL_Cholesterol": 117,
        "HDL_Cholesterol": 50,
        "Triglycerides": 48,
        "UACR": 8.7,
        "BNP_NTproBNP": 44,
        "eGFR": 117
    }
]

UNIT_MAP = {
    "Systolic_BP": "mmHg",
    "Diastolic_BP": "mmHg",
    "HbA1c": "%",
    "LDL_Cholesterol": "mg/dL",
    "HDL_Cholesterol": "mg/dL",
    "Triglycerides": "mg/dL",
    "UACR": "mg/g",
    "BNP_NTproBNP": "pg/mL",
    "eGFR": "mL/min/1.73m2"
}

def main():
    driver = get_driver()
    try:
        driver.verify_connectivity()
        print("CONNECTED TO NEO4J")
        with driver.session(database=DATABASE) as session:
            session.run("""
                MERGE (p:Patient {patient_id: $patient_id})
                SET p.label = $label,
                    p.age = $age,
                    p.sex = $sex,
                    p.t1d_duration = $t1d_duration,
                    p.baseline_cvd_context = $baseline_cvd_context,
                    p.temporal_pattern = $temporal_pattern
            """, **patient)

            prev_vid = None
            for visit in timeline:
                vid = visit["visit_id"]
                vdate = visit["date"]
                session.run("""
                    MATCH (p:Patient {patient_id: $patient_id})
                    MERGE (v:Visit {
                        patient_id: $patient_id,
                        visit_id: $visit_id
                    })
                    SET v.date = date($date),
                        v.age = $age,
                        v.t1d_duration = $t1d_duration
                    MERGE (p)-[:HAS_VISIT]->(v)
                """,
                patient_id=patient["patient_id"],
                visit_id=vid,
                date=vdate,
                age=patient["age"],
                t1d_duration=patient["t1d_duration"])

                if prev_vid:
                    session.run("""
                        MATCH (v1:Visit {patient_id: $patient_id, visit_id: $prev_vid})
                        MATCH (v2:Visit {patient_id: $patient_id, visit_id: $curr_vid})
                        MERGE (v1)-[:NEXT_VISIT]->(v2)
                    """, patient_id=patient["patient_id"], prev_vid=prev_vid, curr_vid=vid)
                prev_vid = vid

                for concept_name, unit in UNIT_MAP.items():
                    if concept_name in visit:
                        val = visit[concept_name]
                        session.run("""
                            MATCH (v:Visit {patient_id: $patient_id, visit_id: $visit_id})
                            MATCH (c:Concept {name: $concept_name})
                            MERGE (m:Measurement {
                                patient_id: $patient_id,
                                visit_id: $visit_id,
                                concept: $concept_name
                            })
                            SET m.value = $value,
                                m.unit = $unit,
                                m.date = date($date)
                            MERGE (v)-[:HAS_MEASUREMENT]->(m)
                            MERGE (m)-[:INSTANCE_OF]->(c)
                        """,
                        patient_id=patient["patient_id"],
                        visit_id=vid,
                        date=vdate,
                        concept_name=concept_name,
                        value=float(val),
                        unit=unit)

        print("PATIENT GRAPH CREATED FOR", patient["patient_id"])
    finally:
        driver.close()

if __name__ == "__main__":
    main()
