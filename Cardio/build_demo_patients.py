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
PATIENTS_CSV = os.path.join(BASE_DIR, "patients.csv")
VISITS_CSV = os.path.join(BASE_DIR, "temporal_patient_visits.csv")

# Measurements mapped to Concept nodes in nodes.csv
MEASUREMENT_CONCEPT_MAP = {
    "systolic_bp_mmHg": ("Systolic_BP", "mmHg"),
    "diastolic_bp_mmHg": ("Diastolic_BP", "mmHg"),
    "hba1c_percent": ("HbA1c", "%"),
    "ldl_mg_dL": ("LDL_Cholesterol", "mg/dL"),
    "hdl_mg_dL": ("HDL_Cholesterol", "mg/dL"),
    "triglycerides_mg_dL": ("Triglycerides", "mg/dL"),
    "uacr_mg_g": ("UACR", "mg/g"),
    "egfr_mL_min_1_73m2": ("eGFR", "mL/min/1.73m2"),
    "bnp_pg_mL": ("BNP_NTproBNP", "pg/mL")
}


def get_driver():
    try:
        driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
        driver.verify_connectivity()
        return driver
    except Exception:
        driver = GraphDatabase.driver(URI, auth=("neo4j", PASSWORD))
        driver.verify_connectivity()
        return driver


def clear_demo_patients(session, patient_ids):
    print(f"Clearing existing demo patients {patient_ids}...")
    session.run("""
        MATCH (p:Patient)
        WHERE p.patient_id IN $patient_ids
        OPTIONAL MATCH (p)-[:HAS_VISIT]->(v:Visit)
        OPTIONAL MATCH (v)-[:HAS_MEASUREMENT]->(m:Measurement)
        WITH collect(DISTINCT p) + collect(DISTINCT v) + collect(DISTINCT m) AS nodes
        UNWIND nodes AS node
        DETACH DELETE node
    """, patient_ids=patient_ids)


def load_patients(session):
    patients = {}
    with open(PATIENTS_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["patient_id"].strip()
            patients[pid] = {
                "patient_id": pid,
                "label": row.get("patient_label", "").strip(),
                "sex": row.get("sex", "").strip(),
                "baseline_cvd_context": row.get("baseline_cvd_context", "").strip(),
                "temporal_pattern": row.get("temporal_pattern", "").strip()
            }
            session.run("""
                MERGE (p:Patient {patient_id: $patient_id})
                SET p.label = $label,
                    p.sex = $sex,
                    p.baseline_cvd_context = $baseline_cvd_context,
                    p.temporal_pattern = $temporal_pattern
            """, **patients[pid])
            print(f"Created Patient node: {pid} ({patients[pid]['label']})")
    return patients


def load_visits_and_measurements(session):
    print(f"Loading patient visits and measurements from {VISITS_CSV}...")
    visits_by_patient = {}

    with open(VISITS_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["patient_id"].strip()
            if pid not in visits_by_patient:
                visits_by_patient[pid] = []
            visits_by_patient[pid].append(row)

    total_visits = 0
    total_measurements = 0

    for pid, visits in visits_by_patient.items():
        sorted_visits = sorted(visits, key=lambda x: x.get("visit_date", ""))
        prev_visit_id = None

        for visit in sorted_visits:
            vid = visit["visit_id"].strip()
            vdate = visit["visit_date"].strip()
            vtime = visit.get("visit_time", "").strip()
            age = float(visit["age_years"]) if visit.get("age_years") else None
            t1d_dur = float(visit["t1d_duration_years"]) if visit.get("t1d_duration_years") else None
            smoking = visit.get("smoking_status", "").strip()
            htn_status = visit.get("hypertension_status", "").strip()
            dyslipidemia = visit.get("dyslipidemia", "").strip()
            known_ascvd = visit.get("known_ascvd", "").strip()
            known_cad = visit.get("known_cad", "").strip()
            ecg = visit.get("ecg_abnormality", "").strip()
            symptoms = visit.get("cardiovascular_symptoms", "").strip()
            action = visit.get("clinical_action", "").strip()
            
            # Additional visit metrics
            bmi = float(visit["bmi"]) if visit.get("bmi") else None
            weight = float(visit["weight_kg"]) if visit.get("weight_kg") else None
            height = float(visit["height_cm"]) if visit.get("height_cm") else None
            hr = float(visit["heart_rate_bpm"]) if visit.get("heart_rate_bpm") else None
            f_glu = float(visit["fasting_glucose_mg_dL"]) if visit.get("fasting_glucose_mg_dL") else None
            r_glu = float(visit["random_glucose_mg_dL"]) if visit.get("random_glucose_mg_dL") else None
            tot_chol = float(visit["total_cholesterol_mg_dL"]) if visit.get("total_cholesterol_mg_dL") else None
            creat = float(visit["serum_creatinine_mg_dL"]) if visit.get("serum_creatinine_mg_dL") else None

            # Update patient age and t1d_duration with latest
            session.run("""
                MATCH (p:Patient {patient_id: $patient_id})
                SET p.age = $age,
                    p.t1d_duration = $t1d_dur
            """, patient_id=pid, age=age, t1d_dur=t1d_dur)

            # Create Visit node and link (Patient)-[:HAS_VISIT]->(Visit)
            session.run("""
                MATCH (p:Patient {patient_id: $patient_id})
                MERGE (v:Visit {patient_id: $patient_id, visit_id: $visit_id})
                SET v.date = date($date),
                    v.time = $time,
                    v.age = $age,
                    v.t1d_duration = $t1d_duration,
                    v.smoking_status = $smoking,
                    v.hypertension_status = $htn_status,
                    v.dyslipidemia = $dyslipidemia,
                    v.known_ascvd = $known_ascvd,
                    v.known_cad = $known_cad,
                    v.ecg_abnormality = $ecg,
                    v.cardiovascular_symptoms = $symptoms,
                    v.clinical_action = $action,
                    v.bmi = $bmi,
                    v.weight_kg = $weight,
                    v.height_cm = $height,
                    v.heart_rate_bpm = $hr,
                    v.fasting_glucose = $f_glu,
                    v.random_glucose = $r_glu,
                    v.total_cholesterol = $tot_chol,
                    v.serum_creatinine = $creat
                MERGE (p)-[:HAS_VISIT]->(v)
            """,
                patient_id=pid,
                visit_id=vid,
                date=vdate,
                time=vtime,
                age=age,
                t1d_duration=t1d_dur,
                smoking=smoking,
                htn_status=htn_status,
                dyslipidemia=dyslipidemia,
                known_ascvd=known_ascvd,
                known_cad=known_cad,
                ecg=ecg,
                symptoms=symptoms,
                action=action,
                bmi=bmi,
                weight=weight,
                height=height,
                hr=hr,
                f_glu=f_glu,
                r_glu=r_glu,
                tot_chol=tot_chol,
                creat=creat
            )
            total_visits += 1

            # Connect sequence of visits (prev_v)-[:NEXT_VISIT]->(v)
            if prev_visit_id:
                session.run("""
                    MATCH (v1:Visit {patient_id: $patient_id, visit_id: $prev_vid})
                    MATCH (v2:Visit {patient_id: $patient_id, visit_id: $curr_vid})
                    MERGE (v1)-[:NEXT_VISIT]->(v2)
                """, patient_id=pid, prev_vid=prev_visit_id, curr_vid=vid)

            prev_visit_id = vid

            # Create measurements mapped to existing Concept nodes
            for col, (concept_name, unit) in MEASUREMENT_CONCEPT_MAP.items():
                val_str = visit.get(col, "").strip()
                if val_str and val_str != "None":
                    try:
                        val = float(val_str)
                    except ValueError:
                        continue

                    session.run("""
                        MATCH (v:Visit {patient_id: $patient_id, visit_id: $visit_id})
                        MATCH (c:Concept {name: $concept_name})
                        CREATE (m:Measurement {
                            patient_id: $patient_id,
                            visit_id: $visit_id,
                            date: date($date),
                            concept: $concept_name,
                            value: $value,
                            unit: $unit
                        })
                        CREATE (v)-[:HAS_MEASUREMENT]->(m)
                        CREATE (m)-[:INSTANCE_OF]->(c)
                    """,
                        patient_id=pid,
                        visit_id=vid,
                        date=vdate,
                        concept_name=concept_name,
                        value=val,
                        unit=unit
                    )
                    total_measurements += 1

    print(f"Loaded {total_visits} Visits and {total_measurements} Measurements across patients.")


def main():
    driver = get_driver()
    try:
        print("Connected to Neo4j.")
        with driver.session(database=DATABASE) as session:
            patient_ids = []
            with open(PATIENTS_CSV, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                patient_ids = [row["patient_id"].strip() for row in reader]

            clear_demo_patients(session, patient_ids)
            load_patients(session)
            load_visits_and_measurements(session)

            result = session.run("""
                MATCH (p:Patient)
                OPTIONAL MATCH (p)-[:HAS_VISIT]->(v:Visit)
                RETURN p.patient_id AS pid, p.label AS label, p.sex AS sex, count(v) AS visits
                ORDER BY pid
            """)
            print("\n" + "=" * 65)
            print("CARDIO DEMO PATIENTS CREATED IN NEO4J")
            print("=" * 65)
            for rec in result:
                print(f"Patient {rec['pid']} | {rec['label']} | {rec['sex']} | Visits: {rec['visits']}")
            print("=" * 65)

    finally:
        driver.close()


if __name__ == "__main__":
    main()
