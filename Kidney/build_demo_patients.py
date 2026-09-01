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


PATIENTS = [

    {
        "patient_id": "P001",
        "age": 15,
        "sex": "M",
        "t1d_duration": 7,
        "visits": [
            {
                "date": "2025-01-15",
                "HbA1c": 7.2,
                "CGM_Time_in_Range": 72,
                "Systolic_BP": 112,
                "Diastolic_BP": 70,
                "UACR": 14,
                "Serum_Creatinine": 0.72,
                "eGFR": 118
            },
            {
                "date": "2025-04-15",
                "HbA1c": 7.8,
                "CGM_Time_in_Range": 67,
                "Systolic_BP": 116,
                "Diastolic_BP": 72,
                "UACR": 21,
                "Serum_Creatinine": 0.74,
                "eGFR": 115
            },
            {
                "date": "2025-07-15",
                "HbA1c": 8.3,
                "CGM_Time_in_Range": 61,
                "Systolic_BP": 121,
                "Diastolic_BP": 76,
                "UACR": 29,
                "Serum_Creatinine": 0.77,
                "eGFR": 111
            },
            {
                "date": "2025-10-15",
                "HbA1c": 8.8,
                "CGM_Time_in_Range": 55,
                "Systolic_BP": 128,
                "Diastolic_BP": 80,
                "UACR": 36,
                "Serum_Creatinine": 0.81,
                "eGFR": 106
            }
        ]
    },


    {
        "patient_id": "P002",
        "age": 14,
        "sex": "F",
        "t1d_duration": 6,
        "visits": [
            {
                "date": "2025-01-10",
                "HbA1c": 6.8,
                "CGM_Time_in_Range": 78,
                "Systolic_BP": 108,
                "Diastolic_BP": 68,
                "UACR": 10,
                "Serum_Creatinine": 0.68,
                "eGFR": 124
            },
            {
                "date": "2025-04-10",
                "HbA1c": 6.9,
                "CGM_Time_in_Range": 77,
                "Systolic_BP": 109,
                "Diastolic_BP": 68,
                "UACR": 11,
                "Serum_Creatinine": 0.69,
                "eGFR": 123
            },
            {
                "date": "2025-07-10",
                "HbA1c": 6.7,
                "CGM_Time_in_Range": 80,
                "Systolic_BP": 108,
                "Diastolic_BP": 67,
                "UACR": 9,
                "Serum_Creatinine": 0.68,
                "eGFR": 124
            },
            {
                "date": "2025-10-10",
                "HbA1c": 6.8,
                "CGM_Time_in_Range": 79,
                "Systolic_BP": 109,
                "Diastolic_BP": 68,
                "UACR": 10,
                "Serum_Creatinine": 0.69,
                "eGFR": 123
            }
        ]
    },


    {
        "patient_id": "P003",
        "age": 16,
        "sex": "M",
        "t1d_duration": 8,
        "visits": [
            {
                "date": "2025-01-20",
                "HbA1c": 7.1,
                "CGM_Time_in_Range": 74,
                "Systolic_BP": 110,
                "Diastolic_BP": 69,
                "UACR": 12,
                "Serum_Creatinine": 0.73,
                "eGFR": 120
            },
            {
                "date": "2025-04-20",
                "HbA1c": 7.3,
                "CGM_Time_in_Range": 71,
                "Systolic_BP": 112,
                "Diastolic_BP": 70,
                "UACR": 48,
                "Serum_Creatinine": 0.74,
                "eGFR": 118
            },
            {
                "date": "2025-07-20",
                "HbA1c": 7.0,
                "CGM_Time_in_Range": 75,
                "Systolic_BP": 111,
                "Diastolic_BP": 69,
                "UACR": 17,
                "Serum_Creatinine": 0.73,
                "eGFR": 120
            },
            {
                "date": "2025-10-20",
                "HbA1c": 7.2,
                "CGM_Time_in_Range": 73,
                "Systolic_BP": 112,
                "Diastolic_BP": 70,
                "UACR": 13,
                "Serum_Creatinine": 0.74,
                "eGFR": 119
            }
        ]
    },


    {
        "patient_id": "P004",
        "age": 15,
        "sex": "F",
        "t1d_duration": 7,
        "visits": [
            {
                "date": "2025-01-05",
                "HbA1c": 7.0,
                "CGM_Time_in_Range": 75,
                "Systolic_BP": 110,
                "Diastolic_BP": 68,
                "UACR": 13,
                "Serum_Creatinine": 0.70,
                "eGFR": 121
            },
            {
                "date": "2025-04-05",
                "HbA1c": 7.6,
                "CGM_Time_in_Range": 68,
                "Systolic_BP": 115,
                "Diastolic_BP": 72,
                "UACR": 14,
                "Serum_Creatinine": 0.71,
                "eGFR": 120
            },
            {
                "date": "2025-07-05",
                "HbA1c": 8.2,
                "CGM_Time_in_Range": 62,
                "Systolic_BP": 121,
                "Diastolic_BP": 76,
                "UACR": 16,
                "Serum_Creatinine": 0.72,
                "eGFR": 119
            },
            {
                "date": "2025-10-05",
                "HbA1c": 8.7,
                "CGM_Time_in_Range": 57,
                "Systolic_BP": 126,
                "Diastolic_BP": 79,
                "UACR": 18,
                "Serum_Creatinine": 0.73,
                "eGFR": 118
            }
        ]
    },


    {
        "patient_id": "P005",
        "age": 17,
        "sex": "M",
        "t1d_duration": 10,
        "visits": [
            {
                "date": "2025-01-12",
                "HbA1c": 7.6,
                "CGM_Time_in_Range": 68,
                "Systolic_BP": 116,
                "Diastolic_BP": 72,
                "UACR": 38,
                "Serum_Creatinine": 0.82,
                "eGFR": 104
            },
            {
                "date": "2025-04-12",
                "HbA1c": 7.8,
                "CGM_Time_in_Range": 66,
                "Systolic_BP": 118,
                "Diastolic_BP": 73,
                "UACR": 44,
                "Serum_Creatinine": 0.85,
                "eGFR": 101
            },
            {
                "date": "2025-07-12",
                "HbA1c": 8.0,
                "CGM_Time_in_Range": 64,
                "Systolic_BP": 120,
                "Diastolic_BP": 75,
                "UACR": 52,
                "Serum_Creatinine": 0.88,
                "eGFR": 97
            },
            {
                "date": "2025-10-12",
                "HbA1c": 8.2,
                "CGM_Time_in_Range": 62,
                "Systolic_BP": 122,
                "Diastolic_BP": 77,
                "UACR": 61,
                "Serum_Creatinine": 0.91,
                "eGFR": 93
            }
        ]
    }

]


UNIT_MAP = {
    "HbA1c": "%",
    "CGM_Time_in_Range": "%",
    "Systolic_BP": "mmHg",
    "Diastolic_BP": "mmHg",
    "UACR": "mg/g",
    "Serum_Creatinine": "mg/dL",
    "eGFR": "ml/min/1.73m2"
}

def clear_demo_patients(session):

    session.run("""
        MATCH (p:Patient)
        WHERE p.patient_id IN [
            "P001",
            "P002",
            "P003",
            "P004",
            "P005"
        ]

        OPTIONAL MATCH (p)-[:HAS_VISIT]->(v:Visit)
        OPTIONAL MATCH (v)-[:HAS_MEASUREMENT]->(m:Measurement)

        WITH
            collect(DISTINCT p) +
            collect(DISTINCT v) +
            collect(DISTINCT m) AS nodes

        UNWIND nodes AS node

        DETACH DELETE node
    """)


def create_patient(session, patient):

    session.run("""
        CREATE (p:Patient {
            patient_id: $patient_id,
            age: $age,
            sex: $sex,
            t1d_duration: $t1d_duration
        })
    """,
        patient_id=patient["patient_id"],
        age=patient["age"],
        sex=patient["sex"],
        t1d_duration=patient["t1d_duration"]
    )

    for visit in patient["visits"]:

        session.run("""
            MATCH (p:Patient {
                patient_id: $patient_id
            })

            CREATE (v:Visit {
                date: date($date)
            })

            CREATE (p)-[:HAS_VISIT]->(v)
        """,
            patient_id=patient["patient_id"],
            date=visit["date"]
        )

        for concept, value in visit.items():

            if concept == "date":
                continue

            session.run("""
                MATCH (p:Patient {
                    patient_id: $patient_id
                })
                -[:HAS_VISIT]->
                (v:Visit {
                    date: date($date)
                })

                MATCH (c:Concept {
                    name: $concept
                })

                CREATE (m:Measurement {
                    value: $value,
                    unit: $unit
                })

                CREATE
                    (v)-[:HAS_MEASUREMENT]->(m)

                CREATE
                    (m)-[:INSTANCE_OF]->(c)
            """,
                patient_id=patient["patient_id"],
                date=visit["date"],
                concept=concept,
                value=value,
                unit=UNIT_MAP[concept]
            )


def main():

    try:

        driver.verify_connectivity()

        print("NEO4J CONNECTED")

        with driver.session(
            database=os.getenv(
                "KIDNEY_NEO4J_DATABASE"
            )
        ) as session:

            print(
                "\nCLEARING EXISTING DEMO PATIENTS..."
            )

            clear_demo_patients(session)

            for patient in PATIENTS:

                print(
                    f"CREATING {patient['patient_id']}..."
                )

                create_patient(
                    session,
                    patient
                )

            result = session.run("""
                MATCH (p:Patient)
                RETURN
                    p.patient_id AS patient_id,
                    p.age AS age,
                    p.sex AS sex,
                    p.t1d_duration AS t1d_duration
                ORDER BY p.patient_id
            """)

            print(
                "\n" + "=" * 60
            )

            print(
                "PATIENTS CREATED"
            )

            print(
                "=" * 60
            )

            for record in result:

                print(
                    f"{record['patient_id']} | "
                    f"Age {record['age']} | "
                    f"{record['sex']} | "
                    f"T1D {record['t1d_duration']} years"
                )

    finally:

        driver.close()


if __name__ == "__main__":
    main()