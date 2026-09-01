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

patient = {
    "patient_id": "P001",
    "age": 15,
    "sex": "M",
    "t1d_duration": 7
}

timeline = [
    {
        "date": "2025-01-15",
        "hba1c": 7.2,
        "cgm_time_in_range": 72,
        "systolic_bp": 112,
        "diastolic_bp": 70,
        "uacr": 14,
        "serum_creatinine": 0.72,
        "egfr": 118
    },
    {
        "date": "2025-04-15",
        "hba1c": 7.8,
        "cgm_time_in_range": 67,
        "systolic_bp": 116,
        "diastolic_bp": 72,
        "uacr": 21,
        "serum_creatinine": 0.74,
        "egfr": 115
    },
    {
        "date": "2025-07-15",
        "hba1c": 8.3,
        "cgm_time_in_range": 61,
        "systolic_bp": 121,
        "diastolic_bp": 76,
        "uacr": 29,
        "serum_creatinine": 0.77,
        "egfr": 111
    },
    {
        "date": "2025-10-15",
        "hba1c": 8.8,
        "cgm_time_in_range": 55,
        "systolic_bp": 128,
        "diastolic_bp": 80,
        "uacr": 36,
        "serum_creatinine": 0.81,
        "egfr": 106
    }
]

try:
    driver.verify_connectivity()
    print("CONNECTED")

    with driver.session(
        database=os.getenv("KIDNEY_NEO4J_DATABASE")
    ) as session:

        session.run("""
            MERGE (p:Patient {patient_id: $patient_id})
            SET
                p.age = $age,
                p.sex = $sex,
                p.t1d_duration = $t1d_duration
        """, **patient)

        for visit in timeline:

            session.run("""
                MATCH (p:Patient {patient_id: $patient_id})

                MERGE (v:Visit {
                    patient_id: $patient_id,
                    date: date($date)
                })

                SET
                    v.age = $age,
                    v.t1d_duration = $t1d_duration

                MERGE (p)-[:HAS_VISIT]->(v)
            """,
            patient_id=patient["patient_id"],
            date=visit["date"],
            age=patient["age"],
            t1d_duration=patient["t1d_duration"])

            measurements = {
                "HbA1c": visit["hba1c"],
                "CGM_Time_in_Range": visit["cgm_time_in_range"],
                "Systolic_BP": visit["systolic_bp"],
                "Diastolic_BP": visit["diastolic_bp"],
                "UACR": visit["uacr"],
                "Serum_Creatinine": visit["serum_creatinine"],
                "eGFR": visit["egfr"]
            }

            for concept_name, value in measurements.items():

                session.run("""
                    MATCH (v:Visit {
                        patient_id: $patient_id,
                        date: date($date)
                    })

                    MATCH (c:Concept {
                        name: $concept_name
                    })

                    MERGE (m:Measurement {
                        patient_id: $patient_id,
                        date: date($date),
                        concept: $concept_name
                    })

                    SET
                        m.value = $value

                    MERGE (v)-[:HAS_MEASUREMENT]->(m)
                    MERGE (m)-[:INSTANCE_OF]->(c)
                """,
                patient_id=patient["patient_id"],
                date=visit["date"],
                concept_name=concept_name,
                value=value)

    print("PATIENT GRAPH CREATED")

finally:
    driver.close()