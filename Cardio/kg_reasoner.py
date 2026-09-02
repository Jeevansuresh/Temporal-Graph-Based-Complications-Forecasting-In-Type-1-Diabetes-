import os
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI

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

neo4j_driver = get_driver()

API_KEY = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_MAIN", "gpt-4.1-mini")

def get_llm_client():
    if not API_KEY:
        return None
    try:
        if ENDPOINT:
            return OpenAI(api_key=API_KEY, base_url=ENDPOINT)
        else:
            return OpenAI(api_key=API_KEY)
    except Exception as e:
        print(f"Warning: Could not initialize LLM client: {e}")
        return None

azure_client = get_llm_client()


def get_patient_data(session, patient_id):
    result = session.run("""
        MATCH (p:Patient {patient_id: $patient_id})
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
            m.value AS value
        ORDER BY v.date
    """, patient_id=patient_id)

    timeline = {}
    for record in result:
        date = str(record["date"])
        concept = record["concept"]
        value = record["value"]
        if date not in timeline:
            timeline[date] = {}
        timeline[date][concept] = value

    return timeline


def get_clinical_knowledge(session):
    result = session.run("""
        MATCH (a:Concept)-[r:CLINICAL_RELATIONSHIP]->(b:Concept)
        RETURN
            a.name AS source,
            r.relation AS relationship,
            b.name AS target,
            r.evidence_id AS evidence_id,
            r.confidence AS confidence,
            r.population AS population
    """)
    knowledge = []
    for record in result:
        knowledge.append({
            "source": record["source"],
            "relationship": record["relationship"],
            "target": record["target"],
            "evidence_id": record["evidence_id"],
            "confidence": record["confidence"],
            "population": record["population"]
        })
    return knowledge


def calculate_trends(timeline):
    dates = sorted(timeline.keys())
    variables = [
        "Systolic_BP",
        "Diastolic_BP",
        "HbA1c",
        "LDL_Cholesterol",
        "HDL_Cholesterol",
        "Triglycerides",
        "UACR",
        "eGFR",
        "BNP_NTproBNP"
    ]

    trends = {}
    for variable in variables:
        values = [
            float(timeline[date][variable])
            for date in dates
            if variable in timeline[date] and timeline[date][variable] is not None
        ]

        if len(values) < 2:
            continue

        changes = [values[i] - values[i - 1] for i in range(1, len(values))]

        if all(change > 0 for change in changes):
            direction = "INCREASING"
        elif all(change < 0 for change in changes):
            direction = "DECREASING"
        elif sum(change > 0 for change in changes) > sum(change < 0 for change in changes):
            direction = "MOSTLY_INCREASING"
        elif sum(change < 0 for change in changes) > sum(change > 0 for change in changes):
            direction = "MOSTLY_DECREASING"
        else:
            direction = "MIXED"

        trends[variable] = {
            "values": values,
            "direction": direction,
            "first": values[0],
            "latest": values[-1],
            "absolute_change": round(values[-1] - values[0], 4)
        }

    return trends


def find_relevant_knowledge(trends, knowledge):
    worsening_variables = []
    for variable, data in trends.items():
        direction = data["direction"]
        if variable in ["HDL_Cholesterol", "eGFR"]:
            worsening = direction in ["DECREASING", "MOSTLY_DECREASING"]
        else:
            worsening = direction in ["INCREASING", "MOSTLY_INCREASING"]

        if worsening:
            worsening_variables.append(variable)

    relevant = []
    for item in knowledge:
        if item["source"] in worsening_variables or item["source"] in ["T1D", "T1D_Duration", "Hypertension", "Dyslipidemia", "Albuminuria"]:
            relevant.append(item)

    return relevant


def ask_azure(patient_id, patient_data, trends, relevant_knowledge):
    if not azure_client:
        return "Azure OpenAI is not configured. Reasoner finished with structured packets."

    prompt = f"""
You are a clinical reasoning research assistant specializing in cardiovascular risk in Type 1 diabetes.

You are analyzing synthetic patient {patient_id} for longitudinal cardiovascular risk signals.

Your task is NOT to diagnose the patient.

Your task is to identify longitudinal cardiovascular risk signals using ONLY:
1. The patient's temporal measurements.
2. The clinical relationships retrieved from the knowledge graph.

PATIENT TIMELINE:
{json.dumps(patient_data, indent=2)}

TEMPORAL TRENDS:
{json.dumps(trends, indent=2)}

CLINICAL KNOWLEDGE GRAPH RELATIONSHIPS:
{json.dumps(relevant_knowledge, indent=2)}

Analyze:
1. Which cardiovascular risk factors/measurements are worsening over time?
2. Which worsening measurements have a direct KG relationship to Cardiovascular_Risk, ASCVD, or Heart_Failure_Risk?
3. Are multiple cardiometabolic variables worsening together (e.g. BP + Lipids + Albuminuria)?
4. What is the strongest longitudinal pattern?
5. Are there important clinical limitations, follow-up actions (e.g., echocardiography for abnormal BNP), or reasons not to treat this as an automated diagnosis?

Return the answer in this exact structure:

TEMPORAL FINDINGS:
- ...

KG-GROUNDED FINDINGS:
- ...

JOINT PATTERN:
- ...

CLINICAL INTERPRETATION:
- ...

LIMITATIONS & RECOMMENDED INVESTIGATIONS:
- ...

Do not invent medical relationships that are not present in the supplied knowledge graph.
"""

    response = azure_client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": "You are an evidence-grounded clinical reasoning assistant for cardiovascular disease in Type 1 diabetes."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )
    return response.choices[0].message.content


def main():
    target_pid = sys.argv[1] if len(sys.argv) > 1 else "P001"
    try:
        neo4j_driver.verify_connectivity()
        print("NEO4J CONNECTED")
        with neo4j_driver.session(database=DATABASE) as session:
            patient_data = get_patient_data(session, target_pid)
            if not patient_data:
                print(f"Patient {target_pid} not found.")
                return

            trends = calculate_trends(patient_data)
            knowledge = get_clinical_knowledge(session)
            relevant_knowledge = find_relevant_knowledge(trends, knowledge)

            print("\n" + "=" * 80)
            print(f"PATIENT TEMPORAL DATA ({target_pid})")
            print("=" * 80)
            print(json.dumps(patient_data, indent=2))

            print("\n" + "=" * 80)
            print("TEMPORAL TRENDS")
            print("=" * 80)
            print(json.dumps(trends, indent=2))

            print("\n" + "=" * 80)
            print("KG RELATIONSHIPS RETRIEVED")
            print("=" * 80)
            for item in relevant_knowledge:
                print(f"  {item['source']} --[{item['relationship']}]--> {item['target']} (Evidence: {item['evidence_id']}, Confidence: {item['confidence']})")

            print("\n" + "=" * 80)
            print("AZURE OPENAI REASONING")
            print("=" * 80)
            answer = ask_azure(target_pid, patient_data, trends, relevant_knowledge)
            print(answer)

    finally:
        neo4j_driver.close()


if __name__ == "__main__":
    main()
