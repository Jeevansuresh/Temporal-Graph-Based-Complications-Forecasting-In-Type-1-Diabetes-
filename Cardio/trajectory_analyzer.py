import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from neo4j import GraphDatabase

from temporal_engine import (
    calculate_trends,
    determine_worsening_variables,
    detect_cross_variable_patterns,
    classify_patient_pattern
)

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


def get_patient_metadata(session, patient_id):
    result = session.run("""
        MATCH (p:Patient {patient_id: $patient_id})
        RETURN p.patient_id AS patient_id,
               p.label AS label,
               p.age AS age,
               p.sex AS sex,
               p.t1d_duration AS t1d_duration,
               p.baseline_cvd_context AS baseline_cvd_context,
               p.temporal_pattern AS temporal_pattern
    """, patient_id=patient_id)
    rec = result.single()
    return dict(rec) if rec else {}


def get_patient_timeline(session, patient_id):
    result = session.run("""
        MATCH (p:Patient {patient_id: $patient_id})
              -[:HAS_VISIT]->
              (v:Visit)
        OPTIONAL MATCH (v)-[:HAS_MEASUREMENT]->(m:Measurement)-[:INSTANCE_OF]->(c:Concept)
        RETURN
            v.visit_id AS visit_id,
            v.date AS date,
            v.age AS age,
            v.t1d_duration AS t1d_duration,
            v.smoking_status AS smoking_status,
            v.hypertension_status AS hypertension_status,
            v.dyslipidemia AS dyslipidemia,
            v.known_ascvd AS known_ascvd,
            v.known_cad AS known_cad,
            v.ecg_abnormality AS ecg_abnormality,
            v.cardiovascular_symptoms AS cardiovascular_symptoms,
            v.clinical_action AS clinical_action,
            c.name AS concept,
            m.value AS value,
            m.unit AS unit
        ORDER BY v.date, concept
    """, patient_id=patient_id)

    timeline = {}
    for record in result:
        date = str(record["date"])
        if date not in timeline:
            timeline[date] = {
                "date": date,
                "visit_id": record["visit_id"],
                "age": record["age"],
                "t1d_duration": record["t1d_duration"],
                "smoking_status": record["smoking_status"],
                "hypertension_status": record["hypertension_status"],
                "dyslipidemia": record["dyslipidemia"],
                "known_ascvd": record["known_ascvd"],
                "known_cad": record["known_cad"],
                "ecg_abnormality": record["ecg_abnormality"],
                "cardiovascular_symptoms": record["cardiovascular_symptoms"],
                "clinical_action": record["clinical_action"]
            }
        concept = record["concept"]
        if concept:
            timeline[date][concept] = record["value"]

    return timeline


def generate_clinical_flags(trends, timeline):
    flags = []
    dates = sorted(timeline.keys())
    latest_visit = timeline[dates[-1]] if dates else {}

    # Blood pressure flags
    if "Systolic_BP" in trends:
        sbp = trends["Systolic_BP"]
        if sbp["latest"] >= 130:
            flags.append(f"Latest Systolic BP is hypertensive (>= 130 mmHg: {sbp['latest']} mmHg)")
        if sbp["direction"] in ["INCREASING", "MOSTLY_INCREASING"]:
            flags.append("Systolic blood pressure is progressively increasing across visits")

    if "Diastolic_BP" in trends:
        dbp = trends["Diastolic_BP"]
        if dbp["latest"] >= 80:
            flags.append(f"Latest Diastolic BP is elevated (>= 80 mmHg: {dbp['latest']} mmHg)")
        if dbp["direction"] in ["INCREASING", "MOSTLY_INCREASING"]:
            flags.append("Diastolic blood pressure is progressively increasing across visits")

    # Glycemic flags
    if "HbA1c" in trends:
        hba1c = trends["HbA1c"]
        if hba1c["latest"] >= 8.0:
            flags.append(f"Significantly elevated glycated hemoglobin (HbA1c {hba1c['latest']}%)")
        if hba1c["direction"] in ["INCREASING", "MOSTLY_INCREASING"]:
            flags.append("Glycemic control is deteriorating longitudinally")

    # Lipid flags
    if "LDL_Cholesterol" in trends:
        ldl = trends["LDL_Cholesterol"]
        if ldl["latest"] >= 160:
            flags.append(f"Markedly elevated LDL cholesterol (>= 160 mg/dL: {ldl['latest']} mg/dL)")
        elif ldl["latest"] >= 100:
            flags.append(f"Elevated LDL cholesterol above optimal diabetes target ({ldl['latest']} mg/dL)")
        if ldl["direction"] in ["INCREASING", "MOSTLY_INCREASING"]:
            flags.append("LDL cholesterol is on an upward trajectory")

    if "HDL_Cholesterol" in trends:
        hdl = trends["HDL_Cholesterol"]
        if hdl["latest"] < 40:
            flags.append(f"Low protective HDL cholesterol ({hdl['latest']} mg/dL)")

    if "Triglycerides" in trends:
        tg = trends["Triglycerides"]
        if tg["latest"] >= 150:
            flags.append(f"Elevated fasting triglycerides (>= 150 mg/dL: {tg['latest']} mg/dL)")

    # Renal-cardiovascular flags
    if "UACR" in trends:
        uacr = trends["UACR"]
        if uacr["latest"] >= 30:
            flags.append(f"Persistent albuminuria / elevated UACR ({uacr['latest']} mg/g)")
        if uacr["direction"] in ["INCREASING", "MOSTLY_INCREASING"]:
            flags.append("UACR is steadily rising, indicating progressive cardiorenal stress")

    if "eGFR" in trends:
        egfr = trends["eGFR"]
        if egfr["latest"] < 60:
            flags.append(f"Reduced estimated GFR (< 60 mL/min/1.73m2: {egfr['latest']})")
        elif egfr["direction"] in ["DECREASING", "MOSTLY_DECREASING"]:
            flags.append("eGFR shows longitudinal downward slope")

    # Natriuretic peptide (BNP) flags
    if "BNP_NTproBNP" in trends:
        bnp = trends["BNP_NTproBNP"]
        if bnp["latest"] >= 100:
            flags.append(f"Elevated BNP/NT-proBNP natriuretic peptide biomarker ({bnp['latest']} pg/mL) indicating increased heart failure risk")
        if bnp["direction"] in ["INCREASING", "MOSTLY_INCREASING"]:
            flags.append("Natriuretic peptide levels are progressively rising")

    # ECG and Symptoms flags
    ecg = latest_visit.get("ecg_abnormality")
    if ecg and ecg.lower() not in ["normal", "none", ""]:
        flags.append(f"Abnormal electrocardiogram finding: '{ecg}'")

    symptoms = latest_visit.get("cardiovascular_symptoms")
    if symptoms and symptoms.lower() not in ["no symptoms", "none", ""]:
        flags.append(f"Active cardiovascular symptoms reported: '{symptoms}'")

    # Behavioral flag
    smoking = latest_visit.get("smoking_status")
    if smoking and smoking.lower() in ["yes", "current", "active"]:
        flags.append("Active tobacco smoking status (major independent CVD risk factor)")

    return flags


def evaluate_rules(timeline, patient_meta):
    dates = sorted(timeline.keys())
    visits = [timeline[d] for d in dates]
    latest_visit = visits[-1] if visits else {}

    # R001: Hypertension (SBP >= 130 or DBP >= 80 mmHg)
    sbp_vals = [float(v["Systolic_BP"]) for v in visits if "Systolic_BP" in v]
    dbp_vals = [float(v["Diastolic_BP"]) for v in visits if "Diastolic_BP" in v]
    r001_elevated = sum(1 for i in range(min(len(sbp_vals), len(dbp_vals))) if sbp_vals[i] >= 130 or dbp_vals[i] >= 80)
    r001_satisfied = (sbp_vals and sbp_vals[-1] >= 130) or (dbp_vals and dbp_vals[-1] >= 80)
    r001 = {
        "rule_id": "R001",
        "name": "Hypertension Classification",
        "trigger": "Systolic_BP >= 130 mmHg OR Diastolic_BP >= 80 mmHg",
        "satisfied": bool(r001_satisfied),
        "latest_sbp": sbp_vals[-1] if sbp_vals else None,
        "latest_dbp": dbp_vals[-1] if dbp_vals else None,
        "elevated_count": r001_elevated,
        "total_visits": len(visits),
        "reason": f"Latest BP: {sbp_vals[-1] if sbp_vals else 'N/A'}/{dbp_vals[-1] if dbp_vals else 'N/A'} mmHg; elevated in {r001_elevated}/{len(visits)} visits"
    }

    # R002: Albuminuria (UACR >= 30 mg/g)
    uacr_vals = [float(v["UACR"]) for v in visits if "UACR" in v]
    r002_elevated = sum(1 for val in uacr_vals if val >= 30.0)
    r002_satisfied = r002_elevated >= 2 if len(uacr_vals) >= 2 else (uacr_vals and uacr_vals[-1] >= 30.0)
    r002 = {
        "rule_id": "R002",
        "name": "Albuminuria / Microvascular Risk",
        "trigger": "UACR >= 30 mg/g",
        "satisfied": bool(r002_satisfied),
        "latest_uacr": uacr_vals[-1] if uacr_vals else None,
        "elevated_count": r002_elevated,
        "total_measurements": len(uacr_vals),
        "reason": f"UACR >= 30 mg/g in {r002_elevated}/{len(uacr_vals)} visits (Latest: {uacr_vals[-1] if uacr_vals else 'N/A'} mg/g)"
    }

    # R003: Chronic Kidney Disease (eGFR < 60 mL/min/1.73m2)
    egfr_vals = [float(v["eGFR"]) for v in visits if "eGFR" in v]
    r003_reduced = sum(1 for val in egfr_vals if val < 60.0)
    r003_satisfied = r003_reduced >= 2 if len(egfr_vals) >= 2 else (egfr_vals and egfr_vals[-1] < 60.0)
    r003 = {
        "rule_id": "R003",
        "name": "Chronic Kidney Disease Stage Assessment",
        "trigger": "eGFR < 60 mL/min/1.73m2",
        "satisfied": bool(r003_satisfied),
        "latest_egfr": egfr_vals[-1] if egfr_vals else None,
        "reduced_count": r003_reduced,
        "total_measurements": len(egfr_vals),
        "reason": f"eGFR < 60 in {r003_reduced}/{len(egfr_vals)} visits (Latest: {egfr_vals[-1] if egfr_vals else 'N/A'} mL/min/1.73m2)"
    }

    # R004: Heart Failure Risk (BNP_NTproBNP abnormal / >= 100 pg/mL)
    bnp_vals = [float(v["BNP_NTproBNP"]) for v in visits if "BNP_NTproBNP" in v]
    r004_elevated = sum(1 for val in bnp_vals if val >= 100.0)
    r004_satisfied = bool(bnp_vals and bnp_vals[-1] >= 100.0)
    r004 = {
        "rule_id": "R004",
        "name": "Heart Failure Biomarker Risk State",
        "trigger": "BNP_NTproBNP is above abnormal threshold (>= 100 pg/mL)",
        "satisfied": r004_satisfied,
        "latest_bnp": bnp_vals[-1] if bnp_vals else None,
        "elevated_count": r004_elevated,
        "reason": f"Latest natriuretic peptide: {bnp_vals[-1] if bnp_vals else 'N/A'} pg/mL (>= 100 pg/mL threshold)"
    }

    # R005: Heart Failure Evaluation Indicated (After abnormal BNP, echocardiography recommended)
    r005_satisfied = r004_satisfied
    r005 = {
        "rule_id": "R005",
        "name": "Heart Failure Evaluation Indicated",
        "trigger": "Abnormal BNP_NTproBNP in diabetes context",
        "satisfied": r005_satisfied,
        "recommendation": "Echocardiography recommended by ADA Standards of Care to detect Stage B heart failure",
        "reason": "Triggered due to elevated natriuretic peptide biomarker" if r005_satisfied else "Natriuretic peptide within normal limits"
    }

    # R006: Secondary Cardiovascular Prevention Context (Established ASCVD / CAD)
    known_ascvd = latest_visit.get("known_ascvd", "").lower() in ["yes", "true"]
    known_cad = latest_visit.get("known_cad", "").lower() in ["yes", "true"]
    context_str = patient_meta.get("baseline_cvd_context", "").lower()
    has_neg = "no " in context_str or "without" in context_str or "none" in context_str
    meta_ascvd = any(k in context_str for k in ["established", "cad history", "prior mi", "documented cad"]) and not has_neg
    r006_satisfied = known_ascvd or known_cad or meta_ascvd
    r006 = {
        "rule_id": "R006",
        "name": "Secondary Cardiovascular Prevention Context",
        "trigger": "T1D AND established_ASCVD = true",
        "satisfied": r006_satisfied,
        "known_ascvd": known_ascvd or meta_ascvd,
        "known_cad": known_cad or meta_ascvd,
        "reason": "Patient has documented established ASCVD / prior myocardial infarction / CAD history" if r006_satisfied else "No prior documented ASCVD event or established CAD"
    }

    # R007: Coronary Investigation Considered (Symptoms or ECG abnormality in T1D)
    ecg = latest_visit.get("ecg_abnormality", "")
    ecg_abnormal = bool(ecg and ecg.lower() not in ["normal", "none", ""])
    symptoms = latest_visit.get("cardiovascular_symptoms", "")
    symptoms_neg = any(neg in symptoms.lower() for neg in ["no symptoms", "no acute", "none", "asymptomatic", "denies"])
    symptoms_present = bool(symptoms) and not symptoms_neg
    r007_satisfied = ecg_abnormal or symptoms_present
    r007 = {
        "rule_id": "R007",
        "name": "Coronary Investigation Considered",
        "trigger": "T1D AND (cardiac/vascular symptoms = true OR ECG_Abnormality = true)",
        "satisfied": r007_satisfied,
        "ecg_finding": ecg if ecg else "Normal",
        "symptoms": symptoms if symptoms else "No symptoms",
        "reason": f"Clinical findings warranting investigation: ECG='{ecg}', Symptoms='{symptoms}'" if r007_satisfied else "Asymptomatic with normal ECG; routine CAD screening not recommended"
    }

    return [r001, r002, r003, r004, r005, r006, r007]


def calculate_trajectory_signal(trends, rules, patient_meta):
    score = 0
    rule_map = {r["rule_id"]: r for r in rules}

    # Secondary prevention baseline
    if rule_map.get("R006", {}).get("satisfied"):
        score += 6

    # Hypertension
    if rule_map.get("R001", {}).get("satisfied"):
        score += 2
    if trends.get("Systolic_BP", {}).get("direction") in ["INCREASING", "MOSTLY_INCREASING"]:
        score += 1

    # Albuminuria / renal
    if rule_map.get("R002", {}).get("satisfied"):
        score += 2
    if trends.get("UACR", {}).get("direction") in ["INCREASING", "MOSTLY_INCREASING"]:
        score += 1

    # Dyslipidemia
    if trends.get("LDL_Cholesterol", {}).get("latest", 0) >= 160:
        score += 2
    elif trends.get("LDL_Cholesterol", {}).get("latest", 0) >= 100:
        score += 1
    if trends.get("LDL_Cholesterol", {}).get("direction") in ["INCREASING", "MOSTLY_INCREASING"]:
        score += 1

    # Glycemia
    if trends.get("HbA1c", {}).get("latest", 0) >= 8.0:
        score += 1
    if trends.get("HbA1c", {}).get("direction") in ["INCREASING", "MOSTLY_INCREASING"]:
        score += 1

    # Heart Failure Biomarker
    if rule_map.get("R004", {}).get("satisfied"):
        score += 3
    elif trends.get("BNP_NTproBNP", {}).get("direction") in ["INCREASING", "MOSTLY_INCREASING"]:
        score += 1

    # Coronary investigation / ECG / symptoms
    if rule_map.get("R007", {}).get("satisfied"):
        score += 2

    # Level classification
    if rule_map.get("R006", {}).get("satisfied") or score >= 9:
        level = "VERY_HIGH_CARDIOVASCULAR_RISK"
    elif score >= 6:
        level = "HIGH_CARDIOVASCULAR_RISK"
    elif score >= 3:
        level = "MODERATE_CARDIOVASCULAR_RISK"
    else:
        level = "LOW_CARDIOVASCULAR_RISK"

    return score, level


def print_trends(trends):
    print("\n" + "=" * 80)
    print("CARDIOVASCULAR LONGITUDINAL TRAJECTORY ANALYSIS")
    print("=" * 80)
    for variable, data in trends.items():
        vals_str = " -> ".join(str(v) for v in data["values"])
        print(f"\n{variable:22} [{data['direction']}] (monotonicity: {data['monotonicity']})")
        print(f"  Trajectory:       {vals_str}")
        print(f"  First -> Latest:  {data['first']} -> {data['latest']}")
        print(f"  Absolute Delta:   {data['absolute_change']:+.2f}")
        print(f"  Percentage Delta: {data['percentage_change']:+.1f}%")
        print(f"  Slope:            {data['slope']:+.4f} | Variability: {data['variability']:.4f}")


def print_rule_results(rules):
    print("\n" + "=" * 80)
    print("CLINICAL RULE & EVIDENCE EVALUATION (R001 - R007)")
    print("=" * 80)
    for r in rules:
        status_str = "[TRIGGERED / SATISFIED]" if r["satisfied"] else "[NOT SATISFIED / NEGATIVE]"
        print(f"\n{r['rule_id']} — {r['name']}: {status_str}")
        print(f"  Trigger Condition: {r['trigger']}")
        print(f"  Clinical Reason:   {r['reason']}")
        if "recommendation" in r:
            print(f"  Clinical Action:   {r['recommendation']}")


def analyze_patient_id(session, patient_id):
    meta = get_patient_metadata(session, patient_id)
    if not meta:
        print(f"Patient {patient_id} not found.")
        return

    timeline = get_patient_timeline(session, patient_id)
    if not timeline:
        print(f"No visit records found for {patient_id}.")
        return

    print("\n" + "#" * 80)
    print(f"PATIENT TRAJECTORY REPORT: {patient_id} ({meta.get('label', '')})")
    print("#" * 80)
    print(f"Demographics: Age {meta.get('age', 'N/A')} | Sex: {meta.get('sex', 'N/A')} | T1D Duration: {meta.get('t1d_duration', 'N/A')} yrs")
    print(f"Baseline Context: {meta.get('baseline_cvd_context', 'None')}")
    print(f"Design Pattern:   {meta.get('temporal_pattern', 'None')}")
    print(f"Visits Recorded:  {len(timeline)}")

    engine_analysis = calculate_trends(timeline)
    print_trends(engine_analysis)

    worsening = determine_worsening_variables(engine_analysis)
    print("\n" + "=" * 80)
    print("WORSENING CARDIOVASCULAR VARIABLES")
    print("=" * 80)
    if worsening:
        for v in worsening:
            print(f"  - {v} (Direction: {engine_analysis[v]['direction']}, Delta: {engine_analysis[v]['absolute_change']:+.2f})")
    else:
        print("  - None (all monitored cardiovascular variables stable or improving)")

    cross_patterns = detect_cross_variable_patterns(engine_analysis)
    print("\n" + "=" * 80)
    print("CROSS-VARIABLE INTERACTION PATTERNS")
    print("=" * 80)
    if cross_patterns:
        for p in cross_patterns:
            print(f"  - {p}")
    else:
        print("  - No concurrent cross-variable worsening patterns detected")

    flags = generate_clinical_flags(engine_analysis, timeline)
    print("\n" + "=" * 80)
    print("CLINICAL RISK FLAGS")
    print("=" * 80)
    if flags:
        for f in flags:
            print(f"  [!] {f}")
    else:
        print("  - No active high-risk clinical flags")

    rules = evaluate_rules(timeline, meta)
    print_rule_results(rules)

    score, level = calculate_trajectory_signal(engine_analysis, rules, meta)
    pat_pattern = classify_patient_pattern(engine_analysis, cross_patterns, meta.get("baseline_cvd_context"))

    print("\n" + "=" * 80)
    print("CARDIOVASCULAR RISK FORECAST SUMMARY")
    print("=" * 80)
    print(f"Calculated Trajectory Score: {score}")
    print(f"Risk Signal Level:           {level}")
    print(f"Classified Temporal Pattern: {pat_pattern}")
    print("=" * 80 + "\n")


def main():
    target_pid = sys.argv[1] if len(sys.argv) > 1 else None
    driver = get_driver()
    try:
        driver.verify_connectivity()
        with driver.session(database=DATABASE) as session:
            if target_pid:
                analyze_patient_id(session, target_pid)
            else:
                p_res = session.run("MATCH (p:Patient) RETURN p.patient_id AS pid ORDER BY pid")
                pids = [r["pid"] for r in p_res]
                if not pids:
                    print("No patients in database. Run build_demo_patients.py first.")
                    return
                for pid in pids:
                    analyze_patient_id(session, pid)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
