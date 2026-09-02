import os
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATIENTS_CSV = os.path.join(BASE_DIR, "patients.csv")
VISITS_CSV = os.path.join(BASE_DIR, "temporal_patient_visits.csv")

print("=" * 70)
print("CARDIO PATIENTS DATA SANITY CHECK")
print("=" * 70)

with open(PATIENTS_CSV, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    print("\n--- PATIENT BASELINES ---")
    for row in reader:
        print(f"ID: {row['patient_id']} | Label: {row['patient_label']} | Sex: {row['sex']}")
        print(f"  Context: {row['baseline_cvd_context']}")
        print(f"  Pattern: {row['temporal_pattern']}")

with open(VISITS_CSV, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    visits = list(reader)
    print(f"\n--- TOTAL VISITS: {len(visits)} ---")
    for v in visits[:4]:
        print(f"Patient {v['patient_id']} | Visit {v['visit_id']} ({v['visit_date']}) | BP: {v['systolic_bp_mmHg']}/{v['diastolic_bp_mmHg']} | HbA1c: {v['hba1c_percent']}% | LDL: {v['ldl_mg_dL']} | UACR: {v['uacr_mg_g']} | BNP: {v['bnp_pg_mL']}")

print("\n" + "=" * 70)
