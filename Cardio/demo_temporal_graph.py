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


def get_patient_ids(session):
    result = session.run("""
        MATCH (p:Patient)
        RETURN p.patient_id AS patient_id
        ORDER BY patient_id
    """)
    return [record["patient_id"] for record in result]


def get_patient_info(session, patient_id):
    result = session.run("""
        MATCH (p:Patient {patient_id: $patient_id})
        RETURN
            p.patient_id AS patient_id,
            p.label AS label,
            p.age AS age,
            p.sex AS sex,
            p.t1d_duration AS t1d_duration,
            p.baseline_cvd_context AS baseline_cvd_context,
            p.temporal_pattern AS temporal_pattern
    """, patient_id=patient_id)
    rec = result.single()
    return dict(rec) if rec else None


def get_patient_timeline(session, patient_id):
    result = session.run("""
        MATCH
            (p:Patient {patient_id: $patient_id})
            -[:HAS_VISIT]->
            (v:Visit)
            -[:HAS_MEASUREMENT]->
            (m:Measurement)
            -[:INSTANCE_OF]->
            (c:Concept)
        RETURN
            v.visit_id AS visit_id,
            v.date AS date,
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
                "visit_id": record["visit_id"]
            }
        timeline[date][record["concept"]] = {
            "value": record["value"],
            "unit": record["unit"]
        }
    return timeline


def convert_timeline_for_engine(timeline):
    converted = {}
    for date, measurements in timeline.items():
        converted[date] = {}
        for concept, data in measurements.items():
            if isinstance(data, dict) and "value" in data:
                converted[date][concept] = data["value"]
            else:
                converted[date][concept] = data
    return converted


def print_patient(patient, timeline, trends):
    print("\n" + "=" * 80)
    print(f"PATIENT {patient['patient_id']} — {patient.get('label', '')}")
    print("=" * 80)
    print(f"Demographics:      Age {patient['age']} | Sex: {patient['sex']} | T1D Duration: {patient['t1d_duration']} years")
    print(f"Baseline Context:  {patient.get('baseline_cvd_context', 'N/A')}")
    print(f"Temporal Pattern:  {patient.get('temporal_pattern', 'N/A')}")
    print("\nTEMPORAL GRAPH (VISITS & MEASUREMENTS)")
    print("-" * 80)

    for date in sorted(timeline.keys()):
        vid = timeline[date].get("visit_id", "")
        print(f"\n[Visit {vid} | Date: {date}]")
        for concept, data in timeline[date].items():
            if concept == "visit_id":
                continue
            if isinstance(data, dict):
                unit_str = f" {data['unit']}" if data.get('unit') else ""
                print(f"  {concept:22} = {data['value']}{unit_str}")
            else:
                print(f"  {concept:22} = {data}")

    print("\nLONGITUDINAL TRAJECTORIES")
    print("-" * 80)
    for variable, data in trends.items():
        change = data["absolute_change"]
        pct = data["percentage_change"]
        print(
            f"{variable:22} "
            f"{data['first']} -> {data['latest']}   "
            f"[{data['direction']:18}] "
            f"delta = {change:+.2f} ({pct:+.1f}%)"
        )

    worsening = determine_worsening_variables(trends)
    cross = detect_cross_variable_patterns(trends)
    pat_pat = classify_patient_pattern(trends, cross, patient.get("baseline_cvd_context"))

    print("\nWORSENING VARIABLES")
    print("-" * 80)
    if worsening:
        for w in worsening:
            print(f"  - {w}")
    else:
        print("  None (All markers stable or improving)")

    print(f"\nCLASSIFIED PATTERN: {pat_pat}")
    print("-" * 80)


def main():
    driver = get_driver()
    try:
        driver.verify_connectivity()
        print("NEO4J CONNECTED")
        with driver.session(database=DATABASE) as session:
            patient_ids = get_patient_ids(session)
            print(f"\nFOUND {len(patient_ids)} CARDIO PATIENTS IN NEO4J GRAPH")

            for pid in patient_ids:
                patient = get_patient_info(session, pid)
                timeline = get_patient_timeline(session, pid)
                engine_timeline = convert_timeline_for_engine(timeline)
                trends = calculate_trends(engine_timeline)
                print_patient(patient, timeline, trends)

            print("\n" + "=" * 80)
            print("CARDIO TEMPORAL GRAPH DEMO COMPLETE")
            print("=" * 80 + "\n")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
